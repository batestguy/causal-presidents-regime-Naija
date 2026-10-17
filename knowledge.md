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

**Status: Stage 5 of 8 built (2026-10-11), re-run at vintage 2026-10-16 — designs validated; no estimates yet.** Ingestion
works end to end on four sources and is provenance-verified — including 174 FAAC disbursement documents,
which are the state fiscal dose — 36 causal graphs are generated and verified, 125 series are
quality-gated, `dbt/` builds the analytical base the models and the app will read, and Stage 5 has
attached a **pre-check verdict to every card — 0 of 36 pass** (15 fail, 7 degraded, 14 not attempted;
`docs/design-memo.md`). The verdicts were **re-run at vintage 2026-10-16** once the fiscal dose landed
and was gated: the totals are unchanged, the *reasons* are not — Family A is dropped because the dose's
per-capita axis waits on the population denominator (X-09) and no outcome is state-attributed, not
because there is no dose. Nothing is fitted: no model card carries an estimate until Stages 6–7. Read `PROGRESS.md` for what is verified and what is blocked.

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
| `ingestion/` | Python: source clients, Prefect-style flows, the five Stage 3 gates |
| `analysis/specs/` | Declared inputs: outcomes, DAG designs, quality gates, harmonisation rules |
| `dbt/` | The transformation project (seeds + staging + analytics). Run from the **repo root** |
| `registry/` | Published artifacts the app reads: DAG cards, the quality report, the Stage 5 diagnostics |
| `tests/` | Independent verifiers — one per stage, each recomputing its stage's claims |
| `data/raw/` | Immutable landed payloads. **Gitignored** and never committed |

The repository is a git repo (public, `main`). There is still no `package.json`, `pyproject.toml`,
`requirements.txt`, `renv.lock`, or CI config — Python dependencies are taken from the `ds-general`
conda environment rather than pinned in the repo.

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
  `analysis/R/02_diagnostics.R`). Testing interpolated rows tests the interpolator. **0 of 36 cards pass
  their pre-check at vintage 2026-10-16** — the dose's specified axis is empty (the nominal one is landed
  and gated), the VECM family is annual-grain and has no catalogue entry for FAAC, and the synthetic
  control is infeasible. `docs/design-memo.md` is the source of truth for
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
- **The monthly spine is only 10.1 % observed** (775 of 7,682 rows; 4,389 interpolated, 2,518 empty),
  because every open source here is annual. A monthly model on `cpi_yoy` therefore cannot see the 2023
  subsidy window — that window holds two annual observations (C-30). Check
  `dim_metric.frequency_gap` before proposing any monthly design.
- **Two invariants the base enforces in code, not in prose:** no value outside a metric's observed span
  (no extrapolation), and no interpolation across a gap wider than one step — a 108-month hole stays a
  hole. Mutating either turns a test red; they are break-tested.
- **Every guard is expected to be able to fail.** The repo's convention is to mutate each new check and
  watch it fail before trusting it; `PROGRESS.md` §4 lists those break-tests. Add one with any new guard.
- Chart constraints: single panel, max 5 metrics (trim + warn, never error), index to 100 at
  Jan 2000 (subtitle must say so), tooltips show raw values, Yar'Adua→Jonathan boundary must
  render correctly in both party and president color modes.
- **CPU-only machine (15.9 GB RAM, no GPU)** — heavy training/modeling goes to Google Colab.
- Drive letters were rotated 2026-09-06: **D:** is the data drive (repos live here),
  **E:** is a FAT32 USB stick (no symlinks, `git` needs `safe.directory`). Older docs may be wrong.
- Windows host but the shell is **bash (Git Bash)** — use POSIX syntax (`ls`, `rm`, `mv`,
  `/dev/null`), forward-slash paths.
- `TOOLING.md` references `ENVIRONMENTS.md` as a companion, but that file is not present here.
