"""One index dags row, keys exposed."""
import json
import sys

sys.stdout.reconfigure(encoding="utf-8")

idx = json.load(open("registry/dags/index.json", encoding="utf-8"))
print("dags row keys:", sorted(idx["dags"][0].keys()))
print(json.dumps(idx["dags"][0], indent=1)[:2500])
