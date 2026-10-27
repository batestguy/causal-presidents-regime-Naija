#!/usr/bin/env Rscript
# Outcome-series figures — one panel per outcome card, drawn from the analytical base.
#
# The artefact this writes is declared in `analysis/specs/series_figures.yml`: what a mark means, which
# window is drawn, what a shaded run is, and what the caption may say. Nothing here is typed — the counts,
# the span, the Stage 3 status and the definition breaks come out of the base, and the outcome's identity
# comes out of `analysis/specs/outcomes.yml`. The engine computes no statistic.
#
# The point of the figure is the thing the cards say in prose: **most of this data is not observations.**
# `u5mr` is 26 annual points stretched across 275 interpolated months; the two education outcomes stop in
# 2010 and cannot see any APC tenure. A chart that smoothed those into one line would defeat the reason the
# cards carry a reason instead of a number, so an interpolated month is drawn dotted and a month with no
# observation is drawn as nothing at all.
#
# Run:
#     Rscript analysis/R/07_series_figures.R
#
# Independent re-derivation of every count and every recorded byte: `tests/verify_series_figures.py`.

suppressPackageStartupMessages({
  library(yaml)
  library(jsonlite)
  library(DBI)
  library(duckdb)
  library(data.table)
})

# ---------------------------------------------------------------------------------------------
# Paths, spec, identity
# ---------------------------------------------------------------------------------------------
script_path <- function() {
  args <- commandArgs(trailingOnly = FALSE)
  hit <- grep("^--file=", args, value = TRUE)
  if (length(hit)) return(normalizePath(sub("^--file=", "", hit[1])))
  normalizePath("analysis/R/07_series_figures.R")
}
REPO_ROOT <- normalizePath(file.path(dirname(script_path()), "..", ".."))

spec_file <- "analysis/specs/series_figures.yml"
spec <- yaml::read_yaml(file.path(REPO_ROOT, spec_file))
outcomes_file <- file.path(REPO_ROOT, spec$input$outcomes_spec)
outcomes_spec <- yaml::read_yaml(outcomes_file)

vintage <- spec$labelled
out_dir <- file.path(REPO_ROOT, spec$output$root, vintage)
fig_dir <- file.path(out_dir, spec$output$figure_dir)
dir.create(fig_dir, showWarnings = FALSE, recursive = TRUE)

message(sprintf("Outcome-series figures — vintage %s", vintage))
message(sprintf("spec: %s", spec_file))

stop_if <- function(condition, ...) if (isTRUE(condition)) stop(sprintf(...), call. = FALSE)
`%||%` <- function(a, b) if (is.null(a)) b else a

generated_at <- format(Sys.time(), "%Y-%m-%dT%H:%M:%S%z")
git_sha <- tryCatch(suppressWarnings(system2("git", c("-C", shQuote(REPO_ROOT), "rev-parse", "--short", "HEAD"),
                                             stdout = TRUE, stderr = FALSE)), error = function(e) character(0))
git_sha <- if (length(git_sha) && nzchar(git_sha[[1]])) git_sha[[1]] else NA_character_
md5 <- function(path) unname(as.character(tools::md5sum(path)))

# ---------------------------------------------------------------------------------------------
# The base
# ---------------------------------------------------------------------------------------------
con <- DBI::dbConnect(duckdb::duckdb(), dbdir = file.path(REPO_ROOT, spec$input$database),
                      read_only = TRUE)
on.exit(DBI::dbDisconnect(con, shutdown = TRUE))

outcomes <- outcomes_spec$outcomes
ids <- vapply(outcomes, function(o) o$id, character(1))
stop_if(anyDuplicated(ids) > 0, "outcomes.yml repeats an outcome id, so a panel would be drawn twice")
stop_if(!isTRUE(spec$input$outcome_key_matches_metric_id),
        "this engine keys the panel on the outcome id; the spec must declare that the base agrees")

fact <- as.data.table(DBI::dbGetQuery(con, sprintf(
  "select metric_id, period_month, value, observation_type from %s order by metric_id, period_month",
  spec$input$fact_table)))
dimension <- as.data.table(DBI::dbGetQuery(con, sprintf(
  "select metric_id, label, unit, native_frequency, quality_status, is_landed from %s",
  spec$input$metric_dimension)))
native <- as.data.table(DBI::dbGetQuery(con, sprintf(
  "select metric_id, anchor_month, scope, value from %s", spec$input$native_table)))
breaks <- as.data.table(DBI::dbGetQuery(con, sprintf(
  "select metric_id, break_month, label, note from %s order by metric_id, break_month",
  spec$input$definition_break_table)))

stop_if(nrow(fact) == 0, "the base holds no fact rows — run dbt before drawing the series")

fact[, period_month := as.Date(period_month)]
breaks[, break_month := as.Date(break_month)]
native[, anchor_month := as.Date(anchor_month)]

unknown_types <- setdiff(unique(fact[metric_id %in% ids, observation_type]), names(spec$marks)[1:3])
stop_if(length(unknown_types) > 0,
        "the base uses observation_type(s) this spec does not define: %s — a new category is a change to the imputation rule",
        paste(unknown_types, collapse = ", "))

# The window is the spine's own span, read from the base rather than typed: the panels describe the series
# the models were fitted on.
window_first <- min(fact$period_month)
window_last <- max(fact$period_month)

# ---------------------------------------------------------------------------------------------
# Marks and helpers
# ---------------------------------------------------------------------------------------------
dec_year <- function(d) {
  as.integer(format(d, "%Y")) + (as.integer(format(d, "%m")) - 1) / 12
}
month_index <- function(d) {
  (as.integer(format(d, "%Y")) - as.integer(format(window_first, "%Y"))) * 12L +
    (as.integer(format(d, "%m")) - as.integer(format(window_first, "%m")))
}

direction_words <- c(down = "lower is better", up = "higher is better")

# Contiguous runs of an observation type, in the spine's own month order.
runs_of <- function(dt, type) {
  if (nrow(dt) == 0) return(list())
  dt <- dt[order(period_month)]
  idx <- month_index(dt$period_month)
  flag <- dt$observation_type == type
  r <- rle(flag)
  ends <- cumsum(r$lengths)
  starts <- ends - r$lengths + 1
  keep <- which(r$values)
  lapply(keep, function(k) {
    list(first = dt$period_month[starts[k]], last = dt$period_month[ends[k]],
         months = ends[k] - starts[k] + 1L)
  })
}

required_text <- function(block_label, unit, status, counts_line, direction, break_names) {
  c(block_label, unit, status, counts_line, direction, break_names)
}

glue_caption <- function(template, counts, first_observed, last_observed, frequency, status, break_names) {
  text <- template
  text <- gsub("{n_observed}", counts$observed, text, fixed = TRUE)
  text <- gsub("{n_interpolated}", counts$interpolated, text, fixed = TRUE)
  text <- gsub("{n_unobserved}", counts$unobserved, text, fixed = TRUE)
  text <- gsub("{first_observed}", if (is.na(first_observed)) "none" else format(first_observed, "%Y-%m"),
               text, fixed = TRUE)
  text <- gsub("{last_observed}", if (is.na(last_observed)) "none" else format(last_observed, "%Y-%m"),
               text, fixed = TRUE)
  text <- gsub("{native_frequency}", frequency, text, fixed = TRUE)
  text <- gsub("{quality_status}", status, text, fixed = TRUE)
  breaks_clause <- if (length(break_names) == 0) "" else
    sprintf(" Definition break%s annotated: %s.", if (length(break_names) == 1) "" else "s",
            paste(break_names, collapse = "; "))
  gsub("{breaks_clause}", breaks_clause, text, fixed = TRUE)
}

svg_has_text <- function(path, needles) {
  svg <- paste(readLines(path, warn = FALSE), collapse = "\n")
  texts <- regmatches(svg, gregexpr("<text[^>]*>[^<]*</text>", svg))[[1]]
  rendered <- gsub("<[^>]*>", "", texts)
  rendered <- gsub("&amp;", "&", rendered)
  vapply(needles, function(n) any(grepl(n, rendered, fixed = TRUE)), logical(1))
}

# ---------------------------------------------------------------------------------------------
# One panel per outcome
# ---------------------------------------------------------------------------------------------
panels <- vector("list", length(outcomes))
index_rows <- vector("list", length(outcomes))

# The figure's size is recorded on its *canonical* bytes (CRLF collapsed to LF), because `.gitattributes`
# stores this repository's text with `eol=lf`. A raw `file.info()$size` is true only on the Windows checkout
# that produced it: after any clone or the Linux runner the file is a few hundred bytes smaller and the
# contract test would call a fresh panel stale. The Python consumers apply the same rule.
canonical_bytes <- function(path) {
  bytes_raw <- readBin(path, "raw", n = file.info(path)$size)
  if (length(bytes_raw) == 0) return(0L)
  is_cr <- bytes_raw == as.raw(13)
  is_lf <- bytes_raw == as.raw(10)
  crlf <- is_cr & c(is_lf[-1], FALSE)
  sum(!crlf)
}

for (i in seq_along(outcomes)) {
  o <- outcomes[[i]]
  id <- o$id
  d <- dimension[metric_id == id]
  stop_if(nrow(d) != 1,
          "%s: the metric dimension has %d row(s) for this outcome; a panel without a unit or a Stage 3 status is not publishable",
          id, nrow(d))
  rows <- fact[metric_id == id]
  drawable <- nrow(rows) > 0
  label <- d$label[1]
  unit <- d$unit[1]
  status <- d$quality_status[1]
  frequency <- d$native_frequency[1]
  direction <- direction_words[[o$direction %||% "undeclared"]] %||%
    sprintf("%s (direction undeclared)", o$direction %||% "?")

  counts <- if (drawable) {
    list(observed = rows[observation_type == "observed", .N],
         interpolated = rows[observation_type == "interpolated", .N],
         unobserved = rows[observation_type == "unobserved", .N])
  } else {
    list(observed = 0L, interpolated = 0L, unobserved = 0L)
  }
  first_observed <- if (counts$observed > 0)
    min(rows[observation_type == "observed", period_month]) else as.Date(NA)
  last_observed <- if (counts$observed > 0)
    max(rows[observation_type == "observed", period_month]) else as.Date(NA)

  in_window <- if (nrow(breaks[metric_id == id]) > 0)
    breaks[metric_id == id & break_month >= window_first & break_month <= window_last] else
    breaks[0]
  break_names <- as.character(in_window$label)

  # A native row with no value is the source's own gap (the World Bank emits a 2025 row for `u5mr` with
  # nothing in it), and counting it as an observation would overstate the data by one month per year.
  native_in_window <- nrow(native[metric_id == id & anchor_month >= window_first &
                                    anchor_month <= window_last & !is.na(value)])

  counts_line <- sprintf("observed %d  ·  interpolated %d  ·  no observation %d of %d months",
                         counts$observed, counts$interpolated, counts$unobserved, nrow(rows))
  if (!drawable) counts_line <- "no rows in the analytical base"

  caption <- if (!drawable) {
    gsub("{vintage}", vintage,
         spec$caption$absence_clause, fixed = TRUE)
  } else {
    base_caption <- glue_caption(spec$caption$format, counts, first_observed, last_observed,
                                 frequency, status, break_names)
    if (counts$unobserved > 0 && !is.na(last_observed) && last_observed < window_last) {
      base_caption <- paste0(base_caption,
                             gsub("{last_observed}", format(last_observed, "%Y-%m"), fixed = TRUE,
                                  spec$caption$no_observation_clause))
    }
    base_caption
  }

  fig_name <- sprintf(spec$output$figure_name, id)
  fig_path <- file.path(fig_dir, fig_name)

  svglite::svglite(fig_path, width = spec$figure$width_in, height = spec$figure$height_in)
  par(mar = c(4.6, 4.4, 3.6, 1.4), cex.axis = 0.85)

  if (!drawable) {
    plot(NA, xlim = c(0, 1), ylim = c(0, 1), axes = FALSE, xlab = "", ylab = "")
    title(main = sprintf("%s (%s)", label, unit), cex.main = 0.98, font.main = 2)
    text(0.5, 0.62, "No series in the analytical base", cex = 1.15, font = 2)
    text(0.5, 0.44, sprintf("stage 3: %s  ·  %s", status, direction), cex = 0.85)
    text(0.5, 0.26, strwrap(o$coverage_note %||% "the card carries the reason", 88), cex = 0.72)
  } else {
    rows <- rows[order(period_month)]
    vals <- rows[observation_type != "unobserved", value]
    y_range <- if (length(vals) && diff(range(vals, na.rm = TRUE)) > 0) range(vals, na.rm = TRUE) else c(0, 1)
    pad <- max(diff(y_range) * 0.08, abs(mean(y_range)) * 0.02, 0.05)
    y_lim <- y_range + c(-pad, pad)

    plot(NA, xlim = c(dec_year(window_first) - 0.2, dec_year(window_last) + 0.2), ylim = y_lim,
         xlab = "", ylab = unit, main = "", axes = FALSE)
    axis(1, at = dec_year(seq(window_first, window_last, by = "year")), labels = FALSE, tcl = -0.25)
    years <- seq(as.integer(format(window_first, "%Y")), as.integer(format(window_last, "%Y")))
    ticks <- years[years %% 5 == 0]
    axis(1, at = ticks, labels = ticks, tick = FALSE, line = -0.45, cex.axis = 0.82)
    axis(2, las = 1)

    # Shaded runs of no observation: declared in the spec, sized in months, and the trailing run is always
    # shown because "the series stops here" is the single most important thing some of these panels say.
    shade <- Filter(function(r) r$months >= spec$marks$min_shaded_run_months, runs_of(rows, "unobserved"))
    trailing <- runs_of(rows, "unobserved")
    if (length(trailing) && identical(trailing[[length(trailing)]]$last, window_last)) {
      shade <- unique(c(shade, trailing[length(trailing)]))
    }
    for (r in shade) {
      rect(dec_year(r$first) - 1 / 24, y_lim[1], dec_year(r$last) + 1 / 24, y_lim[2],
           col = "#f2f2f2", border = NA)
      text((dec_year(r$first) + dec_year(r$last)) / 2, y_lim[2] - pad * 0.35,
           "no observation", cex = 0.68, col = "grey35", srt = 90)
    }

    # What the monthly model saw: the spine, joined where it was filled. Dotted wherever an end of the
    # segment is interpolated; solid only between two adjacent observed months.
    rows[, x := dec_year(period_month)]
    rows[, observed := observation_type == "observed"]
    if (nrow(rows) > 1) {
      for (j in seq_len(nrow(rows) - 1)) {
        a <- rows[j]; b <- rows[j + 1]
        if (a$observation_type == "unobserved" || b$observation_type == "unobserved") next
        both_observed <- a$observed && b$observed
        segments(a$x, a$value, b$x, b$value,
                 lty = if (both_observed) 1 else 3,
                 lwd = if (both_observed) 1.4 else 1.1,
                 col = if (both_observed) "black" else "grey45")
      }
    }
    points(rows[observed == TRUE, x], rows[observed == TRUE, value], pch = 19, cex = 0.62)
    points(rows[observed == TRUE, x], rows[observed == TRUE, value], pch = 1, cex = 1.15, col = "grey20")

    if (nrow(in_window) > 0) {
      for (k in seq_len(nrow(in_window))) {
        abline(v = dec_year(in_window$break_month[k]), lty = 2, col = "grey30", lwd = 1.1)
        text(dec_year(in_window$break_month[k]), y_lim[2], paste0(" ", in_window$label[k], " "),
             srt = 90, adj = c(1, 1), cex = 0.66, col = "grey25", xpd = NA)
      }
    }

    title(main = sprintf("%s (%s)", label, unit), cex.main = 0.98, font.main = 2, line = 2.1)
    mtext(sprintf("stage 3: %s  ·  native frequency: %s  ·  %s", status, frequency, direction),
          side = 3, line = 0.45, cex = 0.7, col = "grey25")
    mtext(counts_line, side = 1, line = 3.2, cex = 0.72, col = "grey25")
    legend("topright", bty = "n", cex = 0.72,
           legend = c(sprintf("observed (%d)", counts$observed),
                      sprintf("interpolated (%d)", counts$interpolated),
                      sprintf("no observation (%d)", counts$unobserved)),
           pch = c(19, NA, 15), lty = c(NA, 3, NA),
           col = c("black", "grey45", "#d9d9d9"), pt.cex = c(0.9, NA, 1.6))
  }
  dev.off()

  needles <- required_text(label, unit, sprintf("stage 3: %s", status), counts_line, direction, break_names)
  present <- svg_has_text(fig_path, needles)
  stop_if(!all(present) ,
          "%s: the figure does not carry as text: %s — a label that did not render is a figure that cannot be checked",
          id, paste(needles[!present], collapse = " | "))

  index_rows[[i]] <- list(
    id = id,
    label = label,
    short = o$short %||% label,
    domain = o$domain %||% NA_character_,
    unit = unit,
    direction = o$direction %||% NA_character_,
    source = o$source %||% NA_character_,
    native_frequency = frequency,
    quality_status = status,
    drawable = drawable,
    window = list(first = format(window_first, "%Y-%m"), last = format(window_last, "%Y-%m")),
    observations = counts,
    native_in_window = native_in_window,
    first_observed = if (is.na(first_observed)) NA_character_ else format(first_observed, "%Y-%m"),
    last_observed = if (is.na(last_observed)) NA_character_ else format(last_observed, "%Y-%m"),
    definition_breaks = if (nrow(in_window) == 0) list() else
      lapply(seq_len(nrow(in_window)), function(k) list(
        date = format(in_window$break_month[k], "%Y-%m"),
        name = in_window$label[k],
        note = in_window$note[k])),
    caption = caption,
    figure = list(path = sprintf("registry/series/%s/%s/%s", vintage, spec$output$figure_dir, fig_name),
                  bytes = canonical_bytes(fig_path))
  )

  message(sprintf("  %-18s observed %3d  interpolated %3d  none %3d  breaks %d  (%d bytes)",
                  id, counts$observed, counts$interpolated, counts$unobserved, length(break_names),
                  canonical_bytes(fig_path)))
  panels[[i]] <- index_rows[[i]]
}

# ---------------------------------------------------------------------------------------------
# The index
# ---------------------------------------------------------------------------------------------
spine_by_type <- fact[metric_id %in% ids, .N, by = observation_type]
type_count <- function(type) {
  hit <- spine_by_type[observation_type == type]
  if (nrow(hit)) as.integer(hit$N[1]) else 0L
}

document <- list(
  schema_version = "0.1.0",
  stage = "9-prep",
  layer = "outcome series, drawn from the analytical base",
  vintage = vintage,
  generated_at = generated_at,
  generator = list(script = spec$engine, git_sha = git_sha),
  spec = list(path = spec_file, md5 = md5(file.path(REPO_ROOT, spec_file)), version = spec$version),
  verifier = spec$verifier,
  input = list(
    database = spec$input$database,
    fact_table = spec$input$fact_table,
    native_table = spec$input$native_table,
    metric_dimension = spec$input$metric_dimension,
    definition_break_table = spec$input$definition_break_table,
    outcomes_spec = spec$input$outcomes_spec,
    outcomes_spec_md5 = md5(outcomes_file)
  ),
  window = list(first = format(window_first, "%Y-%m"), last = format(window_last, "%Y-%m")),
  counts = list(
    outcomes = length(index_rows),
    drawable = sum(vapply(index_rows, function(r) isTRUE(r$drawable), logical(1))),
    flagged = sum(vapply(index_rows, function(r) identical(r$quality_status, "flagged"), logical(1))),
    with_definition_break = sum(vapply(index_rows, function(r) length(r$definition_breaks) > 0, logical(1))),
    spine_rows = list(observed = type_count("observed"),
                      interpolated = type_count("interpolated"),
                      unobserved = type_count("unobserved"))
  ),
  marks = list(observed = spec$marks$observed,
               interpolated = spec$marks$interpolated,
               unobserved = spec$marks$unobserved,
               min_shaded_run_months = spec$marks$min_shaded_run_months),
  outcomes = unname(index_rows),
  notes = list(
    "One panel per outcome in analysis/specs/outcomes.yml, keyed on the outcome id, which is the metric id in the base.",
    "An observed month is a dot; an interpolated month is a dotted segment (the imputation rule made visible); a month with no observation is nothing, and a run of them is shaded and labelled.",
    "Counts, span, Stage 3 status and definition breaks are read from the base; the engine computes no statistic.",
    "Each figure's byte count is recorded here and compared to the file; a figure one dbt run behind its rows fails rather than being noticed by a reader."
  )
)

writeLines(jsonlite::toJSON(document, auto_unbox = TRUE, pretty = TRUE, null = "null", na = "null",
                            digits = 10),
           file.path(out_dir, spec$output$index))
cat(sprintf("\nPASS - %d panel(s) written to registry/series/%s (%d drawable, %d flagged)\n",
            length(index_rows), vintage, document$counts$drawable, document$counts$flagged))
