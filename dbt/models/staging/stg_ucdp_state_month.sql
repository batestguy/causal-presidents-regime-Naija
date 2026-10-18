-- Per-state-month UCDP GED counts, typed, at their native grain — state × month × item.
--
-- The source artifact is written by `ingestion/parsers/ucdp_events.py` from the landed bulk archive
-- (`ingestion/flows/pull_ucdp.py`). It is read here rather than parsed in SQL for the same reason the
-- FAAC documents are: parsing a 250 MB CSV inside a ZIP is not a SQL operation, and the language split
-- is [LOCKED] (decisions D-05).
--
-- **A zero is a measurement, and the parser is where that is decided.** GED records events with at
-- least one fatality, so inside a month the archive covers for the country a state with no event is a
-- recorded zero, and the parser writes it explicitly instead of leaving the cell absent. A month with
-- no Nigeria event anywhere is absent from the artifact entirely — absence of records is not evidence
-- of no violence — and reaches the base as a gap rather than as a row of zeros.
--
-- **`unattributed` is a real scope here.** 47 events (632 fatalities) carry no `adm_1`: `where_prec`
-- says they are located no more precisely than the country. They are kept so the national total stays
-- complete; the state panel joins on `state_id` and therefore never picks them up, which is why the
-- national series is a sum over 38 scopes while the panel has 37 units.
--
-- `value` is an integer count in every item, so it is cast rather than left as the CSV's double:
-- a fatality count of 12.0 invites a mean of 11.6 that then gets reported as a death toll.
with raw as (
    select *
    from read_csv_auto(
        '{{ var("staging_root") }}/ucdp_state_month.csv',
        header = true
    )
)

select
    cast(state_id as integer) as state_id,
    state_name,
    state_name_published,
    strptime(period_month, '%Y-%m')::DATE as period_month,
    item,
    cast(value as integer) as value,
    unit,
    source_dataset_id,
    source_file,
    source_sha256,
    source_location,
    vintage as raw_vintage
from raw
