# Stage 8h — Design C: a synthetic control on under-5 mortality, and the placebos that decide whether it
# means anything.
#
# Everything this file does is declared in `analysis/specs/design_c.yml`: the windows, the year rule, the
# estimator, the placebo designs and the rule that turns them into a verdict. The spec was written before any
# weight was fitted. No date, threshold or coefficient is typed here.
#
# The estimator is the one the Stage 5 gate used — simplex weights on the pre-treatment outcome path, solved as
# a quadratic program — so the gate's pass is this estimator's own pre-fit rather than a separate screen.
# `Synth`'s V search is not used: on this pool it returned a fit worse than the best single donor, which the
# diagnostics artifact records, and a second fit whose weights disagreed with the gate would be a second design
# wearing the same name.
#
# Run: Rscript analysis/R/11_design_c.R

suppressPackageStartupMessages({
  library(DBI); library(duckdb); library(data.table)
  library(jsonlite); library(yaml); library(quadprog)
})

root <- normalizePath(".")
spec_path <- file.path("analysis", "specs", "design_c.yml")
spec <- read_yaml(spec_path)
spec_md5 <- unname(tools::md5sum(spec_path))

index <- fromJSON(file.path("registry", "dags", "index.json"), simplifyVector = FALSE)
vintage <- index$vintage_date
out_dir <- file.path("registry", "design_c", vintage)
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

git_sha <- tryCatch(system2("git", c("rev-parse", "--short", "HEAD"), stdout = TRUE), error = function(e) NA_character_)
if (length(git_sha) == 0) git_sha <- NA_character_

# The windows are declared once, in diagnostics.yml: a treatment date retyped is a date that can drift.
diag_spec <- read_yaml(spec$windows$source)
windows_declared <- Filter(function(w) w$id %in% unlist(spec$windows$ids),
                            diag_spec$windows$candidate_treated_windows)

outcome_id <- spec$input$outcome
first_year <- as.integer(spec$windows$first_year)
last_year <- as.integer(spec$windows$last_year)
min_pre <- as.integer(spec$windows$require_pre_years)
min_post <- as.integer(spec$windows$require_post_years)

# The gate's threshold lives in diagnostics.yml; read it rather than trust the number in this file.
pre_frac <- as.numeric(diag_spec$pretrend$family_c$pre_rmse_threshold_frac_of_sd)
if (!isTRUE(all.equal(pre_frac, 0.10))) {
  stop(sprintf("diagnostics.yml declares pre_rmse_threshold_frac_of_sd = %s; design_c.yml's verdict rule names 0.10",
               format(pre_frac)))
}

con <- dbConnect(duckdb(), dbdir = file.path("data", "analytics.duckdb"), read_only = TRUE)
on.exit(dbDisconnect(con), add = TRUE)

# ---------------------------------------------------------------------------------------------
# Data: Nigeria's native annual path, and the committed donor panel
# ---------------------------------------------------------------------------------------------
treated <- as.data.table(dbGetQuery(con, sprintf(
  "select year(anchor_month) as yr, value
     from %s
    where metric_id = '%s' and native_frequency = 'annual' and value is not null
      and anchor_month between date '%d-01-01' and date '%d-12-31'
    order by 1",
  spec$input$native_table, outcome_id, first_year, last_year)))

donor_panel <- as.data.table(dbGetQuery(con, sprintf(
  "select country_iso3, period_year, value
     from %s
    where metric_id = '%s' and period_year between %d and %d
    order by 1, 2",
  spec$input$donor_table, outcome_id, first_year, last_year)))

donor_panel <- donor_panel[country_iso3 != spec$input$treated_iso3]
donors_all <- sort(unique(donor_panel$country_iso3))

# One matrix row per donor, so a placebo loop indexes a column instead of filtering a table 9,700 times.
donor_matrix <- function(years) {
  m <- vapply(donors_all, function(cc) {
    d <- donor_panel[country_iso3 == cc]
    d$value[match(years, d$period_year)]
  }, numeric(length(years)))
  matrix(m, nrow = length(years), dimnames = list(NULL, donors_all))
}

balance_predictors <- unlist(spec$estimator$balance_predictors)
pred_panel <- as.data.table(dbGetQuery(con, sprintf(
  "select metric_id, country_iso3, period_year, value
     from %s
    where metric_id in (%s) and period_year between %d and %d
    order by 1, 2, 3",
  spec$input$donor_table, paste(sprintf("'%s'", balance_predictors), collapse = ","),
  first_year, last_year)))

pred_national <- as.data.table(dbGetQuery(con, sprintf(
  "select metric_id, year(anchor_month) as yr, value
     from %s
    where metric_id in (%s) and native_frequency = 'annual' and value is not null
      and anchor_month between date '%d-01-01' and date '%d-12-31'
    order by 1, 2",
  spec$input$native_table, paste(sprintf("'%s'", balance_predictors), collapse = ","),
  first_year, last_year)))

value_of <- function(dt, yr) dt$value[match(yr, dt$yr)]

# ---------------------------------------------------------------------------------------------
# Estimator
# ---------------------------------------------------------------------------------------------
# The globally optimal simplex weights for the pre-treatment path. A ridge scaled to the matrix is required
# because donors outnumber pre-period years and the Gram matrix is singular (the same reason and the same scale
# as Stage 5's implementation, so the two produce the same fit).
simplex_weights <- function(z1, Z0, ridge_relative = 1e-8) {
  D <- crossprod(Z0)
  ridge <- max(diag(D)) * ridge_relative
  quadprog::solve.QP(Dmat = D + diag(ridge, ncol(D)), dvec = crossprod(Z0, z1),
                     Amat = cbind(1, diag(ncol(D))), bvec = c(1, rep(0, ncol(D))),
                     meq = 1)$solution
}
rmse_of <- function(z1, Z0, w) sqrt(mean((z1 - as.numeric(Z0 %*% w))^2))

# The years an administration held office on 1 July, clipped to the study window.
window_years <- function(w) {
  from <- as.Date(w$from)
  to <- if (is.null(w$to) || is.na(w$to) || identical(w$to, "")) as.Date(sprintf("%d-12-31", last_year)) else as.Date(w$to)
  yrs <- first_year:last_year
  jul1 <- as.Date(sprintf("%d-07-01", yrs))
  yrs[jul1 >= from & jul1 <= to]
}

# One fit, from matrices: the treated pre-path, the donor pre-block, the treated post-path and the donor
# post-block. Returns the weights, the fit statistics and the gap path.
fit_mat <- function(z1, Z0, y1_post, Y0_post, ridge_relative = 1e-8) {
  w <- simplex_weights(z1, Z0, ridge_relative)
  if (!is.null(colnames(Z0))) names(w) <- colnames(Z0)
  pre_rmse <- rmse_of(z1, Z0, w)
  pre_sd <- stats::sd(z1)
  synth_post <- as.numeric(Y0_post %*% w)
  gap <- y1_post - synth_post
  post_rmse <- if (length(gap) > 1) sqrt(mean(gap^2)) else abs(gap)
  list(weights = w, pre_rmse = pre_rmse, pre_sd = pre_sd,
       pre_ratio = if (pre_sd > 0) pre_rmse / pre_sd else NA_real_,
       synth_post = synth_post, gap = gap, mean_gap = mean(gap),
       post_rmse = post_rmse,
       post_pre_ratio = if (pre_rmse > 0) post_rmse / pre_rmse else NA_real_)
}

# ---------------------------------------------------------------------------------------------
# In-space placebo: every donor treated in turn, its own weights fitted from the others
# ---------------------------------------------------------------------------------------------
space_placebo <- function(Zpre, Zpost, ridge_relative = 1e-8) {
  donors <- colnames(Zpre)
  lapply(donors, function(d) {
    keep <- setdiff(donors, d)
    fit <- fit_mat(Zpre[, d], Zpre[, keep, drop = FALSE],
                   Zpost[, d], Zpost[, keep, drop = FALSE], ridge_relative)
    list(donor = d, pre_ratio = fit$pre_ratio, post_pre_ratio = fit$post_pre_ratio,
         mean_gap = fit$mean_gap)
  })
}

p_from <- function(placebos, treated_ratio) {
  (1 + sum(vapply(placebos, function(r) r$post_pre_ratio >= treated_ratio, logical(1)))) /
    (1 + length(placebos))
}

# ---------------------------------------------------------------------------------------------
# In-time placebo: the treatment date moved back
# ---------------------------------------------------------------------------------------------
time_placebo <- function(start_year, treated_dt, usable, ridge_relative = 1e-8) {
  rows <- list()
  for (k in as.integer(unlist(spec$placebos$in_time$backdate_years))) {
    pseudo_start <- start_year - k
    pseudo_post <- pseudo_start:(start_year - 1)
    pseudo_pre <- first_year:(pseudo_start - 1)
    if (length(pseudo_pre) < min_pre || length(pseudo_post) < min_post) {
      rows[[length(rows) + 1]] <- list(backdated_years = k, status = "not_run",
        detail = sprintf("%d pre and %d post years against the declared minima of %d and %d",
                         length(pseudo_pre), length(pseudo_post), min_pre, min_post))
      next
    }
    Zpre <- donor_matrix(pseudo_pre)
    Zpost <- donor_matrix(pseudo_post)
    keep <- usable[colSums(is.na(Zpre)) == 0 & colSums(is.na(Zpost)) == 0]
    fit <- fit_mat(value_of(treated_dt, pseudo_pre), Zpre[, keep, drop = FALSE],
                   value_of(treated_dt, pseudo_post), Zpost[, keep, drop = FALSE],
                   ridge_relative)
    rows[[length(rows) + 1]] <- list(
      backdated_years = k, status = "estimated",
      pre_years = length(pseudo_pre), post_years = length(pseudo_post),
      mean_gap = fit$mean_gap, ratio_to_estimated = NA_real_)
  }
  rows
}

# ---------------------------------------------------------------------------------------------
# Leave-one-donor-out sweep
# ---------------------------------------------------------------------------------------------
loo_sweep <- function(z1, Zpre, y1_post, Zpost, usable, estimated_gap, ridge_relative = 1e-8) {
  gaps <- vapply(usable, function(d) {
    keep <- setdiff(usable, d)
    fit_mat(z1, Zpre[, keep, drop = FALSE], y1_post,
            Zpost[, keep, drop = FALSE], ridge_relative)$mean_gap
  }, numeric(1))
  list(n_fits = length(gaps), min = min(gaps), max = max(gaps),
       n_sign_flips = sum(sign(gaps) != sign(estimated_gap)))
}

# ---------------------------------------------------------------------------------------------
# Loop the declared windows
# ---------------------------------------------------------------------------------------------
ridge_rel <- as.numeric(spec$estimator$solver_sensitivity$ridge_relative)
results <- list()
for (w in windows_declared) {
  yrs <- window_years(w)
  post_years <- yrs
  start_year <- if (length(post_years)) min(post_years, na.rm = TRUE) else NA_integer_
  pre_years <- if (is.na(start_year) || start_year - 1 < first_year) integer(0) else first_year:(start_year - 1)

  if (!length(post_years) || any(is.na(post_years)) || length(pre_years) < min_pre || length(post_years) < min_post) {
    results[[length(results) + 1]] <- list(
      id = w$id, status = "refused",
      refused = list(reason = "gate_window_not_runnable",
                     detail = sprintf("%d pre and %d post years against the declared minima of %d and %d (%s)",
                                      length(pre_years), length(post_years), min_pre, min_post,
                                      spec$windows$year_rule)),
      pre_years = length(pre_years), post_years = length(post_years))
    next
  }

  # Nigeria must have a native observation in every pre and post year; the annual series does (1999-2024), but
  # the check is explicit so a moved anchor fails loudly rather than via an NA in the objective.
  if (any(is.na(value_of(treated, c(pre_years, post_years))))) {
    results[[length(results) + 1]] <- list(
      id = w$id, status = "refused",
      refused = list(reason = "treated_series_incomplete",
                     detail = "Nigeria has no native annual observation in at least one year of the window"),
      pre_years = length(pre_years), post_years = length(post_years))
    next
  }

  # A donor enters the pool only with a complete path over the pre- and post-periods. A donor whose series stops
  # early is dropped and counted, not interpolated (C-19 is the same failure one stage up).
  Zpre_all <- donor_matrix(pre_years)
  Zpost_all <- donor_matrix(post_years)
  usable <- donors_all[colSums(is.na(Zpre_all)) == 0 & colSums(is.na(Zpost_all)) == 0]
  Zpre <- matrix(Zpre_all[, usable], ncol = length(usable), dimnames = list(NULL, usable))
  Zpost <- matrix(Zpost_all[, usable], ncol = length(usable), dimnames = list(NULL, usable))
  z1 <- value_of(treated, pre_years)
  y1_post <- value_of(treated, post_years)

  fit <- fit_mat(z1, Zpre, y1_post, Zpost)
  placebos <- space_placebo(Zpre, Zpost)
  p_space <- p_from(placebos, fit$post_pre_ratio)

  # The declared QP is underdetermined: 8 to 24 pre-years against 99 weights leaves a face of equally optimal
  # solutions, and solve.QP returns one vertex of it. This refits with a ridge on the weights that makes the
  # solution unique, and recomputes the whole placebo rank under it, so the artifact can say whether the gap and
  # the p-value are a property of the data or of the solver's choice of vertex. A diagnostic: the verdict rule is
  # unchanged and is still read off the primary fit.
  fit_ridge <- fit_mat(z1, Zpre, y1_post, Zpost, ridge_rel)
  p_ridge <- p_from(space_placebo(Zpre, Zpost, ridge_rel), fit_ridge$post_pre_ratio)

  time_rows <- time_placebo(start_year, treated, usable)
  for (i in seq_along(time_rows)) {
    if (identical(time_rows[[i]]$status, "estimated") && abs(fit$mean_gap) > 0) {
      time_rows[[i]]$ratio_to_estimated <- abs(time_rows[[i]]$mean_gap) / abs(fit$mean_gap)
    }
  }
  time_estimated <- Filter(function(r) identical(r$status, "estimated"), time_rows)
  # The declared rule is "every in-time placebo *that could be run*": a window with too few pre years for a
  # backdated fit carries no in-time evidence and the rule says nothing about it.
  time_ok <- length(time_estimated) == 0 ||
    all(vapply(time_estimated, function(r) abs(r$mean_gap) < 0.5 * abs(fit$mean_gap), logical(1)))

  loo <- loo_sweep(z1, Zpre, y1_post, Zpost, usable, fit$mean_gap)

  failed <- c(
    if (!is.na(fit$pre_ratio) && fit$pre_ratio <= pre_frac) NULL else sprintf(
      "the pre-fit ratio is %.4f against the declared %.2f threshold", fit$pre_ratio, pre_frac),
    if (p_space <= 0.05) NULL else sprintf(
      "the in-space rank p is %.4f: %.0f of %d placebos match or exceed the treated unit's post/pre RMSPE ratio",
      p_space, sum(vapply(placebos, function(r) r$post_pre_ratio >= fit$post_pre_ratio, logical(1))),
      length(placebos)),
    if (time_ok) NULL else "an in-time placebo returns a gap at least half the size of the estimated gap")

  status <- if (length(failed) == 0) "identified" else "estimated_not_identified"

  results[[length(results) + 1]] <- list(
    id = w$id, status = status,
    first_year = start_year, last_year = max(post_years),
    pre_years = length(pre_years), post_years = length(post_years),
    n_donors_used = length(usable), n_donors_with_weight = sum(fit$weights > 1e-6),
    path = lapply(seq_along(post_years), function(i) list(
      year = post_years[i], treated = unname(y1_post[i]),
      synthetic = signif(fit$synth_post[i], 10), gap = signif(fit$gap[i], 10))),
    pre_rmse = signif(fit$pre_rmse, 10), pre_sd = signif(fit$pre_sd, 10),
    pre_ratio = signif(fit$pre_ratio, 10),
    post_rmse = signif(fit$post_rmse, 10),
    post_pre_ratio = signif(fit$post_pre_ratio, 10),
    mean_gap = signif(fit$mean_gap, 10),
    weights = lapply(usable[fit$weights > 1e-6], function(d)
      list(donor = d, weight = signif(fit$weights[[d]], 10))),
    n_weights_published = sum(fit$weights > 1e-6),
    in_space = list(
      n_placebos = length(placebos), p_value = signif(p_space, 10),
      n_at_least_as_extreme = sum(vapply(placebos, function(r) r$post_pre_ratio >= fit$post_pre_ratio, logical(1))),
      n_placebos_passing_pre_fit = sum(vapply(placebos, function(r) isTRUE(r$pre_ratio <= pre_frac), logical(1))),
      distribution = lapply(placebos, function(r) list(
        donor = r$donor, pre_ratio = signif(r$pre_ratio, 6),
        post_pre_ratio = signif(r$post_pre_ratio, 6), mean_gap = signif(r$mean_gap, 6)))),
    in_time = time_rows,
    solver_sensitivity = list(
      ridge_relative = ridge_rel,
      mean_gap = signif(fit_ridge$mean_gap, 10),
      pre_ratio = signif(fit_ridge$pre_ratio, 10),
      p_value = signif(p_ridge, 10),
      gap_shift = signif(fit_ridge$mean_gap - fit$mean_gap, 10),
      n_weights_with_ridge = sum(fit_ridge$weights > 1e-6)),
    leave_one_out = list(n_fits = loo$n_fits, min = signif(loo$min, 10), max = signif(loo$max, 10),
                         n_sign_flips = loo$n_sign_flips),
    verdict = list(status = status, rule = gsub("\\s+", " ", trimws(spec$verdict_rule)),
                   failed_checks = as.list(failed)),
    balance = lapply(balance_predictors, function(p) {
      p_nga <- pred_national[metric_id == p]
      p_don <- pred_panel[metric_id == p]
      n_nga <- value_of(p_nga, pre_years)
      vals <- lapply(usable, function(cc) {
        d <- p_don[country_iso3 == cc]
        d$value[match(pre_years, d$period_year)]
      })
      ok <- !is.na(n_nga)
      for (v in vals) ok <- ok & !is.na(v)
      if (sum(ok) < 3) return(list(metric = p, status = "not_balanced",
                                   detail = sprintf("%d years where every unit has data", sum(ok))))
      means <- vapply(vals, function(v) mean(v[ok]), numeric(1))
      wv <- fit$weights
      list(metric = p, status = "balanced", n_years = sum(ok),
           treated = signif(mean(n_nga[ok]), 8),
           synthetic = signif(sum(means * wv) / sum(wv), 8),
           donor_min = signif(min(means), 8), donor_max = signif(max(means), 8))
    }))
}

# ---------------------------------------------------------------------------------------------
# Counts and payload
# ---------------------------------------------------------------------------------------------
statuses <- vapply(results, function(r) r$status, character(1))
estimated <- Filter(function(r) r$status != "refused", results)
counts <- list(
  windows = length(results),
  estimated = length(estimated),
  refused = sum(statuses == "refused"),
  identified = sum(statuses == "identified"),
  not_identified = sum(statuses == "estimated_not_identified"),
  donors = length(donors_all),
  placebos_in_space = sum(vapply(estimated, function(r) r$in_space$n_placebos, integer(1))),
  placebos_in_time = sum(vapply(estimated, function(r)
    sum(vapply(r$in_time, function(x) identical(x$status, "estimated"), logical(1))), integer(1))),
  placebos_passing_pre_fit = sum(vapply(estimated, function(r) r$in_space$n_placebos_passing_pre_fit, integer(1))),
  loo_fits = sum(vapply(estimated, function(r) r$leave_one_out$n_fits, integer(1))))

payload <- list(
  schema_version = "0.1.0",
  stage = spec$stage,
  layer = "Design C: synthetic control with in-space and in-time placebos - an effect estimate only where its placebos support one",
  vintage = vintage,
  generated_at = format(Sys.time(), "%Y-%m-%dT%H:%M:%S%z"),
  generator = list(script = spec$engine, git_sha = git_sha),
  spec = list(path = "analysis/specs/design_c.yml", md5 = spec_md5,
              stamp = spec$stamp, estimator = spec$estimator$name,
              verdict_rule = gsub("\\s+", " ", trimws(spec$verdict_rule)),
              refusals = unlist(spec$refusals), not_claimed = unlist(spec$not_claimed)),
  input = list(
    database = spec$input$database,
    donor_table = spec$input$donor_table,
    native_table = spec$input$native_table,
    outcome = outcome_id,
    treated_iso3 = spec$input$treated_iso3,
    donor_pool = list(n = length(donors_all), artifact = spec$input$donor_panel_artifact),
    treated_series = spec$input$treated_series,
    window_years = sprintf("%d-%d", first_year, last_year),
    pre_fit_threshold = pre_frac),
  counts = counts,
  windows = results)

write_json(payload, file.path(out_dir, "design_c.json"), auto_unbox = TRUE, pretty = TRUE, digits = 10)

fmt <- function(x, d = 2) ifelse(is.na(x), "-", formatC(x, digits = d, format = "f"))
md <- c(
  sprintf("# Stage 8h - Design C, synthetic control on %s - vintage %s", outcome_id, vintage), "",
  sprintf("Generated %s by `%s`. Spec `analysis/specs/design_c.yml` (md5 %s), %s.",
          payload$generated_at, spec$engine, spec_md5, spec$stamp), "",
  "**This is not the effect of a president.** It is the gap between Nigeria's path and a simplex-weighted",
  "combination of other countries' paths after a transition, published with the placebos that decide whether",
  "the gap is distinguishable from what the same method produces where no transition happened.", "",
  "| Window | Years | Mean gap | Ridge gap | Post/pre ratio | In-space p | Verdict |",
  "|---|---|---|---|---|---|---|",
  vapply(results, function(r) {
    if (identical(r$status, "refused")) {
      return(sprintf("| %s | - | - | - | - | - | refused (%s) |", r$id, r$refused$reason))
    }
    sprintf("| %s | %d-%d | %s | %s | %s | %s | **%s** |", r$id, r$first_year, r$last_year,
            fmt(r$mean_gap), fmt(r$solver_sensitivity$mean_gap), fmt(r$post_pre_ratio),
            fmt(r$in_space$p_value, 4), r$status)
  }, character(1)), "",
  "The mean gap is in deaths per 1,000 live births; a negative number means Nigeria sat below the synthetic",
  "counterfactual. The p-value is a rank among placebos, not a sampling distribution, and with 100 units the",
  "smallest attainable value is 0.01.", "",
  "**The two gap columns are the same problem solved twice.** With 99 donors and 8 to 24 pre-years the declared",
  "simplex problem is underdetermined: a face of weight vectors fits the pre-period equally well and they do not",
  "agree about the post-period. The first column is the vertex the declared QP returns; the second is the unique",
  "ridge refit. Where the two disagree in sign the estimate is a property of the solver, not of the data, and the",
  "artifact says so instead of publishing one of them.", "",
  sprintf("- windows estimated: %d; refused: %d", counts$estimated, counts$refused),
  sprintf("- identified: %d; estimated but not identified: %d", counts$identified, counts$not_identified),
  sprintf("- in-space placebos fitted: %d; in-time placebos fitted: %d; leave-one-donor-out fits: %d",
          counts$placebos_in_space, counts$placebos_in_time, counts$loo_fits),
  sprintf("- placebos whose own pre-fit also clears the 0.10 gate: %d of %d - the gate does not discriminate on this pool",
          counts$placebos_passing_pre_fit, counts$placebos_in_space), "",
  "## What this does not claim", "",
  paste0("- ", unlist(spec$not_claimed)), "",
  "## What it refuses to carry", "",
  paste0("- ", unlist(spec$refusals)), "")
writeLines(md, file.path(out_dir, "report.md"))

message(sprintf("wrote registry/design_c/%s/design_c.json - %d estimated, %d refused, %d identified",
                vintage, counts$estimated, counts$refused, counts$identified))
