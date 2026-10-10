# Progress log — causal-presidents-regime-Naija

**Last updated:** 2026-10-10 · **Stage:** 1 of 8 (data collection) — analysis not started
**One-line status:** specification complete, ingestion pipeline working and provenance-verified on one
source; three sources blocked on free credential registration.

---

## 1. What this project is

An interactive causal-inference explorer for national outcomes across Nigerian presidential
administrations (1999–present). Visitors ask causal questions of a model **and** inspect the fitted
models behind the answers — coefficient tables, diagnostics, sensitivity bounds.

Presidents are one input among oil cycles, state governments, donor funding and inherited conditions.
The project's job is to show those confounders, not to bury them. Nothing here identifies a causal
effect that the design cannot support.

## 2. Written deliverables

| Document | Purpose | Status |
|---|---|---|
| `#CausalPresidents.txt` | Base spec (README v1.0) — the original dashboard brief | Source, unmodified |
| `nigeria-causal-inference-spec.md` | Design spec — upgrades the dashboard to a causal-inference explorer; records which base-spec `[LOCKED]` items are overridden and why | Complete |
| `PHASES.md` | Phase plan, Stages 0–8 from data collection to analysis, with exit criteria and gotchas per stage | Complete |
| `docs/decisions.md` | Decision log — 40+ dated decisions: framing, method, data, access findings, coverage findings, infrastructure, RAG | Live, updated as evidence arrives |
| `docs/licences.md` | Licence register — redistribution rights per source, plus 5 open licensing questions | Live |
| `knowledge.md` | Agent-facing repo context | Live |
| `PROGRESS.md` | This file | Live |

## 3. Code and data artefacts

| Artefact | What it does | Verified |
|---|---|---|
| `ingestion/clients/provenance.py` | Shared provenance: byte-exact payload storage, sha256, POSIX paths, **credential redaction** | Redaction confirmed |
| `ingestion/clients/worldbank.py` | World Bank acquisition; retries, pagination, row-count assertion, detects the 200-with-error envelope | Working |
| `ingestion/clients/fred.py` | Brent crude (`DCOILBRENTEU`) — oil covariate for the VECM/ARDL family | Failure path only |
| `ingestion/clients/ucdp.py` | UCDP GED fatalities — security domain (CC-BY, redistributable) | Failure path only |
| `ingestion/flows/pull_worldbank.py` | Lands a vintage: raw pages + `manifest.json` + provisional `coverage.json` | Exit 0, 15/15 |
| `ingestion/flows/probe_candidates.py` | Reconnaissance: which indicators actually reach the APC era | Exit 0 |
| `tests/verify_provenance.py` | Re-derives every sha256 and detects orphaned files | Exit 0 |
| `data/raw/worldbank/2026-10-10/` | 15 payloads + manifest + coverage report | Gitignored, never committed |

## 4. Verification evidence

Commands and their observed results — these are measurements, not assertions:

```
pull_worldbank.py     -> exit 0   succeeded: 15/15   failures: 0
verify_provenance.py  -> exit 0   page files on disk: 15, referenced: 15, orphaned: 0
                                  PASS — every stored payload reproduces its recorded sha256
probe_candidates.py   -> exit 0   covers 2015+: 10 of 15
fred (no key)         -> MissingCredential raised (actionable message)
ucdp (no key)         -> MissingCredential raised (actionable message)
```

Reproduce with:

```bash
conda run -p "C:/Users/TOSHIBA/ds-general" python ingestion/flows/pull_worldbank.py
conda run -p "C:/Users/TOSHIBA/ds-general" python tests/verify_provenance.py
```

Note: `conda run -n ds-general` does **not** work — `ds-general` is a prefix environment at
`~/ds-general`, not a named one under `miniconda3/envs` (decisions.md I-01).

## 5. Findings so far

**Access (probed 2026-10-10; "unreachable" = failed via two independent network paths):**

| Source | Result |
|---|---|
| World Bank API | ✅ keyless, working — the backbone |
| NBS, CBN | ✅ reachable (HTML/PDF, no API) |
| IMF DataMapper | ⚠️ 403 to scripted clients, 200 via relay |
| FRED, UCDP | 🔑 free key / free token required |
| ACLED | ❌ documented endpoint dead; now **OAuth** |
| OAGF, Open Treasury, NEMIS | ❌ unreachable — three Nigerian gov hosts |
| UNESCO UIS | ❌ every path 404, including root |

**Coverage (first vintage, 15 indicators):**

- **Health is strong** — `u5mr` 61 obs no gaps, `life_expectancy` 65, `measles_imm` 41, `health_spend_gdp` 24
- **Economy is strong** — `gdp_per_capita`, `population`, `cpi_yoy` all 66 obs no gaps
- **Security has no usable World Bank series** (`homicides`: 3 obs) — depends entirely on UCDP/ACLED
- **Education is unusable after 2010** — every outcome series stops in 2010–2011. Primary completion,
  lower-secondary completion, pupil-teacher ratio and tertiary enrolment all end mid-Jonathan, so they
  cannot see the APC tenures at all. Only `educ_spend_gdp` (a policy input, not an outcome) and
  `adult_literacy` (6 points) reach the present.

  **Consequence:** of the four registry domains, education should be recorded as a **declared gap**.
  "We found no education effect" and "we had no education outcome data after 2010" are different
  statements, and only the second is true.

## 6. Corrections made (kept visible rather than quietly fixed)

1. **My first endpoint probe was buggy** — it reused a temp file, so failed requests printed the
   previous request's body. Caught and re-run clean; all recorded findings come from the corrected run.
2. **A false-gap hazard in the client.** An invalid World Bank indicator returns **HTTP 200 with an
   error envelope**, not a 4xx. Left unchecked it registers as "no data" and manufactures a fake
   coverage gap. The client now detects the envelope; a negative test confirms `SH.DYN.NMR` raises.
   (The correct neonatal code is `SH.DYN.NMRT`.)
3. **Windows backslash paths in the manifest**, exposed by the orphan check reporting 15/15 files
   orphaned. This would have broken the Linux CI runners the plan schedules against. Fixed with
   `as_posix()`; orphans now 0.
4. **A secret-leak risk removed before it existed.** The FRED key travels in the query string, so an
   un-redacted manifest would have written it into git. Credentials are now masked in both the
   parameter map and the URL.

## 7. Blocked

| Blocker | Needs |
|---|---|
| FRED key, UCDP token, ACLED OAuth app | **You** — three free registrations, none paid. Paste into a local `.env` (see `.env.example`); never into chat |
| UNESCO UIS current API path | Its docs (web search unavailable in this environment) |
| NEMIS reachability | A check from a network other than this one |
| DHIS2 tenant access | Institutional credentials; do not design a model on it until confirmed |

## 8. Next steps, in order

1. **Stage 3 — quality gates.** Promote the provisional gates in `coverage.json` into real gates and add
   the **study-window floor (1999+)**; today the spike gate fires on 1961–63 volatility that is outside
   the question entirely. *Unblocked — no credentials needed.*
2. **Run the FRED and UCDP pulls** once credentials exist; write the ACLED OAuth client.
3. **Stage 4 — harmonisation** (dbt): metric dimension with direction labels, the January-2000 index
   anchor, the administration spine, the state panel at monthly frequency.
4. **Stage 5 — the design memo.** Where models get dropped on the record, before estimating anything.
5. **Stages 6–8** — estimation (R), specification curve, registry and RAG corpus.
6. **Stage 9** — the interactive app.

## 9. Standing constraints

- **Free tier only.** No paid service at any layer.
- **Publish code and derived aggregates; never restricted raw data.** ACLED and DHS/NDHS may not be
  redistributed, which is why this repo's `.gitignore` excludes `data/raw/`.
- **Never a point estimate without its interval.** Six-item rigor floor acts as a shipping gate.
- **The app never fits a model at render time.**
