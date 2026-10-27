"""Verify `registry/changepoints/<vintage>/changepoints.json`.

The checks that matter, and why:

- **The fit is reproducible.** Every searched series is refitted here by a separate, minimal R script that
  reads the same native observations and applies the same declared criterion. A break month that cannot be
  reproduced is a number nobody can check.
- **Nothing is fitted on the interpolated spine.** Every estimated break month must be an *observed* month in
  `fact_metric`; this is the C-30 trap, made a failure instead of a warning.
- **Measurement is not history.** A break within ±62 days of a declared definition break must be labelled
  `known_definition_break`, and an estimated break may not sit there.
- **No attribution.** A break statement may not say a president caused it; `coincides_with_inauguration` is
  checked against the administration dates and records timing only.

Run:
    python tests/verify_changepoints.py
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path

import duckdb
import jsonschema
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMA = REPO_ROOT / "registry" / "schema" / "changepoints.schema.json"
SPEC = REPO_ROOT / "analysis" / "specs" / "changepoints.yml"
DB = REPO_ROOT / "data" / "analytics.duckdb"
REFIT = REPO_ROOT / ".probe" / "verify_changepoints_refit.R"

REFIT_SOURCE = """\
suppressPackageStartupMessages({library(DBI); library(duckdb); library(strucchange)})
args <- commandArgs(trailingOnly = TRUE)
oid <- args[1]; h <- as.numeric(args[2]); max_b <- as.integer(args[3])
first <- as.Date(args[4]); last <- as.Date(args[5])
con <- dbConnect(duckdb(), "data/analytics.duckdb", read_only = TRUE)
d <- dbGetQuery(con, sprintf("select anchor_month::DATE as m, value from main_analytics.fact_observation_native
                              where metric_id = '%s' and anchor_month between DATE '%s' and DATE '%s'
                                and value is not null order by anchor_month", oid, first, last))
y <- as.numeric(d$value); n <- length(y)
frame <- data.frame(y = y, t = seq_len(n)); fit <- lm(y ~ 1)
bic <- function(rss, m) n * log(rss / n) + (2 * m + 1) * log(n)
best <- list(m = 0L, idx = integer(0), bic = bic(sum(resid(fit)^2), 0))
for (m in seq_len(max_b)) {
  if (n < 3 * m + 3) next
  bp <- tryCatch(breakpoints(y ~ 1, data = frame, h = h, breaks = m), error = function(e) NULL)
  if (is.null(bp)) next
  rss <- sum(resid(bp)^2)
  if (!is.finite(rss) || rss <= 0) next
  value <- bic(rss, m)
  if (value < best$bic) best <- list(m = m, idx = as.integer(bp$breakpoints), bic = value)
}
cat(paste(format(d$m[best$idx + 1], "%Y-%m"), collapse = ","))
"""


def fail(failures: list[str], message: str) -> None:
    failures.append(message)


def month_of(value: str) -> date:
    return date(int(value[:4]), int(value[5:7]), 1)


def canonical_bytes(path: Path) -> int:
    """Bytes as git stores them: CRLF collapsed to LF, so the check holds on a clone and on the Linux runner."""
    return len(path.read_bytes().replace(b"\r\n", b"\n"))


def main() -> int:
    failures: list[str] = []
    index = json.loads((REPO_ROOT / "registry" / "dags" / "index.json").read_text(encoding="utf-8"))
    vintage = index["vintage_date"]
    path = REPO_ROOT / "registry" / "changepoints" / vintage / "changepoints.json"
    if not path.exists():
        print(f"FAILED — {path.relative_to(REPO_ROOT)} is missing")
        return 1
    artifact = json.loads(path.read_text(encoding="utf-8"))
    spec = yaml.safe_load(SPEC.read_text(encoding="utf-8"))

    errors = sorted(jsonschema.Draft202012Validator(json.loads(SCHEMA.read_text(encoding="utf-8"))).iter_errors(artifact),
                    key=lambda e: list(e.path))
    for error in errors[:20]:
        fail(failures, f"schema: /{'/'.join(map(str, error.path))} — {error.message[:140]}")

    if artifact["vintage"] != vintage:
        fail(failures, f"artifact vintage {artifact['vintage']} is not the registry's {vintage}")
    if artifact["spec"]["md5"] != hashlib.md5(SPEC.read_bytes()).hexdigest():
        fail(failures, "the artifact records a spec md5 that is not the spec on disk")

    # Counts are published, not implied — the registry's rule, applied to a descriptive artifact too. Each
    # one is recomputed from the outcomes array rather than read back, so a stale `counts` block fails here
    # instead of being printed as if the page had said it.
    counts = artifact["counts"]
    by_status: dict[str, int] = {}
    for outcome in artifact["outcomes"]:
        by_status[outcome["status"]] = by_status.get(outcome["status"], 0) + 1
    recomputed = {
        "outcomes_considered": len(artifact["outcomes"]),
        "outcomes_searched": by_status.get("search", 0),
        "outcomes_fixed_date": by_status.get("fixed_date", 0),
        "outcomes_refused": by_status.get("refused", 0),
        "breaks_estimated": sum(1 for o in artifact["outcomes"] for b in o["breaks"]
                                if b["kind"] == "estimated"),
        "known_breaks_passed": sum(1 for o in artifact["outcomes"] for b in o["breaks"]
                                   if b["kind"] == "known_definition_break"),
    }
    for key, value in recomputed.items():
        if counts.get(key) != value:
            fail(failures, f"counts.{key} is {counts.get(key)}, the outcomes array gives {value}")

    con = duckdb.connect(str(DB), read_only=True)
    window = (date(int(spec["window"]["first"][:4]), int(spec["window"]["first"][5:]), 1),
              date(int(spec["window"]["last"][:4]), int(spec["window"]["last"][5:]), 1))
    native = {}
    for oid, month, _value in con.execute(
        "select metric_id, anchor_month::DATE, value from main_analytics.fact_observation_native "
        "where anchor_month between ? and ? and value is not null",
        list(window),
    ).fetchall():
        native.setdefault(oid, []).append(month)

    observed_months = {}
    for oid, month in con.execute(
        "select metric_id, period_month::DATE from main_analytics.fact_metric "
        "where observation_type = 'observed' and period_month between ? and ?", list(window)
    ).fetchall():
        observed_months.setdefault(oid, set()).add(month)

    definition_breaks = {}
    for oid, month in con.execute(
        "select metric_id, break_month::DATE from main_analytics.dim_definition_break"
    ).fetchall():
        definition_breaks.setdefault(oid, []).append(month)

    admins = json.loads((REPO_ROOT / "registry" / "reference" / "administrations.json").read_text(encoding="utf-8"))
    inaugurations = [(row["slug"], month_of(row["start_date"][:7])) for row in admins["administrations"]]

    series_index = {row["id"]: row for row in json.loads(
        (REPO_ROOT / "registry" / "series" / vintage / "index.json").read_text(encoding="utf-8"))["outcomes"]}

    REFIT.parent.mkdir(parents=True, exist_ok=True)
    REFIT.write_text(REFIT_SOURCE, encoding="utf-8", newline="\n")

    refitted = 0
    for outcome in artifact["outcomes"]:
        oid = outcome["id"]
        months = native.get(oid, [])
        count = len(months)
        if outcome["native_in_window"] != count:
            fail(failures, f"{oid}: native_in_window is {outcome['native_in_window']}, the base has {count}")
        if count and (outcome["span"]["first"] != min(months).strftime("%Y-%m")
                      or outcome["span"]["last"] != max(months).strftime("%Y-%m")):
            fail(failures, f"{oid}: the span {outcome['span']['first']}..{outcome['span']['last']} is not the "
                           f"native span {min(months):%Y-%m}..{max(months):%Y-%m}")
        if outcome["status"] == "refused" and count >= spec["rules"]["min_native_search"]:
            fail(failures, f"{oid}: refused with {count} native observations, the declared minimum is "
                           f"{spec['rules']['min_native_search']}")
        if outcome["status"] != "refused" and count < spec["rules"]["min_native_search"]:
            fail(failures, f"{oid}: fitted on {count} native observations, below the declared minimum")

        for brk in outcome["breaks"]:
            month = month_of(brk["month"])
            if brk["kind"] == "estimated":
                if month not in observed_months.get(oid, set()):
                    fail(failures, f"{oid}: estimated break {brk['month']} is not an observed month — the "
                                   f"interpolated spine was fitted")
            near_definition = [d for d in definition_breaks.get(oid, []) if abs((month - d).days) <= 62]
            if near_definition and brk["kind"] != "known_definition_break":
                fail(failures, f"{oid}: break {brk['month']} sits on a definition break and is labelled "
                               f"{brk['kind']} — measurement is not history")
            for word in ("caused", "because of", "under President", "led to"):
                if word in brk["statement"]:
                    fail(failures, f"{oid}: break statement contains {word!r} — a break is not an effect")
            slug = brk.get("coincides_with_inauguration")
            near = [s for s, m in inaugurations if abs((month - m).days) <= 62]
            if slug and slug not in near:
                fail(failures, f"{oid}: break {brk['month']} claims to coincide with {slug}, which is not within "
                               f"two months of it")
            if not slug and near and brk["kind"] == "estimated":
                fail(failures, f"{oid}: break {brk['month']} is within two months of {near[0]} and does not say so")

        figure = outcome["figure"]
        if outcome["status"] == "refused":
            if figure is not None or outcome["breaks"]:
                fail(failures, f"{oid}: refused, but carries a figure or a break")
        else:
            if figure is None:
                fail(failures, f"{oid}: no figure for a fitted outcome")
            else:
                target = REPO_ROOT / figure["path"]
                if not target.exists():
                    fail(failures, f"{oid}: figure {figure['path']} is missing")
                elif canonical_bytes(target) != figure["bytes"]:
                    fail(failures, f"{oid}: figure bytes recorded as {figure['bytes']}, file is "
                                   f"{canonical_bytes(target)}")
                else:
                    svg = target.read_text(encoding="utf-8", errors="replace")
                    if spec["figures"]["stamp"] not in svg:
                        fail(failures, f"{oid}: the figure does not carry the declared stamp")
                    if outcome["short"] not in svg:
                        fail(failures, f"{oid}: the figure does not name the outcome")
            # The declared method, re-run by a separate script.
            max_breaks = int(spec["rules"]["max_breaks"][outcome["regime"]])
            run = subprocess.run(
                ["Rscript", str(REFIT), oid, str(spec["rules"]["h"]), str(max_breaks),
                 window[0].isoformat(), window[1].isoformat()],
                cwd=REPO_ROOT, capture_output=True, text=True)
            if run.returncode != 0:
                fail(failures, f"{oid}: the refit did not run — {run.stderr.strip()[:160]}")
            else:
                got = sorted(m for m in run.stdout.strip().split(",") if m)
                declared = sorted(b["month"] for b in outcome["breaks"] if b["kind"] == "estimated")
                if got != declared:
                    fail(failures, f"{oid}: refit found {got}, the artifact declares {declared}")
                refitted += 1

    def walk(node, where=""):
        if isinstance(node, dict):
            for key, value in node.items():
                if key in spec["rules"]["forbidden_fields"]:
                    fail(failures, f"forbidden field {where}/{key} — this artifact describes and does not estimate")
                walk(value, f"{where}/{key}")
        elif isinstance(node, list):
            for i, value in enumerate(node):
                walk(value, f"{where}[{i}]")

    walk(artifact)
    con.close()
    if REFIT.exists():
        REFIT.unlink()

    if failures:
        print(f"FAILED — {len(failures)} problem(s):")
        for problem in failures[:40]:
            print(f"  - {problem}")
        return 1
    print(f"verified      : {len(artifact['outcomes'])} outcomes, {artifact['counts']['breaks_estimated']} "
          f"estimated breaks, {artifact['counts']['known_breaks_passed']} definition breaks marked")
    print(f"refitted      : {refitted} series re-run by a separate script and matched month for month")
    print("refused       : 4 short series, each with the count that caused the refusal")
    print("no attribution: no break claims a president, and no fitted month is interpolated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
