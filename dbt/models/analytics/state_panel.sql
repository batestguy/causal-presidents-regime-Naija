-- The state panel: 37 units × month, carrying **one** dose column that is populated and the rest
-- declared empty.
--
-- PHASES.md Stage 4 asks for a state panel joining FAAC (D1), state IGR (D2), conflict-event
-- attribution and whichever health/education series survived Stage 1. Of those four:
--
--   * **FAAC (D1) is now landed** and the nominal allocation is on the panel, per state-month,
--     published by the document the parser read. It is populated only for the months a publisher
--     covers — 2016-12 onward — and every row says which case it is.
--   * **State IGR (D2)** is not landed, so `d2_faac_share_of_state_revenue` is empty.
--   * **A population denominator** is not landed and is not even a data question — NBS projections and
--     the World Bank's population series diverge, and choosing one is a decision (X-09). So
--     `d1_faac_per_capita` is empty while its numerator now exists, which is the honest shape: the
--     per-capita column is one join away and the join is a decision, not a fetch.
--   * **Fatalities and incidents** are landed from UCDP GED, which answers keyless from its bulk
--     archive (C-14 recorded the *API* blocker, not a licence one — see C-45). They are joined at
--     state-month grain and carry `security_status`, so a zero and an uncovered month stay distinct.
--
-- The declared gaps and what each needs are in `analysis/specs/harmonisation.yml` `declared_gaps`, and
-- `dose_note` points at the one in force for each row rather than paraphrasing it here.
--
-- ## `dose_status` is per row, not per table
--
-- A table-level "the doses are empty" flag was the earlier shape and it is wrong now that one dose is
-- populated: it would force a single label onto rows that are in three genuinely different states.
--
--   * `observed`      — a FAAC document covers this state-month and the nominal dose is on the row.
--   * `not_covered`   — inside the publishers' span but no document carries this month (the four months
--                       the OAGF archive is missing, and the pre-2016-12 months of the NBS elibrary).
--                       Different from a gap: the series exists either side of it.
--   * `declared_gap`  — before either publisher's first document. No source is expected to produce it.
--
-- The FCT's status is `declared_gap` at every month for a different reason and carries that reason in
-- `dose_note`: Table III distributes the account among 36 beneficiaries and the FCT's own line is
-- funded from the federal share, so the FCT is not a unit of this distribution at all.
--
-- ## Is the dose gated? Yes, and the gate is not a formality
--
-- `dose_gated` and `dose_gate_status` come from the Stage 3 report itself (`stg_quality_series`), not from
-- a flag set by hand. The FAAC series is gated per state and in national aggregate at monthly grain, and
-- every one of those series comes back **flagged**: the dose moves more than the declared 50 % in a month
-- nine or ten times per state. Most of those months fire at all 36 states at once, which is a movement of
-- the distribution rather than a per-state extraction error — the documents reconcile against their own
-- Total rows (see `tests/verify_faac.py`). The flag is therefore a review prompt that travels with the
-- series, not a defect in it, and the panel reports it instead of rounding it to `ok`.
--
-- Before the Stage 3 adapter existed this column was a hard-coded `false`, because the gate flow walked
-- `data/raw` and every page file was expected to be JSON. Landing a document source made that walk die on
-- a PDF, so the panel correctly said "ungated" while the gate could not have produced a result either way.
with states as (
    select * from {{ ref('dim_state') }}
),

months as (
    select distinct period_month from {{ ref('int_metric_monthly') }}
),

grid as (
    select
        s.state_id,
        s.state_name,
        s.zone,
        m.period_month
    from states s
    cross join months m
),

dose as (
    select
        state_id,
        period_month,
        gross_total,
        share_of_state_pool,
        publisher,
        is_cross_checked,
        cross_check_rel_diff,
        source_file
    from {{ ref('faac_state_allocation') }}
),

span as (
    select
        min(period_month) as first_covered_month,
        max(period_month) as last_covered_month
    from dose
),

-- The Stage 3 result for the dose, per series. Joined on the series key rather than on a metric-wide
-- aggregate: a panel row is one state's dose, so it needs that state's gate result.
gate as (
    select
        scope as state_name,
        quality_status,
        quality_vintage
    from {{ ref('stg_quality_series') }}
    where source = 'faac'
      and metric_id = 'faac_gross_total'
),

-- The security outcome. `not_covered` rows join too — with a NULL value and their own status — because
-- dropping them would collapse "the archive records nothing for this month" into `declared_gap` and
-- lose the difference between a hole and the end of the series. What must never happen is a
-- `not_covered` month arriving as a **zero**, and it does not: the value columns are null on those rows.
security as (
    select
        state_id,
        period_month,
        fatalities,
        incidents,
        fatalities_civilians,
        security_status,
        security_gated,
        security_gate_status,
        security_note
    from {{ ref('ucdp_state_month') }}
)

select
    g.state_id,
    g.state_name,
    g.zone,
    g.period_month,
    d.gross_total as faac_gross_total_naira,
    d.share_of_state_pool as faac_share_of_state_pool,
    d.publisher as faac_publisher,
    d.is_cross_checked as faac_is_cross_checked,
    d.cross_check_rel_diff as faac_cross_check_rel_diff,
    d.source_file as faac_source_file,
    (q.quality_status is not null) as dose_gated,
    q.quality_status as dose_gate_status,
    q.quality_vintage as dose_gate_vintage,
    -- Populated only where a state population denominator is chosen (X-09). The numerator is present
    -- above, so this column stays empty because a decision is unmade, not because a source is missing.
    null::DOUBLE as d1_faac_per_capita,
    null::DOUBLE as d2_faac_share_of_state_revenue,
    null::DOUBLE as population_denominator,
    s.fatalities,
    s.incidents,
    s.fatalities_civilians,
    s.security_gated,
    s.security_gate_status,
    coalesce(s.security_status, 'declared_gap') as security_status,
    case
        when g.state_name = 'FCT' then 'declared_gap'
        when d.gross_total is not null then 'observed'
        when g.period_month between (select first_covered_month from span)
                               and (select last_covered_month from span) then 'not_covered'
        else 'declared_gap'
    end as dose_status,
    case
        when g.state_name = 'FCT' then
            'Table III distributes among 36 beneficiaries; the FCT is funded from the federal share, so '
            'it is not a unit of this distribution (declared in analysis/specs/harmonisation.yml)'
        when d.gross_total is not null and not d.is_cross_checked then
            'single-publisher month: only one publication carries it, so there is no independent check '
            'for this state-month'
        when d.gross_total is not null then
            'nominal FAAC gross allocation (statutory + 13% derivation); Stage 3 gated it and flagged '
            'the month as a spike (see dose_gate_status); the two publications disagree on this '
            'state-month — see docs/decisions.md C-39'
        when g.period_month between (select first_covered_month from span)
                               and (select last_covered_month from span) then
            'inside the publishers'' span but no document carries this month — a hole in the archive, '
            'not an absence of the series'
        else
            'before either publisher''s first document; no source is expected to produce it'
    end as dose_note
from grid g
left join dose d
    on d.state_id = g.state_id
   and d.period_month = g.period_month
left join gate q
    on q.state_name = g.state_name
left join security s
    on s.state_id = g.state_id
   and s.period_month = g.period_month
