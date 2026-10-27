"""Verify the tenure description against the trend it published.

The artifact carries the fitted trend at every native point, so every deviation, tenure mean and contrast can be
recomputed here without refitting a LOESS. The engine's method is checked against its spec; its arithmetic is
checked against itself, row by row.

Run:
    python tests/verify_tenure.py
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import date
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
FORBIDDEN = ("p_value", "standard_error", "confidence_interval", "effect", "significance")


def fail(failures, message):
    failures.append(message)


def month(value: str) -> date:
    return date(int(value[:4]), int(value[5:7]), 1)


def close(a: float, b: float, tol: float = 2e-5) -> bool:
    return abs(a - b) <= tol * max(1.0, abs(a), abs(b))


def main() -> int:
    failures: list[str] = []
    index = json.loads((REPO_ROOT / "registry" / "dags" / "index.json").read_text(encoding="utf-8"))
    vintage = index["vintage_date"]
    path = REPO_ROOT / "registry" / "tenure" / vintage / "tenure.json"
    doc = json.loads(path.read_text(encoding="utf-8"))

    spec_path = REPO_ROOT / doc["spec"]["path"]
    spec = yaml.safe_load(spec_path.read_text(encoding="utf-8"))
    if hashlib.md5(spec_path.read_bytes()).hexdigest() != doc["spec"]["md5"]:
        fail(failures, "the spec's md5 has moved since the artifact was written — the method on disk is not the "
                       "method that produced these numbers")
    if [float(s) for s in spec["trend"]["span_grid"]] != [float(s) for s in doc["spec"]["spans"]]:
        fail(failures, "the artifact's spans are not the spec's span grid")
    if spec["refusals"]["min_native"] != doc["spec"]["min_native"]:
        fail(failures, "the artifact's minimum native count is not the spec's")

    def walk(node, key_path=""):
        if isinstance(node, dict):
            for key, value in node.items():
                if key in FORBIDDEN:
                    fail(failures, f"{key_path}/{key}: a forbidden inferential field is published")
                walk(value, f"{key_path}/{key}")
        elif isinstance(node, list):
            for i, value in enumerate(node):
                walk(value, f"{key_path}[{i}]")

    walk(doc)

    described = [o for o in doc["outcomes"] if o["status"] == "described"]
    refused = [o for o in doc["outcomes"] if o["status"] == "refused"]
    if doc["counts"]["described"] != len(described) or doc["counts"]["refused"] != len(refused):
        fail(failures, "the counts block does not match the outcomes array")

    spans = [float(s) for s in doc["spec"]["spans"]]
    contrasts = 0
    for outcome in described:
        oid = outcome["id"]
        points = {float(t["span"]): t["points"] for t in outcome["trend"]}
        if sorted(points) != sorted(spans):
            fail(failures, f"{oid}: the trend block does not carry one series per declared span")
            continue
        for span, rows in points.items():
            for row in rows:
                if not close(row["value"] - row["trend"], row["deviation"], 5e-5):
                    fail(failures, f"{oid} span {span}: deviation != value - trend at {row['month']}")
                    break

        per_tenure = {t["president"]: t for t in outcome["tenures"]}
        windows = {}
        for president, tenure in per_tenure.items():
            if tenure["status"] != "described":
                continue
            lo, hi = month(tenure["start"]), month(tenure["end"])
            windows[president] = (lo, hi)
            means, abses = [], []
            for span in spans:
                devs = [row["deviation"] for row in points[span] if lo <= month(row["month"]) <= hi]
                if len(devs) != tenure["n_native"]:
                    fail(failures, f"{oid}/{president}: {len(devs)} points in the window, artifact says {tenure['n_native']}")
                means.append(sum(devs) / len(devs))
                abses.append(sum(abs(d) for d in devs) / len(devs))
            if not close(sum(means) / len(means), tenure["mean_deviation"]):
                fail(failures, f"{oid}/{president}: mean deviation does not recompute from the published trend")
            if not close(sum(abses) / len(abses), tenure["mean_absolute_deviation"], 5e-5):
                fail(failures, f"{oid}/{president}: mean absolute deviation does not recompute")
            if not (close(tenure["deviation_range"][0], min(means), 5e-5)
                    and close(tenure["deviation_range"][1], max(means), 5e-5)):
                fail(failures, f"{oid}/{president}: the span range is not the range of the per-span means")
            months = (hi.year - lo.year) * 12 + (hi.month - lo.month) + 1
            if not close(tenure["coverage"], tenure["n_native"] / months, 1e-3):
                fail(failures, f"{oid}/{president}: coverage is not n_native / window months")

        total = sum(t["n_native"] for t in outcome["tenures"])
        if total != outcome["n_native"]:
            fail(failures, f"{oid}: the tenure windows hold {total} native points, the outcome has {outcome['n_native']} "
                           f"— a point is counted twice or dropped")

        for contrast in outcome["contrasts"]:
            contrasts += 1
            a, b = contrast["a"], contrast["b"]
            if a not in windows or b not in windows:
                fail(failures, f"{oid}: contrast names a tenure with no published deviation")
                continue
            diffs = []
            for span in spans:
                def mean_over(president):
                    lo, hi = windows[president]
                    devs = [row["deviation"] for row in points[span] if lo <= month(row["month"]) <= hi]
                    return sum(devs) / len(devs)
                diffs.append(mean_over(a) - mean_over(b))
            if not close(sum(diffs) / len(diffs), contrast["difference"]):
                fail(failures, f"{oid}: {a} vs {b} difference does not recompute from the two deviations")
            if not (close(contrast["range"][0], min(diffs), 5e-5)
                    and close(contrast["range"][1], max(diffs), 5e-5)):
                fail(failures, f"{oid}: {a} vs {b} range is not the range across spans")
            if f"{sum(diffs) / len(diffs):+.2f}" not in contrast["reading"]:
                fail(failures, f"{oid}: the contrast's reading does not quote its own number")

    for outcome in refused:
        if outcome["n_native"] >= doc["spec"]["min_native"]:
            fail(failures, f"{outcome['id']}: refused at {outcome['n_native']} points, above the declared minimum")
        if not outcome.get("refused", {}).get("detail"):
            fail(failures, f"{outcome['id']}: refused with no detail sentence")

    if doc["counts"]["contrasts"] != contrasts:
        fail(failures, f"the counts block says {doc['counts']['contrasts']} contrasts, the artifact carries {contrasts}")

    if failures:
        print(f"FAILED — {len(failures)} problem(s):")
        for problem in failures[:30]:
            print(f"  - {problem}")
        return 1

    print(f"verified      : {len(described)} outcomes described, {len(refused)} refused at vintage {vintage}")
    print(f"recomputed    : every deviation from the published trend, every tenure mean, every span range, "
          f"every coverage")
    print(f"contrasts     : {contrasts} pairwise differences recomputed from the two deviations")
    print(f"no inference  : no p-value, standard error, interval, effect or significance field is published")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
