# Nigeria Causal Inference Explorer — Spec

**Status:** Draft v0.1, from interview on 2026-10-10. No code written yet.
**Source documents:** `#CausalPresidents.txt` (README v1.0 — the base spec), `TOOLING.md` (machine inventory), `knowledge.md` (repo context).
**Short name for this request:** interactive causal inference project — users ask causal questions of a model *and* inspect the models behind the answers.

---

## 1. Purpose of this spec

The base spec (`#CausalPresidents.txt`) builds a **comparison dashboard**. This spec upgrades it to an
**interactive causal-inference explorer**: a public artifact where a visitor can

1. ask a causal question in natural language and receive an answer that states exactly what the estimates
   can and cannot support, and
2. open the model behind that answer as an inspectable object — specification, coefficient table,
   intervals, diagnostics, sensitivity bounds.

The user's own framing of the goal, in priority order:

> "Something users can access and answer questions about causality via the model but also view models and see."
> "Interactive dashboard now, the analysis should just be rigorous enough."

So: **the interactive layer is the deliverable; the analysis must be defensible, not exhaustive.** Rigor
is spent where a skeptical viewer would look, and nowhere else.

---

## 2. Decision record — what this changes in the base spec

The interview overrode two `[LOCKED]` items and ten non-locked defaults. Nothing else in
`#CausalPresidents.txt` is superseded.

| Base spec item | Original | This spec | Why |
|---|---|---|---|
| §11 RAG guardrail `[LOCKED]` | Refuse anything outside descriptive retrieval | **Overridden.** Answer causal questions, with explicit uncertainty and disclaimers, always tied to a retrieved model artifact | User chose "answer causal questions with explicit uncertainty and disclaimers" — the point of the project is that people can ask about causality |
| §9 Tier 4 (DiD) & Tier 5 (synthetic control) | Deferred to v2 | **Promoted to v1** | These are the only designs that can carry a causal-sounding claim; deferring them leaves the app asserting more than it can show |
| §9 Tier ladder | Five tiers, Tier 1 default view | Tier ladder **retained as the adjustment framework**, but **not** the primary display. Primary display is the model card | User selected the four design families, not the tier ladder, as what v1 implements |
| §9/§20 Tenure stratification | Open question | **In**: party effects stratified by tenure (PDP 1st/2nd, APC 1st/2nd) | User chose "party/tenure effects across all four domains" as the v1 registry |
| §10 Adjustment language | R | **R, confirmed** — results exported as tables for the app | User chose R for everything with export |
| §5/§20 Data scope | National series only, non-goals exclude subnational | **State-level panel added** for the DiD family | "Most rigorous and available"; national-only cannot power the chosen designs |
| §16 Honesty layer `[LOCKED]` | Footnote, direction labels, vintage, imputation flags, CIs, methodology link, refusal behavior | **Retained and extended**, not weakened — see §8 | The upgrade raises the claim ceiling, so the honesty layer must carry more weight, not less |
| §4 Free tier | Non-negotiable | Retained. Groq rate cap explicitly accepted as a known failure mode (§12) | User chose public, ungated access |
| §20 "View models" | Not in base spec | **New requirement** (§6) | The distinguishing feature of this project |
| §20 Question bank | Sidebar chat with starter questions | Open-ended NL over a retrieved **model registry**, not a curated bank | User chose open NL over model artifacts |
| §13 Build order | Phase 1–6 pipeline-first | **Analysis layer first, UI later** | User chose that sequencing explicitly |
| §18 Store adjusted estimates as tables | Locked | Retained — **the app never fits a model at render time** | Reproducibility rule; also the only way model cards can be audited |

---

## 3. The artifact, defined

A Streamlit application, publicly hosted, with four working surfaces:

| Surface | What the visitor does | Backing artifact |
|---|---|---|
| **Compare** | Overlaid indexed trend lines, party/president colour mode, shock bands, portraits — the base spec's §8 chart, unchanged | `analytics` tables |
| **Models** | Browse model cards, coefficient tables, forest plots, event-study plots, sensitivity bounds — for every model in the registry | Model registry (precomputed) |
| **Ask the data** | Open natural-language causal questions; answers state the estimate, the interval, the identifying assumption, and what the model cannot rule out, with a link to the model card | RAG over the registry + methodology corpus |
| **Methodology** | Adjustment framework, what each design controls for, cointegration results, sample size and DoF, limitations, RAG scope and evaluation scores | Static + generated docs |

Supporting surfaces: **Data & vintage** (sources, licences, last-refresh timestamp, imputation flags) and an
always-visible footer linking to Methodology.

---

## 4. Audiences and what each must get

The interview selected all four audiences. They are not equally served by one default view, so the app
ships with a **reading-level toggle** that changes copy and default panel, never the numbers.

| Audience | Needs | Interface implication |
|---|---|---|
| General public | A readable answer that cannot be misread as a causal claim | Plain-language answer, banner: colours indicate office, not causation |
| Students / researchers | To see how identification actually works | Model cards front and centre, assumption text, diagnostics one click away |
| Portfolio / professional reviewers | Evidence of engineering and statistical discipline | Reproducibility block, pinned envs, spec curve, published design rationale |
| Policy analysts | Defensible numbers with stated assumptions before quoting | Intervals everywhere, DoF disclosure, copyable citation block per estimate |

---

## 5. Identification designs (v1 — all four, in this order of implementation)

### 5.1 Family A — State-level dose-response / staggered DiD on federal policy shifts

The only family with real statistical power. Each federal shift is a separate study.

- **Unit:** 36 states + FCT × month (or quarter), ~1,000–13,000 state-periods depending on frequency.
- **Treatments (event windows):** 2016 FX regime change and oil crash; 2020 COVID period; 2023 fuel
  subsidy removal and naira float. Succession crisis 2010-02 → 2010-05 is included as a fourth window
  if state-level outcomes permit.
- **Exposure (dose):** state-level intensity of the treatment channel — candidate metrics are FAAC
  allocation per capita, oil-derivable share of state revenue, FX exposure of the state's import-dependent
  consumption basket. **Final exposure metric is an open decision (§15).**
- **Estimator:** modern staggered DiD — Callaway & Sant'Anna group-time ATT via `did`, cross-checked with
  `fixest` two-way FE and Sun–Abraham style event study.
- **Inference:** permutation/randomization inference over treatment-date reassignment, plus state-clustered
  wild bootstrap.
- **Required outputs:** event-study plot, pre-trend test, in-time placebo (fake treatment dates), donor
  permutation distribution, and the imputation warning where outcomes are interpolated.

### 5.2 Family B — VECM / ARDL time-series engine (base spec §9 Tier 3, upgraded)

- **Variables:** outcome; log Brent crude; FAAC allocation to states; NGN/USD; lagged outcomes (≤4 lags);
  party dummy; linear and quadratic time trend.
- **Specification:** test cointegration first (Johansen via `vars` / `urca`); if series are not integrated
  of the same order, fall back to ARDL bounds testing (`dynlm`).
- **Oil interaction — retained and non-negotiable (§9):** oil price interacted with administration
  dummies, so the model estimates whether presidents responded *differently to the same shock*. Oil is the
  dominant exogenous feature of Nigerian political economy and is not partialled out as a nuisance.
- **Output:** long-run multiplier for the party/tenure effect **with a confidence interval** (delta method,
  with a bootstrap cross-check).
- **Published alongside it:** the DoF cost. Five administrations, ~26 annual observations — the interval
  will be wide and the card must say so rather than bury it.

### 5.3 Family C — Synthetic control with a pre-fit-screened mixed donor pool

- **Donor pool (user-selected):** West African neighbours **plus** oil exporters, screened by
  pre-treatment fit — not a fixed list.
- **Candidate donors:** Ghana, Senegal, Côte d'Ivoire, Kenya, Tanzania, South Africa (institutional
  proximity) alongside Angola, Algeria, Gabon, Ecuador, Indonesia, Colombia, Venezuela (oil-channel
  proximity).
- **Selection rule:** donors retained only if they pass a pre-treatment fit threshold on the predictor set
  (GDP growth, inflation, oil dependence, population, health and education levels).
- **Pool composition is itself a robustness axis:** results are reported across donor-pool definitions,
  including the pool that best fits pre-treatment and a leave-one-donor-out sweep.
- **Required diagnostics:** pre-treatment RMSPE, post/pre RMSPE ratio, in-space placebo (every donor
  treated) and in-time placebo.
- **Honest ceiling:** five treatment units is a small treated set. Where the donor pool cannot produce a
  credible counterfactual, **say so on the card instead of shipping the estimate.**

### 5.4 Family D — Specification curve / multiverse

Ties A–C together and is the single strongest defense against a reviewer picking apart one model.

- **Axes:** estimation family (A/B/C), adjustment tier (Tier 1/2/3 from the base spec), covariate set
  (oil only / oil + FAAC / oil + FAAC + FX), lag order, event window length, imputation handling,
  index anchor, donor pool definition (for C).
- **Storage:** every specification in the grid is fitted and stored; the app renders the distribution.
- **Display:** sorted specification-curve plot, with the preferred specification marked and the
  number of specifications supporting each sign stated as a count, never as a vote.

---

## 6. The "view the models" requirement (new)

Users must be able to inspect the fitted model behind any answer. This is a **read-only** requirement —
the interview explicitly did not ask for live re-fitting or in-app specification editing.

**Per-model deliverables, rendered in the app:**

1. **Coefficient table** — estimate, standard error, interval, p-value where appropriate, N.
2. **Specification block** — plain-language statement of the model, covariates, lags, sample window,
   estimator name and version.
3. **Diagnostic and sensitivity plots** — event-study plot, forest plot with intervals, pre-trend test
   output, placebo/permutation distribution, sensitivity bounds.
4. **Assumption text** — the identifying assumption in one sentence, plus what the model cannot rule out.
5. **DoF and sample disclosure** — the effective sample and the degrees-of-freedom cost of the covariates.
6. **Provenance** — vintage date, anchor config, commit hash, R session/environment reference.

**Model card schema (machine-readable, one file per model):**

```
model_id, question_id, family (A/B/C/D), outcome_id, outcome_label, direction (up/down better),
unit (state-year | national-month | country-year), estimand (ATT group-time | long-run multiplier |
  synthetic-control gap), point_estimate, se, ci_low, ci_high, ci_level, n_obs, n_units,
  dof_cost, identifying_assumption, cannot_rule_out [], covariate_set, adjustment_tier,
  estimator, estimator_version, inference_method, diagnostics {pre_trend_p, rmspe_pre, rmspe_ratio,
  placebo_p, spec_curve_support}, sensitivity {oster_delta, rosenbaum_gamma}, vintage_date,
  anchor_config, commit_sha, code_ref []
```

---

## 7. Rigor floor (mandatory, every model)

All six items were selected. Any model card missing one of these **does not ship**:

1. **Intervals on every estimate** — no point estimate anywhere in the app or the API without its interval.
2. **Placebo, pre-trend and permutation tests** — parallel-trends/pre-trend tests, donor-pool placebos,
   permutation-based inference for DiD.
3. **Sensitivity to unobserved confounding** — Oster delta, Rosenbaum bounds where applicable.
4. **Explicit DoF and sample-size disclosure** — the five-administration constraint stated next to the
   affected estimates, at national level and in the app copy.
5. **Randomization inference / in-time placebo** — reassign treatment dates and show how often an effect
   of this magnitude appears by chance.
6. **Named identifying assumptions** — one plain-language sentence per model, adjacent to what it cannot
   rule out.

---

## 8. Honesty layer (base spec §16, retained and extended)

Retained from the base spec (non-negotiable): colours indicate office and not causation; direction labels
(↑/↓ better) per metric in every legend; visible data-vintage timestamp; imputation flags rendering as
dashed segments; intervals beside all adjusted estimates; methodology page linked from every view; RAG
refuses questions outside its data scope.

Extended for the causal upgrade:

- **Tier badge on every estimate** (Tier 1 raw / Tier 2 inherited-conditions flag / Tier 3 adjusted).
- **Assumption-first answer shape** — the Q&A answers *in this order*: what is being asked → what the
  estimate is and its interval → what identifying assumption it rests on → what it cannot rule out →
  the model card link. Conclusion never precedes the assumption.
- **No causal verb without a stated design.** "Caused" is permitted only where Family A or C supports it,
  and the sentence must name the design. Otherwise the language is "the data show X move with Y, and how
  much of that is attributable cannot be recovered here."
- **Unsupported-question ceiling.** Where no model exists, the answer is "I don't have a model for that",
  plus the nearest questions the registry does answer. Never a hallucinated estimate.

---

## 9. Interactive Q&A layer

**Retrieval design (open-ended NL over model artifacts — user's choice):**

1. User question (Streamlit chat input).
2. Embed locally — `sentence-transformers`, `all-MiniLM-L6-v2` (CPU, ~80 MB, no API dependency).
3. Retrieve top-5 chunks from `pgvector` on Neon. Corpus = metric catalog, methodology page, data
   dictionary, shock annotations, administration table, limitations, **and one chunk per model card**.
4. Assemble prompt: system instruction + retrieved model artifacts + question.
5. Call the LLM (Groq, Llama 3.3 70B via the OpenAI-compatible client; Gemini as fallback).
6. Post-check the response before display: does it carry an interval? Does it name the assumption? Does it
   cite a model card or refuse? **A response failing the check is replaced with the refusal template.**
7. Render answer, then citations as expandable blocks linking to the model card and methodology section.

**Latency budget (base spec, retained):** embedding ~50 ms local + vector query ~10 ms + LLM ~500 ms.

**Corpus must be regenerated whenever a model card changes** — the RAG index and the registry share one
vintage stamp so a stale answer can never outlive the model it quotes.

**Starter questions** (base spec's four, extended toward causality):
"What was under-5 mortality under Yar'Adua?" · "Which president had the highest inflation?" · "How did the
2016 recession affect security metrics?" · "Compare PDP and APC on immunisation." · "Did the 2023 subsidy
removal cause the inflation spike, and how would we know?" · "How much would unobserved confounding have
to matter to overturn that?" · "Show me the models behind that answer."

---

## 10. Data layer, licensing, and what may be published

Chosen approach: **ship code plus derived aggregates; never the raw restricted data.**

- **Published in the public repo:** all ingestion/estimation code, the derived aggregates the app reads,
  the model registry, acquisition instructions per source, and the licences.
- **Never published:** raw ACLED extracts and DHS/NDHS microdata. Both restrict redistribution. ACLED's
  free tier also withholds the most recent 12 months and requires registration; DHS/NDHS requires its own
  registration and forbids republication.
- **Verifiable by a stranger:** someone with their own credentials must be able to run the acquisition
  scripts and reproduce the aggregates. Where a source cannot be redistributed, the repo ships a
  documented substitute or an explicit gap note — never a silent hole.
- **Prefer open-licence substitutes where they carry the same signal,** e.g. UCDP GED for conflict
  fatality series, World Bank/UNESCO for socio-economic series.
- **Sources:** as listed in base spec §5 — World Bank Indicators, IMF DataMapper, FRED (Brent), NBS, CBN,
  OAGF/FAAC, DHIS2, DHS/NDHS, MICS, UN IGME, UNESCO UIS, NEMIS, ACLED, UCDP GED.

---

## 11. Estimation stack and export contract

- **R for everything** (user's choice): `vars` (VECM/VAR/Johansen), `urca` (ADF/KPSS/PP, cointegration),
  `dynlm` (ARDL), `fixest`, `did` (Callaway & Sant'Anna), `sandwich` (HAC/robust SEs), `lmtest`
  (diagnostics), `Synth` / `coresynth` / `scpi` (synthetic control), `MatchIt` / `cobalt` if matching is
  used. Pinned with `renv.lock` (base spec §10 and §18).
- **Python for pipeline and app only:** Prefect flows, `dbt` orchestration, Streamlit, Plotly, Pillow,
  pandas/requests, sentence-transformers, llama-index, ragas, the OpenAI-compatible Groq client.
- **Export contract:** R writes, per model, (a) a model card JSON conforming to §6, (b) tidy result tables
  (Parquet/CSV) for plots, (c) a diagnostics bundle. The app reads these artifacts and **never fits a
  model at render time** (base spec §18).
- **Environment:** `ds-general` conda env (Python 3.12) for pipeline/app; R 4.5.2 with `renv` for
  estimation. Both pinned and committed.

---

## 12. Hosting, access, and the known cost failure mode

- **Access (user's choice):** public link, no gating. Dashboard on Streamlit Community Cloud; warehouse on
  Neon Postgres (pgvector shares the 0.5 GB); embeddings local; LLM on Groq free tier.
- **Known failure mode, stated openly:** the Groq free tier allows roughly 1,000 requests/day on
  Llama 3.3 70B. A genuinely public, ungated chat link will exhaust that and answers will start failing
  for later visitors. **Mitigations to implement anyway:** a cached answer layer for repeat questions, a
  visible quota indicator, and a graceful degrade that serves the retrieved model card (with intervals and
  assumption text) when the LLM call fails — so the page never shows a dead chat box.
- **Monitoring:** Grafana Cloud (10K series, 50 GB logs) plus GlitchTip (3K events/month) for error
  tracking, including LLM failure rates and RAGAS scores.
- **Exit hatch if outgrown:** Oracle Cloud Always Free (4 ARM cores, 24 GB RAM, permanent) with the same
  stack, removing the shared-compute and quota constraints.

---

## 13. Reproducibility rules (base spec §18, retained)

All pipelines and R scripts versioned in git · dbt models documented per-model, docs site on GitHub Pages ·
every view reproducible from `vintage_date` + anchor config alone · anchor changes (e.g. an NDHS revision)
logged in `metric_anchor` with a new vintage · adjusted estimates stored as tables, never computed at
render time · R pinned by `renv.lock` · Python pinned by requirements/pyproject · **single source of
truth:** the dashboard, the model cards and the Q&A all read the same exported artifacts, so a number
cannot differ between the chart and the chat answer · RAGAS evaluation in CI on a fixed question set,
scoring faithfulness, answer relevance, context precision, context recall.

---

## 14. Why this is defensible to a skeptical reader ("Q1-worthy" in spirit)

The project is not a journal submission (the interview confirmed that), but it should survive the
questions a journal referee or a hostile reviewer would ask:

| Likely challenge | The project's answer |
|---|---|
| "Five presidents is not an identification strategy." | Conceded in the app, in plain text. Power is added where data allow (state panel, policy events, donor pool); the national time series is labelled as association with intervals. |
| "You picked the specification that suited the story." | Specification curve over the full grid, with the count of supporting specifications and the preferred spec marked. |
| "Oil prices explain everything." | Oil is interacted with administration dummies rather than partialled out, per base spec §9, so differential response is estimated rather than assumed away. |
| "Your data are revised and rebased." | Vintage tracking, anchor logging, imputation flags rendered on the chart, and a named data-vintage timestamp. |
| "Where is the causal claim actually identified?" | Every estimate carries a design label (A/B/C), a named assumption, and its placebo/permutation evidence. |
| "The Q&A is a chatbot making things up." | Answers are constrained to retrieved model artifacts, pass a post-check for interval + assumption + citation, and refuse when no model exists; RAGAS scores published in the methodology page. |
| "I can't check any of this." | Code, derived aggregates, model cards and acquisition instructions are public; restricted raw data is substituted per §10 and the restriction is documented, not hidden. |

**Honest limits to state prominently, not bury** (base spec §9 and §20): five administrations and ~26
annual observations; wide intervals expected; heavy mediation by state governments, oil cycles, donor
funding and inherited conditions; the dashboard shows confounders rather than removing them; earlier data
regimes (pre-2000 index anchor) and revision cycles limit comparability; and the whole exercise reports
adjusted associations and design-supported effects, never unconditional causal facts.

---

## 15. Open decisions remaining

1. **Exposure metric for Family A** — FAAC per capita vs oil-revenue share vs FX exposure of the
   consumption basket. Determines what "dose" means and whether the design is believable.
2. **Final donor-pool list for Family C** after pre-fit screening, and the fit threshold.
3. **Which outcomes get a state-level panel** — health and education series are thin at state level;
   security (ACLED) and fiscal (FAAC) series are richer.
4. **Frequency choice** for the state panel — monthly maximizes N but imports interpolation noise.
5. **Whether Tier 2 (inherited-conditions flag) is displayed as its own model family** or only as a
   specification-curve axis.
6. **Refresh cadence** — base spec §13 monthly flows are retained, but the causal registry may be cheaper
   to refresh quarterly. Decide before wiring Prefect.
7. **Cached-answer layer** — implement at launch, or only after the first quota exhaustion.
8. **Portrait assets and licensing** (base spec §20) — public-domain sourcing still unresolved.
9. **Maintenance ownership** — who re-runs the registry when a source revises data.

---

## 16. Build sequence (analysis layer first, UI later — user's choice)

**Step 0 — data spine.** Reconcile the metric catalog (§6 of base spec) with the state-level series that
Families A and C need; decide frequency; write the acquisition scripts and the licence notes. Nothing
downstream can be honest until the data grain is settled.

**Step 1 — one credible end-to-end slice.** Family A, one shock (2023 subsidy removal and naira float),
one outcome, one model, full rigor floor (intervals, pre-trends, permutation, sensitivity, DoF, named
assumption), exported as a model card. This is the checkpoint — if the slice cannot be made defensible,
the remaining families will not save it.

**Step 2 — remaining design families.** Family B (VECM/ARDL with the oil interaction), then Family C
(synthetic control with pre-fit screened donors), each with its own diagnostics and card.

**Step 3 — registry expansion.** Party/tenure effects across all four domains (health, education,
security, economy), stratified by tenure (PDP first/second term, APC first/second term), attaching the
§6 metric catalog outcomes and their direction labels.

**Step 4 — specification curve.** Fit the full grid over axes (family, tier, covariates, lags, windows,
imputation handling, anchor, donor pool) and render the distribution.

**Step 5 — RAG layer.** Build the pgvector corpus from the registry + methodology + data dictionary +
limitations; wire LlamaIndex + Groq; implement the post-check and refusal template; add RAGAS to CI.

**Step 6 — the app.** Compare (base spec §8 chart, unchanged), Models, Ask the data, Methodology,
Data & vintage; reading-level toggle; footer and banner honesty layer.

**Step 7 — hardening.** Cached answers, quota indicator, graceful degradation, monitoring, docs site,
public repo hygiene (no restricted raw data), methodology page in full.

**Deferred:** Tier 4/5 of the base spec are now in. Still deferred — cross-country institutional
comparison as a contribution in itself, sub-monthly refresh, user accounts, and any use of the estimates
for advocacy rather than explanation.

---

## 17. Definition of done

- A public URL where a stranger can open the app, read the chart, open a model card, and ask a causal
  question and receive an answer carrying an interval, a named assumption, and a citation.
- A model registry in which **every** card satisfies all six rigor-floor items (§7), machine-readable per
  §6, and regenerated from a single pinned pipeline.
- A specification curve over the full grid, published with the preferred specification marked.
- A methodology page stating each design, its cointegration/diagnostic results, its DoF cost, its
  limitations, and the RAG scope with RAGAS scores.
- A public repo that reproduces every published number from code plus the user's own credentials, with
  restricted sources substituted or explicitly gapped, and no restricted raw data committed.
- A chat layer that demonstrably refuses rather than guesses: off-registry questions return the refusal
  template plus the nearest answerable questions.

---

## 18. Research-pending note

Web search and URL retrieval were unavailable during this interview (both providers returned errors), so
the methodological references above (staggered DiD estimators, synthetic control inference, sensitivity
analysis) come from domain knowledge rather than verified sources. Before any methodology page is written
for public consumption, the citations and the estimator-version details must be verified against primary
sources. Recorded here so this is not mistaken for a verified literature review.
