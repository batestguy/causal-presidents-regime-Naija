-- Definition breaks, carried from the Stage 3 report into the base as a dimension.
--
-- PHASES.md Stage 3: "Definition-drift gate — series whose definition changed (unemployment
-- methodology, GDP rebasing in 2014, FX regime breaks) carry an explicit break annotation", and its
-- exit criterion: "every published series carries a quality status field that travels with it into the
-- app". A break that only exists in a report is not travelling with the series.
--
-- This dimension is why the base can annotate a level shift instead of a reader having to notice one:
--
--   * `gdp_growth` / `gdp_per_capita` — the April 2014 rebasing, after which pre- and post-2014 levels
--     are not the same series;
--   * `fx` — the 2016-06 float and the 2023-06 unification;
--   * `unemp` — the 2014 and 2023 NBS methodology changes;
--   * `cpi_yoy` — the January 2025 CPI rebasing, which the spike gate found rather than the reverse.
--
-- The breaks come through `stg_quality_series`, which reads the same report `dim_metric` reads, so an
-- annotation cannot exist in one and not the other.
--
-- **National series only.** The donor panel reports the same breaks for the same indicator ids, once per
-- country, and all 13 rows for `u5mr` would be identical: a definition break is a property of the
-- indicator's definition, not of the country reading it, and this dimension is keyed by `metric_id`. Left
-- unfiltered it produced 34 rows for 8 distinct breaks, which is not more information — it is the same
-- annotation offered 13 times, and it would read as if each donor country had its own method change.
with national as (
    select metric_id, source, quality_vintage, definition_breaks, n_breaks_in_window
    from {{ ref('stg_quality_series') }}
    where source in ('worldbank', 'fred')
)

select
    q.metric_id,
    q.source,
    b.date::DATE as break_date,
    date_trunc('month', b.date::DATE)::DATE as break_month,
    b.label,
    b.note,
    q.quality_vintage as declared_in_vintage
from national q,
    unnest(q.definition_breaks) as t(b)
