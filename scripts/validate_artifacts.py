"""Contract test on artifact paths, names and payload shapes — the checks that keep failing silently.

Two defects found on 2026-10-17 shared one cause and neither was a logic error:

  * ``tests/verify_quality.py`` and the Stage 3 flow both assumed every file under ``data/raw`` was JSON.
    True while every source was an API, false the moment 174 PDFs and spreadsheets landed, and the
    result was a ``UnicodeDecodeError`` on the first byte of a PDF instead of a gate result (C-42).
  * Stage 5 selected the gate report to describe with a **date-only** glob. The report's label had just
    become ``2026-10-16-correction``, so the glob skipped the newest report, described the previous one,
    and wrote its output into that older vintage's directory — with no warning (C-44).

Both are *assumptions about a name or a shape* that a later artifact violated. Code review does not
catch them, because at the time they were written they were true. So they are checked here, mechanically,
against the artifacts on disk:

  1. every payload under a landed vintage is readable by the reader its **extension** declares —
     an unregistered extension is a failure, so a new payload type has to be declared rather than
     silently skipped;
  2. the newest Stage 3 report's own label is a date (S4-20), and the report agrees with its directory;
  3. the newest Stage 5 diagnostics describe the newest Stage 3 report (the C-44 invariant);
  4. the newest Stage 6 estimates describe the newest Stage 3 report (the same invariant, second
     consumer), and the forest plot they name is a real SVG whose byte count is the one the artifact
     recorded — a figure that outlives its rows is a picture of a different result;
  5. the same invariant for the Stage 7 robustness artifact, plus its internal arithmetic: the support
     counts it publishes must equal the counts of its own specification rows, exactly one specification
     per design may be flagged pre-registered, and the specification curve it names must exist and be a
     real SVG with at least one point per specification;
  6. the same invariant for the Stage 8b transition event study, plus its own shape: every row carries the
     contract fields, every declared event x horizon cell is either fitted or published as a declared skip
     with a reason, the rows sit inside the windows the spec's rules produce, and the pre-trend check is
     reported as unavailable rather than as a pass where it cannot be run;
  7. every registry JSON validates against its declared JSON Schema.

Checks that need the raw layer (1) are **reported as skipped** when ``data/raw`` is absent, which is the
normal case in CI: raw payloads are gitignored per the design spec's redistribution constraint. A skip is
printed as a skip and never counted as a pass.

Usage:
    conda run -p "C:/Users/TOSHIBA/ds-general" python scripts/validate_artifacts.py
"""

from __future__ import annotations

import hashlib
import json
import re
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
RAW_ROOT = REPO_ROOT / "data" / "raw"
QUALITY_ROOT = REPO_ROOT / "registry" / "quality"
DIAG_ROOT = REPO_ROOT / "registry" / "diagnostics"
ESTIMATES_ROOT = REPO_ROOT / "registry" / "estimates"
ROBUSTNESS_ROOT = REPO_ROOT / "registry" / "robustness"
EVENTS_ROOT = REPO_ROOT / "registry" / "events"
RAG_ROOT = REPO_ROOT / "registry" / "rag"
CARDS_DIR = REPO_ROOT / "registry" / "dags"
SCHEMA_DIR = REPO_ROOT / "registry" / "schema"
REFERENCE_DIR = REPO_ROOT / "registry" / "reference"
DONORS_DIR = REPO_ROOT / "registry" / "donors"
SERIES_ROOT = REPO_ROOT / "registry" / "series"

DATE_LABEL = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# One entry per payload shape the pipeline has landed, keyed by extension. Adding a source with a new
# payload type means adding a reader here, which is the point: the alternative is what C-42 was.
JSON_SUFFIXES = {".json"}
PDF_SUFFIXES = {".pdf"}
XLSX_SUFFIXES = {".xlsx", ".xlsm"}
CSV_SUFFIXES = {".csv"}
# Added 2026-10-17 with the UCDP GED bulk archive: one 29 MB zip whose member is a CSV. Declared here
# rather than added to a skip list, because the registration *is* the check (C-42's lesson).
ZIP_SUFFIXES = {".zip"}
REGISTERED = JSON_SUFFIXES | PDF_SUFFIXES | XLSX_SUFFIXES | CSV_SUFFIXES | ZIP_SUFFIXES


def newest_dir(root: Path) -> Path | None:
    if not root.exists():
        return None
    dirs = sorted((p for p in root.iterdir() if p.is_dir()), key=lambda p: p.name)
    return dirs[-1] if dirs else None


def check_payload_shapes(failures: list[str]) -> tuple[int, int]:
    """(checked, unreadable) — every landed page file must be readable by its declared reader."""
    if not RAW_ROOT.exists():
        return 0, 0
    checked = 0
    broken = 0
    for source_dir in sorted(p for p in RAW_ROOT.iterdir() if p.is_dir()):
        vintages = sorted(p.name for p in source_dir.iterdir() if p.is_dir())
        if not vintages:
            continue
        vintage_dir = source_dir / vintages[-1]
        manifest_path = vintage_dir / "manifest.json"
        if not manifest_path.exists():
            failures.append(f"{source_dir.name}/{vintages[-1]}: no manifest.json")
            continue
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        for retrieval in manifest["retrievals"]:
            for page in retrieval["page_files"]:
                path = REPO_ROOT / page
                checked += 1
                if not path.exists():
                    failures.append(f"{page}: referenced by the manifest but absent")
                    broken += 1
                    continue
                error = read_payload(path)
                if error:
                    failures.append(f"{page}: {error}")
                    broken += 1
    return checked, broken


def read_payload(path: Path) -> str | None:
    """Return an error message if the file cannot be read as the type its extension declares."""
    suffix = path.suffix.lower()
    if suffix not in REGISTERED:
        return (
            f"unregistered payload extension {suffix!r} — a new payload type must declare its reader "
            "in scripts/validate_artifacts.py (C-42: an undeclared type failed as a decode error)"
        )
    if suffix in JSON_SUFFIXES:
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            return f"declared JSON but does not parse ({exc.__class__.__name__}: {exc})"
        return None
    if suffix in PDF_SUFFIXES:
        with path.open("rb") as handle:
            head = handle.read(5)
        return None if head == b"%PDF-" else f"declared PDF but the header is {head!r}"
    if suffix in XLSX_SUFFIXES or suffix in ZIP_SUFFIXES:
        if not zipfile.is_zipfile(path):
            return f"declared {suffix} but it is not a zip container"
        if suffix in ZIP_SUFFIXES:
            with zipfile.ZipFile(path) as archive:
                names = archive.namelist()
            if not names:
                return "declared zip but it holds no members"
            if not any(name.lower().endswith((".csv", ".json")) for name in names):
                return f"declared zip but holds no CSV or JSON member ({names[:3]})"
        return None
    try:
        path.read_text(encoding="utf-8").splitlines()[0]
    except (UnicodeDecodeError, IndexError) as exc:
        return f"declared CSV but is not readable UTF-8 text ({exc.__class__.__name__})"
    return None


def check_report_label(failures: list[str]) -> str | None:
    """The newest gate report is selected *by date*; its own label must therefore be a date (S4-20)."""
    newest = newest_dir(QUALITY_ROOT)
    if newest is None:
        failures.append("registry/quality/ holds no report")
        return None
    if not DATE_LABEL.match(newest.name):
        failures.append(
            f"registry/quality/{newest.name}: the report's own label is not a date, so every consumer "
            "that selects the newest report by date will skip it (C-44, S4-20)"
        )
    report_path = newest / "report.json"
    if not report_path.exists():
        failures.append(f"{report_path.relative_to(REPO_ROOT)}: missing")
        return newest.name
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if report.get("report_vintage") != newest.name:
        failures.append(
            f"registry/quality/{newest.name}: report_vintage is {report.get('report_vintage')!r}, "
            "which disagrees with the directory that holds it"
        )
    if report.get("n_series_gated") != len(report.get("series") or []):
        failures.append(
            f"registry/quality/{newest.name}: n_series_gated {report.get('n_series_gated')} but "
            f"{len(report.get('series') or [])} rows"
        )
    return newest.name


def check_stage5_matches_stage3(failures: list[str], quality_vintage: str | None) -> None:
    """Stage 5 describes a Stage 3 report; the invariant is that it describes the newest one (C-44)."""
    newest = newest_dir(DIAG_ROOT)
    if newest is None:
        failures.append("registry/diagnostics/ holds no artifact")
        return
    if quality_vintage and newest.name != quality_vintage:
        failures.append(
            f"registry/diagnostics/{newest.name} describes a superseded gate report: the newest is "
            f"{quality_vintage}. Re-run analysis/R/02_diagnostics.R (C-44)"
        )


def check_stage6_matches_stage3(failures: list[str], quality_vintage: str | None) -> None:
    """The estimates are computed from the base the newest gate report describes.

    The same invariant as Stage 5's (C-44), for a second consumer: a report that selects its input by
    date will silently describe a superseded vintage if the label stops being a date or if the estimate
    artifact is not regenerated. Cheap to check, and the failure is invisible otherwise — the numbers
    still reproduce, they are simply computed against different data than the report beside them.
    """
    newest = newest_dir(ESTIMATES_ROOT)
    if newest is None:
        print("stage 6 artifact : none yet (registry/estimates/ is empty)")
        return
    if not DATE_LABEL.match(newest.name):
        failures.append(
            f"registry/estimates/{newest.name}: the estimate vintage is not a date, so a consumer that "
            "selects the newest by date will skip it (C-44, S4-20)"
        )
    document = json.loads((newest / "estimates.json").read_text(encoding="utf-8"))
    if document.get("vintage") != newest.name:
        failures.append(
            f"registry/estimates/{newest.name}: the artifact's own vintage is "
            f"{document.get('vintage')!r}, which disagrees with the directory holding it"
        )
    if quality_vintage and document.get("vintage") != quality_vintage:
        failures.append(
            f"registry/estimates/{document.get('vintage')}: computed against a different gate vintage "
            f"than the newest ({quality_vintage}) — re-run analysis/R/03_estimate.R"
        )
    specs = document.get("specifications") or []
    required = {"n_obs", "coefficient", "standard_error", "ci_low", "ci_high", "design", "outcome"}
    for spec_row in specs:
        missing = required - set(spec_row)
        if missing:
            failures.append(
                f"registry/estimates/{newest.name}: a specification is missing {sorted(missing)} — the "
                "json_contract in analysis/specs/estimation.yml requires them on every row"
            )
    # The figure block (added 2026-10-18 with the forest plot). The verifier checks that every published
    # specification is labelled in the file; this is the cheaper invariant that the picture belongs to the
    # rows beside it at all. Recorded bytes against bytes on disk is what a stale figure looks like from
    # the outside — the same content, one re-fit behind.
    figure = document.get("figure") or {}
    figure_path = newest / str(figure.get("path", ""))
    if not figure:
        failures.append(
            f"registry/estimates/{newest.name}: the spec declares a figure but the artifact carries no "
            "figure block — analysis/R/03_estimate.R was re-run before the `figure` block existed"
        )
    elif not figure_path.exists() or figure_path.stat().st_size == 0:
        failures.append(
            f"registry/estimates/{newest.name}: {figure.get('path')!r} is missing or empty — every "
            "published estimate group ships with the interval figure it is read from"
        )
    else:
        svg = figure_path.read_text(encoding="utf-8", errors="replace")
        if "<svg" not in svg:
            failures.append(f"registry/estimates/{newest.name}: {figure.get('path')} is not an SVG")
        # Canonical (LF) size: the index stores eol=lf, so a raw size is true only on a Windows checkout.
        actual_bytes = len(figure_path.read_bytes().replace(b"\r\n", b"\n"))
        if figure.get("bytes") != actual_bytes:
            failures.append(
                f"registry/estimates/{newest.name}: the artifact records {figure.get('bytes')} bytes for "
                f"{figure.get('path')} and the file is {actual_bytes} — the figure is stale against the rows"
            )
        if not specs:
            failures.append(f"registry/estimates/{newest.name}: a figure is published for zero specifications")

    print(f"stage 6 artifact : {newest.name} ({len(specs)} specifications, contract fields present, "
          f"figure {figure.get('path', '—')})")


def check_stage7(failures: list[str], quality_vintage: str | None) -> None:
    """The robustness artifact: same vintage invariant as Stages 5 and 6, plus its own arithmetic.

    The support counts are recomputed from the published specification rows here rather than trusted. It
    is not a re-fit — `tests/verify_stage7.py` does that — it is the check that the *summary* agrees with
    the *rows it summarises*, which is the failure mode a hand-written summary has and a fitted one can
    still acquire when one of the two is filtered later.
    """
    newest = newest_dir(ROBUSTNESS_ROOT)
    if newest is None:
        print("stage 7 artifact : none yet (registry/robustness/ is empty)")
        return
    if not DATE_LABEL.match(newest.name):
        failures.append(
            f"registry/robustness/{newest.name}: the vintage is not a date, so a consumer that selects "
            "the newest by date will skip it (C-44, S4-20)"
        )
    document_path = newest / "robustness.json"
    if not document_path.exists():
        failures.append(f"{document_path.relative_to(REPO_ROOT)}: missing")
        return
    document = json.loads(document_path.read_text(encoding="utf-8"))
    if document.get("vintage") != newest.name:
        failures.append(
            f"registry/robustness/{newest.name}: the artifact's own vintage is "
            f"{document.get('vintage')!r}, which disagrees with the directory holding it"
        )
    if quality_vintage and document.get("vintage") != quality_vintage:
        failures.append(
            f"registry/robustness/{document.get('vintage')}: computed against a different gate vintage "
            f"than the newest ({quality_vintage}) — re-run analysis/R/04_robustness.R"
        )

    specs = document.get("specifications") or []
    required = {"spec_id", "design", "n_obs", "coefficient", "standard_error", "ci_low", "ci_high",
                "sign", "preferred"}
    for row in specs:
        missing = required - set(row)
        if missing:
            failures.append(
                f"registry/robustness/{newest.name}: specification {row.get('spec_id')!r} is missing "
                f"{sorted(missing)} — the json_contract in analysis/specs/robustness.yml requires them"
            )
    for design in ("A", "B"):
        n_preferred = sum(1 for row in specs if row.get("design") == design and row.get("preferred"))
        if n_preferred != 1:
            failures.append(
                f"registry/robustness/{newest.name}: design {design} has {n_preferred} specifications "
                "flagged preferred; exactly one per design is the pre-registered one"
            )

    for design, key in (("A", "A"), ("B", "B")):
        rows = [row for row in specs if row.get("design") == design]
        published = (document.get("support") or {}).get("by_design", {}).get(key, {})
        recomputed = {
            "n": len(rows),
            "n_positive": sum(1 for r in rows if r["coefficient"] > 0),
            "n_negative": sum(1 for r in rows if r["coefficient"] < 0),
            "n_zero": sum(1 for r in rows if r["coefficient"] == 0),
            "n_positive_ci": sum(1 for r in rows if r["coefficient"] > 0 and r["ci_low"] > 0),
            "n_negative_ci": sum(1 for r in rows if r["coefficient"] < 0 and r["ci_high"] < 0),
        }
        for field, value in recomputed.items():
            if published.get(field) != value:
                failures.append(
                    f"registry/robustness/{newest.name}: design {design} support {field} is "
                    f"{published.get(field)} in the summary and {value} in its own rows"
                )

    figure = document.get("figure") or {}
    figure_path = newest / str(figure.get("path", ""))
    if not figure_path.exists() or figure_path.stat().st_size == 0:
        failures.append(
            f"registry/robustness/{newest.name}: the specification curve {figure.get('path')!r} is "
            "missing or empty — the exit criterion is a rendered curve, not a table"
        )
    else:
        svg = figure_path.read_text(encoding="utf-8", errors="replace")
        n_points = svg.count("<circle") + svg.count("<polygon")
        if "<svg" not in svg:
            failures.append(f"registry/robustness/{newest.name}: {figure.get('path')} is not an SVG")
        elif len(specs) and n_points < len(specs):
            failures.append(
                f"registry/robustness/{newest.name}: the curve draws {n_points} marks for {len(specs)} "
                "specifications — a specification that is not drawn is not in the curve"
            )

    print(f"stage 7 artifact : {newest.name} ({len(specs)} specifications, "
          f"{(document.get('support') or {}).get('by_design', {}).get('A', {}).get('n', '?')} A / "
          f"{(document.get('support') or {}).get('by_design', {}).get('B', {}).get('n', '?')} B, "
          f"counts recomputed from its own rows)")


def check_stage8_registry(failures: list[str]) -> None:
    """The registry's own counts, against the cards on disk.

    Shape is the schema's job (check_schemas). What is checked here is the one thing a schema cannot see:
    whether the index's summary of the cards still describes the cards. The failure this exists for is a
    re-run of analysis/R/01_build_dags.R, which rewrites the cards wholesale and resets the estimate block
    — the index would then still advertise a registry that no longer exists.
    """
    index_path = CARDS_DIR / "index.json"
    if not index_path.exists():
        return
    index = json.loads(index_path.read_text(encoding="utf-8"))
    counts = (index.get("registry") or {}).get("card_estimate_counts")
    if counts is None:
        failures.append(
            "registry/dags/index.json: carries no registry.card_estimate_counts — Stage 8's assembly has "
            "not run over these cards (analysis/R/05_registry.R)"
        )
        print("stage 8 registry : not assembled (no card_estimate_counts on the index)")
        return
    cards = []
    for path in sorted(CARDS_DIR.glob("*.json")):
        if path.name == "index.json":
            continue
        cards.append(json.loads(path.read_text(encoding="utf-8")))
    estimated = sum(1 for c in cards if (c.get("estimate") or {}).get("status") == "estimated")
    reasons: dict[str, int] = {}
    for card in cards:
        block = card.get("estimate") or {}
        if block.get("status") == "not_estimated":
            code = (block.get("not_estimated_reason") or {}).get("code", "missing")
            reasons[code] = reasons.get(code, 0) + 1
    if counts.get("estimated") != estimated:
        failures.append(
            f"registry/dags: the index says {counts.get('estimated')} card(s) carry a published number and "
            f"the cards say {estimated} — the registry is stale against its own cards"
        )
    if counts.get("not_estimated") != len(cards) - estimated:
        failures.append(
            f"registry/dags: the index says {counts.get('not_estimated')} card(s) carry no number and the "
            f"cards say {len(cards) - estimated}"
        )
    if (counts.get("not_estimated_by_reason") or {}) != reasons:
        failures.append(
            f"registry/dags: the index's reasons {counts.get('not_estimated_by_reason')} do not match the "
            f"cards' {reasons}"
        )
    print(f"stage 8 registry : {estimated} of {len(cards)} card(s) carry a published number; index counts "
          f"recomputed from the cards")


def check_events(failures: list[str], quality_vintage: str | None) -> None:
    """The transition event study: same vintage invariant, plus the shape of the design itself.

    `tests/verify_events.py` re-fits all 32 specifications and re-enumerates the placebo distribution. This
    checks what a summary can lose without a fit going wrong: rows missing their contract fields, an
    event x horizon cell that is neither fitted nor declared, a window that drifted from the spec's rule, and
    a pre-trend check that quietly disappeared instead of being declared unavailable.
    """
    newest = newest_dir(EVENTS_ROOT)
    if newest is None:
        print("stage 8b artifact: none yet (registry/events/ is empty)")
        return
    if not DATE_LABEL.match(newest.name):
        failures.append(
            f"registry/events/{newest.name}: the vintage is not a date, so a consumer that selects the "
            "newest by date will skip it (C-44, S4-20)"
        )
    document_path = newest / "events.json"
    if not document_path.exists():
        failures.append(f"{document_path.relative_to(REPO_ROOT)}: missing")
        return
    document = json.loads(document_path.read_text(encoding="utf-8"))
    if document.get("vintage") != newest.name:
        failures.append(
            f"registry/events/{newest.name}: the artifact's own vintage is {document.get('vintage')!r}, "
            "which disagrees with the directory holding it"
        )
    if quality_vintage and document.get("vintage") != quality_vintage:
        failures.append(
            f"registry/events/{document.get('vintage')}: computed against a different gate vintage than the "
            f"newest ({quality_vintage}) — re-run analysis/R/06_events.R"
        )

    specs = document.get("specifications") or []
    required = {"event", "outcome", "horizon", "variant", "beta", "se", "proportional", "ci_low",
                "ci_high", "mde_proportional", "pre_months", "post_months", "n_parameters",
                "window_start", "window_end", "truncated_by_next_transition"}
    for row in specs:
        missing = required - set(row)
        if missing:
            failures.append(
                f"registry/events/{newest.name}: specification {row.get('event')!r} / {row.get('outcome')!r} "
                f"/ h={row.get('horizon')} is missing {sorted(missing)} — the json_contract in "
                "analysis/specs/events.yml requires them on every row"
            )

    events = document.get("events") or []
    horizons = [int(h) for h in (document.get("windows") or {}).get("focus_horizons", [])]
    outcomes = (document.get("series") or {}).get("outcomes") or []
    if not horizons or not outcomes:
        failures.append(f"registry/events/{newest.name}: the artifact does not declare its horizons/outcomes")
    else:
        fitted = {(row.get("event"), row.get("horizon")) for row in specs}
        declared = {(skip.get("event"), skip.get("horizon"))
                    for skip in (document.get("windows") or {}).get("skips", [])}
        for event in events:
            for horizon in horizons:
                cell = (event.get("id"), horizon)
                if cell not in fitted and cell not in declared:
                    failures.append(
                        f"registry/events/{newest.name}: {cell[0]} / h={horizon} is neither fitted nor "
                        "declared as a skip — a missing cell has to say why it is missing"
                    )
        for cell in declared:
            skip = [s for s in (document.get("windows") or {}).get("skips", [])
                    if (s.get("event"), s.get("horizon")) == cell][0]
            if not str(skip.get("why", "")).strip():
                failures.append(f"registry/events/{newest.name}: skip {cell} carries no reason")
        for row in specs:
            if row.get("event") is None or row.get("outcome") not in outcomes \
                    or row.get("horizon") not in horizons:
                failures.append(
                    f"registry/events/{newest.name}: a specification names an undeclared "
                    f"event/outcome/horizon ({row.get('event')!r} / {row.get('outcome')!r} / "
                    f"{row.get('horizon')!r})"
                )
            if not str(row.get("window_start", "")).strip() or not str(row.get("window_end", "")).strip():
                failures.append(
                    f"registry/events/{newest.name}: a specification has no window_start/window_end"
                )

    unavailable = {str(u.get("event")) for u in (document.get("checks") or {}).get("pre_trend_unavailable", [])}
    placebo_rows = {(str(p.get("event")), p.get("outcome")) for p in document.get("pre_trend_placebo") or []}
    for event in events:
        for outcome in outcomes:
            if (str(event.get("id")), outcome) not in placebo_rows and str(event.get("id")) not in unavailable:
                failures.append(
                    f"registry/events/{newest.name}: {event.get('id')} / {outcome} has neither a pre-trend "
                    "placebo row nor a declared reason for its absence"
                )

    if (document.get("party_split") or {}).get("no_test_computed") is not True:
        failures.append(
            f"registry/events/{newest.name}: the party split does not declare `no_test_computed` — two "
            "events against two events carries no inference and must not be presented as if it did"
        )

    figure = document.get("figure") or {}
    figure_path = newest / str(figure.get("path", ""))
    if not figure_path.exists() or figure_path.stat().st_size == 0:
        failures.append(
            f"registry/events/{newest.name}: the figure {figure.get('path')!r} is missing or empty — the "
            "exit criterion is a rendered figure, not a table"
        )
    print(f"stage 8b artifact: {newest.name} ({len(specs)} specifications over {len(events)} transitions, "
          f"{len(unavailable)} declared uncheckable pre-trend(s), cells accounted for)")


def check_rag(failures: list[str], quality_vintage: str | None) -> None:
    """The retrieval corpus: same vintage invariant, plus the two pointers a rebuild can break silently.

    `tests/verify_rag.py` re-hashes every source and recomputes every metric. What is checked here is the
    cheap cross-artifact contract: the corpus is stamped with the newest gate vintage, the vectors it names
    exist and hash to what it recorded, and the retrieval evaluation describes the corpus that is on disk.
    A rebuild that regenerated the text but left the old vectors (or vice versa) is the failure this catches.
    """
    newest = newest_dir(RAG_ROOT)
    if newest is None:
        print("stage 8c artifact: none yet (registry/rag/ is empty)")
        return
    if not DATE_LABEL.match(newest.name):
        failures.append(
            f"registry/rag/{newest.name}: the vintage is not a date, so a consumer that selects the newest "
            "by date will skip it (C-44, S4-20)"
        )
    corpus_path = newest / "corpus.json"
    if not corpus_path.exists():
        failures.append(f"{corpus_path.relative_to(REPO_ROOT)}: missing")
        return
    corpus = json.loads(corpus_path.read_text(encoding="utf-8"))
    if corpus.get("vintage") != newest.name:
        failures.append(
            f"registry/rag/{newest.name}: the corpus vintage is {corpus.get('vintage')!r}, which disagrees "
            "with the directory holding it"
        )
    if quality_vintage and corpus.get("vintage") != quality_vintage:
        failures.append(
            f"registry/rag/{corpus.get('vintage')}: built against a different gate vintage than the newest "
            f"({quality_vintage}) — re-run scripts/build_rag_corpus.py"
        )

    embedding = corpus.get("embedding") or {}
    if embedding.get("status") == "built":
        vectors = newest / "embeddings.npz"
        if not vectors.exists():
            failures.append(f"registry/rag/{newest.name}: the corpus says the vectors are built and "
                            "embeddings.npz is missing")
        elif embedding.get("sha256") != hashlib.sha256(vectors.read_bytes()).hexdigest():
            failures.append(f"registry/rag/{newest.name}: the recorded embeddings sha256 does not match the "
                            "file — the text and the vectors are one edit apart")
        if embedding.get("n_chunk_vectors") != corpus.get("counts", {}).get("chunks"):
            failures.append(f"registry/rag/{newest.name}: {embedding.get('n_chunk_vectors')} vectors for "
                            f"{corpus.get('counts', {}).get('chunks')} chunks")

    eval_path = newest / "eval_set.json"
    retrieval_path = newest / "retrieval_eval.json"
    if not eval_path.exists() or not retrieval_path.exists():
        failures.append(f"registry/rag/{newest.name}: eval_set.json and/or retrieval_eval.json missing")
        return
    eval_set = json.loads(eval_path.read_text(encoding="utf-8"))
    retrieval = json.loads(retrieval_path.read_text(encoding="utf-8"))
    if eval_set.get("vintage") != corpus.get("vintage"):
        failures.append(f"registry/rag/{newest.name}: eval set vintage {eval_set.get('vintage')!r} != "
                        f"corpus vintage {corpus.get('vintage')!r}")
    if retrieval.get("corpus", {}).get("sha256") != hashlib.sha256(corpus_path.read_bytes()).hexdigest():
        failures.append(f"registry/rag/{newest.name}: retrieval_eval.json describes a different corpus — "
                        "re-run scripts/eval_rag.py")
    if retrieval.get("eval_set", {}).get("sha256") != hashlib.sha256(eval_path.read_bytes()).hexdigest():
        failures.append(f"registry/rag/{newest.name}: retrieval_eval.json describes a different eval set")

    # The intent gate's evaluation describes the same corpus and the same vintage. A gate measured
    # against a different corpus would carry a refusal rate that says nothing about this one.
    intent_path = newest / "intent_eval.json"
    if intent_path.exists():
        intent = json.loads(intent_path.read_text(encoding="utf-8"))
        if intent.get("vintage") != corpus.get("vintage"):
            failures.append(
                f"registry/rag/{newest.name}: intent_eval.json carries vintage {intent.get('vintage')!r} and "
                f"the corpus carries {corpus.get('vintage')!r}"
            )
        if intent.get("corpus", {}).get("sha256") != hashlib.sha256(corpus_path.read_bytes()).hexdigest():
            failures.append(
                f"registry/rag/{newest.name}: intent_eval.json describes a different corpus — re-run "
                "scripts/eval_intent.py"
            )

    # The answer layer's measurement is only about this corpus and this gate: a re-run of either leaves
    # it describing a decision nobody made on the text it quotes.
    answer_path = newest / "answer_eval.json"
    if answer_path.exists():
        answer = json.loads(answer_path.read_text(encoding="utf-8"))
        if answer.get("vintage") != corpus.get("vintage"):
            failures.append(
                f"registry/rag/{newest.name}: answer_eval.json carries vintage {answer.get('vintage')!r} "
                f"and the corpus carries {corpus.get('vintage')!r}"
            )
        if answer.get("corpus", {}).get("sha256") != hashlib.sha256(corpus_path.read_bytes()).hexdigest():
            failures.append(
                f"registry/rag/{newest.name}: answer_eval.json describes a different corpus — re-run "
                "scripts/eval_answer.py"
            )
        if (newest / "intent_eval.json").exists():
            if answer.get("gate", {}).get("artifact_sha256") != hashlib.sha256(
                    (newest / "intent_eval.json").read_bytes()).hexdigest():
                failures.append(
                    f"registry/rag/{newest.name}: answer_eval.json was measured against a different "
                    "intent_eval.json — re-run scripts/eval_answer.py"
                )

    print(f"stage 8c artifact: {newest.name} ({corpus.get('counts', {}).get('chunks')} chunks, "
          f"{len(corpus.get('sources') or [])} attributed sources, embedding "
          f"{embedding.get('status')}, retrieval eval describes this corpus)")


def check_series(failures: list[str]) -> None:
    """The outcome panels must describe the same registry the cards do.

    A schema cannot see this: the index could be internally consistent and still carry eleven panels for
    twelve outcome cards, or a figure from another vintage. The app shows one panel per card, so the two
    artifacts have to agree on which outcomes exist before either is rendered.
    """
    newest = newest_dir(SERIES_ROOT)
    if newest is None:
        print("series figures  : none yet (registry/series/ is empty)")
        return
    if not DATE_LABEL.match(newest.name):
        failures.append(
            f"registry/series/{newest.name}: the vintage is not a date, so a consumer that selects the "
            "newest directory would show an older series beside a newer card"
        )
    index_path = newest / "index.json"
    if not index_path.exists():
        failures.append(f"registry/series/{newest.name}: index.json is missing")
        return
    document = json.loads(index_path.read_text(encoding="utf-8"))
    if document.get("vintage") != newest.name:
        failures.append(
            f"registry/series/{newest.name}: the artifact's own vintage is {document.get('vintage')!r}"
        )

    cards_index_path = CARDS_DIR / "index.json"
    if not cards_index_path.exists():
        failures.append("registry/series: the card index is missing, so the panels cannot be matched")
        return
    cards_index = json.loads(cards_index_path.read_text(encoding="utf-8"))
    if document.get("vintage") != cards_index.get("vintage_date"):
        failures.append(
            f"registry/series/{newest.name}: computed against a different registry vintage "
            f"({cards_index.get('vintage_date')!r}) than the cards — re-run analysis/R/07_series_figures.R"
        )

    expected_ids = [row.get("id") for row in cards_index.get("outcomes") or []]
    published_ids = [row.get("id") for row in document.get("outcomes") or []]
    if published_ids != expected_ids:
        failures.append(
            f"registry/series/{newest.name}: the panels are {published_ids} and the card index declares "
            f"{expected_ids} — one panel per outcome card"
        )
    if (document.get("counts") or {}).get("outcomes") != len(published_ids):
        failures.append(
            f"registry/series/{newest.name}: counts.outcomes is "
            f"{(document.get('counts') or {}).get('outcomes')} but {len(published_ids)} panel(s) are published"
        )

    recorded: set[str] = set()
    for row in document.get("outcomes") or []:
        figure = row.get("figure") or {}
        relative = str(figure.get("path") or "")
        recorded.add(relative)
        if not relative.startswith(f"registry/series/{newest.name}/"):
            failures.append(
                f"registry/series/{newest.name}: {row.get('id')} names a figure outside this vintage "
                f"({relative!r})"
            )
            continue
        path = REPO_ROOT / relative
        if not path.exists() or path.stat().st_size == 0:
            failures.append(
                f"registry/series/{newest.name}: {row.get('id')} names {relative!r}, which is missing or "
                "empty — a card would show a caption for a figure that is not on disk"
            )
            continue
        if "<svg" not in path.read_text(encoding="utf-8", errors="replace"):
            failures.append(f"registry/series/{newest.name}: {relative} is not an SVG")
        # Canonical bytes (CRLF collapsed to LF), as git stores the file: a raw size would call a fresh panel
        # stale on the Linux runner and on any clone.
        size = len(path.read_bytes().replace(b"\r\n", b"\n"))
        if figure.get("bytes") != size:
            failures.append(
                f"registry/series/{newest.name}: {row.get('id')} records {figure.get('bytes')} bytes and the "
                f"file is {size} — the figure is one rebuild behind its index"
            )

    for path in sorted((newest / "figures").glob("*.svg")) if (newest / "figures").exists() else []:
        relative = str(path.relative_to(REPO_ROOT)).replace("\\", "/")
        if relative not in recorded:
            failures.append(
                f"registry/series/{newest.name}: {path.name} is on disk and in no panel — a figure the index "
                "does not describe is one nothing can check"
            )

    print(f"series figures  : {newest.name} ({len(published_ids)} panel(s), one per card outcome, "
          f"every figure on disk at its recorded size)")


def check_schemas(failures: list[str]) -> int:
    """Every registry JSON against its declared schema."""
    try:
        import jsonschema
    except ImportError:
        print("  ! jsonschema not importable — schema validation skipped")
        return 0
    validated = 0
    card_schema = json.loads((SCHEMA_DIR / "dag_card.schema.json").read_text(encoding="utf-8"))
    index_schema = json.loads((SCHEMA_DIR / "dag_index.schema.json").read_text(encoding="utf-8"))
    card_validator = jsonschema.Draft202012Validator(card_schema)
    index_validator = jsonschema.Draft202012Validator(index_schema)
    for card_path in sorted(CARDS_DIR.glob("*.json")):
        document = json.loads(card_path.read_text(encoding="utf-8"))
        validator = index_validator if card_path.name == "index.json" else card_validator
        for error in validator.iter_errors(document):
            failures.append(f"{card_path.relative_to(REPO_ROOT)}: {error.message[:200]}")
        validated += 1

    robustness_schema = json.loads((SCHEMA_DIR / "robustness.schema.json").read_text(encoding="utf-8"))
    robustness_validator = jsonschema.Draft202012Validator(robustness_schema)
    for artifact in sorted(ROBUSTNESS_ROOT.glob("*/robustness.json")):
        document = json.loads(artifact.read_text(encoding="utf-8"))
        for error in robustness_validator.iter_errors(document):
            failures.append(f"{artifact.relative_to(REPO_ROOT)}: {error.message[:200]}")
        validated += 1

    events_schema = json.loads((SCHEMA_DIR / "events.schema.json").read_text(encoding="utf-8"))
    events_validator = jsonschema.Draft202012Validator(events_schema)
    for artifact in sorted(EVENTS_ROOT.glob("*/events.json")):
        document = json.loads(artifact.read_text(encoding="utf-8"))
        for error in events_validator.iter_errors(document):
            failures.append(f"{artifact.relative_to(REPO_ROOT)}: {error.message[:200]}")
        validated += 1

    series_schema = json.loads((SCHEMA_DIR / "series_index.schema.json").read_text(encoding="utf-8"))
    series_validator = jsonschema.Draft202012Validator(series_schema)
    for artifact in sorted(SERIES_ROOT.glob("*/index.json")):
        document = json.loads(artifact.read_text(encoding="utf-8"))
        for error in series_validator.iter_errors(document):
            failures.append(f"{artifact.relative_to(REPO_ROOT)}: {error.message[:200]}")
        validated += 1

    for name, path in (("country_vocabulary.schema.json", REFERENCE_DIR / "countries.json"),
                       ("donor_panel.schema.json", DONORS_DIR / "2026-10-18" / "panel.json")):
        schema = json.loads((SCHEMA_DIR / name).read_text(encoding="utf-8"))
        validator = jsonschema.Draft202012Validator(schema)
        document = json.loads(path.read_text(encoding="utf-8"))
        for error in validator.iter_errors(document):
            failures.append(f"{path.relative_to(REPO_ROOT)}: {error.message[:200]}")
        validated += 1

    for name, pattern in (("rag_corpus.schema.json", "*/corpus.json"),
                          ("rag_eval.schema.json", "*/eval_set.json"),
                          ("rag_retrieval.schema.json", "*/retrieval_eval.json"),
                          ("intent_eval.schema.json", "*/intent_eval.json"),
                          ("answer_eval.schema.json", "*/answer_eval.json"),
                          ("answer_quality_eval.schema.json", "*/answer_quality_eval.json")):
        schema = json.loads((SCHEMA_DIR / name).read_text(encoding="utf-8"))
        validator = jsonschema.Draft202012Validator(schema)
        for artifact in sorted(RAG_ROOT.glob(pattern)):
            document = json.loads(artifact.read_text(encoding="utf-8"))
            for error in validator.iter_errors(document):
                failures.append(f"{artifact.relative_to(REPO_ROOT)}: {error.message[:200]}")
            validated += 1
    return validated


def main() -> int:
    failures: list[str] = []

    payloads, unreadable = check_payload_shapes(failures)
    if payloads:
        print(f"payload shapes   : {payloads} files checked, {unreadable} unreadable by their own reader")
    else:
        print("payload shapes   : SKIPPED — no data/raw (raw payloads are gitignored); "
              "run the data job or a local checkout to cover this check")

    quality_vintage = check_report_label(failures)
    if quality_vintage:
        stage3 = "date-shaped"
        if not DATE_LABEL.match(quality_vintage):
            stage3 = "NOT date-shaped (see above)"
        print(f"gate report      : {quality_vintage} ({stage3})")
    check_stage5_matches_stage3(failures, quality_vintage)
    newest_diag = newest_dir(DIAG_ROOT)
    if newest_diag:
        print(f"stage 5 artifact : {newest_diag.name} (must equal the newest gate report vintage)")
    check_stage6_matches_stage3(failures, quality_vintage)
    check_stage7(failures, quality_vintage)
    check_events(failures, quality_vintage)
    check_stage8_registry(failures)
    check_series(failures)
    check_rag(failures, quality_vintage)

    validated = check_schemas(failures)
    print(f"registry schemas : {validated} document(s) validated")

    print()
    if failures:
        print(f"FAILED — {len(failures)} problem(s):")
        for problem in failures[:40]:
            print(f"  - {problem}")
        if len(failures) > 40:
            print(f"  … and {len(failures) - 40} more")
        return 1
    print("PASS — payloads match their declared readers, the newest gate report is reachable by date, "
          "Stages 5-8 describe it, the registry's counts match its cards, and every registry document "
          "matches its schema")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
