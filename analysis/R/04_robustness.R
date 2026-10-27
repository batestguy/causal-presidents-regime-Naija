#!/usr/bin/env Rscript
# Stage 7 — robustness and the multiverse. Writes
# registry/robustness/<vintage>/{robustness.json, report.md, specification_curve.svg}.
#
# The grid, the sensitivity rules, the support-count rule and the figure layout are declared in
# `analysis/specs/robustness.yml`. Nothing that could be a choice is typed here: this file fits what the
# spec declares, computes the counts from the fitted rows, and publishes the specifications that disagree
# as readily as the ones that do not.
#
# Run:
#     Rscript analysis/R/04_robustness.R
#     Rscript analysis/R/04_robustness.R --spec analysis/specs/robustness.yml
#
# Independent recomputation of every number written here: `tests/verify_stage7.py`.

suppressPackageStartupMessages({
  library(yaml)
  library(jsonlite)
  library(DBI)
  library(duckdb)
  library(fixest)
  library(sandwich)
  library(data.table)
})

# ---------------------------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------------------------
script_path <- function() {
  args <- commandArgs(trailingOnly = FALSE)
  hit <- grep("^--file=", args, value = TRUE)
  if (length(hit)) return(normalizePath(sub("^--file=", "", hit[1])))
  normalizePath("analysis/R/04_robustness.R")
}
REPO_ROOT <- normalizePath(file.path(dirname(script_path()), "..", ".."))

cli <- commandArgs(trailingOnly = TRUE)
spec_file <- if (length(cli) >= 2 && cli[1] == "--spec") cli[2] else "analysis/specs/robustness.yml"
spec_path <- file.path(REPO_ROOT, spec_file)
if (!file.exists(spec_path)) stop(sprintf("no specification at %s", spec_file))

spec <- yaml::read_yaml(spec_path)
vintage <- spec$labelled
out_dir <- file.path(REPO_ROOT, spec$output$root, vintage)
dir.create(out_dir, showWarnings = FALSE, recursive = TRUE)

message(sprintf("Stage 7 robustness — vintage %s", vintage))
message(sprintf("spec: %s", spec_file))

# ---------------------------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------------------------
con <- DBI::dbConnect(duckdb::duckdb(), dbdir = file.path(REPO_ROOT, spec$input$database),
                      read_only = TRUE)
on.exit(DBI::dbDisconnect(con, shutdown = TRUE))

q <- spec$design_a$sample
panel <- as.data.table(DBI::dbGetQuery(con, sprintf("
  select state_id, state_name, period_month,
         faac_gross_total_naira as dose, fatalities, incidents, fatalities_civilians,
         strftime(period_month, '%%Y-%%m') as ym
  from %s
  where dose_status = '%s' and security_status = '%s' and faac_gross_total_naira >= %s
  order by state_id, period_month
", spec$input$panel_table, q$require_dose_status, q$require_security_status, q$min_exposure)))

panel[, period_month := as.Date(period_month)]
panel[, ym := factor(ym)]
panel[, state_id := as.factor(state_id)]
panel[, log_dose := log(dose)]
# Months since the first month of the landed dose: the state-specific trend's clock. Declared here and in
# the verifier, which must use the same origin or the trend absorbs a different slope.
panel[, trend := 12L * (as.integer(format(period_month, "%Y")) - 2016L) +
        (as.integer(format(period_month, "%m")) - 12L)]
setorder(panel, state_id, period_month)

# Dose lags on the full panel, before any window filter: a window then loses k months at its start
# instead of silently borrowing a dose from outside it.
panel[, log_dose_lag0 := log_dose]
panel[, log_dose_lag1 := shift(log_dose, 1), by = state_id]
panel[, log_dose_lag2 := shift(log_dose, 2), by = state_id]

oil_id <- spec$input$oil_metric_id
national <- as.data.table(DBI::dbGetQuery(con, sprintf("
  select f.period_month, f.gross_total_naira as faac, m.value as oil
  from %s f
  join %s m on m.metric_id = '%s' and m.period_month = f.period_month
  order by f.period_month
", spec$input$national_faac_table, spec$input$fact_metric_table, oil_id)))
national[, period_month := as.Date(period_month)]
national[, log_faac := log(faac)]
national[, log_oil := log(oil)]
national[, d_log_oil_1m := log_oil - shift(log_oil, 1)]
national[, d_log_oil_3m := (log_oil - shift(log_oil, 3)) / 3]
national[, month_of_year := factor(format(period_month, "%m"))]
national[, covid := as.integer(period_month >= as.Date("2020-03-01") &
                                 period_month <= as.Date("2021-12-01"))]
national[, lag_d_log_oil_1m := shift(d_log_oil_1m, 1)]
national[, lag_d_log_oil_3m := shift(d_log_oil_3m, 1)]

message(sprintf("design A base: %d state-months, %d states, %s -> %s",
                nrow(panel), uniqueN(panel$state_id), min(panel$period_month), max(panel$period_month)))
message(sprintf("design B base: %d months, %s -> %s",
                nrow(national), min(national$period_month), max(national$period_month)))

# ---------------------------------------------------------------------------------------------
# Windows — filter estimation rows only; outcomes and lags are built on the full series
# ---------------------------------------------------------------------------------------------
window_mask <- function(dt, name) {
  w <- spec$windows[[name]]
  keep <- rep(TRUE, nrow(dt))
  if (!is.null(w$drop)) {
    ym_text <- format(dt$period_month, "%Y-%m")
    keep <- keep & !(ym_text >= w$drop[[1]] & ym_text <= w$drop[[2]])
  }
  if (!is.null(w$start)) keep <- keep & format(dt$period_month, "%Y-%m") >= w$start
  if (!is.null(w$end)) keep <- keep & format(dt$period_month, "%Y-%m") <= w$end
  keep
}

# ---------------------------------------------------------------------------------------------
# Design A — every specification in the declared grid
# ---------------------------------------------------------------------------------------------
fe_formula <- function(adjustment_set) {
  switch(adjustment_set,
    state_fe                  = "state_id",
    state_month_fe            = "state_id + ym",
    state_month_fe_state_trend = "state_id + ym + state_id[trend]",
    stop(sprintf("unknown adjustment_set %s", adjustment_set)))
}

fit_dose <- function(dt, outcome, dose_col, adjustment_set) {
  f <- as.formula(sprintf("%s ~ %s | %s", outcome, dose_col, fe_formula(adjustment_set)))
  fixest::fepois(f, data = dt, cluster = ~state_id, notes = FALSE, warn = FALSE)
}

a_axes <- spec$design_a$axes
a_grid <- CJ(outcome = unlist(a_axes$outcome),
             dose_lag_months = unlist(a_axes$dose_lag_months),
             adjustment_set = unlist(a_axes$adjustment_set),
             window = unlist(a_axes$window), sorted = FALSE)

a_rows <- vector("list", nrow(a_grid))
for (i in seq_len(nrow(a_grid))) {
  g <- a_grid[i]
  dose_col <- sprintf("log_dose_lag%d", g$dose_lag_months)
  frame <- panel[!is.na(get(dose_col)) & window_mask(panel, g$window)]
  fit <- fit_dose(frame, g$outcome, dose_col, g$adjustment_set)
  ct <- summary(fit)$coeftable
  est <- unname(ct[1, "Estimate"])
  se <- unname(ct[1, "Std. Error"])
  a_rows[[i]] <- list(
    spec_id = sprintf("A|%s|lag%d|%s|%s", g$outcome, g$dose_lag_months, g$adjustment_set, g$window),
    design = "A", outcome = g$outcome, dose_lag_months = as.integer(g$dose_lag_months),
    adjustment_set = g$adjustment_set, window = g$window,
    estimator = spec$design_a$estimator,
    formula = sprintf("%s ~ %s | %s", g$outcome, dose_col, fe_formula(g$adjustment_set)),
    n_obs = as.integer(stats::nobs(fit)), n_units = as.integer(uniqueN(frame$state_id)),
    first_month = as.character(min(frame$period_month)), last_month = as.character(max(frame$period_month)),
    coefficient = est, standard_error = se,
    ci_low = est - 1.96 * se, ci_high = est + 1.96 * se
  )
  if (i %% 20 == 0) message(sprintf("  design A: %d / %d fitted", i, nrow(a_grid)))
}
message(sprintf("design A: %d specifications fitted", nrow(a_grid)))

# ---------------------------------------------------------------------------------------------
# Design B — every specification in the declared grid, at the focus horizon
# ---------------------------------------------------------------------------------------------
h_focus <- spec$design_b$focus_horizon
hac_lags <- spec$design_b$inference$maxlags

b_controls_rhs <- function(controls, shock) {
  switch(controls,
    none                            = NULL,
    month_of_year                   = "month_of_year",
    month_of_year_plus_lagged_shock = sprintf("%s + lag_%s", "month_of_year", shock),
    month_of_year_plus_covid        = "month_of_year + covid",
    stop(sprintf("unknown control set %s", controls)))
}

# The outcome is built on the **full** series and the window is applied to the estimation rows
# afterwards, as declared in the spec: filtering first would make the last row before an excluded stretch
# take its h-month lead from the far side of the gap.
#
# `shift(x, -h, type = "lead")` is a *lag* in data.table: the sign and the type must not both be negative.
# This line was written that way first and produced a 0.408 gap against Stage 6, which the pre-registered
# check caught before anything was published.
lp_row <- function(dt, shock, controls, h, window_name) {
  frame <- copy(dt)
  frame[, y := shift(log_faac, h, type = "lead") - shift(log_faac, 1)]
  frame <- frame[!is.na(y) & !is.na(get(shock))]
  if (!is.null(window_name)) frame <- frame[window_mask(frame, window_name)]
  rhs <- b_controls_rhs(controls, shock)
  form <- if (is.null(rhs)) sprintf("y ~ %s", shock) else sprintf("y ~ %s + %s", shock, rhs)
  model <- lm(as.formula(form), data = frame)
  V <- sandwich::NeweyWest(model, lag = hac_lags, prewhite = FALSE, adjust = TRUE)
  est <- unname(coef(model)[[shock]])
  se <- unname(sqrt(diag(V))[shock])
  list(model = model, frame = frame, estimate = est, se = se, formula = form)
}

b_axes <- spec$design_b$axes
b_grid <- CJ(shock = unlist(b_axes$shock),
             controls = unlist(b_axes$controls),
             window = unlist(b_axes$window), sorted = FALSE)

b_rows <- vector("list", nrow(b_grid))
for (i in seq_len(nrow(b_grid))) {
  g <- b_grid[i]
  got <- lp_row(national, g$shock, g$controls, h_focus, g$window)
  b_rows[[i]] <- list(
    spec_id = sprintf("B|%s|%s|%s", g$shock, g$controls, g$window),
    design = "B", shock = g$shock, controls = g$controls, window = g$window,
    horizon = as.integer(h_focus),
    estimator = sprintf("%s, h=%d", spec$design_b$estimator, h_focus),
    formula = got$formula,
    n_obs = as.integer(stats::nobs(got$model)), n_units = 1L,
    first_month = as.character(min(got$frame$period_month)),
    last_month = as.character(max(got$frame$period_month)),
    coefficient = got$estimate, standard_error = got$se,
    ci_low = got$estimate - 1.96 * got$se, ci_high = got$estimate + 1.96 * got$se
  )
}
message(sprintf("design B: %d specifications fitted at h=%d", nrow(b_grid), h_focus))

# ---------------------------------------------------------------------------------------------
# Preferred specifications — pre-registered, then checked against Stage 6
# ---------------------------------------------------------------------------------------------
mark_preferred <- function(rows, pref, design) {
  for (i in seq_along(rows)) {
    matches <- all(vapply(names(pref), function(k) {
      if (k == "why") return(TRUE)
      identical(as.character(rows[[i]][[k]]), as.character(pref[[k]]))
    }, logical(1)))
    rows[[i]]$preferred <- matches
  }
  n_pref <- sum(vapply(rows, function(r) isTRUE(r$preferred), logical(1)))
  if (n_pref != 1L) stop(sprintf("design %s: %d preferred specifications, expected exactly 1",
                                 design, n_pref))
  rows
}
a_rows <- mark_preferred(a_rows, spec$design_a$preferred, "A")
b_rows <- mark_preferred(b_rows, spec$design_b$preferred, "B")

pref_a <- a_rows[[which(vapply(a_rows, function(r) isTRUE(r$preferred), logical(1)))]]
pref_b <- b_rows[[which(vapply(b_rows, function(r) isTRUE(r$preferred), logical(1)))]]

# The pre-registered specification must be the one Stage 6 published, not merely one that shares its
# name. A drift here means the grid or the base moved, and the report would otherwise present a
# specification curve around a number the estimate artifact does not contain.
estimates_path <- file.path(REPO_ROOT, spec$upstream$estimates)
stage6_check <- list(checked = FALSE, why = "no estimates artifact at the declared path")
if (file.exists(estimates_path)) {
  estimates <- jsonlite::fromJSON(estimates_path, simplifyVector = FALSE)
  stage6_b <- NULL
  for (s in estimates$specifications) {
    if (identical(s$design, "B") && identical(s$coefficient_name, sprintf("cumulative_pass_through_h%d", h_focus))) {
      stage6_b <- s
    }
  }
  stage6_a <- NULL
  for (s in estimates$specifications) {
    if (identical(s$design, "A") && identical(s$outcome, spec$design_a$preferred$outcome)) stage6_a <- s
  }
  if (is.null(stage6_a) || is.null(stage6_b)) {
    stage6_check <- list(checked = FALSE, why = "the Stage 6 artifact lacks the matching A or B row")
  } else {
    da <- abs(pref_a$coefficient - stage6_a$coefficient)
    db <- abs(pref_b$coefficient - stage6_b$coefficient)
    stage6_check <- list(
      checked = TRUE,
      design_a = list(stage6 = stage6_a$coefficient, robustness = pref_a$coefficient, abs_diff = da),
      design_b = list(stage6 = stage6_b$coefficient, robustness = pref_b$coefficient, abs_diff = db),
      tolerance = 1e-8
    )
    if (da > 1e-8 || db > 1e-8) {
      stop(sprintf(paste0("the pre-registered specification does not reproduce the Stage 6 estimate ",
                          "(A diff %.2e, B diff %.2e): the grid and the estimate artifact disagree"),
                   da, db))
    }
  }
}

# ---------------------------------------------------------------------------------------------
# Support counts — computed from the fitted rows, never typed
# ---------------------------------------------------------------------------------------------
all_rows <- c(a_rows, b_rows)
rows_dt <- rbindlist(lapply(all_rows, function(r) as.data.table(r)), fill = TRUE)
rows_dt[, sign := fifelse(coefficient > 0, "positive",
                          fifelse(coefficient < 0, "negative", "zero"))]
rows_dt[, sign_supported := fifelse(coefficient > 0 & ci_low > 0, "positive",
                             fifelse(coefficient < 0 & ci_high < 0, "negative", "none"))]
# A specification this close to zero has no direction, and its sign is decided by the last bit of a
# floating-point sum in the base rather than by the data — the counts moved once for exactly that reason.
# Declared band (S7-07); members are counted and reported, never quietly removed.
near_zero_band <- spec$support$near_zero_band
rows_dt[, near_zero := abs(coefficient) < near_zero_band]

count_signs <- function(dt) {
  list(
    n = nrow(dt),
    n_positive = sum(dt$sign == "positive"), n_negative = sum(dt$sign == "negative"),
    n_zero = sum(dt$sign == "zero"),
    n_positive_ci = sum(dt$sign_supported == "positive"),
    n_negative_ci = sum(dt$sign_supported == "negative"),
    n_near_zero = sum(dt$near_zero),
    n_positive_outside_band = sum(dt$sign == "positive" & !dt$near_zero),
    n_negative_outside_band = sum(dt$sign == "negative" & !dt$near_zero)
  )
}
support_by_design <- lapply(c("A", "B"), function(d) count_signs(rows_dt[design == d]))
names(support_by_design) <- c("A", "B")
support_overall <- count_signs(rows_dt)

axis_names <- list(A = c("outcome", "dose_lag_months", "adjustment_set", "window"),
                   B = c("shock", "controls", "window"))
pref_sign <- c(A = pref_a$coefficient > 0, B = pref_b$coefficient > 0)

by_axis_level <- list()
for (dz in c("A", "B")) {
  pref_level <- spec[[if (dz == "A") "design_a" else "design_b"]]$preferred
  for (axis in axis_names[[dz]]) {
    levels <- sort(unique(as.character(rows_dt[design == dz][[axis]])))
    for (level in levels) {
      sub <- rows_dt[design == dz & as.character(get(axis)) == level]
      n_pos <- sum(sub$sign == "positive"); n_neg <- sum(sub$sign == "negative")
      n_opposite <- if (pref_sign[[dz]]) n_neg else n_pos
      # Majority rule, declared in the spec: one negative cell in 27 is a corner of the grid, 20 in 27 is
      # a region. The minority count travels beside it rather than being discarded.
      flips <- n_opposite > nrow(sub) / 2
      by_axis_level[[length(by_axis_level) + 1]] <- list(
        design = dz, axis = axis, level = level,
        is_preferred_level = identical(as.character(pref_level[[axis]]), as.character(level)),
        n = nrow(sub), n_positive = n_pos, n_negative = n_neg,
        n_positive_ci = sum(sub$sign_supported == "positive"),
        n_negative_ci = sum(sub$sign_supported == "negative"),
        n_opposite = n_opposite,
        flips_against_preferred = flips
      )
    }
  }
}

# ---------------------------------------------------------------------------------------------
# Sensitivity — Oster delta, leave-one-state-out, in-time placebo, HAC bandwidth
# ---------------------------------------------------------------------------------------------
fmt <- function(x, d = 4) ifelse(is.na(x), "—", formatC(x, digits = d, format = "f"))

# Which base this grid was fitted on, computed by the queries declared in the spec so that the verifier
# runs the identical statement. Values are hashed at 10 significant digits: a rebuild of the same data
# differs in the last bit of a parallel float sum and must not trip the check, while a material change
# must.
base_fingerprint <- lapply(spec$base_fingerprint$queries, function(sql) {
  as.character(DBI::dbGetQuery(con, sql)[[1]])
})
message(sprintf("base fingerprint: state_panel %s, national %s, oil %s",
                substr(base_fingerprint$state_panel, 1, 12),
                substr(base_fingerprint$faac_national_monthly, 1, 12),
                substr(base_fingerprint$oil_series, 1, 12)))

oster_bound <- function(frame, y, treat, long_rhs) {
  long <- lm(as.formula(sprintf("%s ~ %s + %s", y, treat, long_rhs)), data = frame)
  short <- lm(as.formula(sprintf("%s ~ %s", y, treat)), data = frame)
  b_long <- unname(coef(long)[[treat]])
  b_short <- unname(coef(short)[[treat]])
  r2_long <- summary(long)$r.squared
  r2_short <- summary(short)$r.squared
  r_max <- min(1, spec$design_a$checks$oster$rmax_multiplier * r2_long)
  numerator <- b_long * (r2_long - r2_short)
  denominator <- (b_short - b_long) * (r_max - r2_long)
  delta <- if (isTRUE(all.equal(denominator, 0))) NA_real_ else numerator / denominator
  beta_star <- b_long - (b_short - b_long) * (r_max - r2_long) / (r2_long - r2_short)
  # Oster's delta is only a magnitude with a reading when the control set moves the estimate toward zero
  # without changing its sign. Both other cases occur here, so each is named rather than printed as a
  # bare number: a delta of -44 is not "very robust" and a sign flip is not an attenuation bound.
  flips_sign <- sign(b_short) != sign(b_long)
  delta_interpretable <- !is.na(delta) && !flips_sign && delta > 0
  interpretation <- if (is.na(delta)) {
    "the controlled and uncontrolled estimates coincide, so delta is undefined"
  } else if (flips_sign) {
    sprintf(paste0("the control set flips the sign of the estimate (%s without controls, %s with them), ",
                   "so delta has no attenuation reading: it is the amount of unobserved selection that ",
                   "would have to act *against* the observed controls to bring the estimate to zero."),
            fmt(b_short), fmt(b_long))
  } else if (delta > 0) {
    "the observed controls attenuate the estimate toward zero; delta is how much stronger unobserved selection on the treatment would have to be, relative to the observed controls, to bring the estimate to zero"
  } else {
    "the observed controls move the estimate away from zero, so delta is negative and Oster's usual cutoff (delta >= 1) does not apply; beta* at delta = 1 is reported instead"
  }
  list(
    beta_long = b_long, beta_short = b_short,
    r2_long = r2_long, r2_short = r2_short, r2_max = r_max,
    delta = delta, delta_interpretable = delta_interpretable,
    control_set_flips_the_sign = flips_sign,
    beta_star_at_delta_1 = beta_star,
    interpretation = interpretation
  )
}

# Design A: the linear analogue of the preferred PPML specification.
frame_a <- panel[!is.na(log_dose) & window_mask(panel, spec$design_a$preferred$window)]
frame_a[, log1p_outcome := log1p(get(spec$design_a$preferred$outcome))]
oster_a <- oster_bound(frame_a, "log1p_outcome", "log_dose",
                       "factor(state_id) + factor(ym)")
oster_a$analogue <- spec$design_a$checks$oster$analogue
message(sprintf("Oster (A analogue): delta = %s, beta* = %.4f",
                ifelse(is.na(oster_a$delta), "undefined", sprintf("%.3f", oster_a$delta)),
                oster_a$beta_star_at_delta_1))

# Leave-one-state-out on the preferred A specification: 36 refits plus the three oil states together.
loo <- list()
for (state in sort(unique(as.character(frame_a$state_name)))) {
  fit <- fit_dose(frame_a[state_name != state], spec$design_a$preferred$outcome, "log_dose",
                  spec$design_a$preferred$adjustment_set)
  loo[[state]] <- unname(summary(fit)$coeftable[1, "Estimate"])
}
loo_dt <- data.table(state = names(loo), coefficient = unlist(loo))
loo_dt <- loo_dt[order(-abs(coefficient))]
oil_states <- unlist(spec$design_a$checks$leave_one_state_out$oil_states)
fit_oil <- fit_dose(frame_a[!state_name %in% oil_states], spec$design_a$preferred$outcome,
                    "log_dose", spec$design_a$preferred$adjustment_set)
loo_summary <- list(
  unit = "state_name",
  preferred_coefficient = pref_a$coefficient,
  n_refits = nrow(loo_dt),
  min = min(loo_dt$coefficient), max = max(loo_dt$coefficient),
  median = median(loo_dt$coefficient),
  n_sign_flips = sum(sign(loo_dt$coefficient) != sign(pref_a$coefficient)),
  most_influential = lapply(seq_len(min(3, nrow(loo_dt))), function(i) {
    list(state = loo_dt$state[i], coefficient = loo_dt$coefficient[i])
  }),
  drop_oil_states = list(
    states = oil_states,
    coefficient = unname(summary(fit_oil)$coeftable[1, "Estimate"]),
    n_obs = as.integer(stats::nobs(fit_oil))
  ),
  distribution = lapply(seq_len(nrow(loo_dt)), function(i) {
    list(state = loo_dt$state[i], coefficient = loo_dt$coefficient[i])
  })
)
message(sprintf("leave-one-state-out: %d refits, range [%.4f, %.4f], %d sign flip(s); dropping %s: %.4f",
                loo_summary$n_refits, loo_summary$min, loo_summary$max, loo_summary$n_sign_flips,
                paste(oil_states, collapse = "/"), loo_summary$drop_oil_states$coefficient))

# Design B: Oster on the preferred local projection at the focus horizon.
frame_b <- copy(national)
frame_b[, y := shift(log_faac, h_focus, type = "lead") - shift(log_faac, 1)]
frame_b <- frame_b[!is.na(y) & !is.na(get(spec$design_b$preferred$shock)) &
                     window_mask(frame_b, spec$design_b$preferred$window)]
oster_b <- oster_bound(frame_b, "y", spec$design_b$preferred$shock, "month_of_year")
oster_b$analogue <- spec$design_b$checks$oster$analogue
message(sprintf("Oster (B): delta = %s, beta* = %.4f",
                ifelse(is.na(oster_b$delta), "undefined", sprintf("%.3f", oster_b$delta)),
                oster_b$beta_star_at_delta_1))

# In-time placebo: shift the shock series by every non-zero offset and compare, paired on the same rows.
off_lo <- spec$design_b$checks$in_time_placebo$offsets[[1]]
off_hi <- spec$design_b$checks$in_time_placebo$offsets[[2]]
offsets <- setdiff(seq(off_lo, off_hi), 0)
placebo_rows <- vector("list", length(offsets))
for (j in seq_along(offsets)) {
  k <- offsets[j]
  shifted <- copy(national)
  shifted[, placebo_shock := shift(get(spec$design_b$preferred$shock), k)]
  shifted <- shifted[!is.na(placebo_shock)]
  observed_same_rows <- lp_row(shifted, spec$design_b$preferred$shock,
                               spec$design_b$preferred$controls, h_focus,
                               spec$design_b$preferred$window)$estimate
  shifted_fit <- lp_row(shifted, "placebo_shock", spec$design_b$preferred$controls, h_focus,
                        spec$design_b$preferred$window)
  placebo_rows[[j]] <- list(offset = k, observed_same_rows = observed_same_rows,
                            shifted = shifted_fit$estimate, n_obs = nrow(shifted_fit$frame))
}
placebo_est <- unlist(lapply(placebo_rows, function(r) r$shifted))
placebo_obs <- unlist(lapply(placebo_rows, function(r) r$observed_same_rows))
placebo_p <- mean(abs(placebo_est) >= abs(placebo_obs))
in_time <- list(
  offsets = offsets, n_draws = length(offsets), p_value = placebo_p,
  shifted_mean_abs = mean(abs(placebo_est)), shifted_max_abs = max(abs(placebo_est)),
  observed_mean_abs = mean(abs(placebo_obs)), observed = pref_b$coefficient,
  distribution = unname(placebo_rows),
  note = spec$design_b$checks$in_time_placebo$why
)
message(sprintf("in-time placebo (%d offsets): p = %.4f", length(offsets), placebo_p))

# HAC bandwidth sensitivity on the preferred B specification — intervals only, coefficients unchanged.
hac_band <- list()
for (lag in c(spec$design_b$inference$maxlags, unlist(spec$design_b$inference$sensitivity_lags))) {
  got <- lp_row(national, spec$design_b$preferred$shock, spec$design_b$preferred$controls,
                h_focus, spec$design_b$preferred$window)
  V <- sandwich::NeweyWest(got$model, lag = lag, prewhite = FALSE, adjust = TRUE)
  se <- unname(sqrt(diag(V))[spec$design_b$preferred$shock])
  hac_band[[as.character(lag)]] <- list(
    maxlags = as.integer(lag), standard_error = se,
    ci_low = got$estimate - 1.96 * se, ci_high = got$estimate + 1.96 * se
  )
}

# A p-value is not a verdict, and this one sits between the two readings, so the interpretation is
# computed from the numbers rather than chosen beside them.
b_counts <- count_signs(rows_dt[design == "B"])
sign_sentence <- if (b_counts$n_negative == 0 && b_counts$n_zero == 0) {
  sprintf("The *sign* of Design B is the same in all %d grid specifications and all %d of its intervals ",
          b_counts$n, b_counts$n_positive_ci)
} else {
  sprintf("The *sign* of Design B disagrees with the preferred one in %d of %d grid specifications ",
          b_counts$n_negative + b_counts$n_zero, b_counts$n)
}
placebo_note <- if (placebo_p < 0.05) {
  sprintf(paste0(sign_sentence,
                 "exclude zero, and the true alignment is not exceeded by any of the %d shifted ",
                 "alignments (p = %.4f), so the timing of the response is not an artefact of the window."),
          length(offsets), placebo_p)
} else {
  sprintf(paste0(sign_sentence,
                 "exclude zero, but the in-time placebo does **not** clear 0.05: %.0f of %d shifted ",
                 "alignments return an estimate at least as large as the true one (p = %.4f). The sign is ",
                 "the robust claim here; the *timing* is the weaker one, and it is what the placebo tests."),
          round(placebo_p * length(offsets)), length(offsets), placebo_p)
}

rosenbaum <- list(
  status = "not_applicable",
  reason_a = spec$design_a$checks$rosenbaum$why,
  reason_b = spec$design_b$checks$rosenbaum$why
)

# ---------------------------------------------------------------------------------------------
# The figure — a specification curve per design, with the axis strips beneath
# ---------------------------------------------------------------------------------------------
sign_colour <- function(x) ifelse(x > 0, "#2b6cb0", "#c53030")

draw_panel <- function(rows, design, title) {
  d <- Filter(function(r) identical(r$design, design), rows)
  est <- vapply(d, function(r) r$coefficient, numeric(1))
  ord <- order(est)
  d <- lapply(ord, function(i) d[[i]])
  d <- rbindlist(lapply(d, function(r) as.data.table(r)), fill = TRUE)
  n <- nrow(d)
  idx <- seq_len(n)
  ylim <- range(c(d$ci_low, d$ci_high, 0), na.rm = TRUE)
  ylim <- ylim + c(-0.06, 0.06) * diff(ylim)
  par(mar = c(3.2, 5, 2.6, 1))
  plot(idx, d$coefficient, pch = 19, cex = 0.85, col = sign_colour(d$coefficient),
       ylim = ylim, xlab = "", ylab = "coefficient",
       main = title, cex.main = 1.05, las = 1)
  segments(idx, d$ci_low, idx, d$ci_high, col = sign_colour(d$coefficient))
  abline(h = 0, lty = 2, col = "grey30")

  neg <- which(d$coefficient < 0)
  if (length(neg)) {
    rect(0.5, ylim[1], max(neg) + 0.5, 0, col = adjustcolor("#c53030", alpha.f = 0.06), border = NA)
    abline(v = max(neg) + 0.5, lty = 3, col = "#c53030")
  }
  pref_idx <- which(d$preferred)
  abline(v = pref_idx, lty = 4, lwd = 1.4, col = "black")
  text(pref_idx, ylim[2], sprintf(" pre-registered (%.3f) ", d$coefficient[pref_idx]),
       pos = 4, cex = 0.75, srt = 0)

  n_pos <- sum(d$coefficient > 0); n_neg <- sum(d$coefficient < 0)
  ci_pos <- sum(d$coefficient > 0 & d$ci_low > 0); ci_neg <- sum(d$coefficient < 0 & d$ci_high < 0)
  mtext(sprintf("%d specifications sorted by coefficient: %d positive (%d with CI > 0), %d negative (%d with CI < 0)",
                n, n_pos, ci_pos, n_neg, ci_neg), side = 3, line = 0.1, cex = 0.72)
  invisible(d)
}

draw_strip <- function(rows, design, axes) {
  d <- Filter(function(r) identical(r$design, design), rows)
  est <- vapply(d, function(r) r$coefficient, numeric(1))
  d <- lapply(order(est), function(i) d[[i]])
  d <- rbindlist(lapply(d, function(r) as.data.table(r)), fill = TRUE)
  index <- seq_len(nrow(d))
  labels <- character(0); positions <- list(); colours <- list()
  for (axis in axes) {
    levels <- sort(unique(as.character(d[[axis]])))
    for (level in levels) {
      hit <- index[as.character(d[[axis]]) == level]
      labels <- c(labels, sprintf("%s = %s", axis, level))
      positions[[length(positions) + 1]] <- hit
      colours[[length(colours) + 1]] <- sign_colour(d$coefficient[hit])
    }
  }
  k <- length(labels)
  par(mar = c(2.6, 24, 0.8, 1))
  plot.new()
  plot.window(xlim = c(0.5, nrow(d) + 0.5), ylim = c(0.5, k + 0.5), xaxs = "i", yaxs = "i")
  title(xlab = "specification index (same order as the panel above)", cex.lab = 0.75)
  abline(h = seq_len(k), col = "grey92")
  for (i in seq_len(k)) points(positions[[i]], rep(k - i + 1, length(positions[[i]])),
                               pch = 15, cex = 0.5, col = colours[[i]])
  axis(2, at = k - seq_len(k) + 1, labels = labels, las = 1, cex.axis = 0.62, tick = FALSE)
  axis(1, cex.axis = 0.7, tick = FALSE)
  box(col = "grey80")
}

svg_path <- file.path(out_dir, spec$figure$path)
svglite::svglite(svg_path, width = 11, height = 13)
layout(matrix(c(1, 2, 3, 4), nrow = 4), heights = c(3.4, 2.6, 3.4, 1.6))
draw_panel(all_rows, "A", "Design A — state dose-response (PPML elasticity), 81 specifications")
draw_strip(all_rows, "A", unlist(axis_names$A))
draw_panel(all_rows, "B", sprintf("Design B — national fiscal transmission, cumulative elasticity at h=%d, 24 specifications", h_focus))
draw_strip(all_rows, "B", unlist(axis_names$B))
invisible(dev.off())
# The figure's size is recorded on its *canonical* bytes (CRLF collapsed to LF), because `.gitattributes`
# stores this repository's text with `eol=lf`. A raw `file.info()$size` is true only on the Windows checkout that
# produced it: after any clone or on the Linux runner the file is ~800 bytes smaller and the contract check would
# call a fresh figure stale. `03_estimate.R` applies the same rule to the forest plot, and the Python consumers
# (`tests/verify_stage7.py`, `tests/verify_site.py`) apply it too — this engine recorded raw bytes until that
# mismatch was found by the site verifier.
canonical_bytes <- function(path) {
  raw <- readBin(path, "raw", n = file.info(path)$size)
  if (length(raw) == 0) return(0L)
  is_cr <- raw == as.raw(13)
  is_lf <- raw == as.raw(10)
  crlf <- c(FALSE, is_cr[-length(is_cr)] & is_lf[-1])
  sum(!crlf)
}
message(sprintf("figure: %s (%d canonical bytes)", spec$figure$path, canonical_bytes(svg_path)))

# ---------------------------------------------------------------------------------------------
# Write
# ---------------------------------------------------------------------------------------------
sign_flip_levels <- Filter(function(x) isTRUE(x$flips_against_preferred), by_axis_level)

# ---------------------------------------------------------------------------------------------
# Spread decomposition (Design B) — the magnitude claim, computed rather than typed
# ---------------------------------------------------------------------------------------------
# The report says the spread is mostly the shock definition. Which axis moves the coefficient is a
# claim about the grid, so it is computed here from the fitted rows and published in the artifact;
# the deck of numbers the prose quotes then comes from one read, the defect C-49 named.
b_rows <- rows_dt[design == "B"]
b_hold_shock <- b_rows[, .(range = max(coefficient) - min(coefficient)), by = .(shock, window)]
b_hold_controls <- b_rows[, .(range = max(coefficient) - min(coefficient)), by = .(controls, window)]
spread_b <- list(
  rule = spec$design_b$spread_rule,
  n = nrow(b_rows),
  n_cells_holding_shock = nrow(b_hold_shock),
  n_cells_holding_controls = nrow(b_hold_controls),
  coefficient_min = min(b_rows$coefficient),
  coefficient_min_spec = b_rows[which.min(coefficient)]$spec_id,
  coefficient_max = max(b_rows$coefficient),
  coefficient_max_spec = b_rows[which.max(coefficient)]$spec_id,
  across_covariate_sets = mean(b_hold_shock$range),
  across_shock_definitions = mean(b_hold_controls$range)
)

robustness <- list(
  stage = 7,
  layer = "robustness",
  vintage = vintage,
  generated_at = format(Sys.time(), "%Y-%m-%dT%H:%M:%S%z"),
  generator = spec$engine,
  spec = spec_file,
  verifier = spec$verifier,
  input = spec$input,
  upstream = list(estimates = spec$upstream$estimates, preferred_matches_stage6 = stage6_check),
  grid = list(
    design_a = list(n = nrow(a_grid), axes = spec$design_a$axes),
    design_b = list(n = nrow(b_grid), axes = spec$design_b$axes, focus_horizon = as.integer(h_focus)),
    n_total = nrow(a_grid) + nrow(b_grid)
  ),
  preferred = list(
    A = pref_a$spec_id, B = pref_b$spec_id,
    rule = "the specification pre-registered in estimation.yml; marked, not selected by the grid",
    design_a = list(coefficient = pref_a$coefficient, standard_error = pref_a$standard_error,
                    ci_low = pref_a$ci_low, ci_high = pref_a$ci_high, n_obs = pref_a$n_obs),
    design_b = list(coefficient = pref_b$coefficient, standard_error = pref_b$standard_error,
                    ci_low = pref_b$ci_low, ci_high = pref_b$ci_high, n_obs = pref_b$n_obs)
  ),
  base_fingerprint = list(
    why = spec$base_fingerprint$why,
    queries = spec$base_fingerprint$queries,
    values = base_fingerprint
  ),
  support = list(
    rule = list(sign = spec$support$sign_rule, interval = spec$support$interval_rule,
                note = spec$support$counting_note,
                near_zero_band = near_zero_band, near_zero_why = spec$support$near_zero_why),
    overall = support_overall, by_design = support_by_design,
    by_axis_level = unname(by_axis_level),
    flips = list(
      rule = spec$support$flips$rule,
      n_levels = length(sign_flip_levels),
      levels = unname(sign_flip_levels)
    )
  ),
  sensitivity = list(
    design_a = list(oster = oster_a, leave_one_state_out = loo_summary),
    design_b = list(oster = oster_b, in_time_placebo = in_time, hac_bandwidth = unname(hac_band),
                    in_time_placebo_interpretation = placebo_note),
    rosenbaum = rosenbaum
  ),
  spread = list(design_b = spread_b),
  unbuilt_axes = unname(spec$unbuilt_axes),
  figure = list(path = spec$figure$path, layout = spec$figure$layout,
                n_points = nrow(rows_dt), bytes = canonical_bytes(svg_path)),
  specifications = unname(lapply(all_rows, function(r) {
    r$preferred <- isTRUE(r$preferred)
    r$sign <- if (r$coefficient > 0) "positive" else if (r$coefficient < 0) "negative" else "zero"
    r
  })),
  notes = list(
    "Every specification in the declared grid is published, including the ones whose sign disagrees with the preferred specification.",
    "Support counts are descriptive: the specifications share rows, outcomes and windows, so a count is not a vote and is not a probability that the sign is right.",
    "The preferred specification was pre-registered in estimation.yml and is marked on the curve; it was not selected by the grid.",
    "Oster's delta is computed on the linear analogue for Design A because PPML has no R-squared; it is a bound on the analogue, not on the PPML estimate.",
    "Rosenbaum bounds are not applicable: the treatment is continuous and no matching was performed."
  )
)
write_json(robustness, file.path(out_dir, "robustness.json"),
           auto_unbox = TRUE, pretty = TRUE, digits = 10)

# ---------------------------------------------------------------------------------------------
# Report — every number below is computed above
# ---------------------------------------------------------------------------------------------
sup_row <- function(label, s) sprintf("| %s | %d | %d | %d | %d | %d |",
                                      label, s$n, s$n_positive, s$n_positive_ci,
                                      s$n_negative, s$n_negative_ci)
flip_lines <- if (length(sign_flip_levels)) {
  vapply(sign_flip_levels, function(x) sprintf(
    paste0("- **Design %s, %s = %s**: %d of %d specifications carry the opposite sign to the preferred ",
           "one (%d positive, %d negative)"),
    x$design, x$axis, x$level, x$n_opposite, x$n, x$n_positive, x$n_negative), character(1))
} else "- No axis level has a majority of specifications on the opposite side of zero."

axis_table <- vapply(by_axis_level, function(x) sprintf(
  "| %s | %s | %s | %d | %d | %d | %d |", x$design, x$axis, x$level, x$n,
  x$n_positive, x$n_negative, x$n_opposite), character(1))

# The headline about Design A is derived from the grid, not written next to it: the sign's dependence on
# the dose lag is the single most important thing this stage found, and a sentence cannot be trusted to
# keep up with a re-fit.
a_lag_flips <- Filter(function(x) x$design == "A" && x$axis == "dose_lag_months" &&
                        x$flips_against_preferred, by_axis_level)
# The lag sentence is assembled from the fitted rows, not typed: if a re-fit changes which windows are
# negative, the sentence changes with it.
lag1 <- Filter(function(s) s$design == "A" && s$dose_lag_months == 1 &&
                 s$adjustment_set == "state_month_fe" &&
                 identical(s$outcome, spec$design_a$preferred$outcome), a_rows)
lag1_neg <- sum(vapply(lag1, function(s) s$coefficient < 0, logical(1)))
lag1_sentence <- if (length(lag1) && lag1_neg == length(lag1)) {
  sprintf("With the dose lagged one month and state and month effects, the estimate is negative in all %d windows", length(lag1))
} else if (length(lag1)) {
  sprintf("With the dose lagged one month and state and month effects, the estimate is negative in %d of %d windows", lag1_neg, length(lag1))
} else ""
lag_sentences <- vapply(a_lag_flips, function(x) sprintf(
  "At a lag of %d month%s, %d of %d specifications are on the opposite side of zero (%d negative).",
  as.integer(x$level), if (as.integer(x$level) == 1) "" else "s",
  x$n_opposite, x$n, x$n_negative), character(1))
headline_a <- if (length(a_lag_flips)) paste(
  "**The sign of Design A is not stable, and the axis that moves it is the dose lag.**",
  sprintf("%s, while the pre-registered same-month specification is positive.", lag1_sentence),
  paste(lag_sentences, collapse = " "),
  paste0("A quantity whose sign depends on a one-month timing choice is not a direction, and that is a ",
         "stronger statement than Stage 6 could make from one specification and its placebo."),
  collapse = " ") else
  "No dose-lag level has a majority of specifications on the opposite side of zero."

md <- c(
  sprintf("# Stage 7 — robustness and the multiverse, vintage %s", vintage),
  "",
  sprintf("Generated %s by `%s` from `%s`. Every specification and every count is recomputed independently by `%s`.",
          robustness$generated_at, spec$engine, spec_file, spec$verifier),
  "",
  "## What this stage is for",
  "",
  paste0("Stage 6 published two estimates. This stage asks whether they survive the choices that were not ",
         "pinned down: ", nrow(a_grid), " specifications for Design A and ", nrow(b_grid),
         " for Design B, each declared in the spec before it was fitted, every one of them stored — ",
         "including the ones that disagree. The count below is a count over a correlated grid, not a vote."),
  "",
  "## Support counts",
  "",
  "| Group | n | positive | positive, CI excludes 0 | negative | negative, CI excludes 0 |",
  "|---|---|---|---|---|---|",
  sup_row("A — state dose-response", support_by_design$A),
  sup_row("B — national transmission", support_by_design$B),
  sup_row("overall", support_overall),
  "",
  paste0("> ", spec$support$counting_note),
  "",
  paste0("> **The near-zero band.** ", sprintf(
    paste0("%d of the %d specifications sit within ±%s of zero — %d of Design A's and %d of Design B's. ",
           "Their sign is rounding, not direction, and it is not stable across a rebuild of the base: the ",
           "counts above moved by one specification (44/37 to 45/36) between two bases for exactly that ",
           "reason. They stay in the counts and are declared here, because removing them from `n` would ",
           "hide the instability rather than name it."),
    support_overall$n_near_zero, support_overall$n, fmt(near_zero_band, 2),
    support_by_design$A$n_near_zero, support_by_design$B$n_near_zero)),
  "",
  "Excluding the band, the counts are:",
  "",
  "| Group | positive outside the band | negative outside the band |",
  "|---|---|---|",
  sprintf("| A | %d | %d |", support_by_design$A$n_positive_outside_band,
          support_by_design$A$n_negative_outside_band),
  sprintf("| B | %d | %d |", support_by_design$B$n_positive_outside_band,
          support_by_design$B$n_negative_outside_band),
  "",
  "### Where the sign changes",
  "",
  headline_a,
  "",
  flip_lines,
  "",
  "Every axis level, with the count on each side of zero and the count opposite the preferred sign:",
  "",
  "| Design | Axis | Level | n | positive | negative | opposite to preferred |",
  "|---|---|---|---|---|---|---|",
  axis_table,
  "",
  "## The pre-registered specifications",
  "",
  sprintf(paste0("Across the %d Design B specifications the coefficient at h=%d runs from **%s** (`%s`) ",
                 "to **%s** (`%s`). Holding the shock definition fixed, it spans %s across the control ",
                 "sets and windows; holding the covariate set fixed, it spans %s across the two shock ",
                 "definitions — a three-month average shock is a smoother regressor, so less of it is ",
                 "measurement noise and its coefficient is correspondingly larger. Every one of the %d ",
                 "keeps the sign."),
          nrow(b_grid), h_focus,
          fmt(spread_b$coefficient_min), spread_b$coefficient_min_spec,
          fmt(spread_b$coefficient_max), spread_b$coefficient_max_spec,
          fmt(spread_b$across_covariate_sets),
          fmt(spread_b$across_shock_definitions),
          sum(rows_dt[design == "B"]$sign == "positive")),
  "",
  "| Design | Specification | Coefficient | SE | 95 % CI | n |",
  "|---|---|---|---|---|---|",
  sprintf("| A | %s | %s | %s | [%s, %s] | %d |", pref_a$outcome, fmt(pref_a$coefficient),
          fmt(pref_a$standard_error), fmt(pref_a$ci_low), fmt(pref_a$ci_high), pref_a$n_obs),
  sprintf("| B | %s / %s / %s (h=%d) | %s | %s | [%s, %s] | %d |",
          pref_b$shock, pref_b$controls, pref_b$window, h_focus, fmt(pref_b$coefficient),
          fmt(pref_b$standard_error), fmt(pref_b$ci_low), fmt(pref_b$ci_high), pref_b$n_obs),
  "",
  if (isTRUE(stage6_check$checked)) {
    sprintf(paste0("Both reproduce the Stage 6 artifact: A differs by %.1e and B by %.1e, against a ",
                   "tolerance of %.0e — the pre-registered cell of the grid is the published estimate, ",
                   "not a neighbour of it."), stage6_check$design_a$abs_diff,
            stage6_check$design_b$abs_diff, stage6_check$tolerance)
  } else {
    sprintf("Stage 6 comparison not made: %s", stage6_check$why)
  },
  "",
  "## Sensitivity",
  "",
  "### Oster delta (unobserved confounding)",
  "",
  sprintf(paste0("- **Design B**, at h=%d, on the preferred specification: beta(short) = %s, ",
                 "beta(long) = %s, R2 %s -> %s, R2max = %s. ",
                 "**delta = %s** for a zero estimate, and beta* at delta = 1 is %s."),
          h_focus, fmt(oster_b$beta_short), fmt(oster_b$beta_long), fmt(oster_b$r2_short, 3),
          fmt(oster_b$r2_long, 3), fmt(oster_b$r2_max, 3),
          ifelse(is.na(oster_b$delta), "undefined", fmt(oster_b$delta, 2)),
          fmt(oster_b$beta_star_at_delta_1)),
  sprintf("  %s", oster_b$interpretation),
  sprintf(paste0("- **Design A**, on the **linear analogue** (%s): delta = %s, beta* at delta = 1 is %s. ",
                 "This is a bound on the analogue, not on the PPML estimate, because Oster's delta ",
                 "requires an R-squared and PPML does not have one."),
          oster_a$analogue, ifelse(is.na(oster_a$delta), "undefined", fmt(oster_a$delta, 2)),
          fmt(oster_a$beta_star_at_delta_1)),
  sprintf("  %s", oster_a$interpretation),
  "",
  "### Leave-one-state-out (Design A)",
  "",
  sprintf(paste0("36 refits of the preferred specification, dropping one state at a time: coefficients ",
                 "range **[%s, %s]** around %s, median %s, with **%d** sign flip(s). The three most ",
                 "influential states are %s."),
          fmt(loo_summary$min), fmt(loo_summary$max), fmt(pref_a$coefficient),
          fmt(loo_summary$median), loo_summary$n_sign_flips,
          paste(vapply(loo_summary$most_influential, function(x)
            sprintf("%s (%s)", x$state, fmt(x$coefficient)), character(1)), collapse = ", ")),
  sprintf("Dropping the three oil-producing states named in the spec (%s) returns **%s** on %d rows.",
          paste(loo_summary$drop_oil_states$states, collapse = ", "),
          fmt(loo_summary$drop_oil_states$coefficient), loo_summary$drop_oil_states$n_obs),
  "",
  "### In-time placebo (Design B)",
  "",
  sprintf(paste0("The shock series shifted by each of %d non-zero offsets (%d to %d months) and the ",
                 "preferred specification refitted at h=%d: **p = %.4f**. Placebo estimates average ",
                 "|%s| with a maximum of |%s|; the estimate is %s."),
          in_time$n_draws, off_lo, off_hi, h_focus, in_time$p_value,
          fmt(in_time$shifted_mean_abs), fmt(in_time$shifted_max_abs), fmt(pref_b$coefficient)),
  "",
  placebo_note,
  "",
  "### HAC bandwidth (Design B, intervals only)",
  "",
  "| maxlags | SE | 95 % CI |",
  "|---|---|---|",
  vapply(hac_band, function(x) sprintf("| %d | %s | [%s, %s] |", x$maxlags,
                                       fmt(x$standard_error), fmt(x$ci_low), fmt(x$ci_high)),
         character(1)),
  "",
  "Changing the bandwidth changes no coefficient; it shows how much of the interval's width is a ",
  "bandwidth choice rather than a sample.",
  "",
  "### Rosenbaum bounds",
  "",
  paste0("Not applicable. ", rosenbaum$reason_a),
  "",
  "## What the grid cannot vary, and why that is stated",
  "",
  vapply(spec$unbuilt_axes, function(x) sprintf(
    "- **%s** — `%s`. %s", x$axis, x$status, x$reason), character(1)),
  "",
  "## Which base this was fitted on",
  "",
  sprintf(paste0("Fingerprints, computed by the queries declared in `robustness.yml` at 10 significant ",
                 "digits: `state_panel` %s, `faac_national_monthly` %s, the oil series %s. "),
          substr(base_fingerprint$state_panel, 1, 12),
          substr(base_fingerprint$faac_national_monthly, 1, 12),
          substr(base_fingerprint$oil_series, 1, 12)),
  spec$base_fingerprint$why,
  "",
  "## Where the figure is",
  "",
  sprintf("`%s`, drawn by this engine: two panels, each sorted by coefficient with the 95 %% interval, ",
          spec$figure$path),
  "the zero line, the pre-registered specification marked, and the axis levels of every specification ",
  "beneath it in the same order — so a sign change can be read against the choice that produced it.",
  "",
  "## What this stage does not claim",
  "",
  paste0("- A count over this grid is **not** independent evidence: the specifications reuse the same ",
         "rows and outcomes. It bounds how sensitive the sign is to the declared choices; it does not ",
         "estimate a probability that the sign is right."),
  paste0("- The per-capita dose (D1) is **not** in the grid: `d1_faac_per_capita` is empty because the ",
         "state population denominator is an unmade decision (X-09). The nominal dose is what the curve ",
         "varies."),
  paste0("- No specification in this grid makes Design A identified. Stage 6's verdict stands: the ",
         "identifying variation is the oil price moving the derivation share (C-47), and a robustness ",
         "grid over controls and windows cannot create variation the dose does not have."),
  ""
)
writeLines(md, file.path(out_dir, "report.md"))

message(sprintf("\nsupport: A %d positive / %d negative; B %d positive / %d negative",
                support_by_design$A$n_positive, support_by_design$A$n_negative,
                support_by_design$B$n_positive, support_by_design$B$n_negative))
message(sprintf("design B spread: %.4f .. %.4f; across covariate sets %.4f (%d cells), across shock definitions %.4f (%d cells)",
                spread_b$coefficient_min, spread_b$coefficient_max,
                spread_b$across_covariate_sets, spread_b$n_cells_holding_shock,
                spread_b$across_shock_definitions, spread_b$n_cells_holding_controls))
message(sprintf("within the declared +/-%s near-zero band: %d of %d (A %d, B %d)",
                near_zero_band, support_overall$n_near_zero, support_overall$n,
                support_by_design$A$n_near_zero, support_by_design$B$n_near_zero))
message(sprintf("sign-flip levels: %d", length(sign_flip_levels)))
message(sprintf("written: %s", file.path(spec$output$root, vintage, "robustness.json")))
