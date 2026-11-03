"""Scan repo copy sources for em dashes, excluding data/, registry/ (frozen), and site/dist (generated)."""
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
targets = ["app", "analysis/specs", "site/build.py", "tests", "docs"]
for t in targets:
    p = REPO / t
    files = [p] if p.is_file() else sorted(p.rglob("*") if p.is_dir() else [])
    n = 0
    for f in files:
        if f.suffix not in (".py", ".yml", ".yaml", ".md"):
            continue
        text = f.read_text(encoding="utf-8", errors="replace")
        count = text.count("\u2014")
        if count:
            n += count
            print(f"{count:>4}  {f.relative_to(REPO)}")
    if n == 0:
        print(f"   0  {t}/ (clean)")
