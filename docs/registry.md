# What the app reads — Stage 8, the registry

**Vintage 2026-10-17.** Written from the artifacts: `registry/dags/` (36 cards + `index.json`,
`analysis/R/05_registry.R` over `analysis/specs/registry.yml`), with every number recomputed independently
by `tests/verify_registry.py` and the counts re-derived from the cards by `scripts/validate_artifacts.py`.
Stages 6 and 7 are in [`docs/estimates.md`](estimates.md) and [`docs/robustness.md`](robustness.md).

Stage 8's exit criterion is that **Stage 9 can be built without opening R**. That is a statement about where
the numbers live, not about how many there are: the app may read `registry/dags/*.json` and nothing else, so
every number it can display has to be on a card, beside the assumption it rests on, with the artifact it was
copied from named. This stage is the copying.

---

## 1. The problem this layer exists to solve

The registry is 36 cards (12 outcomes × 3 identification designs). Stage 6 published 12 specifications, and
they **do not line up with the cards** the way a reader would guess:

| Design | Published | About what | Cards that can carry it |
|---|---|---|---|
| A — state dose-response | 3 specifications | a catalogue outcome each: `fatalities`, `incidents`, `fatalities_civilians` | **2** — the catalogue holds cards for the first two; `fatalities_civilians` is a UCDP item inside the `fatalities` outcome, so it has no card |
| B — national transmission | 9 specifications | **the national FAAC channel** (cumulative log change in state FAAC), not any outcome a card is about | **0** — on every B card, FAAC is a *mediator* node |
| C — synthetic control | 4 windows, none identified | **the `u5mr` path against a synthetic Nigeria**, published in its own artifact with its placebos | **0** — a synthetic control has no interval, and no point estimate ships without one |

So the honest registry is **2 cards carrying a number and 34 saying why they do not**. That ratio is the
finding, not an accident of assembly, and the layer is built so it cannot be quietly improved: the Design A
mapping is declared with both of its counts, and the engine refuses to write when either changes.

## 2. What a card carries, and what it refuses to

An `estimated` card carries the specification copied field for field from
`registry/estimates/<vintage>/estimates.json` — coefficient, standard error, interval, p-value, sample size,
estimator, formula, covariance, window — plus three things that keep it honest:

- **`the_number_is_for_this_card`** — true only when the specification's own `outcome` is this card's
  outcome. The mapping never produces `false`, which is the point: if the layer ever attached a number to a
  card it was not about, the app would render that as false rather than as a number.
- **the Stage 6 verdict and the check that decided it** — `estimated_not_identified` for Design A, with the
  failed check named. The two `estimated` cards are also cards whose Stage 5 pre-check **failed**: an
  estimate exists for those pairs and the design still does not pass its own gate, and both statements
  travel together rather than one being dropped as inconvenient.
- **the Stage 7 summary for the card's own axis level** — `fatalities` sits at 13 positive against 14
  negative across the grid's 27 specifications sharing that outcome; `incidents` at 25 against 2. "This
  number is one cell of a grid" is on the card rather than in a document the reader has to find.

A `not_estimated` card carries a reason from a **closed set**, so the absence of an estimate is never silent:

| Reason | Cards | What it means |
|---|---|---|
| `outcome_series_absent` | 12 | the outcome has no usable series, so no pre-check ran for this pair — a declared gap, not a null result |
| `no_specification_declared` | 10 | Stage 5 ran a pre-check; Stage 6 declared no specification for this pair. Nothing about the estimate stage says this question was asked and answered |
| `design_result_is_channel_level` | 9 | Design B has a published result, and it is about the channel the design rests on, not about this card's outcome |
| `design_not_run` | 2 | Design C was not run for this outcome — the gate refused it; the reason is on the index and in the estimates artifact |
| `design_estimated_not_identified` | 1 | Design C was run for this outcome and no window survived its placebos; the gap and the placebos are in `registry/design_c/`, and no interval exists to put on a card |

## 3. The two design-level results, on the index

`index.json → published_results` carries one entry per design that reached a verdict, because two of them are
**not about any single card** and showing them twelve times would be the most misleading thing this layer
could do:

- **`B` is declared `result_is_card_level: false`**, with `result_outcome` naming the channel. The nine B
  specifications are published there — every number, interval and sample size — together with the
  design-level sensitivity: Oster's δ = −44.04 read in the case it is actually in, the in-time placebo at
  **p = 0.0625**, and the HAC bandwidth table.
- **`A` is card-level**, carrying its three specifications (including the one no card holds), the
  `estimated_not_identified` verdict and the failed check, the Stage 7 support counts (45 positive / 36
  negative), five majority sign-flip levels and the near-zero band. Its sensitivity blocks — Oster on the
  linear analogue, the 36 leave-one-state-out refits — are computed on the **preferred** specification, so
  they are labelled design-level evidence rather than attached to a card that is not that specification.
- **`C`** carries the non-run and its reason.

The index also carries `registry.card_estimate_counts`, so the app can state the ratio itself, and the index's
`layer` string is now `causal DAGs + published results (the app's data contract)`. Until this stage it read
**"no estimates attached"** — the strongest claim in the repository, and one the app would have believed.

## 4. Reproducing it, and the ordering trap

```bash
Rscript analysis/R/01_build_dags.R     # cards (Stage 5-6 attachment point)
Rscript analysis/R/03_estimate.R       # Stage 6 estimates
Rscript analysis/R/04_robustness.R     # Stage 7 grid
Rscript analysis/R/05_registry.R       # Stage 8: assemble onto the cards + the index
python tests/verify_registry.py        # re-derive the mapping and every number independently
scripts/verify.sh                      # the whole chain, in that order
```

**The ordering trap.** `analysis/R/01_build_dags.R` writes the cards wholesale, which **resets the estimate
block**. That is deliberate — a card generator that preserved a block it does not understand would make the
registry un-rebuildable — but it means the assembler must run after the generator. Two checks catch a broken
ordering rather than letting it look green: `validate_artifacts.py` compares the index's counts against the
cards on disk, and `verify_registry.py` fails when a card that should carry a number does not.

## 5. What this layer does not claim

- **A number on a card is not a passing design.** Two cards carry an estimate and **1 of 36** passes its
  pre-check — and it is not one of them: the pass is `u5mr` under Design C, whose windows were all estimated
  and none identified. The card shows both, and the synthetic control's gap stays on its own artifact because
  it has no interval to publish.
- **The four Design B cards with no series are not "no effect".** `outcome_series_absent` is a statement
  about the data, not about the policy.
- **Nothing here re-estimates anything.** `05_registry.R` fits nothing: it copies published fields and stops
  if the counts change. If a number looks wrong, the fix belongs in Stage 6 or 7 and the registry is
  re-assembled.
- **The registry is not the narrative.** PHASES.md Stage 8 says the card wins when the two disagree, and that
  is enforceable only as far as the narrative is machine-readable; where it is (the summary counts in
  `docs/estimates.md`), the verifier checks it.
