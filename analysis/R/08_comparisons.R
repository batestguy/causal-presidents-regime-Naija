# Descriptive comparisons — group means and group series for the guided flow's chart.
#
# This stage describes. It computes no test, no interval and no contrast: `analysis/specs/comparisons.yml`
# declares the groups, the two means and the forbidden fields, and `tests/verify_comparisons.py` recomputes
# every number here from the base. If a field in the schema is missing from this output, the artifact fails
# validation rather than shipping a page with a hole in it.
#
# Run: Rscript analysis/R/08_comparisons.R

suppressPackageStartupMessages({
  library(DBI); library(duckdb); library(data.table)
  library(jsonlite); library(svglite); library(yaml)
})

root <- normalizePath(".")
spec_path <- file.path("analysis", "specs", "comparisons.yml")
spec <- read_yaml(spec_path)
series_index <- fromJSON(file.path("registry", "series",
                                   fromJSON(file.path("registry", "dags", "index.json"))$vintage_date,
                                   "index.json"), simplifyVector = FALSE)
registry_index <- fromJSON(file.path("registry", "dags", "index.json"), simplifyVector = FALSE)
vintage <- registry_index$vintage_date
out_dir <- file.path("registry", "comparisons", vintage)
fig_dir <- file.path(out_dir, "figures")
dir.create(fig_dir, recursive = TRUE, showWarnings = FALSE)

git_sha <- tryCatch(system2("git", c("rev-parse", "--short", "HEAD"), stdout = TRUE), error = function(e) NA_character_)
if (length(git_sha) == 0) git_sha <- NA_character_

con <- dbConnect(duckdb(), dbdir = file.path("data", "analytics.duckdb"), read_only = TRUE)
on.exit(dbDisconnect(con), add = TRUE)

months_between <- function(first, last) {
  f <- as.Date(paste0(first, "-01")); l <- as.Date(paste0(last, "-01"))
  seq(f, l, by = "month")
}
month_label <- function(d) format(d, "%Y-%m")
signif6 <- function(x) ifelse(is.na(x), NA_real_, signif(x, 6))

window_first <- spec$window$first
window_last <- spec$window$last
window_months <- months_between(window_first, window_last)

outcome_ids <- vapply(series_index$outcomes, function(o) o$id, character(1))

fm <- as.data.table(dbGetQuery(con, sprintf(
  "select metric_id, period_month::DATE as month, value, observation_type,
          tenure_stratum, admin_id, president
     from main_analytics.fact_metric
    where metric_id in (%s)
      and period_month between DATE '%s-01' and DATE '%s-01'
    order by metric_id, period_month",
  paste(sprintf("'%s'", outcome_ids), collapse = ","), window_first, window_last)))
fm[, month_label := format(month, "%Y-%m")]

breaks <- as.data.table(dbGetQuery(con,
  "select metric_id, break_month::DATE as break_month, label, note from main_analytics.dim_definition_break"))

# ---- party/tenure groups ------------------------------------------------------------------------------
# A stratum's months can be non-contiguous (APC_first covers 2015-2019 and 2023-), so runs are found here and
# the figure draws them separately. The mean still covers the whole stratum, which is what the model uses.
strata_order <- c("PDP_first", "PDP_second", "APC_first", "APC_second")
strata_plain <- c(PDP_first = "the first PDP term", PDP_second = "the second PDP term",
                  APC_first = "the first APC term", APC_second = "the second APC term")
strata_technical <- c(PDP_first = "PDP_first", PDP_second = "PDP_second",
                      APC_first = "APC_first", APC_second = "APC_second")

fmt_mean <- function(x) {
  if (length(x) == 0 || all(is.na(x))) return("no observation")
  formatC(x, format = "f", digits = 1, big.mark = ",")
}

party_groups <- function(oid) {
  d <- fm[metric_id == oid & !is.na(tenure_stratum)]
  if (nrow(d) == 0) return(list())
  groups <- list()
  for (s in strata_order) {
    g <- d[tenure_stratum == s][order(month)]
    if (nrow(g) == 0) next
    observed <- g[observation_type == "observed" & !is.na(value)]
    all_vals <- g[!is.na(value)]
    mean_all <- if (nrow(all_vals) > 0) signif6(mean(all_vals$value)) else NA_real_
    mean_nat <- if (nrow(observed) > 0) signif6(mean(observed$value)) else NA_real_
    n_admin <- length(unique(g$admin_id))
    caption <- sprintf("%s: %d months across %d administration%s; %d with an observation; mean %s a month%s.",
                       strata_plain[[s]], nrow(g), n_admin, if (n_admin > 1) "s" else "",
                       nrow(observed), fmt_mean(mean_all),
                       if (!is.na(mean_all) && !is.na(mean_nat) && abs(mean_all - mean_nat) > 0.05)
                         sprintf(" (%s over observed months only)", fmt_mean(mean_nat)) else "")
    groups[[length(groups) + 1]] <- list(
      grouping_id = "party_tenure",
      group_id = s,
      plain = strata_plain[[s]],
      technical = strata_technical[[s]],
      n_units = 1L,
      months = nrow(g),
      group_mean = mean_all,
      group_mean_native_only = mean_nat,
      series = lapply(seq_len(nrow(g)), function(i) list(
        month = g$month_label[i],
        value = signif6(g$value[i]),
        observed = identical(g$observation_type[i], "observed"))),
      caption = caption)
  }
  groups
}

# ---- state dose groups --------------------------------------------------------------------------------
dose_spec <- Filter(function(g) g$id == "state_dose_quartile", spec$groupings)[[1]]
dose_first <- dose_spec$window$first
dose_last <- dose_spec$window$last
state_outcomes <- unlist(dose_spec$applies_to)

sp <- as.data.table(dbGetQuery(con, sprintf(
  "select state_name, period_month::DATE as month, faac_gross_total_naira as dose,
          fatalities, incidents, security_status
     from main_analytics.state_panel
    where period_month between DATE '%s-01' and DATE '%s-01'
    order by state_name, period_month", dose_first, dose_last)))
sp[, month_label := format(month, "%Y-%m")]

state_mean_dose <- sp[!is.na(dose), .(mean_dose = mean(dose)), by = state_name][order(mean_dose)]
n_states <- nrow(state_mean_dose)
# Equal-count quartiles by rank: 10/9/9/9 for 37 units. A rank split cannot be moved by a tie, which a
# quantile cut on the values can be.
state_mean_dose[, quartile := ceiling(seq_len(.N) * 4 / n_states)]
quartile_plain <- c("states that received the least federal money", "states in the lower middle",
                    "states in the upper middle", "states that received the most federal money")
quartile_technical <- c("FAAC dose quartile 1 (lowest)", "FAAC dose quartile 2",
                        "FAAC dose quartile 3", "FAAC dose quartile 4 (highest)")

state_groups <- function(oid) {
  if (!oid %in% state_outcomes) return(list())
  d <- merge(sp, state_mean_dose[, .(state_name, quartile)], by = "state_name")
  groups <- list()
  for (q in 1:4) {
    g <- d[quartile == q]
    units <- unique(g$state_name)
    per_month <- g[security_status == "observed" & !is.na(get(oid)),
                  .(value = mean(get(oid)), n_obs = .N), by = .(month_label, month)]
    per_month <- per_month[order(month)]
    all_vals <- per_month$value
    mean_all <- if (length(all_vals) > 0) signif6(mean(all_vals)) else NA_real_
    caption <- sprintf("%s (%d states): %d months, %d with at least one observed state; mean %s per state-month.",
                       quartile_plain[q], length(units), length(months_between(dose_first, dose_last)),
                       nrow(per_month), fmt_mean(mean_all))
    groups[[length(groups) + 1]] <- list(
      grouping_id = "state_dose_quartile",
      group_id = sprintf("dose_q%d", q),
      plain = quartile_plain[q],
      technical = quartile_technical[q],
      n_units = length(units),
      months = length(months_between(dose_first, dose_last)),
      group_mean = mean_all,
      group_mean_native_only = mean_all,
      series = lapply(seq_len(nrow(per_month)), function(i) list(
        month = per_month$month_label[i],
        value = signif6(per_month$value[i]),
        observed = TRUE)),
      caption = caption)
  }
  groups
}

# ---- figures -------------------------------------------------------------------------------------------
palette <- unlist(spec$figures$palette)
stamp <- spec$figures$stamp

runs_of <- function(months) {
  # A stratum can be interrupted (APC_first: 2015-2019 then 2023-). A line drawn across the interruption
  # would claim continuity the data does not have, so each contiguous run is its own path.
  if (length(months) < 2) return(rep(1L, length(months)))
  gaps <- c(1L, cumsum(as.integer(diff(months)) > 31L) + 1L)
  gaps
}

party_panel <- function(oid, meta) {
  d <- fm[metric_id == oid & !is.na(tenure_stratum) & !is.na(value)]
  ylim <- range(d$value, na.rm = TRUE)
  if (!all(is.finite(ylim)) || diff(ylim) == 0) ylim <- ylim + c(-1, 1)
  plot(window_months, rep(NA_real_, length(window_months)), type = "n", ylim = ylim,
       xlab = "", ylab = meta$unit, las = 1, cex.axis = 0.7,
       main = sprintf("%s — by who was in power", meta$short), adj = 0, cex.main = 0.95, font.main = 1)
  for (i in seq_along(strata_order)) {
    s <- strata_order[i]
    g <- d[tenure_stratum == s][order(month)]
    if (nrow(g) == 0) next
    run <- runs_of(g$month)
    for (r in unique(run)) {
      gr <- g[run == r]
      if (nrow(gr) < 2) next
      obs <- gr$observation_type == "observed"
      # Segment style follows the data: an interpolated stretch is dotted, so the fill is visible.
      for (k in seq_len(nrow(gr) - 1)) {
        segments(gr$month[k], gr$value[k], gr$month[k + 1], gr$value[k + 1],
                 col = palette[i], lwd = 1.6, lty = if (obs[k] && obs[k + 1]) 1 else 3)
      }
    }
    points(g[observation_type == "observed"]$month, g[observation_type == "observed"]$value,
           pch = 19, cex = 0.45, col = palette[i])
  }
  brk <- breaks[metric_id == oid]
  if (nrow(brk) > 0) {
    abline(v = brk$break_month, lty = 2, col = "#b9b3a5")
    text(brk$break_month, ylim[2], labels = brk$label, pos = 4, cex = 0.55, col = "#767d89", srt = 90)
  }
  legend("topright", legend = c("PDP first", "PDP second", "APC first", "APC second"),
         col = palette, lty = 1, bty = "n", cex = 0.65)
  mtext(stamp, side = 3, adj = 1, line = -1.2, cex = 0.55, col = "#8c3a2f")
}

state_panel <- function(oid, meta) {
  d <- merge(sp, state_mean_dose[, .(state_name, quartile)], by = "state_name")
  d <- d[security_status == "observed" & !is.na(get(oid))]
  per_month <- d[, .(value = mean(get(oid))), by = .(quartile, month)]
  ylim <- range(per_month$value, na.rm = TRUE)
  if (!all(is.finite(ylim)) || diff(ylim) == 0) ylim <- ylim + c(-1, 1)
  plot(range(per_month$month), c(ylim[1], ylim[2]), type = "n",
       xlab = "", ylab = sprintf("mean %s per state", meta$unit), las = 1, cex.axis = 0.7,
       main = sprintf("%s — by how much money a state received", meta$short), adj = 0, cex.main = 0.95,
       font.main = 1)
  for (q in 1:4) {
    g <- per_month[quartile == q][order(month)]
    if (nrow(g) == 0) next
    lines(g$month, g$value, col = palette[q], lwd = 1.6)
    points(g$month, g$value, pch = 19, cex = 0.3, col = palette[q])
  }
  legend("topleft", legend = c("least money", "lower middle", "upper middle", "most money"),
         col = palette, lty = 1, bty = "n", cex = 0.65)
  mtext(sprintf("%s to %s — %d states", dose_first, dose_last, n_states),
        side = 3, adj = 0, line = -1.2, cex = 0.55, col = "#767d89")
  mtext(stamp, side = 3, adj = 1, line = -1.2, cex = 0.55, col = "#8c3a2f")
}

draw_outcome <- function(oid, meta, has_state) {
  path <- file.path(fig_dir, sprintf("%s.svg", oid))
  h <- if (has_state) spec$figures$height_in_two_panel else spec$figures$height_in
  svglite(path, width = spec$figures$width_in, height = h)
  op <- par(mar = c(2.6, 4.2, 2.2, 1), oma = c(0, 0, 0, 0), mgp = c(2.2, 0.6, 0))
  if (has_state) {
    layout(matrix(1:2, ncol = 1), heights = c(1.15, 1))
    party_panel(oid, meta); state_panel(oid, meta)
  } else {
    party_panel(oid, meta)
  }
  par(op); invisible(dev.off())
  path
}

# ---- outcomes ------------------------------------------------------------------------------------------
evidence_kind <- function(domain) spec$evidence[[domain]]
evidence_artifact <- function(kind) switch(kind,
  design_result = file.path("registry", "estimates", vintage, "estimates.json"),
  event_study = file.path("registry", "events", vintage, "events.json"),
  series_panel = file.path("registry", "series", vintage, "index.json"))

# The figure's size is recorded on its *canonical* bytes (CRLF collapsed to LF), because `.gitattributes`
# stores this repository's text with `eol=lf`. A raw `file.size()` is true only on the Windows checkout that
# produced it; after any clone or the Linux runner the file is a few hundred bytes smaller and the contract
# test would call a fresh chart stale. The Python consumers apply the same rule.
canonical_bytes <- function(path) {
  bytes_raw <- readBin(path, "raw", n = file.info(path)$size)
  if (length(bytes_raw) == 0) return(0L)
  is_cr <- bytes_raw == as.raw(13)
  is_lf <- bytes_raw == as.raw(10)
  crlf <- is_cr & c(is_lf[-1], FALSE)
  sum(!crlf)
}

outcomes <- list()
for (meta in series_index$outcomes) {
  oid <- meta$id
  pg <- party_groups(oid)
  sg <- state_groups(oid)
  has_state <- length(sg) > 0
  fig_path <- draw_outcome(oid, meta, has_state)

  kind <- evidence_kind(meta$domain)
  if (is.null(kind)) kind <- "series_panel"
  caption <- sprintf(
    "%s: %d months of which %d observed. Grouped %s. %s",
    meta$short, sum(unlist(meta$observations)), meta$observations$observed,
    if (has_state) sprintf("both by who was in power and by state allocation (%s to %s)", dose_first, dose_last)
    else "by who was in power (no state grouping is declared for this outcome)",
    if (has_state) "" else sprintf("Native frequency %s; %s (%s to %s).", meta$native_frequency,
                                    meta$quality_status, meta$first_observed, meta$last_observed))

  outcomes[[length(outcomes) + 1]] <- list(
    id = oid,
    label = meta$label,
    short = meta$short,
    domain = meta$domain,
    unit = meta$unit,
    direction = meta$direction,
    native_frequency = meta$native_frequency,
    quality_status = meta$quality_status,
    window = list(first = meta$window$first, last = meta$window$last),
    observed = list(
      native_in_window = meta$native_in_window,
      observed_months = meta$observations$observed,
      interpolated_months = meta$observations$interpolated,
      unobserved_months = meta$observations$unobserved),
    definition_breaks = lapply(seq_along(meta$definition_breaks), function(i) {
      b <- meta$definition_breaks[[i]]
      list(date = b$date, name = b$name, note = if (is.null(b$note)) NA else b$note)
    }),
    closest_evidence = list(
      kind = kind,
      artifact = evidence_artifact(kind),
      outcome_id = if (identical(kind, "event_study")) oid else NA,
      plain = spec$evidence$plain[[kind]]),
    groups = c(pg, sg),
    caption = caption,
    figure = list(path = fig_path, bytes = canonical_bytes(fig_path)),
    refused = NULL)
}

# ---- artifact ------------------------------------------------------------------------------------------
artifact <- list(
  schema_version = "0.1.0",
  stage = spec$stage,
  layer = spec$layer,
  vintage = vintage,
  generated_at = format(Sys.time(), "%Y-%m-%dT%H:%M:%S%z"),
  generator = list(script = "analysis/R/08_comparisons.R", git_sha = git_sha),
  spec = list(path = "analysis/specs/comparisons.yml",
              md5 = unname(tools::md5sum(spec_path)), version = spec$version),
  verifier = "tests/verify_comparisons.py",
  input = list(
    database = "data/analytics.duckdb",
    fact_table = "main_analytics.fact_metric",
    native_table = "main_analytics.fact_observation_native",
    metric_dimension = "main_analytics.dim_metric",
    definition_break_table = "main_analytics.dim_definition_break",
    outcomes_spec = "analysis/specs/outcomes.yml",
    dose_metric_id = "faac_gross_total_naira"),
  counts = list(
    outcomes = length(outcomes),
    groupings = length(spec$groupings),
    charts = length(outcomes),
    groups_total = sum(vapply(outcomes, function(o) length(o$groups), integer(1))),
    outcomes_refused = sum(vapply(outcomes, function(o) !is.null(o$refused), logical(1)))),
  rules = list(
    group_mean = spec$rules$group_mean,
    grain = "national-month (party/tenure); state-month (state quartiles)",
    forbidden_fields = unlist(spec$rules$forbidden_fields),
    min_units_per_group = spec$rules$min_units_per_group,
    declared_gap_rule = spec$rules$declared_gap),
  groupings = lapply(spec$groupings, function(g) list(
    id = g$id, plain = g$plain, technical = g$technical, group_kind = g$kind, grain = g$grain,
    window = list(first = if (!is.null(g$window)) g$window$first else window_first,
                  last = if (!is.null(g$window)) g$window$last else window_last),
    n_groups = if (identical(g$id, "party_tenure"))
      length(unique(fm$tenure_stratum[!is.na(fm$tenure_stratum)])) else 4L,
    source_note = paste(g$source, if (!is.null(g$excludes)) g$excludes else "",
                        if (!is.null(g$quartile_rule)) g$quartile_rule else ""))),
  outcomes = outcomes,
  notes = c(
    "description only: no test, no interval, no contrast between groups",
    "group_mean averages the drawn series; group_mean_native_only averages observations alone, and the two differ where the spine filled months",
    "a stratum can cover more than one administration; the figure draws each contiguous run separately"))

out_path <- file.path(out_dir, "comparisons.json")
writeLines(toJSON(artifact, auto_unbox = TRUE, pretty = TRUE, digits = NA,
                  null = "null", na = "null"), out_path, useBytes = TRUE)

cat(sprintf("wrote %s — %d outcomes, %d groups, %d figures, vintage %s\n",
            out_path, length(outcomes), artifact$counts$groups_total, length(outcomes), vintage))

