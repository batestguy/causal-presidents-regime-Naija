# Comparing tenures, part 1 — what changed *inside* a tenure

**Vintage 2026-10-18.** Written from the artifact: `registry/events/2026-10-18/events.json` (produced by
`analysis/R/06_events.R` from `analysis/specs/events.yml`), every number recomputed independently by
`tests/verify_events.py`. The rendered version of the same content is
`registry/events/2026-10-18/report.md` and the figure `registry/events/2026-10-18/event_study.svg`.

People ask "which tenure did better?". `docs/estimates.md` answers the version of that question which needs
a counterfactual — *did this tenure move the outcome* — and the answer is no: four to five administrations
against 21-23 annual observations put the minimum detectable effect at 35-99 residual standard deviations.
This stage asks the version the data **can** carry, on the one outcome domain that has monthly coverage:

> **Did monthly conflict move after each transition, relative to that series' own path in the months before
> it — and is any such move larger than what the same calculation produces at months where nothing happened?**

That is a **timing** statement. It is not a level effect, not a party effect and not a causal claim, and the
artifact says so in its own `not_claimed` block rather than only here.

---

## 1. Why this and not a tenure comparison

| What the question wants | Why this design cannot give it |
|---|---|
| "Was violence lower under tenure A than tenure B?" | Two tenures are two numbers at a national grain. Comparing them is a comparison of two means with no variance: there is no counterfactual, and annual data gives 2-4 points per tenure |
| "Did the transition *cause* the change?" | The Indian Ocean is not a control group. The transition is simultaneous with the appointment of a government, a security budget, an amnesty and an offensive |
| What it *can* say | "Reported fatalities in the 12 months after this transition were X % different from the 96 months before it, and that is larger/smaller than the same statistic at the 58 months where no transition happened" |

The design's binding constraint is stated up front and never relaxed: **four events**. Inference is by
**exhaustive placebo assignment** — every eligible month is tried as if it were a transition, with the same
windows, statistic and controls — rather than by a t-statistic that would assume four independent draws.

---

## 2. The series and the events

- **312 months**, 1999-01 → 2024-12, UCDP GED national monthly counts (fatalities and incidents).
- **25 absent months filled with zero** under the declared rule, all before 2010-01. This is the one
  discretionary step in the series: UCDP emits no row when no event was recorded, and dropping those months
  would silently turn "no reported event" into "not in the sample".
- Brent is joined from the base for the second control variant, so the series carries no other source.

| Event | Transition month | Months of history | Post window ends | Truncated by the successor |
|---|---|---|---|---|
| Yar'Adua sworn in | 2007-05 | 100 | 2010-04 | no |
| Jonathan sworn in | 2010-05 | 136 | 2015-04 | no |
| Buhari sworn in | 2015-05 | 196 | 2023-04 | no |
| Tinubu sworn in | 2023-05 | 292 | 2024-12 | **yes** (20 of 24 months exist) |

A fifth transition exists in the base and is **excluded with its reason on the artifact**: Obasanjo's
1999-05 inauguration cannot be compared because the series begins four months before it and the design needs
96 pre-months. That is where the data starts, not a modelling choice.

Each event is bound to `dim_administration_term` by `term_id`, and the verifier checks the spec's date and
`tenure_stratum` against the base — a spec whose event list drifted from the base would otherwise estimate a
transition that never happened.

---

## 3. Windows and the statistic

- **Pre-window: 96 months**, the same for every event, so the four estimates are the same calculation.
- **Post windows: 12 and 24 months**, truncated at the successor transition and at the end of the series.
- **Floor: 75 % of the requested horizon** (9 of 12 months, 18 of 24). A window below the floor is published
  as `not_estimated` with its reason and the months it had; it is never fitted, and no cell is silently
  dropped. Tinubu's 20-month h=24 window clears the floor and is published **with its truncation flag**.
- **Statistic**: Poisson ML on the count, `count ~ post + factor(month_of_year) + trend`, Newey-West (HAC)
  standard errors at 12 lags, reported as `exp(beta) - 1` — the proportional monthly shift over the post
  window. A second variant adds `log(Brent)`, because the fiscal channel reaches the states with a two-to-
  three-month lag (C-48) and a post-window shift could be the oil price rather than the transition.

---

## 4. Inference: the placebo is the null, and it is enumerated

Every eligible month — one with 96 months of history before it, enough after it, and **more than 24 months
from any real transition** — is treated as if it were a transition. 58 months (2012-06 → 2021-04) qualify.
The set is **enumerated, not sampled**: no random number generator is involved, so there is no seed and the
engine and the verifier compute the same distribution from the same data.

Two properties of that null shape how the results must be read:

- **It is not centred on zero.** Placebo mean for fatalities at h=12 is −0.390 (a 32 % *decline*): reported
  violence drifts down through the window, so the typical month already looks like a fall.
- The p-value is therefore the **tail the estimate points at** — for a rise, the share of placebos at least
  as large; for a fall, at least as small — in the add-one form `(1 + #{tail}) / (n + 1)`. It is never zero:
  with 58 placebo months the smallest attainable value is 1/59 = 0.017, and the artifact may not claim more
  resolution than that.

A magnitude test against the raw null was written first and discarded before publication: with the null
sitting at a 32 % decline it scored the largest fall in the series (Buhari 2015, −67 %) as *easily matched*
while its own left tail said the opposite. Both the rule and the reason are on the artifact
(`placebo.direction`, `placebo.direction_why`).

---

## 5. The estimates, and the two checks that decide whether they mean anything

Baseline variant, h=12, proportional shift against the **check** columns (`—` means the check could not be
run or was not applicable):

| Transition | Outcome | Shift | Placebo p | Pre-trend shift | Verdict |
|---|---|---|---|---|---|
| Yar'Adua 2007 | fatalities | −17.1 % | 0.610 | — | `check_not_available` |
| Yar'Adua 2007 | incidents | −34.3 % | 0.186 | — | `check_not_available` |
| Jonathan 2010 | fatalities | +127.7 % | 0.017 | 195.6 % | `not_interpretable_pre_trend` |
| Jonathan 2010 | incidents | +391.3 % | 0.017 | 87.6 % | **`shift_detected`** |
| Buhari 2015 | fatalities | −67.5 % | 0.017 | 83.8 % | `not_interpretable_pre_trend` |
| Buhari 2015 | incidents | −48.0 % | 0.085 | 40.4 % | `no_shift_detected` |
| Tinubu 2023 | fatalities | +76.6 % | 0.017 | 52.8 % | **`shift_detected`** |
| Tinubu 2023 | incidents | +6.7 % | 0.169 | 25.5 % | `not_interpretable_pre_trend` |

Read the verdict column, not the shift column: **two of the eight cells survive both checks**, and four of
the eight fail on the pre-trend — the same shift was already under way 24 months before the transition. The
artifact publishes the coefficient, the interval and the MDE anyway, because a reader who wants to see the
failing number should be able to.

Three further properties are published for every cell:

- **Pre-trend placebo** — the identical statistic with the post window placed 24 months *before* the event.
  Where the series does not reach back 120 months, the check is reported **`check_not_available`** with the
  months it had (Yar'Adua 2007: 100 of 120). A check that could not be run is not a pass.
- **Reporting divergence** — fatalities and incidents are fitted separately at every event, and an event
  whose two series disagree in sign is flagged. Here all four agree in sign, which is a guard, not a fix:
  UCDP GED is a reported-events archive and reporting capacity is itself regime-linked.
- **MDE beside every estimate** — e.g. Tinubu's fatalities estimate of +76.6 % sits against a minimum
  detectable shift of +55.2 %, and Yar'Adua's against +1103 %. "Not significant" and "not detectable" are
  different statements, and the second is what four events buys.

**Family-wise, the largest of the four:** Buhari 2015 is the largest fall in fatalities (−67.5 %, p = 0.017)
and Jonathan 2010 the largest rise in incidents (+391.3 %, p = 0.017), each against the same 58-month
distribution. Publishing the maximum matters because a reader looking at four estimates is looking at the
largest of them whether or not the artifact says so.

---

## 6. The party split is a description, and the artifact enforces that

| Party | Events | Median h=12 shift (fatalities) | The shifts |
|---|---|---|---|
| PDP | 2 | +55.3 % | −17.1 %, +127.7 % |
| APC | 2 | +4.6 % | −67.5 %, +76.6 % |

**No test statistic is computed**, because two events against two events has no sampling distribution and
any p-value would be a number manufactured by an assumption. `party_split.no_test_computed` is `true`, the
JSON Schema requires it to be `true`, and `tests/verify_events.py` fails if a p-value, standard error or
t-statistic field appears anywhere inside that block. The four values above are published so the reader can
see what a two-against-two comparison would be made of.

---

## 7. What this stage does not claim

Recorded on the artifact as `not_claimed` and checked by the verifier:

- a causal effect of a tenure, a party or a president on conflict;
- that conflict is measured without reporting bias;
- a pooled "tenure effect" — there is no average of the four;
- anything about health, education or the economy, which have no monthly series at all.

---

## 8. How it is verified

| Guard | What it does |
|---|---|
| `tests/verify_events.py` | Rebuilds the series from the base, binds every event to `dim_administration_term`, re-derives every window from the declared rules, **re-fits all 32 specifications** with `statsmodels` GLM/Poisson + HAC(12), re-enumerates the 58-month placebo distribution, and recomputes every p-value, verdict, pre-trend row, family-wise maximum and party median |
| Agreement | Coefficients to 1e-6; worst observed HAC standard-error gap **0.002 %** against a stated 5 % allowance |
| `scripts/validate_artifacts.py` (`check_events`) | The vintage invariant, the contract fields on every row, every cell fitted-or-declared, the pre-trend row present or the absence explained, `no_test_computed`, and the figure on disk |
| `registry/schema/events.schema.json` | The whole document against a JSON Schema — closed verdict vocabulary, `deterministic: true`, a p-value that cannot be zero |
| Break-tests | Five mutations applied to the committed artifact — a coefficient moved 2 %, a row deleted, the uncheckable pre-trend scored as a pass, a `p_value` added to the party block, the figure deleted. **All five caught** by the verifier and the contract test, each restored byte-for-byte afterwards |

`scripts/verify.sh` runs the engine and then all nine verifiers, locally and in CI.

---

## 9. What this unlocks, and what it does not

Start here when someone asks to compare tenures, and expect to say: on monthly conflict, two of eight
event-outcome cells show a shift that survives the pre-trend check, four fail it, and one event cannot be
checked at all. On everything else — health, education, the economy — there is no monthly series, so the
only route to a tenure-level statement remains a counterfactual, which is the donor-pool problem Stage 5
left open (`docs/design-memo.md`, Design C).
