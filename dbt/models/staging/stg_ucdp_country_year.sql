-- Country-year per-country counts from the landed UCDP GED archive, for the Design C donor path (C-93).
--
-- The source artifact is written by `ingestion/parsers/ucdp_events.py` from the same bulk archive that
-- builds the state × month security outcome. It is a **derived** table rather than a landed payload: the
-- archive is stored untransformed and the parser is where the aggregation is decided, so a reader can
-- reproduce every row from the archive's own `sha256` (recorded on each row, and on the parse report).
--
-- **A zero is a measurement here too.** The parser writes every pool country × every year from the
-- archive's first year, so a country the archive records no event for has zero *reported* fatalities —
-- the outcome is "reported security fatalities", and GED is a global archive. That is the same rule as
-- the state-month artifact's recorded zero, one grain up, and it is what lets a synthetic control treat
-- a peaceful comparator as a comparator rather than as a missing series.
--
-- Only pool members are written, and the pool is the one the predictor source landed; the filter below
-- keeps that single declaration authoritative.
with raw as (
    select *
    from read_csv_auto(
        '{{ var("staging_root") }}/ucdp_country_year.csv',
        header = true
    )
)

select
    country_iso3,
    country_name,
    cast(period_year as integer) as period_year,
    item as metric_id,
    cast(value as integer) as value,
    unit,
    source_dataset_id,
    source_file,
    source_sha256,
    source_location,
    vintage as raw_vintage
from raw
