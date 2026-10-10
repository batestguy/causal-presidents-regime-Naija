"""Stage 2 ingestion flow: pull the World Bank subset of the metric catalogue.

Writes, per vintage (``vintage_date`` = UTC date of the run):

    data/raw/worldbank/<vintage>/<indicator_id>/page-0001.json   bytes as received
    data/raw/worldbank/<vintage>/manifest.json                   provenance for every retrieval
    data/raw/worldbank/<vintage>/coverage.json                   provisional coverage / gap report

The coverage report is a *provisional* look at Stage 3: it applies the gap and spike
gates so problems surface at ingest rather than during modelling. It is not the
authoritative Stage 3 quality report.

Run:
    conda run -p "C:/Users/TOSHIBA/ds-general" python ingestion/flows/pull_worldbank.py
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from ingestion.clients.provenance import write_manifest, write_pages  # noqa: E402
from ingestion.clients.worldbank import WorldBankError, fetch_indicator  # noqa: E402

RAW_ROOT = REPO_ROOT / "data" / "raw" / "worldbank"

# World Bank-sourced members of the metric catalogue, selected on evidence from
# probe_candidates.py (2026-10-10) rather than on the base spec's assumption.
# (metric_id, indicator_id, indicator_name, note)
INDICATORS = [
    # --- health ---
    ("u5mr", "SH.DYN.MORT", "Under-5 mortality rate (per 1,000 live births)", "61 obs, no gaps, to 2024"),
    ("neonatal_mr", "SH.DYN.NMRT", "Neonatal mortality rate (per 1,000 live births)", "verified code (SH.DYN.NMR is invalid)"),
    ("measles_imm", "SH.IMM.MEAS", "Immunisation, measles (% of children ages 12-23 months)", "41 obs, no gaps"),
    ("health_spend_gdp", "SH.XPD.CHEX.GD.ZS", "Current health expenditure (% of GDP)", "24 obs, no gaps, 2000-2023"),
    ("life_expectancy", "SP.DYN.LE00.IN", "Life expectancy at birth, total (years)", "65 obs, no gaps"),
    # --- economy ---
    ("gdp_growth", "NY.GDP.MKTP.KD.ZG", "GDP growth (annual %)", "65 obs, no gaps"),
    ("gdp_per_capita", "NY.GDP.PCAP.KD", "GDP per capita (constant)", "denominator / control"),
    ("cpi_yoy", "FP.CPI.TOTL.ZG", "Inflation, consumer prices (annual %)", "66 obs, no gaps"),
    ("population", "SP.POP.TOTL", "Population, total", "denominator for per-capita doses"),
    # --- education ---
    # These two stop in 2010/2011: they cover the PDP era only and CANNOT see the APC tenure.
    ("primary_completion", "SE.PRM.CMPT.ZS", "Primary completion rate, total (% of relevant age)", "STOPS 2010 — PDP era only"),
    ("ner_primary", "SE.PRM.NENR", "School enrollment, primary, net (%)", "STOPS 2010 — PDP era only"),
    # Education series that DO reach the APC era, but sparsely.
    ("educ_spend_gdp", "SE.XPD.TOTL.GD.ZS", "Government expenditure on education (% of GDP)", "14 obs to 2023 — a policy variable, not an outcome"),
    ("adult_literacy", "SE.ADT.LITR.ZS", "Literacy rate, adult total (% ages 15+)", "6 obs only — too sparse for time series"),
    ("literacy_youth", "SE.ADT.1524.LT.ZS", "Literacy rate, youth total (% ages 15-24)", "8 obs across 34 years, 11-year hole — base-spec §6 metric, retained for completeness"),
    # --- security (World Bank-hosted proxy; ACLED/UCDP remain the real sources) ---
    ("homicides", "VC.IHR.PSRC.P5", "Intentional homicides (per 100,000 people)", "3 obs to 2023 — proxy only"),
]

# Provisional gate thresholds (Stage 3 will own these).
SPIKE_THRESHOLD_PCT = 50.0


def _gap_profile(rows: list[dict]) -> dict:
    """Coverage of one annual series: span, missing years, and the year-on-year spike gate."""
    observed = sorted(int(r["date"]) for r in rows if r.get("value") is not None)
    if not observed:
        return {
            "n_observed": 0,
            "first_year": None,
            "last_year": None,
            "missing_years": [],
            "gap_runs": [],
            "gap_gate_tripped": True,
            "spike_gate_tripped": False,
            "spikes": [],
            "note": "no non-null observations returned",
        }

    seen = set(observed)
    missing = [y for y in range(observed[0], observed[-1] + 1) if y not in seen]

    gap_runs: list[list[int]] = []
    if missing:
        run = [missing[0]]
        for year in missing[1:]:
            if year == run[-1] + 1:
                run.append(year)
            else:
                gap_runs.append([run[0], run[-1]])
                run = [year]
        gap_runs.append([run[0], run[-1]])

    # Spike gate: |year-on-year relative change| above threshold.
    values = {int(r["date"]): r["value"] for r in rows if r.get("value") is not None}
    spikes = []
    ordered = sorted(values)
    for prev, curr in zip(ordered, ordered[1:]):
        base = values[prev]
        if base in (None, 0):
            continue
        change = (values[curr] - base) / abs(base) * 100.0
        if abs(change) > SPIKE_THRESHOLD_PCT:
            spikes.append(
                {
                    "from_year": prev,
                    "to_year": curr,
                    "change_pct": round(change, 1),
                }
            )

    return {
        "n_observed": len(observed),
        "first_year": observed[0],
        "last_year": observed[-1],
        "n_missing_inside_span": len(missing),
        "missing_years": missing,
        "gap_runs": gap_runs,
        "gap_gate_tripped": bool(missing),
        "spike_gate_tripped": bool(spikes),
        "spikes": spikes,
    }


def main() -> int:
    vintage = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    vintage_dir = RAW_ROOT / vintage
    vintage_dir.mkdir(parents=True, exist_ok=True)

    manifest_entries = []
    coverage: dict[str, dict] = {}
    failures = []

    print(f"vintage: {vintage}")
    print(f"landing: {vintage_dir.relative_to(REPO_ROOT)}")
    print()

    for metric_id, indicator_id, name, note in INDICATORS:
        try:
            retrieval, rows = fetch_indicator(indicator_id, name)
        except (WorldBankError, ValueError) as exc:
            failures.append({"metric_id": metric_id, "indicator_id": indicator_id, "error": str(exc)})
            print(f"  FAIL {metric_id:<20} {indicator_id:<18} {exc}")
            continue

        # Raw payload, one file per page, bytes untouched.
        page_files = write_pages(vintage_dir / indicator_id, retrieval.payloads, REPO_ROOT)

        entry = retrieval.manifest_entry(metric_id=metric_id, note=note, page_files=page_files)
        manifest_entries.append(entry)

        profile = _gap_profile(rows)
        profile["indicator_id"] = indicator_id
        profile["indicator_name"] = name
        coverage[metric_id] = profile

        flag = ""
        if profile["gap_gate_tripped"]:
            flag += " GAP"
        if profile["spike_gate_tripped"]:
            flag += " SPIKE"
        print(
            f"  ok   {metric_id:<20} {indicator_id:<18} rows={profile['n_observed']:<4} "
            f"{profile['first_year']}-{profile['last_year']} sha256={retrieval.sha256[:8]}{flag}"
        )

    write_manifest(
        vintage_dir=vintage_dir,
        vintage_date=vintage,
        source="worldbank",
        entries=manifest_entries,
        failures=failures,
        extra={"n_indicators_requested": len(INDICATORS)},
    )
    (vintage_dir / "coverage.json").write_text(
        json.dumps(
            {
                "vintage_date": vintage,
                "provisional": True,
                "note": "Stage 3 owns the authoritative quality report; this is an ingest-time view.",
                "spike_threshold_pct": SPIKE_THRESHOLD_PCT,
                "metrics": coverage,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    print()
    print(f"succeeded: {len(manifest_entries)}/{len(INDICATORS)}   failures: {len(failures)}")
    print(f"manifest: {(vintage_dir / 'manifest.json').relative_to(REPO_ROOT)}")
    print(f"coverage: {(vintage_dir / 'coverage.json').relative_to(REPO_ROOT)}")

    if failures:
        print()
        print("counts as an incomplete vintage — see manifest.failures")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
