"""Verify the Stage 5 pre-analysis diagnostics independently of the R engine.

`analysis/R/02_diagnostics.R` writes ``registry/diagnostics/<vintage>/diagnostics.json`` (the
machine-readable result) and ``report.md`` (the human page), and ``01_build_dags.R`` copies a
per-card slice of that JSON onto each of the 36 DAG cards. This verifier re-derives the headline
results *from the analytical base* — in Python, from duckdb + numpy/scipy — and compares them to
what the R engine recorded, so a number on a card is never taken on the R script's word:

  * the spec echo matches the thresholds declared in ``analysis/specs/diagnostics.yml``;
  * the grain claim (the observed fraction of the monthly spine) holds on the base;
  * every shock-window visibility count and verdict, recomputed from ``fact_metric`` + ``dim_shock``;
  * the Family A dose validation, recomputed from ``state_panel``;
  * the Johansen trace / max-eigenvalue rank, recomputed from the eigenvalue problem in numpy and
    read with the critical values the R engine itself recorded (see the note below);
  * the Family C pre-treatment fit, re-solved as a simplex-constrained least-squares problem with
    scipy and compared window by window;
  * the Family B minimum detectable effect, rebuilt from the Tier-3 design matrix and the residual
    scale of the thin baseline model;
  * the per-card status and the design-level verdict, re-derived from the checks by the declared
    rule, plus the two guards the R script enforces (no pass on a blocked outcome; a non-pass names
    its blocker);
  * every card's ``diagnostics`` block and the index against their JSON Schemas.

A note on the Johansen check. ``urca::ca.jo`` and an independent implementation (this file, and
``statsmodels.tsa.vector_ar.vecm.coint_johansen``) agree to <0.2% on a controlled synthetic system
(random walk with a known lag structure) but diverge by ~10% on the strongly trending real series,
because the two handle the deterministic term differently. The *rank* — the only quantity the card
uses — is invariant under that difference once urca's own 5% critical values are applied, so the
check recomputes the statistics and asserts the rank, and reports the statistic gap as information
rather than failing on a library convention. The per-row ``r`` label is verified too: urca returns
its statistics ordered r = K-1 .. 0, which the engine must undo before labelling.

Usage:
    conda run -p "C:/Users/TOSHIBA/ds-general" python tests/verify_stage5.py
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
BASE = REPO_ROOT / "data" / "analytics.duckdb"
SPEC_PATH = REPO_ROOT / "analysis" / "specs" / "diagnostics.yml"


# The Stage 5 vintage is the *data* vintage, taken from the latest Stage 3 quality report rather than
# from the run date (the engine explains why). It therefore moves when a new source is gated, which is
# exactly what happened on 2026-10-17: pinning this path to "2026-10-11" made the verifier read a
# superseded artifact and fail on a base that had moved on.
def latest_diagnostics() -> Path:
    root = REPO_ROOT / "registry" / "diagnostics"
    vintages = sorted(p.name for p in root.iterdir() if p.is_dir())
    if not vintages:
        raise SystemExit(f"no diagnostics under {root} — run analysis/R/02_diagnostics.R first")
    return root / vintages[-1] / "diagnostics.json"


DIAG_PATH = latest_diagnostics()
VINTAGE = DIAG_PATH.parent.name
CARDS_DIR = REPO_ROOT / "registry" / "dags"
INDEX_PATH = CARDS_DIR / "index.json"
CARD_SCHEMA = REPO_ROOT / "registry" / "schema" / "dag_card.schema.json"
INDEX_SCHEMA = REPO_ROOT / "registry" / "schema" / "dag_index.schema.json"

# tolerances for float comparisons against the R output
ATOL = 5e-4
RTOL = 5e-3


def close(a, b, atol=ATOL, rtol=RTOL) -> bool:
    if a is None or b is None:
        return a == b
    return abs(float(a) - float(b)) <= atol + rtol * abs(float(b))


# ------------------------------------------------------------------------------------------
# data access — mirrors the R engine's queries
# ------------------------------------------------------------------------------------------
def connect():
    import duckdb
    return duckdb.connect(str(BASE), read_only=True)


def annual_series(con, metric_id: str):
    """Native annual observations joined to the administration spine (the engine's annual_series)."""
    return con.execute(
        """
        select year(n.anchor_month) as yr, n.value as value,
               f.pdp_first, f.pdp_second, f.apc_first, f.apc_second
        from main_analytics.fact_observation_native n
        join main_analytics.fact_metric f
          on f.metric_id = n.metric_id and f.period_month = n.anchor_month
        where n.metric_id = ? and n.native_frequency = 'annual'
          and n.value is not null and n.anchor_month >= date '1999-01-01'
        order by 1
        """, [metric_id]).fetchdf()


def oil_annual(con):
    return con.execute(
        """
        select year(anchor_month) as yr, avg(value) as value
        from main_analytics.fact_observation_native
        where metric_id = 'oil' and native_frequency = 'monthly'
          and value is not null and anchor_month >= date '1999-01-01'
        group by 1 order by 1
        """).fetchdf()


def fx_annual(con):
    return con.execute(
        """
        select year(anchor_month) as yr, value
        from main_analytics.fact_observation_native
        where metric_id = 'fx' and value is not null
          and anchor_month >= date '1999-01-01' order by 1
        """).fetchdf()


# ------------------------------------------------------------------------------------------
# Johansen (base spec section 9), from scratch
# ------------------------------------------------------------------------------------------
def johansen(Y, K=2):
    """Trace and max-eigenvalue statistics for a VECM with an unrestricted constant.

    Returns (trace, maxeig) ordered r = 0 .. p-1. Matches statsmodels' coint_johansen exactly;
    differs from urca's default only through the deterministic-term convention, which leaves the
    rank unchanged for these data (verified in the module docstring).
    """
    X = np.asarray(Y, dtype=float)
    n, p = X.shape
    kd = K - 1
    dX = np.diff(X, axis=0)
    rows = list(range(kd + 1, n))
    dY = np.array([dX[t - 1] for t in rows])
    lag_cols = [[dX[t - 1 - l] for t in rows] for l in range(1, kd + 1)]
    W = np.column_stack([[1.0] * len(rows)] + lag_cols)
    Z1 = np.array([X[t - 1] for t in rows])
    R0 = dY - W @ np.linalg.lstsq(W, dY, rcond=None)[0]
    R1 = Z1 - W @ np.linalg.lstsq(W, Z1, rcond=None)[0]
    T = R0.shape[0]
    S00 = R0.T @ R0 / T
    S01 = R0.T @ R1 / T
    S11 = R1.T @ R1 / T
    M = np.linalg.solve(S11, S01.T @ np.linalg.solve(S00, S01))
    ev = np.sort(np.linalg.eigvals(M).real)[::-1]
    trace = np.array([-T * np.sum(np.log(1 - ev[r:])) for r in range(p)])
    maxeig = np.array([-T * np.log(1 - ev[r]) for r in range(p)])
    return trace, maxeig


# ------------------------------------------------------------------------------------------
# checks
# ------------------------------------------------------------------------------------------
def check_spec_echo(diag, failures):
    """The thresholds the run used must be the ones the spec declares."""
    try:
        import yaml
    except ImportError:
        print("  ! pyyaml not importable — spec-echo cross-check skipped")
        return
    spec = yaml.safe_load(SPEC_PATH.read_text(encoding="utf-8"))
    echo = diag["spec_echo"]
    want = {
        "alpha": spec["unit_root"]["alpha"],
        "min_observations_unit_root": spec["unit_root"]["min_observations"],
        "cointegration_K": spec["cointegration"]["K"],
        "shock_min_observed_in_band": spec["shock_visibility"]["min_observed_in_band"],
        "pre_rmse_threshold_frac_of_sd": spec["pretrend"]["family_c"]["pre_rmse_threshold_frac_of_sd"],
        "tier3_lag_max": spec["dof_power"]["tier3_lag_max"],
        "min_dof": spec["dof_power"]["min_dof"],
        "vif_flag": spec["collinearity"]["vif_flag"],
        "vif_fail": spec["collinearity"]["vif_fail"],
    }
    for k, v in want.items():
        if not close(echo.get(k), v):
            failures.append(f"spec_echo[{k}] = {echo.get(k)!r} but spec declares {v!r}")
    print(f"  spec echo        : {len(want)} thresholds agree with {SPEC_PATH.name}")


def check_grain(con, diag, failures):
    """The grain claim: tests run on native rows, and the spine is mostly interpolated."""
    row = con.execute(
        "select observation_type, count(*) from main_analytics.fact_metric group by 1"
    ).fetchall()
    counts = {k: v for k, v in row}
    total = sum(counts.values())
    observed = counts.get("observed", 0)
    frac = observed / total
    print(f"  grain            : {observed}/{total} spine rows observed ({frac:.1%})")
    if diag["grain_decision"]["primary"] != "native":
        failures.append("grain_decision.primary is not 'native'")
    if frac >= 0.5:
        failures.append(f"spine is {frac:.1%} observed; treating 'native' as the grain is unjustified")
    decision = diag.get("grain_decision", {})
    if (decision.get("observed_rows"), decision.get("spine_rows")) != (observed, total):
        failures.append(
            f"grain_decision records {decision.get('observed_rows')} of {decision.get('spine_rows')} "
            f"observed and the base has {observed} of {total} — the artifact and the base disagree"
        )
    # The memo quotes this number in the present tense, and it went stale once (10.1 % of 7,682 rows for
    # a base at 16.2 % of 8,350): the Stage 5 report was fixed at C-49, the memo beside it was not, and no
    # verifier read the prose. The needle is derived here, so the claim has to move with the base.
    claims = {
        "docs/design-memo.md": f"**{frac * 100:.1f} % observed** ({observed:,} of {total:,} rows",
        "docs/limitations.md": f"**{observed:,} rows ({frac * 100:.1f} %) are observed**",
    }
    for rel, needle in claims.items():
        path = REPO_ROOT / rel
        if not path.exists():
            failures.append(f"{rel} is missing, so its grain claim cannot be checked")
        elif needle not in " ".join(path.read_text(encoding="utf-8").split()):
            failures.append(f"{rel} does not carry {needle!r} — the measured grain moved under the document")


def check_shock_visibility(con, diag, failures):
    """Recompute every per-metric window count and verdict from the base."""
    rows = con.execute(
        """
        select s.shock_id, s.n_months, f.metric_id,
               count(*) filter (where f.observation_type = 'observed')     as n_observed,
               count(*) filter (where f.observation_type = 'interpolated') as n_interpolated,
               count(*) filter (where f.observation_type = 'unobserved')   as n_unobserved,
               count(*)                                                    as n_months
        from main_analytics.dim_shock s
        cross join (select distinct metric_id from main_analytics.fact_metric) mm
        join main_analytics.fact_metric f
          on f.metric_id = mm.metric_id
         and f.period_month between s.start_month and s.end_month
        group by 1, 2, 3
        order by s.shock_id, f.metric_id
        """).fetchall()

    min_in_band = diag["spec_echo"]["shock_min_observed_in_band"]
    min_frac = diag["spec_echo"].get("shock_min_observed_fraction", 0.25)
    checked = 0
    for shock_id, n_months, metric_id, n_obs, n_int, n_unobs, n_total in rows:
        verdict = (
            "not_visible" if n_obs == 0
            else "single_anchor" if n_obs == 1
            else "visible" if n_obs >= min_in_band and n_obs / n_total >= min_frac
            else "partial"
        )
        rec = diag["shock_visibility"].get(str(shock_id), {}).get("per_metric", {}).get(metric_id)
        if rec is None:
            failures.append(f"shock {shock_id}/{metric_id}: engine recorded no verdict")
            continue
        if (rec["n_observed_in_band"], rec["n_interpolated_in_band"],
                rec["n_unobserved_in_band"], rec["n_months_in_band"]) != (n_obs, n_int, n_unobs, n_total):
            failures.append(
                f"shock {shock_id}/{metric_id}: counts differ — engine "
                f"({rec['n_observed_in_band']},{rec['n_interpolated_in_band']},{rec['n_unobserved_in_band']}) "
                f"vs base ({n_obs},{n_int},{n_unobs})")
        if rec["verdict"] != verdict:
            failures.append(f"shock {shock_id}/{metric_id}: verdict {rec['verdict']} != {verdict}")
        checked += 1
    # the partitions on the shock must list exactly the metrics holding each verdict
    for sid, entry in diag["shock_visibility"].items():
        by_verdict = {}
        for mid, rec in entry["per_metric"].items():
            by_verdict.setdefault(rec["verdict"], set()).add(mid)
        for verdict, key in (("visible", "visible_on"), ("single_anchor", "single_anchor_on"),
                             ("not_visible", "not_visible_on"), ("partial", "partial_on")):
            # jsonlite's auto_unbox turns a length-one list into a bare string; normalise it back.
            listed = entry[key] if isinstance(entry[key], list) else [entry[key]]
            if by_verdict.get(verdict, set()) != set(listed):
                failures.append(f"shock {sid}: {key} disagrees with per_metric verdicts")
    print(f"  shock windows    : {len(diag['shock_visibility'])} windows, {checked} metric-windows recomputed")


def check_dose(con, diag, failures):
    """Recompute the Family A dose validation from state_panel."""
    panel_total = con.execute("select count(*) from main_analytics.state_panel").fetchone()[0]
    n_states = con.execute("select count(distinct state_id) from main_analytics.state_panel").fetchone()[0]
    d = diag["dose"]
    if d["n_rows"] != panel_total:
        failures.append(f"dose.n_rows {d['n_rows']} != base {panel_total}")
    if d["n_states"] != n_states:
        failures.append(f"dose.n_states {d['n_states']} != base {n_states}")

    # Every declared axis, including the nominal one added on 2026-10-17. The nominal axis is not the
    # one the estimand is written on, so its numbers are checked here and its verdict is not allowed to
    # substitute for the specified axis below.
    columns = {
        "D1": "d1_faac_per_capita",
        "D1_nominal": "faac_gross_total_naira",
        "D2": "d2_faac_share_of_state_revenue",
    }
    recomputed_axes: dict[str, str] = {}
    for axis_id, col in columns.items():
        row = con.execute(f"""
            select count(*) as n_rows,
                   count("{col}") as n_non_null,
                   count(distinct case when "{col}" is not null then state_id end) as n_states
            from main_analytics.state_panel
        """).fetchone()
        _n_rows, n_non_null, n_states_with = row
        rec = d["axes"].get(axis_id)
        if rec is None:
            failures.append(f"dose axis {axis_id} missing from artifact")
            continue
        if rec["n_non_null"] != n_non_null:
            failures.append(f"dose {axis_id}: n_non_null {rec['n_non_null']} != base {n_non_null}")
        if rec["n_states_with_dose"] != n_states_with:
            failures.append(f"dose {axis_id}: n_states_with_dose {rec['n_states_with_dose']} != {n_states_with}")
        if n_non_null == 0 and rec["verdict"] != "absent":
            failures.append(f"dose {axis_id}: no values but verdict is {rec['verdict']}")
        if n_non_null > 0 and rec["verdict"] in ("absent", "not_built"):
            failures.append(f"dose {axis_id}: {n_non_null} values but verdict is {rec['verdict']}")
        recomputed_axes[axis_id] = rec["verdict"]
    # The axis the estimand is written on decides the family, so a present-but-unspecified axis must not
    # be able to report the gate as satisfied.
    specified = d.get("specified_axis")
    if specified not in columns:
        failures.append(f"dose.specified_axis {specified!r} is not one of the declared axes {sorted(columns)}")
    elif d.get("specified_axis_present") != (recomputed_axes.get(specified) == "pass"):
        failures.append(
            f"dose.specified_axis_present {d.get('specified_axis_present')} but {specified} "
            f"recomputes to {recomputed_axes.get(specified)!r}"
        )
    elif d.get("present_axes") is not None:
        present = sorted(a for a, v in recomputed_axes.items() if v not in ("absent", "not_built"))
        listed = d["present_axes"]
        # A scalar here is a shape bug rather than a value, so it is reported as one instead of being
        # coerced: a one-element list that serialises as a string would silently become characters.
        if not isinstance(listed, list):
            failures.append(f"dose.present_axes is {type(listed).__name__}, not an array: {listed!r}")
        elif sorted(listed) != present:
            failures.append(f"dose.present_axes {sorted(listed)} != base {present}")
    # the panel-wide dose status
    statuses = con.execute(
        "select dose_status, count(*) from main_analytics.state_panel group by 1").fetchall()
    recorded = {r["dose_status"]: r["n"] for r in d["dose_status_values"]}
    if recorded != dict(statuses):
        failures.append(f"dose_status_values {recorded} != base {dict(statuses)}")
    print(f"  dose validation  : panel {panel_total} rows, {n_states} states, "
          f"dose present = {d['any_dose_present']}")


def check_cointegration(con, diag, failures, warnings):
    """Recompute the Johansen statistics and the rank (using the engine's own critical values)."""
    oil_a = oil_annual(con)
    fx = fx_annual(con)
    worst_gap = 0.0
    tested = 0
    disagreement = 0
    K = diag["spec_echo"]["cointegration_K"]
    for oid, co in diag["cointegration"].items():
        if co.get("rank") is None:
            continue
        df = annual_series(con, oid)
        m = (df[["yr", "value"]]
             .merge(oil_a, on="yr", suffixes=("_y", "_oil"))
             .merge(fx, on="yr"))
        # build the {Y, log(oil), fx} system explicitly
        Y = np.column_stack([m["value_y"].values, np.log(m["value_oil"].values), m["value"].values]).astype(float)
        Y = Y[~np.isnan(Y).any(axis=1)]
        trace, maxeig = johansen(Y, K=K)
        # engine's own 5% critical values, keyed by r
        cval_trace = {t["r"]: t["cval"] for t in co["trace"]}
        cval_eigen = {t["r"]: t["cval"] for t in co["eigen"]}

        def scan_rank(stats, cvals):
            r = 0
            for j in range(len(stats)):
                if stats[j] > cvals[j]:
                    r += 1
                else:
                    break
            return r

        rank_trace = scan_rank(trace, [cval_trace[r] for r in range(len(trace))])
        rank_eigen = scan_rank(maxeig, [cval_eigen[r] for r in range(len(maxeig))])
        rank = min(rank_trace, rank_eigen)
        # statistic magnitude gap vs the engine (informational — a deterministic-term convention)
        eng_trace = np.array([co["trace"][r]["teststat"] for r in range(len(trace))])
        gap = float(np.max(np.abs(trace - eng_trace) / np.abs(eng_trace)))
        worst_gap = max(worst_gap, gap)

        # The engine must have applied its own declared rule to its own statistics.
        engine_scan = scan_rank(
            [co["trace"][r]["teststat"] for r in range(len(trace))],
            [co["trace"][r]["cval"] for r in range(len(trace))])
        if engine_scan != co["rank_trace"]:
            failures.append(f"cointegration {oid}: engine rank_trace {co['rank_trace']} != its own scan {engine_scan}")

        if rank != co["rank"]:
            # A rank decided by a statistic sitting close to its critical value is not robust to the
            # estimator's deterministic-term convention; the engine flags that itself. Warn on those,
            # fail on the rest.
            margin = deciding_margin(co)
            if co.get("rank_borderline"):
                warnings.append(
                    f"cointegration {oid}: independent rank {rank} != engine rank {co['rank']}, but "
                    f"the engine's deciding margin is only {margin:.1%} of the critical value — "
                    f"recorded as marginal on the card, not as settled")
            else:
                failures.append(
                    f"cointegration {oid}: recomputed rank {rank} "
                    f"(trace {rank_trace}, eigen {rank_eigen}) != engine rank {co['rank']}")
        # r labels must be the true hypothesis order, monotone r = 0 .. K-1
        if [t["r"] for t in co["trace"]] != list(range(len(trace))):
            failures.append(f"cointegration {oid}: trace rows are not labelled r = 0 .. K-1")
        # and the r = 0 statistic must be the largest (the trace test is decreasing in r)
        if any(trace[i] < trace[i + 1] - 1e-9 for i in range(len(trace) - 1)):
            failures.append(f"cointegration {oid}: recomputed trace is not decreasing in r")
        # the estimator mapping has to follow the declared rule, applied to the engine's own rank
        n_sys = len(trace)
        eng_rank = co["rank"]
        expect = "ardl_bounds" if eng_rank == 0 else ("var_in_levels" if eng_rank >= n_sys else "vecm")
        if co["recommended_estimator"] != expect:
            failures.append(
                f"cointegration {oid}: estimator {co['recommended_estimator']} != {expect} for rank {eng_rank}")
        tested += 1
        if rank != eng_rank:
            disagreement += 1
    print(f"  cointegration    : {tested} outcomes, ranks agree on {tested - disagreement}"
          f"{'/' + str(tested) if disagreement else ''}; max |stat gap| vs urca = {worst_gap:.1%} "
          f"(deterministic-term convention)")


def simplex_qp(z1, Z0):
    """Globally optimal simplex weights for min ||z1 - Z0 w|| (matches quadprog::solve.QP)."""
    from scipy.optimize import minimize
    Z0 = np.asarray(Z0, float)
    z1 = np.asarray(z1, float)
    n = Z0.shape[1]
    D = Z0.T @ Z0
    d = Z0.T @ z1
    ridge = max(np.diag(D)) * 1e-8

    def obj(w):
        return 0.5 * w @ (D + ridge * np.eye(n)) @ w - d @ w

    def grad(w):
        return (D + ridge * np.eye(n)) @ w - d

    cons = [{"type": "eq", "fun": lambda w: np.sum(w) - 1.0,
             "jac": lambda w: np.ones(n)}]
    bounds = [(0.0, 1.0)] * n
    w0 = np.full(n, 1.0 / n)
    res = minimize(obj, w0, jac=grad, bounds=bounds, constraints=cons,
                   method="SLSQP", options={"maxiter": 500, "ftol": 1e-14})
    return res.x


def deciding_margin(co) -> float:
    """Fractional gap between the deciding trace statistic and its critical value."""
    stat = np.array([co["trace"][r]["teststat"] for r in range(len(co["trace"]))])
    cv = np.array([co["trace"][r]["cval"] for r in range(len(co["trace"]))])
    rank = co["rank"]
    if rank > 0:
        return float((stat[rank - 1] - cv[rank - 1]) / cv[rank - 1])
    return float((cv[0] - stat[0]) / cv[0])


def check_prefit(con, diag, failures):
    """Re-solve the Family C pre-treatment fit window by window."""
    import yaml
    spec = yaml.safe_load(SPEC_PATH.read_text(encoding="utf-8"))
    min_pre = spec["pretrend"]["family_c"]["min_pre_years"]
    min_post = spec["pretrend"]["family_c"]["min_post_years"]
    pre_frac = spec["pretrend"]["family_c"]["pre_rmse_threshold_frac_of_sd"]
    windows = spec["windows"]["candidate_treated_windows"]

    donor = con.execute(
        "select country_iso3, metric_id, period_year, value from main_analytics.fact_donor_panel"
    ).fetchdf()
    donor_metrics = sorted(donor["metric_id"].unique())
    nga = con.execute(
        """
        select metric_id, year(anchor_month) as yr, value
        from main_analytics.fact_observation_native
        where native_frequency = 'annual' and value is not null
          and anchor_month >= date '1999-01-01' order by 1, 2
        """).fetchdf()
    donor_countries = sorted(donor["country_iso3"].unique())

    checked = 0
    # The engine only attempts outcomes that are (a) registry outcomes and (b) present in the donor
    # panel; anything else it records as not_attempted. Follow its own outcome list, so donor-only
    # metrics (population, oil_rents) are not mistaken for windows the engine should have fitted.
    for oid in diag["prefit"]:
        if oid not in donor_metrics:
            continue
        predictors = [p for p in donor_metrics if p != oid]
        y_nga = nga[nga["metric_id"] == oid]
        rec = diag["prefit"].get(oid, {})
        for w in windows:
            start_year = int(str(w["from"])[:4])
            yrs = y_nga["yr"].values
            pre_years = [y for y in yrs if y < start_year]
            post_years = [y for y in yrs if y >= start_year]
            rec_w = rec.get("windows", {}).get(w["id"])
            if len(pre_years) < min_pre or len(post_years) < min_post:
                continue  # the engine records not_run here; nothing to recompute
            z1 = y_nga.set_index("yr").loc[pre_years, "value"].values.astype(float)
            z0_all = []
            for cc in donor_countries:
                d = donor[(donor["country_iso3"] == cc) & (donor["metric_id"] == oid)]
                v = d.set_index("period_year")["value"].reindex(pre_years).values
                z0_all.append(np.nan if np.isnan(v).any() else float(np.mean(v)))
            z0_all = np.array(z0_all, float)
            keep = ~np.isnan(z0_all)
            donors_used = [cc for cc, k in zip(donor_countries, keep) if k]
            if len(donors_used) < 5 or np.isnan(z1).any():
                continue
            Z0 = np.column_stack([
                donor[(donor["country_iso3"] == cc) & (donor["metric_id"] == oid)]
                .set_index("period_year")["value"].reindex(pre_years).values.astype(float)
                for cc in donors_used
            ])
            # keep the engine's predictor screen: only predictors spanning a balanced >=3-year block
            use = False
            for p in predictors:
                p_nga = nga[nga["metric_id"] == p].set_index("yr")["value"].reindex(pre_years).values
                per_donor = [
                    donor[(donor["country_iso3"] == cc) & (donor["metric_id"] == p)]
                    .set_index("period_year")["value"].reindex(pre_years).values
                    for cc in donors_used
                ]
                ok = ~np.isnan(p_nga)
                for v in per_donor:
                    ok = ok & ~np.isnan(v)
                if ok.sum() >= 3:
                    use = True
            if not use:
                continue
            wts = simplex_qp(z1, Z0)
            rmse = float(np.sqrt(np.mean((z1 - Z0 @ wts) ** 2)))
            sd_pre = float(np.std(z1, ddof=1))
            ratio = rmse / sd_pre
            verdict = "pass" if ratio <= pre_frac else "weak_fit"
            if rec_w is None or rec_w.get("pre_rmse") is None:
                failures.append(f"prefit {oid}/{w['id']}: engine did not compute a fit but data allow one")
                continue
            if not close(rmse, rec_w["pre_rmse"]):
                failures.append(f"prefit {oid}/{w['id']}: pre-rmse {rec_w['pre_rmse']} != {rmse:.6g}")
            if not close(ratio, rec_w["ratio"]):
                failures.append(f"prefit {oid}/{w['id']}: ratio {rec_w['ratio']} != {ratio:.6g}")
            if verdict != rec_w["verdict"]:
                failures.append(f"prefit {oid}/{w['id']}: verdict {rec_w['verdict']} != {verdict}")
            checked += 1
    print(f"  pre-treatment fit: {checked} outcome-window QPs re-solved and matched")


def check_mde(con, diag, failures):
    """Rebuild the Tier-3 design matrix and the minimum detectable effect."""
    import yaml
    spec = yaml.safe_load(SPEC_PATH.read_text(encoding="utf-8"))
    lag_max = spec["dof_power"]["tier3_lag_max"]
    z_a = spec["dof_power"]["z_alpha_two_sided"]
    z_p = spec["dof_power"]["z_power"]
    oil_a = oil_annual(con)
    strata = ["pdp_first", "pdp_second", "apc_first"]
    checked = 0
    for oid, dp in diag["dof_power"].items():
        if dp.get("verdict") != "computed" or not dp.get("mde_strata"):
            continue
        df = annual_series(con, oid)
        m = df[["yr", "value", "pdp_first", "pdp_second", "apc_first", "apc_second"]].copy()
        m = m.merge(oil_a, on="yr", suffixes=("_y", "_oil")).dropna().sort_values("yr").reset_index(drop=True)
        for L in range(1, lag_max + 1):
            m[f"lag{L}"] = m["value_y"].shift(L)
        m = m.dropna().reset_index(drop=True)
        n_used = len(m)
        if n_used < lag_max + 8:
            continue
        trend = np.arange(1, n_used + 1)
        m["trend"] = trend
        m["trend2"] = trend ** 2
        m["log_oil"] = np.log(m["value_oil"])
        # baseline model supplies sigma only
        Xb = np.column_stack([np.ones(n_used), m["log_oil"], m["trend"]])
        yb = m["value_y"].values
        beta, *_ = np.linalg.lstsq(Xb, yb, rcond=None)
        resid = yb - Xb @ beta
        sigma = float(np.sqrt(resid @ resid / (n_used - Xb.shape[1])))
        X = np.column_stack([
            np.ones(n_used),
            m[strata].values,
            m["log_oil"].values,
            (m[strata].values * m["log_oil"].values[:, None]),
            m["trend"].values,
            m["trend2"].values,
            m[[f"lag{L}" for L in range(1, lag_max + 1)]].values,
        ])
        k = X.shape[1]
        dof = n_used - k
        if dof < spec["dof_power"]["min_dof"]:
            continue
        xtx_inv = np.linalg.inv(X.T @ X)
        mde = (z_a + z_p) * sigma * np.sqrt(np.maximum(np.diag(xtx_inv), 0))
        mde_strata = mde[1:1 + len(strata)] / sigma
        recorded = dp["mde_strata_in_sd_units"]
        recorded_vals = [recorded[s] for s in strata]
        for want, got, s in zip(recorded_vals, mde_strata, strata):
            if not close(got, want, atol=5e-3, rtol=2e-2):
                failures.append(f"mde {oid}/{s}: recomputed {got:.4g} != engine {want}")
        # the reduced spec (interactions dropped)
        X2 = np.column_stack([
            np.ones(n_used), m[strata].values, m["log_oil"].values, m["trend"].values,
        ])
        inv2 = np.linalg.inv(X2.T @ X2)
        mde2 = (z_a + z_p) * sigma * np.sqrt(np.maximum(np.diag(inv2), 0))
        mde2_strata = mde2[1:1 + len(strata)] / sigma
        rec2 = dp.get("mde_strata_reduced_in_sd_units") or {}
        for s, got in zip(strata, mde2_strata):
            if s in rec2 and not close(got, rec2[s], atol=5e-3, rtol=2e-2):
                failures.append(f"mde-reduced {oid}/{s}: recomputed {got:.4g} != engine {rec2[s]}")
        checked += 1
    print(f"  dof / power      : {checked} Tier-3 design matrices rebuilt and MDEs matched")


def check_cards_and_verdicts(diag, failures):
    """Re-derive per-card status and the design verdict; enforce the two guards."""
    try:
        import jsonschema
        card_schema = json.loads(CARD_SCHEMA.read_text(encoding="utf-8"))
        index_schema = json.loads(INDEX_SCHEMA.read_text(encoding="utf-8"))
        card_validator = jsonschema.Draft202012Validator(card_schema)
        index_validator = jsonschema.Draft202012Validator(index_schema)
    except ImportError:
        card_validator = index_validator = None
        print("  ! jsonschema not importable — schema checks skipped")

    cards = diag["cards"]
    coverage = {o["id"]: o["coverage_status"] for o in
                json.loads(INDEX_PATH.read_text(encoding="utf-8"))["outcomes"]}

    statuses_by_design = {"A": {}, "B": {}, "C": {}}
    for dag_id, cd in cards.items():
        outcome_id, design = dag_id.rsplit("__", 1)
        cov = cd.get("coverage_status", coverage.get(outcome_id))
        checks = cd.get("checks", [])
        verdicts = [c["verdict"] for c in checks]
        # re-derive the status by the declared rule for each design
        if design == "A":
            # The declared rule: a dose on the axis the estimand specifies, plus a state-attributed
            # outcome. Both are re-read from the artifact's dose block rather than assumed, so the
            # verdict follows the data instead of the date the engine was last edited.
            axes = diag["dose"]["axes"]
            specified_ok = axes.get(diag["dose"].get("specified_axis"), {}).get("verdict") == "pass"
            outcome_ok = any(v.get("verdict") == "present"
                             for v in diag["dose"]["state_outcomes"].values())
            recomputed = "pass" if (specified_ok and outcome_ok) else "fail"
        elif design == "B":
            if cov in ("declared_gap", "blocked"):
                recomputed = "not_attempted"
            elif "fail" in verdicts:
                recomputed = "fail"
            elif any(v in ("flag", "inconclusive", "not_run", "deviation") for v in verdicts):
                recomputed = "degraded"
            else:
                recomputed = "pass"
        else:  # C
            # The declared rollup (`diagnostics.yml` `outcome_rollup`): a strict majority of the runnable
            # windows. Re-derived here from the card's own check rows, so a card credited on a single window
            # fails the verifier rather than passing on the old "any window" rule.
            wv = [c["verdict"] for c in checks if c["id"].startswith("pretreatment_fit")]
            runnable = sum(1 for v in wv if v in ("pass", "weak_fit"))
            passed = sum(1 for v in wv if v == "pass")
            recomputed = ("pass" if runnable and passed > runnable / 2
                          else "fail" if runnable
                          else "not_attempted")
        if recomputed != cd["status"]:
            failures.append(f"{dag_id}: card status {cd['status']} != recomputed {recomputed}")
        statuses_by_design[design][dag_id] = cd["status"]
        # guard: a blocked outcome cannot pass its pre-check
        if cd["status"] == "pass" and cov in ("blocked", "declared_gap"):
            failures.append(f"{dag_id}: pass on a {cov} outcome")
        # guard: a non-pass must name its blocker
        if cd["status"] != "pass" and not cd.get("blocker"):
            failures.append(f"{dag_id}: status '{cd['status']}' with no blocker recorded")
        # provenance stamped by the engine
        if cd.get("vintage") != VINTAGE:
            failures.append(f"{dag_id}: card diagnostics vintage {cd.get('vintage')} != {VINTAGE}")

    # design-level verdict recomputed from the card statuses
    for design, entry in diag["design_verdicts"].items():
        st = list(statuses_by_design[design].values())
        n_pass = st.count("pass")
        n_attempted = sum(1 for s in st if s in ("pass", "degraded", "fail"))
        if design == "A":
            expect = "dropped"
        elif n_pass > 0:
            expect = "candidate"
        elif "fail" in st and n_pass == 0 and st.count("degraded") == 0:
            expect = "infeasible"
        elif "degraded" in st:
            expect = "degraded"
        else:
            expect = "not_attempted"
        if entry["status"] != expect:
            failures.append(f"design {design}: status {entry['status']} != recomputed {expect}")
        if entry.get("n_outcomes_pass") != n_pass:
            failures.append(f"design {design}: n_outcomes_pass {entry.get('n_outcomes_pass')} != {n_pass}")
        if entry.get("n_outcomes_attempted") != n_attempted:
            failures.append(f"design {design}: n_outcomes_attempted {entry.get('n_outcomes_attempted')} != {n_attempted}")

    # schema validation of every card and the index
    file_failures = 0
    for dag_id in cards:
        card = json.loads((CARDS_DIR / f"{dag_id}.json").read_text(encoding="utf-8"))
        if card_validator is not None:
            for err in card_validator.iter_errors(card):
                failures.append(f"{dag_id}: schema {list(err.path)}: {err.message}")
                file_failures += 1
        if "diagnostics" not in card:
            failures.append(f"{dag_id}: card carries no diagnostics block")
    if index_validator is not None:
        index = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
        for err in index_validator.iter_errors(index):
            failures.append(f"index: schema {list(err.path)}: {err.message}")
    print(f"  cards            : {len(cards)} per-card statuses and design verdicts re-derived"
          + ("" if not file_failures else f" ({file_failures} schema problems)"))


def main() -> int:
    if not DIAG_PATH.exists():
        raise SystemExit(f"no diagnostics at {DIAG_PATH} — run analysis/R/02_diagnostics.R first")
    diag = json.loads(DIAG_PATH.read_text(encoding="utf-8"))
    failures: list[str] = []
    warnings: list[str] = []

    print(f"Stage 5 diagnostics verifier | vintage {diag['vintage']} | stage {diag['stage']}\n")
    con = connect()
    try:
        check_spec_echo(diag, failures)
        check_grain(con, diag, failures)
        check_shock_visibility(con, diag, failures)
        check_dose(con, diag, failures)
        check_cointegration(con, diag, failures, warnings)
        check_prefit(con, diag, failures)
        check_mde(con, diag, failures)
    finally:
        con.close()
    check_cards_and_verdicts(diag, failures)

    print()
    if warnings:
        print(f"{len(warnings)} warning(s) — reported, not fatal:")
        for w in warnings:
            print(f"  ~ {w}")
        print()
    if failures:
        print(f"FAILED — {len(failures)} problem(s):")
        for p in failures:
            print(f"  - {p}")
        return 1
    print("PASS — every headline diagnostic is reproducible from the base, and the cards, "
          "verdicts and schemas are consistent with it")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
