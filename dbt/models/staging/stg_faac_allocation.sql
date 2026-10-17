-- Per-state FAAC allocation rows, typed, at their native grain — state × month × item × publisher.
--
-- The source artifact is written by `ingestion/parsers/faac_disbursement.py` from the landed PDF and
-- XLSX payloads (`ingestion/flows/pull_faac.py`), one row per item each document carried. It is read
-- here rather than parsed in SQL because parsing a PDF is not a SQL operation and the base spec's
-- language split is [LOCKED] (decisions D-05): transformation in SQL, acquisition and document
-- parsing in Python. Nothing in this model decides anything — it types the artifact and keeps both
-- publishers.
--
-- **Why both publishers are still present here.** The same monthly workbook is published twice: by the
-- Office of the Accountant General of the Federation (PDF) and by the NBS as a republication (XLSX).
-- Which one *is* the series is a decision, and decisions belong where they can be declared in a spec
-- and checked by a verifier — so the choice is made once, in `analytics/faac_state_allocation.sql`, and
-- the disagreement between the two is measurable at all only because this model refuses to collapse
-- them early.
--
-- **Why the table is long rather than wide.** The workbook's column set drifts by layout era: 2019
-- carries ~20 columns and no `Electronic Money Transfer Levy` (it did not exist), 2025 carries 23 and
-- adds the augmentation and ecology columns, and the 2023 layouts publish no total column at all. A wide
-- schema would be wrong for most months; a long one records what each document actually carried and
-- leaves absent items absent, so a month that never had an EMTL column cannot be read as a month where
-- EMTL was zero.
--
-- The item set is a measured subset of the workbook: 541 header cells across the 174 documents do not
-- resolve and are enumerated in `data/staging/faac_parse_report.json`, so a missing item here means "not
-- resolved" for those cells and "not carried" for the rest. The dose column is not among them.
--
-- `period_month` is the month the revenue **accrued**, not the month it was shared: a document titled
-- "for the month of January 2024 shared in February 2024" is January. That convention is declared in
-- `analysis/specs/harmonisation.yml` and applied once, in the parser; this model only types the date.
--
-- `raw_vintage` is carried under its own name rather than as `vintage`, because every other staging
-- model's `vintage` column is the label used by `stg_raw_manifest` to pick the one vintage the base
-- reads. Keeping the parser's own label distinct means a staging table can never be mistaken for the
-- manifest's vintage filter.
with raw as (
    select *
    from read_csv_auto(
        '{{ var("staging_root") }}/faac_state_allocation.csv',
        header = true
    )
)

select
    cast(state_id as integer) as state_id,
    state_name,
    state_name_published,
    strptime(period_month, '%Y-%m')::DATE as period_month,
    publisher,
    item,
    cast(amount_naira as double) as amount_naira,
    value_source,
    source_dataset_id,
    source_file,
    source_sha256,
    source_location,
    vintage as raw_vintage
from raw
