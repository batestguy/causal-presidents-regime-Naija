"""Count and list the Ask screen's autocomplete questions from the built page."""
import json
import re
import sys
import html
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

t = (Path("site/dist/ask/index.html")).read_text(encoding="utf-8")
m = re.search(r'<datalist id="ask-questions">(.*?)</datalist>', t, re.S)
qs = re.findall(r'value="(.*?)"', m.group(1)) if m else []
print(f"autocomplete options: {len(qs)}")
for q in qs:
    print(" -", html.unescape(q))

eval_set = json.load(open("registry/rag/2026-11-01/eval_set.json", encoding="utf-8"))
print()
print("measured eval set:", eval_set["counts"])
print("types:", {row["type"] for row in eval_set["questions"]})
