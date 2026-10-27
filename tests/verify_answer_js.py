"""Verify the site's JavaScript answer layer against `answer_eval.json`.

The rule the specification sets: **the JS is accepted only if it reproduces the artifact's measured answers**,
not if it merely answers. So this file builds the site, runs `site/assets/answer.mjs` under node over the same
38 questions the Python layer was measured on, and compares every field a reader can see — status, intent,
shape, rule, citation, the passages used, the answer text and the plain reading — plus the aggregate the
artifact publishes (36 answered, 2 declined, 8 estimate / 14 reason / 14 fact).

It also checks the claim that makes the second implementation safe: the JS carries no rule of its own. The gate
spec, the contract and the corpus are read from `site/dist/data/`, which the build emits from the same YAML the
Python layer reads.

Run:
    python tests/verify_answer_js.py
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DIST = REPO_ROOT / "site" / "dist"
PROBE = REPO_ROOT / ".probe"
RUNNER = PROBE / "answer_js_runner.mjs"
RESULT = PROBE / "answer_js_result.json"
NUMBER = re.compile(r"[−+\-]?\d[\d,]*(?:\.\d+)?")

RUNNER_SOURCE = """\
import fs from "node:fs";
import { loadLayer } from "../site/assets/answer.mjs";

const load = (path) => JSON.parse(fs.readFileSync(path, "utf8"));
const layer = loadLayer({
  gate: load("site/dist/data/gate.json"),
  contract: load("site/dist/data/contract.json"),
  corpus: load("site/dist/data/corpus.json"),
});
const questions = load(process.argv[2]);
const rows = questions.map((row) => {
  const answer = layer.answer(row.question);
  return {
    id: row.id,
    intent: answer.intent,
    rule_id: answer.rule_id,
    route: answer.route,
    status: answer.status,
    shape: answer.shape,
    refusal_code: answer.refusal_code,
    citation: answer.citation,
    chunks_used: answer.chunks_used,
    check: answer.check,
    text: answer.text,
    plain_text: (answer.plain || {}).text || "",
  };
});
fs.writeFileSync(process.argv[3], JSON.stringify(rows));
"""


def main() -> int:
    failures: list[str] = []
    if shutil.which("node") is None:
        print("FAILED — node is not on PATH, so the JavaScript answer layer cannot be run")
        return 1

    build = subprocess.run([sys.executable, str(REPO_ROOT / "site" / "build.py")],
                           cwd=REPO_ROOT, capture_output=True, text=True)
    if build.returncode != 0:
        print("FAILED — the site build did not complete:")
        print(build.stdout[-2000:] + build.stderr[-2000:])
        return 1

    index = json.loads((REPO_ROOT / "registry" / "dags" / "index.json").read_text(encoding="utf-8"))
    artifact = json.loads((REPO_ROOT / "registry" / "rag" / index["vintage_date"] / "answer_eval.json")
                          .read_text(encoding="utf-8"))

    PROBE.mkdir(parents=True, exist_ok=True)
    RUNNER.write_text(RUNNER_SOURCE, encoding="utf-8", newline="\n")
    questions = PROBE / "answer_js_questions.json"
    questions.write_text(json.dumps([{"id": row["id"], "question": row["question"]}
                                     for row in artifact["questions"]], ensure_ascii=False),
                         encoding="utf-8", newline="\n")
    run = subprocess.run(["node", str(RUNNER), str(questions), str(RESULT)],
                         cwd=REPO_ROOT, capture_output=True, text=True)
    if run.returncode != 0:
        print("FAILED — the JavaScript layer did not run:")
        print(run.stdout[-2000:] + run.stderr[-2000:])
        return 1

    produced = {row["id"]: row for row in json.loads(RESULT.read_text(encoding="utf-8"))}
    compared = 0
    for expected in artifact["questions"]:
        got = produced.get(expected["id"])
        if got is None:
            fail = f"{expected['id']}: the JavaScript layer produced no answer"
            failures.append(fail)
            continue
        for field, want in (("intent", expected["intent"]), ("rule_id", expected["rule_id"]),
                            ("route", expected["route"]), ("status", expected["status"]),
                            ("shape", expected["shape"]), ("refusal_code", expected["refusal_code"]),
                            ("citation", expected["citation"]), ("chunks_used", expected["chunks_used"]),
                            ("check", expected["check"]), ("text", expected["text"]),
                            ("plain_text", (expected.get("plain") or {}).get("text") or "")):
            if got[field] != want:
                failures.append(f"{expected['id']}: {field} differs from the artifact — "
                                f"the JS answer has drifted from the measured one")
        # The needle set is compared as a set, not required wholesale: one needle in the published set is
        # missing from the Python layer's own answer, and that miss is published in the artifact rather than
        # fixed by widening the check. The JS layer has to reproduce the artifact's answer, miss included.
        needles = expected.get("needles") or {}
        for needle in needles.get("satisfied") or []:
            if needle not in got["text"]:
                failures.append(f"{expected['id']}: needle {needle!r} is satisfied by the artifact's answer and "
                                f"not by the JS answer")
        js_missing = [needle for needle in needles.get("required") or [] if needle not in got["text"]]
        if js_missing != list(needles.get("missing") or []):
            failures.append(f"{expected['id']}: the JS answer misses {js_missing}, the artifact misses "
                            f"{needles.get('missing')}")
        # A number the artifact's answer does not quote must not appear in the JS one either: this is the
        # "numbers borrowed from another card" failure, checked on the second implementation too.
        quoted = {n.replace(",", "") for n in NUMBER.findall(got["text"].split("**Citation:**")[0])}
        allowed = {n.replace(",", "") for n in NUMBER.findall(expected["text"].split("**Citation:**")[0])}
        for number in sorted(quoted - allowed):
            failures.append(f"{expected['id']}: the JS answer quotes {number}, which the measured answer does not")
        compared += 1

    rows = list(produced.values())
    answered = [row for row in rows if row["status"] == "answered"]
    sets = artifact["sets"]["all"]
    if len(rows) != sets["n"]:
        failures.append(f"the JS layer answered {len(rows)} questions, the artifact measured {sets['n']}")
    if len(answered) != sets["answered"]:
        failures.append(f"the JS layer answered {len(answered)}, the artifact {sets['answered']}")
    shapes = {}
    for row in answered:
        shapes[row["shape"]] = shapes.get(row["shape"], 0) + 1
    if shapes != {name: count for name, count in sets["shapes"].items() if count}:
        failures.append(f"the JS layer's shapes {shapes} are not the artifact's {sets['shapes']}")
    declined = sum(1 for row in rows if row["status"] == "declined")
    if declined != sets["declined"]:
        failures.append(f"the JS layer declined {declined}, the artifact {sets['declined']}")

    # The second implementation must not carry the answers: no rule turned into a lookup table.
    source = (REPO_ROOT / "site" / "assets" / "answer.mjs").read_text(encoding="utf-8")
    for forbidden in ("answer_eval.json", "fetch(", "http://", "https://", "sqlite", "duckdb"):
        if forbidden in source:
            failures.append(f"site/assets/answer.mjs contains {forbidden!r} — the layer reads the emitted specs "
                            f"and nothing else")
    if re.search(r"[−+\-]\d\.\d{3,}", source):
        failures.append("site/assets/answer.mjs carries a coefficient-shaped literal")

    for path in (RUNNER, RESULT, questions):
        if path.exists():
            path.unlink()

    if failures:
        print(f"FAILED — {len(failures)} problem(s):")
        for problem in failures[:40]:
            print(f"  - {problem}")
        if len(failures) > 40:
            print(f"  … and {len(failures) - 40} more")
        return 1

    print(f"reproduced    : {compared} of {len(artifact['questions'])} measured answers, field for field "
          f"(status, shape, rule, citation, passages, text, plain reading)")
    print(f"aggregate     : {len(answered)} answered in {', '.join(f'{k} {v}' for k, v in sorted(shapes.items()))}; "
          f"{declined} declined — the artifact's own counts")
    print("no second copy: the JS reads the emitted gate rules, contract and corpus, and carries no answer text")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
