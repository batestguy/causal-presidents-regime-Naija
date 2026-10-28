"""Measure the intent gate: the held-out set it was not written against, and the published set.

The gate's rules were frozen before the held-out questions existed (`analysis/specs/intent_gate.yml`
records the freeze). This harness is what makes that claim testable:

  * it rebuilds the held-out set from the artifacts and the eval spec — the mechanical families are
    templates filled from the registry, the seeds and the corpus, and the expected intent comes with
    the template rather than from anybody's opinion about a rule;
  * it applies the gate to every question and scores the decision against the expected intent;
  * it measures the gate over the published eval set as well, where the two failed refusal gates were
    measured, so the two numbers can be compared like for like;
  * it writes one artifact, `registry/rag/<vintage>/intent_eval.json`, with the questions, the
    decisions, the metrics and the gates.

Nothing here decides a refusal. The harness measures; the rules decide.

Usage:
    python scripts/eval_intent.py
"""

from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
GATE_SPEC_PATH = REPO_ROOT / "analysis/specs/intent_gate.yml"
INDEX_PATH = REPO_ROOT / "registry/dags/index.json"
STATE_SEED = REPO_ROOT / "dbt/seeds/raw_state.csv"
ADMIN_SEED = REPO_ROOT / "dbt/seeds/raw_administration.csv"
SCHEMA_VERSION = 2


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_sha() -> str | None:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=20,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout.strip() or None


def read_states() -> list[dict]:
    with STATE_SEED.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def read_administrations() -> list[dict]:
    with ADMIN_SEED.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


# ---------------------------------------------------------------------------------------------
# The held-out set — mechanical families, then the authored questions, then the probes
# ---------------------------------------------------------------------------------------------
def build_mechanical(family: dict, index: dict, states: list[dict], admins: list[dict]) -> list[dict]:
    """Fill a family's template from the artifacts, in the order the spec declares."""
    outcomes = index.get("outcomes") or []
    designs = index.get("designs") or []
    family_id = family["id"]
    rows: list[dict] = []

    if family_id == "M1":
        offset = int(family.get("design_offset", 0))
        for position, outcome in enumerate(outcomes):
            design = designs[(position + offset) % len(designs)]
            rows.append({
                "question": family["template"].format(outcome=outcome["label"], design=design["name"]),
                "gold": f"card:{outcome['id']}__{design['id']}",
            })
    elif family_id == "M2":
        positions = family.get("indices") or list(range(6))
        for position in positions:
            rows.append({"question": family["template"].format(outcome=outcomes[position]["label"]),
                         "gold": family["gold"]})
    elif family_id == "M3":
        positions = family.get("indices") or [0, 12, 24]
        for position in positions:
            rows.append({"question": family["template"].format(state=states[position]["state_name"]),
                         "gold": family["gold"]})
    elif family_id == "M4":
        positions = family.get("indices") or [1, 5, 9]
        for position in positions:
            rows.append({"question": family["template"].format(outcome=outcomes[position]["label"]),
                         "gold": family["gold"]})
    elif family_id == "M5":
        positions = family.get("indices") or [0, 3, 6, 9]
        for position in positions:
            rows.append({"question": family["template"].format(outcome=outcomes[position]["label"]),
                         "gold": family["gold"]})
    elif family_id == "M6":
        positions = family.get("indices") or [2, 5, 8, 11]
        admin_positions = family.get("admin_indices") or [0, 1, 2, 3]
        for position, admin_position in zip(positions, admin_positions):
            rows.append({"question": family["template"].format(admin=admins[admin_position]["president"],
                                                               outcome=outcomes[position]["label"]),
                         "gold": family["gold"]})
    else:
        raise ValueError(f"no generator for mechanical family {family_id!r}")

    return [
        {
            "id": f"{family_id}_{number:02d}",
            "family": family["family"],
            "source": "mechanical",
            "question": row["question"],
            "expected_intent": family["intent"],
            "gold": row.get("gold"),
            "gold_scored": bool(family.get("gold_scored")),
            "needle": family.get("needle"),
            "expected_gap": None,
        }
        for number, row in enumerate(rows[: int(family["count"])], start=1)
    ]


def build_regression(eval_spec: dict) -> list[dict]:
    """The previously seen cases: checked, and never counted in the held-out metrics."""
    return [
        {
            "id": item["id"],
            "family": "regression",
            "source": "regression",
            "question": item["question"],
            "expected_intent": item["intent"],
            "gold": None,
            "gold_scored": False,
            "needle": None,
            "expected_gap": None,
        }
        for item in eval_spec.get("regression") or []
    ]


def build_authored(eval_spec: dict) -> list[dict]:
    rows = []
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
# Scoring
# ---------------------------------------------------------------------------------------------
def score_held_out(gate, questions: list[dict]) -> tuple[dict, list[dict]]:
    detail = []
    for row in questions:
        decision = gate.decide(row["question"])
        parts = gate.parts_of(decision.route) if decision.route else []
        carried = " ".join(gate.chunk_text(chunk_id) for chunk_id in parts)
        entry = {
            "id": row["id"],
            "family": row["family"],
            "question": row["question"],
            "expected_intent": row["expected_intent"],
            "intent": decision.intent,
            "rule_id": decision.rule_id,
            "route": decision.route,
            "route_status": decision.route_status,
            "reason": decision.reason,
            "expected_gap": row["expected_gap"],
            "gold": row["gold"],
            "gold_scored": row["gold_scored"],
            "correct": decision.intent == row["expected_intent"],
        }
        if row["gold_scored"] and row["gold"]:
            entry["route_matches_gold"] = decision.route == row["gold"]
            if row.get("needle"):
                entry["needle"] = row["needle"]
                entry["needle_found"] = row["needle"] in carried
        detail.append(entry)

    total = len(detail)
    answerable = [row for row in detail if row["expected_intent"] == "answerable"]
    out_of_scope = [row for row in detail if row["expected_intent"] == "out_of_scope"]
    refusals = [row for row in detail if row["expected_intent"] == "refusal_with_reason"]
    scored_golds = [row for row in detail if row["gold_scored"] and "route_matches_gold" in row]
    needles = [row for row in detail if "needle_found" in row]

    metrics = {
        "n_questions": total,
        "intent_accuracy": round(sum(1 for row in detail if row["correct"]) / max(total, 1), 6),
        "out_of_scope_refusal": round(
            sum(1 for row in out_of_scope if row["intent"] == "out_of_scope") / max(len(out_of_scope), 1), 6
        ),
        "answerable_not_refused": round(
            sum(1 for row in answerable if row["intent"] == "answerable") / max(len(answerable), 1), 6
        ),
        "refusal_route_resolved": round(
            sum(1 for row in refusals if row["route_status"] == "pinned") / max(len(refusals), 1), 6
        ),
        "refusal_reason_cited": round(
            sum(1 for row in needles if row["needle_found"]) / max(len(needles), 1), 6
        ),
        "route_matches_gold": round(
            sum(1 for row in scored_golds if row["route_matches_gold"]) / max(len(scored_golds), 1), 6
        ),
        "counts": {
            "answerable": len(answerable),
            "out_of_scope": len(out_of_scope),
            "refusal_with_reason": len(refusals),
            "n_scored_golds": len(scored_golds),
            "n_needle_checks": len(needles),
        },
    }

    families = []
    for name in sorted({row["family"] for row in detail}):
        rows = [row for row in detail if row["family"] == name]
        families.append({
            "family": name,
            "n": len(rows),
            "intent_accuracy": round(sum(1 for row in rows if row["correct"]) / max(len(rows), 1), 6),
            "misses": [row["id"] for row in rows if not row["correct"]],
        })

    return {"metrics": metrics, "families": families}, detail


def score_regression(gate, questions: list[dict]) -> dict:
    """The seen cases, scored on intent and reported on their own."""
    rows = []
    for row in questions:
        decision = gate.decide(row["question"])
        rows.append({
            "id": row["id"],
            "question": row["question"],
            "expected_intent": row["expected_intent"],
            "intent": decision.intent,
            "rule_id": decision.rule_id,
            "correct": decision.intent == row["expected_intent"],
        })
    n = len(rows)
    return {
        "what_this_is": "previously seen questions, checked after the change that they motivated; "
                        "not a held-out measurement",
        "counts": {"n": n},
        "accuracy": round(sum(1 for row in rows if row["correct"]) / max(n, 1), 6),
        "misses": [row["id"] for row in rows if not row["correct"]],
        "questions": rows,
    }


def measure_published(gate, eval_set: dict, corpus: dict, out_dir: Path, rag_spec: dict) -> tuple[dict, list[dict]]:
    """The published set, under the gate — the two failed gates, measured the same way."""
    rows = eval_set["questions"]
    k = int(rag_spec["retrieval"]["k"])
    scope_ids = {chunk["chunk_id"] for chunk in corpus["chunks"] if chunk.get("doc_type") == "scope"}

    scores: dict[str, list[tuple[str, float]]] = {}
    retrieval_note = "not measured: no embeddings beside the corpus"
    try:
        import numpy as np
    except ImportError:
        np = None
    if np is not None:
        embeddings_path = out_dir / rag_spec["output"]["embeddings"]
        if embeddings_path.exists():
            data = np.load(embeddings_path, allow_pickle=True)
            chunk_ids = [str(cid) for cid in data["chunk_ids"]]
            chunk_vectors = data["chunk_vectors"]
            question_ids = [str(qid) for qid in data["question_ids"]]
            query_vectors = data["query_vectors"]
            if chunk_ids == [chunk["chunk_id"] for chunk in corpus["chunks"]]:
                index_of = {qid: i for i, qid in enumerate(question_ids)}
                for row in rows:
                    vector = query_vectors[index_of[row["id"]]]
                    ordered = np.argsort(-(chunk_vectors @ vector))[:k]
                    scores[row["id"]] = [
                        (chunk_ids[int(i)], float(chunk_vectors[int(i)] @ vector)) for i in ordered
                    ]
                retrieval_note = f"measured: cosine over the committed vectors, k = {k}"
            else:
                retrieval_note = "not measured: embeddings.npz is out of step with corpus.json"
        else:
            retrieval_note = "not measured: no embeddings.npz beside the corpus"

    detail = []
    for row in rows:
        decision = gate.decide(row["question"])
        retrieved = scores.get(row["id"]) or []
        ids = [chunk_id for chunk_id, _ in retrieved]
        gold = set(row.get("gold_chunks") or [])
        first_gold = next((i + 1 for i, chunk_id in enumerate(ids) if chunk_id in gold), None) if gold else None
        parts = gate.parts_of(decision.route) if decision.route else []
        carried = " ".join(gate.chunk_text(chunk_id) for chunk_id in parts)
        needles = row.get("must_contain") or []
        entry = {
            "id": row["id"],
            "type": row["type"],
            "question": row["question"],
            "intent": decision.intent,
            "rule_id": decision.rule_id,
            "route": decision.route,
            "route_status": decision.route_status,
            "expected_refusal_cite": row.get("refusal_must_cite"),
            "route_matches_cite": decision.route == row.get("refusal_must_cite"),
            "carries_a_needle": bool(needles) and any(needle in carried for needle in needles),
            "first_gold_rank": first_gold,
            "retrieved": [{"chunk_id": chunk_id, "score": round(score, 6)} for chunk_id, score in retrieved],
        }
        detail.append(entry)

    answerable = [row for row in detail if row["type"] == "answerable"]
    out_of_scope = [row for row in detail if row["type"] == "out_of_scope"]
    refusals = [row for row in detail if row["type"] == "refusal_with_reason"]
    scored = [row for row in answerable if row["first_gold_rank"] is not None]
    scoped = [row for row in out_of_scope if row["intent"] == "out_of_scope"]

    metrics = {
        "n_questions": len(detail),
        "out_of_scope_refusal": round(len(scoped) / max(len(out_of_scope), 1), 6),
        "answerable_not_refused": round(
            sum(1 for row in answerable if row["intent"] == "answerable") / max(len(answerable), 1), 6
        ),
        "answerable_recall_at_5": round(len(scored) / max(len(answerable), 1), 6),
        "refusal_route_matches_citation": round(
            sum(1 for row in refusals if row["route_matches_cite"]) / max(len(refusals), 1), 6
        ),
        "refusal_reason_cited": round(
            sum(1 for row in refusals if row["carries_a_needle"]) / max(len(refusals), 1), 6
        ),
        "retrieval": retrieval_note,
        "scope_chunks": sorted(scope_ids),
        "counts": {
            "answerable": len(answerable),
            "out_of_scope": len(out_of_scope),
            "refusal_with_reason": len(refusals),
        },
    }
    return {"metrics": metrics}, detail


def gates_for(declared: dict, metrics: dict, keys: list[str]) -> dict:
    gates = {}
    for key in keys:
        target = declared.get(key)
        measured = metrics.get(key)
        gates[key] = {
            "target": target,
            "measured": measured,
            "met": None if measured is None or target is None else measured >= float(target),
        }
    return gates


def main(argv: list[str] | None = None) -> int:
    sys.path.insert(0, str(REPO_ROOT))
    from app.intent_gate import load_gate  # noqa: E402  (the path has to be set first)

    gate_spec = yaml.safe_load(GATE_SPEC_PATH.read_text(encoding="utf-8"))
    # The gate spec names the held-out set, so a new version of the questions is one field's change and
    # the harness cannot measure a set the rules were not frozen against.
    eval_spec_path = REPO_ROOT / gate_spec["eval_spec"]
    eval_spec = yaml.safe_load(eval_spec_path.read_text(encoding="utf-8"))
    rag_spec = yaml.safe_load((REPO_ROOT / "analysis/specs/rag.yml").read_text(encoding="utf-8"))
    index = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    vintage = index["vintage_date"]
    out_dir = REPO_ROOT / "registry/rag" / vintage
    corpus = json.loads((out_dir / "corpus.json").read_text(encoding="utf-8"))
    eval_set = json.loads((out_dir / "eval_set.json").read_text(encoding="utf-8"))

    gate = load_gate(REPO_ROOT)

    questions: list[dict] = []
    for family in eval_spec.get("mechanical") or []:
        questions.extend(build_mechanical(family, index, read_states(), read_administrations()))
    questions.extend(build_authored(eval_spec))
    regression_questions = build_regression(eval_spec)

    held_out, held_out_detail = score_held_out(gate, questions)
    regression = score_regression(gate, regression_questions)
    published, published_detail = measure_published(gate, eval_set, corpus, out_dir, rag_spec)

    declared_gates = gate_spec.get("gates") or {}
    held_out_gates = gates_for(
        declared_gates,
        held_out["metrics"],
        ["intent_accuracy", "out_of_scope_refusal", "answerable_not_refused",
         "refusal_route_resolved", "refusal_reason_cited"],
    )
    published_gates = gates_for(
        declared_gates,
        published["metrics"],
        ["out_of_scope_refusal", "answerable_not_refused", "refusal_reason_cited"],
    )

    document = {
        "schema_version": SCHEMA_VERSION,
        "layer": "Stage 9 — the pre-retrieval intent gate",
        "vintage": vintage,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "generator": {
            "script": "scripts/eval_intent.py",
            "spec": gate_spec["spec_path"],
            "eval_spec": eval_spec["spec_path"],
            "git_sha": git_sha(),
        },
        "specs": {
            "gate": {
                "path": gate_spec["spec_path"],
                "sha256": sha256_of(GATE_SPEC_PATH),
                "frozen_at": eval_spec.get("authored_after"),
            },
            "eval": {
                "path": eval_spec["spec_path"],
                "sha256": sha256_of(eval_spec_path),
                "frozen_at": eval_spec.get("questions_frozen_at"),
            },
        },
        "corpus": {
            "path": f"registry/rag/{vintage}/corpus.json",
            "sha256": sha256_of(out_dir / "corpus.json"),
            "chunks": len(corpus["chunks"]),
            "vintage": corpus["vintage"],
        },
        "rules": [
            {"id": rule["id"], "priority": rule["priority"], "intent": rule["intent"],
             "implements": rule.get("implements")}
            for rule in sorted(gate_spec.get("rules") or [], key=lambda rule: rule["priority"])
        ],
        "held_out": {
            "what_this_is": "the questions the rules were frozen before; the rules are not tuned on it",
            "counts": held_out["metrics"]["counts"],
            "metrics": {key: value for key, value in held_out["metrics"].items() if key != "counts"},
            "gates": held_out_gates,
            "per_family": held_out["families"],
            "questions": held_out_detail,
        },
        "regression": regression,
        "published_set": {
            "what_this_is": "the 22 published questions, measured under the gate; the set the rules "
                            "were written against, so not a generalisation estimate",
            "path": f"registry/rag/{vintage}/eval_set.json",
            "counts": published["metrics"]["counts"],
            "metrics": {key: value for key, value in published["metrics"].items() if key != "counts"},
            "gates": published_gates,
            "questions": published_detail,
        },
        "known_gaps": [
            {"id": gap["id"], "scope_clause": gap.get("scope_clause"), "status": gap.get("status"),
             "why": gap.get("why")}
            for gap in gate_spec.get("known_gaps") or []
        ],
    }

    out_path = out_dir / "intent_eval.json"
    out_path.write_text(json.dumps(document, indent=1, ensure_ascii=False) + "\n",
                        encoding="utf-8", newline="\n")

    print(f"intent eval: {out_path.relative_to(REPO_ROOT).as_posix()}")
    metrics = document["held_out"]["metrics"]
    print(f"  held out   : {metrics['n_questions']} questions, intent accuracy "
          f"{metrics['intent_accuracy']:.3f}, out-of-scope refused {metrics['out_of_scope_refusal']:.3f}, "
          f"answerable kept {metrics['answerable_not_refused']:.3f}, "
          f"reason cited {metrics['refusal_reason_cited']:.3f}")
    published_metrics = document["published_set"]["metrics"]
    k = int(rag_spec["retrieval"]["k"])
    print(f"  published  : out-of-scope refused {published_metrics['out_of_scope_refusal']:.3f}, "
          f"answerable kept {published_metrics['answerable_not_refused']:.3f}, "
          f"answerable recall@{k} {published_metrics['answerable_recall_at_5']:.3f}, "
          f"refusal route matches the declared citation "
          f"{published_metrics['refusal_route_matches_citation']:.3f}")
    print(f"  regression : {regression['counts']['n']} seen cases, intent accuracy "
          f"{regression['accuracy']:.3f}" + (f" — misses {', '.join(regression['misses'])}"
                                               if regression["misses"] else ""))
    for family in document["held_out"]["per_family"]:
        if family["misses"]:
            print(f"  miss       : {family['family']} — {', '.join(family['misses'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
