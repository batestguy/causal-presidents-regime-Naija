"""Audit the built chart page: panels, tenure tables, change labels per outcome."""
import re
import sys
import html

sys.stdout.reconfigure(encoding="utf-8")

t = open("site/dist/chart/index.html", encoding="utf-8").read()
blocks = re.findall(r'<article class="block[^"]*" data-outcome="([a-z0-9_]+)"[^>]*>(.*?)</article>', t, re.S)
for oid, body in blocks:
    split = "state-panel" if "data-split=" in body else "party-only"
    tables = re.findall(r'<table class="deviation-table">(.*?)</table>', body, re.S)
    print(oid, split, "tenure-tables:", len(tables))
    for tb in tables:
        rows = re.findall(r"<tr>(.*?)</tr>", tb, re.S)
        data = []
        for row in rows:
            cells = [html.unescape(c).strip() for c in re.findall(r"<td[^>]*>(.*?)</td>", row)]
            if cells:
                data.append(cells)
        starts = sum(1 for c in data if c[-1] == "start")
        changes = [c[-1] for c in data]
        print("   rows:", len(data), "| labels:", changes, "| start count:", starts)
