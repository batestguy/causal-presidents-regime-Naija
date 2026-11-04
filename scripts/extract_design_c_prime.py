"""P1 - extract the treated/donor annual panel for Design C' (matrix-completion counterfactual).

Read-only. Reads `analysis/specs/design_c_prime.yml`, carries the windows from `design_c.yml` back to
`diagnostics.yml` rather than retyping a treatment date, pulls Nigeria from the **native** observations and
the donors from the donor panel, and writes one exploratory table plus a manifest under `.inspect/`.
No fit happens here and nothing outside `.inspect/` is written.

Run with the causal env (it is the one with duckdb and yaml):
    C:\\Users\\TOSHIBA\\miniconda3\\envs\\causality-handbook\\python.exe scripts/extract_design_c_prime.py
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import date
from pathlib import Path

import duckdb
import yaml

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "analysis" / "specs" / "design_c_prime.yml"
OUT_DIR = ROOT / ".inspect"


def load_spec() -> dict:
    return yaml.safe_load(SPEC.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def declared_windows(spec: dict) -> list[dict]:
    """design_c_prime -> design_c -> diagnostics, with the 1-July year rule applied exactly once."""
    design_c = yaml.safe_load((ROOT / spec["windows"]["source"]).read_text(encoding="utf-8"))
    diagnostics = yaml.safe_load((ROOT / design_c["windows"]["source"]).read_text(encoding="utf-8"))
    wanted = set(design_c["windows"]["ids"])
    first, last = design_c["windows"]["first_year"], design_c["windows"]["last_year"]

    out = []
    for window in diagnostics["windows"]["candidate_treated_windows"]:
        if window["id"] not in wanted:
            continue
        start = window["from"] if isinstance(window["from"], date) else date.fromisoformat(window["from"])
        end = (
            date(last, 12, 31)
            if not window.get("to")
            else (window["to"] if isinstance(window["to"], date) else date.fromisoformat(window["to"]))
        )
        years = [
            y for y in range(first, last + 1) if start <= date(y, 7, 1) <= end
        ]
        post = years
        pre = list(range(first, post[0])) if post else []
        out.append(
            {
                "id": window["id"],
                "first_post_year": post[0] if post else None,
                "last_post_year": post[-1] if post else None,
                "pre_years": len(pre),
                "post_years": len(post),
            }
        )
    return out


def check_against_published(windows: list[dict], spec: dict) -> None:
    """The derived years must equal the frozen Design C artifact's, or a window has drifted."""
    artifact = ROOT / "registry" / "design_c" / "2026-11-01" / "design_c.json"
    if not artifact.exists():
        print("  (design_c artifact absent; year check skipped)")
        return
    published = json.loads(artifact.read_text(encoding="utf-8"))
    u5mr = next(o for o in published["outcomes"] if o["outcome"] == "u5mr")
    by_id = {w["id"]: w for w in u5mr["windows"]}
    mismatches = []
    for w in windows:
        got = by_id.get(w["id"])
        if got is None or got.get("first_year") is None:
            continue  # a window the published artifact refused carries no years: nothing to compare
        if (got.get("first_year"), got.get("last_year")) != (
            w["first_post_year"],
            w["last_post_year"],
        ):
            mismatches.append(
                f"{w['id']}: derived {w['first_post_year']}-{w['last_post_year']}, "
                f"published {got.get('first_year')}-{got.get('last_year')}"
            )
    if mismatches:
        raise SystemExit("window drift against the frozen artifact: " + "; ".join(mismatches))
    print(f"  year check: all {len(windows)} windows match registry/design_c/2026-11-01")


def extract(spec: dict, outcome: str, con: duckdb.DuckDBPyConnection) -> tuple[list[dict], dict]:
    first = spec["input"]["years"]["first"]
    last = spec["input"]["years"]["last"]

    native = con.execute(
        """
        select year(period_start_date) as year, value
        from main_analytics.fact_observation_native
        where metric_id = ? and scope = ? and value is not null
        order by 1
        """,
        [outcome, spec["input"]["treated_scope"]],
    ).fetchall()

    donors = con.execute(
        """
        select country_iso3, period_year, value
        from main_analytics.fact_donor_panel
        where metric_id = ? and not is_treated_unit and value is not null
        order by 1, 2
        """,
        [outcome],
    ).fetchall()

    rows = [
        {"country": "NGA", "year": y, "value": v, "role": "treated"}
        for y, v in native
        if first <= y <= last
    ]
    rows += [
        {"country": c, "year": y, "value": v, "role": "donor"}
        for c, y, v in donors
        if first <= y <= last
    ]
    return rows, {
        "native_rows": len([r for r in rows if r["role"] == "treated"]),
        "donor_rows": len([r for r in rows if r["role"] == "donor"]),
        "donor_units": len({r["country"] for r in rows if r["role"] == "donor"}),
    }


def coverage(panel: list[dict], windows: list[dict], spec: dict) -> list[dict]:
    values = {(r["country"], r["year"]) for r in panel if r["role"] == "donor"}
    donors = sorted({r["country"] for r in panel if r["role"] == "donor"})
    report = []
    for w in windows:
        if w["first_post_year"] is None:
            report.append({**w, "mc_donors": 0, "balanced_donors": 0, "status": "refused_no_post_year"})
            continue
        pre = set(range(spec["input"]["years"]["first"], w["first_post_year"]))
        full = set(range(spec["input"]["years"]["first"], w["last_post_year"] + 1))
        mc = [d for d in donors if pre <= {y for c, y in values if c == d}]
        balanced = [d for d in donors if full <= {y for c, y in values if c == d}]
        minimum = spec["input"]["donor_rule"]["minimum_donors"]
        report.append(
            {
                **w,
                "mc_donors": len(mc),
                "balanced_donors": len(balanced),
                "status": "ok" if min(len(mc), len(balanced)) >= minimum else "too_few_donors",
            }
        )
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--outcome", default="u5mr")
    args = parser.parse_args()

    spec = load_spec()
    con = duckdb.connect(str(ROOT / spec["input"]["database"]), read_only=True)

    print(f"Design C' extraction, outcome={args.outcome}")
    windows = declared_windows(spec)
    check_against_published(windows, spec)

    panel, counts = extract(spec, args.outcome, con)
    report = coverage(panel, windows, spec)

    OUT_DIR.mkdir(exist_ok=True)
    panel_path = OUT_DIR / f"design_c_prime_{args.outcome}_panel.csv"
    with panel_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["country", "year", "value", "role"])
        writer.writeheader()
        writer.writerows(panel)

    print(f"  Nigeria native rows {counts['native_rows']} ({spec['input']['years']['first']}-{spec['input']['years']['last']})")
    print(f"  donor rows {counts['donor_rows']} across {counts['donor_units']} countries")
    print("  window coverage: id / post years / matrix-completion donors / balanced donors")
    for w in report:
        print(
            f"    {w['id']:<9} {str(w['first_post_year']):>4}-{str(w['last_post_year']):<4} "
            f"pre={w['pre_years']:>2} post={w['post_years']:>2} "
            f"mc={w['mc_donors']:>3} balanced={w['balanced_donors']:>3}  {w['status']}"
        )

    manifest = {
        "phase": "P1",
        "outcome": args.outcome,
        "spec": str(SPEC.relative_to(ROOT)).replace("\\", "/"),
        "spec_sha256": sha256(SPEC),
        "database": spec["input"]["database"],
        "treated_series": "fact_observation_native (scope = 'NGA')",
        "donor_rule": spec["input"]["donor_rule"],
        "counts": counts,
        "windows": report,
        "panel": str(panel_path.relative_to(ROOT)).replace("\\", "/"),
    }
    manifest_path = OUT_DIR / f"design_c_prime_{args.outcome}_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"  wrote {panel_path.relative_to(ROOT)} and {manifest_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
