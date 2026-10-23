"""Independent verification of the Stage 9 answer layer and its measurement.

The layer answers a question only when the gate lets it, the corpus supplies an estimate, an identifying
assumption and what it cannot rule out, and every quoted sentence is attributable to a cited chunk. This
verifier checks those claims from the artifacts, without importing `app/answer_layer.py`:

  * **Every answer carries the contract's parts**, and its `check` says so.
  * **Every sentence is extractive.** The content after each label must appear verbatim in the text of the
    cited chunks, so an answer cannot contain a sentence the corpus does not.
  * **Every number is in its citation.** A quoted number absent from the cited chunk's own text fails.
  * **A gate refusal is honoured.** A question the intent artifact routed away from `answerable` cannot be
    answered here, and a refusal must cite the chunk the gate pinned.
  * **The counts are recomputed** from the artifact's own rows.
  * **The module imports no model.** The source is scanned for database, network and fitting imports.

A low answer rate is not a failure: R-04 is an estimate contract, so questions about coverage, status or
dates are declined with the refusal template, and the rate is published rather than tuned (the Stage 7
precedent). What fails here is an answer that is missing a part, quotes a number its citation does not
contain, or contradicts the gate.

Usage:
    python tests/verify_answer.py
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
RAG_SPEC_PATH = REPO_ROOT / "analysis" / "specs" / "rag.yml"
GATE_SPEC_PATH = REPO_ROOT / "analysis" / "specs" / "intent_gate.yml"
INDEX_PATH = REPO_ROOT / "registry" / "dags" / "index.json"
LAYER_PATH = REPO_ROOT / "app" / "answer_layer.py"
RAG_ROOT = REPO_ROOT / "registry" / "rag"

INTERVAL = re.compile(r"\[\s*[−+\-]?\d[\d,.]*\s*,\s*[−+\-]?\d[\d,.]*\s*\]")
ASSUMPTION = re.compile(r"\bassum\w*", re.IGNORECASE)
CANNOT_RULE_OUT = re.compile(r"cannot\s+rule\s+out", re.IGNORECASE)
NUMBER = re.compile(r"[−+\-]?\d[\d,]*(?:\.\d+)?")
PART_HEADER = re.compile(r"^\[.*?\bpart \d+ of \d+\]\s*$", re.MULTILINE)
GLOSSARY_ROW = re.compile(r"^\|\s*\*\*(?P<term>[^*]+)\*\*\s*\|\s*(?P<meaning>[^|]+?)\s*\|\s*$")
LABEL = re.compile(r"^\*\*(?:Question|Estimate|Why there is no number|The check that decided it|"
                   r"Identifying assumption|What it cannot rule out|The passage that answers this|"
                   r"The record says|Citation):\*\* ", re.MULTILINE)
REASON_CODE = re.compile(r"Reason code:|not_run|No estimate for this|not estimated here", re.IGNORECASE)
# The contract declares an order per shape, in names rather than in labels. This is the map from one
# to the other, and the verifier checks the answer's sections appear in that order.
ORDER_LABELS = {
    "question": "**Question:**",
    "estimate_with_interval": "**Estimate:**",
    "reason_code": "**Why there is no number:**",
    "deciding_check": "**The check that decided it:**",
    "identifying_assumption": "**Identifying assumption:**",
    "what_it_cannot_rule_out": "**What it cannot rule out:**",
    "passage": "**The record says:**",
    "citation": "**Citation:**",
}
# The plain reading repeats the shape's sections for a reader who does not work with statistics.
PLAIN_LABELS = {
    "estimate": ("**Short answer:**", "**The number:**", "**What it assumes:**",
                 "**What it cannot tell you:**", "**Where this comes from:**"),
    "no_estimate": ("**Short answer:**", "**Why there is no number:**", "**What it assumes:**",
                    "**What it cannot tell you:**", "**Where this comes from:**"),
    "fact": ("**Short answer:**", "**The record says:**", "**Where this comes from:**"),
}
FORBIDDEN = re.compile(
    r"^\s*(?:import|from)\s+(?:duckdb|sqlite3|psycopg2|sqlalchemy|requests|httpx|urllib|aiohttp|"
    r"torch|transformers|sentence_transformers|statsmodels|sklearn|scipy|linearmodels|synthdid)\b",
    re.MULTILINE,
)


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def flat(text: str) -> str:
    return " ".join(str(text).split())


def numbers_of(text: str) -> set[str]:
    return {match.replace(",", "") for match in NUMBER.findall(text)}


def answer_body(text: str) -> str:
    """The answer's own words: the question it repeats and the citation it carries are not quotes."""
    return "\n".join(line for line in str(text).splitlines()
                     if not line.startswith(("**Question:**", "**Citation:**")))


def plain_body(text: str) -> str:
    """The plain reading's own words, without the line that says where the answer comes from."""
    return "\n".join(line for line in str(text).splitlines()
                     if not line.startswith("**Where this comes from:**"))


def main() -> int:
    failures: list[str] = []
    if not LAYER_PATH.exists():
        print("FAILED — app/answer_layer.py is missing")
        return 1

    index = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    vintage = index["vintage_date"]
    rag_dir = RAG_ROOT / vintage
    artifact_path = rag_dir / "answer_eval.json"
    if not artifact_path.exists():
        print(f"FAILED — {artifact_path.relative_to(REPO_ROOT)} is missing — run scripts/eval_answer.py")
        return 1

    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    corpus = json.loads((rag_dir / "corpus.json").read_text(encoding="utf-8"))
    intent_eval = json.loads((rag_dir / "intent_eval.json").read_text(encoding="utf-8"))
    rag_spec = yaml.safe_load(RAG_SPEC_PATH.read_text(encoding="utf-8"))
    contract = rag_spec["answer_contract"]
    chunks = {chunk["chunk_id"]: chunk for chunk in corpus["chunks"]}

    # ---------------------------------------------------------------------------------------------
    # 1. The artifact describes the corpus, the gate and the contract it was measured on
    # ---------------------------------------------------------------------------------------------
    if artifact.get("vintage") != vintage:
        failures.append(f"the artifact carries vintage {artifact.get('vintage')!r}, not {vintage!r}")
    if (artifact.get("corpus") or {}).get("sha256") != sha256_of(rag_dir / "corpus.json"):
        failures.append("the artifact records a corpus sha256 that does not match corpus.json")
    if (artifact.get("corpus") or {}).get("chunks") != len(corpus["chunks"]):
        failures.append("the artifact's chunk count does not match the corpus")
    if (artifact.get("gate") or {}).get("artifact_sha256") != sha256_of(rag_dir / "intent_eval.json"):
        failures.append("the artifact was measured against a different intent_eval.json — re-run "
                        "scripts/eval_answer.py after scripts/eval_intent.py")
    if (artifact.get("contract") or {}).get("sha256") != sha256_of(RAG_SPEC_PATH):
        failures.append("the artifact records a hash for analysis/specs/rag.yml that no longer matches")
    if (artifact.get("contract") or {}).get("refusal_template") != contract.get("refusal_template"):
        failures.append("the artifact's refusal template is not the contract's")
    if (artifact.get("gate") or {}).get("sha256") != sha256_of(GATE_SPEC_PATH):
        failures.append("the artifact records a gate-spec hash that no longer matches the file")

    template = str(contract["refusal_template"])
    prefix = template.split("{reason}")[0]

    # The gate's own decisions, for cross-checking that the layer did not answer around them.
    gate_intent: dict[str, str] = {}
    gate_route: dict[str, str | None] = {}
    for row in (intent_eval.get("published_set") or {}).get("questions") or []:
        gate_intent[row["id"]] = row["intent"]
        gate_route[row["id"]] = row.get("route")
    for row in (intent_eval.get("held_out") or {}).get("questions") or []:
        gate_intent[f"heldout_{row['id']}"] = row["intent"]
        gate_route[f"heldout_{row['id']}"] = row.get("route")

    rows = artifact.get("questions") or []
    if not rows:
        failures.append("the artifact measures no questions")

    # ---------------------------------------------------------------------------------------------
    # 2. Every row: gate honoured, parts present, sentences extractive, numbers cited
    # ---------------------------------------------------------------------------------------------
    glossary_path = REPO_ROOT / "docs" / "glossary.md"
    glossary = flat(glossary_path.read_text(encoding="utf-8")) if glossary_path.exists() else ""
    if not glossary:
        failures.append("docs/glossary.md: missing — the plain-language readings have no source")

    for row in rows:
        question_id = row.get("id")
        status = row.get("status")
        text = str(row.get("text") or "")
        if question_id not in gate_intent:
            failures.append(f"{question_id}: the question is not in the intent artifact, so the gate's "
                            "decision cannot be cross-checked")
            continue
        if row.get("intent") != gate_intent[question_id]:
            failures.append(f"{question_id}: the layer records intent {row.get('intent')!r} and the gate "
                            f"artifact says {gate_intent[question_id]!r}")
        if not text:
            failures.append(f"{question_id}: empty answer text")
            continue

        if status == "refused":
            if gate_intent[question_id] == "answerable":
                failures.append(f"{question_id}: refused although the gate left it answerable")
            if not row.get("citation"):
                failures.append(f"{question_id}: a refusal without a citation")
            if not text.startswith(prefix):
                failures.append(f"{question_id}: a refusal that does not use the contract's template")
            if row.get("route") != gate_route.get(question_id):
                failures.append(f"{question_id}: the refusal cites {row.get('route')!r} and the gate "
                                f"pinned {gate_route.get(question_id)!r}")
            if row.get("route") not in chunks:
                failures.append(f"{question_id}: the refusal cites a chunk that is not in the corpus")
            continue

        if status == "declined":
            if gate_intent[question_id] != "answerable":
                failures.append(f"{question_id}: declined although the gate had already refused it")
            if not text.startswith(prefix):
                failures.append(f"{question_id}: a declined answer that does not use the refusal template")
            continue

        if status != "answered":
            failures.append(f"{question_id}: unknown status {status!r}")
            continue

        # An answered row must carry the parts its shape requires, and its own check must say so.
        shape = str(row.get("shape") or "")
        spec = (contract.get("shapes") or {}).get(shape)
        if not spec:
            failures.append(f"{question_id}: the row carries shape {shape!r}, which the contract does "
                            "not declare")
            continue
        check = row.get("check") or {}
        for part in spec.get("requires") or []:
            if check.get(part) is not True:
                failures.append(f"{question_id}: the {shape} shape requires {part!r} and the row's "
                                f"check says {check.get(part)!r}")
        for part in spec.get("forbids") or []:
            if check.get(part):
                failures.append(f"{question_id}: the {shape} shape forbids {part!r} and the row's "
                                f"check says {check.get(part)!r}")
        if shape == "estimate":
            if not INTERVAL.search(text):
                failures.append(f"{question_id}: an estimate answer carries no interval")
            if not ASSUMPTION.search(text):
                failures.append(f"{question_id}: an estimate answer carries no identifying assumption")
            if not CANNOT_RULE_OUT.search(text):
                failures.append(f"{question_id}: an estimate answer does not say what it cannot rule out")
        elif shape == "no_estimate":
            if not REASON_CODE.search(text):
                failures.append(f"{question_id}: a reason answer carries no reason code")
            if INTERVAL.search(text):
                failures.append(f"{question_id}: a reason answer carries an interval — it is an "
                                "estimate answer wearing a reason's label")
        elif shape == "fact":
            if INTERVAL.search(text):
                failures.append(f"{question_id}: a fact answer carries an interval")
            if "**The record says:**" not in text:
                failures.append(f"{question_id}: a fact answer quotes no passage")
        if "**Citation:**" not in text:
            failures.append(f"{question_id}: the answer carries no citation")

        # The contract declares an order per shape, and the answer's sections must follow it.
        positions = []
        for part in spec.get("order") or []:
            label = ORDER_LABELS.get(part)
            if not label:
                failures.append(f"{question_id}: the contract's order names {part!r}, which the "
                                "verifier does not know how to look for")
                continue
            at = text.find(label)
            if at < 0:
                failures.append(f"{question_id}: the {shape} shape orders {part!r} and the answer has "
                                f"no {label} section")
            positions.append((part, at))
        if all(at >= 0 for _part, at in positions):
            # The element expression is read in the enclosing scope, so the tuple is unpacked under
            # its own name: a comprehension variable called `part` would silently be the loop's last
            # value rather than the section's.
            ordered = [name for name, _at in sorted(positions, key=lambda item: item[1])]
            declared = [part for part in spec.get("order") or []
                        if any(part == other for other, _at in positions)]
            if ordered != declared:
                failures.append(f"{question_id}: the answer's sections are in the order {ordered} and "
                                f"the contract declares {declared}")

        # Every quoted sentence must exist in a cited chunk.
        cited = row.get("chunks_used") or []
        missing_chunks = [cid for cid in cited if cid not in chunks]
        if missing_chunks:
            failures.append(f"{question_id}: cites chunks that are not in the corpus: {missing_chunks}")
            continue
        bodies = []
        for cid in cited:
            # A cited chunk is cited with its parts: the corpus splits a long document into
            # `<id>#p2`, `<id>#p3`, and the answer quotes a paragraph that lives in one of them.
            # The part ids are derived from the corpus itself, not from the layer.
            family = [cid] + [other for other in chunks if other.startswith(f"{cid}#p")]
            for member in family:
                body = PART_HEADER.sub("", str(chunks[member].get("text") or ""))
                bodies.append(flat(body))
        corpus_text = flat(" ".join(bodies))
        corpus_numbers = numbers_of(corpus_text)
        for line in text.splitlines():
            if not line.strip() or line.startswith("**Question:**") or line.startswith("**Citation:**"):
                continue
            content = LABEL.sub("", line).strip()
            if not content or content.startswith("not present in the retrieved passages"):
                failures.append(f"{question_id}: an answer slot is empty — {line.strip()[:80]!r}")
                continue
            if flat(content) not in corpus_text:
                failures.append(f"{question_id}: a quoted sentence is not in any cited chunk — "
                                f"{content[:90]!r}")

        # Every quoted number must be in the citation, and the artifact's own count must agree.
        quoted = numbers_of(answer_body(text))
        absent = sorted(number for number in quoted if number not in corpus_numbers)
        if absent:
            failures.append(f"{question_id}: quotes numbers absent from the cited chunks: {absent[:6]}")
        if sorted(row.get("numbers_absent_from_citation") or []) != absent:
            failures.append(f"{question_id}: the artifact records "
                            f"{row.get('numbers_absent_from_citation')!r} as absent and this verifier "
                            f"finds {absent!r}")

        # The plain-language reading: same parts, same numbers, definitions from the glossary.
        plain = row.get("plain") or {}
        plain_text = str(plain.get("text") or "")
        if not plain_text:
            failures.append(f"{question_id}: answered with no plain-language reading")
            continue
        for label in PLAIN_LABELS.get(shape, ()):
            if label not in plain_text:
                failures.append(f"{question_id}: the plain reading is missing the section {label!r}")
        plain_absent = sorted(number for number in numbers_of(plain_body(plain_text))
                              if number not in corpus_numbers)
        if plain_absent:
            failures.append(f"{question_id}: the plain reading quotes numbers absent from the cited "
                            f"chunks: {plain_absent[:6]}")
        if sorted(row.get("plain_numbers_absent_from_citation") or []) != plain_absent:
            failures.append(f"{question_id}: the artifact records "
                            f"{row.get('plain_numbers_absent_from_citation')!r} as absent from the plain "
                            f"reading and this verifier finds {plain_absent!r}")
        reading = plain.get("reading")
        if reading:
            interval = INTERVAL.search(text)
            coefficient = re.search(r"=\s*([−+\-]?\d[\d,]*\.?\d*)", text)
            if not interval or not coefficient:
                failures.append(f"{question_id}: the plain reading claims a coefficient the answer does "
                                "not carry")
            else:
                low_text, high_text = [part.strip() for part in
                                       interval.group(0).strip("[]").split(",")]

                def number(value: str) -> float:
                    return float(value.replace("−", "-").replace(",", ""))

                low, high = number(low_text), number(high_text)
                value = number(coefficient.group(1))
                expected = {
                    "coefficient": coefficient.group(1),
                    "interval_low": low_text,
                    "interval_high": high_text,
                    "includes_zero": low <= 0 <= high,
                    "direction": "negative" if value < 0 else ("positive" if value > 0 else "zero"),
                }
                for key, want in expected.items():
                    if reading.get(key) != want:
                        failures.append(f"{question_id}: the plain reading says {key} = "
                                        f"{reading.get(key)!r} and the answer's own numbers give {want!r}")
                if plain.get("headline") != reading.get("sentence"):
                    failures.append(f"{question_id}: the plain headline is not the reading's sentence")
                for key in ("n_state_months", "n_states"):
                    if key in reading and str(reading[key]) not in text:
                        failures.append(f"{question_id}: the plain reading quotes {key} = {reading[key]!r}, "
                                        "which the answer does not carry")
        for item in plain.get("terms") or []:
            term = str(item.get("term") or "")
            meaning = str(item.get("meaning") or "")
            if not term or not meaning:
                failures.append(f"{question_id}: a glossary entry is empty")
                continue
            if term.lower() not in text.lower():
                failures.append(f"{question_id}: the plain reading defines {term!r}, which the answer does "
                                "not use")
            if flat(meaning) not in glossary:
                failures.append(f"{question_id}: the plain meaning given for {term!r} is not in "
                                "docs/glossary.md — a definition the page does not carry is a definition "
                                "that can drift")

        # The needles: what the eval set says the answer must carry, and what it does carry.
        needles = row.get("needles") or {}
        required = list(needles.get("required") or [])
        if required:
            satisfied = [needle for needle in required if needle in text]
            missing = [needle for needle in required if needle not in text]
            if sorted(needles.get("satisfied") or []) != sorted(satisfied):
                failures.append(f"{question_id}: the artifact records {needles.get('satisfied')!r} as "
                                f"satisfied and this verifier finds {satisfied!r}")
            if sorted(needles.get("missing") or []) != sorted(missing):
                failures.append(f"{question_id}: the artifact records {needles.get('missing')!r} as "
                                f"missing and this verifier finds {missing!r}")
            if bool(needles.get("all_satisfied")) != (not missing):
                failures.append(f"{question_id}: the artifact records all_satisfied="
                                f"{needles.get('all_satisfied')!r} and the answer carries "
                                f"{len(satisfied)} of {len(required)} needles")

    # ---------------------------------------------------------------------------------------------
    # 2b. Every refusal code has a plain-English meaning, and every refusal carries one
    # ---------------------------------------------------------------------------------------------
    refusal_codes = contract.get("refusal_codes") or {}
    glossary_entries: dict[str, str] = {}
    for line in glossary_path.read_text(encoding="utf-8").splitlines():
        match = GLOSSARY_ROW.match(line.strip())
        if match:
            glossary_entries[match.group("term").strip()] = match.group("meaning").strip()
    for code, reason in refusal_codes.items():
        if code not in glossary_entries:
            failures.append(f"docs/glossary.md: the refusal code {code} has no plain-English meaning — "
                            f"the refusal would be unexplained ({reason})")
    for term in glossary_entries:
        if re.fullmatch(r"[A-Z]\d{2}", term) and term not in refusal_codes:
            failures.append(f"docs/glossary.md: {term} is explained as a refusal code, but the contract "
                            "does not declare it")
    for row in rows:
        if row.get("status") in ("refused", "declined"):
            code = row.get("refusal_code")
            if not code:
                failures.append(f"{row.get('id')}: a {row.get('status')} answer carries no code")
            elif code not in refusal_codes:
                failures.append(f"{row.get('id')}: the code {code!r} is not one the contract declares")
            elif code not in glossary_entries:
                failures.append(f"{row.get('id')}: the code {code!r} has no plain-English meaning in "
                                "docs/glossary.md")

    # ---------------------------------------------------------------------------------------------
    # 3. The counts, recomputed
    # ---------------------------------------------------------------------------------------------
    def summarise(rows_: list[dict]) -> dict:
        n = len(rows_)
        answered = [row for row in rows_ if row.get("status") == "answered"]
        refused = [row for row in rows_ if row.get("status") == "refused"]
        declined = [row for row in rows_ if row.get("status") == "declined"]
        shapes = contract.get("shapes") or {}

        def parts_of(row: dict) -> tuple[list[str], list[str]]:
            spec = shapes.get(row.get("shape") or "") or {}
            return list(spec.get("requires") or []), list(spec.get("forbids") or [])

        parts = {part: sum(1 for row in answered if (row.get("check") or {}).get(part))
                 for part in ("interval", "reason_code", "identifying_assumption",
                              "cannot_rule_out", "citation")}
        with_needles = [row for row in rows_ if (row.get("needles") or {}).get("required")]
        needles_total = sum(len(row["needles"]["required"]) for row in with_needles)
        needles_found = sum(len(row["needles"]["satisfied"]) for row in with_needles)
        satisfied_questions = sum(1 for row in with_needles if row["needles"]["all_satisfied"])
        return {
            "n": n,
            "answered": len(answered),
            "refused": len(refused),
            "declined": len(declined),
            "answer_rate": round(len(answered) / max(n, 1), 6),
            "answered_with_all_parts": sum(
                1 for row in answered
                if all((row.get("check") or {}).get(part) for part in parts_of(row)[0])
                and not any((row.get("check") or {}).get(part) for part in parts_of(row)[1])),
            "parts_present": parts,
            "shapes": {shape: sum(1 for row in answered if row.get("shape") == shape)
                       for shape in sorted(shapes)},
            "refusals_with_citation": sum(1 for row in refused if row.get("citation")),
            "declined_with_citation": sum(1 for row in declined if row.get("citation")),
            "refusals_with_a_code": sum(1 for row in refused if row.get("refusal_code")),
            "answers_quoting_numbers_absent_from_the_citation": sum(
                1 for row in answered if row.get("numbers_absent_from_citation")),
            "answered_with_plain_language": sum(
                1 for row in answered if (row.get("plain") or {}).get("text")),
            "answers_whose_plain_reading_quotes_uncited_numbers": sum(
                1 for row in answered if row.get("plain_numbers_absent_from_citation")),
            "questions_with_needles": len(with_needles),
            "questions_whose_needles_are_all_satisfied": satisfied_questions,
            "needle_satisfaction": (round(satisfied_questions / len(with_needles), 6)
                                    if with_needles else None),
            "needles_total": needles_total,
            "needles_satisfied": needles_found,
            "needle_recall": (round(needles_found / max(needles_total, 1), 6)
                              if needles_total else None),
        }

    sets = artifact.get("sets") or {}
    for name in ("published", "held_out", "all"):
        expected = summarise([row for row in rows if name == "all" or row.get("set") == name])
        declared = sets.get(name) or {}
        for key, value in expected.items():
            if declared.get(key) != value:
                failures.append(f"sets.{name}.{key}: the artifact says {declared.get(key)!r} and the rows "
                                f"give {value!r}")

    # ---------------------------------------------------------------------------------------------
    # 4. The module imports no model, database or network client
    # ---------------------------------------------------------------------------------------------
    source = LAYER_PATH.read_text(encoding="utf-8")
    for match in FORBIDDEN.finditer(source):
        failures.append(f"app/answer_layer.py imports {match.group(0).strip()!r} — the layer must not "
                        "call a model, a database or a network at request time")
    if "app.intent_gate" not in source:
        failures.append("app/answer_layer.py does not import the intent gate — the decision would not be "
                        "the declared one")

    # ---------------------------------------------------------------------------------------------
    # 4b. It runs with no LLM key, proven rather than asserted
    # ---------------------------------------------------------------------------------------------
    # The layer reads committed files and scores with BM25; nothing in the path wants a credential. This
    # runs it in a child process whose environment has every key-shaped variable removed, because a
    # README that says "no key required" is not a check.
    stripped = {name: value for name, value in os.environ.items()
                if not any(marker in name.upper() for marker in
                           ("API_KEY", "OPENAI", "ANTHROPIC", "GEMINI", "GOOGLE", "AZURE", "GROQ",
                            "TOGETHER", "HF_TOKEN", "HUGGINGFACE"))}
    keyless_script = (
        "import sys; sys.path.insert(0, '.')\n"
        "from app.answer_layer import load_layer\n"
        "layer = load_layer('.')\n"
        "answer = layer.answer('What did the published estimate find for fatalities under Design A?')\n"
        "assert answer.status in ('answered', 'declined'), answer.status\n"
        "assert (answer.plain or {}).get('text'), 'no plain-language reading'\n"
        "print(answer.status)\n"
    )
    try:
        run = subprocess.run([sys.executable, "-c", keyless_script], cwd=REPO_ROOT, env=stripped,
                             capture_output=True, text=True, timeout=180)
    except (OSError, subprocess.SubprocessError) as error:
        failures.append(f"the keyless run could not start: {error}")
    else:
        if run.returncode != 0:
            failures.append("the layer does not run without an LLM key: "
                            f"{(run.stderr or run.stdout).strip().splitlines()[-1] if (run.stderr or run.stdout).strip() else 'no output'}")
        elif run.stdout.strip() not in ("answered", "declined"):
            failures.append(f"the keyless run returned {run.stdout.strip()!r}")

    # ---------------------------------------------------------------------------------------------
    # 5. The narrative quotes the artifact — prose that is not derived is prose that drifts
    # ---------------------------------------------------------------------------------------------
    narrative = REPO_ROOT / "docs" / "answer.md"
    if not narrative.exists():
        failures.append("docs/answer.md: missing — the layer's measured rate would have no prose home")
    else:
        prose = narrative.read_text(encoding="utf-8")
        needles = []
        for name in ("published", "held_out", "all"):
            block = sets.get(name) or {}
            needles.extend([
                (f"{float(block.get('answer_rate') or 0):.3f}", f"the {name} answer rate"),
                (str(block.get("answered")), f"the {name} answered count"),
                (str(block.get("declined")), f"the {name} declined count"),
            ])
            if block.get("questions_with_needles"):
                needles.extend([
                    (f"{float(block.get('needle_satisfaction') or 0):.3f}",
                     f"the {name} needle satisfaction"),
                    (f"{float(block.get('needle_recall') or 0):.3f}", f"the {name} needle recall"),
                    (str(block.get("questions_whose_needles_are_all_satisfied")),
                     f"the {name} count of questions carrying every needle"),
                    (str(block.get("needles_satisfied")), f"the {name} count of needles present"),
                ])
        needles.append((str((sets.get("all") or {}).get("n")), "the measured question count"))
        for needle, label in needles:
            if needle not in prose:
                failures.append(f"docs/answer.md: does not quote {label} ({needle}) — the page has drifted "
                                "from the artifact it describes")

    # ---------------------------------------------------------------------------------------------
    print(f"layer         : {LAYER_PATH.relative_to(REPO_ROOT).as_posix()} — BM25 over "
          f"{len(corpus['chunks'])} chunks, refusing with the contract's template")
    for name in ("published", "held_out", "all"):
        block = sets.get(name) or {}
        print(f"  {name:<10}: {block.get('n')} question(s) — {block.get('answered')} answered, "
              f"{block.get('declined')} declined by R-04, {block.get('refused')} refused by the gate; "
              f"answer rate {float(block.get('answer_rate') or 0):.3f}")
    print(f"cross-check   : every row's intent is the intent artifact's; every refusal cites the gate's pinned "
          f"chunk")
    print(f"extractive    : every quoted sentence appears verbatim in a cited chunk; every number is in its "
          f"citation")
    print()
    if failures:
        print(f"FAILED — {len(failures)} problem(s):")
        for problem in failures[:40]:
            print(f"  - {problem}")
        if len(failures) > 40:
            print(f"  … and {len(failures) - 40} more")
        return 1
    print("PASS — the gate's decisions are honoured, every answer carries the contract's parts with sentences "
          "and numbers attributable to its citations, the counts recompute, and the layer imports no model")
    return 0


if __name__ == "__main__":
    sys.exit(main())
