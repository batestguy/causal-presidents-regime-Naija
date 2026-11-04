"""P2 - fit Design C' on the declared windows: matrix completion vs SDID vs gsynth.

Reads the panel the P1 extractor wrote (`.inspect/design_c_prime_<outcome>_panel.csv`) and the declaration
in `analysis/specs/design_c_prime.yml`, fits the three declared arms on the declared windows, and writes an
**exploratory** table under `.inspect/`. No registry file is read for writing, none is written, and nothing
here is a published number.

    python scripts/fit_design_c_prime.py --outcome u5mr
    python scripts/fit_design_c_prime.py --outcome u5mr --windows yaradua   # one window, for timing

Run with the causal env, which is the one carrying duckdb, cvxpy and numpy:
    C:\\Users\\TOSHIBA\\miniconda3\\envs\\causality-handbook\\python.exe scripts/fit_design_c_prime.py
"""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from pathlib import Path

import cvxpy as cp
import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[1]
INSPECT = ROOT / ".inspect"
SPEC = ROOT / "analysis" / "specs" / "design_c_prime.yml"


# ---------------------------------------------------------------------------------------------
# Panel
# ---------------------------------------------------------------------------------------------
def load_panel(outcome: str) -> tuple[list[str], list[int], np.ndarray]:
    path = INSPECT / f"design_c_prime_{outcome}_panel.csv"
    if not path.exists():
        raise SystemExit(f"{path} not found: run scripts/extract_design_c_prime.py first")
    rows = list(csv.DictReader(path.open(encoding="utf-8")))
    countries = sorted({r["country"] for r in rows if r["role"] == "donor"})
    years = sorted({int(r["year"]) for r in rows})
    units = countries + ["NGA"]
    Y = np.full((len(units), len(years)), np.nan)
    index = {u: i for i, u in enumerate(units)}
    yindex = {y: i for i, y in enumerate(years)}
    for r in rows:
        Y[index[r["country"]], yindex[int(r["year"])]] = float(r["value"])
    return units, years, Y


# ---------------------------------------------------------------------------------------------
# Matrix completion: two-way effects + nuclear norm, solved with cvxpy/SCS
# ---------------------------------------------------------------------------------------------
def fit_mc(Y: np.ndarray, observed: np.ndarray, lam: float) -> dict:
    n, t = Y.shape
    alpha = cp.Variable(n)
    beta = cp.Variable(t)
    L = cp.Variable((n, t))
    residual = Y - (alpha[:, None] + beta[None, :] + L)
    idx = np.where(observed)
    # Only the year effect is pinned to sum zero. Pinning the unit effect as well pushes the panel's level
    # (~130 per 1,000 on u5mr) into L as a rank-1 term and inflates the nuclear norm from 47 to 7,651 on a
    # synthetic panel of this size: the optimum then describes the constraint, not the data. Found by the
    # solver check on 2026-11-04, before any real fit was reported.
    problem = cp.Problem(
        cp.Minimize(0.5 * cp.sum_squares(residual[idx]) + lam * cp.normNuc(L)),
        [cp.sum(beta) == 0],
    )
    problem.solve(solver="SCS", eps=1e-6, max_iters=50000, verbose=False)
    if problem.status not in ("optimal", "optimal_inaccurate"):
        raise RuntimeError(f"matrix completion failed: {problem.status}")
    value = np.where(observed, Y, np.nan)
    fitted = alpha.value[:, None] + beta.value[None, :] + L.value
    return {
        "status": problem.status,
        "lam": lam,
        "alpha": alpha.value,
        "beta": beta.value,
        "L": L.value,
        "fitted": fitted,
        "rank": int(np.linalg.matrix_rank(L.value, tol=1e-6 * max(1.0, np.abs(L.value).max()))),
        "pre_rmse": float(np.sqrt(np.nanmean((value - fitted)[observed] ** 2))),
        "pre_sd": float(np.nanstd(value[observed])),
    }


def refit_admm(Y: np.ndarray, observed: np.ndarray, lam: float, iters: int = 20000,
               tol: float = 1e-7, rho: float = 1.0) -> np.ndarray:
    """Second algorithm, same objective: ADMM with singular-value soft thresholding.

    Splits the two-way effects and the low-rank term into separate blocks and enforces Z = L by a scaled
    dual. Each iteration is one SVD of a 100 x 26 matrix, so it reaches the same optimum as the conic solve
    in a few hundred iterations and by a different route. The stop rule's solver check compares the two gaps.
    """
    n, t = Y.shape
    target_obs = np.where(observed, Y, 0.0)
    alpha = np.zeros(n)
    beta = np.zeros(t)
    for _ in range(50):
        alpha = np.where(observed, target_obs - beta[None, :], 0.0).sum(1) / observed.sum(1)
        beta = np.where(observed, target_obs - alpha[:, None], 0.0).sum(0) / observed.sum(0)
    Z = np.where(observed, target_obs - alpha[:, None] - beta[None, :], 0.0)
    L = np.zeros((n, t))
    dual = np.zeros((n, t))
    for iteration in range(iters):
        for _ in range(3):
            alpha = np.where(observed, target_obs - beta[None, :] - Z, 0.0).sum(1) / observed.sum(1)
            beta = np.where(observed, target_obs - alpha[:, None] - Z, 0.0).sum(0) / observed.sum(0)
        target = target_obs - alpha[:, None] - beta[None, :]
        Z = np.where(observed, (target + rho * (L - dual)) / (1 + rho), L - dual)
        u, s, vt = np.linalg.svd(Z + dual, full_matrices=False)
        L = (u * np.maximum(s - lam / rho, 0.0)) @ vt
        dual += Z - L
        if iteration % 100 == 0 and iteration > 0:
            primal = np.linalg.norm(Z - L) / max(1.0, np.linalg.norm(Z))
            if primal < tol:
                break
    return alpha[:, None] + beta[None, :] + Z


def lambda_max(Y: np.ndarray, observed: np.ndarray) -> float:
    """Largest singular value of the observed residual matrix, two-way effects removed."""
    n, t = Y.shape
    target = np.where(observed, Y, np.nan)
    with np.errstate(invalid="ignore"):
        row = np.nanmean(target, axis=1, keepdims=True)
        col = np.nanmean(target, axis=0, keepdims=True)
    filled = np.where(observed, Y, np.nanmean(Y[observed]) if observed.any() else 0.0)
    residual = np.where(observed, filled - row - col, 0.0)
    return float(np.linalg.svd(residual, compute_uv=False)[0])


def cross_validate(Y, observed, grid, folds, seeds, pre_cols, treated) -> dict:
    """K-fold over **units**, one assignment per seed; the reported lambda minimises held-out MSE.

    Each fold hides a fifth of the countries across every pre-period year, so the criterion answers the
    question the estimator is used for: can this panel predict a country it has not seen? v1 masked
    individual cells, which leaves the held-out cell's own row and column in the fit; that rewards
    interpolation, and it scored against donor post-years the design never declares.
    """
    n, _ = Y.shape
    scores = {lam: [] for lam in grid}
    for seed in seeds:
        rng = np.random.default_rng(seed)
        order = rng.permutation(n)
        for fold_units in np.array_split(order, folds):
            train = observed.copy()
            train[fold_units, :] = False
            truth = Y[np.ix_(fold_units, pre_cols)]
            keep = ~np.isnan(truth)
            for lam in grid:
                fitted = fit_mc(Y, train, lam)["fitted"]
                predicted = fitted[np.ix_(fold_units, pre_cols)][keep]
                scores[lam].append(float(np.mean((truth[keep] - predicted) ** 2)))
    means = {lam: float(np.mean(v)) for lam, v in scores.items()}
    best = min(means, key=means.get)
    return {"best": best, "mse": means, "boundary": best in (grid[0], grid[-1])}


# ---------------------------------------------------------------------------------------------
# One window
# ---------------------------------------------------------------------------------------------
def prepare_window(units, years, Y, spec, window_id):
    """Manifest gates, the donor rule and the observed mask, shared by the fit and the placebos.

    Returns either `{"status": "refused", ...}` or a dict of the arrays both passes must use. Sharing it is
    the point: a placebo fitted on a different donor pool than the estimate it ranks would not be a placebo.
    """
    manifest = json.loads((INSPECT / "design_c_prime_u5mr_manifest.json").read_text(encoding="utf-8"))
    entry = next((w for w in manifest["windows"] if w["id"] == window_id), None)
    if entry is None:
        return {"id": window_id, "status": "refused", "reason": "window not declared"}
    if entry["first_post_year"] is None:
        return {"id": window_id, "status": "refused", "reason": "no post year inside the study window"}
    # The declared floor, applied before a fit rather than after one: obasanjo has no pre year at all, and a
    # counterfactual fitted to zero pre years is the treated series extrapolated, not a comparison.
    minimum_pre = spec["windows"]["require_pre_years"]
    minimum_post = spec["windows"]["require_post_years"]
    if entry["pre_years"] < minimum_pre:
        return {
            "id": window_id, "status": "refused",
            "reason": f"gate_pre_years: {entry['pre_years']} pre years, {minimum_pre} required",
            "pre_years": entry["pre_years"], "post_years": entry["post_years"],
        }
    if entry["post_years"] < minimum_post:
        return {
            "id": window_id, "status": "refused",
            "reason": f"gate_post_years: {entry['post_years']} post years, {minimum_post} required",
            "pre_years": entry["pre_years"], "post_years": entry["post_years"],
        }
    start, end = int(entry["first_post_year"]), int(entry["last_post_year"])
    first = spec["input"]["years"]["first"]
    keep = [i for i, y in enumerate(years) if first <= y <= end]
    yrs = [years[i] for i in keep]
    Yw = Y[:, keep]
    treated = units.index("NGA")
    post = [j for j, y in enumerate(yrs) if y >= start]
    pre = [j for j, y in enumerate(yrs) if y < start]

    # The donor rule, applied by the engine: a donor missing any pre-period year is dropped by the rule,
    # not by preference, and the count is printed. Matrix completion tolerates gaps in the post period, so
    # the observed mask is the data itself minus the treated unit's held-out post cells.
    donors = [i for i in range(len(units)) if i != treated]
    complete = [i for i in donors if not np.isnan(Yw[i, pre]).any()]
    dropped = len(donors) - len(complete)
    if len(complete) < spec["input"]["donor_rule"]["minimum_donors"]:
        return {
            "id": window_id, "status": "refused",
            "reason": f"too few complete donors: {len(complete)}, {spec['input']['donor_rule']['minimum_donors']} required",
            "n_donors": len(complete),
        }
    Yw = Yw[complete + [treated]]
    treated = len(Yw) - 1
    observed = ~np.isnan(Yw)
    observed[treated, post] = False
    if not observed.any():
        return {"id": window_id, "status": "refused", "reason": "no observed cells"}
    return {
        "status": "prepared", "id": window_id, "start": start, "end": end, "years": yrs, "Y": Yw,
        "observed": observed, "post": post, "pre": pre, "treated": treated, "dropped": dropped,
    }


def fit_window(units, years, Y, spec, window_id, quick=False) -> dict:
    prepared = prepare_window(units, years, Y, spec, window_id)
    if prepared["status"] != "prepared":
        return prepared
    Yw, observed = prepared["Y"], prepared["observed"]
    yrs, post, pre, treated = prepared["years"], prepared["post"], prepared["pre"], prepared["treated"]
    start, end, dropped = prepared["start"], prepared["end"], prepared["dropped"]

    # The declared path: 12 log-spaced penalties ending strictly inside the regularisation path, so a
    # boundary hit is visible as one rather than hidden by a grid that stops at the edge.
    top = lambda_max(Yw, observed)
    grid = [round(top * f, 6) for f in np.geomspace(0.01, 0.9, 12)]
    cv = cross_validate(
        Yw, observed, grid,
        folds=3 if quick else spec["estimators"]["primary"]["cv"]["folds"],
        seeds=spec["estimators"]["primary"]["cv"]["seeds"][:1] if quick else spec["estimators"]["primary"]["cv"]["seeds"],
        pre_cols=pre,
        treated=treated,
    )
    fit = fit_mc(Yw, observed, cv["best"])
    second = refit_admm(Yw, observed, cv["best"])

    actual = Yw[treated, post]
    predicted = fit["fitted"][treated, post]
    gap = actual - predicted
    gap_second = actual - second[treated, post]
    spread = float(abs(gap.mean() - gap_second.mean()))

    # The penalty path, reported rather than summarised. A single cross-validated penalty hides the fact
    # that the counterfactual's magnitude, and on one window its sign, is a function of how much cross-country
    # structure the model is allowed to carry. Heavier penalties drive L to zero and leave the two-way
    # fixed-effects extrapolation; lighter ones let the panel's own country structure through. Both are the
    # declared estimator at a different lambda, so both belong beside the gap.
    path = {}
    for fraction in (0.01, 0.02, 0.05, 0.1, 0.2, 0.4, 0.7, 0.9):
        lam_f = round(top * fraction, 6)
        fitted = fit_mc(Yw, observed, lam_f)["fitted"]
        path[f"{fraction:g}"] = float(np.mean(actual - fitted[treated, post]))
    signs = {np.sign(round(value, 6)) for value in path.values()}

    return {
        "id": window_id,
        "status": "estimated",
        "first_year": start,
        "last_year": end,
        "pre_years": len(pre),
        "post_years": len(post),
        "n_donors": int(len(Yw) - 1),
        "donors_dropped_incomplete": dropped,
        "lambda": cv["best"],
        "lambda_max": top,
        "lambda_boundary": cv["boundary"],
        "rank": fit["rank"],
        "pre_rmse": fit["pre_rmse"],
        "pre_ratio": fit["pre_rmse"] / fit["pre_sd"] if fit["pre_sd"] else None,
        "cv_mse": cv["mse"],
        "gap": [float(g) for g in gap],
        "gap_years": [int(yrs[j]) for j in post],
        "mean_gap": float(np.mean(gap)),
        "solver_spread": spread,
        "admm_gap": float(np.mean(gap_second)),
        "solver_ok": spread <= max(1e-3, 1e-3 * abs(float(np.mean(gap)))),
        "penalty_path": path,
        "penalty_path_sign_changes": len(signs) > 1,
        "penalty_path_range": float(max(path.values()) - min(path.values())),
    }


# ---------------------------------------------------------------------------------------------
# R arms
# ---------------------------------------------------------------------------------------------
def run_r_arms(outcome: str, windows: list[dict]) -> dict:
    payload = INSPECT / f"design_c_prime_{outcome}_windows.json"
    payload.write_text(json.dumps(windows, indent=2), encoding="utf-8")
    panel = INSPECT / f"design_c_prime_{outcome}_panel.csv"
    out = INSPECT / f"design_c_prime_{outcome}_arms.json"
    script = ROOT / "analysis" / "R" / "12_design_c_prime_arms.R"
    result = subprocess.run(
        ["Rscript", str(script), str(panel), str(payload), str(out)],
        capture_output=True, text=True, encoding="utf-8",
    )
    sys.stdout.write(result.stdout)
    if result.returncode != 0:
        sys.stderr.write(result.stderr)
        raise SystemExit("R arms failed: see stderr above")
    return json.loads(out.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------------------------
# P3: placebos
# ---------------------------------------------------------------------------------------------
def placebo_gap(Yw: np.ndarray, observed: np.ndarray, treated_row: int, post: list[int],
                lam: float) -> float:
    """Refit with `treated_row` held out over the post years and return its mean gap.

    The penalty is the treated fit's own lambda: re-cross-validating 99 placebos would give each placebo a
    different penalty and make the distribution incomparable with the point it is ranking.
    """
    mask = observed.copy()
    mask[treated_row, post] = False
    fitted = fit_mc(Yw, mask, lam)["fitted"]
    return float(np.mean(Yw[treated_row, post] - fitted[treated_row, post]))


def run_placebos(row: dict, units, years, Y, spec) -> dict:
    """In-space, in-time and leave-one-donor-out placebos, the rank p and the interval, as declared."""
    prepared = prepare_window(units, years, Y, spec, row["id"])
    if prepared["status"] != "prepared":
        return {"id": row["id"], "status": "refused", "reason": prepared.get("reason", "window not prepared")}
    Yw, observed = prepared["Y"], prepared["observed"]
    yrs, post, pre, treated = prepared["years"], prepared["post"], prepared["pre"], prepared["treated"]
    start = prepared["start"]
    lam = row["lambda"]
    labels = [f"D{i:03d}" for i in range(len(Yw))]

    gaps = []
    for unit_row in range(len(Yw)):
        if unit_row == treated:
            continue
        gaps.append((labels[unit_row], placebo_gap(Yw, observed, unit_row, post, lam)))

    values = np.array([g for _, g in gaps])
    treated_gap = float(row["mean_gap"])
    rank_p = float((np.sum(np.abs(values) >= abs(treated_gap)) + 1) / (len(values) + 1))
    low, high = (float(np.percentile(values, 2.5)), float(np.percentile(values, 97.5)))
    inside_interval = bool(low <= treated_gap <= high)

    # Leave one donor out: drop the country from the pool entirely, refit, and record how the gap moves.
    leave_one_out = []
    for unit_row in range(len(Yw)):
        if unit_row == treated:
            continue
        mask = observed.copy()
        mask[unit_row, :] = False
        fitted = fit_mc(Yw, mask, lam)["fitted"]
        leave_one_out.append(float(np.mean(Yw[treated, post] - fitted[treated, post])))
    flips = int(np.sum(np.sign(leave_one_out) != np.sign(treated_gap)))

    # In-time placebos: move the window back k years and re-estimate a gap in an untreated period.
    in_time = []
    for k in spec["placebos"]["in_time"]["backdate_years"]:
        pseudo_post = [j for j, y in enumerate(yrs) if start - k <= y <= start - 1]
        pseudo_pre = [j for j, y in enumerate(yrs) if y < start - k]
        if len(pseudo_pre) < spec["windows"]["require_pre_years"]:
            in_time.append({"backdate": k, "status": "not_runnable",
                            "reason": f"{len(pseudo_pre)} pre years, {spec['windows']['require_pre_years']} required"})
            continue
        mask = observed.copy()
        mask[treated, pseudo_post] = False
        fitted = fit_mc(Yw, mask, lam)["fitted"]
        gap = float(np.mean(Yw[treated, pseudo_post] - fitted[treated, pseudo_post]))
        in_time.append({"backdate": k, "status": "run", "gap": gap,
                        "ratio_to_treated": gap / treated_gap if treated_gap else None})

    return {
        "id": row["id"],
        "treated_gap": treated_gap,
        "n_placebos": len(values),
        "rank_p": rank_p,
        "smallest_attainable_p": 1.0 / (len(values) + 1),
        "interval_low": low,
        "interval_high": high,
        # Two different statements, kept apart: the percentile interval is the declared interval, and the
        # max-absolute test is the weaker one v1 printed under the same word "inside".
        "treated_inside_interval": inside_interval,
        "treated_within_max_placebo": bool(abs(treated_gap) <= np.max(np.abs(values))),
        "leave_one_out": {
            "n": len(leave_one_out),
            "min": float(np.min(leave_one_out)),
            "max": float(np.max(leave_one_out)),
            "sign_flips": flips,
        },
        "placebo_gaps": {label: round(g, 6) for label, g in gaps},
        "in_time": in_time,
    }


# ---------------------------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--outcome", default="u5mr")
    parser.add_argument("--windows", nargs="*", default=None)
    parser.add_argument("--quick", action="store_true", help="3 folds, one seed: timing only, not for reporting")
    parser.add_argument("--no-r", action="store_true", help="matrix completion only")
    parser.add_argument("--placebos", action="store_true", help="also run the P3 placebo pass")
    args = parser.parse_args()

    spec = yaml.safe_load(SPEC.read_text(encoding="utf-8"))
    manifest = json.loads((INSPECT / f"design_c_prime_{args.outcome}_manifest.json").read_text(encoding="utf-8"))
    ids = args.windows or [w["id"] for w in manifest["windows"]]

    units, years, Y = load_panel(args.outcome)
    print(f"Design C' P2 fit: outcome={args.outcome}, {len(units) - 1} donors, {len(years)} years")

    results = []
    for window_id in ids:
        row = fit_window(units, years, Y, spec, window_id, quick=args.quick)
        results.append(row)
        if row["status"] == "estimated":
            print(
                f"  {window_id:<9} mc gap {row['mean_gap']:+8.3f}  rank {row['rank']:>2}  "
                f"lambda {row['lambda']:.2f}  pre-ratio {row['pre_ratio']:.4f}  "
                f"solver spread {row['solver_spread']:.2e}  {'ok' if row['solver_ok'] else 'NOT CONVERGED'}  "
                f"penalty path range {row['penalty_path_range']:.2f}"
                f"{' SIGN CHANGES' if row['penalty_path_sign_changes'] else ''}"
                f"{' (boundary)' if row['lambda_boundary'] else ''}"
            )
        else:
            print(f"  {window_id:<9} refused: {row['reason']}")

    arms = {}
    if not args.no_r:
        arms = run_r_arms(args.outcome, [w for w in results if w["status"] == "estimated"])
    arms_by_id = {a["id"]: a for a in arms} if isinstance(arms, list) else {}

    placebos = {}
    if args.placebos:
        print("\n  P3 placebos (99 refits per window at the treated fit's own penalty)")
        for row in results:
            if row["status"] != "estimated":
                continue
            result = run_placebos(row, units, years, Y, spec)
            row["placebo"] = {
                "rank_p": result["rank_p"],
                "interval": [result["interval_low"], result["interval_high"]],
                "inside_interval": result["treated_inside_interval"],
                "leave_one_out": result["leave_one_out"],
            }
            placebos[row["id"]] = result
            print(
                f"  {row['id']:<9} gap {result['treated_gap']:+8.3f}  rank p {result['rank_p']:.3f}  "
                f"placebo 2.5-97.5% [{result['interval_low']:+.2f}, {result['interval_high']:+.2f}]  "
                f"{'inside' if result['treated_inside_interval'] else 'OUTSIDE'}  "
                f"leave-one-out sign flips {result['leave_one_out']['sign_flips']}/{result['leave_one_out']['n']}"
            )

    # The gate, evaluated as declared and recorded per window rather than inferred from a status word.
    if args.placebos and arms_by_id:
        print("\n  gate")
        for row in results:
            if row["status"] != "estimated":
                continue
            arm = arms_by_id.get(row["id"], {})

            def gap_of(name):
                block = arm.get(name) or {}
                value = block.get("gap")
                return None if not isinstance(value, (int, float)) else float(value)

            sdid, gsynth = gap_of("sdid"), gap_of("gsynth")
            failures = []
            if row["placebo"]["rank_p"] > 0.05:
                failures.append(f"rank_p {row['placebo']['rank_p']:.3f} > 0.05")
            runnable = [p for p in placebos[row["id"]]["in_time"] if p["status"] == "run"]
            too_big = [p for p in runnable if abs(p["gap"]) >= abs(row["mean_gap"])]
            if too_big:
                failures.append(
                    f"in_time placebo at +{too_big[0]['backdate']} yrs moves {too_big[0]['gap']:+.2f}, "
                    f"at least the estimate"
                )
            # "All three agree" is only checkable when all three ran; a refused arm is a failure in its own
            # right, and a disagreement between any two that did run is a failure too.
            missing = [name for name, value in (("sdid", sdid), ("gsynth", gsynth)) if value is None]
            if missing:
                failures.append(f"{' and '.join(missing)} arm refused, so sign agreement cannot be shown")
            else:
                signs = {np.sign(round(value, 6)) for value in (row["mean_gap"], sdid, gsynth)}
                if len(signs) > 1:
                    failures.append(
                        f"arms disagree on sign: mc {row['mean_gap']:+.2f}, sdid {sdid:+.2f}, gsynth {gsynth:+.2f}"
                    )
            row["gate_failures"] = failures
            row["gate_status"] = "identified" if not failures else "estimated_not_identified"
            print(f"  {row['id']:<9} {row['gate_status']}: {'; '.join(failures) if failures else 'all three checks pass'}")

        # Holm across the windows that carry a rank p, printed rather than merely declared. The scope is the
        # windows fitted in this run: with one outcome that is the declared multiplicity set, and if P5 ever
        # opens, the set must span the outcomes too (the artifact records the scope it used).
        ranked = sorted((r for r in results if r["status"] == "estimated"),
                        key=lambda r: r["placebo"]["rank_p"])
        m = len(ranked)
        for index, row in enumerate(ranked):
            row["holm_threshold"] = 0.05 / (m - index)
        print(f"  Holm at 0.05 across {m} windows: " + ", ".join(
            f"{r['id']} p {r['placebo']['rank_p']:.3f} vs {r['holm_threshold']:.4f}" for r in ranked))

    doc = {
        "phase": "P2" + ("+P3" if args.placebos else ""),
        "outcome": args.outcome,
        "spec": str(SPEC.relative_to(ROOT)).replace("\\", "/"),
        "spec_sha256": __import__("hashlib").sha256(SPEC.read_bytes()).hexdigest(),
        "note": "exploratory; no registry artifact, no published number",
        "windows": results,
        "arms": arms,
        "placebos": placebos,
        "holm_scope": [r["id"] for r in results if r["status"] == "estimated"],
    }
    out = INSPECT / f"design_c_prime_{args.outcome}_fits.json"
    out.write_text(json.dumps(doc, indent=2, allow_nan=False) + "\n", encoding="utf-8")

    print("\n  window    matrix completion   sdid      gsynth   sign agreement")
    for row in results:
        if row["status"] != "estimated":
            continue
        arm = arms_by_id.get(row["id"], {})

        def gap_of(name):
            block = arm.get(name) or {}
            value = block.get("gap")
            return None if not isinstance(value, (int, float)) else float(value)

        sdid, gsynth = gap_of("sdid"), gap_of("gsynth")
        gaps = [g for g in (row["mean_gap"], sdid, gsynth) if g is not None]
        signs = {np.sign(round(g, 6)) for g in gaps}
        verdict = "agree" if len(signs) == 1 else "DISAGREE" if len(signs) > 1 else "no arms"
        print(
            f"  {row['id']:<9} {row['mean_gap']:>10.3f}   "
            f"{'refused' if sdid is None else f'{sdid:+.3f}':>9}  "
            f"{'refused' if gsynth is None else f'{gsynth:+.3f}':>9}   {verdict}"
        )
    print(f"\n  wrote {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
