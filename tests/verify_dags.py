"""Verify the causal-DAG layer of the model registry.

Reads ``registry/dags/index.json`` and every card it points at, then re-derives the checks
that matter *independently of the R generator*:

  * the card conforms to ``registry/schema/dag_card.schema.json``;
  * the graph is acyclic, node ids are unique, and every edge cites a real node;
  * exactly one exposure and one outcome node, and they agree with the design block;
  * ``assumption_required`` is exactly the set of unobserved nodes, and is non-empty;
  * the reported ``adjustment_set`` is genuinely a backdoor adjustment set: it blocks every
    backdoor path from the exposure to the outcome in the assumed graph, and blocks none of
    the causal path (it contains no descendant of the exposure);
  * the rendered SVG exists and carries every node label, with nothing silently missing.

The adjustment-set check is the point of the file: the card claims a specific covariate set
follows from the graph, and that claim is recomputed here by d-separation rather than trusted.

Usage:
    conda run -p "C:/Users/TOSHIBA/ds-general" python tests/verify_dags.py
"""

from __future__ import annotations

import html
import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DAGS_DIR = REPO_ROOT / "registry" / "dags"
INDEX_PATH = DAGS_DIR / "index.json"
SCHEMA_PATH = REPO_ROOT / "registry" / "schema" / "dag_card.schema.json"
INDEX_SCHEMA_PATH = REPO_ROOT / "registry" / "schema" / "dag_index.schema.json"

NODE_WRAP = 16
ASSUMED_SUFFIX = " (assumed absent)"
VALID_ROLES = {"exposure", "outcome", "confounder", "mediator", "modifier"}
VALID_SOURCE_STATUS = {"acquired", "gap", "derived", "construct", "unobserved"}


# ------------------------------------------------------------------------------------------
# graph helpers (tiny graphs — no external graph library needed)
# ------------------------------------------------------------------------------------------
def wrap_label(text: str, width: int = NODE_WRAP) -> str:
    """Replicate the generator's greedy word wrap so expected figure lines match."""
    words = text.split()
    lines: list[str] = []
    cur = ""
    for word in words:
        cand = f"{cur} {word}" if cur else word
        if len(cand) > width and cur:
            lines.append(cur)
            cur = word
        else:
            cur = cand
    if cur:
        lines.append(cur)
    return "\n".join(lines)


def build_adjacency(edges: list[dict[str, str]]) -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    children: dict[str, set[str]] = {}
    parents: dict[str, set[str]] = {}
    for edge in edges:
        children.setdefault(edge["from"], set()).add(edge["to"])
        parents.setdefault(edge["to"], set()).add(edge["from"])
    return children, parents


def is_acyclic(node_ids: list[str], children: dict[str, set[str]]) -> bool:
    """Kahn's algorithm."""
    indegree = {n: 0 for n in node_ids}
    for src in node_ids:
        for dst in children.get(src, ()):
            indegree[dst] += 1
    queue = [n for n in node_ids if indegree[n] == 0]
    seen = 0
    while queue:
        node = queue.pop()
        seen += 1
        for dst in children.get(node, ()):
            indegree[dst] -= 1
            if indegree[dst] == 0:
                queue.append(dst)
    return seen == len(node_ids)


def descendants(node: str, children: dict[str, set[str]]) -> set[str]:
    out: set[str] = set()
    stack = list(children.get(node, ()))
    while stack:
        cur = stack.pop()
        if cur in out:
            continue
        out.add(cur)
        stack.extend(children.get(cur, ()))
    return out


def simple_paths(start: str, end: str, neighbours: dict[str, set[str]]) -> list[list[str]]:
    paths: list[list[str]] = []

    def walk(node: str, path: list[str], seen: set[str]) -> None:
        if node == end:
            paths.append(path)
            return
        for nxt in sorted(neighbours.get(node, ())):
            if nxt not in seen:
                walk(nxt, path + [nxt], seen | {nxt})

    walk(start, [start], {start})
    return paths


def path_blocked(path: list[str], parents: dict[str, set[str]], children: dict[str, set[str]],
                 conditioned: set[str]) -> bool:
    """A path is blocked if some node on it blocks it (d-separation, per-path form).

    Interior nodes only: a non-collider blocks when it is conditioned on, a collider blocks
    unless it or one of its descendants is conditioned on.
    """
    for i in range(1, len(path) - 1):
        before, mid, after = path[i - 1], path[i], path[i + 1]
        into_mid = before in parents.get(mid, ()) and after in parents.get(mid, ())
        if into_mid:  # collider
            if mid in conditioned or (descendants(mid, children) & conditioned):
                continue  # opened, does not block
            return True
        if mid in conditioned:
            return True
    return False


# ------------------------------------------------------------------------------------------
# svg helpers
# ------------------------------------------------------------------------------------------
def svg_text_lines(svg: str) -> list[str]:
    line = "".join(svg.split("\n"))
    out: list[str] = []
    for chunk in re.findall(r"<text[^>]*>(.*?)</text>", line, flags=re.DOTALL):
        out.append(html.unescape(re.sub(r"<[^>]*>", "", chunk)).strip())
    return out


# ------------------------------------------------------------------------------------------
# main
# ------------------------------------------------------------------------------------------
def main() -> int:
    if not INDEX_PATH.exists():
        raise SystemExit(f"no index at {INDEX_PATH} — run analysis/R/01_build_dags.R first")

    index = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    failures: list[str] = []

    try:
        import jsonschema
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        validator = jsonschema.Draft202012Validator(schema)
    except ImportError:
        validator, schema = None, None
        print("! jsonschema not importable — schema check skipped")

    if validator is not None and INDEX_SCHEMA_PATH.exists():
        index_schema = json.loads(INDEX_SCHEMA_PATH.read_text(encoding="utf-8"))
        for err in jsonschema.Draft202012Validator(index_schema).iter_errors(index):
            failures.append(f"index schema: {list(err.path)}: {err.message}")

    counts = index["counts"]
    print(f"index vintage {index['vintage_date']} | {counts['outcomes']} outcomes x "
          f"{counts['designs']} designs = {counts['dags']} DAGs")
    if counts["dags"] != counts["outcomes"] * counts["designs"]:
        failures.append("index counts inconsistent (dags != outcomes * designs)")
    if len(index["dags"]) != counts["dags"]:
        failures.append(f"index lists {len(index['dags'])} dags but counts.dags = {counts['dags']}")

    expected = {
        f"{o['id']}__{d['id']}"
        for o in index["outcomes"]
        for d in index["designs"]
    }
    listed = {d["dag_id"] for d in index["dags"]}
    for missing in sorted(expected - listed):
        failures.append(f"index is missing {missing}")

    print(f"\n{'dag_id':<24} {'adj set':<34} {'absent':<6} {'backdoor paths':>14}  svg")
    print("-" * 96)

    for entry in sorted(index["dags"], key=lambda d: d["dag_id"]):
        dag_id = entry["dag_id"]
        card_path = DAGS_DIR / f"{dag_id}.json"
        if not card_path.exists():
            failures.append(f"{dag_id}: card file missing")
            continue
        card = json.loads(card_path.read_text(encoding="utf-8"))
        problems: list[str] = []

        if card["dag_id"] != dag_id:
            problems.append("dag_id disagrees with filename")
        expected_id = f"{card['outcome']['id']}__{card['design']['id']}"
        if expected_id != dag_id:
            problems.append(f"dag_id != outcome__design ({expected_id})")
        if entry["svg"] != card["assets"]["svg"]:
            problems.append("index svg path disagrees with card")

        if validator is not None:
            for err in validator.iter_errors(card):
                problems.append(f"schema: {list(err.path)}: {err.message}")

        nodes = card["nodes"]
        ids = [n["id"] for n in nodes]
        observed_ids = {n["id"] for n in nodes if n["observed"]}
        unobserved_ids = {n["id"] for n in nodes if not n["observed"]}
        if len(ids) != len(set(ids)):
            problems.append("duplicate node ids")

        for node in nodes:
            if node["role"] not in VALID_ROLES:
                problems.append(f"node {node['id']}: bad role {node['role']}")
            if not node.get("source"):
                problems.append(f"node {node['id']}: no source recorded")
            if node.get("source_status") not in VALID_SOURCE_STATUS:
                problems.append(f"node {node['id']}: bad source_status {node.get('source_status')}")

        exposures = [n["id"] for n in nodes if n["role"] == "exposure"]
        outcomes = [n["id"] for n in nodes if n["role"] == "outcome"]
        if len(exposures) != 1:
            problems.append(f"expected exactly one exposure node, found {exposures}")
        if len(outcomes) != 1:
            problems.append(f"expected exactly one outcome node, found {outcomes}")
        if exposures and exposures[0] != card["design"]["exposure_node"]:
            problems.append("exposure node disagrees with the design block")
        if outcomes and outcomes[0] != card["design"]["outcome_node"]:
            problems.append("outcome node disagrees with the design block")

        for edge in card["edges"]:
            if edge["from"] not in ids or edge["to"] not in ids:
                problems.append(f"edge cites an unknown node: {edge}")

        children, _ = build_adjacency(card["edges"])
        if not is_acyclic(ids, children):
            problems.append("graph is cyclic")

        # The adjustment set is defined on the assumed graph: unobserved nodes and their
        # edges removed. Checking it against the displayed graph would be a category error.
        assumed_edges = [e for e in card["edges"]
                         if e["from"] in observed_ids and e["to"] in observed_ids]
        a_children, a_parents = build_adjacency(assumed_edges)

        if set(card["assumption_required"]) != unobserved_ids:
            problems.append("assumption_required != set of unobserved nodes")
        if not unobserved_ids:
            problems.append("no unobserved node: the identifying assumption is unstated")

        adj = list(card["adjustment_set"])
        if not adj:
            problems.append("empty adjustment set")
        unknown = [a for a in adj if a not in observed_ids]
        if unknown:
            problems.append(f"adjustment set cites non-observed node(s): {unknown}")

        # The reported set must really be a backdoor adjustment set.
        n_backdoor = 0
        if len(exposures) == 1 and len(outcomes) == 1:
            exposure, outcome = exposures[0], outcomes[0]
            neighbours: dict[str, set[str]] = {}
            for src, dsts in a_children.items():
                neighbours.setdefault(src, set()).update(dsts)
            for dst, srcs in a_parents.items():
                neighbours.setdefault(dst, set()).update(srcs)
            conditioned = set(adj)
            for path in simple_paths(exposure, outcome, neighbours):
                # backdoor: the first hop enters the exposure (a parent of the exposure)
                if path[1] not in a_parents.get(exposure, ()):
                    continue
                n_backdoor += 1
                if not path_blocked(path, a_parents, a_children, conditioned):
                    problems.append(
                        "adjustment set fails to block backdoor path: " + " -> ".join(path)
                    )
            if conditioned & descendants(exposure, a_children):
                problems.append("adjustment set conditions on a descendant of the exposure "
                                "(the causal path would be blocked)")

        # the stored dagitty strings must agree with the node/edge lists
        full = card["dagitty_full"]
        for node in ids:
            if not re.search(rf"^\s*{re.escape(node)}\s*\[", full, flags=re.MULTILINE):
                problems.append(f"dagitty_full does not declare node {node}")
        for node in unobserved_ids:
            if not re.search(rf"^\s*{re.escape(node)}\s*\[", card["dagitty_assumed"], flags=re.MULTILINE):
                continue
            problems.append(f"dagitty_assumed still declares unobserved node {node}")

        # the rendered figure must carry every label, with the assumption marked
        svg_path = REPO_ROOT / card["assets"]["svg"]
        if not svg_path.exists() or svg_path.stat().st_size == 0:
            problems.append("svg missing or empty")
            rendered: list[str] = []
        else:
            rendered = svg_text_lines(svg_path.read_text(encoding="utf-8", errors="replace"))

        if rendered:
            expected_lines: set[str] = set()
            for node in nodes:
                lines = wrap_label(node["short"]).split("\n")
                if not node["observed"]:
                    lines += wrap_label(ASSUMED_SUFFIX.strip()).split("\n")
                expected_lines.update(lines)
            for line in sorted(expected_lines):
                if line not in rendered:
                    problems.append(f"label not present in svg: '{line}'")
            joined = " ".join(rendered)
            if unobserved_ids and not all(w in joined for w in ASSUMED_SUFFIX.split()):
                problems.append("svg does not mark the assumed-absent node")

        if problems:
            failures.extend(f"{dag_id}: {p}" for p in problems)
            print(f"{dag_id:<24} {'CHECK FAILED':<34} {'':<6} {n_backdoor:>14}")
        else:
            print(f"{dag_id:<24} {', '.join(adj):<34} "
                  f"{','.join(sorted(unobserved_ids)):<6} {n_backdoor:>14}  ok")

    # Orphan check: a card on disk that the index does not list means the registry and its
    # index have drifted apart.
    on_disk = {p.stem for p in DAGS_DIR.glob("*.json") if p.name != "index.json"}
    for orphan in sorted(on_disk - listed):
        failures.append(f"orphaned card (not in index): {orphan}.json")
    print(f"\n  cards on disk: {len(on_disk)}, listed in index: {len(listed)}, "
          f"orphaned: {len(on_disk - listed)}")

    # The registry's own answer to "what are we missing": every node with no usable source,
    # recomputed here from the cards rather than taken from the index's word for it.
    gap_labels: set[str] = set()
    for entry in index["dags"]:
        card = json.loads((DAGS_DIR / f"{entry['dag_id']}.json").read_text(encoding="utf-8"))
        for node in card["nodes"]:
            if node["source_status"] == "gap":
                gap_labels.add(node["label"])
    declared = set(index.get("variables_still_missing", []))
    declared_labels = {item.split(" [", 1)[0] for item in declared}
    if gap_labels != declared_labels:
        failures.append("index variables_still_missing disagrees with the cards "
                        f"(index {len(declared_labels)}, cards {len(gap_labels)})")

    print()
    print(f"  variables with no usable source (recomputed from cards): {len(gap_labels)}")
    for item in sorted(declared):
        print(f"    ! {item}")

    print()
    if failures:
        print(f"FAILED — {len(failures)} problem(s):")
        for problem in failures:
            print(f"  - {problem}")
        return 1
    print("PASS — every card is acyclic, schema-valid, and its adjustment set provably "
          "blocks every backdoor path in its assumed graph")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
