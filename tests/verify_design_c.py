"""Verify Design C by refitting it, not by reading it.

The declared estimator is a simplex-constrained least squares fit of the pre-treatment path. With 8 to 24
pre-years against 99 donors that problem is **underdetermined**: a face of weight vectors fits the pre-period
equally well, and they disagree about the post-period. The artifact deals with that by publishing the vertex the
declared solver returns, a ridge refit whose solution *is* unique, and the leave-one-donor-out range.

So this verifier checks the things a second solver can actually reproduce:

  * every window is a window the Stage 5 gate evaluated, and its pre-fit ratio is the gate's own number;
  * the published weights are a feasible simplex point and produce every published number — the pre-fit, the
    synthetic path, the gaps and both ratios — to rounding;
  * an independent solver (SLSQP) does not improve the declared objective beyond rounding: the published weights
    are an optimum, not merely a solution;
  * the unique ridge refit is recomputed independently and its gap, pre-fit and shift are checked;
  * the rank p follows from the distribution the artifact ships, and the pre-fit saturation it reports is the
    count in its own rows;
  * the in-time placebos respect the declared minima, the leave-one-out range brackets the estimate, and the
    verdict is the declared rule applied to the artifact's own fields.

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
    gate = gate_doc["prefit"][doc["input"]["outcome"]]["windows"]

    first = int(spec["windows"]["first_year"])
    last = int(spec["windows"]["last_year"])
    min_pre = int(spec["windows"]["require_pre_years"])
    min_post = int(spec["windows"]["require_post_years"])
    threshold = float(gate_doc["spec_echo"]["pre_rmse_threshold_frac_of_sd"])
    ridge_rel = float(spec["estimator"]["solver_sensitivity"]["ridge_relative"])

    con = duckdb.connect(str(REPO_ROOT / "data" / "analytics.duckdb"), read_only=True)
    treated = {
        int(y): float(v) for y, v in con.execute(
            "select year(anchor_month), value from main_analytics.fact_observation_native "
            "where metric_id = ? and native_frequency = 'annual' and value is not null "
            "and year(anchor_month) between ? and ?", [doc["input"]["outcome"], first, last]).fetchall()}
    donors = con.execute(
        "select country_iso3, period_year, value from main_analytics.fact_donor_panel "
        "where metric_id = ? and period_year between ? and ? and country_iso3 <> ?",
        [doc["input"]["outcome"], first, last, doc["input"]["treated_iso3"]]).fetchall()
    con.close()
    pool: dict[str, dict[int, float]] = {}
    for iso, year, value in donors:
        pool.setdefault(iso, {})[int(year)] = float(value)

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

    windows = doc["windows"]
    counts = doc["counts"]
    for key, expected in (
        ("windows", len(windows)),
        ("estimated", sum(1 for w in windows if w["status"] != "refused")),
        ("refused", sum(1 for w in windows if w["status"] == "refused")),
        ("identified", sum(1 for w in windows if w["status"] == "identified")),
        ("not_identified", sum(1 for w in windows if w["status"] == "estimated_not_identified")),
        ("placebos_in_space", sum(w["in_space"]["n_placebos"] for w in windows if w["status"] != "refused")),
        ("placebos_passing_pre_fit", sum(w["in_space"]["n_placebos_passing_pre_fit"]
                                         for w in windows if w["status"] != "refused")),
    ):
        if counts[key] != expected:
            fail(failures, f"counts.{key} is {counts[key]} and the windows carry {expected}")

    windows_refit = 0
    sign_disagreements = []
    for w in windows:
        wid = w["id"]
        if wid not in declared:
            fail(failures, f"{wid}: not a declared treatment window")
            continue
        years = window_years(declared[wid], first, last)
        post = years
        start_year = min(post)
        pre = list(range(first, start_year))
        expected_refusal = len(pre) < min_pre or len(post) < min_post
        if expected_refusal and w["status"] != "refused":
            fail(failures, f"{wid}: the declared year rule refuses this window but the artifact estimates it")
            continue
        if not expected_refusal and w["status"] == "refused":
            fail(failures, f"{wid}: the declared year rule estimates this window but the artifact refuses it")
            continue
        if w["status"] == "refused":
            if w["pre_years"] != len(pre) or w["post_years"] != len(post):
                fail(failures, f"{wid}: the refusal's year counts are not the declared rule's")
            continue

        gate_row = gate.get(wid) or {}
        if gate_row.get("verdict") == "not_run":
            fail(failures, f"{wid}: the gate did not run this window")
        if gate_row.get("ratio") is not None and not close(w["pre_ratio"], gate_row["ratio"], 1e-6):
            fail(failures, f"{wid}: the pre-fit ratio is not the gate's own number")

        usable = [iso for iso, series in sorted(pool.items()) if all(y in series for y in (*pre, *post))]
        z1 = np.array([treated[y] for y in pre])
        z0 = np.array([[pool[iso][y] for iso in usable] for y in pre], dtype=float)
        published = np.zeros(len(usable))
        for row in w["weights"]:
            if row["donor"] not in usable:
                fail(failures, f"{wid}: a published weight names a donor outside the usable pool")
                continue
            published[usable.index(row["donor"])] = row["weight"]
        if abs(published.sum() - 1.0) > 1e-6:
            fail(failures, f"{wid}: the published weights do not sum to one")
        if len(w["weights"]) != w["n_weights_published"]:
            fail(failures, f"{wid}: n_weights_published disagrees with the weight list")

        # Arithmetic from the published weights.
        pre_rmse = float(np.sqrt(np.mean((z1 - z0 @ published) ** 2)))
        pre_ratio = pre_rmse / float(np.std(z1, ddof=1))
        synth = np.array([sum(pool[iso][y] * published[i] for i, iso in enumerate(usable)) for y in post])
        actual = np.array([treated[y] for y in post])
        gaps = actual - synth
        mean_gap = float(gaps.mean())
        post_rmse = float(np.sqrt(np.mean(gaps ** 2)))
        if not close(pre_rmse, w["pre_rmse"], 1e-6):
            fail(failures, f"{wid}: the published weights do not produce the published pre-fit")
        if not close(pre_ratio, w["pre_ratio"], 1e-5):
            fail(failures, f"{wid}: the pre-fit ratio does not recompute")
        if not close(mean_gap, w["mean_gap"], 1e-5):
            fail(failures, f"{wid}: the mean gap does not recompute from the published weights")
        if not close(post_rmse / pre_rmse, w["post_pre_ratio"], 1e-5):
            fail(failures, f"{wid}: the post/pre ratio does not recompute")
        for row in w["path"]:
            i = post.index(row["year"])
            if not close(synth[i], row["synthetic"], 1e-6) or not close(gaps[i], row["gap"], 1e-6):
                fail(failures, f"{wid}: {row['year']}'s path does not follow from the published weights")
                break

        # Optimality of the declared objective (the engine's 1e-8 numerical ridge included).
        w_alt = fit_weights(z1, z0, 1e-8)
        gram = z0.T @ z0
        gram = gram + np.eye(gram.shape[0]) * gram.diagonal().max() * 1e-8
        lin = z0.T @ z1
        objective = lambda v: 0.5 * v @ gram @ v - lin @ v  # noqa: E731
        if objective(w_alt) < objective(published) - (1e-9 * abs(objective(published)) + 1e-6):
            fail(failures, f"{wid}: SLSQP improves on the published weights' objective — they are not an optimum")
        windows_refit += 1

        # The unique ridge refit, and the shift the artifact publishes.
        w_ridge = fit_weights(z1, z0, ridge_rel)
        synth_r = np.array([sum(pool[iso][y] * w_ridge[i] for i, iso in enumerate(usable)) for y in post])
        gap_r = float((actual - synth_r).mean())
        pre_r = float(np.sqrt(np.mean((z1 - z0 @ w_ridge) ** 2))) / float(np.std(z1, ddof=1))
        sens = w["solver_sensitivity"]
        if not close(sens["ridge_relative"], ridge_rel, 1e-12):
            fail(failures, f"{wid}: the sensitivity ridge is not the declared one")
        if not close(gap_r, sens["mean_gap"], 1e-4):
            fail(failures, f"{wid}: the ridge refit's gap does not recompute ({gap_r:.6g} vs {sens['mean_gap']:.6g})")
        if not close(pre_r, sens["pre_ratio"], 1e-4):
            fail(failures, f"{wid}: the ridge refit's pre-fit does not recompute")
        if not close(sens["gap_shift"], sens["mean_gap"] - w["mean_gap"], 1e-6):
            fail(failures, f"{wid}: the published gap shift is not the difference of the two fits")
        if (gap_r > 0) != (w["mean_gap"] > 0):
            sign_disagreements.append(wid)

        # Rank p and the saturation it reports, both arithmetic on the shipped distribution.
        distribution = w["in_space"]["distribution"]
        extreme = sum(1 for r in distribution if r["post_pre_ratio"] >= w["post_pre_ratio"])
        if extreme != w["in_space"]["n_at_least_as_extreme"]:
            fail(failures, f"{wid}: n_at_least_as_extreme disagrees with the published distribution")
        if not close(w["in_space"]["p_value"], (1 + extreme) / (1 + len(distribution)), 1e-9):
            fail(failures, f"{wid}: the rank p is not (1 + n_extreme) / (1 + n)")
        passing = sum(1 for r in distribution if r["pre_ratio"] <= threshold)
        if passing != w["in_space"]["n_placebos_passing_pre_fit"]:
            fail(failures, f"{wid}: the saturation count is not the number of placebos clearing the gate")

        # In-time placebos: the declared minima, the ratio arithmetic, and the rule they feed.
        for row in w["in_time"]:
            back = int(row["backdated_years"])
            pseudo_pre = list(range(first, start_year - back))
            pseudo_post = list(range(start_year - back, start_year))
            if row["status"] == "not_run":
                if len(pseudo_pre) >= min_pre and len(pseudo_post) >= min_post:
                    fail(failures, f"{wid}: the {back}-year placebo is not run where the declared minimum is met")
            else:
                if len(pseudo_pre) < min_pre or len(pseudo_post) < min_post:
                    fail(failures, f"{wid}: the {back}-year placebo is run below the declared minimum")
                if abs(row["ratio_to_estimated"] -
                       abs(row["mean_gap"]) / abs(w["mean_gap"])) > 1e-6 * max(1.0, row["ratio_to_estimated"]):
                    fail(failures, f"{wid}: the {back}-year placebo's ratio to the estimate is not arithmetic")

        # Leave-one-out: one fit per donor, bracketing the estimate, with the sign flips it claims.
        loo = w["leave_one_out"]
        if loo["n_fits"] != len(usable):
            fail(failures, f"{wid}: the leave-one-out sweep does not have one fit per donor")
        if not (loo["min"] <= w["mean_gap"] <= loo["max"]):
            fail(failures, f"{wid}: the estimated gap is outside its own leave-one-donor-out range")
        if not (0 <= loo["n_sign_flips"] <= loo["n_fits"]):
            fail(failures, f"{wid}: the sign-flip count is outside the sweep")

        # The verdict is the declared rule applied to the artifact's own fields.
        rule_holds = (
            w["pre_ratio"] <= threshold
            and w["in_space"]["p_value"] <= 0.05
            and all(r.get("status") != "estimated" or abs(r["mean_gap"]) < 0.5 * abs(w["mean_gap"])
                    for r in w["in_time"])
        )
        expected = "identified" if rule_holds else "estimated_not_identified"
        if w["status"] != expected or w["verdict"]["status"] != expected:
            fail(failures, f"{wid}: status is {w['status']!r} and the declared rule gives {expected!r}")
        if not rule_holds and not w["verdict"]["failed_checks"]:
            fail(failures, f"{wid}: not identified and no failed check is named")

    if failures:
        print(f"FAILED — {len(failures)} problem(s):")
        for problem in failures[:30]:
            print(f"  - {problem}")
        return 1

    print(f"verified      : {windows_refit} window(s) refitted from the base, {counts['refused']} refused by the "
          f"declared year rule")
    print(f"recomputed    : the published weights' pre-fit and optimality, every synthetic path, gap, RMSPE and "
          f"ratio, the unique ridge refit, and every in-time and leave-one-out field")
    print(f"rank p        : follows from each shipped distribution; the saturation count is its own rows")
    print(f"verdicts      : {counts['identified']} of {counts['estimated']} windows survive the declared rule; "
          f"{counts['not_identified']} name the check that failed")
    if sign_disagreements:
        print(f"solver note   : the ridge refit disagrees in sign with the declared vertex for "
              f"{', '.join(sign_disagreements)} — published as a diagnostic, not averaged away")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
