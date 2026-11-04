"""Build the guided-flow site from the published registry.

**Screens.** The cover (`/`), the study screen (`/study/`), the comparison screen (`/compare/`), the graph
screen (`/graph/`), the estimate screen (`/estimates/`), the chart screen (`/chart/`) and the answer screen
(`/ask/`). The Ask screen runs the JavaScript answer layer over JSON this build emits from the same specs the
Python layer reads; it carries no rules of its own.

**What it will not do.** It computes no statistic. Counts come from the artifacts' own `counts` blocks, dates
from `registry/reference/administrations.json`, wording from `analysis/specs/guide.yml`, group means from
`registry/comparisons/`, and design choices from the cards' published `diagnostics_status`. The one derivation
this script performs is ranking designs per outcome by the declared order in `RANK` (spec A-01).

Pages are self-contained apart from images and CSS: each embeds the JSON it renders, so the site works from
`file://` and over HTTP with no server, no fetch and no network.

Run:
    python site/build.py
"""

from __future__ import annotations

import html
import csv
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
SITE_SRC = REPO_ROOT / "site" / "assets"
DIST = REPO_ROOT / "site" / "dist"

# A-01, in two steps: a design that published a number for this outcome comes first (with its verdict and the
# check that decided it), then the declared Stage 5 order `pass` > `degraded` > `fail` > `not_attempted`. Ranking
# on status alone would put a `degraded` Design B, whose result is about the national money channel, not about
# the outcome, on the card, ahead of the one design that published a number for the outcome itself.
RANK = {"pass": 0, "degraded": 1, "fail": 2, "not_attempted": 3}
DOMAIN_ORDER = ("health", "education", "security", "economy")
PAGES = ("index.html", "study/index.html", "compare/index.html", "graph/index.html",
         "estimates/index.html", "chart/index.html", "ask/index.html", "designs/index.html",
         "about/index.html", "methodology/index.html", "technical/index.html")
DOMAIN_LABEL = {"health": "Health", "education": "Education", "security": "Security", "economy": "Economy"}


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def md(value) -> str:
    """The subset of Markdown the artifacts use in their prose: **bold**, *italic* and `code`.

    A single unmatched marker is put back rather than left as half a tag, so an artifact with an odd number of
    asterisks renders as text instead of breaking the page.
    """
    text = html.escape(str(value))
    while "**" in text:
        text = text.replace("**", "<strong>", 1)
        if "**" in text:
            text = text.replace("**", "</strong>", 1)
    while "*" in text:
        text = text.replace("*", "<em>", 1)
        if "*" in text:
            text = text.replace("*", "</em>", 1)
        else:
            text = text.replace("<em>", "*", 1)
    while "`" in text:
        text = text.replace("`", "<code>", 1)
        if "`" in text:
            text = text.replace("`", "</code>", 1)
        else:
            text = text.replace("<code>", "`", 1)
    return text


def term(guide: dict, section: str, key: str, field: str = "word") -> str:
    """A declared term. Sections are either a plain string per key or an object with named fields; a missing
    term fails the build rather than rendering an empty label."""
    entry = guide.get(section, {}).get(key)
    if isinstance(entry, str):
        return entry
    if not isinstance(entry, dict) or field not in entry:
        raise SystemExit(f"guide.yml has no {section}.{key}.{field}: add it before building")
    return entry[field]


def fill_text(template: str, values: dict) -> str:
    try:
        return template.format(**values)
    except KeyError as exc:
        raise SystemExit(f"guide.yml uses a placeholder with no declared value: {exc}") from exc


def signed(value: float) -> str:
    return f"{value:+.4f}"


def party_bands(bands: list[str]) -> str:
    """A flag-like backdrop from declared colours: equal vertical bands, left to right."""
    n = len(bands)
    stops = ", ".join(f"{colour} {i * 100 / n:.4f}% {(i + 1) * 100 / n:.4f}%" for i, colour in enumerate(bands))
    return f"linear-gradient(90deg, {stops})"


# The parties' emblems are drawn here as plain line art, not copied from the official marks: an umbrella for
# the PDP and a broom for the APC, at 14px and in the strip's own white. A copied logo would be a trademark
# question and, on an analysis about presidencies, an endorsement the project does not make (docs/decisions.md
# P-09). The shapes are public-domain objects; the drawing is ours.
PARTY_EMBLEMS = {
    "PDP": (
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" '
        'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">'
        '<path d="M2.4 11.4a9.6 9.6 0 0 1 19.2 0Z"/>'
        '<path d="M12 11.4V19a2.2 2.2 0 0 0 4.4 0"/>'
        '<path d="M12 2.2v1.2"/>'
        '<path d="M6.2 11.4a5.8 5.8 0 0 1 11.6 0"/>'
        '</svg>'
    ),
    "APC": (
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" '
        'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">'
        '<path d="M15.6 2.6 11.2 9.8"/>'
        '<path d="M11.2 9.8 3.8 17.6"/>'
        '<path d="M11.2 9.8 6.4 19.4"/>'
        '<path d="M11.2 9.8 9.4 20.2"/>'
        '<path d="M11.2 9.8 12.6 19.6"/>'
        '<path d="M11.2 9.8 15 17.4"/>'
        '<path d="M5.4 14.6c3.4 2.6 7.4 2.8 10.2.6"/>'
        '</svg>'
    ),
}


def party_emblem(code: str) -> str:
    return PARTY_EMBLEMS.get(code, "")


def load_glossary(root: Path) -> dict[str, str]:
    """The plain-language meanings, straight from `docs/glossary.md`, never retyped here."""
    path = root / "docs" / "glossary.md"
    entries: dict[str, str] = {}
    if not path.exists():
        return entries
    for line in path.read_text(encoding="utf-8").splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) == 2 and cells[0].startswith("**") and cells[0].endswith("**"):
            entries[cells[0].strip("*").strip()] = cells[1]
    return entries


def answer_data(root: Path, vintage: str) -> dict:
    """Everything the browser's answer layer reads, emitted from the specs it shares with Python."""
    gate_spec = yaml.safe_load((root / "analysis" / "specs" / "intent_gate.yml").read_text(encoding="utf-8"))
    rag = yaml.safe_load((root / "analysis" / "specs" / "rag.yml").read_text(encoding="utf-8"))
    quality = load(root / "registry" / "quality" / vintage / "report.json")
    corpus = load(root / "registry" / "rag" / vintage / "corpus.json")
    countries = load(root / "registry" / "reference" / "countries.json")
    contract = rag.get("answer_contract") or {}
    chunks = [{key: chunk.get(key) for key in ("chunk_id", "doc_type", "title", "text", "citation", "metadata", "vintage")}
              for chunk in corpus.get("chunks") or []]
    return {
        "gate": {
            "spec": gate_spec,
            "vintage": vintage,
            "window_start": (quality.get("study_window") or {}).get("start"),
            "countries": countries.get("countries") or [],
        },
        "contract": {
            "contract": contract,
            "k": int((rag.get("retrieval") or {}).get("k") or 5),
            "glossary": load_glossary(root),
        },
        "corpus": {"chunks": chunks},
    }


def build_context(root: Path) -> dict:
    index = load(root / "registry" / "dags" / "index.json")
    vintage = index["vintage_date"]
    series = load(root / "registry" / "series" / vintage / "index.json")
    admins = load(root / "registry" / "reference" / "administrations.json")
    guide = yaml.safe_load((root / "analysis" / "specs" / "guide.yml").read_text(encoding="utf-8"))
    comparisons_path = root / "registry" / "comparisons" / vintage / "comparisons.json"
    comparisons = load(comparisons_path) if comparisons_path.exists() else {"outcomes": []}
    charts = {row["id"]: row for row in comparisons.get("outcomes") or []}
    breaks_path = root / "registry" / "changepoints" / vintage / "changepoints.json"
    changepoints = load(breaks_path) if breaks_path.exists() else {"outcomes": []}
    breaks = {row["id"]: row for row in changepoints.get("outcomes") or []}
    # Screen 6b reads the three design-level artifact families. They are loaded by vintage, like every other
    # input, so a figure from one vintage can never sit beside a verdict from another.
    estimates = load(root / "registry" / "estimates" / vintage / "estimates.json")
    robustness = load(root / "registry" / "robustness" / vintage / "robustness.json")
    events = load(root / "registry" / "events" / vintage / "events.json")
    # The supplied portraits, keyed by slug. A file is only rendered when the licence manifest has a row for it;
    # an entry without its file fails the site verifier, not the build.
    manifest_path = root / "site" / "assets" / "presidents" / "manifest.json"
    portraits = {}
    if manifest_path.exists():
        portraits = {row["slug"]: row for row in load(manifest_path)["portraits"]}
    # Stage 8g: the tenure description. Loaded by vintage like every other artifact.
    tenure_path = root / "registry" / "tenure" / vintage / "tenure.json"
    tenure = {row["id"]: row for row in load(tenure_path)["outcomes"]} if tenure_path.exists() else {}
    # The refusal threshold is declared in the spec that R fits against; the site reads it rather than
    # typing the number, so the sentence and the rule cannot drift.
    tenure_spec = yaml.safe_load((root / "analysis" / "specs" / "tenure.yml").read_text(encoding="utf-8"))
    tenure_min_native = (tenure_spec.get("refusals") or {}).get("min_native", 20)

    cards: dict[tuple[str, str], tuple[dict, dict]] = {}
    for entry in index["dags"]:
        cards[(entry["outcome_id"], entry["design_id"])] = (
            entry, load(root / "registry" / "dags" / f"{entry['dag_id']}.json"))

    outcomes = []
    for outcome in index["outcomes"]:
        oid = outcome["id"]
        panel = next((o for o in series["outcomes"] if o["id"] == oid), None)
        if panel is None:
            raise SystemExit(f"series index has no panel for {oid}")

        choices = []
        for design in index["designs"]:
            entry, card = cards[(oid, design["id"])]
            status = entry.get("diagnostics_status") or "not_attempted"
            estimate = card.get("estimate") or {}
            choices.append({
                "design": design["id"],
                "design_name": design["name"],
                "status": status,
                "word": term(guide, "status", status),
                "tone": term(guide, "status", status, "tone"),
                "sentence": term(guide, "status", status, "sentence"),
                "has_number": estimate.get("status") == "estimated",
                "reason_code": (estimate.get("not_estimated_reason") or {}).get("code"),
                "reason_detail": (estimate.get("not_estimated_reason") or {}).get("detail"),
                "blocker": entry.get("diagnostics_blocker"),
                "published_result": estimate.get("published_result"),
                "assumption": card.get("identifying_assumption"),
                "dag_id": entry["dag_id"],
            })

        chosen = sorted(choices, key=lambda c: (0 if c["has_number"] else 1, RANK[c["status"]]))[0]
        # The four kinds a card can be, decided by what the card has rather than by where it is shown: a
        # published coefficient and its interval; a design that ran and was not identified; a result that
        # is about the money channel; or a declared gap. Every flow screen shapes the card on this.
        if chosen["has_number"]:
            kind = "number"
        elif chosen["reason_code"] == "design_estimated_not_identified":
            kind = "described"
        elif chosen["reason_code"] == "design_result_is_channel_level":
            kind = "channel"
        else:
            kind = "gap"
        design = next(d for d in index["designs"] if d["id"] == chosen["design"])
        chosen_card = cards[(oid, chosen["design"])][1]
        labels = {node["id"]: node.get("label") or node["id"] for node in chosen_card.get("nodes") or []}

        assumption = chosen_card.get("identifying_assumption") or "not stated"
        estimate = chosen_card.get("estimate") or {}
        spec = estimate.get("specification") or {}
        verdict = estimate.get("verdict") or {}

        plain = []
        numbers = None
        if spec:
            numbers = {
                "coefficient": signed(spec["coefficient"]),
                "ci_low": f"{spec['ci_low']:.4f}",
                "ci_high": f"{spec['ci_high']:.4f}",
                "p_value": f"{spec['p_value']:.4f}",
                "n_obs": f"{spec['n_obs']:,}",
                "n_units": spec["n_units"],
                "first_month": spec.get("first_month", "?"),
                "last_month": spec.get("last_month", "?"),
            }
            # The card leads with what is associated with what, in words, because a coefficient and a p-value
            # answer no question a general reader has. The formula is the artifact's own; the predictor's
            # plain name is declared in guide.yml, so an unrecognised regressor cannot be silently glossed.
            regressor = str(spec.get("formula") or "").split("~")[-1].split("|")[0].strip()
            exposure = (guide["results"].get("predictors") or {}).get(regressor)
            if exposure and spec.get("coefficient") is not None:
                coefficient = float(spec["coefficient"])
                plain.append(fill_text(guide["results"]["association"], {
                    "exposure": exposure,
                    "change": f"{abs(coefficient):.2f}",
                    "direction": "more" if coefficient >= 0 else "fewer",
                    "outcome": outcome["label"].lower(),
                }))
            crosses = spec["ci_low"] <= 0 <= spec["ci_high"]
            plain.append(guide["results"]["includes_zero"] if crosses else guide["results"]["excludes_zero"])
            plain.append(fill_text(guide["results"]["sample"], numbers))
            if verdict.get("status"):
                plain.append(fill_text(guide["results"]["verdict"], {"verdict": verdict["status"]}))
            if verdict.get("failed_checks"):
                plain.append(fill_text(guide["results"]["failed_check"], {"failed_check": verdict["failed_checks"]}))

        chart = charts.get(oid)
        group_rows = []
        for group in (chart or {}).get("groups") or []:
            group_rows.append({
                "grouping": group["grouping_id"],
                "plain": group["plain"],
                "technical": group["technical"],
                "n_units": group["n_units"],
                "months": group["months"],
                "group_mean": group["group_mean"],
                "caption": group["caption"],
            })

        outcomes.append({
            "id": oid,
            "label": outcome["label"],
            "short": panel["short"],
            "domain": outcome["domain"],
            "domain_label": DOMAIN_LABEL.get(outcome["domain"], outcome["domain"]),
            "unit": panel["unit"],
            "direction": term(guide, "direction", outcome["direction"]),
            "coverage": term(guide, "coverage", outcome["coverage_status"]),
            "coverage_note": term(guide, "coverage_note", outcome["coverage_status"]),
            "native_frequency": panel["native_frequency"],
            "observations": panel["observations"],
            "native_in_window": panel["native_in_window"],
            "observed_span": [panel["first_observed"], panel["last_observed"]],
            "definition_breaks": [b["name"] for b in panel.get("definition_breaks") or []],
            "caption": panel["caption"],
            "compare": {
                "design": design["id"],
                "design_name": design["name"],
                "design_short": design["short"],
                "plain": term(guide, "designs", design["id"], "plain_comparison"),
                "assumes": term(guide, "designs", design["id"], "assumes"),
                **{k: chosen[k] for k in ("status", "word", "tone", "sentence", "has_number",
                                          "reason_code", "reason_detail", "blocker",
                                          "published_result", "assumption")},
                "kind": kind,
                "reason_sentence": term(guide, "reasons", chosen["reason_code"], "sentence")
                if chosen["reason_code"] in guide.get("reasons", {}) else None,
            },
            "graph": {
                "design": design["id"],
                "design_name": design["name"],
                "svg": f"assets/graphs/{chosen['dag_id']}.svg",
                "assumption": assumption,
                "adjustment": [f"{labels.get(node, node)} ({node})" for node in chosen_card.get("adjustment_set") or []],
                "absent": [f"{labels.get(node, node)} ({node})" for node in chosen_card.get("assumption_required") or []],
                "cannot_rule_out": chosen_card.get("cannot_rule_out") or [],
                "alternatives": [{
                    "design": other["design"],
                    "design_name": other["design_name"],
                    "word": other["word"],
                    "tone": other["tone"],
                    "has_number": other["has_number"],
                    "sentence": other["sentence"],
                    "svg": f"assets/graphs/{other['dag_id']}.svg",
                    "assumption": other["assumption"],
                } for other in choices if other["design"] != design["id"]],
            },
            "estimate": {
                "has_number": bool(spec),
                "plain": plain,
                "numbers": numbers if spec else None,
                "spec": spec,
                "verdict": verdict,
                "status_word": chosen["word"],
                "tone": chosen["tone"],
                "kind": kind,
                "reason_code": chosen["reason_code"],
                "reason_sentence": term(guide, "reasons", chosen["reason_code"], "sentence")
                if chosen["reason_code"] in guide.get("reasons", {}) else None,
                "reason_detail": chosen["reason_detail"],
                "published_result": chosen["published_result"],
                "channel_level": chosen["reason_code"] == "design_result_is_channel_level",
            },
            "chart": {
                "figure": f"assets/comparisons/{oid}.svg",
                "caption": (chart or {}).get("caption"),
                "groups": group_rows,
                "has_state": any(g["grouping"] == "state_dose_quartile" for g in group_rows),
            } if chart else None,
            "breaks": {
                "status": breaks[oid]["status"],
                "figure": f"assets/breaks/{oid}.svg" if breaks[oid].get("figure") else None,
                "caption": breaks[oid]["plain_caption"],
                "method": breaks[oid]["method_detail"],
                "native": breaks[oid]["native_in_window"],
                "span": breaks[oid].get("span"),
                "refused": breaks[oid].get("refused"),
                "rows": [{
                    "month": brk["month"],
                    "label": brk["label"],
                    "statement": brk["statement"],
                    "kind": brk["kind"],
                    "coincides": brk.get("coincides_with_inauguration"),
                } for brk in breaks[oid]["breaks"]],
            } if oid in breaks else None,
        })

    # ---- Screen 6b: the design-level results, read field by field from the artifacts ------------------------
    outcome_labels = {o["id"]: o["label"] for o in outcomes}
    copy = guide["design_results"]
    by_design = {row["id"]: row for row in estimates["designs"]}

    def published_rows(design_id: str) -> list[dict]:
        # An outcome the twelve-outcome index does not carry (a UCDP item inside `fatalities`) is named by the
        # declared wording in guide.yml rather than dropped from the table under a plot row that drew it.
        declared = copy.get("outcome_labels") or {}
        return [{
            "outcome": outcome_labels.get(row["outcome"], declared.get(row["outcome"], copy["outcome_unknown"])),
            "line": fill_text(copy["row"], {
                "outcome": outcome_labels.get(row["outcome"],
                                              declared.get(row["outcome"], copy["outcome_unknown"])),
                "coefficient": signed(row["coefficient"]),
                "interval": f"{row['ci_low']:.4f} – {row['ci_high']:.4f}",
                "obs": f"{row['n_obs']:,}",
            }),
        } for row in estimates["specifications"] if row["design"] == design_id]

    a_checks = by_design["A"]["checks"]
    support_by_design = robustness["support"]["by_design"]
    b_spread = robustness["spread"]["design_b"]
    b_placebo = robustness["sensitivity"]["design_b"]["in_time_placebo"]
    preferred_b = robustness["preferred"]["design_b"]

    status_words = copy["event_status"]
    transitions = {row["id"]: row for row in events["events"]}
    event_rows = []
    for verdict in events["verdicts"]:
        if verdict["status"] not in status_words:
            raise SystemExit(f"guide.yml design_results.event_status has no entry for {verdict['status']!r}")
        transition = transitions.get(verdict["event"])
        if transition is None:
            raise SystemExit(f"events.json carries a verdict for an event with no row: {verdict['event']}")
        event_rows.append({
            "month": transition["transition_month"],
            "outcome": outcome_labels.get(verdict["outcome"], copy["outcome_unknown"]),
            "status": status_words[verdict["status"]],
            "p_value": f"{verdict['placebo_p']:.4f}",
        })
    event_rows.sort(key=lambda row: (row["month"], row["outcome"]))

    def support_line(design_id: str) -> str:
        row = support_by_design[design_id]
        return fill_text(copy["support"], {
            "n": row["n"], "n_positive": row["n_positive"],
            "n_negative": row["n_negative"], "n_near_zero": row["n_near_zero"],
        })

    design_results = {
        "forest": {
            "figure": f"assets/designs/{Path(estimates['figure']['path']).name}",
            "bytes": estimates["figure"]["bytes"],
            "layout": estimates["figure"]["layout"],
        },
        "curve": {
            "figure": f"assets/designs/{Path(robustness['figure']['path']).name}",
            "bytes": robustness["figure"]["bytes"],
            "layout": robustness["figure"]["layout"],
            "n_points": robustness["figure"].get("n_points"),
        },
        "event_figure": {
            "figure": f"assets/designs/{Path(events['figure']['path']).name}",
            "bytes": events["figure"]["bytes"],
            "layout": events["figure"]["layout"],
        },
        "a": {
            "status": (by_design["A"].get("verdict") or {}).get("status"),
            "failed_check": (by_design["A"].get("verdict") or {}).get("failed_checks"),
            "rows": published_rows("A"),
            "mis_timed": fill_text(copy["mis_timed"], {
                "lead_months": a_checks["placebo"]["lead_months"],
                "coefficient": signed(a_checks["placebo"]["coefficient"]),
            }),
            "lead_shift": fill_text(copy["lead_shift"], {
                "p_value": f"{a_checks['lead_shift']['p_value']:.4f}",
                "n_draws": a_checks["lead_shift"]["n_draws"],
            }),
        },
        "b": {
            "status": (by_design["B"].get("verdict") or {}).get("status"),
            "published": fill_text(copy["row"], {
                "outcome": copy["channel_outcome"],
                "coefficient": signed(preferred_b["coefficient"]),
                "interval": f"{preferred_b['ci_low']:.4f} – {preferred_b['ci_high']:.4f}",
                "obs": f"{preferred_b['n_obs']:,}",
            }),
        },
        "grid": {
            "a_support": support_line("A"),
            "b_support": support_line("B"),
            "b_spread": fill_text(copy["spread"], {
                "min": f"{b_spread['coefficient_min']:.4f}",
                "max": f"{b_spread['coefficient_max']:.4f}",
            }),
            "b_placebo": fill_text(copy["placebo"], {
                "p_value": f"{b_placebo['p_value']:.4f}",
                "n_draws": b_placebo["n_draws"],
            }),
            "reading": robustness["sensitivity"]["design_b"].get("in_time_placebo_interpretation"),
            "flips": [fill_text(copy["flip"], {
                "axis": row["axis"].replace("_", " "),
                "level": str(row["level"]).replace("_", " "),
                "n_opposite": row["n_opposite"],
                "n": row["n"],
            }) for row in robustness["support"]["flips"]["levels"]],
        },
        "c": {
            "status": by_design["C"].get("status"),
            "why": by_design["C"].get("why"),
            "next_step": by_design["C"].get("next_step"),
            "counts": by_design["C"].get("counts") or {},
            # One group per outcome (C-91): the artifact fits each outcome separately, and a flat list of 35
            # windows would let a reader compare two gaps without seeing that they are in different units.
            "groups": [{
                "outcome": block["outcome"],
                "label": block.get("label") or block["outcome"],
                "unit": block.get("unit") or "",
                "status": block["status"],
                "counts": block.get("counts") or {},
                "rows": [{
                    "years": f"{w['first_year']}–{w['last_year']}",
                    "gap": signed(w["mean_gap"]),
                    "ridge": signed(w["ridge_gap"]),
                    "p": f"{w['p_value']:.2f}",
                    "status": str(w["status"]).replace("_", " "),
                } for w in (by_design["C"].get("windows") or [])
                    if w.get("outcome") == block["outcome"] and w["status"] != "refused"],
            } for block in (by_design["C"].get("outcomes") or [])],
            "rows": [{
                "years": f"{w['first_year']}–{w['last_year']}",
                "gap": signed(w["mean_gap"]),
                "ridge": signed(w["ridge_gap"]),
                "p": f"{w['p_value']:.2f}",
                "status": str(w["status"]).replace("_", " "),
            } for w in by_design["C"].get("windows") or [] if w["status"] != "refused"],
            "refused": [w for w in by_design["C"].get("windows") or [] if w["status"] == "refused"],
        },
        "events": {
            "rows": event_rows,
            "rule": events["verdict_rule"],
            "not_claimed": events["not_claimed"],
        },
    }

    counts = index["registry"]["card_estimate_counts"]
    spine = series["counts"]["spine_rows"]
    design_c = load(root / "registry" / "design_c" / vintage / "design_c.json")
    with (root / "dbt" / "seeds" / "raw_metric_catalogue.csv").open(encoding="utf-8", newline="") as handle:
        catalogue = list(csv.DictReader(handle))
    fills = {
        "window_first": series["window"]["first"],
        "window_last": series["window"]["last"],
        "first_year": series["window"]["first"][:4],
        "last_year": series["window"]["last"][:4],
        "administrations": admins["counts"]["administrations"],
        "spine_total": sum(int(v) for v in spine.values()),
        "spine_observed": spine["observed"],
        "spine_interpolated": spine["interpolated"],
        "spine_unobserved": spine["unobserved"],
        "estimated": counts["estimated"],
        "no_number": counts["not_estimated"],
        "cards": counts["estimated"] + counts["not_estimated"],
        "models": counts["estimated"] + counts["not_estimated"],
        "outcomes": len(index["outcomes"]),
        "covariates": sum(1 for row in catalogue if row["is_outcome"] != "true"),
        "designs": len(index["designs"]),
        "specifications": len(estimates["specifications"]) + len(robustness["specifications"]),
        "donors": design_c["counts"]["donors"],
        "placebos_total": design_c["counts"]["placebos_in_space"],
        "placebos_passing": design_c["counts"]["placebos_passing_pre_fit"],
        "verifiers": len(list((root / "tests").glob("verify_*.py"))),
    }
    for key, value in fills.items():
        fills[key] = f"{value:,}" if isinstance(value, int) else value

    tech = yaml.safe_load((root / "analysis" / "specs" / "technical.yml").read_text(encoding="utf-8"))
    estimation = yaml.safe_load((root / "analysis" / "specs" / "estimation.yml").read_text(encoding="utf-8"))
    grid = yaml.safe_load((root / "analysis" / "specs" / "robustness.yml").read_text(encoding="utf-8"))
    variables = [{
        "id": row["metric_id"],
        "label": row["label"],
        "unit": row["unit"],
        "direction": "higher is better" if row["direction"] == "up" else "lower is better",
        "source": row["source_label"],
        "coverage": row["coverage_status"],
        "outcome": row["is_outcome"] == "true",
    } for row in catalogue]
    design_a = estimation["design_a"]
    design_b = estimation["design_b"]
    design_c_spec = yaml.safe_load((root / "analysis" / "specs" / "design_c.yml").read_text(encoding="utf-8"))
    models = [
        {
            "design": "A",
            "estimator": design_a["estimator"].split(",")[0],
            "outcome": ", ".join([design_a["outcome"], *design_a["robustness_outcomes"]]),
            "treatment": f"log({design_a['exposure']['column']})",
            "controls": ", ".join(design_a["fixed_effects"]) + " (fixed effects)",
            "inference": "cluster by state",
            "artifact": f"registry/estimates/{vintage}/estimates.json",
        },
        {
            "design": "B",
            "estimator": design_b["estimator"],
            "outcome": "; ".join(f"national {o['column']} (log cumulative change)" for o in design_b["outcomes"]),
            "treatment": "Δ log Brent",
            "controls": ", ".join(design_b["controls"]),
            "inference": f"Newey–West, {design_b['inference']['maxlags']} lags",
            "artifact": f"registry/estimates/{vintage}/estimates.json",
        },
        {
            "design": "C",
            "estimator": design_c_spec["estimator"]["name"],
            "outcome": "u5mr (annual native observations)",
            "treatment": "transition window (1 July year rule)",
            "controls": "simplex donor weights; screening predictors as balance only",
            "inference": "in-space and in-time placebos",
            "artifact": f"registry/design_c/{vintage}/design_c.json",
        },
        {
            "design": "Grid",
            "estimator": "PPML (A) and local projection (B)",
            "outcome": "three A outcomes, national FAAC",
            "treatment": "log FAAC at lag 0–2; Δ log Brent",
            "controls": f"{len(grid['design_a']['axes']['adjustment_set'])} adjustment sets (A); "
                        f"{len(grid['design_b']['axes']['controls'])} control sets (B)",
            "inference": "clustered by state; Newey–West",
            "artifact": f"registry/robustness/{vintage}/robustness.json",
        },
    ]

    return {
        "vintage": vintage,
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "guide": guide,
        "technical": tech,
        "variables": variables,
        "models": models,
        "administrations": admins["administrations"],
        "portraits": portraits,
        "tenure_min_native": tenure_min_native,
        "outcomes": outcomes,
        "counts": counts,
        "fills": fills,
        "spine": spine,
        "design_results": design_results,
        "comparisons_generated_at": comparisons.get("generated_at"),
        "changepoints_generated_at": changepoints.get("generated_at"),
        "answer_sets": load(root / "registry" / "rag" / vintage / "answer_eval.json").get("sets", {}),
        "answer_questions": [q["question"] for q in
                             (load(root / "registry" / "rag" / vintage / "answer_eval.json").get("questions") or [])],
        "tenure": tenure,
        "events": load_events(root),
    }


def load_events(root: Path) -> dict[str, dict]:
    """The sourced event photographs, keyed by slug. The manifest is the licence record: a page may only show
    an event it names, and an event with no row here is simply not drawn."""
    path = root / "site" / "assets" / "events" / "manifest.json"
    if not path.exists():
        return {}
    return {row["slug"]: row for row in load(path).get("events") or []}


def event_strip(ctx: dict, key: str) -> str:
    """The header collage: three photographs of national events, decorative so the page carries no caption.
    The licences' attribution travels underneath, folded into a disclosure rather than printed."""
    trio = (ctx["guide"].get("event_strip") or {}).get(key) or []
    rows = [ctx["events"][slug] for slug in trio if slug in ctx["events"]]
    if not rows:
        return ""
    items = "".join(
        f'<li><img src="../assets/events/{html.escape(row["file"])}" '
        f'style="object-position:{html.escape(row.get("focus") or "50% 32%")}" alt=""></li>' for row in rows)
    credits = "".join(f"<li>{html.escape(row['attribution'])}</li>" for row in rows)
    return (f'<section class="event-strip"><ul>{items}</ul>'
            f'<details class="strip-credits"><summary>Photo credits</summary>'
            f'<ul class="credit-list">{credits}</ul></details></section>')


NAV_LABELS: dict[str, str] = {}
# Set in main(): the registry vintage and the build time, used to version the asset URLs so a rebuild is
# never served stale from a reader's browser cache.
BUILD_VINTAGE = "vintage-set-by-main"
BUILD_STAMP = 0
ASSET_STAMP = "0"


def page(title: str, depth: int, body: str, data: dict | None = None, wide: bool = False,
         nav_active: str = "") -> str:
    prefix = "../" * depth
    home = prefix or "./"
    # Asset URLs carry the registry vintage and the build time, so every rebuild ships new behaviour and
    # styles and no browser serves last build's script to a reader who hard-refreshes the page only.
    stamp = ASSET_STAMP
    payload = ""
    if data is not None:
        payload = ('<script id="page-data" type="application/json">'
                   + json.dumps(data, ensure_ascii=False) + "</script>")
    nav_items = []
    for key in ("home", "about", "methodology", "technical", "ask"):
        href = home if key == "home" else f"{prefix}{key}/"
        current = ' aria-current="page"' if nav_active == key else ""
        nav_items.append(f'<li><a href="{href}"{current}>{html.escape(NAV_LABELS.get(key, key.title()))}</a></li>')
    nav = (f'<nav class="topnav" aria-label="Primary">'
           f'<a class="wordmark" href="{home}">Causal Presidents</a>'
           f'<ul>{"".join(nav_items)}</ul></nav>')
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<link rel="stylesheet" href="{prefix}assets/style.css?v={stamp}">
</head>
<body data-page="{html.escape(title)}"{' class="wide-page"' if wide else ''}>
{nav}
{body}
{payload}
<script src="{prefix}assets/app.js?v={stamp}" defer></script>
</body>
</html>
"""


# ------------------------------------------------------------------------------------------------------------
# Cover: large photographs, moving horizontally
# ------------------------------------------------------------------------------------------------------------
def render_cover(ctx: dict) -> str:
    guide = ctx["guide"]
    cover = guide["cover"]
    initials = {"obasanjo": "OO", "yaradua": "MY", "jonathan": "GJ", "buhari": "MB", "tinubu": "BT"}
    parties = guide["parties"]
    supplied = ctx["portraits"]
    slides = []
    for admin in ctx["administrations"]:
        slug = admin["slug"]
        end = admin["end_date"] or "present"
        credit = supplied.get(slug)
        if credit:
            party = parties[admin["party"]]
            portrait = (f'<img src="assets/presidents/{slug}.jpg" '
                        f'alt="Portrait of {html.escape(admin["president"])}">'
                        f'<figcaption class="party-tag" title="{html.escape(party["name"])}">'
                        f'{party_emblem(admin["party"])}<span>{html.escape(admin["party"])}</span></figcaption>')
            figure_open = (f'<figure class="slide-figure has-portrait" '
                           f'style="--party-bands: {party_bands(party["bands"])}">')
        else:
            portrait = (f'<div class="frame frame-empty"><span class="initials">{initials.get(slug, "")}</span>'
                        f'<span class="frame-note">image not supplied</span></div>')
            figure_open = '<figure class="slide-figure">'
        slides.append(f"""<li class="president">
  {figure_open}{portrait}</figure>
  <div class="slide-body">
    <p class="slide-name">{html.escape(admin["president"])}</p>
    <p class="slide-meta">{html.escape(admin["party"])} · {admin["start_date"][:4]}–{end[:4]}
      · {admin["n_terms"]} term{"s" if admin["n_terms"] > 1 else ""}</p>
    <p class="slide-note">{html.escape(admin["note"] or "")}</p>
  </div>
</li>""")

    paragraphs = "".join(f"<p>{md(fill_text(p, ctx['fills']))}</p>" for p in cover["paragraphs"])
    credits = ""
    if supplied:
        items = "".join(f"<li>{html.escape(row['attribution_text'])}</li>" for row in supplied.values())
        credits = (f'<details class="about credits"><summary>{html.escape(cover["portrait_credits"])}</summary>'
                   f'<ul class="credit-list">{items}</ul></details>')
    body = f"""<main class="cover">
  <header class="cover-head">
    <div class="cover-lead">
      <p class="eyebrow">{html.escape(cover['eyebrow'])}</p>
      <h1>{html.escape(cover['title'])}</h1>
      <p class="caption">{html.escape(cover['caption'])}<br><span class="instruction">{html.escape(cover['instruction'])}</span></p>
    </div>
    <div class="cover-cta">
      <div class="cover-stat">
        <p class="cover-count">{html.escape(fill_text(cover['models_line'], ctx['fills']))}</p>
        <p class="cover-scope">{html.escape(fill_text(cover['scope_line'], ctx['fills']))}</p>
      </div>
      <p class="cover-methods">{html.escape(cover['methods_line'])}</p>
      <p class="cover-span">{html.escape(fill_text(cover['span_line'], ctx['fills']))}</p>
      <a class="primary" href="study/">Begin</a>
    </div>
  </header>

  <section class="presidents" aria-label="{html.escape(cover['rail_heading'])}">
    <div class="flag-band" style="--flag-bands: {party_bands(ctx['guide']['national_flag']['bands'])}" aria-hidden="true"></div>
    <ul class="president-grid">
{''.join(slides)}
    </ul>
  </section>

  <footer class="cover-foot">
    <div class="field-note">
      {''.join(f'<p>{html.escape(line)}</p>' for line in cover["premise_lines"])}
    </div>
    <details class="about">
      <summary>About this study</summary>
      <div class="prose">{paragraphs}
      </div>
    </details>
    {credits}
    <p class="vintage">Registry vintage {ctx['vintage']} · built {ctx['generated_at'][:16].replace('T', ' ')}</p>
  </footer>
</main>
"""
    return page("Causal Presidents", 0, body, nav_active="home")


# ------------------------------------------------------------------------------------------------------------
# Flow shell
# ------------------------------------------------------------------------------------------------------------
def flow_steps(guide: dict) -> list[tuple[str, str]]:
    """The six in-flow steps, in order. The cover is the door, not a step: numbering it would make every
    screen say "of seven" against a spec that names six."""
    return [(name, label) for name, label in guide["steps"].items() if name != "cover"]


def steps_html(guide: dict, key: str) -> str:
    """The step rail: numbered dots, all in the site green with white words, the current step darker and ringed."""
    order = flow_steps(guide)
    position = [name for name, _label in order].index(key)
    items = []
    for index, (name, label) in enumerate(order, start=1):
        state = " is-active" if name == key else (" is-done" if index <= position else "")
        current = ' aria-current="step"' if name == key else ""
        items.append(f'<li class="step{state}"{current}><span class="step-dot">{index}</span>'
                     f'<span class="step-label">{html.escape(label)}</span></li>')
    return f'<ol class="steps" aria-label="Steps">{"".join(items)}</ol>'


def step_counter(guide: dict, key: str) -> str:
    order = [name for name, _label in flow_steps(guide)]
    return f"step {order.index(key) + 1} of {len(order)}"


def plain_gloss(guide: dict, outcome_id: str) -> str:
    """What the outcome counts, in words. The build stops rather than show a bare label: the study screen is
    where a reader decides what to study, and a metric name alone does not say what it measures."""
    try:
        return guide["outcome_plain"][outcome_id]
    except KeyError as exc:
        raise SystemExit(f"guide.yml carries no plain gloss for the outcome {outcome_id!r}") from exc


def flow_page(ctx: dict, key: str, title: str, heading: str, intro: str, note: str | None,
              blocks: str, back: str, forward: str | None, extra_head: str = "",
              wide: bool = False, centre: str | None = None) -> str:
    guide = ctx["guide"]
    nxt = (f'<a class="primary" id="next" href="../{forward}/" aria-disabled="true">{html.escape(guide["labels"]["next"])}</a>'
           if forward else "")
    middle = centre or ('<span class="control-note" id="count-note">'
                        'Pick at least one outcome on the first screen.</span>')
    body = f"""<main class="flow">
  {event_strip(ctx, key)}
  <header class="flow-head">
    {steps_html(guide, key)}
    <p class="eyebrow"><a href="../">Causal Presidents</a> · {step_counter(guide, key)}</p>
    <h1>{html.escape(heading)}</h1>
    {f'<p class="caption">{html.escape(intro)}</p>' if intro else ''}
    {f'<p class="note">{md(note)}</p>' if note else ''}
    {extra_head}
  </header>
  <div class="blocks">{blocks}</div>
  <footer class="controls">
    <a class="ghost" href="../{back}/">{html.escape(guide["labels"]["back"])}</a>
    {middle}
    {nxt}
  </footer>
  <p class="vintage">Registry vintage {ctx['vintage']}</p>
</main>
"""
    return page(title, 1, body, data={"outcomes": [o["id"] for o in ctx["outcomes"]]}, wide=wide)


def outcome_shell(outcome: dict, inner: str, tone: str | None = None, kind: str | None = None) -> str:
    tone_class = f" tone-{tone}" if tone else ""
    kind_class = f" kind-{kind}" if kind else ""
    return f"""<article class="block{tone_class}{kind_class}" data-outcome="{outcome['id']}" hidden>
  <header class="block-head">
    <h2>{html.escape(outcome['label'])}</h2>
  </header>
{inner}
</article>"""


# ------------------------------------------------------------------------------------------------------------
# Screen 1: study
# ------------------------------------------------------------------------------------------------------------
def render_study(ctx: dict) -> str:
    guide = ctx["guide"]
    study = guide["study"]
    sections = []
    for domain in DOMAIN_ORDER:
        rows = [o for o in ctx["outcomes"] if o["domain"] == domain]
        if not rows:
            continue
        items = "".join(
            f"""<li class="choice">
  <label>
    <input type="checkbox" name="outcome" value="{o['id']}" id="pick-{o['id']}">
    <span class="choice-label">{html.escape(o['label'])} <span class="choice-plain">({html.escape(plain_gloss(guide, o['id']))})</span></span>
    <span class="choice-meta">{html.escape(o['unit'])} · {html.escape(o['direction'])} · {html.escape(o['coverage'])}</span>
  </label>
</li>"""
            for o in rows)
        sections.append(f"""<section class="domain" data-domain="{domain}">
  <h2>{html.escape(DOMAIN_LABEL[domain])}</h2>
  <ul class="choices">{items}</ul>
</section>""")
    options = "".join(f'<option value="{domain}">{html.escape(DOMAIN_LABEL[domain])}</option>'
                      for domain in DOMAIN_ORDER)
    picker = f"""  <div class="domain-picker">
    <label for="domain-select">{html.escape(study['category_label'])}</label>
    <select id="domain-select" name="domain">{options}</select>
  </div>"""
    # The coverage words are explained once, on a legend line, rather than nine or twelve times in the option
    # meta: the row carries the word, the legend carries what the word means. Both still read from the keys,
    # so the legend cannot drift from the rows.
    legend = " · ".join(
        f"{html.escape(term(guide, 'coverage', k))} ({html.escape(term(guide, 'coverage_note', k))})"
        for k in ("ok", "partial", "declared_gap"))
    body = f"""<main class="flow">
  {event_strip(ctx, "study")}
  <header class="flow-head">
    {steps_html(guide, "study")}
    <p class="eyebrow"><a href="../">Causal Presidents</a> · {step_counter(guide, "study")}</p>
    <h1>{html.escape(study['heading'])}</h1>
    <p class="caption">{html.escape(study['intro'])}</p>
    <p class="note">Coverage: {legend}</p>
  </header>
{picker}
  <div class="domains">{''.join(sections)}</div>
  <footer class="controls">
    <a class="ghost" href="../">{html.escape(guide['labels']['back'])}</a>
    <span class="control-note" id="next-note">{html.escape(study['next_disabled'])}</span>
    <a class="primary is-disabled" id="next" href="#" aria-disabled="true">{html.escape(study['next'])}</a>
  </footer>
  <p class="vintage">Registry vintage {ctx['vintage']}</p>
</main>
"""
    return page("What do you want to study?", 1, body, data={"outcomes": [o["id"] for o in ctx["outcomes"]]})


# ------------------------------------------------------------------------------------------------------------
# Screen 2: the comparison the app chose
# ------------------------------------------------------------------------------------------------------------
def render_compare(ctx: dict) -> str:
    guide = ctx["guide"]
    compare = guide["compare"]
    blocks = []
    for outcome in ctx["outcomes"]:
        c = outcome["compare"]
        # The card's shape follows its kind, because the four kinds say different things at a glance: a
        # card with a published number carries a pointer chip to it; a card whose design ran but found
        # nothing solid reads as a dashed absence; a channel card wears the channel chip; a declared gap
        # is visibly a hole. One sentence still carries comparison and assumption, the pill rides inline,
        # and a line follows only where the reason is the content.
        chip = ""
        if c["kind"] == "number":
            chip = f'<span class="stamp stamp-ahead">{html.escape(compare["number_chip"])}</span>'
        elif c["kind"] == "described":
            chip = f'<span class="stamp stamp-absent">{html.escape(compare["no_number_stamp"])}</span>'
        elif c["kind"] == "channel":
            chip = f'<span class="stamp stamp-channel">{html.escape(compare["channel_chip"])}</span>'
        elif c["kind"] == "gap":
            chip = f'<span class="stamp stamp-gap">{html.escape(compare["gap_stamp"])}</span>'
        tail = ""
        if c["kind"] != "number" and c["reason_sentence"]:
            tail = f'<p class="reason">{html.escape(c["reason_sentence"])}</p>'
        inner = f"""
  <p class="chosen"><strong>{c['design']} · {html.escape(c['design_short'])}</strong>: {html.escape(c['plain'])}, assuming {html.escape(c['assumes'])}. <span class="pill {c['tone']}">{html.escape(c['word'])}</span>{chip}</p>
  {tail}"""
        blocks.append(outcome_shell(outcome, inner, tone=c["tone"], kind=c["kind"]))
    return flow_page(ctx, "compare", "What gets compared", compare["heading"],
                     "", None, "".join(blocks), back="study", forward="graph")


# ------------------------------------------------------------------------------------------------------------
# Screen 3: the assumption, drawn
# ------------------------------------------------------------------------------------------------------------
def render_graph(ctx: dict) -> str:
    guide = ctx["guide"]
    labels = guide["labels"]
    blocks = []
    for outcome in ctx["outcomes"]:
        g = outcome["graph"]
        adjustment = "".join(f"<li>{html.escape(item)}</li>" for item in g["adjustment"]) or "<li>none</li>"
        absent = "".join(f"<li>{html.escape(item)}</li>" for item in g["absent"]) or "<li>none</li>"
        caveats = "".join(f"<li>{html.escape(item)}</li>" for item in g["cannot_rule_out"]) or "<li>none</li>"
        alternatives = "".join(
            f"""<details class="alt">
  <summary><span class="pill {a['tone']}">{html.escape(a['word'])}</span>
    {a['design']} · {html.escape(a['design_name'])}
  </summary>
  <p class="assumes">{html.escape(a['assumption'] or 'not stated')}</p>
  <img class="graph" src="../{a['svg']}" alt="Assumed causal graph for {html.escape(outcome['label'])} under Design {a['design']}">
</details>"""
            for a in g["alternatives"])
        inner = f"""
  <p class="chosen"><strong>{g['design']} · {html.escape(g['design_name'])}</strong></p>
  <figure class="graph-figure">
    <img class="graph" src="../{g['svg']}" alt="Assumed causal graph for {html.escape(outcome['label'])} under Design {g['design']}">
  </figure>
  <div class="columns">
    <div class="col">
      <h3>{html.escape(labels['graph_assumption'])}</h3>
      <p class="assumption">{html.escape(g['assumption'])}</p>
    </div>
    <div class="col">
      <h4>{html.escape(labels['adjustment_heading'])} <span class="gloss">({html.escape(labels['adjustment_gloss'])})</span></h4>
      <ul class="tight">{adjustment}</ul>
      <h4>{html.escape(labels['absent_heading'])} <span class="gloss">({html.escape(labels['absent_gloss'])})</span></h4>
      <ul class="tight">{absent}</ul>
      <h4>{html.escape(labels['cannot_heading'])} <span class="gloss">({html.escape(labels['cannot_gloss'])})</span></h4>
      <ul class="tight">{caveats}</ul>
    </div>
  </div>
  <details class="alt-group">
    <summary>{html.escape(labels['alternatives_heading'])}</summary>
    {alternatives}
  </details>"""
        blocks.append(outcome_shell(outcome, inner))
    return flow_page(ctx, "graph", "The assumption, drawn", labels["graph_heading"],
                     "This is the graph the chosen comparison rests on. If the assumption is false, the number "
                     "below it is not an effect.", labels["graph_caption"], "".join(blocks), back="compare",
                     forward="estimates", wide=True)


# ------------------------------------------------------------------------------------------------------------
# Screen 4: the estimate, in plain words
# ------------------------------------------------------------------------------------------------------------
def widest_trend_sentence(ctx: dict, outcome: dict) -> str | None:
    """The largest pairwise contrast on the outcome's own trend, in years rather than surnames.

    The estimate screen must not name a president (tests/verify_site.py enforces it, and the rule is the
    artifact's own: windows are keyed by tenure). So the contrast is rebuilt from the artifact's years and
    its published difference and range, never from its `reading`, which carries names.
    """
    row = (ctx.get("tenure") or {}).get(outcome["id"])
    if not row or row.get("status") != "described":
        return None
    contrasts = row.get("contrasts") or []
    if not contrasts:
        return None
    widest = max(contrasts, key=lambda c: abs(float(c["difference"])))
    spans = {t["president"]: (str(t["start"])[:4], str(t["end"])[:4])
             for t in row["tenures"] if t.get("status") == "described"}
    first, second = spans.get(widest["a"]), spans.get(widest["b"])
    if not first or not second:
        return None
    low, high = widest["range"]
    unit = (outcome.get("unit") or "").strip()
    difference = float(widest["difference"])
    # "count" is a placeholder unit rather than a measurement, so it is phrased as a change in a count.
    # Everything else keeps the unit exactly as the artifact publishes it, because the chart page prints the
    # same contrast with the same string and two screens must not describe one contrast two ways.
    quantity = (f"{difference:+.2f} in the count" if unit.lower() in {"count", "counts", ""}
                else f"{difference:+.2f} {unit}")
    return (f"the widest gap from the trend is between {first[0]}\u2013{first[1]} and "
            f"{second[0]}\u2013{second[1]}: {quantity} "
            f"(range {float(low):+.2f} to {float(high):+.2f}).")


def sparse_series_sentence(ctx: dict, outcome: dict, minimum: int) -> str | None:
    """For an outcome with a series but too few observed years: how many there are, and when.

    The card already refuses, but "there is no usable series" overstates it, and a reader deserves the count.
    Both numbers come from the changepoint artifact, which measures the same density the tenure and comparison
    layers refuse on.
    """
    block = (outcome.get("breaks") or {})
    if block.get("status") != "refused":
        return None
    refused = block.get("refused") or {}
    if refused.get("reason") != "too_few_native_observations":
        return None
    span = block.get("span") or {}
    native = block.get("native")
    if not native or not span.get("first") or not span.get("last"):
        return None
    frequency = str(outcome.get("frequency") or outcome.get("native_frequency") or "").lower()
    unit = "months" if "month" in frequency else "years"
    return (f"the series is observed in {int(native)} {unit}, "
            f"{str(span['first'])[:4]} to {str(span['last'])[:4]}, and a trend needs {minimum}.")


def render_estimates(ctx: dict) -> str:
    guide = ctx["guide"]
    results = guide["results"]
    blocks = []
    for outcome in ctx["outcomes"]:
        e = outcome["estimate"]
        # The trend description is a property of the outcome's series, not of the design, so it appears on
        # every card whose outcome has one, whatever the card's own verdict: 8 of the 12 do. The label keeps
        # it from being read as the estimate, which is the whole reason it is allowed here at all.
        trend = widest_trend_sentence(ctx, outcome)
        trend_line = (f'<p class="trend">{html.escape(results["trend_label"])}'
                      f'{html.escape(trend)}</p>' if trend else "")
        if not trend_line:
            # No trend description exists, but the series may still have a measurable density. Where it does,
            # say how much is there rather than leaving "no series" standing in for "too few points".
            sparse = sparse_series_sentence(ctx, outcome, ctx.get("tenure_min_native", 20))
            if sparse:
                trend_line = (f'<p class="trend">{html.escape(results["sparse_label"])}'
                              f'{html.escape(sparse)}</p>')
        # The expander carries the technique, not the bookkeeping: the artifact path and the rows that
        # merely repeat the card's own header stay out. Provenance lives once, on the methodology page.
        provenance_keys = {"artifact", "spec_index", "design", "outcome"}
        if e["kind"] == "number":
            spec = e["spec"]
            n = e["numbers"]
            # The published card leads with the number itself; the interval rides beside it as its
            # qualifier, the sample keeps the footing, and the verdict and the check that decided it
            # carry the honesty layer under the figure, not after it.
            them = "".join(f"<p>{html.escape(line)}</p>" for line in e["plain"])
            channel = (f'<p class="channel-note">{html.escape(results["channel_note"])}</p>'
                       if e["channel_level"] else "")
            rows = "".join(
                f"<li><span class='k'>{html.escape(key.replace('_', ' '))}</span>"
                f"<span class='v'>{html.escape(str(value))}</span></li>"
                for key, value in spec.items()
                if value is not None and key not in provenance_keys)
            inner = f"""
  <p class="status-line"><span class="pill {e['tone']}">{html.escape(e['status_word'])}</span></p>
  <p class="num-hero"><span class="figure">{html.escape(n['coefficient'])}</span>
  <span class="qual">95 % interval from {html.escape(n['ci_low'])} to {html.escape(n['ci_high'])}</span></p>
  <div class="plain">{them}</div>
  {channel}
  {trend_line}
  <details class="technical">
    <summary>{html.escape(results['expander'])}</summary>
    <ul class="spec-list">{rows}</ul>
  </details>"""
        elif e["kind"] == "described":
            # The design ran and was not identified: the card reads as an honest absence, dashed, with its
            # one sentence and, below it, the widest description the series itself carries. The pointer to
            # the design-level results now lives in the footer, between Back and Next, so the card stays
            # short and the link is reachable from every card rather than repeated under each.
            inner = f"""
  <p class="status-line"><span class="pill {e['tone']}">{html.escape(e['status_word'])}</span>
  <span class="stamp stamp-absent">{html.escape(results['no_number_stamp'])}</span></p>
  <p class="reason">{html.escape(e['reason_sentence'])}</p>
  {trend_line}"""
        elif e["kind"] == "channel":
            # The design's number is about the money channel: a chip names it once and the sentence says why
            # no outcome number follows. The design-level pointer is in the footer.
            inner = f"""
  <p class="status-line"><span class="pill {e['tone']}">{html.escape(e['status_word'])}</span>
  <span class="stamp stamp-channel">{html.escape(results['channel_chip'])}</span></p>
  <p class="reason">{html.escape(e['reason_sentence'])}</p>
  {trend_line}"""
        else:
            # A declared gap: the outcome has no series here, which is an absence of data, not a finding
            # of zero. The stamp says so before the reason does.
            inner = f"""
  <p class="status-line"><span class="pill {e['tone']}">{html.escape(e['status_word'])}</span>
  <span class="stamp stamp-gap">{html.escape(results['gap_stamp'])}</span></p>
  <p class="reason">{html.escape(e['reason_sentence'] or e['reason_detail'] or "")}</p>
  {trend_line}"""
        blocks.append(outcome_shell(outcome, inner, tone=e["tone"], kind=e["kind"]))
    # The page leads with the outcomes that carry a number. When the selection holds at least one, the
    # others collapse behind this one line (their reasons are on the comparisons screen); when it holds
    # none, every chosen card still shows its one-line reason. app.js fills the counts.
    summary = (f'<p class="note" id="estimate-summary" hidden '
               f'data-template="{html.escape(results["summary"])}"></p>')
    # The design-level results sit in the footer, centred between Back and Next, because a reader who
    # wants the gap windows and placebos should not have to find the same link under nine cards. The count
    # note stays beneath it so the footer still says what was chosen.
    centre = ('<span class="controls-centre">'
              f'<a class="controls-link" href="../designs/">{html.escape(results["designs_link"])}</a>'
              '<span class="control-note" id="count-note"></span></span>')
    return flow_page(ctx, "estimates", results["heading"], results["heading"],
                     "", None, "".join(blocks), back="graph", forward="chart",
                     extra_head=summary, centre=centre)


# ------------------------------------------------------------------------------------------------------------
# Screen 5: the chart, described
# ------------------------------------------------------------------------------------------------------------
def render_tenure(outcome: dict, ctx: dict, guide: dict) -> str:
    """Stage 8g: the outcome's deviation from a tenure-blind trend, and the largest pairwise contrast."""
    copy = guide["tenure"]
    row = (ctx.get("tenure") or {}).get(outcome["id"])
    if not row:
        return ""
    unit = outcome.get("unit")
    if row["status"] != "described":
        # The same heading and the same reading style as a table, with the reason in place of the table.
        message = fill_text(copy["refused"], {"minimum": ctx.get("tenure_min_native", 20),
                                              "points": row["n_native"]})
        return (f'<section class="tenure"><h3>{html.escape(copy["heading"])}</h3>'
                f'<p class="findings">{html.escape(message)}</p></section>')
    described = [t for t in row["tenures"] if t["status"] == "described"]
    # The change column compares each president with the one before him. The comparison comes from the
    # artifact's own pairwise contrasts (difference = earlier mean_deviation - later, with the range
    # across the declared spans). A change is claimed only when that published range cannot contain
    # zero; good and bad follow the outcome's own direction (a "lower is better" outcome moves good when
    # the deviation falls), never the president.
    good_sign = 1 if outcome.get("direction", "").startswith("higher") else -1
    contrasts = {}
    for c in row.get("contrasts") or []:
        contrasts[frozenset((c["a"], c["b"]))] = c
    # The counter column is named for what it counts: years for annual series, months for monthly ones.
    frequency = str(outcome.get("native_frequency") or "").lower()
    points_head = copy.get(f"head_points_{frequency}", copy["head_points_default"])
    heads = (f"<th>{html.escape(copy['head_tenure'])}</th><th>{html.escape(copy['head_party'])}</th>"
             f"<th class='num'>{html.escape(points_head)}</th>"
             f"<th class='num'>{html.escape(copy['head_compare'])}</th>"
             f"<th class='num'>{html.escape(copy['head_change'])}</th>")
    body_rows = []
    changed = []
    neutral = []
    prev = None
    for t in described:
        low, high = t["deviation_range"]
        mean = t["mean_deviation"]
        if prev is None:
            compare = copy["change_none"]
            change = copy["change_first"]
        else:
            pair = contrasts.get(frozenset((prev["president"], t["president"])))
            if pair is not None:
                # delta is current minus previous; the contrast stores earlier minus later, and its range
                # is on the same earlier-minus-later scale, so both are flipped together to match.
                if pair["a"] == prev["president"]:
                    delta = -pair["difference"]
                    diff_low, diff_high = -pair["range"][1], -pair["range"][0]
                else:
                    delta = pair["difference"]
                    diff_low, diff_high = pair["range"]
            else:
                delta = mean - prev["mean"]
                diff_low, diff_high = low - prev["high"], high - prev["low"]
            compare = fill_text(copy["change_vs"], {
                "previous": prev["president"].split()[-1],
                "delta": f"{delta:+.2f}",
                "range": f"{diff_low:+.2f} \u2026 {diff_high:+.2f}",
            })
            if diff_low <= 0 <= diff_high:
                change = copy["change_neutral"]
                neutral.append({"previous": prev["president"].split()[-1],
                                "name": t["president"].split()[-1]})
            elif delta * good_sign > 0:
                change = copy["change_good"]
                changed.append({"previous": prev["president"].split()[-1],
                                "name": t["president"].split()[-1], "good": True})
            else:
                change = copy["change_bad"]
                changed.append({"previous": prev["president"].split()[-1],
                                "name": t["president"].split()[-1], "good": False})
        body_rows.append(
            f"<tr><td>{html.escape(t['president'])}</td><td>{html.escape(t['party'])}</td>"
            f"<td class='num'>{t['n_native']}</td>"
            f"<td class='num'>{html.escape(compare)}</td>"
            f"<td class='num'>{html.escape(change)}</td></tr>")
        prev = {"president": t["president"], "low": low, "high": high, "mean": mean}
    body = "".join(body_rows)

    # What this table found, as one short paragraph for a reader meeting it cold.
    furthest = max(described, key=lambda t: abs(t["mean_deviation"]))
    side = copy["side_above"] if furthest["mean_deviation"] > 0 else copy["side_below"]
    finding = [fill_text(copy["finding_furthest"], {
        "president": furthest["president"],
        "value": f"{abs(furthest['mean_deviation']):.2f}",
        "side": side,
    }).replace("  ", " ")]
    if changed:
        items = copy["finding_join"].join(
            fill_text(copy["finding_item"], {
                "name": item["name"],
                "previous": item["previous"],
                "direction": copy["finding_better"] if item["good"] else copy["finding_worse"],
            }) for item in changed)
        finding.append(fill_text(copy["finding_changes"], {"items": items}))
    else:
        finding.append(copy["finding_no_changes"])
    if neutral:
        finding.append(copy["finding_join"].join(
            fill_text(copy["finding_neutral"], {"previous": item["previous"], "name": item["name"]})
            for item in neutral))
    findings_para = " ".join(finding)
    contrast = ""
    if row["contrasts"]:
        best = max(row["contrasts"], key=lambda c: abs(c["difference"]))
        contrast = (f"<p class='note'><strong>{html.escape(copy['contrast_heading'])}.</strong> "
                    f"{html.escape(best['reading'])}.</p>")
    # The unit lives in the note as a short clause, not tacked onto the heading as an acronym.
    unit_clause = ""
    if unit:
        unit_clause = " Figures are percentages." if unit == "%" else f" Figures are in {unit}."
    return f"""<section class="tenure">
  <h3>{html.escape(copy['heading'])}</h3>
  <p class="tech">{html.escape(copy['note'])}{html.escape(unit_clause)}</p>
  <table class="deviation-table"><thead><tr>{heads}</tr></thead><tbody>{body}</tbody></table>
  <p class="findings">{html.escape(findings_para)}</p>
  {contrast}
</section>"""


# ---- the portrait strip: five faces over the bands R drew --------------------------------------------------
#
# The portraits are *decorative here and the guardrail is what makes that true*: empty `alt`, `aria-hidden` on
# the strip, no name, no title, no verdict word, and no text of any kind. They label a time axis the figure
# already labels in words, so a screen reader loses nothing by skipping them. `tests/verify_site.py` asserts
# all four of those properties rather than trusting this comment.
_BAND_FILLS = ("#eef6f0", "#e3efe6")


def band_geometry(svg_path: Path) -> list[dict]:
    """Each administration band's left edge and width, as a fraction of the figure's own width.

    The bands are drawn by R from the base's half-open administration spans and clipped to the panel's window
    (`analysis/R/08_comparisons.R::tenure_bands`). Re-deriving them here from dates would be a second
    computation of the same fact, and the two would eventually disagree about where a band starts. So the
    shaded rects are read back out of the published SVG (the top panel's, the party-by-tenure panel
    that spans the whole window), and those coordinates are the same space the `<img>` is scaled into.
    """
    text = svg_path.read_text(encoding="utf-8")
    view = re.search(r"viewBox='0 0 ([\d.]+) ", text)
    if not view:
        raise SystemExit(f"{svg_path}: no viewBox, so the strip cannot be aligned to it")
    width = float(view.group(1))
    shaded = []
    for rect in re.findall(r"<rect[^>]*>", text):
        fill = re.search(r"fill: (#[0-9A-Fa-f]{6})", rect) or re.search(r"fill='(#[0-9A-Fa-f]{6})'", rect)
        if not fill or fill.group(1).lower() not in _BAND_FILLS:
            continue
        x = re.search(r"x='([\d.]+)'", rect)
        y = re.search(r"y='([\d.]+)'", rect)
        w = re.search(r"width='([\d.]+)'", rect)
        if x and y and w:
            shaded.append((float(y.group(1)), float(x.group(1)), float(w.group(1))))
    if not shaded:
        raise SystemExit(
            f"{svg_path}: no administration bands found. Every time-axis figure draws them from "
            f"{' / '.join(_BAND_FILLS)}; if R changed its shades, the strip must be re-pointed rather than "
            f"silently dropped."
        )
    top = min(entry[0] for entry in shaded)
    bands = sorted((x, w) for y, x, w in shaded if y == top)
    return [{"left": x / width, "width": w / width} for x, w in bands]


def tenure_strip(ctx: dict, svg_path: Path, prefix: str) -> str:
    """The row of portraits above one panel, one portrait per band, placed at the band's own coordinates."""
    bands = band_geometry(svg_path)
    admins = ctx["administrations"]
    if len(bands) != len(admins):
        raise SystemExit(
            f"{svg_path.name}: {len(bands)} administration band(s) in the figure against "
            f"{len(admins)} in the tenure seed, so the strip cannot be paired without guessing"
        )
    cells = []
    for band, admin in zip(bands, admins):
        row = ctx["portraits"].get(admin["slug"])
        if not row:
            # No licence row means no photograph. The cover shows a labelled empty frame; the strip has no
            # room for a label, so the slot stays empty rather than borrowing a face the manifest does not cover.
            continue
        left = band["left"] * 100
        width = band["width"] * 100
        cells.append(
            f'<li style="left:{left:.2f}%;width:{width:.2f}%">'
            f'<img src="{prefix}assets/presidents/{admin["slug"]}.jpg" alt=""></li>'
        )
    if not cells:
        return ""
    return f'<ol class="tenure-strip" aria-hidden="true" data-bands="{len(bands)}">{"".join(cells)}</ol>'


def render_chart(ctx: dict) -> str:
    guide = ctx["guide"]
    groupings = guide["groupings"]
    control = "".join(
        f"<label class='toggle'><input type='radio' name='grouping' value='{key}'"
        f"{' checked' if key == 'party_tenure' else ''}> {html.escape(groupings[key]['plain'])}"
        f" <span class='tech'>({html.escape(groupings[key]['technical'])})</span>"
        + (f" <span class='dose-note tech' hidden>{html.escape(guide['chart']['dose_note'])}</span>"
           if key == "state_dose_quartile" else "")
        + "</label>"
        for key in ("party_tenure", "state_dose_quartile"))
    extra_head = f"""<div class="grouping-control" role="radiogroup" aria-label="Grouping">{control}</div>"""

    blocks = []
    for outcome in ctx["outcomes"]:
        chart = outcome["chart"]
        if not chart:
            blocks.append(outcome_shell(outcome, "<p class='blocker'>No comparison artifact describes this outcome.</p>"))
            continue
        lists = []
        for key in ("party_tenure", "state_dose_quartile"):
            rows = [g for g in chart["groups"] if g["grouping"] == key]
            if rows:
                body = "".join(
                    f"<li><strong>{html.escape(g['plain'])}</strong> <span class='tech'>({html.escape(g['technical'])})</span>"
                    f"<br><span class='tech'>{html.escape(g['caption'])}</span></li>" for g in rows)
                lists.append(f"<div class='group-list' data-grouping='{key}'><ul class='tight'>{body}</ul></div>")
            else:
                lists.append(f"<div class='group-list' data-grouping='{key}' hidden><p class='blocker'>No state "
                             f"grouping is declared for this outcome.</p></div>")
        # The comparison artifact draws both groupings in one tall figure (two stacked panels). When the
        # outcome carries both, the grouping radio turns the figure into a window that slides between the
        # panels, so the same click that switches the numbers list moves the picture: the panels' own split
        # point is read out of the published SVG rather than guessed.
        figure_path = REPO_ROOT / "registry" / "comparisons" / ctx["vintage"] / "figures" / f"{outcome['id']}.svg"
        split = ""
        if chart["has_state"] and figure_path.exists():
            svg_text = figure_path.read_text(encoding="utf-8", errors="replace")
            plain_second = guide["groupings"]["state_dose_quartile"]["plain"]
            y_match = re.search(rf"<text[^>]*y='([0-9.]+)'[^>]*>[^<]*{re.escape(plain_second)}", svg_text)
            box_match = re.search(r"viewBox='[-0-9.]+ [-0-9.]+ [0-9.]+ ([0-9.]+)'", svg_text)
            if y_match and box_match:
                y2, height = float(y_match.group(1)), float(box_match.group(1))
                if height and 0 < y2 < height:
                    split = f' data-split="{max(0.2, (y2 - 8) / height):.4f}"'
        inner = f"""
  <p class="chosen">{html.escape(chart['caption'] or '')}</p>
  <figure class="chart-figure">
    {tenure_strip(ctx, figure_path, "../")}
    <div class="panel-window"{split}>
      <img class="chart" src="../{chart['figure']}" alt="Outcome series grouped for {html.escape(outcome['label'])}">
    </div>
  </figure>
  <h3>{html.escape(guide['results']['groups_heading'])}</h3>
  {''.join(lists)}
  {render_breaks(outcome, ctx, guide)}{render_tenure(outcome, ctx, guide)}"""
        blocks.append(outcome_shell(outcome, inner))

    # The licence record travels with the faces. The cover carries the full list; the chart repeats it because
    # these are the same five photographs on a second page, and a credit that only exists on another URL is not
    # a credit beside the image.
    supplied = ctx["portraits"]
    credits = ""
    if supplied:
        items = "".join(f"<li>{html.escape(row['attribution_text'])}</li>" for row in supplied.values())
        credits = (f'<details class="about credits"><summary>'
                   f'{html.escape(guide["cover"]["portrait_credits"])}</summary>'
                   f'<ul class="credit-list">{items}</ul></details>')

    return flow_page(ctx, "chart", "The comparison, drawn", guide["labels"]["chart_heading"],
                     "Two ways to look at the same outcome: by who was in power, and by how much money a "
                     "state received, where the outcome is measured state by state.",
                     guide["results"]["stamp_note"], "".join(blocks) + credits,
                     back="estimates", forward="ask", extra_head=extra_head, wide=True)


# ------------------------------------------------------------------------------------------------------------
# Screen 6: ask the corpus, in the browser
# ------------------------------------------------------------------------------------------------------------
def render_ask(ctx: dict) -> str:
    guide = ctx["guide"]
    copy = guide["ask"]
    overall = (ctx.get("answer_sets") or {}).get("all") or {}
    measured = ""
    if overall.get("n"):
        measured = fill_text(copy["measured"], {"answered": overall["answered"], "total": overall["n"]})
    body = f"""<main class="flow ask">
  {event_strip(ctx, "ask")}
  <header class="flow-head">
    {steps_html(guide, "ask")}
    <p class="eyebrow"><a href="../">Causal Presidents</a> · {step_counter(guide, "ask")}</p>
    <h1>{html.escape(copy['heading'])}</h1>
    <p class="caption">{html.escape(copy['intro'])}</p>
    {f'<p class="note">{html.escape(measured)}</p>' if measured else ''}
  </header>
  <form class="ask-form" id="ask-form" autocomplete="off">
    <label for="ask-input">{html.escape(copy['input_label'])}</label>
    <div class="ask-row">
      <input id="ask-input" name="question" type="text" list="ask-questions"
             placeholder="{html.escape(copy['placeholder'])}" autocomplete="off">
      <datalist id="ask-questions">{''.join(f'<option value="{html.escape(q)}"></option>' for q in ctx.get("answer_questions") or [])}</datalist>
      <button class="primary" type="submit">{html.escape(copy['button'])}</button>
      <button class="ghost" type="button" id="ask-clear">{html.escape(copy['clear'])}</button>
    </div>
  </form>
  <p class="control-note" id="ask-status" role="status">{html.escape(copy['empty'])}</p>
  <section class="ask-answer" id="ask-answer" hidden aria-live="polite"></section>
  <footer class="controls">
    <a class="ghost" href="../chart/">{html.escape(guide['labels']['back'])}</a>
    <a class="primary" href="../designs/">{html.escape(copy['deeper'])}</a>
  </footer>
  <p class="vintage">Registry vintage {ctx['vintage']}</p>
</main>
<script type="module" src="../assets/ask.mjs?v={ASSET_STAMP}"></script>"""
    return page("Ask the corpus", 1, body, nav_active="ask")


# ------------------------------------------------------------------------------------------------------------
# Screen 6b: the design-level results
# ------------------------------------------------------------------------------------------------------------
def render_designs(ctx: dict) -> str:
    """One reader for the three figures Stage 8 published. Not a flow step: it is not per-outcome, so it sits
    outside the selection the URL carries and is linked from the estimate screen and the Ask footer."""
    guide = ctx["guide"]
    copy = guide["design_results"]
    d = ctx["design_results"]
    names = {key: guide["designs"][key]["name"] for key in ("A", "B", "C")}

    def figure(block: dict, alt: str) -> str:
        return f"""<figure class="chart-figure">
    <img class="chart" src="../{block['figure']}" alt="{html.escape(alt)}">
    <figcaption>{md(block['layout'])}</figcaption>
  </figure>"""

    a_rows = "".join(f"<li>{html.escape(row['line'])}</li>" for row in d["a"]["rows"])
    flips = "".join(f"<li>{html.escape(line)}</li>" for line in d["grid"]["flips"])
    event_rows = "".join(
        f"<li>{html.escape(fill_text(copy['event_line'], row))}</li>" for row in d["events"]["rows"])
    not_claimed = "".join(f"<li>{md(claim)}</li>" for claim in d["events"]["not_claimed"])

    # Design C publishes its own artifact: a synthetic control has no interval, so its gap cannot be a card
    # number. The page prints the windows by year, never by name, and the two solvers side by side, because
    # where they disagree the estimate is a property of the solver and saying so is the point.
    if d["c"]["status"] == "not_run":
        c_section = (f"<h2>{html.escape(copy['not_run_heading'])}</h2>"
                     f"<h3>{html.escape(names['C'])}</h3>"
                     f"<p>{md(d['c']['why'] or '')}</p>"
                     f"<p><span class=\"tech\">{html.escape(copy['next_step'])}</span> "
                     f"{md(d['c']['next_step'] or '')}</p>")
    else:
        counts = d["c"]["counts"]
        groups_html = []
        for group in d["c"].get("groups") or []:
            head = f"<h4>{html.escape(group['label'])}"
            if group.get("unit"):
                head += f" <span class=\"tech\">({html.escape(group['unit'])})</span>"
            head += "</h4>"
            if group["rows"]:
                body = "<ul class=\"tight\">" + "".join(
                    f"<li>{html.escape(fill_text(copy['c_row'], row))}</li>" for row in group["rows"]) + "</ul>"
            else:
                body = f"<p class=\"blocker\">{html.escape(copy['c_refused_outcome'])}</p>"
            groups_html.append(head + body)
        c_section = (
            f"<h2>{html.escape(copy['c_heading'])}</h2>"
            f"<h3>{html.escape(names['C'])}</h3>"
            f"<p class=\"status-line\"><span class=\"tech\">{html.escape(copy['verdict_label'])}</span> "
            f"<strong>{html.escape(d['c']['status'])}</strong></p>"
            f"<p>{html.escape(fill_text(copy['c_intro'], counts))}</p>"
            f"<p>{html.escape(copy['c_refusal_note'])}</p>"
            + "".join(groups_html)
            + f"<p class=\"note\">{html.escape(copy['c_note'])}</p>")

    body = f"""<main class="flow designs">
  {event_strip(ctx, "designs")}
  <header class="flow-head">
    <p class="eyebrow"><a href="../">Causal Presidents</a> · the design-level results</p>
    <h1>{html.escape(copy['heading'])}</h1>
    <p class="caption">{html.escape(copy['intro'])}</p>
    <p class="note">{html.escape(copy['figure_note'])}</p>
  </header>

  <section class="block design-section">
    <h2>{html.escape(copy['published_heading'])}</h2>
    {figure(d['forest'], 'Forest plot of the published estimates, one panel per design, with each decisive check drawn hollow')}
    <h3>{html.escape(names['A'])}</h3>
    <p class="status-line"><span class="tech">{html.escape(copy['verdict_label'])}</span>
       <strong>{html.escape(d['a']['status'])}</strong></p>
    <p class="blocker">{md(d['a']['failed_check'])}</p>
    <ul class="tight">{a_rows}</ul>
    <h4>{html.escape(copy['checks_heading'])}</h4>
    <ul class="tight"><li>{html.escape(d['a']['mis_timed'])}</li><li>{html.escape(d['a']['lead_shift'])}</li></ul>
    <h3>{html.escape(names['B'])}</h3>
    <p class="status-line"><span class="tech">{html.escape(copy['verdict_label'])}</span>
       <strong>{html.escape(d['b']['status'])}</strong></p>
    <ul class="tight"><li>{html.escape(d['b']['published'])}</li></ul>
  </section>

  <section class="block design-section">
    <h2>{html.escape(copy['grid_heading'])}</h2>
    {figure(d['curve'], 'Specification curve: every fitted specification sorted by coefficient, with the axis levels that produced it')}
    <p>{html.escape(d['grid']['a_support'])}</p>
    <ul class="tight">{flips}</ul>
    <p>{html.escape(d['grid']['b_support'])}</p>
    <p>{html.escape(d['grid']['b_spread'])}</p>
    <p>{html.escape(d['grid']['b_placebo'])}</p>
    <p class="tech">{md(d['grid']['reading'] or '')}</p>
  </section>

  <section class="block design-section">
    {c_section}
  </section>

  <section class="block design-section">
    <h2>{html.escape(copy['transition_heading'])}</h2>
    <p class="note">{html.escape(copy['transition_note'])}</p>
    {figure(d['event_figure'], 'Event study: the conflict series with its transitions marked, and each transition shift against the placebo distribution')}
    <ul class="tight">{event_rows}</ul>
    <details class="technical">
      <summary>{html.escape(copy['rule_heading'])}</summary>
      <p>{md(d['events']['rule'])}</p>
    </details>
    <h3>{html.escape(copy['not_claimed_heading'])}</h3>
    <ul class="tight">{not_claimed}</ul>
  </section>

  <footer class="controls">
    <a class="ghost" href="../ask/">{html.escape(copy['back'])}</a>
    <a class="ghost" href="../">Causal Presidents</a>
  </footer>
  <p class="vintage">Registry vintage {ctx['vintage']}</p>
</main>
"""
    return page("The design-level results", 1, body)


def statement_one(text: str) -> str:
    """The break's own sentence, without the artifact's appended disclaimer: the page header makes the
    not-a-claim point once, so eight blocks do not repeat it. Anything with no marker passes through."""
    marker = "This is a description of the series"
    cut = text.find(marker)
    return text[:cut].rstrip() if 0 < cut else text.rstrip()


def render_breaks(outcome: dict, ctx: dict, guide: dict) -> str:
    """The changepoint half of the chart screen: when the series changes, and the rule that it is not a cause."""
    copy = guide["changepoint"]
    brk = outcome.get("breaks")
    if not brk:
        return ""
    head = f"<h3>{html.escape(copy['heading'])}</h3>"
    if brk["status"] == "refused" or not brk["figure"]:
        # The artifact's own caption is the refusal text; the site adds nothing further.
        return (f"<section class='breaks'>{head}"
                f"<p class='blocker'>{html.escape(brk['caption'])}</p></section>")
    rows = "".join(
        f"<li><strong>{html.escape(r['month'])}</strong>: {html.escape(statement_one(r['statement']))}"
        + (f" <span class='tech'>({html.escape(copy['timing_note'])})</span>" if r["coincides"] else "")
        + "</li>" for r in brk["rows"])
    return f"""<section class="breaks">
  {head}
  <figure class="chart-figure">
    {tenure_strip(ctx, REPO_ROOT / "registry" / "changepoints" / ctx["vintage"] / "figures" / f"{outcome['id']}.svg", "../")}
    <img class="chart" src="../{brk['figure']}" alt="Outcome series with its declared breaks for {html.escape(outcome['label'])}">
  </figure>
  <ul class="tight">{rows}</ul>
  <p class="tech">{html.escape(brk['method'])}</p>
</section>"""


# ------------------------------------------------------------------------------------------------------------
# ------------------------------------------------------------------------------------------------------------
# The two pages outside the flow: About, and Methodology
# ------------------------------------------------------------------------------------------------------------
def mark_doi(text: str) -> str:
    """Escape a reference and mark its bare DOI. Printed, not linked: the site makes no network request, and a
    reader who wants the paper can copy the DOI out of the page."""
    escaped = html.escape(text)
    return re.sub(r"(https?://[^\s<]+)", lambda m: f'<span class="doi">{m.group(1)}</span>', escaped)


def render_about(ctx: dict) -> str:
    about = ctx["guide"]["about"]
    paragraphs = "".join(f"<p>{md(p)}</p>" for p in about["paragraphs"])
    todo = "".join(f"<li>{html.escape(item)}</li>" for item in about["todo"])
    body = f"""<main class="flow page-about">
  {event_strip(ctx, "about")}
  <header class="flow-head">
    <p class="eyebrow">{html.escape(about['eyebrow'])}</p>
    <h1>{html.escape(about['heading'])}</h1>
    <p class="caption">{html.escape(about['intro'])}</p>
  </header>
  <section class="block">
    <div class="prose">{paragraphs}</div>
  </section>
  <section class="block">
    <h2>{html.escape(about['todo_heading'])}</h2>
    <p class="note">{html.escape(about['todo_note'])}</p>
    <ul class="tight">{todo}</ul>
  </section>
  <footer class="controls">
    <a class="ghost" href="../">Causal Presidents</a>
  </footer>
  <p class="vintage">Registry vintage {ctx['vintage']}</p>
</main>
"""
    return page("About", 1, body, nav_active="about")


def render_methodology(ctx: dict) -> str:
    m = ctx["guide"]["methodology"]
    fills = ctx["fills"]
    sections = []
    for section in m["sections"]:
        parts = [f'<section class="method-section" id="{html.escape(section["id"])}">',
                 f'<h2>{html.escape(section["heading"])}</h2>']
        for para in section.get("paragraphs") or []:
            parts.append(f"<p>{md(fill_text(para, fills))}</p>")
        if section.get("bullets"):
            parts.append('<ul class="tight">' + "".join(
                f"<li>{md(fill_text(item, fills))}</li>" for item in section["bullets"]) + "</ul>")
        if section.get("works"):
            parts.append('<dl class="method-works">')
            for work in section["works"]:
                parts.append(f'<dt>{html.escape(work["strand"])}</dt>'
                             f'<dd>{md(work["body"])} <span class="tech">{html.escape(work["refs"])}</span></dd>')
            parts.append("</dl>")
        if section.get("items"):
            parts.append('<dl class="method-items">')
            for item in section["items"]:
                parts.append(f'<dt>{html.escape(item["title"])}</dt>'
                             f'<dd>{md(fill_text(item["body"], fills))}</dd>')
            parts.append("</dl>")
        parts.append("</section>")
        sections.append("".join(parts))

    references = "".join(f"<li>{mark_doi(ref)}</li>" for ref in m["references"])
    # Provenance lives here, once. Every other reader-facing page names what a number says; this is the one
    # page that names the file it comes from, and the Technical page a link away is the detailed version.
    artifacts = sorted({model["artifact"] for model in ctx["models"]})
    file_rows = "".join(f"<li><code>{html.escape(path)}</code></li>" for path in artifacts)
    provenance = f"""<section class="method-section provenance" id="where-the-numbers-live">
  <h2>{html.escape(m['provenance_heading'])}</h2>
  <p>{html.escape(m['provenance_note'])}</p>
  <ul class="tight">{file_rows}</ul>
  <p class="note">{html.escape(m['provenance_link_note']).replace('technical page', '<a href="../technical/">technical page</a>')}</p>
</section>
"""
    body = f"""<main class="flow page-method">
  {event_strip(ctx, "methodology")}
  <header class="flow-head">
    <p class="eyebrow">{html.escape(m['eyebrow'])}</p>
    <h1>{html.escape(m['heading'])}</h1>
    <p class="caption">{html.escape(m['intro'])}</p>
  </header>
  {''.join(sections)}
{provenance}  <section class="method-section references">
    <h2>{html.escape(m['references_heading'])}</h2>
    <p class="note">{html.escape(m['references_note'])}</p>
    <ol>{references}</ol>
  </section>
  <footer class="controls">
    <a class="ghost" href="../">Causal Presidents</a>
  </footer>
  <p class="vintage">Registry vintage {ctx['vintage']}</p>
</main>
"""
    return page("Methodology", 1, body, nav_active="methodology")


def mathify(code: str) -> str:
    """Typeset a declared equation just enough: `x_{a,b}` and `x_t` become subscripts, the rest is literal.
    The equation stays a readable string in the spec, which is what keeps it reviewable there."""
    escaped = html.escape(code)
    escaped = re.sub(r"_\{([^}]*)\}", r"<sub>\1</sub>", escaped)
    escaped = re.sub(r"(?<=[A-Za-zΑ-ωŷΔ])_([A-Za-z0-9])", r"<sub>\1</sub>", escaped)
    return escaped


def render_technical(ctx: dict) -> str:
    t = ctx["technical"]
    page_copy = t["page"]

    def table(columns, rows) -> str:
        head = "".join(f"<th scope='col'>{html.escape(c)}</th>" for c in columns)
        body = "".join("<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>" for row in rows)
        return (f'<div class="table-scroll"><table class="data-table"><thead><tr>{head}</tr></thead>'
                f"<tbody>{body}</tbody></table></div>")

    variable_rows = []
    for v in ctx["variables"]:
        label = html.escape(v["label"])
        if v["outcome"]:
            label += ' <span class="tag">outcome</span>'
        variable_rows.append([
            f"<code>{html.escape(v['id'])}</code>", label, html.escape(v["unit"]),
            html.escape(v["direction"]), html.escape(v["source"]), html.escape(v["coverage"]),
        ])
    variables = table(t["variables"]["columns"], variable_rows)

    design_rows = [[f"<code>{html.escape(row['name'])}</code>", html.escape(row["role"]),
                    html.escape(row["meaning"])] for row in t["design_variables"]["rows"]]
    design_table = table(["Column", "Role", "Meaning"], design_rows)

    model_rows = []
    for m in ctx["models"]:
        model_rows.append([
            f"<strong>{html.escape(m['design'])}</strong>", html.escape(m["estimator"]),
            html.escape(m["outcome"]), f"<code>{html.escape(m['treatment'])}</code>",
            html.escape(m["controls"]), html.escape(m["inference"]),
        ])
    models = table(t["models"]["columns"], model_rows)

    equations = []
    for block in t["equations"]["blocks"]:
        terms = "".join(f"<dt>{mathify(symbol)}</dt><dd>{html.escape(meaning)}</dd>"
                        for symbol, meaning in block["terms"])
        equations.append(
            f'<section class="equation-block"><h3>{html.escape(block["design"])} · '
            f'{html.escape(block["title"])}</h3>'
            f'<pre class="equation">{mathify(block["code"])}</pre>'
            f'<dl class="terms">{terms}</dl></section>')

    body = f"""<main class="flow page-technical">
  {event_strip(ctx, "technical")}
  <header class="flow-head">
    <p class="eyebrow">{html.escape(page_copy['eyebrow'])}</p>
    <h1>{html.escape(page_copy['heading'])}</h1>
    <p class="caption">{html.escape(page_copy['intro'])}</p>
  </header>

  <section class="method-section" id="variables">
    <h2>{html.escape(t['variables']['heading'])}</h2>
    <p class="note">{html.escape(t['variables']['note'])}</p>
    {variables}
  </section>

  <section class="method-section" id="design-variables">
    <h2>{html.escape(t['design_variables']['heading'])}</h2>
    <p class="note">{html.escape(t['design_variables']['note'])}</p>
    {design_table}
  </section>

  <section class="method-section" id="models">
    <h2>{html.escape(t['models']['heading'])}</h2>
    <p class="note">{html.escape(t['models']['note'])}</p>
    {models}
  </section>

  <section class="method-section" id="equations">
    <h2>{html.escape(t['equations']['heading'])}</h2>
    <p class="note">{html.escape(t['equations']['note'])}</p>
    {''.join(equations)}
  </section>

  <footer class="controls">
    <a class="ghost" href="../methodology/">Methodology</a>
    <a class="ghost" href="../">Causal Presidents</a>
  </footer>
  <p class="vintage">Registry vintage {ctx['vintage']}</p>
</main>
"""
    return page("Technical details", 1, body, nav_active="technical", wide=True)


def main() -> int:
    global BUILD_VINTAGE, BUILD_STAMP, ASSET_STAMP
    ctx = build_context(REPO_ROOT)
    NAV_LABELS.update(ctx["guide"]["nav"])
    BUILD_VINTAGE = ctx["vintage"]
    BUILD_STAMP = int(datetime.now(timezone.utc).timestamp())
    ASSET_STAMP = f"{BUILD_VINTAGE}.{BUILD_STAMP}"

    for name in ("", "study", "compare", "graph", "estimates", "chart", "ask", "designs", "about",
                 "methodology", "technical"):
        (DIST / name).mkdir(parents=True, exist_ok=True)
    for name in ("assets", "assets/graphs", "assets/comparisons", "assets/series", "assets/breaks",
                 "assets/designs", "assets/presidents", "assets/events", "data"):
        (DIST / name).mkdir(parents=True, exist_ok=True)

    for name in ("style.css", "app.js", "answer.mjs", "ask.mjs"):
        shutil.copyfile(SITE_SRC / name, DIST / "assets" / name)

    for svg in (REPO_ROOT / "registry" / "dags").glob("*.svg"):
        shutil.copyfile(svg, DIST / "assets" / "graphs" / svg.name)

    comparisons_dir = REPO_ROOT / "registry" / "comparisons" / ctx["vintage"]
    if comparisons_dir.exists():
        for svg in (comparisons_dir / "figures").glob("*.svg"):
            shutil.copyfile(svg, DIST / "assets" / "comparisons" / svg.name)

    breaks_dir = REPO_ROOT / "registry" / "changepoints" / ctx["vintage"] / "figures"
    if breaks_dir.exists():
        for svg in breaks_dir.glob("*.svg"):
            shutil.copyfile(svg, DIST / "assets" / "breaks" / svg.name)

    series_dir = REPO_ROOT / "registry" / "series" / ctx["vintage"] / "figures"
    if series_dir.exists():
        for svg in series_dir.glob("*.svg"):
            shutil.copyfile(svg, DIST / "assets" / "series" / svg.name)

    # The three design-level figures, copied from the vintage directory that holds the artifact describing them.
    design_sources = (
        (ctx["design_results"]["forest"], REPO_ROOT / "registry" / "estimates" / ctx["vintage"]),
        (ctx["design_results"]["curve"], REPO_ROOT / "registry" / "robustness" / ctx["vintage"]),
        (ctx["design_results"]["event_figure"], REPO_ROOT / "registry" / "events" / ctx["vintage"]),
    )
    for block, source in design_sources:
        name = Path(block["figure"]).name
        shutil.copyfile(source / name, DIST / "assets" / "designs" / name)

    # The supplied cover portraits. The manifest is the licence record; a file with no entry is not copied,
    # because a photograph with no licence row is the one thing the cover may not show.
    for row in ctx["portraits"].values():
        source = REPO_ROOT / row["file"]
        shutil.copyfile(source, DIST / "assets" / "presidents" / source.name)

    # The header collage. Drawn only from the events whose manifest rows carry a licence and an attribution.
    for row in ctx["events"].values():
        source = REPO_ROOT / "site" / "assets" / "events" / row["file"]
        shutil.copyfile(source, DIST / "assets" / "events" / source.name)

    (DIST / "index.html").write_text(render_cover(ctx), encoding="utf-8", newline="\n")
    (DIST / "study" / "index.html").write_text(render_study(ctx), encoding="utf-8", newline="\n")
    (DIST / "compare" / "index.html").write_text(render_compare(ctx), encoding="utf-8", newline="\n")
    (DIST / "graph" / "index.html").write_text(render_graph(ctx), encoding="utf-8", newline="\n")
    (DIST / "estimates" / "index.html").write_text(render_estimates(ctx), encoding="utf-8", newline="\n")
    (DIST / "chart" / "index.html").write_text(render_chart(ctx), encoding="utf-8", newline="\n")
    (DIST / "ask" / "index.html").write_text(render_ask(ctx), encoding="utf-8", newline="\n")
    (DIST / "designs" / "index.html").write_text(render_designs(ctx), encoding="utf-8", newline="\n")
    (DIST / "about" / "index.html").write_text(render_about(ctx), encoding="utf-8", newline="\n")
    (DIST / "methodology" / "index.html").write_text(render_methodology(ctx), encoding="utf-8", newline="\n")
    (DIST / "technical" / "index.html").write_text(render_technical(ctx), encoding="utf-8", newline="\n")

    # The answer layer's inputs: the gate's rules, the contract, the glossary and the corpus, emitted from the
    # same specs `app/` reads. Nothing here is a second copy of a rule.
    answers = answer_data(REPO_ROOT, ctx["vintage"])
    (DIST / "data" / "gate.json").write_text(
        json.dumps(answers["gate"], indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    (DIST / "data" / "contract.json").write_text(
        json.dumps(answers["contract"], indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    (DIST / "data" / "corpus.json").write_text(
        json.dumps(answers["corpus"], indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")

    (DIST / "data" / "site.json").write_text(
        json.dumps({
            "vintage": ctx["vintage"],
            "generated_at": ctx["generated_at"],
            "counts": ctx["counts"],
            "spine": ctx["spine"],
            "outcomes": [{k: o[k] for k in ("id", "label", "domain", "unit", "direction", "coverage", "compare")}
                         for o in ctx["outcomes"]],
        }, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8", newline="\n")

    print(f"built {DIST.relative_to(REPO_ROOT)}: {len(PAGES)} pages, {len(ctx['outcomes'])} outcomes, "
          f"vintage {ctx['vintage']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

