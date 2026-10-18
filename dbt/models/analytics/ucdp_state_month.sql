-- The state × month security outcome: fatalities, incidents and civilian fatalities, with the Stage 3
-- gate result travelling on every row.
--
-- This is the outcome Family A lacked. Stage 5 dropped the family for two reasons — the dose was
-- absent on the *per-capita* axis (X-09) and there was **no state-attributed outcome at all** — and it
-- recorded the security series as credential-blocked (C-13/C-14). The credential was only ever needed
-- for the *API*: UCDP's bulk archive answers keyless and is CC-BY, so the blocker was a route, not a
-- licence, and the state-month outcome now exists.
--
-- ## The three statuses are not the same kind of nothing
--
--   * `observed`     — the archive covers this month for the country and recorded this value, which may
--                      legitimately be zero. 80 % of state-months are zero fatalities; that is the
--                      phenomenon, not a hole in it.
--   * `not_covered`  — inside the archive's span, but the month carries no Nigeria event anywhere, so
--                      the parser emits no row (six such months in 1999-2009, none after). Absence of
--                      records, not evidence of zero.
--   * `declared_gap` — outside the archive's span: before 1990-09, or after 2024-12 (GED 25.1 ends
--                      there). No source is expected to produce it, and a design reading the panel must
--                      see the end of the series rather than an endless row of zeros.
--
-- The distinction matters for the estimator: a zero and an unobserved month both render as "nothing
-- happened" on a chart, and one of them is a measurement.
--
-- The gate columns are read from the Stage 3 report per state (`metric_id = 'fatalities'`), the way the
-- FAAC dose reads its own, so a state whose series was flagged does not arrive at a model looking clean.
with typed as (
    select * from {{ ref('stg_ucdp_state_month') }}
),

pivoted as (
    select
        state_id,
        state_name,
        period_month,
        max(case when item = 'fatalities' then value end) as fatalities,
        max(case when item = 'incidents' then value end) as incidents,
        max(case when item = 'fatalities_civilians' then value end) as fatalities_civilians,
        max(source_dataset_id) as source_dataset_id,
        max(source_file) as source_file,
        max(source_sha256) as source_sha256,
        max(raw_vintage) as raw_vintage
    from typed
    where state_id is not null
    group by 1, 2, 3
),

span as (
    select
        min(period_month) as first_month,
        max(period_month) as last_month
    from typed
),

gate as (
    select
        scope as state_name,
        quality_status,
        quality_vintage
    from {{ ref('stg_quality_series') }}
    where source = 'ucdp'
      and metric_id = 'fatalities'
      and scope <> 'national'
)

select
    p.state_id,
    p.state_name,
    p.period_month,
    p.fatalities,
    p.incidents,
    p.fatalities_civilians,
    true as security_observed,
    'observed' as security_status,
    (q.quality_status is not null) as security_gated,
    q.quality_status as security_gate_status,
    q.quality_vintage as security_gate_vintage,
    p.source_dataset_id,
    p.source_file,
    p.source_sha256,
    p.raw_vintage,
    'UCDP GED, state-attributed (adm_1); month of date_start. Zero means the archive covered the state-month and recorded no fatal event.'
        as security_note
from pivoted p
left join gate q
    on q.state_name = p.state_name

union all

-- The months inside the archive's span that carry no Nigeria event anywhere: a declared hole, not a
-- zero. Emitted per unit so the panel is rectangular and the status says which kind of nothing it is.
select
    s.state_id,
    s.state_name,
    g.period_month,
    null::INTEGER as fatalities,
    null::INTEGER as incidents,
    null::INTEGER as fatalities_civilians,
    false as security_observed,
    'not_covered' as security_status,
    false as security_gated,
    null::VARCHAR as security_gate_status,
    null::VARCHAR as security_gate_vintage,
    null::VARCHAR as source_dataset_id,
    null::VARCHAR as source_file,
    null::VARCHAR as source_sha256,
    null::VARCHAR as raw_vintage,
    'inside the archive''s span but the month carries no Nigeria event anywhere — absence of records, not a zero'
        as security_note
from {{ ref('dim_state') }} s
cross join span b
cross join generate_series(b.first_month, b.last_month, INTERVAL 1 MONTH) as g(period_month)
where not exists (
    select 1
    from pivoted p
    where p.state_id = s.state_id
      and p.period_month = g.period_month::DATE
)
