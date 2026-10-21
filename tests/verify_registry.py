"""Verify the Stage 8 registry — the cards and the index the app reads.

Stage 9 must be buildable without opening R, so the registry *is* the app's data contract, and this
verifier is the check on it. It re-derives the mapping from the artifacts in Python rather than reading
it back out of the cards:

  * **Which cards should carry a number**, from the estimates artifact's own Design A specifications.
    Attaching a number to a card it is not about is the most expensive error this layer can make, so the
    expectation is recomputed both ways round: every published Design A specification either sits on a
    card whose outcome it is about, or is declared as published-without-a-card in
    ``analysis/specs/registry.yml``.
  * **Every number on a card equals the artifact it names**, to the artifact's own precision. A card is a
    copy; a copy that drifted is a number no one can trace.
  * **Every card without a number says why**, with a reason from the declared closed set, and the reason
    is the one the recomputation implies (an outcome with no series outranks a design-level reason).
  * **The index's design-level results are the artifacts' numbers**, including the two that make the
    registry honest: Design B's result is channel-level (so nine B cards cannot borrow it), and Design C
    was not run.
  * **Nothing claims the registry holds no estimates.** The index's ``layer`` string said exactly that
    until Stage 8; the app would have read the strongest claim in the repository and been wrong.

Usage:
    conda run -p "C:/Users/TOSHIBA/ds-general" python tests/verify_registry.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC_PATH = REPO_ROOT / "analysis" / "specs" / "registry.yml"
CARDS_DIR = REPO_ROOT / "registry" / "dags"
TOL = 1e-9

REASONS = {
    "outcome_series_absent",
    "no_specification_declared",
    "design_result_is_channel_level",
    "design_not_run",
}


def fail(failures: list[str], message: str) -> None:
    failures.append(message)


def newest_vintage(root: Path) -> str | None:
    if not root.is_dir():
        return None
    vintages = sorted(p.name for p in root.iterdir()
                      if p.is_dir() and re.fullmatch(r"\d{4}-\d{2}-\d{2}", p.name))
    return vintages[-1] if vintages else None


def close(a: float, b: float) -> bool:
    return abs(float(a) - float(b)) <= TOL * max(1.0, abs(float(b)))


def main() -> int:
    spec = yaml.safe_load(SPEC_PATH.read_text(encoding="utf-8"))
    failures: list[str] = []

    est_vintage = newest_vintage(REPO_ROOT / spec["input"]["estimates_root"])
    rob_vintage = newest_vintage(REPO_ROOT / spec["input"]["robustness_root"])
    if est_vintage is None or rob_vintage is None:
        print("FAILED — no estimates or robustness vintage on disk")
        return 1
    if est_vintage != rob_vintage:
        fail(failures, f"the newest estimates vintage ({est_vintage}) and robustness vintage "
                       f"({rob_vintage}) differ; the registry publishes one data vintage")
    vintage = est_vintage

    est_ref = f"registry/estimates/{vintage}/{spec['input']['estimates_artifact']}"
    rob_ref = f"registry/robustness/{vintage}/{spec['input']['robustness_artifact']}"
    estimates = json.loads((REPO_ROOT / est_ref).read_text(encoding="utf-8"))
    robustness = json.loads((REPO_ROOT / rob_ref).read_text(encoding="utf-8"))

    cards = {}
    for path in sorted(CARDS_DIR.glob("*.json")):
        if path.name == "index.json":
            continue
        card = json.loads(path.read_text(encoding="utf-8"))
        cards[card["dag_id"]] = card
    index = json.loads((CARDS_DIR / "index.json").read_text(encoding="utf-8"))

    # ---- 1. the vintage chain ----------------------------------------------------------------
    for dag_id, card in cards.items():
        if card["vintage_date"] != vintage:
            fail(failures, f"{dag_id}: card vintage {card['vintage_date']} but the estimates vintage is "
                           f"{vintage} — the card would quote a number from a different data vintage")
        if card["schema_version"] != index["schema_version"]:
            fail(failures, f"{dag_id}: card schema {card['schema_version']} vs index "
                           f"{index['schema_version']}")
    print(f"vintage {vintage} | {len(cards)} cards | estimates {est_ref} | robustness {rob_ref}")

    # ---- 2. which cards should carry a number, recomputed ------------------------------------
    a_specs = [s for s in estimates["specifications"] if s["design"] == "A"]
    b_specs = [s for s in estimates["specifications"] if s["design"] == "B"]
    card_outcomes = {card["outcome"]["id"] for card in cards.values()}
    should_carry = {s["outcome"]: s for s in a_specs if s["outcome"] in card_outcomes}
    without_card = [s["outcome"] for s in a_specs if s["outcome"] not in card_outcomes]

    declared = spec["mapping"]["design_a"]["expectation"]
    if len(a_specs) != declared["published_specifications"]:
        fail(failures, f"design A: {len(a_specs)} published specifications, registry.yml declares "
                       f"{declared['published_specifications']}")
    if len(should_carry) != declared["cards_that_carry_one"]:
        fail(failures, f"design A: {len(should_carry)} cards should carry a number, registry.yml "
                       f"declares {declared['cards_that_carry_one']}")
    declared_without = sorted(x["outcome"] for x in spec["mapping"]["design_a"]["without_a_card"])
    if sorted(without_card) != declared_without:
        fail(failures, f"design A: published without a card = {sorted(without_card)}; registry.yml "
                       f"declares {declared_without}")

    # ---- 3. every card's block, recomputed ---------------------------------------------------
    n_estimated = 0
    recomputed_reasons: dict[str, int] = {}
    for dag_id, card in sorted(cards.items()):
        outcome = card["outcome"]["id"]
        design = card["design"]["id"]
        block = card.get("estimate")
        if not block:
            fail(failures, f"{dag_id}: no estimate block at all")
            continue

        expected_status = "estimated" if (design == "A" and outcome in should_carry) else "not_estimated"
        if block["status"] != expected_status:
            fail(failures, f"{dag_id}: status {block['status']}, recomputed {expected_status}")
        if block["the_number_is_for_this_card"] is not (expected_status == "estimated"):
            fail(failures, f"{dag_id}: the_number_is_for_this_card "
                           f"{block['the_number_is_for_this_card']} with status {block['status']}")

        if expected_status == "estimated":
            n_estimated += 1
            want = should_carry[outcome]
            got = block["specification"]
            for key in ("coefficient", "standard_error", "ci_low", "ci_high", "p_value"):
                if key not in got:
                    fail(failures, f"{dag_id}: specification.{key} missing")
                elif not close(got[key], want[key]):
                    fail(failures, f"{dag_id}: {key} is {got[key]} on the card and {want[key]} in "
                                   f"{est_ref}")
            for key in ("coefficient_name", "outcome", "design", "first_month", "last_month",
                        "estimator", "formula", "covariance"):
                if got.get(key) != want.get(key):
                    fail(failures, f"{dag_id}: specification.{key} is {got.get(key)!r} on the card and "
                                   f"{want.get(key)!r} in {est_ref}")
            for key in ("n_obs", "n_units"):
                if got.get(key) != want[key]:
                    fail(failures, f"{dag_id}: specification.{key} is {got.get(key)} on the card and "
                                   f"{want[key]} in {est_ref}")
            if got["artifact"] != est_ref:
                fail(failures, f"{dag_id}: names the estimates artifact {got['artifact']}, expected {est_ref}")
            # the number must be findable at the index it claims
            idx = got["spec_index"]
            if not (1 <= idx <= len(estimates["specifications"])) or \
                    estimates["specifications"][idx - 1]["outcome"] != want["outcome"]:
                fail(failures, f"{dag_id}: spec_index {idx} does not point at an A specifications "
                               f"entry for {want['outcome']}")

            design_a = next(d for d in estimates["designs"] if d["id"] == "A")
            if block["verdict"]["status"] != design_a["status"]:
                fail(failures, f"{dag_id}: verdict {block['verdict']['status']} vs the estimates "
                               f"artifact's {design_a['status']}")
            level = next((l for l in robustness["support"]["by_axis_level"]
                          if l["design"] == "A" and l["axis"] == "outcome"
                          and str(l["level"]) == outcome), None)
            if level is None:
                fail(failures, f"{dag_id}: the robustness artifact carries no `outcome = {outcome}` level")
            else:
                rob = block["robustness"]
                for key in ("n", "n_positive", "n_negative", "n_opposite"):
                    if rob["axis_level"].get(key) != level[key]:
                        fail(failures, f"{dag_id}: robustness.axis_level.{key} is "
                                       f"{rob['axis_level'].get(key)} on the card and {level[key]} in "
                                       f"{rob_ref}")
                if rob["axis_level"].get("flips_against_preferred") != level["flips_against_preferred"]:
                    fail(failures, f"{dag_id}: robustness flip flag disagrees with {rob_ref}")
                if rob["artifact"] != rob_ref:
                    fail(failures, f"{dag_id}: robustness names {rob['artifact']}, expected {rob_ref}")
                for key in ("n", "n_positive", "n_negative", "n_near_zero"):
                    if rob["design_support"].get(key) != robustness["support"]["by_design"]["A"][key]:
                        fail(failures, f"{dag_id}: design_support.{key} is "
                                       f"{rob['design_support'].get(key)} on the card and "
                                       f"{robustness['support']['by_design']['A'][key]} in {rob_ref}")
                pref = next((s for s in robustness["specifications"]
                             if s["spec_id"] == robustness["preferred"]["A"]), None)
                if pref is not None and rob["this_specification_is_the_preferred_one"] != \
                        (pref["outcome"] == outcome):
                    fail(failures, f"{dag_id}: the preferred-cell flag disagrees with "
                                   f"{robustness['preferred']['A']}")
        else:
            reason = block.get("not_estimated_reason")
            if not reason:
                fail(failures, f"{dag_id}: no number and no reason — the registry must never leave the "
                               f"absence of an estimate unexplained")
                continue
            if reason["code"] not in REASONS:
                fail(failures, f"{dag_id}: reason code {reason['code']!r} is not in the declared set")
            recomputed_reasons[reason["code"]] = recomputed_reasons.get(reason["code"], 0) + 1

            if card["diagnostics"]["status"] == "not_attempted":
                expect = "outcome_series_absent"
            elif design == "B":
                expect = "design_result_is_channel_level"
            elif design == "C":
                expect = "design_not_run"
            else:
                expect = "no_specification_declared"
            if reason["code"] != expect:
                fail(failures, f"{dag_id}: reason {reason['code']!r}, recomputed {expect!r}")
            if len(reason.get("detail", "")) < 20:
                fail(failures, f"{dag_id}: the reason detail is too short to be a reason")

    if n_estimated != declared["cards_that_carry_one"]:
        fail(failures, f"{n_estimated} cards carry a number, recomputed {declared['cards_that_carry_one']}")
    print(f"cards carrying a published number: {n_estimated} / {len(cards)}")
    for code in sorted(recomputed_reasons):
        print(f"  no number, because {code:34s} {recomputed_reasons[code]}")

    # ---- 4. the index -------------------------------------------------------------------------
    if "no estimates attached" in index["layer"]:
        fail(failures, f"the index still claims the registry carries no estimates: {index['layer']!r}")
    counts = index.get("registry", {}).get("card_estimate_counts", {})
    if counts.get("estimated") != n_estimated:
        fail(failures, f"index says {counts.get('estimated')} cards are estimated; the cards say "
                       f"{n_estimated}")
    if counts.get("not_estimated") != len(cards) - n_estimated:
        fail(failures, f"index says {counts.get('not_estimated')} cards are not estimated; the cards "
                       f"say {len(cards) - n_estimated}")
    if counts.get("not_estimated_by_reason") != recomputed_reasons:
        fail(failures, f"index reasons {counts.get('not_estimated_by_reason')} vs recomputed "
                       f"{recomputed_reasons}")
    if index.get("estimates", {}).get("artifact") != est_ref:
        fail(failures, f"index names the estimates artifact {index.get('estimates', {}).get('artifact')}, "
                       f"expected {est_ref}")

    pr = index.get("published_results", {})
    for design, key in (("A", "A"), ("B", "B"), ("C", "C")):
        block = pr.get(key)
        if not block:
            fail(failures, f"published_results.{key} is missing")
            continue
        art = next((d for d in estimates["designs"] if d["id"] == design), None)
        if art is None:
            fail(failures, f"the estimates artifact carries no Design {design} block")
            continue
        if block["status"] != art["status"]:
            fail(failures, f"published_results.{key}.status {block['status']} vs {art['status']}")
        n_published = len([s for s in estimates["specifications"] if s["design"] == design])
        if len(block["specifications"]) != n_published:
            fail(failures, f"published_results.{key} carries {len(block['specifications'])} "
                           f"specifications, the artifact publishes {n_published}")
        for i, s in enumerate(block["specifications"]):
            want = [x for x in estimates["specifications"] if x["design"] == design][i]
            for key_field in ("coefficient", "standard_error", "ci_low", "ci_high"):
                if not close(s[key_field], want[key_field]):
                    fail(failures, f"published_results.{key} specification {i}: {key_field} is "
                                   f"{s[key_field]} and {want[key_field]} in {est_ref}")
    if pr.get("B", {}).get("result_is_card_level") is not False:
        fail(failures, "published_results.B does not declare itself channel-level: nine B cards would "
                       "then appear to be backed by a number that is not about them")
    if pr.get("A", {}).get("result_is_card_level") is not True:
        fail(failures, "published_results.A is not declared card-level")
    for dag_id, card in cards.items():
        if card["design"]["id"] == "B" and card["estimate"]["status"] == "estimated":
            fail(failures, f"{dag_id}: a Design B card carries a number, but the B result is the FAAC "
                           f"channel rather than this outcome")
    without = [x["outcome"] for x in pr.get("A", {}).get("specifications_without_a_card", [])]
    if sorted(without) != declared_without:
        fail(failures, f"index publishes {sorted(without)} as without-a-card; registry.yml declares "
                       f"{declared_without}")
    print("index: " + json.dumps(counts.get("not_estimated_by_reason", {})))

    # ---- 5. the card wins ---------------------------------------------------------------------
    # The rule PHASES.md Stage 8 states is that when a card and the narrative disagree the card wins. It
    # can only be checked where the narrative is machine-readable: the two documents that quote a Stage 7
    # number must quote the one the artifact carries. A mismatch is reported as a stale narrative.
    # The needles are **derived from the artifacts**, not typed here. A literal in this verifier would
    # only catch a document that changed; deriving it catches the artifact moving under a document that
    # did not — which is the failure this repository has actually had (C-44, C-49, and the events cell
    # split corrected on 2026-10-20). Whitespace is normalised because the documents wrap their prose.
    a_support = robustness["support"]["by_design"]["A"]
    b_support = robustness["support"]["by_design"]["B"]
    preferred_a = next(s for s in estimates["specifications"]
                       if s["design"] == "A" and s["outcome"] == "fatalities")
    lead = estimates["designs"][0]["checks"]["lead_shift"]
    n_as_large = round(float(lead["p_value"]) * int(lead["n_draws"]))
    narrative_numbers = {
        "docs/estimates.md": [
            (f"{a_support['n_positive']} specifications positive, {a_support['n_negative']} negative",
             "Stage 7's Design A support count"),
        ],
        "docs/limitations.md": [
            (f"{a_support['n_positive']} positive against {a_support['n_negative']} negative",
             "Design A's sign split in the grid"),
            (f"{b_support['n_positive']} of {b_support['n']}", "Design B's support count"),
            (f"+{preferred_a['coefficient']:.4f}", "Design A's published coefficient"),
            (f"**{lead['p_value']:.3f}**", "Design A's lead-shift p-value"),
            (f"{n_as_large} return an estimate at least as large", "the lead-shift count"),
            (f"{counts['not_estimated']} cards carry a reason, not a number",
             "the number of cards with a reason instead of a number"),
        ],
    }
    for rel, required in narrative_numbers.items():
        path = REPO_ROOT / rel
        if not path.exists():
            fail(failures, f"the narrative {rel} is missing, so its claims cannot be checked")
            continue
        text = " ".join(path.read_text(encoding="utf-8").split())
        for needle, what in required:
            if needle in text:
                continue
            fail(failures, f"{rel} does not carry {needle!r} — {what} has moved under the narrative; "
                           f"the card wins, so the narrative is stale (PHASES.md Stage 8)")

    if failures:
        print(f"\nFAILED — {len(failures)} problem(s):")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("\nPASS — every card's number is the artifact's number, every card without one names its reason, "
          "and the index carries the design-level results without lending them to a card")
    return 0


if __name__ == "__main__":
    sys.exit(main())
