"""Independent verification of the Stage 9 read-only app.

The app is the one artifact a reader touches directly, so the failure that matters is not "it crashed" but
"it showed something the registry does not say". This verifier renders the app in Streamlit's own test
harness and compares what came out against the cards on disk, without importing `app/registry_data.py`:

  * **Every one of the 36 cards renders.** Each (outcome, design) pair is selected and run. A pair that
    raises is a card the reader cannot reach.
  * **The number shown is the card's number.** The coefficient, its interval, its p-value, the verdict
    status and the two coverage fields are formatted here from the card JSON and required to appear; the
    app's own formatter is never imported, so a formatting bug in it cannot hide a copied number.
  * **A card without a number says why.** The reason code and its detail sentence must appear for every
    `not_estimated` card — silence is the thing Stage 8 forbids.
  * **The adjustment set is the card's, resolved to labels.** Every node id in `adjustment_set` must appear
    as `label (id)`. Hand-written adjustment prose would fail this.
  * **No number is typed into the app.** The published coefficients are searched for in the app's source,
    in both full and 4-decimal form. The card wins; a literal in the UI is the defect.
  * **No model, no database, no network.** The source is scanned for the imports that would let it fit,
    open or fetch — the base spec's §18 rule that the app reads the registry and nothing else.

Usage:
    python tests/verify_app.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
APP_DIR = REPO_ROOT / "app"
APP_FILE = APP_DIR / "streamlit_app.py"
REGISTRY_DIR = REPO_ROOT / "registry" / "dags"


def fail(failures: list[str], message: str) -> None:
    failures.append(message)


def signed(value: float) -> str:
    return f"{value:+.4f}"


def interval(low: float, high: float) -> str:
    return f"[{signed(low)}, {signed(high)}]"


def squash(text: str) -> str:
    """One-line form, so a needle that straddles a markdown line break still matches."""
    return " ".join(text.split())


def rendered_text(at) -> str:
    """Everything the reader can see as text, in one string.

    Components (the embedded graph) are not text and are excluded; every markdown/info/warning/caption
    element is included, because a claim shown in a grey box is still a claim.
    """
    parts: list[str] = []
    for attribute in ("title", "subheader", "markdown", "caption", "info", "warning", "error", "text"):
        for element in getattr(at, attribute, []):
            value = getattr(element, "value", None)
            if isinstance(value, str):
                parts.append(value)
    return squash("\n".join(parts))


def main() -> int:
    failures: list[str] = []

    if not APP_FILE.exists():
        print(f"FAILED — {APP_FILE.relative_to(REPO_ROOT)} is missing")
        return 1

    index = json.loads((REGISTRY_DIR / "index.json").read_text(encoding="utf-8"))
    vintage = index["vintage_date"]
    counts = (index.get("registry") or {}).get("card_estimate_counts") or {}
    estimated = int(counts.get("estimated", 0))
    not_estimated = int(counts.get("not_estimated", 0))
    total = estimated + not_estimated

    cards = {
        path.stem: json.loads(path.read_text(encoding="utf-8"))
        for path in sorted(REGISTRY_DIR.glob("*.json"))
        if path.name != "index.json"
    }
    if not cards:
        print("FAILED — no cards on disk to render")
        return 1

    # ---------------------------------------------------------------------------------------------
    # 1. The app runs, and states the ratio it exists to state
    # ---------------------------------------------------------------------------------------------
    try:
        from streamlit.testing.v1 import AppTest
    except ImportError:
        print("FAILED — streamlit is not importable, so the app cannot be rendered at all")
        return 1

    at = AppTest.from_file(str(APP_FILE), default_timeout=120)
    at.run()

    # The widgets are addressed by key, not by position: tabs render their content on every run, so the
    # order of the radios in the tree is not the order a reader meets them.
    try:
        at.selectbox(key="outcome")
        at.radio(key="causal_model")
        at.radio(key="result_design")
    except KeyError as exc:
        print(f"FAILED — the app does not expose the widgets this verifier drives: {exc}")
        return 1
    if at.exception:
        print("FAILED — the app raised on its default state:")
        for exc in at.exception:
            print(f"  - {exc.message}")
        return 1

    if not at.title or at.title[0].value != "Causal Presidents":
        fail(failures, "the app does not carry its title, so this may not be the app under test")

    headline = f"{estimated} of {total} model cards carry a published number"
    if at.markdown and headline not in rendered_text(at):
        fail(failures, f"the opening statement {headline!r} is not rendered — the ratio is the point of the "
                       f"page (it is what the reader must see before any single number)")

    if vintage not in rendered_text(at):
        fail(failures, f"the registry vintage {vintage!r} is not shown anywhere on the first screen")

    # ---------------------------------------------------------------------------------------------
    # 2. Every card renders, and renders its own content
    # ---------------------------------------------------------------------------------------------
    outcomes = [row["id"] for row in index.get("outcomes") or []]
    designs = [row["id"] for row in index.get("designs") or []]
    pairs = [(outcome_id, design_id) for outcome_id in outcomes for design_id in designs]
    missing = [f"{o}__{d}" for o, d in pairs if f"{o}__{d}" not in cards]
    for dag_id in missing:
        fail(failures, f"the index declares {dag_id} but no card exists on disk, so the app cannot show it")

    published = index.get("published_results") or {}
    b_numbers = {signed(spec["coefficient"]) for spec in (published.get("B") or {}).get("specifications") or []}

    rendered_pairs = 0
    for outcome_id, design_id in pairs:
        dag_id = f"{outcome_id}__{design_id}"
        card = cards.get(dag_id)
        if card is None:
            continue

        # The results tab is pointed at a *different* design while each card is checked. Otherwise a card's
        # own verdict sentence could be satisfied by the design-level tab that repeats it, and "the page
        # shows the failed check" would be true of a page that never showed it on the card.
        results_on = "A" if design_id != "A" else "C"
        at.selectbox(key="outcome").set_value(outcome_id)
        at.radio(key="causal_model").set_value(design_id)
        at.radio(key="result_design").set_value(results_on)
        at.run()
        rendered_pairs += 1
        if at.exception:
            fail(failures, f"{dag_id}: the app raised — "
                           f"{'; '.join(exc.message.splitlines()[0] for exc in at.exception)}")
            continue

        text = rendered_text(at)
        estimate = card.get("estimate") or {}
        status = estimate.get("status")

        if status == "estimated":
            spec = estimate["specification"]
            for needle, what in (
                (signed(spec["coefficient"]), "the published coefficient"),
                (interval(spec["ci_low"], spec["ci_high"]), "the 95 % interval"),
                (f"p = {spec['p_value']:.4f}", "the p-value"),
                (f"{spec['n_obs']:,} observations", "the sample size"),
                (f"{spec['n_units']} units", "the unit count"),
                (spec.get("coefficient_name", ""), "the coefficient's name"),
                ((estimate.get("verdict") or {}).get("status", ""), "the verdict"),
            ):
                if needle and needle not in text:
                    fail(failures, f"{dag_id}: {what} ({needle!r}) is on the card but not on the page")
            verdict = estimate.get("verdict") or {}
            if verdict.get("failed_checks"):
                # The prefix is part of the needle: "**Failed check:**" on the results tab is a different
                # sentence from the card's own "Failed check:", and only the second one is being checked.
                needle = squash("Failed check: " + str(verdict["failed_checks"]))[:70]
                if needle not in text:
                    fail(failures, f"{dag_id}: the verdict names a failed check that the page does not show — "
                                   f"a number shown without it is the failure Stage 8 exists to prevent")
        elif status == "not_estimated":
            reason = estimate.get("not_estimated_reason") or {}
            code = reason.get("code", "")
            if code and f"`{code}`" not in text:
                fail(failures, f"{dag_id}: carries no number and the page does not name its reason code {code!r}")
            detail = squash(reason.get("detail", ""))
            if detail and detail[:70] not in text:
                fail(failures, f"{dag_id}: the reason's detail sentence is not rendered — a code alone does not "
                               f"tell the reader why")
        else:
            fail(failures, f"{dag_id}: the card's estimate block has status {status!r}, which the app does not "
                           f"handle and this verifier cannot check")

        # The assumption, the adjustment set and the caveats are the page's reason to exist.
        assumption = squash(card.get("identifying_assumption", ""))
        if assumption and assumption[:80] not in text:
            fail(failures, f"{dag_id}: the identifying assumption is not rendered")
        for node in card.get("adjustment_set") or []:
            label = next((n["label"] for n in card.get("nodes") or [] if n["id"] == node), None)
            needle = f"{label} ({node})" if label else node
            if needle not in text:
                fail(failures, f"{dag_id}: adjustment node {node!r} is on the card and not on the page — the "
                               f"adjustment set must be the computed one, shown in full")
        for caveat in card.get("cannot_rule_out") or []:
            if squash(caveat)[:60] not in text:
                fail(failures, f"{dag_id}: a cannot-rule-out caveat is not rendered")

        # A design-level result must not be lent to a card: the B number belongs on the index, once.
        if design_id == "B" and status == "not_estimated":
            borrowed = sorted(number for number in b_numbers if number in text)
            if borrowed:
                fail(failures, f"{dag_id}: a B card displays the channel-level coefficient(s) {borrowed} — the "
                               f"result is design-level and must not appear as if it were this outcome's "
                               f"estimate")

    if rendered_pairs != len(pairs):
        fail(failures, f"only {rendered_pairs} of {len(pairs)} declared pairs were rendered")

    # ---------------------------------------------------------------------------------------------
    # 3. The design-level results, on the one tab where they live
    # ---------------------------------------------------------------------------------------------
    for design_id in designs:
        result = published.get(design_id)
        if not result:
            continue
        at.radio(key="causal_model").set_value(design_id)
        at.radio(key="result_design").set_value(design_id)
        at.run()
        if at.exception:
            fail(failures, f"design {design_id}: the results tab raised")
            continue
        text = rendered_text(at)
        if f"`{result.get('status')}`" not in text:
            fail(failures, f"design {design_id}: status {result.get('status')!r} is not shown")
        for spec in result.get("specifications") or []:
            if signed(spec["coefficient"]) not in text:
                fail(failures, f"design {design_id}: published coefficient {signed(spec['coefficient'])} is not "
                               f"on the results tab")
        if result.get("next_step") and squash(result["next_step"])[:60] not in text:
            fail(failures, f"design {design_id}: the declared next step is not rendered")
        if result.get("why") and squash(result["why"])[:60] not in text:
            fail(failures, f"design {design_id}: the reason the design was not run is not rendered")

    # ---------------------------------------------------------------------------------------------
    # 4. No number is typed, and nothing can be fitted at render time
    # ---------------------------------------------------------------------------------------------
    source = "\n".join(path.read_text(encoding="utf-8") for path in sorted(APP_DIR.glob("*.py")))
    estimates = json.loads((REPO_ROOT / "registry" / "estimates" / vintage / "estimates.json").read_text("utf-8"))
    published_specs = estimates.get("specifications") or []
    for spec in published_specs + [s for r in published.values() for s in (r.get("specifications") or [])]:
        value = spec.get("coefficient")
        if value is None:
            continue
        for literal in {str(value), f"{value:.4f}", f"{abs(value):.4f}", signed(value).lstrip("+")}:
            if literal in source:
                fail(failures, f"the coefficient {literal} is typed into the app source — every number must be "
                               f"read from the card it is shown on (the card wins)")

    forbidden = {
        "duckdb": "opens the analytical database",
        "sqlite3": "opens a local database",
        "requests": "makes a network call",
        "urllib": "makes a network call",
        "httpx": "makes a network call",
        "openai": "would put a model behind the number",
        "anthropic": "would put a model behind the number",
        "subprocess": "could re-run an analysis stage at render time",
        "statsmodels": "would fit something at render time",
        "scipy": "would compute something at render time",
    }
    for module, why in forbidden.items():
        if re.search(rf"^\s*(?:import|from)\s+{module}\b", source, re.MULTILINE):
            fail(failures, f"app/ imports {module}, which {why} — the app reads the registry and nothing else")

    # ---------------------------------------------------------------------------------------------
    # 5. The narrative describes this page, and does not claim a chat that is not built
    # ---------------------------------------------------------------------------------------------
    narrative = REPO_ROOT / "docs" / "app.md"
    if not narrative.exists():
        fail(failures, "docs/app.md is missing — the app's narrative and its limits have to live somewhere a "
                       "reader can find without reading the source")
    else:
        story = " ".join(narrative.read_text(encoding="utf-8").split())
        for needle, what in (
            (f"{estimated} of {total}", "the card ratio the page states"),
            ("Nothing is fitted at render time", "the no-model-at-render-time rule"),
            ("cannot rule out", "the caveat the page shows on every card"),
        ):
            if needle not in story:
                fail(failures, f"docs/app.md does not carry {needle!r} — {what} has moved")
        # The reason table is prose too: its counts are derived from the index, so a card changing reason
        # must not leave the narrative quoting the old split.
        for code, count in (counts.get("not_estimated_by_reason") or {}).items():
            if f"`{code}` | {count}" not in story:
                fail(failures, f"docs/app.md's reason table does not say {code} = {count} — the codes and "
                               f"counts are derived from the index, and prose that drifts is stale")

    # ---------------------------------------------------------------------------------------------
    if failures:
        print(f"FAILED — {len(failures)} problem(s):")
        for problem in failures[:40]:
            print(f"  - {problem}")
        if len(failures) > 40:
            print(f"  … and {len(failures) - 40} more")
        return 1

    print(f"rendered      : {rendered_pairs} cards ({len(outcomes)} outcomes x {len(designs)} designs), "
          f"{len(designs)} design-level result tabs")
    print(f"numbers       : {estimated} cards carry a coefficient that is on the page in its card's own value; "
          f"{not_estimated} name their reason and its detail")
    print(f"assumptions   : every card's identifying assumption, computed adjustment set and caveats rendered")
    print(f"card wins     : no published coefficient appears as a literal in the app source; every displayed "
          f"value traces to a card field")
    print(f"no model      : the app imports no database client, network client or fitting library")
    print()
    print("PASS — every card renders its own content, every absent number names its reason, and the "
          "design-level results stay where the index puts them")
    return 0


if __name__ == "__main__":
    sys.exit(main())
