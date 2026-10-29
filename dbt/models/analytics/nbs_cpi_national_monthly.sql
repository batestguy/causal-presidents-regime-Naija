-- National monthly CPI — the composite index and its published measures, wide.
--
-- One row per month, 1995-01 to 2024-10 (the publisher's listing ends with the October-2024 report).
-- This is the same relationship the FAAC national model records: the acquisition is done and the series
-- is Stage 3 gated (both gated measures are `ok` in `registry/quality/2026-10-29`), but it is not on the
-- metric spine, and deliberately not — a `dim_metric` entry would make this the base's inflation metric
-- while the catalogued `cpi_yoy` is an annual World Bank series (C-30), and choosing between two
-- inflation references is an outcome decision for a design, not a modelling convenience. Until a
-- specification declares which one it reads, both exist beside each other, honestly labelled.
--
-- All four measures are pivoted from `stg_nbs_cpi_monthly` rather than summed or transformed: the
-- publisher publishes the 12-month average and the two changes derived from the level, and recomputing
-- them here would be a second computation of a published quantity — the thing the site's "the card wins"
-- rule exists to stop.
--
-- `n_items` travels with every row so a month assembled from all four measures is distinguishable from
-- one assembled from fewer (the 1995-01 row has only the level: the changes need a prior month to exist).
with items as (
    select
        period_month,
        max(case when item = 'cpi_index' then value end) as cpi_index,
        max(case when item = 'cpi_12m_avg' then value end) as cpi_12m_avg,
        max(case when item = 'cpi_mom_pct' then value end) as cpi_mom_pct,
        max(case when item = 'cpi_yoy_pct' then value end) as cpi_yoy_pct,
        count(*) as n_items,
        max(raw_vintage) as vintage,
        max(source_dataset_id) as source_dataset_id
    from {{ ref('stg_nbs_cpi_monthly') }}
    group by 1
)

select
    period_month,
    cpi_index,
    cpi_12m_avg,
    cpi_mom_pct,
    cpi_yoy_pct,
    n_items,
    vintage,
    source_dataset_id
from items
