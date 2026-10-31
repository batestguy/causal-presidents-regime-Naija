#!/usr/bin/env Rscript
# 02_diagnostics.R — Stage 5: pre-analysis diagnostics and design validation.
#
# PHASES.md Stage 5 establishes what the data can support *before* anything is estimated. Its exit
# criterion is the point of the whole stage: every planned model has a stated identifying
# assumption and the specific diagnostic that supports it, and a model that fails its pre-check is
# dropped **here, on the record** — far cheaper than dropping it after its estimate looked
# inconvenient.
#
# This script runs the seven checks PHASES.md names, on the grain the data actually has:
#
#   1. integration order       ADF / KPSS / PP on every series (urca), on native observations
#   2. cointegration           Johansen on the Tier-3 system (vars::ca.jo), rank -> VECM or ARDL
#   3. shock-window visibility are the 2014-16, 2020 and 2023 windows visible, or assumed?
#   4. dose validation         does Family A's dose vary enough across states and time to identify?
#   5. pre-treatment fit       Family C's parallel-trends analogue: can the donors track Nigeria?
#   6. DoF and power           the detectable effect, computed BEFORE any estimate exists
#   7. collinearity            VIF on the Tier-3 design, including the dummies-vs-trend problem
#
# Everything it needs is a declared parameter in analysis/specs/diagnostics.yml — no magic numbers
# live here. The output is written to registry/diagnostics/<vintage>/ as a machine-readable JSON
# and a human-readable page, and is then embedded into the DAG cards by 01_build_dags.R so that a
# card carries the diagnostics for its own (outcome, design) pair.
#
# Usage:
#   Rscript analysis/R/02_diagnostics.R
#
# Writes:
#   registry/diagnostics/<vintage>/diagnostics.json
#   registry/diagnostics/<vintage>/report.md
#
# Then, to attach the diagnostics to the cards:
#   Rscript analysis/R/01_build_dags.R

# Wrapped in suppressWarnings as well as suppressPackageStartupMessages: the installed packages were
# built under a later R minor version and each emits a "built under" warning, which otherwise prints
# as a warning block before the script's own output and makes a clean run look unclean.
suppressWarnings(suppressPackageStartupMessages({
  library(yaml)
  library(jsonlite)
  library(DBI)
  library(duckdb)
  library(urca)
  library(vars)
  library(dynlm)
  library(Synth)
  library(quadprog)
}))

SCHEMA_VERSION <- "0.1.0"
GENERATOR <- "analysis/R/02_diagnostics.R"
STAGE <- 5

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
base_path <- file.path(root, "data", "analytics.duckdb")

if (!file.exists(base_path)) {
  stop(sprintf("no analytical base at %s — run `dbt build` first (PHASES.md Stage 4)", base_path))
}

spec <- read_yaml(file.path(spec_dir, "diagnostics.yml"))
outcomes <- read_yaml(file.path(spec_dir, "outcomes.yml"))$outcomes
designs <- read_yaml(file.path(spec_dir, "dag_designs.yml"))$designs
outcome_ids <- vapply(outcomes, function(o) o$id, character(1))

# The diagnostics describe a *data* vintage, so they are stamped with the vintage of the layer they
# read rather than with the date they happened to run — the same convention Stage 3 uses. That way
# a re-run on the same data cannot masquerade as new evidence.
quality_reports <- list.files(file.path(root, "registry", "quality"),
                              pattern = "^[0-9]{4}-[0-9]{2}-[0-9]{2}$",
                              full.names = TRUE)
if (length(quality_reports) == 0) {
  stop("no registry/quality/<vintage>/ — Stage 3 must run before Stage 5 (its gate findings travel ",
       "onto the design cards)")
}
quality_vintages <- sort(basename(quality_reports))
vintage <- quality_vintages[[length(quality_vintages)]]
quality_report_path <- file.path(root, "registry", "quality", vintage, "report.json")
quality_report <- fromJSON(quality_report_path, simplifyVector = FALSE)

generated_at <- format(Sys.time(), "%Y-%m-%dT%H:%M:%S%z")
git_sha <- tryCatch(
  suppressWarnings(system2("git", c("-C", shQuote(root), "rev-parse", "--short", "HEAD"),
                           stdout = TRUE, stderr = FALSE)),
  error = function(e) character(0)
)
git_sha <- if (length(git_sha) && nzchar(git_sha[[1]])) git_sha[[1]] else NA_character_

out_dir <- file.path(root, "registry", "diagnostics", vintage)
dir.create(out_dir, showWarnings = FALSE, recursive = TRUE)

con <- dbConnect(duckdb::duckdb(), dbdir = base_path, read_only = TRUE)
on.exit(dbDisconnect(con, shutdown = TRUE), add = TRUE)

q <- function(sql, params = NULL) {
  if (is.null(params)) dbGetQuery(con, sql) else dbGetQuery(con, sql, params = params)
}

# ------------------------------------------------------------------------------------------
# small helpers
# ------------------------------------------------------------------------------------------
spec_get <- function(path, default = NULL) {
  cur <- spec
  for (key in path) {
    if (!is.list(cur) || is.null(cur[[key]])) return(default)
    cur <- cur[[key]]
  }
  cur
}

round_or_na <- function(x, digits = 6) {
  if (is.null(x) || length(x) != 1 || is.na(x) || !is.finite(x)) return(NA)
  round(as.numeric(x), digits)
}

# A unit-root test verdict from a statistic and the 5% critical value. urca reports all three of
# the ADF/KPSS/PP objects as a statistic plus a table of critical values; the comparison direction
# depends on the test (see diagnostics.yml `unit_root`).
unit_root_test <- function(kind, x, alpha = 0.05, max_lags = 4) {
  cval_col <- sprintf("%.0fpct", alpha * 100)
  out <- list(kind = kind, n = length(x), teststat = NA, cval = NA, lags = NA,
              verdict = "not_run", note = NA_character_)
  tryCatch({
    if (identical(kind, "adf_drift")) {
      obj <- urca::ur.df(x, type = "drift", lags = max_lags, selectlags = "AIC")
    } else if (identical(kind, "adf_trend")) {
      obj <- urca::ur.df(x, type = "trend", lags = max_lags, selectlags = "AIC")
    } else if (identical(kind, "kpss")) {
      obj <- urca::ur.kpss(x, type = "mu", lags = "short")
    } else if (identical(kind, "pp")) {
      obj <- urca::ur.pp(x, type = "Z-tau", model = "constant", lags = "short")
    } else {
      out$note <- sprintf("unknown test %s", kind)
      return(out)
    }
    stat <- as.numeric(obj@teststat)[1]
    cvals <- obj@cval
    cv <- if (is.matrix(cvals)) as.numeric(cvals[1, cval_col]) else as.numeric(cvals[[cval_col]])
    # ADF/PP: rejecting the unit root means the statistic falls BELOW the critical value.
    # KPSS: the null is stationarity, so rejecting means the statistic rises ABOVE it.
    rejects <- if (identical(kind, "kpss")) stat > cv else stat < cv
    # ur.df and ur.pp carry `lags`; ur.kpss carries `lag`.
    lag_used <- tryCatch(as.numeric(obj@lags)[1], error = function(e) NA_real_)
    if (is.na(lag_used)) lag_used <- tryCatch(as.numeric(obj@lag)[1], error = function(e) NA_real_)
    out$teststat <- round_or_na(stat)
    out$cval <- round_or_na(cv)
    out$lags <- round_or_na(lag_used, 0)
    out$verdict <- if (isTRUE(rejects)) "reject_null" else "fail_to_reject"
  }, error = function(e) {
    out$note <<- conditionMessage(e)
  })
  out
}

# The reconciliation rule declared in diagnostics.yml: all three tests must agree, at the level and
# again at the first difference. A series is only called I(2) when the first difference itself
# satisfies the same three-test unit-root rule, which keeps a level-regime break from being read as
# a second unit root.
says_unit_root <- function(adf, pp, kpss) {
  identical(adf$verdict, "fail_to_reject") && identical(pp$verdict, "fail_to_reject") &&
    identical(kpss$verdict, "reject_null")
}
says_stationary <- function(adf, pp, kpss) {
  identical(adf$verdict, "reject_null") && identical(pp$verdict, "reject_null") &&
    identical(kpss$verdict, "fail_to_reject")
}
classify_order <- function(l) {
  if (says_stationary(l$adf_drift, l$pp, l$kpss)) return(list(order = 0L, decisive = TRUE))
  if (says_unit_root(l$adf_drift, l$pp, l$kpss)) {
    if (says_stationary(l$adf_diff, l$pp_diff, l$kpss_diff)) return(list(order = 1L, decisive = TRUE))
    if (says_unit_root(l$adf_diff, l$pp_diff, l$kpss_diff)) return(list(order = 2L, decisive = TRUE))
  }
  list(order = 1L, decisive = FALSE,
       note = "the three tests did not agree at the level or at the first difference; carried as I(1) (the conservative branch in diagnostics.yml)")
}

# The synthetic-control weights that minimise the pre-treatment path error over the simplex. This is
# a quadratic program, so the solution is the global optimum — which matters, because the pre-fit
# gate has to be able to say "no convex combination of the donors can track Nigeria" rather than
# "this optimiser did not find one".
simplex_path_weights <- function(z1, Z0) {
  D <- crossprod(Z0)
  # A ridge is needed because the donors outnumber the pre-period years, so D is singular and
  # solve.QP requires a positive-definite matrix. It is scaled to D rather than fixed: at 1e-10 on a
  # series measured in the hundreds (u5mr), the smallest eigenvalue is still negative from rounding
  # and the QP refuses outright — which is how this was found. The ridge is negligible beside the
  # data (1e-8 of the largest diagonal), so it cannot move the optimum.
  ridge <- max(diag(D)) * 1e-8
  quadprog::solve.QP(Dmat = D + diag(ridge, ncol(D)), dvec = crossprod(Z0, z1),
                     Amat = cbind(1, diag(ncol(D))), bvec = c(1, rep(0, ncol(D))),
                     meq = 1)$solution
}
rmspe <- function(z1, Z0, w) sqrt(mean((z1 - as.numeric(Z0 %*% w))^2))

vif_of <- function(X) {
  # Variance inflation per predictor, computed directly rather than with a package so the number is
  # checkable by hand: VIF_j = 1 / (1 - R2_j) from regressing column j on the others.
  #
  # The constant column is skipped. Its total sum of squares is zero, so the R2 of regressing it on
  # the others is not defined, and because the other columns can reproduce a constant essentially
  # exactly the regression returns a meaningless ratio and a warning (found by running it: the
  # intercept regression had rss = 3.6e-30). VIF is a property of predictors, not of the intercept.
  p <- ncol(X)
  out <- rep(NA_real_, p)
  for (j in seq_len(p)) {
    y <- X[, j]
    if (stats::sd(y) == 0) next
    others <- X[, -j, drop = FALSE]
    fit <- tryCatch(lm(y ~ others), error = function(e) NULL)
    r2 <- if (is.null(fit)) NA_real_ else summary(fit)$r.squared
    out[j] <- if (is.na(r2)) NA_real_ else 1 / max(1e-12, 1 - r2)
  }
  names(out) <- colnames(X)
  out
}

# ------------------------------------------------------------------------------------------
# input series — always the NATIVE grain (diagnostics.yml `grain`)
# ------------------------------------------------------------------------------------------
annual_series <- function(metric_id) {
  # Non-null native annual observations, joined to the administration spine so the same frame can
  # serve the tests and the design matrix. The join is on the anchor month, so the tenure strata
  # come from the base rather than being re-derived here.
  q("
    select year(n.anchor_month) as yr,
           n.value                as value,
           f.pdp_first, f.pdp_second, f.apc_first, f.apc_second,
           f.president, f.party, f.term_id
    from main_analytics.fact_observation_native n
    join main_analytics.fact_metric f
      on f.metric_id = n.metric_id and f.period_month = n.anchor_month
    where n.metric_id = ? and n.native_frequency = 'annual'
      and n.value is not null
      and n.anchor_month >= date '1999-01-01'
    order by 1", params = list(metric_id))
}

monthly_series <- function(metric_id) {
  q("
    select n.anchor_month as anchor_month, n.value as value
    from main_analytics.fact_observation_native n
    where n.metric_id = ? and n.native_frequency = 'monthly'
      and n.value is not null and n.anchor_month >= date '1999-01-01'
    order by 1", params = list(metric_id))
}

catalogue <- q("select metric_id, label, native_frequency, is_landed, coverage_status, domain
                from main_analytics.dim_metric order by metric_id")

min_obs_unit_root <- spec_get(c("unit_root", "min_observations"), 12)
alpha <- spec_get(c("unit_root", "alpha"), 0.05)
ur_max_lags <- spec_get(c("unit_root", "max_lags"), 4)

cat(sprintf("Stage 5 diagnostics | vintage %s | native grain, study window floor 1999-01-01\n\n",
            vintage))

# ------------------------------------------------------------------------------------------
# 1. integration order
# ------------------------------------------------------------------------------------------
series_diag <- list()

for (i in seq_len(nrow(catalogue))) {
  mid <- catalogue$metric_id[[i]]
  freq <- catalogue$native_frequency[[i]]
  if (identical(freq, "monthly")) next   # handled separately below, at its own grain

  df <- annual_series(mid)
  n <- nrow(df)
  entry <- list(
    metric_id = mid, series_label = mid, label = catalogue$label[[i]], native_frequency = freq,
    n_observations = n, first_year = if (n) min(df$yr) else NA,
    last_year = if (n) max(df$yr) else NA,
    order_of_integration = NA, decisive = NA, note = NA_character_,
    tests = list()
  )
  if (n < min_obs_unit_root) {
    entry$note <- sprintf("only %d native observations in the window (minimum %d) — not tested",
                          n, min_obs_unit_root)
    entry$order_of_integration <- NA
    series_diag[[mid]] <- entry
    next
  }
  x <- as.numeric(df$value)
  entry$tests <- list(
    adf_drift = unit_root_test("adf_drift", x, alpha, ur_max_lags),
    adf_trend = unit_root_test("adf_trend", x, alpha, ur_max_lags),
    kpss = unit_root_test("kpss", x, alpha, ur_max_lags),
    pp = unit_root_test("pp", x, alpha, ur_max_lags),
    adf_diff = unit_root_test("adf_drift", diff(x), alpha, ur_max_lags),
    kpss_diff = unit_root_test("kpss", diff(x), alpha, ur_max_lags),
    pp_diff = unit_root_test("pp", diff(x), alpha, ur_max_lags)
  )
  cls <- classify_order(entry$tests)
  entry$order_of_integration <- cls$order
  entry$decisive <- isTRUE(cls$decisive)
  entry$note <- if (isTRUE(cls$decisive)) NA_character_ else cls$note
  series_diag[[mid]] <- entry
}

# Brent is genuinely monthly, so it is tested at its own grain as well as on the annual side used
# by the Tier-3 system.
oil_m <- monthly_series("oil")
oil_entry <- list(
  metric_id = "oil", series_label = "oil (monthly native)",
  label = "Brent crude (monthly, native)", native_frequency = "monthly",
  n_observations = nrow(oil_m),
  first_year = if (nrow(oil_m)) as.integer(format(min(oil_m$anchor_month), "%Y")) else NA,
  last_year = if (nrow(oil_m)) as.integer(format(max(oil_m$anchor_month), "%Y")) else NA,
  order_of_integration = NA, decisive = NA, note = NA_character_, tests = list()
)
if (nrow(oil_m) >= min_obs_unit_root) {
  xm <- as.numeric(oil_m$value)
  oil_entry$tests <- list(
    adf_drift = unit_root_test("adf_drift", xm, alpha, ur_max_lags),
    adf_trend = unit_root_test("adf_trend", xm, alpha, ur_max_lags),
    kpss = unit_root_test("kpss", xm, alpha, ur_max_lags),
    pp = unit_root_test("pp", xm, alpha, ur_max_lags),
    adf_diff = unit_root_test("adf_drift", diff(xm), alpha, ur_max_lags),
    kpss_diff = unit_root_test("kpss", diff(xm), alpha, ur_max_lags),
    pp_diff = unit_root_test("pp", diff(xm), alpha, ur_max_lags)
  )
  cls <- classify_order(oil_entry$tests)
  oil_entry$order_of_integration <- cls$order
  oil_entry$decisive <- isTRUE(cls$decisive)
  oil_entry$note <- if (isTRUE(cls$decisive)) NA_character_ else cls$note
}
series_diag[["oil_monthly"]] <- oil_entry

# annual mean of Brent, the form the Tier-3 system uses (rule declared in diagnostics.yml)
oil_a <- q("
  select year(anchor_month) as yr, avg(value) as value
  from main_analytics.fact_observation_native
  where metric_id = 'oil' and native_frequency = 'monthly'
    and value is not null and anchor_month >= date '1999-01-01'
  group by 1 order by 1")
if (nrow(oil_a) >= min_obs_unit_root) {
  xa <- as.numeric(oil_a$value)
  e <- list(metric_id = "oil", series_label = "oil (annual mean)",
            label = "Brent crude (annual mean)", native_frequency = "annual_mean",
            n_observations = nrow(oil_a), first_year = min(oil_a$yr), last_year = max(oil_a$yr),
            order_of_integration = NA, decisive = NA, note = NA_character_, tests = list())
  e$tests <- list(
    adf_drift = unit_root_test("adf_drift", xa, alpha, ur_max_lags),
    adf_trend = unit_root_test("adf_trend", xa, alpha, ur_max_lags),
    kpss = unit_root_test("kpss", xa, alpha, ur_max_lags),
    pp = unit_root_test("pp", xa, alpha, ur_max_lags),
    adf_diff = unit_root_test("adf_drift", diff(xa), alpha, ur_max_lags),
    kpss_diff = unit_root_test("kpss", diff(xa), alpha, ur_max_lags),
    pp_diff = unit_root_test("pp", diff(xa), alpha, ur_max_lags)
  )
  cls <- classify_order(e$tests)
  e$order_of_integration <- cls$order
  e$decisive <- isTRUE(cls$decisive)
  e$note <- if (isTRUE(cls$decisive)) NA_character_ else cls$note
  series_diag[["oil_annual"]] <- e
}

# ------------------------------------------------------------------------------------------
# 1b. additional native series declared by name (C-85)
# ------------------------------------------------------------------------------------------
# The catalogue loop skips anything `dim_metric` does not carry, and the NBS monthly CPI is
# deliberately outside it (harmonisation.yml keeps it unspined). A series a design *uses* still has
# to be diagnosed before the design is fitted, so `diagnostics.yml → additional_series` names it and
# the same three-test battery runs on it at its own grain.
additional <- spec_get(c("additional_series"), list())
for (s in additional) {
  id <- as.character(s$id)
  table_name <- as.character(s$table)
  column_name <- as.character(s$column)
  # Table and column come from the spec, so they are checked against the base's own catalogue before
  # being interpolated into SQL: a typo should fail here as a named error, not as a parse error three
  # lines later.
  present <- q(sprintf(
    "select count(*) as n from information_schema.columns
     where table_schema = 'main_analytics' and table_name = '%s' and column_name = '%s'",
    table_name, column_name))$n[[1]]
  if (present == 0) {
    stop(sprintf("additional_series %s: %s.%s does not exist in the base", id, table_name, column_name))
  }
  add_df <- q(sprintf(
    "select period_month as anchor_month, %s as value from main_analytics.%s
     where %s is not null and period_month >= date '1999-01-01' order by 1",
    column_name, table_name, column_name))
  series_transform <- as.character(s$transform %||% "level")
  if (identical(series_transform, "log")) {
    if (any(add_df$value <= 0)) {
      stop(sprintf("additional_series %s: declared transform 'log' but the series carries non-positive values",
                   id))
    }
    add_df$value <- log(add_df$value)
  }
  entry <- list(
    metric_id = id, series_label = id, label = as.character(s$label),
    native_frequency = as.character(s$native_frequency),
    n_observations = nrow(add_df),
    first_year = if (nrow(add_df)) as.integer(format(min(add_df$anchor_month), "%Y")) else NA,
    last_year = if (nrow(add_df)) as.integer(format(max(add_df$anchor_month), "%Y")) else NA,
    order_of_integration = NA, decisive = NA, note = NA_character_, tests = list(),
    declared_by = "diagnostics.yml additional_series",
    transform = series_transform,
    first_month = if (nrow(add_df)) as.character(min(add_df$anchor_month)) else NA_character_,
    last_month = if (nrow(add_df)) as.character(max(add_df$anchor_month)) else NA_character_
  )
  if (nrow(add_df) < min_obs_unit_root) {
    entry$note <- sprintf("only %d native observations in the window (minimum %d) — not tested",
                          nrow(add_df), min_obs_unit_root)
  } else {
    xs <- as.numeric(add_df$value)
    entry$tests <- list(
      adf_drift = unit_root_test("adf_drift", xs, alpha, ur_max_lags),
      adf_trend = unit_root_test("adf_trend", xs, alpha, ur_max_lags),
      kpss = unit_root_test("kpss", xs, alpha, ur_max_lags),
      pp = unit_root_test("pp", xs, alpha, ur_max_lags),
      adf_diff = unit_root_test("adf_drift", diff(xs), alpha, ur_max_lags),
      kpss_diff = unit_root_test("kpss", diff(xs), alpha, ur_max_lags),
      pp_diff = unit_root_test("pp", diff(xs), alpha, ur_max_lags)
    )
    cls <- classify_order(entry$tests)
    entry$order_of_integration <- cls$order
    entry$decisive <- isTRUE(cls$decisive)
    entry$note <- if (isTRUE(cls$decisive)) NA_character_ else cls$note
  }
  series_diag[[id]] <- entry
  cat(sprintf("  %-22s %s -> order %s (%s)\n", id, entry$native_frequency,
              ifelse(is.na(entry$order_of_integration), "not tested",
                     as.character(entry$order_of_integration)),
              ifelse(isTRUE(entry$decisive), "decisive", "inconclusive")))
}

cat(sprintf("1. integration order  — %d series tested at native grain, %d inconclusive\n",
            sum(vapply(series_diag, function(s) !is.null(s$order_of_integration) &&
                         !is.na(s$order_of_integration), logical(1))),
            sum(vapply(series_diag, function(s) isFALSE(s$decisive), logical(1)))))

# ------------------------------------------------------------------------------------------
# 2. cointegration — Johansen on the available Tier-3 system (base spec section 9)
# ------------------------------------------------------------------------------------------
coint_K <- spec_get(c("cointegration", "K"), 2)
coint_alpha <- spec_get(c("cointegration", "alpha"), 0.05)
coint_min_obs <- spec_get(c("cointegration", "min_observations"), 20)

cointegration <- list()
for (o in outcomes) {
  df <- annual_series(o$id)
  if (nrow(df) < coint_min_obs) {
    cointegration[[o$id]] <- list(outcome_id = o$id, verdict = "not_run",
                                  note = sprintf("%d annual observations (minimum %d)",
                                                 nrow(df), coint_min_obs))
    next
  }
  m <- merge(df[, c("yr", "value")], oil_a, by = "yr", suffixes = c("_y", "_oil"))
  fx <- q("select year(anchor_month) as yr, value from main_analytics.fact_observation_native
           where metric_id = 'fx' and value is not null and anchor_month >= date '1999-01-01'
           order by 1")
  m <- merge(m, fx, by = "yr")
  names(m)[names(m) == "value"] <- "fx"
  m <- m[stats::complete.cases(m), ]
  if (nrow(m) < coint_min_obs) {
    cointegration[[o$id]] <- list(
      outcome_id = o$id, verdict = "not_run",
      note = sprintf("%d complete annual rows across {Y, log(oil), fx} (minimum %d)",
                     nrow(m), coint_min_obs))
    next
  }
  sys <- data.frame(y = m$value_y, log_oil = log(m$value_oil), fx = m$fx)
  entry <- list(outcome_id = o$id, verdict = "not_run", n_observations = nrow(sys),
                system = c("Y", "log_oil", "fx"), K = coint_K, ecdet = "const",
                absent_from_system = list("faac"), note = NA_character_)
  res <- tryCatch({
    # ca.jo lives in urca, not vars, from vars >= 1.6 onward. Named in the spec so the dependency
    # is explicit rather than discovered by a stack trace.
    jo <- urca::ca.jo(as.matrix(sys), type = "trace", ecdet = "const", K = coint_K)
    jo_eig <- urca::ca.jo(as.matrix(sys), type = "eigen", ecdet = "const", K = coint_K)
    cval_col <- sprintf("%.0fpct", coint_alpha * 100)
    trace_stats <- as.numeric(jo@teststat)
    trace_cvals <- as.numeric(jo@cval[, cval_col])
    eig_stats <- as.numeric(jo_eig@teststat)
    eig_cvals <- as.numeric(jo_eig@cval[, cval_col])
    # urca::ca.jo returns its statistics ordered r = K-1, K-2, ..., 0 — the largest statistic
    # (the r = 0 hypothesis, "no cointegration") comes LAST, not first. Labelling row i as r = i-1
    # therefore inverted every r on the card: the r = 0 statistic was printed as r = K-1. The
    # pairing of statistic with critical value is positional and so stayed correct, which is why
    # the rank was right while the per-row label was wrong. Reorder to the r = 0 .. K-1 order the
    # rank rule in diagnostics.yml is written in.
    n_r <- length(trace_stats)
    tr_stat <- trace_stats[n_r:1]; tr_cval <- trace_cvals[n_r:1]
    eg_stat <- eig_stats[n_r:1];  eg_cval <- eig_cvals[n_r:1]
    # Rank is the number of consecutive rejections scanning r = 0 upward, stopping at the first
    # failure. For a monotone statistic sequence this equals the count of exceedances; writing it
    # as the textbook scan removes the reliance on that monotonicity holding.
    scan_rank <- function(stat, cval) {
      r <- 0L
      for (j in seq_along(stat)) { if (stat[[j]] > cval[[j]]) r <- r + 1L else break }
      r
    }
    rank_trace <- scan_rank(tr_stat, tr_cval)
    rank_eigen <- scan_rank(eg_stat, eg_cval)
    entry$trace <- lapply(seq_len(n_r), function(r) list(
      r = r - 1L, teststat = round_or_na(tr_stat[[r]]), cval = round_or_na(tr_cval[[r]]),
      exceeds = tr_stat[[r]] > tr_cval[[r]]))
    entry$eigen <- lapply(seq_len(n_r), function(r) list(
      r = r - 1L, teststat = round_or_na(eg_stat[[r]]), cval = round_or_na(eg_cval[[r]]),
      exceeds = eg_stat[[r]] > eg_cval[[r]]))
    entry$rank_trace <- rank_trace
    entry$rank_eigen <- rank_eigen
    rank <- min(rank_trace, rank_eigen)
    n_sys <- ncol(sys)
    entry$rank <- rank
    entry$disagreement <- rank_trace != rank_eigen
    # How close the decision was. A rank taken with the deciding statistic barely over its critical
    # value is not robust to the estimator's deterministic-term convention: urca and an independent
    # implementation agree on every non-marginal rank here and disagree on the one marginal case
    # (mmr, margin < 10%), so the margin is recorded rather than hidden. Declared fraction: 0.25.
    entry$rank_margin_frac <- if (rank > 0) {
      round_or_na((tr_stat[[rank]] - tr_cval[[rank]]) / tr_cval[[rank]])
    } else {
      round_or_na((tr_cval[[1]] - tr_stat[[1]]) / tr_cval[[1]])
    }
    entry$rank_borderline <- isTRUE(entry$rank_margin_frac < 0.25)
    # rank = 0 -> no cointegration -> ARDL bounds (base spec section 9's declared fallback).
    # rank = full system dimension -> the tests read the whole system as stationary, which is not
    # cointegration at all; a VAR in levels is the honest reading, and saying "VECM" here would
    # dress a stationary system up as a long-run relationship.
    entry$recommended_estimator <- if (rank == 0) "ardl_bounds"
      else if (rank >= n_sys) "var_in_levels" else "vecm"
    entry$verdict <- if (rank == 0) "no_cointegration_ardl_fallback"
      else if (rank >= n_sys) "system_reads_as_stationary" else "cointegrated"
    if (rank >= n_sys) {
      entry$note <- sprintf(paste("rank %d of a %d-variable system: the trace test rejects every rank",
                                  "below the dimension, so the system reads as stationary rather than",
                                  "cointegrated"), rank, n_sys)
    }
    if (rank_trace != rank_eigen) {
      entry$note <- sprintf("trace and max-eigenvalue disagree (r = %d vs %d); the smaller rank is ",
                            rank_trace, rank_eigen)
    }
    entry
  }, error = function(e) {
    entry$note <- conditionMessage(e)
    entry
  })
  cointegration[[o$id]] <- res
}

cat(sprintf("2. cointegration     — %d outcomes tested, %d with no cointegration (ARDL fallback)\n",
            sum(vapply(cointegration, function(x) !is.na(x$n_observations %||% NA), logical(1))),
            sum(vapply(cointegration, function(x) identical(x$verdict, "no_cointegration_ardl_fallback"),
                       logical(1)))))

# ------------------------------------------------------------------------------------------
# 2b. the monthly system C-85 declares — the price level against the shock
# ------------------------------------------------------------------------------------------
# Same estimator, same rank rule, same conservative branches as the annual system above; what differs
# is the grain and the system. Published as its own key (`cointegration_monthly`) rather than appended
# to `cointegration`, because that object is keyed by *annual outcome* and every consumer of it —
# including the verifier — reconstructs an annual {Y, log(oil), fx} system from the key.
monthly_spec <- spec_get(c("cointegration", "monthly_system"), NULL)
cointegration_monthly <- NULL
if (!is.null(monthly_spec)) {
  mo <- q("
    select c.period_month, c.cpi_index as outcome_value, o.value as shock_value
    from main_analytics.nbs_cpi_national_monthly c
    join main_analytics.fact_observation_native o
      on o.metric_id = 'oil' and o.native_frequency = 'monthly' and o.anchor_month = c.period_month
    where c.cpi_index is not null and o.value is not null
      and c.period_month >= date '1999-01-01'
    order by 1")
  K_m <- as.integer(monthly_spec$K %||% 2)
  min_m <- as.integer(monthly_spec$min_observations %||% 20)
  cm <- list(
    outcome_id = as.character(monthly_spec$outcome), verdict = "not_run",
    system = c("log(cpi_index)", "log(oil)"), K = K_m, ecdet = "const",
    n_observations = nrow(mo),
    first_month = if (nrow(mo)) as.character(min(mo$period_month)) else NA_character_,
    last_month = if (nrow(mo)) as.character(max(mo$period_month)) else NA_character_,
    note = NA_character_
  )
  if (nrow(mo) < min_m) {
    cm$note <- sprintf("%d complete months across {log(cpi_index), log(oil)} (minimum %d)",
                       nrow(mo), min_m)
  } else {
    sys_m <- data.frame(outcome = log(mo$outcome_value), shock = log(mo$shock_value))
    conventions <- as.character(unlist(monthly_spec$ecdet_conventions %||% list("const")))
    by_convention <- list()
    rank_by <- list()
    for (ecc in conventions) {
      res <- tryCatch({
        jo_m <- urca::ca.jo(as.matrix(sys_m), type = "trace", ecdet = ecc, K = K_m)
        jo_m_eig <- urca::ca.jo(as.matrix(sys_m), type = "eigen", ecdet = ecc, K = K_m)
        cval_col_m <- sprintf("%.0fpct", coint_alpha * 100)
        n_rm <- length(as.numeric(jo_m@teststat))
        # urca orders r = K-1 .. 0; reverse to the r = 0 .. K-1 order the declared rule is written in.
        tr_m <- as.numeric(jo_m@teststat)[n_rm:1]
        trc_m <- as.numeric(jo_m@cval[, cval_col_m])[n_rm:1]
        eg_m <- as.numeric(jo_m_eig@teststat)[n_rm:1]
        egc_m <- as.numeric(jo_m_eig@cval[, cval_col_m])[n_rm:1]
        scan_m <- function(stat, cval) {
          r <- 0L
          for (j in seq_along(stat)) { if (stat[[j]] > cval[[j]]) r <- r + 1L else break }
          r
        }
        rt <- scan_m(tr_m, trc_m)
        re <- scan_m(eg_m, egc_m)
        list(
          ecdet = ecc, rank_trace = rt, rank_eigen = re, rank = min(rt, re),
          trace = lapply(seq_len(n_rm), function(r) list(
            r = r - 1L, teststat = round_or_na(tr_m[[r]]), cval = round_or_na(trc_m[[r]]),
            exceeds = tr_m[[r]] > trc_m[[r]])),
          eigen = lapply(seq_len(n_rm), function(r) list(
            r = r - 1L, teststat = round_or_na(eg_m[[r]]), cval = round_or_na(egc_m[[r]]),
            exceeds = eg_m[[r]] > egc_m[[r]]))
        )
      }, error = function(e) list(ecdet = ecc, rank = NULL, note = conditionMessage(e)))
      by_convention[[ecc]] <- res
      if (!is.null(res$rank)) rank_by[[ecc]] <- as.integer(res$rank)
    }
    cm$by_convention <- by_convention
    cm$rank_by_convention <- rank_by
    if (!length(rank_by)) {
      cm$note <- "no deterministic-term convention produced a rank"
    } else {
      # The declared rule: the smaller rank wins, and both are published. Same conservatism the annual
      # block applies when trace and eigen disagree, applied to the convention instead.
      cm$rank <- min(unlist(rank_by))
      cm$rank_rule <- "conservative_min across the declared deterministic-term conventions"
      cm$conventions_disagree <- length(unique(unlist(rank_by))) > 1L
      # The published rows are those of the convention the conservative rank was read from, so the
      # statistics beside the rank are the ones it was taken from.
      chosen <- names(rank_by)[[which.min(unlist(rank_by))]]
      cm$chosen_convention <- chosen
      cm$ecdet <- chosen
      cm$trace <- by_convention[[chosen]]$trace
      cm$eigen <- by_convention[[chosen]]$eigen
      cm$rank_trace <- by_convention[[chosen]]$rank_trace
      cm$rank_eigen <- by_convention[[chosen]]$rank_eigen
      cm$disagreement <- cm$rank_trace != cm$rank_eigen
      cm$recommended_estimator <- if (cm$rank == 0) "ardl_bounds"
        else if (cm$rank >= ncol(sys_m)) "var_in_levels" else "vecm"
      cm$verdict <- if (cm$rank == 0) "no_cointegration_ardl_fallback"
        else if (cm$rank >= ncol(sys_m)) "stationary_system_var_in_levels"
        else "cointegrated_vecm"
    }
  }
  cointegration_monthly <- cm
  cat(sprintf("2b. cointegration    — %s vs log(oil), %d months, rank %s (%s) | %s\n",
              monthly_spec$outcome, cm$n_observations,
              ifelse(is.null(cm$rank), "not run", as.character(cm$rank)),
              ifelse(is.null(cm$verdict), "not_run", cm$verdict),
              paste(sprintf("%s=%s", names(cm$rank_by_convention %||% list()),
                            unlist(cm$rank_by_convention %||% list())), collapse = ", ")))
}


min_in_band <- spec_get(c("shock_visibility", "min_observed_in_band"), 3)
min_frac <- spec_get(c("shock_visibility", "min_observed_fraction"), 0.25)

shock_rows <- q("
  select s.shock_id, s.label, s.start_month, s.end_month, s.n_months,
         f.metric_id,
         count(*) filter (where f.observation_type = 'observed')     as n_observed,
         count(*) filter (where f.observation_type = 'interpolated') as n_interpolated,
         count(*) filter (where f.observation_type = 'unobserved')   as n_unobserved,
         count(*)                                                    as n_months
  from main_analytics.dim_shock s
  cross join (select distinct metric_id from main_analytics.fact_metric) mm
  join main_analytics.fact_metric f
    on f.metric_id = mm.metric_id
   and f.period_month between s.start_month and s.end_month
  group by 1,2,3,4,5,6
  order by s.shock_id, f.metric_id")

shock_visibility <- list()
for (i in seq_len(nrow(shock_rows))) {
  r <- shock_rows[i, ]
  n <- r$n_months
  verdict <- if (r$n_observed == 0) "not_visible"
    else if (r$n_observed == 1) "single_anchor"
    else if (r$n_observed >= min_in_band && (r$n_observed / n) >= min_frac) "visible"
    else "partial"
  sid <- as.character(r$shock_id)
  if (is.null(shock_visibility[[sid]])) {
    shock_visibility[[sid]] <- list(
      shock_id = as.integer(r$shock_id), label = r$label,
      start_month = format(r$start_month, "%Y-%m-%d"), end_month = format(r$end_month, "%Y-%m-%d"),
      n_months = n,
      visible_on = character(0), single_anchor_on = character(0),
      not_visible_on = character(0), partial_on = character(0),
      per_metric = list()
    )
  }
  shock_visibility[[sid]]$per_metric[[r$metric_id]] <- list(
    metric_id = r$metric_id, n_observed_in_band = r$n_observed,
    n_interpolated_in_band = r$n_interpolated, n_unobserved_in_band = r$n_unobserved,
    n_months_in_band = n, verdict = verdict)
  shock_visibility[[sid]][[switch(verdict,
                                  visible = "visible_on",
                                  single_anchor = "single_anchor_on",
                                  not_visible = "not_visible_on",
                                  partial = "partial_on")]] <-
    c(shock_visibility[[sid]][[switch(verdict, visible = "visible_on",
                                      single_anchor = "single_anchor_on",
                                      not_visible = "not_visible_on",
                                      partial = "partial_on")]], r$metric_id)
}

cat(sprintf("3. shock windows     — %d windows; visible on %s\n",
            length(shock_visibility),
            paste(vapply(shock_visibility, function(s)
              sprintf("%s:%s", s$shock_id, if (length(s$visible_on)) paste(s$visible_on, collapse = "/")
                      else "none"), character(1)), collapse = " ")))

# ------------------------------------------------------------------------------------------
# 4. dose validation (Family A)
# ------------------------------------------------------------------------------------------
dose_cols <- spec_get(c("dose", "dose_columns"), list())
outcome_cols <- unlist(spec_get(c("dose", "outcome_columns"), list()))

panel_total <- q("select count(*) as n from main_analytics.state_panel")$n[[1]]
dose_entries <- list()
for (dc in dose_cols) {
  if (is.null(dc$column)) {
    dose_entries[[dc$id]] <- list(id = dc$id, label = dc$label, column = NA_character_,
                                  verdict = "not_built", n_non_null = 0,
                                  note = dc$reason %||% "not built")
    next
  }
  col <- dc$column
  stats_row <- q(sprintf("
    select count(*) as n_rows,
           count(\"%s\") as n_non_null,
           count(distinct case when \"%s\" is not null then state_id end) as n_states_with_dose,
           count(distinct \"%s\") as n_distinct_values,
           max(cnt) as max_months_per_state,
           min(cnt) as min_months_per_state
    from (select *, count(\"%s\") over (partition by state_id) as cnt
          from main_analytics.state_panel)", col, col, col, col))
  n_non_null <- stats_row$n_non_null[[1]]
  verdict <- if (n_non_null == 0) "absent"
    else if (n_non_null < spec_get(c("dose", "min_non_null_rows"), 1)) "insufficient"
    else if (stats_row$n_states_with_dose[[1]] < spec_get(c("dose", "min_states_with_dose"), 2)) "no_cross_state_variation"
    else if (stats_row$n_distinct_values[[1]] < spec_get(c("dose", "min_distinct_dose_values"), 24)) "insufficient_variation"
    else "pass"
  dose_entries[[dc$id]] <- list(
    id = dc$id, label = dc$label, column = col, verdict = verdict,
    n_rows = stats_row$n_rows[[1]], n_non_null = n_non_null,
    coverage_fraction = round_or_na(n_non_null / max(1, panel_total)),
    n_states_with_dose = stats_row$n_states_with_dose[[1]],
    n_distinct_values = stats_row$n_distinct_values[[1]],
    min_months_per_state = stats_row$min_months_per_state[[1]],
    max_months_per_state = stats_row$max_months_per_state[[1]],
    note = if (identical(verdict, "absent"))
      "column exists and is typed, but no value has landed — the Stage 4 declared gap, not a null result"
    else NA_character_)
}

outcome_entries <- list()
for (col in outcome_cols) {
  n <- q(sprintf("select count(\"%s\") as n from main_analytics.state_panel", col))$n[[1]]
  outcome_entries[[col]] <- list(column = col, n_non_null = n,
                                 verdict = if (n == 0) "absent" else "present")
}

# Which axes carry anything at all, and whether the *specified* one does. These are different questions
# and the family verdict answers the second: the nominal FAAC column landed on 2026-10-16 and is gated,
# the per-capita form the estimand is written on still waits on X-09, and a gate that went green on the
# nominal column would be reporting a dose the design does not use.
specified_axis <- spec_get(c("dose", "specified_axis"), NA_character_)
specified_entry <- dose_entries[[specified_axis]]
specified_present <- !is.null(specified_entry) && identical(specified_entry$verdict, "pass")
present_axes <- names(Filter(
  function(d) !identical(d$verdict, "absent") && !identical(d$verdict, "not_built"), dose_entries))

axis_summary <- paste(vapply(dose_entries, function(d) sprintf("%s=%s", d$id, d$verdict), character(1)),
                      collapse = ", ")

dose <- list(
  table = "state_panel",
  n_rows = panel_total,
  n_states = q("select count(distinct state_id) as n from main_analytics.state_panel")$n[[1]],
  dose_status_values = q("select dose_status, count(*) as n from main_analytics.state_panel
                          group by 1 order by 2 desc"),
  axes = dose_entries,
  specified_axis = specified_axis,
  specified_axis_present = specified_present,
  # I() keeps this an array when there is one element. Without it jsonlite serialises a length-one
  # character vector as a scalar string, so the artifact's shape would depend on how many axes happen
  # to hold data -- the kind of drift a verifier then has to guess about (it split "D1_nominal" into
  # its characters on the first run of this check).
  present_axes = I(present_axes),
  axis_verdicts = axis_summary,
  state_outcomes = outcome_entries,
  any_dose_present = any(vapply(dose_entries, function(d) !identical(d$verdict, "absent") &&
                                  !identical(d$verdict, "not_built"), logical(1))),
  any_state_outcome_present = any(vapply(outcome_entries, function(d) identical(d$verdict, "present"),
                                         logical(1)))
)
# The gate is decided by the specified axis; the presence of another axis is reported, never substituted.
dose$verdict <- if (specified_present) "pass" else "fail"
dose$blockers <- c(if (!specified_present && !dose$any_dose_present) "no_dose_series"
                   else if (!specified_present) sprintf("specified_dose_axis_absent:%s", specified_axis),
                   if (!dose$any_state_outcome_present) "no_state_attributed_outcome")
# A VIF across the doses needs every declared axis; today D1 is empty and D3 was never built, so this is
# false and the collinearity section must not claim to have conditioned on them.
dose$vif_across_doses_computable <- length(dose_entries) > 0 &&
  all(vapply(dose_entries, function(d) identical(d$verdict, "pass"), logical(1)))

cat(sprintf("4. dose validation   — %s (%s; %d of %d panel values on the specified axis; %d state outcomes)\n",
            dose$verdict, axis_summary,
            if (is.null(specified_entry)) 0 else specified_entry$n_non_null,
            panel_total, sum(vapply(outcome_entries, function(d) d$n_non_null, numeric(1)))))

# ------------------------------------------------------------------------------------------
# 5. pre-treatment fit for Family C (Synth)
# ------------------------------------------------------------------------------------------
min_pre <- spec_get(c("pretrend", "family_c", "min_pre_years"), 8)
min_post <- spec_get(c("pretrend", "family_c", "min_post_years"), 2)
pre_frac <- spec_get(c("pretrend", "family_c", "pre_rmse_threshold_frac_of_sd"), 0.10)

donor_panel <- q("select country_iso3, metric_id, period_year, value
                  from main_analytics.fact_donor_panel order by 1, 2, 3")
donor_metrics <- sort(unique(donor_panel$metric_id))
nga_annual <- q("select metric_id, year(anchor_month) as yr, value
                 from main_analytics.fact_observation_native
                 where native_frequency = 'annual' and value is not null
                   and anchor_month >= date '1999-01-01' order by 1, 2")
donor_countries <- sort(unique(donor_panel$country_iso3))
cand_windows <- spec_get(c("windows", "candidate_treated_windows"), list())

prefit <- list()
for (o in outcomes) {
  # Only metrics present in both Nigeria's spine and the donor panel can carry a synthetic control.
  if (!(o$id %in% donor_metrics)) {
    prefit[[o$id]] <- list(outcome_id = o$id, verdict = "not_attempted",
                           note = sprintf("outcome %s is not in the donor panel (predictors: %s)",
                                          o$id, paste(donor_metrics, collapse = ", ")))
    next
  }
  predictors <- setdiff(donor_metrics, o$id)
  entry <- list(outcome_id = o$id, verdict = "not_attempted", n_donors_available = length(donor_countries),
                predictors = predictors, windows = list(), note = NA_character_)
  for (w in cand_windows) {
    start_year <- as.integer(substr(w$from, 1, 4))
    wkey <- w$id
    y_nga <- nga_annual[nga_annual$metric_id == o$id, ]
    yrs <- y_nga$yr
    pre_years <- yrs[yrs < start_year]
    post_years <- yrs[yrs >= start_year]
    if (length(pre_years) < min_pre || length(post_years) < min_post) {
      entry$windows[[wkey]] <- list(window = wkey, verdict = "not_run", pre_years = length(pre_years),
                                    post_years = length(post_years),
                                    note = sprintf("needs >= %d pre and >= %d post years", min_pre, min_post))
      next
    }
    z1 <- y_nga$value[match(pre_years, y_nga$yr)]
    z0_all <- vapply(donor_countries, function(cc) {
      d <- donor_panel[donor_panel$country_iso3 == cc & donor_panel$metric_id == o$id, ]
      v <- d$value[match(pre_years, d$period_year)]
      if (any(is.na(v))) NA_real_ else mean(v)
    }, numeric(1))
    # Synth needs a complete donor block over the pre-period. Donors without a complete outcome
    # path are dropped and *named* rather than silently interpolated (C-19 is the same issue: one
    # donor's series stops early).
    keep <- !is.na(z0_all)
    dropped <- donor_countries[!keep]
    donors_used <- donor_countries[keep]
    if (length(donors_used) < 5 || any(is.na(z1))) {
      entry$windows[[wkey]] <- list(
        window = wkey, verdict = "not_run", pre_years = length(pre_years),
        post_years = length(post_years), n_donors_available = length(donor_countries),
        n_donors_used = length(donors_used),
        donors_dropped_for_incomplete_path = as.list(dropped),
        note = sprintf("%d donors usable over the pre-period (minimum 5)", length(donors_used)))
      next
    }
    z0 <- do.call(cbind, lapply(donors_used, function(cc) {
      d <- donor_panel[donor_panel$country_iso3 == cc & donor_panel$metric_id == o$id, ]
      d$value[match(pre_years, d$period_year)]
    }))
    # Predictors are averaged over the years where every retained donor and Nigeria have data — a
    # balanced window per predictor, recorded rather than imputed (diagnostics.yml).
    x1 <- numeric(0)
    x0 <- matrix(nrow = 0, ncol = length(donors_used))
    used <- character(0)
    balanced_years <- list()
    for (p in predictors) {
      p_nga <- nga_annual[nga_annual$metric_id == p, ]
      p_don <- donor_panel[donor_panel$metric_id == p, ]
      n_nga <- p_nga$value[match(pre_years, p_nga$yr)]
      vals <- lapply(donors_used, function(cc) {
        d <- p_don[p_don$country_iso3 == cc, ]
        d$value[match(pre_years, d$period_year)]
      })
      ok <- !is.na(n_nga)
      for (v in vals) ok <- ok & !is.na(v)
      if (sum(ok) < 3) next
      used <- c(used, p)
      balanced_years[[p]] <- list(first = min(pre_years[ok]), last = max(pre_years[ok]), n = sum(ok))
      x1 <- c(x1, mean(n_nga[ok]))
      x0 <- rbind(x0, vapply(vals, function(v) mean(v[ok]), numeric(1)))
    }
    if (length(used) == 0) {
      entry$windows[[wkey]] <- list(
        window = wkey, verdict = "not_run", pre_years = length(pre_years),
        post_years = length(post_years), n_donors_used = length(donors_used),
        note = "no screening predictor spans a balanced 3-year window across the donors")
      next
    }
    res <- tryCatch({
      # The gate: the globally optimal simplex fit to the pre-treatment path. If even that cannot
      # track Nigeria, no estimator with a worse W can, so the design is infeasible rather than
      # merely hard to fit.
      w_qp <- simplex_path_weights(z1, z0)
      rmse <- rmspe(z1, z0, w_qp)
      sd_pre <- stats::sd(z1)
      # Benchmarks that make the number interpretable: what the best single donor achieves, and
      # whether Nigeria's level even lies inside the donors' convex hull (weights sum to one, so a
      # level outside the donor mean interval is unreachable however the weights are chosen).
      best1 <- min(apply(z0, 2, function(v) sqrt(mean((z1 - v)^2))))
      donor_means <- colMeans(z0)
      lo <- min(donor_means); hi <- max(donor_means)
      treated_mean <- mean(z1)
      level_gap <- if (treated_mean > hi) treated_mean - hi else if (treated_mean < lo) lo - treated_mean else 0
      # Same fit on the first difference, to separate "wrong level" from "wrong shape": a pool that
      # can match changes but not levels is a different (and narrower) claim than a pool that can
      # match neither.
      dz1 <- diff(z1); dz0 <- apply(z0, 2, diff)
      if (is.null(dim(dz0))) dz0 <- matrix(dz0, ncol = ncol(z0))
      w_d <- simplex_path_weights(dz1, dz0)
      rmse_d <- rmspe(dz1, dz0, w_d)
      sd_d <- stats::sd(dz1)
      # Synth is the estimator design spec section 11 names for Family C, so its fit is recorded as
      # a cross-check even though the gate does not rest on it.
      synth_rmse <- tryCatch({
        fit <- Synth::synth(X1 = matrix(x1, ncol = 1), X0 = x0, Z0 = z0, Z1 = matrix(z1, ncol = 1))
        rmspe(z1, z0, as.numeric(fit$solution.w))
      }, error = function(e) NA_real_)
      list(verdict = if (rmse / sd_pre <= pre_frac) "pass" else "weak_fit",
           pre_rmse = rmse, pre_sd = sd_pre, ratio = rmse / sd_pre,
           threshold = pre_frac,
           solver = "simplex_qp (quadprog) - globally optimal weights for the pre-treatment path",
           best_single_donor_rmse = best1, rmse_vs_best_single_donor = rmse / best1,
           donor_mean_interval = c(lo, hi), treated_mean = treated_mean,
           treated_outside_donor_mean_interval = level_gap > 0, level_gap = level_gap,
           rmse_on_differences = rmse_d, sd_of_differences = sd_d,
           ratio_on_differences = rmse_d / sd_d,
           synth_v_optimized_rmse = synth_rmse,
           synth_beats_best_single_donor = isTRUE(synth_rmse < best1),
           weights = setNames(round(w_qp, 6), donors_used),
           n_donors_used = length(donors_used),
           donors_dropped_for_incomplete_path = as.list(dropped),
           n_donors_with_weight = sum(w_qp > 1e-6),
           predictors_used = used, balanced_predictor_years = balanced_years,
           n_predictors = length(used),
           pre_years = length(pre_years), post_years = length(post_years))
    }, error = function(e) list(verdict = "not_run", note = conditionMessage(e)))
    entry$windows[[wkey]] <- c(list(window = wkey, from = w$from), res)
  }
  verdicts <- vapply(entry$windows, function(x) x$verdict, character(1))
  # The declared rollup (diagnostics.yml `outcome_rollup`): a strict majority of the windows that could be
  # run. The first version of this block used "any window passes", which is not what the gate means and is
  # exactly the kind of rule whose answer changes with the pool: with 13 donors nothing passed so it never
  # surfaced, and with 99 donors it would have credited an outcome on one window out of four.
  runnable <- sum(verdicts %in% c("pass", "weak_fit"))
  passed <- sum(verdicts == "pass")
  entry$n_windows_runnable <- runnable
  entry$n_windows_pass <- passed
  entry$rollup_rule <- "strict majority of runnable windows (diagnostics.yml `outcome_rollup`)"
  if (length(verdicts) == 0) {
    entry$verdict <- "not_attempted"
  } else if (runnable > 0 && passed > runnable / 2) {
    entry$verdict <- "pass"
  } else if (runnable > 0) {
    entry$verdict <- "infeasible_weak_pre_fit"
  } else {
    entry$verdict <- "not_run"
  }
  prefit[[o$id]] <- entry
}

cat(sprintf("5. pre-treatment fit — %d outcomes attempted, %d pass, %d infeasible on pre-fit\n",
            sum(vapply(prefit, function(p) length(p$windows) > 0, logical(1))),
            sum(vapply(prefit, function(p) identical(p$verdict, "pass"), logical(1))),
            sum(vapply(prefit, function(p) identical(p$verdict, "infeasible_weak_pre_fit"), logical(1)))))
for (pid in names(prefit)) {
  p <- prefit[[pid]]
  if (!is.null(p$n_windows_runnable) && p$n_windows_runnable > 0)
    cat(sprintf("     %-18s %-26s %d of %d runnable window(s) pass\n", pid, p$verdict,
                p$n_windows_pass, p$n_windows_runnable))
}
# ------------------------------------------------------------------------------------------
# 6. degrees of freedom and the detectable effect (Family B)
# ------------------------------------------------------------------------------------------
z_a <- spec_get(c("dof_power", "z_alpha_two_sided"), 1.959964)
z_p <- spec_get(c("dof_power", "z_power"), 0.8416212)
lag_max <- spec_get(c("dof_power", "tier3_lag_max"), 4)
min_dof <- spec_get(c("dof_power", "min_dof"), 3)

dof_power <- list()
for (o in outcomes) {
  df <- annual_series(o$id)
  n <- nrow(df)
  entry <- list(outcome_id = o$id, n_observations = n, verdict = "not_run", note = NA_character_)
  if (n < 12) {
    entry$note <- sprintf("%d annual observations — too few to fit the Tier-3 design", n)
    dof_power[[o$id]] <- entry
    next
  }
  m <- merge(df[, c("yr", "value", "pdp_first", "pdp_second", "apc_first", "apc_second")],
             oil_a, by = "yr", suffixes = c("_y", "_oil"))
  m <- m[stats::complete.cases(m), ]
  m <- m[order(m$yr), ]
  # lagged outcome (up to lag_max), dropping rows the lags remove
  for (L in seq_len(lag_max)) m[[sprintf("lag%d", L)]] <- c(rep(NA, L), head(m$value_y, -L))
  m <- m[stats::complete.cases(m), ]
  n_used <- nrow(m)
  if (n_used < lag_max + 8) {
    entry$note <- sprintf("%d usable annual rows after %d lags", n_used, lag_max)
    dof_power[[o$id]] <- entry
    next
  }
  trend <- seq_along(m$yr)
  m$trend <- trend
  m$trend2 <- trend^2
  m$log_oil <- log(m$value_oil)
  # The Tier-3 design: party-by-tenure dummies (base spec section 9), log oil, oilxadmin, lags,
  # linear and quadratic trend.
  strata <- c("pdp_first", "pdp_second", "apc_first")     # apc_second is the reference level
  X <- cbind(intercept = 1, as.matrix(m[, strata]), log_oil = m$log_oil)
  for (s in strata) X <- cbind(X, m[[s]] * m$log_oil)
  colnames(X)[(ncol(X) - length(strata) + 1):ncol(X)] <- paste0("log_oil_x_", strata)
  X <- cbind(X, trend = m$trend, trend2 = m$trend2,
             as.matrix(m[, sprintf("lag%d", seq_len(lag_max)), drop = FALSE]))
  k <- ncol(X)
  dof <- n_used - k
  # baseline model supplies sigma only (diagnostics.yml explains why)
  base_fit <- lm(value_y ~ log_oil + trend, data = m)
  sigma <- summary(base_fit)$sigma
  xtx_inv <- tryCatch(solve(crossprod(X)), error = function(e) NULL)
  entry$n_observations <- n_used
  entry$n_parameters <- k
  entry$dof <- dof
  entry$residual_sd_baseline <- round_or_na(sigma)
  entry$spec_terms <- colnames(X)
  if (is.null(xtx_inv) || dof < min_dof) {
    entry$verdict <- "infeasible"
    entry$note <- if (is.null(xtx_inv))
      "the Tier-3 design matrix is singular on this sample"
    else sprintf("%d residual degrees of freedom (minimum %d)", dof, min_dof)
    dof_power[[o$id]] <- entry
    next
  }
  mde <- (z_a + z_p) * sigma * sqrt(pmax(diag(xtx_inv), 0))
  names(mde) <- colnames(X)
  entry$mde <- as.list(round(mde, 6))
  entry$mde_strata <- as.list(round(mde[strata], 6))
  # Expressed against the outcome's own scale, because a MDE in raw units is unreadable on its own.
  # A ratio far above 1 means the design cannot detect a movement as large as the series'
  # year-to-year variation.
  entry$mde_strata_in_sd_units <- as.list(round(mde[strata] / sigma, 3))
  entry$outcome_sd <- round_or_na(stats::sd(m$value_y))
  entry$outcome_range <- c(round_or_na(min(m$value_y)), round_or_na(max(m$value_y)))
  entry$design_condition_number <- round_or_na(kappa(X, exact = TRUE), 3)
  # The same reckoning on the same rows with the oil-by-tenure interactions dropped, because that is
  # the one feature that turns out to decide the width. Keeping the interactions in would have made
  # the comparison meaningless — the two designs would differ only by lag order — while dropping them
  # isolates the cost of the interaction term the base spec makes non-negotiable.
  strata_reduced <- c("pdp_first", "pdp_second", "apc_first")
  X2 <- cbind(intercept = 1, as.matrix(m[, strata_reduced]), log_oil = m$log_oil, trend = m$trend)
  inv2 <- tryCatch(solve(crossprod(X2)), error = function(e) NULL)
  if (!is.null(inv2)) {
    mde2 <- (z_a + z_p) * sigma * sqrt(pmax(diag(inv2), 0))
    names(mde2) <- colnames(X2)
    entry$reduced_spec_terms <- colnames(X2)
    entry$reduced_dof <- n_used - ncol(X2)
    entry$mde_strata_reduced <- as.list(round(mde2[strata_reduced], 6))
    entry$mde_strata_reduced_in_sd_units <- as.list(round(mde2[strata_reduced] / sigma, 3))
  }
  entry$verdict <- "computed"
  dof_power[[o$id]] <- entry
}

cat(sprintf("6. DoF / power       — %d outcomes: %d computed, %d infeasible\n",
            length(dof_power),
            sum(vapply(dof_power, function(d) identical(d$verdict, "computed"), logical(1))),
            sum(vapply(dof_power, function(d) identical(d$verdict, "infeasible"), logical(1)))))

# ------------------------------------------------------------------------------------------
# 7. collinearity
# ------------------------------------------------------------------------------------------
vif_flag <- spec_get(c("collinearity", "vif_flag"), 10)
vif_fail <- spec_get(c("collinearity", "vif_fail"), 30)

collinearity <- list()
for (o in outcomes) {
  df <- annual_series(o$id)
  if (nrow(df) < lag_max + 8) {
    collinearity[[o$id]] <- list(outcome_id = o$id, verdict = "not_computable",
                                 note = sprintf("%d annual observations", nrow(df)))
    next
  }
  m <- merge(df[, c("yr", "value", "pdp_first", "pdp_second", "apc_first", "apc_second")],
             oil_a, by = "yr", suffixes = c("_y", "_oil"))
  m <- m[stats::complete.cases(m), ]
  m <- m[order(m$yr), ]
  trend <- seq_along(m$yr)
  m$trend <- trend
  m$log_oil <- log(m$value_oil)
  strata <- c("pdp_first", "pdp_second", "apc_first")
  X <- cbind(intercept = 1, as.matrix(m[, strata]), log_oil = m$log_oil, trend = m$trend)
  v <- vif_of(X)
  worst <- v[which.max(v)]
  collinearity[[o$id]] <- list(
    outcome_id = o$id, verdict = if (max(v, na.rm = TRUE) >= vif_fail) "fail"
      else if (max(v, na.rm = TRUE) >= vif_flag) "flag" else "pass",
    vif = as.list(round(v, 4)),
    max_vif = round_or_na(max(v, na.rm = TRUE)),
    max_vif_term = names(worst),
    n_obs = nrow(m),
    dose_axes = list(verdict = if (dose$vif_across_doses_computable) "computed" else "not_computable",
                     blocker = if (dose$vif_across_doses_computable) NA_character_
                       else paste(dose$blockers, collapse = " and "),
                     note = paste("VIF across D1/D2/D3 needs every dose axis present;",
                                  if (length(dose$blockers)) paste(dose$blockers, collapse = " and ") else "")),
    note = "party-by-tenure dummies are functions of the calendar, so they compete with the trend terms")
}

cat(sprintf("7. collinearity      — %d outcomes: %d pass, %d flag, %d fail\n",
            length(collinearity),
            sum(vapply(collinearity, function(c) identical(c$verdict, "pass"), logical(1))),
            sum(vapply(collinearity, function(c) identical(c$verdict, "flag"), logical(1))),
            sum(vapply(collinearity, function(c) identical(c$verdict, "fail"), logical(1)))))

# ------------------------------------------------------------------------------------------
# design verdicts and per-card diagnostics
# ------------------------------------------------------------------------------------------
design_verdicts <- list(
  A = list(
    design_id = "A",
    status = if (specified_present && dose$any_state_outcome_present) "candidate" else "dropped",
    gates = list(
      dose_variation = list(passed = specified_present,
                            detail = sprintf("%s: %d of %d panel values across %d states%s",
                                             specified_axis,
                                             if (is.null(specified_entry)) 0 else specified_entry$n_non_null,
                                             panel_total, dose$n_states,
                                             if (length(present_axes))
                                               sprintf(" — other axes present: %s",
                                                       paste(present_axes, collapse = ", "))
                                             else "")),
      state_outcome_attribution = list(passed = dose$any_state_outcome_present,
                                       detail = sprintf("%d of %d state outcome values present",
                                                        sum(vapply(outcome_entries, function(d) d$n_non_null, numeric(1))),
                                                        panel_total))
    ),
    blocker = paste(dose$blockers, collapse = " and "),
    # Both clauses below are built from the dose and outcome blocks, never typed next to them. The
    # alternative (the wording that shipped on 2026-10-17 before this fix) is a sentence that describes
    # a premise the artifacts have already changed: it said the family "is also missing a
    # state-attributed outcome" on the same page as a table reporting 21,238 state outcome values.
    dropped_because = if (specified_present && dose$any_state_outcome_present)
      NA_character_
    else if (!specified_present && dose$any_dose_present)
      paste("the FAAC dose has landed and is Stage 3 gated, but on the **nominal** axis: the estimand is",
            sprintf("written on %s (per capita), which needs the state population denominator decision",
                    specified_axis),
            "(X-09).",
            if (dose$any_state_outcome_present)
              paste(" The state-attributed outcome HAS landed (UCDP GED, C-45), so what is left is the",
                    "denominator decision and the choice of dose axis — Stage 6 ran the nominal-axis",
                    "version and reported it `estimated_not_identified` (registry/estimates/)")
            else
              paste(" The family is also missing a state-attributed outcome, so a dose alone does not",
                    "free it."))
    else paste("PHASES.md Stage 5 dose validation: a dose with near-zero cross-state variance cannot",
               "support a dose-response design, and no estimator fixes that"),
    diagnostics_that_decide = c("dose_variation", "state_outcome_attribution"),
    next_step = if (dose$any_state_outcome_present)
      paste("the state population denominator decision (X-09), which is what the specified axis D1 waits",
            "on. The outcome blocker is cleared: the state-attributed security series landed 2026-10-17")
    else paste("the state population denominator decision (X-09), which is what the specified",
               "axis D1 waits on, plus a state-attributed outcome — the human-security series are",
               "the route and they are credential-blocked (C-13/C-14)")
  ),
  B = list(
    design_id = "B",
    status = "degraded",
    gates = list(
      integration_order = list(passed = NA,
                               detail = sprintf("%d series tested at native grain",
                                                length(series_diag))),
      cointegration_rank = list(passed = NA,
                                detail = sprintf("%d outcomes tested",
                                                 sum(vapply(cointegration, function(c) identical(c$verdict, "cointegrated") ||
                                                              identical(c$verdict, "no_cointegration_ardl_fallback"), logical(1))))),
      dof_minimum = list(passed = NA,
                         detail = sprintf("%d outcomes infeasible at %d residual DoF",
                                          sum(vapply(dof_power, function(d) identical(d$verdict, "infeasible"), logical(1))),
                                          min_dof)),
      collinearity = list(passed = NA,
                          detail = sprintf("%d outcomes fail VIF >= %g",
                                           sum(vapply(collinearity, function(c) identical(c$verdict, "fail"), logical(1))),
                                           vif_fail))
    ),
    blocker = "FAAC is absent from the metric catalogue, so the Tier-3 system runs without its fiscal variable; and the grain is annual, not monthly",
    degraded_because = paste("base spec section 9 specifies oil + FAAC + FX + lags + trend at monthly",
                             "grain; the testable system is {Y, log(oil), fx} at annual grain"),
    diagnostics_that_decide = c("integration_order", "cointegration_rank", "dof_minimum", "collinearity"),
    next_step = paste("a metric-catalogue entry for the FAAC panel (landed and gated, but with no declared",
                      "monthly-to-annual aggregation), and a decision on whether an annual-grain estimate",
                      "is worth publishing")
  ),
  C = list(
    design_id = "C",
    status = "candidate",
    gates = list(
      pretreatment_fit = list(passed = NA,
                              detail = sprintf("%d outcomes pass the pre-fit threshold of %.2f x pre-period SD",
                                                sum(vapply(prefit, function(p) identical(p$verdict, "pass"), logical(1))),
                                                pre_frac)),
      donor_pool_coverage = list(passed = TRUE,
                                 detail = sprintf("%d donor countries x %d predictors",
                                                  length(donor_countries), length(donor_metrics)))
    ),
    blocker = NA_character_,
    diagnostics_that_decide = c("pretreatment_fit"),
    next_step = "Stage 6 fits the synthetic control where pre-fit passes"
  )
)

# per (outcome, design) pre-check status, which is what the cards carry
card_diagnostics <- list()
for (o in outcomes) {
  # Derived from the dose block above, never re-stated as prose here. The 2026-10-11 version of this
  # loop hard-coded "no dose series has landed", which was true then and became false the moment the
  # FAAC parser landed while the card kept saying it -- a card that cannot notice its own premise
  # changing is how a stale verdict survives a data delivery.
  a_dose_check <- list(
    id = "dose_variation",
    verdict = if (specified_present) "pass" else if (dose$any_dose_present) "flag" else "fail",
    detail = if (specified_present)
      sprintf("%s present: %d of %d panel values across %d states",
              specified_axis, specified_entry$n_non_null, panel_total, dose$n_states)
    else if (dose$any_dose_present)
      sprintf(paste("the specified axis %s is absent (the population denominator is an unmade decision,",
                    "X-09) while the nominal axis is present and Stage 3 gated: %s"),
              specified_axis, axis_summary)
    else "no dose series has landed; the state panel's dose columns are typed and empty")
  # The card's **own** outcome, looked up in the panel's outcome columns. `any_state_outcome_present` is a
  # design-level fact — "does the panel carry *any* state outcome" — and echoing it on every card made
  # `cpi_yoy__A` say "22126 state outcome values present" when no state-level CPI exists anywhere in the
  # base (C-90). A design-A card can only be a state x month regression, so the honest question is whether
  # *this* outcome can be one; the design-level fact still decides `design_verdicts$A`.
  o_state <- outcome_entries[[o$id]]
  o_state_present <- !is.null(o_state) && identical(o_state$verdict, "present")
  a_outcome_check <- list(
    id = "state_outcome_attribution",
    verdict = if (o_state_present) "pass" else "fail",
    detail = if (o_state_present)
      sprintf("%s is on the state panel: %d non-null state-months of %d",
              o$id, o_state$n_non_null, panel_total)
    else sprintf(paste("%s is not on the state panel, so a state x month regression has nothing to regress",
                       "for this card (the declared state outcome columns are %s)"),
                 o$id, paste(vapply(outcome_entries, function(d) d$column, character(1)), collapse = ", "))
  )
  card_diagnostics[[sprintf("%s__A", o$id)]] <- list(
    status = if (specified_present && o_state_present) "pass" else "fail",
    checks = list(
      a_dose_check,
      a_outcome_check,
      list(id = "parallel_trends_precheck", verdict = "not_run",
           detail = if (specified_present)
             "needs a state-attributed outcome as well as the dose: with no exposure groups there is nothing to compare"
           else if (dose$any_dose_present)
             paste("the nominal dose could group states by exposure, but the estimand is written on the",
                   "per-capita axis, so a trends test on the nominal dose would be a sensitivity check",
                   "at Stage 6 rather than this pre-check")
           else "needs the dose: with no exposure groups there is nothing to compare")
    ),
    blocker = design_verdicts$A$blocker,
    note = if (specified_present && o_state_present)
      "Passes its pre-check on the dose side; Stage 6 still owes the parallel-trends test."
    else if (!o_state_present)
      paste("Dropped at Stage 5 on the outcome side: this outcome has no state-level series, so there is",
            "nothing for a state x month design to regress. A data finding, not a null result.")
    else "Dropped on the record at Stage 5. This is a data finding, not a null result."
  )
  # R lists are copy-on-modify, so the enriched copy has to be written back. Without this the A
  # cards shipped with no coverage_status at all — caught by the card schema, not by reading the code.
  key <- sprintf("%s__A", o$id)
  cd <- card_diagnostics[[key]]
  cd$coverage_status <- o$coverage_status
  card_diagnostics[[key]] <- cd
}

for (o in outcomes) {
  it <- series_diag[[o$id]]
  co <- cointegration[[o$id]]
  dp <- dof_power[[o$id]]
  cl <- collinearity[[o$id]]
  checks <- list()
  if (!is.null(it) && !is.na(it$order_of_integration %||% NA)) {
    checks[[length(checks) + 1]] <- list(
      id = "integration_order", verdict = if (isTRUE(it$decisive)) "computed" else "inconclusive",
      detail = sprintf("I(%d) across ADF/KPSS/PP on %d native annual observations%s",
                       it$order_of_integration, it$n_observations,
                       if (isTRUE(it$decisive)) "" else " — tests disagree"))
  } else {
    checks[[length(checks) + 1]] <- list(
      id = "integration_order", verdict = "not_run",
      detail = if (!is.null(it)) it$note %||% "insufficient observations" else "no native series")
  }
  checks[[length(checks) + 1]] <- list(
    id = "cointegration_rank",
    verdict = if (is.null(co) || is.na(co$rank %||% NA)) "not_run" else "computed",
    detail = if (is.null(co) || is.na(co$rank %||% NA))
      (co$note %||% "not run")
      else sprintf("Johansen rank %d on {Y, log(oil), fx}, K=%d -> %s%s%s",
                   co$rank, coint_K,
                   switch(co$recommended_estimator,
                          ardl_bounds = "ARDL bounds fallback",
                          vecm = "VECM",
                          var_in_levels = "VAR in levels (rank = system dimension: reads as stationary, not cointegrated)",
                          co$recommended_estimator),
                   if (isTRUE(co$disagreement)) " (trace and eigen disagree; smaller rank taken)" else "",
                   if (isTRUE(co$rank_borderline)) sprintf(" (rank marginal: deciding statistic only %.0f%% over its critical value)",
                                                           100 * co$rank_margin_frac) else ""))
  # Every branch has to yield a length-one string: sprintf() with a NULL argument returns
  # character(0), which serialises as an empty array and breaks the card schema rather than the
  # script. (Also found by the schema, not by looking at the JSON.)
  dof_detail <- if (is.null(dp) || is.na(dp$dof %||% NA)) {
    dp$note %||% "not computed"
  } else if (is.null(dp$mde_strata)) {
    sprintf("%d annual rows, %d parameters, %d residual DoF, but the design matrix is singular",
            dp$n_observations, dp$n_parameters, dp$dof)
  } else {
    sprintf("%d annual rows, %d parameters, %d residual DoF, MDE for the tenure strata %.3g-%.3g",
            dp$n_observations, dp$n_parameters, dp$dof,
            min(unlist(dp$mde_strata), na.rm = TRUE), max(unlist(dp$mde_strata), na.rm = TRUE))
  }
  checks[[length(checks) + 1]] <- list(
    id = "dof_power",
    verdict = if (is.null(dp)) "not_run" else (if (identical(dp$verdict, "infeasible")) "fail" else dp$verdict),
    detail = dof_detail)
  checks[[length(checks) + 1]] <- list(
    id = "collinearity",                verdict = if (is.null(cl)) "not_run" else if (identical(cl$verdict, "not_computable")) "not_run" else cl$verdict,
    detail = if (is.null(cl)) "not computed"
      else if (identical(cl$verdict, "not_computable")) (cl$note %||% "not computable")
      else sprintf("max VIF %.1f on %s (%d rows)", cl$max_vif, cl$max_vif_term, cl$n_obs))
  # A missing FAAC is a *deviation from the specification*, not a failed pre-check: the design can
  # still be estimated, it just is not the model base spec section 9 describes. Marking it "fail"
  # would have reported every Design B card as failed for a reason that is recorded on the card.
  checks[[length(checks) + 1]] <- list(
    id = "faac_in_tier3_system", verdict = "deviation",
    detail = paste("the base-spec Tier-3 system includes FAAC, which has no metric-catalogue entry (the",
                   "monthly state panel landed 2026-10-16 and is Stage 3 gated, but it has no declared",
                   "monthly-to-annual aggregation and no outcome decision); the system is reduced to",
                   "{Y, log(oil), fx}"))
  verdicts <- vapply(checks, function(x) x$verdict, character(1))
  no_data <- o$coverage_status %in% c("declared_gap", "blocked")
  b_status <- if (no_data) "not_attempted"
    else if (any(verdicts == "fail")) "fail"
    else if (any(verdicts %in% c("flag", "inconclusive", "not_run", "deviation"))) "degraded"
    else "pass"
  card_diagnostics[[sprintf("%s__B", o$id)]] <- list(
    status = b_status,
    checks = checks,
    # A non-passing card names what stops it. For Design B that is always the same standing
    # deviation — the base-spec system cannot be built without FAAC — whether the card ends up
    # `degraded` or `fail`, so it is recorded on both rather than left blank on the milder one.
    blocker = if (no_data) sprintf("no usable series for this outcome (%s)", o$coverage_status)
      else design_verdicts$B$blocker,
    note = switch(b_status,
      not_attempted = "No pre-check could run: this outcome has no series over the window.",
      fail = "At least one pre-check fails on this outcome; the estimate would not be interpretable.",
      degraded = "Runs, but not as base spec section 9 specifies; the deviations are listed above.",
      "Every pre-check passes on this outcome.")
  )
  card_diagnostics[[sprintf("%s__B", o$id)]]$coverage_status <- o$coverage_status
}

for (o in outcomes) {
  pf <- prefit[[o$id]]
  checks <- list()
  verdicts <- if (length(pf$windows)) vapply(pf$windows, function(x) x$verdict, character(1)) else character(0)
  best <- if (any(verdicts == "pass")) names(verdicts)[which(verdicts == "pass")[[1]]] else NA_character_
  if (identical(pf$verdict, "not_attempted")) {
    checks[[1]] <- list(id = "pretreatment_fit", verdict = "not_run", detail = pf$note)
  } else {
    for (wn in names(pf$windows)) {
      w <- pf$windows[[wn]]
      checks[[length(checks) + 1]] <- list(
        id = paste0("pretreatment_fit:", wn),
        verdict = w$verdict,
        detail = if (is.null(w$pre_rmse)) (w$note %||% "not run")
        else sprintf("pre-RMSPE %.4g vs %.2f x pre SD %.4g (ratio %.3f), %d pre years, %d donors with weight",
                     w$pre_rmse, pre_frac, w$pre_sd, w$ratio, w$pre_years, w$n_donors_with_weight))
    }
  }
  checks[[length(checks) + 1]] <- list(
    id = "donor_pool_coverage", verdict = "computed",
    detail = sprintf("%d donors x %d predictors; Venezuela's oil-rents series ends 2014 (C-19)",
                     length(donor_countries), length(donor_metrics)))
  card_diagnostics[[sprintf("%s__C", o$id)]] <- list(
    status = switch(pf$verdict,
                    pass = "pass",
                    infeasible_weak_pre_fit = "fail",
                    "not_attempted"),
    checks = checks,
    blocker = switch(pf$verdict,
                     infeasible_weak_pre_fit = paste(
                       "no candidate treated window lets any convex combination of the donors track",
                       "Nigeria's pre-treatment path: best pre-RMSPE exceeds 0.10 x the pre-period",
                       "outcome SD"),
                     if (identical(pf$verdict, "not_attempted")) pf$note else NA_character_),
    note = switch(pf$verdict,
                  pass = sprintf("Pre-treatment fit passes at window(s): %s", paste(best, collapse = ", ")),
                  infeasible_weak_pre_fit = "Reported infeasible rather than estimated, per PHASES.md's Stage 5 gate",
                  "No candidate window is testable for this outcome")
  )
  card_diagnostics[[sprintf("%s__C", o$id)]]$coverage_status <- o$coverage_status
}

# consistency guard: a design cannot pass its pre-check on an outcome with no usable series
for (nm in names(card_diagnostics)) {
  cd <- card_diagnostics[[nm]]
  if (identical(cd$coverage_status, "blocked") || identical(cd$coverage_status, "declared_gap")) {
    if (identical(cd$status, "pass")) {
      stop(sprintf("%s: a %s outcome cannot pass its pre-check", nm, cd$coverage_status))
    }
  }
  # A status that is not "pass" must name what stops it. A card saying "fail" with no blocker is
  # the kind of gap PHASES.md Stage 6 forbids on a model card ("never rendered with a gap").
  if (!identical(cd$status, "pass") && (is.null(cd$blocker) || is.na(cd$blocker))) {
    stop(sprintf("%s: status '%s' with no blocker recorded", nm, cd$status))
  }
  cd$vintage <- vintage
  cd$source <- sprintf("registry/diagnostics/%s/diagnostics.json", vintage)
  card_diagnostics[[nm]] <- cd
}

# The design-level verdict is computed from the cards rather than asserted, so the summary cannot
# say "candidate" while every testable outcome of that design has failed its gate. This is the
# mistake the first draft made with Family C: the design looked alive at the design level and dead
# on all three outcomes it could actually be attempted on.
for (d in names(design_verdicts)) {
  ids <- grep(sprintf("__%s$", d), names(card_diagnostics), value = TRUE)
  st <- vapply(ids, function(k) card_diagnostics[[k]]$status, character(1))
  design_verdicts[[d]]$card_status_counts <- as.list(table(st))
  design_verdicts[[d]]$n_outcomes_pass <- sum(st == "pass")
  design_verdicts[[d]]$n_outcomes_attempted <- sum(st %in% c("pass", "degraded", "fail"))
  design_verdicts[[d]]$status <- if (identical(d, "A")) "dropped"
    else if (sum(st == "pass") > 0) "candidate"
    else if (sum(st == "fail") > 0) if (sum(st %in% c("pass", "degraded")) == 0) "infeasible" else "degraded"
    else if (sum(st == "degraded") > 0) "degraded"
    else "not_attempted"
  design_verdicts[[d]]$status_basis <- sprintf(
    "computed from the %d cards: %s", length(ids),
    paste(sprintf("%s=%d", names(table(st)), as.integer(table(st))), collapse = ", "))
  if (identical(design_verdicts[[d]]$status, "infeasible")) {
    first_fail <- ids[st == "fail"][[1]]
    design_verdicts[[d]]$blocker <- card_diagnostics[[first_fail]]$blocker
    design_verdicts[[d]]$next_step <- paste(
      "either a wider donor pool, or an estimand the pool can support (the fit on first",
      "differences is far better than on levels for u5mr, which is a different question)")
  }
}

# The observed share of the spine is a number the base owns, so it is computed rather than written into
# the prose: the 2026-10-11 wording asserted "10.1%" literally and would have gone on asserting it after
# the Brent, FAAC and UCDP landings moved the share to 16.2% (C-48).
spine_counts <- q("select observation_type, count(*) as n from main_analytics.fact_metric group by 1")
spine_total <- sum(spine_counts$n)
spine_share <- spine_counts$n[spine_counts$observation_type == "observed"] / spine_total

# ------------------------------------------------------------------------------------------
# write the artifacts
# ------------------------------------------------------------------------------------------
diagnostics <- list(
  schema_version = SCHEMA_VERSION,
  stage = STAGE,
  layer = "pre-analysis diagnostics and design validation",
  vintage = vintage,
  generated_at = generated_at,
  generator = list(script = GENERATOR, git_sha = git_sha, r_version = R.version.string),
  spec = "analysis/specs/diagnostics.yml",
  inputs = list(base = "data/analytics.duckdb",
                quality_report = sprintf("registry/quality/%s/report.json", vintage),
                grain = "native observations (fact_observation_native), study window floor 1999-01-01"),
  grain_decision = list(
    primary = "native",
    forbidden = "fact_metric monthly spine",
    observed_rows = spine_counts$n[spine_counts$observation_type == "observed"],
    spine_rows = spine_total,
    observed_fraction = round(spine_share, 6),
    reason = spec_get(c("grain", "forbidden_reason"))),
  series = series_diag,
  cointegration = cointegration,
  cointegration_monthly = cointegration_monthly,
  shock_visibility = shock_visibility,
  dose = dose,
  prefit = prefit,
  dof_power = dof_power,
  collinearity = collinearity,
  design_verdicts = design_verdicts,
  cards = card_diagnostics,
  spec_echo = list(
    alpha = alpha,
    min_observations_unit_root = min_obs_unit_root,
    cointegration_K = coint_K,
    shock_min_observed_in_band = min_in_band,
    pre_rmse_threshold_frac_of_sd = pre_frac,
    tier3_lag_max = lag_max,
    min_dof = min_dof,
    vif_flag = vif_flag,
    vif_fail = vif_fail)
)

json_path <- file.path(out_dir, "diagnostics.json")
writeLines(jsonlite::toJSON(diagnostics, auto_unbox = TRUE, pretty = TRUE, null = "null",
                            na = "null", digits = 6),
           json_path, useBytes = TRUE)

# ------------------------------------------------------------------------------------------
# the human-readable page
# ------------------------------------------------------------------------------------------
fmt <- function(x, d = 3) if (is.null(x) || length(x) != 1 || is.na(x)) "—" else format(round(as.numeric(x), d), trim = TRUE)
monthly_entry <- series_diag[["cpi_index_monthly"]]
monthly_md <- if (is.null(monthly_entry)) character(0) else c(
  "## Design B's second outcome — the monthly price level (C-85)",
  "",
  sprintf("`%s`: **%d** native monthly observations, %s -> %s; integration order **%s** (%s).",
          monthly_entry$metric_id, monthly_entry$n_observations,
          monthly_entry$first_month %||% "?", monthly_entry$last_month %||% "?",
          ifelse(is.na(monthly_entry$order_of_integration), "not tested",
                 as.character(monthly_entry$order_of_integration)),
          ifelse(isTRUE(monthly_entry$decisive), "decisive", "inconclusive")),
  if (!is.null(cointegration_monthly)) c(
    sprintf("Cointegration against log Brent at the same grain: **%d** months, rank **%s** (%s).",
            cointegration_monthly$n_observations,
            ifelse(is.null(cointegration_monthly$rank), "not run",
                   as.character(cointegration_monthly$rank)),
            cointegration_monthly$verdict %||% "not_run")) else "Cointegration against log Brent: not run.",
  "")

md <- c(
  sprintf("# Stage 5 pre-analysis diagnostics — vintage %s", vintage),
  "",
  "Generated by `analysis/R/02_diagnostics.R` from the analytical base and `analysis/specs/diagnostics.yml`.",
  "Every number here is a pre-check computed before any estimate exists. Independent recomputation:",
  "`tests/verify_stage5.py`.",
  "",
  "## Grain",
  "",
  sprintf("All tests run on **native observations**, never on the monthly spine: %.1f%% of spine rows are",
          spine_share * 100),
  "observed, and a unit-root test on interpolated data tests the interpolator.",
  "",
  monthly_md,
  "## Design verdicts",
  "",
  "| Design | Status | Deciding diagnostic |",
  "|---|---|---|",
  sprintf("| A — state dose-response DiD | **%s** | dose variation (%s of %d dose values) |",
          design_verdicts$A$status,
          fmt(sum(vapply(dose_entries, function(d) d$n_non_null, numeric(1))), 0), panel_total),
  sprintf("| B — national VECM / ARDL | **%s** | cointegration rank, DoF, collinearity |", design_verdicts$B$status),
  sprintf("| C — synthetic control | **%s** | pre-treatment fit |", design_verdicts$C$status),
  "",
  "## Shock-window visibility",
  "",
  "| Window | Months | Visible on | Single anchor only |",
  "|---|---|---|---|",
  vapply(shock_visibility, function(s) sprintf("| %s | %d | %s | %s |", s$label, s$n_months,
                                               if (length(s$visible_on)) paste(s$visible_on, collapse = ", ") else "—",
                                               if (length(s$single_anchor_on)) sprintf("%d metrics", length(s$single_anchor_on)) else "—"),
         character(1)),
  "",
  "## Dose validation (Family A)",
  "",
  "| Axis | Column | Present | States with dose | Verdict |",
  "|---|---|---|---|---|",
  vapply(dose_entries, function(d) sprintf("| %s | `%s` | %d | %s | **%s** |", d$id,
                                           d$column %||% "—", d$n_non_null,
                                           fmt(d$n_states_with_dose, 0), d$verdict), character(1)),
  "",
  # The distribution, not its mode. The 2026-10-16 wording took `dose_status_values$dose_status[[1]]`
  # and printed "Dose status on every row: `declared_gap`" — true only while every row was a gap. Once
  # the dose landed the modal status stayed `declared_gap`, so the sentence kept asserting "every row"
  # about a panel that is now 4,104 observed rows out of 12,358 (found 2026-10-17, C-48).
  sprintf("State panel: %d rows = %d states x %d months. Dose status per row: %s.",
          panel_total, dose$n_states, panel_total / dose$n_states,
          paste(sprintf("%s `%s`", format(dose$dose_status_values$n, big.mark = ",", trim = TRUE),
                        dose$dose_status_values$dose_status), collapse = " · ")),
  "",
  "## Integration order (native grain)",
  "",
  "| Series | n | ADF (drift) | KPSS | PP | Order |",
  "|---|---|---|---|---|---|",
  vapply(names(series_diag), function(k) {
    s <- series_diag[[k]]
    sprintf("| %s | %d | %s | %s | %s | %s |", s$series_label %||% s$metric_id, s$n_observations,
            s$tests$adf_drift$verdict %||% "—", s$tests$kpss$verdict %||% "—",
            s$tests$pp$verdict %||% "—",
            if (is.na(s$order_of_integration %||% NA)) "not tested" else sprintf("I(%d)%s",
                                                                                 s$order_of_integration,
                                                                                 if (isTRUE(s$decisive)) "" else "*"))
  }, character(1)),
  "",
  "`*` = the three tests did not agree; the series is carried as I(1) (the conservative branch).",
  "",
  "## Cointegration (Johansen, {Y, log(oil), fx})",
  "",
  "| Outcome | n | Trace rank | Max-eig rank | Taken | Estimator |",
  "|---|---|---|---|---|---|",
  vapply(outcome_ids, function(oid) {
    co <- cointegration[[oid]]
    if (is.null(co) || is.na(co$rank %||% NA)) {
      sprintf("| %s | %s | not run | — | — | — |", oid, fmt(co$n_observations %||% NA, 0))
    } else {
      sprintf("| %s | %d | %d | %d | %d | %s%s |", oid, co$n_observations, co$rank_trace,
              co$rank_eigen, co$rank, co$recommended_estimator,
              if (isTRUE(co$rank_borderline)) " *" else "")
    }
  }, character(1)),
  "",
  "FAAC is absent from the metric catalogue, so the base-spec Tier-3 system is reduced. The deviation",
  "travels onto every Design B card.",
  "",
  "`*` = the rank is marginal: the deciding statistic sits close to its critical value, and an",
  "independent implementation (`tests/verify_stage5.py`) can reach a different rank under a different",
  "deterministic-term convention. Recorded on the card rather than reported as settled.",
  "",
  "## Pre-treatment fit (Family C)",
  "",
  "The gate is the globally optimal simplex fit to the pre-treatment path (a QP), so a failure is a",
  "statement about the donor pool, not about an optimiser. `ratio` is pre-RMSPE / pre-period outcome",
  "SD; the threshold is declared in `diagnostics.yml`.",
  "",
  "| Outcome | Window | Pre yrs | Pre-RMSPE | Pre SD | ratio | best 1 donor | NGA level in hull | ratio on diffs | Synth | Verdict |",
  "|---|---|---|---|---|---|---|---|---|---|---|",
  unlist(lapply(outcome_ids, function(oid) {
    p <- prefit[[oid]]
    if (!length(p$windows)) return(sprintf("| %s | — | — | — | — | — | — | — | — | — | %s |", oid, p$verdict))
    vapply(names(p$windows), function(wn) {
      w <- p$windows[[wn]]
      if (is.null(w$pre_rmse)) {
        return(sprintf("| %s | %s | %s | not run | — | — | — | — | — | — | %s |", oid, wn,
                       fmt(w$pre_years, 0), w$verdict))
      }
      sprintf("| %s | %s | %d | %s | %s | %s | %s | %s | %s | %s | %s |", oid, wn, w$pre_years,
              fmt(w$pre_rmse, 4), fmt(w$pre_sd, 4), fmt(w$ratio), fmt(w$best_single_donor_rmse, 4),
              if (isTRUE(w$treated_outside_donor_mean_interval)) "no" else "yes",
              fmt(w$ratio_on_differences, 3), fmt(w$synth_v_optimized_rmse, 3), w$verdict)
    }, character(1))
  })),
  "",
  "`Synth` is the estimator design spec section 11 names for this family, recorded here as a",
  "cross-check only. On this donor pool its default V search returns a fit worse than the best single",
  "donor, which Stage 6 has to fix before its weights can be trusted.",
  "",
  "## Degrees of freedom and the detectable effect (Family B)",
  "",
  "MDE is the smallest tenure effect this design could detect at 80% power, 5% significance, from the",
  "noise scale of a thin baseline model — computed before any estimate exists. `xSD` expresses it in",
  "units of the residual standard deviation, so a value of 1 means the design can only see effects as",
  "large as the series' own residual variation.",
  "",
  "| Outcome | Annual rows | Params | Residual DoF | sigma | cond(X) | MDE xSD (Tier-3) | MDE xSD (leaner) |",
  "|---|---|---|---|---|---|---|---|",
  vapply(outcome_ids, function(oid) {
    d <- dof_power[[oid]]
    if (is.null(d$mde_strata)) {
      return(sprintf("| %s | %s | — | — | — | — | — | — |", oid, fmt(d$n_observations, 0)))
    }
    sprintf("| %s | %d | %d | %d | %s | %s | %s – %s | %s – %s |", oid, d$n_observations,
            d$n_parameters, d$dof, fmt(d$residual_sd_baseline, 4), fmt(d$design_condition_number, 4),
            fmt(min(unlist(d$mde_strata_in_sd_units)), 2), fmt(max(unlist(d$mde_strata_in_sd_units)), 2),
            fmt(min(unlist(d$mde_strata_reduced_in_sd_units %||% NA)), 2),
            fmt(max(unlist(d$mde_strata_reduced_in_sd_units %||% NA)), 2))
  }, character(1)),
  "",
  "## Collinearity",
  "",
  "| Outcome | Max VIF | Term | Verdict |",
  "|---|---|---|---|",
  vapply(outcome_ids, function(oid) {
    cl <- collinearity[[oid]]
    sprintf("| %s | %s | %s | %s |", oid, fmt(cl$max_vif, 2), cl$max_vif_term %||% "—", cl$verdict)
  }, character(1)),
  "",
  "## What was dropped, on the record",
  "",
  sprintf("- **Family A** — %s.", design_verdicts$A$dropped_because),
  sprintf("- **Family B** — %s.", design_verdicts$B$degraded_because),
  ""
)
writeLines(md, file.path(out_dir, "report.md"), useBytes = TRUE)

cat(sprintf("\nPASS - diagnostics written to registry/diagnostics/%s/\n", vintage))
cat(sprintf("  %s\n  %s\n", basename(json_path), "report.md"))
cat("  Next: Rscript analysis/R/01_build_dags.R  (attaches the diagnostics to the 36 cards)\n")
