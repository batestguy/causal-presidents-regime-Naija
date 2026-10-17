-- One row per payload file, restricted to the current vintage of each source.
--
-- Payloads are joined to retrievals by **(source, vintage, dataset_id)** parsed out of the file path,
-- not by comparing the path against `page_files`. Two reasons, both learned by trying the other way:
--
--   * `page_files` is a `VARCHAR[]` on some host path conventions and a plain string on others; the
--     Stage 3 bug where `jsonlite`/`auto_unbox` collapsed single-element arrays (corrections #7) is
--     the same failure mode one layer down. Path-derived keys have one type everywhere.
--   * the path already carries the three components, so the manifest join is a pure key match and
--     the payload's own identity is provable from the file, not taken on trust from the manifest.
--
-- The layout is `<raw_root>/<source>/<vintage>/<dataset_id>/page-NNNN.json`, so the components are
-- read from the **end** of the split path: no position depends on how deep `raw_root` is.
with payload_files as (
    select
        replace(filename, chr(92), '/') as payload_path,
        content
    from read_text('{{ var("raw_root") }}/*/*/*/page-*.json')
),

parsed as (
    select
        payload_path,
        content,
        string_split(payload_path, '/') as parts
    from payload_files
),

located as (
    select
        payload_path,
        content,
        parts[-4] as source,
        parts[-3] as vintage,
        parts[-2] as dataset_id,
        parts[-1] as file_name
    from parsed
)

select
    l.source,
    l.vintage,
    m.metric_id,
    l.dataset_id,
    l.file_name,
    l.payload_path,
    m.payload_sha256,
    m.payload_row_count,
    l.content
from located l
join {{ ref('stg_raw_manifest') }} m
    on m.source = l.source
   and m.dataset_id = l.dataset_id
   and m.vintage_date::VARCHAR = l.vintage
