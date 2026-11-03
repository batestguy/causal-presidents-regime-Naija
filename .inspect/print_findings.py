"""Print each outcome's findings paragraph from the built page."""
import re
import sys
import html

sys.stdout.reconfigure(encoding="utf-8")

t = open("site/dist/chart/index.html", encoding="utf-8").read()
blocks = re.findall(r'<article class="block[^"]*" data-outcome="([a-z0-9_]+)"[^>]*>(.*?)</article>', t, re.S)
for oid, body in blocks:
    m = re.search(r'<p class="findings">(.*?)</p>', body, re.S)
    print(oid, "::", html.unescape(m.group(1)) if m else "NONE")
    print()
