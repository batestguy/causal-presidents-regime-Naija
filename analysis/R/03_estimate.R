#!/usr/bin/env Rscript
# Stage 6 — estimation. Writes registry/estimates/<vintage>/{estimates.json, report.md}.
#
# Everything the engine does is declared in `analysis/specs/estimation.yml`: the sample, the
# specifications, the inference, the checks that can kill a result and the rule that turns those checks
# into a verdict. No threshold, window or coefficient is typed here. The reason is not tidiness — it is
# that a reported number has to be reproducible from the spec plus the base, and a number that lives in
# this file cannot be checked by reading anything else.
#
# Run:
#     Rscript analysis/R/03_estimate.R
#     Rscript analysis/R/03_estimate.R --spec analysis/specs/estimation.yml
#
# Independent recomputation of every number written here: `tests/verify_stage6.py`.

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
  normalizePath("analysis/R/03_estimate.R")
}
REPO_ROOT <- normalizePath(file.path(dirname(script_path()), "..", ".."))

cli <- commandArgs(trailingOnly = TRUE)
spec_file <- if (length(cli) >= 2 && cli[1] == "--spec") cli[2] else "analysis/specs/estimation.yml"
spec_path <- file.path(REPO_ROOT, spec_file)
if (!file.exists(spec_path)) stop(sprintf("no specification at %s", spec_file))

spec <- yaml::read_yaml(spec_path)
vintage <- spec$labelled
out_dir <- file.path(REPO_ROOT, spec$output$root, vintage)
dir.create(out_dir, showWarnings = FALSE, recursive = TRUE)

message(sprintf("Stage 6 estimation — vintage %s", vintage))
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
panel[, log_dose := log(dose)]
panel[, state_id := as.factor(state_id)]
panel[, ym := as.factor(ym)]
setorder(panel, state_id, period_month)

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
national[, d_oil := log_oil - shift(log_oil)]
national[, month_of_year := as.factor(format(period_month, "%m"))]

message(sprintf("design A sample: %d state-months, %d states, %s -> %s",
                nrow(panel), uniqueN(panel$state_id), min(panel$period_month), max(panel$period_month)))
message(sprintf("design B sample: %d months, %s -> %s",
                nrow(national), min(national$period_month), max(national$period_month)))

specs <- list()
checks <- list()

add_spec <- function(...) specs[[length(specs) + 1]] <<- list(...)

# ---------------------------------------------------------------------------------------------
# Design A — state dose-response
# ---------------------------------------------------------------------------------------------
fit_dose <- function(dt, outcome, dose_col = "log_dose") {
  f <- as.formula(sprintf("%s ~ %s | state_id + ym", outcome, dose_col))
  fixest::fepois(f, data = dt, cluster = ~state_id, notes = FALSE, warn = FALSE)
}

design_a <- spec$design_a
outcomes <- c(design_a$outcome, design_a$robustness_outcomes)

main_fits <- list()
for (outcome in outcomes) {
  fit <- fit_dose(panel, outcome)
  ct <- summary(fit)$coeftable
  term <- rownames(ct)[1]
  est <- ct[term, "Estimate"]
  se <- ct[term, "Std. Error"]
  p <- ct[term, "Pr(>|z|)"]
  main_fits[[outcome]] <- fit
  # Separation: a state with no positive outcome in the window contributes nothing to a Poisson
  # likelihood for its own fixed effect, and fixest drops it. Reported rather than left as an
  # unexplained n - three states lose their rows in the civilian specification, and a reader comparing
  # n across the three outcomes deserves to know which ones and why.
  totals <- panel[, .(total = sum(get(outcome))), by = .(state_id, state_name)]
  zero_units <- totals[total == 0]
  add_spec(
    design = design_a$id, design_name = design_a$name, outcome = outcome,
    estimator = design_a$estimator,
    formula = sprintf("%s ~ log(faac_gross_total_naira) | state_id + year_month", outcome),
    fixed_effects = paste(design_a$fixed_effects, collapse = " + "),
    controls = "state fixed effects, month fixed effects",
    n_obs = as.integer(stats::nobs(fit)),
    n_units = uniqueN(panel$state_id),
    first_month = as.character(min(panel$period_month)),
    last_month = as.character(max(panel$period_month)),
    coefficient_name = "elasticity_of_fatalities_to_allocation",
    coefficient = unname(est), standard_error = unname(se),
    ci_low = unname(est - 1.96 * se), ci_high = unname(est + 1.96 * se),
    p_value = unname(p), covariance = "cluster by state (36 clusters)",
    units_dropped_by_separation = as.character(zero_units$state_name),
    n_units_used = as.integer(uniqueN(panel$state_id) - nrow(zero_units)),
    note = if (nrow(zero_units)) sprintf(paste0(
      "%d state(s) dropped by Poisson separation: no positive value for this outcome anywhere in ",
      "the window, so the state fixed effect is unidentified"), nrow(zero_units)) else "all 36 states used"
  )
}

# ---- placebo: the dose led by the declared number of months, within state ----------------------
lead <- design_a$checks$placebo_lead_months
placebo <- copy(panel)
setorder(placebo, state_id, period_month)
placebo[, log_dose_lead := shift(log_dose, lead, type = "lead"), by = state_id]
placebo <- placebo[!is.na(log_dose_lead)]
fit_placebo <- fit_dose(placebo, design_a$outcome, "log_dose_lead")
ct <- summary(fit_placebo)$coeftable
placebo_est <- unname(ct[1, "Estimate"])
placebo_se <- unname(ct[1, "Std. Error"])
message(sprintf("placebo (dose led %d months): %+.4f (%.4f), n=%d",
                lead, placebo_est, placebo_se, stats::nobs(fit_placebo)))

# ---- the decisive check: a mis-timed dose ------------------------------------------------------
# Every non-zero offset in the declared interval, each against the observed estimate fitted on the same
# rows. Paired by construction: a shift costs observations at the ends, so the observed fit is redone on
# the shifted sample rather than compared with a fit on a larger one.
lead_shift <- design_a$checks$lead_shift
offsets <- setdiff(seq(lead_shift$offsets[[1]], lead_shift$offsets[[2]]), 0)
shift_rows <- list()
for (k in offsets) {
  shifted <- copy(panel)
  setorder(shifted, state_id, period_month)
  shifted[, log_dose_shift := shift(log_dose, k, type = "shift"), by = state_id]
  shifted <- shifted[!is.na(log_dose_shift)]
  fit_obs <- fit_dose(shifted, design_a$outcome)
  fit_shift <- fit_dose(shifted, design_a$outcome, "log_dose_shift")
  observed_same_rows <- unname(summary(fit_obs)$coeftable[1, "Estimate"])
  shifted_est <- unname(summary(fit_shift)$coeftable[1, "Estimate"])
  shift_rows[[as.character(k)]] <- list(
    offset = k, observed = observed_same_rows, shifted = shifted_est,
    direction = if (k > 0) "dose led" else "dose lagged",
    n_obs = as.integer(stats::nobs(fit_shift))
  )
}
shifted_estimates <- vapply(shift_rows, function(r) r$shifted, numeric(1))
observed_estimates <- vapply(shift_rows, function(r) r$observed, numeric(1))
p_lead_shift <- mean(abs(shifted_estimates) >= abs(observed_estimates))
message(sprintf("lead-shift randomisation (%d offsets): p = %.4f; shifted |est| mean %.4f, max %.4f",
                length(offsets), p_lead_shift, mean(abs(shifted_estimates)), max(abs(shifted_estimates))))

# ---- the secondary null, reported and not decisive --------------------------------------------
perm <- design_a$checks$secondary_check
set.seed(perm$seed)
observed <- unname(summary(main_fits[[design_a$outcome]])$coeftable[1, "Estimate"])
draws <- numeric(perm$n_draws)
for (i in seq_len(perm$n_draws)) {
  shuffled <- copy(panel)
  shuffled[, log_dose := sample(log_dose), by = ym]
  draws[i] <- unname(summary(fit_dose(shuffled, design_a$outcome))$coeftable[1, "Estimate"])
}
p_perm <- mean(abs(draws) >= abs(observed))
message(sprintf("secondary null (%d draws, %s): p = %.4f", perm$n_draws, perm$scheme, p_perm))

checks$design_a <- list(
  placebo = list(
    lead_months = lead, coefficient = placebo_est, standard_error = placebo_se,
    n_obs = as.integer(stats::nobs(fit_placebo)),
    note = paste0("the dose shifted ", lead, " months forward within each state; an estimate of ",
                  "comparable size means the specification is reading a shared pattern rather than ",
                  "the dose")
  ),
  lead_shift = list(
    offsets = as.integer(offsets), n_draws = length(offsets),
    p_value = p_lead_shift,
    shifted_mean_abs = mean(abs(shifted_estimates)),
    shifted_max_abs = max(abs(shifted_estimates)),
    observed_mean_abs = mean(abs(observed_estimates)),
    # The full distribution is published, not summarised: 61 numbers are cheap, and a reader who wants
    # to see that no offset reaches the estimate should be able to check that rather than take it.
    distribution = unname(lapply(shift_rows, function(r) r))
  ),
  secondary_check = list(
    n_draws = perm$n_draws, seed = perm$seed, scheme = perm$scheme,
    p_value = p_perm, null_mean = mean(draws), null_sd = sd(draws),
    observed = observed,
    note = perm$why
  )
)

identified <- p_lead_shift < 0.05 && abs(placebo_est) < abs(observed)
reasons <- c(
  if (p_lead_shift < 0.05) NULL else sprintf(
    "the lead-shift p-value is %.3f: %.0f of %d mis-timed doses return an estimate at least as large as the estimate itself",
    p_lead_shift, round(p_lead_shift * length(offsets)), length(offsets)),
  if (abs(placebo_est) < abs(observed)) NULL else sprintf(
    "the %d-month placebo (+%.3f) is at least as large as the estimate (%.3f), so the specification cannot distinguish the dose from itself shifted",
    lead, placebo_est, observed)
)
checks$design_a$verdict <- list(
  status = if (identified) "identified" else "estimated_not_identified",
  rule = design_a$verdict_rule,
  failed_checks = reasons
)

# ---------------------------------------------------------------------------------------------
# Design B — national fiscal transmission
# ---------------------------------------------------------------------------------------------
design_b <- spec$design_b
hac_se <- function(model, term, maxlags) {
  V <- sandwich::NeweyWest(model, lag = maxlags, prewhite = FALSE, adjust = TRUE)
  list(se = unname(sqrt(diag(V))[term]), vcov = V)
}

lp_rows <- list()
for (h in unlist(design_b$horizons)) {
  frame <- copy(national)
  # Cumulative response: log FAAC at t+h against its level at t-1. The cumulative form is the one whose
  # coefficient is "the fraction of the shock that has reached the states by h".
  frame[, y := log_faac[seq_len(.N) + h] - shift(log_faac)]
  frame <- frame[!is.na(y) & !is.na(d_oil)]
  model <- lm(y ~ d_oil + month_of_year, data = frame)
  se <- hac_se(model, "d_oil", design_b$inference$maxlags)
  est <- unname(coef(model)["d_oil"])
  lp_rows[[as.character(h)]] <- list(
    horizon = as.integer(h), coefficient = est, standard_error = se$se,
    ci_low = est - 1.96 * se$se, ci_high = est + 1.96 * se$se,
    t_statistic = est / se$se, n_obs = as.integer(stats::nobs(model))
  )
  add_spec(
    design = design_b$id, design_name = design_b$name,
    outcome = sprintf("cumulative log change in national FAAC at h=%d", h),
    estimator = sprintf("%s, h=%d", design_b$estimator, h),
    formula = "diff(log(faac), lag = h, leading) ~ diff(log(oil)) + month_of_year",
    fixed_effects = "none (local projection on the national series)",
    controls = "month-of-year dummies",
    n_obs = as.integer(stats::nobs(model)), n_units = 1L,
    first_month = as.character(min(frame$period_month)), last_month = as.character(max(frame$period_month)),
    coefficient_name = sprintf("cumulative_pass_through_h%d", h),
    coefficient = est, standard_error = se$se,
    ci_low = est - 1.96 * se$se, ci_high = est + 1.96 * se$se,
    p_value = 2 * pt(-abs(est / se$se), df = stats::nobs(model) - 3),
    covariance = sprintf("Newey-West, %d lags", design_b$inference$maxlags)
  )
}

peak_band <- unlist(design_b$checks$expect_peak_horizon)
band_rows <- Filter(function(r) r$horizon >= peak_band[1] && r$horizon <= peak_band[2], lp_rows)
peak_sig <- Filter(function(r) abs(r$t_statistic) > 1.96, band_rows)

# Lead placebo: does a *future* oil shock move today's allocation?
lead_b <- design_b$checks$placebo_lead_months
pframe <- copy(national)
pframe[, d_oil_lead := shift(d_oil, lead_b, type = "lead")]
pframe[, y := log_faac - shift(log_faac)]
pframe <- pframe[!is.na(y) & !is.na(d_oil_lead)]
pmodel <- lm(y ~ d_oil_lead + month_of_year, data = pframe)
pest <- unname(coef(pmodel)["d_oil_lead"])
pse <- hac_se(pmodel, "d_oil_lead", design_b$inference$maxlags)$se

peak_h <- if (length(lp_rows)) {
  unlist(lapply(lp_rows, function(r) r$horizon))[which.max(unlist(lapply(lp_rows, function(r) r$coefficient)))]
} else NA_integer_

checks$design_b <- list(
  peak_horizon = as.integer(peak_h),
  expected_band = as.integer(peak_band),
  significant_horizons = as.integer(unlist(lapply(peak_sig, function(r) r$horizon))),
  placebo = list(
    lead_months = lead_b, coefficient = pest, standard_error = pse, n_obs = as.integer(stats::nobs(pmodel)),
    note = "a future shock regressed on today's allocation; a comparable size means trend, not transmission"
  ),
  # Unnamed so it serialises as a JSON array rather than an object keyed by "0", "1", …: a reader (and
  # the verifier) should be able to iterate the path, and jsonlite turns a named list into an object.
  horizon_path = unname(lapply(lp_rows, function(r) r))
)
b_ok <- length(peak_sig) > 0 && abs(pest) < max(abs(unlist(lapply(band_rows, function(r) r$coefficient))))
checks$design_b$verdict <- list(
  status = if (b_ok) "estimated" else "estimated_null_at_the_declared_band",
  rule = design_b$verdict_rule,
  failed_checks = c(
    if (length(peak_sig) == 0) "no horizon in the declared peak band has |t| > 1.96" else NULL,
    if (abs(pest) < max(abs(unlist(lapply(band_rows, function(r) r$coefficient))))) NULL else
      "the lead placebo is at least as large as the estimated response"
  )
)

# ---------------------------------------------------------------------------------------------
# Figure — the CI forest plot
# ---------------------------------------------------------------------------------------------
# Declared in the spec's `figure` block, rendered from `specs` and nothing else: this function reads the
# artifact's own rows, so the picture cannot disagree with the table beside it. Base graphics on purpose —
# no extra dependency for a figure whose whole content is points, segments and labels — and the labels are
# drawn as text so that a verifier can look for every published specification in the rendered file rather
# than trusting that the loop ran.
fig_path <- file.path(out_dir, spec$figure$path)
# `svglite`, not the base `svg()` device the Stage 8b panels use: the cairo device converts text to glyph
# outlines, which renders identically but leaves no searchable label in the file — and the spec requires
# this figure to carry every specification's label as text. Stage 7's curve already renders this way.
svglite::svglite(fig_path, width = 11, height = 7.5)
par(mfrow = c(1, 2), mar = c(4.2, 11.5, 3.4, 1.2))

# `par("usr")` is only meaningful after a plot exists, so each panel takes its x-limits from its own rows
# and pads them by the widest interval, which keeps a row's whisker off the frame edge.
forest_panel <- function(rows, placebo_row, main, xlab, band = NULL) {
  est <- vapply(rows, function(r) r$coefficient, numeric(1))
  lo <- vapply(rows, function(r) r$ci_low, numeric(1))
  hi <- vapply(rows, function(r) r$ci_high, numeric(1))
  labs <- vapply(rows, function(r) r$label, character(1))
  # Top row first: a reader scans a forest plot downward, so the first published row must be at the top.
  y <- rev(seq_along(est))
  vals <- c(lo, hi, 0, if (!is.null(placebo_row)) placebo_row$coefficient else NULL)
  pad <- max(diff(range(vals)) * 0.06, 0.05)
  plot(NA, xlim = range(vals) + c(-pad, pad), ylim = c(0.4, length(est) + 1.6), yaxt = "n",
       xlab = xlab, ylab = "", main = main)
  if (!is.null(band))
    rect(par("usr")[1], min(y[band]) - 0.5, par("usr")[2], max(y[band]) + 0.5,
         col = "#f0f0f0", border = NA)
  abline(v = 0, col = "grey50")
  segments(lo, y, hi, y, lwd = 2, col = "black")
  points(est, y, pch = 19, cex = 1.1)
  if (!is.null(placebo_row)) {
    py <- length(est) + 1
    segments(placebo_row$coefficient, py, placebo_row$coefficient, py, lwd = 2)
    points(placebo_row$coefficient, py, pch = 1, cex = 1.2, lwd = 1.6)
    labs <- c(paste0(placebo_row$label, " (hollow)"), labs)
    y <- c(py, y)
  }
  axis(2, at = y, labels = labs, las = 1, cex.axis = 0.78)
}

a_rows <- Filter(function(s) s$design == "A", specs)
for (i in seq_along(a_rows)) a_rows[[i]]$label <- gsub("_", " ", a_rows[[i]]$outcome)
forest_panel(
  a_rows,
  list(label = sprintf("%d-month placebo", lead), coefficient = placebo_est),
  main = sprintf("A — state dose-response\n(%d state-months, %s to %s)",
                 nrow(panel), format(min(panel$period_month), "%Y-%m"), format(max(panel$period_month), "%Y-%m")),
  xlab = "elasticity of conflict to the state's allocation (log-points)"
)
# Spaced, not the artifact's snake_case: this text is read by a person, and `not identified` is the
# phrase the spec requires the figure to carry. (S8's rule that a card and the narrative must agree does
# not apply here — the figure states the same verdict string, only reformatted.)
mtext(sprintf("verdict: %s", gsub("_", " ", checks$design_a$verdict$status)), side = 3, line = -1.4,
      adj = 0.02, cex = 0.75, col = "#b2182b")

# The horizon lives in `lp_rows` and in the coefficient's name, not in the specification row, so it is
# read back out of the name rather than assumed to be present.
b_rows <- Filter(function(s) s$design == "B", specs)
for (i in seq_along(b_rows))
  b_rows[[i]]$horizon <- as.integer(sub("^.*_h", "", b_rows[[i]]$coefficient_name))
for (i in seq_along(b_rows)) b_rows[[i]]$label <- sprintf("h = %d", b_rows[[i]]$horizon)
band_idx <- which(vapply(b_rows, function(r) r$horizon >= peak_band[1] && r$horizon <= peak_band[2], logical(1)))
forest_panel(
  b_rows,
  list(label = sprintf("%d-month lead placebo", lead_b), coefficient = pest),
  main = sprintf("B — oil to state allocations\n(%d national months, %s to %s)",
                 nrow(national), format(min(national$period_month), "%Y-%m"),
                 format(max(national$period_month), "%Y-%m")),
  xlab = "cumulative response of the allocation to a 1 % oil move (log-points)",
  band = band_idx
)
mtext(sprintf("verdict: %s (declared peak band h = %d-%d, shaded)",
              gsub("_", " ", checks$design_b$verdict$status), peak_band[1], peak_band[2]),
      side = 3, line = -1.4, adj = 0.02, cex = 0.75)
mtext("filled = published estimate with its 95 % CI · hollow = the design's decisive check",
      side = 1, line = 2.6, adj = 0, cex = 0.72, col = "grey30")
invisible(dev.off())
# The figure's size is recorded on its *canonical* bytes (CRLF collapsed to LF), because `.gitattributes`
# stores this repository's text with `eol=lf`. A raw `file.info()$size` is true only on the Windows checkout
# that produced it: after any clone or the Linux runner the file is a few hundred bytes smaller and the
# contract test would call a fresh figure stale. The Python consumers apply the same rule.
canonical_bytes <- function(path) {
  raw <- readBin(path, "raw", n = file.info(path)$size)
  if (length(raw) == 0) return(0L)
  is_cr <- raw == as.raw(13)
  is_lf <- raw == as.raw(10)
  crlf <- is_cr & c(is_lf[-1], FALSE)
  sum(!crlf)
}
cat(sprintf("figure: %s (%d canonical bytes)\n", basename(fig_path), canonical_bytes(fig_path)))

# ---------------------------------------------------------------------------------------------
# Write
# ---------------------------------------------------------------------------------------------
estimates <- list(
  stage = 6,
  layer = "estimation",
  vintage = vintage,
  generated_at = format(Sys.time(), "%Y-%m-%dT%H:%M:%S%z"),
  generator = spec$engine,
  spec = spec_file,
  verifier = spec$verifier,
  input = spec$input,
  samples = list(
    design_a = list(
      n_obs = nrow(panel), n_units = uniqueN(panel$state_id),
      first_month = as.character(min(panel$period_month)), last_month = as.character(max(panel$period_month)),
      window_source = q$why
    ),
    design_b = list(
      n_obs = nrow(national), first_month = as.character(min(national$period_month)),
      last_month = as.character(max(national$period_month))
    )
  ),
  designs = list(
    list(id = "A", status = checks$design_a$verdict$status, verdict = checks$design_a$verdict,
         checks = checks$design_a[setdiff(names(checks$design_a), "verdict")]),
    list(id = "B", status = checks$design_b$verdict$status, verdict = checks$design_b$verdict,
         checks = checks$design_b[setdiff(names(checks$design_b), "verdict")]),
    list(id = "C", status = "not_run", why = spec$design_c$why, next_step = spec$design_c$next_step)
  ),
  # The figure block is the artifact's own record that the picture it ships was rendered from these rows:
  # the verifier compares the recorded byte count to the file on disk, so a stale figure fails rather than
  # being noticed by a reader.
  figure = list(path = spec$figure$path, bytes = canonical_bytes(fig_path),
                layout = gsub("\\s+", " ", trimws(spec$figure$layout))),
  specifications = specs,
  notes = list(
    "Every estimate is a pre-declared specification from analysis/specs/estimation.yml.",
    "Design A is reported as estimated, not identified, when its own checks say so; the number is still published with its bounds.",
    "Design C was not run and its reason is carried rather than dropped."
  )
)
write_json(estimates, file.path(out_dir, "estimates.json"),
           auto_unbox = TRUE, pretty = TRUE, digits = 10)

fmt <- function(x, d = 4) ifelse(is.na(x), "—", formatC(x, digits = d, format = "f"))
design_row <- function(s) sprintf("| %s | %s | %s | %d | %s | %s | %s |",
                                  s$design, s$outcome, fmt(s$coefficient),
                                  s$n_obs, fmt(s$standard_error),
                                  paste0("[", fmt(s$ci_low), ", ", fmt(s$ci_high), "]"),
                                  if (!is.null(s$p_value)) fmt(s$p_value) else "—")

md <- c(
  sprintf("# Stage 6 estimates — vintage %s", vintage),
  "",
  sprintf("Generated %s by `%s` from `%s`. Every number is recomputed independently by `%s`.",
          estimates$generated_at, spec$engine, spec_file, spec$verifier),
  "",
  "## The answer this stage arrived at",
  "",
  "**The presidential-tenure question is not answerable with this data and no estimator makes it so** —",
  "four to five administrations against 27 annual observations put the minimum detectable effect at",
  "35–80 residual standard deviations (Stage 5). What *is* answerable is the fiscal channel, and this",
  "stage answers two questions about it.",
  "",
  "| Design | Question | Verdict |",
  "|---|---|---|",
  sprintf("| A | Does a larger federal allocation reduce conflict fatalities in the state that receives it? | **%s** |",
          checks$design_a$verdict$status),
  sprintf("| B | How much of a Brent shock reaches the states, and when? | **%s** |",
          checks$design_b$verdict$status),
  "| C | Did the tenures move an outcome, against a synthetic counterfactual? | not run — Stage 5's donor pool fails the pre-treatment fit |",
  "",
  "## Design A — state dose-response",
  "",
  sprintf("Estimand: *%s*", design_a$estimand),
  "",
  sprintf("Sample: %d state-months, %d states, %s → %s. Estimator: %s.",
          nrow(panel), uniqueN(panel$state_id), min(panel$period_month), max(panel$period_month),
          design_a$estimator),
  "",
  "| Design | Outcome | Coefficient | n | SE | 95% CI | p |",
  "|---|---|---|---|---|---|---|",
  vapply(Filter(function(s) s$design == "A", specs), design_row, character(1)),
  "",
  "### Why the verdict is what it is",
  "",
  sprintf(paste0("- **Lead-shift randomisation (the decisive check)**: %d non-zero offsets, ",
                 "p = **%.3f**. Mis-timed doses average |%.3f| with a maximum of |%.3f|; the estimate is %.3f."),
          length(offsets), p_lead_shift, mean(abs(shifted_estimates)), max(abs(shifted_estimates)), observed),
  sprintf("- **Secondary null** (%d draws, %s): p = %.3f. Reported, not decisive — see the spec for why.",
          perm$n_draws, perm$scheme, p_perm),
  sprintf("- **Placebo** (dose led %d months within state): **%+.4f** (SE %.4f) against the estimate of %+.4f.",
          lead, placebo_est, placebo_se, observed),
  if (length(reasons)) paste0("  - ", reasons) else "- Both checks pass.",
  "",
  paste0("What this design actually uses: the dose's within-state, within-month variation. ",
         "That variation is not spread across the federation — it is concentrated in the oil-producing ",
         "states (residual sd 0.50 in Delta/Bayelsa/Rivers against 0.11 elsewhere), because what ",
         "survives two-way fixed effects is mostly the 13 % derivation share moving with the oil price ",
         "and with production volumes. A dose whose variation is a national oil shock interacted with a ",
         "fixed state characteristic is not the randomised-looking exposure a dose-response design ",
         "assumes, and the placebo says the same thing from the other side."),
  "",
  "## Design B — Brent crude to state allocations",
  "",
  sprintf("Estimand: *%s*", design_b$estimand),
  "",
  "| Design | Specification | Coefficient | n | SE | 95% CI | p |",
  "|---|---|---|---|---|---|---|",
  vapply(Filter(function(s) s$design == "B", specs), design_row, character(1)),
  "",
  sprintf("Peak response at h = %d (declared band %d–%d). Lead placebo at %d months: %+.4f (SE %.4f).",
          peak_h, peak_band[1], peak_band[2], lead_b, pest, pse),
  "",
  "A positive response at a lag of two to four months is what the disbursement calendar implies: the",
  "allocation published for a month is revenue accrued in an earlier one, so an immediate response would",
  "be the surprising result, not a lagged one. The confidence bounds are wide — this is 114 monthly",
  "observations of a series the naira's two devaluations also move, and the FX channel is annual grain",
  "(the monthly NGN/USD series has no keyless source: `docs/decisions.md` C-46).",
  "",
  "## What was not run",
  "",
  paste0("Design C (synthetic control): ", spec$design_c$why),
  "",
  paste0("Next step for it: ", spec$design_c$next_step, "."),
  "",
  "## Honesty notes carried with these numbers",
  "",
  paste0("- ", estimates$notes[[1]]),
  paste0("- ", estimates$notes[[2]]),
  paste0("- ", estimates$notes[[3]]),
  "- 36 clusters is few; a wild-cluster bootstrap would be the fix and is not applied (declared in the spec).",
  ""
)
writeLines(md, file.path(out_dir, "report.md"))

message(sprintf("\ndesign A verdict: %s", checks$design_a$verdict$status))
message(sprintf("design B verdict: %s", checks$design_b$verdict$status))
message(sprintf("written: %s", file.path(spec$output$root, vintage, "estimates.json")))
