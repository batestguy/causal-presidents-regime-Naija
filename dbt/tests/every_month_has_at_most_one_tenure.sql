-- Two failures this catches, both of which would bias a party-by-tenure estimate rather than break it
-- loudly:
--
--   * a month claimed by two terms, which duplicates it in the fact table and weights it twice;
--   * a month claimed by none inside the study window, which silently drops it from every model — the
--     exact failure the half-open span rule in `dim_administration_term` exists to prevent.
with per_month as (
    select
        period_month,
        count(distinct term_id) as n_terms
    from {{ ref('fact_metric') }}
    group by period_month
),

double_assigned as (
    select period_month, 'claimed by more than one term' as problem
    from per_month
    where n_terms > 1
),

unassigned_inside_window as (
    select distinct period_month, 'unassigned inside the study window' as problem
    from {{ ref('fact_metric') }}
    where is_unassigned_month
      and period_month >= DATE '1999-06-01'
)

select * from double_assigned
union all
select * from unassigned_inside_window
