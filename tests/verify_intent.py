"""Independent verification of the Stage 9 intent gate and its measured numbers.

The gate exists because two published refusal gates were failed by measurement: the decision was a
similarity score, so three of four out-of-scope questions were not refused (0.25) and one of two
reason-bearing questions did not retrieve its reason (0.5). The gate replaces the score with a
declared rule set, and the claim that it works has to be checkable by someone who does not trust
the harness. So this verifier re-derives the measurement from the artifacts, without importing
`app/intent_gate.py` or `scripts/eval_intent.py`:

  * **The questions are re-derived.** The held-out set is rebuilt from the eval spec, the registry
    index, the two seeds and the corpus — the same inputs the harness reads, filled by this file's
    own implementation of the declared rotations. A question that was added, dropped, reworded or
    re-labelled after the rules were frozen fails here.
  * **The rules are re-applied by a second implementation.** The decision procedure in
    `analysis/specs/intent_gate.yml` is read from the spec and executed here with this file's own
    matcher. A rule that was widened, or a priority that was moved, changes the decision and fails.
  * **The freeze is checked against git.** The rule spec as of the freeze commit must be byte-identical
    to the rule spec on disk, and the eval spec must *not* have existed at that commit. A rule edited
    after the questions were written is the failure the whole freeze discipline exists to prevent.
  * **Every metric and every `met` flag is recomputed** from the artifact's own question rows, and the
    gate's targets are read from the spec — so a target edited after measurement cannot keep its old
    verdict, and a number the verifier cannot reproduce fails.
  * **The published set is measured again, including the retrieval.** The gate is a refusal gate, so
    answerable recall@5 must be unchanged; the cosine is recomputed from the stored vectors here.

A missed *target* is not a verifier failure: a missed target is a finding to publish (the Stage 7
precedent — p = 0.0625 was published, not widened until it passed). What fails here is a number that
cannot be reproduced, a rule that moved after the questions were written, or a `met` flag that does
not match its own arithmetic.

Usage:
    python tests/verify_intent.py
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
GATE_SPEC_PATH = REPO_ROOT / "analysis" / "specs" / "intent_gate.yml"
EVAL_SPEC_PATH = REPO_ROOT / "analysis" / "specs" / "intent_gate_eval.yml"
INDEX_PATH = REPO_ROOT / "registry" / "dags" / "index.json"
STATE_SEED = REPO_ROOT / "dbt" / "seeds" / "raw_state.csv"
ADMIN_SEED = REPO_ROOT / "dbt" / "seeds" / "raw_administration.csv"
RAG_ROOT = REPO_ROOT / "registry" / "rag"

NON_WORD = re.compile(r"[^a-z0-9]+")
YEAR = re.compile(r"\b((?:19|20)\d{2})\b")


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def normalise(text: str) -> str:
    """The question as the rules see it — re-implemented from the spec's `decision.steps`."""
    lowered = str(text).lower()
    for mark in ("'", "’"):
        lowered = lowered.replace(mark, "")
    return " ".join(NON_WORD.sub(" ", lowered).split())


# ---------------------------------------------------------------------------------------------
# The rules, applied by this file's own matcher
# ---------------------------------------------------------------------------------------------
class SecondImplementation:
    """A second implementation of the spec's decision procedure.

    Written from `analysis/specs/intent_gate.yml` rather than imported from `app/intent_gate.py`,
    so that a change to the engine and a change to the spec cannot agree with each other by
    accident. The semantics it implements:

      * normalise, then evaluate the rules in ascending `priority`; the first rule whose conditions
        all hold decides;
      * `all_of` is a list of groups, each satisfied by any of its patterns; `any_of` is satisfied
        by any one of its groups; `none_of` may not match;
      * `year_window` compares the years the question names with the study window's start and the
        vintage year, both read from the artifacts;
      * a rule whose intent is not `answerable` falls back to `answerable` when its route does not
        resolve to exactly one existing chunk — a refusal without a citation is not a refusal.
    """

    def __init__(self, spec: dict, corpus: dict, window_start: str | None, vintage: str):
        self.rules = sorted(spec.get("rules") or [], key=lambda rule: rule["priority"])
        self.chunks = {chunk["chunk_id"]: chunk for chunk in corpus.get("chunks") or []}
        self.window_start_year = int(str(window_start)[:4]) if window_start else None
        self.vintage_year = int(str(vintage)[:4])

    def decide(self, question: str) -> tuple[str, str | None, str]:
        text = normalise(question)
        for rule in self.rules:
            if not self._holds(rule, text):
                continue
            route, status = self._route(rule)
            if rule["intent"] != "answerable" and status != "pinned":
                return "answerable", None, "unresolved"
            return rule["intent"], route, status
        return "answerable", None, "not_applicable"

    def _holds(self, rule: dict, text: str) -> bool:
        conditions = rule.get("conditions") or {}
        for group in conditions.get("all_of") or []:
            if not any(re.search(pattern, text) for pattern in group):
                return False
        any_of = conditions.get("any_of") or []
        if any_of and not any(any(re.search(pattern, text) for pattern in group) for group in any_of):
            return False
        for entry in conditions.get("none_of") or []:
            patterns = entry if isinstance(entry, list) else [entry]
            if any(re.search(pattern, text) for pattern in patterns):
                return False
        window = conditions.get("year_window") or rule.get("year_window")
        if window and not self._window(window, text):
            return False
        return True

    def _window(self, mode: str, text: str) -> bool:
        years = [int(year) for year in YEAR.findall(text)]
        if not years or self.window_start_year is None:
            return False
        if mode == "outside":
            return any(y < self.window_start_year or y > self.vintage_year for y in years)
        if mode == "future":
            return any(y > self.vintage_year for y in years)
        if mode == "past":
            return any(y < self.window_start_year for y in years)
        raise ValueError(f"unknown year_window mode {mode!r}")

    def _route(self, rule: dict) -> tuple[str | None, str]:
        route = rule.get("route")
        if route is None:
            return None, "not_applicable"
        if isinstance(route, str):
            return (route, "pinned") if route in self.chunks else (None, "unresolved")
        selector = route.get("selector")
        if selector == "chunk":
            chunk_id = route.get("chunk_id")
            return (chunk_id, "pinned") if chunk_id in self.chunks else (None, "unresolved")
        if selector == "section":
            document = str(route.get("document") or "")
            stem = Path(document).stem
            needle = str(route.get("heading_contains") or "").lower()
            prefix = f"doc:{stem}#"
            hits = [
                chunk_id
                for chunk_id, chunk in self.chunks.items()
                if chunk_id.startswith(prefix)
                and chunk_id.count("#") == 1
                and needle in str(chunk.get("title") or "").lower()
            ]
            return (hits[0], "pinned") if len(hits) == 1 else (None, "unresolved")
        return None, "unresolved"

    def parts_of(self, chunk_id: str) -> list[str]:
        return [cid for cid in self.chunks if cid == chunk_id or cid.startswith(f"{chunk_id}#p")]

    def chunk_text(self, chunk_id: str) -> str:
        return str(self.chunks.get(chunk_id, {}).get("text") or "")


# ---------------------------------------------------------------------------------------------
# The held-out set, re-derived
# ---------------------------------------------------------------------------------------------
def read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def rederive_questions(eval_spec: dict, index: dict, states: list[dict], admins: list[dict]) -> list[dict]:
    """Rebuild the held-out set from the spec's declared families, sources and rotations.

    The rotations are re-encoded here from the spec's prose rather than parsed out of it — a
    rotation the spec and the harness disagree about is a change to the measurement, and this file
    fails on it.
    """
    outcomes = index.get("outcomes") or []
    designs = index.get("designs") or []
    rows: list[dict] = []

    for family in eval_spec.get("mechanical") or []:
        family_id = family["id"]
        template = family["template"]
        built: list[dict] = []
        if family_id == "M1":
            for position, outcome in enumerate(outcomes):
                design = designs[position % len(designs)]
                built.append({
                    "question": template.format(outcome=outcome["label"], design=design["name"]),
                    "gold": f"card:{outcome['id']}__{design['id']}",
                })
        elif family_id == "M2":
            for outcome in outcomes[:6]:
                built.append({"question": template.format(outcome=outcome["label"]),
                              "gold": family["gold"]})
        elif family_id == "M3":
            for position in (0, 12, 24):
                built.append({"question": template.format(state=states[position]["state_name"]),
                              "gold": family["gold"]})
        elif family_id == "M4":
            for position in (1, 5, 9):
                built.append({"question": template.format(outcome=outcomes[position]["label"]),
                              "gold": family["gold"]})
        elif family_id == "M5":
            for position in (0, 3, 6, 9):
                built.append({"question": template.format(outcome=outcomes[position]["label"]),
                              "gold": family["gold"]})
        elif family_id == "M6":
            for position, admin in zip((2, 5, 8, 11), admins[:4]):
                built.append({
                    "question": template.format(admin=admin["president"],
                                                outcome=outcomes[position]["label"]),
                    "gold": family["gold"],
                })
        else:
            raise ValueError(f"no re-derivation for mechanical family {family_id!r}")

        for number, row in enumerate(built[: int(family["count"])], start=1):
            rows.append({
                "id": f"{family_id}_{number:02d}",
                "family": family["family"],
                "source": "mechanical",
                "question": row["question"],
                "expected_intent": family["intent"],
                "gold": row.get("gold"),
                "gold_scored": bool(family.get("gold_scored")),
                "needle": family.get("needle"),
                "expected_gap": None,
            })

    for item in eval_spec.get("authored") or []:
        rows.append({
            "id": item["id"],
            "family": "authored",
            "source": "authored",
            "question": item["question"],
            "expected_intent": item["intent"],
            "gold": item.get("gold"),
            "gold_scored": False,
            "needle": None,
            "expected_gap": None,
        })
    for item in eval_spec.get("probes") or []:
        rows.append({
            "id": item["id"],
            "family": "probe",
            "source": "probe",
            "question": item["question"],
            "expected_intent": item["intent"],
            "gold": item.get("gold"),
            "gold_scored": False,
            "needle": None,
            "expected_gap": item.get("expected_gap"),
        })
    return rows


# ---------------------------------------------------------------------------------------------
# The freeze, checked against git
# ---------------------------------------------------------------------------------------------
def git_show(commit: str, path: str) -> bytes | None:
    """The file's bytes at a commit, or None if it did not exist there."""
    try:
        out = subprocess.run(
            ["git", "show", f"{commit}:{path}"],
            cwd=REPO_ROOT,
            capture_output=True,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0:
        return None
    return out.stdout


def main() -> int:
    failures: list[str] = []

    if not GATE_SPEC_PATH.exists() or not EVAL_SPEC_PATH.exists():
        print("FAILED — the gate spec or the eval spec is missing")
        return 1

    gate_spec = yaml.safe_load(GATE_SPEC_PATH.read_text(encoding="utf-8"))
    eval_spec = yaml.safe_load(EVAL_SPEC_PATH.read_text(encoding="utf-8"))
    index = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    vintage = index["vintage_date"]
    rag_dir = RAG_ROOT / vintage
    artifact_path = rag_dir / "intent_eval.json"
    if not artifact_path.exists():
        print(f"FAILED — {artifact_path.relative_to(REPO_ROOT)} is missing — run scripts/eval_intent.py")
        return 1
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))

    corpus = json.loads((rag_dir / "corpus.json").read_text(encoding="utf-8"))
    eval_set = json.loads((rag_dir / "eval_set.json").read_text(encoding="utf-8"))
    quality_path = REPO_ROOT / "registry" / "quality" / vintage / "report.json"
    window_start = None
    if quality_path.exists():
        quality = json.loads(quality_path.read_text(encoding="utf-8"))
        window_start = (quality.get("study_window") or {}).get("start")

    # ---------------------------------------------------------------------------------------------
    # 1. The freeze: the rules have not moved since the questions were written
    # ---------------------------------------------------------------------------------------------
    freeze = eval_spec.get("authored_after")
    if not freeze:
        failures.append(
            "analysis/specs/intent_gate_eval.yml: no `authored_after` — the held-out set does not say which "
            "commit froze the rules, so the freeze cannot be checked"
        )
    else:
        frozen_bytes = git_show(freeze, "analysis/specs/intent_gate.yml")
        if frozen_bytes is None:
            failures.append(
                f"commit {freeze} does not exist, or carried no analysis/specs/intent_gate.yml — the freeze "
                "cannot be checked"
            )
        else:
            frozen_hash = hashlib.sha256(frozen_bytes.replace(b"\r\n", b"\n")).hexdigest()
            on_disk = sha256_of(GATE_SPEC_PATH)
            if frozen_hash != on_disk:
                failures.append(
                    f"the rule spec on disk ({on_disk[:12]}) is not the rule spec at the freeze commit "
                    f"{freeze} ({frozen_hash[:12]}) — the rules were changed after the held-out questions "
                    "were written, so the held-out numbers no longer measure what they say they measure"
                )
        if git_show(freeze, "analysis/specs/intent_gate_eval.yml") is not None:
            failures.append(
                f"the eval spec already existed at the freeze commit {freeze} — the questions must be "
                "written after the rules are frozen, not at the same time"
            )
        if artifact.get("specs", {}).get("gate", {}).get("frozen_at") != freeze:
            failures.append(
                f"the artifact records the rules frozen at "
                f"{artifact.get('specs', {}).get('gate', {}).get('frozen_at')!r} and the eval spec says "
                f"{freeze!r}"
            )

    # The artifact's own hashes must still describe the files on disk.
    for key, path in (("gate", GATE_SPEC_PATH), ("eval", EVAL_SPEC_PATH)):
        recorded = (artifact.get("specs") or {}).get(key) or {}
        if recorded.get("sha256") != sha256_of(path):
            failures.append(
                f"the artifact records sha256 {str(recorded.get('sha256'))[:12]} for {recorded.get('path')} "
                f"and the file hashes {sha256_of(path)[:12]} — the spec moved after the measurement"
            )
    if (artifact.get("corpus") or {}).get("sha256") != sha256_of(rag_dir / "corpus.json"):
        failures.append("the artifact records a corpus sha256 that does not match registry/rag/<vintage>/corpus.json")
    if (artifact.get("corpus") or {}).get("chunks") != len(corpus.get("chunks") or []):
        failures.append("the artifact's chunk count does not match the corpus on disk")

    # ---------------------------------------------------------------------------------------------
    # 2. The questions, re-derived
    # ---------------------------------------------------------------------------------------------
    questions = rederive_questions(eval_spec, index, read_csv(STATE_SEED), read_csv(ADMIN_SEED))
    published_rows = artifact.get("held_out", {}).get("questions") or []
    by_id = {row["id"]: row for row in published_rows}
    if len(by_id) != len(published_rows):
        failures.append("the artifact's held-out rows carry a duplicate id")
    if set(by_id) != {row["id"] for row in questions}:
        missing = sorted({row["id"] for row in questions} - set(by_id))
        extra = sorted(set(by_id) - {row["id"] for row in questions})
        if missing:
            failures.append(f"the artifact is missing held-out question(s) {missing} — the set was changed "
                            "after it was measured")
        if extra:
            failures.append(f"the artifact carries held-out question(s) {extra} that the eval spec does not "
                            "declare")
    for row in questions:
        published = by_id.get(row["id"])
        if published is None:
            continue
        if published.get("question") != row["question"]:
            failures.append(
                f"{row['id']}: the artifact's question text differs from the re-derived one — the question "
                "was reworded after the rules were frozen"
            )
        if published.get("expected_intent") != row["expected_intent"]:
            failures.append(
                f"{row['id']}: the artifact's expected intent is {published.get('expected_intent')!r} and the "
                f"eval spec says {row['expected_intent']!r} — a label moved after the measurement"
            )
        if published.get("gold") != row["gold"]:
            failures.append(f"{row['id']}: the artifact's gold is {published.get('gold')!r} and the spec "
                            f"derives {row['gold']!r}")

    # ---------------------------------------------------------------------------------------------
    # 3. The rules, re-applied
    # ---------------------------------------------------------------------------------------------
    engine = SecondImplementation(gate_spec, corpus, window_start, vintage)
    held_out = artifact.get("held_out") or {}
    recomputed_rows: list[dict] = []
    for row in questions:
        intent, route, status = engine.decide(row["question"])
        parts = engine.parts_of(route) if route else []
        carried = " ".join(engine.chunk_text(chunk_id) for chunk_id in parts)
        entry = {
            "id": row["id"],
            "intent": intent,
            "route": route,
            "route_status": status,
            "correct": intent == row["expected_intent"],
        }
        if row["gold_scored"] and row["gold"]:
            entry["route_matches_gold"] = route == row["gold"]
        if row.get("needle"):
            entry["needle_found"] = row["needle"] in carried
        recomputed_rows.append(entry)

    for entry in recomputed_rows:
        published = by_id.get(entry["id"])
        if published is None:
            continue
        for field in ("intent", "route", "route_status", "correct"):
            if published.get(field) != entry[field]:
                failures.append(
                    f"{entry['id']}: the artifact records {field}={published.get(field)!r} and this verifier's "
                    f"own implementation of the spec's rules gets {entry[field]!r}"
                )
        if "route_matches_gold" in entry and published.get("route_matches_gold") != entry["route_matches_gold"]:
            failures.append(
                f"{entry['id']}: the artifact records route_matches_gold="
                f"{published.get('route_matches_gold')!r} and the re-derived value is "
                f"{entry['route_matches_gold']!r}"
            )
        if "needle_found" in entry and published.get("needle_found") != entry["needle_found"]:
            failures.append(
                f"{entry['id']}: the artifact records needle_found={published.get('needle_found')!r} and the "
                f"re-derived value is {entry['needle_found']!r}"
            )

    # Every refusal must cite a chunk that exists, and the route must be in the corpus.
    for row in published_rows:
        if row.get("intent") in ("out_of_scope", "refusal_with_reason"):
            if not row.get("route"):
                failures.append(f"{row.get('id')}: the gate refused without a route")
            elif row["route"] not in {chunk["chunk_id"] for chunk in corpus.get("chunks") or []}:
                failures.append(f"{row.get('id')}: the refusal cites {row['route']!r}, which is not in the corpus")

    # ---------------------------------------------------------------------------------------------
    # 4. The metrics, recomputed from the artifact's own rows
    # ---------------------------------------------------------------------------------------------
    def fraction(numerator: int, denominator: int) -> float:
        return round(numerator / max(denominator, 1), 6)

    answerable = [row for row in published_rows if row.get("expected_intent") == "answerable"]
    out_of_scope = [row for row in published_rows if row.get("expected_intent") == "out_of_scope"]
    refusals = [row for row in published_rows if row.get("expected_intent") == "refusal_with_reason"]
    scored_golds = [row for row in published_rows if "route_matches_gold" in row]
    needles = [row for row in published_rows if "needle_found" in row]

    recomputed_metrics = {
        "n_questions": len(published_rows),
        "intent_accuracy": fraction(sum(1 for row in published_rows if row.get("correct")), len(published_rows)),
        "out_of_scope_refusal": fraction(
            sum(1 for row in out_of_scope if row.get("intent") == "out_of_scope"), len(out_of_scope)),
        "answerable_not_refused": fraction(
            sum(1 for row in answerable if row.get("intent") == "answerable"), len(answerable)),
        "refusal_route_resolved": fraction(
            sum(1 for row in refusals if row.get("route_status") == "pinned"), len(refusals)),
        "refusal_reason_cited": fraction(
            sum(1 for row in needles if row.get("needle_found")), len(needles)),
        "route_matches_gold": fraction(
            sum(1 for row in scored_golds if row.get("route_matches_gold")), len(scored_golds)),
    }
    published_metrics = held_out.get("metrics") or {}
    for key, value in recomputed_metrics.items():
        if published_metrics.get(key) != value:
            failures.append(
                f"held-out {key}: the artifact publishes {published_metrics.get(key)!r} and the verifier's "
                f"recomputation from the artifact's own rows gives {value!r}"
            )

    counts = held_out.get("counts") or {}
    for key, value in (("answerable", len(answerable)), ("out_of_scope", len(out_of_scope)),
                       ("refusal_with_reason", len(refusals)), ("n_scored_golds", len(scored_golds)),
                       ("n_needle_checks", len(needles))):
        if counts.get(key) != value:
            failures.append(f"held-out count {key}: the artifact says {counts.get(key)!r} and the rows say "
                            f"{value!r}")

    # The per-family breakdown, recomputed.
    by_family: dict[str, list[dict]] = {}
    for row in published_rows:
        by_family.setdefault(str(row.get("family")), []).append(row)
    declared_families = {entry.get("family"): entry for entry in held_out.get("per_family") or []}
    if set(declared_families) != set(by_family):
        failures.append(f"the artifact's families {sorted(declared_families)} do not match the rows' families "
                        f"{sorted(by_family)}")
    for name, rows in by_family.items():
        entry = declared_families.get(name)
        if entry is None:
            continue
        if entry.get("n") != len(rows):
            failures.append(f"family {name}: the artifact says n={entry.get('n')} and the rows say {len(rows)}")
        accuracy = fraction(sum(1 for row in rows if row.get("correct")), len(rows))
        if entry.get("intent_accuracy") != accuracy:
            failures.append(f"family {name}: the artifact's accuracy {entry.get('intent_accuracy')!r} and the "
                            f"recomputed {accuracy!r}")
        misses = sorted(row["id"] for row in rows if not row.get("correct"))
        if sorted(entry.get("misses") or []) != misses:
            failures.append(f"family {name}: the artifact's misses {entry.get('misses')} and the recomputed "
                            f"{misses}")

    # ---------------------------------------------------------------------------------------------
    # 5. The gate flags, against the targets declared in the spec
    # ---------------------------------------------------------------------------------------------
    declared_targets = gate_spec.get("gates") or {}
    for scope, block in (("held_out", held_out.get("gates") or {}),
                         ("published_set", (artifact.get("published_set") or {}).get("gates") or {})):
        for key, gate in block.items():
            target = declared_targets.get(key)
            if target is None:
                failures.append(f"{scope} gate {key!r} has no target in analysis/specs/intent_gate.yml")
                continue
            if gate.get("target") != target:
                failures.append(
                    f"{scope} gate {key!r}: the artifact's target is {gate.get('target')!r} and the spec declares "
                    f"{target!r} — a target edited after the measurement does not keep its old verdict"
                )
            measured = gate.get("measured")
            expected_met = None if measured is None else measured >= float(target)
            if gate.get("met") != expected_met:
                failures.append(
                    f"{scope} gate {key!r}: met={gate.get('met')!r} but {measured!r} against a target of "
                    f"{target!r} gives {expected_met!r}"
                )

    # Every target declared in the spec must be measured somewhere.
    for key in declared_targets:
        if key not in (held_out.get("gates") or {}) and key not in (
                (artifact.get("published_set") or {}).get("gates") or {}):
            failures.append(f"the spec declares a gate {key!r} that the artifact measures nowhere")

    # ---------------------------------------------------------------------------------------------
    # 6. The published set, measured again — including the retrieval
    # ---------------------------------------------------------------------------------------------
    published_block = artifact.get("published_set") or {}
    published_questions = eval_set.get("questions") or []
    published_rows_artifact = published_block.get("questions") or []
    if len(published_rows_artifact) != len(published_questions):
        failures.append(
            f"the artifact measures {len(published_rows_artifact)} published questions and the eval set holds "
            f"{len(published_questions)}"
        )
    rag_spec = yaml.safe_load((REPO_ROOT / "analysis" / "specs" / "rag.yml").read_text(encoding="utf-8"))
    k = int(rag_spec["retrieval"]["k"])

    # The retrieval is recomputed from the stored vectors, so "the gate did not change retrieval" is a
    # measurement rather than a claim.
    retrieved_by_id: dict[str, list[str]] = {}
    embeddings_path = rag_dir / rag_spec["output"]["embeddings"]
    try:
        import numpy as np
    except ImportError:
        np = None
    if np is None:
        print("  ! numpy is not importable — the published set's retrieval is not recomputed here")
    elif not embeddings_path.exists():
        print(f"  ! {embeddings_path.name} is absent — the published set's retrieval is not recomputed here")
    else:
        data = np.load(embeddings_path, allow_pickle=True)
        chunk_ids = [str(cid) for cid in data["chunk_ids"]]
        chunk_vectors = data["chunk_vectors"]
        question_ids = [str(qid) for qid in data["question_ids"]]
        query_vectors = data["query_vectors"]
        index_of = {qid: i for i, qid in enumerate(question_ids)}
        for row in published_questions:
            vector = query_vectors[index_of[row["id"]]]
            ordered = np.argsort(-(chunk_vectors @ vector))[:k]
            retrieved_by_id[row["id"]] = [chunk_ids[int(i)] for i in ordered]

    recomputed_published: list[dict] = []
    for row in published_questions:
        intent, route, status = engine.decide(row["question"])
        retrieved = retrieved_by_id.get(row["id"]) or []
        gold = set(row.get("gold_chunks") or [])
        first_gold = next((i + 1 for i, chunk_id in enumerate(retrieved) if chunk_id in gold), None) if gold else None
        parts = engine.parts_of(route) if route else []
        carried = " ".join(engine.chunk_text(chunk_id) for chunk_id in parts)
        needles = row.get("must_contain") or []
        recomputed_published.append({
            "id": row["id"],
            "type": row["type"],
            "intent": intent,
            "route": route,
            "route_status": status,
            "route_matches_cite": route == row.get("refusal_must_cite"),
            "carries_a_needle": bool(needles) and any(needle in carried for needle in needles),
            "first_gold_rank": first_gold,
        })

    by_pub_id = {row["id"]: row for row in published_rows_artifact}
    for entry in recomputed_published:
        published = by_pub_id.get(entry["id"])
        if published is None:
            failures.append(f"the artifact does not measure the published question {entry['id']!r}")
            continue
        for field in ("intent", "route", "route_status", "route_matches_cite", "carries_a_needle"):
            if published.get(field) != entry[field]:
                failures.append(
                    f"{entry['id']}: the artifact records {field}={published.get(field)!r} and the verifier's "
                    f"recomputation gives {entry[field]!r}"
                )
        if retrieved_by_id and published.get("first_gold_rank") != entry["first_gold_rank"]:
            failures.append(
                f"{entry['id']}: the artifact records first_gold_rank={published.get('first_gold_rank')!r} "
                f"and the recomputed cosine gives {entry['first_gold_rank']!r}"
            )

    pub_answerable = [row for row in recomputed_published if row["type"] == "answerable"]
    pub_out_of_scope = [row for row in recomputed_published if row["type"] == "out_of_scope"]
    pub_refusals = [row for row in recomputed_published if row["type"] == "refusal_with_reason"]
    pub_scored = [row for row in pub_answerable if row["first_gold_rank"] is not None]
    recomputed_pub_metrics = {
        "n_questions": len(recomputed_published),
        "out_of_scope_refusal": fraction(
            sum(1 for row in pub_out_of_scope if row["intent"] == "out_of_scope"), len(pub_out_of_scope)),
        "answerable_not_refused": fraction(
            sum(1 for row in pub_answerable if row["intent"] == "answerable"), len(pub_answerable)),
        "answerable_recall_at_5": fraction(len(pub_scored), len(pub_answerable)),
        "refusal_route_matches_citation": fraction(
            sum(1 for row in pub_refusals if row["route_matches_cite"]), len(pub_refusals)),
        "refusal_reason_cited": fraction(
            sum(1 for row in pub_refusals if row["carries_a_needle"]), len(pub_refusals)),
    }
    pub_metrics = published_block.get("metrics") or {}
    for key, value in recomputed_pub_metrics.items():
        if pub_metrics.get(key) != value:
            failures.append(
                f"published {key}: the artifact publishes {pub_metrics.get(key)!r} and the verifier's "
                f"recomputation gives {value!r}"
            )

    # The gate must not have changed retrieval: answerable recall@5 has to equal the published
    # retrieval evaluation's own answerable recall.
    retrieval_path = rag_dir / "retrieval_eval.json"
    if retrieval_path.exists():
        retrieval = json.loads(retrieval_path.read_text(encoding="utf-8"))
        published_recall = ((retrieval.get("metrics") or {}).get("embedding") or {}).get("recall_at_k")
        if published_recall is not None and pub_metrics.get("answerable_recall_at_5") is not None:
            # The published figure is over all gold-bearing questions; the gate's is over answerable ones.
            # What must hold is that the gate refuses nothing answerable, so the two answerable sets agree.
            if pub_metrics["answerable_not_refused"] != 1.0:
                failures.append(
                    "the gate refused an answerable published question, so the two recall figures are not "
                    "comparable and the retrieval is no longer unchanged"
                )
        published_oos = ((retrieval.get("metrics") or {}).get("embedding") or {}).get("out_of_scope_refusal")
        if published_oos is not None and pub_metrics.get("out_of_scope_refusal") is not None:
            if pub_metrics["out_of_scope_refusal"] <= published_oos:
                failures.append(
                    f"the gate's out-of-scope refusal ({pub_metrics['out_of_scope_refusal']}) does not improve "
                    f"on the published score-based refusal ({published_oos}) — the gate exists to replace it"
                )

    # ---------------------------------------------------------------------------------------------
    # 7. The known gaps are carried into the artifact
    # ---------------------------------------------------------------------------------------------
    declared_gaps = {gap.get("id"): gap for gap in gate_spec.get("known_gaps") or []}
    artifact_gaps = {gap.get("id"): gap for gap in artifact.get("known_gaps") or []}
    if set(declared_gaps) != set(artifact_gaps):
        failures.append(f"the artifact's known gaps {sorted(artifact_gaps)} do not match the spec's "
                        f"{sorted(declared_gaps)}")
    for gap_id, gap in declared_gaps.items():
        carried = artifact_gaps.get(gap_id) or {}
        if carried.get("status") != gap.get("status"):
            failures.append(f"known gap {gap_id}: the artifact says status {carried.get('status')!r} and the "
                            f"spec says {gap.get('status')!r}")

    # A probe's expected gap must be a gap the spec declares.
    for row in questions:
        gap_id = row.get("expected_gap")
        if gap_id and gap_id not in declared_gaps:
            failures.append(f"{row['id']} is labelled with the gap {gap_id!r}, which the spec does not declare")

    # Every miss in the held-out set must be accounted for: either the question is a probe that
    # declares the gap it exposes, or the miss is a real finding that the docs must carry.
    misses = [row for row in published_rows if not row.get("correct")]
    labelled = {row["id"] for row in misses if row.get("expected_gap")}
    for row in misses:
        if row["id"] not in labelled:
            print(f"  note: {row['id']} ({row.get('expected_intent')}) was answered {row.get('intent')!r} by "
                  f"rule {row.get('rule_id')!r} — an unlabelled miss, which the narrative has to carry")

    # ---------------------------------------------------------------------------------------------
    # 8. The rules in the artifact are the rules in the spec
    # ---------------------------------------------------------------------------------------------
    spec_rules = {rule["id"]: rule for rule in gate_spec.get("rules") or []}
    artifact_rules = {rule.get("id"): rule for rule in artifact.get("rules") or []}
    if set(spec_rules) != set(artifact_rules):
        failures.append(f"the artifact's rules {sorted(artifact_rules)} do not match the spec's "
                        f"{sorted(spec_rules)}")
    for rule_id, rule in spec_rules.items():
        carried = artifact_rules.get(rule_id) or {}
        if carried.get("priority") != rule.get("priority"):
            failures.append(f"rule {rule_id}: the artifact records priority {carried.get('priority')!r} and the "
                            f"spec declares {rule.get('priority')!r}")
        if carried.get("intent") != rule.get("intent"):
            failures.append(f"rule {rule_id}: the artifact records intent {carried.get('intent')!r} and the spec "
                            f"declares {rule.get('intent')!r}")

    # ---------------------------------------------------------------------------------------------
    # 9. The narrative quotes the artifact — prose that is not derived is prose that drifts
    # ---------------------------------------------------------------------------------------------
    narrative = REPO_ROOT / "docs" / "intent.md"
    if not narrative.exists():
        failures.append("docs/intent.md: missing — the gate's numbers would have no prose home")
    else:
        prose = narrative.read_text(encoding="utf-8")
        needles = [
            (str(recomputed_metrics["n_questions"]), "the held-out set size"),
            (str(len(answerable)), "the answerable count"),
            (str(len(out_of_scope)), "the out-of-scope count"),
            (str(len(refusals)), "the refusal-with-reason count"),
            (f"{recomputed_metrics['intent_accuracy']:.3f}", "the held-out intent accuracy"),
            (f"{recomputed_metrics['out_of_scope_refusal']:.3f}", "the held-out out-of-scope refusal"),
            (f"{recomputed_metrics['answerable_not_refused']:.3f}", "the held-out answerable-kept rate"),
            (f"{recomputed_metrics['refusal_route_resolved']:.3f}", "the held-out route resolution"),
            (f"{recomputed_metrics['refusal_reason_cited']:.3f}", "the held-out reason-cited rate"),
            (f"{recomputed_metrics['route_matches_gold']:.3f}", "the held-out gold-route match rate"),
            (f"{recomputed_pub_metrics['out_of_scope_refusal']:.3f}", "the published out-of-scope refusal"),
            (f"{recomputed_pub_metrics['refusal_reason_cited']:.3f}", "the published reason-cited rate"),
            (f"{recomputed_pub_metrics['answerable_recall_at_5']:.3f}", "the published answerable recall@5"),
        ]
        for needle, label in needles:
            if needle not in prose:
                failures.append(f"docs/intent.md: does not quote {label} ({needle}) — the page has drifted "
                                "from the artifact it describes")
        # Every miss is a finding the page has to carry, by id — a page that stops naming one has
        # stopped publishing it.
        for row in published_rows:
            if not row.get("correct") and row["id"] not in prose:
                failures.append(f"docs/intent.md: does not name the missed question {row['id']} — a miss "
                                "that is not written down is a miss that was tuned away")
        # Every declared gap is carried into the narrative, because an undeclared gap reads as passing.
        for gap_id in declared_gaps:
            if gap_id not in prose:
                failures.append(f"docs/intent.md: does not carry the known gap {gap_id}")

    # ---------------------------------------------------------------------------------------------
    print(f"gate spec     : {len(spec_rules)} rules, frozen at {freeze}, unchanged since")
    print(f"held out      : {len(published_rows)} questions re-derived from the artifacts "
          f"({len(answerable)} answerable, {len(out_of_scope)} out of scope, {len(refusals)} refusals)")
    print(f"intent        : accuracy {recomputed_metrics['intent_accuracy']:.3f}, out-of-scope refused "
          f"{recomputed_metrics['out_of_scope_refusal']:.3f}, answerable kept "
          f"{recomputed_metrics['answerable_not_refused']:.3f}, reason cited "
          f"{recomputed_metrics['refusal_reason_cited']:.3f}")
    print(f"published     : out-of-scope refused {recomputed_pub_metrics['out_of_scope_refusal']:.3f}, "
          f"answerable kept {recomputed_pub_metrics['answerable_not_refused']:.3f}, answerable recall@{k} "
          f"{recomputed_pub_metrics['answerable_recall_at_5']:.3f}")
    print(f"narrative     : docs/intent.md quotes the measured rates, every miss by id and every declared gap")
    for scope, block in (("held out", held_out.get("gates") or {}),
                         ("published", published_block.get("gates") or {})):
        for key, gate in block.items():
            verdict = "met" if gate.get("met") else "MISSED"
            print(f"  {scope:<10}: {key:<28} {gate.get('measured')} against {gate.get('target')} — {verdict}")
    print()
    if failures:
        print(f"FAILED — {len(failures)} problem(s):")
        for problem in failures[:40]:
            print(f"  - {problem}")
        if len(failures) > 40:
            print(f"  … and {len(failures) - 40} more")
        return 1
    print("PASS — the held-out set re-derives from the artifacts, the rules re-apply to the same decisions "
          "under a second implementation, the freeze holds against git, and every metric and gate flag is "
          "recomputed from the artifact's own rows")
    return 0


if __name__ == "__main__":
    sys.exit(main())
