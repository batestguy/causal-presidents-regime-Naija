"""Stage 2 ingestion flow: land the UCDP GED bulk archive.

Writes, per vintage:

    data/raw/ucdp/<vintage>/ged-<version>/page-0001.zip   bytes as received
    data/raw/ucdp/<vintage>/manifest.json                 provenance
    data/raw/ucdp/<vintage>/coverage.json                 what the archive covers, before any parsing

Why this source and this route: Stage 5 dropped Family A both for want of a state-attributed outcome
and because the security series were recorded as credential-blocked (C-13/C-14). The UCDP **API** does
need a token — verified 2026-10-17, 401 on three versions — but the **bulk archive** on the same host
does not. It is also CC-BY, so the state-month outcome can be derived and published; ACLED's terms
forbid redistributing its raw data.

Nothing is transformed here. The archive is tens of MB zipped and lands whole; the Nigeria filter and the
state-month aggregation happen in ``ingestion/parsers/ucdp_events.py``, which records the sha256 of the
archive it read.

Run::

    conda run -p "C:/Users/TOSHIBA/ds-general" python ingestion/flows/pull_ucdp.py
    conda run -p "C:/Users/TOSHIBA/ds-general" python ingestion/flows/pull_ucdp.py --version 24.1
    conda run -p "C:/Users/TOSHIBA/ds-general" python ingestion/flows/pull_ucdp.py --vintage 2026-10-17-ged
"""

from __future__ import annotations

import argparse
import io
import json
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import requests

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from ingestion.clients.provenance import (  # noqa: E402
    VintageExists,
    prepare_vintage,
    write_blobs,
    write_manifest,
)
from ingestion.clients.ucdp import (  # noqa: E402
    ADOPTED,
    NOTE,
    UcdpError,
    attribution,
    fetch_archive,
)

RAW_ROOT = REPO_ROOT / "data" / "raw" / "ucdp"
# The primary series the archive carries. The manifest's `metric_id` is a single value by schema, so
# it names the primary and `metrics` lists the rest — the gate reads the parsed artifact per item, not
# this field.
METRIC_ID = "fatalities"
METRICS = ["fatalities", "incidents", "fatalities_civilians"]


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Land the UCDP GED bulk archive.")
    parser.add_argument(
        "--vintage",
        default=None,
        help="vintage label (default: today's UTC date). A correction must use a new label — the raw "
             "layer is immutable (X-07).",
    )
    parser.add_argument(
        "--version",
        default=ADOPTED,
        help=f"GED release (default: {ADOPTED}, the adopted release)",
    )
    return parser.parse_args(argv)


def archive_coverage(payload: bytes) -> dict:
    """What the archive says about Nigeria, read without extracting anything to disk.

    This is a *coverage* reading, not the parse: it exists so the manifest can state how many Nigeria
    events the bytes contain and which months they span, without a second copy of the parser's logic.
    The authoritative figure for what lands is `data/staging/ucdp_state_month.csv`.
    """
    # Imported here so the flow's `--help` works on a machine without pandas.
    import pandas as pd

    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        names = [n for n in archive.namelist() if n.lower().endswith(".csv")]
        if not names:
            raise UcdpError("archive contains no CSV")
        with archive.open(names[0]) as handle:
            # GED's CSV carries no release label of its own — the version is the archive's name — so
            # the reading is restricted to the columns this coverage check actually uses.
            frame = pd.read_csv(handle, low_memory=False, usecols=[
                "id", "date_start", "country", "adm_1", "best", "type_of_violence",
            ])
    nigeria = frame[frame["country"] == "Nigeria"]
    months = pd.to_datetime(nigeria["date_start"]).dt.to_period("M")
    return {
        "archive_member": names[0],
        "n_events_global": int(len(frame)),
        "n_events_nigeria": int(len(nigeria)),
        "nigeria_first_month": str(months.min()) if len(months) else None,
        "nigeria_last_month": str(months.max()) if len(months) else None,
        "nigeria_n_months_span": int(months.nunique()) if len(months) else 0,
        "nigeria_n_states_published": int(nigeria["adm_1"].nunique()),
        "nigeria_state_labels": sorted(str(v) for v in nigeria["adm_1"].dropna().unique()),
        "nigeria_n_events_without_state": int(nigeria["adm_1"].isna().sum()),
        "nigeria_fatalities": int(nigeria["best"].fillna(0).sum()),
        "type_of_violence_counts": {
            str(k): int(v) for k, v in nigeria["type_of_violence"].value_counts().items()
        },
        "note": (
            "Read from the landed bytes at ingest time. The authoritative state-month totals are "
            "written by ingestion/parsers/ucdp_events.py to data/staging/ucdp_state_month.csv."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv if argv is not None else sys.argv[1:])
    vintage = args.vintage or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    vintage_dir = RAW_ROOT / vintage

    session = requests.Session()
    print(f"fetching UCDP GED {args.version}")
    try:
        retrieval, payload = fetch_archive(args.version, session)
    except (UcdpError, requests.RequestException) as exc:
        print(f"REFUSED  {exc}")
        return 1

    print(f"  {len(payload) / 1024 / 1024:.1f} MB  sha256={retrieval.sha256[:12]}")

    try:
        prepare_vintage(vintage_dir, "ucdp")
    except VintageExists as exc:
        print(f"REFUSED  {exc}")
        return 1

    coverage = archive_coverage(payload)
    if coverage["n_events_nigeria"] == 0:
        print("REFUSED  the archive carries no Nigeria events — writing nothing rather than an empty vintage")
        return 1

    page_files = write_blobs(
        vintage_dir / retrieval.dataset_id, [("page-0001.zip", payload)], REPO_ROOT
    )

    print()
    print(f"vintage:  {vintage}")
    print(f"landing:  {vintage_dir.relative_to(REPO_ROOT)}")
    print(
        f"nigeria:  {coverage['n_events_nigeria']:,} events, "
        f"{coverage['nigeria_first_month']} -> {coverage['nigeria_last_month']}, "
        f"{coverage['nigeria_n_states_published']} state labels, "
        f"{coverage['nigeria_n_events_without_state']} without a state"
    )

    # Per-release, not a module constant: a re-fetch of an older GED must not carry a newer version's
    # licence string (C-78).
    licence_attribution = attribution(args.version)

    entry = retrieval.manifest_entry(
        page_files=page_files,
        metric_id=METRIC_ID,
        metrics=METRICS,
        licence="CC-BY-4.0",
        attribution=licence_attribution,
        note=NOTE,
        n_events_nigeria=coverage["n_events_nigeria"],
    )
    entry["row_count"] = coverage["n_events_global"]

    coverage_payload = {"vintage_date": vintage, **coverage}
    (vintage_dir / "coverage.json").write_text(
        json.dumps(coverage_payload, indent=2), encoding="utf-8"
    )

    write_manifest(
        vintage_dir=vintage_dir,
        vintage_date=vintage,
        source="ucdp",
        entries=[entry],
        failures=[],
        extra={
            "licence": "CC-BY-4.0",
            "attribution": licence_attribution,
            "note": NOTE,
            "archive_version": args.version,
        },
    )

    print(f"manifest: {(vintage_dir / 'manifest.json').relative_to(REPO_ROOT)}")
    print(f"coverage: {(vintage_dir / 'coverage.json').relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
