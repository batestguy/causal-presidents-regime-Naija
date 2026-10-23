"""Causal Presidents — the read-only app over the published registry.

What this is: outcome → identification design → the assumption it rests on → the published number, or the
reason there is not one. Every value is read from `registry/dags/`; nothing is fitted at render time (base
spec §18), nothing is computed, and no number is typed into this file — `tests/verify_app.py` greps for the
published coefficients to keep it that way.

The **Ask** tab is the same rule one level down: a question goes to the intent gate and then to the
answer layer, and the answer is assembled from the registry's own passages and cites them. A question the
registry cannot answer is refused with the passage that says why. The layer is BM25 over committed text
(`app/answer_layer.py`), so no model is called, no key is needed, and no number is generated.

What it deliberately is not: a dashboard of the raw series (the monthly spine is 16.2 % observed, which is a
plot about coverage rather than about presidents).

Run:
    /c/Users/TOSHIBA/ds-general/python.exe -m streamlit run app/streamlit_app.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import streamlit as st

APP_DIR = Path(__file__).resolve().parent
REPO_ROOT = APP_DIR.parent
# The app directory first, so `registry_data` is this file's sibling; the repository root second, so the
# answer layer imports as `app.answer_layer` and the gate it needs comes with it.
sys.path.insert(0, str(APP_DIR))
sys.path.insert(0, str(REPO_ROOT))

from registry_data import (  # noqa: E402  (the path is set above so the app runs from any cwd)
    RegistryError,
    coverage_words,
    direction_words,
    estimate_rows,
    interval,
    load_registry,
    precheck_lines,
    reason_text,
    result_spec_rows,
    robustness_text,
    signed,
    verdict_text,
)

st.set_page_config(page_title="Causal Presidents", layout="wide")


@st.cache_data(show_spinner=False)
def _registry(root: str):
    return load_registry(root)


# The questions the chat offers are the project's own published ones: the app reads their text from the
# published evaluation set rather than carrying a copy, so an example cannot drift from the question the
# measurement was run on. The ids are the only thing typed here, and they name one of each kind of
# exchange — an estimate, a design that was not run, a fact, and a refusal.
CHAT_EXAMPLE_IDS = (
    "q01_fatalities_elasticity",
    "q06_design_c_status",
    "q08_observed_share",
    "o04_normative_allocation",
)


@st.cache_data(show_spinner=False)
def _chat_examples(root: str, vintage: str) -> list[tuple[str, str]]:
    """The published questions the chat offers, read from the published evaluation set."""
    path = Path(root) / "registry" / "rag" / vintage / "eval_set.json"
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    rows = {str(row.get("id")): row for row in data.get("questions") or []}
    found: list[tuple[str, str]] = []
    for question_id in CHAT_EXAMPLE_IDS:
        row = rows.get(question_id)
        if row and row.get("question"):
            found.append((question_id, str(row["question"])))
    return found


@st.cache_resource(show_spinner=False)
def _chat_layer(root: str):
    """The answer layer over the published vintage: the gate, the corpus and the answer contract.

    It is loaded when a reader asks a question, not when the page opens: the corpus is the largest
    thing this app reads, and a reader who never asks anything should never wait for it.
    """
    from app.answer_layer import load_layer

    return load_layer(root)


def _render_turn(question: str, answer) -> None:
    """One exchange: the question, and the answer with its plain reading first.

    The plain reading is what a reader gets; the contract's own answer is one click away, because the
    plain reading is a second reading of it and never replaces it.
    """
    with st.chat_message("user"):
        st.markdown(question)
    with st.chat_message("assistant"):
        plain = str((answer.plain or {}).get("text") or answer.text)
        if answer.answered:
            st.markdown(plain)
            with st.expander("The answer as the registry states it"):
                st.markdown(answer.text)
        else:
            st.warning(plain)
            with st.expander("The refusal as the registry states it"):
                st.markdown(answer.text)


try:
    registry = _registry(str(REPO_ROOT))
except RegistryError as exc:  # a registry mid-rebuild is shown, never rendered around
    st.error(f"The registry cannot be rendered faithfully: {exc}")
    st.stop()

counts = registry.card_counts()
total_cards = int(counts.get("estimated", 0)) + int(counts.get("not_estimated", 0))
designs = registry.designs()
design_short = {row["id"]: row["short"] for row in designs}

# ---------------------------------------------------------------------------------------------
# Sidebar — what the page is about
# ---------------------------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### Choose a question")
    outcome_id = st.selectbox(
        "Outcome",
        key="outcome",
        options=[row["id"] for row in registry.outcomes()],
        format_func=lambda oid: f"{registry.outcome(oid)['label']} · {registry.outcome(oid)['domain']}",
        help="The 12 catalogue outcomes. A declared coverage gap is a stated absence, not a null result.",
    )
    design_id = st.radio(
        "Causal model",
        key="causal_model",
        options=[row["id"] for row in designs],
        format_func=lambda did: f"{did} — {registry.design(did)['name']}",
    )
    st.divider()
    st.caption(
        f"Registry vintage **{registry.vintage}**. Every number below is copied from the card it is shown "
        f"on; nothing is re-fitted here."
    )

card = registry.card(outcome_id, design_id)
outcome = card.get("outcome") or registry.outcome(outcome_id)
design = card.get("design") or registry.design(design_id)
estimate = card.get("estimate") or {}
status = estimate.get("status", "not_estimated")

st.title("Causal Presidents")
st.caption(
    "Presidential transitions and national outcomes in Nigeria, 1999–present. "
    "Read the assumption before the number."
)
st.markdown(
    f"**{counts.get('estimated')} of {total_cards} model cards carry a published number; the rest say why "
    f"not.** This page is showing *{outcome['label']}* under **Design {design_id} — {design['name']}**."
)

card_tab, result_tab, about_tab, chat_tab = st.tabs(
    ["Model card", "Design-level results", "What this reads", "Ask the registry"]
)

# ---------------------------------------------------------------------------------------------
# Model card
# ---------------------------------------------------------------------------------------------
with card_tab:
    st.subheader(f"{outcome['label']} — Design {design_id}: {design['name']}")
    st.markdown(
        f"**Outcome.** `{outcome['id']}`. Unit: {outcome.get('unit', 'not stated')}. "
        f"Direction: {direction_words(outcome.get('direction'))}. "
        f"Frequency: {outcome.get('frequency', 'not stated')}. "
        f"Source: {outcome.get('source', 'not stated')}."
    )
    st.markdown(f"**Coverage.** {coverage_words(outcome.get('coverage_status'))}.")
    if outcome.get("coverage_note"):
        st.caption(outcome["coverage_note"])
    st.markdown(
        f"**Estimand.** {design.get('estimand', 'not stated')}  \n"
        f"**Estimator.** {design.get('estimator', 'not stated')}  \n"
        f"**Unit.** {design.get('unit', 'not stated')}"
    )

    assumption_col, number_col = st.columns([3, 2], gap="large")

    with assumption_col:
        st.markdown("#### The assumption this rests on")
        st.markdown(card.get("identifying_assumption", "not stated"))
        st.markdown(
            f"**Adjustment set** — {design.get('adjustment_criterion', 'the declared')} criterion, resolved by "
            f"dagitty on the assumed graph in this card:"
        )
        labels = registry.adjustment_labels(card)
        st.markdown("\n".join(f"- {label}" for label in labels) or "- none")
        st.markdown("**Assumed absent** — the node this design needs not to exist:")
        absent = registry.assumed_absent_labels(card)
        st.markdown("\n".join(f"- {label}" for label in absent) or "- none")
        st.markdown("**What this design cannot rule out:**")
        caveats = card.get("cannot_rule_out") or []
        st.markdown("\n".join(f"- {item}" for item in caveats) or "- not stated")

    with number_col:
        st.markdown("#### The published number" if status == "estimated" else "#### A number for this pair")
        if status == "estimated":
            spec = estimate.get("specification") or {}
            st.markdown(f"### {signed(spec['coefficient'])}")
            st.markdown(
                f"95 % interval **{interval(spec['ci_low'], spec['ci_high'])}** · p = {spec['p_value']:.4f}"
            )
            st.markdown(
                f"{spec['n_obs']:,} observations over {spec['n_units']} units, "
                f"{spec.get('first_month', '?')} to {spec.get('last_month', '?')}."
            )
            verdict = (estimate.get("verdict") or {}).get("status", "not stated")
            if verdict == "estimated_not_identified":
                st.warning(
                    f"**Verdict: `{verdict}`.** A number exists for this pair and the design does not "
                    f"identify it. The check that decided that came first:"
                )
            else:
                st.info(f"**Verdict: `{verdict}`.**")
            st.markdown(verdict_text(estimate))
            with st.expander("Every field of the published specification"):
                for label, value in estimate_rows(estimate):
                    st.markdown(f"- **{label}:** {value}")
            grid = robustness_text(estimate)
            if grid:
                st.caption(grid)
        else:
            code, detail = reason_text(estimate)
            st.info(f"**Reason: `{code}`**")
            st.markdown(detail)
            if estimate.get("published_result"):
                st.markdown(
                    f"The design's own result is published once, on the index, at "
                    f"`{estimate['published_result']}` — see the *Design-level results* tab. It is not an "
                    f"estimate for this outcome."
                )

    st.divider()
    st.markdown("#### Stage 5 pre-check, run before anything was estimated")
    for line in precheck_lines(card):
        st.markdown(line)

    svg_path = registry.svg_path(card)
    if svg_path.exists():
        st.markdown("#### The assumed causal graph")
        st.html(
            "<div style='max-height:430px;overflow:auto'>"
            + svg_path.read_text(encoding="utf-8")
            + "</div>"
        )
        st.caption(
            "The unobserved node is drawn and named rather than omitted. Adjustment sets are computed on the "
            "assumed graph, never hand-listed."
        )
    else:
        st.caption(f"The card names a figure at `{svg_path}` that is not on disk.")

    st.caption(
        f"Card: `registry/dags/{card['dag_id']}.json` · vintage {registry.vintage} · "
        f"schema {card.get('schema_version', '?')}"
    )

# ---------------------------------------------------------------------------------------------
# Design-level results
# ---------------------------------------------------------------------------------------------
with result_tab:
    st.subheader("The results that are not about a single card")
    st.markdown(
        "Design B's published result measures the **national FAAC channel**, and on every B card FAAC is a "
        "mediator rather than the outcome; Design C was not run. Both are published here, once, rather than "
        "on twelve cards each where they could be mistaken for that card's estimate."
    )
    result_design = st.radio(
        "Design",
        options=[row["id"] for row in designs],
        horizontal=True,
        format_func=lambda did: f"{did} — {design_short.get(did, did)}",
        key="result_design",
    )
    result = registry.design_result(result_design)
    if not result:
        st.info("The index carries no published result for this design.")
    else:
        st.markdown(
            f"**Status: `{result.get('status')}`** · card-level: "
            f"`{str(result.get('result_is_card_level')).lower()}`"
        )
        if result.get("result_outcome"):
            st.markdown(f"**What the number is about:** {result['result_outcome']}")
        verdict = result.get("verdict") or {}
        if verdict.get("rule"):
            st.markdown(f"**Verdict rule, fixed before the numbers were read:** {verdict['rule']}")
        failed = verdict.get("failed_checks")
        if isinstance(failed, list):
            st.markdown(f"**Failed checks:** {', '.join(failed) if failed else 'none'}")
        elif failed:
            st.markdown(f"**Failed check:** {failed}")

        rows = result_spec_rows(result)
        if rows:
            st.markdown("#### Published specifications")
            st.dataframe(rows, width="stretch", hide_index=True)
            for row in rows:
                st.markdown(
                    f"- {row['specification']}: {row['estimate']} {row['95 % interval']} "
                    f"(p = {row['p']}, n = {row['n']}, {row['window']})"
                )
        elif result_design == "C":
            st.markdown("**Published specifications:** none — the design was not run.")

        robustness = result.get("robustness") or {}
        support = robustness.get("support") or {}
        if support:
            st.markdown(
                f"#### Robustness\n{support.get('n_positive')} of the design's {support.get('n')} "
                f"specifications are positive and {support.get('n_negative')} negative; "
                f"{support.get('n_positive_ci')} have an interval entirely above zero and "
                f"{support.get('n_negative_ci')} entirely below it. "
                f"{robustness.get('sign_flip_levels')} axis levels flip against the preferred specification."
            )
        if result.get("why"):
            st.markdown("#### Why it was not run" if result.get("status") == "not_run" else "#### Why")
            st.markdown(result["why"])
        if result.get("next_step"):
            st.markdown(f"**Next step:** {result['next_step']}")
        artifact = (result.get("artifacts") or {}).get("estimates")
        if artifact:
            st.caption(f"Source: `{artifact}` · registry vintage {registry.vintage}")

# ---------------------------------------------------------------------------------------------
# What this reads
# ---------------------------------------------------------------------------------------------
with about_tab:
    st.subheader("What this page reads, and what it refuses to do")
    st.markdown(
        f"- `registry/dags/index.json` — the registry index, vintage **{registry.vintage}**\n"
        f"- `registry/dags/<outcome>__<design>.json` — **{len(registry.cards)}** model cards\n"
        f"- `registry/dags/<outcome>__<design>.svg` — the assumed causal graph beside each card"
    )
    st.markdown(
        f"- `registry/rag/{registry.vintage}/corpus.json` — the published corpus the **Ask** tab reads\n"
        f"- `registry/rag/{registry.vintage}/eval_set.json` — the published questions the tab offers\n"
        "- `analysis/specs/intent_gate.yml`, `analysis/specs/rag.yml` — the gate's rules and the answer contract\n"
        "- `docs/glossary.md` — the plain meanings the answers use"
    )
    st.markdown(
        "**Nothing is fitted at render time.** The app holds no model, opens no database and makes no network "
        "call. A number on this page is a field of a card written by an R stage; if the page and the card ever "
        "disagree, the card wins and this code is wrong."
    )
    st.markdown(
        f"**The ratio the app exists to state:** {counts.get('estimated')} of {total_cards} cards carry a "
        "published number. The rest carry a reason from a closed set, so an absent estimate is never silent:"
    )
    for code, count in (counts.get("not_estimated_by_reason") or {}).items():
        st.markdown(f"- `{code}` — {count} card(s)")
    st.divider()
    st.markdown(
        "**What this page does not answer.** It renders published estimates and the assumptions they rest on. "
        "It does not compare tenures, forecast, or recommend policy. The tenure comparison is not identifiable "
        "with this data — four to five administrations against 22–23 annual observations per outcome — and "
        "`docs/limitations.md` is where that arithmetic is written down. The **Ask** tab answers from the "
        "published corpus and refuses what the corpus cannot answer, but it answers the registry's questions, "
        "not the reader's wishes: a forecast, a policy recommendation or a comparison of tenures is refused "
        "with the passage that says why, and the refusal carries a code and a citation."
    )

# ---------------------------------------------------------------------------------------------
# Ask the registry — the gate and the answer layer, in the reader's own words
# ---------------------------------------------------------------------------------------------
with chat_tab:
    st.subheader("Ask the registry")
    st.markdown(
        "Ask about the published cards, the numbers they carry, or the reasons they do not. The answer is "
        "assembled from the registry's own passages and cites them; a question the registry cannot answer is "
        "refused with the passage that says why. Nothing is generated — the retrieval is the same BM25 the "
        "retrieval evaluation measures — so no model is called and no key is needed."
    )
    examples = _chat_examples(str(REPO_ROOT), registry.vintage)
    if examples:
        st.markdown("**Questions this project has published and measured:**")
        for _question_id, example in examples:
            st.markdown(f"- {example}")
        st.caption("Type one of them, or ask your own.")
    else:
        st.caption("The published evaluation set is not on disk, so there are no example questions to show.")

    # The conversation is rendered into a container placed above the input, so the newest exchange
    # appears above the question box rather than under it.
    conversation = st.container()
    question = st.chat_input("Ask the registry a question…")

    if "chat_turns" not in st.session_state:
        st.session_state["chat_turns"] = []
    turns = st.session_state["chat_turns"]

    with conversation:
        for asked, answer in turns:
            _render_turn(asked, answer)
        if question:
            try:
                answer = _chat_layer(str(REPO_ROOT)).answer(question)
            except (OSError, ValueError, KeyError) as exc:
                st.error(
                    f"The registry cannot answer that question right now: {exc}. The registry is being "
                    f"rebuilt, and the app shows that rather than answering around it."
                )
            else:
                turns.append((question, answer))
                _render_turn(question, answer)
