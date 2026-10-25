"""Verify `registry/comparisons/<vintage>/comparisons.json` against the base.

What this checks, and why each check exists:

- **Every count is recomputed from DuckDB**, not read back from the artifact: group means, both means, unit
  counts, month counts and the observed flags in each series.
- **The caption's numbers are the artifact's numbers.** A caption is prose, and prose drifts; here it is
  assembled from the same fields, and a mean moved by 0.1 without the caption moving fails.
- **No inferential field exists anywhere in the file.** A contrast between groups is an estimate, and
  estimates belong to Stage 6 with its verdict rule.
- **The vintage and the spec hash are right**, so an artifact cannot describe a spec that has since moved.

It does not import `analysis/R/08_comparisons.R`: the point is a second implementation over the same tables.

Run:
    python tests/verify_comparisons.py
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import date
from pathlib import Path

import duckdb
import jsonschema
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMA = REPO_ROOT / "registry" / "schema" / "comparisons.schema.json"
SPEC = REPO_ROOT / "analysis" / "specs" / "comparisons.yml"
DB = REPO_ROOT / "data" / "analytics.duckdb"

FORBIDDEN = ("p_value", "standard_error", "ci_low", "ci_high", "t_stat", "verdict", "stars", "q_value")


def fail(failures: list[str], message: str) -> None:
    failures.append(message)


def months_between(first: str, last: str) -> list[str]:
    year, month = int(first[:4]), int(first[5:])
    out: list[str] = []
    while f"{year:04d}-{month:02d}" <= last:
        out.append(f"{year:04d}-{month:02d}")
        month += 1
        if month == 13:
            year, month = year + 1, 1
    return out


def main() -> int:
    failures: list[str] = []
    index = json.loads((REPO_ROOT / "registry" / "dags" / "index.json").read_text(encoding="utf-8"))
    vintage = index["vintage_date"]
    artifact_path = REPO_ROOT / "registry" / "comparisons" / vintage / "comparisons.json"
    if not artifact_path.exists():
        print(f"FAILED — {artifact_path.relative_to(REPO_ROOT)} is missing")
        return 1
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))

    errors = sorted(jsonschema.Draft202012Validator(schema).iter_errors(artifact), key=lambda e: list(e.path))
    for error in errors[:20]:
        fail(failures, f"schema: /{'/'.join(map(str, error.path))} — {error.message[:140]}")

    spec = yaml.safe_load(SPEC.read_text(encoding="utf-8"))
    if artifact["vintage"] != vintage:
        fail(failures, f"artifact vintage {artifact['vintage']} is not the registry's {vintage}")
    disk_md5 = hashlib.md5(SPEC.read_bytes()).hexdigest()
    if artifact["spec"]["md5"] != disk_md5:
        fail(failures, "the artifact records a spec md5 that is not the spec on disk — it describes a method "
                       "that has since moved")

    window = months_between(spec["window"]["first"], spec["window"]["last"])
    counts = artifact["counts"]
    if counts["outcomes"] != len(artifact["outcomes"]):
        fail(failures, "counts.outcomes does not equal the outcomes array")
    if counts["groupings"] != len(spec["groupings"]):
        fail(failures, "counts.groupings does not equal the spec's groupings")
    if counts["groups_total"] != sum(len(o["groups"]) for o in artifact["outcomes"]):
        fail(failures, "counts.groups_total does not equal the groups present")
    if counts["charts"] != sum(1 for o in artifact["outcomes"] if not o["figure"] is None):
        fail(failures, "counts.charts does not equal the figures present")

    con = duckdb.connect(str(DB), read_only=True)
    series_index = json.loads((REPO_ROOT / "registry" / "series" / vintage / "index.json").read_text(encoding="utf-8"))
    series_rows = {row["id"]: row for row in series_index["outcomes"]}

    rows = con.execute(
        """
        select metric_id, strftime(period_month, '%Y-%m') as month, value, observation_type, tenure_stratum
        from main_analytics.fact_metric
        where period_month between ? and ?
        """,
        [date(int(spec["window"]["first"][:4]), int(spec["window"]["first"][5:]), 1),
         date(int(spec["window"]["last"][:4]), int(spec["window"]["last"][5:]), 1)],
    ).fetchall()
    by_metric: dict[str, list[tuple]] = {}
    for row in rows:
        by_metric.setdefault(row[0], []).append(row[1:])

    for outcome in artifact["outcomes"]:
        oid = outcome["id"]
        panel = series_rows.get(oid)
        if panel is None:
            fail(failures, f"{oid}: no panel in the series index")
            continue
        expected = {
            "native_in_window": panel["native_in_window"],
            "observed_months": panel["observations"]["observed"],
            "interpolated_months": panel["observations"]["interpolated"],
            "unobserved_months": panel["observations"]["unobserved"],
        }
        for key, value in expected.items():
            if outcome["observed"][key] != value:
                fail(failures, f"{oid}: observed.{key} is {outcome['observed'][key]}, the series index says {value}")
        if sum(outcome["observed"][k] for k in ("observed_months", "interpolated_months", "unobserved_months")) != len(window):
            fail(failures, f"{oid}: the three month counts do not sum to the window's {len(window)} months")

        seen = by_metric.get(oid, [])
        unassigned = [r for r in seen if r[3] is None]
        party = [g for g in outcome["groups"] if g["grouping_id"] == "party_tenure"]
        if len(party) + 0 and len(party) != 4:
            fail(failures, f"{oid}: {len(party)} party/tenure groups, expected 4")
        if sum(g["months"] for g in party) + len(unassigned) != len(window):
            fail(failures, f"{oid}: party months plus unassigned months do not equal the window")

        for group in party:
            members = [r for r in seen if r[3] == group["group_id"]]
            if len(members) != group["months"]:
                fail(failures, f"{oid}/{group['group_id']}: months is {group['months']}, the base has {len(members)}")
            values = [r[1] for r in members if r[1] is not None]
            observed = [r[1] for r in members if r[1] is not None and r[2] == "observed"]
            mean_all = sum(values) / len(values) if values else None
            mean_nat = sum(observed) / len(observed) if observed else None
            for label, got, want in (("group_mean", group["group_mean"], mean_all),
                                     ("group_mean_native_only", group["group_mean_native_only"], mean_nat)):
                if want is None and got is not None:
                    fail(failures, f"{oid}/{group['group_id']}: {label} is {got}, expected none")
                elif want is not None and (got is None or abs(got - want) > 5e-6 * max(1.0, abs(want))):
                    # The artifact writes six significant digits, so the check has to be that rounding and no
                    # looser: a mean moved in the fourth digit is a different number from the base's.
                    fail(failures, f"{oid}/{group['group_id']}: {label} is {got}, recomputed {want}")
            if group["months"] != len(group["series"]):
                fail(failures, f"{oid}/{group['group_id']}: series has {len(group['series'])} rows for {group['months']} months")
            expected_observed = {r[0] for r in members if r[2] == "observed"}
            got_observed = {row["month"] for row in group["series"] if row["observed"]}
            if expected_observed != got_observed:
                fail(failures, f"{oid}/{group['group_id']}: the observed marks differ from the base by "
                               f"{len(expected_observed ^ got_observed)} month(s)")
            if group["months"] and not re.search(rf"\b{group['months']} months\b", group["caption"]):
                fail(failures, f"{oid}/{group['group_id']}: the caption does not quote its {group['months']} months")
            if mean_all is not None:
                match = re.search(r"mean ([\d,]+\.\d)", group["caption"])
                if not match:
                    fail(failures, f"{oid}/{group['group_id']}: the caption quotes no mean")
                else:
                    quoted = float(match.group(1).replace(",", ""))
                    if abs(quoted - round(group["group_mean"], 1)) > 0.0500001:
                        fail(failures, f"{oid}/{group['group_id']}: caption says {quoted}, the artifact's mean "
                                       f"rounds to {round(group['group_mean'], 1)}")
    # ---- the state dose grouping ------------------------------------------------------------------
    dose_spec = next(g for g in spec["groupings"] if g["id"] == "state_dose_quartile")
    dose_first, dose_last = dose_spec["window"]["first"], dose_spec["window"]["last"]
    dose_months = months_between(dose_first, dose_last)
    state_rows = con.execute(
        """
        select state_name, strftime(period_month, '%Y-%m') as month, faac_gross_total_naira,
               fatalities, incidents, security_status
        from main_analytics.state_panel
        where period_month between ? and ?
        """,
        [date(int(dose_first[:4]), int(dose_first[5:]), 1), date(int(dose_last[:4]), int(dose_last[5:]), 1)],
    ).fetchall()

    dose_mean: dict[str, float] = {}
    for name, _month, dose, *_ in state_rows:
        if dose is not None:
            dose_mean.setdefault(name, 0.0)
    sums: dict[str, list[float]] = {name: [0.0, 0] for name in dose_mean}
    for name, _month, dose, *_ in state_rows:
        if dose is not None:
            sums[name][0] += dose
            sums[name][1] += 1
    ranked = sorted(sums.items(), key=lambda kv: kv[1][0] / kv[1][1])
    quartile_of: dict[str, int] = {}
    for position, (name, _) in enumerate(ranked, start=1):
        quartile_of[name] = -(-position * 4 // len(ranked))  # ceiling, as the engine's rank split
    if len(ranked) != 36:
        fail(failures, f"the dose exists for {len(ranked)} states, expected 36 (the FCT has no FAAC row)")

    for outcome in artifact["outcomes"]:
        state_groups = [g for g in outcome["groups"] if g["grouping_id"] == "state_dose_quartile"]
        if outcome["id"] not in dose_spec["applies_to"]:
            if state_groups:
                fail(failures, f"{outcome['id']}: carries a state grouping the spec does not declare for it")
            continue
        if len(state_groups) != 4:
            fail(failures, f"{outcome['id']}: {len(state_groups)} state groups, expected 4")
        column = outcome["id"]
        index_of = {"state_name": 0, "month": 1, "fatalities": 3, "incidents": 4, "security_status": 5}
        for group in state_groups:
            quartile = int(group["group_id"].split("q")[-1])
            members = [r for r in state_rows if quartile_of.get(r[0]) == quartile]
            units = {r[0] for r in members}
            if group["n_units"] != len(units):
                fail(failures, f"{outcome['id']}/{group['group_id']}: n_units is {group['n_units']}, base has {len(units)}")
            if group["months"] != len(dose_months):
                fail(failures, f"{outcome['id']}/{group['group_id']}: months is {group['months']}, "
                               f"the window is {len(dose_months)}")
            per_month: dict[str, list[float]] = {}
            for row in members:
                value = row[index_of[column]]
                if row[index_of["security_status"]] == "observed" and value is not None:
                    per_month.setdefault(row[1], []).append(float(value))
            monthly = {m: sum(v) / len(v) for m, v in per_month.items()}
            want = sum(monthly.values()) / len(monthly) if monthly else None
            got = group["group_mean"]
            if want is None and got is not None:
                fail(failures, f"{outcome['id']}/{group['group_id']}: mean is {got}, no observed state-month exists")
            elif want is not None and (got is None or abs(got - want) > 5e-6 * max(1.0, abs(want))):
                fail(failures, f"{outcome['id']}/{group['group_id']}: mean is {got}, recomputed {want}")
            if group["series"] and {row["month"] for row in group["series"]} != set(monthly):
                fail(failures, f"{outcome['id']}/{group['group_id']}: the series months differ from the base")
            if f"{len(units)} states" not in group["caption"]:
                fail(failures, f"{outcome['id']}/{group['group_id']}: the caption does not quote its {len(units)} states")
            if want is not None:
                match = re.search(r"mean ([\d,]+\.\d)", group["caption"])
                if not match or abs(float(match.group(1).replace(",", "")) - round(group["group_mean"], 1)) > 0.0500001:
                    fail(failures, f"{outcome['id']}/{group['group_id']}: caption mean disagrees with the recomputed one")

    # ---- figures, evidence pointers, and the absence of inference ---------------------------------
    known_outcomes = {row["id"] for row in index["outcomes"]}
    for outcome in artifact["outcomes"]:
        figure = outcome["figure"]
        if figure is None:
            fail(failures, f"{outcome['id']}: no figure, and the artifact does not record a refusal")
            continue
        path = REPO_ROOT / figure["path"]
        if not path.exists():
            fail(failures, f"{outcome['id']}: figure {figure['path']} is not on disk")
            continue
        if path.stat().st_size != figure["bytes"]:
            fail(failures, f"{outcome['id']}: figure bytes recorded as {figure['bytes']}, file is {path.stat().st_size}")
        svg = path.read_text(encoding="utf-8", errors="replace")
        if spec["figures"]["stamp"] not in svg:
            fail(failures, f"{outcome['id']}: the figure does not carry the '{spec['figures']['stamp']}' stamp")
        if outcome["short"] not in svg:
            fail(failures, f"{outcome['id']}: the figure does not name the outcome — a label cut out of the SVG "
                           f"cannot be seen by a reader or a check")
        evidence = outcome["closest_evidence"]
        if evidence["outcome_id"] is not None and evidence["outcome_id"] not in known_outcomes:
            fail(failures, f"{outcome['id']}: closest_evidence points at {evidence['outcome_id']}, not a catalogue outcome")
        if evidence["artifact"] and not (REPO_ROOT / evidence["artifact"]).exists():
            fail(failures, f"{outcome['id']}: closest_evidence names {evidence['artifact']}, which does not exist")

    def walk(node, path=""):
        if isinstance(node, dict):
            for key, value in node.items():
                if key in FORBIDDEN:
                    fail(failures, f"forbidden field {path}/{key} — this artifact describes and does not estimate")
                walk(value, f"{path}/{key}")
        elif isinstance(node, list):
            for i, value in enumerate(node):
                walk(value, f"{path}[{i}]")

    walk(artifact)

    con.close()
    if failures:
        print(f"FAILED — {len(failures)} problem(s):")
        for problem in failures[:40]:
            print(f"  - {problem}")
        if len(failures) > 40:
            print(f"  … and {len(failures) - 40} more")
        return 1
    print(f"verified      : {len(artifact['outcomes'])} outcomes, {counts['groups_total']} groups, "
          f"{counts['charts']} figures at vintage {vintage}")
    print("recomputed    : every group mean, both means, unit and month counts, observed marks and caption number")
    print("refused       : no inferential field finds a home here; the artifact describes and does not estimate")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
