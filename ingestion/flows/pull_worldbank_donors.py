"""Stage 2 ingestion flow: the synthetic-control donor panel (Design C).

Design C needs a counterfactual for Nigeria, built from a donor pool that is *screened on fit*
rather than fixed (design spec section 5.3). That screening needs each candidate donor's
predictor set, which nothing was fetching — the DAG's ``donors`` and ``common`` nodes had no data
behind them.

``probe_missing_variables.py`` verified that all 13 candidates carry all 5 predictors keylessly
(Venezuela is partial: its oil-rents series does not reach 2015). This flow lands them.

Writes, per vintage:

    data/raw/worldbank_donors/<vintage>/<indicator_id>/page-0001.json
    data/raw/worldbank_donors/<vintage>/manifest.json
    data/raw/worldbank_donors/<vintage>/coverage.json

One multi-country request per predictor, so a donor cannot be silently half-landed: the row-count
assertion in the client fires if pagination truncates.

Run:
    conda run -p "C:/Users/TOSHIBA/ds-general" python ingestion/flows/pull_worldbank_donors.py
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

RAW_ROOT = REPO_ROOT / "data" / "raw" / "worldbank_donors"
APC_FLOOR = 2015
STUDY_FLOOR = 1999

# Design spec section 5.3: West African neighbours plus oil exporters.
DONORS = {
    "GH": "Ghana",
    "SN": "Senegal",
    "CI": "Cote d'Ivoire",
    "KE": "Kenya",
    "TZ": "Tanzania",
    "ZA": "South Africa",
    "AO": "Angola",
    "DZ": "Algeria",
    "GA": "Gabon",
    "EC": "Ecuador",
    "ID": "Indonesia",
    "CO": "Colombia",
    "VE": "Venezuela",
}

# The predictor set the pool is screened on.
PREDICTORS = [
    ("gdp_growth", "NY.GDP.MKTP.KD.ZG", "GDP growth (annual %)"),
    ("cpi_yoy", "FP.CPI.TOTL.ZG", "Inflation, consumer prices (annual %)"),
    ("oil_rents", "NY.GDP.PETR.RT.ZS", "Oil rents (% of GDP)"),
    ("population", "SP.POP.TOTL", "Population, total"),
    ("u5mr", "SH.DYN.MORT", "Under-5 mortality rate (per 1,000 live births)"),
]


def _per_country(rows: list[dict]) -> dict[str, dict]:
    """Per-donor coverage: observations, span, and whether the series reaches the screen floors."""
    out: dict[str, dict] = {}
    for row in rows:
        country = (((row.get("country") or {}).get("id")) or row.get("countryiso3code") or "").upper()
        if country not in DONORS or row.get("value") is None:
            continue
        bucket = out.setdefault(country, {"n": 0, "years": []})
        bucket["n"] += 1
        bucket["years"].append(int(row["date"]))
    for country, bucket in out.items():
        years = sorted(bucket.pop("years"))
        bucket["first_year"] = years[0]
        bucket["last_year"] = years[-1]
        bucket["reaches_1999"] = years[0] <= STUDY_FLOOR
        bucket["reaches_2015"] = years[-1] >= APC_FLOOR
    return out


def main() -> int:
    vintage = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    vintage_dir = RAW_ROOT / vintage
    vintage_dir.mkdir(parents=True, exist_ok=True)
    countries = ";".join(DONORS)

    entries = []
    coverage: dict[str, dict] = {}
    failures = []

    print(f"vintage: {vintage}")
    print(f"landing: {vintage_dir.relative_to(REPO_ROOT)}")
    print(f"donors:  {len(DONORS)}  predictors: {len(PREDICTORS)}")
    print()

    for label, indicator_id, name in PREDICTORS:
        try:
            retrieval, rows = fetch_indicator(indicator_id, name, country=countries)
        except (WorldBankError, ValueError) as exc:
            failures.append({"metric_id": label, "indicator_id": indicator_id, "error": str(exc)})
            print(f"  FAIL {label:<14} {indicator_id:<18} {exc}")
            continue

        page_files = write_pages(vintage_dir / indicator_id, retrieval.payloads, REPO_ROOT)
        entries.append(retrieval.manifest_entry(
            metric_id=label,
            note="donor-panel predictor for synthetic-control screening",
            page_files=page_files,
            n_countries=len(DONORS),
        ))

        per_country = _per_country(rows)
        coverage[label] = {
            "indicator_id": indicator_id,
            "indicator_name": name,
            "n_donors_with_data": len(per_country),
            "n_donors_reaching_2015": sum(v["reaches_2015"] for v in per_country.values()),
            "countries": per_country,
        }
        print(f"  ok   {label:<14} {indicator_id:<18} donors={len(per_country)}/{len(DONORS)} "
              f"reaching_2015={coverage[label]['n_donors_reaching_2015']}/{len(DONORS)} "
              f"sha256={retrieval.sha256[:8]}")

    write_manifest(
        vintage_dir=vintage_dir,
        vintage_date=vintage,
        source="worldbank_donors",
        entries=entries,
        failures=failures,
        extra={
            "n_indicators_requested": len(PREDICTORS),
            "donors": DONORS,
            "n_donors": len(DONORS),
        },
    )
    (vintage_dir / "coverage.json").write_text(
        json.dumps(
            {
                "vintage_date": vintage,
                "purpose": "synthetic-control donor screening (Design C)",
                "donors": DONORS,
                "predictors": coverage,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    print()
    print(f"succeeded: {len(entries)}/{len(PREDICTORS)}   failures: {len(failures)}")
    if failures:
        print("counts as an incomplete vintage — see manifest.failures")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
