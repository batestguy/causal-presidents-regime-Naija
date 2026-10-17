-- Base spec section 7 is [LOCKED], so this test does not second-guess the dates — it checks that the
-- spine is *coherent* as a spine, which is what a locked table still has to be.
--
-- The base spec's `end_date` is a handover date and it is not written consistently: four boundaries have
-- `end_date` equal to the next `start_date` (Obasanjo 2007-05-29 -> Yar'Adua 2007-05-29) and one has a
-- one-day gap (Yar'Adua `end_date` 2010-05-05 -> Jonathan sworn 2010-05-06). Anything other than a
-- zero-or-one-day handover means either a gap in which nobody held office or an overlap in which two
-- people did, and both would corrupt a monthly assignment downstream while looking harmless here.
with ordered as (
    select
        admin_id,
        president,
        start_date,
        end_date,
        lead(start_date) over (order by start_date) as next_start_date
    from {{ ref('dim_administration') }}
)

select
    admin_id,
    president,
    start_date,
    end_date,
    next_start_date,
    datediff('day', end_date, next_start_date) as handover_day_gap
from ordered
where next_start_date is not null
  and datediff('day', end_date, next_start_date) not in (0, 1)
