-- The administration spine — base spec section 7 [LOCKED], five rows.
--
-- The five rows are as the base spec defines them, including the one row that covers two terms
-- (Obasanjo 1999-2007, Buhari 2015-2023). Term-level splitting is a separate model
-- (`dim_administration_term`), because collapsing the two would break a LOCKED table's shape; the
-- party-by-tenure strata the base spec's section 9 requires live there.
--
-- **The span rule.** The base spec's `end_date` is a handover date, not a last-possible-day: four of
-- the five boundaries have `end_date` equal to the next administration's `start_date`, and exactly one
-- has a one-day gap (Yar'Adua `end_date` 2010-05-05, Jonathan sworn 2010-05-06 — PHASES.md Stage 4:
-- the boundary must be a single decided date, acting from 2010-02-09 and sworn in 2010-05-06). A table
-- written as closed intervals would therefore overlap on four boundaries and leave a one-day hole on
-- the fifth, so the effective span is **half-open**: `[start_date, next_start_date)`, falling back to
-- `end_date` only for the final administration. `end_date` is retained unchanged beside it so the base
-- spec's own field is still there to read.
--
-- `oil_price_at_start` comes from the oil series rather than being typed in, and it comes in two forms
-- on purpose: the price **on the start date** (daily, may be null on a holiday) and the **month mean**
-- (the frozen Stage 3 resampling rule). The base spec asks for "Brent crude, USD/barrel" without saying
-- which, and the two answer different questions; both are exposed and neither is silently chosen.
with spine as (
    select
        admin_id,
        president,
        party,
        start_date::DATE as start_date,
        end_date::DATE as end_date,
        n_terms,
        notes
    from {{ ref('raw_administration') }}
),

ordered as (
    select
        *,
        lead(start_date) over (order by start_date) as next_start_date
    from spine
),

oil_daily as (
    select observation_date, value
    from {{ ref('stg_fred_daily') }}
    where metric_id = 'oil'
),

oil_monthly as (
    select period_month, value
    from {{ ref('stg_fred_monthly') }}
    where metric_id = 'oil'
)

select
    o.admin_id,
    o.president,
    o.party,
    o.start_date,
    o.end_date,
    (o.end_date is null) as is_incumbent,
    coalesce(o.next_start_date, o.end_date, DATE '9999-12-31') as end_date_effective,
    (o.next_start_date is not null) as has_successor,
    o.n_terms,
    o.notes,
    date_trunc('month', o.start_date)::DATE as start_month,
    od.value as oil_price_on_start_date,
    om.value as oil_price_at_start_month_mean,
    om.period_month as oil_price_start_month
from ordered o
left join oil_daily od
    on od.observation_date = o.start_date
left join oil_monthly om
    on om.period_month = date_trunc('month', o.start_date)::DATE
