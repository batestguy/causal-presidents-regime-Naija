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

One multi-country request per predictor **per chunk of the pool**, so a donor cannot be silently
half-landed: the row-count assertion in the client fires if pagination truncates, and the chunk's own
country list is checked back against the codes the request asked for. The chunking is not a preference:
a 99-country request returns an unparseable body (the API's limit is between 30 and 50 codes — measured,
not assumed), so the pool is landed in batches of ``CHUNK_SIZE`` and each batch is its own dataset.

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
# The API's multi-country limit is between 30 and 50 codes (a 50-code request returns a body that is not
# JSON at all, a 30-code request returns 1,980 rows). 20 leaves room under it and keeps each payload readable.
CHUNK_SIZE = 20

# The candidate pool, in four declared groups. Design spec section 5.3 named 13 West African neighbours
# and oil exporters, and Stage 5's pre-fit gate then failed every window against that pool: the best single
# donor beat the fitted simplex on every window (C-59), i.e. what failed was the *pool*, not the optimiser.
# A pool of 13 that was chosen on GDP comparability and geography cannot answer whether a wider, differently
# screened pool could track Nigeria, so the candidate set is widened here rather than re-screened from the
# same 13.
#
# What the widening is screened on, declared before the gate is re-run:
#
#   * **oil dependence** — the outcome paths of a rentier state move with the commodity cycle, which is the
#     confounder Design C exists to absorb (`oil_rents`, already in the predictor set);
#   * **region and income band** — Sub-Saharan comparators and lower-middle-income large countries, because
#     under-5 mortality and inflation paths cluster by those two things, not by GDP alone;
#   * **coverage** — a candidate has to reach 1999 (the pre-period floor) and 2024 (the last treated
#     window); the flow measures that per country and the gate drops what fails, rather than it being
#     assumed at selection time.
#
# None of these groups decides the pool. They are the candidate set the gate screens on pre-treatment fit,
# and every group is published with the vintage so a later reader can see what was offered and what was used.
DONOR_GROUPS = {
    "neighbour_west_africa": ["GH", "SN", "CI", "ML", "BF", "NE", "BJ", "TG", "GN", "SL", "LR", "GM",
                              "CV"],
    "oil_exporter": ["AO", "DZ", "GA", "EC", "ID", "CO", "VE", "CG", "GQ", "CM", "NG", "TT", "GY", "KZ",
                     "AZ", "IQ", "SA", "AE", "KW", "OM", "QA", "IR", "LY", "BN", "MY", "PE", "MX",
                     "BR", "BD", "MN"],
    "africa_comparator": ["KE", "TZ", "ZA", "ET", "UG", "ZM", "ZW", "MZ", "MW", "CD", "RW", "SD",
                           "SS", "SO", "NA", "BW", "MG", "EG", "MA", "TN", "DJ", "ER", "LS", "SZ",
                           "BI", "CF", "TD", "MR"],
    "lower_middle_income_large": ["PK", "VN", "PH", "TH", "IN", "LK", "ID", "EG", "MA", "BO", "HN",
                                  "GT", "NI", "SV", "PY", "DO", "JM", "TR", "RO", "UA", "UZ", "KG",
                                  "TJ", "MN", "PG", "TL", "NP", "KH", "LA", "MM", "BD", "YE", "JO",
                                  "SY", "ZA"],
}
# Nigeria is the treated unit and can never be its own donor; it is named here so the exclusion is explicit
# rather than an omission a reader has to notice.
TREATED_UNIT = "NG"

# The pool actually requested: the union of the groups, minus the treated unit. The groups overlap on
# purpose (South Africa is both an African comparator and a large lower-middle-income country), so the union
# is deduplicated here and the group tags stay as the declared *reason* a country is a candidate.
DONORS = {code: code for code in sorted({code for group in DONOR_GROUPS.values() for code in group})
          if code != TREATED_UNIT}
DONOR_NAMES = {
    "GH": "Ghana", "SN": "Senegal", "CI": "Cote d'Ivoire", "KE": "Kenya", "TZ": "Tanzania",
    "ZA": "South Africa", "AO": "Angola", "DZ": "Algeria", "GA": "Gabon", "EC": "Ecuador",
    "ID": "Indonesia", "CO": "Colombia", "VE": "Venezuela", "ML": "Mali", "BF": "Burkina Faso",
    "NE": "Niger", "BJ": "Benin", "TG": "Togo", "GN": "Guinea", "SL": "Sierra Leone",
    "LR": "Liberia", "GM": "Gambia, The", "CV": "Cabo Verde", "CG": "Congo, Rep.", "GQ": "Equatorial Guinea",
    "CM": "Cameroon", "TT": "Trinidad and Tobago", "GY": "Guyana", "KZ": "Kazakhstan", "AZ": "Azerbaijan",
    "IQ": "Iraq", "SA": "Saudi Arabia", "AE": "United Arab Emirates", "KW": "Kuwait", "OM": "Oman",
    "QA": "Qatar", "IR": "Iran, Islamic Rep.", "LY": "Libya", "BN": "Brunei Darussalam",
    "MY": "Malaysia", "PE": "Peru", "MX": "Mexico", "BR": "Brazil", "BD": "Bangladesh",
    "MN": "Mongolia", "ET": "Ethiopia", "UG": "Uganda", "ZM": "Zambia", "ZW": "Zimbabwe",
    "MZ": "Mozambique", "MW": "Malawi", "CD": "Congo, Dem. Rep.", "RW": "Rwanda", "SD": "Sudan",
    "SS": "South Sudan", "SO": "Somalia", "NA": "Namibia", "BW": "Botswana", "MG": "Madagascar",
    "EG": "Egypt, Arab Rep.", "MA": "Morocco", "TN": "Tunisia", "DJ": "Djibouti", "ER": "Eritrea",
    "LS": "Lesotho", "SZ": "Eswatini", "BI": "Burundi", "CF": "Central African Republic",
    "TD": "Chad", "MR": "Mauritania", "PK": "Pakistan", "VN": "Viet Nam", "PH": "Philippines",
    "TH": "Thailand", "IN": "India", "LK": "Sri Lanka", "BO": "Bolivia", "HN": "Honduras",
    "GT": "Guatemala", "NI": "Nicaragua", "SV": "El Salvador", "PY": "Paraguay",
    "DO": "Dominican Republic", "JM": "Jamaica", "TR": "Turkiye", "RO": "Romania", "UA": "Ukraine",
    "UZ": "Uzbekistan", "KG": "Kyrgyz Republic", "TJ": "Tajikistan", "PG": "Papua New Guinea",
    "TL": "Timor-Leste", "NP": "Nepal", "KH": "Cambodia", "LA": "Lao PDR", "MM": "Myanmar",
    "YE": "Yemen, Rep.", "JO": "Jordan", "SY": "Syrian Arab Republic",
}
# Every requested code must have a declared name, or a reader of the coverage report meets a bare ISO code —
# the same auditability rule the donor panel's country-name column carries in the base.
MISSING_NAMES = sorted(set(DONORS) - set(DONOR_NAMES))

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
        bucket["name"] = DONOR_NAMES[country]
        bucket["groups"] = sorted(g for g, codes in DONOR_GROUPS.items() if country in codes
                                  and country != TREATED_UNIT)
    return out


def fetch_codes(indicator_id: str, name: str, codes: list[str], depth: int = 0) -> list[dict]:
    """One request for ``codes``, split in half and retried when the API's WAF refuses the combination.

    A content-based WAF rule sits in front of the API and returns an HTML block page (403, "Request Blocked
    by WAF") for some *combinations* of otherwise-fine country codes: ``LK;LR`` returns 200 and
    ``LK;LR;LS`` returns 403 every time, while ``LS`` alone returns 200. The block is deterministic and
    keyed on the URL, not on load, so retrying the same request cannot help; splitting it can.

    The split is recorded rather than hidden: each returned piece carries the countries it asked for and the
    depth it was split at, so the manifest shows which part of the pool needed a narrower request (and a
    reader can tell a WAF block from an empty series). Raises the last error when a single country cannot be
    fetched.
    """
    try:
        retrieval, rows = fetch_indicator(indicator_id, name, country=";".join(codes))
        return [{"codes": codes, "retrieval": retrieval, "rows": rows, "split_depth": depth}]
    except (WorldBankError, ValueError):
        if len(codes) == 1:
            raise
        middle = len(codes) // 2
        pieces = []
        for part in (codes[:middle], codes[middle:]):
            pieces.extend(fetch_codes(indicator_id, name, part, depth + 1))
        return pieces


def main() -> int:
    vintage = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    vintage_dir = RAW_ROOT / vintage
    vintage_dir.mkdir(parents=True, exist_ok=True)
    entries = []
    coverage: dict[str, dict] = {}
    failures = []

    if MISSING_NAMES:
        print(f"FAIL: {len(MISSING_NAMES)} requested code(s) have no declared name: {MISSING_NAMES}")
        return 1

    print(f"vintage: {vintage}")
    print(f"landing: {vintage_dir.relative_to(REPO_ROOT)}")
    print(f"donors:  {len(DONORS)}  predictors: {len(PREDICTORS)}  chunk size: {CHUNK_SIZE}")
    for group, codes in DONOR_GROUPS.items():
        print(f"  group {group:<26} {len([c for c in codes if c != TREATED_UNIT]):>3} candidate(s)")
    print(f"  treated unit {TREATED_UNIT} excluded from the pool")
    print()

    for label, indicator_id, name in PREDICTORS:
        per_country: dict[str, dict] = {}
        rows_seen = 0
        chunks = [codes for codes in (list(DONORS)[i:i + CHUNK_SIZE]
                                      for i in range(0, len(DONORS), CHUNK_SIZE)) if codes]
        for index, codes in enumerate(chunks, start=1):
            try:
                pieces = fetch_codes(indicator_id, name, codes)
            except (WorldBankError, ValueError) as exc:
                failures.append({"metric_id": label, "indicator_id": indicator_id,
                                 "dataset_id": f"{indicator_id}-p{index:02d}", "countries": codes,
                                 "error": str(exc)})
                print(f"  FAIL {label:<14} chunk {index}/{len(chunks)}: {exc}")
                continue

            for sub, piece in enumerate(pieces, start=1):
                part, retrieval, rows = piece["codes"], piece["retrieval"], piece["rows"]
                dataset_id = f"{indicator_id}-p{index:02d}" if len(pieces) == 1 else \
                    f"{indicator_id}-p{index:02d}s{sub:02d}"
                # A donor cannot be silently half-landed: the request named these codes, so the payload has
                # to name them back (a country whose series is entirely empty would otherwise vanish).
                returned = set(_per_country(rows))
                absent = sorted(set(part) - returned)
                page_files = write_pages(vintage_dir / dataset_id, retrieval.payloads, REPO_ROOT)
                # `dataset_id` must be passed explicitly: the client derives its own from the indicator id,
                # and the analytical base joins payload files to manifest entries on
                # (source, vintage, dataset_id) read from the path. Leaving the client's value in place
                # wrote 40 retrieval records all named `NY.GDP.PETR.RT.ZS` while the directories were named
                # `NY.GDP.PETR.RT.ZS-p01…`, so the donor panel silently became zero rows — a join that
                # matches nothing is worse than an error, and this is the check that catches it.
                entry = retrieval.manifest_entry(
                    metric_id=label,
                    dataset_id=dataset_id,
                    dataset_name=f"{name} — donor pool chunk {index}/{len(chunks)} ({len(part)} countries)",
                    note=(f"donor-panel predictor for synthetic-control screening, pool chunk "
                          f"{index}/{len(chunks)} ({len(part)} of {len(codes)} countries in this request; "
                          f"split depth {piece['split_depth']})"),
                    page_files=page_files,
                    n_countries=len(part),
                )
                mismatched = sorted({path.split("/")[-2] for path in page_files} - {dataset_id})
                if mismatched:
                    failures.append({"metric_id": label, "dataset_id": dataset_id,
                                     "error": f"page files land in {mismatched}, not in the manifest's "
                                              f"dataset_id"})
                    print(f"  FAIL {label:<14} {dataset_id:<24} page files land in {mismatched}")
                    continue
                entries.append(entry)
                rows_seen += len(rows)
                for code, bucket in _per_country(rows).items():
                    merged = per_country.setdefault(code, {"n": 0, "years": [], "name": bucket["name"],
                                                           "groups": bucket["groups"]})
                    merged["n"] += bucket["n"]
                    merged["years"].extend(range(bucket["first_year"], bucket["last_year"] + 1))
                if piece["split_depth"]:
                    print(f"  note {label:<14} {dataset_id:<24} {len(part)} country(ies) landed after "
                          f"{piece['split_depth']} WAF split(s)")
                if absent:
                    print(f"  note {label:<14} {dataset_id:<24} {len(absent)} code(s) with no data at all: "
                          f"{', '.join(absent)}")

        for bucket in per_country.values():
            span = sorted(set(bucket.pop("years")))
            bucket["first_year"], bucket["last_year"] = span[0], span[-1]
            bucket["reaches_1999"] = span[0] <= STUDY_FLOOR
            bucket["reaches_2015"] = span[-1] >= APC_FLOOR
        if not per_country:
            continue
        coverage[label] = {
            "indicator_id": indicator_id,
            "indicator_name": name,
            "n_donors_with_data": len(per_country),
            "n_donors_reaching_2015": sum(v["reaches_2015"] for v in per_country.values()),
            "countries": per_country,
        }
        print(f"  ok   {label:<14} {indicator_id:<18} chunks={len(chunks)} rows={rows_seen} "
              f"donors={len(per_country)}/{len(DONORS)} "
              f"reaching_2015={coverage[label]['n_donors_reaching_2015']}/{len(DONORS)}")

    write_manifest(
        vintage_dir=vintage_dir,
        vintage_date=vintage,
        source="worldbank_donors",
        entries=entries,
        failures=failures,
        extra={
            "n_indicators_requested": len(PREDICTORS),
            "donors": DONORS,
            "donor_names": {code: DONOR_NAMES[code] for code in DONORS},
            "donor_groups": DONOR_GROUPS,
            "treated_unit": TREATED_UNIT,
            "n_donors": len(DONORS),
        },
    )
    (vintage_dir / "coverage.json").write_text(
        json.dumps(
            {
                "vintage_date": vintage,
                "purpose": "synthetic-control donor screening (Design C)",
                "donors": DONORS,
                "donor_names": {code: DONOR_NAMES[code] for code in DONORS},
                "donor_groups": DONOR_GROUPS,
                "treated_unit": TREATED_UNIT,
                "screen_axes": ["oil dependence (oil rents, % of GDP)",
                                "region and income band (Sub-Saharan / lower-middle-income)",
                                "coverage of the 1999 pre-period floor and the last treated window"],
                "predictors": coverage,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    landed = sorted({entry["metric_id"] for entry in entries})
    print()
    print(f"succeeded: {len(landed)}/{len(PREDICTORS)} predictor(s) in {len(entries)} request(s)"
          f"   failures: {len(failures)}")
    if failures:
        print("counts as an incomplete vintage — see manifest.failures")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
