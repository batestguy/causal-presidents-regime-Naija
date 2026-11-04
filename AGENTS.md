# Project knowledge

Freebuff context for this repo: what runs, where things live, and the rules a change must not break.

**Status: the registry is frozen at vintage 2026-11-01.** Every phase of `presidents-completion-plan.md` is
closed with its exit criteria measured green (`presidents-completion-state.yml` carries the evidence), and
the completion statement in `PROGRESS.md` — followed by the 2026-11-02 post-freeze presentation record and
the 2026-11-03/04 site pass — says what the system claims, what it refuses to claim, and the limitations it
leaves open. The registry was not edited after the freeze; the static site's presentation was revised, and
the causal-ML first pass has since run outside the registry and stopped at its own gate.

## Causal ML and discovery (post-freeze, no registry change yet)

Two tracks are documented and waiting, both read via `PROGRESS.md`'s 2026-11-04 entries:

- **Discovery** — `docs/causal-discovery.md`. Only `fatalities` and `incidents` have native monthly outcome
  series; the annual ten are below any discovery floor and their monthly values are interpolations. A
  PCMCI smoke run exists in `.inspect/discovery_smoke.py`; nothing is published.
- **What-if counterfactuals** — `docs/counterfactual-recommendation.md` (full recommendation, presentation
  contract, artifact contract, five open decisions), with the method menu in `docs/causal-ml-options.md`
  and the execution plan in `docs/causal-ml-plan.md`. **The first pass has now run and stopped at its own
  gate** (2026-11-04): matrix completion on `u5mr` gives gaps of -4.4, -2.2, +4.0 and +6.6 per 1,000, every
  one sits inside its 99-placebo distribution (rank p 0.38 to 0.78 against a 0.05 gate), and the gap moves by
  4 to 8 per 1,000 across the declared penalty path with Buhari's sign changing inside it. The solver
  dependence is gone (cross-check spread 2.6e-4 or smaller), the placebo null is not an outlier artefact,
  and the stop rule fired: `mmr` and `unemp` are not fitted and no what-if number is published. The phase
  workflow, its gates and its live status board are `docs/causal-phases.md`; the numbers are in
  `PROGRESS.md`, 2026-11-04. The frozen registry is still untouched.

The causal work runs in the conda env **`causality-handbook`** (Python 3.11), not `ds-general`:
`C:\Users\TOSHIBA\miniconda3\envs\causality-handbook\python.exe` carries `duckdb`, `doubleml`,
`tigramite`, `causallearn`, `econml`, `dowhy`, `causalml`, `linearmodels`, `cvxpy`. R 4.5.2 carries
`synthdid`, `gsynth`, `did`, `dagitty`. The accidental `causal-learn`/`tigramite` installs were removed from
`ds-general`, which remains the verified build environment.

Site behaviour worth knowing before touching presentation: page asset URLs carry a build stamp
(`?v=<vintage>.<timestamp>`) so rebuilds are not served stale; the study screen restores selections from
`?outcomes=` and every Back link carries it; cards are shaped by kind (number, described, channel, gap);
the trend table reports president-vs-president contrasts from the published artifact; the Ask screen renders
the plain answer first with one collapsed Technical section. Verifiers: `tests/verify_site.py`,
`tests/verify_answer_js.py` (which also guards the datalist bug), the usual `scripts/verify.sh` chain.

**The estimate screen is two lines a card** (2026-11-04). A card with a number shows the figure and its
interval, one sentence saying what is associated with what (built from the artifact's formula, never typed),
and whether the interval includes zero. A card without one shows its refusal sentence plus a single
descriptive line: the widest gap from the tenure trend in years, or the observed-year count where the series
is too sparse. The p-value, the sample, the verdict word and the check that decided it live in the technical
expander. The design-level results link is a pill in the page footer, centred between Back and Next, not a
pointer under each card. Visible words across twelve cards: 513.

**The causal refusal is stated on three screens, number-free:** a bullet in Methodology section 4, a
paragraph under the synthetic-counterfactual intro on the designs page, and a clause in the chart header.
All three name under-5 mortality, so none can be read as covering an outcome that was never re-fitted.

## Agent workflow

The process — classify, plan, fan out for independent reads, verify with a different family, escalate the
model rather than the agent count — is global: `~/.config/opencode/AGENTS.md` is loaded into every session, in
every project. `docs/agentic-workflow.md` carries the routing and the allowance arithmetic. What this repo
adds:

- **Only `ml-builder`, `causal-analyst` and `writer` may write.** Recon, planning and review are edit-denied
  by permission, not by good intentions.
- **R stages and `dbt build` run alone.** `03_estimate.R`, `04_robustness.R` and `05_registry.R` write shared
  state; two of them in one fan-out is a corrupted run, not a speed-up.
- **The registry is frozen for agents too.** A correction is a new vintage produced by the engine — never a
  hand-edit, even when the number improves.
- **`scripts/verify.sh` is the acceptance command.** A reviewer may run `pytest`, `ruff`, `python` and
  read-only `git`; `Rscript` is denied there, because `05_registry.R` writes the artifact it would audit.

## Quickstart

The verified interpreter on this machine is the `ds-general` conda env (3.12); the default `python` on PATH
has no `duckdb`. R (4.5.2) is needed only for `analysis/R/`.

```bash
PY=/c/Users/TOSHIBA/ds-general/python.exe

# Everything, in order, one exit status: acquire -> parse -> gates -> dbt -> R stages 5-8b -> RAG -> verifiers
PYTHON=$PY scripts/verify.sh            # add RAG_PYTHON=/c/conda-envs/drlca-rag/python.exe to rebuild vectors

# The app (read-only, reads registry/dags/ only)
$PY -m streamlit run app/streamlit_app.py

# One stage at a time
$PY tests/verify_app.py                 # renders all 36 cards and compares the page with the cards
$PY scripts/validate_artifacts.py       # schema + cross-artifact contracts
Rscript analysis/R/03_estimate.R        # Stage 6 estimates
Rscript analysis/R/11_design_c.R        # Stage 8h synthetic control (run before 03: 03 carries its status)
Rscript analysis/R/04_robustness.R      # Stage 7 grid
Rscript analysis/R/05_registry.R        # Stage 8 registry — must run after 01_build_dags.R
```

`scripts/verify.sh` skips acquisition when `data/raw/` is landed (the raw layer is immutable), and skips the
R stages when `Rscript` is absent — it says so in the log rather than passing quietly.

**Run it with Git Bash, not the WSL `bash`.** On this machine plain `bash` resolves to WSL, which
cannot pass `/mnt/d/...` paths to the Windows Python and R interpreters; the script fails at the first
globbed `py_compile`. From PowerShell:

```powershell
& "C:\Program Files\Git\bin\bash.exe" -c "PYTHON=/c/Users/TOSHIBA/ds-general/python.exe `
RAG_PYTHON=/c/conda-envs/drlca-rag/python.exe HF_HUB_OFFLINE=1 bash scripts/verify.sh"
```

It ends in `all checks passed`. A *fresh* clone is the one thing it cannot do: the NBS elibrary index
returns 500, so the FAAC panel and the NBS CPI workbook cannot be re-acquired whole — `docs/limitations.md`
§11, and the raw layer is the record.

## Architecture

- `ingestion/` — one client per source (`clients/`), stage runners (`flows/`), parsers, and the Stage 3 gates
  (`quality/`). Every payload records its provenance manifest.
- `dbt/` — seeds (the spine, catalogue, states, shocks) and the analytical base: one monthly table plus the
  37-unit state panel in `data/analytics.duckdb` (gitignored, built by `dbt build`).
- `analysis/` — `specs/` (declared before fitting: outcomes, designs, grid, rag) and `R/` (one script per
  stage). R writes JSON/SVG artifacts; it never renders.
- `registry/` — the published artifacts the app reads: `dags/` (36 cards + index + SVGs), `estimates/`,
  `robustness/`, `events/`, `quality/`, `rag/`, and `schema/`. Each vintage is a directory.
- `app/` — `registry_data.py` (framework-free loader, enforces the vintage contract) and
  `streamlit_app.py` (view only).
- `tests/` — one independent verifier per stage. They re-derive numbers from artifacts and raw payloads
  rather than importing the code under test.
- `docs/` — the narratives (`decisions.md`, `limitations.md`, `app.md`, `rag.md`, …). `PROGRESS.md` is the
  handoff log; `PHASES.md` is the plan.

Data flow: raw payloads → staging → dbt base → R stages → registry artifacts → app. Nothing flows back.

## Conventions

- **The card wins.** Every displayed number is a field of a registry artifact. A literal coefficient in the
  UI is a defect (`tests/verify_app.py` greps for it).
- **No model at render time.** The app opens no database, makes no network call and imports no fitting
  library; the verifier scans for those imports.
- **Prose numbers are derived.** Narrative claims are required by verifiers from the artifact they describe
  (`docs/app.md`, `docs/rag.md`, `docs/registry.md`), because unchecked prose drifts.
- **Vintage discipline.** Corrections create a new vintage directory, never an edit. A card whose vintage is
  not the index's is a loader error, not a warning.
- **Counts are published, not implied.** 2 of 36 cards carry a number; the other 34 name a reason from a
  closed set. A missing estimate is never silent.
- **A check that fails is published.** Two retrieval gates measure 0.5 and 0.25 against declared targets and
  stay in the artifact. Do not widen a target after measuring.
- **Formatting:** `ruff check .` is recorded, not gating (the repo carries pre-existing conventions);
  `python -m py_compile` is gating. Write files as UTF-8; the index stores LF, so hash contracts normalise
  CRLF (see `tests/verify_rag.py::sha256_text`).
- **Avoid:** re-fitting inside a verifier, importing the module under test into its verifier, hand-listing an
  adjustment set, and editing `registry/` artifacts by hand — regenerate them from the engine.
