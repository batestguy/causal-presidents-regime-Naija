-- NBS monthly CPI observations, typed, at their native grain — national × month × item.
--
-- The source artifact is written by `ingestion/parsers/nbs_cpi.py` from the landed workbook
-- (`ingestion/flows/pull_nbs_cpi.py`). It is read here rather than parsed in SQL for the same reason
-- the UCDP and FAAC artifacts are: parsing a spreadsheet's merged header blocks is not a SQL operation,
-- and the language split is [LOCKED] (decisions D-05).
--
-- **One scope.** The composite index the parser reads is the national "All Items" block of the
-- workbook's Table 1, so every row is `national` and the model does not pretend to a state grain the
-- source does not give (NBS publishes a state CPI, and that would be its own source with its own
-- declaration, not a column added here).
--
-- **The series ends where the publisher ends, at 2024-10.** The elibrary's CPI listing stops with the
-- October-2024 report, and the months after it are absent — not null: their absence is why the series
-- carries no January-2025 rebasing (C-27 applies from 2025-01, and this series never reaches it).
-- A trailing gap to the spine's 2026-10 is a fact about NBS's listing, recorded in the gate's
-- `coverage.trail_gap_months` rather than in an extra row here.
--
-- `value` is a real in every item but means different things per item — an index level for
-- `cpi_index`/`cpi_12m_avg`, a percentage change for `cpi_mom_pct`/`cpi_yoy_pct` — so the unit column
-- travels and is not normalised away.
with raw as (
    select *
    from read_csv_auto(
        '{{ var("staging_root") }}/nbs_cpi_monthly.csv',
        header = true
    )
)

select
    scope,
    strptime(period_month, '%Y-%m')::DATE as period_month,
    item,
    value::DOUBLE as value,
    unit,
    label,
    source_dataset_id,
    source_file,
    source_sha256,
    source_location,
    vintage as raw_vintage
from raw
