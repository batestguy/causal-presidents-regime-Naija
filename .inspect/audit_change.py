"""Audit the trend change column across every outcome against the artifact's own fields."""
import json
import sys

sys.stdout.reconfigure(encoding="utf-8")

root = "registry/tenure/2026-11-01/tenure.json"
t = json.load(open(root, encoding="utf-8"))
idx = json.load(open("registry/dags/index.json", encoding="utf-8"))
direction = {o["id"]: o["direction"] for o in idx["outcomes"]}

for row in t["outcomes"]:
    if row.get("status") != "described" or "tenures" not in row:
        print(f"== {row['id']} skipped: status={row.get('status')}")
        continue
    described = [x for x in row["tenures"] if x["status"] == "described"]
    if not described:
        continue
    d = direction.get(row["id"], "down")
    good_sign = 1 if d == "up" else -1
    print(f"== {row['id']} ({row['label']}) direction={d}")
    prev = None
    diffs = 0
    for ten in described:
        low, high = ten["deviation_range"]
        mid = (low + high) / 2
        mean = ten["mean_deviation"]
        if prev is None:
            label_mid = label_mean = "start"
        else:
            diff_low, diff_high = low - prev["high"], high - prev["low"]
            straddle = diff_low <= 0 <= diff_high
            label_mid = label_mean = "no change, neutral" if straddle else None
            if not straddle:
                label_mid = "change, good" if (mid - prev["mid"]) * good_sign > 0 else "change, bad"
                label_mean = "change, good" if (mean - prev["mean"]) * good_sign > 0 else "change, bad"
            else:
                # how does the published mean move even though the spans overlap?
                item = ten["president"].split()[-1]
                lean = "up" if mean > prev["mean"] else "down"
                print(f"   neutral: {item:<10} mean {prev['mean']:+7.2f} -> {mean:+7.2f} ({lean})"
                      f"  diff[{diff_low:+.2f}, {diff_high:+.2f}]")
                diffs += 1
        if label_mid != label_mean:
            print(f"   MISMATCH {ten['president']}: midpoint->{label_mid}  mean->{label_mean}")
        prev = {"low": low, "high": high, "mid": mid, "mean": mean}
    print()
