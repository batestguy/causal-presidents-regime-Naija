"""Verify the NBS CPI acquisition without importing the code that produced it.

The claim being checked is not "the parser ran" but "the series in `data/staging` is the one in the workbook the
publisher served". So this file re-reads the landed bytes, re-derives the months **its own way**, and compares
row for row. It also holds the two things a parse can silently get wrong:

* **The month labels.** The workbook's year column stops before the report's own year, so a forward fill turns
  the last ten months into the previous year. This re-derivation walks backwards from the report's month and
  compares every year cell that exists against the result — the same cross-check, written separately.
* **The block.** Table 1 carries three column blocks (All Items, Food, All items less farm produce and energy).
  Reading the wrong block would produce a plausible series of the wrong thing, so six months are compared against
  the headline inflation the NBS published.

What it does not do: it does not judge whether the published headline is right, only that this repository
reproduces it from the bytes it landed.

Run::

    python tests/verify_nbs_cpi.py
    python tests/verify_nbs_cpi.py --vintage 2026-10-29
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
# The release is landed but **not adopted**: no gate entry and no base table read it yet, and a vintage under
# `data/raw/` is a claim that it has been gated (C-79). So it sits in `data/pending/`, and this verifier looks
# there too — an acquisition that cannot be checked until it is adopted would be worth much less.
RAW_ROOTS = (REPO_ROOT / "data" / "raw" / "nbs_cpi", REPO_ROOT / "data" / "pending" / "nbs_cpi")
STAGING = REPO_ROOT / "data" / "staging"

MONTH_NAMES = {
    "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
    "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12,
}
# column index in Table 1 of each published "All Items" measure
COLUMN_OF = {"cpi_index": 2, "cpi_12m_avg": 3, "cpi_mom_pct": 4, "cpi_yoy_pct": 5}

# Headline year-on-year inflation as the NBS published it, to two decimals. If a parse ever reads the wrong
# column block these are the numbers that stop it: Food and core both sit plausibly close to All Items.
PUBLISHED_HEADLINE = {
    "2023-05": 22.41, "2023-06": 22.79, "2023-12": 28.92,
    "2024-01": 29.90, "2024-06": 34.19, "2024-10": 33.88,
}


def fail(failures: list[str], message: str) -> None:
    failures.append(message)


def latest_vintage() -> Path | None:
    """The newest vintage under either root, or None when nothing is landed anywhere.

    A parked source is not on CI (the weekly runner acquires only adopted sources), so absence is a
    normal state, not a failure: the caller prints a SKIPPED notice and moves on rather than turning
    the chain red over a vintage that was deliberately never adopted (C-81).
    """
    roots = [root for root in RAW_ROOTS if root.exists()]
    if not roots:
        return None
    vintages = sorted(
        (p for root in roots for p in root.iterdir() if p.is_dir() and (p / "manifest.json").exists()),
        key=lambda p: p.name,
    )
    return vintages[-1] if vintages else None


def rederive(workbook: Path, reported_period: str) -> tuple[dict[str, int], int, int]:
    """Month rows, walked backwards from the report's month; plus how many year labels were checked."""
    frame = pd.read_excel(workbook, sheet_name="Table1", header=None)
    rows = [(i, MONTH_NAMES[str(frame.iat[i, 1]).strip()[:3]])
            for i in range(frame.shape[0])
            if str(frame.iat[i, 1]).strip()[:3] in MONTH_NAMES]
    anchor = int(reported_period[:4]) * 12 + int(reported_period[5:])
    out: dict[str, int] = {}
    checked = disagreements = 0
    for offset, (row_index, _month) in enumerate(rows):
        ordinal = anchor - (len(rows) - 1 - offset)
        year, month_index = divmod(ordinal - 1, 12)
        label = f"{year:04d}-{month_index + 1:02d}"
        out[label] = row_index
        cell = frame.iat[row_index, 0]
        if isinstance(cell, (int, float)) and not pd.isna(cell) and 1990 <= int(cell) <= 2100:
            checked += 1
            if int(cell) != year:
                disagreements += 1
    return out, checked, disagreements


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Verify the NBS CPI acquisition against its landed bytes.")
    ap.add_argument("--vintage", default=None)
    args = ap.parse_args(argv if argv is not None else sys.argv[1:])

    failures: list[str] = []
    if args.vintage:
        candidates = [root / args.vintage for root in RAW_ROOTS if (root / args.vintage).is_dir()]
        if not candidates:
            print(f"FAILED — no vintage {args.vintage} under data/raw/nbs_cpi or data/pending/nbs_cpi")
            return 1
        vintage_dir = candidates[0]
    else:
        vintage_dir = latest_vintage()
        if vintage_dir is None:
            print("SKIPPED — no NBS CPI vintage landed under data/raw (adopted) or data/pending (parked): "
                  "the acquisition has nothing to check here, and the parked release is deliberate (C-81)")
            return 0
        print(f"note: the vintage is parked under {vintage_dir.relative_to(REPO_ROOT).as_posix()} "
              f"(not adopted: C-81); the verification still runs in full against the parked bytes")
    vintage = vintage_dir.name
    manifest = json.loads((vintage_dir / "manifest.json").read_text(encoding="utf-8"))
    retrieval = manifest["retrievals"][0]
    period = manifest.get("archive_version") or retrieval["dataset_id"].replace("nbs-cpi-", "")

    # ---- the payload is the one the manifest recorded ----------------------------------------------------
    worksheets = sorted(vintage_dir.glob("nbs-cpi-*/page-0001.*"))
    if not worksheets:
        print("FAILED — no workbook in the vintage")
        return 1
    payload = worksheets[0].read_bytes()
    digest = hashlib.sha256(payload).hexdigest()
    if digest != retrieval["sha256"]:
        fail(failures, f"the workbook hashes to {digest[:12]}, the manifest recorded "
                       f"{retrieval['sha256'][:12]}")
    if len(payload) != retrieval["payload_bytes"]:
        fail(failures, f"the workbook is {len(payload)} bytes, the manifest recorded {retrieval['payload_bytes']}")
    # The manifest records where the bytes were landed. A parked vintage has moved (C-79), so the recorded
    # prefix can be stale; what must hold is that the recorded file name is the workbook beside the manifest.
    recorded = [Path(p).name for p in retrieval["page_files"]]
    if recorded != [worksheets[0].name]:
        fail(failures, f"the manifest records page file {recorded}, the vintage holds {worksheets[0].name}")

    # ---- the months, re-derived --------------------------------------------------------------------------
    months, checked, disagreements = rederive(worksheets[0], period)
    if disagreements:
        fail(failures, f"{disagreements} year label(s) disagree with the backwards derivation")
    if checked == 0:
        fail(failures, "no year labels were available to cross-check the derivation against")
    if f"{period}" not in months:
        fail(failures, f"the derivation does not contain the report's own month {period}")

    # ---- staging matches the workbook, row for row -------------------------------------------------------
    staging_path = STAGING / "nbs_cpi_monthly.csv"
    if not staging_path.exists():
        print("FAILED — data/staging/nbs_cpi_monthly.csv is missing")
        return 1
    staged = list(csv.DictReader(staging_path.open(encoding="utf-8")))
    if not staged:
        fail(failures, "the staging artifact is empty")
    if {row["vintage"] for row in staged} != {vintage}:
        fail(failures, f"staging cites vintage(s) {sorted({row['vintage'] for row in staged})}, not {vintage}")
    frame = pd.read_excel(worksheets[0], sheet_name="Table1", header=None)
    seen: set[tuple[str, str]] = set()
    for row in staged:
        key = (row["period_month"], row["item"])
        if key in seen:
            fail(failures, f"{row['period_month']}/{row['item']} appears twice in staging")
        seen.add(key)
        if row["source_sha256"] != digest:
            fail(failures, f"{row['period_month']}/{row['item']} cites a different file hash")
            break
        if row["item"] not in COLUMN_OF:
            fail(failures, f"unexpected item {row['item']!r} in staging")
            continue
        row_index = months.get(row["period_month"])
        if row_index is None:
            fail(failures, f"{row['period_month']} is in staging but not in the derivation")
            continue
        expected = frame.iat[row_index, COLUMN_OF[row["item"]]]
        if row["value"] == "" and pd.isna(expected):
            continue
        if row["value"] == "" or pd.isna(expected):
            fail(failures, f"{row['period_month']}/{row['item']}: staging says {row['value']!r}, "
                           f"the workbook says {expected!r}")
            continue
        if abs(float(row["value"]) - float(expected)) > 1e-9:
            fail(failures, f"{row['period_month']}/{row['item']}: staging {row['value']} against "
                           f"the workbook's {expected}")

    staged_months = {row["period_month"] for row in staged}
    if staged_months != set(months):
        missing = sorted(set(months) - staged_months)[:4]
        extra = sorted(staged_months - set(months))[:4]
        fail(failures, f"staging covers {len(staged_months)} months against the workbook's {len(months)} "
                       f"(missing {missing}, extra {extra})")

    # ---- the block: six months against the published headline --------------------------------------------
    yoy = {row["period_month"]: float(row["value"]) for row in staged
           if row["item"] == "cpi_yoy_pct" and row["value"] != ""}
    for month, published in PUBLISHED_HEADLINE.items():
        got = yoy.get(month)
        if got is None:
            fail(failures, f"{month} has no year-on-year value to compare with the published {published}")
        elif abs(got - published) > 0.005:
            fail(failures, f"{month}: year-on-year reads {got:.2f}, the NBS published {published:.2f} — "
                           f"this is the check that catches the wrong column block")

    report = json.loads((STAGING / "nbs_cpi_parse_report.json").read_text(encoding="utf-8"))
    if report["source_sha256"] != digest:
        fail(failures, "the parse report cites a different file hash")
    if report["n_months"] != len(months):
        fail(failures, f"the parse report claims {report['n_months']} months, the derivation gives {len(months)}")
    if report["first_month"] != min(months) or report["last_month"] != max(months):
        fail(failures, "the parse report's span is not the derivation's span")

    if failures:
        print(f"FAILED — {len(failures)} problem(s):")
        for line in failures:
            print(f"  - {line}")
        return 1

    print(f"vintage       : {vintage}  ({worksheets[0].name})")
    print(f"sha256        : {digest[:12]}  ({len(payload):,} bytes, as recorded)")
    print(f"report        : {period}  ·  {len(months)} months  {min(months)} -> {max(months)}")
    print(f"year labels   : {checked} checked against the backwards derivation, {disagreements} disagreements")
    print(f"staging       : {len(staged):,} rows, every value reproduced from the workbook")
    print(f"headline      : {len(PUBLISHED_HEADLINE)} published months reproduced to 0.01 pp "
          f"({', '.join(sorted(PUBLISHED_HEADLINE))})")
    print("PASS — the series in staging is the one in the workbook the publisher served, on the right column block")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
