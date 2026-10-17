-- **The analytical base table.** One row per (metric, month), read by the models and the app alike,
-- with nothing computed at render time (base spec section 18 [LOCKED]).
--
-- It carries four things beyond the value:
--
--   1. `value_indexed` — base spec section 8: index to 100 at January 2000, fixed anchor, both `value`
--      and `value_indexed` stored. The anchor period per metric is in `metric_anchor`, because for
--      some series January 2000 has no value and the anchor falls back; a reader can always ask
--      "100 relative to what?" and get an answer. Null wherever the value is null: an index computed
--      from a missing value would be an invented observation.
--   2. `observation_type` — observed / interpolated / unobserved. The app draws interpolated months
--      dashed and Stage 7 excludes them on a robustness axis; neither is possible unless the base says
--      which months those are.
--   3. The **tenure strata** base spec section 9 requires (PDP first/second, APC first/second) as
--      columns, so a model estimates the exposure without re-deriving it and two models cannot
--      disagree about which months are which.
--   4. `quality_status` -adjacent provenance: source and vintage per row, so a published number can be
--      traced to the retrieval that produced it (PHASES.md cross-cutting conventions).
--
-- **Month assignment.** A month belongs to the term that contains its **first day**, which is why the
-- bound is `in_month_start`/`in_month_last` rather than a naive calendar-year split: an inauguration on
-- 29 May means May's first day still falls under the outgoing administration. The month containing a
-- boundary is therefore assigned to the outgoing term and additionally flagged
-- `is_transition_month`, so a Tier-2 inherited-conditions view or a robustness axis can drop it without
-- anyone having to reconstruct the boundary dates.
--
-- Months before the first administration's span (1999-01..1999-05) keep `is_unassigned_month = true`
-- rather than being assigned to whoever was in office before the study window: they are inside the
-- spine's floor but outside the exposure, and the flag says so.
with monthly as (
    select * from {{ ref('int_metric_monthly') }}
),

anchor as (
    select
        metric_id,
        anchor_value
    from {{ ref('metric_anchor') }}
),

terms as (
    select
        term_id,
        admin_id,
        term_ordinal,
        president,
        party,
        tenure_stratum,
        term_start,
        term_end,
        case
            when extract(day from term_start) = 1
                then date_trunc('month', term_start)::DATE
            else (date_trunc('month', term_start) + INTERVAL 1 MONTH)::DATE
        end as in_month_start,
        date_trunc('month', term_end - INTERVAL 1 DAY)::DATE as in_month_last
    from {{ ref('dim_administration_term') }}
),

term_spans as (
    select * from terms
    where in_month_start <= in_month_last
),

transitions as (
    select distinct
        date_trunc('month', term_start)::DATE as period_month
    from terms
)

select
    m.metric_id,
    m.period_month,
    m.value,
    case
        when m.value is null then null
        else m.value / a.anchor_value * 100
    end as value_indexed,
    m.observation_type,
    m.native_frequency,
    m.source,
    m.vintage,

    t.term_id,
    t.admin_id,
    t.term_ordinal,
    t.president,
    t.party,
    t.tenure_stratum,
    coalesce(t.tenure_stratum = 'PDP_first', false) as pdp_first,
    coalesce(t.tenure_stratum = 'PDP_second', false) as pdp_second,
    coalesce(t.tenure_stratum = 'APC_first', false) as apc_first,
    coalesce(t.tenure_stratum = 'APC_second', false) as apc_second,
    (t.term_id is null) as is_unassigned_month,
    coalesce(tr.period_month is not null, false) as is_transition_month
from monthly m
join anchor a
    on a.metric_id = m.metric_id
left join term_spans t
    on m.period_month >= t.in_month_start
   and m.period_month <= t.in_month_last
left join transitions tr
    on tr.period_month = m.period_month
