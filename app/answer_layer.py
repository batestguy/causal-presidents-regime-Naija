"""The answer layer: gate → retrieve → assemble → post-check, with no model at request time.

The intent gate decides whether the corpus may answer a question and, if not, which chunk the refusal must
quote. This layer takes that decision and does the two things the gate deliberately does not: it retrieves
the passages that answer an answerable question, and it enforces the answer contract
(`analysis/specs/rag.yml#answer_contract`) on what it assembles.

Four rules are enforced here rather than trusted:

  * **A refusal quotes the gate's own citation.** The refusal template is the contract's, the reason is the
    rule's first sentence, and the citation is the pinned chunk's — so a refusal is an argument with a
    source, not a shrug.
  * **An answer is extractive.** Every sentence in it is a paragraph of a committed chunk. Nothing is
    paraphrased and no number is typed: the layer selects passages and labels them in the contract's order
    (question, estimate with interval, identifying assumption, what it cannot rule out, citation).
  * **The post-check can overrule the answer.** If the assembled text carries no interval, no identifying
    assumption or no "cannot rule out", the contract says the response is replaced by the refusal template
    (R-04). That happens here, and the result says which part was missing.
  * **No model is called.** Retrieval is Okapi BM25 over the corpus text — the same lexical scorer the
    retrieval evaluation measures as its baseline — so the layer imports no embedding library, no database
    client, no network client and no fitting library. The committed vectors are used offline by
    `scripts/eval_rag.py`, not here.

The module is framework-free on purpose: the same code answers a question in a test, in the app, and in a
harness.
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from app.intent_gate import load_gate

RAG_SPEC_PATH = Path("analysis/specs/rag.yml")
CORPUS_PATH = "registry/rag/{vintage}/corpus.json"
GLOSSARY_PATH = Path("docs/glossary.md")
GLOSSARY_ROW = re.compile(r"^\|\s*\*\*(?P<term>[^*]+)\*\*\s*\|\s*(?P<meaning>[^|]+?)\s*\|\s*$")
COEFFICIENT = re.compile(r"=\s*([−+\-]?\d[\d,]*\.?\d*)")
SAMPLE = re.compile(r"n\s*=\s*([\d,]+)\s+state-months over ([\d,]+) states")
SPAN = re.compile(r"(\d{4}-\d{2}) to (\d{4}-\d{2})")

# The tokenizer and stopword list are the retrieval evaluation's, copied rather than imported: `app/` must
# stand on its own, and `tests/verify_answer.py` proves the parity by reproducing the published BM25 ranking
# from this file's scorer.
STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "with", "by", "at", "from", "as", "is",
    "are", "was", "were", "be", "been", "being", "it", "its", "this", "that", "these", "those", "there",
    "which", "who", "whom", "whose", "what", "when", "where", "why", "how", "does", "do", "did", "done",
    "can", "could", "would", "should", "will", "shall", "may", "might", "must", "have", "has", "had",
    "not", "no", "but", "if", "then", "than", "so", "such", "into", "about", "over", "under", "between",
    "after", "before", "during", "any", "all", "each", "every", "more", "most", "some", "much", "many",
    "you", "your", "we", "our", "they", "their", "he", "she", "his", "her", "i", "me", "my", "us",
}

# An interval is a bracketed pair of numbers: [-0.1132, +1.0718], [0.1234, 0.6254], [−0.1132, 1.0718].
INTERVAL = re.compile(r"\[\s*[−+\-]?\d[\d,.]*\s*,\s*[−+\-]?\d[\d,.]*\s*\]")
ASSUMPTION = re.compile(r"\bassum\w*", re.IGNORECASE)
CANNOT_RULE_OUT = re.compile(r"cannot\s+rule\s+out", re.IGNORECASE)
PART_HEADER = re.compile(r"^\[.*?\bpart \d+ of \d+\]\s*$", re.MULTILINE)
# The contract is an *estimate* answer contract. A question that asks for one can be answered with the
# estimate, its assumption, its caveats and the passage it sits in; a question that asks for something else
# (a coverage fact, a date, a status) has no interval to carry, and R-04 replaces it with the template.
ESTIMATE_ASK = re.compile(
    r"\b(?:estimates?|estimated|estimation|coefficients?|elasticity|interval|identified|identify|results?|"
    r"find|finds|found|magnitude|pass[- ]?through|how much|standard error|point estimate|significant)\b",
    re.IGNORECASE,
)
# "Effect" and "impact" are estimate words only when the question also names the outcome they are about;
# on their own they are vague enough to pull a robustness paragraph about a different quantity.
EFFECT_ASK = re.compile(r"\b(?:effects?|impacts?)\b", re.IGNORECASE)


def tokenize(text: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9]+", text.lower()) if len(t) > 1 and t not in STOPWORDS]


class BM25:
    """Okapi BM25 over the corpus text, with the evaluation's parameters. No stemming, no synonyms."""

    def __init__(self, documents: dict[str, str], k1: float = 1.5, b: float = 0.75) -> None:
        self.k1, self.b = k1, b
        self.ids = list(documents)
        self.tokens = {cid: tokenize(text) for cid, text in documents.items()}
        self.lengths = {cid: len(toks) or 1 for cid, toks in self.tokens.items()}
        self.avgdl = sum(self.lengths.values()) / max(len(self.lengths), 1)
        df: dict[str, int] = {}
        for toks in self.tokens.values():
            for term in set(toks):
                df[term] = df.get(term, 0) + 1
        n = len(self.ids)
        self.idf = {term: math.log(1 + (n - count + 0.5) / (count + 0.5)) for term, count in df.items()}
        self.tf = {cid: self._counts(toks) for cid, toks in self.tokens.items()}

    @staticmethod
    def _counts(tokens: list[str]) -> dict[str, int]:
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
            length = self.lengths[cid]
            for term in terms:
                frequency = counts.get(term, 0)
                if not frequency:
                    continue
                denominator = frequency + self.k1 * (1 - self.b + self.b * length / self.avgdl)
                score += self.idf.get(term, 0.0) * frequency * (self.k1 + 1) / denominator
            out[cid] = score
        return out

    def rank(self, query: str, k: int) -> list[tuple[str, float]]:
        return sorted(self.scores(query).items(), key=lambda item: (-item[1], item[0]))[:k]


@dataclass(frozen=True)
class Answer:
    """What the layer returned, and why."""

    status: str                 # answered | refused | declined
    question: str
    text: str
    intent: str
    rule_id: str | None
    route: str | None
    citation: str | None
    chunks_used: list[str] = field(default_factory=list)
    check: dict = field(default_factory=dict)
    plain: dict = field(default_factory=dict)

    @property
    def answered(self) -> bool:
        return self.status == "answered"

    def as_dict(self) -> dict:
        return {
            "status": self.status,
            "question": self.question,
            "text": self.text,
            "intent": self.intent,
            "rule_id": self.rule_id,
            "route": self.route,
            "citation": self.citation,
            "chunks_used": self.chunks_used,
            "check": self.check,
            "plain": self.plain,
        }


class AnswerLayer:
    """The gate, the corpus and the contract, applied to a question."""

    def __init__(self, gate, corpus: dict, contract: dict, k: int = 5,
                 glossary: dict[str, str] | None = None):
        self.gate = gate
        self.corpus = corpus
        self.contract = contract
        self.k = k
        self.glossary = dict(glossary or {})
        self.template = str(contract.get("refusal_template") or
                            "I don't have a model for that. {reason} — see {citation}.")
        self.chunks = {chunk["chunk_id"]: chunk for chunk in corpus.get("chunks") or []}
        self.bm25 = BM25({cid: str(chunk.get("text") or "") for cid, chunk in self.chunks.items()})
        # Outcome labels, from the cards' own metadata: a question that names an outcome may only be
        # answered from a passage about that outcome. Without this, a design-level result that lists
        # three other outcomes answers a fourth one with their numbers — the lending failure the app's
        # results tab exists to prevent, one layer down.
        self.outcomes: dict[str, str] = {}
        for chunk in self.chunks.values():
            metadata = chunk.get("metadata") or {}
            if metadata.get("outcome_id") and metadata.get("outcome_label"):
                self.outcomes[str(metadata["outcome_id"])] = str(metadata["outcome_label"])

    # -- what a question gets -------------------------------------------------------------------
    def answer(self, question: str) -> Answer:
        decision = self.gate.decide(question)
        if decision.intent != "answerable":
            citation, quote = self._pin(decision.route)
            return Answer(
                status="refused",
                question=question,
                text=self._refusal(self._template_reason(decision.reason), citation),
                intent=decision.intent,
                rule_id=decision.rule_id,
                route=decision.route,
                citation=citation,
                chunks_used=[decision.route] if decision.route else [],
                check={"cited": bool(citation), "quote": quote},
                plain={"headline": self._refusal(self._template_reason(decision.reason), citation),
                       "reading": None, "terms": [],
                       "text": self._refusal(self._template_reason(decision.reason), citation)},
            )

        named_outcomes = self._named_outcomes(question)
        asks_for_an_estimate = bool(ESTIMATE_ASK.search(question)) or bool(
            EFFECT_ASK.search(question) and named_outcomes)
        if not asks_for_an_estimate:
            # R-04 answers carry an estimate; a question that asks for a coverage fact or a status has
            # nothing to carry and is refused rather than dressed in an unrelated coefficient.
            top = self.bm25.rank(question, 1)
            citation, quote = self._pin(top[0][0] if top else None)
            text = self._refusal(
                "the answer contract is an estimate contract: an answer must carry an interval, an "
                "identifying assumption and what it cannot rule out, and this question asks for none "
                "of the three",
                citation,
            )
            return Answer(
                status="declined",
                question=question,
                text=text,
                plain={"headline": text, "reading": None, "terms": [], "text": text},
                intent=decision.intent,
                rule_id=decision.rule_id,
                route=None,
                citation=citation,
                chunks_used=[cid for cid, _score in self.bm25.rank(question, self.k)],
                check={"retrieved": min(self.k, len(self.chunks)), "quote": quote},
            )

        # A card contributes up to eight part-chunks, so a top-5 *chunk* window can contain one parent.
        # The layer therefore scans deeper and tries the top k distinct parent documents: the retrieval
        # metric stays k = 5 chunks (docs/rag.md), and assembly gets a real choice of documents.
        retrieved = self.bm25.rank(question, self.k * 8)
        tried = 0
        for parent, parts in self._parents_in_order(retrieved):
            if tried >= self.k:
                break
            tried += 1
            if named_outcomes and not self._covers(parent, named_outcomes):
                continue
            assembled = self._assemble(question, parent, parts)
            if not self._estimate_is_about(assembled.get("estimate"), named_outcomes):
                continue
            named_designs = self._named_designs(question)
            design_id = (self.chunks.get(parent, {}).get("metadata") or {}).get("design_id")
            if named_designs and design_id and str(design_id) not in named_designs:
                # A question about Design B's grid answered from a Design A card would lend one
                # design's result to another — the failure the design ids exist to make visible.
                continue
            borrowed: list[str] = []
            for slot, pattern in (("assumption", ASSUMPTION), ("cannot", CANNOT_RULE_OUT)):
                if assembled[slot]:
                    continue
                hit = self._borrow(pattern, retrieved, parent, question)
                if hit:
                    assembled[slot] = hit["block"]
                    borrowed.append(hit["chunk_id"])
            check = {
                "interval": bool(assembled["estimate"] and INTERVAL.search(assembled["estimate"])),
                "assumption": bool(assembled["assumption"] and ASSUMPTION.search(assembled["assumption"])),
                "cannot_rule_out": bool(assembled["cannot"] and CANNOT_RULE_OUT.search(assembled["cannot"])),
                "citation": bool(assembled["citation"]),
            }
            if all(check.values()):
                citations = [assembled["citation"]]
                citations += [str(self.chunks[cid].get("citation") or cid) for cid in borrowed]
                rendered = self._render(question, parent, assembled, citations)
                return Answer(
                    status="answered",
                    question=question,
                    text=rendered,
                    intent=decision.intent,
                    rule_id=decision.rule_id,
                    route=None,
                    citation="; ".join(dict.fromkeys(citations)),
                    chunks_used=parts + borrowed,
                    check=check,
                    plain=self._plain(assembled, parent, citations),
                )

        # R-04: an answer that cannot carry all three parts is replaced by the refusal template.
        top = retrieved[0][0] if retrieved else None
        citation, quote = self._pin(top)
        text = self._refusal(
            "the retrieved passages carry no interval, no identifying assumption and no "
            "cannot-rule-out together, so no answer meets the contract",
            citation,
        )
        return Answer(
            status="declined",
            question=question,
            text=text,
            plain={"headline": text, "reading": None, "terms": [], "text": text},
            intent=decision.intent,
            rule_id=decision.rule_id,
            route=top,
            citation=citation,
            chunks_used=[cid for cid, _ in retrieved],
            check={"retrieved": len(retrieved), "quote": quote},
        )

    # -- assembly -------------------------------------------------------------------------------
    @staticmethod
    def post_check(text: str) -> dict:
        """R-04: an interval, an identifying assumption and what it cannot rule out."""
        return {
            "interval": bool(INTERVAL.search(text)),
            "assumption": bool(ASSUMPTION.search(text)),
            "cannot_rule_out": bool(CANNOT_RULE_OUT.search(text)),
        }

    def _named_outcomes(self, question: str) -> set[str]:
        """The outcome ids whose label the question names, by a majority of the label's own terms."""
        terms = set(tokenize(question))
        matched: set[str] = set()
        for outcome_id, label in self.outcomes.items():
            label_terms = set(tokenize(label))
            if not label_terms:
                continue
            overlap = terms & label_terms
            # The label's longest word is its distinctive one — "fatalities" inside "Reported security
            # fatalities", "inflation" inside "Headline inflation (y/y)". Matching that word is enough;
            # a single generic word ("rate", "reported") is not, because most labels carry one.
            longest = max(label_terms, key=len)
            if longest in overlap or (len(overlap) >= 2 and len(overlap) / len(label_terms) >= 0.5):
                matched.add(outcome_id)
        return matched

    def _named_designs(self, question: str) -> set[str]:
        """The design ids a question names outright — "Design B", "design a"."""
        return {match.upper() for match in re.findall(r"\bdesign\s*([abc])\b", question.lower())}

    def _estimate_is_about(self, block: str | None, named: set[str]) -> bool:
        """Whether an estimate paragraph names one of the outcomes the question names.

        A design-level result lists several outcomes' coefficients; taking the first interval in it
        answers a fatalities question with an incidents number. The parent-level guard cannot see
        inside the paragraph, so the paragraph is checked too.
        """
        if not block or not named:
            return True
        text = block.lower()
        keys = {max(tokenize(self.outcomes[outcome_id]), key=len, default="")
                for outcome_id in named}
        return any(key and key in text for key in keys)

    def _covers(self, parent: str, named: set[str]) -> bool:
        """Whether a parent is about one of the outcomes the question names."""
        metadata = self.chunks.get(parent, {}).get("metadata") or {}
        if metadata.get("outcome_id"):
            return str(metadata["outcome_id"]) in named
        text = " ".join(str(self.chunks.get(cid, {}).get("text") or "")
                         for cid in self.gate.parts_of(parent)).lower()
        return any(self.outcomes[outcome_id].lower() in text for outcome_id in named)

    def _parents_in_order(self, retrieved: list[tuple[str, float]]) -> list[tuple[str, list[str]]]:
        seen: list[str] = []
        for chunk_id, _score in retrieved:
            parent = chunk_id.split("#p", 1)[0]
            if parent not in seen:
                seen.append(parent)
        return [(parent, self.gate.parts_of(parent)) for parent in seen]

    def _assemble(self, question: str, parent: str, parts: list[str]) -> dict:
        paragraphs: list[str] = []
        for chunk_id in parts:
            body = PART_HEADER.sub("", str(self.chunks.get(chunk_id, {}).get("text") or "")).strip()
            for block in re.split(r"\n\s*\n", body):
                block = block.strip()
                if block and not block.startswith(("[", "Model card ", "Published result ")):
                    paragraphs.append(block)

        estimate = next((block for block in paragraphs
                         if INTERVAL.search(block) and "interval" in block.lower()), None)
        estimate = estimate or next((block for block in paragraphs if INTERVAL.search(block)), None)
        assumption = next((block for block in paragraphs
                           if block != estimate and "identifying assumption" in block.lower()), None)
        assumption = assumption or next(
            (block for block in paragraphs if block != estimate and ASSUMPTION.search(block)), None)
        cannot = next((block for block in paragraphs
                       if block != estimate and CANNOT_RULE_OUT.search(block)), None)

        # The passage the question is about is quoted alongside the estimate, so the answer is not only
        # the number: "which failed check" must carry the check, not just the coefficient it decided.
        terms = set(tokenize(question))
        overlap = {block: len(terms & set(tokenize(block))) for block in paragraphs}
        focus = max(paragraphs, key=lambda block: (overlap[block], len(block)), default=None)
        if focus in (estimate, assumption, cannot):
            focus = None

        citation = str(self.chunks.get(parent, {}).get("citation") or parent)
        return {"citation": citation, "estimate": estimate, "assumption": assumption,
                "cannot": cannot, "focus": focus}

    @staticmethod
    def _render(question: str, parent: str, parts: dict, citations: list[str]) -> str:
        lines = [
            f"**Question:** {question}",
            f"**Estimate:** {parts['estimate']}",
            f"**Identifying assumption:** {parts['assumption']}",
            f"**What it cannot rule out:** {parts['cannot']}",
        ]
        if parts.get("focus"):
            lines.append(f"**The passage that answers this:** {parts['focus']}")
        lines.append(f"**Citation:** {'; '.join(dict.fromkeys(citations))} — {parent}")
        return "\n\n".join(lines)

    def _borrow(self, pattern: re.Pattern, retrieved: list[tuple[str, float]],
                parent: str, question: str) -> dict | None:
        """A paragraph another retrieved chunk carries, if it shares a term with the question.

        R-04 asks a single answer to carry the estimate, its assumption and what it cannot rule out.
        The corpus keeps those in different places — a result chunk may carry the interval while the
        limitations carry the caveats — so the layer quotes each from the chunk that has it and cites
        them all. It does not invent a part: every borrowed paragraph is a committed paragraph.
        """
        terms = set(tokenize(question))
        for chunk_id, _score in retrieved:
            parent_id = chunk_id.split("#p", 1)[0]
            if parent_id == parent:
                continue
            if parent_id.startswith("scope:"):
                # The scope statement is the corpus's own limits, not evidence about a design; it
                # contains the words "identifying assumption" only because the contract's post-check
                # is described there. Borrowing from it dressed a refusal in an answer's clothes.
                continue
            body = PART_HEADER.sub("", str(self.chunks.get(chunk_id, {}).get("text") or ""))
            for block in re.split(r"\n\s*\n", body.strip()):
                block = block.strip()
                if block and pattern.search(block) and terms & set(tokenize(block)):
                    return {"chunk_id": chunk_id, "block": block}
        return None

    # -- the plain-language view ----------------------------------------------------------------
    def _plain(self, assembled: dict, parent: str, citations: list[str]) -> dict:
        """The same answer for a reader who does not work with statistics.

        It restates nothing that the quoted passages do not say: the signs, the interval's bounds, the
        sample size and the months are copied out of the estimate paragraph, and the definitions are
        the glossary's own lines. The contract answer remains `text`; this is a second reading of it.
        """
        estimate_full = " ".join(str(assembled.get("estimate") or "").split())
        estimate = self._sentence_with(estimate_full, "interval") or estimate_full
        reading = self._reading(estimate)
        headline = (reading or {}).get("sentence") or (
            "The corpus answers this from the passage below; it carries no single coefficient to read."
        )
        assumption_full = " ".join(str(assembled.get("assumption") or "").split())
        assumption = (self._sentence_with(assumption_full, "identifying assumption")
                      or assumption_full)
        cannot_full = str(assembled.get("cannot") or "")
        bullets = [line.strip() for line in cannot_full.splitlines()
                   if line.strip().startswith(("-", "*"))]
        cannot = "\n".join(bullets) if bullets else " ".join(cannot_full.split())
        quoted = " ".join(str(assembled.get(slot) or "") for slot in
                          ("estimate", "assumption", "cannot", "focus"))
        terms = [{"term": term, "meaning": meaning}
                 for term, meaning in self.glossary.items()
                 if re.search(rf"\b{re.escape(term.lower())}\b", quoted.lower())]
        lines = [
            f"**Short answer:** {headline}",
            "",
            f"**The number:** {estimate}",
            "",
            f"**What it assumes:** {assumption}",
            "",
            f"**What it cannot tell you:** {cannot}",
            "",
            f"**Where this comes from:** {'; '.join(dict.fromkeys(citations))} — {parent}",
        ]
        if terms:
            lines += ["", "**What the words mean:**", ""]
            lines += [f"- **{item['term']}** — {item['meaning']}" for item in terms]
        return {"headline": headline, "reading": reading, "terms": terms,
                "text": "\n".join(lines)}

    @staticmethod
    def _sentence_with(text: str, needle: str) -> str | None:
        """The one sentence of a quoted block that says the thing a plain reader needs."""
        for sentence in re.split(r"(?<=[.!?])\s+", text):
            if needle in sentence.lower():
                return sentence.strip()
        return None

    @staticmethod
    def _reading(estimate: str) -> dict | None:
        """The estimate's own numbers, read out loud. Nothing here is new arithmetic."""
        interval = INTERVAL.search(estimate)
        coefficient = COEFFICIENT.search(estimate)
        if not interval or not coefficient:
            return None
        low_text, high_text = [part.strip() for part in interval.group(0).strip("[]").split(",")]

        def number(text: str) -> float:
            return float(text.replace("−", "-").replace(",", ""))

        try:
            low, high, value = number(low_text), number(high_text), number(coefficient.group(1))
        except ValueError:
            return None
        includes_zero = low <= 0 <= high
        direction = "negative" if value < 0 else ("positive" if value > 0 else "zero")
        sentence = f"The published estimate is {direction} ({coefficient.group(1)}). "
        sentence += f"The range the data cannot rule out runs from {low_text} to {high_text}"
        if includes_zero:
            sentence += ", and it includes zero, so this answer does not establish a direction."
        else:
            sentence += (", and it does not include zero, so the data are consistent with a "
                        "relationship — the assumption below is what makes it credible.")
        reading: dict = {"coefficient": coefficient.group(1), "interval_low": low_text,
                         "interval_high": high_text, "includes_zero": includes_zero,
                         "direction": direction}
        sample = SAMPLE.search(estimate)
        if sample:
            reading["n_state_months"] = sample.group(1)
            reading["n_states"] = sample.group(2)
            sentence += f" It rests on {sample.group(1)} state-months across {sample.group(2)} states"
            span = SPAN.search(estimate)
            if span:
                reading["first_month"] = span.group(1)
                reading["last_month"] = span.group(2)
                sentence += f", {span.group(1)} to {span.group(2)}"
            sentence += "."
        reading["sentence"] = sentence
        return reading

    # -- citations and refusals -----------------------------------------------------------------
    def _pin(self, chunk_id: str | None) -> tuple[str | None, str]:
        if not chunk_id or chunk_id not in self.chunks:
            return None, ""
        chunk = self.chunks[chunk_id]
        quote = " ".join(str(chunk.get("text") or "").split())[:280]
        return str(chunk.get("citation") or chunk_id), quote

    @staticmethod
    def _template_reason(reason: str) -> str:
        """The rule's first sentence, ready to follow the template's full stop.

        It is capitalised rather than lowercased: the template ends a sentence before the reason, and a
        refusal that starts mid-sentence reads as a copied fragment rather than an argument.
        """
        flat = " ".join(str(reason).split())
        return flat[:1].upper() + flat[1:] if flat else "No rule matched"

    def _refusal(self, reason: str, citation: str | None) -> str:
        return self.template.format(reason=reason, citation=citation or "no citable chunk")


def load_layer(root: Path | str | None = None) -> AnswerLayer:
    """The layer over the published vintage: the gate, its corpus and the answer contract."""
    base = Path(root) if root is not None else Path(__file__).resolve().parents[1]
    gate = load_gate(base)
    index = json.loads((base / "registry/dags/index.json").read_text(encoding="utf-8"))
    corpus = json.loads((base / CORPUS_PATH.format(vintage=index["vintage_date"])).read_text(encoding="utf-8"))
    rag_spec = yaml.safe_load((base / RAG_SPEC_PATH).read_text(encoding="utf-8"))
    contract = rag_spec.get("answer_contract") or {}
    k = int((rag_spec.get("retrieval") or {}).get("k") or 5)
    return AnswerLayer(gate=gate, corpus=corpus, contract=contract, k=k,
                       glossary=load_glossary(base))


def load_glossary(root: Path | str | None = None) -> dict[str, str]:
    """The plain-language meanings, straight from `docs/glossary.md` — never paraphrased in code."""
    base = Path(root) if root is not None else Path(__file__).resolve().parents[1]
    path = base / GLOSSARY_PATH
    if not path.exists():
        return {}
    entries: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        match = GLOSSARY_ROW.match(line.strip())
        if match:
            entries[match.group("term").strip()] = match.group("meaning").strip()
    return entries
