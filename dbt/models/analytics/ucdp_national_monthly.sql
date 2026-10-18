-- National monthly security counts — the series Design B and the app read.
--
-- The sum is over **38 scopes**: the 37 units plus `unattributed`. That is deliberate and it is the
-- difference between a national total and a total of the states. 47 Nigeria events in this vintage
-- (632 fatalities) are located no more precisely than the country; leaving them out would make the
-- national series quietly 0.9 % too small on fatalities and would make the 1990s look emptier than the
-- archive says. `n_scopes` travels with every row so the 38 is visible rather than implied, the way
-- `n_beneficiaries` does for the FAAC national series.
--
-- Only months the archive covers are emitted — a month with no Nigeria event at all is absent, not
-- zero. `security_status` in `ucdp_state_month` records which kind of nothing each month is.
with per_scope as (
    select
        state_name,
        period_month,
        max(case when item = 'fatalities' then value end) as fatalities,
        max(case when item = 'incidents' then value end) as incidents,
        max(case when item = 'fatalities_civilians' then value end) as fatalities_civilians,
        max(raw_vintage) as raw_vintage,
        max(source_dataset_id) as source_dataset_id
    from {{ ref('stg_ucdp_state_month') }}
    group by 1, 2
)

select
    period_month,
    sum(fatalities)::BIGINT as fatalities,
    sum(incidents)::BIGINT as incidents,
    sum(fatalities_civilians)::BIGINT as fatalities_civilians,
    count(*) as n_scopes,
    max(raw_vintage) as vintage,
    max(source_dataset_id) as source_dataset_id
from per_scope
group by 1
