"""Inventory how the 12 outcomes' card facts differ, per screen family."""
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

root = Path(".")
idx = json.load(open("registry/dags/index.json", encoding="utf-8"))
RANK = {"pass": 0, "degraded": 1, "fail": 2, "not_attempted": 3}
guide_ranks = {"pass": 0, "degraded": 1, "fail": 2, "not_attempted": 3}
pub_by_outcome = {s["outcome"] for s in idx["published_results"]["A"]["specifications"]}

print(f"{'outcome':<18} {'chosen':<7} {'status':<13} {'word':<26} {'tone':<6} "
      f"{'specs':<7} {'breaks':<7} {'tenure':<8} {'groupings'}")
comps = {r["id"]: r for r in json.load(open(f"registry/comparisons/{idx['vintage_date']}/comparisons.json", encoding='utf-8'))["outcomes"]}
brks = {r["id"]: r for r in json.load(open(f"registry/changepoints/{idx['vintage_date']}/changepoints.json", encoding='utf-8'))["outcomes"]}
for row in idx["outcomes"]:
    oid = row["id"]
    choices = []
    for entry in idx["dags"]:
        if entry["outcome_id"] != oid:
            continue
        card = json.load(open(f"registry/dags/{entry['dag_id']}.json", encoding="utf-8"))
        spec = (card.get("estimate") or {}).get("specification") or {}
        estimate = card.get("estimate") or {}
        has_number = estimate.get("status") == "estimated"
        status = entry.get("diagnostics_status") or "not_attempted"
        choices.append((0 if oid in pub_by_outcome and entry["design_id"] == "A" else 1,
                        guide_ranks.get(status, 3), entry["design_id"], status,
                        has_number, bool(spec), (estimate.get("verdict") or {}).get("status")))
    best = sorted(choices)[0]
    _, _, design, status, has_number, has_spec, verdict = best
    comp = comps.get(oid, {})
    brk = brks.get(oid, {})
    n_breaks = len(brk.get("breaks") or [])
    tenure = comp
    print(f"{oid:<18} {design:<7} {status:<13} {'num=' + str(has_number):<26} {verdict or '':<6} "
          f"{str(has_spec):<7} {str(n_breaks):<7} {str(bool(brk.get('tenure'))):<8} "
          f"{len(comp.get('groups') or [])}")
