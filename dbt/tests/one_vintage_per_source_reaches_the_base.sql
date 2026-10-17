-- The raw layer keeps superseded vintages on purpose (X-07), and `worldbank/2026-10-10` is still on
-- disk beside `worldbank/2026-10-11`. If the vintage filter in `stg_raw_manifest` ever broke, that older
-- vintage would re-enter and every affected series would appear twice with two vintages.
--
-- Two checks in one: each source resolves to exactly one vintage, and every vintage that reached the
-- base is that one.
with per_source as (
    select
        source,
        count(distinct vintage_date) as n_vintages,
        max(vintage_date) as latest_vintage
    from {{ ref('stg_raw_manifest') }}
    group by source
),

multiple as (
    select source, 'more than one vintage survived the filter' as problem
    from per_source
    where n_vintages <> 1
),

base_vintages as (
    select distinct source, vintage
    from {{ ref('fact_metric') }}
),

stale as (
    select b.source, 'a superseded vintage reached fact_metric' as problem
    from base_vintages b
    join per_source p
        on p.source = b.source
    where b.vintage <> p.latest_vintage::VARCHAR
)

select * from multiple
union all
select * from stale
