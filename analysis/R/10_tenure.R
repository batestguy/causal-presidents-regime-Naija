# Tenure description - deviations from a tenure-blind LOESS trend, and the descriptive contrast between tenures.
#
# This stage does not estimate an effect. `analysis/specs/tenure.yml` declares the method, the spans, the refusals
# and the forbidden fields; this file applies them and types no choice of its own. Every deviation is published with
# the trend value it was taken from, so `tests/verify_tenure.py` can recompute the summaries without refitting.
#
# Run: Rscript analysis/R/10_tenure.R

suppressPackageStartupMessages({
  library(DBI); library(duckdb); library(data.table)
  library(jsonlite); library(yaml)
})

root <- normalizePath(".")
spec_path <- file.path("analysis", "specs", "tenure.yml")
spec <- read_yaml(spec_path)
spec_md5 <- unname(tools::md5sum(spec_path))

registry_index <- fromJSON(file.path("registry", "dags", "index.json"), simplifyVector = FALSE)
vintage <- registry_index$vintage_date
series_index <- fromJSON(file.path("registry", "series", vintage, "index.json"), simplifyVector = FALSE)
out_dir <- file.path("registry", "tenure", vintage)
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

git_sha <- tryCatch(system2("git", c("rev-parse", "--short", "HEAD"), stdout = TRUE), error = function(e) NA_character_)
if (length(git_sha) == 0) git_sha <- NA_character_

con <- dbConnect(duckdb(), dbdir = file.path("data", "analytics.duckdb"), read_only = TRUE)
on.exit(dbDisconnect(con), add = TRUE)

outcome_ids <- vapply(series_index$outcomes, function(o) o$id, character(1))

native <- as.data.table(dbGetQuery(con, sprintf(
  "select metric_id, anchor_month::DATE as month, value
     from main_analytics.fact_observation_native
    where metric_id in (%s) and value is not null
      and anchor_month between DATE '%s-01' and DATE '%s-01'
    order by metric_id, anchor_month",
  paste(sprintf("'%s'", outcome_ids), collapse = ","), spec$window$first, spec$window$last)))

adm <- as.data.table(dbGetQuery(con,
  "select president, party, start_date::DATE as start_date, end_date_effective::DATE as end_date_effective
     from main_analytics.dim_administration order by start_date"))

spans <- as.numeric(unlist(spec$trend$span_grid))
min_native <- as.integer(spec$refusals$min_native)
min_tenure <- as.integer(spec$refusals$min_native_per_tenure)

months_in <- function(a, b) {
  if (is.na(a) || is.na(b) || b <= a) return(0L)
  length(seq(a, b - 1, by = "month"))
}

outcomes <- list()
for (meta in series_index$outcomes) {
  oid <- meta$id
  d <- native[metric_id == oid][order(month)]
  n <- nrow(d)

  if (n < min_native) {
    outcomes[[length(outcomes) + 1]] <- list(
      id = oid, label = meta$short, unit = meta$unit, status = "refused",
      n_native = n,
      refused = list(reason = "too_few_native_observations",
                     detail = sprintf("%d native observations; this stage describes nothing below %d", n, min_native)))
    next
  }

  t <- as.numeric(d$month - min(d$month)) / 30.44
  per_span <- list()
  for (s in spans) {
    fit <- loess(d$value ~ t, span = s, degree = 1, control = loess.control(surface = "direct"))
    trend <- as.numeric(fitted(fit))
    per_span[[as.character(s)]] <- data.table(
      month = d$month, value = d$value, trend = signif(trend, 10),
      deviation = signif(d$value - trend, 6))
  }

  tenures <- list()
  window_end <- as.Date(paste0(spec$window$last, "-01"))
  for (i in seq_len(nrow(adm))) {
    # Month-start arithmetic on both sides: observations are month-starts, the administration boundary is a day.
    # The window is [month(start), month(end - 1 day)] inclusive, which is the same set as the half-open span
    # [start, next_start) applied to month-start rows - and it is the definition the verifier recomputes.
    a <- as.Date(format(as.Date(adm$start_date[i]), "%Y-%m-01"))
    b_excl <- min(as.Date(adm$end_date_effective[i]), window_end + 31)
    b <- as.Date(format(b_excl - 1, "%Y-%m-01"))
    inside <- d$month >= a & d$month <= b
    n_in <- sum(inside)
    window_months <- length(seq(a, b, by = "month"))
    if (n_in < min_tenure) {
      tenures[[length(tenures) + 1]] <- list(
        president = adm$president[i], party = adm$party[i],
        start = format(a, "%Y-%m"), end = format(b, "%Y-%m"),
        n_native = n_in, status = "insufficient_points",
        detail = sprintf("%d native points in the window; a deviation needs at least %d", n_in, min_tenure))
      next
    }
    means <- vapply(spans, function(s) {
      ps <- per_span[[as.character(s)]]
      mean(ps$deviation[inside])
    }, numeric(1))
    abses <- vapply(spans, function(s) {
      ps <- per_span[[as.character(s)]]
      mean(abs(ps$deviation[inside]))
    }, numeric(1))
    tenures[[length(tenures) + 1]] <- list(
      president = adm$president[i], party = adm$party[i],
      start = format(a, "%Y-%m"), end = format(b, "%Y-%m"),
      n_native = n_in, coverage = signif(n_in / max(window_months, 1L), 4),
      status = "described",
      mean_deviation = signif(mean(means), 6),
      mean_absolute_deviation = signif(mean(abses), 6),
      deviation_range = c(signif(min(means), 6), signif(max(means), 6)))
  }

  described <- Filter(function(x) identical(x$status, "described"), tenures)
  contrasts <- list()
  if (length(described) >= 2) {
    as_date <- function(m) as.Date(paste0(m, "-01"))
    for (i in seq_len(length(described) - 1)) {
      for (j in seq(i + 1, length(described))) {
        a <- described[[i]]; b <- described[[j]]
        wa <- d$month >= as_date(a$start) & d$month <= as_date(a$end)
        wb <- d$month >= as_date(b$start) & d$month <= as_date(b$end)
        diffs <- vapply(spans, function(s) {
          dev <- per_span[[as.character(s)]]$deviation
          mean(dev[wa]) - mean(dev[wb])
        }, numeric(1))
        contrasts[[length(contrasts) + 1]] <- list(
          a = a$president, b = b$president,
          difference = signif(mean(diffs), 6),
          range = c(signif(min(diffs), 6), signif(max(diffs), 6)),
          reading = sprintf("%s sat %+.2f %s from the trend relative to %s, across the declared spans",
                            a$president, mean(diffs), meta$unit, b$president))
      }
    }
  }

  outcomes[[length(outcomes) + 1]] <- list(
    id = oid, label = meta$short, unit = meta$unit, status = "described", n_native = n,
    trend = lapply(spans, function(s) {
      ps <- per_span[[as.character(s)]]
      list(span = s, points = lapply(seq_len(nrow(ps)), function(k) list(
        month = format(ps$month[k], "%Y-%m"), value = ps$value[k],
        trend = ps$trend[k], deviation = ps$deviation[k])))
    }),
    tenures = tenures,
    contrasts = contrasts)
}

counts <- list(
  outcomes = length(outcomes),
  described = sum(vapply(outcomes, function(o) identical(o$status, "described"), logical(1))),
  refused = sum(vapply(outcomes, function(o) identical(o$status, "refused"), logical(1))),
  tenures_described = sum(vapply(outcomes, function(o)
    if (identical(o$status, "described")) sum(vapply(o$tenures, function(x) identical(x$status, "described"), logical(1))) else 0L, integer(1))),
  tenures_insufficient = sum(vapply(outcomes, function(o)
    if (identical(o$status, "described")) sum(vapply(o$tenures, function(x) identical(x$status, "insufficient_points"), logical(1))) else 0L, integer(1))),
  contrasts = sum(vapply(outcomes, function(o) if (identical(o$status, "described")) length(o$contrasts) else 0L, integer(1))))

payload <- list(
  schema_version = "0.1.0",
  stage = "8g",
  layer = "descriptive tenure deviations from a tenure-blind trend, and the contrast between tenures - never an effect",
  vintage = vintage,
  generated_at = format(Sys.time(), "%Y-%m-%dT%H:%M:%S%z"),
  generator = list(script = "analysis/R/10_tenure.R", git_sha = git_sha),
  spec = list(path = spec_path, md5 = spec_md5,
              spans = spans, min_native = min_native, min_native_per_tenure = min_tenure,
              forbidden = unlist(spec$forbidden), stamp = spec$stamp),
  input = list(table = "fact_observation_native",
               rule = "native observations only; the interpolated spine is never touched"),
  counts = counts,
  outcomes = outcomes)

write_json(payload, file.path(out_dir, "tenure.json"), auto_unbox = TRUE, pretty = TRUE, digits = 10)

md <- c(
  sprintf("# Stage 8g - tenure description, vintage %s", vintage), "",
  "Deviations of each outcome from a tenure-blind LOESS trend, by administration, with the range across the",
  "declared spans. **This is description, not a causal comparison.** A deviation labels a window; it is not an",
  "effect of a presidency, and the contrast between two tenures is the difference of two deviations.", "",
  sprintf("- outcomes described: %d; refused: %d", counts$described, counts$refused),
  sprintf("- tenure deviations published: %d; insufficient points: %d", counts$tenures_described, counts$tenures_insufficient),
  sprintf("- pairwise contrasts: %d", counts$contrasts),
  sprintf("- spans: %s", paste(spans, collapse = ", ")),
  sprintf("- spec: `%s` (md5 %s)", spec_path, spec_md5), "")
writeLines(md, file.path(out_dir, "report.md"))

message(sprintf("wrote registry/tenure/%s/tenure.json - %d described, %d refused, %d contrasts",
                vintage, counts$described, counts$refused, counts$contrasts))
