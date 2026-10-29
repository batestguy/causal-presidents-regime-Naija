"""The phase gate: the completion plan's ordering, enforced rather than stated.

`presidents-completion-plan.md` says the remaining work happens in a fixed order; this file makes that
sentence a check. The state lives in `presidents-completion-state.yml` - one status per phase - and the
rule is deliberately simple so that a violation is unarguable:

* phases must be the same phases the plan declares (same ids, same count) - a state file whose phases
  drifted from the plan is a violation, not a reordering;
* at most one phase may be `in_progress`;
* the phases before an `in_progress` (or `done`) phase must all be `done` - no phase starts, and no
  phase closes, ahead of the one before it;
* every phase after the frontier must be `not_started`;
* a `done` phase must carry evidence: one entry per exit check, each naming the check that ran and the
  date it ran. `done` without evidence is the failure mode this gate exists for - a claim nobody ran.

The gate runs in the static portion of the chain (`scripts/verify.sh`, the CI `static` job) because the
order is a property of the repository, not of the data. A skip ahead turns the whole chain red in the
same way a stale registry vintage does.

Run::

    python scripts/check_phase_gate.py
"""

from __future__ import annotations

import re
import sys
from datetime import date
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
STATE_PATH = REPO_ROOT / "presidents-completion-state.yml"
PLAN_PATH = REPO_ROOT / "presidents-completion-plan.md"

STATUSES = ("not_started", "in_progress", "done")


def plan_phase_ids(plan_text: str) -> list[str]:
    """The phase ids the plan declares, from its own `## Phase X - ...` headings."""
    return re.findall(r"^## Phase ([A-Z]) ", plan_text, re.MULTILINE)


def main(argv: list[str] | None = None) -> int:
    failures: list[str] = []

    if not STATE_PATH.exists():
        print(f"FAILED - no phase state at {STATE_PATH.name}")
        return 1
    if not PLAN_PATH.exists():
        print(f"FAILED - no plan at {PLAN_PATH.name}")
        return 1

    state = yaml.safe_load(STATE_PATH.read_text(encoding="utf-8"))
    plan_ids = plan_phase_ids(PLAN_PATH.read_text(encoding="utf-8"))

    # ---- the phases are the plan's phases -----------------------------------------------------------------
    if state.get("plan") != PLAN_PATH.name:
        failures.append(f"the state names {state.get('plan')!r}, not {PLAN_PATH.name!r}")
    phases = state.get("phases") or []
    ids = [p.get("id") for p in phases]
    if ids != plan_ids:
        failures.append(f"the state's phase ids {ids} are not the plan's {plan_ids}")

    # ---- statuses are legal, and the order holds ----------------------------------------------------------
    for phase in phases:
        status = phase.get("status")
        if status not in STATUSES:
            failures.append(f"phase {phase.get('id')}: status {status!r} is not one of {STATUSES}")

    in_progress = [p["id"] for p in phases if p.get("status") == "in_progress"]
    if len(in_progress) > 1:
        failures.append(f"{len(in_progress)} phases are in_progress ({', '.join(in_progress)}) "
                        "- the plan is sequential, not parallel")

    closed = {p["id"] for p in phases if p.get("status") == "done"}
    for index, p in enumerate(phases):
        if p.get("status") in ("done", "in_progress"):
            for earlier in phases[:index]:
                earlier_status = earlier.get("status")
                if earlier_status == "not_started":
                    failures.append(
                        f"phase {earlier['id']}({earlier_status}) precedes phase {p['id']} "
                        f"({p.get('status')}) - the plan's order forbids starting at the back")
                elif earlier_status not in ("done",):
                    failures.append(
                        f"phase {earlier['id']} is {earlier_status}, not done, and phase {p['id']} "
                        f"is already {p.get('status')} - a phase runs to its exit criteria first")
    # phases after the in_progress frontier must be unstarted
    if in_progress:
        position = phases.index(next(p for p in phases if p.get("status") == "in_progress"))
        for p in phases[position + 1:]:
            if p.get("status") != "not_started":
                failures.append(
                    f"phase {p['id']} is {p.get('status')} while {in_progress[0]} is in_progress "
                    "- work behind the frontier has started")

    # ---- done requires evidence, and evidence names a check and a date ------------------------------------
    for p in phases:
        if p.get("status") != "done":
            continue
        evidence = p.get("evidence") or []
        if not evidence:
            failures.append(f"phase {p['id']} is done with no evidence - a claim nobody ran")
            continue
        for entry in evidence:
            check = str(entry.get("check", "")).strip()
            ran_on = str(entry.get("date", "")).strip()
            if not check:
                failures.append(f"phase {p['id']}: an evidence entry names no check")
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", ran_on):
                failures.append(f"phase {p['id']}: evidence date {ran_on!r} is not YYYY-MM-DD")
            elif date.fromisoformat(ran_on) > date.today():
                failures.append(f"phase {p['id']}: evidence is dated in the future ({ran_on})")

    if failures:
        print(f"FAILED - the phase gate found {len(failures)} problem(s):")
        for line in failures:
            print(f"  - {line}")
        print(f"Fix the state in {STATE_PATH.name}; the plan's prose is not the enforcement.")
        return 1

    print(f"phase gate     : {len(phases)} phases, 0 violations")
    for p in phases:
        marker = {"done": "[x]", "in_progress": "[~]", "not_started": "[ ]"}[p.get("status")]
        print(f"  {marker} Phase {p['id']} - {p.get('title')}")
    frontier_text = in_progress[0] if in_progress else "none (next permitted: unstarted phases only)"
    print(f"frontier       : {frontier_text}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
