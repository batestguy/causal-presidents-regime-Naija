"""Stage 2 ingestion flow: land an NBS CPI and Inflation Report workbook.

Writes, per vintage:

    data/raw/nbs_cpi/<vintage>/nbs-cpi-<period>/page-0001.xlsx   bytes as received
    data/raw/nbs_cpi/<vintage>/manifest.json                     provenance
    data/raw/nbs_cpi/<vintage>/coverage.json                     what the workbook covers, before any parsing

**Why one workbook and not ninety.** A monthly report's Table 1 is the composite index from 1995-01 to the
report's own month, so the newest report is the whole series and its vintage is its month. That is what makes
this acquisition cheap enough to be worth doing at all — and it is also why the series can only be as current as
the latest report, which the elibrary currently stops at 2024-10.

Nothing is transformed here. The workbook lands whole; the parse happens in
``ingestion/parsers/nbs_cpi.py``, which records the sha256 of the file it read.

Run::

    conda run -p "C:/Users/TOSHIBA/ds-general" python ingestion/flows/pull_nbs_cpi.py
    conda run -p "C:/Users/TOSHIBA/ds-general" python ingestion/flows/pull_nbs_cpi.py --period 2024-03
    conda run -p "C:/Users/TOSHIBA/ds-general" python ingestion/flows/pull_nbs_cpi.py --vintage 2026-10-29
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from ingestion.clients.nbs_cpi import (  # noqa: E402
    ATTRIBUTION,
    LATEST_PERIOD,
    NOTE,
    NbsCpiError,
    discover,
    fetch_workbook,
    resolve_workbook,
)
from ingestion.clients.provenance import (  # noqa: E402
    VintageExists,
    prepare_vintage,
    write_blobs,
    write_manifest,
)

RAW_ROOT = REPO_ROOT / "data" / "raw" / "nbs_cpi"
METRICS = ["cpi_index", "cpi_12m_avg", "cpi_mom_pct", "cpi_yoy_pct"]


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Land an NBS CPI and Inflation Report workbook.")
    parser.add_argument(
        "--vintage", default=None,
        help="vintage label (default: today's UTC date). A correction must use a new label — the raw layer is "
             "immutable (X-07).",
    )
    parser.add_argument("--period", default=LATEST_PERIOD,
                        help=f"report month, YYYY-MM (default: {LATEST_PERIOD})")
    return parser.parse_args(argv)


def workbook_coverage(payload: bytes, sheet: str = "Table1") -> dict:
    """What the workbook says about its own coverage, read without writing anything.

    This is a coverage reading, not the parse: the manifest should be able to state the span the bytes carry
    without a second copy of the parser's month logic. The authoritative figures are
    ``data/staging/nbs_cpi_parse_report.json``.
    """
    import io

    import pandas as pd

    frame = pd.read_excel(io.BytesIO(payload), sheet_name=sheet, header=None)
    months = [str(frame.iat[i, 1]).strip()[:3] for i in range(frame.shape[0])]
    return {
        "sheet": sheet,
        "n_rows": int(frame.shape[0]),
        "n_month_rows": sum(1 for m in months if m in
                            ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")),
        "title_rows": [str(frame.iat[0, 0]).strip(), str(frame.iat[1, 0]).strip()],
        "note": ("Read from the landed bytes at ingest time. The authoritative month span is written by "
                 "ingestion/parsers/nbs_cpi.py to data/staging/nbs_cpi_parse_report.json."),
    }


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv if argv is not None else sys.argv[1:])
    vintage = args.vintage or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    vintage_dir = RAW_ROOT / vintage

    session = requests.Session()
    print(f"discovering the NBS CPI report for {args.period}")
    try:
        report = discover(args.period, session)
        workbook = resolve_workbook(report, session)
        print(f"  report {report['report_id']}: {report['title']}")
        print(f"  workbook {workbook['url']}")
        retrieval, payload = fetch_workbook(report, workbook, session)
    except (NbsCpiError, requests.RequestException) as exc:
        print(f"REFUSED  {exc}")
        return 1

    print(f"  {len(payload) / 1024:.0f} KB  sha256={retrieval.sha256[:12]}")

    try:
        prepare_vintage(vintage_dir, "nbs_cpi")
    except VintageExists as exc:
        print(f"REFUSED  {exc}")
        return 1

    coverage = workbook_coverage(payload)
    if coverage["n_month_rows"] == 0:
        print("REFUSED  the workbook carries no month rows in Table 1 — writing nothing rather than an empty "
              "vintage")
        return 1

    page_files = write_blobs(
        vintage_dir / retrieval.dataset_id, [("page-0001" + workbook["suffix"], payload)], REPO_ROOT
    )

    print()
    print(f"vintage:  {vintage}")
    print(f"landing:  {vintage_dir.relative_to(REPO_ROOT)}")
    print(f"coverage: {coverage['n_month_rows']} month rows in {coverage['sheet']}; "
          f"{coverage['title_rows'][0][:70]}")

    entry = retrieval.manifest_entry(
        page_files=page_files,
        metric_id="cpi_index",
        metrics=METRICS,
        licence="public-document",
        attribution=ATTRIBUTION,
        note=NOTE,
        n_month_rows=coverage["n_month_rows"],
    )
    entry["row_count"] = coverage["n_rows"]

    (vintage_dir / "coverage.json").write_text(
        json.dumps({"vintage_date": vintage, "period": args.period, **coverage}, indent=2), encoding="utf-8"
    )
    write_manifest(
        vintage_dir=vintage_dir,
        vintage_date=vintage,
        source="nbs_cpi",
        entries=[entry],
        failures=[],
        extra={
            "licence": "public-document",
            "attribution": ATTRIBUTION,
            "note": NOTE,
            "archive_version": args.period,
        },
    )

    print(f"manifest: {(vintage_dir / 'manifest.json').relative_to(REPO_ROOT)}")
    print(f"coverage: {(vintage_dir / 'coverage.json').relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
