-- Daily Brent -> monthly, using the rule Stage 3 froze. **Reuse, not re-choice.**
--
-- `analysis/specs/quality.yml` declares this exact resampling as an input:
--
--     rule: mean_of_daily_observations
--     reason: the mean of the days actually quoted in a month, chosen over month-end (an arbitrary
--             single day, and exactly the day missing on a holiday) and over the sum (which scales
--             with the number of trading days rather than the price level)
--
-- PHASES.md Stage 2 requires the rule to be frozen "because changing it later changes every adjusted
-- estimate". Stage 4 therefore reuses it and `tests/verify_harmonisation.py` recomputes this series
-- from the raw payload under the same rule and fails if they disagree — so a future edit here that
-- changed the rule (to month-end, or to a sum) would be caught rather than quietly propagate into
-- every oil-adjusted estimate.
--
-- `n_daily_observations` is kept on every row so the resample is auditable: a month averaging three
-- quotes is a different object from a month averaging 23, and the 2023 shock window is exactly where
-- that matters (PHASES.md risk: a monthly mean of a daily price understates within-month volatility).
select
    metric_id,
    vintage,
    dataset_id,
    source,
    date_trunc('month', observation_date)::DATE as period_month,
    avg(value) as value,
    count(*) as n_daily_observations,
    min(observation_date) as first_observation_date,
    max(observation_date) as last_observation_date
from {{ ref('stg_fred_daily') }}
where value is not null
group by 1, 2, 3, 4, 5
