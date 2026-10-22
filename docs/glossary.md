# Words this project uses, and what they mean

The answers quote the project's own passages, so the vocabulary in them is the vocabulary of the registry.
This page is the plain reading of those words. It is written once, for a reader who does not work with
statistics, and the answer layer quotes it verbatim rather than paraphrasing it. Nothing here carries a
number: a number in an answer must come from the passage that answer cites.

The answer layer reads this file at request time and shows the entries for the words that actually appear in
the answer it assembled. An entry that is edited here changes the answer immediately, which is why the
verifier checks every meaning the layer printed against the line in this file.

| Word | Plain meaning |
|---|---|
| **coefficient** | The size of the relationship the model estimated, in the outcome's own units. A coefficient of zero means "no relationship found"; a negative one means the outcome was lower where the thing being measured was higher, under the assumptions listed with it. |
| **standard error** | How much the coefficient would typically move if the same model were estimated on a different sample of the same kind. A small standard error means the number is precise, not that it is right. |
| **95% interval** | The range of values the data cannot rule out. If the range runs from a negative number to a positive one, then an effect of zero is still inside it, and the data do not establish a direction. |
| **p value** | The probability of seeing a coefficient at least this large if there were truly no relationship. It is not the probability that the finding is true, and a small p value does not make a design's assumptions hold. |
| **identifying assumption** | The one condition that has to be true for the number to mean what it claims. If the condition fails, the number still exists — it just no longer measures the thing it is named after. |
| **state-months** | One state observed in one month. A sample of this size is the states followed for a number of months, and the count is the unit the regression works in — so the precision is quoted in the same unit. |
| **state panel** | The table that follows each state over the months of the study window, one row per state per month. |
| **design** | The identification strategy — the argument for why the comparison is informative. This project has a two-way fixed-effects panel (Design A), a panel with a shock interaction (Design B), and a synthetic control (Design C). |
| **specification** | One exact combination of outcome, design and control set. The same question can have several specifications, and the robustness grid reports all of them rather than the one that looked best. |
| **estimator** | The method that turns the data into the coefficient — for example a fixed-effects regression. It is a procedure, not a finding. |
| **robustness** | Whether the finding survives reasonable changes: a different control set, a different sample, a different way of measuring the outcome. A finding that flips sign under those changes is reported as flipping, not dropped. |
| **near-zero band** | A small range around zero declared before the grid was run. A specification that lands inside it is described as near zero rather than as a positive or negative finding. |
| **per-capita** | Divided by population, so that places of different sizes can be compared. The denominator this project would need for that is typed into the schema and empty — an unmade decision, not a missing download. |
| **donor panel** | The set of candidate countries the screening step compared against Nigeria. The corpus carries no series for any of them; it carries the count and says so. |
| **out of scope** | The corpus has no passage that could answer the question — a forecast, another country, a population count, or a policy recommendation. The refusal cites the statement that says so. |
| **cannot rule out** | The list of alternative explanations the design cannot separate from the one it estimates. It is part of every answer because a number without its caveats is a claim the project has not earned. |
