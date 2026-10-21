"""Verify the transition event-study artifact (`registry/events/<vintage>/events.json`).

Re-derives every published number from the analytical base **independently of** ``analysis/R/06_events.R``:
the series, the windows, all 32 specifications, the exhaustive placebo distribution, the p-values, the
verdicts, the pre-trend placebo, the family-wise maximum and the party description — the same design written
separately, in a different language, from the same spec. What is checked, and why each one is here:

  * **The series is rebuilt from the base, not read from the artifact** — UCDP national monthly counts with
    the declared blank-month rule, plus Brent. A series that disagrees is a different study, and the
    blank-month count is the one discretionary step in it.
  * **Every transition is bound to the administration table.** The four events are looked up by ``term_id``
    in ``dim_administration_term`` and their dates and tenure strata must match what the base records. A spec
    whose event list drifted from the base would otherwise estimate a transition that never happened.
  * **Every window is re-derived** from the declared rules (``pre_months``, the horizon, truncation at the
    next transition and at the end of the series, the 75 % post-window floor). Each published row must sit on
    the window the rule produces, and every event x horizon cell must be either fitted or declared as a skip
    with a reason — a cell that is merely absent is a silent omission.
  * **All 32 specifications are re-fitted** with ``statsmodels`` GLM/Poisson and HAC(12) covariance. The
    coefficient is compared at 1e-6; the standard error at a stated 5 % allowance with the observed gap
    printed, because ``sandwich::NeweyWest`` and ``statsmodels`` apply different small-sample corrections to
    the HAC weights (the same allowance, and the same reason, as Stages 6 and 7).
  * **The placebo distribution is re-enumerated** — 58 eligible months, no RNG — and every per-event
    p-value, the family-wise maximum and the pre-trend placebo are recomputed from it. The p-value must be the
    add-one same-side tail the spec declares, never a raw share that can print 0.000.
  * **The verdicts are re-derived** from the declared rule and must come from the closed set, with
    ``check_not_available`` used where the pre-trend placebo cannot be run: a missing check is not a pass.
  * **The party split carries no test.** The four estimates are grouped and described; the verifier fails if
    a test statistic appears anywhere on that block.

Usage:
    conda run -p "C:/Users/TOSHIBA/ds-general" python tests/verify_events.py
"""

from __future__ import annotations

import json
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
import statsmodels.api as sm
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
EVENTS_ROOT = REPO_ROOT / "registry" / "events"
SPEC_PATH = REPO_ROOT / "analysis" / "specs" / "events.yml"

# The Poisson coefficient is the same maximum-likelihood estimate in both implementations and is compared at
# 1e-6 — tighter than Stages 6 and 7 because this design has no clustering and no demeaning: nothing between
# the two fits differs except floating-point order. The HAC standard error gets a stated 5 % allowance and its
# gap is printed, so a drift larger than a fraction of a per cent is visible rather than absorbed.
COEF_TOL = 1e-6
SE_TOL_REL = 0.05
QUANTILE_TOL = 1e-6

VERDICTS = {"shift_detected", "not_interpretable_pre_trend", "no_shift_detected", "check_not_available",
            "not_estimated"}

# Fields that would turn the party description into a test, or reintroduce the pooled "tenure effect" this
# stage exists to refuse. Their presence on the artifact is a failure, not a nuance.
FORBIDDEN_KEYS = {"p_value", "pvalue", "t_stat", "t_statistic", "se", "std_error", "test", "pooled",
                  "average_effect", "atten"}


def fail(failures: list[str], message: str) -> None:
    failures.append(message)


def month_floor(value) -> pd.Timestamp:
    stamp = pd.Timestamp(value)
    return pd.Timestamp(year=stamp.year, month=stamp.month, day=1)


def load_series(spec: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    """The declared series: the archive keyed to a complete monthly grid, blanks visible before filling."""
    con = duckdb.connect(str(REPO_ROOT / spec["input"]["database"]), read_only=True)
    try:
        conflict = con.execute(
            f"select period_month, fatalities, incidents from {spec['input']['national_conflict_table']} "
            "order by period_month"
        ).fetch_df()
        oil = con.execute(
            f"select period_month, value as oil from {spec['input']['fact_metric_table']} "
            f"where metric_id = '{spec['input']['oil_metric_id']}'"
        ).fetch_df()
        terms = con.execute(
            f"select term_id, admin_id, president, party, term_start, tenure_stratum "
            f"from {spec['input']['administration_term_table']} order by term_id"
        ).fetch_df()
    finally:
        con.close()

    start = pd.Timestamp(spec["series"]["start_month"] + "-01")
    end = pd.Timestamp(spec["series"]["end_month"] + "-01")
    grid = pd.DataFrame({"period_month": pd.date_range(start, end, freq="MS")})
    for frame in (conflict, oil):
        frame["period_month"] = pd.to_datetime(frame["period_month"])
    series = grid.merge(conflict, on="period_month", how="left").merge(oil, on="period_month", how="left")
    series["oil"] = pd.to_numeric(series["oil"], errors="coerce")
    series["trend"] = ((series["period_month"].dt.year - start.year) * 12
                       + (series["period_month"].dt.month - start.month))
    series["month_of_year"] = series["period_month"].dt.month
    return series, terms


def fit(series: pd.DataFrame, rows: list[int], post_from: int, outcome: str, variant: str,
        hac_lags: int) -> dict:
    """Poisson ML with month-of-year dummies and a (declared) linear trend, HAC(``hac_lags``) covariance."""
    sub = series.iloc[rows].reset_index(drop=True)
    design = pd.get_dummies(sub["month_of_year"], prefix="m", drop_first=True).astype(float)
    design["post"] = (np.arange(len(sub)) >= post_from).astype(float)
    design["trend"] = sub["trend"].to_numpy(dtype=float)
    if variant == "seasonality_trend_oil":
        design["log_oil"] = np.log(sub["oil"].to_numpy(dtype=float))
    elif variant != "seasonality_trend":
        raise ValueError(f"unknown control variant {variant!r}")
    design = sm.add_constant(design, has_constant="add")
    model = sm.GLM(sub[outcome].to_numpy(dtype=float), design,
                   family=sm.families.Poisson()).fit(cov_type="HAC", cov_kwds={"maxlags": hac_lags})
    return {"beta": float(model.params["post"]), "se": float(model.bse["post"]),
            "n_parameters": int(len(model.params))}


def tail_p(dist: np.ndarray, beta: float) -> float:
    """The declared add-one p-value: the tail the estimate points at, one-sided in that direction."""
    exceed = np.sum(dist >= beta) if beta > 0 else np.sum(dist <= beta)
    return float((1 + exceed) / (len(dist) + 1))


def main() -> int:
    failures: list[str] = []
    spec = yaml.safe_load(SPEC_PATH.read_text(encoding="utf-8"))

    vintages = sorted(d for d in EVENTS_ROOT.glob("*") if (d / "events.json").exists())
    if not vintages:
        print("FAILED — no events artifact found under registry/events/")
        return 1
    vintage_dir = vintages[-1]
    document = json.loads((vintage_dir / "events.json").read_text(encoding="utf-8"))
    rows = document["specifications"]
    print(f"artifact         : registry/events/{vintage_dir.name}/events.json ({len(rows)} specifications)")

    if document.get("vintage") != spec["labelled"]:
        fail(failures, f"artifact vintage {document.get('vintage')!r} != spec `labelled` {spec['labelled']!r}")

    pre_months = int(spec["windows"]["pre_months"])
    horizons = [int(h) for h in spec["windows"]["focus_horizons"]]
    min_post_fraction = float(spec["windows"]["min_post_fraction"])
    floor_by_horizon = {h: int(np.ceil(min_post_fraction * h)) for h in horizons}
    outcomes = [str(o) for o in spec["series"]["outcomes"]]
    variants = list(spec["statistic"]["controls_variants"].keys())
    baseline = variants[0]
    hac_lags = int(spec["statistic"]["hac_lags"])
    buffer = int(spec["inference"]["buffer_months"])

    # ------------------------------------------------------------------------------------------
    # The series
    # ------------------------------------------------------------------------------------------
    series, terms = load_series(spec)
    published_series = document["series"]
    blank = series["fatalities"].isna()
    blank_incidents = series["incidents"].isna()
    if int(published_series["n_months"]) != len(series):
        fail(failures, f"series: artifact says {published_series['n_months']} months, the base gives "
                       f"{len(series)}")
    if int(published_series["months_filled_with_zero"]) != int(blank.sum()):
        fail(failures, f"series: artifact says {published_series['months_filled_with_zero']} blank months, the "
                       f"base has {int(blank.sum())}")
    if not blank.equals(blank_incidents):
        fail(failures, "series: fatalities and incidents do not have the same blank months")
    filled_by_year = {int(y): int(n) for y, n in blank.groupby(series["period_month"].dt.year).sum().items()
                      if n > 0}
    published_filled = {int(entry["year"]): int(entry["months"]) for entry in published_series["filled_by_year"]}
    if filled_by_year != published_filled:
        fail(failures, f"series: published filled months by year {published_filled} != the base's "
                       f"{filled_by_year}")
    series["fatalities"] = series["fatalities"].fillna(0).astype(int)
    series["incidents"] = series["incidents"].fillna(0).astype(int)
    if int(series["oil"].isna().sum()):
        fail(failures, f"series: {int(series['oil'].isna().sum())} month(s) of the window carry no Brent quote")
    print(f"series           : {len(series)} months {series['period_month'].iloc[0]:%Y-%m} -> "
          f"{series['period_month'].iloc[-1]:%Y-%m}, {int(blank.sum())} blank month(s) filled, "
          f"{len(filled_by_year)} year(s) affected")

    # ------------------------------------------------------------------------------------------
    # The transitions, bound to the administration table
    # ------------------------------------------------------------------------------------------
    events = spec["events"]
    term_index = terms.set_index("term_id")
    series_months = list(series["period_month"])
    event_rows: dict[str, int] = {}
    for event in events:
        term_id = int(event["term_id"])
        if term_id not in term_index.index:
            fail(failures, f"event {event['id']}: term_id {term_id} is not in the administration table")
            continue
        term = term_index.loc[term_id]
        if month_floor(term["term_start"]) != month_floor(event["date"]):
            fail(failures, f"event {event['id']}: spec date {event['date']} != term_start {term['term_start']} "
                           f"for term {term_id}")
        if str(term["tenure_stratum"]) != str(event["tenure_stratum"]):
            fail(failures, f"event {event['id']}: spec tenure_stratum {event['tenure_stratum']!r} != base "
                           f"{term['tenure_stratum']!r}")
        month = month_floor(event["date"])
        if month not in series_months:
            fail(failures, f"event {event['id']}: transition month {month:%Y-%m} is outside the series")
            continue
        event_rows[str(event["id"])] = series_months.index(month)
    print(f"transitions      : {len(event_rows)} of {len(events)} bound to dim_administration_term at the "
          f"declared dates and strata")
    if len(event_rows) != len(events):
        return finish(failures)

    def next_transition_row(index: int) -> int:
        later = [month_floor(e["date"]) for e in events
                 if month_floor(e["date"]) > month_floor(events[index]["date"])]
        return series_months.index(min(later)) - 1 if later else len(series) - 1

    def window_of(event_id: str, horizon: int) -> tuple[list[int], list[int]]:
        index = [k for k, e in enumerate(events) if str(e["id"]) == event_id][0]
        t0 = event_rows[event_id]
        post_to = min(t0 + horizon - 1, next_transition_row(index), len(series) - 1)
        return list(range(t0 - pre_months, t0)), list(range(t0, post_to + 1))

    # ------------------------------------------------------------------------------------------
    # Every declared cell is fitted, or declared as a skip with a reason
    # ------------------------------------------------------------------------------------------
    cells = [(str(e["id"]), h) for e in events for h in horizons]
    declared_skips = {(str(s["event"]), int(s["horizon"])): s for s in document["windows"].get("skips", [])}
    fitted_cells = {(str(r["event"]), int(r["horizon"])) for r in rows}
    for cell in cells:
        if cell in fitted_cells:
            continue
        if cell not in declared_skips:
            fail(failures, f"cell {cell[0]} / h={cell[1]} is neither fitted nor declared as a skip")
        elif not str(declared_skips[cell].get("why", "")).strip():
            fail(failures, f"declared skip {cell} carries no reason")
    for cell in declared_skips:
        if cell not in cells:
            fail(failures, f"declared skip {cell} is not a declared event x horizon cell")
        _, post_rows = window_of(cell[0], cell[1])
        if len(post_rows) >= floor_by_horizon[cell[1]]:
            fail(failures, f"{cell[0]} / h={cell[1]} is declared as a skip but its window has "
                           f"{len(post_rows)} month(s), at or above the {floor_by_horizon[cell[1]]}-month floor")
    if len(fitted_cells) != len(cells) - len(declared_skips):
        fail(failures, "the number of fitted cells does not equal the declared cells minus the declared skips")

    # ------------------------------------------------------------------------------------------
    # Re-fit every published specification
    # ------------------------------------------------------------------------------------------
    worst_se_gap, worst_se_cell = 0.0, ""
    expected_rows = len(events) * len(horizons) * len(outcomes) * len(variants)
    if len(rows) != expected_rows - len(declared_skips) * len(outcomes) * len(variants):
        fail(failures, f"{len(rows)} specification(s) published; the declared grid allows "
                       f"{expected_rows - len(declared_skips) * len(outcomes) * len(variants)}")
    for row in rows:
        event_id, horizon, outcome, variant = (str(row["event"]), int(row["horizon"]), row["outcome"],
                                               row["variant"])
        if event_id not in event_rows:
            fail(failures, f"row references undeclared event {event_id!r}")
            continue
        if variant not in variants or outcome not in outcomes or horizon not in horizons:
            fail(failures, f"{event_id}: row names an undeclared outcome/horizon/variant "
                           f"({outcome}/{horizon}/{variant})")
            continue
        pre_rows, post_rows = window_of(event_id, horizon)
        min_post = floor_by_horizon[horizon]
        if len(post_rows) < min_post:
            fail(failures, f"{event_id} / h={horizon}: published below the {min_post}-month floor with "
                           f"{len(post_rows)} month(s)")
        if pd.Timestamp(row["window_start"]) != series_months[pre_rows[0]] or \
                pd.Timestamp(row["window_end"]) != series_months[post_rows[-1]]:
            fail(failures, f"{event_id} / {outcome} / h={horizon}: published window "
                           f"{row['window_start']}..{row['window_end']} != the declared rule's "
                           f"{series_months[pre_rows[0]]:%Y-%m}..{series_months[post_rows[-1]]:%Y-%m}")
        if int(row["post_months"]) != len(post_rows) or int(row["pre_months"]) != len(pre_rows):
            fail(failures, f"{event_id} / {outcome} / h={horizon}: published window lengths disagree with the "
                           f"declared rule")
        if int(row["n_pre"]) != len(pre_rows) or int(row["n_post"]) != len(post_rows):
            fail(failures, f"{event_id} / {outcome} / h={horizon}: published n_pre/n_post disagree with the "
                           f"window")
        if bool(row["truncated_by_next_transition"]) != (post_rows[-1] < event_rows[event_id] + horizon - 1):
            fail(failures, f"{event_id} / {outcome} / h={horizon}: truncation flag disagrees with the rule")

        model = fit(series, pre_rows + post_rows, len(pre_rows), outcome, variant, hac_lags)
        where = f"{event_id} / {outcome} / h={horizon} / {variant}"
        if abs(model["beta"] - float(row["beta"])) > COEF_TOL:
            fail(failures, f"{where}: refit beta {model['beta']:.10f} != published {float(row['beta']):.10f}")
        gap = abs(model["se"] - float(row["se"])) / max(abs(float(row["se"])), 1e-12)
        if gap > worst_se_gap:
            worst_se_gap, worst_se_cell = gap, where
        if gap > SE_TOL_REL:
            fail(failures, f"{where}: refit SE {model['se']:.10f} differs from published {float(row['se']):.10f} "
                           f"by {gap:.1%} > {SE_TOL_REL:.0%}")
        expected_parameters = 11 + 3 + (1 if variant == "seasonality_trend_oil" else 0)
        if int(row["n_parameters"]) != model["n_parameters"] or model["n_parameters"] != expected_parameters:
            fail(failures, f"{where}: {row['n_parameters']} parameter(s) published, the fit has "
                           f"{model['n_parameters']} (expected {expected_parameters})")
        if abs(float(row["proportional"]) - (np.exp(model["beta"]) - 1)) > 1e-8:
            fail(failures, f"{where}: the published proportional shift is not exp(beta) - 1")
        # The interval and the MDE are arithmetic on the *published* coefficient and standard error, so they
        # are checked against those rather than against the refit — the refit SE carries the few-per-cent
        # package difference and would make a formula check fail for the wrong reason.
        published_beta, published_se = float(row["beta"]), float(row["se"])
        if abs(float(row["mde_proportional"]) - (np.exp((1.959964 + 0.8416212) * published_se) - 1)) > 1e-6:
            fail(failures, f"{where}: the published MDE is not the declared z on the published SE")
        for bound, z in (("ci_low", -1.959964), ("ci_high", 1.959964)):
            expected = np.exp(published_beta + z * published_se) - 1
            if abs(float(row[bound]) - expected) > 1e-6:
                fail(failures, f"{where}: {bound} is not exp(beta ± 1.96 SE) - 1 on the published SE")
    print(f"specifications   : {len(rows)} rows re-fitted from the base; worst SE gap {worst_se_gap:.3%} "
          f"({worst_se_cell}), allowance {SE_TOL_REL:.0%}")

    # ------------------------------------------------------------------------------------------
    # The placebo distribution, re-enumerated from the declared eligibility rule
    # ------------------------------------------------------------------------------------------
    excluded = np.zeros(len(series), dtype=bool)
    for event_id in event_rows:
        t0 = event_rows[event_id]
        excluded[max(0, t0 - buffer):min(len(series), t0 + buffer + 1)] = True
    strictest = floor_by_horizon[max(horizons)]
    index_range = np.arange(len(series))
    eligible = np.where(~excluded & (index_range >= pre_months) & (index_range <= len(series) - 1 - strictest))[0]
    published_placebo = document["placebo"]
    if int(published_placebo["eligible_months"]) != len(eligible):
        fail(failures, f"placebo: artifact says {published_placebo['eligible_months']} eligible months, the "
                       f"declared rule gives {len(eligible)}")
    if len(eligible):
        if pd.Timestamp(published_placebo["first_eligible"]) != series_months[eligible[0]] or \
                pd.Timestamp(published_placebo["last_eligible"]) != series_months[eligible[-1]]:
            fail(failures, f"placebo: published eligible range {published_placebo['first_eligible']}.."
                           f"{published_placebo['last_eligible']} != the rule's "
                           f"{series_months[eligible[0]]:%Y-%m}..{series_months[eligible[-1]]:%Y-%m}")
    if published_placebo.get("deterministic") is not True:
        fail(failures, "placebo: the artifact does not declare the enumeration as deterministic")

    def placebo_betas(outcome: str, horizon: int) -> np.ndarray:
        return np.array([fit(series, list(range(t0 - pre_months, t0)) + list(range(t0, t0 + horizon)),
                             pre_months, outcome, baseline, hac_lags)["beta"] for t0 in eligible])

    distributions: dict[tuple[str, int], np.ndarray] = {}
    published_by_horizon = {(p["outcome"], int(p["horizon"])): p for p in published_placebo["distributions"]}
    if set(published_by_horizon) != {(o, h) for o in outcomes for h in horizons}:
        fail(failures, "placebo: the published distribution set is not outcomes x horizons")
    for outcome in outcomes:
        for horizon in horizons:
            betas = placebo_betas(outcome, horizon)
            distributions[(outcome, horizon)] = betas
            published = published_by_horizon.get((outcome, horizon))
            if published is None:
                continue
            if int(published["n"]) != len(betas):
                fail(failures, f"placebo {outcome} / h={horizon}: {published['n']} months published, "
                               f"{len(betas)} re-enumerated")
            if abs(float(published["mean_beta"]) - float(betas.mean())) > 1e-6:
                fail(failures, f"placebo {outcome} / h={horizon}: published mean "
                               f"{published['mean_beta']} != recomputed {betas.mean():.10f}")
            if abs(float(published["sd_beta"]) - float(betas.std(ddof=1))) > 1e-6:
                fail(failures, f"placebo {outcome} / h={horizon}: published SD {published['sd_beta']} != "
                               f"recomputed {betas.std(ddof=1):.10f}")
            for key, level in (("quantiles", [0.05, 0.5, 0.9, 0.95, 0.99]), ("abs_quantiles", None)):
                if key == "abs_quantiles":
                    continue
                published_quantiles = [float(v) for v in published.get(key, [])]
                expected = list(np.quantile(betas, level))
                if len(published_quantiles) != len(expected):
                    fail(failures, f"placebo {outcome} / h={horizon}: {len(published_quantiles)} quantile(s) "
                                   f"published, {len(expected)} declared")
                    continue
                for got, want in zip(published_quantiles, expected):
                    if abs(got - want) > QUANTILE_TOL:
                        fail(failures, f"placebo {outcome} / h={horizon}: published quantile {got} != "
                                       f"recomputed {want:.10f}")
    print(f"placebo          : {len(eligible)} month(s) re-enumerated per outcome/horizon, distributions and "
          f"quantiles reproduced")

    # ------------------------------------------------------------------------------------------
    # The p-values, the verdicts and the family-wise maximum
    # ------------------------------------------------------------------------------------------
    verdict_rows = {(str(v["event"]), v["outcome"]): v for v in document["verdicts"]}
    if set(verdict_rows) != {(str(e["id"]), o) for e in events for o in outcomes}:
        fail(failures, "verdicts: the published verdict set is not events x outcomes")
    pretrend = {(str(p["event"]), p["outcome"]): p for p in document["pre_trend_placebo"]}
    unavailable = {str(u["event"]) for u in document["checks"].get("pre_trend_unavailable", [])}
    for row in rows:
        event_id, horizon, outcome, variant = (str(row["event"]), int(row["horizon"]), row["outcome"],
                                               row["variant"])
        if variant != baseline:
            if row.get("placebo_p") is not None:
                fail(failures, f"{event_id} / {outcome} / h={horizon} / {variant}: a p-value is published for a "
                               f"non-baseline control variant, which has no placebo distribution")
            continue
        dist = distributions[(outcome, horizon)]
        expected_p = tail_p(dist, float(row["beta"]))
        if abs(float(row["placebo_p"]) - expected_p) > 1e-9:
            fail(failures, f"{event_id} / {outcome} / h={horizon}: published p {row['placebo_p']} != "
                           f"recomputed {expected_p:.10f}")
        if int(row["placebo_n"]) != len(dist):
            fail(failures, f"{event_id} / {outcome} / h={horizon}: published placebo n {row['placebo_n']} != "
                           f"{len(dist)}")
        if float(row["placebo_p"]) <= 0.0:
            fail(failures, f"{event_id} / {outcome} / h={horizon}: p-value of exactly zero — the declared "
                           f"add-one form has a floor of 1/(n+1)")
        expected_tail = "increase" if float(row["beta"]) > 0 else "decrease"
        if str(row["placebo_tail"]) != expected_tail:
            fail(failures, f"{event_id} / {outcome} / h={horizon}: the p-value is taken in the "
                           f"{row['placebo_tail']} tail for a {expected_tail}ing estimate")

    for (event_id, outcome), verdict in verdict_rows.items():
        if str(verdict["status"]) not in VERDICTS:
            fail(failures, f"verdict {event_id} / {outcome}: {verdict['status']!r} is outside the closed set")
            continue
        focal = [r for r in rows if str(r["event"]) == event_id and r["outcome"] == outcome
                 and int(r["horizon"]) == (12 if 12 in horizons else horizons[0]) and r["variant"] == baseline]
        if not focal:
            if str(verdict["status"]) != "not_estimated":
                fail(failures, f"verdict {event_id} / {outcome}: no focal specification, so the verdict must be "
                               f"`not_estimated`, not {verdict['status']!r}")
            continue
        focal = focal[0]
        pre = pretrend.get((event_id, outcome))
        pre_magnitude = abs(float(pre["proportional"])) if pre else np.nan
        if event_id in unavailable and not np.isnan(pre_magnitude):
            fail(failures, f"{event_id}: declared as lacking the pre-trend check but a placebo row is published")
        if np.isnan(pre_magnitude):
            expected_status = "check_not_available"
        elif float(focal["placebo_p"]) <= 0.05 and pre_magnitude < abs(float(focal["proportional"])):
            expected_status = "shift_detected"
        elif pre_magnitude >= abs(float(focal["proportional"])):
            expected_status = "not_interpretable_pre_trend"
        else:
            expected_status = "no_shift_detected"
        if str(verdict["status"]) != expected_status:
            fail(failures, f"verdict {event_id} / {outcome}: published {verdict['status']!r}, the declared rule "
                           f"gives {expected_status!r}")
        if abs(float(focal["placebo_p"] or -1) - float(verdict["placebo_p"] or -2)) > 1e-9 and \
                not np.isnan(float(verdict["placebo_p"])):
            fail(failures, f"verdict {event_id} / {outcome}: the verdict's p-value disagrees with the row's")
        if np.isnan(pre_magnitude) and not str(verdict.get("why", "")).strip():
            fail(failures, f"verdict {event_id} / {outcome}: `check_not_available` without a stated reason")

    # The pre-trend rows themselves: the same statistic with the pseudo-post window 24 months before the event.
    for (event_id, outcome), published in pretrend.items():
        index = [k for k, e in enumerate(events) if str(e["id"]) == event_id][0]
        t0 = event_rows[event_id]
        pseudo_post = list(range(t0 - 24, t0))
        pre_rows = list(range(pseudo_post[0] - pre_months, pseudo_post[0]))
        if not pre_rows or pre_rows[0] < 0:
            fail(failures, f"pre-trend {event_id} / {outcome}: published although the check cannot be run")
            continue
        model = fit(series, pre_rows + pseudo_post, len(pre_rows), outcome, baseline, hac_lags)
        if abs(float(published["proportional"]) - (np.exp(model["beta"]) - 1)) > 1e-6:
            fail(failures, f"pre-trend {event_id} / {outcome}: published {published['proportional']} != "
                           f"recomputed {np.exp(model['beta']) - 1:.10f}")
        if len(pre_rows) + len(pseudo_post) > len(series):
            fail(failures, f"pre-trend {event_id} / {outcome}: window runs past the series")
    for event in events:
        event_id = str(event["id"])
        t0 = event_rows[event_id]
        runnable = t0 - 24 - pre_months >= 0
        if runnable and event_id in unavailable:
            fail(failures, f"{event_id}: declared as lacking the pre-trend check, but {t0} month(s) of history "
                           f"are available and the check needs {pre_months + 24}")
        if not runnable and event_id not in unavailable:
            fail(failures, f"{event_id}: the pre-trend check cannot be run ({t0} month(s) of history < "
                           f"{pre_months + 24}) but the artifact does not say so")

    for family in document["placebo"]["family_wise"]:
        outcome, horizon = family["outcome"], int(family["horizon"])
        candidates = [r for r in rows if r["outcome"] == outcome and int(r["horizon"]) == horizon
                      and r["variant"] == baseline]
        if not candidates:
            fail(failures, f"family-wise {outcome} / h={horizon}: no baseline specification to take a maximum over")
            continue
        largest = max(candidates, key=lambda r: abs(float(r["beta"])))
        expected_p = tail_p(distributions[(outcome, horizon)], float(largest["beta"]))
        if str(family["largest_event"]) != str(largest["event"]):
            fail(failures, f"family-wise {outcome} / h={horizon}: largest is {largest['event']}, artifact says "
                           f"{family['largest_event']}")
        if abs(float(family["largest_beta"]) - float(largest["beta"])) > COEF_TOL or \
                abs(float(family["largest_proportional"]) - float(largest["proportional"])) > 1e-8:
            fail(failures, f"family-wise {outcome} / h={horizon}: the published maximum is not the largest "
                           f"refitted estimate")
        if abs(float(family["p"]) - expected_p) > 1e-9:
            fail(failures, f"family-wise {outcome} / h={horizon}: published p {family['p']} != recomputed "
                           f"{expected_p:.10f}")
        if str(family.get("direction")) != ("increase" if float(largest["beta"]) > 0 else "decrease"):
            fail(failures, f"family-wise {outcome} / h={horizon}: the tail direction disagrees with the sign")
    print(f"inference        : {len(verdict_rows)} verdict(s) re-derived; {len(document['pre_trend_placebo'])} "
          f"pre-trend placebo(row)s reproduced, {len(unavailable)} event(s) declared uncheckable")

    # ------------------------------------------------------------------------------------------
    # The party split is a description, and the artifact says what it does not claim
    # ------------------------------------------------------------------------------------------
    split = document["party_split"]
    if split.get("no_test_computed") is not True:
        fail(failures, "party split: `no_test_computed` is not true")

    def walk(node, path: str) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if str(key).lower() in FORBIDDEN_KEYS:
                    fail(failures, f"party split: a test-like field `{path}{key}` is populated")
                walk(value, f"{path}{key}.")
        elif isinstance(node, list):
            for item in node:
                walk(item, path)

    walk(split, "party_split.")
    focal_horizon = 12 if 12 in horizons else horizons[0]
    expected_events = []
    for event in events:
        event_id = str(event["id"])
        row = [r for r in rows if str(r["event"]) == event_id and r["outcome"] == "fatalities"
               and int(r["horizon"]) == focal_horizon and r["variant"] == baseline]
        if not row:
            continue
        expected_events.append({"event": event_id, "tenure_stratum": str(event["tenure_stratum"]),
                                "party": str(event["tenure_stratum"]).split("_")[0],
                                "shift": float(row[0]["proportional"]),
                                "p": float(row[0]["placebo_p"])})
    published_events = {str(e["event"]): e for e in split["events"]}
    if set(published_events) != {e["event"] for e in expected_events}:
        fail(failures, f"party split: published events {sorted(published_events)} != the fitted set "
                       f"{sorted(e['event'] for e in expected_events)}")
    for expected in expected_events:
        published = published_events.get(expected["event"])
        if published is None:
            continue
        if str(published["party"]) != expected["party"] or \
                str(published["tenure_stratum"]) != expected["tenure_stratum"]:
            fail(failures, f"party split {expected['event']}: published party/stratum disagree with the spec")
        if abs(float(published["shift_fatalities_h12"]) - expected["shift"]) > 1e-8:
            fail(failures, f"party split {expected['event']}: published shift "
                           f"{published['shift_fatalities_h12']} != the row's {expected['shift']:.10f}")
        if abs(float(published["placebo_p"]) - expected["p"]) > 1e-9:
            fail(failures, f"party split {expected['event']}: published p-value is not the row's")
    groups = {}
    for expected in expected_events:
        groups.setdefault(expected["party"], []).append(expected["shift"])
    published_groups = {str(g["party"]): g for g in split["by_party"]}
    if set(published_groups) != set(groups):
        fail(failures, f"party split: published parties {sorted(published_groups)} != {sorted(groups)}")
    for party, shifts in groups.items():
        published = published_groups.get(party)
        if published is None:
            continue
        if int(published["n_events"]) != len(shifts):
            fail(failures, f"party split {party}: published n_events {published['n_events']} != {len(shifts)}")
        if abs(float(published["median_shift_h12"]) - float(np.median(shifts))) > 1e-8:
            fail(failures, f"party split {party}: published median {published['median_shift_h12']} != "
                           f"recomputed {np.median(shifts):.10f}")
        if sorted(float(v) for v in published["shifts"]) != sorted(float(v) for v in shifts):
            fail(failures, f"party split {party}: the published shifts are not the fitted ones")
    if not groups:
        fail(failures, "party split: no events grouped — the description is empty")
    else:
        smallest = min(len(v) for v in groups.values())
        if smallest < 2:
            print(f"party split      : {len(published_groups)} group(s), smallest n = {smallest} — description "
                  f"only, which is what the artifact claims")
    print(f"party split      : {len(expected_events)} event(s) grouped into {len(groups)} group(s), medians and "
          f"shifts reproduced, no test field present")

    # ------------------------------------------------------------------------------------------
    # The figure, and the claims the artifact refuses to make
    # --------------------------------------------------------------------------------------
    figure = document.get("figure") or {}
    figure_path = vintage_dir / str(figure.get("path", ""))
    if not figure_path.exists():
        fail(failures, f"figure: {figure_path.name} is published but missing")
    else:
        svg = figure_path.read_text(encoding="utf-8", errors="replace")
        # The SVG device renders points and text as glyph paths rather than as <circle>/<text>, so the
        # Stage 7 contract's element count cannot be used here. What can be counted is the one mark the figure
        # draws per transition: a dashed vertical rule at the transition month. A transition that is not drawn
        # is not in the figure, which is the thing this contract exists to catch.
        rules = svg.count("stroke-dasharray")
        if "<svg" not in svg:
            fail(failures, f"figure: {figure_path.name} is not an SVG")
        elif rules < len(events):
            fail(failures, f"figure: {rules} dashed rule(s) for {len(events)} transition(s) — an event that is "
                           f"not drawn is not in the figure")
        elif "width=" not in svg or "height=" not in svg:
            fail(failures, f"figure: {figure_path.name} declares no width/height")
        elif abs(int(figure.get("bytes", -1)) - figure_path.stat().st_size) > 0:
            fail(failures, f"figure: the published size {figure.get('bytes')} != {figure_path.stat().st_size} "
                           f"bytes on disk")

    not_claimed = " ".join(str(c) for c in document.get("not_claimed", [])).lower()
    for phrase, why in (("causal", "the design identifies no counterfactual"),
                        ("tenure effect", "no pooled tenure effect is estimated"),
                        ("reporting bias", "the archive is a reported-events source")):
        if phrase not in not_claimed:
            fail(failures, f"claims: the artifact does not refuse the `{phrase}` claim ({why})")
    if len(document.get("not_claimed", [])) < 4:
        fail(failures, "claims: fewer than four refusals published; this stage's value is partly in what it "
                       "does not claim")
    if not str(document.get("verdict_rule", "")).strip() or not str(document.get("verifier", "")).strip():
        fail(failures, "claims: the artifact does not carry its verdict rule and verifier path")

    # ---- the narrative cannot drift from the verdicts it quotes ------------------------------
    # `docs/events.md` said "four of the eight fail on the pre-trend" while the artifact had three
    # failing and two that could not be checked, and every verifier passed, because none of them read
    # the prose. The counts below are recomputed from the verdicts this run just re-derived and then
    # required to appear in the documents that quote them — a literal typed here would only catch a
    # document that changed, not a verdict that moved underneath one that did not.
    status_counts: dict[str, int] = {}
    for verdict in verdict_rows.values():
        status_counts[str(verdict["status"])] = status_counts.get(str(verdict["status"]), 0) + 1
    shifted = status_counts.get("shift_detected", 0)
    pre_trend = status_counts.get("not_interpretable_pre_trend", 0)
    unavailable = status_counts.get("check_not_available", 0)
    no_shift = status_counts.get("no_shift_detected", 0)
    n_cells = len(verdict_rows)
    words = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven", 8: "eight",
             9: "nine", 10: "ten"}
    w = lambda n: words.get(n, str(n))  # noqa: E731 — a two-word helper, not a policy
    claims = {
        "docs/events.md": [
            (f"**{w(shifted)} of the {w(n_cells)} cells survive both checks**",
             "the number of cells surviving both checks"),
            (f"{w(pre_trend)} of the {w(n_cells)} fail on the pre-trend",
             "the number of cells failing the pre-trend check"),
        ],
        "docs/limitations.md": [
            (f"**{w(shifted).capitalize()} of {w(n_cells)} event-outcome cells**",
             "the number of cells surviving both checks"),
            (f"{w(pre_trend)} fail the pre-trend",
             "the number of cells failing the pre-trend check"),
        ],
    }
    for rel, required in claims.items():
        path = REPO_ROOT / rel
        if not path.exists():
            fail(failures, f"claims: {rel} is missing, so its claims cannot be checked")
            continue
        # Whitespace-normalised: the documents wrap prose, and a claim must not fail because a line
        # break moved. Bold markers are kept, so "**two of the eight cells**" still means that phrase.
        text = " ".join(path.read_text(encoding="utf-8").split())
        for needle, what in required:
            if needle not in text:
                fail(failures, f"claims: {rel} does not carry {needle!r} — {what} has moved under the "
                               f"narrative")
    print(f"narrative        : {shifted} shift / {pre_trend} pre-trend / {unavailable} unavailable / "
          f"{no_shift} no-shift of {n_cells} cells, quoted counts checked in docs/events.md and "
          f"docs/limitations.md")

    return finish(failures)


def finish(failures: list[str]) -> int:
    print()
    if failures:
        print(f"FAILED — {len(failures)} problem(s):")
        for problem in failures[:40]:
            print(f"  - {problem}")
        if len(failures) > 40:
            print(f"  … and {len(failures) - 40} more")
        return 1
    print("PASS — every published number re-derived from the base, on the declared windows, with the declared "
          "inference")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
