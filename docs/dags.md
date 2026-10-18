# The causal-graph layer

**What this is.** For every outcome the registry models, three causal graphs — one per
identification design. A visitor picks an outcome, then picks *which causal model to believe*,
and sees the assumption that estimate would rest on, the covariates the graph says must be held
fixed, and what the design cannot rule out. The estimate itself is attached at Stages 6–7.

**Why graphs first.** A coefficient is only interpretable relative to a causal model. Drawing the
model makes three things checkable before any number exists: which variable is being held fixed,
what must be assumed absent, and which claim the design can actually carry. The adjustment set is
not chosen by hand — it is computed from the graph.

**Status:** DAG layer built and verified (2026-10-11); every card carries its **Stage 5 pre-check**
(`diagnostics`), re-run at vintage **2026-10-18** after the fiscal dose, the security outcome and the
widened donor pool landed. Cards do not carry estimates as a layer — that is Stage 8's job — and
**1 of 36 cards passes its pre-check**: `u5mr` under Design C. The rest are **14 fail, 9 degraded,
12 not attempted**; see `docs/design-memo.md`. The totals moved on the last two re-runs (2026-10-16 was
15 fail / 7 degraded / 14 not attempted; 2026-10-17 was 15 / 9 / 12), while the reasons moved on all of
them.
Family A's cards now say the dose is absent on the per-capita axis the estimand is written on (the
nominal dose is landed and gated) and that **the state-attributed outcome has arrived** — so the family is
estimable on the nominal axis, which Stage 6 ran: `estimated_not_identified`, with the failing check named
(`docs/estimates.md`, C-47).

---

## The question, and the exposure

The question is the influence of a **regime / administration** on outcomes in health, security,
education and the economy. The exposure is therefore always the administration. The three designs
differ in how the exposure is operationalised:

| Design | How the administration enters | Unit |
|---|---|---|
| **A** — State dose-response DiD | A federal policy shift, with each state's exposure intensity as the dose | state-month |
| **B** — National VECM / ARDL | The party×tenure dummy, interacted with oil | national-month |
| **C** — Synthetic control | The treated tenure itself, against a donor pool | country-year |

## Node vocabulary

Nodes are shared across designs where the concept is shared, so the graphs are comparable.

| Node | Meaning | Appears in |
|---|---|---|
| `oil` | Brent crude price / global oil shock | A, B |
| `inherit` | Inherited state conditions at baseline | A |
| `statefe`, `timefe` | State and time fixed effects | A |
| `donor` | Donor-funded programmes (health and education outcomes only) | A, B |
| `dose` | Policy exposure intensity — D1, FAAC per capita | A (exposure) |
| `lagY` | Lagged outcome (persistence) | B |
| `trend` | Linear and quadratic time trend | B |
| `admin` | Administration (party × tenure) | B (exposure) |
| `oilxadmin` | Oil × administration — effect modification, never partialled out | B |
| `faac` | FAAC allocation / fiscal space | B |
| `fx` | NGN/USD exchange rate | B |
| `common` | Common factors (global oil / commodity cycle) | C |
| `countryfe` | Country fixed effects | C |
| `donors` | Donor-pool outcome paths (synthetic weights) | C |
| `treat` | Nigeria under administration X | C (exposure) |
| `Y` | The outcome — substituted per outcome | A, B, C (outcome) |

## The three designs, as assumptions

### A — State dose-response DiD
**Estimand:** ATT of a federal policy shift, with state exposure as the dose.
**Adjustment set:** `{inherit, oil, statefe, timefe}` — plus `donor` for health and education.
**Identifying assumption:** parallel trends — absent the shift, states with different exposure would
have followed parallel paths; formally, no unmeasured state-by-time confounder drives both dose and
outcome. The unobserved node `u_st` is assumed absent.
**Does not establish:** anticipation before the formal date; SUTVA violations via cross-state
spillovers; that the dose itself is uncontaminated by the policy it measures.

### B — National VECM / ARDL time series
**Estimand:** the long-run multiplier for the administration effect, oil-interacted.
**Adjustment set:** `{oil}`.
**Identifying assumption:** conditional exogeneity of the administration dummy given oil, lagged
outcome, fiscal and FX controls and the trend. The unobserved node `u_t` is assumed absent.
**Does not establish:** the *total* effect — `faac` and `fx` are downstream of the administration,
so conditioning on them identifies a **direct effect net of the fiscal and FX channel**. Also:
~26 annual observations, five administrations, wide intervals; structural breaks not fully absorbed.

> **Finding that fell out of drawing the graph.** The Tier 3 covariate set in the base spec is
> `oil + FAAC + FX + lags + trend`. In graph terms, FAAC and FX are *mediators* of the
> administration channel, so that specification estimates a direct effect rather than the total
> effect. This was invisible before the graph existed and is now on every Design B card's
> `cannot_rule_out`.

### C — Synthetic control (cross-country)
**Estimand:** the treatment gap, Nigeria minus synthetic Nigeria.
**Adjustment set:** `{common}`.
**Identifying assumption:** the donor-weighted common factors (above all the oil cycle) stand in for
Nigeria's counterfactual, and no Nigeria-specific shock coincides with the treatment. The unobserved
node `u_ng` is assumed absent.
**Does not establish:** anything when pre-treatment fit is weak, or when an idiosyncratic
Nigeria-only shock falls inside the window. Where the donor pool cannot produce a credible
counterfactual, the card says so instead of shipping the gap.

## How "assumed absent" is computed and shown

Each design includes exactly one **unobserved** node. The graph displayed includes it, drawn and
labelled `(assumed absent)`. The adjustment set, however, is computed by `dagitty` on the
**assumed graph** — unobserved nodes and their edges removed — with `type = "minimal"` and
`effect = "total"`. The full graph is not identifiable (an unblockable backdoor path runs through
the unobserved node), which is precisely the point: the estimate is *conditional on that node being
absent*, and the card states it rather than burying it.

## Coverage is not the same as identifiability

A graph is a claim about causal structure; it is valid whether or not the outcome series currently
reaches the study window. All 12 catalogue outcomes therefore have all three graphs, with coverage
carried alongside on the card:

- **Health** — usable (interpolated annual series).
- **Economy** — usable (note the 2014 rebasing break).
- **Education** — `declared_gap`: no open outcome series reaches the APC tenures. The graphs exist;
  the card says the data do not.
- **Security** — `blocked`: depends entirely on ACLED/UCDP, not yet wired.

"We found no education effect" and "we had no post-2010 education outcome" are different statements.
Only the second is true here, and the card carries the distinction.

## Every variable, and where it comes from

Each node on each card carries a `source` and a `source_status`, so Stage 1's exit criterion —
*every variable required by a design maps to a named source, or is recorded as a declared gap* — is
machine-checkable rather than asserted. The generator refuses to emit a card with an unsourced node.

| Node | Source | Status |
|---|---|---|
| `admin`, `treat` | Administration spine (base spec §7) | acquired |
| `donor` | World Bank `DT.ODA.ALLD.CD` (net ODA) | acquired — **contaminated, see below** |
| `fx` | World Bank `PA.NUS.FCRF` (annual); CBN for monthly | acquired |
| `donors` (pool) | Donor panel: 99 candidate countries × 5 predictors (widened 2026-10-18) | acquired — 27,352 country-metric-years, 1960–2025; 62 countries carry all five across 1990–2015 |
| `Y` | the outcome's own source, from `outcomes.yml` | per outcome |
| `inherit`, `lagY`, `oilxadmin` | derived from other nodes | derived |
| `statefe`, `timefe`, `trend`, `countryfe` | design artefacts, not data | construct |
| `u_st`, `u_t`, `u_ng` | the node the estimate assumes absent | unobserved |
| `oil` | FRED `DCOILBRENTEU` via `ingestion/flows/pull_fred.py` | **acquired** (10,275 daily obs, 1987→2026) |
| `common` | derived from the donor-panel paths and the Brent cycle | derived |
| `dose`, `faac` | NBS FAAC disbursement reports | **gap** — needs a PDF parser |

`index.json` carries `variables_still_missing`: every node with no usable source across the whole
registry. `tests/verify_dags.py` **recomputes that list from the cards** and fails if the index
disagrees, so the gap list cannot drift from the graphs it summarises.

### One acquired node is not a clean control

Stage 3's spike gate caught `donor_oda` rising **+1006% in 2005** and reversing −82.9% by 2007, because
Paris Club debt relief is recorded as official development assistance (OECD, UNCTAD; Nigeria's US$18bn
deal was announced October 2005 and completed April 2006). The node is genuinely *acquired* — the series
exists and is gated — but it measures aid **received including debt forgiveness**, not donor effort.

That matters here rather than in a footnote: `donor` sits in the adjustment set for **design A and
design B on every health and education outcome**, so conditioning on it partially conditions on a debt
restructuring that coincided with the start of the 2003–2007 tenure. Stage 5 must annotate those cards
and, if the trace through `donor` is doing real work, report the estimate with and without it.

This is the intended division of labour: the graph layer declares *what is held fixed*, and the quality
gates record *whether that thing is fit to hold fixed* (decisions C-28).

### Still missing, by root cause

**Five variables, two root causes** — the oil group closed on 2026-10-11 and the security group on
2026-10-17:

| Root cause | Variables | What it needs |
|---|---|---|
| **Fiscal dose** | `dose` (D1), `faac` | ~~An NBS FAAC PDF/HTML parser, plus a decided state population denominator~~ — **the parser is done (2026-10-16) and the series is Stage 3 gated (2026-10-17)**; what is left is the state population denominator (X-09), on which the per-capita form of `dose` rests |
| **Education outcomes** | primary completion, net enrolment, youth literacy | No open source reaches 2015+. UNESCO UIS 404s, NEMIS times out |
| **Security outcomes** | fatalities, incidents | ✅ **Closed 2026-10-17** — UCDP GED, landed from its **keyless bulk archive** (the API's token was never the only route, C-45); state-attributed on the panel, national on the spine |
| ~~**Oil price**~~ | ~~`oil` (designs A, B), `common` (design C)~~ | ✅ **Closed** — free FRED key registered, Brent landed (C-23, C-24) |

Closing the oil group took **design C to zero unsourced nodes**. With the security outcome also closed,
designs A and B are each down to one unsourced node — the per-capita FAAC dose — and that one is now a
*decision* (X-09) rather than a source, which is what Stage 6's log specification works around for the
elasticity (S6-06).

> **The two rows above `dose`/`faac` are not stale, and the reason is worth keeping.** `dose` and `faac`
> still carry `source_status: gap` because `analysis/specs/dag_designs.yml` says so and the cards are
> generated from it. The FAAC series itself exists — 174 documents, 114 months × 36 states, populated on
> the panel, gated by Stage 3 (S4-13…S4-19, C-39…C-43) and now carrying an estimate on the *nominal* axis
> (S6-06). What is missing is the per-capita form the `dose` node is specified as, and that waits on X-09.
> So `gap` is under-specified rather than wrong, and it is left alone rather than hand-edited:
> `tests/verify_dags.py` recomputes the gap list from the cards and would fail against an edited page.
> The security outcomes, by contrast, have left this list — their `coverage_status` changed in
> `outcomes.yml` because the data changed (C-45), and the cards were regenerated from it.

### Acquired since the last vintage

Probing closed seven of the gaps (see `ingestion/flows/probe_missing_variables.py` and decisions
C-17…C-20). Best of the batch: `donor` had **no source at all** but is now landed, and the entire
Design C donor pool is in hand — all 13 candidate countries carry all 5 screening predictors to
2015, except Venezuela's oil-rents series. *(That was the pool as landed on 2026-10-11; it was widened
to 99 candidates on 2026-10-18 — the inventory table above is the current one.)*

The eighth closed by **registration rather than probing**: the oil price had no keyless route at all
(C-20), so a free FRED key was obtained and Brent crude is now landed as a daily series through
`ingestion/flows/pull_fred.py` (C-23). `probe_missing_variables.py` now exercises that *keyed* path
first and falls back to the keyless-substitute test only when no key is present.

```bash
# what the graphs need that nothing sources
conda run -p "C:/Users/TOSHIBA/ds-general" python ingestion/flows/probe_missing_variables.py

# land the national series, the donor panel and the oil covariate, then prove all three
conda run -p "C:/Users/TOSHIBA/ds-general" python ingestion/flows/pull_worldbank.py
conda run -p "C:/Users/TOSHIBA/ds-general" python ingestion/flows/pull_worldbank_donors.py
conda run -p "C:/Users/TOSHIBA/ds-general" python ingestion/flows/pull_fred.py
conda run -p "C:/Users/TOSHIBA/ds-general" python tests/verify_provenance.py
```

## Artefacts

| Path | What it is |
|---|---|
| `analysis/specs/outcomes.yml` | The 12 outcomes with Stage-1 coverage status |
| `analysis/specs/dag_designs.yml` | The three design templates — nodes, edges, sources, assumption text |
| `analysis/R/01_build_dags.R` | Generator: instantiate → validate → compute adjustment set → render → check |
| `registry/schema/dag_card.schema.json` | JSON Schema for a DAG card |
| `registry/schema/dag_index.schema.json` | JSON Schema for the index |
| `registry/dags/<outcome>__<design>.svg` | The rendered graph (36 figures) |
| `registry/dags/<outcome>__<design>.json` | The card (36 files) |
| `registry/dags/index.json` | The matrix + `variables_still_missing` |
| `ingestion/flows/probe_missing_variables.py` | Reconnaissance: what the graphs need that nothing sources |
| `ingestion/flows/pull_worldbank_donors.py` | The Design C donor panel |
| `ingestion/flows/pull_fred.py` | The oil covariate (Brent crude); refuses to overwrite a landed vintage |
| `analysis/specs/diagnostics.yml` | Stage 5 pre-check configuration |
| `analysis/R/02_diagnostics.R` | Stage 5 engine — writes `registry/diagnostics/<vintage>/` |
| `registry/diagnostics/<vintage>/diagnostics.json` | The machine-readable pre-check result |
| `registry/diagnostics/<vintage>/report.md` | The human-readable page |
| `docs/design-memo.md` | The Stage 5 output: which family is credible per outcome, and why |
| `tests/verify_dags.py` | Independent verification |
| `tests/verify_stage5.py` | Independent recomputation of every Stage 5 headline number |

A card carries: the outcome and its coverage status, the design and its estimator, the node/edge
lists with each node's source and source status, the adjustment set, the `assumption_required`
nodes, the identifying assumption in one sentence, what cannot be ruled out, the dagitty graph
strings, the SVG path, and an `estimate` block that stays `not_estimated` until Stages 6–7. Since
Stage 5 it also carries a **`diagnostics` block** — the pre-check status (`pass` / `degraded` /
`fail` / `not_attempted`), the list of checks with their verdicts, the blocker that explains any
non-pass, and the vintage and source it came from.

```bash
# regenerate (R 4.5.2 + ggdag/dagitty)
Rscript analysis/R/01_build_dags.R

# verify (independent of R: re-derives acyclicity and the backdoor-blocking property)
conda run -p "C:/Users/TOSHIBA/ds-general" python tests/verify_dags.py
```

The verifier does not trust the generator. It re-checks the schema, re-derives acyclicity, and
confirms by d-separation that the reported adjustment set blocks **every** backdoor path in the
assumed graph while blocking none of the causal path. Across the 36 graphs that is 3–8 backdoor
paths per graph, all blocked.

## What comes next

1. **Stage 4 harmonisation** gives the cards their inputs: the administration spine, the monthly panel,
   direction labels, the January-2000 anchor — and Brent resampled by the rule Stage 3 froze.
2. **Stage 5 diagnostics** — **built 2026-10-11, re-run at vintage 2026-10-16 and again 2026-10-17**: every card carries its pre-check verdict, and the
   three families are decided on the record (A dropped, B degraded, C infeasible; `docs/design-memo.md`).
   It carries Stage 3's findings onto the affected cards too — the `donor` contamination above, and the
   January-2025 CPI rebasing inside `cpi_yoy`'s window.
3. **Estimation.** Stage 6 **ran on 2026-10-17** and published 12 specifications with intervals and the
   check behind each verdict (`registry/estimates/2026-10-17/`, `docs/estimates.md`) — but not on these
   cards: the `estimate` block is the model-card schema, which is Stage 8 work. Until it is filled the app
   shows the assumption and the adjustment set with **no number**, which is the rule M-02 set: a card
   without an interval does not ship. The card's own `estimate.note` says so, computed by the generator
   rather than typed beside it.
4. **The app** reads the index and renders: pick an outcome → pick a causal model → read the
   assumption and adjustment set → later, the estimate under that model.
