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

**Status: spec stage — no code exists yet.** The repo is one authoritative document plus
machine notes. Do not assume a build, package manager, or test runner exists.

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
| `.agents/types/` | Codebuff agent TypeScript type definitions (boilerplate — not app code) |

Not a git repository yet (`git status` fails). No `package.json`, `pyproject.toml`,
`requirements.txt`, `renv.lock`, or CI config is present.

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

- **Warehouse:** Neon Postgres (+ pgvector) · **Storage:** Cloudflare R2
- **Orchestration:** Prefect Cloud Hobby (monthly flows, §13) · **Transform:** dbt Core → GitHub Actions
- **Dashboard:** Streamlit Community Cloud + Plotly · **Portraits:** Pillow
- **Adjustment (R):** `vars` (VECM/Johansen), `urca`, `dynlm` (ARDL), `fixest`, `did`, `sandwich`;
  pinned via `renv.lock`. Python fallback: `statsmodels`, `pyfixest`/`linearmodels`.
- **RAG:** sentence-transformers (`all-MiniLM-L6-v2`, local) → pgvector → Groq (Llama 3.3 70B,
  OpenAI-compatible client); LlamaIndex; RAGAS in CI.
- Language split is [LOCKED]: ingestion/dashboard Python, transformation SQL (dbt), adjustment R.

## Commands

None yet — the repo has no build tooling. When the build starts, use the toolchain listed
in `TOOLING.md`:

- **Python work:** `ds-general` conda env (Python 3.12) is the workhorse; `C:\Python314` for
  quick scripts. Run env commands by explicit path, e.g.
  `conda run -n ds-general python -c "import pandas, sklearn; print(pandas.__version__)"`.
- **R work:** R 4.5.2 on PATH; `Rscript -e "..."`.
- **Docs/PDF:** Quarto 1.9.38, Pandoc 3.8, TinyTeX.

## Conventions & gotchas

- **Free tier is a hard constraint.** Rejections are recorded in §4 (Railway, Fly.io, Supabase,
  Pinecone/Qdrant). Migration escape hatch: Oracle Cloud Always Free.
- **Honesty layer is non-negotiable** (§16): every chart labeled "colors indicate office, not
  causation", direction labels (↑/↓ better), vintage timestamp, imputation flags, CIs on all
  adjusted estimates, methodology page linked everywhere, RAG refuses out-of-scope questions.
- **Never present a point estimate without its confidence interval**; adjusted estimates are
  *associations, not causal effects*, and are stored as tables, never computed at render time.
- **Sample size is tiny** (5 administrations, ~26 annual observations) — expect wide CIs.
- Chart constraints: single panel, max 5 metrics (trim + warn, never error), index to 100 at
  Jan 2000 (subtitle must say so), tooltips show raw values, Yar'Adua→Jonathan boundary must
  render correctly in both party and president color modes.
- **CPU-only machine (15.9 GB RAM, no GPU)** — heavy training/modeling goes to Google Colab.
- Drive letters were rotated 2026-09-06: **D:** is the data drive (repos live here),
  **E:** is a FAT32 USB stick (no symlinks, `git` needs `safe.directory`). Older docs may be wrong.
- Windows host but the shell is **bash (Git Bash)** — use POSIX syntax (`ls`, `rm`, `mv`,
  `/dev/null`), forward-slash paths.
- `TOOLING.md` references `ENVIRONMENTS.md` as a companion, but that file is not present here.
