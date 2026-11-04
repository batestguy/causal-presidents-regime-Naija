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


def cross_validate(Y, observed, grid, folds, mask_fraction, seeds) -> dict:
    """K-fold over the observed cells, one mask per seed; the reported lambda minimises held-out MSE."""
    idx = np.argwhere(observed)
    scores = {lam: [] for lam in grid}
    for seed in seeds:
        rng = np.random.default_rng(seed)
        order = rng.permutation(len(idx))
        cut = int(round(mask_fraction * len(idx)))
        held = idx[order[:cut]]
        for fold in range(folds):
            fold_held = held[fold::folds]
            train = observed.copy()
            train[fold_held[:, 0], fold_held[:, 1]] = False
            for lam in grid:
                fit = fit_mc(Y, train, lam)
                predicted = fit["fitted"][fold_held[:, 0], fold_held[:, 1]]
                truth = Y[fold_held[:, 0], fold_held[:, 1]]
                scores[lam].append(float(np.mean((truth - predicted) ** 2)))
    means = {lam: float(np.mean(v)) for lam, v in scores.items()}
    best = min(means, key=means.get)
    return {"best": best, "mse": means}


# ---------------------------------------------------------------------------------------------
# One window
# ---------------------------------------------------------------------------------------------
def fit_window(units, years, Y, spec, window_id, quick=False) -> dict:
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
    observed = np.ones_like(Yw, dtype=bool)
    observed[treated, [j for j, y in enumerate(yrs) if y >= start]] = False
    if np.isnan(Yw[observed]).any():
        return {"id": window_id, "status": "refused", "reason": "a donor cell required by the fit is missing"}

    grid = [round(lambda_max(Yw, observed) * f, 6) for f in (0.02, 0.05, 0.1, 0.2, 0.3, 0.5, 0.7, 0.9)]
    cv = cross_validate(
        Yw, observed, grid,
        folds=3 if quick else spec["estimators"]["primary"]["cv"]["folds"],
        mask_fraction=spec["estimators"]["primary"]["cv"]["mask_fraction"],
        seeds=spec["estimators"]["primary"]["cv"]["seeds"][:1] if quick else spec["estimators"]["primary"]["cv"]["seeds"],
    )
    fit = fit_mc(Yw, observed, cv["best"])
    second = refit_admm(Yw, observed, cv["best"])

    post = [j for j, y in enumerate(yrs) if y >= start]
    pre = [j for j, y in enumerate(yrs) if y < start]
    actual = Yw[treated, post]
    predicted = fit["fitted"][treated, post]
    gap = actual - predicted
    gap_second = actual - second[treated, post]
    spread = float(abs(gap.mean() - gap_second.mean()))

    return {
        "id": window_id,
        "status": "estimated",
        "first_year": start,
        "last_year": end,
        "pre_years": len(pre),
        "post_years": len(post),
        "n_donors": len(units) - 1,
        "lambda": cv["best"],
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
    """In-space and in-time placebos, the rank p, and the placebo interval, exactly as declared."""
    first = spec["input"]["years"]["first"]
    start, end = row["first_year"], row["last_year"]
    keep = [i for i, y in enumerate(years) if first <= y <= end]
    yrs = [years[i] for i in keep]
    Yw = Y[:, keep]
    treated = units.index("NGA")
    observed = np.ones_like(Yw, dtype=bool)
    post = [j for j, y in enumerate(yrs) if y >= start]
    pre = [j for j, y in enumerate(yrs) if y < start]
    observed[treated, post] = False
    lam = row["lambda"]

    gaps = []
    for unit_row, unit in enumerate(units):
        if unit == "NGA":
            continue
        gaps.append((unit, placebo_gap(Yw, observed, unit_row, post, lam)))

    values = np.array([g for _, g in gaps])
    treated_gap = float(row["mean_gap"])
    rank_p = float((np.sum(np.abs(values) >= abs(treated_gap)) + 1) / (len(values) + 1))
    low, high = (float(np.percentile(values, 2.5)), float(np.percentile(values, 97.5)))
    inside = bool(abs(treated_gap) <= np.max(np.abs(values)))

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
        "treated_inside_placebo_range": inside,
        "placebo_gaps": {unit: round(g, 6) for unit, g in gaps},
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
                f"solver spread {row['solver_spread']:.2e}  {'ok' if row['solver_ok'] else 'NOT CONVERGED'}"
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
                "inside": result["treated_inside_placebo_range"],
            }
            placebos[row["id"]] = result
            print(
                f"  {row['id']:<9} gap {result['treated_gap']:+8.3f}  rank p {result['rank_p']:.3f}  "
                f"placebo 2.5-97.5% [{result['interval_low']:+.2f}, {result['interval_high']:+.2f}]  "
                f"{'inside' if result['treated_inside_placebo_range'] else 'OUTSIDE'}"
            )

    doc = {
        "phase": "P2" + ("+P3" if args.placebos else ""),
        "outcome": args.outcome,
        "spec": str(SPEC.relative_to(ROOT)).replace("\\", "/"),
        "note": "exploratory; no registry artifact, no published number",
        "windows": results,
        "arms": arms,
        "placebos": placebos,
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
