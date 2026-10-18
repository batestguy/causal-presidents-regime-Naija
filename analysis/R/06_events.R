#!/usr/bin/env Rscript
# Stage 8b — comparing tenures, part 1: what changed inside a tenure.
#
# The question people ask is "which tenure did better?". Stage 5 answered the version that needs a
# counterfactual (not identifiable: four to five administrations against 21-23 annual points) and the
# synthetic control that would have supplied one fails its pre-fit gate. This engine asks the version the
# data can carry, for the only domain with monthly coverage: **did monthly conflict move after each
# transition, relative to that series' own path just before it?**
#
# It is a timing statement, not a party effect, and the design makes that hard to blur:
#
#   * Every estimate is per event. There is no pooled "tenure effect" and no average of the four.
#   * Inference is by **exhaustive placebo assignment** — every eligible month in the series is tried as if
#     it were the transition — because four events is four events and a t-statistic would pretend otherwise.
#     The placebo set is enumerated, never sampled, so the engine and the verifier agree without a seed.
#   * Two checks decide whether an estimate means anything, and both are published even when they fail: a
#     **pre-trend placebo** (the same statistic 24 months earlier) and a **reporting-divergence** comparison
#     between the two count series the archive carries.
#   * The party split is a description with its n printed. No test statistic is computed, because two events
#     against two events has no sampling distribution, and the verifier fails if one appears.

suppressPackageStartupMessages({
  library(data.table)
  library(duckdb)
  library(jsonlite)
  library(yaml)
  library(sandwich)
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

`%||%` <- function(a, b) if (is.null(a)) b else a
stop_if <- function(condition, ...) if (isTRUE(condition)) stop(sprintf(...), call. = FALSE)
fmt <- function(x, digits = 4) if (length(x) == 0 || is.na(x)) "—" else formatC(x, format = "f", digits = digits)

root <- find_root()
spec_file <- "analysis/specs/events.yml"
spec <- read_yaml(file.path(root, spec_file))

vintage <- as.character(spec$labelled)
out_dir <- file.path(root, "registry", "events", vintage)
dir.create(out_dir, showWarnings = FALSE, recursive = TRUE)

pre_months <- as.integer(spec$windows$pre_months)
horizons <- as.integer(unlist(spec$windows$focus_horizons))
min_post_fraction <- as.numeric(spec$windows$min_post_fraction)
# The floor is per horizon: 75 % of 12 is 9 months, of 24 is 18. A single month count would either admit
# a four-month "h = 24" estimate or reject Tinubu's 20-month window out of 24.
min_post_by_horizon <- vapply(horizons, function(h) as.integer(ceiling(min_post_fraction * h)), integer(1))
names(min_post_by_horizon) <- as.character(horizons)
min_post_longest <- min_post_by_horizon[[as.character(max(horizons))]]
outcomes <- as.character(unlist(spec$series$outcomes))
variants <- names(spec$statistic$controls_variants)
baseline <- variants[[1]]
hac_lags <- as.integer(spec$statistic$hac_lags %||% 12L)
mde_z <- 1.959964 + 0.8416212
CI_Z <- 1.959964

# ---------------------------------------------------------------------------------------------
# The series, built to the declared blank-month rule
# ---------------------------------------------------------------------------------------------
con <- dbConnect(duckdb::duckdb(), dbdir = file.path(root, spec$input$database), read_only = TRUE)
on.exit(dbDisconnect(con, shutdown = TRUE), add = TRUE)

start_month <- as.Date(paste0(spec$series$start_month, "-01"))
end_month <- as.Date(paste0(spec$series$end_month, "-01"))

conflict <- dbGetQuery(con, sprintf(
  "select period_month, fatalities, incidents from %s where period_month between date '%s' and date '%s'",
  spec$input$national_conflict_table, start_month, end_month))
oil <- dbGetQuery(con, sprintf(
  "select period_month, value as oil from %s where metric_id = '%s' and period_month between date '%s' and date '%s'",
  spec$input$fact_metric_table, spec$input$oil_metric_id, start_month, end_month))

series <- data.table(period_month = seq(start_month, end_month, by = "month"))
series <- merge(series, as.data.table(conflict), by = "period_month", all.x = TRUE)
series <- merge(series, as.data.table(oil), by = "period_month", all.x = TRUE)
series[, period_month := as.Date(period_month)]
series[, oil := as.numeric(oil)]

filled <- series[is.na(fatalities), .N]
filled_by_year <- series[is.na(fatalities), .N, by = .(year = as.integer(format(period_month, "%Y")))][order(year)]
series[is.na(fatalities), fatalities := 0L]
series[is.na(incidents), incidents := 0L]

stop_if(series[is.na(oil), .N] > 0L, "%d month(s) in the window carry no Brent quote",
        series[is.na(oil), .N])

series[, log_oil := log(oil)]
series[, month_of_year := factor(format(period_month, "%m"))]
series[, trend := 12L * (as.integer(format(period_month, "%Y")) - as.integer(format(start_month, "%Y"))) +
         (as.integer(format(period_month, "%m")) - as.integer(format(start_month, "%m")))]
setorder(series, period_month)

month_of_date <- function(d) as.Date(format(as.Date(d), "%Y-%m-01"))
event_months <- month_of_date(vapply(spec$events, function(e) as.character(e$date), character(1)))
event_row <- function(i) which(series$period_month == event_months[[i]])[[1]]
next_transition_row <- function(i) {
  later <- event_months[event_months > event_months[[i]]]
  if (!length(later)) nrow(series) else which(series$period_month == min(later))[[1]] - 1L
}

# ---------------------------------------------------------------------------------------------
# The statistic — one path, used by every fit in this script
# ---------------------------------------------------------------------------------------------
# Poisson ML on the count with month-of-year fixed effects and a (declared) linear trend, and a Newey-West
# covariance. `post` is the only coefficient reported: exp(beta) - 1 is the proportional monthly shift.
fit <- function(rows, post_from, outcome, variant) {
  d <- copy(series[rows])
  d[, post := 0L]
  d[which(rows %in% post_from), post := 1L]
  formula_text <- if (identical(variant, "seasonality_trend_oil"))
    sprintf("%s ~ post + month_of_year + trend + log_oil", outcome) else
    sprintf("%s ~ post + month_of_year + trend", outcome)
  m <- glm(as.formula(formula_text), data = d, family = poisson())
  v <- sandwich::NeweyWest(m, lag = hac_lags, prewhite = FALSE)
  beta <- unname(coef(m)["post"])
  se <- sqrt(unname(v["post", "post"]))
  list(beta = beta, se = se, proportional = exp(beta) - 1,
       ci_low = exp(beta - CI_Z * se) - 1, ci_high = exp(beta + CI_Z * se) - 1,
       mde_proportional = exp(mde_z * se) - 1,
       n_pre = sum(d$post == 0L), n_post = sum(d$post == 1L), n_parameters = length(coef(m)))
}

# ---------------------------------------------------------------------------------------------
# Real events: every declared event x horizon x outcome x control variant
# ---------------------------------------------------------------------------------------------
rows <- list()
skips <- list()
for (i in seq_along(spec$events)) {
  e <- spec$events[[i]]
  t0 <- event_row(i)
  stop_if(t0 - 1L < pre_months,
          "%s: %d pre-month(s) available, the design needs %d", as.character(e$id), t0 - 1L, pre_months)
  for (h in horizons) {
    post_to <- min(t0 + as.integer(h) - 1L, next_transition_row(i), nrow(series))
    post_rows <- t0:post_to
    min_post <- min_post_by_horizon[[as.character(h)]]
    if (length(post_rows) < min_post) {
      # Declared, not silently dropped: the cell is missing because the successor arrived, and the
      # artifact says so with the months it had.
      skips[[length(skips) + 1L]] <- list(
        event = as.character(e$id), horizon = as.integer(h), post_months_available = length(post_rows),
        post_months_required = min_post,
        why = sprintf("the next transition arrives %d month(s) after this one; h = %d needs %d of its months",
                      length(post_rows), as.integer(h), min_post))
      next
    }
    pre_rows <- (t0 - pre_months):(t0 - 1L)
    for (outcome in outcomes) {
      for (variant in variants) {
        f <- fit(c(pre_rows, post_rows), post_rows, outcome, variant)
        rows[[length(rows) + 1L]] <- c(
          list(event = as.character(e$id), date = as.character(e$date), label = as.character(e$label),
               tenure_stratum = as.character(e$tenure_stratum), horizon = as.integer(h),
               outcome = outcome, variant = variant,
               pre_months = length(pre_rows), post_months = length(post_rows),
               window_start = as.character(series$period_month[pre_rows[[1]]]),
               window_end = as.character(series$period_month[post_to]),
               truncated_by_next_transition = post_to < t0 + as.integer(h) - 1L),
          f)
      }
    }
  }
}
cat(sprintf("series: %d months %s -> %s, %d blank month(s) filled with zero\n", nrow(series),
            format(start_month, "%Y-%m"), format(end_month, "%Y-%m"), filled))
by_horizon <- vapply(horizons, function(h) sum(vapply(rows, function(r) r$horizon == h, logical(1))), integer(1))
cat(sprintf("events: %d | specifications fitted: %d (%s) | declared skips: %d\n", length(spec$events),
            length(rows), paste(sprintf("h=%d: %d", horizons, by_horizon), collapse = ", "), length(skips)))
stop_if(any(by_horizon == 0L),
        "a declared horizon was fitted for no event (%s): the spec asks for a window this sample cannot carry",
        paste(horizons[by_horizon == 0L], collapse = ", "))

# ---------------------------------------------------------------------------------------------
# Pre-trend placebo: the same statistic with the post window 24 months before the real transition
# ---------------------------------------------------------------------------------------------
pretrend <- list()
pretrend_unavailable <- list()
for (i in seq_along(spec$events)) {
  e <- spec$events[[i]]
  t0 <- event_row(i)
  pseudo_post <- (t0 - 24L):(t0 - 1L)
  pre_from <- pseudo_post[[1]] - pre_months
  if (pre_from < 1L) {
    pretrend_unavailable[[length(pretrend_unavailable) + 1L]] <- list(
      event = as.character(e$id), months_available = t0 - 1L, months_required = pre_months + 24L,
      why = sprintf("the check needs %d months before the transition; the series has %d before this one",
                    pre_months + 24L, t0 - 1L))
    next
  }
  pre_rows <- pre_from:(pseudo_post[[1]] - 1L)
  for (outcome in outcomes) {
    f <- fit(c(pre_rows, pseudo_post), pseudo_post, outcome, baseline)
    pretrend[[length(pretrend) + 1L]] <- list(
      event = as.character(e$id), outcome = outcome, variant = baseline,
      window_start = as.character(series$period_month[pre_rows[[1]]]),
      window_end = as.character(series$period_month[pseudo_post[[length(pseudo_post)]]]),
      pre_months = length(pre_rows), post_months = length(pseudo_post),
      proportional = f$proportional, se = f$se)
  }
}

# ---------------------------------------------------------------------------------------------
# Exhaustive placebo assignment
# ---------------------------------------------------------------------------------------------
buffer <- as.integer(spec$inference$buffer_months)
excluded <- rep(FALSE, nrow(series))
for (t0 in vapply(seq_along(spec$events), event_row, integer(1))) {
  excluded[max(1L, t0 - buffer):min(nrow(series), t0 + buffer)] <- TRUE
}
eligible <- which(!excluded & seq_len(nrow(series)) > pre_months &
                    seq_len(nrow(series)) <= nrow(series) - min_post_longest)
stop_if(!length(eligible), "no eligible placebo month; the declared windows leave nothing to try")

placebo <- list()
for (outcome in outcomes) {
  for (h in horizons) {
    betas <- vapply(eligible, function(t0) {
      post_rows <- t0:min(t0 + as.integer(h) - 1L, nrow(series))
      fit(c((t0 - pre_months):(t0 - 1L), post_rows), post_rows, outcome, baseline)$beta
    }, numeric(1))
    placebo[[length(placebo) + 1L]] <- list(
      outcome = outcome, horizon = as.integer(h), variant = baseline, n = length(betas),
      mean_beta = mean(betas), sd_beta = sd(betas),
      quantiles = as.list(unname(quantile(betas, c(0.05, 0.5, 0.9, 0.95, 0.99)))),
      abs_quantiles = as.list(unname(quantile(abs(betas), c(0.5, 0.9, 0.95, 0.99)))),
      betas = betas)
  }
}
placebo_dist <- function(outcome, h) {
  Filter(function(p) identical(p$outcome, outcome) && identical(p$horizon, as.integer(h)), placebo)[[1]]$betas
}
# One definition of the p-value, used by the per-event rows and by the family-wise maximum.
tail_p <- function(dist, beta) {
  if (beta > 0) (1 + sum(dist >= beta)) / (length(dist) + 1) else
    (1 + sum(dist <= beta)) / (length(dist) + 1)
}
cat(sprintf("placebo: %d eligible month(s) per outcome/horizon, enumerated (no RNG)\n", length(eligible)))

for (k in seq_along(rows)) {
  r <- rows[[k]]
  if (!identical(r$variant, baseline)) next
  dist <- placebo_dist(r$outcome, r$horizon)
  # Add-one randomisation p-value, in the tail the estimate points at: (1 + #{placebo at least as extreme on
  # that side}) / (n + 1). Reporting the raw share would print 0.000 whenever the event beats every placebo
  # month, which overstates the resolution: with 58 placebo months the smallest attainable p is 1/59.
  rows[[k]]$placebo_p <- tail_p(dist, r$beta)
  rows[[k]]$placebo_tail <- if (r$beta > 0) "increase" else "decrease"
  rows[[k]]$placebo_n <- length(dist)
  rows[[k]]$in_placebo_95 <- if (r$beta > 0) r$beta >= unname(quantile(dist, 0.95)) else
    r$beta <= unname(quantile(dist, 0.05))
}

family_wise <- list()
for (outcome in outcomes) {
  for (h in horizons) {
    obs <- Filter(function(r) identical(r$outcome, outcome) && r$horizon == as.integer(h) &&
                    identical(r$variant, baseline), rows)
    largest <- obs[[which.max(vapply(obs, function(r) abs(r$beta), numeric(1)))]]
    dist <- placebo_dist(outcome, h)
    family_wise[[length(family_wise) + 1L]] <- list(
      outcome = outcome, horizon = as.integer(h), largest_event = largest$event,
      largest_beta = largest$beta, largest_proportional = largest$proportional,
      p = tail_p(dist, largest$beta), n_placebo = length(dist),
      direction = if (largest$beta > 0) "increase" else "decrease")
  }
}

# ---------------------------------------------------------------------------------------------
# Verdicts and the two checks
# ---------------------------------------------------------------------------------------------
verdict_of <- function(event_id, outcome) {
  post <- Filter(function(r) identical(r$event, event_id) && identical(r$outcome, outcome) &&
                   r$horizon == 12L && identical(r$variant, baseline), rows)
  pre <- Filter(function(r) identical(r$event, event_id) && identical(r$outcome, outcome), pretrend)
  if (!length(post))
    return(list(status = "not_estimated", why = "no h=12 specification for this event", place = NA_real_,
                pre_trend = NA_real_, placebo_p = NA_real_))
  post <- post[[1]]
  pre_mag <- if (length(pre)) abs(pre[[1]]$proportional) else NA_real_
  post_mag <- abs(post$proportional)
  # A pre-trend check that could not be run is reported as unavailable. Collapsing it into "no shift"
  # would record a missing check as a null result, which is the failure mode this project exists to avoid.
  status <- if (is.na(pre_mag)) "check_not_available" else if
    (!is.na(post$placebo_p) && post$placebo_p <= 0.05 && pre_mag < post_mag) "shift_detected" else if
      (pre_mag >= post_mag) "not_interpretable_pre_trend" else "no_shift_detected"
  list(status = status, place = post$proportional, pre_trend = pre_mag,
       placebo_p = post$placebo_p,
       why = if (is.na(pre_mag))
         sprintf("the pre-trend placebo needs %d months before the transition; %d are available",
                 pre_months + 24L, event_row(which(vapply(spec$events, function(x) identical(as.character(x$id), event_id), logical(1)))[[1]]) - 1L)
       else NA_character_)
}

verdicts <- list()
for (e in spec$events) for (outcome in outcomes)
  verdicts[[length(verdicts) + 1L]] <- c(list(event = as.character(e$id), outcome = outcome),
                                         verdict_of(as.character(e$id), outcome))
for (k in seq_along(rows)) {
  r <- rows[[k]]
  if (r$horizon != 12L || !identical(r$variant, baseline)) next
  v <- Filter(function(x) identical(x$event, r$event) && identical(x$outcome, r$outcome), verdicts)[[1]]
  rows[[k]]$verdict <- v$status
}

divergence <- Filter(Negate(is.null), lapply(spec$events, function(e) {
  pick <- function(outcome) Filter(function(r) identical(r$event, as.character(e$id)) &&
                                     identical(r$outcome, outcome) && r$horizon == 12L &&
                                     identical(r$variant, baseline), rows)
  a <- pick("fatalities"); b <- pick("incidents")
  if (!length(a) || !length(b)) return(NULL)
  list(event = as.character(e$id), fatalities = a[[1]]$proportional, incidents = b[[1]]$proportional,
       signs_agree = sign(a[[1]]$proportional) == sign(b[[1]]$proportional))
}))

party_events <- rbindlist(lapply(spec$events, function(e) {
  v <- Filter(function(x) identical(x$event, as.character(e$id)) && identical(x$outcome, "fatalities"),
              verdicts)[[1]]
  data.table(event = as.character(e$id), tenure_stratum = as.character(e$tenure_stratum),
             party = sub("_.*$", "", as.character(e$tenure_stratum)),
             shift_fatalities_h12 = v$place, placebo_p = v$placebo_p, verdict = v$status)
}))
party_by_group <- lapply(split(party_events, party_events$party), function(d) list(
  party = d$party[[1]], n_events = nrow(d), median_shift_h12 = median(d$shift_fatalities_h12),
  shifts = as.list(d$shift_fatalities_h12)))
no_test_computed <- TRUE

# ---------------------------------------------------------------------------------------------
# Figure
# ---------------------------------------------------------------------------------------------
svg_path <- file.path(out_dir, "event_study.svg")
svg(svg_path, width = 11, height = 7.5)
par(mfrow = c(2, 1), mar = c(4, 4.5, 2.8, 1))
plot(series$period_month, series$fatalities, type = "h", col = "grey35", xlab = "month",
     ylab = "reported fatalities",
     main = sprintf("Nigeria, monthly reported conflict fatalities (UCDP GED) with the %d transitions",
                    length(spec$events)))
for (t0 in vapply(seq_along(spec$events), event_row, integer(1)))
  abline(v = series$period_month[t0], col = "#b2182b", lwd = 1.6, lty = 2)
legend("topright", legend = c("monthly count", "transition"), col = c("grey35", "#b2182b"),
       lty = c(1, 2), lwd = c(1, 1.6), bty = "n", cex = 0.8)

h12 <- Filter(function(r) r$horizon == 12L && identical(r$variant, baseline) &&
                identical(r$outcome, "fatalities"), rows)
ord <- order(vapply(h12, function(r) r$proportional, numeric(1)))
est <- vapply(h12, function(r) r$proportional, numeric(1))[ord]
lo <- vapply(h12, function(r) r$ci_low, numeric(1))[ord]
hi <- vapply(h12, function(r) r$ci_high, numeric(1))[ord]
labs <- vapply(h12, function(r) sprintf("%s\n(%s)", r$label, r$tenure_stratum), character(1))[ord]
plot(seq_along(est), est, xaxt = "n", xlim = c(0.5, length(est) + 0.5), pch = 19, ylim = range(c(lo, hi, 0)),
     xlab = "", ylab = "proportional shift, h = 12",
     main = "Per-transition shift in monthly fatalities, against the placebo distribution")
segments(seq_along(est), lo, seq_along(est), hi, lwd = 2)
abline(h = 0, col = "grey50")
dist <- placebo_dist("fatalities", 12L)
# Both tails are drawn, because the p-value is a same-side tail and the null is not centred on zero.
abline(h = exp(unname(quantile(dist, 0.95))) - 1, col = "#2166ac", lty = 3)
abline(h = exp(unname(quantile(dist, 0.05))) - 1, col = "#2166ac", lty = 3)
axis(1, at = seq_along(est), labels = labs, cex.axis = 0.8)
legend("topleft", legend = c("95 % CI", "placebo 5th / 95th percentile"), col = c("black", "#2166ac"),
       lty = c(1, 3), bty = "n", cex = 0.8)
invisible(dev.off())
cat(sprintf("figure: %s (%d bytes)\n", basename(svg_path), file.info(svg_path)$size))

# ---------------------------------------------------------------------------------------------
# Write
# ---------------------------------------------------------------------------------------------
document <- list(
  stage = "8b",
  layer = "events (within-tenure timing)",
  vintage = vintage,
  generated_at = format(Sys.time(), "%Y-%m-%dT%H:%M:%S%z"),
  generator = "analysis/R/06_events.R",
  spec = spec_file,
  verifier = "tests/verify_events.py",
  input = spec$input,
  series = list(
    start_month = as.character(spec$series$start_month), end_month = as.character(spec$series$end_month),
    outcomes = outcomes, n_months = nrow(series), months_filled_with_zero = filled,
    filled_by_year = unname(lapply(seq_len(nrow(filled_by_year)), function(i)
      list(year = filled_by_year$year[[i]], months = filled_by_year$N[[i]]))),
    blank_months_rule = as.character(spec$series$blank_months_rule)),
  windows = list(pre_months = pre_months, focus_horizons = horizons,
                 min_post_fraction = min_post_fraction,
                 min_post_months_by_horizon = as.list(min_post_by_horizon),
                 min_post_rule = as.character(spec$windows$min_post_rule),
                 post_end_rule = as.character(spec$windows$post_end_rule),
                 skips = unname(skips)),
  events = unname(lapply(seq_along(spec$events), function(i) {
    e <- spec$events[[i]]
    t0 <- event_row(i)
    list(id = as.character(e$id), date = as.character(e$date), label = as.character(e$label),
         tenure_stratum = as.character(e$tenure_stratum), term_id = as.integer(e$term_id),
         note = if (is.null(e$note)) NA else as.character(e$note),
         transition_month = format(series$period_month[t0], "%Y-%m"),
         pre_months_available = t0 - 1L,
         post_window_end = format(series$period_month[next_transition_row(i)], "%Y-%m"),
         truncated_by_next_transition = next_transition_row(i) < t0 + max(horizons) - 1L,
         place_in_series = list(from = format(series$period_month[[1]], "%Y-%m"),
                                to = format(series$period_month[[nrow(series)]], "%Y-%m")))
  })),
  excluded = unname(lapply(spec$excluded, function(x) list(id = as.character(x$id),
                                                          date = as.character(x$date),
                                                          why = as.character(x$why)))),
  placebo = list(
    rule = as.character(spec$inference$rule),
    direction = as.character(spec$inference$direction),
    direction_why = as.character(spec$inference$direction_why),
    p_definition = "(1 + #{placebo at least as extreme as the observed shift, on the side the shift points at}) / (n + 1)",
    eligible_months_rule = as.character(spec$inference$eligible_months),
    exclusion_buffer_months = buffer, eligible_months = length(eligible),
    first_eligible = format(series$period_month[min(eligible)], "%Y-%m"),
    last_eligible = format(series$period_month[max(eligible)], "%Y-%m"),
    deterministic = TRUE,
    distributions = unname(lapply(placebo, function(p) list(
      outcome = p$outcome, horizon = p$horizon, n = p$n, mean_beta = p$mean_beta, sd_beta = p$sd_beta,
      quantiles = p$quantiles, abs_quantiles = p$abs_quantiles))),
    family_wise = unname(family_wise)),
  specifications = unname(rows),
  pre_trend_placebo = unname(pretrend),
  verdict_rule = as.character(spec$verdict_rule),
  verdicts = unname(verdicts),
  checks = list(
    pre_trend_placebo = as.character(spec$checks$pre_trend_placebo),
    pre_trend_unavailable = unname(pretrend_unavailable),
    reporting_divergence = as.character(spec$checks$reporting_divergence),
    mde = as.character(spec$checks$mde),
    divergence = unname(divergence)),
  party_split = list(
    rule = as.character(spec$party_split$rule), why = as.character(spec$party_split$why),
    no_test_computed = no_test_computed,
    events = unname(lapply(seq_len(nrow(party_events)), function(i) as.list(party_events[i]))),
    by_party = unname(party_by_group)),
  figure = list(path = "event_study.svg", bytes = unname(file.info(svg_path)$size),
                layout = "top: the monthly series with the transitions marked; bottom: the per-transition h=12 shift with its interval against the 5th and 95th percentiles of the placebo distribution"),
  not_claimed = as.character(unlist(spec$not_claimed))
)
writeLines(jsonlite::toJSON(document, auto_unbox = TRUE, pretty = TRUE, null = "null", na = "null",
                            digits = 10), file.path(out_dir, "events.json"), useBytes = TRUE)

# ---------------------------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------------------------
r12 <- Filter(function(r) r$horizon == 12L && identical(r$variant, baseline), rows)
md <- c(
  sprintf("# What changed inside a tenure — monthly conflict around %d transitions, vintage %s",
          length(spec$events), vintage),
  "",
  sprintf("Generated %s by `analysis/R/06_events.R` from `%s`. Every number is recomputed independently by `tests/verify_events.py`.",
          format(Sys.time(), "%Y-%m-%dT%H:%M:%S%z"), spec_file),
  "",
  "## What this stage is, and what it is not",
  "",
  sprintf("**A timing comparison, per transition, on the only monthly outcome in the base.** Each of the %d",
          length(spec$events)),
  sprintf("in-window civilian transitions is compared against its own path in the %d months before it, with",
          pre_months),
  "month-of-year fixed effects and a linear trend, and the post window truncated at the next transition so no",
  "month is counted twice.",
  "",
  "**Not a tenure effect, not a party effect, not a causal claim.** Four events is four events: there is no",
  "counterfactual here, and the party split below is a description with its n printed rather than a test.",
  "",
  "## The series",
  "",
  sprintf("- %d months, %s to %s. **%d month(s) absent from the archive were filled with zero** under the declared rule.",
          nrow(series), format(start_month, "%Y-%m"), format(end_month, "%Y-%m"), filled),
  sprintf("- The transition that cannot be compared: **%s** — %s", spec$excluded[[1]]$id,
          gsub("\\s+", " ", as.character(spec$excluded[[1]]$why))),
  "",
  "## The estimates",
  "",
  "| Transition | Outcome | h | shift | SE | 95 % CI | placebo p | variant | verdict |",
  "|---|---|---|---|---|---|---|---|---|",
  vapply(rows, function(r) sprintf("| %s | %s | %d | %s | %s | [%s, %s] | %s | %s | %s |",
                                   r$label, r$outcome, r$horizon, fmt(r$proportional), fmt(r$se),
                                   fmt(r$ci_low), fmt(r$ci_high),
                                   if (is.na(r$placebo_p %||% NA_real_)) "—" else fmt(r$placebo_p, 3),
                                   r$variant, r$verdict %||% "—"), character(1)),
  "",
  "## Inference: exhaustive placebo assignment",
  "",
  sprintf("%d eligible months were each tried as if they were the transition (the declared rule excludes months",
          length(eligible)),
  sprintf("within %d months of a real one). The set is enumerated, not sampled, so there is no seed.", buffer),
  "",
  sprintf("The p-value is the tail in the direction of the estimate: `(1 + #{that tail}) / (n + 1)` over those %d",
          length(eligible)),
  "months, so its floor is 1/59, and a decline counts as evidence exactly as an increase does. The null is",
  "**not centred on zero** — the placebo distribution's mean is printed below — because reported fatalities",
  "drift down through the window; the p-value uses that empirical distribution as it is.",
  "",
  "| Outcome | h | placebo mean (log) | placebo SD | p05 | p50 | p95 | p99 |",
  "|---|---|---|---|---|---|---|---|",
  vapply(placebo, function(p) sprintf("| %s | %d | %s | %s | %s | %s | %s | %s |", p$outcome, p$horizon,
                                      fmt(p$mean_beta, 3), fmt(p$sd_beta, 3), fmt(p$quantiles[[1]], 3),
                                      fmt(p$quantiles[[2]], 3), fmt(p$quantiles[[4]], 3),
                                      fmt(p$quantiles[[5]], 3)), character(1)),
  "",
  "Family-wise — the largest of the four events against that distribution:",
  "",
  vapply(family_wise, function(f) sprintf("- **%s, h=%d**: largest of the four is %s, %s (log %s), p = %s over %d placebo months",
                                          f$outcome, f$horizon, f$largest_event, fmt(f$largest_proportional),
                                          fmt(f$largest_beta, 3), fmt(f$p, 3), f$n_placebo), character(1)),
  "",
  "## The checks that decide whether an estimate means anything",
  "",
  "### Pre-trend placebo",
  "",
  gsub("\\s+", " ", as.character(spec$checks$pre_trend_placebo)),
  "",
  "| Transition | Outcome | pre-window shift (h=12 equivalent) | post-window shift (h=12) | verdict |",
  "|---|---|---|---|---|",
  unname(unlist(lapply(outcomes, function(outcome) vapply(spec$events, function(e) {
    v <- Filter(function(x) identical(x$event, as.character(e$id)) && identical(x$outcome, outcome),
                verdicts)[[1]]
    sprintf("| %s | %s | %s | %s | %s |", e$label, outcome, fmt(v$pre_trend), fmt(v$place), v$status)
  }, character(1))))),
  "",
  if (length(pretrend_unavailable)) c(
    "Where the check could not be run, the artifact says so instead of scoring it as a pass:",
    "",
    vapply(pretrend_unavailable, function(u) sprintf("- **%s**: %s", u$event, u$why), character(1))) else
    c("- Every transition had enough history for the check."),
  "",
  "### Reporting divergence",
  "",
  gsub("\\s+", " ", as.character(spec$checks$reporting_divergence)),
  "",
  vapply(divergence, function(d) sprintf("- **%s**: fatalities %s, incidents %s — signs %s", d$event,
                                         fmt(d$fatalities), fmt(d$incidents),
                                         if (isTRUE(d$signs_agree)) "agree" else "**disagree**"),
         character(1)),
  "",
  "### Detectable effect",
  "",
  gsub("\\s+", " ", as.character(spec$checks$mde)),
  "",
  vapply(r12, function(r) sprintf("- %s / %s: MDE %s against an estimate of %s", r$label, r$outcome,
                                  fmt(r$mde_proportional), fmt(r$proportional)), character(1)),
  "",
  "## The party split, as description",
  "",
  gsub("\\s+", " ", as.character(spec$party_split$rule)),
  "",
  "| Party | events | median shift (fatalities, h=12) | the shifts |",
  "|---|---|---|---|",
  vapply(party_by_group, function(p) sprintf("| %s | %d | %s | %s |", p$party, p$n_events,
                                             fmt(p$median_shift_h12),
                                             paste(vapply(p$shifts, fmt, character(1)), collapse = ", ")),
         character(1)),
  "",
  sprintf("`no_test_computed = %s` — and the verifier fails if a test statistic appears on this artifact.",
          tolower(as.character(no_test_computed))),
  "",
  "## What this stage does not claim",
  "",
  vapply(as.character(unlist(spec$not_claimed)), function(x) sprintf("- %s", x), character(1)),
  "",
  "## Where the figure is",
  "",
  "`event_study.svg` — the monthly series with the four transitions marked, and the per-transition h=12 shift",
  "with its interval against the 5th and 95th percentiles of the placebo distribution (both are drawn: the",
  "p-value is a same-side tail and the null is not centred on zero)."
)
writeLines(md, file.path(out_dir, "report.md"), useBytes = TRUE)

cat("\nverdicts (h=12, baseline):\n")
for (v in verdicts)
  cat(sprintf("  %-14s %-12s %-26s post=%s pre=%s p=%s\n", v$event, v$outcome, v$status,
              fmt(v$place), fmt(v$pre_trend), fmt(v$placebo_p, 3)))
cat(sprintf("\nwritten: registry/events/%s/events.json + report.md + event_study.svg\n", vintage))
