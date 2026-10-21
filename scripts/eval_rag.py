"""Measure the retrieval half of the RAG layer, offline, on the declared eval set.

Two retrievers are measured on the same chunks and the same questions:

  * **embedding** — cosine over the stored `multi-qa-MiniLM-L6-cos-v1` vectors. This is the production
    path, and the query vectors are stored beside the chunk vectors so this script (and the verifier) never
    needs to load a model.
  * **BM25** — a dependency-free lexical baseline. It exists so the embedding numbers have something to
    beat. If BM25 retrieves the gold chunk as often as the embeddings do, the corpus is keyword-addressable
    and the model is not adding anything.

What is deliberately *not* measured here: faithfulness, answer relevance and the RAGAS suite. Those need a
generation step and a judge model, and this repository has no LLM key. The artifact declares them
`not_run` with that reason rather than reporting an unmeasured contract as satisfied — the same discipline
`scripts/verify.sh` uses when it skips the R stages on a Python-only runner.

Usage:
    python scripts/eval_rag.py            # both retrievers; the embedding side needs embeddings.npz
    python scripts/eval_rag.py --bm25-only
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC_PATH = REPO_ROOT / "analysis" / "specs" / "rag.yml"
SCHEMA_VERSION = "0.1.0"

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
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_sha() -> str | None:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=REPO_ROOT,
                              capture_output=True, text=True, check=True).stdout.strip() or None
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        return None


def tokenize(text: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9]+", text.lower()) if len(t) > 1 and t not in STOPWORDS]


class BM25:
    """Okapi BM25 with the parameters declared in analysis/specs/rag.yml. No stemming, no synonyms."""

    def __init__(self, documents: dict[str, str], k1: float = 1.5, b: float = 0.75) -> None:
        self.k1, self.b = k1, b
        self.ids = list(documents)
        self.tokens = {cid: tokenize(text) for cid, text in documents.items()}
        self.lengths = {cid: len(toks) for cid, toks in self.tokens.items()}
        self.avgdl = sum(self.lengths.values()) / max(len(self.lengths), 1)
        df: dict[str, int] = {}
        for toks in self.tokens.values():
            for term in set(toks):
                df[term] = df.get(term, 0) + 1
        self.n = len(self.ids)
        self.idf = {term: math.log(1 + (self.n - count + 0.5) / (count + 0.5)) for term, count in df.items()}
        self.tf = {cid: self._term_counts(toks) for cid, toks in self.tokens.items()}

    @staticmethod
    def _term_counts(tokens: list[str]) -> dict[str, int]:
        counts: dict[str, int] = {}
        for token in tokens:
            counts[token] = counts.get(token, 0) + 1
        return counts

    def scores(self, query: str) -> dict[str, float]:
        terms = tokenize(query)
        out: dict[str, float] = {}
        for cid in self.ids:
            score = 0.0
            counts = self.tf[cid]
            length = self.lengths[cid] or 1
            for term in terms:
                frequency = counts.get(term, 0)
                if not frequency:
                    continue
                denominator = frequency + self.k1 * (1 - self.b + self.b * length / self.avgdl)
                score += self.idf.get(term, 0.0) * frequency * (self.k1 + 1) / denominator
            out[cid] = score
        return out


def rank(scores: dict[str, float], k: int) -> list[tuple[str, float]]:
    return sorted(scores.items(), key=lambda item: (-item[1], item[0]))[:k]


def first_hit_rank(retrieved: list[str], gold: set[str]) -> int | None:
    for position, chunk_id in enumerate(retrieved, start=1):
        if chunk_id in gold:
            return position
    return None


def measure(rows: list[dict], retrieve, threshold: float | None, k: int,
            scope_ids: set[str] | None = None) -> tuple[dict, list[dict]]:
    """rows = eval questions; retrieve(row) -> [(chunk_id, score)] top-k.

    The refusal decision is two-part, and only for the two types where it is a score question: below the
    declared threshold, or the top chunk is the corpus's own scope statement. A `refusal_with_reason`
    question is *not* decided by score — its reason chunk should rank high — so `refused` stays null there
    and the citation recall is what gets measured.
    """
    scope_ids = scope_ids or set()
    detail: list[dict] = []
    answerable_top1: list[float] = []
    recall_hits = gold_hits = gold_total = 0
    reciprocal: list[float] = []
    refusal_hits = refusal_total = 0
    out_refused = out_total = 0
    answerable_kept = answerable_total = 0

    for row in rows:
        retrieved = retrieve(row)
        ids = [cid for cid, _ in retrieved]
        scores = [score for _, score in retrieved]
        gold = set(row["gold_chunks"])
        top1 = scores[0] if scores else 0.0
        rank_hit = first_hit_rank(ids, gold) if gold else None
        entry = {
            "id": row["id"],
            "type": row["type"],
            "retrieved": [{"chunk_id": cid, "score": round(score, 6)} for cid, score in retrieved],
            "top1_score": round(top1, 6),
            "first_gold_rank": rank_hit,
        }
        if row["type"] != "out_of_scope":
            answerable_top1.append(top1)
        if gold:
            gold_total += 1
            in_top_k = rank_hit is not None
            recall_hits += int(in_top_k)
            recovered = len(gold.intersection(ids))
            gold_hits += recovered / len(gold)
            reciprocal.append(1 / rank_hit if rank_hit else 0.0)
        refused = None
        if threshold is not None:
            refused = top1 < threshold or (bool(ids) and ids[0] in scope_ids)
        if row["type"] == "answerable":
            answerable_total += 1
            if refused is not None:
                entry["refused"] = refused
                answerable_kept += int(not refused)
        elif row["type"] == "refusal_with_reason":
            refusal_total += 1
            entry["refused"] = None
        else:
            out_total += 1
            if refused is not None:
                entry["refused"] = refused
                out_refused += int(refused)
        detail.append(entry)

    metrics = {
        "recall_at_k": round(recall_hits / max(gold_total, 1), 6),
        "gold_coverage_at_k": round(gold_hits / max(gold_total, 1), 6),
        "mrr_at_10": round(sum(reciprocal) / max(len(reciprocal), 1), 6),
        "n_scored": gold_total,
        "n_refusal_questions": refusal_total,
        "out_of_scope_refusal": round(out_refused / out_total, 6) if out_total and threshold is not None else None,
        "answerable_not_refused": (round(answerable_kept / answerable_total, 6)
                                   if answerable_total and threshold is not None else None),
    }
    # `refusal_reason_recall` is over refusal questions only, not over every gold-bearing question.
    reason_rows = [d for d in detail if d["type"] == "refusal_with_reason"]
    metrics["refusal_reason_recall"] = (
        round(sum(1 for d in reason_rows if d["first_gold_rank"] is not None) / len(reason_rows), 6)
        if reason_rows else None
    )
    return metrics, detail


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Measure retrieval on the RAG eval set.")
    parser.add_argument("--bm25-only", action="store_true", help="skip the embedding retriever")
    parser.add_argument("--allow-degrade", action="store_true",
                        help="permit overwriting published embedding metrics with a BM25-only run")
    args = parser.parse_args(argv)

    import yaml

    spec = yaml.safe_load(SPEC_PATH.read_text(encoding="utf-8"))
    out_root = REPO_ROOT / spec["output"]["root"]
    vintages = sorted((p for p in out_root.iterdir() if p.is_dir()), key=lambda p: p.name)
    if not vintages:
        print("no corpus under registry/rag — run scripts/build_rag_corpus.py first", file=sys.stderr)
        return 2
    out_dir = vintages[-1]
    corpus_path = out_dir / spec["output"]["corpus"]
    eval_path = out_dir / spec["output"]["eval_set"]
    corpus = json.loads(corpus_path.read_text(encoding="utf-8"))
    eval_set = json.loads(eval_path.read_text(encoding="utf-8"))
    k = int(spec["retrieval"]["k"])

    documents = {chunk["chunk_id"]: chunk["text"] for chunk in corpus["chunks"]}
    rows = eval_set["questions"]

    scope_ids = {chunk["chunk_id"] for chunk in corpus["chunks"] if chunk["doc_type"] == "scope"}
    bm25 = BM25(documents, k1=1.5, b=0.75)
    bm25_metrics, bm25_detail = measure(
        rows, lambda row: rank(bm25.scores(row["question"]), k), threshold=None, k=k, scope_ids=scope_ids
    )

    embedding_metrics = None
    embedding_detail = None
    embedding_manifest = None
    threshold = None
    median_top1 = None
    embedding_info = corpus.get("embedding") or {}
    embeddings_path = out_dir / spec["output"]["embeddings"]
    if not args.bm25_only and embedding_info.get("status") == "built" and embeddings_path.exists():
        try:
            import numpy as np
        except ImportError:
            print("  ! numpy not importable — embedding retrieval skipped", file=sys.stderr)
            np = None
        if np is not None:
            data = np.load(embeddings_path, allow_pickle=True)
            chunk_ids = [str(cid) for cid in data["chunk_ids"]]
            chunk_vectors = data["chunk_vectors"]
            question_ids = [str(qid) for qid in data["question_ids"]]
            query_vectors = data["query_vectors"]
            if chunk_ids != [chunk["chunk_id"] for chunk in corpus["chunks"]]:
                print("embeddings.npz is out of step with corpus.json — rebuild with --embed", file=sys.stderr)
                return 2
            index_of = {qid: i for i, qid in enumerate(question_ids)}
            if set(index_of) != {row["id"] for row in rows}:
                print("embeddings.npz carries a different question set — rebuild with --embed", file=sys.stderr)
                return 2

            def retrieve(row: dict) -> list[tuple[str, float]]:
                vector = query_vectors[index_of[row["id"]]]
                scores = chunk_vectors @ vector
                order = np.argsort(-scores)[:k]
                return [(chunk_ids[int(i)], float(scores[int(i)])) for i in order]

            # The refusal threshold is declared in the spec as a fraction of the median answerable top-1.
            # It is computed over answerable questions only — the out-of-scope rows must not move the
            # threshold that is supposed to catch them.
            answerable_top1 = []
            for row in rows:
                if row["type"] != "answerable":
                    continue
                vector = query_vectors[index_of[row["id"]]]
                answerable_top1.append(float(max(chunk_vectors @ vector)))
            median_top1 = sorted(answerable_top1)[len(answerable_top1) // 2]
            threshold = round(0.5 * median_top1, 6)

            embedding_metrics, embedding_detail = measure(rows, retrieve, threshold=threshold, k=k,
                                                          scope_ids=scope_ids)
            embedding_manifest = {
                "status": "measured",
                "model": embedding_info.get("model"),
                "path": spec["output"]["embeddings"],
                "sha256": embedding_info.get("sha256"),
                "n_chunk_vectors": int(chunk_vectors.shape[0]),
                "dim": int(chunk_vectors.shape[1]),
            }

    gates_declared = spec.get("gates") or {}
    gates: dict[str, dict] = {}
    for name, metrics in (("embedding", embedding_metrics), ("bm25", bm25_metrics)):
        key = f"recall_at_{k}"
        if not metrics:
            gates[name] = {"status": "not_measured",
                           "why": "no embeddings for this corpus — rebuild with --embed"}
            continue
        measured = {
            key: {"target": gates_declared.get(f"recall_at_{k}"),
                  "measured": metrics["recall_at_k"],
                  "met": metrics["recall_at_k"] >= float(gates_declared.get(f"recall_at_{k}", 0))},
            "refusal_reason_recall": {
                "target": gates_declared.get("refusal_reason_recall"),
                "measured": metrics["refusal_reason_recall"],
                "met": (metrics["refusal_reason_recall"] is not None
                        and metrics["refusal_reason_recall"]
                        >= float(gates_declared.get("refusal_reason_recall", 0))),
            },
        }
        for gate_name in ("out_of_scope_refusal", "answerable_not_refused"):
            value = metrics.get(gate_name)
            measured[gate_name] = {
                "target": gates_declared.get(gate_name),
                "measured": value,
                "met": None if value is None else value >= float(gates_declared.get(gate_name, 0)),
            }
        gates[name] = measured

    document = {
        "schema_version": SCHEMA_VERSION,
        "layer": "RAG retrieval evaluation (offline; generation metrics declared, not measured)",
        "vintage": corpus["vintage"],
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "generator": {"script": "scripts/eval_rag.py", "spec": spec["spec_path"], "git_sha": git_sha()},
        "corpus": {"path": spec["output"]["corpus"], "sha256": sha256_of(corpus_path),
                   "chunks": corpus["counts"]["chunks"], "vintage": corpus["vintage"]},
        "eval_set": {"path": spec["output"]["eval_set"], "sha256": sha256_of(eval_path),
                     "counts": eval_set["counts"]},
        "k": k,
        "retrievers": {
            "embedding": embedding_manifest or {"status": "not_measured",
                                                "why": "no embeddings.npz beside the corpus"},
            "bm25": {"status": "measured", "k1": 1.5, "b": 0.75,
                     "why": spec["retrieval"]["baseline_why"]},
        },
        "refusal": {
            "rule": spec["retrieval"]["refusal_rule"],
            "threshold": threshold,
            "median_answerable_top1": None if median_top1 is None else round(median_top1, 6),
            "applies_to": "embedding retriever only — BM25 scores are unbounded and not comparable to cosine",
            "caveat": "the threshold is calibrated on the answerable eval questions, so refusal recall is "
                      "optimistic; it is a declared rule with a published number, not a guarantee",
        },
        "metrics": {"embedding": embedding_metrics, "bm25": bm25_metrics},
        "gates": gates,
        "answer_shape": {
            "status": "not_measured",
            "why": "the post-check (interval + identifying assumption + citation, R-04) runs on assembled "
                   "answers and there is no generation step in this repository yet. The eval set carries "
                   "`must_contain` needles per question so the check is ready to run with the app.",
            "declared_in": spec["answer_contract"]["order"],
        },
        "ragas": eval_set["ragas"],
        "questions": [
            {**embedding_row, "bm25": bm25_row}
            for embedding_row, bm25_row in zip(embedding_detail or [{"id": r["id"]} for r in rows], bm25_detail)
        ],
    }
    if embedding_detail is None:
        document["questions"] = bm25_detail

    out_path = out_dir / spec["output"]["retrieval_eval"]
    if embedding_metrics is None and out_path.exists() and not args.allow_degrade:
        previous = json.loads(out_path.read_text(encoding="utf-8"))
        if (previous.get("metrics") or {}).get("embedding"):
            print(
                "refusing to overwrite published embedding metrics with a BM25-only run — that would drop "
                "the measured retrieval numbers from the artifact. Use an interpreter that can load "
                "numpy and the stored vectors (the retrieval half needs no torch), or pass --allow-degrade.",
                file=sys.stderr,
            )
            return 2
    out_path.write_text(json.dumps(document, indent=1, ensure_ascii=False) + "\n",
                        encoding="utf-8", newline="\n")

    print(f"retrieval eval: {out_path.relative_to(REPO_ROOT).as_posix()}")
    for name in ("embedding", "bm25"):
        metrics = document["metrics"][name]
        if not metrics:
            print(f"  {name:<9}: not measured")
            continue
        print(f"  {name:<9}: recall@{k} {metrics['recall_at_k']:.3f}, gold coverage "
              f"{metrics['gold_coverage_at_k']:.3f}, MRR {metrics['mrr_at_10']:.3f}, "
              f"refusal recall {metrics['refusal_reason_recall']}, "
              f"out-of-scope refused {metrics['out_of_scope_refusal']}, "
              f"answerable kept {metrics['answerable_not_refused']}")
    if threshold is not None:
        print(f"  refusal threshold (cosine): {threshold} from median answerable top-1 {median_top1:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
