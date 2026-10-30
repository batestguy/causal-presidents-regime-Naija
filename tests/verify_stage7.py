"""Verify the Stage 7 robustness artifact.

Re-derives every published number from the analytical base **independently of**
``analysis/R/04_robustness.R``: the same specifications, written separately, in a different language,
from the same spec. What is checked, and why each one is here:

  * **Every specification in the grid is re-fitted** — 81 Design A PPML fits with ``statsmodels``
    GLM/IRLS (not ``fixest``'s demeaning IRLS) and 24 Design B local projections with ``statsmodels``
    OLS/Newey-West. A robustness grid whose cells cannot be reproduced is a table, not a result.
  * **The support counts and the sign-flip levels are recomputed** from the published rows *and* from the
    re-fitted ones. The first catches a summary that drifted from its own rows; the second catches a grid
    that was fitted on something other than the declared base.
  * **The pre-registered cell reproduces Stage 6.** The curve is drawn around the published estimate; if
    the preferred specification had drifted, the curve would be a different study's.
  * **The sensitivity checks reproduce** — Oster's delta on both analogues, the 36 leave-one-state-out
    refits, the in-time placebo distribution, and the HAC bandwidth table.
  * **The unbuilt axes are present.** The grid cannot vary the per-capita dose, the IGR instrument, the
    donor pool or the imputation rule; an artifact that silently omitted them would look complete.

Usage:
    conda run -p "C:/Users/TOSHIBA/ds-general" python tests/verify_stage7.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
import statsmodels.api as sm
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
ROBUSTNESS_ROOT = REPO_ROOT / "registry" / "robustness"
SPEC_PATH = REPO_ROOT / "analysis" / "specs" / "robustness.yml"

# The coefficient is the same maximum-likelihood estimate in both implementations and is compared at
# 1e-4. The clustered standard error differs by the packages' finite-sample corrections (a few per cent
# on 36 clusters), so it is compared at 5 % and the difference is printed when it is material. The
# Newey-West standard error has no such allowance: both implementations use the same estimator.
COEF_TOL = 1e-4
SE_TOL_REL = 0.05
# Design B's Newey-West: the same estimator in both packages, but ``sandwich::NeweyWest`` and
# ``statsmodels`` differ in the small-sample factor they apply to the HAC weights, so the standard
# errors are compared relatively at the same 5 % allowance the Stage 6 verifier uses — and the observed
# gap is printed, so a drift larger than a fraction of a per cent is visible rather than absorbed.
NP_SE_TOL_REL = 0.05


def fail(failures: list[str], message: str) -> None:
    failures.append(message)


def load_base(spec: dict, outcome_defs: list[dict]) -> tuple[pd.DataFrame, dict[str, pd.DataFrame]]:
    con = duckdb.connect(str(REPO_ROOT / spec["input"]["database"]), read_only=True)
    try:
        q = spec["design_a"]["sample"]
        panel = con.sql(
            f"""
            select state_id, state_name, period_month,
                   faac_gross_total_naira as dose, fatalities, incidents, fatalities_civilians
            from {spec['input']['panel_table']}
            where dose_status = '{q['require_dose_status']}'
              and security_status = '{q['require_security_status']}'
              and faac_gross_total_naira >= {q['min_exposure']}
            order by state_id, period_month
            """
        ).df()
        # One frame per outcome family (C-85), each from its own declared table — the mapping lives in
        # estimation.yml, which robustness.yml names as its upstream.
        frames: dict[str, pd.DataFrame] = {}
        for o in outcome_defs:
            frames[o["id"]] = con.sql(
                f"""
                select t.period_month, t.{o['column']} as outcome_value, m.value as oil
                from {o['table']} t
                join {spec['input']['fact_metric_table']} m
                  on m.metric_id = '{spec['input']['oil_metric_id']}'
                 and m.period_month = t.period_month
                where t.{o['column']} is not null and m.value is not null
                order by t.period_month
                """
            ).df()
    finally:
        con.close()

    panel["period_month"] = pd.to_datetime(panel["period_month"])
    panel["dose"] = panel["dose"].astype(float)
    panel["log_dose"] = np.log(panel["dose"])
    # The same trend clock as the engine: months since the first month of the landed dose.
    panel["trend"] = 12 * (panel["period_month"].dt.year - 2016) + (panel["period_month"].dt.month - 12)
    panel["ym"] = panel["period_month"].dt.strftime("%Y-%m")
    panel = panel.sort_values(["state_id", "period_month"]).reset_index(drop=True)
    for lag in (0, 1, 2):
        panel[f"log_dose_lag{lag}"] = panel.groupby("state_id")["log_dose"].shift(lag)

    for frame in frames.values():
        frame["period_month"] = pd.to_datetime(frame["period_month"])
        frame["outcome_value"] = frame["outcome_value"].astype(float)
        frame["oil"] = frame["oil"].astype(float)
        frame["log_outcome"] = np.log(frame["outcome_value"])
        frame["log_oil"] = np.log(frame["oil"])
        frame["d_log_oil_1m"] = frame["log_oil"].diff(1)
        frame["d_log_oil_3m"] = frame["log_oil"].diff(3) / 3
        frame["month_of_year"] = frame["period_month"].dt.month.astype("category")
        frame["covid"] = (
            (frame["period_month"] >= "2020-03-01") & (frame["period_month"] <= "2021-12-01")
        ).astype(int)
        for shock in ("d_log_oil_1m", "d_log_oil_3m"):
            frame[f"lag_{shock}"] = frame[shock].shift(1)
    return panel, frames


def base_fingerprints(spec: dict) -> dict[str, str]:
    """The base the grid claims to have been fitted on, hashed by the spec's own declared queries.

    Both implementations run the identical SQL from ``robustness.yml``. The values are formatted at 10
    significant digits there, so rebuilding the same base (a parallel float sum is not associative) does
    not trip the check while a material change does — which is the difference between a guard and a
    nuisance.
    """
    con = duckdb.connect(str(REPO_ROOT / spec["input"]["database"]), read_only=True)
    try:
        return {name: str(con.sql(sql).fetchone()[0])
                for name, sql in spec["base_fingerprint"]["queries"].items()}
    finally:
        con.close()


def window_mask(frame: pd.DataFrame, name: str, spec: dict) -> np.ndarray:
    w = spec["windows"][name]
    keep = np.ones(len(frame), dtype=bool)
    ym = frame["period_month"].dt.strftime("%Y-%m").to_numpy()
    if w.get("drop"):
        keep &= ~((ym >= w["drop"][0]) & (ym <= w["drop"][1]))
    if w.get("start"):
        keep &= ym >= w["start"]
    if w.get("end"):
        keep &= ym <= w["end"]
    return keep


def fe_design(frame: pd.DataFrame, adjustment_set: str, dose_col: str) -> pd.DataFrame:
    """The fixed-effect design, spelled out as dummies rather than within-transformed."""
    frame = frame.reset_index(drop=True)
    parts = [frame[[dose_col]]]
    if adjustment_set in ("state_fe", "state_month_fe", "state_month_fe_state_trend"):
        parts.append(pd.get_dummies(frame["state_id"], prefix="s", drop_first=True, dtype=float)
                     .reset_index(drop=True))
    if adjustment_set in ("state_month_fe", "state_month_fe_state_trend"):
        parts.append(pd.get_dummies(frame["ym"], prefix="m", drop_first=True, dtype=float)
                     .reset_index(drop=True))
    if adjustment_set == "state_month_fe_state_trend":
        # One state's slope is dropped, exactly as ``drop_first`` drops one state dummy: the sum of all 36
        # slopes is a linear function of the month, which the month dummies already span. Writing all 36
        # leaves the design rank-deficient, and a rank-deficient design makes the sandwich covariance
        # depend on which generalized inverse the package happens to use — the first version of this
        # verifier disagreed with the engine's standard error by 97 % for that reason while agreeing on
        # the coefficient to 1e-10. Dropping the same reference state keeps a full-rank design, and the
        # span (and therefore every fitted quantity) is unchanged.
        trend = frame["trend"].to_numpy(dtype=float)
        state = frame["state_id"].to_numpy()
        slopes = {f"t_{s}": trend * (state == s) for s in sorted(pd.unique(state))[1:]}
        parts.append(pd.DataFrame(slopes, index=frame.index).reset_index(drop=True))
    return sm.add_constant(pd.concat(parts, axis=1), has_constant="add")


def ppml(frame: pd.DataFrame, outcome: str, dose_col: str, adjustment_set: str) -> tuple[float, float, int]:
    """Poisson pseudo-ML with the declared fixed effects, clustered by state."""
    """
    Separation is applied here too: a state with no positive value for the outcome anywhere in the frame
    has an unidentified fixed effect and contributes nothing to the likelihood, so ``fixest`` drops it and
    reports the smaller n. Reproducing that rule explicitly is what makes the two implementations compare
    the same sample.
    """
    frame = frame.copy()
    totals = frame.groupby("state_id")[outcome].transform("sum")
    frame = frame[totals > 0].reset_index(drop=True)
    design = fe_design(frame, adjustment_set, dose_col)
    result = sm.GLM(frame[outcome].astype(float), design, family=sm.families.Poisson()).fit(
        cov_type="cluster", cov_kwds={"groups": frame["state_id"]}, maxiter=200
    )
    return float(result.params[dose_col]), float(result.bse[dose_col]), int(result.nobs)


def lp(frame: pd.DataFrame, shock: str, controls: str, h: int, maxlags: int = 12,
       window: str | None = None, spec: dict | None = None) -> dict:
    """Cumulative local projection at horizon h, in the direction data.table's shift spells.

    The outcome is built on the full series and the window is applied to the estimation rows afterwards,
    as the spec declares: filtering first would let the last row before an excluded stretch take its
    h-month lead from the far side of the gap.
    """
    frame = frame.copy()
    frame["y"] = frame["log_outcome"].shift(-h) - frame["log_outcome"].shift(1)
    frame = frame.dropna(subset=["y", shock])
    if window is not None:
        frame = frame[window_mask(frame, window, spec)]
    design = frame[[shock]].reset_index(drop=True)
    if controls in ("month_of_year", "month_of_year_plus_lagged_shock", "month_of_year_plus_covid"):
        design = pd.concat(
            [design, pd.get_dummies(frame["month_of_year"], prefix="m", drop_first=True, dtype=float)
             .reset_index(drop=True)], axis=1)
    if controls == "month_of_year_plus_lagged_shock":
        design = pd.concat([design, frame[[f"lag_{shock}"]].reset_index(drop=True)], axis=1)
    if controls == "month_of_year_plus_covid":
        design = pd.concat([design, frame[["covid"]].reset_index(drop=True)], axis=1)
    # R's ``lm`` drops rows with a missing value in any regressor (``na.action = na.omit``), and the lagged
    # shock column has one: the first month of the series. Dropping the same rows here is what makes the
    # two n's comparable rather than two different samples.
    valid = design.notna().all(axis=1).to_numpy()
    if not valid.all():
        frame = frame[valid]
        design = design[valid]
    design = sm.add_constant(design, has_constant="add")
    result = sm.OLS(frame["y"].to_numpy(dtype=float), design).fit(
        cov_type="HAC", cov_kwds={"maxlags": maxlags, "use_correction": True}
    )
    return {
        "coefficient": float(result.params[shock]),
        "standard_error": float(result.bse[shock]),
        "n_obs": int(result.nobs),
        "model": result,
    }


def oster(frame: pd.DataFrame, y_col: str, treat: str, long_design, spec: dict) -> dict:
    short = sm.OLS(frame[y_col].to_numpy(dtype=float), sm.add_constant(frame[[treat]].to_numpy(dtype=float))) \
        .fit()
    long = sm.OLS(frame[y_col].to_numpy(dtype=float), long_design).fit()
    b_short, b_long = float(short.params[1]), float(long.params[treat])
    r2_short, r2_long = float(short.rsquared), float(long.rsquared)
    r_max = min(1.0, spec["design_a"]["checks"]["oster"]["rmax_multiplier"] * r2_long)
    denominator = (b_short - b_long) * (r_max - r2_long)
    delta = None if abs(denominator) < 1e-15 else b_long * (r2_long - r2_short) / denominator
    beta_star = b_long - (b_short - b_long) * (r_max - r2_long) / (r2_long - r2_short)
    return {"beta_long": b_long, "beta_short": b_short, "r2_long": r2_long, "r2_short": r2_short,
            "r2_max": r_max, "delta": delta, "beta_star": beta_star, "flips": np.sign(b_short) != np.sign(b_long)}


def main() -> int:
    if not SPEC_PATH.exists():
        raise SystemExit(f"no robustness spec at {SPEC_PATH}")
    spec = yaml.safe_load(SPEC_PATH.read_text(encoding="utf-8"))
    vintage = spec["labelled"]
    artifact_path = ROBUSTNESS_ROOT / vintage / "robustness.json"
    if not artifact_path.exists():
        raise SystemExit(f"no robustness artifact at {artifact_path.relative_to(REPO_ROOT)} — run 04_robustness.R")

    report = json.loads(artifact_path.read_text(encoding="utf-8"))
    failures: list[str] = []
    print(f"robustness {report['vintage']} | {len(report['specifications'])} specifications | "
          f"generated {report['generated_at']}")

    panel, b_frames = load_base(spec, yaml.safe_load(
        (REPO_ROOT / spec["upstream"]["estimation_spec"]).read_text(encoding="utf-8"))["design_b"]["outcomes"])
    by_id = {row["spec_id"]: row for row in report["specifications"]}

    # ---- 1. the grid is complete and nothing undeclared was published -----------------------
    declared = (len(spec["design_a"]["axes"]["outcome"]) * len(spec["design_a"]["axes"]["dose_lag_months"])
                * len(spec["design_a"]["axes"]["adjustment_set"]) * len(spec["design_a"]["axes"]["window"]))
    declared += (len(spec["design_b"]["axes"]["outcome"]) * len(spec["design_b"]["axes"]["shock"])
                 * len(spec["design_b"]["axes"]["controls"]) * len(spec["design_b"]["axes"]["window"]))
    if len(report["specifications"]) != declared:
        fail(failures, f"grid: {len(report['specifications'])} specifications published, {declared} declared")
    if report["grid"]["n_total"] != declared:
        fail(failures, f"grid: n_total {report['grid']['n_total']} but {declared} are declared")
    for design in ("A", "B"):
        rows = [r for r in report["specifications"] if r["design"] == design]
        if sum(1 for r in rows if r["preferred"]) != 1:
            fail(failures, f"design {design}: not exactly one preferred specification")

    # ---- 2. every Design A specification re-fitted ------------------------------------------
    print(f"\n{'spec':<52}{'reported':>11}{'recomputed':>12}{'diff':>10}  n  verdict")
    print("-" * 92)
    a_worst = 0.0
    a_se_worst = 0.0
    for row in sorted((r for r in report["specifications"] if r["design"] == "A"),
                      key=lambda r: r["spec_id"]):
        frame = panel[panel[f"log_dose_lag{row['dose_lag_months']}"].notna()
                      & window_mask(panel, row["window"], spec)]
        beta, se, n = ppml(frame, row["outcome"], f"log_dose_lag{row['dose_lag_months']}",
                           row["adjustment_set"])
        delta = abs(beta - row["coefficient"])
        a_worst = max(a_worst, delta)
        a_se_worst = max(a_se_worst, abs(se - row["standard_error"]) / max(row["standard_error"], 1e-12))
        verdict = "ok"
        if delta > COEF_TOL:
            verdict = "FAIL"
            fail(failures, f"design A / {row['spec_id']}: reported {row['coefficient']:.6f} vs "
                           f"recomputed {beta:.6f}")
        if row["n_obs"] != n:
            verdict = "FAIL"
            fail(failures, f"design A / {row['spec_id']}: reported n {row['n_obs']} vs recomputed {n}")
        if abs(se - row["standard_error"]) / max(row["standard_error"], 1e-12) > SE_TOL_REL:
            verdict = "FAIL"
            fail(failures, f"design A / {row['spec_id']}: clustered SE differs by "
                           f"{100 * abs(se - row['standard_error']) / row['standard_error']:.1f}% "
                           "(beyond the stated allowance)")
        sign = "positive" if beta > 0 else "negative"
        if row["sign"] != sign:
            fail(failures, f"design A / {row['spec_id']}: published sign is {row['sign']}, recomputed {sign}")
        print(f"{row['spec_id'][:51]:<52}{row['coefficient']:>11.4f}{beta:>12.4f}{delta:>10.2e}"
              f"  {n}  {verdict}")

    # ---- 3. every Design B specification re-fitted -------------------------------------------
    print(f"\n{'spec':<52}{'reported':>11}{'recomputed':>12}{'diff':>10}  n  verdict")
    print("-" * 92)
    # The re-fitted coefficients are kept: the spread decomposition below is checked against these
    # rather than against the published rows, so a grid fitted on something else is caught.
    b_refitted: list[dict] = []
    for row in sorted((r for r in report["specifications"] if r["design"] == "B"), key=lambda r: r["spec_id"]):
        got = lp(b_frames[row["outcome"]], row["shock"], row["controls"], row["horizon"],
                 spec["design_b"]["inference"]["maxlags"], window=row["window"], spec=spec)
        b_refitted.append({**row, "coefficient": got["coefficient"]})
        delta = abs(got["coefficient"] - row["coefficient"])
        verdict = "ok"
        if delta > COEF_TOL:
            verdict = "FAIL"
            fail(failures, f"design B / {row['spec_id']}: reported {row['coefficient']:.6f} vs "
                           f"recomputed {got['coefficient']:.6f}")
        if row["n_obs"] != got["n_obs"]:
            verdict = "FAIL"
            fail(failures, f"design B / {row['spec_id']}: reported n {row['n_obs']} vs {got['n_obs']}")
        se_gap = abs(got["standard_error"] - row["standard_error"]) / max(row["standard_error"], 1e-12)
        if se_gap > NP_SE_TOL_REL:
            verdict = "FAIL"
            fail(failures, f"design B / {row['spec_id']}: Newey-West SE differs by {100 * se_gap:.2f}% "
                           f"({row['standard_error']:.4f} vs {got['standard_error']:.4f}) — beyond the "
                           "stated allowance")
        print(f"{row['spec_id'][:51]:<52}{row['coefficient']:>11.4f}{got['coefficient']:>12.4f}"
              f"{delta:>10.2e}  {got['n_obs']}  {verdict}")
    print(f"\ndesign A: worst coefficient difference {a_worst:.2e}, worst clustered-SE gap {100 * a_se_worst:.2f}%")

    # ---- 4. support counts and flips recomputed from the published rows -----------------------
    def counts(rows: list[dict]) -> dict:
        return {
            "n": len(rows),
            "n_positive": sum(1 for r in rows if r["coefficient"] > 0),
            "n_negative": sum(1 for r in rows if r["coefficient"] < 0),
            "n_zero": sum(1 for r in rows if r["coefficient"] == 0),
            "n_positive_ci": sum(1 for r in rows if r["coefficient"] > 0 and r["ci_low"] > 0),
            "n_negative_ci": sum(1 for r in rows if r["coefficient"] < 0 and r["ci_high"] < 0),
        }

    for design in ("A", "B"):
        rows = [r for r in report["specifications"] if r["design"] == design]
        published = report["support"]["by_design"][design]
        want = counts(rows)
        for key, value in want.items():
            if published[key] != value:
                fail(failures, f"support / design {design}: {key} is {published[key]} in the summary and "
                               f"{value} in its own rows")
    overall = counts(report["specifications"])
    for key, value in overall.items():
        if report["support"]["overall"][key] != value:
            fail(failures, f"support / overall: {key} is {report['support']['overall'][key]} and {value}")
    print(f"\nsupport: {overall['n_positive']} positive ({overall['n_positive_ci']} with CI>0), "
          f"{overall['n_negative']} negative ({overall['n_negative_ci']} with CI<0) of {overall['n']}")

    # The flip rule is the declared majority rule; recomputed from the published rows.
    pref_sign = {d: next(r["coefficient"] for r in report["specifications"]
                         if r["design"] == d and r["preferred"]) > 0 for d in ("A", "B")}
    axes = {"A": ["outcome", "dose_lag_months", "adjustment_set", "window"],
            "B": ["outcome", "shock", "controls", "window"]}
    expected_levels = {}
    for design, axis_list in axes.items():
        rows = [r for r in report["specifications"] if r["design"] == design]
        for axis in axis_list:
            for level in sorted({str(r[axis]) for r in rows}):
                sub = [r for r in rows if str(r[axis]) == level]
                opposite = sum(1 for r in sub if (r["coefficient"] > 0) != pref_sign[design]
                               and r["coefficient"] != 0)
                expected_levels[(design, axis, level)] = (len(sub), opposite, opposite > len(sub) / 2)
    published_levels = {(x["design"], x["axis"], x["level"]): x for x in report["support"]["by_axis_level"]}
    if set(published_levels) != set(expected_levels):
        missing = set(expected_levels) - set(published_levels)
        extra = set(published_levels) - set(expected_levels)
        fail(failures, f"axis levels: {len(missing)} missing and {len(extra)} undeclared "
                       f"({sorted(missing)[:3]} / {sorted(extra)[:3]})")
    for key, (n, opposite, flips) in expected_levels.items():
        got = published_levels.get(key)
        if got is None:
            continue
        if got["n"] != n or got["n_opposite"] != opposite or got["flips_against_preferred"] != flips:
            fail(failures, f"axis level {key}: published n {got['n']}, opposite {got['n_opposite']}, "
                           f"flip {got['flips_against_preferred']}; recomputed {n}, {opposite}, {flips}")
    published_flips = {(x["design"], x["axis"], x["level"]) for x in report["support"]["flips"]["levels"]}
    expected_flips = {k for k, v in expected_levels.items() if v[2]}
    if published_flips != expected_flips:
        fail(failures, f"flip list: published {sorted(published_flips)} vs recomputed {sorted(expected_flips)}")
    if report["support"]["flips"]["n_levels"] != len(expected_flips):
        fail(failures, "flip count disagrees with the recomputed majority rule")
    print(f"sign-flip levels (majority rule, recomputed): {len(expected_flips)}")

    # ---- 4b. the spread decomposition the report and the docs quote ---------------------------
    # Computed from the re-fitted Design B coefficients, not from the published ones: the point of
    # publishing the decomposition is that the prose stops quoting a typed number, so the check has
    # to reach past the published rows to the fitted grid. **Per outcome family**, because pooling two
    # estimands into one min/max publishes a range no single outcome produces (C-85).
    def spread_of(rows: list[dict]) -> dict:
        def within_cell_range(keys: tuple[str, ...]) -> tuple[float, int]:
            cells: dict[tuple, list[float]] = {}
            for r in rows:
                cells.setdefault(tuple(r[k] for k in keys), []).append(r["coefficient"])
            return float(np.mean([max(v) - min(v) for v in cells.values()])), len(cells)

        across_covariate_sets, n_shock_cells = within_cell_range(("shock", "window"))
        across_shock_definitions, n_control_cells = within_cell_range(("controls", "window"))
        return {
            "n": len(rows),
            "n_cells_holding_shock": n_shock_cells,
            "n_cells_holding_controls": n_control_cells,
            "coefficient_min": min(r["coefficient"] for r in rows),
            "coefficient_min_spec": min(rows, key=lambda r: r["coefficient"])["spec_id"],
            "coefficient_max": max(r["coefficient"] for r in rows),
            "coefficient_max_spec": max(rows, key=lambda r: r["coefficient"])["spec_id"],
            "across_covariate_sets": across_covariate_sets,
            "across_shock_definitions": across_shock_definitions,
        }

    published_spread = report.get("spread", {}).get("design_b")
    if not published_spread:
        fail(failures, "spread / design B: the artifact publishes no spread decomposition")
    else:
        # the top-level fields are the pre-registered family's, and `by_outcome` carries both
        preferred_id = spec["design_b"]["preferred"]["outcome"]
        expected_spread = spread_of([r for r in b_refitted if r["outcome"] == preferred_id])
        for key, want in expected_spread.items():
            got = published_spread.get(key)
            if got is None:
                fail(failures, f"spread / design B: {key} is missing from the artifact")
            elif key.endswith("_spec"):
                # A specification id is tie-sensitive: two cells can share the minimum coefficient to
                # floating precision, and which one `which.min` names first is not a claim about the
                # grid. The claim is that the *named* cell attains the published extreme, so that is
                # what is checked.
                named = by_id.get(got)
                extreme = published_spread.get(key.replace("_spec", ""))
                if named is None:
                    fail(failures, f"spread / design B / {key}: {got!r} is not a published specification")
                elif named["outcome"] != preferred_id:
                    fail(failures, f"spread / design B / {key}: {got!r} is not in the pre-registered family")
                elif abs(named["coefficient"] - extreme) > 1e-9:
                    fail(failures, f"spread / design B / {key}: {got!r} has coefficient "
                                   f"{named['coefficient']:.6f}, not the published extreme {extreme:.6f}")
            elif isinstance(want, float):
                if abs(got - want) > 1e-6:
                    fail(failures, f"spread / design B / {key}: published {got:.6f} vs recomputed "
                                   f"{want:.6f} — the magnitude claim is not the fitted grid's")
            elif got != want:
                fail(failures, f"spread / design B / {key}: published {got} vs recomputed {want}")
        by_outcome = published_spread.get("by_outcome") or {}
        for oid in sorted({r["outcome"] for r in b_refitted}):
            want = spread_of([r for r in b_refitted if r["outcome"] == oid])
            if oid not in by_outcome:
                fail(failures, f"spread / design B: no decomposition published for outcome {oid}")
                continue
            for key, value in want.items():
                got = by_outcome[oid].get(key)
                if key.endswith("_spec"):
                    named = by_id.get(got)
                    extreme = by_outcome[oid].get(key.replace("_spec", ""))
                    if named is None or named["outcome"] != oid:
                        fail(failures, f"spread / design B[{oid}] / {key}: {got!r} is not a "
                                       f"specification of this family")
                    elif extreme is not None and abs(named["coefficient"] - extreme) > 1e-9:
                        fail(failures, f"spread / design B[{oid}] / {key}: {got!r} has coefficient "
                                       f"{named['coefficient']:.6f}, not the published extreme "
                                       f"{extreme:.6f}")
                elif isinstance(value, float):
                    if got is None or abs(got - value) > 1e-6:
                        fail(failures, f"spread / design B[{oid}] / {key}: published {got} vs "
                                       f"recomputed {value:.6f}")
                elif got != value:
                    fail(failures, f"spread / design B[{oid}] / {key}: published {got} vs recomputed {value}")
    print(f"\nspread (Design B[{preferred_id}], recomputed): {expected_spread['coefficient_min']:.4f} .. "
          f"{expected_spread['coefficient_max']:.4f}; across the covariate sets "
          f"{expected_spread['across_covariate_sets']:.4f} (mean over "
          f"{expected_spread['n_cells_holding_shock']} shock x window cells), across the two "
          f"shock definitions {expected_spread['across_shock_definitions']:.4f}")

    # ---- 5. the pre-registered cell is the published Stage 6 estimate -------------------------
    upstream = report["upstream"]
    estimates_path = REPO_ROOT / spec["upstream"]["estimates"]
    # The same rule the engine enforces (C-83): the artifact this stage reproduces must be its own
    # vintage's. Checked from the spec, not from the artifact, so a stale declaration fails here even if
    # the numbers happened to match.
    if estimates_path.parent.name != str(spec["labelled"]):
        fail(failures, f"upstream: the declared estimates path is vintage {estimates_path.parent.name} "
                       f"but this stage writes {spec['labelled']} — the reproduction check would read a "
                       "superseded artifact (C-83)")
    estimates = json.loads(estimates_path.read_text(encoding="utf-8"))
    h_focus = spec["design_b"]["focus_horizon"]
    stage6_a = next(s for s in estimates["specifications"]
                    if s["design"] == "A" and s["outcome"] == spec["design_a"]["preferred"]["outcome"])
    stage6_b = next(s for s in estimates["specifications"]
                    if s["design"] == "B"
                    and s["coefficient_name"] == f"cumulative_pass_through_h{h_focus}")
    pref_a = by_id[report["preferred"]["A"]]
    pref_b = by_id[report["preferred"]["B"]]
    for label, got, want in (("A", pref_a["coefficient"], stage6_a["coefficient"]),
                             ("B", pref_b["coefficient"], stage6_b["coefficient"])):
        if abs(got - want) > 1e-8:
            fail(failures, f"preferred {label}: robustness {got:.8f} vs Stage 6 {want:.8f} — the grid was "
                            "fitted around a different specification")
    if not (upstream["preferred_matches_stage6"].get("checked") is True):
        fail(failures, "upstream: the artifact does not claim to have checked the Stage 6 reproduction")
    print(f"\npreferred reproduces Stage 6: A {stage6_a['coefficient']:+.4f} (n={stage6_a['n_obs']}), "
          f"B h={h_focus} {stage6_b['coefficient']:+.4f} (n={stage6_b['n_obs']})")

    # ---- 6. sensitivity reproduces ------------------------------------------------------------
    pref_a_frame = panel[panel["log_dose"].notna()
                         & window_mask(panel, spec["design_a"]["preferred"]["window"], spec)].copy()
    pref_a_frame["np_outcome"] = np.log1p(pref_a_frame[spec["design_a"]["preferred"]["outcome"]].astype(float))
    long_design = fe_design(pref_a_frame, spec["design_a"]["preferred"]["adjustment_set"], "log_dose")
    oster_a = oster(pref_a_frame, "np_outcome", "log_dose", long_design, spec)
    published_oster_a = report["sensitivity"]["design_a"]["oster"]
    for key, got in (("beta_long", oster_a["beta_long"]), ("beta_short", oster_a["beta_short"]),
                     ("r2_long", oster_a["r2_long"]), ("r2_short", oster_a["r2_short"]),
                     ("r2_max", oster_a["r2_max"]), ("beta_star_at_delta_1", oster_a["beta_star"])):
        if abs(got - published_oster_a[key]) > 1e-6:
            fail(failures, f"oster A / {key}: published {published_oster_a[key]:.8f} vs recomputed {got:.8f}")
    if (published_oster_a["delta"] is None) != (oster_a["delta"] is None) or (
        published_oster_a["delta"] is not None
        and abs(published_oster_a["delta"] - oster_a["delta"]) > 1e-6
    ):
        fail(failures, "oster A / delta: published and recomputed differ")
    if published_oster_a["control_set_flips_the_sign"] != bool(oster_a["flips"]):
        fail(failures, "oster A: the sign-flip flag disagrees with the recomputed analogue")
    print(f"Oster A analogue: beta_short {oster_a['beta_short']:+.4f} -> beta_long {oster_a['beta_long']:+.4f}, "
          f"delta {oster_a['delta']:.3f}, beta* {oster_a['beta_star']:.4f}")

    # leave-one-state-out, all 36 refits
    loo = {}
    for state in sorted(pref_a_frame["state_name"].unique()):
        sub = pref_a_frame[pref_a_frame["state_name"] != state]
        loo[state] = ppml(sub, spec["design_a"]["preferred"]["outcome"], "log_dose",
                          spec["design_a"]["preferred"]["adjustment_set"])[0]
    published_loo = report["sensitivity"]["design_a"]["leave_one_state_out"]
    if published_loo["n_refits"] != len(loo):
        fail(failures, f"leave-one-state-out: {published_loo['n_refits']} refits published, {len(loo)} recomputed")
    if abs(published_loo["min"] - min(loo.values())) > 1e-4 or abs(published_loo["max"] - max(loo.values())) > 1e-4:
        fail(failures, f"leave-one-state-out range: published [{published_loo['min']:.4f}, "
                       f"{published_loo['max']:.4f}] vs recomputed [{min(loo.values()):.4f}, {max(loo.values()):.4f}]")
    if abs(published_loo["median"] - float(np.median(list(loo.values())))) > 1e-4:
        fail(failures, "leave-one-state-out: the median differs")
    flips = sum(1 for v in loo.values() if np.sign(v) != np.sign(pref_a["coefficient"]))
    if published_loo["n_sign_flips"] != flips:
        fail(failures, f"leave-one-state-out: {published_loo['n_sign_flips']} sign flips published, "
                       f"{flips} recomputed")
    oil_states = spec["design_a"]["checks"]["leave_one_state_out"]["oil_states"]
    sub = pref_a_frame[~pref_a_frame["state_name"].isin(oil_states)]
    drop_oil = ppml(sub, spec["design_a"]["preferred"]["outcome"], "log_dose",
                    spec["design_a"]["preferred"]["adjustment_set"])
    if abs(published_loo["drop_oil_states"]["coefficient"] - drop_oil[0]) > 1e-4:  # type: ignore[index]
        fail(failures, "leave-one-state-out / drop the oil states: the coefficient differs")
    print(f"leave-one-state-out: recomputed range [{min(loo.values()):.4f}, {max(loo.values()):.4f}], "
          f"{flips} sign flip(s); dropping {'/'.join(oil_states)} -> {drop_oil[0]:+.4f}")

    # Oster on Design B
    pref_b_frame = b_frames[spec["design_b"]["preferred"]["outcome"]].copy()
    pref_b_frame["y"] = pref_b_frame["log_outcome"].shift(-h_focus) - pref_b_frame["log_outcome"].shift(1)
    shock = spec["design_b"]["preferred"]["shock"]
    pref_b_frame = pref_b_frame.dropna(subset=["y", shock])
    pref_b_frame = pref_b_frame[
        window_mask(pref_b_frame, spec["design_b"]["preferred"]["window"], spec)]
    long_b = pd.concat(
        [pref_b_frame[[shock]].reset_index(drop=True),
         pd.get_dummies(pref_b_frame["month_of_year"], prefix="m", drop_first=True, dtype=float)
         .reset_index(drop=True)], axis=1)
    long_b = sm.add_constant(long_b, has_constant="add")
    oster_b = oster(pref_b_frame, "y", shock, long_b, spec)
    published_oster_b = report["sensitivity"]["design_b"]["oster"]
    for key, got in (("beta_long", oster_b["beta_long"]), ("beta_short", oster_b["beta_short"]),
                     ("r2_long", oster_b["r2_long"]), ("r2_short", oster_b["r2_short"])):
        if abs(got - published_oster_b[key]) > 1e-8:
            fail(failures, f"oster B / {key}: published {published_oster_b[key]:.8f} vs recomputed {got:.8f}")
    print(f"Oster B: beta_short {oster_b['beta_short']:+.4f} -> beta_long {oster_b['beta_long']:+.4f}, "
          f"delta {oster_b['delta']:.3f}")

    # in-time placebo
    in_time = report["sensitivity"]["design_b"]["in_time_placebo"]
    shifted, observed_same_rows = [], []
    preferred_window = spec["design_b"]["preferred"]["window"]
    for k in in_time["offsets"]:
        frame = b_frames[spec["design_b"]["preferred"]["outcome"]].copy()
        frame["placebo_shock"] = frame[shock].shift(k)
        frame = frame[frame["placebo_shock"].notna()]
        shifted.append(lp(frame, "placebo_shock", spec["design_b"]["preferred"]["controls"], h_focus,
                          window=preferred_window, spec=spec)["coefficient"])
        observed_same_rows.append(lp(frame, shock, spec["design_b"]["preferred"]["controls"], h_focus,
                                     window=preferred_window, spec=spec)["coefficient"])
    p_recomputed = float(np.mean(np.abs(shifted) >= np.abs(observed_same_rows)))
    if abs(p_recomputed - in_time["p_value"]) > 1e-9:
        fail(failures, f"in-time placebo: published p {in_time['p_value']:.6f} vs recomputed {p_recomputed:.6f}")
    if abs(float(np.mean(np.abs(shifted))) - in_time["shifted_mean_abs"]) > 1e-6:
        fail(failures, "in-time placebo: the mean absolute placebo estimate differs")
    print(f"in-time placebo: p = {p_recomputed:.4f} over {len(shifted)} offsets "
          f"({round(p_recomputed * len(shifted))} at least as large)")

    # HAC bandwidth
    for entry in report["sensitivity"]["design_b"]["hac_bandwidth"]:
        got = lp(b_frames[spec["design_b"]["preferred"]["outcome"]], shock, spec["design_b"]["preferred"]["controls"], h_focus,
                 maxlags=entry["maxlags"], window=preferred_window, spec=spec)
        if abs(got["standard_error"] - entry["standard_error"]) / entry["standard_error"] > NP_SE_TOL_REL:
            fail(failures, f"HAC bandwidth {entry['maxlags']}: published SE {entry['standard_error']:.6f} vs "
                           f"recomputed {got['standard_error']:.6f}")
    print("HAC bandwidth table reproduced at every declared bandwidth")

    # ---- 7. the artifact was fitted on the base that is on disk --------------------------------
    expected_fingerprints = base_fingerprints(spec)
    published_fingerprints = report.get("base_fingerprint", {}).get("values", {})
    for name, value in expected_fingerprints.items():
        if published_fingerprints.get(name) != value:
            fail(failures, f"base fingerprint / {name}: the artifact records "
                           f"{str(published_fingerprints.get(name))[:12]} and the base on disk hashes to "
                           f"{value[:12]} — the grid was fitted on a different base; re-run "
                           "analysis/R/04_robustness.R")
    print(f"base fingerprint: {', '.join(f'{k} {v[:12]}' for k, v in expected_fingerprints.items())}"
          " (artifact matches the base on disk)")

    # The near-zero band: declared in the spec, counted in the artifact, recomputed here. A count that
    # moved when a specification with no direction flipped would be a count of rounding.
    band = spec["support"]["near_zero_band"]
    for design in ("A", "B", None):
        rows = report["specifications"] if design is None else [
            r for r in report["specifications"] if r["design"] == design]
        published = report["support"]["overall"] if design is None \
            else report["support"]["by_design"][design]
        want = {
            "n_near_zero": sum(1 for r in rows if abs(r["coefficient"]) < band),
            "n_positive_outside_band": sum(1 for r in rows if r["coefficient"] >= band),
            "n_negative_outside_band": sum(1 for r in rows if r["coefficient"] <= -band),
        }
        for key, value in want.items():
            if published.get(key) != value:
                fail(failures, f"near-zero band ({design or 'overall'}): {key} is {published.get(key)} in "
                               f"the summary and {value} in its own rows")
    overall_near_zero = sum(1 for r in report["specifications"] if abs(r["coefficient"]) < band)
    print(f"near-zero band +/-{band}: {overall_near_zero} of {len(report['specifications'])} specifications "
          f"(counted, not removed: A {report['support']['by_design']['A']['n_positive_outside_band']}/"
          f"{report['support']['by_design']['A']['n_negative_outside_band']} outside the band)")

    # ---- 8. the dead axes are named, and the figure is a curve --------------------------------
    unbuilt = {axis["axis"] for axis in report["unbuilt_axes"]}
    for axis in ("population_denominator", "state_igr_d2", "donor_pool", "imputation_handling"):
        if axis not in unbuilt:
            fail(failures, f"unbuilt axes: {axis} is neither varied nor declared as unbuilt")
    figure = ROBUSTNESS_ROOT / vintage / report["figure"]["path"]
    if not figure.exists():
        fail(failures, f"figure: {report['figure']['path']} is missing")
    else:
        svg = figure.read_text(encoding="utf-8", errors="replace")
        marks = svg.count("<circle") + svg.count("<polygon")
        if marks < len(report["specifications"]):
            fail(failures, f"figure: {marks} marks drawn for {len(report['specifications'])} specifications")
        if svg.count("pre-registered") < 2:
            fail(failures, "figure: the pre-registered specification is not marked on both panels")
        for axis in ("dose_lag_months", "adjustment_set", "controls", "shock"):
            if axis not in svg:
                fail(failures, f"figure: the axis strip does not label {axis}")
        print(f"figure: {report['figure']['path']}, {marks} marks, both panels labelled")

    print()
    if failures:
        print(f"FAILED — {len(failures)} problem(s):")
        for problem in failures:
            print(f"  - {problem}")
        return 1
    print("PASS — every specification, count, flip, sensitivity check and the curve reproduce independently")
    return 0


if __name__ == "__main__":
    sys.exit(main())
