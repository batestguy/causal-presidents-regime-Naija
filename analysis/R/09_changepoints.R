# When each outcome series changes — description only.
#
# The fit is Bai–Perron on the native observations, with the break count chosen by BIC. Nothing here tests a
# hypothesis, estimates an effect or attributes a break to a presidency; `analysis/specs/changepoints.yml`
# declares the method and the forbidden fields, and `tests/verify_changepoints.py` refits the series and
# refuses an inferential field.
#
# Run: Rscript analysis/R/09_changepoints.R

suppressPackageStartupMessages({
  library(DBI); library(duckdb); library(data.table)
  library(jsonlite); library(svglite); library(yaml); library(strucchange)
})

root <- normalizePath(".")
spec_path <- file.path("analysis", "specs", "changepoints.yml")
spec <- read_yaml(spec_path)
registry_index <- fromJSON(file.path("registry", "dags", "index.json"), simplifyVector = FALSE)
series_index <- fromJSON(file.path("registry", "series", registry_index$vintage_date, "index.json"),
                         simplifyVector = FALSE)
vintage <- registry_index$vintage_date
out_dir <- file.path("registry", "changepoints", vintage)
fig_dir <- file.path(out_dir, "figures")
dir.create(fig_dir, recursive = TRUE, showWarnings = FALSE)

git_sha <- tryCatch(system2("git", c("rev-parse", "--short", "HEAD"), stdout = TRUE), error = function(e) NA_character_)
if (length(git_sha) == 0) git_sha <- NA_character_

con <- dbConnect(duckdb(), dbdir = file.path("data", "analytics.duckdb"), read_only = TRUE)
on.exit(dbDisconnect(con), add = TRUE)

outcome_ids <- vapply(series_index$outcomes, function(o) o$id, character(1))
native <- as.data.table(dbGetQuery(con, sprintf(
  "select metric_id, anchor_month::DATE as month, value
     from main_analytics.fact_observation_native
    where metric_id in (%s) and anchor_month between DATE '%s-01' and DATE '%s-01'
      and value is not null
    order by metric_id, anchor_month",
  paste(sprintf("'%s'", outcome_ids), collapse = ","), spec$window$first, spec$window$last)))
native[, month_label := format(month, "%Y-%m")]

defs <- as.data.table(dbGetQuery(con,
  "select metric_id, break_month::DATE as break_month, label from main_analytics.dim_definition_break"))

admins <- fromJSON(file.path("registry", "reference", "administrations.json"), simplifyVector = FALSE)
inaugurations <- lapply(admins$administrations, function(a)
  list(slug = a$slug, month = substr(a$start_date, 1, 7)))

regime_of <- function(frequency, n) {
  if (identical(frequency, "monthly") && n >= 60) return("monthly")
  if (n >= 20) return("annual")
  "annual_short"
}

fmt_month <- function(d) format(d, "%Y-%m")

# A break's timing is the only thing recorded about a handover. `coincides_with_inauguration` says the months
# are adjacent and nothing else — the word "coincides" is the whole claim.
coincident_slug <- function(month_label) {
  for (inaug in inaugurations) {
    delta <- abs(as.integer(difftime(as.Date(paste0(month_label, "-01")),
                                     as.Date(paste0(inaug$month, "-01")), units = "days")))
    if (delta <= 62) return(inaug$slug)
  }
  NA_character_
}

draw_series <- function(meta, d, breaks, path) {
  svglite(path, width = spec$figures$width_in, height = spec$figures$height_in)
  op <- par(mar = c(2.8, 4.2, 2.6, 1), mgp = c(2.2, 0.6, 0))
  plot(d$month, d$value, type = "n", las = 1, cex.axis = 0.72,
       xlab = "", ylab = meta$unit,
       main = sprintf("%s — when the series changes", meta$short), adj = 0, cex.main = 0.95, font.main = 1)
  if (nrow(d) >= 2) {
    if (identical(meta$native_frequency, "monthly")) lines(d$month, d$value, col = spec$figures$palette$line, lwd = 1.2)
    points(d$month, d$value, pch = 19, cex = if (identical(meta$native_frequency, "annual")) 0.8 else 0.3,
           col = spec$figures$palette$point)
  }
  for (b in breaks) {
    colour <- if (identical(b$kind, "known_definition_break")) spec$figures$palette$measurement else spec$figures$palette$estimated
    abline(v = as.Date(paste0(b$month, "-01")), col = colour, lwd = 1.3,
           lty = if (identical(b$kind, "known_definition_break")) 2 else 1)
    text(as.Date(paste0(b$month, "-01")), max(d$value, na.rm = TRUE), labels = b$short_label,
         pos = 4, cex = 0.55, col = colour, srt = 90)
  }
  mtext(spec$figures$stamp, side = 3, adj = 1, line = -1.2, cex = 0.55, col = "#8c3a2f")
  mtext(sprintf("native observations: %d · %s", nrow(d), meta$native_frequency),
        side = 3, adj = 0, line = -1.2, cex = 0.55, col = "#767d89")
  par(op); invisible(dev.off())
}

# The figure's size is recorded on its *canonical* bytes (CRLF collapsed to LF), because `.gitattributes`
# stores this repository's text with `eol=lf`. A raw `file.size()` is true only on the Windows checkout that
# produced it; after any clone or the Linux runner the file is a few hundred bytes smaller and the contract
# test would call a fresh break panel stale. The Python consumers apply the same rule.
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
  d <- native[metric_id == oid][order(month)]
  n <- nrow(d)
  regime <- regime_of(meta$native_frequency, n)
  span <- list(first = if (n > 0) fmt_month(d$month[1]) else NA, last = if (n > 0) fmt_month(d$month[n]) else NA)
  known <- defs[metric_id == oid]

  refused <- NULL
  status <- "search"
  method_detail <- ""
  found <- list()

  if (n < spec$rules$min_native_search) {
    status <- "refused"
    refused <- list(
      reason = "too_few_native_observations",
      detail = sprintf(paste("%d native observations in the window; this stage fits nothing below %d, and a",
                             "segmented fit at a chosen date would be a drawing rather than a description"),
                       n, spec$rules$min_native_search))
    method_detail <- sprintf("no fit: %d native observations, minimum %d", n, spec$rules$min_native_search)
  } else {
    y <- as.numeric(d$value)
    n_y <- length(y)
    frame <- data.frame(y = y, t = seq_len(n_y))
    fit <- lm(y ~ 1)

    # The criterion is computed here rather than taken from `BIC()` on the breakpoints object: the package's
    # BIC and `stats::BIC(lm)` do not count parameters the same way, and comparing them would decide the number
    # of breaks with two rulers. A mean-only model with m breaks has 2m + 1 parameters (m + 1 means and m
    # locations), which is the count declared in the spec.
    rss_of <- function(m) {
      if (m == 0) return(list(rss = sum(resid(fit)^2), idx = integer(0)))
      bp <- tryCatch(breakpoints(y ~ 1, data = frame, h = spec$rules$h, breaks = m),
                     error = function(e) NULL)
      if (is.null(bp)) return(NULL)
      list(rss = sum(resid(bp)^2), idx = as.integer(bp$breakpoints))
    }
    bic_of <- function(rss, m) n_y * log(rss / n_y) + (2 * m + 1) * log(n_y)

    max_breaks <- as.integer(spec$rules$max_breaks[[regime]])
    start <- rss_of(0)
    best <- list(m = 0L, idx = integer(0), bic = bic_of(start$rss, 0))
    for (m in seq_len(max_breaks)) {
      if (n_y < 3 * m + 3) next
      candidate <- rss_of(m)
      if (is.null(candidate) || !is.finite(candidate$rss) || candidate$rss <= 0) next
      value <- bic_of(candidate$rss, m)
      if (value < best$bic) best <- list(m = m, idx = candidate$idx, bic = value)
    }
    best_m <- best$m
    best_idx <- best$idx
    method_detail <- sprintf("Bai-Perron mean model, 0-%d breaks, BIC over 2m+1 parameters, %d selected",
                             max_breaks, best_m)
    if (best_m == 0) status <- "no_break_detected"

    for (idx in best_idx) {
      month_label <- fmt_month(d$month[idx + 1])
      # A break within one native period of a declared definition break is measurement, not history.
      near <- known[abs(as.integer(difftime(known$break_month, d$month[idx + 1], units = "days"))) <= 62]
      if (nrow(near) > 0) next
      found[[length(found) + 1]] <- list(
        month = month_label, kind = "estimated", short_label = month_label,
        label = "the series changes here",
        statement = sprintf(paste("%s changes level around %s. This is a description of the series,",
                                  "not an effect of an administration."), meta$short, month_label),
        coincides = coincident_slug(month_label))
    }
  }

  for (i in seq_len(nrow(known))) {
    month_label <- fmt_month(known$break_month[i])
    found[[length(found) + 1]] <- list(month = month_label, kind = "known_definition_break",
                                       short_label = known$label[i], label = known$label[i],
                                       statement = sprintf("The series is measured differently from %s (%s).",
                                                           month_label, known$label[i]),
                                       coincides = NA_character_)
  }
  found <- found[order(vapply(found, function(b) b$month, character(1)))]

  figure <- NULL
  if (identical(status, "refused")) {
    found <- list()
  } else {
    path <- file.path(fig_dir, sprintf("%s.svg", oid))
    draw_series(meta, d, found, path)
    figure <- list(path = path, bytes = canonical_bytes(path))
  }

  breaks_json <- lapply(found, function(b) list(month = b$month, kind = b$kind, label = b$label,
                                                 statement = b$statement,
                                                 coincides_with_inauguration = b$coincides))
  caption <- if (identical(status, "refused")) {
    sprintf(paste("%s: %d native observations in the window. Too few to say when the series changes,",
                  "and the stage does not fit a date it was told to find."), meta$short, n)
  } else if (length(breaks_json) == 0) {
    sprintf("%s: %d native observations; no break was selected over the no-break model.", meta$short, n)
  } else {
    sprintf("%s: %d native observations; %d marked month%s (%s).", meta$short, n, length(breaks_json),
            if (length(breaks_json) > 1) "s" else "",
            paste(vapply(found, function(b) b$month, character(1)), collapse = ", "))
  }

  outcomes[[length(outcomes) + 1]] <- list(
    id = oid, label = meta$label, short = meta$short,
    native_frequency = meta$native_frequency, regime = regime, native_in_window = n,
    span = span, status = status, method_detail = method_detail,
    breaks = breaks_json, plain_caption = caption, figure = figure, refused = refused)
}

artifact <- list(
  schema_version = "0.1.0", stage = spec$stage, layer = spec$layer, vintage = vintage,
  generated_at = format(Sys.time(), "%Y-%m-%dT%H:%M:%S%z"),
  generator = list(script = "analysis/R/09_changepoints.R", git_sha = git_sha),
  spec = list(path = "analysis/specs/changepoints.yml", md5 = unname(tools::md5sum(spec_path)), version = spec$version),
  verifier = "tests/verify_changepoints.py",
  input = list(database = "data/analytics.duckdb", native_table = "main_analytics.fact_observation_native",
               metric_dimension = "main_analytics.dim_metric",
               definition_break_table = "main_analytics.dim_definition_break",
               administrations_source = "registry/reference/administrations.json"),
  counts = list(
    outcomes_considered = length(outcomes),
    outcomes_searched = sum(vapply(outcomes, function(o) o$status %in% c("search", "no_break_detected"), logical(1))),
    outcomes_fixed_date = sum(vapply(outcomes, function(o) identical(o$status, "fixed_date"), logical(1))),
    outcomes_refused = sum(vapply(outcomes, function(o) identical(o$status, "refused"), logical(1))),
    breaks_estimated = sum(vapply(outcomes, function(o) sum(vapply(o$breaks, function(b) identical(b$kind, "estimated"), logical(1))), integer(1))),
    known_breaks_passed = sum(vapply(outcomes, function(o) sum(vapply(o$breaks, function(b) identical(b$kind, "known_definition_break"), logical(1))), integer(1)))),
  rules = list(method = spec$rules$method, package = spec$rules$package, criterion = spec$rules$criterion,
               input_rule = spec$rules$input_rule, min_native_search = spec$rules$min_native_search,
               min_native_fixed_date = spec$rules$min_native_fixed_date,
               max_breaks = spec$rules$max_breaks, definition_break_rule = spec$rules$definition_break_rule,
               attribution_rule = spec$rules$attribution_rule,
               forbidden_fields = unlist(spec$rules$forbidden_fields)),
  outcomes = outcomes,
  notes = c("description only: a break is a statement about a series, never about a presidency",
            "native observations only; the interpolated spine is never fitted",
            "a break near a handover records timing; it is not evidence that the handover caused it"))

out_path <- file.path(out_dir, "changepoints.json")
writeLines(toJSON(artifact, auto_unbox = TRUE, pretty = TRUE, digits = NA, null = "null", na = "null"),
           out_path, useBytes = TRUE)
cat(sprintf("wrote %s — %d outcomes, %d breaks estimated, %d refused, vintage %s\n",
            out_path, length(outcomes), artifact$counts$breaks_estimated,
            artifact$counts$outcomes_refused, vintage))

