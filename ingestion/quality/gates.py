"""Stage 3 quality gates — the five checks a landed series must pass to leave the raw layer.

PHASES.md Stage 3 is the "honesty chokepoint": Stage 8's limitations section is largely written from
this module's output. The gates are:

  1. **gap**              a run of more than ``gap_max_months`` consecutive missing months
  2. **spike**            a period-over-period move beyond ``spike_pct``, flagged for adjudication
  3. **revision**         this vintage vs the previous one for the same period, beyond tolerance
  4. **definition-drift** a declared break inside the window is carried as an annotation
  5. **provenance**       every value is observed, not imputed, or its imputation method is named

Everything measured is measured **inside the declared study window**. That is deliberate: scanning a
series' whole history fires on 1961->1962 (+2039%) in `gdp_growth` and on pre-1999 volatility in five
more series, none of which is inside the question (decisions C-06, C-21). Noise in a quality report is
worse than an absent gate, because it teaches the reader to ignore flags.

Two judgements worth stating, because the gates could reasonably have been written the other way:

* **A spike is flagged, not failed.** A >50% move in a policy-era macro series is usually a real
  documented event (the 2008 oil peak, the 2020 collapse, the 2023 float), and the gate cannot tell
  that from a typo. So a flag is *adjudicated* in ``quality.yml`` and an unadjudicated flag is reported
  as such. There is no path where a flag disappears without a reason attached.
* **Only adjacent periods are compared for spikes.** Comparing consecutive *observed* years across a
  hole (2000 -> 2004 because 2001-03 are missing) measures a four-year level change and would dress it
  as a spike. Non-adjacent pairs are counted and skipped instead.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import pairwise

# ------------------------------------------------------------------------------------------
# period arithmetic — everything is expressed in months so the gates mean the same thing at
# annual, monthly and daily grain
# ------------------------------------------------------------------------------------------


def month_index(year: int, month: int) -> int:
    """Zero-based month counter, so differences are month counts."""
    return year * 12 + (month - 1)


def index_to_month(index: int) -> str:
    return f"{index // 12:04d}-{index % 12 + 1:02d}"


@dataclass(frozen=True)
class Point:
    """One period of a series as landed. No transformation happens in this layer."""

    label: str
    start_index: int
    end_index: int  # inclusive; an annual period spans 12 months, a monthly one spans 1
    value: float | None

    @property
    def observed(self) -> bool:
        return self.value is not None


# ------------------------------------------------------------------------------------------
# parsers — one per payload shape, all keyless and dependency-free
# ------------------------------------------------------------------------------------------


def _worldbank_points(rows) -> list[Point]:
    """Annual rows -> sorted points.

    Gotcha: the API returns rows in **descending** date order (2025 first, 1960 last). The result is
    sorted here rather than trusted, because a spike gate over descending data would report every
    change with its sign flipped and every gap run reversed.
    """
    points: list[Point] = []
    for row in rows or []:
        raw_date = row.get("date")
        if not raw_date or not str(raw_date)[:4].isdigit():
            continue
        year = int(str(raw_date)[:4])
        value = row.get("value")
        points.append(
            Point(
                label=str(year),
                start_index=month_index(year, 1),
                end_index=month_index(year, 12),
                value=None if value is None else float(value),
            )
        )
    return sorted(points, key=lambda p: p.start_index)


def parse_worldbank_payload(blob) -> list[Point]:
    """World Bank ``[metadata, rows]`` payload for one country."""
    if not isinstance(blob, list) or len(blob) != 2 or not isinstance(blob[1], list):
        raise ValueError("not a World Bank [metadata, rows] payload")
    return _worldbank_points(blob[1])


def parse_worldbank_by_country(blob) -> dict[str, list[Point]]:
    """The same payload split by country, for the 13-country donor panel.

    A donor-panel retrieval returns every donor in one payload, and coverage differs by country
    (Venezuela's oil-rents series stops in 2014), so gating the payload as a single series would
    average 13 different coverage stories into none.
    """
    if not isinstance(blob, list) or len(blob) != 2 or not isinstance(blob[1], list):
        raise ValueError("not a World Bank [metadata, rows] payload")
    grouped: dict[str, list[dict]] = {}
    for row in blob[1]:
        code = ((row.get("country") or {}).get("id")) or row.get("countryiso3code") or "??"
        grouped.setdefault(str(code).upper(), []).append(row)
    return {code: _worldbank_points(rows) for code, rows in grouped.items()}


def parse_fred_payload(blob) -> list[tuple[object, float | None]]:
    """FRED ``observations`` payload, daily rows. Returns ``[(date, value_or_None)]``.

    FRED marks a day with no quote with a literal ``"."`` — a weekend, a holiday, or a genuine gap.
    Returning raw ``(date, value)`` pairs rather than points lets the declared resample rule decide
    the grain, which is the whole point of freezing that rule (see ``quality.yml``).
    """
    if not isinstance(blob, dict) or "observations" not in blob:
        raise ValueError("not a FRED observations payload")
    from datetime import date as _date

    out: list[tuple[object, float | None]] = []
    for obs in blob["observations"]:
        raw = obs.get("date")
        if not raw:
            continue
        value = obs.get("value")
        try:
            parsed = _date.fromisoformat(str(raw))
        except ValueError:
            continue
        out.append((parsed, None if value in (None, "", ".") else float(value)))
    return out


def parse_staging_monthly_series(
    rows,
    *,
    key_field: str,
    value_field: str,
    publisher_field: str | None = None,
    publisher_precedence: list[str] | None = None,
) -> dict[str, list[Point]]:
    """A parsed staging table (one row per unit-period-item) -> monthly points per unit.

    Document sources cannot be gated from their payload: the payload is a PDF or a spreadsheet, and the
    series only exists after ``ingestion/parsers/`` has read it. So the gates read the *parsed* artifact
    — the same file Stage 4 reads — rather than deriving the series a second time here, which would give
    the gate and the base two series that could drift apart.

    The month is emitted only where the table has a value. Unlike ``resample_to_monthly`` there is no
    reason to pad the span with empty points: the gap gate measures holes from the month *indices*, so a
    hole is already visible as a missing index, and padding would inflate ``n_observed``'s denominator.

    ``publisher_precedence`` exists because the same month is published twice. The first publisher in
    the list that carries the month supplies the value, mirroring the rule the base applies; the list
    itself is declared in ``analysis/specs/harmonisation.yml`` and passed in, never hard-coded here.
    """
    order = list(publisher_precedence or [])
    chosen: dict[str, dict[int, tuple[float, int]]] = {}
    for row in rows:
        key = str(row[key_field])
        raw_month = str(row["period_month"])[:7]
        year, _, month = raw_month.partition("-")
        index = month_index(int(year), int(month))
        value = row.get(value_field)
        if value in (None, "", "nan"):
            continue
        rank = 0
        if publisher_field is not None:
            publisher = str(row.get(publisher_field, ""))
            rank = order.index(publisher) if publisher in order else len(order)
        current = chosen.setdefault(key, {}).get(index)
        if current is None or rank < current[1]:
            chosen[key][index] = (float(value), rank)
    return {
        key: [
            Point(label=index_to_month(index), start_index=index, end_index=index, value=value)
            for index, (value, _) in sorted(series.items())
        ]
        for key, series in chosen.items()
    }


def resample_to_monthly(observations, rule: str) -> list[Point]:
    """Apply the declared daily->monthly rule. ``rule`` must be ``mean_of_daily_observations``.

    Assertive rather than permissive: an unrecognised rule raises, because silently falling back to
    some default aggregation is exactly how an unfrozen rule becomes an unexplained estimate.
    """
    if rule != "mean_of_daily_observations":
        raise ValueError(f"unknown daily->monthly rule: {rule!r}")
    buckets: dict[int, list[float]] = {}
    for day, value in observations:
        index = month_index(day.year, day.month)
        if value is not None:
            buckets.setdefault(index, []).append(value)
    if not buckets:
        return []
    first, last = min(buckets), max(buckets)
    points: list[Point] = []
    # Every month in the span is emitted, including empty ones, so a hole is visible as a hole
    # rather than silently absent from the series.
    for index in range(first, last + 1):
        values = buckets.get(index)
        points.append(
            Point(
                label=index_to_month(index),
                start_index=index,
                end_index=index,
                value=None if not values else sum(values) / len(values),
            )
        )
    return points


# ------------------------------------------------------------------------------------------
# the gates
# ------------------------------------------------------------------------------------------


def _in_window(point: Point, start_index: int, end_index: int) -> bool:
    """A period counts if any part of it falls inside the window."""
    return point.end_index >= start_index and point.start_index <= end_index


def coverage_gate(points: list[Point], start_index: int, end_index: int) -> dict:
    """How much of the study window the series actually covers, and where its edges fall short.

    Edge shortfall is reported here rather than as a gap on purpose: a series that simply starts in
    2005 has not *missed* 1999-2004, it was never published for it. Calling that a gap would put a
    coverage fact and a data hole in the same field.
    """
    observed = [p for p in points if p.observed and _in_window(p, start_index, end_index)]
    if not observed:
        return {
            "n_observed": 0,
            "first_observed": None,
            "last_observed": None,
            "window_months": end_index - start_index + 1,
            "lead_gap_months": None,
            "trail_gap_months": None,
            "density_in_span": 0.0,
        }
    first, last = observed[0], observed[-1]
    span_months = max(1, last.start_index - first.start_index + 1)
    lead = max(0, first.start_index - start_index)
    trail = max(0, end_index - last.end_index)
    return {
        "n_observed": len(observed),
        "first_observed": first.label,
        "last_observed": last.label,
        "window_months": end_index - start_index + 1,
        "lead_gap_months": lead,
        "trail_gap_months": trail,
        "density_in_span": round(len(observed) / span_months, 3),
    }


def gap_gate(points: list[Point], start_index: int, end_index: int, max_gap_months: int) -> dict:
    """Interior holes only: runs of missing months between the first and last observed period.

    An annual series that misses one year produces a 12-month hole and therefore trips a 3-month
    threshold, which is the intent — at annual grain "one missing year" *is* a large gap.
    """
    observed = [p for p in points if p.observed and _in_window(p, start_index, end_index)]
    runs: list[dict] = []
    for previous, current in pairwise(observed):
        missing = current.start_index - previous.end_index - 1
        if missing > 0:
            runs.append(
                {
                    "after": previous.label,
                    "before": current.label,
                    "missing_months": missing,
                    "missing_periods": (
                        missing // 12 if previous.end_index - previous.start_index == 11 else missing
                    ),
                }
            )
    longest = max((run["missing_months"] for run in runs), default=0)
    return {
        "max_gap_months": longest,
        "n_gap_runs": len(runs),
        "gap_runs": runs,
        "tripped": longest > max_gap_months,
    }


def spike_gate(
    points: list[Point],
    start_index: int,
    end_index: int,
    threshold_pct: float,
    measure: str = "relative",
    threshold_points: float = 10.0,
) -> dict:
    """Period-over-period moves beyond the threshold, inside the window.

    Two measures, because one rule cannot serve both series types: ``relative`` tests
    ``|delta / value| > threshold_pct`` and suits a **level** series (a price, a population);
    ``points`` tests ``|delta| > threshold_points`` and suits a series already expressed as a
    percentage, where the comparable statistic is the change in percentage points.

    The distinction is not cosmetic. A single 50%-relative rule flagged 52 of 88 series, because a
    growth rate moving 0.5% -> 3.0% is a 500% relative change and a 2.5-point move. Over-flagging
    hides the real problems in the flood, which is the failure a quality gate exists to prevent.

    Only **adjacent** periods are compared. The provisional gate in Stage 2 zipped consecutive
    observed periods, so a hole turned a multi-year level change into a single reported "spike".
    """
    if measure not in ("relative", "points"):
        raise ValueError(f"unknown spike measure: {measure!r}")
    observed = [p for p in points if p.observed and _in_window(p, start_index, end_index)]
    spikes: list[dict] = []
    non_adjacent = 0
    for previous, current in pairwise(observed):
        if current.start_index != previous.end_index + 1:
            non_adjacent += 1
            continue
        base = previous.value
        if measure == "relative":
            if not base:  # zero or None: a relative change is undefined
                continue
            change = (current.value - base) / abs(base) * 100.0
            tripped = abs(change) > threshold_pct
            detail = {"change_pct": round(change, 1)}
        else:
            change = current.value - base
            tripped = abs(change) > threshold_points
            detail = {"change_points": round(change, 2)}
        if tripped:
            spikes.append(
                {
                    "from": previous.label,
                    "to": current.label,
                    "from_value": previous.value,
                    "to_value": current.value,
                    **detail,
                }
            )
    return {
        "measure": measure,
        "threshold": threshold_pct if measure == "relative" else threshold_points,
        "threshold_pct": threshold_pct,
        "n_spikes": len(spikes),
        "spikes": spikes,
        "non_adjacent_pairs_skipped": non_adjacent,
        "tripped": bool(spikes),
    }


def definition_drift_gate(breaks: list[dict], start_index: int, end_index: int) -> dict:
    """Declared breaks that land inside the window. An annotation, never a failure."""

    def index_of(date_text: str) -> int:
        year, _, tail = date_text.partition("-")
        month = int(tail.split("-")[0]) if tail else 1
        return month_index(int(year), month)

    in_window = [
        dict(break_) for break_ in breaks if start_index <= index_of(break_["date"]) <= end_index
    ]
    return {
        "n_breaks_in_window": len(in_window),
        "breaks": in_window,
        "out_of_window_breaks": len(breaks) - len(in_window),
    }


def provenance_gate(declared_imputation: list[dict], n_points: int) -> dict:
    """Every value observed, or its imputation method named.

    No transformation happens in the raw layer (Stage 2 contract, and the sha256 provenance chain
    depends on it), so at Stage 3 this gate must find zero imputed values. It exists to make the
    Stage 4 hand-off explicit: imputation is allowed there, but it has to declare a method.
    """
    unnamed = [entry for entry in declared_imputation if not entry.get("method")]
    return {
        "n_points": n_points,
        # Zero by construction at Stage 3: the gates read the raw payloads, and no transformation
        # happens in the raw layer. What `declared_imputation` records is the Stage 4 *plan*, so
        # this stays 0 whether or not imputation has been declared downstream.
        "n_imputed": 0,
        "n_declarations": len(declared_imputation),
        "declared_imputation": declared_imputation,
        "status": "observed" if not declared_imputation else "declared_for_stage4",
        "unnamed_methods": len(unnamed),
        "tripped": bool(unnamed),
    }


def revision_gate(current: list[Point], previous: list[Point] | None, tol_pct: float,
                  tol_abs: float) -> dict:
    """This vintage vs the previous one, matched on period.

    A series present in the new vintage but absent from the old one is ``new_series``, not a
    revision — the World Bank catalogue grew from 15 to 22 datasets between the two vintages, and
    reporting seven new series as seven revisions would be wrong.
    """
    if previous is None:
        return {
            "previous_vintage": None,
            "status": "no_previous_vintage",
            "n_compared": 0,
            "n_revised": 0,
            "n_new_periods": len([p for p in current if p.observed]),
            "revisions": [],
            "tripped": False,
        }
    prior = {p.start_index: p.value for p in previous if p.observed}
    common = [p for p in current if p.observed and p.start_index in prior]
    revisions = []
    for point in common:
        before = prior[point.start_index]
        if before is None:
            continue
        delta = point.value - before
        relative = abs(delta) / abs(before) * 100.0 if before else float("inf")
        if relative > tol_pct and abs(delta) > tol_abs:
            revisions.append(
                {
                    "period": point.label,
                    "previous_value": before,
                    "current_value": point.value,
                    "change_pct": round(relative, 4),
                }
            )
    return {
        "previous_vintage": None,
        "status": "compared",
        "n_compared": len(common),
        "n_revised": len(revisions),
        "n_new_periods": len([p for p in current if p.observed and p.start_index not in prior]),
        "revisions": revisions,
        "tripped": bool(revisions),
    }


def quality_status(gates: dict) -> str:
    """`empty` · `flagged` · `ok` — the single field that travels with the series into the app.

    Mechanically derived so it cannot be asserted by hand: empty means nothing inside the window to
    analyse, flagged means at least one gate tripped, ok means neither.
    """
    if gates["coverage"]["n_observed"] == 0:
        return "empty"
    if gates["gap"]["tripped"] or gates["spike"]["tripped"] or gates["provenance"]["tripped"]:
        return "flagged"
    return "ok"


def evaluate_series(
    points: list[Point],
    *,
    grain_period: str,
    study_start: int,
    study_end: int,
    thresholds: dict,
    breaks: list[dict],
    declared_imputation: list[dict],
    previous_points: list[Point] | None = None,
    adjudications: list[dict] | None = None,
    spike_measure: str = "relative",
) -> dict:
    """Run all five gates over one series and attach its status."""
    coverage = coverage_gate(points, study_start, study_end)
    gap = gap_gate(points, study_start, study_end, thresholds["gap_max_months"])
    spike = spike_gate(
        points,
        study_start,
        study_end,
        thresholds["spike_pct"],
        measure=spike_measure,
        threshold_points=thresholds.get("spike_points", 10.0),
    )
    drift = definition_drift_gate(breaks, study_start, study_end)
    provenance = provenance_gate(declared_imputation, len(points))
    revision = revision_gate(
        points,
        previous_points,
        thresholds["revision_tolerance_pct"],
        thresholds["revision_tolerance_abs"],
    )

    # Adjudicate the spikes that fired, against the metric's own adjudications (the caller
    # filters to one metric). An unadjudicated flag is carried forward, never dropped.
    adjudicated, unadjudicated = [], []
    for spike_event in spike["spikes"]:
        entry = next(
            (a for a in (adjudications or []) if a["period"] == spike_event["to"]), None
        )
        if entry is None:
            unadjudicated.append(spike_event)
        else:
            adjudicated.append(
                {
                    **spike_event,
                    "verdict": entry.get("verdict", ""),
                    "reason": entry.get("reason", ""),
                }
            )
    spike["adjudicated"] = adjudicated
    spike["unadjudicated"] = unadjudicated

    gates = {
        "coverage": coverage,
        "gap": gap,
        "spike": spike,
        "definition_drift": drift,
        "provenance": provenance,
        "revision": revision,
    }
    return {
        "grain_period": grain_period,
        "spike_measure": spike_measure,
        "status": quality_status(gates),
        "gates": gates,
    }
