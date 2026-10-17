"""Stage 2 ingestion flow: land the FAAC monthly disbursement documents.

Writes, per vintage (``vintage_date`` = UTC date of the run unless ``--vintage`` is given)::

    data/raw/faac/<vintage>/oagf-<YYYY-MM>/page-0001.pdf    bytes as received (primary series)
    data/raw/faac/<vintage>/nbs-<YYYY-MM>/page-0001.xlsx    bytes as received (cross-check)
    data/raw/faac/<vintage>/manifest.json                   provenance for every retrieval
    data/raw/faac/<vintage>/coverage.json                   months present, months missing

This is the acquisition the Stage 1 exit criterion left open. OAGF is the primary publisher: the
monthly workbook originates in the Office of the Accountant General of the Federation, which is the
office the base spec section 5 names for the exposure metric D1. NBS republishes the same workbook as
XLSX, which is landed because an independent publication of the same numbers is the only thing that
can check the primary — two files, two domains, two formats, one document.

Three deliberate choices, each of which could reasonably have gone the other way:

1. **No transformation.** The payloads are PDF and XLSX and they land byte-for-byte. Parsing is a
   separate step (``ingestion/parsers/faac_disbursement.py``) that reads these files and records the
   ``sha256`` of whatever it read, so a month that is re-issued can never be silently re-parsed as if
   it were the month first landed.
2. **A document that is not the document type is a failure.** These hosts have been observed to answer
   200 with an HTML error page, so the magic bytes are checked (``%PDF``, ``PK`` for XLSX) and a
   mislabelled response is recorded as a failure rather than landed as a payload that would fail
   silently three stages later.
3. **One retry pass, at the end.** An 80-document crawl across two hosts will meet a transient error;
   a single second pass over the failures keeps the vintage complete without hiding a genuine absence,
   because a month that is really gone fails both passes. What survives both passes is a failure, and
   an incomplete vintage exits non-zero.

Nothing here decides the dose. Which column of the workbook is the exposure, and whether the series
reaches back far enough to be worth having, are recorded in ``analysis/specs/harmonisation.yml`` and
reported by the Stage 5 dose validation — not assumed at ingest time.

Run::

    conda run -p "C:/Users/TOSHIBA/ds-general" python ingestion/flows/pull_faac.py
    conda run -p "C:/Users/TOSHIBA/ds-general" python ingestion/flows/pull_faac.py --publishers oagf
    conda run -p "C:/Users/TOSHIBA/ds-general" python ingestion/flows/pull_faac.py --limit 3   # smoke
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

from ingestion.clients.faac import (  # noqa: E402
    FaacError,
    MonthlyDocument,
    build_retrieval,
    discover_nbs,
    discover_oagf,
    fetch_document,
    resolve_nbs_resource,
)
from ingestion.clients.provenance import (  # noqa: E402
    VintageExists,
    prepare_vintage,
    write_blobs,
    write_manifest,
)

RAW_ROOT = REPO_ROOT / "data" / "raw" / "faac"
# The metric every document in this flow belongs to: one series, per state, per month.
METRIC_ID = "faac_state_allocation"

MAGIC = {
    "oagf": (b"%PDF", ".pdf", "PDF"),
    "nbs": (b"PK", ".xlsx", "XLSX"),
}
NOTE = (
    "FAAC monthly disbursement workbook (Tables I-IV). Primary publisher: the Office of the "
    "Accountant General of the Federation, the office base spec section 5 names for exposure metric "
    "D1. The NBS payload is the republication of the same document, landed as the independent "
    "cross-check."
)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Land the FAAC monthly disbursement documents.")
    parser.add_argument(
        "--vintage",
        default=None,
        help="vintage label (default: today's UTC date). A correction must use a new label, "
             "because the raw layer is immutable (X-07).",
    )
    parser.add_argument(
        "--publishers",
        default="oagf,nbs",
        help="comma-separated subset of {oagf, nbs} (default: both)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="land only the first N months per publisher (smoke test; never used for a real vintage)",
    )
    return parser.parse_args(argv)


def look_like(document: MonthlyDocument, payload: bytes) -> str | None:
    """Return a reason the payload is not the document it claims to be, or ``None`` if it is."""
    if not payload:
        return "empty response body"
    magic, _, label = MAGIC[document.publisher]
    if not payload.startswith(magic):
        head = payload[:80].decode("utf-8", errors="replace").replace("\n", " ")
        return f"not a {label} (starts {head!r})"
    return None


def land_one(
    document: MonthlyDocument,
    vintage_dir: Path,
    session: requests.Session,
) -> tuple[dict | None, str | None, str | None]:
    """Fetch and write one document.

    Returns ``(manifest_entry, failure_reason, note)``. A NBS report that publishes no spreadsheet is
    neither a landing nor a failure — it is recorded and counted, because "the cross-check does not
    cover this month" is a fact about the elibrary, not an error in this run.
    """
    url = document.url
    if document.publisher == "nbs":
        resource = resolve_nbs_resource(document, session)
        if resource is None:
            return None, None, "no spreadsheet published for this report (image/scan only)"
        url = resource

    try:
        payload, status = fetch_document(url, session)
    except requests.RequestException as exc:
        return None, f"transport error: {exc}", None

    if status != 200:
        return None, f"HTTP {status}", None

    reason = look_like(document, payload)
    if reason is not None:
        return None, reason, None

    _, extension, _ = MAGIC[document.publisher]
    entry = build_retrieval(
        document=document,
        payload=payload,
        http_status=status,
        note=NOTE,
    )
    page_files = write_blobs(
        vintage_dir / document.dataset_id, [(f"page-0001{extension}", payload)], REPO_ROOT
    )
    # `metric_id` travels on the manifest entry, the way the World Bank and FRED flows record it, so
    # every source's manifest can be filtered by metric without the base parsing an id out of a path.
    entry = entry.manifest_entry(
        page_files=page_files,
        metric_id=METRIC_ID,
        publisher=document.publisher,
        period=document.period,
        resource_url=url,
    )
    return entry, None, None


def missing_months(periods: list[str]) -> list[str]:
    """Months absent from a contiguous span — the holes a gap flag would eventually report."""
    if not periods:
        return []
    first_year, first_month = (int(part) for part in min(periods).split("-"))
    last_year, last_month = (int(part) for part in max(periods).split("-"))
    index = first_year * 12 + first_month - 1
    end = last_year * 12 + last_month - 1
    present = set(periods)
    holes = []
    while index <= end:
        period = f"{index // 12:04d}-{index % 12 + 1:02d}"
        if period not in present:
            holes.append(period)
        index += 1
    return holes


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv if argv is not None else sys.argv[1:])
    publishers = [p.strip() for p in args.publishers.split(",") if p.strip()]
    unknown = [p for p in publishers if p not in MAGIC]
    if unknown:
        print(f"REFUSED  unknown publisher(s) {unknown}; known: {sorted(MAGIC)}")
        return 1

    vintage = args.vintage or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    vintage_dir = RAW_ROOT / vintage

    session = requests.Session()

    print("discovering the archive")
    documents: list[MonthlyDocument] = []
    if "oagf" in publishers:
        try:
            oagf = discover_oagf(session)
        except (FaacError, requests.RequestException) as exc:
            print(f"REFUSED  OAGF archive unavailable: {exc}")
            return 1
        documents.extend(oagf)
        print(f"  oagf: {len(oagf)} monthly documents", end="")
        if oagf:
            print(f", {oagf[0].period} -> {oagf[-1].period}")
        else:
            print()
    if "nbs" in publishers:
        try:
            nbs = discover_nbs(session)
        except (FaacError, requests.RequestException) as exc:
            print(f"  nbs: unavailable ({exc}) — continuing without the cross-check")
            nbs = []
        documents.extend(nbs)
        print(f"  nbs:  {len(nbs)} report documents", end="")
        if nbs:
            print(f", {nbs[0].period} -> {nbs[-1].period}")
        else:
            print()

    # A elibrary report that covers two months at once ("December 2022 & January 2023 Disbursement") is
    # not a month, and it carries two tables. Splitting it is a parsing decision the parser must make
    # explicitly, so this flow records the document and does not land it — guessing which table is
    # which month would put a real month's allocations in the wrong month, which is undetectable
    # downstream. The months it would have covered are reported as uncovered instead.
    multi_period = [d for d in documents if d.multi_period]
    if multi_period:
        documents = [d for d in documents if not d.multi_period]
        print()
        print(f"{len(multi_period)} document(s) cover more than one month and are not landed:")
        for document in multi_period:
            print(f"  excluded  {document.publisher:<5} {document.period}  {document.title[:70]}")

    if not documents:
        print("REFUSED  discovery found no documents — writing nothing rather than an empty vintage")
        return 1

    if args.limit:
        documents = documents[: args.limit]
        print(f"  limited to {len(documents)} documents for this run")

    try:
        prepare_vintage(vintage_dir, "faac")
    except VintageExists as exc:
        print(f"REFUSED  {exc}")
        return 1

    print()
    print(f"vintage:  {vintage}")
    print(f"landing:  {vintage_dir.relative_to(REPO_ROOT)}")
    print(f"documents: {len(documents)}")
    print()

    entries: list[dict] = []
    failures: dict[str, str] = {}
    skipped: list[dict] = []
    landed_periods: dict[str, list[str]] = {"oagf": [], "nbs": []}

    def pass_over(pending: list[MonthlyDocument]) -> list[MonthlyDocument]:
        remaining: list[MonthlyDocument] = []
        for document in pending:
            entry, failure, note = land_one(document, vintage_dir, session)
            if entry is not None:
                entries.append(entry)
                landed_periods[document.publisher].append(document.period)
                print(
                    f"  ok    {document.publisher:<5} {document.period}  "
                    f"{entry['payload_bytes'] / 1024:>8.0f} kB  sha256={entry['sha256'][:12]}"
                )
            elif failure is not None:
                remaining.append(document)
                failures[document.dataset_id] = failure
                print(f"  FAIL  {document.publisher:<5} {document.period}  {failure}")
            else:
                skipped.append(
                    {"publisher": document.publisher, "period": document.period, "title": document.title,
                     "reason": note}
                )
                print(f"  skip  {document.publisher:<5} {document.period}  {note}")
        return remaining

    pending = pass_over(documents)
    if pending:
        print()
        print(f"retrying {len(pending)} document(s) that did not land — a month that is really absent")
        print("fails both passes, so this keeps a transient error from leaving a hole in the series")
        failures.clear()
        still_pending = pass_over(pending)
        for document in still_pending:
            failures.setdefault(document.dataset_id, "failed on both attempts")

    coverage = {
        "vintage_date": vintage,
        "note": (
            "Ingest-time view only; Stage 3 owns the authoritative quality report. `missing_months` is "
            "the hole in each publisher's own span, before any gate."
        ),
        "primary_publisher": "oagf",
        "publishers": {
            publisher: {
                "n_landed": len(periods),
                "first_period": min(periods) if periods else None,
                "last_period": max(periods) if periods else None,
                "n_months_in_span": (
                    len(periods) + len(missing_months(periods)) if periods else 0
                ),
                "missing_months": missing_months(periods),
            }
            for publisher, periods in landed_periods.items()
        },
        "cross_check_months": sorted(set(landed_periods["oagf"]) & set(landed_periods["nbs"])),
        "cross_check_not_published": skipped,
        "multi_period_documents_excluded": [
            {"publisher": d.publisher, "period": d.period, "title": d.title}
            for d in multi_period
        ],
    }
    (vintage_dir / "coverage.json").write_text(json.dumps(coverage, indent=2), encoding="utf-8")

    write_manifest(
        vintage_dir=vintage_dir,
        vintage_date=vintage,
        source="faac",
        entries=entries,
        failures=[{"metric_id": key, "error": value} for key, value in sorted(failures.items())],
        extra={
            "n_documents_requested": len(documents),
            "n_documents_landed": len(entries),
            "n_cross_check_not_published": len(skipped),
            "n_multi_period_documents_excluded": len(multi_period),
            "primary_publisher": "oagf",
            "note": NOTE,
        },
    )

    print()
    for publisher, periods in landed_periods.items():
        if periods:
            holes = missing_months(periods)
            print(
                f"{publisher}: landed {len(periods)} months, {min(periods)} -> {max(periods)}, "
                f"{len(holes)} missing month(s)"
                + (f" {holes}" if holes else "")
            )
    overlap = len(set(landed_periods["oagf"]) & set(landed_periods["nbs"]))
    print(f"months published by both (the cross-check span): {overlap}")
    print(f"manifest: {(vintage_dir / 'manifest.json').relative_to(REPO_ROOT)}")
    print(f"coverage: {(vintage_dir / 'coverage.json').relative_to(REPO_ROOT)}")

    if failures:
        print()
        print(f"INCOMPLETE — {len(failures)} document(s) did not land; see manifest.failures")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
