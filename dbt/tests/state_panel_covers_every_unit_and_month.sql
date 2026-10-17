-- A ragged panel is the classic way a difference-in-differences sample shrinks without anyone noticing:
-- unbalanced states drop out of the estimation sample and the "effect" is measured on whoever survived.
with per_state as (
    select
        state_id,
        count(*) as n_months
    from {{ ref('state_panel') }}
    group by state_id
),

spine as (
    select count(distinct period_month) as n_spine_months
    from {{ ref('fact_metric') }}
)

select
    p.state_id,
    p.n_months,
    (select n_spine_months from spine) as spine_months
from per_state p
where p.n_months <> (select n_spine_months from spine)
