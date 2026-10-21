#!/usr/bin/env bash
# One command that runs everything this project claims to have verified.
#
# Why this exists: the verifiers were only ever run by hand, and on 2026-10-17 two of them had already
# been failing against the current data without anyone noticing (C-42, C-44). A check nobody runs is a
# claim, not a check. This script is what CI calls and what a human calls, so there is one answer to
# "is it verified?" rather than a convention.
#
# Usage:
#   scripts/verify.sh              # full chain; re-uses the landed raw layer if present
#   PYTHON=... scripts/verify.sh   # pick the interpreter (CI passes the venv's python)
#
# Exit status is the first failing step's — set -e is deliberate: a partial run must not look green.
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"
PYTHON="${PYTHON:-python}"

# dbt is not on PATH on the development machine — it lives in the `ds-general` conda env (I-01), and CI
# installs it from requirements.txt instead. Resolving it here is what lets the "one command" claim be
# true on both: a bare `dbt` is used when it exists, otherwise the env's own entry point.
DBT="${DBT:-}"
if [ -z "$DBT" ]; then
  if command -v dbt >/dev/null 2>&1; then
    DBT="dbt"
  elif [ -x "$HOME/ds-general/Scripts/dbt.exe" ]; then
    DBT="$HOME/ds-general/Scripts/dbt.exe"
  elif [ -x "$HOME/ds-general/bin/dbt" ]; then
    DBT="$HOME/ds-general/bin/dbt"
  else
    printf 'dbt not found: set DBT=/path/to/dbt or install the ds-general env\n' >&2
    exit 1
  fi
fi

step() { printf '\n=== %s\n' "$1"; }

step "static: compile"
$PYTHON -m py_compile ingestion/clients/*.py ingestion/flows/*.py ingestion/parsers/*.py \
  ingestion/quality/*.py tests/*.py scripts/*.py

step "static: artifacts and contracts"
$PYTHON scripts/validate_artifacts.py

# The raw layer is immutable (X-07): a correction creates a new vintage, never an overwrite. So the
# acquisition steps run only when nothing is landed — a fresh clone or a CI runner.
if [ -z "$(ls -A data/raw/worldbank 2>/dev/null || true)" ]; then
  step "acquire: worldbank"
  $PYTHON ingestion/flows/pull_worldbank.py
  step "acquire: worldbank donors"
  $PYTHON ingestion/flows/pull_worldbank_donors.py
  step "acquire: fred"
  $PYTHON ingestion/flows/pull_fred.py
  step "acquire: faac documents"
  $PYTHON ingestion/flows/pull_faac.py
  step "acquire: ucdp security events"
  $PYTHON ingestion/flows/pull_ucdp.py
else
  printf '\n=== acquire: SKIPPED — raw layer already present (immutable, X-07)\n'
fi

if [ ! -f data/staging/faac_state_allocation.csv ]; then
  step "parse: faac documents"
  $PYTHON ingestion/parsers/faac_disbursement.py
else
  printf '\n=== parse: SKIPPED — staging artifact already present\n'
fi

if [ ! -f data/staging/ucdp_state_month.csv ]; then
  step "parse: ucdp security events"
  $PYTHON ingestion/parsers/ucdp_events.py
else
  printf '\n=== parse: SKIPPED — ucdp staging artifact already present\n'
fi

step "stage 3: quality gates"
$PYTHON ingestion/flows/check_quality.py

step "stage 4: build the analytical base"
$DBT build --project-dir dbt --profiles-dir dbt

# Stage 6 needs R (fixest, sandwich, duckdb) as well as the base. The Python CI image does not carry it,
# so the engine is skipped there and `tests/verify_stage6.py` then verifies the *committed* estimates
# against the CI-android base — weaker than a re-estimate, and labelled as such rather than passed off.
# A design whose recomputed coefficient disagrees with the committed artifact still fails the step.
if command -v Rscript >/dev/null 2>&1; then
  step "stage 6: estimates"
  Rscript analysis/R/03_estimate.R
  # Stage 7 refits the whole declared grid, so it is the slower half of the R work and it is skipped on
  # the Python-only runner for the same reason: tests/verify_stage7.py then verifies the committed grid
  # against the freshly built base, which catches a base that moved even when the engine did not run.
  step "stage 7: robustness grid and specification curve"
  Rscript analysis/R/04_robustness.R
  # Stage 8 assembles those two stages onto the 36 cards and the index, which is what the app reads. It
  # runs last on purpose: analysis/R/01_build_dags.R writes the cards wholesale and resets the estimate
  # block, so the registry must be assembled after it, and tests/verify_registry.py fails when a card that
  # should carry a number does not — which is what a reset looks like from the outside.
  step "stage 8: registry assembly"
  Rscript analysis/R/05_registry.R
  # Stage 8b is the transition event study — the within-tenure timing half of "compare the tenures". It is
  # independent of the card registry (it writes its own artifact under registry/events/), so it can run
  # after it without ordering risk, and it needs no source that Stage 6 did not already need.
  step "stage 8b: transition event study"
  Rscript analysis/R/06_events.R
else
  printf '\n=== stage 6: SKIPPED — no Rscript on PATH; verify_stage6.py will check the committed estimates\n'
  printf '\n=== stage 7: SKIPPED — no Rscript on PATH; verify_stage7.py will check the committed grid\n'
  printf '\n=== stage 8: SKIPPED — no Rscript on PATH; verify_registry.py will check the committed registry\n'
  printf '\n=== stage 8b: SKIPPED — no Rscript on PATH; verify_events.py will check the committed artifact\n'
fi

# Stage 8c — the retrieval corpus. The text half needs only Python and PyYAML; the vectors need
# sentence-transformers, which lives in its own CPU conda env on this machine (docs/rag.md §5). A rebuild in
# an interpreter without it is *refused* by the builder rather than silently dropping the published vectors,
# so this step runs only when an embedding interpreter is available — and `tests/verify_rag.py` checks the
# committed corpus and vectors in every case.
RAG_PYTHON="${RAG_PYTHON:-}"
if [ -z "$RAG_PYTHON" ] && [ -x "/c/conda-envs/drlca-rag/python.exe" ]; then
  RAG_PYTHON="/c/conda-envs/drlca-rag/python.exe"
fi
if [ -n "$RAG_PYTHON" ]; then
  step "stage 8c: RAG corpus"
  "$RAG_PYTHON" scripts/build_rag_corpus.py --embed
  step "stage 8c: retrieval evaluation"
  $PYTHON scripts/eval_rag.py
else
  printf '\n=== stage 8c: SKIPPED — no RAG_PYTHON with sentence-transformers; verify_rag.py will check the committed corpus and vectors\n'
fi

step "verifiers (each re-derives its numbers independently)"
$PYTHON tests/verify_quality.py
$PYTHON tests/verify_stage6.py
$PYTHON tests/verify_stage7.py
$PYTHON tests/verify_registry.py
$PYTHON tests/verify_harmonisation.py
$PYTHON tests/verify_faac.py
$PYTHON tests/verify_dags.py
$PYTHON tests/verify_stage5.py
$PYTHON tests/verify_events.py
$PYTHON tests/verify_provenance.py
$PYTHON tests/verify_rag.py

printf '\nall checks passed\n'
