# Causal Presidents — the completion plan

**Companion to:** `PHASES.md` (what was built when), `presidents-guided-flow-build-plan.md` (the site),
`docs/decisions.md` (why). **Written:** 2026-10-29, the day the registry re-stamped at vintage
2026-10-29 with the NBS monthly CPI adopted (**C-81**, verified) and GED 26.1 still parked (C-77).

**The rule that orders everything, in one sentence:** no phase begins until the previous phase's exit
criteria are *measured green* — a named check run to completion and passing, not a belief — because each
time that discipline was skipped in this project, a verifier found a defect nobody could have found by
reading (C-42, C-44, C-49, C-52).

**Status markers:** `[ ]` not started · `[~]` in progress · `[x]` done, with the evidence noted.

> **This plan is enforced, not just stated.** The checkboxes below are prose; the *record* is
> `presidents-completion-state.yml`, and `scripts/check_phase_gate.py` fails the whole chain (verify.sh's
> static step and CI's static job) if the state skips ahead: two phases in progress, a phase started
> before the one before it closed, a phase marked done without a named check + date, or a phase list
> that drifted from the plan. Moving to the next phase means editing the state file only after the
> previous phase's exit criteria are observed green - the gate catches everything else.

---

## Phase A — adopt GED 26.1 (the data revision pass)

**Why it is first.** 26.1 *revises* 173 of the 175 overlapping cells inside Design A's estimation window
(fatalities +1.55%, incidents +2.41% in-window; 12 new months beyond it). Any fit done in earlier phases
would have to be re-fit under the revised history anyway, so every phase below waits for this one.

- [x] **A1. Spec first, engine second.** Edit `analysis/specs/estimation.yml` BEFORE any fit: the stale
  window sentence ("UCDP ends 2024-12 (GED 25.1)") and the 3,456 sample count — both re-derived from the
  26.1 parse, never estimated by eye.
- [x] **A2. Move the adopted label.** `ingestion/clients/ucdp.py`: `ADOPTED = "25.1"` → `"26.1"`. The
  release is already landed at `data/pending/ucdp/2026-10-29/` — it moves into `data/raw/ucdp/` under the
  C-79 rule (raw = adopted claim, now true), the same move the CPI vintage made in its adoption pass.
- [x] **A3. Reparse, regate, rebuild.** `ingestion/parsers/ucdp_events.py` → staging regenerated from 26.1;
  `check_quality.py` publishes the new quality vintage; `dbt build` (expect the test count to move only if
  a table's contract changed — a revision moves values, not schema).
- [x] **A4. Re-run the R chain** in declared order (`02_diagnostics`, `01_build_dags`, `11_design_c`,
  `03_estimate`, `04_robustness`, `05_registry`, `06_events`–`10_tenure`) with the stage specs' `labelled:`
  fields moved to the new date — the same eight specs the CPI adoption moved.
- [x] **A5. Measure the verdict movement as a revision, not a finding.** Field-by-field compare the new
  estimates/robustness/events artifacts against the 2026-10-29 family (the diff script pattern recorded in
  PROGRESS 2026-10-29). A moved coefficient or a moved verdict is reported **as a data revision the source
  published**, in `decisions.md` (C-82) and on `docs/limitations.md` — never as "better" or "new".
- [x] **A6. Exit criteria.** `validate_artifacts.py` PASS · all 24 verifiers PASS · the "the card wins"
  chain (`verify_registry`, `verify_app`, `verify_site`) PASS on numbers that are the 26.1 numbers ·
  `data/pending/` empty except whatever the next phase parks. **Do not proceed to Phase B until all green.**

## Phase B — the monthly inflation outcome in Design B (the subsidy estimand)

**Why it is second.** The acquisition is done and gated (C-81); what remains is a *decision*, then a fit.
Phase A first because B's sample would otherwise be re-fit on the revised security history once more.

- [x] **B1. Declare, then fit.** The choice to record in `decisions.md` first: does Design B read the
  monthly NBS series as the inflation outcome for a declared specification, with `cpi_yoy` (annual)
  retained as the annual cross-check reference? The base already carries
  `nbs_cpi_national_monthly` unspined; the catalogue entry (`raw_metric_catalogue`) plus the estimation
  spec entry are the declaration, not code changes.
- [x] **B2. Stage 5 re-run on the new pair** (`02_diagnostics.R`): the monthly series must pass (or fail,
  on record) integration/cointegration checks at its native grain before any estimate exists.
- [x] **B3. Fit and publish.** Stage 6/7 re-run; the card answers whether the 2023-06→2023-12
  subsidy-removal window is estimable — either a declared refusal with its reason from the closed set, or
  the first outcome card that works at monthly grain. `docs/limitations.md`, `docs/estimates.md` move with
  it if prose quotes counts.
- [x] **B4. Exit criteria.** Same full-gate battery as A6; plus `validate_artifacts`' C-44 invariant
  (Stage 5 newest == quality newest). **Do not proceed to Phase C until all green.**

## Phase C — close or permanently record every not-estimated reason

**Why it is third.** These are decisions about evidence, best taken when the data layer is final and the
headline designs already say what they say. Each sub-track is a table walk, pair by pair, and the exit is
"no card's reason is a shrug": every no-number card names either a declared refusal (reason + why) or a
planned specific fix.

- [ ] **C1. `no_specification_declared` (10 cards).** For each (outcome, design) pair: declare the
  specification in the relevant stage spec, or record the refusal with its reason. Nothing is "left open".
- [ ] **C2. `design_not_run` (2 cards: `cpi_yoy__C`, `gdp_growth__C`).** Design C is specified for `u5mr`
  only. Decide: extend Design C's spec to these outcomes (where a donor panel exists or is buyable: WB
  country-year GDP exists; the pool extension is declared in `design_c.yml`'s own donor fields) or record
  the refusal. A spec change to C re-runs `11_design_c.R` and `verify_design_c.py` — that is the exit.
- [ ] **C3. `outcome_series_absent` (12 cards).** Audit award series against sources, cheapest first:
  (i) cross-country *security* outcomes for Design C are likely cheap — UCDP's bulk archive is keyless and
  country-level pages exist (a client of the `ucdp.py` family); (ii) the World Bank outcomes for missing
  B/C donor panels come from an already-adopted source (a second WDI dataset id + parser wiring);
  (iii) education (NEMIS/UIS) stays **permanently refused on the record** — C-11/C-12 measured both dead;
  only a verified new source reopens it. Acquisitions follow the standing pattern: land → parse → verify →
  declare in the gate → adopt in one accountable pass (C-79/C-81), never silently.
- [ ] **C4. `variables_still_missing` audit.** The index list still names FAAC and primary-completion as
  missing while both are landed — the list's *grain* is the unresolved pieces (D1 needs the state
  population denominator, X-09). Trim it to what is genuinely outstanding, with the audit written down.
- [ ] **C5. Exit criteria.** Every card's reason re-published with its final state; `verify_dags.py`'s
  G-11 check (the index carries missing variables) PASS; the full battery green. **Do not proceed to
  Phase D until green.**

## Phase D — (optional) the RAGAS library run on Colab

- [ ] **D1.** Only if the judge API budget is approved: run RAGAS with an LLM judge on Colab (free tier),
  the four metric definitions against the same 15 answers + corpus, `library: true` beside the existing
  `library: false` artifact. **Scores are not comparable to the in-repo implementation** — that sentence
  travels onto the artifact and `docs/rag.md` as it already does for the in-repo runs. Skip is allowed;
  record the skip as a decision either way. Exit: artifact published or refusal recorded.

## Phase E — delivery polish

- [ ] **E1.** README quickstart mirrors reality (`scripts/verify.sh`, the conda env, R required in one path).
- [ ] **E2.** Blog/video: decide to skip or do, and record the decision so PHASES.md stops carrying it as
  "undocumented".
- [ ] **E3.** One-command proof: `scripts/verify.sh` end-to-end green from a clean checkout pattern
  (acquire path included). Exit: the script's `all checks passed` line, actually observed.
- [ ] **E4.** Live deployment check: the Pages URL serves the re-built site at the final registry vintage.

## Phase F — completion freeze

- [ ] **F1.** `PROGRESS.md`, `PHASES.md`, `docs/decisions.md` final-state edit; every card reason final;
  `git log` clean (no uncommitted verifier state). Final commit. The project is done when **the checkout
  itself is the deliverable**: any reader runs `verify.sh` and watches it pass.

---

## Standing constraints (apply to every phase)

1. A spec is declared and frozen before the engine that applies it runs; the engine publishes before the
   site renders from it; nothing deploys off a red chain.
2. Corrections create new vintages; superseded directories are never edited (X-07 in `data/raw/` *and*
   `registry/`).
3. Every displayed number is a field of a registry artifact; a missing estimate names a reason from the
   closed set — never silence.
4. A verifier that has never been red is broken; break it on purpose before trusting the green.
5. Raw payloads stay out of git; publish code and derived aggregates only.
