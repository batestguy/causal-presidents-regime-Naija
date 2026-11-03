"""Audit the trend section style across all twelve outcomes in the built chart page."""
import re
import sys
import html

sys.stdout.reconfigure(encoding="utf-8")

t = open("site/dist/chart/index.html", encoding="utf-8").read()
blocks = re.findall(r'<article class="block[^"]*" data-outcome="([a-z0-9_]+)"[^>]*>(.*?)</article>', t, re.S)
for oid, body in blocks:
    sec = re.search(r'<section class="tenure">(.*?)</section>', body, re.S)
    if not sec:
        print(f"{oid:<18} NO TENURE SECTION")
        continue
    inner = sec.group(1)
    heading = re.search(r"<h3>(.*?)</h3>", inner, re.S)
    heads = [html.unescape(h) for h in re.findall(r"<th>(.*?)</th>", inner)]
    rows = len(re.findall(r"<tr>", re.findall(r"<tbody>(.*?)</tbody>", inner, re.S)[0])) if "<tbody>" in inner else 0
    para = re.search(r'<p class="(findings|blocker|note)">(.*?)</p>', inner, re.S)
    print(f"{oid:<18} heads={len(heads)} rows={rows} "
          f"heads0={heads[:1]} para={html.unescape(para.group(2))[:95] if para else 'NONE'}")
