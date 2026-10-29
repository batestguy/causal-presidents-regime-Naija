"""Parse an NBS CPI workbook into a monthly series — the whole history from one document.

**The months are derived, and the publisher's year labels are used as the check.** Column A carries the year,
but only on some rows: the 2024-10 workbook labels 1995 through 2023 and then leaves January–October 2024
unlabelled, and one year block carries its year twice. A state machine over that column is wrong in both
directions — forward-filling turns 2024-10 into 2023-10, and treating every year cell as a reset double-counts
the duplicated one. So the periods are walked **backwards from the report's own month**, which the title states,
and every year cell that *is* present is compared against the derivation. A disagreement fails the parse.

That is the same contract the rest of this repository uses for a published table: derive the thing, then check
it against the publisher's own labels rather than trusting either alone.

Run::

    conda run -p "C:/Users/TOSHIBA/ds-general" python ingestion/parsers/nbs_cpi.py
    conda run -p "C:/Users/TOSHIBA/ds-general" python ingestion/parsers/nbs_cpi.py --vintage 2026-10-29
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

RAW_ROOT = REPO_ROOT / "data" / "raw" / "nbs_cpi"
STAGING = REPO_ROOT / "data" / "staging"
OUT_CSV = STAGING / "nbs_cpi_monthly.csv"
OUT_REPORT = STAGING / "nbs_cpi_parse_report.json"

# Table 1, columns 2–5: the composite "All Items" measures, in the order NBS publishes them.
MEASURES = {
    "cpi_index": 2,
    "cpi_12m_avg": 3,
    "cpi_mom_pct": 4,
    "cpi_yoy_pct": 5,
}
EXPECTED_HEADERS = ["Monthly", "12-Month Average", "Month-on change (%)", "Year-on change (%)"]
UNITS = {
    "cpi_index": "index, November 2009 = 100",
    "cpi_12m_avg": "index, November 2009 = 100",
    "cpi_mom_pct": "% change on the previous month",
    "cpi_yoy_pct": "% change on the same month a year earlier",
}
ITEM_LABELS = {
    "cpi_index": "All Items, monthly index",
    "cpi_12m_avg": "All Items, 12-month average index",
    "cpi_mom_pct": "All Items, month-on-month change",
    "cpi_yoy_pct": "All Items, year-on-year change",
}
MONTHS = {
    m: i for i, m in enumerate(
        ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], start=1)
}


def latest_archive() -> tuple[Path, str, Path]:
    vintages = sorted(
        (p for p in RAW_ROOT.iterdir() if p.is_dir() and (p / "manifest.json").exists()),
        key=lambda p: p.name,
    )
    if not vintages:
        raise SystemExit(f"no landed NBS CPI vintage under {RAW_ROOT.relative_to(REPO_ROOT)}")
    vintage_dir = vintages[-1]
    archives = sorted(vintage_dir.glob("nbs-cpi-*/page-0001.*"))
    if not archives:
        raise SystemExit(f"no workbook in {vintage_dir.relative_to(REPO_ROOT)}")
    return vintage_dir, vintage_dir.name, archives[-1]


def month_rows(frame: pd.DataFrame) -> list[tuple[int, int, object]]:
    """Every row of Table 1 whose column B is a month name: ``(row index, month number, year cell)``."""
    rows = []
    for i in range(frame.shape[0]):
        name = str(frame.iat[i, 1]).strip()[:3].title()
        if name in MONTHS:
            rows.append((i, MONTHS[name], frame.iat[i, 0]))
    return rows


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Parse an NBS CPI workbook into a monthly series.")
    ap.add_argument("--vintage", default=None, help="vintage to parse (default: the latest landed)")
    ap.add_argument("--anchor", default=None,
                    help="the report's own month, YYYY-MM (default: read from the manifest's archive_version)")
    args = ap.parse_args(argv if argv is not None else sys.argv[1:])

    if args.vintage:
        vintage_dir, vintage = RAW_ROOT / args.vintage, args.vintage
        archive_path = sorted(vintage_dir.glob("nbs-cpi-*/page-0001.*"))[-1]
    else:
        vintage_dir, vintage, archive_path = latest_archive()

    manifest = json.loads((vintage_dir / "manifest.json").read_text(encoding="utf-8"))
    # The flow records the report's month as `archive_version`; the retrieval's dataset id carries it too, but
    # one place is enough and the flow's field is the one that names the release.
    period = args.anchor or manifest.get("archive_version") \
        or manifest["retrievals"][0]["dataset_id"].replace("nbs-cpi-", "")
    if not (len(period) == 7 and period[4] == "-" and period[5:].isdigit()):
        raise SystemExit(f"cannot read a YYYY-MM period from {period!r}")

    payload = archive_path.read_bytes()
    sha256 = hashlib.sha256(payload).hexdigest()
    frame = pd.read_excel(archive_path, sheet_name="Table1", header=None)

    headers = [str(v).strip() for v in frame.iloc[3, 2:6].tolist()]
    if headers[:2] != EXPECTED_HEADERS[:2]:
        raise SystemExit(f"{archive_path.name}: Table 1's header reads {headers!r}, not the published "
                         f"{EXPECTED_HEADERS!r} — the layout changed and the column map must be re-read")

    rows = month_rows(frame)
    if not rows:
        raise SystemExit(f"{archive_path.name}: Table 1 carries no month rows")

    anchor_ordinal = int(period[:4]) * 12 + int(period[5:])
    derived = []
    for offset, (row_index, month, year_cell) in enumerate(rows):
        ordinal = anchor_ordinal - (len(rows) - 1 - offset)
        year, month_of = divmod(ordinal - 1, 12)
        derived.append({"period": f"{year:04d}-{month_of + 1:02d}", "row": row_index,
                        "year_cell": year_cell})

    if derived[-1]["period"] != period:
        raise SystemExit(f"the last month row derives {derived[-1]['period']}, but the report is {period}")

    checked, disagreements = 0, []
    for entry in derived:
        cell = entry["year_cell"]
        if isinstance(cell, (int, float)) and not pd.isna(cell) and 1990 <= int(cell) <= 2100:
            checked += 1
            if int(cell) != int(entry["period"][:4]):
                disagreements.append({"row": entry["row"], "year_cell": int(cell),
                                      "derived": entry["period"]})
    if disagreements:
        raise SystemExit(
            f"{archive_path.name}: {len(disagreements)} year label(s) disagree with the derivation, so the "
            f"sheet is not the contiguous run this parser assumes: {disagreements[:3]}"
        )

    periods = [entry["period"] for entry in derived]
    if len(set(periods)) != len(periods):
        raise SystemExit(f"{archive_path.name}: the derivation produced a duplicate month")

    long_rows = []
    absent = {measure: 0 for measure in MEASURES}
    for entry in derived:
        for measure, column in MEASURES.items():
            value = frame.iat[entry["row"], column]
            if pd.isna(value):
                # A month the publisher did not print is **absent**, not a row with an empty value: the
                # coverage gate reads absence as an observation that is not there, which is what it is.
                absent[measure] += 1
                continue
            long_rows.append({
                "period_month": entry["period"],
                "scope": "national",
                "item": measure,
                "label": ITEM_LABELS[measure],
                "value": float(value),
                "unit": UNITS[measure],
                "source_dataset_id": archive_path.parent.name,
                "source_file": archive_path.relative_to(REPO_ROOT).as_posix(),
                "source_sha256": sha256,
                "source_location": f"Table1!row{entry['row'] + 1}",
                "vintage": vintage,
            })

    STAGING.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(long_rows[0]))
        writer.writeheader()
        writer.writerows(long_rows)

    first_last = {}
    for measure in MEASURES:
        rows_of = [r["period_month"] for r in long_rows if r["item"] == measure]
        first_last[measure] = (rows_of[0] if rows_of else None, rows_of[-1] if rows_of else None)
    report = {
        "vintage": vintage,
        "source_file": archive_path.relative_to(REPO_ROOT).as_posix(),
        "source_sha256": sha256,
        "sheet": "Table1",
        "reported_period": period,
        "first_month": periods[0],
        "last_month": periods[-1],
        "n_months": len(periods),
        "n_value_rows": len(long_rows),
        "year_labels_checked": checked,
        "year_label_disagreements": len(disagreements),
        "measures": {
            measure: {
                "label": ITEM_LABELS[measure],
                "unit": UNITS[measure],
                "n_present": sum(1 for r in long_rows if r["item"] == measure),
                "n_absent": absent[measure],
                "first": first_last[measure][0],
                "last": first_last[measure][1],
            } for measure in MEASURES
        },
        "assumptions": {
            "month_assignment": (
                "periods are walked backwards from the report's own month, which the title states; the "
                "publisher's year cells are compared against that derivation and a disagreement fails the parse"
            ),
            "why_not_the_year_column": (
                "column A labels 1995-2023 and then stops, leaving 2024 unlabelled, and one year block carries "
                "its year twice — forward-filling it turns the last ten months into 2023"
            ),
            "base": (
                "the workbook states its base on its first rows (Base November 2009 = 100 for the current series); "
                "the series ends before the January-2025 rebasing that C-27 records, so it contains no "
                "definition break of its own"
            ),
            "coverage": (
                "the source's monthly CPI listing ends at this report (2024-10); months after it are absent from "
                "the publisher, not missing from this parse"
            ),
        },
    }
    OUT_REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"vintage: {vintage}  sha256={sha256[:12]}")
    print(f"report:  {period}  sheet Table1  {len(periods)} months  {periods[0]} -> {periods[-1]}")
    print(f"years:   {checked} label(s) checked against the derivation, {len(disagreements)} disagreements")
    print(f"rows:    {len(long_rows):,}  ({', '.join(MEASURES)})")
    for measure in MEASURES:
        info = report["measures"][measure]
        print(f"  {measure:<14} present={info['n_present']:>3}  {info['first']} -> {info['last']}")
    print(f"staging: {OUT_CSV.relative_to(REPO_ROOT)}")
    print(f"report:  {OUT_REPORT.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
