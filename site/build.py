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
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
SITE_SRC = REPO_ROOT / "site" / "assets"
DIST = REPO_ROOT / "site" / "dist"

# A-01, in two steps: a design that published a number for this outcome comes first (with its verdict and the
# check that decided it), then the declared Stage 5 order `pass` > `degraded` > `fail` > `not_attempted`. Ranking
# on status alone would put a `degraded` Design B — whose result is about the national money channel, not about
# the outcome on the card — ahead of the one design that published a number for the outcome itself.
RANK = {"pass": 0, "degraded": 1, "fail": 2, "not_attempted": 3}
DOMAIN_ORDER = ("health", "education", "security", "economy")
PAGES = ("index.html", "study/index.html", "compare/index.html", "graph/index.html",
         "estimates/index.html", "chart/index.html", "ask/index.html", "designs/index.html")
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


def load_glossary(root: Path) -> dict[str, str]:
    """The plain-language meanings, straight from `docs/glossary.md` — never retyped here."""
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
        design = next(d for d in index["designs"] if d["id"] == chosen["design"])
        chosen_card = cards[(oid, chosen["design"])][1]
        labels = {node["id"]: node.get("label") or node["id"] for node in chosen_card.get("nodes") or []}

        assumption = chosen_card.get("identifying_assumption") or "not stated"
        estimate = chosen_card.get("estimate") or {}
        spec = estimate.get("specification") or {}
        verdict = estimate.get("verdict") or {}

        plain = []
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
            plain.append(fill_text(guide["results"]["number"], numbers))
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
                "spec": spec,
                "verdict": verdict,
                "status_word": chosen["word"],
                "tone": chosen["tone"],
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
        },
        "events": {
            "rows": event_rows,
            "rule": events["verdict_rule"],
            "not_claimed": events["not_claimed"],
        },
    }

    counts = index["registry"]["card_estimate_counts"]
    spine = series["counts"]["spine_rows"]
    fills = {
        "window_first": series["window"]["first"],
        "window_last": series["window"]["last"],
        "administrations": admins["counts"]["administrations"],
        "spine_total": sum(int(v) for v in spine.values()),
        "spine_observed": spine["observed"],
        "spine_interpolated": spine["interpolated"],
        "spine_unobserved": spine["unobserved"],
        "estimated": counts["estimated"],
        "cards": counts["estimated"] + counts["not_estimated"],
    }
    for key, value in fills.items():
        fills[key] = f"{value:,}" if isinstance(value, int) else value

    return {
        "vintage": vintage,
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "guide": guide,
        "administrations": admins["administrations"],
        "portraits": portraits,
        "outcomes": outcomes,
        "counts": counts,
        "fills": fills,
        "spine": spine,
        "design_results": design_results,
        "comparisons_generated_at": comparisons.get("generated_at"),
        "changepoints_generated_at": changepoints.get("generated_at"),
        "answer_sets": load(root / "registry" / "rag" / vintage / "answer_eval.json").get("sets", {}),
        "answer_questions": [q["question"] for q in
                             (load(root / "registry" / "rag" / vintage / "answer_eval.json").get("questions") or [])
                             if q.get("set") == "published"],
        "tenure": tenure,
    }


def page(title: str, depth: int, body: str, data: dict | None = None, wide: bool = False) -> str:
    prefix = "../" * depth
    payload = ""
    if data is not None:
        payload = ('<script id="page-data" type="application/json">'
                   + json.dumps(data, ensure_ascii=False) + "</script>")
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<link rel="stylesheet" href="{prefix}assets/style.css">
</head>
<body data-page="{html.escape(title)}"{' class="wide-page"' if wide else ''}>
{body}
{payload}
<script src="{prefix}assets/app.js" defer></script>
</body>
</html>
"""


# ------------------------------------------------------------------------------------------------------------
# Cover — large photographs, moving horizontally
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
                        f'<figcaption class="party-tag">{html.escape(admin["party"])} &middot; '
                        f'{html.escape(party["name"])}</figcaption>')
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
    <p class="eyebrow">{html.escape(cover['eyebrow'])}</p>
    <h1>{html.escape(cover['title'])}</h1>
    <p class="caption">{html.escape(cover['caption'])} <span class="instruction">{html.escape(cover['instruction'])}</span></p>
  </header>

  <section class="presidents" aria-label="{html.escape(cover['rail_heading'])}">
    <div class="flag-band" style="--flag-bands: {party_bands(ctx['guide']['national_flag']['bands'])}" aria-hidden="true"></div>
    <ul class="president-grid">
{''.join(slides)}
    </ul>
    <p class="rail-note">{md(cover['rail_note'])}</p>
  </section>

  <footer class="cover-foot">
    <p class="ratio">{md(fill_text(cover['ratio'], ctx['fills']))}</p>
    <a class="primary" href="study/" role="button">Begin</a>
    <details class="about">
      <summary>About this study</summary>
      <div class="prose">{paragraphs}</div>
    </details>
    {credits}
    <p class="vintage">Registry vintage {ctx['vintage']} · built {ctx['generated_at'][:16].replace('T', ' ')}</p>
  </footer>
</main>
"""
    return page("Causal Presidents", 0, body)


# ------------------------------------------------------------------------------------------------------------
# Flow shell
# ------------------------------------------------------------------------------------------------------------
def flow_page(ctx: dict, key: str, title: str, heading: str, intro: str, note: str | None,
              blocks: str, back: str, forward: str | None, extra_head: str = "",
              wide: bool = False) -> str:
    guide = ctx["guide"]
    steps = list(guide["steps"].items())
    order = [name for name, _label in steps]
    position = order.index(key) + 1
    labels = ""
    for name, label in steps:
        active = " is-active" if name == key else ""
        labels += f'<li class="step{active}">{html.escape(label)}</li>'
    nxt = (f'<a class="primary" id="next" href="../{forward}/" aria-disabled="true">{html.escape(guide["labels"]["next"])}</a>'
           if forward else "")
    body = f"""<main class="flow">
  <ol class="steps" aria-label="Steps">{labels}</ol>
  <header class="flow-head">
    <p class="eyebrow"><a href="../">Causal Presidents</a> · step {position} of {len(order)}</p>
    <h1>{html.escape(heading)}</h1>
    <p class="caption">{html.escape(intro)}</p>
    {f'<p class="note">{md(note)}</p>' if note else ''}
    {extra_head}
  </header>
  <div class="blocks">{blocks}</div>
  <footer class="controls">
    <a class="ghost" href="../{back}/">{html.escape(guide["labels"]["back"])}</a>
    <span class="control-note" id="count-note">Pick at least one outcome on the first screen.</span>
    {nxt}
  </footer>
  <p class="vintage">Registry vintage {ctx['vintage']}</p>
</main>
"""
    return page(title, 1, body, data={"outcomes": [o["id"] for o in ctx["outcomes"]]}, wide=wide)


def outcome_shell(outcome: dict, inner: str, tone: str | None = None) -> str:
    tone_class = f" tone-{tone}" if tone else ""
    return f"""<article class="block{tone_class}" data-outcome="{outcome['id']}" hidden>
  <header class="block-head">
    <h2>{html.escape(outcome['label'])}</h2>
    <span class="meta">{html.escape(outcome['unit'])} · {html.escape(outcome['direction'])} · {html.escape(outcome['coverage'])}</span>
  </header>
{inner}
</article>"""


# ------------------------------------------------------------------------------------------------------------
# Screen 1 — study
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
    <span class="choice-label">{html.escape(o['label'])}</span>
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
    body = f"""<main class="flow">
  <header class="flow-head">
    <p class="eyebrow"><a href="../">Causal Presidents</a> · step 1 of 6</p>
    <h1>{html.escape(study['heading'])}</h1>
    <p class="caption">{html.escape(study['intro'])}</p>
    <p class="note">{md(fill_text(study['caption'], ctx['fills']))}</p>
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
# Screen 2 — the comparison the app chose
# ------------------------------------------------------------------------------------------------------------
def render_compare(ctx: dict) -> str:
    guide = ctx["guide"]
    compare = guide["compare"]
    blocks = []
    for outcome in ctx["outcomes"]:
        c = outcome["compare"]
        reason = (f'<p class="reason"><code>{html.escape(c["reason_code"])}</code> '
                  f'{html.escape(c["reason_sentence"] or "")}</p>' if c["reason_code"] else
                  '<p class="reason"><strong>Number published.</strong> The estimate is on the next screens.</p>')
        blocker = f'<p class="blocker">{html.escape(c["blocker"])}</p>' if c["blocker"] else ""
        inner = f"""
  <p class="chosen"><strong>{c['design']} — {html.escape(c['design_name'])}.</strong> {html.escape(c['plain'])}.</p>
  <p class="assumes">What it assumes: {html.escape(c['assumes'])}.</p>
  <p class="status-line"><span class="pill {c['tone']}">{html.escape(c['word'])}</span>
     <span class="status-sentence">{html.escape(c['sentence'])}</span></p>
  {reason}
  {blocker}"""
        blocks.append(outcome_shell(outcome, inner, tone=c["tone"]))
    return flow_page(ctx, "compare", "What this data can tell you", compare["heading"], compare["intro"],
                     compare["tenure_note"], "".join(blocks), back="study", forward="graph")


# ------------------------------------------------------------------------------------------------------------
# Screen 3 — the assumption, drawn
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
    {a['design']} — {html.escape(a['design_name'])}
  </summary>
  <p class="assumes">{html.escape(a['assumption'] or 'not stated')}</p>
  <img class="graph" src="../{a['svg']}" alt="Assumed causal graph for {html.escape(outcome['label'])} under Design {a['design']}">
</details>"""
            for a in g["alternatives"])
        inner = f"""
  <p class="chosen"><strong>{g['design']} — {html.escape(g['design_name'])}.</strong> {html.escape(outcome['compare']['plain'])}.</p>
  <figure class="graph-figure">
    <img class="graph" src="../{g['svg']}" alt="Assumed causal graph for {html.escape(outcome['label'])} under Design {g['design']}">
    <figcaption>The unobserved node is drawn and named rather than omitted. Adjustment sets are computed on the assumed graph, never hand-listed.</figcaption>
  </figure>
  <div class="columns">
    <div class="col">
      <h3>{html.escape(labels['graph_heading'])}</h3>
      <p class="assumption">{html.escape(g['assumption'])}</p>
    </div>
    <div class="col">
      <h4>Adjustment set</h4>
      <ul class="tight">{adjustment}</ul>
      <h4>Assumed absent</h4>
      <ul class="tight">{absent}</ul>
      <h4>What this cannot rule out</h4>
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
                     "below it is not an effect.", None, "".join(blocks), back="compare", forward="estimates",
                     wide=True)


# ------------------------------------------------------------------------------------------------------------
# Screen 4 — the estimate, in plain words
# ------------------------------------------------------------------------------------------------------------
def render_estimates(ctx: dict) -> str:
    guide = ctx["guide"]
    results = guide["results"]
    blocks = []
    for outcome in ctx["outcomes"]:
        e = outcome["estimate"]
        if e["has_number"]:
            spec = e["spec"]
            plain = "".join(f"<p>{html.escape(line)}</p>" for line in e["plain"])
            channel = (f'<p class="channel-note">{html.escape(results["channel_note"])}</p>'
                       if e["channel_level"] else "")
            rows = "".join(
                f"<li><span class='k'>{html.escape(key.replace('_', ' '))}</span>"
                f"<span class='v'>{html.escape(str(value))}</span></li>"
                for key, value in spec.items() if value is not None)
            inner = f"""
  <p class="status-line"><span class="pill {e['tone']}">{html.escape(e['status_word'])}</span></p>
  <div class="plain">{plain}</div>
  {channel}
  <details class="technical">
    <summary>{html.escape(results['expander'])}</summary>
    <ul class="spec-list">{rows}</ul>
  </details>"""
        else:
            pointer = (f'<p class="blocker">The design\'s own result is published once, at '
                       f'<a href="../designs/">the design-level results</a> '
                       f'(<code>{html.escape(e["published_result"])}</code>). It is not an estimate for this outcome.</p>'
                       if e["published_result"] else "")
            detail = f'<p class="blocker">{html.escape(e["reason_detail"])}</p>' if e["reason_detail"] else ""
            inner = f"""
  <p class="status-line"><span class="pill {e['tone']}">{html.escape(e['status_word'])}</span></p>
  <div class="plain">
    <p>{html.escape(fill_text(results['no_number'], {'reason_sentence': e['reason_sentence'] or ''}))}</p>
    {f'<p class="reason"><code>{html.escape(e["reason_code"])}</code></p>' if e['reason_code'] else ''}
  </div>
  {detail}
  {pointer}"""
        blocks.append(outcome_shell(outcome, inner, tone=e["tone"]))
    return flow_page(ctx, "estimates", results["heading"], results["heading"],
                     "Plain reading first; the number with its interval, its verdict and the check that decided "
                     "it; the technical version folded away.", None, "".join(blocks),
                     back="graph", forward="chart")


# ------------------------------------------------------------------------------------------------------------
# Screen 5 — the chart, described
# ------------------------------------------------------------------------------------------------------------
def render_tenure(outcome: dict, ctx: dict, guide: dict) -> str:
    """Stage 8g: the outcome's deviation from a tenure-blind trend, and the largest pairwise contrast."""
    copy = guide["tenure"]
    row = (ctx.get("tenure") or {}).get(outcome["id"])
    if not row:
        return ""
    if row["status"] != "described":
        return (f"<section class='tenure'><h3>{html.escape(copy['heading'])}</h3>"
                f"<p class='blocker'>{html.escape(copy['refused'])} "
                f"({row['n_native']} native observations).</p></section>")
    described = [t for t in row["tenures"] if t["status"] == "described"]
    body = "".join(
        f"<tr><td>{html.escape(t['president'])}</td><td>{html.escape(t['party'])}</td>"
        f"<td class='num'>{t['n_native']}</td>"
        f"<td class='num'>{t['deviation_range'][0]:+.2f} &hellip; {t['deviation_range'][1]:+.2f}</td></tr>"
        for t in described)
    heads = "".join(f"<th>{html.escape(h)}</th>" for h in copy["heads"])
    contrast = ""
    if row["contrasts"]:
        best = max(row["contrasts"], key=lambda c: abs(c["difference"]))
        contrast = (f"<p class='note'><strong>{html.escape(copy['contrast_heading'])}.</strong> "
                    f"{html.escape(best['reading'])}.</p>")
    return f"""<section class="tenure">
  <h3>{html.escape(copy['heading'])}</h3>
  <p class="tech">{html.escape(copy['note'])}</p>
  <table class="deviation-table"><thead><tr>{heads}</tr></thead><tbody>{body}</tbody></table>
  {contrast}
</section>"""


def render_chart(ctx: dict) -> str:
    guide = ctx["guide"]
    groupings = guide["groupings"]
    control = "".join(
        f"<label class='toggle'><input type='radio' name='grouping' value='{key}'"
        f"{' checked' if key == 'party_tenure' else ''}> {html.escape(groupings[key]['plain'])}"
        f" <span class='tech'>({html.escape(groupings[key]['technical'])})</span></label>"
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
                    f"<li><strong>{html.escape(g['plain'])}</strong> <span class='tech'>{html.escape(g['technical'])}</span>"
                    f"<br><span class='tech'>{html.escape(g['caption'])}</span></li>" for g in rows)
                lists.append(f"<div class='group-list' data-grouping='{key}'><ul class='tight'>{body}</ul></div>")
            else:
                lists.append(f"<div class='group-list' data-grouping='{key}' hidden><p class='blocker'>No state "
                             f"grouping is declared for this outcome.</p></div>")
        inner = f"""
  <p class="chosen">{html.escape(chart['caption'] or '')}</p>
  <figure class="chart-figure">
    <img class="chart" src="../{chart['figure']}" alt="Outcome series grouped for {html.escape(outcome['label'])}">
    <figcaption>{html.escape(guide['chart']['stamp'])}. {html.escape(guide['results']['stamp_note'])}</figcaption>
  </figure>
  <h3>{html.escape(guide['results']['groups_heading'])}</h3>
  {''.join(lists)}
  {render_breaks(outcome, guide)}{render_tenure(outcome, ctx, guide)}"""
        blocks.append(outcome_shell(outcome, inner))

    return flow_page(ctx, "chart", "The comparison, drawn", guide["labels"]["chart_heading"],
                     "Two ways to look at the same outcome: by who was in power, and — where the outcome is "
                     "measured state by state — by how much money a state received.", None, "".join(blocks),
                     back="estimates", forward="ask", extra_head=extra_head)


# ------------------------------------------------------------------------------------------------------------
# Screen 6 — ask the corpus, in the browser
# ------------------------------------------------------------------------------------------------------------
def render_ask(ctx: dict) -> str:
    guide = ctx["guide"]
    copy = guide["ask"]
    overall = (ctx.get("answer_sets") or {}).get("all") or {}
    measured = ""
    if overall.get("n"):
        measured = fill_text(copy["measured"], {"answered": overall["answered"], "total": overall["n"]})
    body = f"""<main class="flow ask">
  <ol class="steps" aria-label="Steps">
    {''.join(f'<li class="step{" is-active" if name == "ask" else ""}">{html.escape(label)}</li>' for name, label in guide['steps'].items())}
  </ol>
  <header class="flow-head">
    <p class="eyebrow"><a href="../">Causal Presidents</a> · step {len(guide['steps'])} of {len(guide['steps'])}</p>
    <h1>{html.escape(copy['heading'])}</h1>
    <p class="caption">{html.escape(copy['intro'])}</p>
    {f'<p class="note">{html.escape(measured)}</p>' if measured else ''}
  </header>
  <form class="ask-form" id="ask-form" autocomplete="off">
    <label for="ask-input">{html.escape(copy['heading'])}</label>
    <input id="ask-input" name="question" type="text" list="ask-questions"
           placeholder="{html.escape(copy['placeholder'])}" autocomplete="off">
    <datalist id="ask-questions">{''.join(f'<option value="{html.escape(q)}"></option>' for q in ctx.get("answer_questions") or [])}</datalist>
    <button class="primary" type="submit">{html.escape(copy['button'])}</button>
  </form>
  <p class="control-note" id="ask-status" role="status">{html.escape(copy['empty'])}</p>
  <section class="ask-answer" id="ask-answer" hidden aria-live="polite"></section>
  <footer class="controls">
    <a class="ghost" href="../chart/">{html.escape(guide['labels']['back'])}</a>
    <a class="ghost" href="../designs/">{html.escape(copy['deeper'])}</a>
    <a class="ghost" href="../">Causal Presidents</a>
  </footer>
  <p class="vintage">Registry vintage {ctx['vintage']}</p>
</main>
<script type="module" src="../assets/ask.mjs"></script>"""
    return page("Ask the corpus", 1, body)


# ------------------------------------------------------------------------------------------------------------
# Screen 6b — the design-level results
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
    <figcaption>{md(block['layout'])} <span class="tech">{html.escape(copy['figure_note'])}</span></figcaption>
  </figure>"""

    a_rows = "".join(f"<li>{html.escape(row['line'])}</li>" for row in d["a"]["rows"])
    flips = "".join(f"<li>{html.escape(line)}</li>" for line in d["grid"]["flips"])
    event_rows = "".join(
        f"<li>{html.escape(fill_text(copy['event_line'], row))}</li>" for row in d["events"]["rows"])
    not_claimed = "".join(f"<li>{md(claim)}</li>" for claim in d["events"]["not_claimed"])

    body = f"""<main class="flow designs">
  <header class="flow-head">
    <p class="eyebrow"><a href="../">Causal Presidents</a> · the design-level results</p>
    <h1>{html.escape(copy['heading'])}</h1>
    <p class="caption">{html.escape(copy['intro'])}</p>
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
    <h2>{html.escape(copy['not_run_heading'])}</h2>
    <h3>{html.escape(names['C'])}</h3>
    <p>{md(d['c']['why'] or '')}</p>
    <p><span class="tech">{html.escape(copy['next_step'])}</span> {md(d['c']['next_step'] or '')}</p>
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


def render_breaks(outcome: dict, guide: dict) -> str:
    """The changepoint half of the chart screen: when the series changes, and the rule that it is not a cause."""
    copy = guide["changepoint"]
    brk = outcome.get("breaks")
    if not brk:
        return ""
    head = (f"<h3>{html.escape(copy['heading'])}</h3>"
            f"<p class='tech'>{html.escape(copy['intro'])}</p>")
    if brk["status"] == "refused" or not brk["figure"]:
        return (f"<section class='breaks'>{head}<p class='blocker'>{html.escape(copy['refused'])} "
                f"{html.escape(brk['caption'])}</p></section>")
    rows = "".join(
        f"<li><strong>{html.escape(r['month'])}</strong> — {html.escape(r['statement'])}"
        + (f" <span class='tech'>({html.escape(copy['timing_note'])})</span>" if r["coincides"] else "")
        + "</li>" for r in brk["rows"])
    return f"""<section class="breaks">
  {head}
  <figure class="chart-figure">
    <img class="chart" src="../{brk['figure']}" alt="Outcome series with its declared breaks for {html.escape(outcome['label'])}">
    <figcaption>{html.escape(guide['chart']['stamp'])}. {html.escape(copy['note'])}</figcaption>
  </figure>
  <p class="chosen">{html.escape(brk['caption'])}</p>
  <ul class="tight">{rows}</ul>
  <p class="tech">{html.escape(brk['method'])}</p>
</section>"""


# ------------------------------------------------------------------------------------------------------------
def main() -> int:
    ctx = build_context(REPO_ROOT)

    for name in ("", "study", "compare", "graph", "estimates", "chart", "ask", "designs"):
        (DIST / name).mkdir(parents=True, exist_ok=True)
    for name in ("assets", "assets/graphs", "assets/comparisons", "assets/series", "assets/breaks",
                 "assets/designs", "assets/presidents", "data"):
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

    (DIST / "index.html").write_text(render_cover(ctx), encoding="utf-8", newline="\n")
    (DIST / "study" / "index.html").write_text(render_study(ctx), encoding="utf-8", newline="\n")
    (DIST / "compare" / "index.html").write_text(render_compare(ctx), encoding="utf-8", newline="\n")
    (DIST / "graph" / "index.html").write_text(render_graph(ctx), encoding="utf-8", newline="\n")
    (DIST / "estimates" / "index.html").write_text(render_estimates(ctx), encoding="utf-8", newline="\n")
    (DIST / "chart" / "index.html").write_text(render_chart(ctx), encoding="utf-8", newline="\n")
    (DIST / "ask" / "index.html").write_text(render_ask(ctx), encoding="utf-8", newline="\n")
    (DIST / "designs" / "index.html").write_text(render_designs(ctx), encoding="utf-8", newline="\n")

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

    print(f"built {DIST.relative_to(REPO_ROOT)} — {len(PAGES)} pages, {len(ctx['outcomes'])} outcomes, "
          f"vintage {ctx['vintage']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

