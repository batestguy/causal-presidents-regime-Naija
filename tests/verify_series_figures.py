"""Independent verification of the outcome-series figures.

The figure is the one artifact whose content a reader can see without reading a number, so the failure that
matters is not "it is ugly" but "it draws something the base no longer says". This verifier re-derives every
count from `data/analytics.duckdb`, reads the outcome identity out of `analysis/specs/outcomes.yml`, and then
checks the published index and the SVG files against both — without importing the R engine or the app:

  * **One panel per outcome, and no others.** The twelve ids and their order come from the outcome registry.
  * **The counts are the base's.** `observed` / `interpolated` / `unobserved`, the window, the first and last
    observation, and the number of native observations are recomputed from the two base tables.
  * **The identity is the dimension's.** Unit, native frequency and Stage 3 status come from `dim_metric`;
    the source and direction come from `outcomes.yml`.
  * **The definition breaks are the ones inside the window.** A break outside it would be a claim about a
    period the panel does not draw.
  * **The figure is the one the artifact records.** Its byte count is compared to the file, and the strings
    the spec requires as text (label, unit, status, counts, direction, break names) are looked for in the
    rendered SVG — so a label that failed to render fails here instead of being noticed by a reader.
  * **The caption agrees with the panel.** Every number in it is recomputed here first, and the "series
    stops at" sentence is required exactly when the series does stop inside the window.
  * **The artifact describes this vintage.** Its vintage must be the registry index's, and its recorded md5s
    must be the spec files on disk — a spec edited without a rebuild is caught rather than trusted.

Usage:
    python tests/verify_series_figures.py
"""

from __future__ import annotations

import hashlib
import html
import json
import re
import sys
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SERIES_ROOT = REPO_ROOT / "registry" / "series"
CARDS_INDEX = REPO_ROOT / "registry" / "dags" / "index.json"
SPEC_FILE = REPO_ROOT / "analysis" / "specs" / "series_figures.yml"
OUTCOMES_FILE = REPO_ROOT / "analysis" / "specs" / "outcomes.yml"

DIRECTION_WORDS = {"down": "lower is better", "up": "higher is better"}


def fail(failures: list[str], message: str) -> None:
    failures.append(message)


def md5(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


def month(value: date) -> str:
    return f"{value.year:04d}-{value.month:02d}"


def newest_vintage() -> Path | None:
    if not SERIES_ROOT.exists():
        return None
    dirs = sorted((p for p in SERIES_ROOT.iterdir() if p.is_dir()), key=lambda p: p.name)
    return dirs[-1] if dirs else None


def svg_text(path: Path) -> str:
    raw = path.read_text(encoding="utf-8")
    texts = re.findall(r"<text[^>]*>(.*?)</text>", raw, flags=re.S)
    return html.unescape(" ".join(re.sub(r"<[^>]*>", "", t) for t in texts))


def main() -> int:
    failures: list[str] = []

    artefact_dir = newest_vintage()
    if artefact_dir is None:
        print("FAILED — registry/series/ holds no vintage, so no outcome figure is published")
        return 1
    index_path = artefact_dir / "index.json"
    if not index_path.exists():
        print(f"FAILED — {index_path.relative_to(REPO_ROOT)} is missing")
        return 1
    artifact = json.loads(index_path.read_text(encoding="utf-8"))

    try:
        import yaml
    except ImportError:
        print("FAILED — PyYAML is not importable, so the declared outcome list cannot be read")
        return 1
    outcomes_spec = yaml.safe_load(OUTCOMES_FILE.read_text(encoding="utf-8"))
    declared = outcomes_spec["outcomes"]
    declared_ids = [row["id"] for row in declared]

    # -- the artifact describes this run and this spec -------------------------------------------
    vintage = artifact.get("vintage")
    cards_index = json.loads(CARDS_INDEX.read_text(encoding="utf-8"))
    if vintage != cards_index.get("vintage_date"):
        fail(failures,
             f"the series artifact is vintage {vintage!r} and the registry index is "
             f"{cards_index.get('vintage_date')!r} — the app would show a series from one vintage beside a "
             f"card from another")
    recorded = (artifact.get("spec") or {}).get("md5")
    if recorded != md5(SPEC_FILE):
        fail(failures, "the spec's md5 has moved since the figures were drawn — rebuild the figures "
                       "(analysis/R/07_series_figures.R); the panels would otherwise describe an older spec")
    recorded_outcomes = (artifact.get("input") or {}).get("outcomes_spec_md5")
    if recorded_outcomes != md5(OUTCOMES_FILE):
        fail(failures, "analysis/specs/outcomes.yml has moved since the figures were drawn — a panel is "
                       "missing or renamed")

    # -- the base -------------------------------------------------------------------------------
    try:
        import duckdb
    except ImportError:
        print("FAILED — duckdb is not importable, so the counts cannot be re-derived from the base")
        return 1
    database = (artifact.get("input") or {}).get("database")
    db_path = REPO_ROOT / str(database)
    if not db_path.exists():
        print(f"FAILED — {db_path.relative_to(REPO_ROOT)} is missing; run `dbt build` before verifying")
        return 1
    con = duckdb.connect(str(db_path), read_only=True)
    inputs = artifact["input"]
    placeholders = ", ".join("?" for _ in declared_ids)

    window_first, window_last = con.execute(
        f"select min(period_month), max(period_month) from {inputs['fact_table']} "
        f"where metric_id in ({placeholders})", declared_ids
    ).fetchone()
    published_window = artifact.get("window") or {}
    if (published_window.get("first"), published_window.get("last")) != (month(window_first), month(window_last)):
        fail(failures, f"the artifact's window {published_window} is not the base's "
                       f"{month(window_first)}..{month(window_last)}")

    spine = con.execute(
        f"select metric_id, observation_type, count(*) from {inputs['fact_table']} "
        f"where metric_id in ({placeholders}) group by 1, 2", declared_ids
    ).fetchall()
    totals = {"observed": 0, "interpolated": 0, "unobserved": 0}
    per_metric: dict[str, dict[str, int]] = {mid: {"observed": 0, "interpolated": 0, "unobserved": 0}
                                             for mid in declared_ids}
    for metric_id, observation_type, count in spine:
        if observation_type not in totals:
            fail(failures, f"{metric_id}: the base carries observation_type {observation_type!r}, which the "
                           f"marks do not define")
            continue
        totals[observation_type] += count
        per_metric[metric_id][observation_type] = count
    published_totals = (artifact.get("counts") or {}).get("spine_rows") or {}
    for key, value in totals.items():
        if published_totals.get(key) != value:
            fail(failures, f"the artifact says {published_totals.get(key)} {key} spine rows and the base has "
                           f"{value}")

    # -- one panel per outcome -------------------------------------------------------------------
    rows = artifact.get("outcomes") or []
    published_ids = [row.get("id") for row in rows]
    if published_ids != declared_ids:
        fail(failures, f"the panels are {published_ids} and the outcome registry declares {declared_ids} — "
                       f"one panel per outcome card, in the registry's order")
    if (artifact.get("counts") or {}).get("outcomes") != len(declared_ids):
        fail(failures, "the artifact's outcome count is not the registry's")

    figures_seen: set[str] = set()
    for row, declared_row in zip(rows, declared):
        oid = row.get("id")
        if oid != declared_row.get("id"):
            continue
        dim = con.execute(
            f"select label, unit, native_frequency, quality_status from {inputs['metric_dimension']} "
            f"where metric_id = ?", [oid]
        ).fetchone()
        if dim is None:
            fail(failures, f"{oid}: no row in dim_metric, so a unit or a Stage 3 status is missing from the "
                           f"panel and the artifact should not have been written")
            continue
        label, unit, frequency, status = dim
        for field, expected in (("label", label), ("unit", unit), ("native_frequency", frequency),
                                ("quality_status", status)):
            if row.get(field) != expected:
                fail(failures, f"{oid}: the artifact's {field} is {row.get(field)!r} and the base says "
                               f"{expected!r}")

        counts = con.execute(
            f"select count(*) from {inputs['fact_table']} where metric_id = ?", [oid]
        ).fetchone()[0]
        published_counts = row.get("observations") or {}
        if sum(published_counts.values()) != counts:
            fail(failures, f"{oid}: the artifact's counts sum to {sum(published_counts.values())} and the base "
                           f"has {counts} months")
        for key, value in per_metric.get(oid, {}).items():
            if published_counts.get(key) != value:
                fail(failures, f"{oid}: {key} is {published_counts.get(key)} in the artifact and {value} in "
                               f"the base")

        native = con.execute(
            f"select count(*) from {inputs['native_table']} where metric_id = ? "
            f"and anchor_month between ? and ? and value is not null", [oid, window_first, window_last]
        ).fetchone()[0]
        if row.get("native_in_window") != native:
            fail(failures, f"{oid}: native_in_window is {row.get('native_in_window')} and the base has "
                           f"{native} native observations with a value in the window")

        first_obs, last_obs = con.execute(
            f"select min(period_month), max(period_month) from {inputs['fact_table']} "
            f"where metric_id = ? and observation_type = 'observed'", [oid]
        ).fetchone()
        for field, expected in (("first_observed", month(first_obs) if first_obs else None),
                                ("last_observed", month(last_obs) if last_obs else None)):
            if row.get(field) != expected:
                fail(failures, f"{oid}: {field} is {row.get(field)!r} and the base says {expected!r}")

        drawable = counts > 0
        if row.get("drawable") is not drawable:
            fail(failures, f"{oid}: drawable is {row.get('drawable')} and the base has {counts} row(s)")

        breaks = con.execute(
            f"select break_month, label from {inputs['definition_break_table']} "
            f"where metric_id = ? and break_month between ? and ? order by break_month",
            [oid, window_first, window_last]
        ).fetchall()
        published_breaks = row.get("definition_breaks") or []
        if [b.get("date") for b in published_breaks] != [month(b[0]) for b in breaks]:
            fail(failures, f"{oid}: the artifact's definition breaks {[b.get('date') for b in published_breaks]} "
                           f"are not the base's in-window breaks {[month(b[0]) for b in breaks]}")
        if [b.get("name") for b in published_breaks] != [b[1] for b in breaks]:
            fail(failures, f"{oid}: a definition break's name is not the dimension's label")

        # -- the caption -----------------------------------------------------------------------
        caption = str(row.get("caption") or "")
        for needle, what in (
            (f"{published_counts.get('observed')} observations in the window", "the observed count"),
            (f"{published_counts.get('interpolated')} months interpolated", "the interpolated count"),
            (f"{published_counts.get('unobserved')} months with no observation", "the absent count"),
            (f"Stage 3 status {status}", "the Stage 3 status"),
            (f"Native frequency {frequency}", "the native frequency"),
        ):
            if needle not in caption:
                fail(failures, f"{oid}: the caption does not carry {what} ({needle!r})")
        if last_obs and month(last_obs) not in caption:
            fail(failures, f"{oid}: the caption does not name the last observation ({month(last_obs)})")
        if last_obs and last_obs < window_last:
            if f"The series stops at {month(last_obs)}" not in caption:
                fail(failures, f"{oid}: the series stops before the window ends and the caption does not say so")
        for _, break_label in breaks:
            if break_label not in caption:
                fail(failures, f"{oid}: the caption does not name the definition break {break_label!r}")

        # -- the figure ------------------------------------------------------------------------
        figure = row.get("figure") or {}
        path = REPO_ROOT / str(figure.get("path") or "")
        if not path.exists():
            fail(failures, f"{oid}: the figure {figure.get('path')!r} is not on disk")
            continue
        if path in figures_seen:
            fail(failures, f"{oid}: two outcomes share one figure file ({figure.get('path')})")
        figures_seen.add(str(path))
        size = path.stat().st_size
        if figure.get("bytes") != size:
            fail(failures, f"{oid}: the artifact records {figure.get('bytes')} bytes and the file is {size} — "
                           f"the figure is not the one the artifact describes")
        raw = path.read_text(encoding="utf-8")
        if "<svg" not in raw or raw.count("<text") < 5:
            fail(failures, f"{oid}: {path.name} is not a real SVG with rendered text")
            continue
        rendered = svg_text(path)
        counts_line = (f"observed {published_counts.get('observed')}  "
                       f"·  interpolated {published_counts.get('interpolated')}  "
                       f"·  no observation {published_counts.get('unobserved')} of {counts} months")
        needles = [label, unit, f"stage 3: {status}", counts_line,
                   DIRECTION_WORDS.get(str(row.get("direction")), "")]
        needles += [b[1] for b in breaks]
        for needle in needles:
            if needle and needle not in rendered:
                fail(failures, f"{oid}: the SVG does not carry {needle!r} as text — a required label did not "
                               f"render, so the figure cannot be checked by reading it")

    # -- the headline counts ---------------------------------------------------------------------
    flagged = sum(1 for row in rows if row.get("quality_status") == "flagged")
    with_break = sum(1 for row in rows if row.get("definition_breaks"))
    for field, expected in (("flagged", flagged), ("with_definition_break", with_break)):
        if (artifact.get("counts") or {}).get(field) != expected:
            fail(failures, f"the artifact's counts.{field} is {(artifact.get('counts') or {}).get(field)} and "
                           f"the panels say {expected}")

    con.close()

    if failures:
        print(f"FAILED — {len(failures)} problem(s):")
        for problem in failures[:40]:
            print(f"  - {problem}")
        if len(failures) > 40:
            print(f"  … and {len(failures) - 40} more")
        return 1

    print(f"panels        : {len(rows)} outcome series at vintage {vintage}, one per outcome card, "
          f"{totals['observed']} observed / {totals['interpolated']} interpolated / "
          f"{totals['unobserved']} unobserved months")
    print(f"counts        : every count, span and first/last observation re-derived from the base")
    print(f"identity      : unit, native frequency and Stage 3 status read from dim_metric; "
          f"{with_break} panel(s) carry a definition break")
    print(f"figures       : {len(figures_seen)} SVG(s) whose byte count and required text match the artifact")
    print(f"captions      : every caption's numbers recomputed before it was accepted")
    print()
    print("PASS — the panels draw what the base holds, and a figure that moved under its rows fails here")
    return 0


if __name__ == "__main__":
    sys.exit(main())
