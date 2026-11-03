"""Scan site/dist visible text for file-like references a reader has no business with."""
import re, html as h
from pathlib import Path

dist = Path("site/dist")
pat = re.compile(r"[a-zA-Z0-9_/\-.]+\.(?:json|R|py|r|csv|yml|yaml|md|svg|js|mjs|duckdb)\b|registry/|analysis/|dbt/|scripts/|\.R\b|R script|dagitty|duckdb")

import sys
sys.stdout.reconfigure(encoding="utf-8")

for p in sorted(dist.rglob("index.html")):
    t = p.read_text(encoding="utf-8")
    t = re.sub(r"<(script|style|svg)[^>]*>.*?</\1>", " ", t, flags=re.S)
    t = h.unescape(re.sub(r"<[^>]+>", " ", t))
    t = re.sub(r"\s+", " ", t)
    for m in pat.finditer(t):
        a, b = max(0, m.start() - 70), m.end() + 70
        frag = t[a:b].strip()
        print(f"{str(p.relative_to(dist)):<24} :: {frag}")
