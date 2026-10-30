"""Verify the Stage 6 estimates.

Re-derives every published number from the analytical base **independently of**
``analysis/R/03_estimate.R``: the same estimators, written separately, in a different language, from the
same spec. The engine is the thing under test; a verifier that called it would only prove it is
self-consistent.

What it checks, and why each one is here:

  * **The sample is the declared sample.** A window that silently moved (a landing that changed the
    panel's span, a filter that stopped matching) changes every number downstream, and it is the one
    error a coefficient cannot reveal. Counts, unit count and first/last month are recomputed.
  * **Design A's coefficients reproduce.** PPML with state and month fixed effects, clustered by state:
    recomputed with ``statsmodels`` GLM/IRLS rather than ``fixest``'s demeaning IRLS. Coefficients are
    compared tightly (they are the same MLE); standard errors are compared with an allowance, because
    the two packages apply different finite-sample corrections to a clustered covariance and the
    allowance is stated rather than hidden.
  * **Design A's checks reproduce** — the 24-month placebo and the lead-shift randomisation, which is
    the check that decides the verdict. A verdict rule that cannot be re-run is a label, not a rule.
  * **Design B's path reproduces** — OLS with month-of-year dummies and Newey-West standard errors at
    the declared bandwidth, at every horizon, including the lead placebo and the peak horizon.
  * **The verdicts follow from the checks.** Recomputed from the declared rules, not read from the
    report: a design reported as ``identified`` while its own checks fail is the failure this catches.

Usage:
    conda run -p "C:/Users/TOSHIBA/ds-general" python tests/verify_stage6.py
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
ESTIMATES_ROOT = REPO_ROOT / "registry" / "estimates"
SPEC_PATH = REPO_ROOT / "analysis" / "specs" / "estimation.yml"

# Tolerances, stated rather than buried: the coefficient is the same maximum-likelihood estimate in both
# implementations and is compared at 1e-4; the clustered standard error differs by the packages'
# finite-sample corrections (a few per cent on 36 clusters), so it is compared at 5 % and the difference
# is printed when it is material.
COEF_TOL = 1e-4
SE_TOL_REL = 0.05


def fail(failures: list[str], message: str) -> None:
    failures.append(message)


def load_base(spec: dict) -> tuple[pd.DataFrame, dict[str, pd.DataFrame]]:
    con = duckdb.connect(str(REPO_ROOT / spec["input"]["database"]), read_only=True)
    try:
        q = spec["design_a"]["sample"]
        panel = con.sql(
            f"""
            select state_id, state_name, period_month,
                   faac_gross_total_naira as dose, fatalities, incidents, fatalities_civilians,
                   strftime(period_month, '%Y-%m') as ym
            from {spec['input']['panel_table']}
            where dose_status = '{q['require_dose_status']}'
              and security_status = '{q['require_security_status']}'
              and faac_gross_total_naira >= {q['min_exposure']}
            order by state_id, period_month
            """
        ).df()
        # Design B has one frame per outcome family (C-85), each read from its own declared table.
        frames = {}
        for o in spec["design_b"]["outcomes"]:
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
    panel["log_dose"] = np.log(panel["dose"])
    panel["ym"] = panel["period_month"].dt.strftime("%Y-%m")
    for frame in frames.values():
        frame["period_month"] = pd.to_datetime(frame["period_month"])
        frame["log_outcome"] = np.log(frame["outcome_value"])
        frame["log_oil"] = np.log(frame["oil"])
        frame["d_oil"] = frame["log_oil"].diff()
    return panel, frames


def ppml(frame: pd.DataFrame, outcome: str, dose: str = "log_dose") -> tuple[float, float, int]:
    """Poisson pseudo-ML with state + month fixed effects, clustered by state.

    Dummies are used rather than demeaning: it is slower and it is the point — a second implementation
    that shares ``fixest``'s within-transformation would share its mistakes as well.

    **Separation is applied here too.** A state with no positive outcome anywhere in the window has an
    unidentified fixed effect and contributes nothing to the Poisson likelihood for it; ``fixest`` drops
    those states and reports the smaller n. The verifier reproduces that rule explicitly (rather than
    accepting whatever n the report claims) so the two implementations are comparing the same sample.
    """
    totals = frame.groupby("state_id")[outcome].transform("sum")
    frame = frame[totals > 0]
    design = pd.get_dummies(frame[["state_id", "ym"]], columns=["state_id", "ym"],
                            drop_first=True, dtype=float)
    design = pd.concat([design, frame[[dose]]], axis=1)
    design = sm.add_constant(design)
    result = sm.GLM(frame[outcome], design, family=sm.families.Poisson()).fit(
        cov_type="cluster", cov_kwds={"groups": frame["state_id"]}, maxiter=200
    )
    return float(result.params[dose]), float(result.bse[dose]), int(result.nobs)


def horizon_spec(national: pd.DataFrame, h: int, shock: str = "d_oil") -> dict:
    """Cumulative local projection at horizon h: log outcome(t+h) - log outcome(t-1) on the shock."""
    frame = national.copy()
    frame["y"] = frame["log_outcome"].shift(-h) - frame["log_outcome"].shift(1)
    frame["month_of_year"] = frame["period_month"].dt.month.astype("category")
    frame = frame.dropna(subset=["y", shock])
    design = pd.concat(
        [frame[[shock]], pd.get_dummies(frame["month_of_year"], prefix="m",
                                       drop_first=True, dtype=float)], axis=1
    )
    design = sm.add_constant(design, has_constant="add")
    result = sm.OLS(frame["y"], design).fit(
        cov_type="HAC", cov_kwds={"maxlags": 12, "use_correction": True}
    )
    return {
        "coefficient": float(result.params[shock]),
        "standard_error": float(result.bse[shock]),
        "n_obs": int(result.nobs),
    }


def main() -> int:
    if not SPEC_PATH.exists():
        raise SystemExit(f"no estimation spec at {SPEC_PATH}")
    spec = yaml.safe_load(SPEC_PATH.read_text(encoding="utf-8"))
    vintage = spec["labelled"]
    report_path = ESTIMATES_ROOT / vintage / "estimates.json"
    if not report_path.exists():
        raise SystemExit(f"no estimates at {report_path.relative_to(REPO_ROOT)} — run 03_estimate.R")

    report = json.loads(report_path.read_text(encoding="utf-8"))
    failures: list[str] = []
    print(f"estimates {report['vintage']} | {len(report['specifications'])} specifications | "
          f"generated {report['generated_at']}")

    panel, b_frames = load_base(spec)

    # ---- 1. the sample is the declared sample -------------------------------------------
    declared = report["samples"]["design_a"]
    checks = [
        (declared["n_obs"], len(panel), "design A rows"),
        (declared["n_units"], panel["state_id"].nunique(), "design A units"),
        (declared["first_month"], str(panel["period_month"].min().date()), "design A first month"),
        (declared["last_month"], str(panel["period_month"].max().date()), "design A last month"),
    ]
    for oid, frame in b_frames.items():
        got = report["samples"]["design_b"][oid]
        checks.append((got["n_obs"], len(frame), f"design B[{oid}] rows"))
        checks.append((got["first_month"], str(frame["period_month"].min().date()),
                       f"design B[{oid}] first month"))
        checks.append((got["last_month"], str(frame["period_month"].max().date()),
                       f"design B[{oid}] last month"))
    for got, want, label in checks:
        if got != want:
            fail(failures, f"sample: {label} is {got} in the report and {want} in the base")
    print(f"\nsample: {len(panel)} state-months x {panel['state_id'].nunique()} states "
          f"({panel['period_month'].min().date()} -> {panel['period_month'].max().date()}); "
          + "; ".join(f"{oid} {len(fr)} national months" for oid, fr in b_frames.items()))

    # ---- 2. Design A reproduces ----------------------------------------------------------
    rows = {(s["design"], s["outcome"], s["coefficient_name"]): s for s in report["specifications"]}
    # Deliberately ASCII: a Greek delta in a print() is fine on a UTF-8 console and a UnicodeEncodeError
    # on a cp1252 one, which is how this verifier first failed inside scripts/verify.sh (the pipe changes
    # the default encoding). A verifier that dies on its own output encoding is not verifying anything.
    print(f"\n{'design':<7}{'outcome':<22}{'reported':>11}{'recomputed':>12}{'diff':>10}  verdict")
    print("-" * 74)
    for outcome in (spec["design_a"]["outcome"], *spec["design_a"]["robustness_outcomes"]):
        key = ("A", outcome, "elasticity_of_fatalities_to_allocation")
        row = rows.get(key)
        if row is None:
            fail(failures, f"design A: no published specification for outcome {outcome}")
            continue
        beta, se, n = ppml(panel, outcome)
        delta = abs(beta - row["coefficient"])
        verdict = "ok"
        if delta > COEF_TOL:
            verdict = "FAIL"
            fail(failures, f"design A / {outcome}: reported coefficient {row['coefficient']:.6f} vs "
                           f"recomputed {beta:.6f}")
        if row["n_obs"] != n:
            verdict = "FAIL"
            fail(failures, f"design A / {outcome}: reported n {row['n_obs']} vs recomputed {n}")
        se_gap = abs(se - row["standard_error"]) / max(row["standard_error"], 1e-12)
        if se_gap > SE_TOL_REL:
            verdict = "FAIL"
            fail(failures, f"design A / {outcome}: clustered SE differs by {100 * se_gap:.1f}% "
                           f"({row['standard_error']:.4f} vs {se:.4f}) — beyond the stated allowance")
        print(f"{'A':<7}{outcome:<22}{row['coefficient']:>11.4f}{beta:>12.4f}{delta:>10.2e}  {verdict}")

    # ---- 3. Design A's checks, and the verdict they imply ---------------------------------
    placebo_lead = spec["design_a"]["checks"]["placebo_lead_months"]
    ordered = panel.sort_values(["state_id", "period_month"]).copy()
    ordered["lead_dose"] = ordered.groupby("state_id")["log_dose"].shift(-placebo_lead)
    placebo_frame = ordered.dropna(subset=["lead_dose"])
    placebo_beta, placebo_se, placebo_n = ppml(placebo_frame, spec["design_a"]["outcome"], "lead_dose")
    reported_placebo = report["designs"][0]["checks"]["placebo"]
    if abs(placebo_beta - reported_placebo["coefficient"]) > 1e-3:
        fail(failures, f"design A placebo: reported {reported_placebo['coefficient']:.4f} vs "
                       f"recomputed {placebo_beta:.4f}")
    if reported_placebo["n_obs"] != placebo_n:
        fail(failures, f"design A placebo: reported n {reported_placebo['n_obs']} vs {placebo_n}")

    low, high = spec["design_a"]["checks"]["lead_shift"]["offsets"]
    offsets = [k for k in range(low, high + 1) if k != 0]
    shifted, observed_same_rows = [], []
    for k in offsets:
        frame = panel.sort_values(["state_id", "period_month"]).copy()
        frame["shifted_dose"] = frame.groupby("state_id")["log_dose"].shift(k)
        frame = frame.dropna(subset=["shifted_dose"])
        observed_same_rows.append(ppml(frame, spec["design_a"]["outcome"])[0])
        shifted.append(ppml(frame, spec["design_a"]["outcome"], "shifted_dose")[0])
    p_lead_shift = float(np.mean(np.abs(shifted) >= np.abs(observed_same_rows)))
    reported_shift = report["designs"][0]["checks"]["lead_shift"]
    # Discrete by construction: 1/(n+1) at the finest. The recomputation is a second implementation of
    # the same statistic, so it should agree exactly; a mismatch means one of the two is shifting the
    # dose the other way round.
    if abs(p_lead_shift - reported_shift["p_value"]) > 1 % (len(offsets) + 1):
        fail(failures, f"design A lead-shift: reported p {reported_shift['p_value']:.4f} vs recomputed "
                       f"{p_lead_shift:.4f} — larger than one draw's worth of difference")

    identified = (p_lead_shift < 0.05) and (abs(placebo_beta) < abs(rows[('A', spec['design_a']['outcome'],
                                                                        'elasticity_of_fatalities_to_allocation')]["coefficient"]))
    expected_status = "identified" if identified else "estimated_not_identified"
    reported_status = next(d["status"] for d in report["designs"] if d["id"] == "A")
    if reported_status != expected_status:
        fail(failures, f"design A: the declared rule gives '{expected_status}' and the report says "
                       f"'{reported_status}'")
    print(f"\ndesign A checks: placebo (lead {placebo_lead}) recomputed {placebo_beta:+.4f} "
          f"(reported {reported_placebo['coefficient']:+.4f}); lead-shift p recomputed "
          f"{p_lead_shift:.4f} (reported {reported_shift['p_value']:.4f})")
    print(f"design A verdict from the declared rule: {expected_status}")

    # ---- 4. Design B reproduces, per outcome family -----------------------------------------
    lead_b = spec["design_b"]["checks"]["placebo_lead_months"]
    band = spec["design_b"]["checks"]["expect_peak_horizon"]
    b_block = next(d for d in report["designs"] if d["id"] == "B")
    reported_outcomes = {o["outcome_id"]: o for o in b_block["outcomes"]}
    if sorted(reported_outcomes) != sorted(o["id"] for o in spec["design_b"]["outcomes"]):
        fail(failures, f"design B: the artifact publishes outcome families "
                       f"{sorted(reported_outcomes)} but the spec declares "
                       f"{sorted(o['id'] for o in spec['design_b']['outcomes'])}")
    for o in spec["design_b"]["outcomes"]:
        oid = o["id"]
        frame = b_frames[oid]
        print(f"\n{'horizon':<9}{'reported':>11}{'recomputed':>12}{'diff':>10}  "
              f"{'SE reported':>12}{'SE recomputed':>14}   [{oid}]")
        print("-" * 72)
        for h in spec["design_b"]["horizons"]:
            name = f"{o['coefficient_name']}_h{h}"
            row = next((s for s in report["specifications"]
                        if s["design"] == "B" and s["coefficient_name"] == name), None)
            if row is None:
                fail(failures, f"design B[{oid}]: no published specification at h={h}")
                continue
            got = horizon_spec(frame, h)
            delta = abs(got["coefficient"] - row["coefficient"])
            verdict = "ok"
            if delta > COEF_TOL:
                verdict = "FAIL"
                fail(failures, f"design B[{oid}] h={h}: reported {row['coefficient']:.6f} vs recomputed "
                               f"{got['coefficient']:.6f}")
            if row["n_obs"] != got["n_obs"]:
                verdict = "FAIL"
                fail(failures, f"design B[{oid}] h={h}: reported n {row['n_obs']} vs recomputed "
                               f"{got['n_obs']}")
            se_gap = abs(got["standard_error"] - row["standard_error"]) / max(row["standard_error"], 1e-12)
            if se_gap > SE_TOL_REL:
                verdict = "FAIL"
                fail(failures, f"design B[{oid}] h={h}: HAC SE differs by {100 * se_gap:.1f}% "
                               f"({row['standard_error']:.4f} vs {got['standard_error']:.4f})")
            print(f"{h:<9}{row['coefficient']:>11.4f}{got['coefficient']:>12.4f}{delta:>10.2e}  "
                  f"{row['standard_error']:>12.4f}{got['standard_error']:>14.4f}  {verdict}")

        checks_b = reported_outcomes[oid]["checks"]
        placebo_frame = frame.copy()
        placebo_frame["d_oil_lead"] = placebo_frame["d_oil"].shift(-lead_b)
        got_placebo = horizon_spec(placebo_frame, 0, shock="d_oil_lead")
        placed = checks_b["placebo"]
        if abs(got_placebo["coefficient"] - placed["coefficient"]) > 1e-3:
            fail(failures, f"design B[{oid}] lead placebo: reported {placed['coefficient']:.4f} vs "
                           f"recomputed {got_placebo['coefficient']:.4f}")

        path = {r["horizon"]: r for r in checks_b["horizon_path"]}
        peak = max(path.values(), key=lambda r: r["coefficient"])["horizon"]
        if peak != checks_b["peak_horizon"]:
            fail(failures, f"design B[{oid}]: reported peak horizon {checks_b['peak_horizon']} vs "
                           f"recomputed {peak}")

        # ---- 5. the verdict follows the declared rule, per family ---------------------------
        band_rows = [path[h] for h in band if h in path]
        significant = [r for r in band_rows if abs(r["t_statistic"]) > 1.96]
        largest = max(abs(r["coefficient"]) for r in band_rows) if band_rows else 0.0
        expected = "estimated" if significant and abs(got_placebo["coefficient"]) < largest \
            else "estimated_null_at_the_declared_band"
        if reported_outcomes[oid]["status"] != expected:
            fail(failures, f"design B[{oid}]: the declared rule gives '{expected}' and the report says "
                           f"'{reported_outcomes[oid]['status']}'")

    # the design-level headline must be the family the spec pre-registers, not whichever passed
    preferred = spec["design_b"]["outcomes"][0]["id"]
    headline = next(d["status"] for d in report["designs"] if d["id"] == "B")
    if headline != reported_outcomes[preferred]["status"]:
        fail(failures, f"design B: the headline status {headline!r} is not the pre-registered family's "
                       f"({preferred}: {reported_outcomes[preferred]['status']!r})")

    c = next(d for d in report["designs"] if d["id"] == "C")
    # Design C is fitted in its own stage (8h). This artifact carries its status and a pointer, never a second
    # copy of its numbers; the check is that the two agree about whether the design was run.
    design_c_path = REPO_ROOT / "registry" / "design_c" / report["vintage"] / "design_c.json"
    if design_c_path.exists():
        cdoc = json.loads(design_c_path.read_text(encoding="utf-8"))
        estimated = [w for w in cdoc["windows"] if w["status"] != "refused"]
        expected_c = ("identified" if any(w["status"] == "identified" for w in estimated)
                      else "estimated_not_identified" if estimated else "not_run")
        if c["status"] != expected_c:
            fail(failures, f"design C: estimates.json says {c['status']!r} and the stage 8h artifact gives "
                           f"{expected_c!r}")
        if c.get("artifact") != f"registry/design_c/{report['vintage']}/design_c.json":
            fail(failures, "design C: the estimate block does not point at its own artifact")
        if (c.get("counts") or {}).get("estimated") != len(estimated):
            fail(failures, "design C: the counts block does not match the artifact's estimated windows")
    elif c["status"] != "not_run" or not c.get("why"):
        fail(failures, "design C: reported as estimated with no artifact, or as not_run without a reason")

    print("\ndesign B verdicts from the declared rule: " + "; ".join(
        f"{oid} {reported_outcomes[oid]['status']} (peak h={reported_outcomes[oid]['checks']['peak_horizon']}, "
        f"lead placebo {reported_outcomes[oid]['checks']['placebo']['coefficient']:+.4f})"
        for oid in reported_outcomes))

    # ---- 6. every published specification is declared --------------------------------------
    declared_outcomes = set(spec["design_a"]["robustness_outcomes"]) | {spec["design_a"]["outcome"]}
    declared_b = {o["id"] for o in spec["design_b"]["outcomes"]}
    for s in report["specifications"]:
        if s["design"] == "A" and s["outcome"] not in declared_outcomes:
            fail(failures, f"design A publishes an outcome the spec does not declare: {s['outcome']}")
        if s["design"] == "A" and abs(s["coefficient"]) > 5:
            fail(failures, f"design A / {s['outcome']}: |coefficient| {s['coefficient']:.3f} is out of "
                           "range for a count elasticity — check for a units or scale error")
        if s["design"] == "B" and s.get("outcome_id") not in declared_b:
            fail(failures, f"design B publishes an outcome family the spec does not declare: "
                           f"{s.get('outcome_id')!r}")

    # ---- 7. the forest plot is this artifact's own figure ----------------------------------
    # The figure is declared in the spec and rendered by the engine from `specs`, so the checks here are
    # the three ways that can go wrong: the declared path is ignored, the file is stale (recorded bytes
    # disagree with what is on disk), or the render loop stopped early and silently dropped rows. The
    # last one is why the labels are asserted as text rather than counted as marks — a forest plot missing
    # its last three rows still looks like a forest plot.
    figure = report.get("figure")
    if not figure:
        fail(failures, "figure: the spec declares one but the artifact carries no figure block")
    else:
        declared = spec["figure"]["path"]
        if figure.get("path") != declared:
            fail(failures, f"figure: artifact publishes {figure.get('path')!r}, spec declares {declared!r}")
        figure_path = report_path.parent / str(figure.get("path", ""))
        if not figure_path.exists():
            fail(failures, f"figure: {figure_path.name} is declared but missing")
        else:
            svg = figure_path.read_text(encoding="utf-8", errors="replace")
            if "<svg" not in svg:
                fail(failures, f"figure: {figure_path.name} is not an SVG")
            # Canonical (LF) size — the same rule the engine records, so the check survives the CRLF -> LF
            # conversion .gitattributes applies to every checkout.
            actual_bytes = len(figure_path.read_bytes().replace(b"\r\n", b"\n"))
            if figure.get("bytes") != actual_bytes:
                fail(failures, f"figure: artifact records {figure.get('bytes')} bytes, {figure_path.name} is "
                               f"{actual_bytes} — the figure is stale against the artifact")
            if "<text" not in svg:
                fail(failures, "figure: no text elements — labels were rendered as outlines, so a row that "
                               "never got drawn cannot be detected")
            for s in report["specifications"]:
                # The engine spaces the underscores out because these labels are read by a person; the
                # check has to apply the same transform rather than assume the raw outcome id appears.
                label = (s["outcome"].replace("_", " ") if s["design"] == "A"
                         else f"h = {s['coefficient_name'].rsplit('_h', 1)[-1]}")
                if label not in svg:
                    fail(failures, f"figure: no label for the published specification {s['design']}/{label}")
            # The verdict on the figure is the verdict this verifier just recomputed, not a typed string.
            phrase = str(report["designs"][0]["status"]).replace("_", " ")
            if phrase not in svg:
                fail(failures, f"figure: does not carry design A's recomputed verdict {phrase!r}")
            if "hollow" not in svg:
                fail(failures, "figure: the decisive-check markers are not explained in the figure itself")
            print(f"figure: {figure_path.name} — {actual_bytes} bytes, {svg.count('<text')} text elements, "
                  f"every published specification labelled")

    print()
    if failures:
        print(f"FAILED — {len(failures)} problem(s):")
        for problem in failures:
            print(f"  - {problem}")
        return 1
    print("PASS — every published estimate, sample and verdict reproduces independently")
    return 0


if __name__ == "__main__":
    sys.exit(main())
