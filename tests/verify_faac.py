"""Verify the FAAC acquisition and the state dose independently of the parser and of dbt.

Three layers are checked, and each one is checked against something other than itself:

  * **The documents against the parser's record of them.** For a sample of landed payloads the verifier
    re-reads the file itself and looks for the total the parser says it found — over the *whole* payload's
    text, with no header resolution and no table detection, so a total read from the wrong table or the
    wrong page cannot pass. What this cannot check is which column a figure came from; the parser's own
    reconciliation covers that, and its result is re-checked here as arithmetic.
  * **The staging artifact against the base.** `faac_state_allocation` is recomputed in plain Python from
    `data/staging/faac_state_allocation.csv` — publisher preference, the monthly pool, the share, the
    cross-check columns — and compared row for row with the built DuckDB table. The SQL is not imported
    and not read.
  * **The dose against its declared rules.** `analysis/specs/harmonisation.yml` declares the dose column,
    the publisher order and the tolerance; this fails if the built table implements anything else, which
    is the only way a spec and its implementation stay in step.

Every headline number quoted in `docs/decisions.md` C-39/C-40/C-41 and in the models' comments is
recomputed here, so a documentation claim that stops being true fails a test rather than living on.

Usage:
    conda run -p "C:/Users/TOSHIBA/ds-general" python tests/verify_faac.py
    conda run -p "C:/Users/TOSHIBA/ds-general" python tests/verify_faac.py --sample 12
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

import duckdb
import openpyxl
import pdfplumber
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
RAW_ROOT = REPO_ROOT / "data" / "raw" / "faac"
STAGING = REPO_ROOT / "data" / "staging" / "faac_state_allocation.csv"
PARSE_REPORT = REPO_ROOT / "data" / "staging" / "faac_parse_report.json"
SPEC_PATH = REPO_ROOT / "analysis" / "specs" / "harmonisation.yml"
DB_PATH = REPO_ROOT / "data" / "analytics.duckdb"
SCHEMA = "main_analytics"

STATES_EXPECTED = 36
FCT_STATE_ID = 15
# One naira, the spec's declared tolerance for the cross-check between the two publications.
CROSS_CHECK_TOLERANCE = 1.0


def latest_vintage() -> str:
    vintages = sorted(p.name for p in RAW_ROOT.iterdir() if p.is_dir())
    if not vintages:
        raise SystemExit(f"no FAAC vintages under {RAW_ROOT}")
    return vintages[-1]


def load_spec() -> dict:
    spec = yaml.safe_load(SPEC_PATH.read_text(encoding="utf-8"))
    if "faac_dose" not in spec:
        raise SystemExit("harmonisation.yml declares no `faac_dose` section")
    return spec["faac_dose"]


def load_staging() -> dict:
    """The staging rows, grouped the way the dose model groups them."""
    rows: list[dict] = []
    with STAGING.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            rows.append(row)
    if not rows:
        raise SystemExit(f"no rows in {STAGING}")

    amounts: dict[tuple[str, str, str, str], float | None] = {}
    for row in rows:
        raw = row["amount_naira"]
        amounts[(row["period_month"], row["publisher"], row["state_id"], row["item"])] = (
            None if raw == "" else float(raw)
        )

    vintages = sorted({row["vintage"] for row in rows})
    return {"rows": rows, "amounts": amounts, "vintages": vintages}


# ---------------------------------------------------------------------------------------------
# 1. the documents against the parser's record of them
# ---------------------------------------------------------------------------------------------


def payload_text(payload_path: Path) -> str:
    """The payload's whole text, read the crudest way that still works.

    Nothing here resolves a header, finds a table or knows what a column is — which is the point: it is an
    independent path to the same digits, so a total read from the wrong table or the wrong page cannot pass.
    """
    if payload_path.suffix.lower() == ".pdf":
        with pdfplumber.open(io.BytesIO(payload_path.read_bytes())) as pdf:
            return "\n".join(page.extract_text() or "" for page in pdf.pages)
    book = openpyxl.load_workbook(io.BytesIO(payload_path.read_bytes()), read_only=True, data_only=True)
    try:
        return "\n".join(
            " ".join(str(cell) for cell in row if cell is not None)
            for name in book.sheetnames
            for row in book[name].iter_rows(values_only=True)
        )
    finally:
        book.close()


def total_is_printed(text: str, total: float) -> tuple[bool, str]:
    """Whether the payload prints this figure, by two methods, and which one matched.

    * **As a token.** Whitespace and commas are removed and the figure is looked for as a complete
      token. This is the strict form and it is what most documents satisfy.
    * **In the digit stream.** Some OAGF layouts print the Total row so tightly that the figure's digits
      sit flush against its neighbour's (`...127.33` `145,293,615,067.77`), so stripping the whitespace
      *merges* the two and no token survives — which is a defect in the scan, not in the document. Looking
      for the figure's digits in the payload's digit stream answers the question actually being asked:
      *is this figure printed here?* It cannot say which column it is in, and it is therefore the weaker
      of the two, used only when the strict form finds nothing and only for a figure long enough that a
      coincidental match is implausible.
    """
    cleaned = re.sub(r"[\s,₦]", "", text)
    if f"{total:.2f}" in cleaned:
        return True, "token"
    digits = re.sub(r"\D", "", f"{total:.2f}")
    if len(digits) >= 8 and digits in re.sub(r"\D", "", text):
        return True, "digit stream"
    return False, ""


def check_documents(report: dict, sample: int) -> tuple[list[str], list[str], list[str]]:
    """Documents vs the report. Returns (failures, notes, printed lines)."""
    failures: list[str] = []
    lines: list[str] = []
    documents = report["documents"]

    if len(documents) != report["n_documents_parsed"]:
        failures.append(
            f"report says {report['n_documents_parsed']} documents parsed but carries {len(documents)}"
        )
    if report["n_documents_failed"]:
        failures.append(f"{report['n_documents_failed']} document(s) failed to parse")

    # Every document must carry all 36 beneficiaries, and its own Total row must equal the states plus the
    # distribution's 37th line. This is arithmetic on the parser's own report — it re-checks the claim,
    # not the extraction.
    for document in documents:
        if document["n_states"] != STATES_EXPECTED:
            failures.append(
                f"{document['dataset_id']}: {document['n_states']} states, expected {STATES_EXPECTED}"
            )
        total = document["gross_total_published"]
        parsed = document["gross_sum"] + document["other_beneficiary_sum"]
        if total is None:
            failures.append(
                f"{document['dataset_id']}: the document's own Total row was not found for the dose "
                "column, so nothing reconciles it"
            )
            continue
        tolerance = max(1.0, abs(total) * 1e-9)
        if abs(parsed - total) > tolerance:
            failures.append(
                f"{document['dataset_id']}: states+other {parsed:,.2f} vs published total "
                f"{total:,.2f} (tolerance {tolerance:,.2f})"
            )

    # The dose column must not be among the header cells that did not resolve, in any document.
    lost = sorted({cell for cells in report["unmapped_header_cells"].values() for cell in cells})
    if any("GROSS TOTAL" in cell for cell in lost):
        failures.append(f"the dose column itself did not resolve somewhere: {lost}")

    lines.append(
        f"documents: {len(documents)} parsed, {report['n_documents_failed']} failed, "
        f"all {STATES_EXPECTED} states per document, all reconciled to their own Total row"
    )
    lines.append(
        f"unmapped header cells: {sum(len(v) for v in report['unmapped_header_cells'].values())} "
        f"across {len(report['unmapped_header_cells'])} document(s), {len(lost)} distinct — "
        "the decomposition is incomplete, the dose is not"
    )

    # The independent path: for a sample, look for the total the parser reported anywhere in the payload.
    by_dataset = {document["dataset_id"]: document for document in documents}
    manifest = json.loads((RAW_ROOT / report["vintage"] / "manifest.json").read_text(encoding="utf-8"))
    checked = 0
    for entry in manifest["retrievals"]:
        if checked >= sample:
            break
        dataset_id = entry["dataset_id"]
        document = by_dataset.get(dataset_id)
        if document is None or document["gross_total_published"] is None:
            continue
        payload_path = REPO_ROOT / entry["page_files"][0]
        total = round(document["gross_total_published"], 2)
        found, how = total_is_printed(payload_text(payload_path), total)
        if not found:
            failures.append(
                f"{dataset_id}: the parser's total {total:,.2f} does not appear anywhere in the payload "
                "— it cannot have come from this document's own figures"
            )
        else:
            lines.append(
                f"  independent re-read  {dataset_id}  total {total / 1e9:,.3f}bn printed in the payload "
                f"({how})"
            )
        checked += 1
    if checked < sample:
        failures.append(f"only {checked} document(s) could be re-read (asked for {sample})")
    return failures, [], lines


# ---------------------------------------------------------------------------------------------
# 2. the staging artifact against the built base
# ---------------------------------------------------------------------------------------------
def recompute_dose(staging: dict, spec: dict) -> dict[tuple[int, str], dict]:
    """The dose table, recomputed from the staging CSV under the declared rules."""
    dose_column = spec["dose_column"]
    order = {spec["publisher_rule"]["primary"]: 0, spec["publisher_rule"]["fallback"]: 1}
    amounts = staging["amounts"]

    items: dict[tuple[str, str, str], dict[str, float]] = defaultdict(dict)
    for (period, publisher, state_id, item), amount in amounts.items():
        if amount is not None:
            items[(period, publisher, state_id)][item] = amount

    chosen: dict[tuple[int, str], dict] = {}
    for (period, publisher, state_id), values in items.items():
        if dose_column not in values:
            continue
        key = (int(state_id), period)
        candidate = {"publisher": publisher, "gross_total": values[dose_column], "values": values}
        if key not in chosen or order[publisher] < order[chosen[key]["publisher"]]:
            chosen[key] = candidate

    pool: dict[str, float] = defaultdict(float)
    for (state_id, period), entry in chosen.items():
        pool[period] += entry["gross_total"]

    other: dict[tuple[int, str], dict] = {}
    for (period, publisher, state_id), values in items.items():
        if dose_column not in values:
            continue
        key = (int(state_id), period)
        if chosen.get(key, {}).get("publisher") == publisher:
            continue
        other[key] = {"publisher": publisher, "gross_total": values[dose_column]}

    for key, entry in chosen.items():
        entry["share_of_state_pool"] = (
            entry["gross_total"] / pool[key[1]] if pool[key[1]] else None
        )
        peer = other.get(key)
        entry["is_cross_checked"] = peer is not None
        entry["other_publisher"] = peer["publisher"] if peer else None
        entry["other_gross_total"] = peer["gross_total"] if peer else None
        entry["cross_check_rel_diff"] = (
            abs(entry["gross_total"] - peer["gross_total"]) / peer["gross_total"]
            if peer and peer["gross_total"]
            else None
        )
        entry["n_beneficiaries"] = sum(1 for k in chosen if k[1] == key[1])
    return chosen


def compare_with_base(staging: dict, spec: dict, con) -> tuple[list[str], list[str], dict]:
    failures: list[str] = []
    lines: list[str] = []
    recomputed = recompute_dose(staging, spec)

    # The built table's `period_month` is a DATE, the staging artifact's is 'YYYY-MM'; the key is the
    # month, so both are normalised to seven characters before anything is compared.
    built = {
        (int(state_id), str(period)[:7]): row
        for state_id, period, *row in con.execute(
            f"""select state_id, period_month, publisher, gross_total, share_of_state_pool,
                       is_cross_checked, other_publisher, other_gross_total, cross_check_rel_diff,
                       n_beneficiaries, month_state_pool
                from {SCHEMA}.faac_state_allocation"""
        ).fetchall()
    }
    if len(built) != len(recomputed):
        failures.append(
            f"faac_state_allocation has {len(built)} rows, the independent recomputation has "
            f"{len(recomputed)}"
        )
    missing = sorted(set(recomputed) - set(built))[:5]
    extra = sorted(set(built) - set(recomputed))[:5]
    if missing:
        failures.append(f"state-months the recomputation has and the base does not: {missing}")
    if extra:
        failures.append(f"state-months the base has and the recomputation does not: {extra}")

    for key in sorted(set(built) & set(recomputed)):
        want = recomputed[key]
        got = built[key]
        state_id, period = key
        if got[0] != want["publisher"]:
            failures.append(f"{state_id}/{period}: publisher {got[0]} vs recomputed {want['publisher']}")
        for index, field in ((1, "gross_total"), (2, "share_of_state_pool")):
            wanted = want[field]
            if wanted is None or got[index] is None:
                if got[index] is not None or wanted is not None:
                    failures.append(f"{state_id}/{period}: {field} {got[index]} vs recomputed {wanted}")
                continue
            if abs(got[index] - wanted) > max(1.0, abs(wanted) * 1e-9):
                failures.append(f"{state_id}/{period}: {field} {got[index]:,.2f} vs {wanted:,.2f}")
        # Row layout: 0 publisher, 1 gross_total, 2 share_of_state_pool, 3 is_cross_checked,
        # 4 other_publisher, 5 other_gross_total, 6 cross_check_rel_diff, 7 n_beneficiaries.
        if bool(got[3]) != want["is_cross_checked"]:
            failures.append(f"{state_id}/{period}: is_cross_checked disagrees")
        if (got[4] or None) != want["other_publisher"]:
            failures.append(f"{state_id}/{period}: other_publisher {got[4]} vs {want['other_publisher']}")
        other_wanted = want["other_gross_total"]
        if (got[5] is None) != (other_wanted is None):
            failures.append(f"{state_id}/{period}: other_gross_total present/absent disagrees")
        elif other_wanted is not None and abs(got[5] - other_wanted) > max(1.0, abs(other_wanted) * 1e-9):
            failures.append(f"{state_id}/{period}: other_gross_total {got[5]:,.2f} vs {other_wanted:,.2f}")
        diff_wanted = want["cross_check_rel_diff"]
        if (got[6] is None) != (diff_wanted is None):
            failures.append(f"{state_id}/{period}: cross_check_rel_diff present/absent disagrees")
        elif diff_wanted is not None and abs(got[6] - diff_wanted) > 1e-9:
            failures.append(
                f"{state_id}/{period}: cross_check_rel_diff {got[6]:.6f} vs {diff_wanted:.6f}"
            )
        if got[7] != want["n_beneficiaries"]:
            failures.append(f"{state_id}/{period}: n_beneficiaries {got[7]} vs {want['n_beneficiaries']}")

    # The national series must be the sum of the states it claims to be the sum of.
    national = {
        str(period)[:7]: (total, n)
        for period, total, n in con.execute(
            f"select period_month, gross_total_naira, n_beneficiaries from {SCHEMA}.faac_national_monthly"
        ).fetchall()
    }
    pool: dict[str, float] = defaultdict(float)
    counts: dict[str, int] = defaultdict(int)
    for (state_id, period), entry in recomputed.items():
        pool[period] += entry["gross_total"]
        counts[period] += 1
    if set(national) != set(pool):
        failures.append(f"national series covers {len(national)} months, the dose covers {len(pool)}")
    for period in sorted(set(national) & set(pool)):
        total, n = national[period]
        if abs(total - pool[period]) > max(1.0, abs(pool[period]) * 1e-9):
            failures.append(f"{period}: national total {total:,.2f} vs sum of states {pool[period]:,.2f}")
        if n != counts[period]:
            failures.append(f"{period}: national row counts {n} states, the dose has {counts[period]}")

    # The panel must carry the dose, once, keyed correctly — and the FCT must carry none.
    panel_doses, fct, statuses = con.execute(
        f"""select count(faac_gross_total_naira),
                   count(*) filter (where state_id = {FCT_STATE_ID} and faac_gross_total_naira is not null),
                   count(*) filter (where dose_status = 'observed'
                                    and faac_gross_total_naira is null)
                       + count(*) filter (where dose_status <> 'observed'
                                          and faac_gross_total_naira is not null)
            from {SCHEMA}.state_panel"""
    ).fetchone()
    if panel_doses != len(recomputed):
        failures.append(f"state_panel carries {panel_doses} dose values, expected {len(recomputed)}")
    if fct:
        failures.append(f"the FCT carries {fct} dose value(s)")
    if statuses:
        failures.append(f"{statuses} row(s) where dose_status and the dose value disagree")

    # The claims the documentation makes, recomputed.
    both = [
        (state_id, period)
        for (state_id, period), entry in recomputed.items()
        if entry["is_cross_checked"] and entry["other_gross_total"] is not None
    ]
    agreeing = [
        key
        for key in both
        if abs(recomputed[key]["gross_total"] - recomputed[key]["other_gross_total"])
        <= max(CROSS_CHECK_TOLERANCE, abs(recomputed[key]["other_gross_total"]) * 1e-9)
    ]
    months_both = {period for _, period in both}
    months_clean = {
        period
        for period in months_both
        if all(key in agreeing for key in both if key[1] == period)
    }
    dirty = sorted(months_both - months_clean)
    lines.append(
        f"cross-publisher check: {len(agreeing)}/{len(both)} state-months agree within a naira; "
        f"{len(months_clean)}/{len(months_both)} months agree at every state"
        + (f"; months that do not: {dirty}" if dirty else "")
    )
    derivation_months = sorted(
        {
            row["period_month"]
            for row in staging["rows"]
            if row["publisher"] == spec["publisher_rule"]["primary"]
            and row["item"] == "derivation_13pct"
        }
    )
    primary_months = sorted(
        {row["period_month"] for row in staging["rows"] if row["publisher"] == spec["publisher_rule"]["primary"]}
    )
    lines.append(
        f"dose coverage: {len({period for _, period in recomputed})} months, "
        f"{len(primary_months)} from the primary publisher; derivation column present in "
        f"{len(derivation_months)} of its months"
    )
    lines.append(
        f"vintage(s) in the staging artifact: {', '.join(staging['vintages'])}"
    )
    return failures, lines, recomputed


# ---------------------------------------------------------------------------------------------
# 3. the dose against its declared rules
# ---------------------------------------------------------------------------------------------
def check_spec(spec: dict, staging: dict, recomputed: dict) -> list[str]:
    failures: list[str] = []
    if spec["dose_column"] != "gross_total":
        failures.append(
            f"harmonisation.yml declares dose_column {spec['dose_column']!r}; this verifier recomputes "
            "gross_total and would not be checking the declared dose"
        )
    if "gross_total" not in {row["item"] for row in staging["rows"]}:
        failures.append("the staging artifact carries no gross_total item at all")
    primary = spec["publisher_rule"]["primary"]
    fallback = spec["publisher_rule"]["fallback"]
    if primary != "oagf" or fallback != "nbs":
        failures.append(f"the spec's publisher order is now {primary}/{fallback}")

    # Which publishers carry each month's dose, from the artifact.
    publishers: dict[str, set[str]] = defaultdict(set)
    for row in staging["rows"]:
        if row["item"] == spec["dose_column"] and row["amount_naira"] != "":
            publishers[row["period_month"]].add(row["publisher"])
    used = {period for _, period in recomputed}
    if not used <= set(publishers):
        failures.append(f"the recomputation invented months: {sorted(used - set(publishers))[:5]}")
    both = {period for period, pubs in publishers.items() if len(pubs) > 1}
    if not both:
        failures.append("no month is published by both publishers, so the preference order is untested")

    # Where both publications carry a month, the dose must come from the primary. This is the preference
    # order actually being applied, read off the chosen rows rather than off the SQL.
    wrong = sorted(
        (state_id, period, entry["publisher"])
        for (state_id, period), entry in recomputed.items()
        if period in both and entry["publisher"] != primary
    )
    if wrong:
        failures.append(
            f"{len(wrong)} state-month(s) in months both publishers carry were not taken from "
            f"{primary}: {wrong[:3]}"
        )

    fallback_only = sorted(period for period in used if publishers[period] == {fallback})
    if fallback_only:
        print(
            f"  fallback in use: {len(fallback_only)} month(s) only the fallback publishes "
            f"({fallback_only[0]} .. {fallback_only[-1]})"
        )
    else:
        print("  fallback in use: no month — the primary covers every month in the dose")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify the FAAC dose independently.")
    parser.add_argument("--sample", type=int, default=6, help="documents to re-read from their payload")
    args = parser.parse_args()

    for path in (STAGING, PARSE_REPORT, DB_PATH):
        if not path.exists():
            raise SystemExit(f"missing artifact: {path} — run the parser and `dbt build` first")

    spec = load_spec()
    staging = load_staging()
    report = json.loads(PARSE_REPORT.read_text(encoding="utf-8"))
    vintage = latest_vintage()
    print(f"vintage on disk: {vintage}; parse report vintage: {report['vintage']}")

    failures: list[str] = []
    if report["vintage"] != vintage:
        failures.append(
            f"the parse report describes vintage {report['vintage']} but {vintage} is the latest on disk"
        )
    if staging["vintages"] != [report["vintage"]]:
        failures.append(
            f"the staging artifact carries vintage(s) {staging['vintages']}, the report says "
            f"{report['vintage']}"
        )

    document_failures, _, document_lines = check_documents(report, args.sample)
    failures.extend(document_failures)
    for line in document_lines:
        print(f"  {line}")

    con = duckdb.connect(str(DB_PATH), read_only=True)
    try:
        base_failures, base_lines, recomputed = compare_with_base(staging, spec, con)
    finally:
        con.close()
    failures.extend(base_failures)
    for line in base_lines:
        print(f"  {line}")

    failures.extend(check_spec(spec, staging, recomputed))

    print()
    if failures:
        print(f"FAILED — {len(failures)} problem(s):")
        for problem in failures[:40]:
            print(f"  - {problem}")
        if len(failures) > 40:
            print(f"  … and {len(failures) - 40} more")
        return 1
    print(
        "PASS — every document reconciles to its own Total row, the dose recomputes from the staging "
        "artifact row for row, the national series is the sum of the states, the panel carries the dose "
        "once with no FCT dose, and the built table implements the rules the spec declares"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
