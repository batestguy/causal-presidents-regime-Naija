"""Verify the answer-quality measurement without trusting the script that produced it.

The scores are LLM judgements, so no verifier can re-derive them without paying for another run. What it can
do — and what this file does — is prove that the artifact is *internally honest*: every per-question score
recomputes from that question's own recorded evidence, the aggregate recomputes from the per-question scores,
the artifacts it names are the ones on disk, the set it scored is the set the answer layer answered, and
`docs/rag.md` quotes the numbers it describes.

The one thing it cannot check is whether the judge was right. That is stated in the artifact's own caveats
rather than papered over here.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
RAG_ROOT = REPO_ROOT / "registry" / "rag"
DOCS = REPO_ROOT / "docs"
METRICS = ("faithfulness", "answer_relevancy", "context_precision", "context_recall")
SECRET = re.compile(r"(AIza[0-9A-Za-z_\-]{30,}|AQ\.[0-9A-Za-z_\-]{20,})")


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# The canonical forms are recomputed here independently of the measurement script, from the files on disk.
# They are content fingerprints, not file hashes: the chain rewrites the artifacts' timestamps on every run.
def corpus_content(corpus: dict) -> str:
    rows = sorted((str(chunk["chunk_id"]), str(chunk["text"])) for chunk in corpus["chunks"])
    return sha256_text("\n".join(f"{cid}\t{text}" for cid, text in rows))


def answers_content(answers: dict) -> str:
    rows = sorted((str(row["id"]), str(row.get("status")), str(row.get("text") or ""),
                   ",".join(row.get("chunks_used") or [])) for row in answers["questions"])
    return sha256_text("\n".join("\t".join(row) for row in rows))


def eval_set_content(eval_set: dict) -> str:
    rows = sorted((str(row["id"]), str(row["question"]), str(row.get("reference_answer") or ""))
                  for row in eval_set["questions"])
    return sha256_text("\n".join("\t".join(row) for row in rows))


def mean(values):
    kept = [value for value in values if value is not None]
    return (sum(kept) / len(kept)) if kept else None


# The artifact stores six decimal places, so the verifier compares at that precision: a tighter tolerance
# would fail on the rounding it deliberately performs, which is a false failure and hides real ones.
def close(left, right, tolerance: float = 1e-6) -> bool:
    if left is None or right is None:
        return left is None and right is None
    return abs(float(left) - float(right)) <= tolerance


def anticipated_precision(flags: list[bool]) -> float:
    hits, total = 0, 0.0
    for position, flag in enumerate(flags, start=1):
        if flag:
            hits += 1
            total += hits / position
    return (total / hits) if hits else 0.0


def main() -> int:
    failures: list[str] = []
    index = json.loads((REPO_ROOT / "registry" / "dags" / "index.json").read_text(encoding="utf-8"))
    vintage = index["vintage_date"]
    out_path = RAG_ROOT / vintage / "answer_quality_eval.json"

    if not out_path.exists():
        print(f"FAILED — {out_path.relative_to(REPO_ROOT)} is missing: the answer-quality measurement "
              "has not been published")
        return 1
    text = out_path.read_text(encoding="utf-8")
    artifact = json.loads(text)

    if SECRET.search(text):
        failures.append("artifact: contains a string shaped like an API key — a secret must never reach a "
                        "committed artifact")
    if artifact.get("vintage") != vintage:
        failures.append(f"artifact: vintage {artifact.get('vintage')!r} != registry vintage {vintage!r}")
    if artifact.get("status") != "measured":
        failures.append(f"artifact: status {artifact.get('status')!r} — a partial run is not a measurement")

    # 1. The inputs it names are the inputs on disk, compared by content.
    inputs = artifact.get("inputs") or {}
    paths = {key: REPO_ROOT / str(inputs.get(key) or "") for key in ("corpus", "answer_eval", "eval_set")}
    for key, path in paths.items():
        if not path.exists():
            print(f"FAILED — {out_path.relative_to(REPO_ROOT)}: cannot verify without {path}")
            return 1
    corpus = json.loads(paths["corpus"].read_text(encoding="utf-8"))
    answers = json.loads(paths["answer_eval"].read_text(encoding="utf-8"))
    eval_set = json.loads(paths["eval_set"].read_text(encoding="utf-8"))
    for key, expected, actual in (
            ("corpus", inputs.get("corpus_content_sha256"), corpus_content(corpus)),
            ("answer_eval", inputs.get("answer_eval_content_sha256"), answers_content(answers)),
            ("eval_set", inputs.get("eval_set_content_sha256"), eval_set_content(eval_set))):
        if expected != actual:
            failures.append(f"inputs.{key}: content fingerprint does not match the file on disk — the "
                            "measurement describes different content than the artifact beside it")
    chunk_ids = {chunk["chunk_id"] for chunk in corpus["chunks"]}

    # 2. The set it scored is the set the answer layer answered.
    answered_ids = {row["id"] for row in answers["questions"]
                    if row.get("status") == "answered" and row["id"] in
                    {q["id"] for q in eval_set["questions"]}}
    scored_ids = {row["id"] for row in artifact["questions"]}
    excluded_ids = {row["id"] for row in artifact["excluded"]}
    if scored_ids | excluded_ids != {row["id"] for row in answers["questions"]}:
        failures.append("artifact: scored + excluded does not cover the answer-eval questions")
    if not scored_ids <= answered_ids:
        failures.append(f"artifact: scored a question the layer did not answer: "
                        f"{sorted(scored_ids - answered_ids)[:3]}")
    if scored_ids & excluded_ids:
        failures.append("artifact: a question is both scored and excluded")
    if artifact.get("scored") != len(artifact["questions"]):
        failures.append("artifact: `scored` disagrees with the number of question rows")
    if artifact.get("expected") != len(answered_ids):
        failures.append(f"artifact: `expected` is {artifact.get('expected')}, the answer layer answered "
                        f"{len(answered_ids)}")

    # 3. Every per-question score recomputes from that question's own evidence.
    for row in artifact["questions"]:
        detail = row.get("detail") or {}
        scores = row.get("scores") or {}
        statements = detail.get("statements") or []
        supported = detail.get("statement_supported") or []
        claims = detail.get("reference_claims") or []
        attributable = detail.get("claim_supported") or []
        flags = detail.get("context_usable") or []
        similarities = detail.get("similarities") or []

        if len(supported) != len(statements):
            failures.append(f"{row['id']}: {len(supported)} support flags for {len(statements)} statements")
        if len(attributable) != len(claims):
            failures.append(f"{row['id']}: {len(attributable)} claim flags for {len(claims)} claims")
        if len(flags) != len(row.get("contexts") or []):
            failures.append(f"{row['id']}: {len(flags)} context flags for "
                            f"{len(row.get('contexts') or [])} contexts")
        if row.get("contexts") and not set(row["contexts"]) <= chunk_ids:
            failures.append(f"{row['id']}: cites a chunk that is not in the corpus")

        expected_faithfulness = (sum(supported) / len(statements)) if statements else None
        expected_precision = anticipated_precision(flags) if row.get("contexts") else None
        expected_recall = (sum(attributable) / len(claims)) if claims else None
        expected_relevancy = (sum(similarities) / len(similarities)) if similarities else None
        for name, expected in (("faithfulness", expected_faithfulness),
                               ("context_precision", expected_precision),
                               ("context_recall", expected_recall),
                               ("answer_relevancy", expected_relevancy)):
            if not close(scores.get(name), expected):
                failures.append(f"{row['id']}: {name} is {scores.get(name)}; its own evidence gives "
                                f"{expected}")
        if detail.get("judge_replied") is not True:
            failures.append(f"{row['id']}: the judge's reply was not parsed — the scores above cannot come "
                            "from a judgement that did not happen")

    # 4. The aggregate recomputes from the rows.
    for name in METRICS:
        expected = mean([row["scores"].get(name) for row in artifact["questions"]])
        if not close(artifact["metrics"].get(name), expected):
            failures.append(f"metrics.{name} is {artifact['metrics'].get(name)}; the rows give {expected}")

    # 5. It says what it is, and what it is not.
    source = artifact.get("metric_source") or {}
    if source.get("library") is not False:
        failures.append("metric_source.library must be false: the ragas package was not installed")
    if not str(source.get("comparability") or "").lower().startswith("scores are not comparable"):
        failures.append("metric_source.comparability: the artifact must say its scores are not comparable "
                        "to a ragas library run")
    if not re.fullmatch(r"[0-9a-f]{64}", str(source.get("prompt_sha256") or "")):
        failures.append("metric_source.prompt_sha256: the judge prompt is not fingerprinted")
    judge = artifact.get("judge") or {}
    if not judge.get("model"):
        failures.append("judge.model: the artifact does not name its judge")

    # 6. The narrative quotes the numbers it describes.
    narrative = DOCS / "rag.md"
    prose = narrative.read_text(encoding="utf-8") if narrative.exists() else ""
    for name in METRICS:
        value = artifact["metrics"].get(name)
        needle = f"{value:.3f}" if value is not None else "n/a"
        if needle not in prose:
            failures.append(f"docs/rag.md: does not quote {name} ({needle}) — the page has drifted from the "
                            "artifact it describes")

    print(f"artifact      : {out_path.relative_to(REPO_ROOT)} — {artifact['scored']} of "
          f"{artifact['expected']} answered question(s), judge {judge.get('model')}")
    for name in METRICS:
        value = artifact["metrics"].get(name)
        print(f"  {name:18} {'n/a' if value is None else f'{value:.4f}'}")
    print("independent   : every per-question score recomputes from its own recorded evidence; the "
          "aggregates recompute from the rows")
    print("attribution   : the corpus, answer-eval and eval-set content fingerprints match the files on disk")
    print("honesty       : library=false, comparability stated, prompt fingerprinted, no key in the artifact")
    print("narrative     : docs/rag.md quotes the four measured values")
    print()

    if failures:
        print(f"FAILED — {len(failures)} problem(s):")
        for problem in failures[:40]:
            print(f"  - {problem}")
        if len(failures) > 40:
            print(f"  … and {len(failures) - 40} more")
        return 1
    print("PASS — the measurement is internally consistent, attributed to the artifacts it names, and "
          "described as what it is: the RAGAS definitions implemented here, not the ragas library")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
