"""Stage 1 reconnaissance: variables the causal graphs require but ingestion does not yet source.

The DAG layer (``registry/dags``) names every variable each design needs. This flow takes the
difference between that vocabulary and what ``pull_worldbank.py`` actually lands, and probes each
gap for reachability — so "what are we missing" is answered with measurements, not guesses.

Three groups are tested:

1. **Missing outcomes** — catalogue metrics with no usable series (education, security, and the
   health outcomes currently pinned to survey sources).
2. **Missing covariates** — DAG nodes with no source at all: the exchange rate, donor funding,
   and the oil-channel proxy used to screen the synthetic-control donor pool.
3. **The donor pool** — whether the candidate donor countries actually carry the predictor set
   the synthetic control screens on.

Nothing here lands a vintage; reconnaissance only. Anything adopted is re-fetched properly
through ``pull_worldbank.py``.

The tests that matter, per the study window:
  * does the series reach 1999+ (the first administration), and
  * does it reach 2015+ (without which it cannot see the APC tenures at all).

Run:
    conda run -p "C:/Users/TOSHIBA/ds-general" python ingestion/flows/probe_missing_variables.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import requests

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from ingestion.clients.fred import fetch_series, get_api_key  # noqa: E402
from ingestion.clients.provenance import MissingCredential, load_env_file  # noqa: E402
from ingestion.clients.worldbank import WorldBankError, fetch_indicator  # noqa: E402

STUDY_FLOOR = 1999
APC_FLOOR = 2015

# ------------------------------------------------------------------------------------------
# 1+2. missing outcomes and covariates, all keyless World Bank indicators
# ------------------------------------------------------------------------------------------
# (variable, status, needed_by, indicator_id, indicator_name, note)
MISSING = [
    (
        "mmr", "outcome", "Design A/B/C outcome (maternal mortality)",
        "SH.STA.MMRT", "Maternal mortality ratio (per 100,000 live births)",
        "catalogue source is NDHS/WHO (5-yearly, interpolated); this is the keyless annual series",
    ),
    (
        "skilled_birth", "outcome", "Design A/B/C outcome (skilled birth attendance)",
        "SH.STA.BRTC.ZS", "Births attended by skilled health staff (% of total)",
        "catalogue source is NDHS/MICS; this is the keyless series",
    ),
    (
        "immun_penta3", "outcome", "Design A/B/C outcome (penta3 coverage)",
        "SH.IMM.IDPT", "Immunization, DPT (% of children ages 12-23 months)",
        "DHIS2 penta3 is credential-blocked; DPT3 is the annual national proxy for the same antigen",
    ),
    (
        "unemp", "outcome", "Design A/B/C outcome (unemployment)",
        "SL.UEM.TOTL.ZS", "Unemployment, total (% of labor force, modelled ILO estimate)",
        "NBS methodology breaks twice (2014, 2023); modelled series at least has one definition",
    ),
    (
        "fx", "covariate", "DAG node 'fx' — Design B (NGN/USD)",
        "PA.NUS.FCRF", "Official exchange rate (LCU per US$, period average)",
        "keyless annual; the monthly series still needs CBN",
    ),
    (
        "donor", "covariate", "DAG node 'donor' — Designs A and B (donor funding)",
        "DT.ODA.ALLD.CD", "Net official development assistance received (current US$)",
        "no source identified at all; the graph assumes it into the adjustment set for health/education",
    ),
    (
        "oil_rents", "covariate", "DAG node 'common' — Design C donor screening (oil channel)",
        "NY.GDP.PETR.RT.ZS", "Oil rents (% of GDP)",
        "oil-channel proxy; the price itself is probed separately below",
    ),
]

# ------------------------------------------------------------------------------------------
# 3. the synthetic-control donor pool
# ------------------------------------------------------------------------------------------
DONORS = {
    "GH": "Ghana", "SN": "Senegal", "CI": "Cote d'Ivoire", "KE": "Kenya", "TZ": "Tanzania",
    "ZA": "South Africa", "AO": "Angola", "DZ": "Algeria", "GA": "Gabon", "EC": "Ecuador",
    "ID": "Indonesia", "CO": "Colombia", "VE": "Venezuela",
}
# The predictor set the donor pool is screened on (design spec section 5.3).
DONOR_PREDICTORS = [
    ("gdp_growth", "NY.GDP.MKTP.KD.ZG", "GDP growth (annual %)"),
    ("cpi_yoy", "FP.CPI.TOTL.ZG", "Inflation, consumer prices (annual %)"),
    ("oil_rents", "NY.GDP.PETR.RT.ZS", "Oil rents (% of GDP)"),
    ("population", "SP.POP.TOTL", "Population, total"),
    ("u5mr", "SH.DYN.MORT", "Under-5 mortality rate"),
]


def profile(rows: list[dict]) -> tuple[int, int | None, int | None]:
    years = sorted(int(r["date"]) for r in rows if r.get("value") is not None)
    if not years:
        return 0, None, None
    return len(years), years[0], years[-1]


def country_of(row: dict) -> str:
    """The API returns a 2-letter id under ``country`` and a 3-letter code under
    ``countryiso3code`` (Ghana -> GH / GHA). The 2-letter form is what the donor list uses."""
    return (((row.get("country") or {}).get("id"))
            or row.get("countryiso3code") or "").upper()


def verdict(n: int, first: int | None, last: int | None, gate: int = APC_FLOOR) -> str:
    """Reaching the window is necessary but not sufficient — a survey series with nine points
    across thirty years is an interpolation problem, not an annual series, and is flagged."""
    if n == 0:
        return "EMPTY"
    if last is not None and last < gate:
        return f"STOPS {last}"
    density = n / (last - first + 1) if first is not None and last is not None else 0.0
    if density < 0.5:
        return f"SPARSE ({n} obs / {last - first + 1}y)"
    return "covers study window"


def probe_nigeria() -> tuple[list[str], list[str]]:
    acquirable: list[str] = []
    blocked: list[str] = []
    print("MISSING VARIABLES — Nigeria")
    print(f"{'variable':<16}{'kind':<11}{'indicator':<18}{'n':>4}  {'span':<12}{'density':>8}  verdict")
    print("-" * 100)
    for variable, kind, _, indicator_id, name, _ in MISSING:
        try:
            _, rows = fetch_indicator(indicator_id, name, country="NG")
        except (WorldBankError, ValueError) as exc:
            print(f"{variable:<16}{kind:<11}{indicator_id:<18}{'--':>4}  {'--':<12}FETCH FAILED: {exc}")
            blocked.append(f"{variable} ({indicator_id})")
            continue
        n, first, last = profile(rows)
        v = verdict(n, first, last)
        span = f"{first}-{last}" if first is not None else "--"
        density = f"{n / (last - first + 1):.2f}" if first is not None and last is not None else "--"
        print(f"{variable:<16}{kind:<11}{indicator_id:<18}{n:>4}  {span:<12}{density:>8}  {v}")
        (acquirable if v == "covers study window" else blocked).append(f"{variable} ({indicator_id})")
    return acquirable, blocked


def probe_donor_pool() -> None:
    countries = ";".join(DONORS)
    n_pred = len(DONOR_PREDICTORS)
    print()
    print(f"DONOR POOL — {len(DONORS)} candidate countries x {n_pred} screening predictors")
    print(f"{'predictor':<14}{'indicator':<18}{'donors w/ data':>15}{'reaching 2015':>15}")
    print("-" * 92)
    present: dict[str, set[str]] = {c: set() for c in DONORS}
    covering: dict[str, set[str]] = {c: set() for c in DONORS}
    for label, indicator_id, name in DONOR_PREDICTORS:
        try:
            _, rows = fetch_indicator(indicator_id, name, country=countries)
        except (WorldBankError, ValueError) as exc:
            print(f"{label:<14}{indicator_id:<18}{'FETCH FAILED':>15}  {exc}")
            continue
        have, cover = set(), set()
        for row in rows:
            country = country_of(row)
            if row.get("value") is None or country not in DONORS:
                continue
            have.add(country)
            present[country].add(label)
            if int(row["date"]) >= APC_FLOOR:
                cover.add(country)
                covering[country].add(label)
        print(f"{label:<14}{indicator_id:<18}{len(have):>7}/{len(DONORS):<7}{len(cover):>7}/{len(DONORS):<7}")

    print()
    print(f"  {'donor':<16}{'predictors present':>19}{'reaching 2015':>15}   screenable")
    print("  " + "-" * 74)
    for code in sorted(DONORS):
        p, c = len(present[code]), len(covering[code])
        flag = "yes" if c == n_pred else ("partial" if p else "NO DATA")
        print(f"  {DONORS[code]:<16}{p:>10}/{n_pred:<8}{c:>10}/{n_pred:<5}   {flag}")


def probe_brent() -> None:
    """The oil covariate is specified as FRED ``DCOILBRENTEU`` — the DAG node ``oil``.

    As of 2026-10-11 a free API key is configured, so the *authenticated client* is the thing
    tested: it is the real acquisition path (``pull_fred.py``), not a substitute. The keyless
    endpoints are still probed when no key is present, because the finding they support — that no
    keyless route serves this series from here, so the key is a hard dependency (C-20) — is what
    justifies requiring a registration rather than working around it.
    """
    print()
    print("OIL PRICE — FRED DCOILBRENTEU, the DAG node 'oil' (designs A and B)")
    user_agent = {"User-Agent": "causal-presidents/0.1 (low-volume public-data access)"}

    try:
        get_api_key()
    except MissingCredential:
        print("  no key configured — falling back to the keyless-substitute test (C-20)")
    else:
        retrieval, observations = fetch_series("DCOILBRENTEU", "Crude Oil Prices: Brent - Europe")
        dated = sorted(o["date"] for o in observations if o.get("value") not in ("", ".", None))
        span = f"{dated[0]}..{dated[-1]}" if dated else "--"
        years = sorted({d[:4] for d in dated})
        last_year = int(years[-1]) if years else 0
        print(f"  authenticated client: HTTP {retrieval.http_status}, {len(dated)} obs with values, "
              f"span {span}, sha256 {retrieval.sha256[:12]}")
        print(f"  -> {'USABLE — reaches the study window and the 2023 subsidy window' if last_year >= 2023 else 'insufficient'}"
              f" (landed by ingestion/flows/pull_fred.py; daily, so Stage 4 freezes the resample rule)")
        return

    url = "https://fred.stlouisfed.org/graph/fredgraph.csv"
    for attempt in (1, 2):
        try:
            response = requests.get(url, params={"id": "DCOILBRENTEU"}, timeout=45,
                                    headers=user_agent)
            break
        except requests.RequestException as exc:
            response = None
            if attempt == 2:
                print(f"  fredgraph.csv: FETCH FAILED after 2 attempts ({exc})")
    if response is not None:
        if response.status_code != 200:
            print(f"  fredgraph.csv: HTTP {response.status_code} — key still required")
        else:
            lines = [ln for ln in response.text.splitlines() if ln.strip()]
            data = [ln for ln in lines[1:] if not ln.endswith(",.")]
            years = sorted({ln.split(",")[0][:4] for ln in data if ln.split(",")[0][:4].isdigit()})
            span = f"{years[0]}-{years[-1]}" if years else "--"
            print(f"  fredgraph.csv (Brent daily): HTTP 200, {len(data)} obs, span {span}"
                  f"  -> {'USABLE' if years and years[-1] >= str(APC_FLOOR) else 'insufficient'}")

    stooq = "https://stooq.com/q/d/l/"
    try:
        response = requests.get(stooq, params={"s": "cb.f", "i": "m"}, timeout=45,
                                headers=user_agent)
        if response.status_code == 200 and response.text.lower().startswith("date"):
            rows = [ln for ln in response.text.splitlines() if ln.strip()][1:]
            years = sorted({ln.split(",")[0][:4] for ln in rows if ln.split(",")[0][:4].isdigit()})
            span = f"{years[0]}-{years[-1]}" if years else "--"
            print(f"  stooq cb.f (Brent monthly): HTTP 200, {len(rows)} obs, span {span}"
                  f"  -> {'USABLE' if years and years[-1] >= str(APC_FLOOR) else 'insufficient'}")
        else:
            print(f"  stooq cb.f: HTTP {response.status_code} — not a CSV series")
    except requests.RequestException as exc:
        print(f"  stooq cb.f: FETCH FAILED ({exc})")


def main() -> int:
    load_env_file(REPO_ROOT)
    acquirable, blocked = probe_nigeria()
    probe_donor_pool()
    probe_brent()

    print()
    print("=" * 92)
    print("SUMMARY")
    print(f"  acquirable now, keyless, covering the study window: {len(acquirable)}")
    for item in acquirable:
        print(f"    + {item}")
    print(f"  still missing or gated: {len(blocked)}")
    for item in blocked:
        print(f"    - {item}")
    print()
    print("  known credential-gated (not probed here — see docs/decisions.md):")
    print("    - UCDP GED security fatalities  (free token, endpoint verified C-14)")
    print("    - ACLED incidents/fatalities    (OAuth app; 12-month embargo; no redistribution)")
    print("    - DHIS2 penta3 monthly          (Nigeria tenant access unverified)")
    print("    - FAAC / state IGR (D1, D2 dose) (NBS PDFs — needs a parser, no API)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
