"""Verify the Stage 3 vintage quality report.

Re-derives the gate results **independently of** ``ingestion/quality/gates.py`` — parsing the raw
payloads directly and recomputing the gap and spike results from scratch — then compares them with
what the report claims. The gates are the thing under test; a verifier that imported them would only
prove the module is self-consistent.

What it checks:

  * **Exit criterion** — every series declared by every manifest has a row in the report. PHASES.md
    Stage 3 says no series reaches Stage 4 without a gate result, and that is only true if nothing is
    omitted. A silent omission is the failure mode this check exists for.
  * **The study-window floor actually does something** — the pre-1999 volatility that C-06 and C-21
    recorded must be *absent* from the windowed results and *present* in an unwindowed recomputation.
    If the floor were inert, both scans would agree and the check fails.
  * **Gap and spike results reproduce** — recomputed per series and compared with the report.
  * **Adjudications are live** — every adjudication declared in the spec matched a real flagged event
    (a stale entry means the spec has drifted from the data), and every verdict is from the declared
    vocabulary.

Usage:
    conda run -p "C:/Users/TOSHIBA/ds-general" python tests/verify_quality.py
"""

from __future__ import annotations

import csv
import json
from datetime import date
from itertools import pairwise
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
RAW_ROOT = REPO_ROOT / "data" / "raw"
QUALITY_ROOT = REPO_ROOT / "registry" / "quality"
SPEC_PATH = REPO_ROOT / "analysis" / "specs" / "quality.yml"

VERDICTS = {
    "accepted_as_real_event",
    "accounting_artefact",
    "explained_by_definition_break",
    "probable_data_error",
}
MULTI_COUNTRY_SOURCES = {"worldbank_donors"}


# ------------------------------------------------------------------------------------------
# an independent reimplementation of the gate arithmetic — deliberately not imported
# ------------------------------------------------------------------------------------------
def mi(year: int, month: int) -> int:
    return year * 12 + (month - 1)


def study_start_index(spec: dict) -> int:
    year, _, tail = str(spec["study_window"]["start"]).partition("-")
    return mi(int(year), int(tail.split("-")[0]) if tail else 1)


def annual_points(rows: list[dict]) -> list[tuple[str, int, int, float | None]]:
    """(label, start_index, end_index, value) for annual rows, sorted ascending."""
    out = []
    for row in rows or []:
        raw = row.get("date")
        if not raw or not str(raw)[:4].isdigit():
            continue
        year = int(str(raw)[:4])
        value = row.get("value")
        out.append((str(year), mi(year, 1), mi(year, 12), None if value is None else float(value)))
    return sorted(out, key=lambda p: p[1])


def monthly_points(observations: list[dict]) -> list[tuple[str, int, int, float | None]]:
    """Daily observations averaged to months, every month in the span emitted (even empty ones)."""
    buckets: dict[int, list[float]] = {}
    for obs in observations:
        raw = obs.get("date")
        if not raw:
            continue
        try:
            day = date.fromisoformat(str(raw))
        except ValueError:
            continue
        value = obs.get("value")
        if value in (None, "", "."):
            continue
        buckets.setdefault(mi(day.year, day.month), []).append(float(value))
    if not buckets:
        return []
    out = []
    for index in range(min(buckets), max(buckets) + 1):
        values = buckets.get(index)
        out.append(
            (
                f"{index // 12:04d}-{index % 12 + 1:02d}",
                index,
                index,
                None if not values else sum(values) / len(values),
            )
        )
    return out


def recompute(points, *, start: int, end: int, max_gap_months: int, measure: str,
              threshold_pct: float, threshold_points: float) -> dict:
    observed = [p for p in points if p[3] is not None and p[2] >= start and p[1] <= end]
    longest = 0
    n_runs = 0
    for (_, _, prev_end, _), (_, cur_start, _, _) in pairwise(observed):
        missing = cur_start - prev_end - 1
        if missing > 0:
            n_runs += 1
            longest = max(longest, missing)

    spikes = []
    for (plabel, _, prev_end, pval), (clabel, cur_start, _, cval) in pairwise(observed):
        if cur_start != prev_end + 1:
            continue
        if measure == "relative":
            if not pval:
                continue
            if abs((cval - pval) / abs(pval) * 100.0) > threshold_pct:
                spikes.append(clabel)
        else:
            if abs(cval - pval) > threshold_points:
                spikes.append(clabel)

    return {
        "n_observed": len(observed),
        "first": observed[0][0] if observed else None,
        "last": observed[-1][0] if observed else None,
        "max_gap_months": longest,
        "n_gap_runs": n_runs,
        "gap_tripped": longest > max_gap_months,
        "spike_periods": spikes,
        "spike_tripped": bool(spikes),
    }


# ------------------------------------------------------------------------------------------
# payload discovery — mirrors the flow, independently
# ------------------------------------------------------------------------------------------
def load_series(spec: dict) -> dict:
    """{(source, metric_id, scope): {"points": [...], "grain": str}} for the latest vintage."""
    series: dict = {}
    document_sources = set((spec.get("document_sources") or {}).keys())
    for source_dir in sorted(p for p in RAW_ROOT.iterdir() if p.is_dir()):
        source = source_dir.name
        # A document source's page files are PDFs or spreadsheets. They are gated from the parsed
        # artifact below, not from the payload — reading them here would fail on the first byte of a
        # PDF rather than verifying anything.
        if source in document_sources:
            continue
        vintages = sorted(p.name for p in source_dir.iterdir() if p.is_dir())
        if not vintages:
            continue
        vintage_dir = source_dir / vintages[-1]
        manifest = json.loads((vintage_dir / "manifest.json").read_text(encoding="utf-8"))
        for retrieval in manifest["retrievals"]:
            blobs = [
                json.loads((REPO_ROOT / page).read_text(encoding="utf-8"))
                for page in retrieval["page_files"]
            ]
            metric = retrieval["metric_id"]
            if source == "fred":
                observations = [o for blob in blobs for o in blob["observations"]]
                series[(source, metric, None)] = {
                    "points": monthly_points(observations),
                    "grain": "monthly",
                }
            elif source in MULTI_COUNTRY_SOURCES:
                grouped: dict[str, list[dict]] = {}
                for blob in blobs:
                    for row in blob[1]:
                        code = ((row.get("country") or {}).get("id")) or row.get("countryiso3code")
                        grouped.setdefault(str(code).upper(), []).append(row)
                for code, rows in grouped.items():
                    series[(source, metric, code)] = {
                        "points": annual_points(rows),
                        "grain": "annual",
                    }
            else:
                rows = [row for blob in blobs for row in blob[1]]
                series[(source, metric, "NGA")] = {"points": annual_points(rows), "grain": "annual"}
    return series


def publisher_precedence(spec: dict) -> list[str]:
    """The publisher order declared in harmonisation.yml, read rather than restated."""
    for cfg in (spec.get("document_sources") or {}).values():
        rule = cfg.get("publisher_rule") or {}
        if not rule:
            continue
        document = yaml.safe_load((REPO_ROOT / rule["spec"]).read_text(encoding="utf-8"))
        node = document
        for key in rule["path"]:
            node = node[key]
        return [node["primary"], node["fallback"]]
    return []


def staging_rows(cfg: dict) -> list[dict]:
    with (REPO_ROOT / cfg["staging"]).open(newline="", encoding="utf-8") as handle:
        return [row for row in csv.DictReader(handle) if row.get("item") == cfg["value_item"]]


def load_document_series(spec: dict) -> dict:
    """The same shape as ``load_series``, built from each document source's parsed artifact.

    Written independently of ``gates.parse_staging_monthly_series`` on purpose: the verifier has to
    recompute the selection, not call the code under test. The publisher precedence is therefore
    re-applied here from the declared rule.
    """
    series: dict = {}
    precedence = publisher_precedence(spec)
    for name, cfg in (spec.get("document_sources") or {}).items():
        if not (REPO_ROOT / cfg["staging"]).exists():
            continue
        rows = staging_rows(cfg)
        chosen: dict[str, dict[int, tuple[float, int]]] = {}
        for row in rows:
            month = str(row["period_month"])[:7]
            year, _, number = month.partition("-")
            index = mi(int(year), int(number))
            publisher = str(row.get(cfg.get("publisher_field") or ""))
            rank = precedence.index(publisher) if publisher in precedence else len(precedence)
            key = str(row[cfg["series_key"]])
            current = chosen.setdefault(key, {}).get(index)
            if current is None or rank < current[1]:
                chosen[key][index] = (float(row[cfg["value_field"]]), rank)

        points = {
            key: [
                (f"{index // 12:04d}-{index % 12 + 1:02d}", index, index, value)
                for index, (value, _) in sorted(monthly.items())
            ]
            for key, monthly in chosen.items()
        }
        n_units = len(points)
        months: dict[int, list[float]] = {}
        for unit_points in points.values():
            for _, index, _, value in unit_points:
                months.setdefault(index, []).append(value)
        if n_units:
            points[cfg.get("national_scope", "national")] = [
                (f"{index // 12:04d}-{index % 12 + 1:02d}", index, index, sum(values))
                for index, values in sorted(months.items())
                if len(values) == n_units
            ]
        for scope, unit_points in points.items():
            series[(name, cfg["metric_id"], scope)] = {"points": unit_points, "grain": "monthly"}
    return series


def documents_are_accounted_for(spec: dict) -> list[str]:
    """Every document the raw layer landed must be referenced by the parsed artifact.

    The exit criterion is *no series reaches Stage 4 without a gate result*. For a document source the
    unit of the raw layer is a document, not a series, so the equivalent claim is that the artifact the
    gate read was built from every landed document. A parse that dropped a file would otherwise shrink
    the series silently while the gate kept passing.
    """
    problems: list[str] = []
    for name, cfg in (spec.get("document_sources") or {}).items():
        vintages = sorted(p.name for p in (RAW_ROOT / name).iterdir() if p.is_dir())
        if not vintages:
            problems.append(f"{name}: declared as a document source but has no vintage")
            continue
        manifest = json.loads(
            (RAW_ROOT / name / vintages[-1] / "manifest.json").read_text(encoding="utf-8")
        )
        landed = {page.replace("\\", "/") for r in manifest["retrievals"] for page in r["page_files"]}
        referenced = {row["source_file"] for row in staging_rows(cfg)}
        for page in sorted(landed - referenced):
            problems.append(f"{name}: landed document not read by the parsed artifact: {page}")
        for page in sorted(referenced - landed):
            problems.append(f"{name}: parsed artifact cites a document that is not in the manifest: {page}")
    return problems


def main() -> int:
    if not SPEC_PATH.exists():
        raise SystemExit(f"no gate specification at {SPEC_PATH}")
    report_dirs = sorted(p for p in QUALITY_ROOT.iterdir() if p.is_dir()) if QUALITY_ROOT.exists() else []
    if not report_dirs:
        raise SystemExit(f"no quality report under {QUALITY_ROOT} — run check_quality.py first")

    spec = yaml.safe_load(SPEC_PATH.read_text(encoding="utf-8"))
    thresholds = spec["thresholds"]
    start = study_start_index(spec)
    pp_series = set(spec["spike_measure"]["percentage_point_series"])
    failures: list[str] = []

    report_dir = report_dirs[-1]
    report = json.loads((report_dir / "report.json").read_text(encoding="utf-8"))
    rows = {(r["source"], r["metric_id"], r["scope"]) for r in report["series"]}
    print(f"report {report['report_vintage']} | {report['n_series_gated']} series | "
          f"ok {report['counts']['ok']}, flagged {report['counts']['flagged']}, "
          f"empty {report['counts']['empty']}")

    series = load_series(spec)
    document_series = load_document_series(spec)
    if document_series:
        print(f"document sources: {len(document_series)} series from the parsed artifacts")
    series.update(document_series)
    failures.extend(documents_are_accounted_for(spec))

    # ---- 1. exit criterion -------------------------------------------------------------
    missing = sorted(set(series) - rows)
    extra = sorted(rows - set(series))
    for key in missing:
        failures.append(f"exit criterion: {key} is in the manifest but has no gate result")
    for key in extra:
        failures.append(f"{key} is in the report but not in any manifest (stale row)")
    print(f"\nexit criterion: {len(series)} series in the manifests, {len(rows)} gated, "
          f"{len(missing)} omitted")

    # ---- 2. per-series reproduction ----------------------------------------------------
    print(f"\n{'metric':<20}{'scope':<6}{'recov n':>8}{'gap':>6}{'spikes':>8}  agree")
    print("-" * 62)
    disagreements = 0
    for row in sorted(report["series"], key=lambda r: (r["source"], r["metric_id"], r["scope"] or "")):
        key = (row["source"], row["metric_id"], row["scope"])
        entry = series.get(key)
        if entry is None:
            continue
        points = entry["points"]
        end = max((p[2] for p in points), default=start)
        measure = "points" if row["metric_id"] in pp_series else "relative"
        got = recompute(
            points,
            start=start,
            end=end,
            max_gap_months=thresholds["gap_max_months"],
            measure=measure,
            threshold_pct=thresholds["spike_pct"],
            threshold_points=thresholds["spike_points"],
        )
        claimed = row["gates"]
        ok = (
            got["n_observed"] == claimed["coverage"]["n_observed"]
            and got["max_gap_months"] == claimed["gap"]["max_gap_months"]
            and got["n_gap_runs"] == claimed["gap"]["n_gap_runs"]
            and got["gap_tripped"] == claimed["gap"]["tripped"]
            and len(got["spike_periods"]) == claimed["spike"]["n_spikes"]
            and sorted(got["spike_periods"]) == sorted(s["to"] for s in claimed["spike"]["spikes"])
        )
        if not ok:
            disagreements += 1
            claimed_periods = [s["to"] for s in claimed["spike"]["spikes"]]
            failures.append(
                f"{row['metric_id']}/{row['scope']}: report disagrees with independent "
                f"recomputation — observed {got['n_observed']} vs "
                f"{claimed['coverage']['n_observed']}, max gap {got['max_gap_months']}m vs "
                f"{claimed['gap']['max_gap_months']}m, gap runs {got['n_gap_runs']} vs "
                f"{claimed['gap']['n_gap_runs']}, n_spikes {len(got['spike_periods'])} vs "
                f"reported {claimed['spike']['n_spikes']}"
                + (
                    f", listed periods {sorted(got['spike_periods'])} vs "
                    f"{sorted(claimed_periods)}"
                    if sorted(got["spike_periods"]) != sorted(claimed_periods)
                    else ""
                )
            )
        if row["source"] == "worldbank" or row["metric_id"] == "oil":
            print(f"{row['metric_id']:<20}{(row['scope'] or '-'):<6}{got['n_observed']:>8}"
                  f"{got['max_gap_months']:>6}{len(got['spike_periods']):>8}  {'ok' if ok else 'FAIL'}")

    # ---- 3. the study-window floor must be doing work -----------------------------------
    # Recompute WITHOUT the floor and confirm the pre-1999 volatility is there. If the floored and
    # unfloored scans agreed, the floor would be inert and this whole gate a formality.
    pre_1999_found: dict[str, list[str]] = {}
    for row in report["series"]:
        key = (row["source"], row["metric_id"], row["scope"])
        entry = series.get(key)
        if entry is None:
            continue
        points = entry["points"]
        end = max((p[2] for p in points), default=start)
        measure = "points" if row["metric_id"] in pp_series else "relative"
        unfenced = recompute(
            points,
            start=0,
            end=end,
            max_gap_months=thresholds["gap_max_months"],
            measure=measure,
            threshold_pct=thresholds["spike_pct"],
            threshold_points=thresholds["spike_points"],
        )
        windowed = {s["to"] for s in row["gates"]["spike"]["spikes"]}
        pre = [p for p in unfenced["spike_periods"] if p not in windowed and p[:4].isdigit()
               and int(p[:4]) < 1999]
        if pre:
            pre_1999_found[f"{row['source']}/{row['metric_id']}/{row['scope'] or '-'}"] = pre

    # Nothing in the report may itself be pre-1999. Checked first, because when the floor has been
    # disabled this is the direct symptom and the "inert" reading below would be a false one.
    reported_pre_1999 = 0
    for row in report["series"]:
        for spike in row["gates"]["spike"]["spikes"]:
            if spike["to"][:4].isdigit() and int(spike["to"][:4]) < 1999:
                reported_pre_1999 += 1
                failures.append(
                    f"{row['metric_id']}/{row['scope']}: the report flags a pre-1999 spike "
                    f"({spike['to']}) — the study-window floor was not applied"
                )

    total_pre = sum(len(v) for v in pre_1999_found.values())
    print(f"\nstudy-window floor: {total_pre} pre-1999 spikes exist in an unwindowed scan")
    if total_pre == 0 and reported_pre_1999 == 0:
        failures.append(
            "the study-window floor is inert: neither the report nor an unwindowed scan found any "
            "pre-1999 spike, so the floor is not demonstrably doing anything (C-06/C-21 recorded "
            "pre-1999 volatility in several series)"
        )
    for label, periods in sorted(pre_1999_found.items()):
        print(f"  suppressed: {label:<34}{', '.join(periods[:6])}"
              f"{' …' if len(periods) > 6 else ''}")

    # ---- 4. adjudications are live and use the declared vocabulary ----------------------
    declared = {(a["metric_id"], a["period"]) for a in spec.get("spike_adjudications") or []}
    matched = set()
    for row in report["series"]:
        for event in row["gates"]["spike"]["adjudicated"]:
            matched.add((row["metric_id"], event["to"]))
            if event["verdict"] not in VERDICTS:
                failures.append(
                    f"{row['metric_id']}/{event['to']}: verdict '{event['verdict']}' is not in the "
                    f"declared vocabulary {sorted(VERDICTS)}"
                )
    stale = declared - matched
    for metric_id, period in sorted(stale):
        failures.append(
            f"stale adjudication in the spec: {metric_id}/{period} matched no flagged event "
            "(the spec has drifted from the data)"
        )
    n_unadj = sum(len(r["gates"]["spike"]["unadjudicated"]) for r in report["series"])
    print(f"adjudications: {len(matched)} matched, {len(stale)} stale; "
          f"{n_unadj} spikes left unadjudicated (reported, not dropped)")

    # ---- 5. report counts are self-consistent ------------------------------------------
    recount = {"ok": 0, "flagged": 0, "empty": 0}
    for row in report["series"]:
        recount[row["status"]] = recount.get(row["status"], 0) + 1
    if recount != report["counts"]:
        failures.append(f"report counts {report['counts']} disagree with its own rows {recount}")

    print()
    if failures:
        print(f"FAILED — {len(failures)} problem(s):")
        for problem in failures[:40]:
            print(f"  - {problem}")
        if len(failures) > 40:
            print(f"  … and {len(failures) - 40} more")
        return 1
    print("PASS — every series has a gate result, the gap and spike results reproduce from the raw "
          "payloads, the study-window floor demonstrably suppresses pre-1999 noise, and every "
          "adjudication is live")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
