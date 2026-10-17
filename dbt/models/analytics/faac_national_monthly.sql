-- The national monthly FAAC allocation to the 36 states — the fiscal transfer channel as a national
-- series, so it can sit on the same spine as every other metric.
--
-- This is the series base spec §9's Tier-3 system needs: the system is `Y + log Brent + FAAC + FX +
-- lags + trend`, and Stage 5 recorded FAAC as *absent from the metric catalogue* so the testable system
-- had to be reduced to `{Y, log(oil), fx}`, with that deviation travelling onto every Design B card.
-- The series now exists. Two things follow, and it is worth being exact about which is which:
--
--   * **The acquisition is done.** The catalogue entry can be made, because the data behind it now
--     exists and reconciles to each document's own Total row.
--   * **It is not yet on the metric spine, and deliberately not.** `dim_metric`'s contract is that a
--     metric's `native_frequency` and `quality_status` come from the Stage 3 report, and PHASES.md's
--     Stage 3 exit criterion is that *no series reaches Stage 4 without a gate result*. A metric added
--     here would be the one column in `dim_metric` with no gate behind it. So the series is built and
--     reconciled, and the catalogue entry plus its Stage 3 gate are the next step rather than a shortcut
--     taken now. The Tier-3 gate therefore moves from `faac_absent_from_catalogue` to
--     `faac_ungated_and_too_short_at_outcome_grain` — a different, more honest blocker, not the removal
--     of one: the series begins 2016-12, so an annual alignment gives 10 calendar years of FAAC against
--     the 20-observation floor Johansen needs.
--
-- The aggregation rule is a sum over states, and it is stated because the alternative is not
-- unreasonable: a per-capita or a real-terms series would be the better quantity for a model, and both
-- need the state population denominator that `analysis/specs/harmonisation.yml` records as a decision
-- not yet made (X-09). The nominal sum is the quantity the documents publish, so it is what is built.
--
-- `n_beneficiaries` travels with every row so the aggregate is auditable: a month assembled from 36
-- states is a different object from a month assembled from 20, and the difference would otherwise be
-- invisible in a sum. `max_cross_check_rel_diff` is carried for the same reason — it is the largest
-- disagreement between the two publications for that month, and it is what makes the dose's
-- publisher-dependence visible at the national grain too.
select
    period_month,
    sum(gross_total) as gross_total_naira,
    count(*) as n_beneficiaries,
    count(*) filter (where publisher = 'oagf') as n_beneficiaries_from_primary,
    count(*) filter (where is_cross_checked) as n_beneficiaries_cross_checked,
    max(cross_check_rel_diff) as max_cross_check_rel_diff,
    count(*) filter (where n_lgcs is not null) as n_beneficiaries_with_lgc_count
from {{ ref('faac_state_allocation') }}
group by 1
