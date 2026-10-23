"""Measure the answer layer: what it answers, what R-04 makes it refuse, and on what citation.

The intent gate decides whether the corpus may answer a question and pins the chunk a refusal must quote.
This harness runs the layer over the two question sets that exist — the 22 published questions and the 22
answerable held-out questions — and writes one artifact recording, per question, the gate's intent, the
layer's status, the post-check's parts, the citation and the passages used.

It decides nothing itself. The gate decides the intent, the contract decides the post-check, and the layer
assembles. This script measures.

Usage:
    python scripts/eval_answer.py
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
RAG_SPEC_PATH = REPO_ROOT / "analysis/specs/rag.yml"
GATE_SPEC_PATH = REPO_ROOT / "analysis/specs/intent_gate.yml"
INDEX_PATH = REPO_ROOT / "registry/dags/index.json"
SCHEMA_VERSION = 1
NUMBER = re.compile(r"[−+\-]?\d[\d,]*(?:\.\d+)?")


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_sha() -> str | None:
    try:
        out = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT,
                             capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout.strip() or None


def numbers_of(text: str) -> set[str]:
    return {match.replace(",", "") for match in NUMBER.findall(text)}


def answer_body(text: str) -> str:
    """The answer's own words, without the question it repeats and the citation it carries.

    The question is the reader's, not the corpus's: "Under-5 mortality" carries a 5, and "in 2012"
    carries a year. The citation line is metadata, and its vintage date carries a year too. Neither is
    a number the answer quotes from a chunk, so both are stripped before the numbers are counted.
    """
    return "\n".join(line for line in str(text).splitlines()
                     if not line.startswith(("**Question:**", "**Citation:**")))


def plain_body(text: str) -> str:
    """The plain reading's own words, without the line that says where the answer comes from."""
    return "\n".join(line for line in str(text).splitlines()
                     if not line.startswith("**Where this comes from:**"))


def main() -> int:
    sys.path.insert(0, str(REPO_ROOT))
    from app.answer_layer import load_layer  # noqa: E402

    rag_spec = yaml.safe_load(RAG_SPEC_PATH.read_text(encoding="utf-8"))
    gate_spec = yaml.safe_load(GATE_SPEC_PATH.read_text(encoding="utf-8"))
    index = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    vintage = index["vintage_date"]
    rag_dir = REPO_ROOT / "registry/rag" / vintage
    corpus = json.loads((rag_dir / "corpus.json").read_text(encoding="utf-8"))
    eval_set = json.loads((rag_dir / "eval_set.json").read_text(encoding="utf-8"))
    intent_eval = json.loads((rag_dir / "intent_eval.json").read_text(encoding="utf-8"))
    chunks = {chunk["chunk_id"]: chunk for chunk in corpus["chunks"]}

    layer = load_layer(REPO_ROOT)
    k = int((rag_spec.get("retrieval") or {}).get("k") or 5)
    contract = rag_spec["answer_contract"]
    shapes = contract.get("shapes") or {}

    rows: list[dict] = []
    seen: set[str] = set()

    def add(question_id: str, question: str, source: str, expected_intent: str | None,
            needles: list[str] | None = None) -> None:
        if question_id in seen:
            return
        seen.add(question_id)
        answer = layer.answer(question)
        parent = (answer.chunks_used or [None])[0]
        cited_text = ""
        if answer.status == "answered" and parent:
            # Every chunk the answer cites, not only the parent's parts: the answer may borrow its
            # assumption or its caveats from another chunk, and it cites that chunk too.
            cited_ids: list[str] = []
            for chunk_id in answer.chunks_used:
                cited_ids.extend(layer.gate.parts_of(chunk_id.split("#p", 1)[0]))
            cited_text = " ".join(str(chunks.get(cid, {}).get("text") or "")
                                  for cid in dict.fromkeys(cited_ids))
        elif answer.route and answer.route in chunks:
            cited_text = " ".join(str(cid_text) for cid_text in
                                  [chunks[answer.route].get("text") or ""])
        quoted = numbers_of(answer_body(answer.text))
        cited_numbers = numbers_of(cited_text)
        plain_text = (answer.plain or {}).get("text") or ""
        plain_quoted = numbers_of(plain_body(plain_text)) if plain_text else set()
        wanted = list(needles or [])
        found = [needle for needle in wanted if needle in answer.text]
        rows.append({
            "id": question_id,
            "set": source,
            "question": question,
            "expected_intent": expected_intent,
            "intent": answer.intent,
            "rule_id": answer.rule_id,
            "route": answer.route,
            "status": answer.status,
            "shape": answer.shape,
            "refusal_code": answer.refusal_code,
            "check": answer.check,
            "citation": answer.citation,
            "chunks_used": answer.chunks_used,
            "needles": {
                "required": wanted,
                "satisfied": found,
                "missing": [needle for needle in wanted if needle not in found],
                "all_satisfied": bool(wanted) and len(found) == len(wanted),
            },
            "numbers_quoted": sorted(quoted),
            "numbers_absent_from_citation": sorted(
                number for number in quoted if number not in cited_numbers
            ) if cited_text else [],
            "plain_numbers_absent_from_citation": sorted(
                number for number in plain_quoted if number not in cited_numbers
            ) if answer.status == "answered" and cited_text else [],
            "text": answer.text,
            "plain": answer.plain,
        })

    for question in eval_set["questions"]:
        if question["type"] == "answerable":
            add(question["id"], question["question"], "published", "answerable",
                question.get("must_contain"))
    for question in intent_eval["held_out"]["questions"]:
        if question["expected_intent"] == "answerable":
            add(f"heldout_{question['id']}", question["question"], "held_out", "answerable")

    def parts_of(row: dict) -> tuple[list[str], list[str]]:
        """The contract's required and forbidden parts for the row's shape."""
        spec = shapes.get(row.get("shape") or "") or {}
        return list(spec.get("requires") or []), list(spec.get("forbids") or [])

    def summarise(rows_: list[dict]) -> dict:
        n = len(rows_)
        answered = [row for row in rows_ if row["status"] == "answered"]
        refused = [row for row in rows_ if row["status"] == "refused"]
        declined = [row for row in rows_ if row["status"] == "declined"]
        parts = {key: sum(1 for row in answered if row["check"].get(key)) for key in
                 ("interval", "reason_code", "identifying_assumption", "cannot_rule_out", "citation")}
        with_needles = [row for row in rows_ if (row.get("needles") or {}).get("required")]
        needles_total = sum(len(row["needles"]["required"]) for row in with_needles)
        needles_found = sum(len(row["needles"]["satisfied"]) for row in with_needles)
        return {
            "n": n,
            "answered": len(answered),
            "refused": len(refused),
            "declined": len(declined),
            "answer_rate": round(len(answered) / max(n, 1), 6),
            "answered_with_all_parts": sum(
                1 for row in answered
                if all(row["check"].get(part) for part in parts_of(row)[0])
                and not any(row["check"].get(part) for part in parts_of(row)[1])),
            "parts_present": parts,
            "shapes": {shape: sum(1 for row in answered if row.get("shape") == shape)
                       for shape in sorted(shapes)},
            "refusals_with_citation": sum(1 for row in refused if row["citation"]),
            "declined_with_citation": sum(1 for row in declined if row["citation"]),
            "refusals_with_a_code": sum(1 for row in refused if row.get("refusal_code")),
            "answers_quoting_numbers_absent_from_the_citation": sum(
                1 for row in answered if row["numbers_absent_from_citation"]),
            "answered_with_plain_language": sum(
                1 for row in answered if (row.get("plain") or {}).get("text")),
            "answers_whose_plain_reading_quotes_uncited_numbers": sum(
                1 for row in answered if row["plain_numbers_absent_from_citation"]),
            "questions_with_needles": len(with_needles),
            "questions_whose_needles_are_all_satisfied": sum(
                1 for row in with_needles if row["needles"]["all_satisfied"]),
            "needle_satisfaction": (round(
                sum(1 for row in with_needles if row["needles"]["all_satisfied"])
                / len(with_needles), 6) if with_needles else None),
            "needles_total": needles_total,
            "needles_satisfied": needles_found,
            "needle_recall": (round(needles_found / max(needles_total, 1), 6)
                              if needles_total else None),
        }

    sets = {
        "published": summarise([row for row in rows if row["set"] == "published"]),
        "held_out": summarise([row for row in rows if row["set"] == "held_out"]),
    }
    sets["all"] = summarise(rows)

    document = {
        "schema_version": SCHEMA_VERSION,
        "layer": "Stage 9 — the answer layer: gate -> retrieve -> assemble -> R-04 post-check",
        "vintage": vintage,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "generator": {
            "script": "scripts/eval_answer.py",
            "spec": "analysis/specs/rag.yml#answer_contract",
            "gate_spec": gate_spec["spec_path"],
            "git_sha": git_sha(),
        },
        "corpus": {
            "path": f"registry/rag/{vintage}/corpus.json",
            "sha256": sha256_of(rag_dir / "corpus.json"),
            "chunks": len(corpus["chunks"]),
        },
        "gate": {
            "path": gate_spec["spec_path"],
            "sha256": sha256_of(GATE_SPEC_PATH),
            "artifact": f"registry/rag/{vintage}/intent_eval.json",
            "artifact_sha256": sha256_of(rag_dir / "intent_eval.json"),
        },
        "contract": {
            "path": "analysis/specs/rag.yml#answer_contract",
            "sha256": sha256_of(RAG_SPEC_PATH),
            "version": contract.get("version"),
            "post_check": rag_spec["answer_contract"]["post_check"],
            "refusal_template": rag_spec["answer_contract"]["refusal_template"],
            "shapes": {name: {"requires": list(spec.get("requires") or []),
                              "forbids": list(spec.get("forbids") or [])}
                       for name, spec in shapes.items()},
            "retrieval": f"BM25 over the corpus text, k = {k}; no model, no network, no database",
        },
        "sets": sets,
        "questions": rows,
    }

    out_path = rag_dir / "answer_eval.json"
    out_path.write_text(json.dumps(document, indent=1, ensure_ascii=False) + "\n",
                        encoding="utf-8", newline="\n")

    print(f"answer eval: {out_path.relative_to(REPO_ROOT).as_posix()}")
    for name in ("published", "held_out", "all"):
        block = sets[name]
        print(f"  {name:<10}: {block['n']:>2} question(s) — {block['answered']} answered, "
              f"{block['declined']} declined by the post-check, {block['refused']} refused by the gate; "
              f"answer rate {block['answer_rate']:.3f}")
        if block["answered"]:
            shapes_used = ", ".join(f"{shape} {count}" for shape, count in block["shapes"].items() if count)
            print(f"  {'':<10}  shapes: {shapes_used}; "
                  f"{block['answered_with_plain_language']} of the {block['answered']} carry a "
                  f"plain-language reading, {block['answers_whose_plain_reading_quotes_uncited_numbers']} "
                  f"of them quote a number their citation does not")
        if block["questions_with_needles"]:
            print(f"  {'':<10}  needles: {block['questions_whose_needles_are_all_satisfied']} of "
                  f"{block['questions_with_needles']} questions carry every needle they require "
                  f"({block['needle_satisfaction']:.3f}); {block['needles_satisfied']} of "
                  f"{block['needles_total']} needles are present ({block['needle_recall']:.3f})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
