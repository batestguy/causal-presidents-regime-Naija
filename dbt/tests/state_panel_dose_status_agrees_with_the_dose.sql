-- The panel's dose status and its dose columns have to agree, in both directions.
--
-- The earlier version of this test asserted that every row was `declared_gap` with an empty dose, which
-- was correct while nothing was landed and became a lie the moment the FAAC parser arrived. What is
-- left is the invariant that survives the landing:
--
--   * a row with a populated dose must say `observed` — an empty column labelled `observed` reads as a
--     month the state received nothing, which is the opposite of what it means;
--   * a row with no dose must NOT say `observed`, for the same reason in reverse;
--   * the FCT has no dose at any month, because Table III distributes among 36 beneficiaries and the
--     FCT's line in the federal share is not this distribution;
--   * the status is one of the three declared values — an unhandled case must fail here rather than
--     reach the app as a fourth, undocumented state.
select
    state_id,
    state_name,
    period_month,
    dose_status,
    faac_gross_total_naira
from {{ ref('state_panel') }}
where dose_status not in ('observed', 'not_covered', 'declared_gap')
   or (faac_gross_total_naira is not null and dose_status <> 'observed')
   or (faac_gross_total_naira is null and dose_status = 'observed')
   or (state_name = 'FCT' and faac_gross_total_naira is not null)

union all

-- The other half of the FCT rule: it must be a declared gap and not merely absent, because an absent
-- row is indistinguishable from a failed join.
select
    state_id,
    state_name,
    period_month,
    dose_status,
    faac_gross_total_naira
from {{ ref('state_panel') }}
where state_name = 'FCT'
  and dose_status <> 'declared_gap'
