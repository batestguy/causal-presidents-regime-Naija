-- Term-level administration spans — the exposure the models actually use.
--
-- Base spec section 9 is [LOCKED]: "Present party effects stratified by tenure (PDP first term, PDP
-- second term, APC first term, APC second term) rather than aggregating. Literature suggests first-
-- and second-term effects differ systematically." and `docs/dags.md` names Design B's exposure node
-- `admin` / "Administration (party × tenure)".
--
-- **How the four strata are read (decision M-11).** "First/second term" is the *president's own* term
-- in office, not the party's ordinal presidential term. Under the alternative reading — PDP's first
-- term, PDP's second term — PDP's four consecutive terms (1999-2003, 2003-2007, 2007-2011, 2011-2015)
-- would leave 2007-2015 outside all four strata entirely, and the exposure could not be represented
-- for two of the five administrations. Under this reading the four strata cover the whole study window
-- with no residual category:
--
--   PDP_first   1999-05..2003-05 (Obasanjo I) · 2007-05..2010-05 (Yar'Adua I) · 2010-05..2015-05 (Jonathan I)
--   PDP_second  2003-05..2007-05 (Obasanjo II)
--   APC_first   2015-05..2019-05 (Buhari I) · 2023-05..present (Tinubu I)
--   APC_second  2019-05..2023-05 (Buhari II)
--
-- Nigerian presidential terms run four years from a 29 May inauguration, so a term break inside an
-- administration (Obasanjo, Buhari — the two rows the base spec marks "Two terms") is placed at
-- `start_date + 4 years`. A single-term administration gets one row, and the term ends where the
-- administration ends — including Jonathan's five years, which is a completed inherited term plus his
-- own and is not stretched to fit a four-year template.
--
-- `term_end` is also half-open, for the same reason as `dim_administration`.
with administrations as (
    select * from {{ ref('dim_administration') }}
),

terms as (
    select
        admin_id,
        president,
        party,
        start_date,
        end_date_effective,
        n_terms,
        unnest(generate_series(1, n_terms)) as term_ordinal
    from administrations
),

bounds as (
    select
        t.*,
        (t.start_date + to_years(4 * (t.term_ordinal - 1)))::DATE as term_start,
        case
            when t.term_ordinal < t.n_terms
                then (t.start_date + to_years(4 * t.term_ordinal))::DATE
            else t.end_date_effective
        end as term_end
    from terms t
),

-- The term's own start price, not the administration's. Obasanjo's second term began in May 2003 at
-- roughly $26 a barrel; reporting the 1999 price against it would be a silent error in exactly the
-- column a reader would use to sanity-check an oil-adjusted estimate.
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
    (b.admin_id * 10 + b.term_ordinal) as term_id,
    b.admin_id,
    b.term_ordinal,
    b.president,
    b.party,
    b.term_start,
    b.term_end,
    b.term_end = DATE '9999-12-31' as is_open_ended,
    b.party || case when b.term_ordinal = 1 then '_first' else '_second' end as tenure_stratum,
    b.n_terms,
    date_trunc('month', b.term_start)::DATE as term_start_month,
    date_trunc('month', b.term_end)::DATE as term_end_month,
    od.value as oil_price_on_term_start_date,
    om.value as oil_price_at_term_start_month_mean
from bounds b
join administrations a
    on a.admin_id = b.admin_id
left join oil_daily od
    on od.observation_date = b.term_start
left join oil_monthly om
    on om.period_month = date_trunc('month', b.term_start)::DATE
order by b.term_start
