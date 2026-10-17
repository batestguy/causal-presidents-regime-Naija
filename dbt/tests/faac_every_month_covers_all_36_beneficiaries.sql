-- Two invariants the FAAC parser claims per document, re-checked on the assembled table.
--
-- **36 beneficiaries per month.** The parser refuses a document that does not yield exactly 36 states,
-- because a partially read document is worse than a missing one — it looks complete. That refusal is
-- per document, and this test re-checks the property on the joined result, where a duplicate row or a
-- month that silently picked up a second publisher's stale rows would show up as a count that is not 36.
--
-- **Every FAAC state-month reaches the panel.** The panel is a left join from the grid; a failing join
-- key would quietly empty the dose while leaving `state_panel` present and the FAAC table plausible. So
-- the count check runs against the panel, not against the source.
with per_month as (
    select
        period_month,
        count(*) as n_beneficiaries,
        count(distinct state_id) as n_distinct_states
    from {{ ref('faac_state_allocation') }}
    group by period_month
),

missing_from_panel as (
    select f.state_id, f.period_month
    from {{ ref('faac_state_allocation') }} f
    left join {{ ref('state_panel') }} p
        on p.state_id = f.state_id
       and p.period_month = f.period_month
    where p.faac_gross_total_naira is null
)

select
    period_month,
    n_beneficiaries,
    n_distinct_states,
    'month does not cover 36 distinct beneficiaries' as problem
from per_month
where n_beneficiaries <> 36
   or n_distinct_states <> 36

union all

select
    period_month,
    state_id,
    state_id,
    'a FAAC state-month did not reach the panel dose column' as problem
from missing_from_panel
