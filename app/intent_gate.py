"""The intent gate: decide whether a question can be answered, and what a refusal must cite.

Stage 8's exit criterion is that the app can be built without opening R. This module is the same
contract for the *chat* layer the registry cannot serve: it reads the rules declared in
`analysis/specs/intent_gate.yml` and the corpus those rules point at, and it decides an intent. It
computes no statistic, holds no number, and fits nothing.

Four rules are enforced here rather than trusted to the caller:

  * **The rules decide, in order.** Every rule carries a unique priority, so the decision is total
    and deterministic: the first rule whose conditions hold decides, and no rule holds means
    `answerable`.
  * **The default is `answerable`.** The gate may add a refusal; it may never remove one. A question
    the corpus could have answered is not one the gate takes away.
  * **A refusal needs a reason.** A reason-bearing rule resolves its route against the corpus, and a
    route that does not resolve to exactly one existing chunk falls back to `answerable` — the gate
    will not refuse without something to cite.
  * **No number is typed here.** The study window and the vintage come from the artifacts, and the
    rules come from the spec. The only literals in this file are the regexes that read the spec's own
    conditions, and the year pattern that finds a year in a question.

The module is framework-free on purpose: it imports no UI library, no model, no database and no
network client, so the same code answers a question in a test, in the app, and in a harness.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

SPEC_PATH = Path("analysis/specs/intent_gate.yml")
INDEX_PATH = Path("registry/dags/index.json")
CORPUS_PATH = "registry/rag/{vintage}/corpus.json"
QUALITY_PATH = "registry/quality/{vintage}/report.json"

# The normalisation the spec declares: lowercase, drop apostrophes, everything else that is not
# alphanumeric becomes a space, then collapse the spaces. No stemming and no synonyms — a rule has to
# be readable in the form it is matched in.
NON_WORD = re.compile(r"[^a-z0-9]+")
APOSTROPHES = ("'", "’")
YEAR = re.compile(r"\b((?:19|20)\d{2})\b")


def normalise(text: str) -> str:
    """The question as the rules see it."""
    lowered = str(text).lower()
    for mark in APOSTROPHES:
        lowered = lowered.replace(mark, "")
    return " ".join(NON_WORD.sub(" ", lowered).split())


def first_sentence(text: str) -> str:
    """The rule's own words, in one sentence — what a refusal template can carry."""
    flat = " ".join(str(text).split())
    parts = re.split(r"(?<=[.!?])\s+", flat, maxsplit=1)
    return parts[0].strip()


@dataclass(frozen=True)
class Decision:
    """What the gate decided, and what a refusal would have to cite."""

    intent: str
    rule_id: str | None
    route: str | None
    route_status: str
    reason: str
    matched: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {
            "intent": self.intent,
            "rule_id": self.rule_id,
            "route": self.route,
            "route_status": self.route_status,
            "reason": self.reason,
            "matched": self.matched,
        }


class Gate:
    """The declared rules, applied to a question, over one corpus."""

    def __init__(self, spec: dict, corpus: dict, window_start: str | None, vintage: str):
        self.spec = spec
        self.rules = sorted(spec.get("rules") or [], key=lambda rule: rule["priority"])
        self.chunks = {chunk["chunk_id"]: chunk for chunk in corpus.get("chunks") or []}
        self.window_start_year = int(str(window_start)[:4]) if window_start else None
        self.vintage_year = int(str(vintage)[:4])
        self._section_cache: dict[tuple[str, str], str | None] = {}

    # -- the decision ---------------------------------------------------------------------------
    def decide(self, question: str) -> Decision:
        text = normalise(question)
        for rule in self.rules:
            if not self._conditions_hold(rule, text):
                continue
            route, route_status = self._resolve_route(rule)
            if rule["intent"] != "answerable" and route_status != "pinned":
                # A refusal without a reason to quote is the failure this project is built to avoid.
                return Decision(
                    intent="answerable",
                    rule_id=rule["id"],
                    route=None,
                    route_status="unresolved",
                    reason=f"rule {rule['id']} matched but its route did not resolve, so the question is "
                           "answered rather than refused without a citation",
                    matched=self._matched(rule, text),
                )
            return Decision(
                intent=rule["intent"],
                rule_id=rule["id"],
                route=route,
                route_status=route_status,
                reason=first_sentence(rule.get("why") or rule.get("implements") or ""),
                matched=self._matched(rule, text),
            )
        return Decision(
            intent="answerable",
            rule_id=None,
            route=None,
            route_status="not_applicable",
            reason="no rule matched, and the default is answerable",
            matched={},
        )

    # -- conditions -----------------------------------------------------------------------------
    def _conditions_hold(self, rule: dict, text: str) -> bool:
        conditions = rule.get("conditions") or {}
        for group in conditions.get("all_of") or []:
            if not any(re.search(pattern, text) for pattern in group):
                return False
        any_of = conditions.get("any_of") or []
        if any_of and not any(any(re.search(pattern, text) for pattern in group) for group in any_of):
            return False
        for entry in conditions.get("none_of") or []:
            # `none_of` is a flat list of patterns in the spec; a rule may also write one group of
            # alternatives, so a list is flattened before it is read.
            patterns = entry if isinstance(entry, list) else [entry]
            if any(re.search(pattern, text) for pattern in patterns):
                return False
        window = conditions.get("year_window") or rule.get("year_window")
        if window and not self._year_window_holds(window, text):
            return False
        return True

    def _year_window_holds(self, mode: str, text: str) -> bool:
        years = [int(year) for year in YEAR.findall(text)]
        if not years or self.window_start_year is None:
            return False
        if mode == "outside":
            return any(
                year < self.window_start_year or year > self.vintage_year for year in years
            )
        if mode == "future":
            return any(year > self.vintage_year for year in years)
        if mode == "past":
            return any(year < self.window_start_year for year in years)
        raise ValueError(f"unknown year_window mode {mode!r}")

    def _matched(self, rule: dict, text: str) -> dict:
        """Which of the rule's own patterns fired — so a decision can be argued with."""
        conditions = rule.get("conditions") or {}
        hits: list[str] = []
        for group in conditions.get("all_of") or []:
            hits.extend(pattern for pattern in group if re.search(pattern, text))
        for group in conditions.get("any_of") or []:
            hits.extend(pattern for pattern in group if re.search(pattern, text))
        return {"patterns": sorted(set(hits))}

    # -- routes ---------------------------------------------------------------------------------
    def _resolve_route(self, rule: dict) -> tuple[str | None, str]:
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
            resolved = self._resolve_section(route)
            return (resolved, "pinned") if resolved else (None, "unresolved")
        return None, "unresolved"

    def _resolve_section(self, route: dict) -> str | None:
        """A documentation section, found by its heading — not by a typed chunk id.

        A document that renames its sections makes the route fail to resolve, and a route that cannot
        resolve falls back to `answerable` rather than refusing without a reason.
        """
        document = str(route.get("document") or "")
        stem = Path(document).stem
        needle = str(route.get("heading_contains") or "").lower()
        key = (stem, needle)
        if key in self._section_cache:
            return self._section_cache[key]
        prefix = f"doc:{stem}#"
        hits = [
            chunk_id
            for chunk_id, chunk in self.chunks.items()
            if chunk_id.startswith(prefix)
            and chunk_id.count("#") == 1
            and needle in str(chunk.get("title") or "").lower()
        ]
        resolved = hits[0] if len(hits) == 1 else None
        self._section_cache[key] = resolved
        return resolved

    # -- the corpus a chunk's parts belong to ---------------------------------------------------
    def parts_of(self, chunk_id: str) -> list[str]:
        """The chunk and its parts — a reason is often in the part, not the parent."""
        return [cid for cid in self.chunks if cid == chunk_id or cid.startswith(f"{chunk_id}#p")]

    def chunk_text(self, chunk_id: str) -> str:
        return str(self.chunks.get(chunk_id, {}).get("text") or "")


def load_gate(root: Path | str | None = None) -> Gate:
    """The gate over the published vintage: its rules, its corpus, and the window it reads."""
    root = Path(root) if root is not None else Path(__file__).resolve().parents[1]
    spec = yaml.safe_load((root / SPEC_PATH).read_text(encoding="utf-8"))
    index = json.loads((root / INDEX_PATH).read_text(encoding="utf-8"))
    vintage = index["vintage_date"]
    corpus = json.loads((root / CORPUS_PATH.format(vintage=vintage)).read_text(encoding="utf-8"))
    quality_path = root / QUALITY_PATH.format(vintage=vintage)
    window_start = None
    if quality_path.exists():
        quality = json.loads(quality_path.read_text(encoding="utf-8"))
        window_start = (quality.get("study_window") or {}).get("start")
    return Gate(spec=spec, corpus=corpus, window_start=window_start, vintage=vintage)
