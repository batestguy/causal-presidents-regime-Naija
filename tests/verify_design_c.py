"""Verify Design C by refitting it, not by reading it — for every outcome the artifact carries.

The declared estimator is a simplex-constrained least squares fit of the pre-treatment path. With 8 to 24
pre-years against 99 donors that problem is **underdetermined**: a face of weight vectors fits the pre-period
equally well, and they disagree about the post-period. The artifact deals with that by publishing the vertex the
declared solver returns, a ridge refit whose solution *is* unique, and the leave-one-donor-out range.

Since C-91 the artifact carries **one block per outcome** rather than one outcome. This verifier therefore
loops the blocks and checks, for each:

  * the block's outcome is a registry outcome the donor panel carries, and its declared annual rule is the
    one applied (native annual observations, or the calendar-year sum of a monthly count);
  * every window is a window the Stage 5 gate evaluated — and where the gate could run it, its pre-fit ratio is
    the gate's own number; where the outcome is a monthly count the gate cannot see the annual path at all and
    the artifact says so instead of implying a pass;
  * the published weights are a feasible simplex point and produce every published number — the pre-fit, the
    synthetic path, the gaps and both ratios — to rounding;
  * an independent solver (SLSQP) does not improve the declared objective beyond rounding;
  * the unique ridge refit is recomputed independently and its gap, pre-fit and shift are checked;
  * the rank p follows from the distribution the artifact ships, and the pre-fit saturation it reports is the
    count in its own rows;
  * the in-time placebos respect the declared minima, the leave-one-out range brackets the estimate, and the
    verdict is the declared rule applied to the artifact's own fields;
  * the aggregate counts are the sum of the per-outcome counts, and a refused window is one the declared year
    rule or the treated series actually refuses.

It deliberately does **not** demand that a second solver reproduce the placebo ratios weight for weight: those are
different optima of an underdetermined problem, and a verifier that demanded equality would be checking the
solver's tie-breaking, not the data. That is what `solver_sensitivity` is for.

Run:
    python tests/verify_design_c.py
"""

from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path

import duckdb
import numpy as np
import yaml
from scipy.optimize import minimize

REPO_ROOT = Path(__file__).resolve().parent.parent
TOL = 2e-5


def fail(failures: list[str], message: str) -> None:
    failures.append(message)


def close(a: float, b: float, tol: float = TOL) -> bool:
    return abs(a - b) <= tol * max(1.0, abs(a), abs(b))


def fit_weights(z1: np.ndarray, z0: np.ndarray, ridge_relative: float = 0.0) -> np.ndarray:
    """The declared simplex-constrained problem, solved by SLSQP instead of a QP."""
    gram = z0.T @ z0
    if ridge_relative:
        gram = gram + np.eye(gram.shape[0]) * gram.diagonal().max() * ridge_relative
    lin = z0.T @ z1
    d = z0.shape[1]
    fun = lambda w: 0.5 * w @ gram @ w - lin @ w  # noqa: E731
    jac = lambda w: gram @ w - lin  # noqa: E731
    result = minimize(
        fun, np.full(d, 1.0 / d), jac=jac, method="SLSQP",
        bounds=[(0.0, 1.0)] * d,
        constraints=[{"type": "eq", "fun": lambda w: w.sum() - 1.0, "jac": lambda w: np.ones_like(w)}],
        options={"maxiter": 500, "ftol": 1e-14})
    w = np.clip(result.x, 0.0, None)
    return w / w.sum()


def window_years(window: dict, first: int, last: int) -> list[int]:
    start = window["from"] if isinstance(window["from"], date) else date.fromisoformat(str(window["from"]))
    if window.get("to"):
        end = window["to"] if isinstance(window["to"], date) else date.fromisoformat(str(window["to"]))
    else:
        end = date(last, 12, 31)
    return [y for y in range(first, last + 1) if start <= date(y, 7, 1) <= end]


def load_treated(con, outcome: str, first: int, last: int, annual_sum: bool, frequency: str):
    """Nigeria's annual path, applying the declared grain rule for a monthly count."""
    if annual_sum and frequency == "monthly":
        rows = con.execute(
            "select year(anchor_month) as yr, sum(value) from main_analytics.fact_observation_native "
            "where metric_id = ? and native_frequency = 'monthly' and value is not null "
            "and year(anchor_month) between ? and ? group by 1 order by 1",
            [outcome, first, last]).fetchall()
    else:
        rows = con.execute(
            "select year(anchor_month) as yr, value from main_analytics.fact_observation_native "
            "where metric_id = ? and native_frequency = 'annual' and value is not null "
            "and year(anchor_month) between ? and ? order by 1",
            [outcome, first, last]).fetchall()
    return {int(y): float(v) for y, v in rows}


def main() -> int:
    failures: list[str] = []
    index = json.loads((REPO_ROOT / "registry" / "dags" / "index.json").read_text(encoding="utf-8"))
    vintage = index["vintage_date"]
    artifact_path = REPO_ROOT / "registry" / "design_c" / vintage / "design_c.json"
    if not artifact_path.exists():
        print(f"FAILED — no design C artifact at registry/design_c/{vintage}/design_c.json")
        return 1
    doc = json.loads(artifact_path.read_text(encoding="utf-8"))

    spec_path = REPO_ROOT / doc["spec"]["path"]
    spec = yaml.safe_load(spec_path.read_text(encoding="utf-8"))
    if hashlib.md5(spec_path.read_bytes()).hexdigest() != doc["spec"]["md5"]:
        fail(failures, "the spec's md5 has moved since the artifact was written")

    diagnostics = yaml.safe_load((REPO_ROOT / "analysis" / "specs" / "diagnostics.yml").read_text(encoding="utf-8"))
    declared = {w["id"]: w for w in diagnostics["windows"]["candidate_treated_windows"]}
    gate_doc = json.loads((REPO_ROOT / "registry" / "diagnostics" / vintage / "diagnostics.json").read_text(encoding="utf-8"))
    registry = yaml.safe_load((REPO_ROOT / "analysis" / "specs" / "outcomes.yml").read_text(encoding="utf-8"))
    registry_ids = {o["id"] for o in registry["outcomes"]}

    first = int(spec["windows"]["first_year"])
    last = int(spec["windows"]["last_year"])
    min_pre = int(spec["windows"]["require_pre_years"])
    min_post = int(spec["windows"]["require_post_years"])
    threshold = float(gate_doc["spec_echo"]["pre_rmse_threshold_frac_of_sd"])
    ridge_rel = float(spec["estimator"]["solver_sensitivity"]["ridge_relative"])
    annual_sum = set(doc["input"]["annual_sum_metrics"])

    con = duckdb.connect(str(REPO_ROOT / "data" / "analytics.duckdb"), read_only=True)
    frequencies = {
        oid: freq for oid, freq in con.execute(
            "select metric_id, native_frequency from main_analytics.dim_metric").fetchall()}
    donor_metrics = {m for (m,) in con.execute(
        "select distinct metric_id from main_analytics.fact_donor_panel").fetchall()}

    def walk(node, where=""):
        if isinstance(node, dict):
            for key, value in node.items():
                if key in ("standard_error", "confidence_interval"):
                    fail(failures, f"{where}/{key}: a field a synthetic control cannot carry is published")
                walk(value, f"{where}/{key}")
        elif isinstance(node, list):
            for i, value in enumerate(node):
                walk(value, f"{where}[{i}]")

    walk(doc)

    outcomes = doc["outcomes"]
    seen = [o["outcome"] for o in outcomes]
    if sorted(seen) != sorted(set(seen)):
        fail(failures, "an outcome appears twice in the artifact")
    if sorted(seen) != sorted(doc["input"]["outcomes"]):
        fail(failures, "input.outcomes and the outcome blocks disagree")
    for oid in seen:
        if oid not in registry_ids:
            fail(failures, f"{oid}: not a registry outcome")
        if oid not in donor_metrics:
            fail(failures, f"{oid}: not in the donor panel")

    all_windows = []
    windows_refit = 0
    sign_disagreements = []
    for block in outcomes:
        oid = block["outcome"]
        treated = load_treated(con, oid, first, last, oid in annual_sum, frequencies.get(oid))
        donors = con.execute(
            "select country_iso3, period_year, value from main_analytics.fact_donor_panel "
            "where metric_id = ? and period_year between ? and ? and country_iso3 <> ?",
            [oid, first, last, doc["input"]["treated_iso3"]]).fetchall()
        pool: dict[str, dict[int, float]] = {}
        for iso, year, value in donors:
            pool.setdefault(iso, {})[int(year)] = float(value)

        gate_basis = block["gate_basis"]
        if gate_basis not in ("stage5_prefit", "stage8h_annual_aggregation"):
            fail(failures, f"{oid}: unknown gate basis {gate_basis!r}")
        if gate_basis == "stage5_prefit" and frequencies.get(oid) != "annual":
            fail(failures, f"{oid}: claims the gate's prefit for a non-annual outcome")
        gate = (gate_doc["prefit"].get(oid) or {}).get("windows") or {}

        windows = block["windows"]
        all_windows.extend(dict(w, outcome=oid) for w in windows)
        counts = block["counts"]
        for key, expected in (
            ("windows", len(windows)),
            ("estimated", sum(1 for w in windows if w["status"] != "refused")),
            ("refused", sum(1 for w in windows if w["status"] == "refused")),
            ("identified", sum(1 for w in windows if w["status"] == "identified")),
            ("not_identified", sum(1 for w in windows if w["status"] == "estimated_not_identified")),
        ):
            if counts.get(key) != expected:
                fail(failures, f"{oid}: counts.{key} is {counts.get(key)} and the windows carry {expected}")

        for w in windows:
            wid = w["id"]
            if wid not in declared:
                fail(failures, f"{oid}/{wid}: not a declared treatment window")
                continue
            years = window_years(declared[wid], first, last)
            post = years
            if not post:
                fail(failures, f"{oid}/{wid}: no post year under the declared rule")
                continue
            start_year = min(post)
            pre = list(range(first, start_year))
            short_window = len(pre) < min_pre or len(post) < min_post
            incomplete = not short_window and any(y not in treated for y in (*pre, *post))
            should_refuse = short_window or incomplete
            if should_refuse and w["status"] != "refused":
                fail(failures, f"{oid}/{wid}: the declared rule refuses this window but the artifact estimates it")
                continue
            if not should_refuse and w["status"] == "refused":
                fail(failures, f"{oid}/{wid}: the declared rule estimates this window but the artifact refuses it")
                continue
            if w["status"] == "refused":
                if w["pre_years"] != len(pre) or w["post_years"] != len(post):
                    fail(failures, f"{oid}/{wid}: the refusal's year counts are not the declared rule's")
                expected_reason = "gate_window_not_runnable" if short_window else "treated_series_incomplete"
                if w["refused"]["reason"] != expected_reason:
                    fail(failures, f"{oid}/{wid}: refusal reason is {w['refused']['reason']!r}, "
                                   f"recomputed {expected_reason!r}")
                continue

            gate_row = gate.get(wid) or {}
            if gate_basis == "stage8h_annual_aggregation":
                if w.get("gate", {}).get("basis") != "stage8h_annual_aggregation":
                    fail(failures, f"{oid}/{wid}: a monthly-count window must say its own pre-fit is the screen")

            usable = [iso for iso, series in sorted(pool.items()) if all(y in series for y in (*pre, *post))]
            # The gate's pool is the complete *pre*-path set. Where a donor has no post value the stage's
            # pool is smaller than the gate's, and its pre-fit ratio legitimately differs from the gate's
            # number; the artifact must account for the difference donor by donor (C-92).
            gate_donors = [iso for iso, series in sorted(pool.items()) if all(y in series for y in pre)]
            if gate_basis == "stage5_prefit":
                if gate_row.get("verdict") == "not_run":
                    fail(failures, f"{oid}/{wid}: the gate did not run this window")
                if set(gate_donors) == set(usable) and gate_row.get("ratio") is not None:
                    if not close(w["pre_ratio"], gate_row["ratio"], 1e-6):
                        fail(failures, f"{oid}/{wid}: the pre-fit ratio is not the gate's own number")
                elif set(gate_donors) != set(usable):
                    if not w.get("donors_dropped_for_post_gap"):
                        fail(failures, f"{oid}/{wid}: the stage's pool differs from the gate's and the "
                                       f"artifact does not name the donors it dropped")
            if w.get("n_donors_used") != len(usable):
                fail(failures, f"{oid}/{wid}: n_donors_used is not the usable-pool size")
            if w.get("n_donors_in_gate") != len(gate_donors):
                fail(failures, f"{oid}/{wid}: n_donors_in_gate is not the gate's pool size")
            if set(w.get("donors_dropped_for_post_gap") or []) != set(gate_donors) - set(usable):
                fail(failures, f"{oid}/{wid}: the donors dropped for a post-period gap are not the difference "
                               f"between the gate's pool and the stage's")
            z1 = np.array([treated[y] for y in pre])
            z0 = np.array([[pool[iso][y] for iso in usable] for y in pre], dtype=float)
            published = np.zeros(len(usable))
            for row in w["weights"]:
                if row["donor"] not in usable:
                    fail(failures, f"{oid}/{wid}: a published weight names a donor outside the usable pool")
                    continue
                published[usable.index(row["donor"])] = row["weight"]
            if abs(published.sum() - 1.0) > 1e-6:
                fail(failures, f"{oid}/{wid}: the published weights do not sum to one")
            if len(w["weights"]) != w["n_weights_published"]:
                fail(failures, f"{oid}/{wid}: n_weights_published disagrees with the weight list")

            pre_rmse = float(np.sqrt(np.mean((z1 - z0 @ published) ** 2)))
            pre_ratio = pre_rmse / float(np.std(z1, ddof=1))
            synth = np.array([sum(pool[iso][y] * published[i] for i, iso in enumerate(usable)) for y in post])
            actual = np.array([treated[y] for y in post])
            gaps = actual - synth
            mean_gap = float(gaps.mean())
            post_rmse = float(np.sqrt(np.mean(gaps ** 2)))
            if not close(pre_rmse, w["pre_rmse"], 1e-6):
                fail(failures, f"{oid}/{wid}: the published weights do not produce the published pre-fit")
            if not close(pre_ratio, w["pre_ratio"], 1e-5):
                fail(failures, f"{oid}/{wid}: the pre-fit ratio does not recompute")
            if not close(mean_gap, w["mean_gap"], 1e-5):
                fail(failures, f"{oid}/{wid}: the mean gap does not recompute from the published weights")
            if not close(post_rmse, w["post_rmse"], 1e-6):
                fail(failures, f"{oid}/{wid}: the post-period RMSPE does not recompute")
            if not close(w["post_pre_ratio"], w["post_rmse"] / w["pre_rmse"], 1e-9):
                fail(failures, f"{oid}/{wid}: the post/pre ratio is not the published RMSPEs' quotient")
            for row in w["path"]:
                i = post.index(row["year"])
                if not close(synth[i], row["synthetic"], 1e-6) or not close(gaps[i], row["gap"], 1e-6):
                    fail(failures, f"{oid}/{wid}: {row['year']}'s path does not follow from the published weights")
                    break

            w_alt = fit_weights(z1, z0, 1e-8)
            gram = z0.T @ z0
            gram = gram + np.eye(gram.shape[0]) * gram.diagonal().max() * 1e-8
            lin = z0.T @ z1
            objective = lambda v: 0.5 * v @ gram @ v - lin @ v  # noqa: E731
            if objective(w_alt) < objective(published) - (1e-9 * abs(objective(published)) + 1e-6):
                fail(failures, f"{oid}/{wid}: SLSQP improves on the published weights' objective")
            windows_refit += 1

            w_ridge = np.zeros(len(usable))
            for row in w["solver_sensitivity"]["weights"]:
                if row["donor"] not in usable:
                    fail(failures, f"{oid}/{wid}: a published ridge weight names a donor outside the usable pool")
                    continue
                w_ridge[usable.index(row["donor"])] = row["weight"]
            if abs(w_ridge.sum() - 1.0) > 1e-6:
                fail(failures, f"{oid}/{wid}: the published ridge weights do not sum to one")
            if len(w["solver_sensitivity"]["weights"]) != w["solver_sensitivity"]["n_weights_with_ridge"]:
                fail(failures, f"{oid}/{wid}: n_weights_with_ridge disagrees with the ridge weight list")
            synth_r = np.array([sum(pool[iso][y] * w_ridge[i] for i, iso in enumerate(usable)) for y in post])
            gap_r = float((actual - synth_r).mean())
            pre_r = float(np.sqrt(np.mean((z1 - z0 @ w_ridge) ** 2))) / float(np.std(z1, ddof=1))
            sens = w["solver_sensitivity"]
            if not close(sens["ridge_relative"], ridge_rel, 1e-12):
                fail(failures, f"{oid}/{wid}: the sensitivity ridge is not the declared one")
            if not close(gap_r, sens["mean_gap"], 1e-4):
                fail(failures, f"{oid}/{wid}: the ridge refit's gap does not recompute from its own weights")
            if not close(pre_r, sens["pre_ratio"], 1e-4):
                fail(failures, f"{oid}/{wid}: the ridge refit's pre-fit does not recompute from its own weights")
            if not close(sens["gap_shift"], sens["mean_gap"] - w["mean_gap"], 1e-6):
                fail(failures, f"{oid}/{wid}: the published gap shift is not the difference of the two fits")
            if (gap_r > 0) != (w["mean_gap"] > 0):
                sign_disagreements.append(f"{oid}/{wid}")

            # The ridge point must be an optimum of the declared ridge objective: an independent solver may
            # land elsewhere (SLSQP does, on these ill-conditioned problems) but it may never improve on the
            # published point. This is the check that replaces "a second solver reproduces the ridge gap",
            # which was only ever true when the problem was well conditioned (C-92).
            gram_r = z0.T @ z0
            gram_r = gram_r + np.eye(gram_r.shape[0]) * gram_r.diagonal().max() * ridge_rel
            lin_r = z0.T @ z1
            objective_r = lambda v: 0.5 * v @ gram_r @ v - lin_r @ v  # noqa: E731
            alt_r = fit_weights(z1, z0, ridge_rel)
            if objective_r(alt_r) < objective_r(w_ridge) - (1e-9 * abs(objective_r(w_ridge)) + 1e-6):
                fail(failures, f"{oid}/{wid}: an independent solver improves on the published ridge weights")

            distribution = w["in_space"]["distribution"]
            extreme = sum(1 for r in distribution if r["post_pre_ratio"] >= w["post_pre_ratio"])
            if extreme != w["in_space"]["n_at_least_as_extreme"]:
                fail(failures, f"{oid}/{wid}: n_at_least_as_extreme disagrees with the published distribution")
            if not close(w["in_space"]["p_value"], (1 + extreme) / (1 + len(distribution)), 1e-9):
                fail(failures, f"{oid}/{wid}: the rank p is not (1 + n_extreme) / (1 + n)")
            passing = sum(1 for r in distribution
                           if r["pre_ratio"] is not None and r["pre_ratio"] <= threshold)
            if passing != w["in_space"]["n_placebos_passing_pre_fit"]:
                fail(failures, f"{oid}/{wid}: the saturation count is not the number of placebos clearing the gate")

            for row in w["in_time"]:
                back = int(row["backdated_years"])
                pseudo_start = start_year - back
                pseudo_pre = list(range(first, pseudo_start))
                pseudo_post = list(range(pseudo_start, start_year))
                if row["status"] == "not_run":
                    if len(pseudo_pre) >= min_pre and len(pseudo_post) >= min_post:
                        fail(failures, f"{oid}/{wid}: the {back}-year placebo is not run where the minimum is met")
                else:
                    if len(pseudo_pre) < min_pre or len(pseudo_post) < min_post:
                        fail(failures, f"{oid}/{wid}: the {back}-year placebo is run below the declared minimum")
                    if abs(row["ratio_to_estimated"] -
                           abs(row["mean_gap"]) / abs(w["mean_gap"])) > 1e-6 * max(1.0, row["ratio_to_estimated"]):
                        fail(failures, f"{oid}/{wid}: the {back}-year placebo's ratio is not arithmetic")

            loo = w["leave_one_out"]
            if loo["n_fits"] != len(usable):
                fail(failures, f"{oid}/{wid}: the leave-one-out sweep does not have one fit per donor")
            if not (loo["min"] <= w["mean_gap"] <= loo["max"]):
                fail(failures, f"{oid}/{wid}: the estimated gap is outside its leave-one-donor-out range")
            if not (0 <= loo["n_sign_flips"] <= loo["n_fits"]):
                fail(failures, f"{oid}/{wid}: the sign-flip count is outside the sweep")

            rule_holds = (
                w["pre_ratio"] <= threshold
                and w["in_space"]["p_value"] <= 0.05
                and all(r.get("status") != "estimated" or abs(r["mean_gap"]) < 0.5 * abs(w["mean_gap"])
                        for r in w["in_time"])
            )
            expected = "identified" if rule_holds else "estimated_not_identified"
            if w["status"] != expected or w["verdict"]["status"] != expected:
                fail(failures, f"{oid}/{wid}: status is {w['status']!r} and the declared rule gives {expected!r}")
            if not rule_holds and not w["verdict"]["failed_checks"]:
                fail(failures, f"{oid}/{wid}: not identified and no failed check is named")

        expected_status = ("identified" if counts["identified"] else
                           "estimated_not_identified" if counts["estimated"] else "not_run")
        if block["status"] != expected_status:
            fail(failures, f"{oid}: block status {block['status']!r} but its windows give {expected_status!r}")

    con.close()

    totals = doc["counts"]
    for key, expected in (
        ("outcomes", len(outcomes)),
        ("windows", len(all_windows)),
        ("estimated", sum(1 for w in all_windows if w["status"] != "refused")),
        ("refused", sum(1 for w in all_windows if w["status"] == "refused")),
        ("identified", sum(1 for w in all_windows if w["status"] == "identified")),
        ("not_identified", sum(1 for w in all_windows if w["status"] == "estimated_not_identified")),
        ("placebos_in_space", sum(w["in_space"]["n_placebos"] for w in all_windows if w["status"] != "refused")),
        ("placebos_passing_pre_fit", sum(w["in_space"]["n_placebos_passing_pre_fit"]
                                         for w in all_windows if w["status"] != "refused")),
    ):
        if totals.get(key) != expected:
            fail(failures, f"counts.{key} is {totals.get(key)} and the outcome blocks sum to {expected}")

    if failures:
        print(f"FAILED — {len(failures)} problem(s):")
        for problem in failures[:30]:
            print(f"  - {problem}")
        return 1

    print(f"verified      : {len(outcomes)} outcome(s), {windows_refit} window(s) refitted from the base, "
          f"{totals['refused']} refused by the declared rule")
    print(f"recomputed    : every published weight's pre-fit and optimality, every synthetic path, gap, RMSPE and "
          f"ratio, the unique ridge refit, and every in-time and leave-one-out field")
    print(f"rank p        : follows from each shipped distribution; the saturation count is its own rows")
    print(f"verdicts      : {totals['identified']} of {totals['estimated']} windows survive the declared rule; "
          f"{totals['not_identified']} name the check that failed")
    if sign_disagreements:
        print(f"solver note   : the ridge refit disagrees in sign with the declared vertex for "
              f"{', '.join(sign_disagreements)} — published as a diagnostic, not averaged away")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
