"""Scan site/dist for repeated sentences across pages and within a page."""
import re, html as h, collections
from pathlib import Path

dist = Path("site/dist")
pages = ["index.html", "study/index.html", "compare/index.html", "graph/index.html",
         "estimates/index.html", "chart/index.html", "ask/index.html", "designs/index.html",
         "about/index.html", "methodology/index.html", "technical/index.html"]


def text(p):
    t = (dist / p).read_text(encoding="utf-8")
    t = re.sub(r"<(script|style|svg)[^>]*>.*?</\1>", " ", t, flags=re.S)
    t = re.sub(r"<[^>]+>", " ", t)
    t = h.unescape(t)
    return re.sub(r"\s+", " ", t)


texts = {p: text(p) for p in pages}
sents = collections.defaultdict(list)
for p, t in texts.items():
    for s in re.split(r"(?<=[.!?]) ", t):
        s2 = s.strip().lower()
        if len(s2) > 25:
            sents[s2].append(p)
rep = {s: set(ps) for s, ps in sents.items() if len(ps) > 1}
print(f"== sentences appearing on >1 page (or repeated pages): {len(rep)} ==")
for s, ps in sorted(rep.items(), key=lambda kv: -len(kv[1]))[:60]:
    print(f"[{len(ps):>2}] {'/'.join(sorted(p[:12] for p in ps)):<40} {s[:100]}")

print()
print("== same sentence repeated within one page ==")
for p, t in texts.items():
    c = collections.Counter(s.strip().lower() for s in re.split(r"(?<=[.!?]) ", t) if len(s.strip()) > 25)
    for s, n in c.items():
        if n > 1:
            print(f"[x{n:<2}] {p:<20} {s[:100]}")

print()
print("== page word counts (reader-facing) ==")
for p, t in texts.items():
    words = len(t.split())
    print(f"{p:<24} {words:>6} words")
