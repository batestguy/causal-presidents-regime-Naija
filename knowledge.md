# Project knowledge

**GitHub repo: `causal-presidents-regime-Naija`** (renamed 2026-10-10; supersedes the earlier `causal-presidents` slug). README H1: *Causal Presidents —
Presidential Transitions and National Outcomes in Nigeria, 1999–present*. Never use
*performance*, *scorecard*, *accountability* or *ranking* in a title or subtitle — they
presuppose a verdict the analysis cannot support.

High-signal context for agents working in this repo. See `TOOLING.md` for the full
machine inventory and `AGENTS.md` for the terse project-knowledge template.

## What this project is

An interactive, monthly-refreshed causal-inference explorer for national outcomes across
Nigerian presidential administrations (1999–present) on health, education, security and
economic metrics. Visitors ask causal questions of a model and inspect the fitted models
behind the answers. (Base spec title: "Nigeria Presidential Performance Dashboard" — the
word *performance* is retired from all user-facing naming; see the title note above.)

**Status: Stage 8 of 8 begun (2026-10-18) — the registry the app reads exists.** Ingestion
works end to end on **five** sources and is provenance-verified — including 174 FAAC disbursement
documents, which are the state fiscal dose, and the UCDP GED security events, which are the
state-attributed outcome (keyless: its bulk archive needs no token, C-45) — 36 causal graphs are generated
and verified, 672 series are quality-gated, `dbt/` builds the analytical base the models and the app read,
and Stage 5 has attached a **pre-check verdict to every card — 1 of 36 passes** (14 fail, 9 degraded, 12 not
attempted; `docs/design-memo.md`; re-run at vintage 2026-10-18 over the widened donor pool). The one pass is
`u5mr` under Design C. The verdicts have been re-run three times, once per data delivery (the artifact on
disk is `registry/diagnostics/2026-10-18/`), and the totals **did** move while the reasons moved too:
Family A is dropped because the dose's per-capita axis waits on the population denominator (X-09), not for
want of a dose or an outcome.

**Stage 6 has since published the first estimates, and the finding is a split verdict**
(`docs/estimates.md`): the fiscal transmission channel is **estimated** — a 10 % Brent move reaches the
states as roughly 5 % more money two to three months later (C-48) — while the state dose-response question
is **estimated but not identified**, because the dose's post-fixed-effect variation is the 13 % derivation
share moving with the oil price and a mis-timed dose fits just as well (C-47). The presidential-tenure
question is not answerable at all: 4–5 administrations against 27 annual observations put the minimum
detectable effect at 35–80 residual standard deviations.

**Stage 7 has since asked whether either answer survives the choices it did not pin down**
(`docs/robustness.md`, `registry/robustness/2026-10-17/`): **105 specifications** declared before fitting
and all published. Design B holds its sign in 24 of 24 (its *timing* is the weak part — in-time placebo
p = 0.0625), and Design A's sign **does not survive at all**: 45 positive against 36 negative, negative in
every window once the dose is lagged a month, so Stage 6's `estimated_not_identified` was the milder of the
two true statements.

**Stage 8 has since assembled the registry the app reads** (`docs/registry.md`, `analysis/specs/registry.yml`,
`analysis/R/05_registry.R`): **2 of the 36 cards carry a published number, 34 carry a reason**, because
Stage 6's twelve specifications do not line up with 36 cards — three Design A specifications are about
catalogue outcomes (two of which have cards), nine Design B specifications are about the **national FAAC
channel**, which is a *mediator* node on every B card, and Design C was not run. The two B/C results sit on
`registry/dags/index.json → published_results` with `result_is_card_level: false` where the app can show them
once instead of implying them nine times, every `not_estimated` card names a reason from a closed set, and
`tests/verify_registry.py` re-derives the mapping and checks each number against the artifact it names. Read
`PROGRESS.md` for what is verified and what is blocked.

**Stage 5 has since been re-run against a widened Design C donor pool (vintage 2026-10-18).** The candidate
set went from 13 GDP-selected countries to **99 candidates screened on oil dependence, region/income band
and coverage**, and the pre-fit gate moved from `infeasible` on everything to **`pass` on `u5mr` (3 of its
4 runnable windows)** with `gdp_growth` (1 of 4) and `cpi_yoy` (0 of 4) still failing — under a rollup rule
that is now **declared** (strict majority of runnable windows). Two cautions travel with it and are on the
artifact: a 99-donor simplex can fit almost any pre-period, so the gate is weaker evidence than it was at
13 donors; and Design C is still **not estimated** — the estimator and its placebos are the next build. The
quality gate now covers **672 series** (was 242) and the donor panel is 27,352 rows.

**Stage 8b has since answered the one tenure-shaped question the data can carry** (`docs/events.md`,
`registry/events/2026-10-17/`): monthly conflict around the four in-window transitions, 32 specifications,
inference by exhaustive placebo assignment over 58 eligible months. **2 of 8 event-outcome cells survive both
the placebo and the pre-trend check** (2010 incidents +391 %, 2023 fatalities +77 %, each p = 0.017), four
fail the pre-trend, one transition cannot be checked at all (Yar'Adua 2007 — 100 months of history against a
120-month requirement, reported as `check_not_available`, never as a null). The party split is published as
description with `no_test_computed: true`. If someone asks to *compare the tenures*, start here and say what
the four events can and cannot carry; do not produce a party effect.

**Scope upgrade (2026-10-10):** it is no longer a comparison dashboard. It is an
interactive causal-inference explorer — visitors ask causal questions of a model *and*
inspect the fitted models behind the answers (model cards, coefficient tables, diagnostics).
See `nigeria-causal-inference-spec.md` for every design decision and which base-spec
`[LOCKED]` items it overrides, and `PHASES.md` for the build order.

## Where things live

| Path | What it is |
|---|---|
| `#CausalPresidents.txt` | **The complete specification (README v1.0, 525 lines). Authoritative.** |
| `TOOLING.md` | Machine inventory: languages, 10 Python envs, conda envs, R packages, CLI tools |
| `AGENTS.md` | Project-knowledge template (quickstart/architecture/conventions stubs) |
| `nigeria-causal-inference-spec.md` | Design spec — turns the dashboard into an interactive causal-inference explorer |
| `PHASES.md` | **Phase plan: Stages 0–8 from data collection to analysis (start here when building)** |
| `PROGRESS.md` | **Live state: what is built, verified, blocked and next — read this second** |
| `docs/decisions.md` | Decision log, dated, with the reason for each choice |
| `docs/data-dictionary.md` | Every column of the analytical base, its grain and its imputation rules |
| `docs/dags.md` | The causal-graph layer: designs, assumptions, variable sources, and each card's pre-check |
| `docs/design-memo.md` | Stage 5 output: which design family is credible per outcome, and the diagnostic that decides it |
| `docs/estimates.md` · `docs/robustness.md` | Stage 6 output (what the data can answer) and Stage 7 output (what survives the choices) |
| `ingestion/` | Python: source clients, Prefect-style flows, the five Stage 3 gates |
| `analysis/specs/` | Declared inputs: outcomes, DAG designs, quality gates, harmonisation rules, estimation, the Stage 7 robustness grid |
| `dbt/` | The transformation project (seeds + staging + analytics). Run from the **repo root** |
| `registry/` | Published artifacts the app reads: DAG cards, the quality report, the Stage 5 diagnostics |
| `tests/` | Independent verifiers — one per stage, each recomputing its stage's claims |
| `data/raw/` | Immutable landed payloads. **Gitignored** and never committed |

The repository is a git repo (public, `main`). Python dependencies are pinned in `requirements.txt` and
`requirements-dev.txt` *and* taken from the `ds-general` conda environment; CI is
`.github/workflows/verify.yml`, which runs `scripts/verify.sh` — the one command that runs the whole
chain (compile, artifact contracts, acquisition if nothing is landed, Stage 3, dbt, Stages 6 and 7, every
verifier) and whose exit status is the answer to "is it verified?". There is still no `package.json`,
`pyproject.toml` or `renv.lock`.

## Reading the spec

`#CausalPresidents.txt` uses decision markers — respect them:

- **[LOCKED]** — do not change. Covers the language split (§3), administration dimension
  (§7), chart spec (§8), adjustment tiers (§9), NLP/RAG approach (§11), methodology page
  (§15), honesty layer (§16), reproducibility rules (§18).
- **[OPEN]** — confirm with the user before proceeding. §20 lists the open questions that
  **must be resolved before construction begins** (metric catalog completeness, shock list,
  portrait licensing, default adjustment tier, tenure stratification, hosting, RAG framework,
  blog platform).

## Planned stack (all free-tier — no paid service at any layer)

- **Warehouse (built): a local DuckDB file** at `data/analytics.duckdb`, gitignored and reproducible from
  `data/raw/` plus `analysis/specs/` — a deliberate departure from the base spec's Neon Postgres (S4-01):
  free-tier only, ~20k rows, and no account needed to reproduce it. Postgres + pgvector returns only if
  the RAG layer needs it (Stage 8). **Storage:** Cloudflare R2 (unused so far)
- **Orchestration:** Prefect Cloud Hobby (monthly flows, §13) · **Transform:** dbt Core + `dbt-duckdb` 1.12,
  installed in the `ds-general` env (which pulled protobuf 6.x and opentelemetry-api 1.45 into it and broke
  two unrelated pins — see decision I-14 before adding anything else to that env)
- **Dashboard:** Streamlit Community Cloud + Plotly · **Portraits:** Pillow
- **Adjustment (R):** `vars` (VECM/Johansen), `urca`, `dynlm` (ARDL), `fixest`, `did`, `sandwich`;
  pinned via `renv.lock`. Python fallback: `statsmodels`, `pyfixest`/`linearmodels`.
- **RAG:** sentence-transformers (`all-MiniLM-L6-v2`, local) → pgvector → Groq (Llama 3.3 70B,
  OpenAI-compatible client); LlamaIndex; RAGAS in CI.
- Language split is [LOCKED]: ingestion/dashboard Python, transformation SQL (dbt), adjustment R.

## Commands

```bash
PY="conda run -p C:/Users/TOSHIBA/ds-general python"   # NOT -n: ds-general is a prefix env

$PY ingestion/flows/pull_worldbank.py            # land a vintage (needs the key for FRED only)
$PY tests/verify_provenance.py                   # every sha256, every source
$PY ingestion/flows/check_quality.py && $PY tests/verify_quality.py    # Stage 3 gates + verifier
Rscript analysis/R/01_build_dags.R && $PY tests/verify_dags.py          # DAG cards + verifier
conda run -p C:/Users/TOSHIBA/ds-general dbt build --project-dir dbt --profiles-dir dbt
$PY tests/verify_harmonisation.py                # recompute the base from raw, independently
Rscript analysis/R/02_diagnostics.R              # Stage 5 engine -> registry/diagnostics/<vintage>/
Rscript analysis/R/01_build_dags.R               # re-attach the pre-checks to the 36 cards
$PY tests/verify_stage5.py                       # recompute every Stage 5 number independently
$PY ingestion/flows/pull_ucdp.py && $PY ingestion/parsers/ucdp_events.py   # security outcome
Rscript analysis/R/03_estimate.R                 # Stage 6 engine -> registry/estimates/<vintage>/
$PY tests/verify_stage6.py                       # recompute every estimate independently
Rscript analysis/R/04_robustness.R               # Stage 7 grid + curve -> registry/robustness/<vintage>/
$PY tests/verify_stage7.py                       # re-fit all 105 specifications independently (~3 min)
Rscript analysis/R/05_registry.R                 # Stage 8: assemble estimates + robustness onto the cards
$PY tests/verify_registry.py                     # re-derive which card carries which number

scripts/verify.sh                                # all of the above, one exit status
```

- **Everything runs from the repository root.** Both dbt paths (`profiles.yml`'s DuckDB file and the
  `raw_root` var) are relative to the **invocation** directory, not the project directory.
- **`conda run -p` takes a prefix path.** `conda run -n ds-general` does not work — `ds-general` is a
  prefix environment at `~/ds-general`, not a named one under `miniconda3/envs` (decision I-01).
- **Do not pass multi-line scripts to `conda run ... python -c`** — it fails with a `NotImplementedError`
  about newlines. Write a file and run that.
- **R work:** R 4.5.2 on PATH; `Rscript analysis/R/01_build_dags.R`.
- **Lint:** `ruff` is at `~/.local/bin/ruff`, **not** in the `ds-general` env.
- **Docs/PDF:** Quarto 1.9.38, Pandoc 3.8, TinyTeX.

## Conventions & gotchas

- **Stage 5 runs every test on the native observation, never the monthly spine** (`analysis/specs/diagnostics.yml`,
  `analysis/R/02_diagnostics.R`). Testing interpolated rows tests the interpolator. **1 of 36 cards passes
  its pre-check at vintage 2026-10-18** (`u5mr` under Design C; 14 fail, 9 degraded, 12 not attempted) —
  the dose's specified axis is empty (the nominal one is landed and gated), the VECM family is
  annual-grain and has no catalogue entry for FAAC, and the synthetic control is a `candidate` rather
  than infeasible. `docs/design-memo.md` is the source of truth for
  which design is credible per outcome; the summary is computed from the cards, never asserted.
- **The `mmr` Johansen rank is marginal** (the deciding statistic sits ~9% over its critical value) and
  an independent implementation reaches a different rank under a different deterministic-term convention.
  `urca::ca.jo` returns its statistics ordered r = K-1 … 0; the engine reorders them to r = 0 … K-1.
  Do not treat `mmr`'s rank as settled. `verify_stage5.py` **warns** on a marginal rank disagreement and
  **fails** on any non-marginal one.
- **Free tier is a hard constraint.** Rejections are recorded in §4 (Railway, Fly.io, Supabase,
  Pinecone/Qdrant). Migration escape hatch: Oracle Cloud Always Free.
- **Honesty layer is non-negotiable** (§16): every chart labeled "colors indicate office, not
  causation", direction labels (↑/↓ better), vintage timestamp, imputation flags, CIs on all
  adjusted estimates, methodology page linked everywhere, RAG refuses out-of-scope questions.
- **Never present a point estimate without its confidence interval**; adjusted estimates are
  *associations, not causal effects*, and are stored as tables, never computed at render time.
- **Sample size is tiny** (5 administrations, ~26 annual observations) — expect wide CIs.
- **The monthly spine is only 16.2 % observed** (1,349 of 8,350 rows; 4,389 interpolated, 2,612 empty) —
  it was 10.1 % until the monthly landings (Brent, the FAAC dose, UCDP). A monthly model on `cpi_yoy`
  still cannot see the 2023 subsidy window, because that window holds two *annual* observations (C-30).
  Check `dim_metric.frequency_gap` before proposing any monthly design.
- **Two invariants the base enforces in code, not in prose:** no value outside a metric's observed span
  (no extrapolation), and no interpolation across a gap wider than one step — a 108-month hole stays a
  hole. Mutating either turns a test red; they are break-tested.
- **Every guard is expected to be able to fail.** The repo's convention is to mutate each new check and
  watch it fail before trusting it; `PROGRESS.md` §4 lists those break-tests. Add one with any new guard.
- **A number that appears in prose belongs in the artifact, computed.** Three defects now share one cause
  (C-42, C-44, C-49): a literal or a glob that was true when written and silently false later. The Stage 5
  report asserted "10.1 %" and "dose status on every row: `declared_gap`" for a base at 16.2 % with 4,104
  observed rows, and the verifier could not catch it because it recomputes from the *base*, not the page.
- Chart constraints: single panel, max 5 metrics (trim + warn, never error), index to 100 at
  Jan 2000 (subtitle must say so), tooltips show raw values, Yar'Adua→Jonathan boundary must
  render correctly in both party and president color modes.
- **CPU-only machine (15.9 GB RAM, no GPU)** — heavy training/modeling goes to Google Colab.
- Drive letters were rotated 2026-09-06: **D:** is the data drive (repos live here),
  **E:** is a FAT32 USB stick (no symlinks, `git` needs `safe.directory`). Older docs may be wrong.
- Windows host but the shell is **bash (Git Bash)** — use POSIX syntax (`ls`, `rm`, `mv`,
  `/dev/null`), forward-slash paths.
- `TOOLING.md` references `ENVIRONMENTS.md` as a companion, but that file is not present here.
