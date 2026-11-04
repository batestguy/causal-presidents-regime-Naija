# P2 - Design C' comparison arms: SDID and generalized synthetic control
#
#   Rscript analysis/R/12_design_c_prime_arms.R <panel.csv> <windows.json> <out.json>
#
# Reads the panel the P1 extractor wrote and the windows P2 declared in
# analysis/specs/design_c_prime.yml (passed in as JSON by scripts/fit_design_c_prime.py, so a treatment year
# is never retyped in R). Fits synthdid::synthdid_estimate and gsynth::gsynth on the same window and the same
# balanced donor pool as the matrix-completion arm, and writes one JSON row per window and arm.
#
# Exploratory only: nothing here reads or writes registry/.
suppressPackageStartupMessages({
  library(jsonlite)
  library(synthdid)
  library(gsynth)
})

args <- commandArgs(trailingOnly = TRUE)
if (length(args) != 3) stop("usage: 12_design_c_prime_arms.R <panel.csv> <windows.json> <out.json>")
panel_path <- args[[1]]
windows_path <- args[[2]]
out_path <- args[[3]]

panel <- read.csv(panel_path, stringsAsFactors = FALSE)
windows <- fromJSON(windows_path, simplifyDataFrame = TRUE)

first_year <- min(panel$year)
results <- list()

for (i in seq_len(nrow(windows))) {
  w <- windows[i, ]
  start <- as.integer(w$first_year)
  end <- as.integer(w$last_year)
  d <- panel[panel$year >= first_year & panel$year <= end, ]

  wide <- tapply(d$value, list(d$year, d$country), function(v) v[1])
  complete <- colSums(is.na(wide)) == 0
  wide <- wide[, complete, drop = FALSE]
  row <- list(id = w$id, first_year = start, last_year = end,
              n_donors = sum(colnames(wide) != "NGA"),
              dropped_incomplete = sum(!complete))
  years <- as.integer(rownames(wide))
  T0 <- sum(years < start)
  row$pre_years <- T0
  row$post_years <- length(years) - T0

  if (!"NGA" %in% colnames(wide)) {
    row$status <- "refused"
    row$reason <- "treated unit incomplete in the window"
    results[[length(results) + 1]] <- row
    next
  }

  controls <- setdiff(colnames(wide), "NGA")
  Y <- t(wide)[c(controls, "NGA"), , drop = FALSE]
  N0 <- length(controls)

  # --- SDID ----------------------------------------------------------------------------------
  # The jackknife the package offers returns NA on this panel, and its placebo-variance fallback is not
  # reproducible: three runs of the same window gave 12.01, 12.09 and 14.58 under a fixed seed. So the
  # interval here is a leave-one-donor-out jackknife computed in this file, which is deterministic and
  # auditable, and the package's own variance is not used at all.
  row$sdid <- tryCatch({
    est <- synthdid_estimate(Y, N0, T0)
    loo <- vapply(controls, function(d) {
      keep <- c(setdiff(controls, d), "NGA")
      as.numeric(synthdid_estimate(Y[keep, , drop = FALSE], length(keep) - 1, T0))
    }, numeric(1))
    n <- length(loo)
    se <- sqrt((n - 1) / n * sum((loo - mean(loo))^2))
    list(status = "ok", gap = as.numeric(est), se = as.numeric(se),
         ci_low = as.numeric(est) - 1.96 * as.numeric(se),
         ci_high = as.numeric(est) + 1.96 * as.numeric(se),
         jackknife_range = c(min = min(loo), max = max(loo)),
         variance = "leave-one-donor-out jackknife, computed here")
  }, error = function(e) list(status = "refused", reason = conditionMessage(e)))

  # --- gsynth --------------------------------------------------------------------------------
  # gsynth's CV folds are unseeded, so the seed is fixed here: without it the selected rank (and the gap)
  # changed between runs of the same window, which is not a number anyone can audit.
  set.seed(20261104)
  df <- data.frame(country = rep(rownames(Y), times = ncol(Y)),
                   year = rep(years, each = nrow(Y)),
                   value = as.numeric(Y),
                   D = as.integer(rep(rownames(Y), times = ncol(Y)) == "NGA" &
                                    rep(years, each = nrow(Y)) >= start))
  row$gsynth <- tryCatch({
    fit <- suppressWarnings(suppressMessages(
      gsynth(value ~ D, data = df, index = c("country", "year"), force = "two-way",
             CV = TRUE, r = c(0, 5), se = FALSE)))
    # `att.avg` is not the post-period gap in gsynth 1.4.0 (it returned 113.8 on a window whose gap is
    # about -13), so the gap is computed here from the counterfactual matrix, whose column index is the
    # treated unit's position (`fit$tr`). The validity rule is the declared one: a counterfactual that is
    # non-physical (a negative rate) or beyond twice the window's largest observation is a divergence, and
    # the arm is reported as refused with the number that failed rather than averaged into anything.
    post <- which(years >= start)
    pre <- which(years < start)
    counterfactual <- as.numeric(fit$Y.ct[, fit$tr])
    observed <- as.numeric(Y["NGA", ])
    gap <- observed[post] - counterfactual[post]
    pre_rmse <- sqrt(mean((observed[pre] - counterfactual[pre])^2))
    ceiling <- 2 * max(observed, na.rm = TRUE)
    out_of_range <- any(!is.finite(counterfactual[post])) ||
      any(counterfactual[post] < 0) || any(counterfactual[post] > ceiling)
    poor_fit <- pre_rmse > 0.10 * stats::sd(observed[pre])
    why <- c(
      if (out_of_range) sprintf("counterfactual out of range (%s)",
                                paste(round(range(counterfactual[post]), 1), collapse = " to ")),
      if (poor_fit) sprintf("pre-fit rmse %.2f exceeds 10%% of the pre-period sd", pre_rmse))
    common <- list(pre_rmse = pre_rmse, r = as.numeric(fit$r.cv))
    if (out_of_range || poor_fit) {
      c(list(status = "refused", reason = paste(why, collapse = "; ")), common)
    } else {
      c(list(status = "ok", gap = mean(gap),
             variance = "none: no interval is computed for this arm, so none is implied"), common)
    }
  }, error = function(e) list(status = "refused", reason = conditionMessage(e)))

  row$status <- "estimated"
  results[[length(results) + 1]] <- row
}

write_json(results, out_path, auto_unbox = TRUE, pretty = TRUE, digits = 10, na = "null")
for (r in results) {
  sdid <- if (identical(r$sdid$status, "ok")) sprintf("%+8.3f", r$sdid$gap) else " refused"
  gs <- if (identical(r$gsynth$status, "ok")) sprintf("%+8.3f", r$gsynth$gap) else " refused"
  cat(sprintf("  %-9s sdid %s  gsynth %s  donors %d\n", r$id, sdid, gs, r$n_donors))
}
