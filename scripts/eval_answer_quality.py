"""Answer-quality measurement: the four RAGAS metric definitions, implemented here.

Why this exists, and what it is not
-----------------------------------
`docs/rag.md` has carried `ragas: not_run` since the corpus was built, with the reason: RAGAS needs a
generation step and a judge model, and neither existed. A Gemini key now exists, so the measurement can be
made — but the `ragas` library is **not installed** in this repository or in any of the machine's
environments, and installing it would add a dependency tree to a project whose answering path deliberately
has none.

So the four metrics are implemented against their published definitions, with the judge prompt written here
and hashed into the artifact. The artifact says `library: false` and name-checks the difference, because a
score produced by this file is *not* numerically comparable to a `ragas` library run: the prompt, the
decomposition and the weighting are this repository's. What it does measure is the same four questions RAGAS
asks — is the answer supported by its context, does it answer the question, is the context precise, does the
context carry the reference answer.

    faithfulness        supported statements / statements in the answer
    answer_relevancy    mean cosine(question, question generated from the answer), n=3
    context_precision   average precision over the cited chunks judged useful
    context_recall      reference claims attributable to the contexts / reference claims

One judge call per question, not one per item
---------------------------------------------
The free tier on this key allows 20 `gemini-2.5-flash` requests per window, which a per-statement design
would exhaust on the second question. The judgement is therefore one structured call per question returning
every part the four metrics need, and the embeddings are one batched call. That is a working-paper detail,
stated in the artifact: the *definitions* are unchanged, the call pattern is not RAGAS's.

Only questions the layer actually answered are scored: a refusal has no answer to judge, and an out-of-scope
question has no answer by design. The count is recorded, not assumed.

No secret is written anywhere. The key comes from `GOOGLE_API_KEY`, or from `--key-file`.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC_PATH = Path("analysis/specs/rag.yml")
INDEX_PATH = Path("registry/dags/index.json")
CORPUS_PATH = "registry/rag/{vintage}/corpus.json"
ANSWER_PATH = "registry/rag/{vintage}/answer_eval.json"
EVAL_PATH = "registry/rag/{vintage}/eval_set.json"
OUT_PATH = "registry/rag/{vintage}/answer_quality_eval.json"

API_ROOT = "https://generativelanguage.googleapis.com/v1beta"
# `gemini-3.5-flash-lite` is the judge: 1.2 s per call on this key, against 6 s for `gemini-2.5-flash`
# (whose free tier is 20 requests) and 112 s for `gemini-3.8-flash`. The model is recorded in the artifact,
# so the choice is inspectable rather than implied.
DEFAULT_MODEL = "gemini-3.5-flash-lite"
DEFAULT_EMBED_MODEL = "gemini-embedding-001"
EMBED_DIM = 768

PROMPT_JUDGE = """You are evaluating an answer produced by a retrieval-augmented system. You will be given \
the QUESTION, the ANSWER, the CONTEXTS the answer cites, and a REFERENCE ANSWER written by the project.

Do all five tasks below, judging only what the text says and never adding outside knowledge.

1. Break the ANSWER into atomic factual statements. Each statement must be self-contained and keep every
   number and qualifier exactly as written.
2. For each statement, decide whether the CONTEXTS support it. Supported means the contexts state the same
   fact; being on the same topic is not support, and a number must appear with the same meaning.
3. Write 3 questions that the ANSWER answers, phrased as a reader would ask them.
4. For each numbered CONTEXT, decide whether it is useful for producing the REFERENCE ANSWER. Useful means
   it carries information the reference answer needs.
5. Break the REFERENCE ANSWER into atomic claims, and for each claim decide whether the CONTEXTS state it or
   imply it directly.

QUESTION:
{question}

ANSWER:
{answer}

CONTEXTS:
{contexts}

REFERENCE ANSWER:
{reference}

Reply with JSON only, using exactly these keys:
{{"statements": ["..."], "statement_supported": [true], "generated_questions": ["..."],
 "context_usable": [true], "reference_claims": ["..."], "claim_supported": [true]}}
The three boolean lists must have one entry per item in the list beside them."""


class ApiError(RuntimeError):
    pass


class UnparsedJudge(RuntimeError):
    """The judge replied with something that is not the JSON object the prompt asked for.

    This is not a low score and must never be recorded as one: on the first published run a single question
    came back unparseable, and writing its empty lists through as nulls made a failed call look like a
    measurement. The caller skips the question and says so.
    """


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def content_sha256_corpus(corpus: dict) -> str:
    """A fingerprint of the corpus's *content*, not its bytes.

    The chain rebuilds `corpus.json` on every verification run, which rewrites `generated_at` and therefore
    the file's hash while the chunks are identical. A file hash would make this artifact stale every time the
    chain ran; a content hash changes only when a chunk's text does, which is what the measurement depends on.
    """
    rows = sorted((str(chunk["chunk_id"]), str(chunk["text"])) for chunk in corpus["chunks"])
    return sha256_text("\n".join(f"{cid}\t{text}" for cid, text in rows))


def content_sha256_answers(answers: dict) -> str:
    """The answered rows this measurement reads: id, status, answer text and the chunks it cited."""
    rows = sorted((str(row["id"]), str(row.get("status")), str(row.get("text") or ""),
                   ",".join(row.get("chunks_used") or [])) for row in answers["questions"])
    return sha256_text("\n".join("\t".join(row) for row in rows))


def content_sha256_eval_set(eval_set: dict) -> str:
    """The questions and reference answers the scoring is read against."""
    rows = sorted((str(row["id"]), str(row["question"]), str(row.get("reference_answer") or ""))
                  for row in eval_set["questions"])
    return sha256_text("\n".join("\t".join(row) for row in rows))


class Gemini:
    """The smallest client that can judge: REST, a key, retries on the free tier's throttles."""

    def __init__(self, key: str, model: str, embed_model: str, sleep: float) -> None:
        self.key, self.model, self.embed_model = key, model, embed_model
        self.sleep = sleep
        self.calls = 0

    def _post(self, url: str, payload: dict, attempts: int = 5) -> dict:
        body = json.dumps(payload).encode("utf-8")
        delay = 2.0
        for attempt in range(1, attempts + 1):
            request = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
            try:
                with urllib.request.urlopen(request, timeout=120) as response:
                    self.calls += 1
                    if self.sleep:
                        time.sleep(self.sleep)
                    return json.loads(response.read().decode("utf-8"))
            # HTTPError is a subclass of OSError, so it is caught first: a 503 is the service queueing,
            # not a dead socket, and both are retried with the same backoff.
            except urllib.error.HTTPError as error:
                detail = error.read().decode("utf-8", "replace")[:300]
                if error.code in (429, 500, 502, 503, 504) and attempt < attempts:
                    time.sleep(delay)
                    delay *= 2
                    continue
                raise ApiError(f"HTTP {error.code}: {detail}") from error
            except (TimeoutError, OSError) as error:
                if attempt < attempts:
                    time.sleep(delay)
                    delay *= 2
                    continue
                raise ApiError(f"network: {error}") from error
        raise ApiError("exhausted retries")

    def generate(self, prompt: str) -> str:
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.0, "responseMimeType": "application/json"},
        }
        data = self._post(f"{API_ROOT}/models/{self.model}:generateContent?key={self.key}", payload)
        candidates = data.get("candidates") or []
        if not candidates:
            raise ApiError(f"no candidates: {json.dumps(data)[:200]}")
        parts = (candidates[0].get("content") or {}).get("parts") or []
        return "".join(str(part.get("text") or "") for part in parts).strip()

    def embed_many(self, texts: list[str]) -> list[list[float]]:
        payload = {"requests": [
            {"model": f"models/{self.embed_model}",
             "content": {"parts": [{"text": text}]},
             "outputDimensionality": EMBED_DIM}
            for text in texts
        ]}
        data = self._post(f"{API_ROOT}/models/{self.embed_model}:batchEmbedContents?key={self.key}", payload)
        embeddings = data.get("embeddings") or []
        if len(embeddings) != len(texts):
            raise ApiError(f"expected {len(texts)} embeddings, got {len(embeddings)}")
        return [[float(value) for value in item["values"]] for item in embeddings]


def parse_json(text: str) -> dict:
    """The JSON object a judge replied with, or an empty one — never a crash on a chatty reply."""
    try:
        body = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            return {}
        try:
            body = json.loads(match.group(0))
        except json.JSONDecodeError:
            return {}
    return body if isinstance(body, dict) else {}


def text_list(body: dict, key: str) -> list[str]:
    values = body.get(key)
    if not isinstance(values, list):
        return []
    return [str(value).strip() for value in values if str(value).strip()]


def flag_list(body: dict, key: str, size: int) -> list[bool]:
    """A boolean list aligned to `size`. A short or chatty reply yields False, which is the safe direction
    for every one of these metrics: an unsupported claim is not counted as supported."""
    values = body.get(key)
    if not isinstance(values, list):
        return [False] * size
    out = []
    for index in range(size):
        value = values[index] if index < len(values) else False
        if isinstance(value, bool):
            out.append(value)
        else:
            out.append(str(value).strip().lower().startswith(("true", "yes", "1")))
    return out


def report(value: float | None) -> float | None:
    """A score as the artifact stores it: six places, inside [0, 1].

    The clamp is not cosmetic. Averaging cosine similarities produced 1.0000000000000002 in the published
    artifact, which is outside the range a metric can take and failed the schema — the arithmetic is right
    and the representation was wrong.
    """
    if value is None:
        return None
    return round(min(max(float(value), 0.0), 1.0), 6)


def cosine(left: list[float], right: list[float]) -> float:
    dot = sum(a * b for a, b in zip(left, right))
    norm = math.sqrt(sum(a * a for a in left)) * math.sqrt(sum(b * b for b in right))
    return dot / norm if norm else 0.0


def score_question(client: Gemini, row: dict, chunks: dict[str, str], n_questions: int,
                   max_contexts: int) -> dict:
    """The four metrics for one answered question, from a single structured judgement."""
    question = row["question"]
    answer = row.get("text") or ""
    reference = row.get("reference_answer") or ""
    context_ids = [cid for cid in (row.get("chunks_used") or []) if cid in chunks][:max_contexts]
    contexts = [chunks[cid] for cid in context_ids]
    numbered = "\n\n".join(f"[{position}] {text}" for position, text in enumerate(contexts, start=1)) or "(none)"

    prompt = PROMPT_JUDGE.format(question=question, answer=answer, contexts=numbered, reference=reference)
    body: dict = {}
    for attempt in range(4):
        body = parse_json(client.generate(prompt))
        if body and ("statements" in body or "reference_claims" in body):
            break
        time.sleep(1.5 * (attempt + 1))
    if not body:
        raise UnparsedJudge(f"{row['id']}: no JSON object in the judge's reply after 4 attempts")

    statements = text_list(body, "statements")
    supported = flag_list(body, "statement_supported", len(statements))
    generated = text_list(body, "generated_questions")[:n_questions]
    usable = flag_list(body, "context_usable", len(contexts))
    claims = text_list(body, "reference_claims")
    attributable = flag_list(body, "claim_supported", len(claims))

    faithfulness = (sum(supported) / len(statements)) if statements else None

    vectors = client.embed_many([question] + generated) if generated else []
    # Rounded and clamped like every other stored number: a cosine of a vector with itself arrives as
    # 1.0000000000000002, which is correct arithmetic and an invalid metric value.
    similarities = [round(min(max(cosine(vectors[0], vector), -1.0), 1.0), 6)
                    for vector in vectors[1:]] if vectors else []
    answer_relevancy = (sum(similarities) / len(similarities)) if similarities else None

    context_precision = None
    if contexts:
        hits, precision_sum = 0, 0.0
        for position, flag in enumerate(usable, start=1):
            if flag:
                hits += 1
                precision_sum += hits / position
        context_precision = (precision_sum / hits) if hits else 0.0

    context_recall = (sum(attributable) / len(claims)) if claims else None

    return {
        "id": row["id"],
        "question": question,
        "contexts": context_ids,
        "answer_chars": len(answer),
        "scores": {
            "faithfulness": report(faithfulness),
            "answer_relevancy": report(answer_relevancy),
            "context_precision": report(context_precision),
            "context_recall": report(context_recall),
        },
        "detail": {
            "statements": statements,
            "statement_supported": supported,
            "generated_questions": generated,
            "similarities": similarities,
            "context_usable": usable,
            "reference_claims": claims,
            "claim_supported": attributable,
            "judge_replied": bool(body),
        },
    }


def mean(values: list[float | None]) -> float | None:
    kept = [value for value in values if value is not None]
    return (sum(kept) / len(kept)) if kept else None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Measure answer quality against the RAGAS definitions.")
    parser.add_argument("--model", default=os.environ.get("JUDGE_MODEL", DEFAULT_MODEL))
    parser.add_argument("--embed-model", default=os.environ.get("JUDGE_EMBED_MODEL", DEFAULT_EMBED_MODEL))
    parser.add_argument("--key-file", default=None, help="read the API key from this file instead of the env")
    parser.add_argument("--limit", type=int, default=0, help="score at most N questions (smoke test)")
    parser.add_argument("--sleep", type=float, default=1.0, help="seconds between judged calls (free tier)")
    parser.add_argument("--n-questions", type=int, default=3)
    parser.add_argument("--max-contexts", type=int, default=4)
    args = parser.parse_args(argv)

    key = os.environ.get("GOOGLE_API_KEY", "").strip()
    if not key and args.key_file:
        key = Path(args.key_file).read_text(encoding="utf-8").strip()
    if not key:
        print("no key: set GOOGLE_API_KEY or pass --key-file", file=sys.stderr)
        return 2

    spec = yaml.safe_load((REPO_ROOT / SPEC_PATH).read_text(encoding="utf-8"))
    index = json.loads((REPO_ROOT / INDEX_PATH).read_text(encoding="utf-8"))
    vintage = index["vintage_date"]
    corpus_path = REPO_ROOT / CORPUS_PATH.format(vintage=vintage)
    answer_path = REPO_ROOT / ANSWER_PATH.format(vintage=vintage)
    eval_path = REPO_ROOT / EVAL_PATH.format(vintage=vintage)
    out_path = REPO_ROOT / OUT_PATH.format(vintage=vintage)

    corpus = json.loads(corpus_path.read_text(encoding="utf-8"))
    answers = json.loads(answer_path.read_text(encoding="utf-8"))
    eval_set = json.loads(eval_path.read_text(encoding="utf-8"))
    chunks = {chunk["chunk_id"]: chunk["text"] for chunk in corpus["chunks"]}
    references = {row["id"]: row.get("reference_answer") or "" for row in eval_set["questions"]}

    answered = [row for row in answers["questions"]
                if row.get("status") == "answered" and row["id"] in references]
    # Declared against the whole answer set, not the truncated run: `--limit` is a smoke test, and an
    # exclusion list that grew with the limit would misdescribe what the measurement covers.
    scored_ids = {row["id"] for row in answered}
    excluded = [{"id": row["id"], "why": f"status={row.get('status')}"}
                for row in answers["questions"] if row["id"] not in scored_ids]
    if args.limit:
        answered = answered[: args.limit]

    client = Gemini(key, args.model, args.embed_model, args.sleep)
    failed: list[dict] = []
    rows: list[dict] = []
    if out_path.exists():
        previous = json.loads(out_path.read_text(encoding="utf-8"))
        rows = [row for row in previous.get("questions") or [] if row["id"] in {a["id"] for a in answered}]
    done = {row["id"] for row in rows}

    for row in answered:
        if row["id"] in done:
            print(f"skip {row['id']} (already scored)")
            continue
        payload = dict(row)
        payload["reference_answer"] = references[row["id"]]
        try:
            scored = score_question(client, payload, chunks, args.n_questions, args.max_contexts)
        except UnparsedJudge as error:
            print(f"SKIP {error}")
            failed.append({"id": row["id"], "why": "judge reply could not be parsed — rerun scores it"})
            continue
        rows.append(scored)
        print(f"{row['id']}: " + ", ".join(
            f"{name}={value:.3f}" if isinstance(value, float) else f"{name}=n/a"
            for name, value in scored["scores"].items()))
        # Written after every question: a throttled free tier must not cost the whole run.
        partial = {name: report(mean([r["scores"][name] for r in rows]))
                   for name in ("faithfulness", "answer_relevancy", "context_precision", "context_recall")}
        artifact = {
            "schema_version": 1,
            "layer": "answer quality — the four RAGAS metric definitions, implemented in this repository",
            "vintage": vintage,
            "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "status": "partial" if (len(rows) < len(scored_ids) or failed) else "measured",
            "metric_source": {
                "library": False,
                "why": "the `ragas` package is not installed in this repository or on this machine, and the "
                       "answering path is deliberately dependency-free; the definitions are implemented in "
                       "scripts/eval_answer_quality.py",
                "definitions": {
                    "faithfulness": "supported statements / statements in the answer",
                    "answer_relevancy": "mean cosine(question, question generated from the answer)",
                    "context_precision": "average precision over cited chunks judged useful",
                    "context_recall": "reference claims attributable to the contexts / reference claims",
                },
                "comparability": "scores are NOT comparable to a `ragas` library run: the prompt, the "
                                 "decomposition and the call pattern are this repository's",
                "call_pattern": "one structured judge call per question plus one batched embedding call, "
                                "because this key's free tier allows 20 requests per window",
                "prompt_sha256": sha256_text(PROMPT_JUDGE),
            },
            "judge": {"provider": "Google Generative Language REST", "model": args.model,
                      "temperature": 0.0, "embedding_model": args.embed_model, "embedding_dim": EMBED_DIM,
                      "n_generated_questions": args.n_questions, "max_contexts": args.max_contexts,
                      "calls": client.calls},
            "inputs": {
                "corpus": str(corpus_path.relative_to(REPO_ROOT)).replace("\\", "/"),
                "corpus_content_sha256": content_sha256_corpus(corpus),
                "answer_eval": str(answer_path.relative_to(REPO_ROOT)).replace("\\", "/"),
                "answer_eval_content_sha256": content_sha256_answers(answers),
                "eval_set": str(eval_path.relative_to(REPO_ROOT)).replace("\\", "/"),
                "eval_set_content_sha256": content_sha256_eval_set(eval_set),
            },
            "scored": len(rows),
            "expected": len(scored_ids),
            "excluded": excluded + failed,
            "metrics": partial,
            "caveats": [
                "faithfulness is near 1.0 by construction when the answer is a selection of quoted corpus "
                "paragraphs — it measures the contract, not the retrieval's judgement",
                "the judge is one model at temperature 0; a different judge would move these numbers",
                "the free tier throttles, so the run is resumable rather than fast: a question is scored "
                "once and skipped on the next run",
            ],
            "questions": rows,
        }
        out_path.write_text(json.dumps(artifact, indent=1, ensure_ascii=False) + "\n",
                            encoding="utf-8", newline="\n")

    artifact = json.loads(out_path.read_text(encoding="utf-8"))
    print()
    print(f"artifact : {out_path.relative_to(REPO_ROOT)} — {artifact['status']}, {artifact['scored']} "
          f"question(s), {client.calls} call(s) this run")
    for name, value in artifact["metrics"].items():
        print(f"  {name:18} {'n/a' if value is None else f'{value:.4f}'}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ApiError as error:
        print(f"API FAILED — {error}", file=sys.stderr)
        raise SystemExit(3)
