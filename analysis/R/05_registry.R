#!/usr/bin/env Rscript
# Stage 8 — registry assembly.
#
# Stage 9 has to be buildable without opening R (PHASES.md Stage 8). That means the app never reads
# registry/estimates/ or registry/robustness/ directly: it reads the cards and the index, and every number
# it can show is already on the card next to the assumption it rests on, with its source named.
#
# This engine is the layer that does that copying, and it is deliberately the dullest script in the repo:
# it computes no estimates, fits nothing, and invents no numbers. Its whole job is:
#
#   1. **Attach** the published specification to the cards it is actually about — and only those. Design A
#      published three catalogue outcomes, so exactly three cards carry a number.
#   2. **Refuse to attach it to the rest.** Design B's nine published specifications measure the national
#      FAAC channel, which on every B card is a *mediator* node, not the outcome. Nine cards that a reader
#      would expect to carry a number carry a reason instead. Putting the channel's coefficient on them
#      would make the registry lie in the most expensive direction.
#   3. **Say why**, on every card that carries none: a closed set of reasons (analysis/specs/registry.yml),
#      so "no estimate" is never silent.
#   4. **Lift the design-level results onto the index**, once, where the app can show them without implying
#      they belong to any one card.
#
# Ordering: this runs *after* analysis/R/01_build_dags.R, which writes the cards wholesale and resets the
# estimate block. `scripts/verify.sh` runs them in that order, and tests/verify_registry.py fails if a card
# that should carry a number does not — which is what a reset looks like from the outside.
#
# Everything it writes is a copy of a published artifact's own field. If a number here disagreed with the
# artifact it names, the verifier would fail rather than the app quietly showing it.

suppressPackageStartupMessages({
  library(jsonlite)
  library(yaml)
})

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
spec_file <- "analysis/specs/registry.yml"
spec <- read_yaml(file.path(root, spec_file))
SCHEMA_VERSION <- "0.3.0"
GENERATOR <- "analysis/R/05_registry.R"

`%||%` <- function(a, b) if (is.null(a)) b else a

stop_if <- function(condition, ...) if (isTRUE(condition)) stop(sprintf(...), call. = FALSE)

newest_vintage <- function(path) {
  if (!dir.exists(path)) return(NA_character_)
  v <- sort(list.files(path, pattern = "^[0-9]{4}-[0-9]{2}-[0-9]{2}$"))
  if (!length(v)) NA_character_ else v[[length(v)]]
}

est_root <- file.path(root, spec$input$estimates_root)
rob_root <- file.path(root, spec$input$robustness_root)
cards_dir <- file.path(root, spec$input$cards_dir)
index_path <- file.path(root, spec$input$index)

est_vintage <- newest_vintage(est_root)
rob_vintage <- newest_vintage(rob_root)
stop_if(is.na(est_vintage), "no registry/estimates/<vintage>/ — run analysis/R/03_estimate.R first")
stop_if(is.na(rob_vintage), "no registry/robustness/<vintage>/ — run analysis/R/04_robustness.R first")
stop_if(!identical(est_vintage, rob_vintage),
        "the newest estimates vintage is %s and the newest robustness vintage is %s. The registry publishes\nboth against one data vintage; re-run the later stage rather than mixing them.",
        est_vintage, rob_vintage)
vintage <- est_vintage

est_path <- file.path(est_root, vintage, spec$input$estimates_artifact)
rob_path <- file.path(rob_root, vintage, spec$input$robustness_artifact)
stop_if(!file.exists(est_path), "missing %s", est_path)
stop_if(!file.exists(rob_path), "missing %s", rob_path)

estimates <- fromJSON(est_path, simplifyVector = FALSE)
robustness <- fromJSON(rob_path, simplifyVector = FALSE)

# ---- the cards, and the vintage they claim -------------------------------------------------
card_files <- sort(list.files(cards_dir, pattern = "^[a-z0-9_]+__(A|B|C)\\.json$", full.names = TRUE))
stop_if(!length(card_files), "no cards in %s", cards_dir)

cards <- lapply(card_files, function(p) fromJSON(p, simplifyVector = FALSE))
names(cards) <- vapply(cards, function(c) c$dag_id, character(1))

card_vintages <- unique(vapply(cards, function(c) c$vintage_date, character(1)))
stop_if(length(card_vintages) != 1L,
        "the cards claim %d different vintages (%s)", length(card_vintages),
        paste(card_vintages, collapse = ", "))
stop_if(!identical(card_vintages[[1]], vintage),
        "the cards are stamped %s but the newest estimates vintage is %s. Re-run analysis/R/01_build_dags.R\nso the cards carry the vintage whose numbers this registry would publish (S8-01).",
        card_vintages[[1]], vintage)

# ---- the published specifications, and who they are about ----------------------------------
specs <- estimates$specifications
spec_design <- vapply(specs, function(s) as.character(s$design), character(1))
spec_outcome <- vapply(specs, function(s) if (is.null(s$outcome)) NA_character_ else as.character(s$outcome),
                       character(1))
a_index <- which(spec_design == "A")
a_by_outcome <- setNames(a_index, spec_outcome[a_index])

card_outcomes <- unique(vapply(cards, function(c) as.character(c$outcome$id), character(1)))
expected_specs <- as.integer(spec$mapping$design_a$expectation$published_specifications)
expected_cards <- as.integer(spec$mapping$design_a$expectation$cards_that_carry_one)
stop_if(length(a_index) != expected_specs,
        "the estimates artifact publishes %d Design A specifications; %s declares %d. What the app shows\nchanged, so the registry does not write until the declaration does (S8-02).",
        length(a_index), spec_file, expected_specs)

# A published specification whose outcome has no card is a declared gap, not a silent omission: it is
# named in the spec, carried on the index, and checked in both directions.
a_with_card <- a_index[spec_outcome[a_index] %in% card_outcomes]
a_without_card <- a_index[!(spec_outcome[a_index] %in% card_outcomes)]
stop_if(length(a_with_card) != expected_cards,
        "%d Design A specification(s) map to a card; %s declares %d",
        length(a_with_card), spec_file, expected_cards)
declared_without <- vapply(spec$mapping$design_a$without_a_card, function(x) as.character(x$outcome),
                           character(1))
stop_if(!setequal(spec_outcome[a_without_card], declared_without),
        "published without a card: %s; %s declares %s",
        paste(spec_outcome[a_without_card], collapse = ", "), spec_file,
        paste(declared_without, collapse = ", "))

design_block <- function(id) {
  hit <- Filter(function(d) identical(as.character(d$id), id), estimates$designs)
  if (!length(hit)) NULL else hit[[1]]
}
designs <- setNames(lapply(c("A", "B", "C"), design_block), c("A", "B", "C"))

# ---- support counts per design, from the robustness artifact -------------------------------
support_by_design <- robustness$support$by_design
flip_levels <- robustness$support$flips$levels
axis_levels <- robustness$support$by_axis_level

level_for <- function(design, axis, level) {
  hit <- Filter(function(l) identical(l$design, design) && identical(l$axis, axis) &&
                  identical(as.character(l$level), as.character(level)), axis_levels)
  if (!length(hit)) NULL else hit[[1]]
}

support_of <- function(design) {
  s <- support_by_design[[design]]
  list(n = s$n, n_positive = s$n_positive, n_negative = s$n_negative, n_near_zero = s$n_near_zero,
       n_positive_ci = s$n_positive_ci, n_negative_ci = s$n_negative_ci)
}

preferred_spec <- vapply(c("A", "B"), function(d) as.character(robustness$preferred[[d]]), character(1))
near_zero_band <- robustness$support$rule$near_zero_band

# Which outcome the preferred specification is about, read off the grid rather than re-derived from the
# spec_id string: a card is the preferred cell when its own outcome is the one that cell was fitted on.
pref_row <- Filter(function(s) identical(as.character(s$spec_id), preferred_spec[["A"]]),
                   robustness$specifications)
pref_a_outcome <- if (length(pref_row)) as.character(pref_row[[1]]$outcome) else NA_character_

# ---- one estimate block per card -----------------------------------------------------------
estimates_artifact_ref <- sprintf("registry/estimates/%s/%s", vintage, spec$input$estimates_artifact)
robustness_artifact_ref <- sprintf("registry/robustness/%s/%s", vintage, spec$input$robustness_artifact)

copied_spec <- function(i) {
  s <- specs[[i]]
  list(
    artifact = estimates_artifact_ref,
    spec_index = i,
    design = as.character(s$design),
    outcome = if (is.null(s$outcome)) NA else as.character(s$outcome),
    coefficient_name = as.character(s$coefficient_name),
    coefficient = s$coefficient,
    standard_error = s$standard_error,
    ci_low = s$ci_low,
    ci_high = s$ci_high,
    p_value = s$p_value,
    n_obs = as.integer(s$n_obs),
    n_units = as.integer(s$n_units),
    first_month = as.character(s$first_month),
    last_month = as.character(s$last_month),
    estimator = as.character(s$estimator),
    formula = as.character(s$formula),
    covariance = as.character(s$covariance)
  )
}

verdict_of <- function(design) {
  d <- designs[[design]]
  if (is.null(d)) return(list(status = NA, rule = NA, failed_checks = NA))
  failed <- d$verdict$failed_checks
  list(
    status = as.character(d$status),
    rule = as.character(d$verdict$rule),
    failed_checks = if (is.null(failed)) NA else as.character(failed),
    checked_at = list(artifact = estimates_artifact_ref, design = design)
  )
}

reason <- function(code) {
  list(code = code, detail = sub("\\s+", " ", trimws(as.character(spec$not_estimated_reasons[[code]]))))
}

build_block <- function(card) {
  outcome_id <- as.character(card$outcome$id)
  design_id <- as.character(card$design$id)
  diag_status <- as.character(card$diagnostics$status)

  if (identical(diag_status, "not_attempted")) {
    return(list(
      status = "not_estimated", model_card_ref = NA,
      the_number_is_for_this_card = FALSE,
      not_estimated_reason = reason("outcome_series_absent"),
      published_result = if (identical(design_id, "C")) "index.json#published_results.design.C" else NULL,
      note = sprintf(paste0("No estimate for (%s, %s). The outcome series is absent, so no pre-check ran ",
                            "for this pair (Stage 5 status %s). This is a declared gap, not a null result."),
                     outcome_id, design_id, diag_status)
    ))
  }

  if (identical(design_id, "A") && outcome_id %in% names(a_by_outcome)) {
    i <- a_by_outcome[[outcome_id]]
    level <- level_for("A", "outcome", outcome_id)
    stop_if(is.null(level),
            "the robustness grid carries no `outcome = %s` axis level, so the card cannot say what its number\nwas one cell of. Re-run analysis/R/04_robustness.R.", outcome_id)
    rob <- list(
      artifact = robustness_artifact_ref,
      axis = "outcome",
      preferred_specification = preferred_spec[["A"]],
      this_specification_is_the_preferred_one = identical(outcome_id, pref_a_outcome),
      axis_level = level,
      design_support = support_of("A"),
      design_flip_levels = robustness$support$flips$n_levels,
      near_zero_band = near_zero_band,
      rule = as.character(robustness$support$flips$rule)
    )
    return(list(
      status = "estimated",
      model_card_ref = sprintf("%s#specification[%d]", estimates_artifact_ref, i),
      the_number_is_for_this_card = TRUE,
      specification = copied_spec(i),
      verdict = verdict_of("A"),
      robustness = rob,
      note = sprintf(paste0("One of the %d Design A specifications published at Stage 6, and the number the ",
                            "card's outcome was fitted on. It sits in a grid: %d of the design's %d ",
                            "specifications share this outcome and %s of those %d are on the other side of ",
                            "zero. The card's Stage 5 status is %s — an estimate exists for this pair and the ",
                            "design still does not pass its pre-check, which is why both travel together."),
                     expected_specs, level$n, support_of("A")$n,
                     if (isTRUE(level$flips_against_preferred)) "a majority" else "a minority",
                     level$n, diag_status)
    ))
  }

  if (identical(design_id, "B")) {
    return(list(
      status = "not_estimated", model_card_ref = NA,
      the_number_is_for_this_card = FALSE,
      not_estimated_reason = reason("design_result_is_channel_level"),
      published_result = "index.json#published_results.design.B",
      note = sprintf(paste0("No estimate for (%s, B). The design has a published result, but it measures ",
                            "the national FAAC channel (%s) — on this card, FAAC is a mediator node, not the ",
                            "outcome. The number is on the index, once, rather than on the nine B cards that ",
                            "would each imply it is about their outcome."),
                     outcome_id, as.character(spec$mapping$design_b$result_outcome))
    ))
  }

  if (identical(design_id, "C")) {
    return(list(
      status = "not_estimated", model_card_ref = NA,
      the_number_is_for_this_card = FALSE,
      not_estimated_reason = reason("design_not_run"),
      published_result = "index.json#published_results.design.C",
      note = sprintf(paste0("No estimate for (%s, C). The design was not run: %s"),
                     outcome_id,
                     if (is.null(designs[["C"]][["why"]])) "see the index." else as.character(designs[["C"]][["why"]]))
    ))
  }

  list(
    status = "not_estimated", model_card_ref = NA,
    the_number_is_for_this_card = FALSE,
    not_estimated_reason = reason("no_specification_declared"),
    note = sprintf(paste0("No estimate for (%s, %s). Stage 5 ran a pre-check for this pair (status %s), but ",
                          "Stage 6 declared no specification for it: the stage fitted the outcomes its series ",
                          "could carry, and this was not one of them. Nothing here says the question was ",
                          "asked and answered."), outcome_id, design_id, diag_status)
  )
}

# ---- write ----------------------------------------------------------------------------------
n_estimated <- 0L
reason_counts <- list()
for (id in names(cards)) {
  card <- cards[[id]]
  block <- build_block(card)
  if (identical(block$status, "estimated")) n_estimated <- n_estimated + 1L
  else {
    code <- block$not_estimated_reason$code
    reason_counts[[code]] <- (reason_counts[[code]] %||% 0L) + 1L
  }
  card$schema_version <- SCHEMA_VERSION
  card$estimate <- block
  cards[[id]] <- card
  writeLines(jsonlite::toJSON(card, auto_unbox = TRUE, pretty = TRUE, null = "null", na = "null",
                              digits = 10),
             file.path(cards_dir, sprintf("%s.json", id)), useBytes = TRUE)
}

# ---- the index ------------------------------------------------------------------------------
index <- fromJSON(index_path, simplifyVector = FALSE)

design_result <- function(id) {
  d <- designs[[id]]
  stop_if(is.null(d), "the estimates artifact carries no Design %s block", id)
  spec_entries <- specs[spec_design == id]
  list(
    design = id,
    status = as.character(d$status),
    verdict = list(
      rule = as.character(d$verdict$rule),
      status = as.character(d$verdict$status),
      failed_checks = if (is.null(d$verdict$failed_checks)) NA else as.character(d$verdict$failed_checks)
    ),
    result_is_card_level = TRUE,
    specifications = unname(lapply(which(spec_design == id), copied_spec)),
    artifacts = list(
      estimates = estimates_artifact_ref,
      robustness = if (id %in% c("A", "B")) robustness_artifact_ref else NA
    )
  )
}

res <- list(
  A = design_result("A"),
  B = design_result("B"),
  C = list(
    design = "C",
    status = "not_run",
    verdict = list(
      rule = as.character(designs[["C"]][["verdict"]][["rule"]] %||% NA),
      status = as.character(designs[["C"]][["status"]]),
      failed_checks = NA
    ),
    result_is_card_level = FALSE,
    why = as.character(designs[["C"]][["why"]]),
    next_step = as.character(designs[["C"]][["next_step"]]),
    specifications = list(),
    artifacts = list(estimates = estimates_artifact_ref, robustness = NA)
  )
)

# Design B's published result is about the channel, not about a card's outcome. That is the single most
# important sentence in the registry: it is what stops nine cards from borrowing a number.
res$B$result_is_card_level <- FALSE
res$B$result_outcome <- as.character(spec$mapping$design_b$result_outcome)
res$B$cards_that_carry_no_number <- sum(vapply(cards, function(c)
  identical(as.character(c$design$id), "B"), logical(1)))
res$A$result_is_card_level <- TRUE
res$C$result_is_card_level <- FALSE

res$A$specifications_without_a_card <- unname(lapply(a_without_card, function(i) list(
  outcome = spec_outcome[[i]],
  why = as.character(Filter(function(x) identical(as.character(x$outcome), spec_outcome[[i]]),
                            spec$mapping$design_a$without_a_card)[[1]]$why),
  specification = copied_spec(i)
)))
res$A$robustness <- list(
  artifact = robustness_artifact_ref,
  support = support_of("A"),
  sign_flip_levels = robustness$support$flips$n_levels,
  flip_rule = as.character(robustness$support$flips$rule),
  near_zero_band = near_zero_band,
  sensitivity = list(
    computed_on = preferred_spec[["A"]],
    oster_linear_analogue = robustness$sensitivity$design_a$oster,
    leave_one_state_out = robustness$sensitivity$design_a$leave_one_state_out
  )
)
res$B$robustness <- list(
  artifact = robustness_artifact_ref,
  support = support_of("B"),
  sign_flip_levels = robustness$support$flips$n_levels,
  near_zero_band = near_zero_band,
  sensitivity = list(
    computed_on = preferred_spec[["B"]],
    oster = robustness$sensitivity$design_b$oster,
    in_time_placebo = robustness$sensitivity$design_b$in_time_placebo,
    hac_bandwidth = robustness$sensitivity$design_b$hac_bandwidth,
    rosenbaum = robustness$sensitivity$rosenbaum
  )
)

index$schema_version <- SCHEMA_VERSION
index$layer <- "causal DAGs + published results (the app's data contract)"
index$registry <- list(
  generated_at = format(Sys.time(), "%Y-%m-%dT%H:%M:%S%z"),
  generated_by = GENERATOR,
  spec = spec_file,
  rule = as.character(spec$mapping$design_a$rule),
  card_estimate_counts = list(
    estimated = n_estimated,
    not_estimated = length(cards) - n_estimated,
    not_estimated_by_reason = reason_counts
  ),
  card_wins = "The card wins over prose (PHASES.md Stage 8). Every number here is copied from the artifact it names."
)
index$estimates <- list(
  artifact = estimates_artifact_ref,
  vintage = vintage,
  design_status = setNames(lapply(c("A", "B", "C"), function(id)
    as.character(designs[[id]]$status)), c("A", "B", "C"))
)
index$published_results <- res

writeLines(jsonlite::toJSON(index, auto_unbox = TRUE, pretty = TRUE, null = "null", na = "null", digits = 10),
           index_path, useBytes = TRUE)

# ---- report ---------------------------------------------------------------------------------
cat(sprintf("vintage %s | %d cards | %d carry a published number, %d do not\n", vintage, length(cards),
            n_estimated, length(cards) - n_estimated))
cat(sprintf("  estimates artifact : %s (%d specifications)\n", estimates_artifact_ref, length(specs)))
cat(sprintf("  robustness artifact: %s (%d specifications, %d flip levels)\n", robustness_artifact_ref,
            as.integer(robustness$grid$n_total), as.integer(robustness$support$flips$n_levels)))
if (length(reason_counts)) {
  cat("  no number, because:\n")
  for (code in sort(names(reason_counts))) {
    cat(sprintf("    %-34s %d card(s)\n", code, reason_counts[[code]]))
  }
}
cat("  design results on the index:\n")
for (id in c("A", "B", "C")) {
  n_spec <- length(res[[id]]$specifications)
  cat(sprintf("    %s  %-24s %d specification(s)  card-level: %s\n", id,
              as.character(res[[id]]$status), n_spec,
              if (isTRUE(res[[id]]$result_is_card_level)) "yes" else "no"))
}
if (length(a_without_card)) {
  cat(sprintf("    A  published without a card: %s\n",
              paste(spec_outcome[a_without_card], collapse = ", ")))
}
cat(sprintf("\nwritten: %s + %d cards\n", index_path, length(cards)))
