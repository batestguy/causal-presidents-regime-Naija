"""Stage 2 ingestion flow: pull the FRED-sourced members of the metric catalogue.

Writes, per vintage (``vintage_date`` = UTC date of the run unless ``--vintage`` is given):

    data/raw/fred/<vintage>/<series_id>/page-0001.json   bytes as received
    data/raw/fred/<vintage>/manifest.json                provenance for every retrieval
    data/raw/fred/<vintage>/coverage.json                provisional coverage report

Requires a free API key in the environment, or in ``.env`` at the repo root::

    FRED_API_KEY=<32-char key>

Register: https://fred.stlouisfed.org/docs/api/api_key.html

Two differences from the World Bank flow, both deliberate:

1. **There is no keyless path.** Without a key FRED answers HTTP 400 ``api_key is not set``; the
   flow stops and writes nothing rather than landing an empty vintage that would later read as a
   coverage gap (decisions.md I-10 / C-20).
2. **The World Bank gap and spike gates are not applied.** ``DCOILBRENTEU`` is *daily*, so an
   annual missing-year rule and a year-on-year spike threshold are the wrong granularity and would
   fire on every weekend. What this flow reports instead is a coverage profile — span, per-month
   observation counts, longest run of missing days — because Stage 4 has to freeze a
   daily-to-monthly resampling rule and that rule must not be chosen against an unexamined series.

Run:
    conda run -p "C:/Users/TOSHIBA/ds-general" python ingestion/flows/pull_fred.py
    conda run -p "C:/Users/TOSHIBA/ds-general" python ingestion/flows/pull_fred.py --vintage 2026-10-11-rerun01
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from ingestion.clients.fred import fetch_series, get_api_key  # noqa: E402
from ingestion.clients.provenance import (  # noqa: E402
    MissingCredential,
    VintageExists,
    load_env_file,
    prepare_vintage,
    write_manifest,
    write_pages,
)

RAW_ROOT = REPO_ROOT / "data" / "raw" / "fred"

# Before the series' inception (Brent daily starts 1987-05-20), so the free endpoint returns the
# whole history. Stage 3 owns the study-window floor; Stage 2 does not narrow it, exactly as the
# World Bank flow does not.
OBSERVATION_START = "1960-01-01"

# FRED-sourced members of the metric catalogue. The oil node is the only FRED series any design
# names; (metric_id, series_id, series_name, note).
SERIES = [
    (
        "oil",
        "DCOILBRENTEU",
        "Crude Oil Prices: Brent - Europe (US Dollars per Barrel)",
        (
            "DAG node 'oil' (designs A and B) and part of design C's 'common'. DAILY, not "
            "monthly — the daily->monthly rule is frozen in Stage 4 (decisions.md C-21)"
        ),
    ),
]

# FRED marks a day with no value with a literal "." (weekends, holidays, and genuine gaps).
MISSING_MARKERS = {"", ".", "nan", "NaN", None}


def _present(rows: list[dict]) -> list[tuple[date, float]]:
    """Observations carrying a real value, as ``(date, value)`` in payload order."""
    out: list[tuple[date, float]] = []
    for row in rows:
        raw = row.get("value")
        if raw in MISSING_MARKERS:
            continue
        try:
            out.append((date.fromisoformat(row["date"]), float(raw)))
        except (KeyError, TypeError, ValueError):
            continue
    return out


def _longest_missing_run_days(observed: list[date], first: date, last: date) -> int:
    """Longest run of consecutive calendar days with no observation, inside the series span.

    Daily financial series always have such runs (weekends), so this is a descriptive statistic,
    not a gate: it tells Stage 4 how much interpolation a monthly resample will have to do and
    where the real holes are.
    """
    if not observed:
        return (last - first).days + 1
    seen = set(observed)
    longest = run = 0
    day = first
    while day <= last:
        if day in seen:
            run = 0
        else:
            run += 1
            longest = max(longest, run)
        day += timedelta(days=1)
    return longest


def _coverage_profile(rows: list[dict]) -> dict:
    """Coverage of one daily series: span, missing markers, and per-month observation counts."""
    dates = []
    for row in rows:
        try:
            dates.append(date.fromisoformat(row["date"]))
        except (KeyError, TypeError, ValueError):
            continue

    if not rows or not dates:
        return {
            "is_daily": True,
            "n_observations": 0,
            "n_with_value": 0,
            "first_date": None,
            "last_date": None,
            "span_days": 0,
            "n_missing_markers": 0,
            "longest_missing_run_days": 0,
            "n_months": 0,
            "months_with_no_observation": [],
            "min_observations_per_month": 0,
            "max_observations_per_month": 0,
            "gate_note": "series returned no observations",
        }

    present = _present(rows)
    observed_days = [day for day, _ in present]
    first, last = min(dates), max(dates)

    per_month: dict[str, int] = {}
    for day in observed_days:
        key = f"{day.year:04d}-{day.month:02d}"
        per_month[key] = per_month.get(key, 0) + 1

    months = sorted({
        f"{day.year:04d}-{day.month:02d}"
        for day in (first + timedelta(days=n) for n in range((last - first).days + 1))
    })
    empty_months = [month for month in months if month not in per_month]
    counts = sorted(per_month.values())

    return {
        "is_daily": True,
        "n_observations": len(rows),
        "n_with_value": len(present),
        "first_date": first.isoformat(),
        "last_date": last.isoformat(),
        "span_days": (last - first).days + 1,
        "n_missing_markers": len(rows) - len(present),
        "longest_missing_run_days": _longest_missing_run_days(observed_days, first, last),
        "n_months": len(months),
        "n_months_with_observation": len(per_month),
        "months_with_no_observation": empty_months,
        "min_observations_per_month": counts[0] if counts else 0,
        "max_observations_per_month": counts[-1] if counts else 0,
        "reaches_2023_subsidy_window": last.year >= 2023,
        "gate_note": (
            "Descriptive only. The annual gap and spike gates used for the World Bank series are "
            "not meaningful at daily granularity; Stage 3 owns the study-window floor (from 1999) "
            "and Stage 4 owns the daily->monthly resampling rule."
        ),
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Land the FRED subset of the metric catalogue.")
    parser.add_argument(
        "--vintage",
        default=None,
        help="vintage label (default: today's UTC date). A correction must use a new label, "
             "because the raw layer is immutable (X-07).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv if argv is not None else sys.argv[1:])
    load_env_file(REPO_ROOT)

    # Pre-flight the credential before touching the filesystem, so a keyless run refuses cleanly
    # rather than leaving a half-written vintage behind.
    try:
        get_api_key()
    except MissingCredential as exc:
        print(f"REFUSED  {exc}")
        return 1

    vintage = args.vintage or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    vintage_dir = RAW_ROOT / vintage

    try:
        prepare_vintage(vintage_dir, "fred")
    except VintageExists as exc:
        print(f"REFUSED  {exc}")
        return 1

    print(f"vintage: {vintage}")
    print(f"landing: {vintage_dir.relative_to(REPO_ROOT)}")
    print(f"series:  {len(SERIES)}")
    print()

    manifest_entries = []
    coverage: dict[str, dict] = {}
    failures = []

    for metric_id, series_id, name, note in SERIES:
        try:
            retrieval, observations = fetch_series(series_id, name, observation_start=OBSERVATION_START)
        except MissingCredential as exc:
            # No partial vintage. The manifest is only written at the end, so at this point the
            # directory holds nothing but this run's own files — remove it rather than leave a
            # vintage a later stage could read as "we fetched oil and it was empty".
            print(f"REFUSED  {exc}")
            shutil.rmtree(vintage_dir, ignore_errors=True)
            return 1
        except (RuntimeError, ValueError) as exc:
            failures.append({"metric_id": metric_id, "series_id": series_id, "error": str(exc)})
            print(f"  FAIL {metric_id:<12} {series_id:<14} {exc}")
            continue

        page_files = write_pages(vintage_dir / series_id, retrieval.payloads, REPO_ROOT)
        manifest_entries.append(
            retrieval.manifest_entry(metric_id=metric_id, note=note, page_files=page_files)
        )

        profile = _coverage_profile(observations)
        profile["series_id"] = series_id
        profile["series_name"] = name
        coverage[metric_id] = profile

        flag = "" if profile["n_with_value"] else " EMPTY"
        print(
            f"  ok   {metric_id:<12} {series_id:<14} obs={profile['n_with_value']:<6} "
            f"{profile['first_date']}..{profile['last_date']} "
            f"months={profile['n_months_with_observation']}/{profile['n_months']} "
            f"sha256={retrieval.sha256[:8]}{flag}"
        )

    write_manifest(
        vintage_dir=vintage_dir,
        vintage_date=vintage,
        source="fred",
        entries=manifest_entries,
        failures=failures,
        extra={"n_series_requested": len(SERIES)},
    )
    (vintage_dir / "coverage.json").write_text(
        json.dumps(
            {
                "vintage_date": vintage,
                "provisional": True,
                "granularity": "daily",
                "note": "Stage 3 owns the authoritative quality report; this is an ingest-time view.",
                "metrics": coverage,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    print()
    print(f"succeeded: {len(manifest_entries)}/{len(SERIES)}   failures: {len(failures)}")
    print(f"manifest: {(vintage_dir / 'manifest.json').relative_to(REPO_ROOT)}")
    print(f"coverage: {(vintage_dir / 'coverage.json').relative_to(REPO_ROOT)}")

    if failures:
        print()
        print("counts as an incomplete vintage — see manifest.failures")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
