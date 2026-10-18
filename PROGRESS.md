# Progress log — causal-presidents-regime-Naija

**Last updated:** 2026-10-18 (sixth session) · **Stage:** 8 of 8, begun — the registry the app will read
exists: 36 cards, **2 carrying a published number and 34 carrying a reason**, the design-level results on
the index, **plus Stage 8b's tenure-timing artifact** · **verified by `scripts/verify.sh` at vintage
2026-10-18**: 10 verifiers, 0 failures, 41 registry documents schema-validated

**This session, in one line:** two things were built — **the transition event study** (`docs/events.md`:
did conflict move after each swearing-in?) and **a widened Design C donor pool** (`docs/design-memo.md` §4:
13 → 99 candidates, which took the design from `infeasible` to passing its pre-fit gate on `u5mr`). Both
were declared before they were fitted, both are independently verified, and both changed a published
verdict — which is why the whole chain was re-run at the new vintage rather than left describing the old
one.

**One-line status:** specification complete; ingestion working and provenance-verified on **five**
sources — **203 payloads**, 0 orphaned files — the newest being **UCDP GED**, whose bulk archive turned
out to be keyless (C-45), so the state-attributed security outcome exists. **Stage 6 has published its
first estimates** (`docs/estimates.md`, `registry/estimates/2026-10-17/`): the fiscal transmission
channel is estimated (**a 10 % Brent move reaches the states as ~5 % more money two to three months
later**, C-48), and the state dose-response question is **estimated but not identified** (C-47) — with the
numbers and the failing check both on the record. Ingestion, plus the older status: the FAAC monthly
disbursement workbook — **the fiscal dose is landed and gated** (174 documents, 114 months × 36 states,
2016-12 → 2026-06; 37 series through the Stage 3 gates with the result travelling on the panel); the
causal-graph (DAG) assumption layer is built — 36 graphs (12 outcomes × 3 identification designs); Stage
3's five quality gates run over all **242** landed series (60 `ok`, 182 `flagged`, 0 `empty` — the FAAC
dose and the UCDP scopes are flagged on movements the whole panel shares); Stage 4's analytical base
exists — one monthly table, **8,350 rows (25 metrics × 334 months, 1999-01 → 2026-10)**, held by 136 data
tests; and **Stage 5 has decided what the data can support before anything is estimated**. Every one of
the **36 (outcome × design) cards carries a pre-check verdict and none passes** — 15 fail, 7 degraded,
14 not attempted, **re-run at vintage 2026-10-17** after the security landing. The totals have never moved
while the reasons did: Family A is still dropped, now because its dose is absent **on the per-capita axis
the estimand is written on** (the nominal dose is landed and gated) rather than for want of an outcome;
Family B is degraded (annual grain, FAAC present as data but absent from the catalogue, a 38–99 SD
detectable effect); Family C is infeasible (no convex combination of the 13 donors tracks Nigeria). **No
credential gates anything now** — FRED's key is set, UCDP's archive is keyless, and ACLED is simply not
wired. The recurring constraint is the one Stage 4 measured: **the monthly spine is only 16.2 % observed**,
and on the native grain the study is ~26 annual observations.


**Last action (2026-10-18, fifth session): Stage 8 — the registry. The app's data contract exists, and it
carries two numbers, not twelve.**

Stage 9 has to be buildable without opening R (PHASES.md Stage 8), so every number the app can show has to be
on a card, beside the assumption it rests on, with the artifact it was copied from named. Stage 6 published
12 specifications and the registry has 36 cards — and the two do not line up:

- **2 cards carry a published number, 34 say why not**, and the ratio is enforced rather than reported. Both
  Design A cards that can carry one do (fatalities +0.4793, incidents +0.5460, each with its interval, its
  `estimated_not_identified` verdict and the check that decided it); the third Design A specification lives
  on an outcome with no card (`fatalities_civilians` is a UCDP item inside the `fatalities` outcome) and is
  carried on the index as a declared gap rather than dropped (C-55).
- **No Design B card carries a number, and that is the point of the layer.** Stage 6's nine B specifications
  measure the **national FAAC channel**; on every B card FAAC is a *mediator* node, not the outcome. The
  result is published once, on the index, with `result_is_card_level: false` — showing it nine times would
  have been the most misleading thing this layer could do.
- **Every card with no number names a reason from a closed set** — `outcome_series_absent` (12),
  `no_specification_declared` (10), `design_result_is_channel_level` (9), `design_not_run` (3) — so the
  absence of an estimate is never silent, and the verifier recomputes which reason each card should carry.
- **The index no longer claims the registry holds no estimates.** Its `layer` string said exactly that until
  this stage; the app would have read the strongest claim in the repository and been wrong.
- **The engine found the omission before publication.** The first assembly wrote 2 of 3 Design A numbers and
  reported success, because the declared expectation counted *published specifications* rather than *cards*.
  The count that matters is now declared separately and checked in both directions (S8-02, C-55).

**Current action (2026-10-18, sixth session): comparing tenures, and the donor pool that unblocked Design C.**

Two builds, both declared before anything was fitted, and both because the previous session's write-ups ended
with a stated next step rather than a silent gap.

- **Stage 8b — the transition event study** (`analysis/specs/events.yml`, `analysis/R/06_events.R`,
  `registry/schema/events.schema.json`, `tests/verify_events.py`, `docs/events.md`). The tenure question needs
a counterfactual and has none; its **timing** half is answerable on the one monthly outcome. Four in-window
transitions, 96 pre-months each, post windows of 12 and 24 months truncated at the successor, inference by
**exhaustive placebo assignment** over 58 eligible months — enumerated, not sampled, so there is no seed.
**2 of 8 event-outcome cells survive both the placebo and the pre-trend check** (2010 incidents +391 %,
2023 fatalities +77 %, each p = 0.017, the floor at 58 placebo months); four fail the pre-trend placebo,
including the largest shift in the series (2015 fatalities −67 %); one event cannot be checked at all and
says so. **No party comparison is published** — two events against two events has no sampling distribution.
- **Design C's donor pool, widened from 13 countries to 99** (`ingestion/flows/pull_worldbank_donors.py`,
  `analysis/specs/diagnostics.yml`, `analysis/R/02_diagnostics.R`). Stage 5's `infeasible` verdict was always
about the pool, so the pool was rebuilt on declared groups (West African neighbours, oil exporters, African
comparators, large lower-middle-income countries) screened on oil dependence, region/income band and
coverage. The gate moved: **`u5mr` passes 3 of its 4 runnable windows** (ratios 0.0014–0.0042 against the
declared 0.10), `gdp_growth` 1 of 4, `cpi_yoy` 0 of 4 — under a rollup rule that is now **declared** as a
strict majority of the runnable windows, where the old rule ("any window passes") was undeclared and would
have credited `gdp_growth` on one window of four (S5-12). Design C is still not estimated: the estimator and
the placebos are the next build, and the pass carries the warning that a 99-donor simplex can fit almost any
pre-period (C-59).
- **Everything was re-run at vintage 2026-10-18** because the donor vintage changed the base, and the
discipline is that a published number names the vintage it was computed on: quality (672 series now, up from
242), dbt, Stage 5, Stage 6, Stage 7, the registry and Stage 8b. **All 10 verifiers pass, 41 registry
documents validate against their schemas, and the two break-test suites catch all six mutations they apply**
(5 on the events artifact, 1 on the newly declared Design C rollup).
- Three defects were found by the chain rather than by review and are recorded with their causes: the
**`dataset_id` join** that silently emptied the donor panel under a green `dbt build` (C-61), a Stage 3
**coverage count** that described a request shape rather than the data (S5-14), and the **undeclared
gate rollup** itself (S5-12). Each one is the same failure class this project keeps finding: a claim that was
true when written and quietly false later.

**Previous action (2026-10-18, fourth session): Stage 7 — robustness and the multiverse. The grid was fitted,
and it turned one design's verdict into a different one.**

Stage 6 published two estimates. Stage 7 asks whether either survives the choices it did not pin down:
**105 specifications** fitted and published (81 Design A, 24 Design B), every one declared in
`analysis/specs/robustness.yml` before any of them ran, with the specification curve drawn and the support
counts computed rather than typed.

- **Design B survives, with a named weak part.** All **24 of 24** specifications are positive and all 24
  intervals exclude zero; the pre-registered cell reproduces Stage 6 to 4.3e-12. Its *magnitude* is a
  choice (the coefficient at h=2 spans +0.3968 to +2.3976, and the spread is mostly the shock definition —
  a three-month average is a smoother regressor) and its **timing is weaker than its sign**: the in-time
  placebo, 48 shifted alignments, returns **p = 0.0625**. That number is published as a bound rather than
  widened until it passed (S7-04).
- **Design A does not survive, and that is the finding.** **45 of 81 specifications are positive and 36
  negative.** Five axis levels have a majority on the opposite side of zero from the pre-registered
  specification — including the preferred `outcome = fatalities` level itself (14 of 27), and 6 of the 105
  specifications sit inside the declared ±0.02 near-zero band and are counted as such — and the sharpest
  is the **dose lag**: with the dose lagged one month and state and month effects, the estimate is negative
  in all three windows while the pre-registered same-month estimate is +0.479. The 36 leave-one-state-out
  refits do **not** flip the sign ([0.1234, 0.6254], 0 flips), so the fragility is the identification and
  the timing rather than one unit; dropping Delta/Bayelsa/Rivers raises the estimate to 0.6663 (C-47 restated).
  Stage 6's `estimated_not_identified` was therefore the *milder* of the two true statements: this number is
  not a direction (C-50).
- **What the grid cannot vary is declared rather than dropped.** Four of the design spec's eight axes have
  no live variant here (imputation handling, index anchor, donor pool, event window) and each carries its
  reason; the **per-capita dose axis is live in principle and unbuilt in fact** — `d1_faac_per_capita` is
  0 of 12,358 rows because X-09 is unmade — so the curve is a curve over the nominal dose and says so.
- **Sensitivity, reported in the case it is actually in.** Oster's delta is negative for both designs
  (Design B −44.04: the controls move the estimate away from zero; Design A's linear analogue −1.53: the
  control set flips its sign, −0.1023 to +0.0882), so the artifact carries `delta_interpretable`, a
  sign-flip flag and beta* at delta = 1 rather than a bare number that reads like a certification.
  **Rosenbaum bounds are declared not applicable** (continuous treatment, no matching) with the reason, and
  the HAC bandwidth moves the Design B interval only from 0.1609 to 0.1723, so its width is the sample.
- **The engine found a real bug and the pre-registered check caught it before publication.** `data.table`'s
  `shift(x, -h, type = "lead")` is a *lag* — the sign and the type cancel — and the first grid run produced
  a Design B coefficient 0.408 away from Stage 6's. The engine refuses to write when the pre-registered cell
  disagrees with the estimate artifact, which is exactly the class of error that check exists for (C-52).
  Two more were found the same session: a rank-deficient state-slope design made the verifier's clustered SE
  disagree by 97 % while the coefficient agreed to 1e-10, and `lm`'s silent drop of the first lagged month had
  to be reproduced explicitly so the two implementations compare the same sample.

**Previous action (2026-10-17, third session): the verification became one command, and the documentation was
put back onto the artifacts.**

What this session found is that the project's *claims* drifted faster than its artifacts: three of them
(C-42, C-44, C-49) were true when written and silently false later, and the verifiers were only ever run
by hand — so a green verifier on disk was a convention, not a check.

- **`scripts/verify.sh` and `.github/workflows/verify.yml`.** One command runs compile, the artifact
  contracts, acquisition when nothing is landed, Stage 3, dbt, Stage 6 and all seven verifiers, and returns
  the first failure's status; CI runs it from `requirements.txt` on a clean runner. Run today: **exit 0 —
  `all checks passed`**.
- **`scripts/validate_artifacts.py`, the contract test.** Every landed payload must be readable by the
  reader its **extension** declares — an unregistered extension fails rather than being skipped — the
  newest gate report's own label must be a date and agree with its directory, Stage 5 must describe that
  report, and every registry JSON must validate against its schema. Today: 203 payloads, 37 documents, 0
  unreadable. Three mutations confirmed each check can fail, on the real raw layer (§4).
- **C-49 — two numbers in the Stage 5 report were typed into the prose, and one was worse than stale.** It
  printed the *modal* dose status under the words "on every row", so a panel that is now 4,104 observed
  rows out of 12,358 still described itself as entirely declared gaps; the observed share was the literal
  "10.1%". Both are now computed (`grain_decision.observed_fraction`), the report was regenerated at
  vintage 2026-10-17 and the 36 cards re-emitted — and each card's own `estimate.note` was fixed too, since
  it promised estimates from a stage that has already run (G-07, narrowed).
- **The documentation was put back onto the artifacts**, and checked by a script against
  `data/analytics.duckdb`, the quality report and `estimates.json` rather than by eye: 7,682 → **8,350**
  rows, 23 → **25** metrics, 92 → **136** data tests, 125 → **242** gated series, 3 → **5** provenance
  sources, 10.1 % → **16.2 %** observed, and "five published estimates" → the **12 specifications** that are
  actually in `estimates.json`. Dated session logs and decisions were left as written; only the
  current-state claims moved.

**Previous action (2026-10-17, second session): the security outcome landed, and Stage 6 ran.**

The blocker that mattered was a credential — `fatalities` and `incidents` were recorded as needing a UCDP
token or an ACLED OAuth app (C-14/C-13), and Family A had no state-attributed outcome at all. Both halves
turned out to be one probe away: **UCDP's API is token-gated and its bulk archive is not** (401 on three
API versions, a plain 200 on a 29 MB zip), and it is CC-BY, unlike ACLED. So the security domain stopped
being blocked rather than being unblocked, and the state-month outcome exists.

- **Landed and gated**: 7,418 Nigeria events, 1990-09 → 2024-12, state-attributed via `adm_1`. 117 new
gated series (38 scopes × 3 items + national), the national series on the monthly spine from 1999-01, and
the state outcome on the panel — with `security_status` distinguishing a **recorded zero** (80 % of
state-months) from a month the archive does not cover at all.
- **A decision the landing forced**: a count series must never be interpolated. The spine would otherwise
  have carried **25 fabricated fatality-months** (1999-2009) between months the archive covers and months
  it does not (S6-05).
- **Stage 6** (`analysis/R/03_estimate.R`, 12 specifications, every number recomputed by
  `tests/verify_stage6.py` to within 1e-12): Design B is **estimated** — cumulative elasticity of state
  FAAC to a Brent shock of −0.160 at h=0, **+0.518 at h=2**, +0.470 at h=3, with a 6-month lead placebo of
  +0.095 — and Design A is **estimated, not identified**: the dose's post-fixed-effect variation is 0.50 in
  the oil-producing states against 0.11 elsewhere, and 8 of 60 mis-timed doses return an estimate at least
  as large (C-47). Both are published, each with the check that decided it.
- **Stage 5 re-ran** on the new base: the same 0-of-36 verdicts, with the reasons recomputed — the outcome
  blocker is now cleared and the remaining one is the dose axis plus the population denominator. The cards
  carry that, and the one stale sentence they carried ("missing a state-attributed outcome", on the same
  page as 21,238 outcome values) is now derived from the artifacts rather than typed beside them.

**Previous action (2026-10-17, first session): Stage 5 re-run — the dose's checks recomputed on the axis the estimand is
actually written on.**

The registry had drifted from the base and the drift was the kind that flatters: `tests/verify_stage5.py`
compared the recorded Stage 5 artifact against the panel and **failed** — `dose_status_values`
`{'declared_gap': 12358}` in the artifact against `{declared_gap: 8218, observed: 4104, not_covered: 36}`
in the base — because the artifact was computed before the FAAC dose landed. Its Family A cards still read
"dropped — 0 of 12,358 dose values present", which had stopped being true on 2026-10-16.

- **The fix is a re-run, not a re-word.** `analysis/R/02_diagnostics.R` recomputes everything from the
  base and stamps the artifact with the data vintage, so the re-run is what makes the registry honest.
  It now writes `registry/diagnostics/2026-10-16/` (the vintage of the Stage 3 report it reads) and
  rebuilds all 36 cards through `01_build_dags.R`.
- **The dose is measured on the specified axis and on the others, separately.** A new declared field,
  `dose.specified_axis: D1`, decides the family; the nominal FAAC column is a measured axis, not a
  substitute. Result: `D1=absent, D1_nominal=pass, D2=absent, D3=not_built`, and Family A stays
  **dropped** — for `specified_dose_axis_absent:D1 and no_state_attributed_outcome` instead of "no dose
  series". A dose that exists on the wrong axis cannot turn the gate green by proxy, and the card says
  which axis it is waiting on (S5-10).
- **The Family A card text is now derived from the dose block rather than typed next to it.** It had been
  hard-coded as "no dose series has landed" — true when written, false within a day of the parser
  landing, and invisible to every check, because a sentence cannot fail. The same defect class as C-42:
  an assumption about the data's shape that the data eventually violated quietly.
- **A second silent-skip bug was found in the same run and fixed.** Stage 5 picks the Stage 3 report to
  describe by globbing directories that match a **date** (`^[0-9]{4}-[0-9]{2}-[0-9]{2}$`). The report's
  vintage had just become `2026-10-16-correction` (the FAAC raw vintage's correction label), so the glob
  skipped the newest report and Stage 5 described the previous one — silently, and while writing its
  output into that older vintage's directory (C-44). Fixed on both sides: the Stage 3 report's own label
  is a date again (the raw correction label still travels per source in `source_vintages`), and the
  verifier now reads the latest diagnostics vintage instead of a hard-coded one (S4-20).
- **The verdict totals are unchanged** — 15 fail, 7 degraded, 14 not attempted, 0 of 36 pass — and that is
the result: the dose's arrival changed *why* an estimate is not yet possible, not whether one is.

Immediately prior (2026-10-17) — **the FAAC dose through Stage 3, and a verifier that had been broken by
the landing without saying so.**

Stage 3 was the last thing standing between the dose and its being usable, and running it found two
things, one of which was a defect of mine:

- **The gate flow and its verifier both died on the FAAC payloads, silently.** Both walked `data/raw` and
  assumed every page file was JSON — true while every source was an API, false the moment 174 PDFs and
  spreadsheets landed. `tests/verify_quality.py` raised `UnicodeDecodeError` on the first byte of a PDF,
  and the gate flow had the same line and would have died identically, leaving the newest source in the
  raw layer with **no gate result at all** while the report on disk still read 88 series. That is the
  exact failure the Stage 3 exit criterion exists to prevent, seen from the other side (C-42).
- **Document sources are now gated from their parsed artifact**, declared in `quality.yml`
  (`document_sources`), because a PDF has no series until the parser reads it — and gating the parsed
  table means the gate and Stage 4 read the *same* series rather than two derivations of it. The
  publisher preference is read from `harmonisation.yml` for the same reason. 37 rows: 36 states plus the
  national aggregate, on the argument that a national series passing while one state's column is broken
  leaves the dose ungated where it is actually used (S4-19).
- **The dose is gated and the gate does not pass it quietly.** All 37 series come back **`flagged`**: the
  distribution moves more than the declared 50 % in a month nine or ten times per state, and most of
  those months fire at **all 36 states at once** (2024-12 at 36 of 37, largest move +606 %; 2021-07 at
  37). A month flagged in every unit is a movement of the distribution, not a per-state extraction
  error — and it is corroborated independently, since every document reconciles against its own
  published Total row. So the flag is carried, not resolved: `state_panel.dose_gated` is `true` with
  `dose_gate_status = 'flagged'`, read from the report, and the spikes are deliberately left
  **unadjudicated** because a verdict without evidence would be worse than the prompt (C-43).
- **The panel can no longer claim a gate it does not carry.** `dose_gated`/`dose_gate_status`/
  `dose_gate_vintage` come from the quality report by join, and a new dbt test fails if they disagree — or
  if the join matches nothing, which is the failure mode that makes every row read "ungated" while staying
  internally consistent. The test was break-tested against a doctored panel (a state that loses its gate
  result, a state claiming a status it lacks, an empty join, the FCT wrongly gated): it catches all four
  and is clean on the real table.
- **A fresh number for the report:** Stage 3 now covers **125 series — ok 60, flagged 65, empty 0** (242
  after the UCDP scopes landed on 2026-10-17),
  up from 88, with `tests/verify_quality.py` recomputing every one of them independently (and checking
  that every one of the 174 landed documents is referenced by the parse).
- **What this does not do.** It does not put FAAC on the metric spine. That needs a declared
  monthly-to-annual aggregation and a national outcome decision — a different question from whether the
  series has been checked, which it now has. S4-17's blocker is narrowed to
  `faac_gated_but_too_short_at_outcome_grain`, and X-09 (the population denominator) is still open.

Immediately prior (2026-10-16) — **the FAAC fiscal dose — acquisition, parser and dose.** Stage 5 named the NBS
FAAC parser as the single action that moves the most, and this is it. The monthly disbursement workbook is
acquired from **both** of its publishers, parsed into per-state items, and carried into the base as the
exposure Family A's estimand is written on:

- **174 documents landed and parsed** — 83 OAGF PDFs (2019-04 → 2026-06) and 91 NBS XLSX reports
  (2016-12 → 2024-07), 114 distinct months. Every document yields all 36 beneficiaries, and **every
  document reconciles against its own published Total row**; the parser refuses a month that does not.
- **The acquisition corrected a Stage 1 finding.** PHASES.md recorded the OAGF portal as unreachable (20s
  timeout) and called for a source substitution. The portal is still unreachable, but the OAGF publishes
  the monthly PDFs from its own site, so **D1's primary source was recovered rather than substituted** —
  and it is the longer of the two series.
- **The dose column is the one every layout agrees on**: `gross_total` (statutory allocation + the 13%
  derivation share). Three other candidates were rejected *against the documents* — the full-share column
  exists only from 2024 and its declared column formula does not survive extraction on every layout, so
  reading it back was wrong by hundreds of millions on several months rather than failing (S4-13).
- **The cross-check did not corroborate the way the design assumed, and that is now recorded rather than
  smoothed.** 2,124 of 2,160 overlapping state-months (98.3%) agree to within a naira and 59 of the 60
  overlapping months agree at every state — but **2023-04 disagrees at every one of the 36 states**
  (~1.83×), while both documents reconcile to their own Total rows. The dose's level is therefore
  publisher-dependent for that month, so the publisher is a column and the choice is a robustness axis
  (C-39).
- **A silent loss was found and closed.** The 2022 OAGF layouts publish a 13% derivation column whose
  header the PDF text layer interleaves (`13% SHAR(EN OEFT D)ERIVATION`), so it never resolved and eleven
  months were missing a component the documents do carry. The dose is unaffected (`gross_total` resolves
  and reconciles everywhere), but header cells that do not resolve are now **collected per document and
  persisted** instead of dropped — 541 of them, enumerated in the parse report (C-40).
- **What this does not fix, stated plainly.** The series begins 2016-12, so at the annual grain the
  outcomes are on it is 10 calendar years against the ~20-observation floor Johansen needs, and it has no
  Stage 3 gate — so it is **not** on the metric spine and the Tier-3 system is still not estimable as
  written. The blocker moved from "FAAC is absent" to "FAAC is ungated and short" (S4-17, C-41) — a
  blocker the next day's Stage 3 gate replaced with a narrower one, and the re-run below recorded that
  (S4-19, S5-10).

Immediately prior (2026-10-11) — **Stage 5, pre-analysis diagnostics and design validation.** Built the
engine that decides what the data can support *before* anything is estimated, and dropped designs on
the record rather than after an estimate looked inconvenient. The stage turned several expectations
over:

- **Nothing clears its gate.** Of 36 (outcome × design) cards, **0 pass** — 15 fail, 7 degraded, 14 not
  attempted. The state dose is empty (Family A dropped); the national VECM family runs at **annual**
  grain without FAAC (degraded); and **no convex combination of the 13 donors tracks Nigeria's
  pre-treatment path**, so the synthetic control is reported infeasible rather than shipped weak.
- **The base-spec Tier-3 design can detect almost nothing.** The mandated `oil × tenure` interactions
  are nearly collinear with the tenure dummies themselves (R² 0.997–0.999), inflating the minimum
  detectable effect from ~2 residual SDs to **35–99**. That is a property of the *design matrix*, not
  the data, and it is written down before any estimate exists (C-35).
- **A real bug, found by an independent implementation.** `urca::ca.jo` returns its statistics ordered
  r = K-1 … 0; the engine had labelled them r = 0 … K-1, inverting every per-row rank label on every
  Design B card (the *rank* itself, a count of exceedances, was right; the label was wrong). Fixed, and
  the verifier now re-derives the rank from the eigenvalue problem. On the one outcome where the two
  implementations still disagree — `mmr`, whose deciding statistic sits only 8.9 % over its critical
  value — the card carries `rank marginal` rather than claiming certainty (C-36).
- **The estimator the design spec names for the synthetic control lost to a single donor.** `Synth`'s
  default V search returned a fit worse than the best single donor on every window; recorded for Stage 6
  rather than trusted (C-37).

Immediately prior (2026-10-11) — **Stage 4, the analytical base.** Built the dbt project
(staging → analytics) that turns the gated raw layer into the single table the models and the app both
read: `fact_metric`, on a local DuckDB file (`data/analytics.duckdb`, gitignored — reproducible from
`data/raw/` plus `analysis/specs/`). Three substantive results:

- **The base is reproduced, not asserted.** `tests/verify_harmonisation.py` recomputes the entire
  spine from the raw payloads and the declared specs — 7,682 rows compared row for row, every
  `observation_type`, every index value, the administration spine against base spec §7, and the four
  tenure strata — while 92 dbt tests hold the same invariants from inside the build. Twenty guards were
  then mutated to confirm they *can* fail (seven dbt tests and thirteen verifier checks), because a
  green test that cannot go red proves nothing.
- **10.1 % of the base was observed at this vintage** (775 of 7,682 rows; 4,389 interpolated, 2,518 empty —
  the same measure reads 16.2 %, 1,349 of 8,350, after the 2026-10-16/17 monthly landings). That ratio is the
  honest cost of a monthly spine over annual sources, and it settles a question §8 had left open:
  **design B on `cpi_yoy` cannot see the 2023-06 → 2023-12 window monthly**, because the landed series
  is annual and that window contains two observations (C-30). `dim_metric.frequency_gap` flags
  `cpi_yoy`, `gdp_growth` and `unemp` for the same reason.
- **The state panel that will carry the FAAC dose was built complete (37 × 334) with its dose columns
  typed, empty and labelled `declared_gap`, rather than absent and ambiguous** (S4-09). It was the right
  call at the time and the dose landed into it without a schema change — `dose_status` was widened from a
  table-level label to a per-row one when the nominal dose arrived (S4-14).

Immediately prior (2026-10-11) — **Stage 3, the quality gates**: Built the five gates PHASES.md calls "the
honesty chokepoint" and ran them over every landed series. Two of the three headline results are
defects the gates found rather than checks they passed:

- **The study-window floor now exists and is quantified.** An unwindowed scan reports **198 pre-1999
  spike flags**; the windowed report contains none. That closes C-06 and C-21, which had been open
  since Stage 1 (decisions C-26).
- **The gate found a gap in its own specification.** It flagged Nigerian inflation at 2024→2025
  (−10.23 points) and the cause was an undeclared definition break — the NBS rebased the CPI in
  January 2025, the first time since 2009 (C-27).
- **A covariate the designs condition on is contaminated.** `donor_oda` rose **+1006% in 2005** because
  Paris Club debt relief is recorded as ODA. `donor` sits in the adjustment set for designs A and B on
  every health and education outcome, so those designs partially condition on a debt restructuring
  (C-28). This is the most consequential thing Stage 3 produced and it is carried into Stage 5.

Immediately prior: the **FRED key** (account registered, Brent landed at 10,275 rows, `oil` flipped to
*acquired*, taking design C to zero unsourced nodes — C-23…C-25).

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
| `docs/dags.md` | The causal-graph layer: node vocabulary, the three designs as assumptions, every variable's source, and what is still missing | Complete |
| `docs/decisions.md` | Decision log — 40+ dated decisions: framing, method, data, access findings, coverage findings, infrastructure, RAG | Live, updated as evidence arrives |
| `docs/licences.md` | Licence register — redistribution rights per source, plus 5 open licensing questions | Live |
| `docs/data-dictionary.md` | Every column of the analytical base: grain, meaning, imputation rules, vintage conventions and the declared gaps | Complete |
| `knowledge.md` | Agent-facing repo context | Live |
| `PROGRESS.md` | This file | Live |

## 3. Code and data artefacts

| Artefact | What it does | Verified |
|---|---|---|
| `ingestion/clients/provenance.py` | Shared provenance: byte-exact payload storage, sha256, POSIX paths, **credential redaction** | Redaction confirmed |
| `ingestion/clients/worldbank.py` | World Bank acquisition; retries, pagination, row-count assertion, detects the 200-with-error envelope | Working |
| `ingestion/clients/fred.py` | Brent crude (`DCOILBRENTEU`) — oil covariate for the VECM/ARDL family | **Working** (key present) |
| `ingestion/clients/ucdp.py` | UCDP GED fatalities — security domain (CC-BY, redistributable) | **Working** — bulk archive, keyless (C-45) |
| `ingestion/flows/pull_worldbank.py` | Lands a vintage: raw pages + `manifest.json` + provisional `coverage.json` | Exit 0, 22/22 |
| `ingestion/flows/probe_candidates.py` | Reconnaissance: which indicators actually reach the APC era | Exit 0 |
| `ingestion/flows/probe_missing_variables.py` | Reconnaissance: what the causal graphs need that nothing sources | Exit 0 |
| `ingestion/flows/pull_worldbank_donors.py` | The Design C donor panel — 13 countries × 5 screening predictors | Exit 0, 5/5 |
| `ingestion/flows/pull_fred.py` | Lands the oil covariate: Brent crude, daily; refuses to overwrite a landed vintage (X-07) | Exit 0, 1/1 |
| `ingestion/flows/pull_faac.py` | Acquires the FAAC monthly disbursement documents from both publishers (174 PDF/XLSX payloads, 2016-12 → 2026-06) | Exit 0, 174/174 |
| `ingestion/parsers/faac_disbursement.py` | Parses the documents into per-state items and persists the parse report (per-document reconciliation + the header cells that did not resolve) | Exit 0, 4,104 state-months |
| `ingestion/flows/pull_ucdp.py` | Lands the UCDP GED bulk archive — keyless, 28 MB, CC-BY — which is the state-attributed security outcome | Exit 0, 1/1 |
| `ingestion/parsers/ucdp_events.py` | Filters to Nigeria, aggregates to scope × month × item, and carries the 47 unattributed events as their own scope rather than dropping them (S6-04) | Exit 0, 37,734 rows |
| `tests/verify_faac.py` | Re-reads the parsed documents and re-derives the dose, the publisher rule and the cross-publisher differences | Exit 0 |
| `analysis/specs/quality.yml` | Stage 3 gate configuration: study window, thresholds, grains, frozen resample rules, definition breaks, spike adjudications, and the `document_sources` block that gates a PDF/XLSX source from its parsed artifact | 672 series configured |
| `ingestion/quality/gates.py` | The five gates (gap · spike · revision · definition-drift · provenance) as pure functions | covered by `verify_quality.py` |
| `ingestion/flows/check_quality.py` | Runs the gates over every landed series; enforces the exit criterion in code (the multi-country count is per retrieval, C-62) | Exit 0, 672/672 |
| `registry/quality/2026-10-18/` | The vintage quality report — `report.json` + a human-readable `report.md` (older vintages are kept) | 672 series: 357 ok, 313 flagged, 2 empty (Eritrea/Somalia CPI; the donors' 495 country-series are gated like any other) |
| `tests/verify_quality.py` | Recomputes the gap and spike results from the raw payloads independently of the gate module | Exit 0 |
| `tests/verify_provenance.py` | Re-derives every sha256, for every source, and detects orphaned files | Exit 0, 5 sources / 203 payloads |
| `data/raw/worldbank/2026-10-11/` | 22 payloads + manifest + coverage report | Gitignored, never committed |
| `data/raw/worldbank_donors/2026-10-18/` | 60 payloads over 40 requests in **5 chunks of 20 candidates** (99 donors), plus the WAF-split requests, + manifest + coverage | Gitignored, never committed |
| `data/raw/fred/2026-10-11/` | 1 payload (Brent, 10,275 rows) + manifest + coverage profile | Gitignored, never committed |
| `analysis/specs/outcomes.yml` | Outcome registry for the DAG layer — 12 catalogue outcomes with Stage-1 coverage status | 12/12 |
| `analysis/specs/dag_designs.yml` | The three identification designs as node/edge templates, with assumption text | 36/36 instantiated |
| `analysis/R/01_build_dags.R` | DAG generator: acyclicity check → dagitty adjustment set → ggdag SVG → in-figure legibility check | Exit 0, 36/36 |
| `registry/dags/` | 36 DAG cards + 36 SVG figures + index — the assumption layer **and the published results**, i.e. everything the app reads | Verified: 2 cards carry a published number, 34 carry a reason |
| `analysis/specs/registry.yml` | Stage 8's contract: the mapping rule, both of its counts, the cardless specification, the closed reason set, the ordering constraint | 36 cards mapped |
| `analysis/R/05_registry.R` | The Stage 8 assembler: copies the published specification onto the cards it is about, lifts the design-level results onto the index, fits nothing | Exit 0, 2 estimated / 34 explained |
| `tests/verify_registry.py` | Re-derives the mapping and checks every card's number against the artifact it names; fails when a card that should carry one does not | Exit 0 |
| `docs/registry.md` | The Stage 8 output: what the app reads, which cards carry a number, and why the rest do not | Complete |
| `tests/verify_dags.py` | Independent verification of every DAG card (schema, acyclicity, backdoor blocking) | Exit 0 |
| `analysis/specs/harmonisation.yml` | Stage 4's declared rules: spine, annual→monthly alignment, interpolation, the index anchor and its recorded fallback, and the declared gaps | 5 gaps declared |
| `dbt/` | The transformation project (D-05: SQL, never Python): staging → analytics, run into a local DuckDB | 25 models, 4 seeds |
| `dbt/seeds/raw_administration.csv` | Administration spine + term count, base spec §7 | 5 rows |
| `dbt/seeds/raw_metric_catalogue.csv` | The metric dimension's source: label, unit, **direction**, domain, catalogue vs landed frequency, coverage status | 25 metrics, 12 outcomes |
| `dbt/seeds/raw_shock_bands.csv` · `raw_state.csv` | Base spec §8 shock bands · the 37 state-level units | 3 · 37 |
| `dbt/models/analytics/fact_metric.sql` | **The analytical base**: 25 metrics × 334 months with the index, the observation type and the tenure strata | Built, 8,350 rows |
| `dbt/models/analytics/metric_anchor.sql` | The index anchor per metric, naming the rule that produced it | 25 rows (18 fixed, 7 fallback) |
| `dbt/models/analytics/int_metric_monthly.sql` | The spine before indexing: observed / interpolated / unobserved, no extrapolation, no interpolation across a gap | 8,350 rows |
| `dbt/models/analytics/dim_administration_term.sql` | Term-level spans carrying the four LOCKED party-by-tenure strata | 7 terms |
| `dbt/models/analytics/dim_metric.sql` | The metric dimension, with the Stage 3 quality status and definition breaks travelling on it | 25 rows |
| `dbt/models/analytics/state_panel.sql` | 37 × 334 panel: the FAAC dose and the UCDP outcome where their sources cover the month, the rest typed and declared | 12,358 rows, 4,104 doses observed |
| `dbt/models/analytics/fact_donor_panel.sql` | Design C's donor pool, kept off the national spine | 27,352 rows, 99 countries |
| `dbt/models/analytics/faac_state_allocation.sql` | The dose itself: one publisher chosen per state-month by the declared rule, the other measured beside it | 4,104 rows |
| `dbt/models/analytics/faac_national_monthly.sql` | The dose summed over the 36 states — the fiscal transfer channel on a national spine | 114 months |
| `dbt/models/analytics/ucdp_state_month.sql` | The security outcome at state-month grain, `observed` / `not_covered` distinguished | 15,244 rows |
| `dbt/models/analytics/ucdp_national_monthly.sql` | The same archive at national grain, summed over 38 scopes so the country is not the sum of its states | 331 rows |
| `dbt/tests/` | 13 singular tests for what generic tests cannot express: no extrapolation, no interpolation across a gap, the frozen Brent rule, vintage isolation, spine completeness, term coverage, declared gaps | 136 data tests total |
| `tests/verify_harmonisation.py` | Recomputes the whole base from `data/raw/` + the specs, independently of dbt and of the gate module | Exit 0 |
| `analysis/specs/diagnostics.yml` | Stage 5's declared parameters: grain, unit-root reconciliation, cointegration rule, dose thresholds, pre-fit gate, DoF/power, collinearity, candidate windows, design gates | 9 thresholds echoed |
| `analysis/R/02_diagnostics.R` | The Stage 5 engine: integration order, Johansen, shock visibility, dose validation, pre-fit QP, DoF/power, collinearity — then attaches a verdict to every card | Exit 0, 36/36 cards |
| `registry/diagnostics/2026-10-18/` | The Stage 5 result, re-run over the widened donor pool — `diagnostics.json` + a human-readable `report.md` | 0 of 36 pass (15 fail, 7 degraded, 14 not attempted); **Design C: `u5mr` pass (3/4 windows), `gdp_growth` 1/4, `cpi_yoy` 0/4** |
| `docs/design-memo.md` | The Stage 5 output: per outcome, which family is credible, which is not attempted, and the diagnostic that decides it | Complete |
| `analysis/specs/estimation.yml` | Stage 6's declared parameters: the 12 specifications, horizons, HAC lags, the placebo and null designs, and the rule that decides a design's verdict | 12 specifications |
| `analysis/R/03_estimate.R` | The Stage 6 engine: local projections, PPML count models, the placebo, the time-shift null, the power bound | Exit 0, 12 specifications |
| `registry/estimates/2026-10-18/` | The Stage 6 result — `estimates.json` + a human-readable `report.md`, each estimate carrying the check that decided its verdict | 12 specifications: 3 Design A outcomes, 9 Design B horizons; Design C's reason rewritten from "the pool fails" to "the pool passes on `u5mr`; the estimator and its placebos are next" |
| `docs/estimates.md` | The Stage 6 output: what the data can answer, what it cannot, and the check behind each verdict | Complete |
| `tests/verify_stage6.py` | Recomputes every coefficient, sample size, horizon and verdict from the base to within 1e-12 | Exit 0 |
| `analysis/specs/robustness.yml` | Stage 7's declared multiverse: the 4 live axes per design, the windows, the two Oster analogues, the placebo and leave-one-out rules, the support-count rule, and the 6 axes that are dead or unbuilt with their reasons | 105 specifications declared |
| `analysis/R/04_robustness.R` | The Stage 7 engine: fits the whole grid, computes the sensitivity checks, the support counts and the majority-flip rule, draws the specification curve | Exit 0, 81 A + 24 B |
| `registry/robustness/2026-10-18/` | The Stage 7 result — `robustness.json`, `report.md` and `specification_curve.svg` (two panels, axis strips beneath, pre-registered cell marked) | 105 specifications: A 45 positive / 36 negative, B 24 positive; 6 inside the declared ±0.02 near-zero band |
| `analysis/specs/events.yml` · `analysis/R/06_events.R` · `registry/events/2026-10-18/` | **Stage 8b — the transition event study**: 4 in-window transitions on 312 months of UCDP conflict, 32 specifications, exhaustive placebo inference over 58 eligible months, a pre-trend placebo, a reporting-divergence check and the party split as description | 2 of 8 cells `shift_detected`, 4 `not_interpretable_pre_trend`, 1 event `check_not_available`, 1 `no_shift_detected` |
| `registry/schema/events.schema.json` · `tests/verify_events.py` | The Stage 8b contract and its independent verifier (re-fits all 32 specifications and re-enumerates the placebo distribution; worst HAC SE gap 0.002 % against a stated 5 % allowance) | Exit 0 |
| `registry/schema/robustness.schema.json` | The Stage 7 contract: every row carries its axis levels, its interval and its sign; the preferred cell is flagged; an unbuilt axis is listed rather than omitted | Validated by `validate_artifacts.py` |
| `tests/verify_stage7.py` | Re-fits all 81 PPML specifications (statsmodels, not fixest), all 24 local projections, 36 leave-one-state-out refits and 48 placebo alignments, and recomputes both Oster bounds and every count | Exit 0, worst coefficient gap 6.5e-9 |
| `docs/robustness.md` | The Stage 7 output: what survived, what did not, and the checks behind each | Complete |
| `tests/verify_stage5.py` | Recomputes every Stage 5 headline number from the base in numpy/scipy and re-derives the design verdicts from the card statuses | Exit 0, 1 warning |
| `scripts/validate_artifacts.py` | Contract test on names and shapes: every landed payload readable by the reader its **extension** declares, the newest gate report date-labelled and self-consistent, Stage 5 describing it, every registry JSON schema-valid | Exit 0 (1 check skipped without `data/raw`, which is the CI case) |
| `scripts/verify.sh` | One command that runs the whole chain — compile, artifact contracts, acquisition when nothing is landed, Stage 3, dbt, Stages 6 and 7, every verifier — and returns the first failure's status | Exit 0 |
| `.github/workflows/verify.yml` | CI: installs the pinned requirements and runs `scripts/verify.sh` on a clean runner (the R engines are skipped there; every verifier still runs) | Wired, runs on push |
| `requirements.txt` · `requirements-dev.txt` | The pinned Python dependencies (runtime · verification), beside the `ds-general` conda environment rather than replacing it | Pinned |
| `docs/data-dictionary.md` | Every column of the base, documented — Stage 4's exit criterion and the Stage 0 data dictionary that was never written | Complete |

## 4. Verification evidence

Commands and their observed results — these are measurements, not assertions. Every exit status
below was captured directly, not inferred from filtered output.

**Vintage 2026-10-17 (current, second session) — the UCDP landing and Stage 6:**

```
pull_ucdp.py               -> exit 0  1/1 — GED 25.1 bulk archive, 28.0 MB, sha256 e256f1fb20a5,
                                      keyless; 7,418 Nigeria events, 1990-09 -> 2024-12,
                                      38 state labels, 46 events with no state
ucdp_events.py             -> exit 0  37,734 staging rows = 38 scopes x 331 active months x 3 items;
                                      totals 73,822 fatalities, 7,418 incidents, 19,538 civilians;
                                      parse report carries the 81 inactive months and the 47
                                      unattributed events
check_quality.py           -> exit 0  242/242 series gated (60 ok, 182 flagged, 0 empty); the 117
                                      new ones are the UCDP scopes, flagged on monthly volatility
                                      as any count series is; 0 omitted, exit criterion enforced
verify_quality.py          -> exit 0  242 series, exit criterion met, every gap/spike reproduced
                                      independently; the multi-item document source is handled
                                      by the verifier's own reader, not by the gate's
dbt build                  -> exit 0  165 nodes: 4 seeds, 25 models, 136 tests, 0 errors. New:
                                      stg_ucdp_state_month, ucdp_state_month,
                                      ucdp_national_monthly, plus the spine and panel joins
verify_harmonisation.py    -> exit 0  25 metrics, 8,350 spine rows, 1,349 observed (16.2%), and the
                                      count metrics carry **0 interpolated months** (the rule is
                                      keyed on the catalogue's unit = 'count')
verify_stage6.py           -> exit 0  12 specifications reproduced independently: PPML coefficients
                                      agree to 2e-12, cumulative LP coefficients to 1e-12, and the
                                      five verdicts re-derived from the declared rules
03_estimate.R              -> exit 0  12 specifications + 60-offset lead-shift distribution +
                                      499-draw secondary null; design A estimated_not_identified,
                                      design B estimated
verify_stage5.py           -> exit 0  36 cards, diagnostics re-run on the new base; 1 reported
                                      warning (the marginal mmr cointegration rank), 0 failures
verify_dags.py             -> exit 0  36/36 cards acyclic, schema-valid, adjustment sets block
                                      every backdoor path in the assumed graph
```

**Vintage 2026-10-18 (fourth session) — Stage 7, the multiverse:**

```
04_robustness.R            -> exit 0  105 specifications fitted (81 Design A PPML, 24 Design B
                                      local projections at h=2); support A 45 positive /
                                      36 negative, B 24 / 0; 5 axis levels flip by majority;
                                      6 of the 105 inside the declared ±0.02 near-zero
                                      band; the pre-registered cell reproduces Stage 6
                                      to 4.3e-12; spread decomposition 0.4073 across
                                      covariate sets / 0.7548 across shock definitions;
                                      base fingerprint state_panel dd11d300f588,
                                      national 0084ea1d7129, oil 167ff0dce42d;
                                      specification_curve.svg written (94,502 bytes,
                                      505 marks across two panels)
verify_stage7.py           -> exit 0  every specification re-fitted independently: 81 PPML
                                      fits in statsmodels, 24 local projections, 36
                                      leave-one-state-out refits and 48 placebo alignments;
                                      worst coefficient gap 6.5e-9, worst clustered-SE gap
                                      0.85 % against the stated 5 % allowance; both Oster
                                      bounds, the majority-flip rule, the HAC table and
                                      the spread decomposition reproduced — the spread
                                      from the verifier's own re-fitted coefficients,
                                      not from the published rows
validate_artifacts.py      -> exit 0  105 specifications, 81 A / 24 B; the support counts are
                                      recomputed from the artifact's own rows, exactly one
                                      specification per design is flagged pre-registered,
                                      the curve exists and draws at least one mark per
                                      specification; 38 registry documents schema-valid
scripts/verify.sh          -> exit 0  the whole chain in one status — compile, contracts,
                                      Stage 3 gates, dbt build, Stage 6 estimates, Stage 7
                                      grid and all seven verifiers — ending "all checks
                                      passed" with the Stage 7 curve regenerated in the
                                      same run it was verified against
```

**Vintage 2026-10-18 (current, fifth session) — Stage 8, the registry:**

```
05_registry.R             -> exit 0  vintage 2026-10-17 | 36 cards | 2 carry a published number,
                                    34 do not: outcome_series_absent 12,
                                    no_specification_declared 10,
                                    design_result_is_channel_level 9, design_not_run 3;
                                    published without a card: fatalities_civilians;
                                    design results A estimated_not_identified (3 specs),
                                    B estimated (9, channel-level), C not_run
verify_registry.py        -> exit 0  the mapping re-derived from the artifacts: 2 of 36 cards
                                    should carry a number and 2 do; every attached number
                                    equals the estimates artifact's to 1e-9; every
                                    not_estimated card's reason is the recomputed one; the
                                    index's design-level results are the artifacts' numbers;
                                    B is declared channel-level
validate_artifacts.py     -> exit 0  2 of 36 cards carry a published number; the index's counts
                                    recomputed from the cards on disk; 38 registry
                                    documents schema-valid against 0.3.0
```

**Stage 8 break-tests — three guards mutated, the failure observed, then restored.** The driver backed up
all 37 registry documents, kept the digest of the directory, and checked afterwards that it was
byte-identical (`ed6a53a8c7da6630`): a break-test that leaves the artifact changed is worse than none.

```
validate_artifacts  a card's estimate block reset (the   -> exit 1  "registry/dags: the index says 2 card(s)
                   ordering trap)                                    carry a published number and the cards
                                                                     say 1 — the registry is stale against
                                                                     its own cards"
verify_registry    a coefficient moved off the artifact's-> exit 1  "fatalities__A: coefficient is
                   value                                             0.4892847253 on the card and
                                                                     0.4792847253 in registry/estimates/
                                                                     2026-10-17/estimates.json"
verify_registry    a not_estimated card's reason swapped -> exit 1  "mmr__B: reason
                                                                     'no_specification_declared',
                                                                     recomputed
                                                                     'design_result_is_channel_level'"
                                     each case restored  -> exit 0  contracts green again; registry
                                                                    digest unchanged
```

**Stage 7 break-tests — eight guards mutated, the failure observed, then restored.** The first four are
contract tests and run in seconds; the last four re-run the verifier, which re-fits the whole grid (three
minutes each). The driver kept each run's full output and checked afterward that the artifact's sha256 was
byte-identical to the one it started from — a mutation that leaves the artifact changed is the failure
mode a break-test exists to rule out, and a restored-but-different artifact would look green.

```
validate_artifacts  support count 45 -> 46 in the summary     -> exit 1  "design A support n_positive
                                                                          is 46 in the summary and 45
                                                                          in its own rows"
validate_artifacts  a second specification flagged preferred -> exit 1  "design A has 2 specifications
                                                                          flagged preferred; exactly one
                                                                          per design is the pre-registered
                                                                          one"
validate_artifacts  specification_curve.svg moved aside      -> exit 1  "the specification curve is
                                                                          missing or empty — the exit
                                                                          criterion is a rendered curve,
                                                                          not a table"
validate_artifacts  artifact vintage -> 2026-10-16           -> exit 1  "the artifact's own vintage is
                                                                          '2026-10-16', which disagrees
                                                                          with the directory holding it"
verify_stage7       one coefficient moved by 0.01            -> exit 1  "design A / A|fatalities|lag0|
                                                                          state_fe|full: reported
                                                                          -0.062311 vs recomputed
                                                                          -0.052311"
verify_stage7       the `fatalities` flip level removed      -> exit 1  "flip list: published [...] vs
                                                                          recomputed [...]" — the published
                                                                          4 omit 'outcome = fatalities' from
                                                                          the recomputed 5 — and "flip count
                                                                          disagrees with the recomputed
                                                                          majority rule"
verify_stage7       the per-capita axis removed from the
                    unbuilt list                             -> exit 1  "unbuilt axes: population_
                                                                          denominator is neither varied
                                                                          nor declared as unbuilt"
verify_stage7       the spread decomposition moved to 0.9   -> exit 1  "spread / design B /
                                                                          across_shock_definitions:
                                                                          published 0.900000 vs
                                                                          recomputed 0.754829 — the
                                                                          magnitude claim is not the
                                                                          fitted grid's"
                                      each case restored  -> exit 0  contracts and verifier green again;
                                                                     artifact byte-identical to the
                                                                     one the run started from
```

The earlier vintages below are kept as history. Note that the report's own label is a date and the raw
vintages are not (S4-20) — `registry/quality/2026-10-17/` is the current gate report.

**Vintage 2026-10-16-correction (current, 2026-10-17):**

```
check_quality.py           -> exit 0  125/125 series gated (60 ok, 65 flagged, 0 empty);
                                      exit criterion enforced in code, 0 series omitted
                                      (37 of the 125 are the FAAC dose, gated from its
                                      parsed artifact rather than from its PDF payloads)
verify_quality.py          -> exit 0  every series has a gate result; gap and spike results
                                      reproduce from the raw payloads and the parsed
                                      artifact; all 174 landed FAAC documents shown to be
                                      referenced by the parse; 198 pre-1999 spikes
                                      shown to exist in an unwindowed scan and correctly
                                      absent from the report; 7 adjudications live,
                                      0 stale; 437 spikes left unadjudicated and printed
dbt build                  -> exit 0  144 nodes: 4 seeds, 22 models, 118 tests; the new
                                      dose-gate test break-tested against a doctored
                                      panel (4 lies, all caught; 0 false positives)
```

The 2026-10-11 figures for the same commands — 88 series, 60 ok, 28 flagged — are the earlier vintage and
are kept in §5 below as history, not as the current result.

```
probe_missing_variables.py -> exit 0  7 World Bank variables probed: 6 keyless and covering the study
                                      window (mmr, immun_penta3, unemp, fx, donor, oil_rents),
                                      1 flagged SPARSE (skilled_birth, 9 obs / 33y); donor pool
                                      13/13; the oil section now exercises the KEYED client
pull_worldbank.py          -> exit 0  22/22 (was 15/15) — the DAG-required variables added
pull_worldbank_donors.py   -> exit 0  5/5 predictors x 13 donors
pull_fred.py               -> exit 0  1/1 — Brent DCOILBRENTEU, 10,275 rows (9,102 with values),
                                      1987-05-20..2026-10-06, 474/474 months carry an observation,
                                      longest missing run 12 days, sha256 b6807052c734
verify_provenance.py       -> exit 0  28 payloads across 3 sources (22 + 5 + 1), 0 orphaned,
                                      every sha256 reproduced
01_build_dags.R            -> exit 0  36/36 DAGs (12 outcomes x 3 designs), 0 failures;
                                      every label present in the SVG, none overflowing its node
verify_dags.py             -> exit 0  36/36 schema-valid, acyclic, adjustment set blocks
                                      every backdoor path (3-8 per graph); 0 orphaned cards;
                                      variables_still_missing recomputed from the cards: 7
py_compile (8 files)       -> exit 0
ruff check (files edited)  -> the 5 remaining hits are the repo's own pre-existing noqa: E402
                                      convention (pull_worldbank.py carries the identical two)
```

**Stage 4 — the analytical base (built 2026-10-11):**

```
dbt build --project-dir dbt --profiles-dir dbt
                           -> exit 0  115/115 (4 seeds, 19 models, 92 data tests, 7 views)
                                      PASS=115 WARN=0 ERROR=0 SKIP=0 NO-OP=0 REUSED=0
                                      fact_metric 7,682 rows = 23 metrics x 334 months
                                      (1999-01 .. 2026-10); observed 775 (10.1%),
                                      interpolated 4,389, unobserved 2,518
verify_harmonisation.py    -> exit 0  the whole spine recomputed from data/raw/ + the declared
                                      specs and compared row for row: 0 observation-type
                                      disagreements and 0 value disagreements beyond float
                                      noise (largest relative difference 8.9e-16 = 4 ulps,
                                      against a one-month population step of ~2e7);
                                      23 anchors (16 fixed at 2000-01, 7 on the recorded
                                      fallback); 474 monthly Brent values reproduce the
                                      frozen mean-of-daily rule; administration spine matches
                                      base spec section 7 including the decided Yar'Adua ->
                                      Jonathan boundary (2010-05-05 -> 2010-05-06); four
                                      strata covering 329 months + 5 pre-study; 25 metrics,
                                      12 outcomes, 8 definition breaks; state panel
                                      37 x 334 with 0 doses; donor panel 13 countries,
                                      0 treated-unit rows
py_compile + ruff check    -> exit 0  new verifier clean
verify_quality.py          -> exit 0  unchanged, so Stage 4 introduced no regression in Stage 3
verify_dags.py             -> exit 0  unchanged
verify_provenance.py       -> exit 0  unchanged (28 payloads, 3 sources, 0 orphaned)
```

**Stage 5 — pre-analysis diagnostics (re-run at vintage 2026-10-16, 2026-10-17):**

```
02_diagnostics.R           -> exit 0  vintage 2026-10-16 (taken from the latest Stage 3 report);
                                      dose axes measured separately: D1=absent, D1_nominal=pass,
                                      D2=absent, D3=not_built; the specified axis D1 decides the
                                      family; 36 card pre-checks attached (15 fail, 7 degraded,
                                      14 not attempted, 0 pass)
01_build_dags.R            -> exit 0  36/36 cards rebuilt at vintage 2026-10-16
verify_stage5.py           -> exit 0  every headline diagnostic reproduced from the base; the new
                                      dose-axis claims recomputed (including that a length-one
                                      present_axes is an array, not a string); 1 warning (mmr, as
                                      before), 0 failures
verify_dags.py             -> exit 0  unchanged, so the Stage 5 re-run introduced no regression
                                      in the DAG layer
```

The 2026-10-11 Stage 5 run — the one that produced the first set of verdicts against the pre-FAAC base —
is recorded in §5 as history; its artifact directory was superseded rather than kept, because it described
a base that no longer exists (C-44).

**Stage 5 — first run (built 2026-10-11, superseded):**

```
02_diagnostics.R           -> exit 0  native grain, study floor 1999-01-01; 26 series, 18 classified,
                                      10 inconclusive (carried as I(1), the conservative branch);
                                      Johansen on {Y, log(oil), fx}: 6 outcomes ranked, estimators
                                      assigned by the base-spec rule; 3 shock windows x 23 metrics
                                      counted; dose validation (0 of 12,358); 12 pre-fit QPs;
                                      6 Tier-3 MDEs; VIF per outcome; 36 card pre-checks attached
01_build_dags.R            -> exit 0  36/36 cards rebuilt, each now carrying its `diagnostics` block
verify_dags.py             -> exit 0  unchanged, so Stage 5 introduced no regression in the DAG layer
verify_stage5.py           -> exit 0  spec echo (9 thresholds) · observed-spine fraction (775/7,682
                                      = 10.1%) · 69 shock-window counts and verdicts · dose
                                      validation · Johansen rank (6/6; 5 exact, 1 warned) ·
                                      12 pre-fit QPs re-solved with scipy · 6 Tier-3 MDEs rebuilt ·
                                      card statuses and design verdicts re-derived; 1 warning
                                      (mmr rank marginal), 0 failures
py_compile + ruff check    -> exit 0  new verifier clean
verify_quality.py          -> exit 0  unchanged
verify_harmonisation.py    -> exit 0  unchanged
verify_provenance.py       -> exit 0  unchanged
```

**Stage 5 break-tests.** Ten guards mutated — the failure observed, then restored. Eight on the
verifier (each mutation of `diagnostics.json` below turns `verify_stage5.py` red), two on the engine:

```
verifier: shock 1/oil observed count 31 -> 30    -> exit 1  counts differ from the base
verifier: dose D1 n_non_null 0 -> 5              -> exit 1  disagrees with state_panel
verifier: prefit u5mr/yaradua ratio 0.670 -> 0.5 -> exit 1  differs from the re-solved QP
verifier: gdp_growth Johansen rank 0 -> 1        -> exit 1  recomputed rank 0 != engine rank 1
verifier: card u5mr__A status fail -> pass       -> exit 1  != recomputed fail
verifier: mde u5mr pdp_first halved             -> exit 1  != rebuilt design matrix
verifier: design B status degraded -> candidate  -> exit 1  != recomputed from the cards
verifier: u5mr trace rows reordered              -> exit 1  rows are not labelled r = 0 .. K-1
engine:   A card status fail -> pass             -> exit 1  "a declared_gap outcome cannot pass"
engine:   drop a non-pass card's blocker         -> exit 1  "status 'fail' with no blocker recorded"
                                      each case restored -> exit 0  base green again
```

**Break-tests — every new guard mutated, the failure observed, then restored.** Twenty of them: seven
dbt tests and thirteen verifier checks. A green guard that cannot go red proves nothing.

```
fact_metric index /100 -> /101                  -> exit 1  anchor months are not indexed at 100
interpolation bound 12 months -> 400            -> exit 1  4,389 rows carry the wrong
                                                          observation_type (the 108-month hole)
stg_fred_monthly avg -> max                     -> exit 1  monthly Brent disagrees with the
                                                          frozen rule
fact_metric term join widened by one month      -> exit 1  duplicate (metric, month) rows
seed: fatalities coverage_status cleared        -> exit 1  unlanded outcome with no declared gap
int_metric_monthly: unobserved filled with 0.0  -> exit 1  values outside the observed span
stg_raw_manifest: vintage filter removed        -> exit 1  a superseded vintage reached fact_metric
verifier: spec anchor moved to 2001-01          -> exit 1  metric_anchor disagrees with the spec
verifier: spec spine floor moved to 2000-01     -> exit 1  grid differs: 5 extra months
verifier: spec interpolation span -> 1 month    -> exit 1  4,389 observation-type disagreements
quality.yml: frozen resample rule renamed       -> exit 1  "verifier does not implement the
                                                          declared resample rule"
verifier: one base value +1                     -> exit 1  301 rows differ, e.g. u5mr/1999-07
verifier: one index value x1.01                 -> exit 1  1 row is not value/anchor*100
verifier: one spine month deleted               -> exit 1  grid: 1 missing (2023-06)
verifier: a tenure stratum relabelled           -> exit 1  dim_administration_term 21 differs
verifier: a definition break deleted            -> exit 1  the fx breaks are missing
verifier: a state-panel dose column populated   -> exit 1  dose populated with no source landed
verifier: an outcome's declared gap cleared     -> exit 1  coverage_status vs outcomes.yml
verifier: quality status desynced from report   -> exit 1  u5mr 'flagged' vs the report's 'ok'
verifier: a frequency gap erased                -> exit 1  cpi_yoy catalogue_frequency
                                      each case restored -> exit 0  base green again
```

**Break-tests — the artifact contracts (2026-10-17).** The three checks in `scripts/validate_artifacts.py`
exist because C-42 and C-44 were both a *name or a shape that stayed in the code after it stopped being
true*. Each was mutated and the failure observed, on the real raw layer, then restored:

```
validate_artifacts  PDF_SUFFIXES = {} (drop the reader)      -> exit 1  data/raw/faac/2026-10-16-correction/
                                                                       oagf-2019-04/page-0001.pdf: unregistered
                                                                       payload extension '.pdf'
validate_artifacts  report label must be '...-correction'    -> exit 1  registry/quality/2026-10-17: the report's
                                                                       own label is not a date, so every consumer
                                                                       that selects the newest report by date
                                                                       will skip it
validate_artifacts  Stage 5 must describe 2026-10-11 instead -> exit 1  registry/diagnostics/2026-10-17
                                                                       describes a superseded gate report
                                         each case restored  -> exit 0  contracts green again
```

```bash
# Stage 4 — build the analytical base, run its tests, then verify it independently
# (dbt is not on PATH: it lives in the ds-general env, so it needs the same conda run wrapper)
conda run -p C:/Users/TOSHIBA/ds-general dbt build --project-dir dbt --profiles-dir dbt
$PY tests/verify_harmonisation.py
```

**Vintage 2026-10-10 (first, superseded but retained for revision detection):**

```
pull_worldbank.py     -> exit 0   succeeded: 15/15   failures: 0
verify_provenance.py  -> exit 0   page files on disk: 15, referenced: 15, orphaned: 0
probe_candidates.py   -> exit 0   covers 2015+: 10 of 15
fred (no key)         -> MissingCredential raised (actionable message)
ucdp (no key)         -> MissingCredential raised (actionable message)
```

**Break-tests — checks that were made to fail on purpose.** A green test that cannot go red proves
nothing, so each guard was mutated and the failure observed, then restored:

```
verify_dags.py  drop 'oil' from an adjustment set   -> exit 1  fails to block backdoor path
verify_dags.py  add a back edge Y -> oil            -> exit 1  graph is cyclic
verify_dags.py  blank a node's source               -> exit 1  CHECK FAILED
verify_dags.py  drop a gap from the index           -> exit 1  index disagrees with the cards (6 vs 7)
verify_dags.py  adjustment_set as a string          -> exit 1  schema violation
verify_dags.py  delete a rendered SVG               -> exit 1  svg missing or empty
pull_fred.py    no key in .env (moved aside)         -> exit 1  REFUSED "FRED_API_KEY is not set";
                                                               no vintage directory created
pull_fred.py    key present but unregistered         -> exit 1  REFUSED "FRED rejected the API key";
                                                               partial vintage deleted, none left
pull_fred.py    same-day re-run (vintage exists)     -> exit 1  REFUSED "vintage '2026-10-11' already
                                                               exists ... raw layer is immutable"
pull_fred.py    --vintage <new label>               -> exit 0  identical sha256 (reproducible fetch)
verify_prov.    flip one byte of the Brent payload   -> exit 1  sha256 mismatch (b6807052 vs 154ffdc3)
verify_quality  inflate a reported spike count       -> exit 1  "n_spikes 2 vs reported 99"
verify_quality  drop a series row from the report    -> exit 1  "exit criterion: worldbank/u5mr/NGA is
                                                               in the manifest but has no gate result"
verify_quality  add an adjudication that matches
                nothing to the spec                  -> exit 1  "stale adjudication: population/2011
                                                               matched no flagged event"
verify_quality  disable the study-window floor
                (start 1900) and regenerate          -> exit 1  198 problems, "the report flags a
                                                               pre-1999 spike (1990-08)"; flagged
                                                               series rise 28 -> 45
check_quality   125 series, one flag flipped to pass -> n/a    status is derived, not asserted;
                                                               empty/gap/spike alone decide it
dbt build       doctor the state panel: a state
                loses its gate result, then claims
                one it lacks, then the join is
                emptied, then the FCT is gated  -> exit 1  "dose_gate_status_agrees_with_dose_gated"
                                                               returns 1, 2, 12,024 and 334 rows
                                                               respectively; 0 on the real table
each case, restored                                 -> exit 0
```

Reproduce with:

```bash
PY="conda run -p C:/Users/TOSHIBA/ds-general python"

# what the graphs need that nothing sources
$PY ingestion/flows/probe_missing_variables.py

# land the national series, the donor panel and the oil covariate, then prove all three
$PY ingestion/flows/pull_worldbank.py
$PY ingestion/flows/pull_worldbank_donors.py
$PY ingestion/flows/pull_fred.py        # needs FRED_API_KEY; in .env or exported
$PY tests/verify_provenance.py          # every source under data/raw

# Stage 3 — gate every landed series, then verify the report independently
$PY ingestion/flows/check_quality.py
$PY tests/verify_quality.py

# DAG layer (R 4.5.2 + ggdag/dagitty)
Rscript analysis/R/01_build_dags.R
$PY tests/verify_dags.py
```

Note: `conda run -n ds-general` does **not** work — `ds-general` is a prefix environment at
`~/ds-general`, not a named one under `miniconda3/envs` (decisions.md I-01).

## 5. Findings so far

**Design C's donor pool, widened (2026-10-18).** Full write-up: `docs/design-memo.md` §4;
artifact `registry/diagnostics/2026-10-18/`.

- **The `infeasible` verdict was about the pool, and the pool was fixable.** Against 13 countries chosen on
  GDP comparability no window could track Nigeria (ratios 0.58–1.55 against a 0.10 threshold). Against **99
  candidates** screened on oil dependence, region/income band and coverage: `u5mr` **passes 3 of its 4
  runnable windows** (ratios 0.0014–0.0042; ratio-on-differences 0.013–0.064), `gdp_growth` passes 1 of 4,
  `cpi_yoy` none (C-59).
- **A pass the design cannot celebrate yet.** A 99-donor simplex can fit almost any pre-period — the
  `gdp_growth`/yaradua window reaches a ratio of 1.7e-06, which is interpolation rather than validation — so
  the pre-fit gate is **weaker evidence than it was with 13 donors**, `Synth` still loses to the best single
  donor, and Design C remains **not estimated**: the estimator and the placebos Stage 5 deferred to Stage 6
  are the next build.
- **The rollup rule was undeclared, and the widened pool is what made that matter.** With 13 donors nothing
  passed, so the engine's "any window passes" rule never showed; with 99 it would have reported
  `gdp_growth: pass` on one window of four. It is now declared as a strict majority of the runnable windows,
  implemented by the engine and the Stage 5 verifier, and break-tested (S5-12).
- **Two acquisition defects were found by the chain, not by review.** The World Bank WAF rejects some country
  *combinations* deterministically (`LK;LR` 200, `LK;LR;LS` 403), so the flow splits and retries and records
  the split depth (C-60); and the chunked landing silently broke the `dataset_id` join, emptying the donor
  panel under a green `dbt build` with every Stage 5 outcome reported `not_attempted` rather than failing
  (C-61). The second was found by reading a reason string, and the flow now checks its own landing contract.

**Stage 8b — comparing tenures on the one monthly outcome (2026-10-18).** Full write-up: `docs/events.md`;
artifact `registry/events/2026-10-18/`.

- **Two of eight event-outcome cells survive both checks.** Reported incidents rose **+391 %** in the 12
  months after the 2010 transition and fatalities **+77 %** after the 2023 one, each at p = 0.017 — the
  floor of what 58 placebo months can resolve — with the pre-trend placebo smaller than the post-window
  shift (C-56).
- **Four cells fail the pre-trend placebo**, including the largest shift in the series: the 2015 fall in
  fatalities (−67 %, family-wise p = 0.017) was already under way 24 months before the transition. Buhari
  2015 on incidents and Tinubu 2023 on incidents fail for the same reason, in the other direction (C-56).
- **One transition cannot be checked at all.** Yar'Adua 2007 has 100 months of history and the pre-trend
  placebo needs 120; the artifact reports `check_not_available` rather than scoring the missing check as a
  null (S8b-05).
- **The placebo null drifts down by 32 %**, so the first inference rule written for this stage — two-sided
  in magnitude — was discarded before publication: it scored the largest fall in the series as unremarkable
  while its own left tail said the opposite (C-57). The published rule is the same-side signed tail in the
  add-one form, and the reason is on the artifact.
- **No party comparison is published.** Two events against two events has no sampling distribution; the
  PDP/APC medians (+55.3 % / +4.6 %) are published as description with `no_test_computed: true`, and the
  verifier fails if a test statistic appears in that block (S8b-06).

**Stage 7 — what survives the choices (2026-10-18).** Full write-up: `docs/robustness.md`.

- **Design B's sign is invariant; its timing is not.** 24 of 24 specifications positive, all 24 intervals
  excluding zero, the pre-registered cell reproducing Stage 6 to 4.3e-12 — against an in-time placebo of
  **p = 0.0625** (3 of 48 shifted alignments as large as the estimate) and a coefficient that spans 0.3968
  to 2.3976 across the grid, mostly because the three-month shock is a smoother regressor. The honest
  reading: the channel and its sign are the result; "two to three months" is a weaker claim that now
  carries its placebo (C-51).
- **Design A is not robust, and the axis that moves it is the dose lag.** 45 of 81 positive against 36
  negative; the lag-1 specification is negative in all three windows while the pre-registered same-month
  one is positive; `state_fe` and `state_month_fe_state_trend` also flip by majority. Leave-one-state-out
  does not flip it (0 of 36), so the instability is not one unit — and dropping the three oil-producing
  states moves the estimate from +0.479 to +0.666, the same oil-price concentration C-47 measured (C-50).
- **The per-capita dose is still missing and the curve says so.** Every cell is the nominal dose, because
  `d1_faac_per_capita` is 0 of 12,358 rows (X-09). S6-06's invariance argument is an argument, not a fitted
  specification, and the artifact lists the axis as unbuilt rather than quietly omitting it.
- **Oster's delta does not certify anything here, and the artifact says which case it is in.** Negative for
  both designs — the controls move Design B away from zero (−44.04) and flip the sign of Design A's linear
  analogue (−0.1023 → +0.0882) — so the δ ≥ 1 cutoff has no reading. Rosenbaum bounds are recorded as not
  applicable rather than omitted (S7-05).

**Stage 6 — what could actually be answered (2026-10-17).** Full write-up: `docs/estimates.md`.

- **The presidential-tenure question is not answerable**, and the reason is arithmetic: four to five
  administrations against 27 annual observations put the minimum detectable effect at 35–80 residual
  standard deviations (Stage 5's rebuilt design matrices). It is not "no evidence yet"; it is a question
  this data cannot carry. Any tenure number would be a restatement of its own assumptions.
- **The fiscal channel is answerable, and now estimated.** A 10 % Brent rise reaches state allocations as
  **~5 % more money, two to three months later** (cumulative elasticity +0.518 at h=2, HAC SE 0.166;
  −0.160 at h=0; 6-month lead placebo +0.095). The lag matches the disbursement calendar rather than
  contradicting it, and the zero at h=0 is part of the finding (C-48).
- **The dose-response question is estimable and not identified.** Higher allocations do not visibly buy
  less violence, and the design cannot distinguish that from any other timing: 8 of 60 mis-timed doses
  return an estimate at least as large as the estimate itself, and the 24-month placebo (+0.302) is nearly
  the estimate (+0.479). The cause is measurable, not rhetorical — after state and month effects the
  dose's variation is the 13 % derivation share moving with the oil price (residual sd 0.50 in Delta,
  Bayelsa, Rivers; 0.11 elsewhere) — a national shock interacted with a fixed state characteristic (C-47).
- **A monthly NGN/USD series does not exist on any keyless source** (C-46), so the price and exchange-rate
  channels cannot be separated inside Design B. It is a stated limitation on the estimate, not a silent one.

**Access (probed 2026-10-10; "unreachable" = failed via two independent network paths):**

| Source | Result |
|---|---|
| World Bank API | ✅ keyless, working — the backbone |
| NBS, CBN | ✅ reachable (HTML/PDF, no API) |
| IMF DataMapper | ⚠️ 403 to scripted clients, 200 via relay |
| FRED | ✅ **resolved 2026-10-11** — key registered, HTTP 200, Brent landed |
| UCDP | ✅ **keyless via the bulk archive (2026-10-17)** — the *API* still returns 401 without a token, but `ged251-csv.zip` is a plain 200 (29,307,888 bytes) and CC-BY. Landed as the security outcome (C-45) |
| ACLED | ❌ documented endpoint dead; now **OAuth** |
| OAGF (`oagf.gov.ng`), Open Treasury, NEMIS | **OAGF 🟡 corrected 2026-10-16** — the Open Treasury portal is still unreachable, but the OAGF's own site publishes the monthly disbursement PDFs and was crawled successfully (83 documents). Open Treasury and NEMIS remain ❌ — two Nigerian gov hosts of the three |
| UNESCO UIS | ❌ every path 404, including root |

**Variable gaps (probed 2026-10-11).** The causal-graph layer named variables that nothing was
sourcing, so the difference was probed rather than assumed. Seven were keyless and reach 1999+ 2015+,
and are now landed (`donor` had no source at all before this). **The oil gap closed on 2026-10-11**
(C-23/C-24): Brent crude is landed and the `oil` nodes are `acquired`. `index.json` carries the residue
as `variables_still_missing` — **7 variables, 3 root causes**:

| Root cause | Variables | Needs |
|---|---|---|
| Fiscal dose | `dose` (D1), `faac` | ✅ **The acquisition is done (2026-10-16)** — 174 documents, 114 months × 36 states, `state_panel.faac_gross_total_naira` — **and the Stage 3 gate is done (2026-10-17)**: 37 series gated, all `flagged` on distribution-cycle spikes, with `dose_gate_status` on the panel. What remains is a **decision** (the state population denominator, X-09), a **catalogue entry** for a panel with no declared national aggregation, and a decision about the annual-grain length |
| Education outcomes | primary completion, net enrolment, youth literacy | No open source reaches 2015+ |
| Security outcomes | fatalities, incidents | ✅ **Closed 2026-10-17** — UCDP GED bulk archive, keyless, state-attributed, on the panel and on the spine (C-45). ACLED would still be a second, richer source, and its terms stay unresolved without leaving a hole |

**Oil price — closed.** Brent crude is landed as a daily series: 10,275 rows, 9,102 with values,
1987-05-20 → 2026-10-06, sha256 `b6807052c734`. All **474 months** in the span carry at least one
observation (min 4, max 23) and the longest gap is 12 days, so a monthly oil series is constructible
across the whole study window including the 2023 subsidy window. Spot-checked against the real Brent
history: 2008-07-03 = $143.95, 2020-04-21 = $9.12, and the 2008-07-04 US holiday is correctly marked.
**Caveat:** the series is *daily*, and Stage 4 must freeze the daily→monthly rule before any
oil-adjusted estimate is computed — changing it later changes every adjusted result (C-23).

Design C's donor pool is **not** blocked: all 13 candidates carry all 5 screening predictors to 2015
(only Venezuela's oil-rents series stops early). With `common` now `derived`, **design C has zero
unsourced nodes**; designs A and B are each down to one, the FAAC fiscal dose.

**Coverage (22 indicators as of 2026-10-11; the 15-indicator first vintage reads the same):**

- **Health is strong** — `u5mr` 61 obs no gaps, `life_expectancy` 65, `measles_imm` 41, `health_spend_gdp` 24
- **Health gained three series** — `mmr` 39 obs to 2023 (now `ok`), `immun_penta3` 41 obs to 2024
  (`partial`: an annual DPT3 stand-in, since DHIS2 is credential-blocked), `skilled_birth` 9 obs in 33
  years (`partial`: a survey series, not an annual one — it must render as flagged points)
- **Economy is strong** — `gdp_per_capita`, `population`, `cpi_yoy` all 66 obs no gaps
- **Security has no usable World Bank series** (`homicides`: 3 obs) — depends entirely on UCDP/ACLED
- **Education is unusable after 2010** — every outcome series stops in 2010–2011. Primary completion,
  lower-secondary completion, pupil-teacher ratio and tertiary enrolment all end mid-Jonathan, so they
  cannot see the APC tenures at all. Only `educ_spend_gdp` (a policy input, not an outcome) and
  `adult_literacy` (6 points) reach the present.

  **Consequence:** of the four registry domains, education should be recorded as a **declared gap**.
  "We found no education effect" and "we had no education outcome data after 2010" are different
  statements, and only the second is true.

**Stage 3 gate results (2026-10-11) — 88 series, 60 `ok`, 28 `flagged`.** The full report is
`registry/quality/2026-10-11/report.md`. What the gates found, rather than what they waved through:

- **The study-window floor works, and the size is now measured.** An unwindowed scan reports **198
  pre-1999 spike flags** across the landed series; the windowed report contains none. C-06 and C-21
  are closed, and `verify_quality.py` fails if the floor ever becomes inert.
- **An undeclared definition break, found by the gate.** `cpi_yoy` 2024→2025 falls 10.23 points, and
  the cause is the **NBS rebasing the CPI in January 2025** on a new 2024 base year — the first
  rebasing since 2009 (Reuters, NBS). Headline inflation fell 34.80% → 24.48% at the rebasing. Not a
  data error, and not detectable from the numbers alone.
- **`donor_oda` is contaminated, and that touches the adjustment set.** Net ODA rose **+1006% in 2005**
  ($0.58bn → $6.4bn) and reversed −82.9% by 2007, because **Paris Club debt relief is recorded as
  ODA** (OECD, UNCTAD; Nigeria's US$18bn deal was announced October 2005, completed April 2006).
  `donor` is in the adjustment set for designs A and B on every health and education outcome, so a
  design conditioning on it partially conditions on a debt restructuring. **This is the most
  consequential output of Stage 3 and it goes to Stage 5.**
- **The gaps are real and now quantified:** `adult_literacy` has a **108-month** hole (2006→2016),
  `literacy_youth` and `skilled_birth` 48-month holes, `primary_completion` and `ner_primary`
  36-month holes. These are the C-03/C-04/C-07 findings restated as gate results.
- **One gate had to be rebuilt after running it.** A single 50%-relative spike rule flagged **52 of 88**
  series — Ecuador's growth rate 18 times in 27 years — because a rate moving 0.5%→3.0% is a 500%
  relative change and a 2.5-point move. Splitting the measure by series type (relative for levels,
  percentage points for series already in percent) brought it to 28 and let the real signals through.
- **60 of 67 spikes are deliberately left unadjudicated.** The immunisation and primary-completion
  swings have no documented cause, so the report says `UNADJUDICATED` rather than inventing one.

**Donor pool and re-vintage verification (2026-10-18, sixth session) — transcript.**

```
$ python ingestion/flows/pull_worldbank_donors.py
vintage: 2026-10-18   donors: 99   predictors: 5   chunk size: 20
  group neighbour_west_africa       13 candidate(s)
  group oil_exporter                29 candidate(s)
  group africa_comparator           28 candidate(s)
  group lower_middle_income_large   35 candidate(s)
  treated unit NG excluded from the pool
  note gdp_growth  NY.GDP.MKTP.KD.ZG-p03s01  5 country(ies) landed after 2 WAF split(s)
  ok   u5mr        SH.DYN.MORT        chunks=5 rows=6534 donors=99/99 reaching_2015=99/99
succeeded: 5/5 predictor(s) in 40 request(s)   failures: 0

$ dbt build                -> 165 PASS, 0 ERROR   (donor panel 27,352 rows / 99 countries)
$ ingestion/flows/check_quality.py   -> 672 series gated: 357 ok, 313 flagged, 2 empty
$ Rscript analysis/R/02_diagnostics.R
5. pre-treatment fit — 3 outcomes attempted, 1 pass, 2 infeasible on pre-fit
     u5mr               pass                       3 of 4 runnable window(s) pass
     gdp_growth         infeasible_weak_pre_fit    1 of 4 runnable window(s) pass
     cpi_yoy            infeasible_weak_pre_fit    0 of 4 runnable window(s) pass

$ all verifiers (vintage 2026-10-18)
validate_artifacts -> 0   quality -> 0   stage6 -> 0   stage7 -> 0   registry -> 0
harmonisation -> 0        faac -> 0      dags -> 0     stage5 -> 0    events -> 0   provenance -> 0
registry schemas : 41 document(s) validated

$ python .probe/break_events.py     -> all 5 mutations caught, restored byte-for-byte
$ python .probe/break_stage5_c.py   -> caught: status -> pass while 0 of 4 runnable window(s) pass
```

**Stage 8b verification (2026-10-18) — transcript.**

```
$ Rscript analysis/R/06_events.R
series: 312 months 1999-01 -> 2024-12, 25 blank month(s) filled with zero
events: 4 | specifications fitted: 32 (h=12: 16, h=24: 16) | declared skips: 0
placebo: 58 eligible month(s) per outcome/horizon, enumerated (no RNG)
figure: event_study.svg (196379 bytes)

verdicts (h=12, baseline):
  yaradua_2007   fatalities   check_not_available          post=-0.1712 pre=—      p=0.610
  yaradua_2007   incidents    check_not_available          post=-0.3434 pre=—      p=0.186
  jonathan_2010  fatalities   not_interpretable_pre_trend  post=1.2770  pre=1.9558 p=0.017
  jonathan_2010  incidents    shift_detected               post=3.9125  pre=0.8758 p=0.017
  buhari_2015    fatalities   not_interpretable_pre_trend  post=-0.6747 pre=0.8381 p=0.017
  buhari_2015    incidents    no_shift_detected            post=-0.4795 pre=0.4041 p=0.085
  tinubu_2023    fatalities   shift_detected               post=0.7664  pre=0.5275 p=0.017
  tinubu_2023    incidents    not_interpretable_pre_trend  post=0.0671  pre=0.2547 p=0.169

$ python tests/verify_events.py                              -> exit 0
artifact         : registry/events/2026-10-18/events.json (32 specifications)
series           : 312 months 1999-01 -> 2024-12, 25 blank month(s) filled, 10 year(s) affected
transitions      : 4 of 4 bound to dim_administration_term at the declared dates and strata
specifications   : 32 rows re-fitted from the base; worst SE gap 0.002%, allowance 5%
placebo          : 58 month(s) re-enumerated per outcome/horizon, distributions and quantiles reproduced
inference        : 8 verdict(s) re-derived; 6 pre-trend placebo(row)s reproduced, 1 event declared uncheckable
party split      : 4 event(s) grouped into 2 group(s), medians and shifts reproduced, no test field present
PASS

$ python scripts/validate_artifacts.py                       -> exit 0
stage 8b artifact: 2026-10-17 (32 specifications over 4 transitions, 1 declared uncheckable pre-trend,
                   cells accounted for)
registry schemas : 39 document(s) validated
PASS

$ python .probe/break_events.py                              -> exit 0
1. coefficient moved 2 %                         verifier=1 contract=1  caught
2. one row deleted (silent omission)             verifier=1 contract=1  caught
3. uncheckable pre-trend scored as a pass        verifier=1 contract=1  caught
4. test statistic added to the party description verifier=1 contract=1  caught
5. figure deleted                                verifier=1 contract=1  caught
restored byte-for-byte: True True
PASS — all 5 mutations caught by at least one guard
```

**Stage 4 harmonisation (2026-10-11) — what building the base measured.** The stage's job was to build
a table; what it produced that matters is one constraint and two confirmations.

- **The monthly spine is 16.2 % observed (C-30)** — 1,349 of 8,350 rows — and was **10.1 %** (775 of
  7,682) when the finding was first recorded, before the monthly Brent, FAAC and UCDP landings. 4,389 rows
  are linear interpolations between annual points and 2,612 are empty months within the spine's span. That
  is not a defect — it is what a monthly spine over annual sources *is* — but it has a consequence that
  changes the plan: **the landed `cpi_yoy` is annual, so a monthly design-B estimate cannot see the
  2023-06 → 2023-12 window**, which contains two observations. `dim_metric.frequency_gap` flags
  `cpi_yoy`, `gdp_growth` and `unemp`. The three ways forward are in §8.
- **Brent at every administration's start reproduces the real oil history (C-31).** 1999-05-29 carries
  no quote (a Saturday) with a May-1999 month mean of **$15.44**; 2007-05-29 **$69.31**; 2010-05-06
  **$80.21**; 2015-05-29 **$63.16**; 2023-05-29 no quote, month mean **$75.47**. Obasanjo's *second*
  term starts at **$26.05**, not his first term's $15.44 — the number a reader would sanity-check an
  oil-adjusted estimate against, and the reason the price is computed per term.
- **A level shift is now annotatable rather than a finding (C-32).** 8 definition breaks reach the base
  as a dimension: the 2014 GDP rebasing (×2), the 2016 float, the 2023 unification, the 2014 and 2023
  unemployment methodology changes, the 2020 WTI episode carried on Brent, and the January-2025 CPI
  rebasing. A verifier check fails if the Stage 3 report's breaks do not all arrive.

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
5. **A YAML 1.1 trap in the DAG specs.** An unquoted `Y` parses as boolean `TRUE` — YAML 1.1 treats
   `y`/`Y` as true — so the outcome node's id silently became a logical and the first generator run
   died on `vapply`. Node ids are now quoted. Instructive because it failed *loudly*; the dangerous
   version of the same bug is a node that quietly never appears.
6. **`ggdag`'s tidy layout emits one row per edge, not one per node.** Nodes with no outgoing edge
   (the terminal outcome) get a standalone row; every other node appears only as an edge source.
   Labelling "rows where `to` is NA" therefore labelled exactly one node and dropped the rest — and
   the figures still rendered, so nothing failed. Caught only by reading the SVG back and asserting
   every node label is present. That assertion is now a build-time gate.
7. **`jsonlite`'s `auto_unbox` collapsed single-element arrays.** `adjustment_set: ["oil"]`
   serialised as the string `"oil"`, violating the card schema. Fixed with `I()` on the array
   fields, and the verifier now validates against the JSON Schema so this class of error cannot
   return silently.
8. **`ggdag` does not render latent nodes dashed** in this version, so the identifying assumption
   would have been invisible on the figure. It is now stated inside the node itself
   (`(assumed absent)`) and in the caption, and the generator asserts the marker reaches the SVG.
9. **The browser-automation session captured the API key in a page snapshot.** Registering the FRED
   key required driving a real browser, and `playwright-cli` writes a YAML snapshot of every page it
   visits into `.playwright-cli/`. One of those pages *displays the freshly issued key*, so
   `.playwright-cli/page-2026-10-11T07-06-49-517Z.yml` contained the credential in clear — a
   directory that was sitting untracked inside the repo. Caught by grepping the working tree for the
   key after the fact, not by any existing check. Directory deleted and `.playwright-cli/` added to
   `.gitignore`; the key now exists only in the gitignored `.env`. Same class of risk as D-01c
   (TOOLING.md) and the reason I-07 redacts manifests — this time in a tool the project does not own.

10. **`dim_definition_break` produced 34 rows for 8 breaks.** The donor panel reports the same
    definition breaks for the same indicator ids once per country, so all 13 `u5mr` rows were identical
    duplicates. A break is a property of the indicator's definition, not of the country reading it, and
    the dimension is keyed by `metric_id`. Found by reading the built table rather than by any test —
    the count looked plausible until it was compared with the report's distinct breaks. Now national
    series only (8 rows, decision S4-11).
11. **`oil_price_at_start` was attached to both terms of a two-term administration.**
    `dim_administration_term` joined the *administration's* start price, so Obasanjo's second term
    reported May-1999 rather than May-2003. Same class of error as an off-by-one date: it looks like a
    number and it is wrong. Caught by reading the built table — `$15.44` beside a 2003 term start was
    the tell. The term model now joins the price at its own start month (**$26.05**).
12. **A seed CSV field with an internal comma** ("Two terms — one spine row, two terms") parsed as an
    eighth column and failed the seed load. Quoted. Worth recording because the same class of error is
    invisible in a diff and a comma inside a free-text field is exactly what a `notes` column attracts.
13. **The verifier's value comparison was absolute and is now relative.** Ten of 7,682 rows first
    "failed" at a 1e-9 *absolute* tolerance on float round-tripping. Measured before loosening
    anything: the largest relative difference is **8.9e-16** (four ulps), against a one-month
    interpolation step of ~2e7 on the population series — so the tolerance remains ~14 orders of
    magnitude tighter than the smallest real defect it has to catch. A bounded, justified loosening,
    not a silenced assertion; the measurement is in §4.
14. **The dbt `profiles.yml` path is relative to the invocation directory, not the project directory.**
    `../data/analytics.duckdb` resolved to `D:\data\analytics.duckdb` and failed. Now written relative
    to the repository root, matching the `raw_root` var, with every documented command run from there.
15. **`read_json_auto(filename = true)` returns Windows backslash paths** while the manifests store
    POSIX paths — the same Windows/Linux break the Stage 2 manifest fix addressed (correction 3), one
    layer down, and the same one that would break the Linux CI runner the plan schedules against.
    Normalised in one place with `chr(92)`, not a backslash literal: a bare `'\'` inside a DuckDB
    string literal is an escape character, not a path separator.

## 7. Blocked

| Blocker | Needs |
|---|---|
| ~~FRED key~~ | ✅ **Unblocked 2026-10-11** — registered, key in `.env`, Brent landed, `oil` acquired (C-23) |
| ~~UCDP token~~ | ✅ **Not needed 2026-10-17** — the bulk archive is keyless and the security outcome is landed (C-45). ACLED stays unwired by choice: UCDP is CC-BY and already answers the domain |
| ~~FAAC parser (D1)~~ | ✅ **Unblocked 2026-10-16** — both publishers crawled, 174 documents parsed, every one reconciled to its own Total row (C-39/C-41) |
| State IGR parser (D2) | NBS publishes PDFs and HTML, no API. D2 is FAAC ÷ (FAAC + IGR), so the IGR half is now the only missing input |
| ~~A Stage 3 gate on the FAAC series (S4-17)~~ | ✅ **Done 2026-10-17** — 37 series (36 states + the national aggregate) gated from the parsed artifact and the result read onto the panel (S4-19). What the national series still lacks is a **catalogue entry**, which needs a declared monthly-to-annual aggregation, not a gate |
| UNESCO UIS current API path | Its docs (web search unavailable in this environment) |
| NEMIS reachability | A check from a network other than this one |
| DHIS2 tenant access | Institutional credentials; do not design a model on it until confirmed |
| Monthly NBS CPI — the grain the app's chart spec states | The manual-download parser. The landed CPI is annual, so design B cannot see the 2023 window monthly on it (C-30) even though the spine is now 16.2 % observed. Either parse the monthly series, or run design B at its annual cross-check |

## 8. Next steps, in order

**Stages 0–6 are done. No credential gates anything on the critical path, and the first estimates exist.**
What is left is not acquisition: it is the two *decisions* that would let the unidentified design become
identified (X-09 and a non-oil fiscal instrument), the designs that were never runnable, and the stages
that turn estimates into a product.

**A. Credentials: none outstanding.**

1. ~~**UCDP token**~~ **Not needed — 2026-10-17.** The API wants a token (401 on three versions) but the
   bulk archive does not, and it is CC-BY, so the security outcome landed keyless (C-45). ACLED stays the
   richer alternative and stays unwired: it needs OAuth and forbids redistribution, and the domain is
   answered. FRED needed no further action either (key in `.env`, Brent landed) — so the covariate gap
   that appeared against designs A, B and C is closed for three of those nodes at once.

**B. Unblocked now, no credentials needed.**

2. ~~**Stage 3 — quality gates.**~~ **Done 2026-10-11.** The study-window floor is in and quantified
   (198 pre-1999 spikes suppressed); the Brent daily→monthly rule is **frozen as a declared input**
   (`mean_of_daily_observations`) and applied by the gates, so Stage 4 must reuse it rather than
   re-choose it. Carried forward: **60 unadjudicated spikes**, and the `donor_oda` contamination that
   must reach every health and education card (C-28).
3. ~~**Stage 4 — harmonisation** (dbt).~~ **Done 2026-10-11.** The analytical base exists: 7,682 rows
   (23 metrics × 334 months, 1999-01 → 2026-10; 25 metrics after the FAAC and UCDP landings) on a local
   DuckDB, with the January-2000 index anchor
   and its recorded fallback, direction labels as a dimension, the base-spec §7 administration spine
   plus term-level party-by-tenure strata, the 37 × 334 state panel with declared-empty dose columns,
   the shock bands, and the Stage 3 quality status and 8 definition breaks travelling on it. 92 dbt
   tests and 20 break-tests; `tests/verify_harmonisation.py` recomputes the whole base independently.
4. ~~**Stage 5 — the design memo.**~~ **Done 2026-10-11, re-run 2026-10-16 and 2026-10-17** — it took
   C-30 (the 2023 window is not monthly-visible on the landed annual CPI), C-28 (the `donor_oda`
   contamination), C-27 (the 2025 CPI rebasing), the unadjudicated spikes and the 3 frequency gaps, and
   dropped failing designs *on the record*: 0 of 36 cards pass. Diagnostics are attached to every card;
   the artifact on disk is `registry/diagnostics/2026-10-17/` and the narrative is
   `docs/design-memo.md` at the vintage it was written against.
5. ~~**The FAAC parser (D1)**~~ **Done 2026-10-16.** All four publishers' paths are now acquired and the
   dose is in the base. ~~**Stage 3 gate on the FAAC series**~~ **Done 2026-10-17** — 37 series (36 states
   + national) gated from the parsed artifact, all `flagged` on spikes that fire at every state at once,
   with the result read into `state_panel.dose_gated`/`dose_gate_status` and a break-tested dbt test
   holding it honest (S4-19, C-42, C-43). What is left from this item is not acquisition: **D2** (the NBS
   state IGR half of the share) and the **population denominator decision** (X-09).
   Note the constraint the landing measured rather than assumed: the dose begins 2016-12, so it is an
   APC-era exposure and 10 years long at the annual grain — the dose now exists, but a *monthly*
   dose-response estimate is not what this makes possible (C-41).

**C. Then, in plan order.**

6. ~~**Stage 5 re-run — the design memo.**~~ **Done 2026-10-17, twice: at vintage 2026-10-16 over the FAAC dose and at vintage 2026-10-17 over the security outcome** (artifact: `registry/diagnostics/2026-10-17/`; the second re-run also replaced the two hand-typed numbers in the report with computed ones, C-49). The dose and
   Tier-3 checks were re-run against the post-FAAC base: the nominal column is now a measured dose axis,
   the specified axis `D1` (per capita) still decides the family, the Family A card text is derived
   rather than typed, all 36 cards were re-emitted, and `tests/verify_stage5.py` passes again (S5-10,
   S4-20, C-44). What the re-run **did not** do, and what now heads this list:
   - **X-09 — the state population denominator.** It is the only thing standing between the landed
     nominal dose and the per-capita axis Family A's estimand is written on, and it is a decision.
   - ~~**A state-attributed outcome.**~~ **Done 2026-10-17** — UCDP GED landed keyless, state-attributed,
     on the panel and the spine (C-45). Family A's other blocker is cleared; what remains on it is the
     dose axis and the identification below.
   - **A metric-catalogue entry for the FAAC panel** with a declared monthly-to-annual aggregation, which
     is what Family B's Tier-3 system is missing now that the series exists and is gated.
   - **`dag_designs.yml`'s `dose`/`faac` nodes still read `source_status: gap`,** deliberately — the node
     is specified as *per capita*, and the per-capita axis is absent. Noted in `docs/dags.md` rather than
     flipped, because `gap` is under-specified here, not wrong.
7. ~~**Stage 6 — estimation (R).**~~ **Built 2026-10-17, partially.** Twelve specifications across two designs
   (`registry/estimates/2026-10-17/`, verifier `tests/verify_stage6.py`, output `docs/estimates.md`).
   Design B — the fiscal transmission channel — is **estimated**; Design A is **estimated, not
   identified**, and says so with the check that decided it. The plan's `did` estimator was not used and
   the deviation is recorded (the dose has no staggered adoption; it is a magnitude, not a switch).
   **Still open, and this is what heads the list now that the estimates exist:**
   - **Identification for Design A.** C-47 measured the problem: the post-fixed-effect dose variation is
     the 13 % derivation share moving with the oil price. A fiscal instrument that varies within state
     for reasons unrelated to oil (state IGR, the VAT distribution) is a different acquisition, not a
     different estimator.
   - **The estimate block on the card schema** — Stage 8 work, not claimed by Stage 6. A card without an
     interval still does not ship, and no card currently carries an estimate.
   - **The FX channel** inside Design B (C-46): a monthly NGN/USD series would separate the price and
     exchange-rate channels and has no keyless source, so it would have to be assembled from CBN.
8. ~~**Stage 7 — robustness and the multiverse.**~~ **Built 2026-10-18** (`registry/robustness/2026-10-17/`,
   verifier `tests/verify_stage7.py`, output `docs/robustness.md`). 105 specifications declared before
   fitting and all published; the exit criteria are met by construction rather than by assertion — support
   counts per sign computed from the fitted rows, the pre-registered specification marked on the curve,
   and the five majority sign-flip levels named in the artifact, the figure and the narrative. What it
   changed: Design B's verdict now carries a timing bound (placebo p = 0.0625) and Design A's verdict is
   sharper than `estimated_not_identified` — its **sign** does not survive the grid. **What is still open
   from this stage:** the per-capita dose axis (X-09), the IGR instrument (D2), and a donor pool that would
   let Design C run at all.
9. **Stage 8 — the registry, narrative and RAG corpus.**
10. **Stage 9 — the app**, reading `registry/dags/index.json`: pick an outcome → pick a causal model →
   read the assumption and adjustment set → then the estimate under that model.

### The smallest credible end-to-end slice — revisited by Stage 4

`nigeria-causal-inference-spec.md` §16 Step 1 calls for one defensible model, end to end, as the
checkpoint. Stage 3 named design B on `cpi_yoy` (the 2023 subsidy window) as the fastest unblocked route,
on the grounds that `cpi_yoy` is `ok` (66 observations, no gaps) and its only non-outcome covariate — the
oil price — was landed and gated. **Building the base measured something that argument missed: those 66
observations are annual** (C-30). On a monthly spine, the 2023-06 → 2023-12 window contains two of them,
and the other ten months are interpolated. A monthly VECM on interpolated annual data estimates
something about the interpolation rule, not about the subsidy removal.

Three routes, in the order Stage 5 should weigh them:

1. **Run design B on `cpi_yoy` at its annual cross-check** (~26 observations, which base spec §9 already
   assumes and its sample-size constraint already discloses). Cheapest, fully unblocked, and honest —
   the interval will be wide and the card says why. It just cannot answer a *monthly* question.
2. **Parse the monthly NBS CPI.** The app's chart spec states a monthly CPI, so this is the acquisition
   that closes the gap rather than working around it. It is the same parser family as the FAAC work
   (NBS PDF/HTML), so doing both together is cheaper than either alone.
3. **Pick a genuinely monthly outcome instead.** `oil` is monthly and complete (334/334 observed), but it
   is a covariate, not an outcome.

What is already true either way: the study-window floor exists, the daily→monthly Brent rule is frozen
and verified, the base is built and independently reproduced, and **nothing on the estimation path is
credential-blocked**. The remaining caveats are annotatable rather than blocking — `cpi_yoy` carries the
January-2025 CPI rebasing inside the study window (C-27), so any estimate spanning it mixes a real
inflation path with a measurement change; that is an exclusion axis and a card annotation.

### Resolved by Stage 5 — the slice is the *boundary*, not a headline

Stage 5 weighed the three routes and found that **none of the 36 (outcome × design) cards passes its
pre-check**, so there is no headline estimate to build the end-to-end slice on. What Stage 5 hands to
Stage 6 instead is the boundary: the *annual* Design B VECM/ARDL and the *differenced* synthetic control
are the only estimators with a testable question, and each carries its own disclaimer (a 38–99 SD
detectable effect on the Tier-3 design; a donor pool that tracks changes but not levels). The one
action that moves the most is the **NBS FAAC parser** — it revives Family A outright and restores the
base-spec Tier-3 system for Family B — and it is the same parser family as the monthly NBS CPI, so
doing both together is cheaper than either alone. The full reasoning is `docs/design-memo.md`.

## 9. Standing constraints

- **Free tier only.** No paid service at any layer.
- **Publish code and derived aggregates; never restricted raw data.** ACLED and DHS/NDHS may not be
  redistributed, which is why this repo's `.gitignore` excludes `data/raw/`.
- **Never a point estimate without its interval.** Six-item rigor floor acts as a shipping gate.
- **The app never fits a model at render time.**
