"""Verify the Stage 4 analytical base independently of the dbt models.

Recomputes the base **from the raw payloads and the declared specs**, in plain Python, and compares the
result with what dbt built. Nothing here imports a dbt model, a dbt macro or `ingestion/quality/gates.py`
— a verifier that reused the thing under test would only prove the thing is self-consistent. This is the
same arrangement Stage 3 uses (`tests/verify_quality.py`): the spec declares, the build implements, the
verifier is the tie-breaker.

What it checks:

  * **The spine is the declared spine.** Every (metric, month) row is recomputed from the payloads under
    `analysis/specs/harmonisation.yml` — annual values anchored at July, linear interpolation only between
    observations exactly one step apart, nothing extrapolated, nothing interpolated across a gap — and
    compared row for row with `fact_metric`, including the `observation_type` of every month. This is the
    check that makes "no extrapolation" a fact rather than a comment in a model.
  * **The index is anchored where the spec says**, with the fallback applied and recorded per metric, and
    `value_indexed` is recomputed from the anchor value rather than trusted.
  * **The Brent resample follows the frozen rule** read out of `analysis/specs/quality.yml` — the rule
    string is compared, not just the numbers, so an edited model that happened to agree on this vintage
    would still be caught on the next one.
  * **The administration spine is base spec section 7**, row for row, including the decided Yar'Adua ->
    Jonathan boundary, and the term strata are re-derived and must cover the window exactly once.
  * **The metric catalogue agrees with `outcomes.yml`** on every field an outcome declares — label, short
    label, unit, direction, domain, catalogue frequency and coverage status. Two files state the same
    thing; this fails if they ever diverge, which is the only reason the duplication is acceptable.
  * **Gaps are declared, not missing.** The state panel's dose columns are labelled per row; the columns
    that need an unmade decision (the per-capita denominator, the IGR share) are empty and must stay so;
    the unlanded outcomes carry `blocked` or `declared_gap`; and the spec's `declared_gaps` list is
    non-empty. The FAAC dose itself is verified in its own right by `tests/verify_faac.py`, which
    recomputes the publisher choice and the share from the staging artifact.

Usage:
    conda run -p "C:/Users/TOSHIBA/ds-general" python tests/verify_harmonisation.py
"""

from __future__ import annotations

import csv
import json
import sys
from itertools import pairwise
from pathlib import Path

import duckdb
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
RAW_ROOT = REPO_ROOT / "data" / "raw"
SPEC_DIR = REPO_ROOT / "analysis" / "specs"
DB_PATH = REPO_ROOT / "data" / "analytics.duckdb"
SCHEMA = "main_analytics"

# Base spec section 7 [LOCKED], written out here rather than imported from the seed: the point of the
# check is that the built table matches the *spec*, and rereading the seed would only prove the seed
# agrees with itself.
BASE_SPEC_ADMINISTRATIONS = [
    (1, "Olusegun Obasanjo", "PDP", "1999-05-29", "2007-05-29", 2),
    (2, "Umaru Musa Yar'Adua", "PDP", "2007-05-29", "2010-05-05", 1),
    (3, "Goodluck Jonathan", "PDP", "2010-05-06", "2015-05-29", 1),
    (4, "Muhammadu Buhari", "APC", "2015-05-29", "2023-05-29", 2),
    (5, "Bola Ahmed Tinubu", "APC", "2023-05-29", None, 1),
]
DECIDED_BOUNDARY = ("2010-05-05", "2010-05-06")  # Yar'Adua's last day -> Jonathan sworn in


# ---------------------------------------------------------------------------------------------
# month arithmetic — the spine is indexed by integer months, the way Stage 3 gates index it
# ---------------------------------------------------------------------------------------------
def mi(year: int, month: int) -> int:
    return year * 12 + (month - 1)


def month_label(index: int) -> str:
    return f"{index // 12:04d}-{index % 12 + 1:02d}"


def parse_index(value) -> int:
    if hasattr(value, "year"):
        return mi(value.year, value.month)
    text = str(value)
    return mi(int(text[:4]), int(text[5:7]))


# ---------------------------------------------------------------------------------------------
# the raw layer, read independently
# ---------------------------------------------------------------------------------------------
def load_raw(spec: dict) -> dict:
    """{'sources': {source: vintage}, 'annual': {metric: [(index, value)]}, 'daily': [(date, value)]}"""
    sources: dict[str, str] = {}
    per_source: dict[str, list[dict]] = {}

    for manifest_path in sorted(RAW_ROOT.glob("*/*/manifest.json")):
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        source = manifest["source"]
        vintage = str(manifest["vintage_date"])
        if source not in sources or vintage > sources[source]:
            sources[source] = vintage
            per_source[source] = manifest["retrievals"]

    annual: dict[str, list[tuple[int, float]]] = {}
    daily: list[tuple[str, float]] = []
    donors: dict[tuple[str, str, int], float] = {}

    def pages(retrieval) -> list:
        return [
            json.loads((REPO_ROOT / page).read_text(encoding="utf-8"))
            for page in retrieval["page_files"]
        ]

    for retrieval in per_source.get("worldbank", []):
        metric = retrieval["metric_id"]
        points = annual.setdefault(metric, [])
        for blob in pages(retrieval):
            for row in blob[1]:
                if (row.get("countryiso3code") or "").upper() != "NGA":
                    continue
                value = row.get("value")
                label = str(row.get("date", ""))
                if value is None or not label[:4].isdigit():
                    continue
                points.append((mi(int(label[:4]), 7), float(value)))

    for retrieval in per_source.get("fred", []):
        for blob in pages(retrieval):
            for obs in blob["observations"]:
                raw_value = obs.get("value")
                if raw_value in (None, "", "."):
                    continue
                daily.append((obs["date"], float(raw_value)))

    for retrieval in per_source.get("worldbank_donors", []):
        metric = retrieval["metric_id"]
        for blob in pages(retrieval):
            for row in blob[1]:
                code = (row.get("countryiso3code") or "").upper()
                label = str(row.get("date", ""))
                value = row.get("value")
                if value is None or not label[:4].isdigit():
                    continue
                donors[(code, metric, int(label[:4]))] = float(value)

    for points in annual.values():
        points.sort()

    return {"sources": sources, "annual": annual, "daily": daily, "donors": donors,
            "security": security_national(spec)}


def security_national(spec: dict) -> dict[str, list[tuple[int, float]]]:
    """The UCDP national monthly series, recomputed from the parsed artifact.

    Summed over **every scope the artifact carries**, including `unattributed`, so this is the country and
    not the states — the same rule the dbt model applies, arrived at independently here. If the model
    ever summed only the 37 units, the spine comparison below would catch it as a value mismatch rather
    than as a plausible-looking smaller number.
    """
    path = REPO_ROOT / "data" / "staging" / "ucdp_state_month.csv"
    if not path.exists():
        return {}
    items = {}
    for cfg in (spec.get("ucdp_source") or {}).get("metrics", []):
        items[cfg] = cfg
    with path.open(newline="", encoding="utf-8") as handle:
        totals: dict[str, dict[int, float]] = {}
        for row in csv.DictReader(handle):
            item = row["item"]
            if items and item not in items:
                continue
            year, _, month = str(row["period_month"])[:7].partition("-")
            bucket = totals.setdefault(item, {})
            index = mi(int(year), int(month))
            bucket[index] = bucket.get(index, 0.0) + float(row["value"])
    return {metric: sorted(points.items()) for metric, points in totals.items()}


def daily_to_monthly(daily: list[tuple[str, float]], rule: str) -> dict[int, tuple[float, int]]:
    """Apply the rule named in quality.yml. Only the declared rule is implemented — so an edit to the
    spec that named a rule this verifier does not know would fail loudly instead of silently passing."""
    if rule != "mean_of_daily_observations":
        raise SystemExit(f"verifier does not implement the declared resample rule {rule!r}")
    buckets: dict[int, list[float]] = {}
    for date, value in daily:
        buckets.setdefault(mi(int(date[:4]), int(date[5:7])), []).append(value)
    return {index: (sum(vals) / len(vals), len(vals)) for index, vals in buckets.items()}


# ---------------------------------------------------------------------------------------------
# the declared rules
# ---------------------------------------------------------------------------------------------
def expected_spine(annual, oil_monthly, security, spec) -> tuple[dict, int, int]:
    """Recompute every (metric, month) row from the spec's alignment and interpolation rules."""
    floor = mi(int(str(spec["spine"]["start"])[:4]), int(str(spec["spine"]["start"])[5:7]))
    annual_step = spec["alignment"]["annual"]["step_months"]
    max_span = spec["interpolation"]["max_span_months"]
    anchor_month = spec["alignment"]["annual"]["anchor_month"]

    series: dict[str, list[tuple[int, float]]] = {
        metric: [(i, v) for i, v in points if i >= floor]
        for metric, points in annual.items()
    }
    series["oil"] = [(i, v) for i, (v, _) in sorted(oil_monthly.items()) if i >= floor]
    # The security series are monthly and are **never interpolated** (harmonisation.yml
    # `interpolation.no_interpolation`, keyed on the catalogue's `unit = 'count'`), so a month the archive
    # does not cover stays unobserved even where two nearby months are observed. That is what the loop
    # below does with them: `b - a` is 1, never 12, so nothing is filled between them.
    for metric, points in security.items():
        series[metric] = [(i, v) for i, v in points if i >= floor]

    last = max(points[-1][0] for points in series.values() if points)
    months = list(range(floor, last + 1))

    rows: dict[tuple[str, int], tuple[float | None, str]] = {}
    for metric, points in series.items():
        observed = dict(points)
        values: dict[int, float] = dict(points)
        kind = {i: "unobserved" for i in months}
        for index in observed:
            kind[index] = "observed"
        for (a, va), (b, vb) in pairwise(points):
            if b - a != annual_step or b - a > max_span:
                continue
            for index in range(a + 1, b):
                kind[index] = "interpolated"
                values[index] = va + (vb - va) * (index - a) / (b - a)
        for index in months:
            if kind[index] == "unobserved":
                rows[(metric, index)] = (None, "unobserved")
            else:
                rows[(metric, index)] = (values[index], kind[index])

    # sanity: the anchor month rule really is July for annual series, as the spec declares
    assert anchor_month == 7, "verifier assumes the annual midpoint rule is July"

    return rows, floor, last


def expected_anchor(rows: dict, spec) -> dict:
    """Recompute each metric's anchor period and the rule that produced it."""
    anchor_index = mi(int(str(spec["index"]["anchor_period"])[:4]), int(str(spec["index"]["anchor_period"])[5:7]))
    out = {}
    per_metric: dict[str, list[tuple[int, float]]] = {}
    for (metric, index), (value, _) in rows.items():
        if value is not None:
            per_metric.setdefault(metric, []).append((index, value))

    for metric, points in per_metric.items():
        points.sort()
        at_fixed = dict(points).get(anchor_index)
        if at_fixed is not None:
            out[metric] = (anchor_index, at_fixed, "fixed_2000_01")
            continue
        later = [p for p in points if p[0] >= anchor_index]
        if later:
            out[metric] = (later[0][0], later[0][1], "first_available_after_2000_01")
    return out


# ---------------------------------------------------------------------------------------------
# the checks
# ---------------------------------------------------------------------------------------------
# One long main(): a verifier is a list of checks, and splitting it into helpers would hide the
# interface a reader actually needs to see — what is checked, in what order, against which source.
def main() -> int:
    if not DB_PATH.exists():
        raise SystemExit(f"no analytical base at {DB_PATH} — run `dbt build --project-dir dbt` first")

    spec = yaml.safe_load((SPEC_DIR / "harmonisation.yml").read_text(encoding="utf-8"))
    quality_spec = yaml.safe_load((SPEC_DIR / "quality.yml").read_text(encoding="utf-8"))
    outcomes = yaml.safe_load((SPEC_DIR / "outcomes.yml").read_text(encoding="utf-8"))

    raw = load_raw(spec)
    frozen_rule = next(
        r["rule"] for r in quality_spec["resample_rules"] if r["dataset_id"] == "DCOILBRENTEU"
    )
    oil_monthly = daily_to_monthly(raw["daily"], frozen_rule)
    rows, floor, last_month = expected_spine(raw["annual"], oil_monthly, raw["security"], spec)
    anchors = expected_anchor(rows, spec)

    con = duckdb.connect(str(DB_PATH), read_only=True)
    failures: list[str] = []

    print(f"raw vintages: {raw['sources']}")
    print(f"declared resample rule: {frozen_rule} (from quality.yml)")
    print(f"recomputed spine: floor {month_label(floor)}, last {month_label(last_month)}, "
          f"{last_month - floor + 1} months, {len({m for m, _ in rows})} metrics, {len(rows)} rows")

    # ---- 1. fact_metric, row for row -------------------------------------------------------
    built = {
        (metric, parse_index(period)): (value, kind)
        for metric, period, value, kind in con.execute(
            f"select metric_id, period_month, value, observation_type from {SCHEMA}.fact_metric"
        ).fetchall()
    }
    if set(built) != set(rows):
        missing = sorted(set(rows) - set(built))[:5]
        extra = sorted(set(built) - set(rows))[:5]
        failures.append(
            f"fact_metric grid differs from the recomputed spine: "
            f"{len(set(rows) - set(built))} missing (e.g. {[month_label(i) for _, i in missing]}), "
            f"{len(extra)} extra (e.g. {[month_label(i) for _, i in extra]})"
        )
    mismatched_value = mismatched_kind = 0
    examples: list[str] = []
    for key in sorted(set(built) & set(rows)):
        want_value, want_kind = rows[key]
        got_value, got_kind = built[key]
        if got_kind != want_kind:
            mismatched_kind += 1
            if len(examples) < 5:
                examples.append(
                    f"{key[0]}/{month_label(key[1])}: type {got_kind} vs {want_kind}"
                )
        if (want_value is None) != (got_value is None) or (
            want_value is not None
            and got_value is not None
            # relative tolerance: an interpolation of population (~2e8) cannot be asserted at 1e-9
            # absolute, and one of a mortality rate (~1e2) should not be allowed to drift.
            and abs(want_value - got_value) > 1e-9 * max(1.0, abs(want_value))
        ):
            mismatched_value += 1
            if len(examples) < 5 and want_value is not None and got_value is not None:
                examples.append(
                    f"{key[0]}/{month_label(key[1])}: {got_value!r} vs {want_value!r} "
                    f"(diff {abs(want_value - got_value):.3g})"
                )
    if mismatched_kind:
        failures.append(
            f"fact_metric: {mismatched_kind} rows carry the wrong observation_type — {examples}"
        )
    if mismatched_value:
        failures.append(
            f"fact_metric: {mismatched_value} rows carry a different value than recomputed — {examples}"
        )

    counts: dict[str, int] = {"observed": 0, "interpolated": 0, "unobserved": 0}
    for _, kind in built.values():
        counts[kind] = counts.get(kind, 0) + 1
    pct = 100.0 * counts["observed"] / max(len(built), 1)
    print(f"\nbase table: {len(built)} rows | observed {counts['observed']} "
          f"({pct:.1f}%), interpolated {counts['interpolated']}, unobserved {counts['unobserved']}")

    # ---- 2. no extrapolation, checked directly --------------------------------------------
    extrapolated = [
        (metric, month_label(index))
        for (metric, index), (value, _) in built.items()
        if value is not None and (index < min(i for m, i in rows if m == metric)
                                 or index > max(i for m, i in rows if m == metric))
    ]
    if extrapolated:
        failures.append(f"fact_metric carries values outside the observed span: {extrapolated[:5]}")

    # ---- 3. the index ---------------------------------------------------------------------
    anchor_rows = {
        metric: (parse_index(period), value, rule)
        for metric, period, value, rule in con.execute(
            f"select metric_id, anchor_period, anchor_value, anchor_rule from {SCHEMA}.metric_anchor"
        ).fetchall()
    }
    for metric, (index, value, rule) in anchors.items():
        got = anchor_rows.get(metric)
        if got is None:
            failures.append(f"metric_anchor has no row for {metric}")
            continue
        if got[0] != index or got[2] != rule or abs(got[1] - value) > 1e-9:
            failures.append(
                f"metric_anchor {metric}: built ({month_label(got[0])}, {got[2]}, {got[1]:.6g}) vs "
                f"recomputed ({month_label(index)}, {rule}, {value:.6g})"
            )
    indexed = con.execute(
        f"""
        select count(*) from {SCHEMA}.fact_metric f
        join {SCHEMA}.metric_anchor a using (metric_id)
        where f.value is not null
          and abs(f.value_indexed - f.value / a.anchor_value * 100) > 1e-9
        """
    ).fetchone()[0]
    if indexed:
        failures.append(f"fact_metric: {indexed} rows have a value_indexed that is not value/anchor*100")
    at_anchor = con.execute(
        f"""
        select count(*) from {SCHEMA}.fact_metric f
        join {SCHEMA}.metric_anchor a using (metric_id)
        where f.period_month = a.anchor_period and abs(f.value_indexed - 100) > 1e-9
        """
    ).fetchone()[0]
    if at_anchor:
        failures.append(f"fact_metric: {at_anchor} anchor months are not indexed at 100")
    fallback = sum(1 for _, _, rule in anchors.values() if rule != "fixed_2000_01")
    print(f"index: {len(anchors)} anchors, {len(anchors) - fallback} at the fixed January-2000 anchor, "
          f"{fallback} on the recorded fallback rule")

    # ---- 4. the frozen Brent rule ---------------------------------------------------------
    built_oil = {
        parse_index(month): (value, n)
        for month, value, n in con.execute(
            "select period_month, value, n_daily_observations from main_staging.stg_fred_monthly"
        ).fetchall()
    }
    wrong = [month_label(i) for i, (v, n) in oil_monthly.items()
             if i not in built_oil or abs(built_oil[i][0] - v) > 1e-9 or built_oil[i][1] != n]
    if wrong:
        failures.append(f"monthly Brent disagrees with the frozen '{frozen_rule}' rule: {wrong[:5]}")
    print(f"oil: {len(built_oil)} months recomputed under the frozen rule, "
          f"{len(wrong)} disagreements")

    # ---- 5. the administration spine ------------------------------------------------------
    built_admin = con.execute(
        f"""select admin_id, president, party, start_date, end_date, n_terms, end_date_effective,
                   oil_price_at_start_month_mean
            from {SCHEMA}.dim_administration order by admin_id"""
    ).fetchall()
    if len(built_admin) != len(BASE_SPEC_ADMINISTRATIONS):
        failures.append(f"dim_administration has {len(built_admin)} rows, base spec section 7 has 5")
    for built_row, spec_row in zip(built_admin, BASE_SPEC_ADMINISTRATIONS):
        _, president, party, start, end, n_terms, effective, oil = built_row
        want = BASE_SPEC_ADMINISTRATIONS[built_row[0] - 1]
        if (president, party, str(start), str(end) if end else None, n_terms) != (
            want[1], want[2], want[3], want[4], want[5]
        ):
            failures.append(f"dim_administration row {built_row[0]} differs from base spec section 7")
        expected_oil = oil_monthly.get(mi(int(str(start)[:4]), int(str(start)[5:7])))
        if expected_oil and abs(oil - expected_oil[0]) > 1e-9:
            failures.append(f"dim_administration row {built_row[0]}: oil price at start is not the "
                            f"Brent value for its start month")
    boundary = con.execute(
        f"""select a.end_date, b.start_date from {SCHEMA}.dim_administration a
            join {SCHEMA}.dim_administration b on b.admin_id = a.admin_id + 1
            where a.admin_id = 2"""
    ).fetchone()
    if tuple(str(x) for x in boundary) != DECIDED_BOUNDARY:
        failures.append(
            f"the Yar'Adua -> Jonathan boundary is {boundary}, not the decided "
            f"{DECIDED_BOUNDARY} (acting from 2010-02-09, sworn in 2010-05-06)"
        )
    print(f"administration spine: {len(built_admin)} rows, boundary {boundary[0]} -> {boundary[1]}")

    # ---- 6. term strata cover the window exactly once -------------------------------------
    built_terms = con.execute(
        f"""select term_id, admin_id, term_ordinal, term_start, term_end, tenure_stratum
            from {SCHEMA}.dim_administration_term order by term_start"""
    ).fetchall()
    expected_terms = []
    admin_by_id = {row[0]: row for row in built_admin}
    for admin_id, president, party, start, end, n_terms in BASE_SPEC_ADMINISTRATIONS:
        successor = admin_by_id.get(admin_id + 1)
        effective = successor[3] if successor else (str(end) if end else "9999-12-31")
        for term in range(1, n_terms + 1):
            term_start = _plus_years(start, 4 * (term - 1))
            term_end = _plus_years(start, 4 * term) if term < n_terms else str(effective)
            expected_terms.append(
                (admin_id * 10 + term, admin_id, term, term_start, term_end,
                 f"{party}_{'first' if term == 1 else 'second'}")
            )
    if len(built_terms) != len(expected_terms):
        failures.append(f"dim_administration_term has {len(built_terms)} rows, expected "
                        f"{len(expected_terms)} from the base spec's two-term administrations")
    for built_row, want in zip(built_terms, sorted(expected_terms, key=lambda r: r[3])):
        if (built_row[0], built_row[1], built_row[2], str(built_row[3]), str(built_row[4]),
                built_row[5]) != (want[0], want[1], want[2], want[3], want[4], want[5]):
            failures.append(f"dim_administration_term {built_row[0]} differs from the recomputed terms")
    strata_months = con.execute(
        f"""select tenure_stratum, count(distinct period_month) from {SCHEMA}.fact_metric
            group by 1 order by 1"""
    ).fetchall()
    strata = {name: n for name, n in strata_months if name}
    if set(strata) != {"PDP_first", "PDP_second", "APC_first", "APC_second"}:
        failures.append(f"the four LOCKED strata are not all present: {sorted(strata)}")
    if sum(strata.values()) + 5 != last_month - floor + 1:
        failures.append(
            f"strata cover {sum(strata.values())} months + 5 pre-study = "
            f"{sum(strata.values()) + 5}, spine has {last_month - floor + 1}"
        )
    print(f"term strata: {sorted(strata.items())} (+5 pre-study months unassigned)")

    # ---- 7. the metric catalogue agrees with outcomes.yml ---------------------------------
    report = _latest_quality_report()
    report_grain = {
        series["metric_id"]: series["grain_period"]
        for series in report["series"]
        if series["source"] in ("worldbank", "fred")
    }
    report_status = {
        series["metric_id"]: series["status"]
        for series in report["series"]
        if series["source"] in ("worldbank", "fred")
    }
    catalogue = {
        row[0]: row
        for row in con.execute(
            f"""select metric_id, label, short_label, unit, direction, domain, is_outcome,
                       coverage_status, catalogue_frequency, is_landed, quality_status, frequency_gap
                from {SCHEMA}.dim_metric"""
        ).fetchall()
    }
    if len(catalogue) < 25:
        failures.append(f"dim_metric has {len(catalogue)} rows; the catalogue has 25")
    for outcome in outcomes["outcomes"]:
        got = catalogue.get(outcome["id"])
        if got is None:
            failures.append(f"dim_metric is missing the outcome {outcome['id']}")
            continue
        checks = {
            "label": (got[1], outcome["label"]),
            "short_label": (got[2], outcome["short"]),
            "unit": (got[3], outcome["unit"]),
            "direction": (got[4], outcome["direction"]),
            "domain": (got[5], outcome["domain"]),
            "catalogue_frequency": (got[8], outcome["frequency"]),
            "coverage_status": (got[7], outcome["coverage_status"]),
        }
        for field, (built_value, spec_value) in checks.items():
            if built_value != spec_value:
                failures.append(
                    f"dim_metric {outcome['id']}.{field}: built {built_value!r}, "
                    f"outcomes.yml says {spec_value!r}"
                )
    # percentage-point series must actually be measured in percent (quality.yml consistency)
    for metric_id in quality_spec["spike_measure"]["percentage_point_series"]:
        row = catalogue.get(metric_id)
        if row and not str(row[3]).startswith("%"):
            failures.append(
                f"quality.yml treats {metric_id} as a percentage-point series but its unit is "
                f"{row[3]!r}"
            )
    # A frequency gap is a landed series whose catalogue grain differs from what the Stage 3 gate report
    # says actually landed — read from the report, not from the bone the base is being checked against.
    gaps = sorted(m for m, row in catalogue.items() if row[11])
    expected_gaps = sorted(
        m for m, row in catalogue.items()
        if report_grain.get(m) is not None and row[8] != report_grain[m]
    )
    if gaps != expected_gaps:
        failures.append(f"frequency_gap is {gaps}, recomputed from the quality report {expected_gaps}")
    for metric_id, status in report_status.items():
        row = catalogue.get(metric_id)
        if row is not None and row[10] != status:
            failures.append(
                f"dim_metric {metric_id}.quality_status is {row[10]!r}, but the Stage 3 report says "
                f"{status!r} — the quality status is not travelling"
            )
    print(f"metric catalogue: {len(catalogue)} metrics, {sum(1 for r in catalogue.values() if r[6])} "
          f"outcomes, {len(gaps)} frequency gaps ({', '.join(gaps)})")

    # ---- 8. definition breaks travel ------------------------------------------------------
    report_breaks = {
        (series["metric_id"], str(b["date"]))
        for series in report["series"] if series["source"] in ("worldbank", "fred")
        for b in series["gates"]["definition_drift"]["breaks"]
    }
    built_breaks = {
        (metric, str(date))
        for metric, date in con.execute(
            f"select metric_id, break_date from {SCHEMA}.dim_definition_break"
        ).fetchall()
    }
    if not report_breaks <= built_breaks:
        failures.append(
            f"definition breaks do not all reach the base: missing "
            f"{sorted(report_breaks - built_breaks)[:5]}"
        )
    print(f"definition breaks: {len(built_breaks)} in the base, "
          f"{len(report_breaks)} declared for national series")

    # ---- 9. declared gaps are declared ----------------------------------------------------
    panel = con.execute(
        f"""select count(*), count(distinct state_id), count(distinct period_month),
                   count(d1_faac_per_capita), count(d2_faac_share_of_state_revenue),
                   count(faac_gross_total_naira), count(distinct faac_publisher)
            from {SCHEMA}.state_panel"""
    ).fetchone()
    if panel[1] != 37 or panel[2] != last_month - floor + 1 or panel[0] != 37 * (last_month - floor + 1):
        failures.append(f"state panel is not a complete 37 x {last_month - floor + 1} grid: {panel[:3]}")
    # The per-capita and IGR-share columns are the two that must stay empty: one needs an unmade
    # decision (which population series, X-09) and one needs a series nobody has landed. A populated one
    # is a decision that was taken somewhere other than the spec.
    if panel[3] or panel[4]:
        failures.append(
            "the per-capita or IGR-share dose column is populated, but neither a chosen population "
            "denominator (X-09) nor a state IGR series is declared in harmonisation.yml"
        )
    # Every FAAC row, exactly once, on the panel: the join key from the dose to the grid is checked here
    # as a count because a broken join empties the dose while leaving both tables plausible.
    dose_rows, fct_rows = con.execute(
        f"""select (select count(*) from {SCHEMA}.faac_state_allocation),
                   (select count(*) from {SCHEMA}.state_panel
                     where state_id = 15 and faac_gross_total_naira is not null)"""
    ).fetchone()
    if panel[5] != dose_rows:
        failures.append(
            f"state_panel carries {panel[5]} dose values but faac_state_allocation has {dose_rows} rows"
        )
    if fct_rows:
        failures.append(
            f"the FCT has {fct_rows} FAAC dose value(s); Table III distributes among 36 beneficiaries "
            "and the FCT's line is funded from the federal share"
        )
    declared = [g["id"] for g in spec["declared_gaps"]]
    if len(declared) < 5:
        failures.append(f"harmonisation.yml declares only {len(declared)} gaps")
    donors = con.execute(
        f"""select count(*), count(distinct country_iso3), count(*) filter (where is_treated_unit),
                   count(distinct metric_id) from {SCHEMA}.fact_donor_panel"""
    ).fetchone()
    # The expected pool size is the *landed candidate set*, read from the raw layer rather than typed here:
    # the flow's candidate list is a design decision that changes (it went from 13 to 99 candidates on
    # 2026-10-18, and the treated unit is excluded by name), and a literal in the verifier is exactly the
    # kind of copy that goes stale without anyone noticing (C-54, C-58).
    expected_donor_countries = {code for code, _metric, _year in raw["donors"]}
    if donors[1] != len(expected_donor_countries) or donors[2] != 0:
        failures.append(
            f"donor panel: {donors[1]} countries, {donors[2]} treated-unit row(s) "
            f"(expected {len(expected_donor_countries)} from the raw layer, 0)"
        )
    if "NG" in expected_donor_countries:
        failures.append("the treated unit (NG) is inside the landed candidate pool")
    expected_donor_keys = {(c, m, y) for (c, m, y), v in raw["donors"].items()}
    built_donor_keys = {
        (c, m, y) for c, m, y in con.execute(
            f"select country_iso3, metric_id, period_year from {SCHEMA}.fact_donor_panel"
        ).fetchall()
    }
    missing_donors = expected_donor_keys - built_donor_keys
    if missing_donors:
        failures.append(f"donor panel is missing {len(missing_donors)} country-metric-years")
    print(f"state panel: {panel[0]} rows, 37 units x {panel[2]} months, {panel[5]} nominal FAAC dose "
          f"value(s) from {panel[6]} publisher(s); per-capita and IGR-share empty "
          f"(declared gaps: {', '.join(declared[:3])}…)")
    print(f"donor panel: {donors[0]} rows, {donors[1]} countries, {donors[3]} predictors, "
          f"{len(missing_donors)} missing")

    print()
    if failures:
        print(f"FAILED — {len(failures)} problem(s):")
        for problem in failures[:40]:
            print(f"  - {problem}")
        if len(failures) > 40:
            print(f"  … and {len(failures) - 40} more")
        return 1
    print("PASS — the analytical base recomputes from the raw payloads under the declared specs: spine, "
          "interpolation, index anchor, frozen Brent rule, administration spine, term strata, metric "
          "catalogue, definition breaks and declared gaps all agree")
    return 0


def _plus_years(date_text: str, years: int) -> str:
    year, month, day = (int(part) for part in str(date_text)[:10].split("-"))
    return f"{year + years:04d}-{month:02d}-{day:02d}"


def _latest_quality_report() -> dict:
    reports = sorted((REPO_ROOT / "registry" / "quality").glob("*/report.json"))
    if not reports:
        raise SystemExit("no Stage 3 quality report found — run check_quality.py first")
    return json.loads(reports[-1].read_text(encoding="utf-8"))


if __name__ == "__main__":
    sys.exit(main())
