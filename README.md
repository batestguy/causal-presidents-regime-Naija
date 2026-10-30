# Causal Presidents

**Regime and national outcomes in Nigeria, 1999–present — an interactive causal-inference explorer.**

Visitors will ask causal questions of a model *and* open the fitted models behind the answers:
coefficient tables, intervals, diagnostics and sensitivity bounds.

> **Presidents are one input, not the cause.** Presidential influence on Nigerian outcomes is heavily
> mediated by oil price cycles, state governments, donor funding and inherited conditions. This project
> is built to show those confounders rather than hide them, and it reports adjusted **associations** —
> never an unconditional causal fact. Where the design cannot identify an effect, it says so.

---

## Status: Stages 0–9, the analysis chain verified and the read-only app built — the registry carries two numbers

> **The headline finding (2026-10-18): an oil-price shock reaches Nigeria's states, federal money does not
> visibly buy peace, and the tenure question has one answerable half.** A 10 % rise in Brent reaches state allocations as roughly **5 % more money, two
> to three months later** (cumulative elasticity +0.518 at h=2, HAC SE 0.166; C-48), and that sign holds in
> **all 24** specifications of the robustness grid — though the *timing* is its weak part: an in-time
> placebo across 48 shifted alignments returns p = 0.0625. The state dose-response question *can* be
> estimated — 3,888 state-months — and **cannot be identified** from this dose: a mis-timed dose fits just
> as well, because what survives the fixed effects is the 13 % derivation share moving with the oil price
> (C-47). Asked 81 ways, **its sign survives most of the grid** — 60 positive against 21 negative — and the
> check that still fails is the lead-shift placebo, not the grid (C-82). The presidential-tenure question is **not answerable at all**
> from 4–5 administrations and 27 annual observations — though **the timing half of it is answerable**: on
> the one monthly outcome, two of eight transition-outcome cells survive both the placebo and the pre-trend
> check (`registry/events/2026-10-18/`). And the synthetic-control design that could not be built is no
> longer blocked on data: widening the donor pool from 13 countries to **99** took it from `infeasible` to
> passing its pre-fit gate on `u5mr` (3 of 4 windows). Full write-ups:
> [`docs/estimates.md`](docs/estimates.md), [`docs/robustness.md`](docs/robustness.md) and
> [`docs/events.md`](docs/events.md) — and the boundary all three sit inside,
> [`docs/limitations.md`](docs/limitations.md).

| | |
|---|---|
| Specification | ✅ Complete (`nigeria-causal-inference-spec.md`, `PHASES.md`) |
| Ingestion | ✅ **Five** sources working, provenance-verified: 22 national indicators + a **99-country** synthetic-control candidate panel + the Brent crude oil series + 174 FAAC disbursement documents (the state fiscal dose) + the UCDP GED security events (the state-attributed outcome — **keyless**, C-45) |
| Assumption layer | ✅ **36 causal graphs** — 3 identification designs × 12 outcomes, with the adjustment set computed from each graph |
| Quality gates | ✅ **Stage 3** — 5 gates over **674 series**: 359 ok, 313 flagged, 2 empty, 0 silently dropped (the donor pool's 495 country-series join the 37 FAAC ones and the 117 UCDP scopes; the 2 empty are `Eritrea`/`Somalia` CPI, declared with no data at all) |
| Analytical base | ✅ **Stage 4** — one monthly table, 8,350 rows (25 metrics × 334 months), index-anchored, with the party-by-tenure strata, the Stage 3 quality status and the 37 × 334 state panel carrying both the dose and the outcome |
| Pre-analysis diagnostics | ✅ **Stage 5** — every design validated before estimation, **re-run at vintage 2026-10-18** after the donor pool was widened from 13 countries to **99 candidates**. **1 of 36 cards passes its pre-check** — `u5mr` under Design C (14 fail, 9 degraded, 12 not attempted): Family A dropped on the dose *axis* (per capita waits on X-09) with the outcome blocker now cleared, B degraded (annual grain, a 38–99 SD detectable effect), and **C moved from `infeasible` to `pass` on `u5mr` (3 of its 4 windows)** while `gdp_growth` (1 of 4) and `cpi_yoy` (0 of 4) still fail the gate — with the rollup now a **declared strict-majority rule** and the caveat that a 99-donor simplex can fit almost any pre-period |
| Estimation | ✅ **Stage 6** — 12 specifications across two designs (3 Design A outcomes, 9 Design B horizons), every one published with its interval and the check that decided its verdict. Verifier recomputes every number to 1e-12 |
| Robustness | ✅ **Stage 7** — **105 specifications** declared before fitting and all published, with the specification curve drawn and the support counts computed from the fitted rows: Design B 24/24 positive, Design A 60 positive / 21 negative with one majority sign-flip level (2 of the 105 sit inside a declared ±0.02 near-zero band and are counted as such). Verifier re-fits every one of them (worst coefficient gap 6.5e-9) |
| Within-tenure timing | ✅ **Stage 8b** — the transition event study: **4 in-window transitions** on 324 months of UCDP conflict (1999-01→2025-12, the only monthly outcome), 32 specifications, inference by **exhaustive placebo assignment** over 58 eligible months. **2 of 8 event-outcome cells survive both the placebo and the pre-trend check**, 4 fail the pre-trend, 1 event cannot be checked at all (declared, not scored as a pass), and the party split is published as **description with no test**. Verifier re-fits all 32 and re-enumerates the placebo distribution (worst HAC SE gap 0.002 %) |
| Retrieval corpus | ✅ **Stage 8c** — **441 chunks from 51 attributed sources** at the registry's vintage: one document per model card (179 parts), the three design results, the narrative, the data dictionary, the transition events, the tables, the two coverage counts and the scope paragraph. Every chunk records its source's sha256, so a document edited without a rebuild fails the verifier. Measured on `multi-qa-MiniLM-L6-cos-v1`: **recall@5 0.944** (BM25 baseline 0.833), MRR 0.724; **two refusal gates fail and are published** — reason-bearing refusals 0.5, out-of-scope 0.25, because a forecast about a covered outcome embeds closer than some real questions do. RAGAS declared `not_run` (no LLM key). `docs/rag.md` |
| Registry / dashboard | 🔨 **Stage 8, registry half built** — **2 of 36 cards carry a published number, 34 carry a reason** (both Design A cards that can: fatalities +0.4678, incidents +0.5278, each with its interval, its `estimated_not_identified` verdict and the Stage 7 grid summary for its own outcome); Design B's nine specifications are published on the index as **channel-level** (`result_is_card_level: false`, because on every B card FAAC is a mediator) and Design C's non-run likewise; every card without a number names a reason from a closed set. Verifier re-derives the mapping and checks every number against the artifact it names |
| The app | ✅ **Stage 9, read-only half** — `app/streamlit_app.py`: pick an outcome, pick one of the three designs, and get the assumption, the digraph-computed adjustment set, the cannot-rule-out list and the Stage 5 pre-check — then the number with the verdict and the failed check behind it, or the reason there is none. Reads `registry/dags/` only: no database, no network, no model, no coefficient typed into the UI. `tests/verify_app.py` renders **all 36 cards** through Streamlit's own harness and compares the page against the card JSON. **The chat tab is not built**: out-of-scope refusal measures 0.25, so a forecast about a covered outcome is not refused by similarity alone — and shipping that would be the failure the corpus exists to prevent. The framework choice (Streamlit, and what it costs) is a recorded decision, not a default: `docs/decisions.md` UI-01…UI-08 |

**The app runs, read-only, and it leads with the ratio instead of a number.** `2 of 36 model cards carry a
published number; the rest say why not` is the first line on the page, because a reader who scans one card
otherwise cannot tell whether this project estimated two things or failed to estimate thirty-four. There is no
chat tab yet — see `docs/app.md` §3 for why that wait is deliberate.

```bash
conda run -p C:/Users/TOSHIBA/ds-general python -m streamlit run app/streamlit_app.py
python tests/verify_app.py     # renders all 36 cards and compares the page with the cards
```

Ingestion works end to end, the causal-graph assumption layer
is built, the harmonised analytical base the models and the app will read exists, Stage 5 established what
the data can support **before** estimating anything, Stage 6 estimated the part of it that is estimable —
publishing a null and an unidentified estimate beside the one clean result — and Stage 7 asked whether
either survives its own choices, 105 specifications of them. Stage 8b then answered the one tenure-shaped
question the data can carry, on monthly conflict around the four transitions, and refused the rest in
writing. See
[`PROGRESS.md`](PROGRESS.md) for what is verified and what is blocked,
[`docs/limitations.md`](docs/limitations.md) for what cannot be said and why, before any finding,
[`docs/estimates.md`](docs/estimates.md) for the answer to "what can this data actually say?",
[`docs/robustness.md`](docs/robustness.md) for what survives that answer's choices,
[`docs/design-memo.md`](docs/design-memo.md) for the per-design verdict,
[`docs/dags.md`](docs/dags.md) for the graphs, and [`docs/data-dictionary.md`](docs/data-dictionary.md)
for every column of the base.

**And a finding worth stating on the front page**, because it shapes what can be estimated at all: the
monthly spine is only **16.4 % observed** (1,373 of 8,350 rows; it was 10.1 % before the monthly Brent,
FAAC and UCDP landings). The national sources are annual, so a monthly model on `cpi_yoy` cannot see the
2023 fuel-subsidy window — the spine exists, most of its values are interpolation, and the base says which
months those are (`observation_type`) rather than presenting them as data.

**And the first tenure-comparison numbers the project can publish.** Asked *"did conflict change after each
swearing-in?"* on the only monthly outcome, **two of eight event-outcome cells survive both checks**:
reported incidents rose 391 % in the 12 months after the 2010 transition and fatalities 77 % after the 2023
one, each against a 58-month placebo distribution at p = 0.017 — the floor of what 58 placebo months can
resolve. Four cells fail the pre-trend placebo (the 2015 fall in fatalities is real but already under way 24
months earlier), one transition cannot be checked at all, and **no party comparison is made**: two events
against two events has no sampling distribution. [`docs/events.md`](docs/events.md).

## What works today

```bash
PY="conda run -p C:/Users/TOSHIBA/ds-general python"

# Stage 9: the read-only app over the published registry (no database, no R, no keys)
$PY -m streamlit run app/streamlit_app.py

# Pull a World Bank vintage (raw payloads + provenance manifest + coverage report)
$PY ingestion/flows/pull_worldbank.py

# Pull the synthetic-control donor panel (99 candidate countries x 5 screening predictors)
$PY ingestion/flows/pull_worldbank_donors.py

# Pull the oil covariate (Brent crude, daily) - needs a free FRED key in .env
$PY ingestion/flows/pull_fred.py

# Prove the stored raw data is byte-identical to what the API returned, for every source
$PY tests/verify_provenance.py

# Build the causal graphs (R 4.5.2 + ggdag/dagitty): assumption, adjustment set, SVG, card
Rscript analysis/R/01_build_dags.R
$PY tests/verify_dags.py

# Stage 3: gate every landed series, then verify the report independently
$PY ingestion/flows/check_quality.py
$PY tests/verify_quality.py

# Stage 4: build the analytical base (dbt + DuckDB), then recompute it from the raw payloads
conda run -p C:/Users/TOSHIBA/ds-general dbt build --project-dir dbt --profiles-dir dbt
$PY tests/verify_harmonisation.py

# Stage 5: pre-analysis diagnostics - which designs survive, then verify every number independently
Rscript analysis/R/02_diagnostics.R && Rscript analysis/R/01_build_dags.R   # engine + attach to cards
$PY tests/verify_stage5.py

# Land the security outcome (keyless, CC-BY) and parse it to state-month
$PY ingestion/flows/pull_ucdp.py && $PY ingestion/parsers/ucdp_events.py

# Stage 6: estimate, then recompute every coefficient, sample and verdict independently
Rscript analysis/R/03_estimate.R        # -> registry/estimates/<vintage>/
$PY tests/verify_stage6.py

# Stage 7: fit the declared multiverse and draw the specification curve, then re-fit all 105 independently
Rscript analysis/R/04_robustness.R      # -> registry/robustness/<vintage>/
$PY tests/verify_stage7.py

# Stage 8b: the transition event study - what moved inside each tenure - then re-fit all 32 independently
Rscript analysis/R/06_events.R          # -> registry/events/<vintage>/
$PY tests/verify_events.py

# Everything above, in order, with one exit status
scripts/verify.sh
```

Last run: 22/22 national indicators, 5/5 donor-panel predictors, 1/1 oil series, 1/1 conflict archive and
174 FAAC disbursement documents — **203 payloads across 5 sources**, every one reproducing its recorded
`sha256`, 0 orphaned files. 36/36 DAGs built, and every one verified to be acyclic, schema-valid, and to
have an adjustment set that provably blocks every backdoor path in its graph.

The oil series is Brent crude from FRED: 10,275 daily observations spanning 1987→2026, provenance
verified. It refuses to overwrite a landed vintage, because the raw layer is immutable.

The analytical base is 8,350 rows = 25 metrics × 334 months, built by dbt from the raw layer plus the
declared rules in `analysis/specs/harmonisation.yml`: a January-2000 index anchor (with the fallback
recorded per metric), the base-spec §7 administration spine split into term-level party-by-tenure
strata, the 37 × 334 state panel whose dose columns are filled for 4,104 state-months and declared gaps
elsewhere, and every definition break the quality gates found. **136 data tests** hold it, and
`tests/verify_harmonisation.py` recomputes the whole thing from `data/raw/` without importing a single
dbt model.

Key-gated sources read free credentials from a gitignored `.env` — copy `.env.example` to `.env`:

| Variable | Source | Status |
|---|---|---|
| `FRED_API_KEY` | Brent crude oil price ([register](https://fred.stlouisfed.org/docs/api/api_key.html)) | ✅ set, series landed |
| ~~`UCDP_ACCESS_TOKEN`~~ | Organised-violence fatalities | ✅ **Not needed** — its *API* wants a token (401), its **bulk archive** does not (200, 29 MB, CC-BY), and that is what landed (C-45) |
| ACLED | Security events (now **OAuth**, not a key) | not yet wired |

## Repository layout

```
docs/decisions.md     decision log — every choice, dated, with its reason
docs/licences.md      per-source redistribution rights and open licensing questions
docs/dags.md          the causal-graph layer: designs, assumptions, variable sources
PHASES.md             the plan: Stages 0–8, data collection through analysis
ingestion/clients/    one client per source, plus shared provenance
ingestion/flows/      stage runners that land a vintage, and the Stage 3 gate runner
ingestion/quality/    the five Stage 3 gates, as pure functions
analysis/specs/       outcome registry, the three identification designs, gate config, harmonisation rules
analysis/R/           one script per stage that runs in R: DAG generator, Stage 5 diagnostics,
                      Stage 6 estimates, Stage 7 robustness grid, Stage 8b transition event study
dbt/                  the transformation project: seeds (spine, catalogue, shocks, states),
                      models/staging (raw payloads -> typed observations) and models/analytics
                      (dimensions, the spine, the index anchor, the analytical base table)
registry/dags/        the DAG cards, JSON schemas and figures
registry/quality/     the vintage quality report (gate results per series)
registry/diagnostics/ the Stage 5 pre-check result (diagnostics.json + report.md)
registry/estimates/   the Stage 6 estimates (estimates.json + report.md), one dir per vintage
registry/robustness/  the Stage 7 multiverse (robustness.json + report.md + specification_curve.svg)
registry/events/      the Stage 8b transition event study (events.json + report.md + event_study.svg)
registry/rag/         the Stage 8c retrieval corpus, its eval set and the measured retrieval numbers
docs/design-memo.md   the Stage 5 output - which design family is credible per outcome, and why
docs/limitations.md   the boundary, written before the findings - what cannot be said, and what would change it
docs/estimates.md     the Stage 6 output - what the data can actually answer, and what it cannot
docs/robustness.md    the Stage 7 output - what survives the choices, and where the sign changes
docs/events.md        the Stage 8b output - comparing tenures on the one monthly outcome, and its limits
docs/rag.md           the Stage 8c output - what the chat layer may quote, and what retrieval cannot yet do
docs/app.md           the Stage 9 output - what the app shows, the rules it is held to, and its limits
app/                  the Stage 9 read-only app: registry_data.py (the loader) and streamlit_app.py
docs/data-dictionary.md  every column of the analytical base, its grain and its imputation rules
tests/                one independent verifier per stage (provenance, DAGs, quality, harmonisation,
                      Stage 5, Stage 6, Stage 7, Stage 8b events, registry, Stage 8c retrieval,
                      Stage 9 app)
```

## Two things worth knowing about the data

**Education cannot be modelled after 2010.** Every World Bank education *outcome* series stops in
2010–2011 — primary completion, enrolment, pupil-teacher ratio, tertiary enrolment. They cannot see the
2015–2023 administration at all. Education is recorded as a **declared gap**, not a null result.

**A covariate the design conditions on is contaminated, and the gate is how we know.** Stage 3's spike
gate flagged Nigerian net ODA rising **+1006% in 2005** — Paris Club debt relief is recorded as
official development assistance. `donor` sits in the adjustment set for designs A and B on every
health and education outcome, so those designs partially condition on a debt restructuring. This is
recorded on the cards and carried to Stage 5 rather than quietly used as a clean control.

**What is still missing is listed, not hidden.** `registry/dags/index.json` carries
`variables_still_missing`: every variable a design needs that has no usable source yet — currently **5,
in two groups** (the per-capita FAAC dose, which is a *decision* rather than a source, and the education
outcomes, which no open series covers past 2010). Three groups have closed, one at a time: the oil price
(2026-10-11), the FAAC fiscal dose (2026-10-16) and the security outcomes (2026-10-17) — the last because
UCDP's bulk archive is keyless even though its API is not. The verifier recomputes that list from the
graphs, so it cannot drift from what it summarises.

**And Stage 5 asked whether any of it is estimable yet — the answer was no, on the record, and re-running
it after each delivery has kept that answer honest.** Every one of the 36 (outcome × design)cards carries a pre-check verdict and **exactly one passes** — `u5mr` under Design C: the state dose is absent on the per-capita axis the estimand is
written on (the nominal dose landed and is gated, and the state-attributed outcome arrived on 2026-10-17),
so the state DiD family stays dropped on its *axis*; the national VECM family runs at **annual** grain
without FAAC and, on its base-spec design, can only detect an effect ~38–99× the residual SD (the
mandated oil×tenure interactions are nearly collinear with the tenure dummies — a property of the
*design*, not the data); and no convex combination of the 13 donors tracks Nigeria's pre-treatment path,
so the synthetic control is reported **infeasible rather than shipped weak**. What Stage 6 then did with
the series that did land is [`docs/estimates.md`](docs/estimates.md): the fiscal transmission channel is
estimated, and the dose-response question is estimated but not identified, with the failing check named.
Stage 7 then asked the same two questions 105 ways: the transmission channel keeps its sign in all 24 of
its specifications (its timing is the weak part, placebo p = 0.0625), and the dose-response estimate's
**sign does not survive at all** — 45 positive against 36 negative, negative in every window once the dose
is lagged a month, which is a sharper statement than "estimated, not identified".
Full per-design reasoning: [`docs/design-memo.md`](docs/design-memo.md) and
[`docs/robustness.md`](docs/robustness.md).

**Raw restricted data is never committed.** ACLED's terms prohibit redistribution and DHS/NDHS microdata
may not be republished, so the repository ships code, derived aggregates and acquisition instructions —
`.gitignore` excludes `data/raw/`. World Bank data is CC-BY and is cited as such.

## Documentation

- [`PHASES.md`](PHASES.md) — the build plan and its stage gates
- [`nigeria-causal-inference-spec.md`](nigeria-causal-inference-spec.md) — design decisions, including
  which original constraints were deliberately overridden
- [`docs/limitations.md`](docs/limitations.md) — the limitations, written before the findings: the
  arithmetic, the coverage gaps, the identification failures and what would change each answer
- [`docs/estimates.md`](docs/estimates.md) — which causal question this data can carry, and why not the one
  the brief asked for
- [`docs/robustness.md`](docs/robustness.md) — what survives the choices the estimates did not pin down
- [`docs/events.md`](docs/events.md) — comparing tenures, part 1: what changed *inside* a tenure, on the only
  monthly outcome
- [`docs/app.md`](docs/app.md) — the app: the ratio it leads with, the rules its verifier enforces, why the
  chat tab waits for a gate that does not pass yet, and what the Streamlit choice costs
- [`docs/decisions.md`](docs/decisions.md) — the decision log, including UI-01…UI-08: the framework, the
  read-only-before-chat rule, the costs accepted and the condition that would reverse them
- [`docs/rag.md`](docs/rag.md) — the retrieval corpus: what the chat layer is allowed to quote, the model
  and budget decisions behind it, and the two refusal gates it does not yet meet
- [`docs/decisions.md`](docs/decisions.md) — the decision log
- [`PROGRESS.md`](PROGRESS.md) — current state, verification evidence, blockers
