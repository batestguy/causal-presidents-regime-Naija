"""Stage 1 reconnaissance: which candidate indicators actually have coverage?

Fetches candidate World Bank indicators and reports non-null coverage, so indicator
selection is made on evidence rather than on the base spec's assumption.

This is a **reconnaissance tool**: it lands nothing and writes no vintage. Coverage of a
candidate that gets adopted is re-fetched properly through ``pull_worldbank.py``.

The critical test is whether a series reaches 2015+ — without that, the series cannot see
the APC tenures and cannot support a party comparison.

Run:
    conda run -p "C:/Users/TOSHIBA/ds-general" python ingestion/flows/probe_candidates.py
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from ingestion.clients.worldbank import WorldBankError, fetch_indicator  # noqa: E402

# The study window ends at the current administration, so a usable series must reach 2015+.
APC_FLOOR = 2015

CANDIDATES = [
    # domain, metric_id, indicator_id, short name
    ("education", "primary_completion", "SE.PRM.CMPT.ZS", "Primary completion rate"),
    ("education", "lower_sec_completion", "SE.SEC.CMPT.LO.ZS", "Lower secondary completion"),
    ("education", "educ_spend_gdp", "SE.XPD.TOTL.GD.ZS", "Govt expenditure on education (% GDP)"),
    ("education", "adult_literacy", "SE.ADT.LITR.ZS", "Adult literacy rate"),
    ("education", "pupil_teacher", "SE.PRM.ENRL.TC.ZS", "Pupil-teacher ratio, primary"),
    ("education", "tertiary_enrol", "SE.TER.ENRR", "Tertiary enrolment (gross %)"),
    ("health", "u5mr", "SH.DYN.MORT", "Under-5 mortality"),
    ("health", "neonatal_mr", "SH.DYN.NMR", "Neonatal mortality"),
    ("health", "skilled_birth", "SH.STA.BRTC.ZS", "Births attended by skilled staff (%)"),
    ("health", "measles_imm", "SH.IMM.MEAS", "Measles immunisation (% 12-23m)"),
    ("health", "health_spend_gdp", "SH.XPD.CHEX.GD.ZS", "Current health expenditure (% GDP)"),
    ("health", "life_expectancy", "SP.DYN.LE00.IN", "Life expectancy at birth"),
    ("economy", "gdp_per_capita", "NY.GDP.PCAP.KD", "GDP per capita (constant)"),
    ("economy", "population", "SP.POP.TOTL", "Population, total"),
    ("security", "homicides", "VC.IHR.PSRC.P5", "Intentional homicides (per 100k)"),
]


def coverage_of(rows: list[dict]) -> tuple[int, int | None, int | None, list[int]]:
    years = sorted(int(r["date"]) for r in rows if r.get("value") is not None)
    if not years:
        return 0, None, None, []
    seen = set(years)
    missing = [y for y in range(years[0], years[-1] + 1) if y not in seen]
    return len(years), years[0], years[-1], missing


def main() -> int:
    print(f"{'domain':<10}{'metric':<22}{'n':>4}  {'span':<12}{'miss':>5}  verdict")
    print("-" * 78)

    usable: list[str] = []
    unusable: list[str] = []

    for domain, metric_id, indicator_id, name in CANDIDATES:
        try:
            _, rows = fetch_indicator(indicator_id, name)
        except (WorldBankError, ValueError) as exc:
            print(f"{domain:<10}{metric_id:<22}{'--':>4}  {'--':<12}{'--':>5}  FETCH FAILED: {exc}")
            unusable.append(f"{metric_id} (fetch failed)")
            continue

        n, first, last, missing = coverage_of(rows)
        if n == 0:
            verdict = "EMPTY — no usable data"
            unusable.append(metric_id)
        elif last is not None and last >= APC_FLOOR:
            verdict = "covers APC era"
            usable.append(metric_id)
        else:
            verdict = f"STOPS {last} — cannot see APC tenure"
            unusable.append(metric_id)

        span = f"{first}-{last}" if first is not None else "--"
        print(f"{domain:<10}{metric_id:<22}{n:>4}  {span:<12}{len(missing):>5}  {verdict}")

    print()
    print(f"covers 2015+: {len(usable)} of {len(CANDIDATES)}")
    for metric in usable:
        print(f"  + {metric}")
    print(f"cannot cover the APC era: {len(unusable)}")
    for metric in unusable:
        print(f"  - {metric}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
