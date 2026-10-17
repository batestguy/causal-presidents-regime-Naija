-- The locked shape: five administrations, PDP three times then APC twice, starting 1999-05-29. A sixth
-- row or a reordered party sequence would change what "PDP first term" means in every model, so the
-- check is on the shape rather than on any individual row.
with summary as (
    select
        count(*) as n_rows,
        count(*) filter (where party = 'PDP') as n_pdp,
        count(*) filter (where party = 'APC') as n_apc,
        min(start_date) as first_start,
        max(start_date) as last_start,
        count(*) filter (where start_date < DATE '1999-05-29') as n_before_study
    from {{ ref('dim_administration') }}
)

select *
from summary
where n_rows <> 5
   or n_pdp <> 3
   or n_apc <> 2
   or first_start <> DATE '1999-05-29'
   or n_before_study <> 0
