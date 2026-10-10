# Causal Presidents

**Regime and national outcomes in Nigeria, 1999–present — an interactive causal-inference explorer.**

Visitors will ask causal questions of a model *and* open the fitted models behind the answers:
coefficient tables, intervals, diagnostics and sensitivity bounds.

> **Presidents are one input, not the cause.** Presidential influence on Nigerian outcomes is heavily
> mediated by oil price cycles, state governments, donor funding and inherited conditions. This project
> is built to show those confounders rather than hide them, and it reports adjusted **associations** —
> never an unconditional causal fact. Where the design cannot identify an effect, it says so.

---

## Status: Stage 1 of 8 — early, and honest about it

| | |
|---|---|
| Specification | ✅ Complete (`nigeria-causal-inference-spec.md`, `PHASES.md`) |
| Ingestion | 🟡 Working for one source, provenance-verified |
| Analysis | ⬜ Not started |
| Dashboard | ⬜ Not started |

**There is no dashboard to look at yet.** One ingestion source works end to end; the econometrics have
not begun. See [`PROGRESS.md`](PROGRESS.md) for what is verified and what is blocked.

## What works today

```bash
# Pull a World Bank vintage (raw payloads + provenance manifest + coverage report)
conda run -p "C:/Users/TOSHIBA/ds-general" python ingestion/flows/pull_worldbank.py

# Prove the stored raw data is byte-identical to what the API returned
conda run -p "C:/Users/TOSHIBA/ds-general" python tests/verify_provenance.py
```

Last run: 15/15 indicators, every payload reproducing its recorded `sha256`, 0 orphaned files.

To use the key-gated sources, copy `.env.example` to `.env` and add free credentials:

| Variable | Source | Register |
|---|---|---|
| `FRED_API_KEY` | Brent crude oil price | https://fred.stlouisfed.org/docs/api/api_key.html |
| `UCDP_ACCESS_TOKEN` | Organised-violence fatalities | https://ucdp.uu.se/ |
| ACLED | Security events (now **OAuth**, not a key) | not yet wired |

## Repository layout

```
docs/decisions.md     decision log — every choice, dated, with its reason
docs/licences.md      per-source redistribution rights and open licensing questions
PHASES.md             the plan: Stages 0–8, data collection through analysis
ingestion/clients/    one client per source, plus shared provenance
ingestion/flows/      stage runners that land a vintage
tests/                provenance verification
```

## Two things worth knowing about the data

**Education cannot be modelled after 2010.** Every World Bank education *outcome* series stops in
2010–2011 — primary completion, enrolment, pupil-teacher ratio, tertiary enrolment. They cannot see the
2015–2023 administration at all. Education is recorded as a **declared gap**, not a null result.

**Raw restricted data is never committed.** ACLED's terms prohibit redistribution and DHS/NDHS microdata
may not be republished, so the repository ships code, derived aggregates and acquisition instructions —
`.gitignore` excludes `data/raw/`. World Bank data is CC-BY and is cited as such.

## Documentation

- [`PHASES.md`](PHASES.md) — the build plan and its stage gates
- [`nigeria-causal-inference-spec.md`](nigeria-causal-inference-spec.md) — design decisions, including
  which original constraints were deliberately overridden
- [`docs/decisions.md`](docs/decisions.md) — the decision log
- [`PROGRESS.md`](PROGRESS.md) — current state, verification evidence, blockers
