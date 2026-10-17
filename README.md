# Causal Presidents

**Regime and national outcomes in Nigeria, 1999–present — an interactive causal-inference explorer.**

Visitors will ask causal questions of a model *and* open the fitted models behind the answers:
coefficient tables, intervals, diagnostics and sensitivity bounds.

> **Presidents are one input, not the cause.** Presidential influence on Nigerian outcomes is heavily
> mediated by oil price cycles, state governments, donor funding and inherited conditions. This project
> is built to show those confounders rather than hide them, and it reports adjusted **associations** —
> never an unconditional causal fact. Where the design cannot identify an effect, it says so.

---

## Status: Stage 5 of 8 — designs validated, no estimates yet

| | |
|---|---|
| Specification | ✅ Complete (`nigeria-causal-inference-spec.md`, `PHASES.md`) |
| Ingestion | ✅ **Four** sources working, provenance-verified: 22 national indicators + a 13-country donor panel + the Brent crude oil series + 174 FAAC disbursement documents (the state fiscal dose) |
| Assumption layer | ✅ **36 causal graphs** — 3 identification designs × 12 outcomes, with the adjustment set computed from each graph |
| Quality gates | ✅ **Stage 3** — 5 gates over 125 series: 60 ok, 65 flagged, 0 silently dropped (37 of them the FAAC dose, gated from its parsed documents) |
| Analytical base | ✅ **Stage 4** — one monthly table, 7,682 rows (23 metrics × 334 months), index-anchored, with the party-by-tenure strata and the Stage 3 quality status on it |
| Pre-analysis diagnostics | ✅ **Stage 5** — every design validated before estimation, **re-run at vintage 2026-10-16** after the dose landed. **0 of 36 cards pass their pre-check** (15 fail, 7 degraded, 14 not attempted): Family A dropped (the dose now exists, but its per-capita axis waits on X-09 and no outcome is state-attributed), B degraded (annual grain, FAAC not in the catalogue, a 38–99 SD detectable effect), C infeasible (donor pool can't track Nigeria) |
| Analysis | ⬜ Not started (Stages 6–8) — no estimate is attached to any model |
| Dashboard | ⬜ Not started |

**There is no dashboard to look at yet.** Ingestion works end to end, the causal-graph assumption layer
is built, the harmonised analytical base the models and the app will read exists, and Stage 5 has
established what the data can support **before** estimating anything — which is to say, very little
without the FAAC fiscal-dose parser. See [`PROGRESS.md`](PROGRESS.md) for what is verified and what is
blocked, [`docs/design-memo.md`](docs/design-memo.md) for the stage's verdict on every design,
[`docs/dags.md`](docs/dags.md) for the graphs, and [`docs/data-dictionary.md`](docs/data-dictionary.md)
for every column of the base.

**And a finding worth stating on the front page**, because it shapes what can be estimated at all: the
monthly spine is only **10.1 % observed**. The open sources here are annual, so a monthly model cannot
see the 2023 fuel-subsidy window — the spine exists, the values in it are mostly interpolation, and the
base says which months those are (`observation_type`) rather than presenting them as data.

## What works today

```bash
PY="conda run -p C:/Users/TOSHIBA/ds-general python"

# Pull a World Bank vintage (raw payloads + provenance manifest + coverage report)
$PY ingestion/flows/pull_worldbank.py

# Pull the synthetic-control donor panel (13 countries x 5 screening predictors)
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
```

Last run: 22/22 national indicators, 5/5 donor-panel predictors and 1/1 oil series — **28 payloads
across 3 sources**, every one reproducing its recorded `sha256`, 0 orphaned files. 36/36 DAGs built,
and every one verified to be acyclic, schema-valid, and to have an adjustment set that provably blocks
every backdoor path in its graph.

The oil series is Brent crude from FRED: 10,275 daily observations spanning 1987→2026, provenance
verified. It refuses to overwrite a landed vintage, because the raw layer is immutable.

The analytical base is 7,682 rows = 23 metrics × 334 months, built by dbt from the raw layer plus the
declared rules in `analysis/specs/harmonisation.yml`: a January-2000 index anchor (with the fallback
recorded per metric), the base-spec §7 administration spine split into term-level party-by-tenure
strata, the 37 × 334 state panel with its dose columns declared empty, and every definition break the
quality gates found. 92 data tests hold it, and `tests/verify_harmonisation.py` recomputes the whole
thing from `data/raw/` without importing a single dbt model.

Key-gated sources read free credentials from a gitignored `.env` — copy `.env.example` to `.env`:

| Variable | Source | Status |
|---|---|---|
| `FRED_API_KEY` | Brent crude oil price ([register](https://fred.stlouisfed.org/docs/api/api_key.html)) | ✅ set, series landed |
| `UCDP_ACCESS_TOKEN` | Organised-violence fatalities ([register](https://ucdp.uu.se/)) | ⬜ still needed |
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
analysis/R/           DAG generator (estimation scripts land here at Stage 6)
dbt/                  the transformation project: seeds (spine, catalogue, shocks, states),
                      models/staging (raw payloads -> typed observations) and models/analytics
                      (dimensions, the spine, the index anchor, the analytical base table)
registry/dags/        the DAG cards, JSON schemas and figures
registry/quality/     the vintage quality report (gate results per series)
registry/diagnostics/ the Stage 5 pre-check result (diagnostics.json + report.md)
docs/design-memo.md   the Stage 5 output - which design family is credible per outcome, and why
docs/data-dictionary.md  every column of the analytical base, its grain and its imputation rules
tests/                one independent verifier per stage (provenance, DAGs, quality, harmonisation, Stage 5)
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
`variables_still_missing`: every variable a design needs that has no usable source yet — currently **7,
in three groups** (the FAAC fiscal dose, and the education and security outcomes). The oil price used
to be the fourth and largest group; it is now acquired, which took **design C down to zero unsourced
nodes**. The verifier recomputes that list from the graphs, so it cannot drift from what it summarises.

**And Stage 5 asked whether any of it is estimable yet — the answer is no, on the record.** Every one
of the 36 (outcome × design) cards carries a pre-check verdict and **none passes**: the state dose has 0
of 12,358 values, so the state DiD family is dropped; the national VECM family runs at **annual** grain
without FAAC and, on its base-spec design, can only detect an effect ~38–99× the residual SD (the
mandated oil×tenure interactions are nearly collinear with the tenure dummies — a property of the
*design*, not the data); and no convex combination of the 13 donors tracks Nigeria's pre-treatment path,
so the synthetic control is reported **infeasible rather than shipped weak**. The one action that revives
the most is an NBS FAAC parser. Full reasoning: [`docs/design-memo.md`](docs/design-memo.md).

**Raw restricted data is never committed.** ACLED's terms prohibit redistribution and DHS/NDHS microdata
may not be republished, so the repository ships code, derived aggregates and acquisition instructions —
`.gitignore` excludes `data/raw/`. World Bank data is CC-BY and is cited as such.

## Documentation

- [`PHASES.md`](PHASES.md) — the build plan and its stage gates
- [`nigeria-causal-inference-spec.md`](nigeria-causal-inference-spec.md) — design decisions, including
  which original constraints were deliberately overridden
- [`docs/decisions.md`](docs/decisions.md) — the decision log
- [`PROGRESS.md`](PROGRESS.md) — current state, verification evidence, blockers
