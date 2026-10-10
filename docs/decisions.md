# Decision log — causal-presidents

Every decision that shapes the analysis, with its status. Written so that a reader can tell
*why* each choice was made, and so that a later reversal is visible rather than silent.

Status values: **LOCKED** (base spec, not to be changed) · **DECIDED** (this project) ·
**VERIFIED** (empirically confirmed) · **OPEN** (unresolved) · **SUPERSEDED**.

## Project framing

| # | Decision | Status | Date | Reason |
|---|---|---|---|---|
| D-01 | Repo title `causal-presidents`; display "Causal Presidents" | SUPERSEDED | 2026-10-10 | Matches the existing spec filename; short and memorable |
| D-01a | **GitHub repo: `causal-presidents-regime-Naija`** (user-specified), display title stays "Causal Presidents" | DECIDED | 2026-10-10 | Supersedes D-01. The slug carries mixed case, which is unconventional for GitHub but preserved as specified |
| D-01b | The repository is **public** | DECIDED | 2026-10-10 | Portfolio intent per base spec §19; contents verified free of secrets and restricted raw data |
| D-01c | `.agents/` and `TOOLING.md` are **excluded** from the published repo | DECIDED | 2026-10-10 | `TOOLING.md` is a machine inventory (host, user, drives, local env paths) carrying security notes about previously exposed credentials; `.agents/` is harness boilerplate, not project code. Reversible by removing two lines from `.gitignore` |
| D-02 | *performance / scorecard / accountability / ranking* excluded from all user-facing naming | DECIDED | 2026-10-10 | Those words presuppose a verdict the analysis cannot support; the title is part of the honesty layer |
| D-03 | The artifact is an interactive causal-inference explorer, not a comparison dashboard | DECIDED | 2026-10-10 | Users ask causal questions of a model **and** inspect the fitted models |
| D-04 | Analysis "rigorous enough" rather than journal-grade; interactive layer is the deliverable | DECIDED | 2026-10-10 | User's stated priority |
| D-05 | Language split: ingestion/dashboard Python, transformation SQL (dbt), adjustment **R** | LOCKED | base spec §3 | R for all estimation, results exported as tables the app reads |

## Method

| # | Decision | Status | Date | Reason |
|---|---|---|---|---|
| M-01 | All four design families in v1: state dose-response DiD, VECM/ARDL, synthetic control, specification curve | DECIDED | 2026-10-10 | Base spec §9 deferred DiD and synthetic control to v2; without them the app asserts more than it shows |
| M-02 | Six-item rigor floor is a shipping gate: intervals, placebo/pre-trend/permutation, confounding sensitivity, DoF disclosure, randomization inference, named assumptions | DECIDED | 2026-10-10 | A model card missing any item does not ship |
| M-03 | Oil is interacted with administration dummies, never partialled out as a nuisance | LOCKED | base spec §9 | Differential response to the same shock is the estimand |
| M-04 | Party effects stratified by tenure (PDP 1st/2nd, APC 1st/2nd), never aggregated | LOCKED | base spec §9 | First- and second-term effects differ systematically |
| M-05 | Cointegration test first (Johansen); ARDL bounds testing only as the documented fallback | LOCKED | base spec §9 | Model choice follows the test result, not preference |
| M-06 | v1 model registry = party/tenure effects across health, education, security, economy | DECIDED | 2026-10-10 | User's choice of registry scope |
| M-07 | Panel frequency: monthly primary, quarterly aggregation as a robustness axis | DECIDED | 2026-10-10 | Monthly is needed to see the short 2023 window (2023-06 → 2023-12) |
| M-08 | No model is ever fitted at render time; the app reads exported artifacts only | LOCKED | base spec §18 | Reproducibility; also the only way model cards can be audited |
| M-09 | Specification curve over the full grid is the primary defence against specification-shopping | DECIDED | 2026-10-10 | Answers the "you picked the friendly model" challenge |
| M-10 | Party vs tenure interaction; samples of 5 administrations / ~26 annual observations acknowledged openly | LOCKED | base spec §9 | Never present a point estimate without its interval |

## Data

| # | Decision | Status | Date | Reason |
|---|---|---|---|---|
| X-01 | Exposure metric **D1 = FAAC allocation per capita** (primary) | DECIDED | 2026-10-10 | Only dose available from open, free, state-month sources across the period |
| X-02 | **D2 = FAAC share of state total revenue** (secondary) | DECIDED | 2026-10-10 | Measures exposure/dependence; computable from FAAC + NBS state IGR |
| X-03 | **D3 = FX/import intensity** (optional, flagged constructed) | DECIDED | 2026-10-10 | Needed for the 2023 naira-float window; no ready series exists |
| X-04 | Oil-derivative revenue share and net-FAAC-after-deductions **rejected** | DECIDED | 2026-10-10 | Rejected on availability, not theory: patchy state audited accounts; not reconstructable to 1999 |
| X-05 | Index to 100 at **January 2000**, fixed anchor, `value` and `value_indexed` both stored | LOCKED | base spec §8 | Fixed anchor, not window start; tooltips show raw values |
| X-06 | Direction labels (↑/↓ better) are a dimension column, never inferred at render | LOCKED | base spec §6 | A falling mortality line reads as failure unless labelled |
| X-07 | Raw layer is immutable; corrections create a **new vintage**, never an edit | DECIDED | 2026-10-10 | Enables revision detection (Stage 3, gate 3) |
| X-08 | Restricted raw (ACLED, DHS/NDHS) is never committed; code + derived aggregates only | DECIDED | 2026-10-10 | Republication is prohibited by their terms |

## Access findings — verified empirically 2026-10-10

Probed with `curl` (clean per-request state, exit codes captured) and independently through the
`read_url` service. "Unreachable" below means **both** paths failed.

| # | Finding | Status | Consequence |
|---|---|---|---|
| A-01 | World Bank Indicators API: keyless, `200`, real paginated JSON | VERIFIED | **Unblocked — this is where collection starts** |
| A-02 | OAGF (`oagf.gov.ng`) and Open Treasury (`opentreasury.gov.ng`): 20s timeout on both paths | VERIFIED | **D1's planned primary source is gone** → route through NBS FAAC disbursement reports; early years may be a declared gap |
| A-03 | ACLED: `api.acleddata.com` **no longer resolves** (DNS failure) | VERIFIED | Base spec §5 endpoint is **stale**; do not build a client against it |
| A-04 | UCDP GED API: `401` — `x-ucdp-access-token` header required | VERIFIED | API is now token-gated (free registration); base spec assumed open download |
| A-05 | FRED: `400` — `api_key is not set` | VERIFIED | Free key required |
| A-06 | IMF DataMapper: `403` to scripted clients, `200` with real JSON via `read_url` | VERIFIED | Reachable, but blocks non-browser clients; needs browser-like headers or the relay |
| A-07 | NBS (`nigerianstat.gov.ng`) and CBN: `200`, HTML | VERIFIED | Reachable; no API — HTML/PDF parsing required |
| A-08 | DHIS2: host reachable (`302`→login); Nigeria tenant unverified | VERIFIED | Institutional credentials required; do not design on it until confirmed |
| A-09 | UNESCO UIS API: `400 Bad Request` (params, not auth) | VERIFIED | Endpoint changed since the base spec; needs re-check against current docs |

## Coverage findings — first World Bank vintage (2026-10-10)

Pulled 7 indicators, 7/7 succeeded, provenance verified (every payload reproduces its recorded
sha256). Coverage is uneven, and the education series is a problem.

| # | Finding | Status | Consequence |
|---|---|---|---|
| C-01 | `u5mr` 61 obs 1964–2024, no gaps; `population` and `cpi_yoy` 66 obs, no gaps | VERIFIED | Health and economy series can carry annual modelling |
| C-02 | **`primary_completion` stops in 2010** (8 obs: 2000, 2004–2010) | VERIFIED | Cannot cover the APC tenures at all (2015+). Useless for party comparison as a World Bank series |
| C-03 | **`ner_primary` stops in 2010** (9 obs: 1999, 2000, 2004–2010) | VERIFIED | Same; the education domain loses its enrolment outcomes post-2010 |
| C-04 | **`literacy_youth` has 8 obs across a 34-year span** (1991, 2003, 2006, 2008, 2013, 2016, 2021, 2024), with an 11-year hole 1992–2002 | VERIFIED | 8 irregular points cannot support a lagged time-series model at all |
| C-05 | **Education is now load-bearing on UNESCO UIS or NEMIS** | OPEN | UNESCO's endpoint is returning `400` and NEMIS is an unprobed manual portal. If neither yields post-2010 state or national education data, the education domain of the registry (M-06) must be **demoted to a declared gap**, not silently under-powered |
| C-06 | The provisional spike gate fires on 1961→1962 (+2039%) and 1962→1963 (−151%) | VERIFIED | Gate needs a **study-window floor (1999+)**; pre-1999 volatility is outside the question and flagging it is noise |

## Candidate indicator probe (2026-10-10)

15 candidates tested for the decisive property: does the series reach 2015+, i.e. can it see the APC
tenures at all? 10 of 15 could. The education result is the important one.

| # | Finding | Status | Consequence |
|---|---|---|---|
| C-07 | **Every World Bank education *outcome* series stops in 2010–2011** — primary completion (2010), lower-secondary completion (2010), pupil-teacher ratio (2010), tertiary enrolment (2011) | VERIFIED | The education domain **cannot carry an outcome model after 2010**. Party comparison (PDP vs APC) on education outcomes is not possible from World Bank data |
| C-08 | Only two education series reach the APC era: `educ_spend_gdp` (14 obs, to 2023) and `adult_literacy` (6 obs) | VERIFIED | Spending is a **policy input, not an outcome**; 6 points cannot support a lagged model. **Education outcome modelling is effectively unavailable** |
| C-09 | Health coverage is strong: `u5mr` 61 obs (0 gaps), `measles_imm` 41 obs (0 gaps), `life_expectancy` 65 obs, `health_spend_gdp` 24 obs (2000–2023), `neonatal_mr` 58 obs | VERIFIED | **Health becomes the anchor domain** — it can support the DiD and time-series families |
| C-10 | World Bank security proxy is unusable: `homicides` has 3 obs (2016–2023) | VERIFIED | The security domain depends **entirely** on ACLED/UCDP |
| C-11 | UNESCO UIS: **every path returns 404, including the API root** | VERIFIED | Path structure changed entirely; endpoint undiscoverable without current docs. **Education fallback 1 blocked** |
| C-12 | NEMIS portal (`nemis.education.gov.ng`): 20s timeout | VERIFIED | **Education fallback 2 blocked.** Third Nigerian government host unreachable, with OAGF and Open Treasury — a pattern worth noting |
| C-13 | ACLED site reachable; its docs confirm **OAuth** authentication for the "updated ACLED API" | VERIFIED | Not a simple key: free **OAuth app registration** required. The base spec's key-based host is dead |
| C-14 | UCDP API root serves Swagger UI; token header confirmed as `x-ucdp-access-token` | VERIFIED | Free token registration at `ucdp.uu.se` (reachable) |
| C-15 | An **invalid World Bank indicator returns HTTP 200 with an error envelope**, not a 4xx | VERIFIED | Would register as "no data" and manufacture a **false coverage gap**. Client now detects the envelope explicitly. Also: `SH.DYN.NMR` is invalid — the correct neonatal code is `SH.DYN.NMRT` |
| C-16 | The manifest stored **Windows backslash paths**; the new orphan check exposed it (15 of 15 files reported orphaned) | VERIFIED → FIXED | Would have broken the GitHub Actions (Linux) plan. Now written via `as_posix()`; orphan count 15 → 0 |

**Education verdict.** Of the four registry domains (M-06), education is the only one with no viable
post-2010 outcome series on free, open, reachable sources. Stage 5 should treat education as a
**declared gap** unless UNESCO's endpoint or NEMIS access is recovered — and the methodology page must
say so, because "we found no education effect" and "we had no education outcome data after 2010" are
very different statements.

## Infrastructure

| # | Decision | Status | Date | Reason |
|---|---|---|---|---|
| I-01 | Python env: `ds-general` prefix env (`~/ds-general`, 3.12.13, requests 2.34.2, pandas 2.2.3) | VERIFIED | 2026-10-10 | `conda run -n ds-general` **fails** — it is a prefix env, not a named one under `miniconda3/envs`. Correct form: `conda run -p "C:/Users/TOSHIBA/ds-general" python ...` |
| I-02 | Free tier is a hard constraint; no paid service at any layer | LOCKED | base spec §4 | Railway/Fly.io/Supabase/Pinecone verified rejected in base spec |
| I-03 | Public, ungated chat access accepted, with the ~1,000 req/day LLM cap as a known failure mode | DECIDED | 2026-10-10 | Migations required: cached answers, quota indicator, graceful degradation to the model card |
| I-04 | Scheduling target is GitHub Actions cron, not a local Prefect agent | OPEN | 2026-10-10 | A laptop cannot guarantee monthly uptime; Prefect retained for dev-time orchestration |
| I-05 | The two spec documents remain at the repo root; `docs/spec/` exists but is empty | OPEN | 2026-10-10 | Migration deliberately deferred to avoid broken references while the plan is still moving |
| I-06 | **One** shared provenance module (`ingestion/clients/provenance.py`) used by every source; the World Bank client was refactored onto it | DECIDED | 2026-10-10 | Two provenance implementations drift, and a drifted manifest is a broken audit trail. Regression-checked: flow exit 0, verify exit 0, probe exit 0 |
| I-07 | Manifests **redact** credential-bearing parameters and URLs | DECIDED | 2026-10-10 | The FRED key travels in the query string, so an un-redacted manifest would leak it into git. Verified: `api_key` masked in both the parameter map and the URL |
| I-08 | Credentials come from environment variables; `.env.example` documents them and `.env` is gitignored | DECIDED | 2026-10-10 | Key-gated clients must fail fast with an actionable `MissingCredential` rather than a confusing HTTP error. Both failure paths verified |
| I-09 | Key-gated clients (`fred`, `ucdp`) are written and tested on their failure paths | DECIDED | 2026-10-10 | Removes everything except the user's registration step from the blocked item; only the credentials themselves remain outstanding |

## RAG / interactive layer

| # | Decision | Status | Date | Reason |
|---|---|---|---|---|
| R-01 | RAG **will** answer causal questions with explicit uncertainty and disclaimers | DECIDED | 2026-10-10 | **Overrides base spec §11, which was `[LOCKED]` as strict refusal** — answering causal questions is the point of the project |
| R-02 | Open-ended natural language over retrieved model artifacts (not a curated question bank) | DECIDED | 2026-10-10 | User's choice |
| R-03 | Assumption-first answer shape: question → estimate + interval → identifying assumption → what it cannot rule out → model card link | DECIDED | 2026-10-10 | A conclusion must never precede the assumption it rests on |
| R-04 | Post-check every answer for interval + assumption + citation; failing responses are replaced by the refusal template | DECIDED | 2026-10-10 | Prevents the RAG layer inventing an estimate |
| R-05 | Model cards rendered read-only: coefficient tables and diagnostics. No live re-fitting, no in-app specification editing | DECIDED | 2026-10-10 | User's selection; keeps the app honest and cheap |
