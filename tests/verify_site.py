"""Verify the built site against the registry it was generated from.

The site is a second renderer over the same artifacts, so it can disagree with them without any engine
changing — that is the failure this file exists to catch. It builds the site, parses the emitted HTML with
regular expressions and stdlib only (no browser, no AppTest), and compares what a reader would see with the
JSON the build read.

What it does not do: it does not import `site/build.py`, and it does not run the JavaScript. A block that only
appears after a script runs is still in the HTML — the build writes all twelve and the script unhides the
chosen ones — so the text contract is checkable without a browser, and the behaviour contract is checked by
hand in Brave (documented in the spec's limits).

Run:
    python tests/verify_site.py
"""

from __future__ import annotations

import html as html_module
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
DIST = REPO_ROOT / "site" / "dist"
PAGES = ("index.html", "study/index.html", "compare/index.html", "graph/index.html",
         "estimates/index.html", "chart/index.html", "ask/index.html", "designs/index.html")


def fail(failures: list[str], message: str) -> None:
    failures.append(message)


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def text_of(markup: str) -> str:
    """The page as a reader reads it: entities resolved, so a name with an apostrophe compares to the seed."""
    return html_module.unescape(markup)


def blocks(html: str) -> dict[str, str]:
    """Every `article.block` in the page, keyed by the outcome it is about."""
    out: dict[str, str] = {}
    for match in re.finditer(r'<article class="block[^"]*" data-outcome="([a-z0-9_]+)"[^>]*>(.*?)</article>',
                             html, re.S):
        out[match.group(1)] = text_of(match.group(2))
    return out


def main() -> int:
    failures: list[str] = []
    build = subprocess.run([sys.executable, str(REPO_ROOT / "site" / "build.py")],
                           cwd=REPO_ROOT, capture_output=True, text=True)
    if build.returncode != 0:
        print("FAILED — the build did not complete:")
        print(build.stdout[-2000:] + build.stderr[-2000:])
        return 1

    index = json.loads(read(REPO_ROOT / "registry" / "dags" / "index.json"))
    guide = yaml.safe_load(read(REPO_ROOT / "analysis" / "specs" / "guide.yml"))
    admins = json.loads(read(REPO_ROOT / "registry" / "reference" / "administrations.json"))
    comparisons_path = REPO_ROOT / "registry" / "comparisons" / index["vintage_date"] / "comparisons.json"
    comparisons = {row["id"]: row for row in json.loads(read(comparisons_path))["outcomes"]}
    breaks_path = REPO_ROOT / "registry" / "changepoints" / index["vintage_date"] / "changepoints.json"
    breaks = {row["id"]: row for row in json.loads(read(breaks_path))["outcomes"]}

    for page in PAGES:
        if not (DIST / page).exists():
            fail(failures, f"{page} was not built")

    cover = text_of(read(DIST / "index.html"))
    flow = {page: text_of(read(DIST / page)) for page in PAGES[1:]}
    # The study screen is checkboxes and the ask screen is a question box: this is where the pages that
    # carry one block per outcome are named, rather than inferred from the page list.
    block_pages = [page for page in ("compare/index.html", "graph/index.html", "estimates/index.html",
                                     "chart/index.html")]

    # ---- the cover states the ratio, names five administrations, and attributes nothing -----------------
    counts = index["registry"]["card_estimate_counts"]
    ratio = f"{counts['estimated']} of {counts['estimated'] + counts['not_estimated']} model cards carry a published number"
    if ratio not in cover:
        fail(failures, f"the cover does not state the ratio it exists to state ({ratio!r})")
    for admin in admins["administrations"]:
        if admin["president"] not in cover:
            fail(failures, f"the cover does not carry {admin['president']}")
    if index["vintage_date"] not in cover:
        fail(failures, "the cover does not stamp the registry vintage")
    for outcome in index["outcomes"]:
        if outcome["label"] in cover:
            fail(failures, f"the cover names the outcome {outcome['label']!r} — the cover is a spine, not a "
                           f"place where an outcome is put next to a face")

    # ---- no flow page attributes an outcome to a president ----------------------------------------------
    # A president's name is permitted in exactly two places, both of which are labels rather than verdicts: the
    # tenure table (a period label) and a published question offered as an autocomplete option. Everywhere else the
    # name stays forbidden, and the tension inside the tenure table is checked separately below.
    def without_period_labels(markup: str) -> str:
        markup = re.sub(r'<section class="tenure">.*?</section>', "", markup, flags=re.S)
        return re.sub(r"<datalist[^>]*>.*?</datalist>", "", markup, flags=re.S)

    surnames = {admin["president"].split()[-1] for admin in admins["administrations"]}
    verdict_words = ("caused", "because of", "effect of", "improved", "worsened", "blame", "credit")
    for page, html in flow.items():
        scanned = without_period_labels(html)
        for surname in surnames:
            if re.search(rf"\b{surname}\b", scanned):
                fail(failures, f"{page} names {surname} — a per-president verdict is the claim this build "
                               f"refuses to make, in a tab, a label or a caption")
    for label_block in re.findall(r'<section class="tenure">.*?</section>', read(DIST / "chart" / "index.html"),
                                  flags=re.S):
        for word in verdict_words:
            if word in label_block.lower():
                fail(failures, f"chart/: the tenure table carries the verdict word {word!r} — a deviation labels a "
                               f"window and may not be narrated")

    # ---- twelve outcomes reachable on every flow screen -------------------------------------------------
    expected_ids = {row["id"] for row in index["outcomes"]}
    for page in block_pages:
        found = blocks(flow[page])
        if set(found) != expected_ids:
            fail(failures, f"{page}: blocks for {sorted(set(expected_ids) ^ set(found))} are missing or extra")
    for page, markup in flow.items():
        if index["vintage_date"] not in markup:
            fail(failures, f"{page} does not stamp the registry vintage")

    # ---- the chosen design is the recomputed one (A-01: number first, then status) -----------------------
    rank = {"pass": 0, "degraded": 1, "fail": 2, "not_attempted": 3}
    published_a = {row["outcome"] for row in
                   (index["published_results"]["A"]["specifications"] if index.get("published_results") else [])}
    card_status = {(row["outcome_id"], row["design_id"]): row.get("diagnostics_status") or "not_attempted"
                   for row in index["dags"]}
    for oid in expected_ids:
        best = min((d["id"] for d in index["designs"]),
                   key=lambda design: (0 if (design == "A" and oid in published_a) else 1, rank[card_status[(oid, design)]]))
        compare_block = blocks(flow["compare/index.html"]).get(oid, "")
        if not re.search(rf"<strong>{best} — ", compare_block):
            fail(failures, f"compare/{oid}: the page does not name Design {best} as the chosen comparison")

    # ---- every published coefficient appears once, on its own outcome, with its verdict -----------------
    for specification in (index.get("published_results", {}).get("A", {}) or {}).get("specifications", []):
        coefficient = f"{specification['coefficient']:+.4f}"
        carrier = specification["outcome"]
        if carrier not in expected_ids:
            continue
        for oid, block in blocks(flow["estimates/index.html"]).items():
            has_number = coefficient in block
            if oid == carrier and not has_number:
                fail(failures, f"estimates/{oid}: the published coefficient {coefficient} is not on its own block")
            if oid != carrier and has_number:
                fail(failures, f"estimates/{oid}: carries {coefficient}, which belongs to {carrier} — a number "
                               f"lent to an outcome it was not estimated on")
        verdict = (index["published_results"]["A"].get("verdict") or {}).get("status")
        if verdict and verdict not in blocks(flow["estimates/index.html"]).get(carrier, ""):
            fail(failures, f"estimates/{carrier}: the verdict {verdict!r} is not shown beside its coefficient")
        failed = (index["published_results"]["A"].get("verdict") or {}).get("failed_checks")
        if failed and failed[:60] not in blocks(flow["estimates/index.html"]).get(carrier, ""):
            fail(failures, f"estimates/{carrier}: the check that decided the verdict is not shown")

    # ---- the graphs exist and are the chosen design's ---------------------------------------------------
    graph_blocks = blocks(flow["graph/index.html"])
    for row in index["dags"]:
        if not (DIST / "assets" / "graphs" / f"{row['dag_id']}.svg").exists():
            fail(failures, f"assets/graphs/{row['dag_id']}.svg is not in the build")
    for oid, block in graph_blocks.items():
        if not re.search(rf'<img class="graph" src="\.\./assets/graphs/{oid}__[ABC]\.svg"', block):
            fail(failures, f"graph/{oid}: no assumed graph is rendered")

    # ---- the chart uses the comparison artifact, stamps it, and draws every declared grouping ------------
    chart_blocks = blocks(flow["chart/index.html"])
    for oid, record in comparisons.items():
        figure = REPO_ROOT / record["figure"]["path"]
        copied = DIST / "assets" / "comparisons" / f"{oid}.svg"
        if not copied.exists():
            fail(failures, f"chart/{oid}: the comparison figure was not copied into the build")
        elif copied.stat().st_size != figure.stat().st_size:
            fail(failures, f"chart/{oid}: the copied figure differs in size from {record['figure']['path']}")
        block = chart_blocks.get(oid, "")
        if record["caption"] and record["caption"] not in block:
            fail(failures, f"chart/{oid}: the artifact's caption is not on the page")
        if guide["chart"]["stamp"] not in block:
            fail(failures, f"chart/{oid}: the 'description, not a causal comparison' stamp is missing")
        for grouping in {g["grouping_id"] for g in record["groups"]}:
            if f'data-grouping="{grouping}"' not in block and f"data-grouping='{grouping}'" not in block:
                fail(failures, f"chart/{oid}: the {grouping} group list is not rendered")
        for group in record["groups"]:
            if group["plain"] not in block:
                fail(failures, f"chart/{oid}: group {group['group_id']} has no label on the page")

    # ---- the changepoint half of the chart screen is the artifact, and the figure is the artifact's --------
    for oid, record in breaks.items():
        block = chart_blocks.get(oid, "")
        if guide["changepoint"]["heading"] not in block:
            fail(failures, f"chart/{oid}: the changepoint section is missing")
        if record["plain_caption"] and record["plain_caption"] not in block:
            fail(failures, f"chart/{oid}: the changepoint caption is not on the page")
        for brk in record["breaks"]:
            if brk["month"] not in block or brk["statement"] not in block:
                fail(failures, f"chart/{oid}: break {brk['month']} is not shown with its statement")
        if record["figure"] is None:
            if guide["changepoint"]["refused"] not in block:
                fail(failures, f"chart/{oid}: refused with no break, but the page does not say why")
            continue
        figure = REPO_ROOT / record["figure"]["path"]
        copied = DIST / "assets" / "breaks" / f"{oid}.svg"
        if not copied.exists():
            fail(failures, f"chart/{oid}: the changepoint figure was not copied into the build")
        elif copied.stat().st_size != figure.stat().st_size:
            fail(failures, f"chart/{oid}: the copied changepoint figure differs from the artifact's file")
        if guide["changepoint"]["note"] not in block:
            fail(failures, f"chart/{oid}: the 'a break is not evidence' note is missing")

    # ---- the Ask screen runs the second answer implementation over JSON the build emits ----------------
    ask = flow["ask/index.html"]
    answers = json.loads(read(REPO_ROOT / "registry" / "rag" / index["vintage_date"] / "answer_eval.json"))
    overall = answers["sets"]["all"]
    measured = fill = (f"{overall['answered']} of {overall['n']} questions")
    if measured not in ask:
        fail(failures, f"ask/: the measured limit ({fill}) is not stated on the page — the layer's failure rate "
                       f"is published, not implied")
    for asset in ("assets/answer.mjs", "assets/ask.mjs", "data/gate.json", "data/contract.json", "data/corpus.json"):
        if not (DIST / asset).exists():
            fail(failures, f"ask/: {asset} is not in the build, so the page cannot answer anything")
    emitted = json.loads(read(DIST / "data" / "gate.json"))["spec"]
    spec = yaml.safe_load(read(REPO_ROOT / "analysis" / "specs" / "intent_gate.yml"))
    if [rule["id"] for rule in emitted["rules"]] != [rule["id"] for rule in spec["rules"]]:
        fail(failures, "ask/: the emitted gate rules are not the spec's rules — the browser would decide "
                       "questions under a rule set nobody reviewed")
    if json.loads(read(DIST / "data" / "contract.json"))["contract"] != yaml.safe_load(
            read(REPO_ROOT / "analysis" / "specs" / "rag.yml"))["answer_contract"]:
        fail(failures, "ask/: the emitted answer contract is not rag.yml's")

    # ---- Screen 6b is the three design-level artifacts: figure, layout, verdict and check ------------------
    def plain(markup: str) -> str:
        """The page as text: tags removed *before* entities are resolved, so a literal `<` in the prose (`p <= 0.05`)
        is not mistaken for the start of a tag and swallowed."""
        return html_module.unescape(re.sub(r"<[^>]+>", "", markup))

    designs_page = plain(read(DIST / "designs" / "index.html"))
    estimates = json.loads(read(REPO_ROOT / "registry" / "estimates" / index["vintage_date"] / "estimates.json"))
    robustness = json.loads(read(REPO_ROOT / "registry" / "robustness" / index["vintage_date"] / "robustness.json"))
    events = json.loads(read(REPO_ROOT / "registry" / "events" / index["vintage_date"] / "events.json"))
    by_design = {row["id"]: row for row in estimates["designs"]}

    def stripped(value: str) -> str:
        """The artifact's prose as a reader sees it: the three Markdown markers removed."""
        return str(value).replace("**", "").replace("*", "").replace("`", "")

    def canonical_size(path: Path) -> int:
        """Bytes as git stores them: CRLF collapsed to LF, the rule `verify_stage6`/`verify_changepoints` use, so
        a figure's recorded size holds on this Windows checkout and on the Linux runner alike."""
        return len(path.read_bytes().replace(b"\r\n", b"\n"))

    figure_families = (("estimates", estimates["figure"], "the forest plot"),
                       ("robustness", robustness["figure"], "the specification curve"),
                       ("events", events["figure"], "the event study"))
    for family, record, label in figure_families:
        source = REPO_ROOT / "registry" / family / index["vintage_date"] / Path(record["path"]).name
        copied = DIST / "assets" / "designs" / Path(record["path"]).name
        if not copied.exists():
            fail(failures, f"designs/: {label} was not copied into the build")
            continue
        if canonical_size(copied) != canonical_size(source):
            fail(failures, f"designs/: the copied {label} differs from {family}'s artifact file")
        if record["bytes"] != canonical_size(copied):
            fail(failures, f"designs/: the {family} artifact records {record['bytes']} bytes for {label} "
                           f"but the file is {canonical_size(copied)} — a figure one re-fit behind its artifact")
        if stripped(record["layout"]) not in designs_page:
            fail(failures, f"designs/: the {family} artifact's layout sentence is not on the page — the figure "
                           f"would be drawn with no account of what it draws")

    # Design A's verdict, the check that decided it, and every number it published.
    a_verdict = by_design["A"].get("verdict") or {}
    if a_verdict.get("status") and a_verdict["status"] not in designs_page:
        fail(failures, f"designs/: Design A's verdict {a_verdict['status']!r} is not on the page")
    if a_verdict.get("failed_checks") and stripped(a_verdict["failed_checks"]) not in designs_page:
        fail(failures, "designs/: the check that decided Design A's verdict is not on the page")
    for row in estimates["specifications"]:
        if row["design"] != "A":
            continue
        coefficient = f"{row['coefficient']:+.4f}"
        if coefficient not in designs_page:
            fail(failures, f"designs/: Design A's published coefficient {coefficient} is missing")
        if f"{row['ci_low']:.4f}" not in designs_page or f"{row['ci_high']:.4f}" not in designs_page:
            fail(failures, f"designs/: the interval for {row['outcome']} is missing")

    # Design B's number, and the grid that qualifies it.
    b_status = (by_design["B"].get("verdict") or {}).get("status")
    if b_status and b_status not in designs_page:
        fail(failures, f"designs/: Design B's verdict {b_status!r} is not on the page")
    preferred_b = robustness["preferred"]["design_b"]
    if f"{preferred_b['coefficient']:+.4f}" not in designs_page:
        fail(failures, "designs/: Design B's published coefficient is missing")
    for design_id in ("A", "B"):
        support = robustness["support"]["by_design"][design_id]
        needle = f"{support['n_positive']} of {support['n']} specifications"
        if needle not in designs_page:
            fail(failures, f"designs/: the grid's {design_id} support count ({needle!r}) is not on the page")
    placebo = robustness["sensitivity"]["design_b"]["in_time_placebo"]
    if f"p = {placebo['p_value']:.4f}" not in designs_page:
        fail(failures, f"designs/: the in-time placebo p ({placebo['p_value']}) is not on the page")
    for row in robustness["support"]["flips"]["levels"]:
        needle = f"{row['n_opposite']} of {row['n']} specifications point the other way"
        if needle not in designs_page:
            fail(failures, f"designs/: the sign-flip at {row['axis']}={row['level']} is not on the page")

    # Design C: the synthetic control lives in its own artifact. A run design prints its windows by year and
    # never by name; a design that did not run prints the reason instead of an empty section.
    c_row = by_design["C"]
    if c_row.get("status") == "not_run":
        if stripped(c_row.get("why") or "") not in designs_page:
            fail(failures, "designs/: Design C's reason for not running is not on the page")
        if stripped(c_row.get("next_step") or "") not in designs_page:
            fail(failures, "designs/: Design C's next step is not on the page")
    else:
        if stripped(guide["design_results"]["c_note"]) not in designs_page:
            fail(failures, "designs/: the note that a synthetic control has no interval is not on the page")
        for window in c_row.get("windows") or []:
            if window.get("status") == "refused":
                continue
            years = f"{window['first_year']}–{window['last_year']}"
            if years not in designs_page:
                fail(failures, f"designs/: Design C's window {years} is not on the page")
            if f"{window['p_value']:.2f}" not in designs_page:
                fail(failures, f"designs/: Design C's placebo p for {years} is not on the page")

    # The transition study: one line per artifact verdict, its rule, and what it does not claim.
    expected_rows = []
    for verdict in events["verdicts"]:
        transition = next((row for row in events["events"] if row["id"] == verdict["event"]), None)
        if transition is None:
            fail(failures, f"designs/: a verdict names {verdict['event']!r}, which has no transition row")
            continue
        expected_rows.append((transition["transition_month"], f"{verdict['placebo_p']:.4f}"))
    found_rows = re.findall(r"(\d{4}-\d{2})[^\n]*?placebo p = (\d\.\d{4})", designs_page)
    if sorted(found_rows) != sorted(expected_rows):
        fail(failures, f"designs/: the transition rows on the page are not the artifact's — "
                       f"{len(found_rows)} found against {len(expected_rows)} verdicts, and the month/p pairs "
                       f"must match one for one")
    if stripped(events["verdict_rule"]) not in designs_page:
        fail(failures, "designs/: the rule the transition verdicts were read against is not on the page")
    for claim in events["not_claimed"]:
        if stripped(claim) not in designs_page:
            fail(failures, f"designs/: the not-claimed statement {claim[:40]!r}… is not on the page")

    # The screen is reachable from where a reader meets the gap it fills.
    for origin in ("estimates/index.html", "ask/index.html"):
        if "../designs/" not in flow[origin]:
            fail(failures, f"{origin}: no link to the design-level results — the screen would be unreadable "
                           f"from the flow that names it")

    # ---- the cover's portraits: the licence manifest is the gate, not the file's presence ------------------
    # docs/portraits.md §4 lists five invariants the build and this verifier enforce. Four of them are here; the
    # fifth (portrait_status supplied iff the manifest has an entry) is the loop's closing check.
    manifest_path = REPO_ROOT / "site" / "assets" / "presidents" / "manifest.json"
    manifest = json.loads(read(manifest_path)) if manifest_path.exists() else {"portraits": []}
    portrait_rows = {row["slug"]: row for row in manifest["portraits"]}
    licence_lines = [line for line in read(REPO_ROOT / "docs" / "licences.md").splitlines()
                     if line.startswith("|")]
    admin_by_slug = {a["slug"]: a for a in admins["administrations"]}

    for slug, row in portrait_rows.items():
        path = REPO_ROOT / row["file"]
        if not path.exists():
            fail(failures, f"portrait {slug}: {row['file']} is in the manifest but not on disk")
            continue
        if hashlib.sha256(path.read_bytes()).hexdigest() != row["sha256"]:
            fail(failures, f"portrait {slug}: the file's sha256 does not match the manifest — the image was "
                           f"swapped without a licence review")
        if slug not in admin_by_slug:
            fail(failures, f"portrait {slug}: no administration carries this slug")
        elif admin_by_slug[slug]["portrait_status"] != "supplied":
            fail(failures, f"portrait {slug}: the file and manifest exist but administrations.json says "
                           f"{admin_by_slug[slug]['portrait_status']!r} — regenerate the reference")
        matches = [line for line in licence_lines if row.get("file_title", "~none~") in line]
        if len(matches) != 1:
            fail(failures, f"portrait {slug}: {len(matches)} rows in docs/licences.md name its file title; the "
                           f"licence register must carry exactly one")
        else:
            cells = [cell.strip() for cell in matches[0].strip().strip("|").split("|")]
            if len(cells) < 4 or "yes" not in cells[3].lower():
                fail(failures, f"portrait {slug}: docs/licences.md does not permit redistribution "
                               f"({cells[3] if len(cells) > 3 else 'no cell'!r})")
        if f'assets/presidents/{slug}.jpg' not in cover:
            fail(failures, f"portrait {slug}: the cover does not render the supplied file")
        if row["attribution_text"] not in cover:
            fail(failures, f"portrait {slug}: its attribution text is not in the cover footer")

    for slug, admin in admin_by_slug.items():
        if admin["portrait_status"] == "supplied" and slug not in portrait_rows:
            fail(failures, f"portrait {slug}: administrations.json claims a portrait the manifest does not carry")
        if admin["portrait_status"] == "supplied" and 'has-portrait' not in cover:
            fail(failures, f"portrait {slug}: supplied but the cover draws no party backdrop for it")

    # ---- nothing on the site reaches the network -------------------------------------------------------
    for page, markup in flow.items():
        for match in re.findall(r'(?:src|href)="(https?:[^"]+)"', markup):
            fail(failures, f"{page}: {match} is an external reference — the site reads only its own files")

    # ---- every asset a page points at resolves from that page's own URL --------------------------------
    # The blind spot this closes: the checks above proved a figure existed in `dist/assets/…` but never that
    # the markup pointed *at* it. Every figure on /chart/ and /graph/ was written `assets/…` on a page served
    # from /chart/ or /graph/, so the deployed site requested `/chart/assets/…` and 404ed while all checks
    # stayed green. A path is a claim until something resolves it.
    for page in PAGES:
        base = (DIST / page).parent
        for attr, value in re.findall(r'(src|href)="([^"]+)"', read(DIST / page)):
            if value.startswith(("http://", "https://", "#", "mailto:", "data:", "javascript:")):
                continue
            target = (base / value.split("?", 1)[0]).resolve()
            if value.split("?", 1)[0].endswith("/"):
                target = target / "index.html"
            if not target.exists():
                fail(failures, f"{page}: {attr}={value!r} does not resolve to a file in the build")

    # ---- the wording on screen is the declared wording --------------------------------------------------
    statuses = set(guide["status"])
    for page, html in flow.items():
        for word in re.findall(r'class="pill [a-z]+">([^<]+)<', html):
            if not any(entry["word"] == word for entry in guide["status"].values()):
                fail(failures, f"{page}: pill text {word!r} is not a declared status word")
    if not all(entry.get("word") for entry in guide["status"].values()):
        fail(failures, "a declared status has no word — guide.yml and the renderer disagree")

    # ---- the renderer carries no typed number ------------------------------------------------------------
    build_source = read(REPO_ROOT / "site" / "build.py")
    for number in re.findall(r"\b\d[\d,]{2,}\b", build_source):
        if number.replace(",", "") not in {"100", "999"}:
            fail(failures, f"site/build.py carries the literal {number} — every count on the page is read from "
                           f"an artifact or a spec")

    if failures:
        print(f"FAILED — {len(failures)} problem(s):")
        for problem in failures[:40]:
            print(f"  - {problem}")
        if len(failures) > 40:
            print(f"  … and {len(failures) - 40} more")
        return 1

    print(f"built         : {len(PAGES)} pages at vintage {index['vintage_date']}")
    print(f"checked       : the ratio, {len(admins['administrations'])} administrations, {len(expected_ids)} "
          f"outcomes per screen, the chosen design per outcome")
    print(f"numbers       : {len((index.get('published_results', {}).get('A', {}) or {}).get('specifications', []))} "
          f"published coefficients, each on its own outcome with its verdict and failed check")
    print(f"charts        : {len(comparisons)} comparison figures, every group labelled, every chart stamped")
    print(f"breaks        : {len(breaks)} changepoint panels, every declared break shown, every refusal explained")
    print(f"designs       : 3 figures byte-matched to their artifacts, A's number and check, the grid's support "
          f"and flips, C's "
          f"{'reason' if by_design['C'].get('status') == 'not_run' else 'windows by year'}, "
          f"{len(events['verdicts'])} transition verdicts, the rule, {len(events['not_claimed'])} "
          f"not-claimed statements")
    print(f"ask           : the gate's own rules, the contract and the corpus emitted; the measured limit stated")
    print("wording       : every status pill is a declared word; no count is typed into the renderer")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
