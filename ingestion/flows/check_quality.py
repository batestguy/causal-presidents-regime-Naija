"""Stage 3 flow: apply the quality gates to every landed series and publish the vintage report.

Reads the raw layer and writes:

    registry/quality/<vintage>/report.json    machine-readable, one row per gated series
    registry/quality/<vintage>/report.md      the human-readable page

The gates live in :mod:`ingestion.quality.gates` and their configuration — study window, thresholds,
declared resample rules, definition breaks, spike adjudications — in ``analysis/specs/quality.yml``.
This flow is only plumbing: it finds the series, feeds them through the gates, and writes down what
came back. Nothing is decided here, so a gate result can be reproduced from the spec plus the payload.

Exit criteria (PHASES.md Stage 3): **no series reaches Stage 4 without a gate result**, and the report
is published with the vintage timestamp. Both are enforced — a series present in a manifest with no
row in the report is a failure, not an omission.

Run:
    conda run -p "C:/Users/TOSHIBA/ds-general" python ingestion/flows/check_quality.py
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from ingestion.quality.gates import (  # noqa: E402
    evaluate_series,
    index_to_month,
    month_index,
    parse_fred_payload,
    parse_staging_monthly_series,
    parse_worldbank_by_country,
    parse_worldbank_payload,
    resample_to_monthly,
)

RAW_ROOT = REPO_ROOT / "data" / "raw"
SPEC_PATH = REPO_ROOT / "analysis" / "specs" / "quality.yml"
OUT_ROOT = REPO_ROOT / "registry" / "quality"

# Sources whose payload carries several countries, keyed by source name.
MULTI_COUNTRY_SOURCES = {"worldbank_donors"}


def load_spec() -> dict:
    spec = yaml.safe_load(SPEC_PATH.read_text(encoding="utf-8"))
    start = spec["study_window"]["start"]
    year, _, tail = str(start).partition("-")
    spec["_study_start"] = month_index(int(year), int(tail.split("-")[0]) if tail else 1)
    return spec


def vintages_for(source_dir: Path) -> list[str]:
    return sorted(p.name for p in source_dir.iterdir() if p.is_dir())


def read_payloads(vintage_dir: Path, page_files: list[str]) -> list[object]:
    return [json.loads((REPO_ROOT / page).read_text(encoding="utf-8")) for page in page_files]


def report_date(vintage: str) -> str:
    """The date part of a source vintage label, so the report keeps a date as its own label.

    A raw vintage needs a label that distinguishes a same-day re-landing (X-07), so it may read
    ``2026-10-16-correction``. The Stage 3 *report* is a different object with a different convention:
    its label is a date, and consumers select it by date — ``analysis/R/02_diagnostics.R`` globs
    ``^[0-9]{4}-[0-9]{2}-[0-9]{2}$`` to find the vintage to describe. Inheriting the raw label made that
    glob skip the newest report **silently** and describe the older one instead, which is how a Stage 5
    re-run came to read a superseded gate report (C-44). The exact labels still travel per source in
    ``source_vintages``, so nothing is hidden by keeping the report's own label a date.
    """
    parts = vintage.split("-")
    if len(parts) >= 3 and all(part.isdigit() for part in parts[:3]):
        return "-".join(parts[:3])
    return vintage


def publisher_precedence(cfg: dict) -> list[str]:
    """The publisher order the base applies, read from the spec that declares it.

    Restating ``[oagf, nbs]`` here would be a second copy of a decision, and the copy the gate used
    could silently diverge from the copy Stage 4 used — so the gate reads the same declaration.
    """
    rule = cfg.get("publisher_rule") or {}
    if not rule:
        return []
    document = yaml.safe_load((REPO_ROOT / rule["spec"]).read_text(encoding="utf-8"))
    node = document
    for key in rule["path"]:
        node = node[key]
    return [node["primary"], node["fallback"]]


def gate_document_source(name: str, cfg: dict, spec: dict, failures: list[str]) -> tuple[list[dict], str | None]:
    """Gate a source whose series only exists in its parsed artifact (a PDF/XLSX source).

    Returns one row per gated series plus the raw vintage the artifact was parsed from. The national
    aggregate is gated alongside the per-unit series: it is the series a national design would read, and
    a panel whose parts pass while its total is broken is not a gated dose.
    """
    staging_path = REPO_ROOT / cfg["staging"]
    if not staging_path.exists():
        failures.append(
            f"{name}: no parsed artifact at {cfg['staging']} — a document source cannot be gated from "
            "its payload, so this source has no gate result"
        )
        return [], None

    # A parsed artifact may carry several metrics in one long table (`item` -> one series per item).
    # `value_items` names them; `value_item`/`metric_id` is the single-series form FAAC uses, kept
    # because a 174-document source with one dose should not have to spell out a one-entry map.
    value_items = cfg.get("value_items") or {cfg["value_item"]: cfg["metric_id"]}

    with staging_path.open(newline="", encoding="utf-8") as handle:
        artifact_rows = list(csv.DictReader(handle))
    rows = [row for row in artifact_rows if row.get("item") in value_items]
    if not rows:
        failures.append(
            f"{name}: the parsed artifact carries none of the declared items {sorted(value_items)}"
        )
        return [], None

    vintages = sorted({row["vintage"] for row in rows})
    if len(vintages) != 1:
        failures.append(
            f"{name}: the parsed artifact mixes vintages {vintages} — one gate result per artifact "
            "requires one vintage"
        )
    vintage = vintages[-1]

    spike_spec = spec.get("spike_measure") or {}
    out: list[dict] = []

    for item, metric_id in value_items.items():
        item_rows = [row for row in artifact_rows if row.get("item") == item]
        if not item_rows:
            failures.append(f"{name}: the parsed artifact carries no '{item}' rows")
            continue

        series = parse_staging_monthly_series(
            item_rows,
            key_field=cfg["series_key"],
            value_field=cfg["value_field"],
            publisher_field=cfg.get("publisher_field"),
            publisher_precedence=publisher_precedence(cfg),
        )

        # The national aggregate, summed over the same selected values the panel carries. A month is
        # present only if every unit is: a partial sum is not a national total.
        n_units = len(series)
        by_month: dict[int, list[float]] = {}
        for points in series.values():
            for point in points:
                by_month.setdefault(point.start_index, []).append(point.value)
        national = parse_staging_monthly_series(
            [
                {
                    cfg["series_key"]: cfg["national_scope"],
                    "period_month": index_to_month(index),
                    cfg["value_field"]: str(sum(values)),
                    "item": item,
                }
                for index, values in by_month.items()
                if len(values) == n_units
            ],
            key_field=cfg["series_key"],
            value_field=cfg["value_field"],
        )
        series.update(national)

        measure = (
            "points"
            if metric_id in (spike_spec.get("percentage_point_series") or [])
            else spike_spec.get("default", "relative")
        )
        adjudications = [
            a for a in spec.get("spike_adjudications") or [] if a["metric_id"] == metric_id
        ]
        breaks = next(
            (b["breaks"] for b in spec.get("definition_breaks") or [] if b["metric_id"] == metric_id),
            [],
        )
        imputation = [i for i in spec.get("imputation") or [] if i["metric_id"] == metric_id]

        for scope in sorted(series, key=lambda s: (s == cfg.get("national_scope"), s)):
            points = series[scope]
            result = evaluate_series(
                points,
                grain_period=spec["grains"][name]["period"],
                study_start=spec["_study_start"],
                study_end=_study_end(points, spec),
                thresholds=spec["thresholds"],
                breaks=breaks,
                declared_imputation=imputation,
                previous_points=None,
                adjudications=adjudications,
                spike_measure=measure,
            )
            # A revision gate that never compares is reported as such rather than as zero revisions. The
            # parsed artifact is overwritten by each parse, so the previous vintage's parse no longer exists
            # to compare against — the omission is named instead of looking like a clean comparison.
            result["gates"]["revision"]["note"] = (
                "the parsed artifact holds one vintage; an earlier parse is not retained, so this gate "
                "cannot compare the correction vintage against the original (the raw payloads for both are "
                "on disk — see docs/decisions.md C-39/C-42)"
            )
            out.append(
                {
                    "source": name,
                    "vintage": vintage,
                    "metric_id": metric_id,
                    "dataset_id": f"{vintage}:{item}",
                    "value_item": item,
                    "scope": scope,
                    "resample": None,
                    **result,
                }
            )
    return out, vintage


def gate_source(
    source: str, vintage: str, spec: dict, failures: list[str]
) -> list[dict]:
    """Gate every series in one source's vintage. Returns one row per gated series."""
    vintage_dir = RAW_ROOT / source / vintage
    manifest_path = vintage_dir / "manifest.json"
    if not manifest_path.exists():
        failures.append(f"{source}/{vintage}: no manifest")
        return []
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    previous_manifest = None
    earlier = [v for v in vintages_for(RAW_ROOT / source) if v < vintage]
    if earlier:
        prior_path = RAW_ROOT / source / earlier[-1] / "manifest.json"
        if prior_path.exists():
            previous_manifest = json.loads(prior_path.read_text(encoding="utf-8"))

    rows: list[dict] = []
    for retrieval in manifest["retrievals"]:
        metric_id = retrieval["metric_id"]
        dataset_id = retrieval["dataset_id"]
        try:
            payloads = read_payloads(vintage_dir, retrieval["page_files"])
        except (OSError, json.JSONDecodeError) as exc:
            failures.append(f"{source}:{metric_id}: unreadable payload ({exc})")
            continue

        # ---- resolve the series, its grain and its resample rule -------------------------
        rule = next(
            (
                r
                for r in spec.get("resample_rules") or []
                if r["source"] == source and r["dataset_id"] == dataset_id
            ),
            None,
        )
        grain = spec["grains"][source]
        resampled_note = None

        if source == "fred":
            observations: list[tuple] = []
            for payload in payloads:
                observations.extend(parse_fred_payload(payload))
            if rule:
                points = resample_to_monthly(observations, rule["rule"])
                grain_period = rule["to"]
                resampled_note = {
                    "from": spec["grains"][source]["period"],
                    "rule": rule["rule"],
                    "declared": rule["declared"],
                    "n_source_observations": len(observations),
                }
            else:
                failures.append(
                    f"{source}:{metric_id}: no resample rule declared and the series is not gateable "
                    "at its native grain"
                )
                continue
        elif source in MULTI_COUNTRY_SOURCES:
            points = None
            grain_period = grain["period"]
        else:
            points = []
            for payload in payloads:
                points.extend(parse_worldbank_payload(payload))
            grain_period = grain["period"]

        # ---- previous vintage, matched on the same key -----------------------------------
        previous_rows = None
        if previous_manifest is not None and source not in MULTI_COUNTRY_SOURCES:
            prior = next(
                (r for r in previous_manifest["retrievals"] if r["dataset_id"] == dataset_id), None
            )
            if prior is not None:
                try:
                    prior_payloads = read_payloads(
                        RAW_ROOT / source / previous_manifest["vintage_date"], prior["page_files"]
                    )
                    previous_rows = []
                    for payload in prior_payloads:
                        previous_rows.extend(
                            parse_fred_payload(payload)
                            if source == "fred"
                            else parse_worldbank_payload(payload)
                        )
                    if source == "fred" and rule:
                        previous_rows = resample_to_monthly(previous_rows, rule["rule"])
                except (OSError, json.JSONDecodeError):
                    previous_rows = None

        # Which measure of "a spike" applies to this series type (quality.yml `spike_measure`).
        spike_spec = spec.get("spike_measure") or {}
        measure = (
            "points"
            if metric_id in (spike_spec.get("percentage_point_series") or [])
            else spike_spec.get("default", "relative")
        )
        adjudications = [a for a in spec.get("spike_adjudications") or [] if a["metric_id"] == metric_id]
        breaks = next(
            (b["breaks"] for b in spec.get("definition_breaks") or [] if b["metric_id"] == metric_id),
            [],
        )
        imputation = [
            i for i in spec.get("imputation") or [] if i["metric_id"] == metric_id
        ]

        if source in MULTI_COUNTRY_SOURCES:
            panel = {}
            for payload in payloads:
                for code, series_points in parse_worldbank_by_country(payload).items():
                    panel.setdefault(code, []).extend(series_points)
            for code in sorted(panel):
                result = evaluate_series(
                    sorted(panel[code], key=lambda p: p.start_index),
                    grain_period=grain_period,
                    study_start=spec["_study_start"],
                    study_end=_study_end(panel[code], spec),
                    thresholds=spec["thresholds"],
                    breaks=breaks,
                    declared_imputation=imputation,
                    previous_points=None,
                    adjudications=adjudications,
                    spike_measure=measure,
                )
                rows.append(
                    {
                        "source": source,
                        "vintage": vintage,
                        "metric_id": metric_id,
                        "dataset_id": dataset_id,
                        "scope": code,
                        "resample": None,
                        **result,
                    }
                )
            continue

        result = evaluate_series(
            points,
            grain_period=grain_period,
            study_start=spec["_study_start"],
            study_end=_study_end(points, spec),
            thresholds=spec["thresholds"],
            breaks=breaks,
            declared_imputation=imputation,
            previous_points=previous_rows,
            adjudications=adjudications,
            spike_measure=measure,
        )
        rows.append(
            {
                "source": source,
                "vintage": vintage,
                "metric_id": metric_id,
                "dataset_id": dataset_id,
                "scope": "NGA" if source == "worldbank" else None,
                "resample": resampled_note,
                **result,
            }
        )
    return rows


def _study_end(points: list, spec: dict) -> int:
    """The window's end: the declared end if set, otherwise the last observed period."""
    declared = spec["study_window"].get("end")
    if isinstance(declared, str) and declared:
        year, _, tail = declared.partition("-")
        month = int(tail.split("-")[0]) if tail else 12
        return month_index(int(year), month)
    return max((p.end_index for p in points), default=spec["_study_start"])


def money(x) -> str:
    return "—" if x is None else f"{x:,.4g}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Stage 3 — quality gates for every landed series.")
    parser.add_argument("--vintage", default=None, help="label the report (default: latest vintage)")
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])

    if not SPEC_PATH.exists():
        print(f"REFUSED  no gate specification at {SPEC_PATH.relative_to(REPO_ROOT)}")
        return 1
    if not RAW_ROOT.exists():
        print(f"REFUSED  no raw data at {RAW_ROOT.relative_to(REPO_ROOT)}")
        return 1

    spec = load_spec()
    document_sources = spec.get("document_sources") or {}
    sources = sorted(p.name for p in RAW_ROOT.iterdir() if p.is_dir())
    if not sources:
        print("REFUSED  no sources under data/raw")
        return 1

    failures: list[str] = []
    rows: list[dict] = []
    source_vintages: dict[str, str] = {}

    for source in sources:
        vintages = vintages_for(RAW_ROOT / source)
        if not vintages:
            failures.append(f"{source}: no vintages")
            continue
        vintage = vintages[-1]
        source_vintages[source] = vintage
        # A document source's page files are PDFs or spreadsheets, so the payload walk below would die
        # on a decode instead of gating the series. It is gated from its parsed artifact instead.
        if source in document_sources:
            continue
        rows.extend(gate_source(source, vintage, spec, failures))

    for name, cfg in document_sources.items():
        if name not in source_vintages:
            failures.append(
                f"{name}: declared as a document source but has no vintage under data/raw — the "
                "declaration has drifted from the raw layer"
            )
            continue
        document_rows, document_vintage = gate_document_source(name, cfg, spec, failures)
        rows.extend(document_rows)
        if document_vintage:
            source_vintages[name] = document_vintage

    report_vintage = args.vintage or max(report_date(v) for v in source_vintages.values())
    out_dir = OUT_ROOT / report_vintage
    out_dir.mkdir(parents=True, exist_ok=True)

    counts = {"ok": 0, "flagged": 0, "empty": 0}
    for row in rows:
        counts[row["status"]] = counts.get(row["status"], 0) + 1

    # Exit criterion, enforced rather than asserted: every series the manifests declare must have a
    # row here. A silent omission is how "no series reaches Stage 4 without a gate result" quietly
    # stops being true.
    expected = 0
    for source, vintage in source_vintages.items():
        if source in document_sources:
            # One gate row per parsed series (units + the national aggregate), not one per document:
            # 174 documents describing 114 months are not 174 series. Every declared item must cover
            # the *same* set of scopes — an item whose scope set differs is a parse that lost a unit,
            # which is exactly the silent hole this check exists for.
            scopes_by_item: dict[str, set[str]] = {}
            for row in rows:
                if row["source"] == source:
                    scopes_by_item.setdefault(row["metric_id"], set()).add(row["scope"])
            scope_sets = {frozenset(v) for v in scopes_by_item.values()}
            if len(scope_sets) > 1:
                failures.append(
                    f"{source}: its items cover different scope sets "
                    f"({ {k: len(v) for k, v in scopes_by_item.items()} }) — an item lost a unit"
                )
            expected += sum(len(v) for v in scopes_by_item.values())
            continue
        manifest = json.loads((RAW_ROOT / source / vintage / "manifest.json").read_text(encoding="utf-8"))
        for retrieval in manifest["retrievals"]:
            expected += 1
        if source in MULTI_COUNTRY_SOURCES:
            # One retrieval fans out into one series per country in *that retrieval*. The first version of
            # this line multiplied the pool-wide country count by the number of retrievals, which is only
            # the same number while every retrieval covers every country — true for one request per
            # predictor and false the moment the pool is landed in chunks (2026-10-18: 99 candidates in 5
            # chunks, so the old formula expected 495 series per predictor and the real answer is 99). The
            # count is therefore read from each retrieval's own payloads, which is also what makes an
            # accidental overlap between chunks visible as a mismatch rather than absorbed by a heuristic.
            expected -= len(manifest["retrievals"])
            for retrieval in manifest["retrievals"]:
                countries: set[str] = set()
                for payload in read_payloads(RAW_ROOT / source / vintage, retrieval["page_files"]):
                    countries.update(parse_worldbank_by_country(payload))
                expected += len(countries)
    reported = len({(r["source"], r["metric_id"], r["scope"]) for r in rows})
    if reported != expected:
        failures.append(
            f"coverage of the raw layer: {expected} series declared in the manifests, "
            f"{reported} gated — the exit criterion 'no series reaches Stage 4 without a gate "
            "result' is not met"
        )

    report = {
        "stage": 3,
        "layer": "validation and quality gates",
        "report_vintage": report_vintage,
        "source_vintages": source_vintages,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "generator": "ingestion/flows/check_quality.py",
        "spec": "analysis/specs/quality.yml",
        "document_sources": sorted(document_sources),
        "study_window": spec["study_window"],
        "thresholds": spec["thresholds"],
        "counts": counts,
        "n_series_gated": reported,
        "failures": failures,
        "series": rows,
    }
    (out_dir / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (out_dir / "report.md").write_text(render_markdown(report), encoding="utf-8")

    print(f"report vintage: {report_vintage}")
    print("source vintages: " + ", ".join(f"{k}={v}" for k, v in source_vintages.items()))
    print(f"study window: {spec['study_window']['start']} -> open")
    print()
    print(f"{'source':<18}{'metric':<20}{'scope':<6}{'grain':<9}{'n':>5}  {'span':<17}{'status':<9}flags")
    print("-" * 104)
    for row in sorted(rows, key=lambda r: (r["source"], r["metric_id"], r["scope"] or "")):
        flags = []
        if row["gates"]["gap"]["tripped"]:
            flags.append(f"GAP({row['gates']['gap']['max_gap_months']}m)")
        if row["gates"]["spike"]["tripped"]:
            flags.append(f"SPIKE({row['gates']['spike']['n_spikes']},{row['gates']['spike']['measure']})")
        if row["gates"]["definition_drift"]["n_breaks_in_window"]:
            flags.append(f"BREAK({row['gates']['definition_drift']['n_breaks_in_window']})")
        coverage = row["gates"]["coverage"]
        span = f"{coverage['first_observed']}..{coverage['last_observed']}"
        print(
            f"{row['source']:<18}{row['metric_id']:<20}{(row['scope'] or '-'):<6}"
            f"{row['grain_period']:<9}{coverage['n_observed']:>5}  {span:<17}"
            f"{row['status']:<9}{' '.join(flags)}"
        )

    print()
    print(f"gated: {reported} series   ok={counts['ok']} flagged={counts['flagged']} empty={counts['empty']}")
    print(f"report: {(out_dir / 'report.json').relative_to(REPO_ROOT)}")
    print(f"page:   {(out_dir / 'report.md').relative_to(REPO_ROOT)}")

    if failures:
        print()
        print(f"FAILED — {len(failures)} problem(s):")
        for problem in failures:
            print(f"  - {problem}")
        return 1
    return 0


def render_markdown(report: dict) -> str:
    """The human-readable page. Written from the same object the JSON is, so they cannot diverge."""
    thresholds = ", ".join(f"{k}={v}" for k, v in report["thresholds"].items())
    sources = ", ".join(f"`{k}` @ {v}" for k, v in report["source_vintages"].items())
    counts = report["counts"]
    provenance = (
        "Stage 3 gate results for every series in the raw layer. Generated "
        f"{report['generated_at']} by `{report['generator']}` from `{report['spec']}`."
    )
    window_line = (
        f"**Study window:** {report['study_window']['start']} → open. "
        "Gates for gaps and spikes are evaluated *inside* this window only."
    )
    counts_line = (
        f"**Series gated:** {report['n_series_gated']} — ok {counts['ok']}, "
        f"flagged {counts['flagged']}, empty {counts['empty']}."
    )
    lines = [
        f"# Vintage quality report — {report['report_vintage']}",
        "",
        provenance,
        "",
        window_line,
        "",
        f"**Thresholds:** {thresholds}.",
        "",
        f"**Sources:** {sources}.",
        "",
        counts_line,
        "",
    ]

    flagged = [r for r in report["series"] if r["status"] == "flagged"]
    empty = [r for r in report["series"] if r["status"] == "empty"]
    document_sources = set(report.get("document_sources") or [])
    # Payload sources are listed series by series; document sources are aggregated by period, because
    # a monthly panel of 36 units fires the same distribution-cycle month in all 36 and 350 identical
    # table rows would bury the 28 flags that are actually per-series.
    payload_flagged = [r for r in flagged if r["source"] not in document_sources]
    document_flagged = [r for r in flagged if r["source"] in document_sources]

    lines += ["## Flagged series", ""]
    if not payload_flagged:
        lines += ["None.", ""]
    else:
        lines += [
            "| Source | Metric | Scope | Grain | Gate | Detail |",
            "|---|---|---|---|---|---|",
        ]
        for row in payload_flagged:
            gates = row["gates"]
            if gates["gap"]["tripped"]:
                lines.append(
                    f"| {row['source']} | `{row['metric_id']}` | {row['scope'] or '—'} | "
                    f"{row['grain_period']} | gap | longest hole "
                    f"**{gates['gap']['max_gap_months']} months** across "
                    f"{gates['gap']['n_gap_runs']} run(s) |"
                )
            for spike_event in gates["spike"]["spikes"]:
                verdict = next(
                    (
                        a["verdict"]
                        for a in gates["spike"]["adjudicated"]
                        if a["to"] == spike_event["to"]
                    ),
                    "**UNADJUDICATED**",
                )
                size = (
                    f"{spike_event['change_pct']:+.1f}%"
                    if "change_pct" in spike_event
                    else f"{spike_event['change_points']:+.2f} points"
                )
                lines.append(
                    f"| {row['source']} | `{row['metric_id']}` | {row['scope'] or '—'} | "
                    f"{row['grain_period']} | spike | {spike_event['from']} → "
                    f"{spike_event['to']}: **{size}** — {verdict} |"
                )
        lines.append("")

    lines += ["### Document sources, aggregated by period", ""]
    if not document_flagged:
        lines += ["None.", ""]
    else:
        totals: dict[tuple[str, str], int] = {}
        for row in report["series"]:
            if row["source"] in document_sources:
                totals[(row["source"], row["metric_id"])] = (
                    totals.get((row["source"], row["metric_id"]), 0) + 1
                )
        grouped: dict[tuple[str, str, str], dict] = {}
        for row in document_flagged:
            for event in row["gates"]["spike"]["spikes"]:
                key = (row["source"], row["metric_id"], event["to"])
                entry = grouped.setdefault(key, {"n": 0, "max": 0.0, "measure": row["spike_measure"]})
                entry["n"] += 1
                size = event.get("change_pct")
                if size is None:
                    size = event.get("change_points", 0.0)
                entry["max"] = max(entry["max"], abs(size))
        lines += [
            "| Source | Metric | Period | Gate | Series flagged | Largest move |",
            "|---|---|---|---|---|---|",
        ]
        for (source, metric_id, period), entry in sorted(grouped.items()):
            total = totals[(source, metric_id)]
            unit = "%" if entry["measure"] == "relative" else " points"
            lines.append(
                f"| {source} | `{metric_id}` | {period} | spike | "
                f"{entry['n']} of {total} | {entry['max']:.1f}{unit} |"
            )
        for row in document_flagged:
            if row["gates"]["gap"]["tripped"]:
                lines.append(
                    f"| {row['source']} | `{row['metric_id']}` | {row['scope']} | gap | "
                    f"longest hole **{row['gates']['gap']['max_gap_months']} months** | — |"
                )
        lines.append("")
        lines.append(
            "A month flagged in every unit is a movement of the distribution, not a per-unit extraction "
            "error: the source documents are reconciled against their own published Total row by "
            "`tests/verify_faac.py`, so a swing shared by all 36 states is what the documents say. "
            "These flags are review prompts and are **not** adjudicated in the spec, because a verdict "
            "without evidence would be worse than the prompt."
        )
        lines.append("")

    lines += ["## Empty series (nothing inside the study window)", ""]
    if not empty:
        lines += ["None.", ""]
    else:
        for row in empty:
            lines.append(f"- `{row['source']}` / `{row['metric_id']}` / {row['scope'] or '—'}")
        lines.append("")

    lines += ["## Definition breaks carried into the window", ""]
    any_breaks = False
    for row in report["series"]:
        for break_ in row["gates"]["definition_drift"]["breaks"]:
            any_breaks = True
            lines.append(
                f"- `{row['metric_id']}` — {break_['date']} · **{break_['label']}**: "
                f"{' '.join(break_['note'].split())}"
            )
    if not any_breaks:
        lines.append("None.")
    lines.append("")

    lines += [
        "## What a flag means",
        "",
        "A flag is a review prompt, not a verdict. A gap flag means the series has a hole the models",
        "must not silently interpolate across. A spike flag means the move is either a documented event",
        "or a probable data error, and `spike_adjudications` in `analysis/specs/quality.yml` records",
        "which — an unadjudicated flag is printed as such rather than dropped.",
        "",
    ]
    if report["failures"]:
        lines += ["## Failures", ""] + [f"- {f}" for f in report["failures"]] + [""]
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
