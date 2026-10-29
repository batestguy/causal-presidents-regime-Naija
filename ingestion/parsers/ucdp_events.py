"""Parse the landed UCDP GED archive into a state × month security artifact.

Writes:

    data/staging/ucdp_state_month.csv     state × month × item, the table Stage 3 gates and Stage 4 reads
    data/staging/ucdp_parse_report.json   what the parse assumed, excluded and could not attribute

Why this is the artifact Stage 5 said was missing: Family A is a state-level design whose outcome has
to be attributed to a state and a month. The World Bank security series are national and annual
(`homicides` has three observations); ACLED is credential- and licence-blocked (C-13); UCDP's API needs
a token (C-14) but its bulk archive does not. GED carries `adm_1` — the state — and a start date, so
the outcome can be built at exactly the grain the design needs.

Four decisions, each stated because the alternative is defensible:

1. **The month is `date_start`'s month.** GED gives a start and an end date, and an event can span a
   month boundary. Attributing it to the month it began is the convention that matches how the data
   are collected; the alternative (split pro rata) would invent fractional fatalities per month, and
   the count models used downstream require integers. Multi-month events are counted in the report so
   the size of the assumption is visible.

2. **Events without a state go to an explicit `unattributed` scope, not to a state and not nowhere.**
   `where_prec` records how precisely an event was located; 46 Nigeria events (632 fatalities) have no
   `adm_1` at all. Dropping them would make the national series quietly too small; spreading them would
   invent a location. They are carried as their own row so the national total stays complete (the gate
   sums the scopes) while the state panel joins only the 37 units it has.

3. **`Gongola` is unattributed, not mapped forward.** It was split into Adamawa and Taraba in 1991, and
   the archive carries exactly one event for it (1990-09-25) — before this project's study window and
   before either modern state's boundary existed. Mapping it onto a modern state would be a false
   attribution; the report records the label and the event.

4. **A month with no Nigeria event at all is absent, not a row of zeros.** GED only records events with
   at least one fatality, so a state-month with no event inside a month the archive covers for the
   country is a recorded zero — the archive scanned the country and found nothing there. A month with
   no Nigeria event anywhere is different: it is not evidence of zero violence, it is absence of
   records, and it stays a gap so the Stage 3 gap gate can see it. Six such months fall inside the
   1999-2009 window (`1999-08`, `1999-12`, `2000-04`, `2008-10`, `2009-08`, `2009-09`); none after 2009.

Run::

    conda run -p "C:/Users/TOSHIBA/ds-general" python ingestion/parsers/ucdp_events.py
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import sys
import zipfile
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
RAW_ROOT = REPO_ROOT / "data" / "raw" / "ucdp"
STATE_SEED = REPO_ROOT / "dbt" / "seeds" / "raw_state.csv"
OUT_CSV = REPO_ROOT / "data" / "staging" / "ucdp_state_month.csv"
OUT_REPORT = REPO_ROOT / "data" / "staging" / "ucdp_parse_report.json"

COUNTRY = "Nigeria"
UNATTRIBUTED = "unattributed"

# The items carried. `fatalities` is the primary outcome (GED `best`, the centre of the fatality
# estimate); `incidents` is the event count; `fatalities_civilians` is the robustness axis, because a
# transfer that buys counter-insurgency and one that buys civilian protection are different claims.
ITEMS = {
    "fatalities": "count",
    "incidents": "count",
    "fatalities_civilians": "count",
}

# GED labels the states as "<Name> state" and the capital as "Federal Capital territory". Declared
# rather than derived, so a change in the publisher's labelling fails the parse instead of silently
# dropping a state.
LABEL_EXCEPTIONS = {"FCT": "Federal Capital territory"}


def ged_label(state_name: str) -> str:
    return LABEL_EXCEPTIONS.get(state_name, f"{state_name} state")


def latest_archive() -> tuple[Path, str, Path]:
    """The newest landed vintage and its archive path."""
    vintages = sorted(
        (p for p in RAW_ROOT.iterdir() if p.is_dir() and (p / "manifest.json").exists()),
        key=lambda p: p.name,
    )
    if not vintages:
        raise SystemExit(f"no landed UCDP vintage under {RAW_ROOT.relative_to(REPO_ROOT)}")
    vintage_dir = vintages[-1]
    archives = sorted(vintage_dir.glob("ged-*/page-0001.zip"))
    if not archives:
        raise SystemExit(f"no archive in {vintage_dir.relative_to(REPO_ROOT)}")
    return vintage_dir, vintage_dir.name, archives[-1]


def read_events(archive_path: Path) -> tuple[pd.DataFrame, str, str]:
    """Read the Nigeria slice from the archive without extracting it to disk."""
    payload = archive_path.read_bytes()
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        members = [n for n in archive.namelist() if n.lower().endswith(".csv")]
        if not members:
            raise SystemExit("archive contains no CSV")
        with archive.open(members[0]) as handle:
            frame = pd.read_csv(
                handle,
                low_memory=False,
                usecols=[
                    "id", "date_start", "date_end", "country", "adm_1", "adm_2",
                    "best", "deaths_civilians", "type_of_violence", "where_prec",
                    "latitude", "longitude",
                ],
            )
    sha256 = hashlib.sha256(payload).hexdigest()
    return frame[frame["country"] == COUNTRY].copy(), members[0], sha256


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Parse UCDP GED into a state-month artifact.")
    parser.add_argument("--vintage", default=None, help="vintage to parse (default: the latest landed)")
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])

    if args.vintage:
        vintage_dir = RAW_ROOT / args.vintage
        vintage = args.vintage
        archive_path = sorted(vintage_dir.glob("ged-*/page-0001.zip"))[-1]
    else:
        vintage_dir, vintage, archive_path = latest_archive()

    states = pd.read_csv(STATE_SEED)
    events, member, sha256 = read_events(archive_path)
    if events.empty:
        raise SystemExit("the archive carries no Nigeria events")

    label_to_state = {ged_label(row.state_name): row.state_name for row in states.itertuples()}
    state_id_of = dict(zip(states["state_name"], states["state_id"]))

    events["period_month"] = pd.to_datetime(events["date_start"]).dt.to_period("M")
    events["state_name"] = events["adm_1"].map(label_to_state).fillna(UNATTRIBUTED)
    unmapped = sorted(
        str(v) for v in events.loc[events["state_name"] == UNATTRIBUTED, "adm_1"].dropna().unique()
    )

    # Active months: a month the archive covers for the country at all. Every other month is a hole.
    active = sorted(events["period_month"].unique())
    scopes = list(states["state_name"]) + [UNATTRIBUTED]

    # One row per scope x active month, then melted to items: the grid carries no item axis of its own,
    # or the merge would fan each month out three times before the melt did it again (found by the
    # totals: incidents came back at exactly 3x the event count).
    grid = pd.MultiIndex.from_product(
        [scopes, active], names=["state_name", "period_month"]
    ).to_frame(index=False)

    by_state_month = events.groupby(["state_name", "period_month"], sort=False)
    values = pd.DataFrame(
        {
            "fatalities": by_state_month["best"].sum(),
            "incidents": by_state_month.size(),
            "fatalities_civilians": by_state_month["deaths_civilians"].sum(),
        }
    ).reset_index()

    out = grid.merge(values, on=["state_name", "period_month"], how="left")
    out[list(ITEMS)] = out[list(ITEMS)].fillna(0)
    long = out.melt(
        id_vars=["state_name", "period_month"], value_vars=list(ITEMS),
        var_name="item", value_name="value",
    )
    # Nullable integer, not float: the unattributed scope has no state id, and a float id would make
    # `1.0` and `1` different keys in a join while looking identical in a CSV.
    long["state_id"] = long["state_name"].map(state_id_of).astype("Int64")
    long["state_name_published"] = long["state_name"].map(
        lambda s: next((k for k, v in label_to_state.items() if v == s), s)
    )
    long["unit"] = long["item"].map(ITEMS)
    long["period_month"] = long["period_month"].astype(str)
    long["source_dataset_id"] = archive_path.parent.name
    long["source_file"] = archive_path.relative_to(REPO_ROOT).as_posix()
    long["source_sha256"] = sha256
    long["source_location"] = f"{member}#country={COUNTRY}"
    long["vintage"] = vintage
    long = long.sort_values(["item", "state_name", "period_month"])
    long["value"] = long["value"].astype("int64")

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    long[
        ["state_id", "state_name", "state_name_published", "period_month", "item", "value", "unit",
         "source_dataset_id", "source_file", "source_sha256", "source_location", "vintage"]
    ].to_csv(OUT_CSV, index=False, quoting=csv.QUOTE_MINIMAL)

    # Multi-month events: the size of decision 1.
    start = pd.to_datetime(events["date_start"])
    end = pd.to_datetime(events["date_end"])
    multi_month = events[start.dt.to_period("M") != end.dt.to_period("M")]

    span = pd.period_range(min(active), max(active), freq="M")
    inactive = sorted(str(m) for m in set(span) - set(active))
    totals = {item: int(long.loc[long["item"] == item, "value"].sum()) for item in ITEMS}

    # The unattributed sentence is *derived*, not typed: it carried "46 ... 632 fatalities" as a literal
    # through the 25.1 vintage, which is the defect class C-49 names (a number in generated prose that
    # the artifact was free to outgrow). Both halves are counted here so a new release cannot falsify it.
    missing_state = events["adm_1"].isna()
    unmapped_labelled = (events["state_name"] == UNATTRIBUTED) & ~missing_state
    unattributed_note = (
        f"events with no adm_1 ({int(missing_state.sum()):,} in this vintage, "
        f"{int(events.loc[missing_state, 'best'].sum()):,} fatalities)"
    )
    if unmapped:
        n_unmapped = int(unmapped_labelled.sum())
        unattributed_note += (
            f" and the unmapped label(s) {', '.join(unmapped)} "
            f"({n_unmapped:,} {'event' if n_unmapped == 1 else 'events'}, "
            f"{int(events.loc[unmapped_labelled, 'best'].sum()):,} fatalities)"
        )
    unattributed_note += (
        " are carried as the `unattributed` scope so the national sum stays complete; the state panel "
        "joins only the 37 units"
    )

    report = {
        "vintage": vintage,
        "source_file": archive_path.relative_to(REPO_ROOT).as_posix(),
        "source_sha256": sha256,
        "archive_member": member,
        "country": COUNTRY,
        "n_events": int(len(events)),
        "n_events_unattributed": int((events["state_name"] == UNATTRIBUTED).sum()),
        "n_fatalities_unattributed": int(events.loc[events["state_name"] == UNATTRIBUTED, "best"].sum()),
        "unmapped_labels": unmapped,
        "n_multi_month_events": int(len(multi_month)),
        "n_multi_month_fatalities": int(multi_month["best"].sum()),
        "first_month": str(min(active)),
        "last_month": str(max(active)),
        "n_active_months": len(active),
        "inactive_months": inactive,
        "n_scopes": len(scopes),
        "n_rows": int(len(long)),
        "totals": totals,
        "state_label_mapping": {k: v for k, v in sorted(label_to_state.items())},
        "assumptions": {
            "month_assignment": "date_start's month; multi-month events are counted in the month they began",
            "zero_means": (
                "inside an active month, a scope with no event is a recorded zero: GED only records "
                "events with at least one fatality, so the scope was covered and nothing was found"
            ),
            "inactive_months": (
                "a month with no Nigeria event anywhere is absent from the artifact rather than zero — "
                "it is absence of records, not evidence of no violence, and the Stage 3 gap gate sees it"
            ),
            "unattributed": unattributed_note,
        },
    }
    OUT_REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"vintage: {vintage}  sha256={sha256[:12]}")
    print(
        f"events:  {len(events):,}  ({report['n_events_unattributed']} unattributed, "
        f"{len(multi_month)} spanning months)"
    )
    print(f"months:  {report['first_month']} -> {report['last_month']}  active={len(active)}  inactive={len(inactive)}")
    print(f"scopes:  {len(scopes)} (37 units + unattributed)   items: {', '.join(ITEMS)}")
    print(f"totals:  " + ", ".join(f"{k}={v:,}" for k, v in totals.items()))
    print(f"staging: {OUT_CSV.relative_to(REPO_ROOT)}  ({len(long):,} rows)")
    print(f"report:  {OUT_REPORT.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
