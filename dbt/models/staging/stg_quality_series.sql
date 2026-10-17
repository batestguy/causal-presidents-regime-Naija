-- The Stage 3 vintage quality report, one row per gated series.
--
-- PHASES.md Stage 3 exit criterion: "no series reaches Stage 4 without a gate result" and "every
-- published series carries a quality status field that travels with it into the app". This model is
-- how that status travels: `dim_metric` joins it, so a metric's quality state is a dimension attribute
-- rather than something a chart re-derives or a reader has to open another file to find.
--
-- Only the latest report vintage is read — an old report describes an old raw vintage, and carrying
-- both would let a superseded flag outlive the data it was computed on.
with report as (
    select
        report_vintage,
        replace(filename, chr(92), '/') as report_path,
        unnest(series).source as source,
        unnest(series).metric_id as metric_id,
        unnest(series).dataset_id as dataset_id,
        unnest(series).scope as scope,
        unnest(series).status as status,
        unnest(series).grain_period as native_frequency,
        unnest(series).spike_measure as spike_measure,
        unnest(series).gates.coverage.n_observed as n_observed_in_window,
        unnest(series).gates.coverage.first_observed as first_observed,
        unnest(series).gates.coverage.last_observed as last_observed,
        unnest(series).gates.gap.max_gap_months as max_gap_months,
        unnest(series).gates.gap.tripped as gap_tripped,
        unnest(series).gates.spike.n_spikes as n_spikes,
        -- Definition breaks arrive as a list of structs, and are unnested one level into a dimension of
        -- their own (`dim_definition_break`) rather than summarised into a count here: a count tells the
        -- app that something changed but not when, and the when is the whole point of an annotation.
        unnest(series).gates.definition_drift.breaks as definition_breaks,
        unnest(series).gates.definition_drift.n_breaks_in_window as n_breaks_in_window
    from read_json_auto(
        '{{ var("registry_root") }}/quality/*/report.json',
        filename = true,
        maximum_object_size = 40000000
    )
),

latest as (
    select max(report_vintage) as report_vintage
    from report
)

select
    source,
    metric_id,
    dataset_id,
    scope,
    status as quality_status,
    native_frequency,
    spike_measure,
    n_observed_in_window,
    first_observed,
    last_observed,
    max_gap_months,
    gap_tripped,
    n_spikes,
    n_breaks_in_window,
    definition_breaks,
    report_vintage as quality_vintage,
    report_path
from report
where report_vintage = (select report_vintage from latest)
