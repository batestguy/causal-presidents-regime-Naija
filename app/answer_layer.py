"""The answer layer: gate → route → assemble → post-check, with no model at request time.

The intent gate decides whether the corpus may answer a question and, if not, which chunk the refusal must
quote. This layer takes that decision and does the two things the gate deliberately does not: it finds the
passage that answers an answerable question, and it enforces the answer contract
(`analysis/specs/rag.yml#answer_contract`) on what it assembles.

Five rules are enforced here rather than trusted:

  * **A refusal quotes the gate's own citation.** The refusal template is the contract's, the reason is the
    rule's first sentence, and the citation is the pinned chunk's — so a refusal is an argument with a
    source, not a shrug. The plain reading of a refusal is the glossary's line for its code.
  * **An answer is extractive.** Every sentence in it is a paragraph of a committed chunk. Nothing is
    paraphrased and no number is typed: the layer selects passages and labels them in the contract's order.
  * **The shape follows what the corpus actually has.** The contract has three shapes — an estimate, a
    reason, and a fact — because 34 of the 36 cards carry a reason rather than a number, and refusing to
    answer those was refusing for the wrong reason. A question that asks for a number is answered with the
    card that carries one, or with the card's reason when it carries none; a question that asks for
    something else is answered with the passage that says it.
  * **The post-check can overrule the answer.** If the assembled text does not carry the parts its shape
    requires, the contract says the response is replaced by the refusal template (R-04). That happens here,
    and the result says which part was missing.
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

# An interval is a bracketed pair of numbers: [-0.1132, +1.0718], [0.1234, 0.6254], [−0.1132, 1.0718].
INTERVAL = re.compile(r"\[\s*[−+\-]?\d[\d,.]*\s*,\s*[−+\-]?\d[\d,.]*\s*\]")
ASSUMPTION = re.compile(r"\bassum\w*", re.IGNORECASE)
CANNOT_RULE_OUT = re.compile(r"cannot\s+rule\s+out", re.IGNORECASE)
PART_HEADER = re.compile(r"^\[.*?\bpart \d+ of \d+\]\s*$", re.MULTILINE)
YEAR = re.compile(r"\b((?:19|20)\d{2})\b")
DATE_RANGE = re.compile(r"(\d{4}-\d{2}-\d{2})\s+to\s+(\d{4}-\d{2}-\d{2})")

# The block markers the `card_estimate` family writes, and the looser ones a prose chunk carries. The
# estimate family is self-describing: a card serialised as one piece says which block is the assumption,
# which is the caveat, which is the specification and which is the reason. A design-level result is prose,
# so it is matched on the same words.
BLOCK_ASSUMPTION = re.compile(r"^Identifying assumption:", re.MULTILINE)
BLOCK_CANNOT = re.compile(r"^What this design cannot rule out:", re.MULTILINE)
BLOCK_SPECIFICATION = re.compile(r"^The published specification is", re.MULTILINE)
BLOCK_REASON = re.compile(r"^No estimate for this", re.MULTILINE)
BLOCK_VERDICT = re.compile(r"^Verdict:", re.MULTILINE)
BLOCK_CHECK = re.compile(r"^The check that decided:", re.MULTILINE)
# The looser markers, for a chunk that is prose rather than a serialised card.
LOOSE_REASON = re.compile(r"\bReason code:|Status:\s*not_run|not estimated here|infeasible", re.IGNORECASE)
LOOSE_CHECK = re.compile(r"\bFailed checks:|Verdict rule:|placebo|lead-shift", re.IGNORECASE)

# The tokens the retrieval scorer drops. The layer copies the retrieval evaluation's list rather than
# importing it: `app/` must stand on its own, and `tests/verify_answer.py` proves the parity by
# reproducing the published BM25 ranking from this file's scorer.
STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "with", "by", "at", "from", "as", "is",
    "are", "was", "were", "be", "been", "being", "it", "its", "this", "that", "these", "those", "there",
    "which", "who", "whom", "whose", "what", "when", "where", "why", "how", "does", "do", "did", "done",
    "can", "could", "would", "should", "will", "shall", "may", "might", "must", "have", "has", "had",
    "not", "no", "but", "if", "then", "than", "so", "such", "into", "about", "over", "under", "between",
    "after", "before", "during", "any", "all", "each", "every", "more", "most", "some", "much", "many",
    "you", "your", "we", "our", "they", "their", "he", "she", "his", "her", "i", "me", "my", "us",
}

# The question words that ask for a published number. "result" is one of them because a question about a
# design's result is a question about its published estimate; "find" is not, because "what did the
# robustness grid find" asks for a finding, not for a coefficient.
ESTIMATE_ASK = re.compile(
    r"\b(?:estimates?|estimated|estimation|coefficients?|elasticity|interval|identified|identify|"
    r"results?|magnitude|pass[- ]?through|how much|standard error|point estimate|significant)\b",
    re.IGNORECASE,
)
# "Effect" and "impact" are estimate words only when the question also names the outcome they are about;
# on their own they are vague enough to pull a robustness paragraph about a different quantity.
EFFECT_ASK = re.compile(r"\b(?:effects?|impacts?)\b", re.IGNORECASE)

# Words that are too ordinary to identify an outcome on their own. A label term that no other label uses
# is distinctive — unless it is one of these, in which case a question carrying it names no outcome.
GENERIC_TERMS = {
    "under", "over", "rate", "net", "real", "level", "index", "value", "share", "series", "year", "month",
    "state", "national", "primary", "change", "current", "total", "other",
}

# A question's term and a passage's token are the same term when they share a four-character prefix: the
# corpus matches "flag" to "flagged" and "fatality" to "fatalities" without a stemmer, and nothing shorter
# is allowed to match.
PREFIX = 4


def tokenize(text: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9]+", text.lower()) if len(t) > 1 and t not in STOPWORDS]


def same_term(left: str, right: str) -> bool:
    """Whether two tokens are the same term for matching purposes."""
    if len(left) < PREFIX or len(right) < PREFIX:
        return left == right
    return left[:PREFIX] == right[:PREFIX]


def matched_terms(terms: list[str], passage_terms: set[str]) -> set[str]:
    """The question's terms the passage carries."""
    return {term for term in terms if any(same_term(term, other) for other in passage_terms)}


def normalise_term(token: str) -> str:
    """The form two spellings of one word share: a plural folded to its singular.

    Only the plural endings are folded, and nothing else. A prefix rule would fold "cover" into
    "coverage", and a question about a shock band would then name the immunisation outcome, whose
    label says "coverage" — a wrong name restricts what may be quoted, which is worse than no name.
    """
    if token.endswith("ies") and len(token) > 4:
        return token[:-3] + "y"
    if token.endswith("ses") and len(token) > 4:
        return token[:-2]
    if token.endswith("s") and not token.endswith("ss") and len(token) > 3:
        return token[:-1]
    return token


def label_words(label: str) -> list[str]:
    """A label as a phrase: every word, in order, plurals folded."""
    return [normalise_term(word) for word in re.findall(r"[a-z0-9]+", label.lower())]


def question_words(text: str) -> list[str]:
    """A question as a phrase: every word, in order, plurals folded."""
    return [normalise_term(word) for word in re.findall(r"[a-z0-9]+", text.lower())]


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
    shape: str | None = None
    refusal_code: str | None = None

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
            "shape": self.shape,
            "refusal_code": self.refusal_code,
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
        self.shapes = dict(contract.get("shapes") or {})
        self.fact_overlap_min = float(contract.get("fact_overlap_min") or 0.0)
        self.fact_max_passages = int(contract.get("fact_max_passages") or 1)
        self.refusal_codes = dict(contract.get("refusal_codes") or {})
        self.chunks = {chunk["chunk_id"]: chunk for chunk in corpus.get("chunks") or []}
        self.bm25 = BM25({cid: str(chunk.get("text") or "") for cid, chunk in self.chunks.items()})
        # Outcome labels, from the cards' own metadata: a question that names an outcome may only be
        # answered from a passage about that outcome. Without this, a design-level result that lists
        # three other outcomes answers a fourth one with their numbers — the lending failure the app's
        # results tab exists to prevent, one layer down.
        self.outcomes: dict[str, str] = {}
        # The `card_estimate` family: one chunk per (outcome, design), carrying that card's own fields.
        self.cards: dict[tuple[str, str], str] = {}
        self.designs: dict[str, str] = {}
        for chunk in self.chunks.values():
            metadata = chunk.get("metadata") or {}
            outcome_id = metadata.get("outcome_id")
            design_id = metadata.get("design_id")
            if outcome_id and metadata.get("outcome_label"):
                self.outcomes.setdefault(str(outcome_id), str(metadata["outcome_label"]))
            if outcome_id and design_id:
                key = (str(outcome_id), str(design_id))
                if metadata.get("design_name"):
                    self.designs.setdefault(str(design_id), str(metadata["design_name"]))
                # Two families carry the same card: `card_estimate` is the card in one piece, and
                # `model_card` is the same card split into parts. The layer assembles from the one
                # that keeps the assumption, the caveats and the number in the same chunk — the
                # split family put the number in one part and the assumption in another, and an
                # answer assembled from a single part was missing half of what the contract requires.
                if chunk.get("doc_type") == "card_estimate" or key not in self.cards:
                    self.cards[key] = chunk["chunk_id"]
        # A term that is rare in the corpus is stronger evidence than one every chunk uses. The
        # weight is the retrieval scorer's own idf, so the layer and the retrieval measurement
        # agree on what makes a term distinctive.
        self.default_idf = math.log(1 + (len(self.bm25.ids) + 0.5) / 0.5)

    # -- what a question gets -------------------------------------------------------------------
    def answer(self, question: str) -> Answer:
        decision = self.gate.decide(question)
        if decision.intent != "answerable":
            return self._refused(question, decision)

        if self._asks_for_a_number(question):
            answer = self._number_answer(question, decision)
            if answer is not None:
                return answer
            return self._declined(question, decision, "L01")

        answer = self._fact_answer(question, decision)
        if answer is not None:
            return answer
        return self._declined(question, decision, "L02")

    # -- the refusal ----------------------------------------------------------------------------
    def _refused(self, question: str, decision) -> Answer:
        """The gate said no, and the passage that says why is quoted rather than cited."""
        citation, quote = self._pin(decision.route)
        reason = self._template_reason(decision.reason)
        text = self._refusal(reason, citation)
        if quote:
            text = f"{text}\n\n**What the record says:** {quote}"
        code = decision.rule_id
        return Answer(
            status="refused",
            question=question,
            text=text,
            intent=decision.intent,
            rule_id=decision.rule_id,
            route=decision.route,
            citation=citation,
            chunks_used=[decision.route] if decision.route else [],
            check={"cited": bool(citation), "quote": bool(quote)},
            plain=self._plain_refusal(reason, citation, quote, code),
            shape="refusal",
            refusal_code=code,
        )

    def _declined(self, question: str, decision, code: str) -> Answer:
        """The layer could not assemble an answer that meets the contract, and says which code that is."""
        reason = self.refusal_codes.get(code) or "the corpus does not carry an answer in any shape"
        citation, quote = self._pin(None)
        text = self._refusal(self._template_reason(reason), citation)
        return Answer(
            status="declined",
            question=question,
            text=text,
            intent=decision.intent,
            rule_id=code,
            route=None,
            citation=citation,
            chunks_used=[],
            check={"cited": bool(citation)},
            plain=self._plain_refusal(self._template_reason(reason), citation, "", code),
            shape="decline",
            refusal_code=code,
        )

    # -- the number path ------------------------------------------------------------------------
    def _asks_for_a_number(self, question: str) -> bool:
        """Whether the question asks for a published number, and the corpus can be asked for one.

        A question that names an outcome or a design is asking about that card or that result. A question
        that names neither is asking about the corpus, and it is a number question only when the best
        passage the retrieval finds is itself a published estimate: "how much of the monthly data series is
        observed" is a coverage question, and "how much of an oil shock reaches the states" is not.
        """
        if EFFECT_ASK.search(question) and self._named_outcomes(question):
            return True
        if not ESTIMATE_ASK.search(question):
            return False
        if self._named_outcomes(question) or self._named_designs(question):
            return True
        for chunk_id, _score in self.bm25.rank(question, 1):
            return self._carries_interval(chunk_id)
        return False

    def _number_answer(self, question: str, decision) -> Answer | None:
        outcomes = self._named_outcomes(question)
        designs = self._named_designs(question)
        for source in self._number_sources(question, outcomes, designs):
            assembled = self._assemble(question, source, outcomes, designs)
            if assembled is None:
                continue
            if all(assembled["check"].get(part) for part in assembled["required"]):
                return self._answered(question, decision, source, assembled)
        return None

    def _number_sources(self, question: str, outcomes: set[str], designs: set[str]) -> list[str]:
        """The chunks that could answer a question about a published number, in the order to try them."""
        sources: list[str] = []
        if outcomes:
            for outcome_id in sorted(outcomes):
                for design_id in sorted(self.designs):
                    if designs and design_id not in designs:
                        continue
                    chunk_id = self.cards.get((outcome_id, design_id))
                    if chunk_id:
                        sources.append(chunk_id)
            if not sources:
                # The question named a design this outcome has no card for: the design-level result is
                # the only thing the corpus can say about it.
                for design_id in sorted(designs):
                    chunk_id = f"result:{design_id}"
                    if chunk_id in self.chunks:
                        sources.append(chunk_id)
            # A published estimate first. The question asked for a number, and the card that carries one
            # is the card that answers it; the cards that carry a reason come after it.
            sources.sort(key=lambda cid: (0 if self._carries_interval(cid) else 1, cid))
        elif designs:
            for design_id in sorted(designs):
                chunk_id = f"result:{design_id}"
                if chunk_id in self.chunks:
                    sources.append(chunk_id)
        if not sources:
            # No outcome, no design: the corpus's own best answer to a question about a number is the
            # published estimate the retrieval finds first.
            for chunk_id, _score in self.bm25.rank(question, self.k * 8):
                parent = chunk_id.split("#p", 1)[0]
                if parent in sources:
                    continue
                if self._carries_interval(parent):
                    sources.append(parent)
                if len(sources) >= 3:
                    break
        return sources

    def _assemble(self, question: str, source: str, outcomes: set[str], designs: set[str]) -> dict | None:
        """Fill the contract's slots from one source, and check them against its shape."""
        blocks = self._blocks(source)
        if not blocks:
            return None
        terms = tokenize(question)
        design_id = self._design_of(source)

        estimate = self._pick(blocks, terms, INTERVAL, exclude=())
        reason = self._pick(blocks, terms, re.compile(REASON_PATTERN, re.IGNORECASE), exclude=())
        check_block = self._pick(blocks, terms, re.compile(CHECK_PATTERN, re.IGNORECASE), exclude=())
        assumption = self._pick(blocks, terms, ASSUMPTION, exclude=())
        cannot = self._pick(blocks, terms, CANNOT_RULE_OUT, exclude=())
        focus = self._pick(blocks, terms, re.compile(r"(?!)"), exclude=(estimate, reason, check_block,
                                                                     assumption, cannot))

        borrowed: list[str] = []
        citations = [str(self.chunks.get(source, {}).get("citation") or source)]
        if design_id and design_id in self.designs and (assumption is None or cannot is None):
            # A design-level result carries no assumption of its own: the design's assumption lives on
            # its cards, and it is the same on every one of them. The borrow is not conditional on the
            # question having named the design — a question that named it is exactly the question the
            # result answers, and it still needs the assumption the result does not carry.
            donor = self._design_donor(design_id)
            if donor and donor != source:
                donor_blocks = self._blocks(donor)
                assumption = assumption or self._pick(donor_blocks, terms, ASSUMPTION, exclude=())
                cannot = cannot or self._pick(donor_blocks, terms, CANNOT_RULE_OUT, exclude=())
                borrowed.append(donor)
                citations.append(str(self.chunks.get(donor, {}).get("citation") or donor))

        shape = "estimate" if estimate else "no_estimate"
        required = list(self.shapes.get(shape, {}).get("requires") or [])
        forbidden = list(self.shapes.get(shape, {}).get("forbids") or [])
        check = {
            "interval": bool(estimate and INTERVAL.search(estimate)),
            "reason_code": bool(reason),
            "identifying_assumption": bool(assumption and ASSUMPTION.search(assumption)),
            "cannot_rule_out": bool(cannot and CANNOT_RULE_OUT.search(cannot)),
            "citation": bool(citations[0]),
        }
        missing = [part for part in required if not check.get(part)]
        if missing:
            return None
        violated = [part for part in forbidden if check.get(part)]
        if violated:
            # A reason answer that carries an interval is an estimate answer wearing a reason's label.
            return None
        return {
            "shape": shape,
            "required": required,
            "estimate": estimate,
            "reason": reason,
            "check_block": check_block,
            "assumption": assumption,
            "cannot": cannot,
            "focus": focus,
            "citation": "; ".join(dict.fromkeys(citations)),
            "chunks_used": [source] + borrowed,
            "check": check,
        }

    def _design_donor(self, design_id: str) -> str | None:
        """One card of a design, to carry the design's assumption and caveats."""
        candidates = sorted(
            chunk_id for (outcome_id, card_design), chunk_id in self.cards.items()
            if card_design == design_id
        )
        return candidates[0] if candidates else None

    def _answered(self, question: str, decision, source: str, assembled: dict) -> Answer:
        text = self._render(question, source, assembled)
        return Answer(
            status="answered",
            question=question,
            text=text,
            intent=decision.intent,
            rule_id=decision.rule_id,
            route=None,
            citation=assembled["citation"],
            chunks_used=assembled["chunks_used"],
            check=assembled["check"],
            plain=self._plain(assembled, source),
            shape=assembled["shape"],
            refusal_code=None,
        )

    # -- the fact path --------------------------------------------------------------------------
    def _fact_answer(self, question: str, decision) -> Answer | None:
        """A question that asks for neither a number nor a reason is answered with the passages that say it.

        The unit quoted is the paragraph, not the chunk. A section of the corpus is long, and the
        sentence that answers the question is one paragraph of it: quoting the whole section buries
        the answer, and quoting the single paragraph with the highest word overlap drops the
        conclusion when the section's answer is split across two paragraphs -- the first sets out the
        situation, the second says what it means. So the document whose best paragraph answers the
        question is the one quoted, and its other paragraphs that carry the question's words are
        quoted with it.
        """
        outcomes = self._named_outcomes(question)
        terms = tokenize(question)
        years = {int(year) for year in YEAR.findall(question)}
        passages = self._fact_passages(question, terms, years, outcomes)
        if not passages:
            return None
        body = "\n\n".join(text for _parent, _chunk_id, text in passages)
        citations = list(dict.fromkeys(
            str(self.chunks.get(parent, {}).get("citation") or parent)
            for parent, _chunk_id, _text in passages))
        citation = "; ".join(citations)
        if not citation:
            return None
        assembled = {
            "shape": "fact",
            "estimate": None,
            "reason": None,
            "check_block": None,
            "assumption": None,
            "cannot": None,
            "focus": body,
            "citation": citation,
            "chunks_used": [chunk_id for _parent, chunk_id, _text in passages],
            "check": {"citation": True, "interval": False, "reason_code": False,
                      "identifying_assumption": False, "cannot_rule_out": False},
        }
        return self._answered(question, decision, passages[0][0], assembled)

    def _fact_passages(self, question: str, terms: list[str], years: set[int],
                       outcomes: set[str]) -> list[tuple[str, str, str]]:
        """The paragraphs that answer the question, each with the document it belongs to.

        The score is the retrieval scorer's own idf weighting, so a paragraph carrying the rare words
        of the question outranks one that merely repeats its common ones. A paragraph carrying an
        interval is not a fact passage: it is a number without the assumption that makes it mean
        anything, and the contract forbids an interval in a fact answer.

        The answer quotes one document. A second document was tried and dropped: it never supplied a
        passage the first did not, and it added passages about a different subject that happened to
        share a word with the question.
        """
        candidates: list[tuple[float, int, str, str, str]] = []
        for rank, (parent, parts) in enumerate(self._parents_in_order(self.bm25.rank(question, self.k * 8))):
            if outcomes and not self._covers(parent, outcomes):
                continue
            for chunk_id in parts:
                for paragraph in self._paragraphs(chunk_id):
                    if INTERVAL.search(paragraph):
                        continue
                    # The assumption and the caveats are the estimate shape's slots. A fact answer is
                    # the passage that says the thing asked about, so it does not quote them.
                    if BLOCK_ASSUMPTION.match(paragraph) or BLOCK_CANNOT.match(paragraph):
                        continue
                    score = self._overlap(terms, years, paragraph)
                    if score <= 0.0:
                        continue
                    candidates.append((score, rank, parent, chunk_id, paragraph))
        if not candidates:
            return []
        candidates.sort(key=lambda row: (-row[0], row[1], row[3]))
        if candidates[0][0] < self.fact_overlap_min:
            return []
        document = candidates[0][2]
        chosen = [row for row in candidates if row[2] == document][:self.fact_max_passages]
        return [(row[2], row[3], row[4]) for row in chosen]

    def _weight(self, term: str) -> float:
        """How much a matched term is worth. A term rare in the corpus is stronger evidence."""
        return float(self.bm25.idf.get(term, self.default_idf))

    def _overlap(self, terms: list[str], years: set[int], body: str) -> float:
        """How much of the question the passage carries, weighted by how rare each word is.

        The weight is the retrieval scorer's own idf. Counting words equally let a passage that says
        "president" and "party" outrank the administration record that names the year the question
        asked about; weighting by rarity puts the record first, because "2012" is rarer in the corpus
        than "president" and is the word the question turns on. A year counts as carried when the
        passage states it or when a date range in it spans it.
        """
        if not terms:
            return 1.0
        body_terms = set(tokenize(body))
        hits = matched_terms(terms, body_terms)
        spans = DATE_RANGE.findall(body)
        for year in years:
            key = str(year)
            if key in hits:
                continue
            if key in body or any(int(low[:4]) <= year <= int(high[:4]) for low, high in spans):
                hits.add(key)
        total = sum(self._weight(term) for term in terms)
        got = sum(self._weight(term) for term in hits)
        return got / max(total, 1e-9)

    # -- routing --------------------------------------------------------------------------------
    def _named_outcomes(self, question: str) -> set[str]:
        """The outcome the question names, resolved by the label's own words.

        A label is a phrase and a question names it by a run of that phrase: "under-5 mortality"
        is three words of "Under-5 mortality rate" in order, and "maternal mortality" is one word
        of "Maternal mortality ratio" — the longer run wins, so a maternal question does not land on
        the under-5 card. A single word is enough only when no other label uses it, which is what
        keeps "fatalities" naming the fatality outcome and "cover" naming nothing at all.
        """
        if not self.outcomes:
            return set()
        words = question_words(question)
        distinctive = self._distinctive_terms()
        best: tuple[tuple[int, int], str] | None = None
        for outcome_id, label in self.outcomes.items():
            run = self._longest_run(label_words(label), words)
            hits = len(distinctive.get(outcome_id, set()) & set(words))
            if run == 0 or (run == 1 and hits == 0):
                continue
            score = (run, hits)
            if best is None or score > best[0]:
                best = (score, outcome_id)
        return {best[1]} if best else set()

    def _distinctive_terms(self) -> dict[str, set[str]]:
        """Each outcome's words that no other outcome's label uses, and that are not ordinary words."""
        labels = {outcome_id: label_words(label) for outcome_id, label in self.outcomes.items()}
        counts: dict[str, int] = {}
        for words in labels.values():
            for word in set(words):
                counts[word] = counts.get(word, 0) + 1
        return {
            outcome_id: {
                word for word in set(words)
                if counts[word] == 1 and len(word) >= 4 and word not in GENERIC_TERMS
            }
            for outcome_id, words in labels.items()
        }

    @staticmethod
    def _longest_run(label_terms: list[str], question_terms: list[str]) -> int:
        """The longest run of the label's words the question carries, contiguously and in order."""
        best = 0
        for start in range(len(label_terms)):
            for end in range(start + 1, len(label_terms) + 1):
                run = label_terms[start:end]
                if len(run) <= best:
                    break
                if AnswerLayer._contains_run(run, question_terms):
                    best = len(run)
        return best

    @staticmethod
    def _contains_run(run: list[str], sequence: list[str]) -> bool:
        """Whether the sequence carries the run as a contiguous phrase."""
        size = len(run)
        if size == 0 or size > len(sequence):
            return False
        return any(sequence[index:index + size] == run for index in range(len(sequence) - size + 1))

    @staticmethod
    def _appears_in_order(run: list[str], sequence: list[str]) -> bool:
        position = 0
        for term in run:
            for index in range(position, len(sequence)):
                if same_term(term, sequence[index]):
                    position = index + 1
                    break
            else:
                return False
        return True

    def _named_designs(self, question: str) -> set[str]:
        """The designs a question names — "Design B", or the design's own name."""
        named = {match.upper() for match in re.findall(r"\bdesign\s*([abc])\b", question.lower())}
        if named:
            return named
        terms = set(tokenize(question))
        for design_id, name in self.designs.items():
            distinctive = {term for term in tokenize(name) if term not in GENERIC_TERMS}
            if len(distinctive & terms) >= 2:
                named.add(design_id)
        return named

    def _design_of(self, source: str) -> str | None:
        metadata = self.chunks.get(source, {}).get("metadata") or {}
        if metadata.get("design_id"):
            return str(metadata["design_id"])
        if source.startswith("result:"):
            return source.split(":", 1)[1]
        return None

    def _covers(self, parent: str, named: set[str]) -> bool:
        """Whether a parent is about one of the outcomes the question names."""
        metadata = self.chunks.get(parent, {}).get("metadata") or {}
        if metadata.get("outcome_id"):
            return str(metadata["outcome_id"]) in named
        cells = metadata.get("cells") or {}
        if cells:
            # An event chunk carries the outcome it measured as its cell keys.
            return any(str(outcome_id) in named for outcome_id in cells)
        words = set(question_words(" ".join(
            str(self.chunks.get(cid, {}).get("text") or "")
            for cid in self.gate.parts_of(parent)
        )))
        for outcome_id in named:
            if outcome_id in words:
                return True
            if set(label_words(self.outcomes.get(outcome_id, ""))) & words:
                return True
        return False

    # -- assembly -------------------------------------------------------------------------------
    def _blocks(self, source: str) -> list[str]:
        """The paragraphs of a chunk, with the part markers taken out."""
        blocks: list[str] = []
        for chunk_id in self.gate.parts_of(source):
            blocks.extend(self._paragraphs(chunk_id))
        return blocks

    def _paragraphs(self, chunk_id: str) -> list[str]:
        """A chunk's paragraphs: the blank lines separate them, and the part marker is not one."""
        return [block.strip() for block in re.split(r"\n\s*\n", self._body(chunk_id)) if block.strip()]

    def _body(self, chunk_id: str) -> str:
        """A chunk's text without the part marker the corpus writes at the top of each part."""
        return PART_HEADER.sub("", str(self.chunks.get(chunk_id, {}).get("text") or "")).strip()

    def _pick(self, blocks: list[str], terms: list[str], pattern: re.Pattern,
              exclude: tuple) -> str | None:
        """The block that best matches the question among those the pattern accepts."""
        candidates = [block for block in blocks
                      if block not in exclude and pattern.search(block)]
        if not candidates:
            return None
        return max(candidates, key=lambda block: (len(matched_terms(terms, set(tokenize(block)))), -len(block)))

    def _carries_interval(self, chunk_id: str) -> bool:
        """Whether a chunk carries a published interval — a number with the range the data cannot rule out.

        The search is over the chunk's text and its parts', not its identifier: the identifier says
        which card it is, and the interval is what the card says — and a design-level result keeps
        its number in a part.
        """
        return any(INTERVAL.search(self._body(part)) for part in self.gate.parts_of(chunk_id))

    def _parents_in_order(self, retrieved: list[tuple[str, float]]) -> list[tuple[str, list[str]]]:
        seen: list[str] = []
        for chunk_id, _score in retrieved:
            parent = chunk_id.split("#p", 1)[0]
            if parent not in seen:
                seen.append(parent)
        return [(parent, self.gate.parts_of(parent)) for parent in seen]

    def _render(self, question: str, source: str, assembled: dict) -> str:
        lines = [f"**Question:** {question}", ""]
        if assembled["shape"] == "estimate":
            lines += [f"**Estimate:** {assembled['estimate']}", ""]
            if assembled.get("check_block"):
                lines += [f"**The check that decided it:** {assembled['check_block']}", ""]
        elif assembled["shape"] == "no_estimate":
            lines += [f"**Why there is no number:** {assembled['reason']}", ""]
            if assembled.get("check_block"):
                lines += [f"**The check that decided it:** {assembled['check_block']}", ""]
        else:
            lines += [f"**The record says:** {assembled['focus']}", ""]
        if assembled.get("assumption"):
            lines += [f"**Identifying assumption:** {assembled['assumption']}", ""]
        if assembled.get("cannot"):
            lines += [f"**What it cannot rule out:** {assembled['cannot']}", ""]
        if assembled.get("focus") and assembled["shape"] != "fact":
            lines += [f"**The passage that answers this:** {assembled['focus']}", ""]
        lines.append(f"**Citation:** {assembled['citation']} — {source}")
        return "\n".join(lines).strip()

    # -- the plain-language view ----------------------------------------------------------------
    def _plain(self, assembled: dict, source: str) -> dict:
        """The same answer for a reader who does not work with statistics.

        It restates nothing that the quoted passages do not say: the signs, the interval's bounds, the
        sample size and the months are copied out of the estimate paragraph, and the definitions are
        the glossary's own lines. The contract answer remains `text`; this is a second reading of it.
        """
        quoted = " ".join(str(assembled.get(slot) or "") for slot in
                          ("estimate", "reason", "check_block", "assumption", "cannot", "focus"))
        terms = [{"term": term, "meaning": meaning}
                 for term, meaning in self.glossary.items()
                 if re.search(rf"\b{re.escape(term.lower())}\b", quoted.lower())]
        lines: list[str] = []

        if assembled["shape"] == "estimate":
            estimate_full = " ".join(str(assembled.get("estimate") or "").split())
            estimate = self._sentence_with(estimate_full, "interval") or estimate_full
            reading = self._reading(estimate)
            headline = (reading or {}).get("sentence") or (
                "The corpus answers this from the passage below; it carries no single coefficient to read."
            )
            lines += [f"**Short answer:** {headline}", "", f"**The number:** {estimate}", ""]
        elif assembled["shape"] == "no_estimate":
            reason = " ".join(str(assembled.get("reason") or "").split())
            headline = self._sentence_with(reason, "Reason code") or reason
            lines += [f"**Short answer:** {headline}", "",
                      f"**Why there is no number:** {reason}", ""]
            if assembled.get("check_block"):
                lines += [f"**What decided it:** {assembled['check_block']}", ""]
        else:
            passage = " ".join(str(assembled.get("focus") or "").split())
            headline = self._first_sentence(passage)
            lines += [f"**Short answer:** {headline}", "", f"**The record says:** {passage}", ""]

        if assembled.get("assumption"):
            assumption_full = " ".join(str(assembled.get("assumption") or "").split())
            assumption = (self._sentence_with(assumption_full, "identifying assumption")
                          or assumption_full)
            lines += [f"**What it assumes:** {assumption}", ""]
        if assembled.get("cannot"):
            cannot_full = str(assembled.get("cannot") or "")
            bullets = [line.strip() for line in cannot_full.splitlines()
                       if line.strip().startswith(("-", "*"))]
            cannot = "\n".join(bullets) if bullets else " ".join(cannot_full.split())
            lines += [f"**What it cannot tell you:** {cannot}", ""]
        lines.append(f"**Where this comes from:** {assembled['citation']} — {source}")
        if terms:
            lines += ["", "**What the words mean:**", ""]
            lines += [f"- **{item['term']}** — {item['meaning']}" for item in terms]
        reading = None
        if assembled["shape"] == "estimate":
            estimate_full = " ".join(str(assembled.get("estimate") or "").split())
            reading = self._reading(self._sentence_with(estimate_full, "interval") or estimate_full)
        return {"headline": headline, "reading": reading, "terms": terms, "text": "\n".join(lines)}

    def _plain_refusal(self, reason: str, citation: str | None, quote: str, code: str | None) -> dict:
        """A refusal, read plainly: what the rule is, in the glossary's own words."""
        meaning = self.glossary.get(str(code)) if code else None
        lines = [f"**Short answer:** {reason}", ""]
        if meaning:
            lines += [f"**In plain English ({code}):** {meaning}", ""]
        if quote:
            lines += [f"**What the record says:** {quote}", ""]
        lines.append(f"**Where this comes from:** {citation or 'no citable chunk'}")
        text = "\n".join(lines)
        return {"headline": reason, "reading": None, "terms": [], "text": text}

    @staticmethod
    def _first_sentence(text: str) -> str:
        parts = re.split(r"(?<=[.!?])\s+", text, maxsplit=1)
        return parts[0].strip() if parts else text

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
        quote = " ".join(self._body(chunk_id).split())
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


# The patterns a prose chunk is matched on, declared here so the assembly rules are in one place.
REASON_PATTERN = (r"Reason code:|Status:\s*not_run|not estimated here|infeasible|"
                  r"not estimated|No estimate for this")
CHECK_PATTERN = r"Failed checks:|Verdict rule:|The check that decided:|^Verdict:|placebo|lead-shift"
# The pattern that accepts any paragraph at all, so the "passage that answers this" can be the
# remaining paragraph that matches the question best.
ANY_BLOCK = re.compile(r".", re.DOTALL)


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
