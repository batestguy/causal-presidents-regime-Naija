"""Build the Stage 8 retrieval corpus from the registry, the tables and the narrative.

Why this is generated rather than written: the RAG layer is the one component that can undo this project's
honesty argument in a sentence — retrieve the +0.4793, drop the `estimated_not_identified` verdict, and
answer with a citation that looks authoritative. So no chunk is composed by hand. A model-card chunk is a
serialisation of the card's own fields (assumption, adjustment set, cannot-rule-out, estimate block,
verdict); a result chunk is a serialisation of the index's published result; a narrative chunk is a split of
the committed markdown. Nothing here computes a statistic, and nothing here types a number.

Two invariants decide the shape of the artifact:

  * **Vintage.** The corpus vintage is the registry index's `vintage_date`, every chunk carries it, and it
    must equal the vintage of the estimates, events and quality artifacts the chunks quote. An answer
    stamped from a chunk is a statement about that data vintage, not about the clock.
  * **Attribution.** Every chunk records the sha256 of the file it was read from. If a source changes and
    the corpus is not rebuilt, `tests/verify_rag.py` fails — the same invariant the registry uses for
    numbers (C-44, C-53), applied to prose.

The vectors are a separate step (`--embed`) on purpose: building the text needs only Python and PyYAML, so
CI can rebuild the corpus without torch. `--embed` encodes the chunks *and* the eval questions, so the
verifier can recompute every retrieval metric from the stored vectors without loading a model.

Usage:
    python scripts/build_rag_corpus.py                 # text corpus + eval set (no model needed)
    python scripts/build_rag_corpus.py --embed         # the above, then the vectors
    /c/conda-envs/drlca-rag/python.exe scripts/build_rag_corpus.py --embed   # the torch env
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC_PATH = REPO_ROOT / "analysis" / "specs" / "rag.yml"
EVAL_SPEC_PATH = REPO_ROOT / "analysis" / "specs" / "rag_eval.yml"
SCHEMA_VERSION = "0.1.0"


class BuildError(RuntimeError):
    """A declared input or rule did not hold. Never downgraded to a warning."""


# ---------------------------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------------------------
def sha256_of(path: Path) -> str:
    """Raw bytes — for binary artifacts, where any normalisation would corrupt the comparison."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sha256_text(path: Path) -> str:
    """Canonical source hash: CRLF collapsed to LF before hashing.

    `.gitattributes` sets `* text=auto eol=lf`, so the index stores this repository's text with LF even
    though it is authored on Windows. Hashing the working-tree bytes would therefore record a hash that a
    fresh clone (or the Linux runner) can never reproduce — a corpus that verifies only on the machine that
    built it. The source hashes cover the *canonical* file, and `tests/verify_rag.py` applies the same rule,
    so a Windows checkout and a CI checkout agree.
    """
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def git_sha() -> str | None:
    try:
        return subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip() or None
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        return None


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def newest_dir(root: Path) -> Path:
    if not root.exists():
        raise BuildError(f"{root.relative_to(REPO_ROOT)}: no such directory")
    dirs = sorted((p for p in root.iterdir() if p.is_dir()), key=lambda p: p.name)
    if not dirs:
        raise BuildError(f"{root.relative_to(REPO_ROOT)}: no vintage directory")
    return dirs[-1]


def newest_artifact(root: Path, name: str) -> Path:
    newest = newest_dir(root)
    path = newest / name
    if not path.exists():
        raise BuildError(f"{path.relative_to(REPO_ROOT)}: missing")
    return path


def signed(value: float) -> str:
    """The one number format used in every chunk and therefore in the eval set's needles."""
    return f"{value:+.4f}"


def interval(low: float, high: float) -> str:
    return f"[{signed(low)}, {signed(high)}]"


def slug(text: str, limit: int = 60) -> str:
    out = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return out[:limit].strip("-") or "section"


def rel(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def flat(value: object) -> str:
    """Collapse a field's internal line breaks.

    Artifact strings are wrapped for reading in their source file ("... 25\n observations above."), and a
    hard line break inside a sentence looks like a paragraph boundary to the splitter, which then ships
    " above." as a 7-character chunk. Artifact prose is flattened; markdown documents are not, because there
    the line breaks are part of the document's own formatting.
    """
    return re.sub(r"\s*\n\s*", " ", str(value)).strip()


# ---------------------------------------------------------------------------------------------
# Chunk assembly
# ---------------------------------------------------------------------------------------------
class Corpus:
    def __init__(self, spec: dict, index: dict) -> None:
        self.spec = spec
        self.index = index
        self.vintage = index.get("vintage_date")
        if not self.vintage:
            raise BuildError("registry/dags/index.json carries no vintage_date")
        self.chunks: list[dict] = []
        self.sources: dict[str, dict] = {}
        self._ids: set[str] = set()
        self._files: dict[str, dict] = {}
        self.max_chars = int(spec["chunking"]["max_chars"])
        self.min_chars = int(spec["chunking"]["min_chars"])
        self.min_part_chars = int(spec["chunking"].get("min_part_chars", spec["chunking"]["min_chars"]))

    def register_source(self, path: Path, role: str) -> dict:
        if not path.exists():
            raise BuildError(f"{rel(path)}: declared in analysis/specs/rag.yml but absent — the corpus would "
                             "lose a whole family of chunks while still looking complete")
        key = rel(path)
        if key not in self._files:
            data = path.read_bytes()
            self._files[key] = {
                "path": key,
                "role": role,
                "sha256": sha256_text(path),
                "bytes": len(data.replace(b"\r\n", b"\n")),
                "hash_rule": "sha256 of the file with CRLF normalised to LF (the index's eol=lf)",
            }
        return self._files[key]

    def add(
        self,
        chunk_id: str,
        doc_type: str,
        title: str,
        text: str,
        source_path: Path,
        anchor: str | None,
        metadata: dict,
        header: str | None = None,
    ) -> None:
        """Add one chunk, splitting on paragraphs when the text exceeds the budget.

        `header` is context every part carries (a document's H1 + section heading). It is *not* part of the
        text being split, because a 112-character header inside the split would become a 112-character
        "chunk" of its own the moment the content below it is a single big table — which is exactly what
        happened to `docs/limitations.md` §3 before this was separated.

        The split is the only place a chunk id may grow a `#pN` suffix. Every part keeps the parent title and
        opens with a line naming the parent and the part, because a part retrieved alone has to be
        attributable: a fragment that starts mid-argument is how a quotation loses the caveat beside it.
        """
        text = text.strip()
        header = (header or "").strip()
        short_title = title[:48]
        overhead = (len(header) + 2 if header else 0) + len(short_title) + 40
        # Split until every assembled body fits. The marker is bounded (a truncated title plus the part
        # number), so this converges in one pass in practice; the retry is here because "it fits in practice"
        # is the assumption that produced a 1,839-character chunk on the first attempt.
        for attempt in range(4):
            budget = max(self.max_chars - overhead - attempt * 80, self.min_chars)
            parts = split_to_budget(text, budget, min_tail=self.min_part_chars)
            n_parts = len(parts)
            bodies = []
            for number, part in enumerate(parts, start=1):
                marker = (f"[{short_title} — part {number} of {n_parts}]" if n_parts > 1 else "")
                bodies.append("\n\n".join(piece for piece in (header, marker, part) if piece).strip())
            if all(len(body) <= self.max_chars for body in bodies):
                break
        else:
            raise BuildError(
                f"{chunk_id}: could not fit the text into {self.max_chars}-character parts after four passes"
            )
        for number, (part, body) in enumerate(zip(parts, bodies), start=1):
            part_id = chunk_id if number == 1 else f"{chunk_id}#p{number}"
            if part_id in self._ids:
                raise BuildError(f"{part_id}: duplicate chunk id")
            if len(body) > self.max_chars:
                raise BuildError(
                    f"{part_id}: {len(body)} chars exceeds chunking.max_chars={self.max_chars} — the split "
                    "rule is required to keep every chunk inside the embedding budget"
                )
            floor = self.min_part_chars if n_parts > 1 else self.min_chars
            if len(part) < floor:
                raise BuildError(
                    f"{part_id}: {len(part)} chars of content is below the declared floor ({floor}) — a "
                    "header with no body is not a retrievable unit, and a split part below 80 characters is "
                    "a sentence torn out of its argument"
                )
            source = self.register_source(source_path, doc_type)
            self._ids.add(part_id)
            self.chunks.append(
                {
                    "chunk_id": part_id,
                    "doc_type": doc_type,
                    "title": title,
                    "text": body,
                    "vintage": self.vintage,
                    "source": {
                        "path": source["path"],
                        "anchor": anchor,
                        "sha256": source["sha256"],
                    },
                    "citation": f"{title} — {source['path']} (vintage {self.vintage})",
                    "metadata": {**metadata, "part": number, "n_parts": n_parts},
                    "chars": len(body),
                    # A hash of the chunk's own text: the source hashes catch an edited document, and this
                    # catches an edited *chunk* — a text change small enough not to move a ranking would
                    # otherwise leave the corpus describing something no build produced.
                    "text_sha256": hashlib.sha256(body.encode("utf-8")).hexdigest(),
                }
            )

    def source_manifest(self) -> list[dict]:
        return [self._files[key] for key in sorted(self._files)]


# ---------------------------------------------------------------------------------------------
# Family: model cards
# ---------------------------------------------------------------------------------------------
def direction_words(direction: str) -> str:
    return {"down": "down (lower is better)", "up": "up (higher is better)"}.get(
        str(direction), f"{direction} (direction undeclared)"
    )


def card_text(card: dict) -> str:
    outcome = card["outcome"]
    design = card["design"]
    lines = [
        f"Model card {card['dag_id']}: {outcome['label']} under Design {design['id']} ({design['short']}).",
        "",
        f"Outcome: {outcome['label']} ({outcome['id']}). Unit: {outcome.get('unit', 'not stated')}. "
        f"Direction: {direction_words(outcome.get('direction'))}. Frequency: {outcome.get('frequency', '?')}. "
        f"Source: {outcome.get('source', '?')}. Coverage: {outcome.get('coverage_status', '?')}.",
    ]
    if outcome.get("coverage_note"):
        lines.append(f"Coverage note: {flat(outcome['coverage_note'])}")

    lines += [
        "",
        f"Design {design['id']} — {design['name']}. Unit: {design.get('unit', '?')}. "
        f"Estimand: {flat(design.get('estimand', '?'))}. Estimator: {flat(design.get('estimator', '?'))}.",
        f"Identifying assumption: {flat(card.get('identifying_assumption', 'not stated'))}",
        f"Adjustment set (backdoor criterion): {', '.join(card.get('adjustment_set') or []) or 'none'}.",
        f"Node assumed absent: {', '.join(card.get('assumption_required') or []) or 'none'}.",
        "",
        "What this design cannot rule out:",
    ]
    for item in card.get("cannot_rule_out") or []:
        lines.append(f"- {flat(item)}")

    diag = card.get("diagnostics") or {}
    lines += ["", f"Stage 5 pre-check on this (outcome, design) pair: {diag.get('status', 'not run')}."]
    if diag.get("blocker"):
        lines.append(f"Pre-check blocker: {flat(diag['blocker'])}.")
    failed_checks = [check for check in (diag.get("checks") or [])
                     if check.get("verdict") not in ("pass", "computed")]
    for check in failed_checks:
        lines.append(f"- {check.get('id')}: {check.get('verdict')} — {flat(check.get('detail'))}")
    # The full per-check list lives in registry/diagnostics; a card chunk carrying every check of every
    # design is what turned one card into eight retrieval units and diluted the estimate paragraph.
    if diag.get("note"):
        lines.append(flat(diag["note"]))

    estimate = card.get("estimate") or {}
    status = estimate.get("status", "not_estimated")
    lines += ["", f"Estimate status: {status}."]
    if status == "estimated":
        spec = estimate["specification"]
        verdict = estimate.get("verdict") or {}
        robustness = estimate.get("robustness") or {}
        level = robustness.get("axis_level") or {}
        support = robustness.get("design_support") or {}
        lines += [
            f"The published specification is Design {spec['design']} on {spec['outcome']}: "
            f"{spec['coefficient_name']} = {signed(spec['coefficient'])} "
            f"(standard error {spec['standard_error']:.4f}), "
            f"95% interval {interval(spec['ci_low'], spec['ci_high'])}, "
            f"p = {spec['p_value']:.4f}, n = {spec['n_obs']:,} state-months over {spec['n_units']} states, "
            f"{spec['first_month']} to {spec['last_month']}.",
            f"Estimator: {spec['estimator']}. Formula: {spec['formula']}. Covariance: {spec['covariance']}.",
            f"The number is for this card: {str(estimate.get('the_number_is_for_this_card')).lower()}.",
            f"Verdict: {verdict.get('status')}. {flat(verdict.get('failed_checks') or 'No check failed.')} "
            f"{flat(verdict.get('rule') or '')}".strip(),
        ]
        if level:
            lines += [
                f"Stage 7 robustness: this specification is "
                f"{'the' if robustness.get('this_specification_is_the_preferred_one') else 'not the'} "
                f"preferred one for its design. Across the {level.get('n')} specifications sharing this "
                f"outcome, {level.get('n_positive')} are positive and {level.get('n_negative')} negative; "
                f"{level.get('n_opposite')} sit on the other side of zero, so this axis level "
                f"{'flips against' if level.get('flips_against_preferred') else 'does not flip against'} "
                f"the preferred specification. The design's {support.get('n')} specifications split "
                f"{support.get('n_positive')} positive / {support.get('n_negative')} negative, with "
                f"{support.get('n_near_zero')} inside the ±{robustness.get('near_zero_band')} near-zero band "
                f"and {robustness.get('design_flip_levels')} axis levels flipping. The flip rule and its "
                f"reason are in docs/robustness.md.",
            ]
        lines.append(f"Model card reference: {estimate.get('model_card_ref')}.")
    else:
        reason = estimate.get("not_estimated_reason") or {}
        lines += [
            f"No estimate for this (outcome, design) pair. Reason code: {reason.get('code')}. "
            f"{flat(reason.get('detail'))}",
        ]
        if estimate.get("published_result"):
            lines.append(f"The design-level result is published at {estimate['published_result']}.")

    return "\n".join(line for line in lines if line is not None)


def build_cards(corpus: Corpus) -> None:
    cards_dir = REPO_ROOT / corpus.spec["input"]["cards_dir"]
    paths = sorted(p for p in cards_dir.glob("*.json") if p.name != "index.json")
    if not paths:
        raise BuildError(f"{rel(cards_dir)}: no cards on disk")
    for path in paths:
        card = read_json(path)
        corpus.add(
            chunk_id=f"card:{card['dag_id']}",
            doc_type="model_card",
            title=f"Model card {card['dag_id']} — {card['outcome']['label']} under Design "
                  f"{card['design']['id']}",
            text=card_text(card),
            source_path=path,
            anchor=None,
            metadata={
                "dag_id": card["dag_id"],
                "outcome_id": card["outcome"]["id"],
                "outcome_label": card["outcome"]["label"],
                "domain": card["outcome"].get("domain"),
                "design_id": card["design"]["id"],
                "estimate_status": (card.get("estimate") or {}).get("status"),
                "precheck_status": (card.get("diagnostics") or {}).get("status"),
                "coverage_status": card["outcome"].get("coverage_status"),
                "svg": (card.get("assets") or {}).get("svg"),
            },
        )


# ---------------------------------------------------------------------------------------------
# Family: published results (design-level)
# ---------------------------------------------------------------------------------------------
def result_text(design_id: str, result: dict, vintage: str, source_specs: list[dict],
                index_design: dict | None = None) -> str:
    specs = result.get("specifications") or []
    heading = f"Published result for Design {design_id}"
    if index_design and index_design.get("name"):
        heading = f"{heading} — {flat(index_design['name'])}"
    # The design's own question, taken from the estimates artifact rather than restated here. It is also the
    # strongest retrieval anchor the chunk has: it uses the words a reader uses ("Brent", "oil shock",
    # "states"), where the coefficient rows only use the variable names.
    if source_specs:
        name = flat(source_specs[0].get("design_name", ""))
        if name:
            heading = f"{heading}. {name}"
        estimator = source_specs[0].get("estimator")
        if estimator:
            heading = f"{heading} Estimator: {flat(estimator)}."
    if index_design and index_design.get("estimand"):
        heading = f"{heading} Estimand: {flat(index_design['estimand'])}."
    lines = [
        f"{heading}",
        f"Status: {result.get('status')}. Result is card-level: "
        f"{str(result.get('result_is_card_level')).lower()}.",
    ]
    if not specs and result.get("why"):
        first_sentence = re.split(r"(?<=[.!?])\s+", flat(result["why"]))[0]
        lines.append(f"Headline: {first_sentence}")
    verdict = result.get("verdict") or {}
    if verdict.get("rule"):
        lines.append(f"Verdict rule: {flat(verdict['rule'])}")
    failed = verdict.get("failed_checks")
    if isinstance(failed, list):
        lines.append(f"Failed checks: {flat(', '.join(failed)) if failed else 'none'}.")
    elif failed:
        lines.append(f"Failed checks: {flat(failed)}")

    if specs:
        # A derived headline, because the per-horizon list is a wall of numbers: without this sentence the
        # chunk that answers "how much of an oil shock reaches the states" ranks below the prose that says
        # the same thing, which is what the first measurement showed.
        excluding = [spec for spec in specs if spec.get("ci_low", 0) > 0 or spec.get("ci_high", 0) < 0]
        peak = max(specs, key=lambda spec: spec["coefficient"])
        parts = [f"The largest response is {signed(peak['coefficient'])} "
                 f"({peak.get('outcome') or peak.get('coefficient_name')})"]
        if excluding:
            parts.append(
                "the specifications whose 95 % interval excludes zero are "
                + "; ".join(f"{spec.get('outcome')} = {signed(spec['coefficient'])} "
                            f"{interval(spec['ci_low'], spec['ci_high'])}" for spec in excluding)
            )
        else:
            parts.append("no specification's 95 % interval excludes zero")
        lines += ["", f"Headline: {'. '.join(parts)}."]
        lines.append(f"{len(specs)} specification(s) published at vintage {vintage}:")
        for spec in specs:
            lines.append(
                f"- {spec.get('outcome')}: {spec.get('coefficient_name')} = "
                f"{signed(spec['coefficient'])}, 95% interval "
                f"{interval(spec['ci_low'], spec['ci_high'])}, p = {spec['p_value']:.4f}, "
                f"n = {spec['n_obs']:,}, {spec.get('first_month')} to {spec.get('last_month')} "
                f"({spec.get('estimator')})."
            )
        if any(spec.get("formula") for spec in specs):
            lines.append(f"Formula: {specs[0].get('formula')}. Covariance: {specs[0].get('covariance')}.")

    if result.get("result_outcome"):
        lines.append(f"The design's result measures: {result['result_outcome']}.")
    if result.get("cards_that_carry_no_number") is not None:
        lines.append(
            f"Cards that carry no number because of this design-level result: "
            f"{result['cards_that_carry_no_number']}."
        )
    robustness = result.get("robustness") or {}
    support = robustness.get("support") or {}
    if support:
        lines += [
            "",
            f"Stage 7 robustness for this design: {support.get('n_positive')} of {support.get('n')} "
            f"specifications positive, {support.get('n_negative')} negative, "
            f"{support.get('n_positive_ci')} with an interval above zero and "
            f"{support.get('n_negative_ci')} below it; {robustness.get('sign_flip_levels')} axis levels "
            f"flip against the preferred specification.",
        ]
        sensitivity = robustness.get("sensitivity") or {}
        oster = sensitivity.get("oster") or {}
        if oster:
            lines.append(
                f"Oster delta on the preferred specification: {oster.get('delta'):.4f} "
                f"(interpretable: {str(oster.get('delta_interpretable')).lower()}). "
                f"{flat(oster.get('interpretation') or '')}".strip()
            )
        # The placebo and leave-one-out blocks are full row sets; they belong to the robustness artifact and
        # docs/robustness.md. Serialising them here split a single design result into twelve chunks and
        # pushed the published numbers out of the top five for their own questions.
        for key, label in (("in_time_placebo", "In-time placebo"), ("leave_one_state_out", "Leave-one-state-out")):
            block = sensitivity.get(key) or {}
            if isinstance(block, dict) and block:
                summary = {k: v for k, v in block.items()
                           if not isinstance(v, (list, dict))}
                if summary:
                    lines.append(f"{label}: " + ", ".join(f"{k} = {v}" for k, v in summary.items()) + ".")

    if result.get("why"):
        lines += ["", f"Why: {flat(result['why'])}"]
    if result.get("next_step"):
        lines.append(f"Next step: {flat(result['next_step'])}")
    if result.get("artifacts"):
        lines.append(f"Artifacts: {json.dumps(result['artifacts'], ensure_ascii=False)}")

    return "\n".join(line for line in lines if line)


def build_results(corpus: Corpus) -> None:
    index_path = REPO_ROOT / corpus.spec["input"]["registry_index"]
    results = corpus.index.get("published_results") or {}
    if not results:
        raise BuildError("registry/dags/index.json carries no published_results")
    estimates_path = newest_artifact(REPO_ROOT / corpus.spec["input"]["estimates_root"],
                                     corpus.spec["input"]["estimates_artifact"])
    estimates = read_json(estimates_path)
    corpus.register_source(estimates_path, "estimates")
    by_design: dict[str, list[dict]] = {}
    for row in estimates.get("specifications") or []:
        by_design.setdefault(row["design"], []).append(row)
    index_designs = {row["id"]: row for row in corpus.index.get("designs") or []}
    for design_id in sorted(results):
        corpus.add(
            chunk_id=f"result:{design_id}",
            doc_type="published_result",
            title=f"Published result — Design {design_id}",
            text=result_text(design_id, results[design_id], corpus.vintage, by_design.get(design_id, []),
                             index_designs.get(design_id)),
            source_path=index_path,
            anchor=f"published_results.{design_id}",
            metadata={
                "design_id": design_id,
                "status": results[design_id].get("status"),
                "result_is_card_level": results[design_id].get("result_is_card_level"),
                "n_specifications": len(results[design_id].get("specifications") or []),
            },
        )


# ---------------------------------------------------------------------------------------------
# Family: narrative documents
# ---------------------------------------------------------------------------------------------
def split_paragraphs(text: str) -> list[str]:
    return [block.strip() for block in re.split(r"\n\s*\n", text) if block.strip()]


def atoms(text: str, budget: int) -> list[str]:
    """Paragraphs, with an over-long paragraph broken on sentence ends and then hard-wrapped."""
    out: list[str] = []
    for block in split_paragraphs(text):
        if re.fullmatch(r"[-*_]{3,}", block.strip()):
            continue  # markdown horizontal rule: no content, and a 3-character chunk is not a chunk
        if len(block) <= budget:
            out.append(block)
            continue
        current = ""
        for sentence in re.split(r"(?<=[.!?])\s+", block):
            candidate = f"{current} {sentence}".strip() if current else sentence
            if len(candidate) <= budget:
                current = candidate
                continue
            if current:
                out.append(current)
            while len(sentence) > budget:
                # Break on a word boundary, never mid-word: a hard character cut leaves " above." as a
                # 7-character unit, which then ships as a chunk below the floor.
                cut = sentence.rfind(" ", 0, budget)
                cut = budget if cut <= 0 else cut
                out.append(sentence[:cut])
                sentence = sentence[cut:].lstrip()
            current = sentence
        if current:
            out.append(current)
    # A short fragment glued to its predecessor is a better retrieval unit than a fragment on its own, and
    # the small overflow stays inside max_chars because the packing budget already leaves room for it. A
    # short fragment with nothing before it ("After all of the above, four things survive:") is a lead-in:
    # it belongs with what it introduces, so it merges *forward* instead of becoming a 44-character chunk.
    if len(out) > 1 and len(out[0]) < 80 and len(out[0]) + 2 + len(out[1]) <= budget + 80:
        out[1] = f"{out[0]}\n\n{out[1]}"
        out = out[1:]
    merged: list[str] = []
    for piece in out:
        if merged and len(piece) < 80 and len(merged[-1]) + 1 + len(piece) <= budget + 80:
            merged[-1] = f"{merged[-1]} {piece}"
        else:
            merged.append(piece)
    return merged


def _pack(units: list[str], target: int) -> list[str]:
    pieces: list[str] = []
    current = ""
    for unit in units:
        candidate = f"{current}\n\n{unit}" if current else unit
        if len(candidate) <= target:
            current = candidate
            continue
        if current:
            pieces.append(current)
        current = unit
    if current:
        pieces.append(current)
    return pieces


def split_to_budget(text: str, budget: int, min_tail: int = 0) -> list[str]:
    """Split into *balanced* parts, so the last part is not a 25-character tail.

    Greedy packing at the budget produces a long run of full chunks and one scrap at the end; the scrap is
    below the minimum and is a poor retrieval unit, and merging it back breaks the budget. So the target is
    `ceil(len / n)`, which spreads the same text over the same number of parts without a scrap. When the
    tail still lands under `min_tail` (a dense table followed by one short sentence does this), the packer
    adds a bin and retries rather than shipping the scrap or overflowing the budget.
    """
    if len(text) <= budget:
        return [text]
    units = atoms(text, budget)
    base_bins = max(2, -(-len(text) // budget))
    pieces: list[str] = []
    # Try progressively *larger* targets: a short last atom joins its predecessor only when the target grows,
    # and the budget is the cap, so the final candidate is greedy packing at the budget itself.
    candidates = [max(1, -(-len(text) // max(2, base_bins + extra))) for extra in (0, -1, -2, -3)]
    candidates.append(budget)
    for target in dict.fromkeys(min(c, budget) for c in candidates):
        pieces = _pack(units, target)
        while len(pieces) > 1 and len(pieces[-1]) < min_tail \
                and len(pieces[-2]) + len(pieces[-1]) + 2 <= budget:
            pieces[-2] = f"{pieces[-2]}\n\n{pieces[-1]}"
            pieces = pieces[:-1]
        if not min_tail or len(pieces[-1]) >= min_tail or len(pieces) == 1:
            return pieces
    return pieces


def markdown_chunks(text: str, max_chars: int, min_chars: int) -> list[tuple[str, str, str, str]]:
    """(anchor, title, body, header) per H2 section, with the H1 kept as context.

    Sections are returned whole; the budget split is `Corpus.add`'s job, so there is exactly one splitting
    rule in this builder. The header is returned separately so it can prefix every part without being
    counted as content. A section too short to stand alone is merged into the previous one (its heading is
    kept as a bolded lead-in) rather than shipped as a header with no body.
    """
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = text.split("\n")
    h1 = ""
    sections: list[tuple[str, str, list[str]]] = []
    current_title = None
    current_lines: list[str] = []
    used: dict[str, int] = {}

    def flush() -> None:
        nonlocal current_title, current_lines
        if current_title is not None:
            sections.append((current_title, "", current_lines))
        current_title, current_lines = None, []

    for line in lines:
        if line.startswith("# ") and not line.startswith("## "):
            h1 = line[2:].strip()
            continue
        if line.startswith("## "):
            flush()
            current_title = line[3:].strip()
            continue
        if current_title is not None:
            current_lines.append(line)
    flush()
    if not sections:
        sections = [("", "", text.split("\n"))]

    out: list[tuple[str, str, str]] = []
    for title, _unused, body_lines in sections:
        body = "\n".join(body_lines).strip()
        number_match = re.match(r"^(\d+)\.\s", title)
        base = f"s{int(number_match.group(1)):02d}" if number_match else slug(title, 48)
        if base in used:
            used[base] += 1
            base = f"{base}-{used[base]}"
        else:
            used[base] = 1
        header = f"{h1}\n\n## {title}".strip() if title else h1
        if len(body) < min_chars and out:
            previous_anchor, previous_title, previous_body, previous_header = out[-1]
            out[-1] = (previous_anchor, previous_title,
                       f"{previous_body}\n\n**{title or h1}**\n\n{body}", previous_header)
            continue
        out.append((base, title or h1, body, header))
    return out


def build_docs(corpus: Corpus) -> None:
    for doc in corpus.spec["input"]["docs"]:
        path = REPO_ROOT / doc
        text = path.read_text(encoding="utf-8")
        stem = path.stem
        for anchor, title, body, header in markdown_chunks(text, corpus.max_chars, corpus.min_chars):
            doc_type = "data_dictionary" if stem == "data-dictionary" else "methodology"
            chunk_title = f"{stem} — {title}" if title else stem
            corpus.add(
                chunk_id=f"doc:{stem}#{anchor}",
                doc_type=doc_type,
                title=chunk_title,
                text=body,
                source_path=path,
                anchor=anchor,
                metadata={"document": doc, "section": title},
                header=header,
            )


# ---------------------------------------------------------------------------------------------
# Families: administration, shocks, events, coverage
# ---------------------------------------------------------------------------------------------
def read_csv(path: Path) -> list[dict]:
    import csv

    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def build_administration(corpus: Corpus) -> None:
    path = REPO_ROOT / corpus.spec["input"]["seeds"]["administration"]
    rows = read_csv(path)
    for row in rows:
        corpus.add(
            chunk_id=f"admin:{row['admin_id']}",
            doc_type="administration",
            title=f"Administration {row['admin_id']} — {row['president']} ({row['party']})",
            text=(
                f"Administration {row['admin_id']}: {row['president']}, party {row['party']}, "
                f"from {row['start_date']} to {row['end_date']}, {row['n_terms']} term(s). "
                f"Note: {flat(row.get('notes') or 'none')}. "
                f"The dates are the decided boundaries of the administration spine "
                f"(dbt/seeds/raw_administration.csv); the Yar'Adua to Jonathan boundary is a single decided "
                f"date and is not re-litigated by the corpus."
            ),
            source_path=path,
            anchor=f"admin_id={row['admin_id']}",
            metadata={
                "admin_id": int(row["admin_id"]),
                "president": row["president"],
                "party": row["party"],
                "start_date": row["start_date"],
                "end_date": row["end_date"],
                "n_terms": int(row["n_terms"]),
            },
        )


def build_shocks(corpus: Corpus) -> None:
    path = REPO_ROOT / corpus.spec["input"]["seeds"]["shock_bands"]
    rows = read_csv(path)
    for row in rows:
        corpus.add(
            chunk_id=f"shock:{row['shock_id']}",
            doc_type="shock",
            title=f"Shock band {row['shock_id']} — {row['label']}",
            text=(
                f"Annotated shock band {row['shock_id']}: {row['label']}, {row['start_date']} to "
                f"{row['end_date']}. {flat(row.get('note') or 'No note.')} The band is a declared annotation on "
                f"the charts and in the analysis, not a break detected by a test."
            ),
            source_path=path,
            anchor=f"shock_id={row['shock_id']}",
            metadata={
                "shock_id": int(row["shock_id"]),
                "label": row["label"],
                "start_date": row["start_date"],
                "end_date": row["end_date"],
            },
        )


def build_events(corpus: Corpus) -> None:
    path = newest_artifact(REPO_ROOT / corpus.spec["input"]["events_root"],
                           corpus.spec["input"]["events_artifact"])
    document = read_json(path)
    if document.get("vintage") != corpus.vintage:
        raise BuildError(
            f"{rel(path)}: artifact vintage {document.get('vintage')!r} does not equal the registry vintage "
            f"{corpus.vintage!r}"
        )
    verdicts = document.get("verdicts") or []
    windows = document.get("windows") or {}
    for event in document.get("events") or []:
        cells = [v for v in verdicts if v.get("event") == event["id"]]
        lines = [
            f"Transition event {event['id']}: {event['label']} on {event['date']} "
            f"(tenure stratum {event['tenure_stratum']}, transition month {event['transition_month']}).",
            f"Pre-window: {event['pre_months_available']} months available before the transition "
            f"(the design uses {windows.get('pre_months')} pre-months). Post window ends "
            f"{event['post_window_end']}"
            f"{', truncated by the next transition or the archive end' if event.get('truncated_by_next_transition') else ''}.",
            f"Label: {event['label']}. Term id: {event['term_id']}.",
        ]
        if event.get("note"):
            lines.append(flat(event["note"]))
        lines += [
            "",
            "Outcome cells, each with the checks that decided whether the shift is interpretable:",
        ]
        for cell in cells:
            lines.append(
                f"- {cell['outcome']}: status {cell['status']}; proportional change "
                f"{signed(cell['place'])}, placebo p = {cell['placebo_p']:.4f}"
                + (f", pre-trend placebo {signed(cell['pre_trend'])}" if cell.get("pre_trend") is not None
                   else ", pre-trend placebo unavailable")
                + (f" — {flat(cell['why'])}" if cell.get("why") else ".")
            )
        lines += [
            "",
            "This is a within-series timing comparison, not a causal effect of a tenure, a party or a "
            "president: the design has no counterfactual. Inference is exhaustive placebo assignment over "
            f"{(document.get('placebo') or {}).get('eligible_months', 'the eligible')} eligible months "
            f"(deterministic: {str((document.get('placebo') or {}).get('deterministic')).lower()}), with the "
            f"minimum attainable p-value set by the placebo count rather than by a model.",
        ]
        corpus.add(
            chunk_id=f"event:{event['id']}",
            doc_type="event_study",
            title=f"Transition event {event['id']} — {event['label']}",
            text="\n".join(lines),
            source_path=path,
            anchor=f"events.{event['id']}",
            metadata={
                "event_id": event["id"],
                "date": event["date"],
                "tenure_stratum": event["tenure_stratum"],
                "cells": {cell["outcome"]: cell["status"] for cell in cells},
            },
        )

    not_claimed = document.get("not_claimed") or []
    corpus.add(
        chunk_id="event:scope",
        doc_type="event_study",
        title="Transition event study — what it does not claim",
        text=(
            "What the transition event study does not claim:\n"
            + "\n".join(f"- {item}" for item in not_claimed)
            + f"\n\nThe party split is published as description with no test "
              f"(no_test_computed: {str((document.get('party_split') or {}).get('no_test_computed')).lower()}), "
              f"because two events against two events carries no sampling distribution."
        ),
        source_path=path,
        anchor="not_claimed",
        metadata={"event_id": None, "cells": {}},
    )


def build_registry_coverage(corpus: Corpus) -> None:
    path = REPO_ROOT / corpus.spec["input"]["registry_index"]
    counts = (corpus.index.get("registry") or {}).get("card_estimate_counts")
    if not counts:
        raise BuildError(f"{rel(path)}: carries no registry.card_estimate_counts — Stage 8's assembly has "
                         "not run, so the corpus cannot state the ratio")
    total = int(counts.get("estimated", 0)) + int(counts.get("not_estimated", 0))
    reasons = counts.get("not_estimated_by_reason") or {}
    reason_text = "; ".join(f"{code} {count}" for code, count in sorted(reasons.items()))
    corpus.add(
        chunk_id="coverage:registry",
        doc_type="coverage",
        title="Registry coverage — how many cards carry a published number",
        text=(
            f"The registry holds {total} model cards: {corpus.index.get('counts', {}).get('outcomes')} "
            f"outcomes across {corpus.index.get('counts', {}).get('designs')} identification designs. "
            f"{counts.get('estimated')} cards carry a published estimate and "
            f"{counts.get('not_estimated')} carry a reason instead, from a closed set: {reason_text}. "
            f"A card with no number is not a null result — it names why no specification was published for "
            f"that (outcome, design) pair. The design-level results (the national FAAC channel and Design "
            f"C's non-run) sit on the index, once, because they are statements about the channel a design "
            f"rests on rather than about any single card's outcome."
        ),
        source_path=path,
        anchor="registry.card_estimate_counts",
        metadata={"estimated": counts.get("estimated"), "not_estimated": counts.get("not_estimated"),
                  "not_estimated_by_reason": reasons},
    )


def build_scope(corpus: Corpus) -> None:
    contract = corpus.spec.get("answer_contract") or {}
    order = contract.get("order") or []
    corpus.add(
        chunk_id="scope:answer",
        doc_type="scope",
        title="What this corpus can and cannot answer",
        text=(
            f"What this corpus can answer: {flat(contract.get('scope', 'not declared'))} "
            f"An answer is assembled in this order: {', '.join(order)}. "
            f"Post-check: {flat(contract.get('post_check', 'not declared'))} "
            f"Refusal template: {flat(contract.get('refusal_template', 'not declared'))} "
            f"This paragraph is the corpus's own scope statement, copied from analysis/specs/rag.yml so the "
            f"scope a refusal cites is the scope the layer declared."
        ),
        source_path=SPEC_PATH,
        anchor="answer_contract",
        metadata={"order": order},
    )


def build_coverage(corpus: Corpus) -> None:
    path = newest_artifact(REPO_ROOT / corpus.spec["input"]["quality_root"],
                           corpus.spec["input"]["quality_artifact"])
    document = read_json(path)
    counts = document.get("counts") or {}
    window = document.get("study_window") or {}
    corpus.add(
        chunk_id="coverage:quality",
        doc_type="coverage",
        title="Data coverage — the Stage 3 quality gate result",
        text=(
            f"Stage 3 gated {document.get('n_series_gated')} series at report vintage "
            f"{document.get('report_vintage')}: {counts.get('ok')} ok, {counts.get('flagged')} flagged and "
            f"{counts.get('empty')} empty.\n\n"
            f"Study window: starts {window.get('start')}, ends {window.get('end') or 'the latest observation'}. "
            f"{window.get('reason') or ''}\n\n"
            f"Thresholds: gap gate flags more than {document.get('thresholds', {}).get('gap_max_months')} "
            f"missing months; the spike gate flags a move beyond "
            f"{document.get('thresholds', {}).get('spike_pct')} percent (or "
            f"{document.get('thresholds', {}).get('spike_points')} percentage points for series already in "
            f"percent); the revision tolerance is "
            f"{document.get('thresholds', {}).get('revision_tolerance_pct')} percent.\n\n"
            f"A flag is not a deletion: the series remains in the base with its status travelling on it. "
            f"The share of the monthly spine that is actually observed, and what each flag means, are in "
            f"docs/limitations.md."
        ),
        source_path=path,
        anchor="counts",
        metadata={
            "report_vintage": document.get("report_vintage"),
            "counts": counts,
            "n_series_gated": document.get("n_series_gated"),
        },
    )


# ---------------------------------------------------------------------------------------------
# Eval set — authored questions, validated against the built corpus
# ---------------------------------------------------------------------------------------------
def build_eval_set(corpus: Corpus, spec: dict) -> dict:
    if not EVAL_SPEC_PATH.exists():
        raise BuildError(f"{rel(EVAL_SPEC_PATH)}: the eval spec is declared but absent")
    authored = yaml.safe_load(EVAL_SPEC_PATH.read_text(encoding="utf-8"))
    chunk_by_id = {chunk["chunk_id"]: chunk for chunk in corpus.chunks}
    questions = authored.get("questions") or []
    if not questions:
        raise BuildError("analysis/specs/rag_eval.yml declares no questions")

    def resolve(reference: str) -> list[str]:
        """A gold ref names a parent; a split parent resolves to the parent *and* all of its parts.

        A split parent keeps the plain id for its first part, so an exact match is not evidence that the
        document was not split — the first attempt at this returned only part 1 and the needle lived in
        part 3, which looked like a wrong needle rather than a wrong resolver.
        """
        parts = sorted(cid for cid in chunk_by_id if cid.startswith(f"{reference}#"))
        if reference in chunk_by_id:
            return [reference, *parts]
        return parts

    seen: set[str] = set()
    rows = []
    for item in questions:
        qid = item["id"]
        if qid in seen:
            raise BuildError(f"{qid}: duplicate eval question id")
        seen.add(qid)
        qtype = item["type"]
        if qtype not in {"answerable", "refusal_with_reason", "out_of_scope"}:
            raise BuildError(f"{qid}: unknown type {qtype!r}")
        gold_refs = item.get("gold") or []
        resolved: list[str] = []
        for reference in gold_refs:
            ids = resolve(reference)
            if not ids:
                raise BuildError(
                    f"{qid}: gold chunk {reference!r} is not in the corpus — an eval set that points at a "
                    "chunk that does not exist measures nothing"
                )
            resolved.extend(ids)
        if qtype == "out_of_scope" and gold_refs:
            raise BuildError(f"{qid}: an out_of_scope question must not name a gold chunk")
        if qtype != "out_of_scope" and not gold_refs:
            raise BuildError(f"{qid}: {qtype} question names no gold chunk")
        needles = item.get("must_contain") or []
        if qtype != "out_of_scope" and not needles:
            raise BuildError(f"{qid}: no must_contain needle — the answer-shape check would have nothing to check")
        for needle in needles:
            if not any(needle in chunk_by_id[g]["text"] for g in resolved):
                raise BuildError(
                    f"{qid}: needle {needle!r} does not appear in its gold chunk(s) {resolved} — the needle "
                    "is wrong or the corpus changed, and either way the check would fail for the wrong reason"
                )
        if qtype == "refusal_with_reason" and not item.get("refusal_must_cite"):
            raise BuildError(f"{qid}: a refusal must cite the reason chunk")
        rows.append(
            {
                "id": qid,
                "type": qtype,
                "question": item["question"],
                "gold_refs": gold_refs,
                "gold_chunks": resolved,
                "must_contain": needles,
                "refusal_must_cite": item.get("refusal_must_cite"),
                "reference_answer": item.get("reference_answer", ""),
                "notes": item.get("notes"),
            }
        )

    return {
        "schema_version": SCHEMA_VERSION,
        "layer": "RAG evaluation set (retrieval-gated; generation metrics declared, not measured)",
        "vintage": corpus.vintage,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "generator": {"script": rel(Path(__file__)), "spec": rel(EVAL_SPEC_PATH),
                      "git_sha": git_sha()},
        "corpus": rel(REPO_ROOT / spec["output"]["root"] / corpus.vintage / spec["output"]["corpus"]),
        "ragas": {
            "status": "not_run",
            "why": "RAGAS metrics (faithfulness, answer relevance, context precision/recall) need a generation "
                   "step and a judge model. No LLM key is configured in this repository, so the generation "
                   "metrics are declared and skipped; the retrieval half is measured offline in "
                   "retrieval_eval.json and is what verifies this stage. `reference_answer` is carried per "
                   "question so a RAGAS run can be wired the day a key exists.",
            "metadata": ["question", "contexts", "answer", "ground_truth"],
        },
        "counts": {
            "questions": len(rows),
            "answerable": sum(1 for r in rows if r["type"] == "answerable"),
            "refusal_with_reason": sum(1 for r in rows if r["type"] == "refusal_with_reason"),
            "out_of_scope": sum(1 for r in rows if r["type"] == "out_of_scope"),
        },
        "questions": rows,
    }


# ---------------------------------------------------------------------------------------------
# Embeddings
# ---------------------------------------------------------------------------------------------
def embed(corpus_doc: dict, eval_doc: dict, spec: dict, out_dir: Path) -> dict:
    try:
        import numpy as np
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:  # pragma: no cover - depends on the interpreter
        raise BuildError(
            "embedding requested but sentence-transformers/numpy is not importable in this interpreter. "
            "Use the dedicated env: /c/conda-envs/drlca-rag/python.exe scripts/build_rag_corpus.py --embed"
        ) from exc

    model_name = spec["embedding"]["model"]
    model = SentenceTransformer(model_name, device="cpu")
    dim = int(spec["embedding"]["dim"])
    chunk_texts = [chunk["text"] for chunk in corpus_doc["chunks"]]
    chunk_ids = [chunk["chunk_id"] for chunk in corpus_doc["chunks"]]
    question_ids = [row["id"] for row in eval_doc["questions"]]
    question_texts = [row["question"] for row in eval_doc["questions"]]

    chunk_vectors = model.encode(chunk_texts, normalize_embeddings=True, batch_size=32,
                                 show_progress_bar=False).astype("float32")
    query_vectors = model.encode(question_texts, normalize_embeddings=True, batch_size=32,
                                 show_progress_bar=False).astype("float32")
    if chunk_vectors.shape[1] != dim:
        raise BuildError(f"{model_name}: produced {chunk_vectors.shape[1]} dims, spec declares {dim}")

    # The check that makes the budget real: the model's own tokenizer, not a char heuristic. A chunk over the
    # limit is encoded with its tail dropped, and retrieval then searches a document the author cannot see.
    limit = int(getattr(model, "max_seq_length", 0) or 0)
    declared = int(spec["embedding"].get("max_tokens", 0) or 0)
    if limit and declared and limit != declared:
        raise BuildError(f"{model_name}: model limit {limit} tokens, spec declares {declared}")
    token_lengths = [len(ids) for ids in model.tokenizer(chunk_texts, add_special_tokens=True)["input_ids"]]
    longest = max(token_lengths)
    if limit and longest > limit:
        worst = chunk_ids[token_lengths.index(longest)]
        raise BuildError(
            f"{worst}: {longest} tokens exceeds {model_name}'s {limit}-token limit — the tail would be "
            "truncated at encode time and be unreachable by retrieval"
        )

    path = out_dir / spec["output"]["embeddings"]
    np.savez_compressed(
        path,
        chunk_ids=np.array(chunk_ids, dtype=object),
        chunk_vectors=chunk_vectors,
        question_ids=np.array(question_ids, dtype=object),
        query_vectors=query_vectors,
    )
    return {
        "status": "built",
        "path": rel(path),
        "model": model_name,
        "dim": dim,
        "normalised": True,
        "metric": "cosine",
        "sha256": sha256_of(path),
        "bytes": path.stat().st_size,
        "n_chunk_vectors": int(chunk_vectors.shape[0]),
        "n_query_vectors": int(query_vectors.shape[0]),
        "library": {
            "sentence-transformers": _version("sentence_transformers"),
            "torch": _version("torch"),
            "numpy": _version("numpy"),
        },
    }


def _version(module: str) -> str:
    try:
        return __import__(module).__version__
    except Exception:  # pragma: no cover - reported, never raised
        return "unknown"


# ---------------------------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------------------------
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the Stage 8 retrieval corpus.")
    parser.add_argument("--embed", action="store_true",
                        help="also encode the chunks and questions (needs sentence-transformers)")
    parser.add_argument("--allow-embedding-drop", action="store_true",
                        help="permit a rebuild that discards vectors the committed corpus already has")
    args = parser.parse_args(argv)

    spec = yaml.safe_load(SPEC_PATH.read_text(encoding="utf-8"))
    index_path = REPO_ROOT / spec["input"]["registry_index"]
    index = read_json(index_path)
    corpus = Corpus(spec, index)
    corpus.register_source(index_path, "registry_index")

    build_cards(corpus)
    build_results(corpus)
    build_docs(corpus)
    build_administration(corpus)
    build_shocks(corpus)
    build_events(corpus)
    build_coverage(corpus)
    build_registry_coverage(corpus)
    build_scope(corpus)
    corpus.chunks.sort(key=lambda chunk: (chunk["doc_type"], chunk["chunk_id"]))

    estimates_path = newest_artifact(REPO_ROOT / spec["input"]["estimates_root"],
                                     spec["input"]["estimates_artifact"])
    if read_json(estimates_path).get("vintage") != corpus.vintage:
        raise BuildError(f"{rel(estimates_path)}: artifact vintage disagrees with the registry vintage")

    eval_doc = build_eval_set(corpus, spec)

    out_dir = REPO_ROOT / spec["output"]["root"] / corpus.vintage
    out_dir.mkdir(parents=True, exist_ok=True)

    # A plain build on a machine without torch would overwrite a corpus that has vectors with one that does
    # not, and every published retrieval number would then describe a corpus nobody can reproduce. That is a
    # deliberate stop, not a warning: verify.sh calls this only from the env that can embed.
    existing = out_dir / spec["output"]["corpus"]
    if existing.exists() and not args.embed and not args.allow_embedding_drop:
        previous = read_json(existing).get("embedding") or {}
        if previous.get("status") == "built":
            raise BuildError(
                f"{rel(existing)} already carries built vectors ({previous.get('model')}); this interpreter "
                "would rebuild the text and drop them, leaving the published retrieval numbers describing a "
                "corpus nobody can reproduce. Run --embed with an interpreter that has "
                "sentence-transformers (see docs/rag.md), or pass --allow-embedding-drop to do it anyway"
            )

    by_type: dict[str, int] = {}
    for chunk in corpus.chunks:
        by_type[chunk["doc_type"]] = by_type.get(chunk["doc_type"], 0) + 1

    corpus_doc = {
        "schema_version": SCHEMA_VERSION,
        "layer": "retrieval corpus (one card per model card, plus the results, the tables and the narrative)",
        "vintage": corpus.vintage,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "generator": {"script": rel(Path(__file__)), "spec": rel(SPEC_PATH), "git_sha": git_sha()},
        "registry": {
            "index": rel(index_path),
            "index_vintage": index.get("vintage_date"),
            "card_estimate_counts": (index.get("registry") or {}).get("card_estimate_counts"),
        },
        "chunking": spec["chunking"],
        "retrieval": spec["retrieval"],
        "embedding": {"status": "not_built", "model": spec["embedding"]["model"],
                      "dim": spec["embedding"]["dim"]},
        "source_hash_rule": "sha256 of each source with CRLF normalised to LF — the same bytes the git "
                            "index stores under .gitattributes (eol=lf), so a Windows checkout and the "
                            "Linux runner hash identically",
        "sources": corpus.source_manifest(),
        "counts": {
            "chunks": len(corpus.chunks),
            "by_doc_type": by_type,
            "chars": {
                "total": sum(c["chars"] for c in corpus.chunks),
                "max": max(c["chars"] for c in corpus.chunks),
                "min": min(c["chars"] for c in corpus.chunks),
            },
        },
        "chunks": corpus.chunks,
    }

    if args.embed:
        corpus_doc["embedding"] = embed(corpus_doc, eval_doc, spec, out_dir)
        corpus_doc["embedding"]["questions_embedded"] = eval_doc["counts"]["questions"]

    corpus_path = out_dir / spec["output"]["corpus"]
    corpus_path.write_text(json.dumps(corpus_doc, indent=1, ensure_ascii=False) + "\n",
                           encoding="utf-8", newline="\n")
    eval_path = out_dir / spec["output"]["eval_set"]
    eval_path.write_text(json.dumps(eval_doc, indent=1, ensure_ascii=False) + "\n",
                         encoding="utf-8", newline="\n")

    print(f"corpus    : {rel(corpus_path)} — {len(corpus.chunks)} chunks ({by_type})")
    print(f"eval set  : {rel(eval_path)} — {eval_doc['counts']}")
    print(f"embedding : {corpus_doc['embedding'].get('status')}"
          + (f" ({corpus_doc['embedding']['model']}, {corpus_doc['embedding']['n_chunk_vectors']} vectors)"
             if corpus_doc["embedding"].get("status") == "built" else ""))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BuildError as exc:
        print(f"BUILD FAILED — {exc}", file=sys.stderr)
        raise SystemExit(2)
