-- The shock bands base spec section 8 requires shaded on every view.
--
-- They are a dimension, not a hard-coded list in the chart, so the app, the model cards and the
-- specification curve all shade the same three windows and a new shock is added in one place.
--
-- PHASES.md Stage 5 asks whether the 2016, 2020 and 2023 windows are "visible in the data rather than
-- assumed" — that check is a diagnostic against these bands, which is only possible if the bands have
-- machine-readable month bounds, hence `start_month`/`end_month`/`n_months` alongside the dates.
select
    shock_id,
    label,
    start_date::DATE as start_date,
    end_date::DATE as end_date,
    date_trunc('month', start_date::DATE)::DATE as start_month,
    date_trunc('month', end_date::DATE)::DATE as end_month,
    (datediff('month', start_date::DATE, end_date::DATE) + 1) as n_months,
    note
from {{ ref('raw_shock_bands') }}
