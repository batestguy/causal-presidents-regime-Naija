"""Read the registry the analysis stages publish. No model, no database, no network.

Stage 8's exit criterion is that the app can be built without opening R. This module is the whole of that
contract on the Python side: it opens `registry/dags/index.json` and the 36 card files, refuses anything that
disagrees with its own vintage, and formats what it finds. It computes no statistic and holds no number.

Three rules are enforced here rather than trusted to the UI:

  * **The card wins.** If a card's `vintage_date` is not the index's, the loader raises instead of rendering
    a number from one vintage beside a count from another.
  * **Nothing is inferred.** Direction, unit, coverage and the adjustment set are read from the card; the
    adjustment set is resolved from node ids to their labels using the card's own node list.
  * **No number is typed.** Every displayed value is a field of a card or the index. `tests/verify_app.py`
    greps the app for the published coefficients to keep it that way.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

CARDS_DIR = "registry/dags"
SERIES_DIR = "registry/series"
INDEX_FILE = "index.json"
DESIGNS = {"A": "DiD", "B": "Time series", "C": "Synthetic control"}


class RegistryError(RuntimeError):
    """The registry on disk cannot be rendered faithfully. Never downgraded to a warning."""


def signed(value: float) -> str:
    return f"{value:+.4f}"


def interval(low: float, high: float) -> str:
    return f"[{signed(low)}, {signed(high)}]"


def direction_words(direction: str | None) -> str:
    return {"down": "down (lower is better)", "up": "up (higher is better)"}.get(
        str(direction), f"{direction} (direction undeclared)"
    )


def coverage_words(status: str | None) -> str:
    return {
        "ok": "ok — a usable series reaches the study window",
        "partial": "partial — a series exists but part of the window is interpolation or a declared gap",
        "declared_gap": "declared gap — no usable series",
        "blocked": "blocked — the source could not be reached or licensed",
    }.get(str(status), f"{status} (status undeclared)")


@dataclass(frozen=True)
class Registry:
    """The published registry, loaded and cross-checked."""

    root: Path
    index: dict
    cards: dict[str, dict]
    # The outcome panels are a second published family, keyed on the same outcome ids. They are loaded
    # here so the card and the series it describes cannot come from two vintages.
    series: dict[str, dict] | None = None
    series_marks: dict | None = None

    # -- identity -------------------------------------------------------------------------------
    @property
    def vintage(self) -> str:
        return str(self.index.get("vintage_date"))

    def outcome(self, outcome_id: str) -> dict:
        for row in self.index.get("outcomes") or []:
            if row["id"] == outcome_id:
                return row
        raise RegistryError(f"outcome {outcome_id!r} is not in the index")

    def design(self, design_id: str) -> dict:
        for row in self.index.get("designs") or []:
            if row["id"] == design_id:
                return row
        raise RegistryError(f"design {design_id!r} is not in the index")

    def outcomes(self) -> list[dict]:
        return list(self.index.get("outcomes") or [])

    def designs(self) -> list[dict]:
        return list(self.index.get("designs") or [])

    # -- cards ----------------------------------------------------------------------------------
    def card(self, outcome_id: str, design_id: str) -> dict:
        dag_id = f"{outcome_id}__{design_id}"
        if dag_id not in self.cards:
            raise RegistryError(f"no card for ({outcome_id}, {design_id}) — dag_id {dag_id!r}")
        return self.cards[dag_id]

    def card_path(self, card: dict) -> Path:
        return self.root / CARDS_DIR / f"{card['dag_id']}.json"

    def svg_path(self, card: dict) -> Path:
        return self.root / str((card.get("assets") or {}).get("svg", ""))

    # -- outcome series -------------------------------------------------------------------------
    def series_row(self, outcome_id: str) -> dict:
        rows = self.series or {}
        if outcome_id not in rows:
            raise RegistryError(
                f"no outcome panel for {outcome_id!r} — every card names an outcome and every outcome has a "
                f"published series (run analysis/R/07_series_figures.R)"
            )
        return rows[outcome_id]

    def series_path(self, row: dict) -> Path:
        return self.root / str((row.get("figure") or {}).get("path", ""))

    def node_label(self, card: dict, node_id: str) -> str:
        for node in card.get("nodes") or []:
            if node["id"] == node_id:
                return f"{node['label']} ({node_id})"
        return f"{node_id} (not in this card's node list)"

    def adjustment_labels(self, card: dict) -> list[str]:
        return [self.node_label(card, node) for node in card.get("adjustment_set") or []]

    def assumed_absent_labels(self, card: dict) -> list[str]:
        return [self.node_label(card, node) for node in card.get("assumption_required") or []]

    # -- design-level results -------------------------------------------------------------------
    def design_result(self, design_id: str) -> dict | None:
        return (self.index.get("published_results") or {}).get(design_id)

    # -- counts ---------------------------------------------------------------------------------
    def outcome_series(self, outcome_id: str) -> tuple[dict, Path, str]:
        """(panel row, figure path, how-to-read sentence) for an outcome."""
        row = self.series_row(outcome_id)
        return row, self.series_path(row), series_marks_text({"marks": self.series_marks})

    def card_counts(self) -> dict:
        return (self.index.get("registry") or {}).get("card_estimate_counts") or {}

    def counts(self) -> dict:
        return dict(self.index.get("counts") or {})


# ---------------------------------------------------------------------------------------------
# Render-ready formatting. Every string below is built from an artifact field.
# ---------------------------------------------------------------------------------------------
def estimate_rows(block: dict) -> list[tuple[str, str]]:
    """(label, value) pairs for an `estimated` card, in the order the card states them."""
    spec = block.get("specification") or {}
    rows = [
        ("estimate", f"{signed(spec['coefficient'])}  ·  95 % interval {interval(spec['ci_low'], spec['ci_high'])}"),
        ("standard error", f"{spec['standard_error']:.4f}"),
        ("p-value", f"{spec['p_value']:.4f}"),
        ("coefficient", str(spec.get("coefficient_name", "not stated"))),
        ("estimator", str(spec.get("estimator", "not stated"))),
        ("formula", str(spec.get("formula", "not stated"))),
        ("covariance", str(spec.get("covariance", "not stated"))),
        ("sample", f"{spec['n_obs']:,} observations over {spec['n_units']} units, "
                   f"{spec.get('first_month', '?')} to {spec.get('last_month', '?')}"),
        ("verdict", str((block.get("verdict") or {}).get("status", "not stated"))),
        ("the number is for this card", str(block.get("the_number_is_for_this_card")).lower()),
        ("model card reference", str(block.get("model_card_ref") or "not stated")),
    ]
    return rows


def verdict_text(block: dict) -> str:
    verdict = block.get("verdict") or {}
    rule = verdict.get("rule")
    failed = verdict.get("failed_checks")
    lines = []
    if failed:
        lines.append(f"Failed check: {failed}")
    else:
        lines.append("No check failed.")
    if rule:
        lines.append(f"The rule, fixed before the numbers were read: {rule}")
    return "\n\n".join(lines)


def robustness_text(block: dict) -> str:
    robustness = block.get("robustness") or {}
    level = robustness.get("axis_level") or {}
    support = robustness.get("design_support") or {}
    if not level:
        return ""
    return (
        f"One cell of a grid: {level.get('n_positive')} of the {level.get('n')} specifications sharing this "
        f"outcome are positive and {level.get('n_negative')} negative"
        f"{', a majority against the preferred specification' if level.get('flips_against_preferred') else ''}. "
        f"Across the design's {support.get('n')} specifications the split is {support.get('n_positive')} "
        f"positive / {support.get('n_negative')} negative, with {robustness.get('design_flip_levels')} axis "
        f"levels flipping and {support.get('n_near_zero')} inside the ±{robustness.get('near_zero_band')} "
        f"near-zero band."
    )


def reason_text(block: dict) -> tuple[str, str]:
    """(code, detail) for a card that carries no number."""
    reason = block.get("not_estimated_reason") or {}
    return str(reason.get("code", "no_reason_given")), str(reason.get("detail", ""))


def series_marks_text(row: dict) -> str:
    """How to read the panel, assembled from the artifact's own mark definitions."""
    marks = row.get("marks") or {}
    parts = []
    for key, label in (("observed", "observed"), ("interpolated", "interpolated"),
                       ("unobserved", "no observation")):
        if marks.get(key):
            parts.append(f"**{label}** — {marks[key]}")
    return "; ".join(parts)


def precheck_lines(card: dict) -> list[str]:
    diag = card.get("diagnostics") or {}
    lines = [f"Stage 5 pre-check: **{diag.get('status', 'not run')}**"]
    if diag.get("blocker"):
        lines.append(f"Blocker: {diag['blocker']}")
    for check in diag.get("checks") or []:
        if check.get("verdict") in ("pass", "computed"):
            continue
        lines.append(f"- {check.get('id')}: {check.get('verdict')} — {check.get('detail')}")
    return lines


def result_spec_rows(result: dict) -> list[dict]:
    return [
        {
            "specification": spec.get("outcome"),
            "estimate": signed(spec["coefficient"]),
            "95 % interval": interval(spec["ci_low"], spec["ci_high"]),
            "p": f"{spec['p_value']:.4f}",
            "n": f"{spec['n_obs']:,}",
            "window": f"{spec.get('first_month', '?')} to {spec.get('last_month', '?')}",
        }
        for spec in result.get("specifications") or []
    ]


# ---------------------------------------------------------------------------------------------
# Loading, with the vintage contract enforced
# ---------------------------------------------------------------------------------------------
def load_registry(root: Path | str | None = None) -> Registry:
    root = Path(root) if root is not None else Path(__file__).resolve().parents[1]
    index_path = root / CARDS_DIR / INDEX_FILE
    if not index_path.exists():
        raise RegistryError(f"{index_path}: missing — run the Stage 8 assembly (analysis/R/05_registry.R)")
    index = json.loads(index_path.read_text(encoding="utf-8"))
    vintage = index.get("vintage_date")
    if not vintage:
        raise RegistryError(f"{index_path}: carries no vintage_date")

    cards: dict[str, dict] = {}
    for path in sorted((root / CARDS_DIR).glob("*.json")):
        if path.name == INDEX_FILE:
            continue
        card = json.loads(path.read_text(encoding="utf-8"))
        dag_id = card.get("dag_id")
        if not dag_id:
            raise RegistryError(f"{path}: card carries no dag_id")
        if card.get("vintage_date") != vintage:
            raise RegistryError(
                f"{path.name}: card vintage {card.get('vintage_date')!r} is not the index's {vintage!r} — "
                "the registry is mid-rebuild and a number from one vintage must not be shown beside another"
            )
        cards[dag_id] = card

    # The outcome panels are loaded under the same contract as the cards: same vintage, one panel per
    # outcome the index declares. A missing family is an error rather than a card without its series,
    # because the page is not supposed to render a reason without the series the reason is about.
    series_path = root / SERIES_DIR / str(vintage) / INDEX_FILE
    if not series_path.exists():
        raise RegistryError(
            f"{series_path}: missing — run analysis/R/07_series_figures.R (the outcome panels are published "
            "at the registry vintage)"
        )
    series_document = json.loads(series_path.read_text(encoding="utf-8"))
    if series_document.get("vintage") != vintage:
        raise RegistryError(
            f"registry/series: the panels are vintage {series_document.get('vintage')!r} and the cards are "
            f"{vintage!r} — a series from one vintage must not be shown under a card from another"
        )
    declared_outcomes = [row["id"] for row in index.get("outcomes") or []]
    series_rows = {row["id"]: row for row in series_document.get("outcomes") or []}
    if sorted(series_rows) != sorted(declared_outcomes):
        raise RegistryError(
            f"registry/series: {len(series_rows)} panel(s) for {len(declared_outcomes)} declared outcome(s) — "
            f"missing {sorted(set(declared_outcomes) - set(series_rows))}"
        )

    registry = Registry(root=root, index=index, cards=cards, series=series_rows,
                        series_marks=series_document.get("marks") or {})
    expected = registry.counts()
    outcomes, designs = expected.get("outcomes"), expected.get("designs")
    if outcomes and designs and len(cards) != int(outcomes) * int(designs):
        raise RegistryError(
            f"{len(cards)} cards for {outcomes} x {designs} pairs — the registry is incomplete"
        )
    estimated = sum(1 for card in cards.values()
                    if (card.get("estimate") or {}).get("status") == "estimated")
    declared = registry.card_counts().get("estimated")
    if declared is not None and declared != estimated:
        raise RegistryError(
            f"the index says {declared} card(s) carry a published number and the cards say {estimated} — "
            "the registry is stale against its own cards"
        )
    return registry
