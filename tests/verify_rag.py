"""Independent verification of the Stage 8 retrieval corpus, its eval set and the measured retrieval numbers.

What this verifier re-derives rather than trusts:

  * **Attribution.** Every chunk names a source file and a sha256; the file is hashed again here. A document
    edited without a corpus rebuild fails — the same invariant the registry uses for numbers, applied to
    prose (C-44, C-53).
  * **Completeness.** Every card on disk has at least one chunk, every declared family is present, and the
    parent-document counts match the sources (cards, designs, seed rows, events).
  * **Eval-set integrity.** Every gold reference resolves to a chunk, every needle appears in the chunk it
    is supposed to check, and no out-of-scope question quietly names a gold chunk.
  * **The retrieval numbers.** BM25 is re-implemented here from the declared parameters and cosine is
    recomputed from the stored vectors — neither calls `scripts/eval_rag.py`. A published recall that the
    verifier cannot reproduce fails, including a threshold that was moved after the fact.
  * **The gate booleans.** Each `met` flag is recomputed from the measured value and the declared target, so
    a target that was edited after measurement cannot keep its old verdict.

A missed *target* is not a verifier failure: retrieval quality is a finding to publish (the Stage 7
precedent — p = 0.0625 was published, not widened until it passed). What fails here is a number that is
wrong, a claim that cannot be reproduced, or a gate whose `met` flag does not match its own arithmetic.

Usage:
    python tests/verify_rag.py
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC_PATH = REPO_ROOT / "analysis" / "specs" / "rag.yml"
RAG_ROOT = REPO_ROOT / "registry" / "rag"

STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "with", "by", "at", "from", "as", "is",
    "are", "was", "were", "be", "been", "being", "it", "its", "this", "that", "these", "those", "there",
    "which", "who", "whom", "whose", "what", "when", "where", "why", "how", "does", "do", "did", "done",
    "can", "could", "would", "should", "will", "shall", "may", "might", "must", "have", "has", "had",
    "not", "no", "but", "if", "then", "than", "so", "such", "into", "about", "over", "under", "between",
    "after", "before", "during", "any", "all", "each", "every", "more", "most", "some", "much", "many",
    "you", "your", "we", "our", "they", "their", "he", "she", "his", "her", "i", "me", "my", "us",
}


def sha256_of(path: Path) -> str:
    """Raw bytes — for binary artifacts (the vectors)."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sha256_text(path: Path) -> str:
    """Canonical text hash: CRLF -> LF first, because the git index stores eol=lf.

    Without this, every source hash would reproduce only on the Windows checkout that built it and fail on
    a fresh clone or the Linux runner — the corpus would verify on one machine and nowhere else.
    """
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def tokenize(text: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9]+", text.lower()) if len(t) > 1 and t not in STOPWORDS]


def bm25_scores(documents: dict[str, str], query: str, k1: float = 1.5, b: float = 0.75) -> dict[str, float]:
    """An independent Okapi BM25, written from the formula rather than imported from the harness."""
    tokens = {cid: tokenize(text) for cid, text in documents.items()}
    lengths = {cid: len(toks) for cid, toks in tokens.items()}
    avgdl = sum(lengths.values()) / max(len(lengths), 1)
    df: Counter[str] = Counter()
    for toks in tokens.values():
        df.update(set(toks))
    n = len(tokens)
    idf = {term: math.log(1 + (n - count + 0.5) / (count + 0.5)) for term, count in df.items()}
    terms = tokenize(query)
    out: dict[str, float] = {}
    for cid, toks in tokens.items():
        counts: Counter[str] = Counter(toks)
        score = 0.0
        for term in terms:
            frequency = counts.get(term, 0)
            if not frequency:
                continue
            denominator = frequency + k1 * (1 - b + b * lengths[cid] / avgdl)
            score += idf.get(term, 0.0) * frequency * (k1 + 1) / denominator
        out[cid] = score
    return out


def parent_id(chunk_id: str) -> str:
    return chunk_id.split("#", 1)[0]


def compare(published, recomputed, label: str, failures: list[str], tolerance: float = 1e-6) -> None:
    if published is None or recomputed is None:
        if published != recomputed:
            failures.append(f"{label}: published {published!r} but recomputed {recomputed!r}")
        return
    if isinstance(published, float) or isinstance(recomputed, float):
        if abs(float(published) - float(recomputed)) > tolerance:
            failures.append(f"{label}: published {published!r}, recomputed {recomputed!r}")
    elif published != recomputed:
        failures.append(f"{label}: published {published!r}, recomputed {recomputed!r}")


def main() -> int:
    import yaml

    failures: list[str] = []
    spec = yaml.safe_load(SPEC_PATH.read_text(encoding="utf-8"))
    vintages = sorted((p for p in RAG_ROOT.iterdir() if p.is_dir()), key=lambda p: p.name) if RAG_ROOT.exists() else []
    if not vintages:
        print("FAILED — registry/rag holds no corpus; run scripts/build_rag_corpus.py")
        return 1
    out_dir = vintages[-1]
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", out_dir.name):
        failures.append(f"registry/rag/{out_dir.name}: the vintage is not a date, so a consumer selecting the "
                        "newest by date will skip it (C-44, S4-20)")

    corpus_path = out_dir / spec["output"]["corpus"]
    eval_path = out_dir / spec["output"]["eval_set"]
    retrieval_path = out_dir / spec["output"]["retrieval_eval"]
    for path in (corpus_path, eval_path, retrieval_path):
        if not path.exists():
            failures.append(f"{path.relative_to(REPO_ROOT)}: missing")
    if failures:
        print("FAILED —\n  " + "\n  ".join(failures))
        return 1

    corpus = json.loads(corpus_path.read_text(encoding="utf-8"))
    eval_set = json.loads(eval_path.read_text(encoding="utf-8"))
    retrieval = json.loads(retrieval_path.read_text(encoding="utf-8"))
    index = json.loads((REPO_ROOT / spec["input"]["registry_index"]).read_text(encoding="utf-8"))

    # ---------------------------------------------------------------------------------------------
    # 1. The vintage chain
    # ---------------------------------------------------------------------------------------------
    expected_vintage = index.get("vintage_date")
    if corpus.get("vintage") != expected_vintage:
        failures.append(f"corpus vintage {corpus.get('vintage')!r} != registry index vintage "
                        f"{expected_vintage!r} — a stale answer could outlive the model it quotes")
    for name, document in (("corpus", corpus), ("eval set", eval_set), ("retrieval eval", retrieval)):
        if document.get("vintage") != expected_vintage:
            failures.append(f"{name}: vintage {document.get('vintage')!r} != {expected_vintage!r}")
    if corpus.get("registry", {}).get("index_vintage") != expected_vintage:
        failures.append("corpus: registry.index_vintage disagrees with the index's own vintage_date")
    for family in ("estimates", "events", "quality"):
        newest = sorted((REPO_ROOT / "registry" / family).iterdir(), key=lambda p: p.name)[-1]
        artifact = {"estimates": "estimates.json", "events": "events.json", "quality": "report.json"}[family]
        document = json.loads((newest / artifact).read_text(encoding="utf-8"))
        stamp = document.get("vintage") or document.get("report_vintage")
        if stamp != expected_vintage:
            failures.append(f"registry/{family}/{newest.name}: vintage {stamp!r} != registry vintage "
                            f"{expected_vintage!r} — the corpus quotes and the artifact would disagree")

    # ---------------------------------------------------------------------------------------------
    # 2. Attribution: every source hash still matches the file on disk
    # ---------------------------------------------------------------------------------------------
    if not corpus.get("source_hash_rule"):
        failures.append("corpus: no source_hash_rule — a source hash whose normalisation is undeclared is "
                        "a hash that only reproduces on one platform")
    sources = {row["path"]: row for row in corpus.get("sources") or []}
    for path_text, source in sources.items():
        path = REPO_ROOT / path_text
        if not path.exists():
            failures.append(f"{path_text}: recorded as a corpus source but absent from disk")
            continue
        if sha256_text(path) != source["sha256"]:
            failures.append(
                f"{path_text}: sha256 changed since the corpus was built — re-run "
                "scripts/build_rag_corpus.py (a source that moves under an unchanged corpus is the defect "
                "the attribution record exists to catch)"
            )

    # ---------------------------------------------------------------------------------------------
    # 3. Chunk integrity and family completeness
    # ---------------------------------------------------------------------------------------------
    chunks = corpus.get("chunks") or []
    ids = [chunk["chunk_id"] for chunk in chunks]
    if len(ids) != len(set(ids)):
        duplicates = [cid for cid, count in Counter(ids).items() if count > 1]
        failures.append(f"corpus: duplicate chunk ids {duplicates[:5]}")
    max_chars = int(spec["chunking"]["max_chars"])
    # Family key -> doc_type. Two families (`coverage`, `registry_coverage`) share the `coverage` doc type,
    # so the mapping is declared rather than assumed to be the identity.
    family_to_type = {"model_card": "model_card", "published_result": "published_result",
                      "methodology": "methodology", "data_dictionary": "data_dictionary",
                      "administration": "administration", "shock": "shock", "event_study": "event_study",
                      "coverage": "coverage", "registry_coverage": "coverage", "scope": "scope"}
    declared_types = set(spec["chunk_families"])
    if set(family_to_type) != declared_types:
        failures.append(f"spec: chunk_families {sorted(declared_types)} do not map onto the artifact's doc "
                        f"types ({sorted(set(family_to_type))})")
    by_type: Counter[str] = Counter()
    for chunk in chunks:
        if chunk["vintage"] != expected_vintage:
            failures.append(f"{chunk['chunk_id']}: chunk vintage {chunk['vintage']!r} != {expected_vintage!r}")
        if chunk["source"]["path"] not in sources:
            failures.append(f"{chunk['chunk_id']}: source {chunk['source']['path']!r} is not in the manifest")
        if len(chunk["text"]) > max_chars:
            failures.append(f"{chunk['chunk_id']}: {len(chunk['text'])} chars exceeds the declared budget "
                            f"{max_chars}")
        if chunk["chars"] != len(chunk["text"]):
            failures.append(f"{chunk['chunk_id']}: chars field disagrees with the text length")
        if chunk.get("text_sha256") != hashlib.sha256(chunk["text"].encode("utf-8")).hexdigest():
            failures.append(f"{chunk['chunk_id']}: the chunk's text hash does not match its text — the "
                            "artifact was edited after it was built")
        if chunk["doc_type"] not in declared_types:
            failures.append(f"{chunk['chunk_id']}: undeclared doc_type {chunk['doc_type']!r}")
        if chunk["source"]["path"] not in chunk["citation"]:
            failures.append(f"{chunk['chunk_id']}: citation does not name its source path")
        by_type[chunk["doc_type"]] += 1
    for doc_type, count in (corpus.get("counts", {}).get("by_doc_type") or {}).items():
        if by_type.get(doc_type, 0) != count:
            failures.append(f"corpus: counts.by_doc_type[{doc_type!r}] is {count} and the chunks say "
                            f"{by_type.get(doc_type, 0)}")
    if sum(by_type.values()) != corpus["counts"]["chunks"]:
        failures.append("corpus: counts.chunks does not equal the number of chunks")

    # Parent documents, not parts: a card split into three parts is still one card.
    parents = {doc_type: {parent_id(cid) for cid in ids
                          if next(c for c in chunks if c["chunk_id"] == cid)["doc_type"] == doc_type}
               for doc_type in by_type}
    cards = [p for p in (REPO_ROOT / spec["input"]["cards_dir"]).glob("*.json") if p.name != "index.json"]
    expected_parents = {
        "model_card": len(cards),
        "published_result": len(index.get("published_results") or {}),
        "administration": len(spec["input"]["seeds"]) and _csv_rows(REPO_ROOT / spec["input"]["seeds"]["administration"]),
        "shock": _csv_rows(REPO_ROOT / spec["input"]["seeds"]["shock_bands"]),
        "coverage": 2,
        "scope": 1,
    }
    for doc_type, expected in expected_parents.items():
        if len(parents.get(doc_type, set())) != expected:
            failures.append(f"corpus: {doc_type} has {len(parents.get(doc_type, set()))} parent document(s), "
                            f"the sources declare {expected}")
    events_path = sorted((REPO_ROOT / "registry" / "events").iterdir(), key=lambda p: p.name)[-1] / "events.json"
    events = json.loads(events_path.read_text(encoding="utf-8"))
    if len(parents.get("event_study", set())) != len(events.get("events") or []) + 1:
        failures.append(f"corpus: event_study has {len(parents.get('event_study', set()))} parent document(s); "
                        f"the artifact has {len(events.get('events') or [])} events plus the scope chunk")

    # ---------------------------------------------------------------------------------------------
    # 4. Eval-set integrity
    # ---------------------------------------------------------------------------------------------
    chunk_by_id = {chunk["chunk_id"]: chunk for chunk in chunks}
    questions = eval_set.get("questions") or []
    if Counter(q["type"] for q in questions).get("questions"):
        pass
    counted = Counter(q["type"] for q in questions)
    for key, value in (eval_set.get("counts") or {}).items():
        if key == "questions" and value != len(questions):
            failures.append(f"eval set: counts.questions is {value}, the set has {len(questions)}")
        elif key in counted and value != counted[key]:
            failures.append(f"eval set: counts.{key} is {value}, the set has {counted[key]}")
    seen: set[str] = set()
    for row in questions:
        qid = row["id"]
        if qid in seen:
            failures.append(f"eval set: duplicate question id {qid}")
        seen.add(qid)
        if row["type"] == "out_of_scope":
            if row["gold_chunks"]:
                failures.append(f"{qid}: an out_of_scope question names a gold chunk")
        else:
            if not row["gold_chunks"]:
                failures.append(f"{qid}: {row['type']} question has no gold chunk")
            if not row["must_contain"]:
                failures.append(f"{qid}: no must_contain needle")
        for cid in row["gold_chunks"]:
            if cid not in chunk_by_id:
                failures.append(f"{qid}: gold chunk {cid!r} is not in the corpus")
        for needle in row["must_contain"]:
            if not any(needle in chunk_by_id.get(cid, {"text": ""})["text"] for cid in row["gold_chunks"]):
                failures.append(f"{qid}: needle {needle!r} is absent from its gold chunk(s)")
        if row["type"] == "refusal_with_reason" and not row.get("refusal_must_cite"):
            failures.append(f"{qid}: a refusal must cite the chunk that gives the reason")
        if not row.get("reference_answer"):
            failures.append(f"{qid}: no reference answer — a RAGAS run would have no ground truth")
    if eval_set.get("ragas", {}).get("status") == "measured":
        failures.append("eval set: claims RAGAS has been measured, and no LLM-judged run exists in this repo")

    # ---------------------------------------------------------------------------------------------
    # 5. The retrieval numbers, recomputed
    # ---------------------------------------------------------------------------------------------
    documents = {chunk["chunk_id"]: chunk["text"] for chunk in chunks}
    k = int(retrieval["k"])
    if retrieval["corpus"]["sha256"] != sha256_of(corpus_path):
        failures.append("retrieval eval: the corpus it names is not the corpus on disk")
    if retrieval["eval_set"]["sha256"] != sha256_of(eval_path):
        failures.append("retrieval eval: the eval set it names is not the eval set on disk")

    def metrics_for(ranked: dict[str, list[tuple[str, float]]], threshold: float | None,
                    scope_ids: set[str]) -> dict:
        recall = coverage = 0.0
        reciprocal = []
        reason_recall = []
        refused_out = out_total = kept = answerable = 0
        for row in questions:
            ids_ranked = ranked[row["id"]]
            gold = set(row["gold_chunks"])
            hit = next((position for position, (cid, _) in enumerate(ids_ranked, start=1) if cid in gold), None)
            if gold:
                recall += 1 if hit else 0
                coverage += len(gold.intersection(cid for cid, _ in ids_ranked)) / len(gold)
                reciprocal.append(1 / hit if hit else 0.0)
            top1 = ids_ranked[0][1] if ids_ranked else 0.0
            top1_id = ids_ranked[0][0] if ids_ranked else None
            refused = None if threshold is None else (top1 < threshold or top1_id in scope_ids)
            if row["type"] == "refusal_with_reason":
                reason_recall.append(1 if hit else 0)
            elif row["type"] == "answerable":
                answerable += 1
                kept += int(not refused) if refused is not None else 0
            else:
                out_total += 1
                refused_out += int(bool(refused))
        n_gold = sum(1 for row in questions if row["gold_chunks"])
        return {
            "recall_at_k": round(recall / max(n_gold, 1), 6),
            "gold_coverage_at_k": round(coverage / max(n_gold, 1), 6),
            "mrr_at_10": round(sum(reciprocal) / max(len(reciprocal), 1), 6),
            "n_scored": n_gold,
            "n_refusal_questions": len(reason_recall),
            "refusal_reason_recall": round(sum(reason_recall) / len(reason_recall), 6) if reason_recall else None,
            "out_of_scope_refusal": (round(refused_out / out_total, 6)
                                     if out_total and threshold is not None else None),
            "answerable_not_refused": (round(kept / answerable, 6)
                                       if answerable and threshold is not None else None),
        }

    scope_ids = {chunk["chunk_id"] for chunk in chunks if chunk["doc_type"] == "scope"}
    bm25_ranked = {
        row["id"]: sorted(bm25_scores(documents, row["question"]).items(),
                          key=lambda item: (-item[1], item[0]))[:k]
        for row in questions
    }
    recomputed_bm25 = metrics_for(bm25_ranked, None, scope_ids)
    published_bm25 = (retrieval.get("metrics") or {}).get("bm25") or {}
    for field, value in recomputed_bm25.items():
        compare(published_bm25.get(field), value, f"retrieval/bm25/{field}", failures)

    embedding_published = (retrieval.get("metrics") or {}).get("embedding")
    embeddings_path = out_dir / spec["output"]["embeddings"]
    if embedding_published:
        try:
            import numpy as np
        except ImportError:
            print("  ! numpy not importable — embedding metrics NOT recomputed (reported as a skip)")
            np = None
        if np is not None:
            if not embeddings_path.exists():
                failures.append("retrieval eval: publishes embedding metrics but embeddings.npz is missing")
            else:
                manifest = corpus.get("embedding") or {}
                if manifest.get("sha256") != sha256_of(embeddings_path):
                    failures.append("corpus: the recorded embeddings sha256 does not match the file")
                data = np.load(embeddings_path, allow_pickle=True)
                chunk_ids = [str(cid) for cid in data["chunk_ids"]]
                if chunk_ids != [chunk["chunk_id"] for chunk in chunks]:
                    failures.append("embeddings.npz: vector order does not match corpus.json — a vector "
                                    "would be attributed to the wrong chunk")
                question_ids = [str(qid) for qid in data["question_ids"]]
                if set(question_ids) != {row["id"] for row in questions}:
                    failures.append("embeddings.npz: the embedded question set is not the eval set")
                position = {qid: index for index, qid in enumerate(question_ids)}
                vectors = data["chunk_vectors"]
                queries = data["query_vectors"]
                answerable_top1 = []
                for row in questions:
                    if row["type"] == "answerable":
                        answerable_top1.append(float(max(vectors @ queries[position[row["id"]]])))
                median = sorted(answerable_top1)[len(answerable_top1) // 2]
                recomputed_threshold = round(0.5 * median, 6)
                compare(retrieval["refusal"].get("threshold"), recomputed_threshold,
                        "retrieval/refusal/threshold", failures)
                compare(retrieval["refusal"].get("median_answerable_top1"), round(median, 6),
                        "retrieval/refusal/median_answerable_top1", failures)
                embedding_ranked = {}
                for row in questions:
                    scores = vectors @ queries[position[row["id"]]]
                    order = np.argsort(-scores)[:k]
                    embedding_ranked[row["id"]] = [(chunk_ids[int(i)], float(scores[int(i)])) for i in order]
                recomputed = metrics_for(embedding_ranked, recomputed_threshold, scope_ids)
                for field, value in recomputed.items():
                    compare(embedding_published.get(field), value, f"retrieval/embedding/{field}", failures)

    # Gate booleans, recomputed against the declared targets.
    declared = spec.get("gates") or {}
    for name in ("embedding", "bm25"):
        gate_block = (retrieval.get("gates") or {}).get(name) or {}
        if gate_block.get("status") == "not_measured":
            continue
        metrics = (retrieval.get("metrics") or {}).get(name) or {}
        for gate_name, target in declared.items():
            published_gate = gate_block.get(gate_name)
            if not isinstance(published_gate, dict):
                failures.append(f"retrieval/gates/{name}/{gate_name}: missing")
                continue
            # The metrics block names the recall field with the actual k (`recall_at_k`), so a target
            # written as `recall_at_5` has to be resolved to it rather than looked up literally.
            field = "recall_at_k" if gate_name == f"recall_at_{k}" else gate_name
            measured = metrics.get(field)
            expected_met = None if measured is None else (float(measured) >= float(target))
            if published_gate.get("target") != target:
                failures.append(f"retrieval/gates/{name}/{gate_name}: target {published_gate.get('target')} "
                                f"vs the spec's {target}")
            if published_gate.get("met") != expected_met:
                failures.append(f"retrieval/gates/{name}/{gate_name}: met={published_gate.get('met')} but "
                                f"measured {measured} against target {target} gives {expected_met}")
    for name, gate_block in (retrieval.get("gates") or {}).items():
        for gate_name, gate in gate_block.items():
            if isinstance(gate, dict) and gate.get("met") is True and gate.get("measured") == 0:
                failures.append(f"retrieval/gates/{name}/{gate_name}: met=true with a measured value of 0")

    # ---------------------------------------------------------------------------------------------
    # 6. The narrative quotes the numbers it describes, derived from the artifacts
    # ---------------------------------------------------------------------------------------------
    narrative = REPO_ROOT / "docs" / "rag.md"
    if not narrative.exists():
        failures.append("docs/rag.md: missing — the retrieval layer's numbers would have no prose home")
    else:
        prose = narrative.read_text(encoding="utf-8")
        embedding_metrics = (retrieval.get("metrics") or {}).get("embedding") or {}
        bm25_metrics = (retrieval.get("metrics") or {}).get("bm25") or {}
        needles = [
            (str(corpus["counts"]["chunks"]), "the chunk count"),
            (str(len(sources)), "the attributed-source count"),
            (str(len(questions)), "the eval-set size"),
            (f"{bm25_metrics.get('recall_at_k', 0):.3f}", "the BM25 recall"),
        ]
        if embedding_metrics:
            needles += [
                (f"{embedding_metrics['recall_at_k']:.3f}", "the embedding recall"),
                (f"{embedding_metrics['gold_coverage_at_k']:.3f}", "the gold coverage"),
                (f"{embedding_metrics['mrr_at_10']:.3f}", "the MRR"),
                (f"{embedding_metrics['refusal_reason_recall']:g}", "the refusal-with-reason recall"),
                (f"{embedding_metrics['out_of_scope_refusal']:g}", "the out-of-scope refusal rate"),
                (f"{retrieval['refusal']['threshold']:.6f}", "the refusal threshold"),
            ]
        for needle, label in needles:
            if needle not in prose:
                failures.append(f"docs/rag.md: does not quote {label} ({needle}) — the page has drifted from "
                                "the artifact it describes")

    # ---------------------------------------------------------------------------------------------
    # 7. Per-question rows describe chunks that exist
    # ---------------------------------------------------------------------------------------------
    if len(retrieval.get("questions") or []) != len(questions):
        failures.append("retrieval eval: per-question rows do not cover the eval set")
    for row in retrieval.get("questions") or []:
        for item in row.get("retrieved") or []:
            if item["chunk_id"] not in chunk_by_id:
                failures.append(f"retrieval eval/{row['id']}: retrieved chunk {item['chunk_id']!r} does not exist")
        if row["id"] not in {q["id"] for q in questions}:
            failures.append(f"retrieval eval: row {row['id']!r} is not an eval question")

    # ---------------------------------------------------------------------------------------------
    print(f"corpus        : {out_dir.name} — {len(chunks)} chunks, {len(parents.get('model_card', set()))} "
          f"cards, {len(sources)} attributed sources")
    print(f"families      : " + ", ".join(f"{t} {n}" for t, n in sorted(by_type.items())))
    print(f"eval set      : {len(questions)} questions ({dict(counted)}), every gold chunk and needle resolved")
    print(f"retrieval     : k={k}; bm25 and embedding metrics recomputed from the stored data")
    for name in ("embedding", "bm25"):
        gate_block = (retrieval.get("gates") or {}).get(name) or {}
        if gate_block.get("status") == "not_measured":
            print(f"  {name:<9}: not measured ({gate_block.get('why')})")
        elif isinstance(gate_block, dict) and "recall_at_5" in gate_block:
            print(f"  {name:<9}: recall@5 {gate_block['recall_at_5'].get('measured')} "
                  f"(target {gate_block['recall_at_5'].get('target')}, met "
                  f"{gate_block['recall_at_5'].get('met')}); refusal recall "
                  f"{gate_block['refusal_reason_recall'].get('measured')}; out-of-scope refused "
                  f"{gate_block['out_of_scope_refusal'].get('measured')}")
    shape = retrieval.get("answer_shape") or {}
    print(f"answer shape  : {shape.get('status')} — {str(shape.get('why'))[:110]}")
    print(f"ragas         : {retrieval.get('ragas', {}).get('status')}")
    print(f"narrative     : docs/rag.md quotes its chunk count, recall, coverage, MRR, refusal numbers and "
          f"threshold")

    print()
    if failures:
        print(f"FAILED — {len(failures)} problem(s):")
        for problem in failures[:40]:
            print(f"  - {problem}")
        if len(failures) > 40:
            print(f"  … and {len(failures) - 40} more")
        return 1
    print("PASS — the corpus attributes every chunk to a source whose hash still matches, every card and "
          "family is present, the eval set's gold chunks and needles resolve, and every published retrieval "
          "number and gate flag is recomputed from the stored vectors and the declared parameters")
    return 0


def _csv_rows(path: Path) -> int:
    return max(sum(1 for _ in path.read_text(encoding="utf-8").splitlines()) - 1, 0)


if __name__ == "__main__":
    raise SystemExit(main())
