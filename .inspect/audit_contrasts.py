"""Audit the change column under the artifact-contrast rule across every outcome."""
import json
import sys

sys.stdout.reconfigure(encoding="utf-8")

t = json.load(open("registry/tenure/2026-11-01/tenure.json", encoding="utf-8"))
idx = json.load(open("registry/dags/index.json", encoding="utf-8"))
direction = {o["id"]: o["direction"] for o in idx["outcomes"]}

for row in t["outcomes"]:
    described = [x for x in row.get("tenures") or [] if x["status"] == "described"]
    if not described:
        print(f"== {row['id']}: no described tenures")
        continue
    d = direction.get(row["id"], "down")
    good_sign = 1 if d == "up" else -1
    contrasts = {frozenset((c["a"], c["b"])): c for c in row.get("contrasts") or []}
    print(f"== {row['id']} direction={d}")
    prev = None
    for ten in described:
        if prev is None:
            print(f"   start   {ten['president']}")
        else:
            pair = contrasts.get(frozenset((prev["president"], ten["president"])))
            if pair:
                delta = -pair["difference"] if pair["a"] == prev["president"] else pair["difference"]
                lo, hi = pair["range"]
                src = "contrast"
            else:
                delta = ten["mean_deviation"] - prev["mean_deviation"]
                lo, hi = ten["deviation_range"][0] - prev["deviation_range"][1], \
                    ten["deviation_range"][1] - prev["deviation_range"][0]
                src = "DERIVED"
            if lo <= 0 <= hi:
                label = "no change, neutral"
            elif delta * good_sign > 0:
                label = "change, good"
            else:
                label = "change, bad"
            print(f"   {label:<20} {ten['president'].split()[-1]:<10} vs "
                  f"{prev['president'].split()[-1]:<10} {delta:+7.2f} "
                  f"range[{lo:+7.2f},{hi:+7.2f}] {src}")
        prev = ten
    print()
