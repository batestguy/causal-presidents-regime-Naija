-- One row per landed retrieval, for the **latest vintage of each source only**.
--
-- The raw layer is immutable and deliberately keeps superseded vintages (X-07) so Stage 3 can
-- detect revisions. The analytical base must read exactly one vintage per source, or a single
-- series would appear twice with two different vintages and quietly double-count. That filter lives
-- here and nowhere else, so it cannot be forgotten by a downstream model: everything that reads raw
-- payloads reads this view.
--
-- Two things this file knows that are easy to get wrong:
--
--   1. `read_json_auto(..., filename = true)` returns Windows backslash paths on this host while the
--      manifests themselves store POSIX paths (`as_posix()`, decisions C-16). A Windows path would
--      never join and would break the Linux CI runners the plan schedules against, so paths are
--      normalised once, here, with `chr(92)` rather than a backslash literal — a bare `'\'` inside a
--      DuckDB string literal is an escape character, not a path separator.
--   2. `unnest(retrievals).field` appears several times in one SELECT. DuckDB zips the unnests of a
--      single list, which is why the fields stay on one row; it is not zip-truncation by accident.
with manifests as (
    select
        replace(filename, chr(92), '/') as manifest_path,
        vintage_date,
        source,
        generated_at,
        n_datasets_succeeded,
        n_failures,
        unnest(retrievals).metric_id as metric_id,
        unnest(retrievals).dataset_id as dataset_id,
        unnest(retrievals).dataset_name as dataset_name,
        unnest(retrievals).sha256 as payload_sha256,
        unnest(retrievals).row_count as payload_row_count,
        unnest(retrievals).http_status as http_status,
        unnest(retrievals).retrieved_at as retrieved_at
    from read_json_auto(
        '{{ var("raw_root") }}/*/*/manifest.json',
        filename = true
    )
),

latest as (
    select source, max(vintage_date) as vintage_date
    from manifests
    group by source
)

select
    m.source,
    m.vintage_date,
    m.manifest_path,
    m.generated_at,
    m.metric_id,
    m.dataset_id,
    m.dataset_name,
    m.payload_sha256,
    m.payload_row_count,
    m.http_status,
    m.retrieved_at
from manifests m
join latest l
    on l.source = m.source
   and l.vintage_date = m.vintage_date
