#!/usr/bin/env Rscript
# 01_build_dags.R — build the causal-graph (DAG) layer of the model registry.
#
# For every outcome in analysis/specs/outcomes.yml and every identification design in
# analysis/specs/dag_designs.yml this script:
#   1. instantiates the design's node/edge template for that outcome,
#   2. validates the graph is acyclic,
#   3. computes the backdoor adjustment set with dagitty on the "assumed" graph (unobserved
#      nodes removed -- the working assumption the estimate leans on),
#   4. renders the full graph to SVG with ggdag on deterministic dagitty coordinates,
#   5. checks the rendered SVG actually carries every node label and that no label overflows
#      its node,
#   6. attaches the Stage 5 pre-analysis diagnostics for that (outcome, design) pair, and
#   7. writes one JSON card per (outcome, design) plus an index.
#
# Step 6 is a hard dependency, not a nicety. PHASES.md Stage 5's exit criterion is that every model
# has a stated identifying assumption *and the specific diagnostic that supports it*; a card that
# declares an assumption with no pre-check attached is the thing that stage exists to prevent. So if
# registry/diagnostics/<vintage>/diagnostics.json is missing, this script stops and says so.
#
# Run order:
#   Rscript analysis/R/02_diagnostics.R   # Stage 5 pre-checks (needs the Stage 4 base built)
#   Rscript analysis/R/01_build_dags.R    # cards carrying those pre-checks
#
# The graph is the assumption. The adjustment set it yields is what the estimator will later
# condition on, so the app can say "given this causal model, here is what is being held fixed
# and here is what must be assumed absent" before any number is shown.
#
# The exposure is always the administration/regime. The three designs differ in how it is
# operationalised: (A) the differential state dose of a federal policy shift, (B) the
# party-by-tenure dummy in a national time series, (C) the treated tenure in a cross-country
# synthetic control.
#
# Usage:
#   Rscript analysis/R/01_build_dags.R
#
# Writes:
#   registry/dags/<outcome_id>__<design_id>.svg
#   registry/dags/<outcome_id>__<design_id>.json
#   registry/dags/index.json

suppressPackageStartupMessages({
  library(yaml)
  library(jsonlite)
  library(dagitty)
  library(ggdag)
  library(ggplot2)
})

SCHEMA_VERSION <- "0.2.0"   # 0.2.0 adds the required `diagnostics` block (Stage 5)
GENERATOR <- "analysis/R/01_build_dags.R"
NODE_WRAP <- 16   # characters per label line, so text stays inside the node circle
NODE_SIZE <- 24   # node diameter in mm; at 72 px/inch this is ~68 px of room per label line
TEXT_SIZE <- 2.3
ASSUMED_SUFFIX <- " (assumed absent)"

# ------------------------------------------------------------------------------------------
# paths
# ------------------------------------------------------------------------------------------
find_root <- function() {
  args <- commandArgs(trailingOnly = FALSE)
  file_arg <- grep("^--file=", args, value = TRUE)
  starts <- character(0)
  if (length(file_arg)) starts <- c(starts, dirname(sub("^--file=", "", file_arg[[1]])))
  starts <- c(starts, getwd())
  for (s in starts) {
    d <- normalizePath(s, mustWork = FALSE)
    for (i in seq_len(10)) {
      if (file.exists(file.path(d, "analysis", "specs", "outcomes.yml"))) return(d)
      parent <- dirname(d)
      if (identical(parent, d)) break
      d <- parent
    }
  }
  stop("could not locate repo root (searched upward for analysis/specs/outcomes.yml)")
}

root <- find_root()
spec_dir <- file.path(root, "analysis", "specs")
out_dir <- file.path(root, "registry", "dags")
dir.create(out_dir, showWarnings = FALSE, recursive = TRUE)

outcomes <- read_yaml(file.path(spec_dir, "outcomes.yml"))$outcomes
designs <- read_yaml(file.path(spec_dir, "dag_designs.yml"))$designs

# ---- Stage 5 diagnostics, which the cards carry -------------------------------------------
diag_root <- file.path(root, "registry", "diagnostics")
diag_vintages <- if (dir.exists(diag_root))
  sort(list.files(diag_root, pattern = "^[0-9]{4}-[0-9]{2}-[0-9]{2}$")) else character(0)
if (length(diag_vintages) == 0) {
  stop("no registry/diagnostics/<vintage>/diagnostics.json.\n",
       "  Stage 5 must run before the cards are published, so that every card carries its own ",
       "pre-analysis diagnostics (PHASES.md Stage 5 exit criterion).\n",
       "  Run:  Rscript analysis/R/02_diagnostics.R")
}
diag_vintage <- diag_vintages[[length(diag_vintages)]]
diag_path <- file.path(diag_root, diag_vintage, "diagnostics.json")
if (!file.exists(diag_path)) stop(sprintf("missing %s", diag_path))
diagnostics <- jsonlite::fromJSON(diag_path, simplifyVector = FALSE)
cat(sprintf("diagnostics vintage %s | %d pre-check statuses | design verdicts: %s\n",
            diag_vintage, length(diagnostics$cards),
            paste(vapply(names(diagnostics$design_verdicts),
                         function(k) sprintf("%s=%s", k, diagnostics$design_verdicts[[k]]$status),
                         character(1)), collapse = " ")))


# The vintage is the *data* vintage, taken from the diagnostics they carry, not the date the script
# happened to run. A card is a statement about a data vintage; stamping it with the run date would
# let a re-run pass itself off as new evidence, and would disagree with registry/quality/<vintage>
# and registry/diagnostics/<vintage>, which both use the data vintage. `generated_at` records when
# the card was produced.
vintage <- diag_vintage
generated_at <- format(Sys.time(), "%Y-%m-%dT%H:%M:%S%z")

git_sha <- tryCatch(
  suppressWarnings(system2("git", c("-C", shQuote(root), "rev-parse", "--short", "HEAD"),
                           stdout = TRUE, stderr = FALSE)),
  error = function(e) character(0)
)
git_sha <- if (length(git_sha) && nzchar(git_sha[[1]])) git_sha[[1]] else NA_character_

# ------------------------------------------------------------------------------------------
# helpers
# ------------------------------------------------------------------------------------------
# Word-wrap a label so every line fits inside a node circle.
wrap_label <- function(x, width = NODE_WRAP) {
  words <- strsplit(x, "\\s+")[[1]]
  lines <- character(0)
  cur <- ""
  for (w in words) {
    cand <- if (nzchar(cur)) paste(cur, w) else w
    if (nchar(cand) > width && nzchar(cur)) {
      lines <- c(lines, cur)
      cur <- w
    } else {
      cur <- cand
    }
  }
  if (nzchar(cur)) lines <- c(lines, cur)
  paste(lines, collapse = "\n")
}

# Build a dagitty DAG string. `pos` pins the layout so it is reproducible; node status carries
# exposure/outcome/unobserved so dagitty can compute the adjustment set from the graph itself.
dag_text <- function(nodes, edges) {
  stopifnot(length(nodes) > 0)
  lines <- "dag {"
  for (n in nodes) {
    attrs <- sprintf('pos = "%s"', n$pos)
    if (identical(n$role, "exposure")) attrs <- c(attrs, "exposure")
    if (identical(n$role, "outcome")) attrs <- c(attrs, "outcome")
    if (!isTRUE(n$observed)) attrs <- c(attrs, "unobserved")
    lines <- c(lines, sprintf("  %s [%s]", n$id, paste(attrs, collapse = ", ")))
  }
  for (e in edges) lines <- c(lines, sprintf("  %s -> %s", e$from, e$to))
  paste(c(lines, "}"), collapse = "\n")
}

# Instantiate a design template for one outcome: outcome node labels substituted, domain-gated
# nodes kept only where the outcome's domain qualifies, dangling edges dropped.
instantiate <- function(design, outcome) {
  keep <- vapply(design$nodes, function(n) {
    wd <- n$when_domain
    is.null(wd) || (outcome$domain %in% as.character(wd))
  }, logical(1))
  nodes <- lapply(design$nodes[keep], function(n) {
    n$label <- gsub("{{outcome_label}}", outcome$label, n$label, fixed = TRUE)
    n$short <- gsub("{{outcome_short}}", outcome$short, n$short, fixed = TRUE)
    n$source <- gsub("{{outcome_source}}", outcome$source, n$source, fixed = TRUE)
    # The outcome node's provenance is the outcome's, not the template's: an outcome with no
    # usable series is a declared gap, and that must show up as one on the card.
    if (identical(n$role, "outcome")) {
      n$source_status <- switch(
        outcome$coverage_status,
        ok = "acquired", partial = "acquired",
        declared_gap = "gap", blocked = "gap", "gap"
      )
    }
    if (is.null(n$observed)) n$observed <- TRUE
    n
  })
  ids <- vapply(nodes, function(n) n$id, character(1))
  edges <- Filter(function(e) e$from %in% ids && e$to %in% ids, design$edges)
  list(nodes = nodes, edges = edges, ids = ids)
}

as_set_list <- function(sets) {
  if (length(sets) == 0) return(list())
  lapply(seq_along(sets), function(i) I(as.character(sets[[i]])))
}

# force array even for length one: jsonlite's auto_unbox would otherwise emit a scalar and
# break the card schema (adjustment_set / assumption_required are arrays)

# Read back the rendered SVG and confirm it carries every node label line and that no line is
# wider than the node it sits in. Cheap guard against a silently unreadable figure.
check_svg <- function(path, expected_lines) {
  svg <- paste(readLines(path, warn = FALSE), collapse = "\n")
  texts <- regmatches(svg, gregexpr("<text[^>]*>.*?</text>", svg))[[1]]
  if (length(texts) == 0) return(list(missing = expected_lines, too_wide = character(0)))
  rendered <- vapply(texts, function(x) trimws(gsub("<[^>]*>", "", sub("^[^>]*>", "", x))),
                     character(1), USE.NAMES = FALSE)
  widths <- suppressWarnings(as.numeric(sub(".*textLength='([0-9.]+)px'.*", "\\1", texts)))
  diam_px <- NODE_SIZE / 25.4 * 72
  missing <- setdiff(expected_lines, rendered)
  too_wide <- character(0)
  for (line in expected_lines) {
    i <- match(line, rendered)
    if (!is.na(i) && !is.na(widths[i]) && widths[i] > diam_px) too_wide <- c(too_wide, line)
  }
  list(missing = missing, too_wide = too_wide)
}

write_json_file <- function(x, path) {
  writeLines(jsonlite::toJSON(x, auto_unbox = TRUE, pretty = TRUE, null = "null",
                              na = "null", digits = 6),
             path, useBytes = TRUE)
}

# ------------------------------------------------------------------------------------------
# build
# ------------------------------------------------------------------------------------------
cards <- list()
failures <- character(0)

cat(sprintf("vintage %s | %d outcomes x %d designs = %d DAGs\n\n",
            vintage, length(outcomes), length(designs), length(outcomes) * length(designs)))
cat(sprintf("%-18s %-3s %-32s %-34s %-6s %s\n", "outcome", "dsg", "adjustment set",
            "stage 5 status (assumed absent)", "gaps", "svg"))
cat(strrep("-", 130), "\n")

for (outcome in outcomes) {
  for (design in designs) {
    dag_id <- sprintf("%s__%s", outcome$id, design$id)
    fail <- function(msg) failures <<- c(failures, sprintf("%s: %s", dag_id, msg))

    inst <- instantiate(design, outcome)
    # Stage 1 exit criterion: every variable maps to a named source, or is a declared gap.
    for (n in inst$nodes) {
      if (is.null(n$source) || is.null(n$source_status) ||
          !nzchar(n$source) || !nzchar(n$source_status)) {
        fail(sprintf("node '%s' has no source recorded", n$id))
      }
    }
    full_txt <- dag_text(inst$nodes, inst$edges)
    g_full <- tryCatch(as.dagitty(full_txt), error = function(e) {
      fail(sprintf("dagitty parse failed (%s)", conditionMessage(e)))
      NULL
    })
    if (is.null(g_full)) next

    if (!isAcyclic(g_full)) {
      fail("graph is not acyclic")
      next
    }

    assumed_nodes <- Filter(function(n) isTRUE(n$observed), inst$nodes)
    assumed_ids <- vapply(assumed_nodes, function(n) n$id, character(1))
    assumed_edges <- Filter(function(e) e$from %in% assumed_ids && e$to %in% assumed_ids,
                            inst$edges)
    assumed_txt <- dag_text(assumed_nodes, assumed_edges)
    g_assumed <- as.dagitty(assumed_txt)

    # minimal adjustment sets for the total effect, by the backdoor criterion
    sets <- as_set_list(adjustmentSets(g_assumed, type = "minimal", effect = "total"))
    adj_set <- if (length(sets)) sets[[1]] else character(0)
    unobserved <- Filter(function(n) !isTRUE(n$observed), inst$nodes)
    assumption_required <- vapply(unobserved, function(n) n$id, character(1))

    # ---- render ---------------------------------------------------------------------------
    svg_name <- sprintf("%s.svg", dag_id)
    svg_path <- file.path(out_dir, svg_name)
    df <- tryCatch(as.data.frame(tidy_dagitty(g_full, layout = "dagitty")),
                   error = function(e) NULL)
    if (is.null(df)) {
      fail("tidy_dagitty failed")
      next
    }
    unknown <- setdiff(inst$ids, df$name)
    if (length(unknown)) {
      fail(sprintf("node(s) absent from the rendered layout: %s", paste(unknown, collapse = ", ")))
      next
    }

    labs <- setNames(vapply(inst$nodes, function(n) n$short, character(1)), inst$ids)
    observed_flag <- setNames(vapply(inst$nodes, function(n) isTRUE(n$observed), logical(1)),
                              inst$ids)
    lab_row <- unname(vapply(labs[df$name], wrap_label, character(1)))
    unobs_row <- !observed_flag[df$name]
    # the assumption stays on its own line so it cannot be word-split away
    lab_row[unobs_row] <- paste0(lab_row[unobs_row], "\n", wrap_label(trimws(ASSUMED_SUFFIX)))
    df$node_label <- lab_row

    exposure_short <- labs[[design$exposure]]
    # The figure states the pre-check outcome, because a graph published with no indication that its
    # design failed its own gate is the most misleading artefact this layer could produce.
    diag_status <- diagnostics$cards[[dag_id]]$status %||% "not_run"
    diag_line <- switch(diag_status,
      pass = "Stage 5 pre-check: PASSED - this design survives.",
      degraded = "Stage 5 pre-check: RUNS DEGRADED - see the deviations on the card.",
      fail = sprintf("Stage 5 pre-check: FAILED - %s",
                     diagnostics$cards[[dag_id]]$blocker %||% "a pre-check did not pass"),
      not_attempted = "Stage 5 pre-check: NOT ATTEMPTED - no data for this outcome in the donor pool.",
      sprintf("Stage 5 pre-check: %s", diag_status)
    )
    caption <- sprintf(
      "The exposure is the administration. Node(s) labelled '%s' are unobserved and are assumed absent.\nBackdoor adjustment set: %s.\n%s\nThe estimate is attached at Stages 6-7.",
      trimws(ASSUMED_SUFFIX),
      if (length(adj_set)) paste(adj_set, collapse = ", ") else "none (no open backdoor path)",
      diag_line
    )
    p <- ggplot(df, aes(x = x, y = y, xend = xend, yend = yend)) +
      geom_dag_edges() +
      geom_dag_node(size = NODE_SIZE) +
      geom_dag_text(aes(label = node_label), size = TEXT_SIZE) +
      theme_dag() +
      labs(
        title = sprintf("%s - Design %s: %s", outcome$label, design$id, design$name),
        subtitle = sprintf("Unit: %s  |  Exposure: %s  |  Outcome: %s",
                           design$unit, exposure_short, outcome$short),
        caption = caption
      ) +
      theme(plot.title = element_text(size = 11, face = "bold"),
            plot.subtitle = element_text(size = 8.5, colour = "grey30"),
            plot.caption = element_text(hjust = 0, size = 7.5, colour = "grey30"))

    rendered <- tryCatch({
      ggsave(svg_path, p, width = 10, height = 6.5, bg = "white")
      file.exists(svg_path) && file.info(svg_path)$size > 0
    }, error = function(e) {
      fail(sprintf("render failed (%s)", conditionMessage(e)))
      FALSE
    })
    if (!isTRUE(rendered)) next

    expected_lines <- unique(unlist(strsplit(df$node_label, "\n", fixed = TRUE)))
    chk <- check_svg(svg_path, expected_lines)
    if (length(chk$missing)) fail(sprintf("label(s) missing from svg: %s",
                                          paste(chk$missing, collapse = " | ")))
    if (length(chk$too_wide)) fail(sprintf("label(s) overflow their node: %s",
                                           paste(chk$too_wide, collapse = " | ")))

    # ---- card -----------------------------------------------------------------------------
    card <- list(
      dag_id = dag_id,
      schema_version = SCHEMA_VERSION,
      vintage_date = vintage,
      generated_at = generated_at,
      generator = list(script = GENERATOR, git_sha = git_sha),
      outcome = list(
        id = outcome$id, label = outcome$label, short = outcome$short,
        domain = outcome$domain, unit = outcome$unit, direction = outcome$direction,
        frequency = outcome$frequency, source = outcome$source,
        coverage_status = outcome$coverage_status, coverage_note = outcome$coverage_note
      ),
      design = list(
        id = design$id, name = design$name, short = design$short, unit = design$unit,
        estimand = design$estimand, estimator = design$estimator,
        exposure_node = design$exposure, outcome_node = design$outcome,
        adjustment_criterion = design$adjustment_criterion,
        design_controls = I(as.character(design$design_controls))
      ),
      nodes = lapply(inst$nodes, function(n) list(
        id = n$id, label = n$label, short = n$short, role = n$role,
        observed = isTRUE(n$observed), source = n$source, source_status = n$source_status
      )),
      edges = lapply(inst$edges, function(e) list(from = e$from, to = e$to)),
      adjustment_set = I(adj_set),
      adjustment_sets = sets,
      assumption_required = I(assumption_required),
      identifying_assumption = design$identifying_assumption,
      cannot_rule_out = I(as.character(design$cannot_rule_out)),
      dagitty_full = full_txt,
      dagitty_assumed = assumed_txt,
      diagnostics = diagnostics$cards[[dag_id]],
      assets = list(svg = sprintf("registry/dags/%s", svg_name)),
      estimate = list(
        status = "not_estimated",
        model_card_ref = NA,
        note = "Estimates are attached at Stages 6-7; a card without an interval does not ship (docs/decisions.md M-02)."
      )
    )

    write_json_file(card, file.path(out_dir, sprintf("%s.json", dag_id)))
    cards[[dag_id]] <- card

    n_gaps <- sum(vapply(inst$nodes, function(n) identical(n$source_status, "gap"), logical(1)))
    cat(sprintf("%-18s %-3s %-32s %-34s %-6s %s\n", outcome$id, design$id,
                if (length(adj_set)) paste(adj_set, collapse = ", ") else "(none)",
                sprintf("%s (absent: %s)",
                        diagnostics$cards[[dag_id]]$status %||% "not_run",
                        if (length(assumption_required)) paste(assumption_required, collapse = ",") else "none"),
                n_gaps,
                if (length(chk$missing) || length(chk$too_wide)) "CHECK FAILED" else "ok"))
  }
}

# ------------------------------------------------------------------------------------------
# index
# ------------------------------------------------------------------------------------------
index <- list(
  schema_version = SCHEMA_VERSION,
  layer = "causal DAGs (assumption layer) - no estimates attached",
  vintage_date = vintage,
  generated_at = generated_at,
  generator = list(script = GENERATOR, git_sha = git_sha),
  # Stage 5's answer, carried on the index so the app can say which causal models survive their
  # pre-checks without reading 36 cards. The per-card detail stays on the cards.
  diagnostics = list(
    vintage = diag_vintage,
    source = sprintf("registry/diagnostics/%s/diagnostics.json", diag_vintage),
    spec = diagnostics$spec,
    design_verdicts = diagnostics$design_verdicts,
    status_counts = as.list(table(vapply(cards, function(c) c$diagnostics$status %||% "not_run",
                                        character(1))))
  ),
  counts = list(outcomes = length(outcomes), designs = length(designs), dags = length(cards)),
  designs = I(lapply(designs, function(d) list(
    id = d$id, name = d$name, short = d$short, unit = d$unit, estimand = d$estimand
  ))),
  outcomes = I(lapply(outcomes, function(o) list(
    id = o$id, label = o$label, domain = o$domain, direction = o$direction,
    coverage_status = o$coverage_status
  ))),
  dags = I(unname(lapply(cards, function(c) list(
    dag_id = c$dag_id, outcome_id = c$outcome$id, design_id = c$design$id,
    svg = c$assets$svg, adjustment_set = c$adjustment_set,
    assumption_required = I(c$assumption_required),
    diagnostics_status = c$diagnostics$status %||% "not_run",
    diagnostics_blocker = c$diagnostics$blocker %||% NA_character_
  )))),
  # Stage 1's exit criterion, made machine-readable: every variable a design needs either
  # resolves to a named source or is listed here as a declared gap.
  variables_still_missing = I(sort(unique(unlist(lapply(cards, function(c)
    vapply(Filter(function(n) identical(n$source_status, "gap"), c$nodes),
           function(n) sprintf("%s [%s]", n$label, n$source), character(1)))))))
)
write_json_file(index, file.path(out_dir, "index.json"))

cat("\n")
if (length(failures)) {
  cat(sprintf("FAILED - %d problem(s):\n", length(failures)))
  for (f in failures) cat(sprintf("  - %s\n", f))
  quit(status = 1)
}
cat(sprintf("PASS - %d cards written to registry/dags (vintage %s)\n", length(cards), vintage))
