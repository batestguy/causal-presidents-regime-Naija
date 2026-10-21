# Project knowledge

Freebuff context for this repo: what runs, where things live, and the rules a change must not break.

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
Rscript analysis/R/04_robustness.R      # Stage 7 grid
Rscript analysis/R/05_registry.R        # Stage 8 registry — must run after 01_build_dags.R
```

`scripts/verify.sh` skips acquisition when `data/raw/` is landed (the raw layer is immutable), and skips the
R stages when `Rscript` is absent — it says so in the log rather than passing quietly.

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
