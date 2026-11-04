# Agentic workflow — models, agents, and when to fan out

**Status:** operational change, 2026-11-04. No registry artifact, R stage, schema, or hash contract
was touched. The registry stays frozen at vintage 2026-11-01; this document describes *how work is
done*, not what was estimated.

**Scope:** the OpenCode harness on this machine — which model does which job, what each subagent is
allowed to touch, and the one rule that matters most: when to run agents in parallel and when that
is merely expensive.

---

## 1. What the Go plan actually gives you

OpenCode Go is a $10/month subscription, not a metered API. The binding constraint is **not** a
request count, it is a **monthly dollar allowance per model**: the 5-hour window is 20 % of that
model's monthly limit, the week is 50 %, the month is 100 %. Two consequences follow, and they
drive everything below.

1. A cheap model with a large allowance is effectively unlimited; a frontier model with a $15/month
   allowance is a scarce resource even though its token price looks reasonable.
2. Routing is an allowance problem, not just a quality problem. Running every step on the best model
   exhausts the best model by mid-morning.

| Model | Monthly limit | ~Requests / 5 h | Role |
|---|---:|---:|---|
| **DeepSeek V4.1 Flash** | **$100** | 43,330 | primary: planning, building, analysis, writing |
| **GLM-5.3-Flash** | **$60** | 6,320 | second lane: review, and builds when a second family is wanted |
| **Muse Spark 1.3 Contributor** | **$60** | 45,300 | volume lane, public work only (§3) |
| GLM-5.3 | $15 | 220 | escalation only, after two failed verifications |
| Kimi K3.1 Pro | $15 | 147 | escalation only, when a plan keeps going wrong |
| Qwen3.8 Flash | $30 | 5,400 | spare lineage for a third opinion on short context |
| ~~DeepSeek V4 Pro~~ | $15 | 1,050 | retired upstream; superseded by V4.1 Flash |
| ~~Gemini 4 Argon~~ | $30 | 440 | redundant: 1M context now ships on $60 models |
| ~~MiMo-V2.6-Flash~~ | $60 | 30,100 | benchmaxxed; weak real coding, injection-prone |
| ~~Claude Haiku 5.5~~ | $15 | 3,850 | alternate reviewer, not the default |

The three bold rows carry the work. Combined they are **$220 of monthly allowance across ~95,000
requests per five hours**, which is why nothing runs out.

Four exclusions worth stating plainly, because they are easy to get wrong:

- **Beam Free is geo-blocked.** Nigeria is on the unavailable list, so the "unlimited free model" is
  not available from here. Do not build a workflow that depends on it.
- **Muse Spark Contributor is available here but trains on your prompts** (`ZDR: no`). Meta's
  restricted-territory list does not include Nigeria, so the block above does not apply to Muse — the
  block is the data term, not the border. Fine for open-source and published work, wrong for client
  data, an embargoed paper, or anything under NDA.
- **Iceman Contributor Free carries the same data term** and no measurable quality edge; skip it.
- **DeepSeek needs `Regions: Global` enabled** in the workspace privacy settings before V4.1 Flash
  works. If it vanishes from `/models`, that setting is the first thing to check.

When a limit is hit, the free models on the `opencode` provider (`deepseek-v4.1-flash-free`,
`glm-5.3-flash-free`) keep the session alive — with the usual caveat that free means the provider's
terms apply.

---

## 2. Model routing

Published third-party runs, not vendor claims, and not something this repo reproduced — sources are
listed at the end. Treat the ordering as a prior to test, not a fact.

| Role | Model | Why this one |
|---|---|---|
| Daily driver — plan, build, analyse, write | `opencode-go/deepseek-v4.1-flash#high` (`#max` for planning and causal work) | It replaced V4 Pro, not the other way round: DeepSeek retired V4 Pro on 14 September 2026 and routed its traffic to V4.1 Flash, saying Flash "comprehensively surpassed V4 Pro across all key metrics". That is true of the **agentic** ones — 74.2 vs 62.7 DeepSWE, 90.6 vs 87.9 Terminal-Bench 2.1 — and of price and speed (about a third of the cost, ~1.8× the throughput). It is **not** true of factual recall: V4 Pro still leads GPQA Diamond (92.4 vs 90.9), HLE text-only (42.7 vs 39.1) and SimpleQA (55.2 vs 42.3). The root `model` in `opencode.json` names it without a variant — V2 keeps the root selection variant-free — so `#high`/`#max` are carried by the agents and commands. |
| Second lane + reviewer | `opencode-go/glm-5.3-flash#high` | The strongest cheap open-weight model: 63.4 DeepSWE, 84.3 Terminal-Bench 2.1, 78.4 Toolathlon, 1.31M context, MIT. Crucially it is a **different family** from DeepSeek, so the review is a real audit rather than a plausibility check. $60 and 6,320 requests per 5 h means it never runs dry. |
| Volume lane (public work only) | `opencode-go/muse-spark-1.3-contributor#high` | $60 allowance and 45,300 requests per 5 h — the largest cheap quota in the lineup — with 1M context and top-tier long-context retrieval (98.5 % MRCR at 256k–512k). Forums rate it well on instruction following and as an implementation subagent. The price is the data term, not the dollar: prompts train the model. |
| Hard-code escalation | `opencode-go/glm-5.3#high` | ~74 % in the same agentic run, MIT weights. Used only after a build has failed twice, via `/deep-build`. |
| Plan escalation | `opencode-go/kimi-k3.1-pro#high` | 67.2 % on Terminal-Bench 4.0, the strongest long-horizon result in the lineup. 147 requests per 5 h is why it is a burst, not a default. |
| Third opinion | `opencode-go/qwen3.8-flash#high` | 91.9 LiveCodeBench v6 and 91.7 GPQA from 6B active parameters, at $30. Short context and single-shot only; use it when two families agree too easily. |

Two things are deliberately **not** in the table. `minimax-m3.1-flash` is not used for verification —
it answered 56 % of AA-Omniscience correctly while attempting nearly every question instead of
declining, the opposite of what an auditor should do. `mimo-v2.6-flash` is not used at all despite its
$60 allowance: an independent hands-on review found it weaker at coding than most recent models,
worse at finding security issues than Qwen3.8 Flash, and the most prompt-injection-susceptible of the
set. A big quota on a benchmaxxed model is not a saving.

**When to leave the Go allowance entirely.** For a genuinely long-horizon run — many files, many
hours, one coherent change — `opencode/claude-opus-5-5` (66.4 % Terminal-Bench 4.0) or
`opencode/gpt-6.1-sol` on pay-as-you-go is the better tool. The rule: escalate to a Zen model when
the task is measured in hours, not when it is merely annoying.

---

## 3. The roster

Seven subagents, each with a model, a step cap, and a permission boundary. Descriptions are the
routing surface — the main agent picks by reading them, so overlapping triggers cost real money.

| Agent | Model | Writes? | Job |
|---|---|---|---|
| `scout` | deepseek-v4.1-flash#high | no | Codebase or web recon with citations. Maps a call path; fetches the primary doc, not the blog post. |
| `planner` | deepseek-v4.1-flash#max | no | Decision, ordered steps, acceptance criteria, risks, out-of-scope. |
| `data-explorer` | deepseek-v4.1-flash#high | no (edit denied) | Profiling, missingness, duplicates, leakage scan. Shell is open for profiling commands; `rm`, `mv`, `pip`, `conda`, `git commit` and `git push` are denied. |
| `causal-analyst` | deepseek-v4.1-flash#max | yes | Estimand, identification, diagnostics, effect with an interval. R and Python. |
| `ml-builder` | deepseek-v4.1-flash#high | yes | Implements the plan. No redesign in flight. `/muse-build` swaps in Muse for volume; `/deep-build` escalates to GLM-5.3. |
| `ship-reviewer` | glm-5.3-flash#high | no | Correctness, claim integrity, ML soundness, ship-readiness. Re-runs cheap checks. Deliberately a different family from the builder. |
| `writer` | deepseek-v4.1-flash#high | yes | Prose grounded in artifacts. Every number points at its source. |

Four rules hold the roster together:

- **One writer per file set.** Two agents editing the same path overwrite each other; the second one
  silently wins. Parallel writing is allowed only when ownership is partitioned by path, and here it
  almost never is.
- **The verifier is a different model family from the builder.** Same-family review is a
  plausibility check, not an audit.
- **The planner cannot edit and the builder cannot re-plan.** The handoff is the plan; if the plan is
  wrong, the turn goes back, it does not get quietly rewritten mid-build.
- **Step caps are real.** 8 for profiling, 12 for review, 25 for a build. A step cap converts a
  runaway loop into a report.

---

## 4. Parallelism: the number and the exceptions

The default fan-out is **three subagents**. The hard cap is **five**. This is not a performance
tuning knob; it is where the cost curve stops being worth it.

- Spawning a subagent costs roughly 20k tokens before it does anything useful (system prompt, tool
  bindings, role framing). One audit traced a subagent spending 160k tokens on work that would have
  cost ~3k in the parent's context.
- A supervisor plus three workers runs around 70–80k tokens for a research fan-out; a five-agent
  sequential pipeline with full history carried at each hop runs 130–150k. Multi-agent traces have
  been measured at roughly 15× the tokens of the same work done in one context.
- Three focused agents consistently beat five scattered ones. Past three, the marginal agent is
  usually re-reading what a sibling already read.

| Work | Fan-out | Who |
|---|---|---|
| Recon before a plan | 3, in one message — 2 if the third would only re-read | `scout` (code), `scout` (docs), `data-explorer` (data) or a third `scout` (history) |
| Pre-ship review | 2, in one message | `ship-reviewer`, `scout` (regression hunt) |
| Independent re-derivation of a number | 2 | `causal-analyst`, `ship-reviewer` |
| One implementation | 1 | `ml-builder` |
| A build whose verification failed twice | 1, stronger model | `glm-5.3` via `/deep-build`, then Kimi, then Opus |

**Never in parallel:** anything that writes the same path, anything that fits or estimates, and
anything whose second step depends on the first step's result. Parallelism buys independent reads;
it does not buy a pipeline.

`experimental.subagent_depth` is pinned to `1`, so a subagent cannot start its own fan-out. That is
the guard rail that stops a three-way recon from becoming a nine-way one two levels down.

**Escalate the model, not the agent count.** When a fix fails twice, the next step is a stronger
model with the failure written down — not more agents repeating the same mistake in parallel.

---

## 5. How this lands on this repo

The repo's own rules already imply most of the agent policy; this section just makes the mapping
explicit.

- **Only three agents may write** — `ml-builder`, `causal-analyst`, `writer`. `scout`, `planner` and
  `ship-reviewer` are edit-denied. `data-explorer` is edit-denied and shell-limited rather than fully
  read-only, because profiling a dataset without running code is not profiling; its prompt forbids
  writes and `git status` will show any that happen.
- **R stages are serial.** `03_estimate.R`, `04_robustness.R` and `05_registry.R` write shared
  artifacts (`registry/`, the DuckDB base). Two stages in one fan-out is a corrupted run, not a
  speed-up. Parallel agents read; one agent runs R.
- **`scripts/verify.sh` is the acceptance command.** The reviewer may run `pytest`, `ruff`,
  `python`, and the `git diff`/`log`/`status` reads — nothing that writes. `Rscript` is denied there
  on purpose: `05_registry.R` writes the frozen registry, and a reviewer that can rewrite the
  artifact it is auditing is not a reviewer.
- **The registry is frozen.** No agent edits a `registry/` artifact by hand; a correction is a new
  vintage, produced by the engine. The three writing agents therefore carry an explicit
  `edit deny` on `**/registry/**`, which still leaves the engine's own R output untouched.
- **Parallel write lanes get a worktree.** Two builders on one checkout will fight over the same
  files and the same DuckDB file.
- **Prose numbers are derived.** `writer` must cite the artifact behind every figure; `ship-reviewer`
  blocks a number it cannot trace. That is the same rule the prose verifiers enforce, applied one
  step earlier.

---

## 6. What a normal day costs

A realistic mixed day under the routing above:

| Work | Runs | Model | Share of that model's 5 h window |
|---|---:|---|---:|
| Planning | 1 | deepseek-v4.1-flash#max | ~0.003 % |
| Recon | 3 | deepseek-v4.1-flash | ~0.01 % |
| Builds | 10 | deepseek-v4.1-flash | ~0.02 % |
| Volume builds (public only) | 6 | muse-spark-1.3-contributor | ~0.01 % |
| Reviews | 4 | glm-5.3-flash | ~0.06 % |
| Writing | 2 | deepseek-v4.1-flash | ~0.005 % |
| Hard-code escalation | 1 | glm-5.3 | ~0.45 % |
| Plan escalation | 0–1 | kimi-k3.1-pro | ~0.7 % when used |

Nothing sits above 1 % of its own five-hour window, and the two escalations are the only entries that
touch a scarce model at all. The failure mode this table prevents is the one where a session defaults
to the strongest model because it is "the best" and hits a 147-request wall before lunch.

If a day went wrong and every step fell back to the primary, the damage is bounded too: a hundred
DeepSeek requests is 0.2 % of its window and about $0.30 at list price. That is the whole argument for
routing *down* rather than optimising for the best model per task.

---

## 7. What this does not do

- **It does not validate the models on this repo.** The routing follows published benchmarks, forum
  reports and the observed behaviour of a few sessions. A proper test would replay a fixed task set
  through two models and compare, and nobody has done that here.
- **It does not make Muse trustworthy.** Meta's own 1.3 numbers (75.4 % DeepSWE) are vendor-published,
  and a hands-on review found the real-world output did not match the score. The forum verdict — good
  instruction following, decent as an implementation subagent, no weird hallucinations while compacted
  around 200–240k — is exactly the profile of a volume lane that needs a plan and a reviewer, not a
  planner.
- **It does not rescue a vague request.** A bad plan fans out faster and more confidently than a
  single agent would. The planner step exists for that reason; skipping it is how you get five
  agents building the wrong thing.
- **One reviewer is one opinion.** DeepSeek's own results on a single model vary by 8.7 points across
  scaffolds — larger than the gap between competing models — so a review that agrees with the builder
  proves less than it looks. For anything that will be published, pay for a second check from a
  different family (`qwen3.8-flash`) or from a human.
- **It does not fix DeepSeek's weak factual recall.** SimpleQA 42.3 is the lowest number in the
  comparison above, and it is precisely the trait an agent needs when it asserts a citation. That is
  why `writer` may not invent a source and `ship-reviewer` blocks a number it cannot trace.
- **It does not give you LSP diagnostics.** The V2 migration guide states that V2 accepts and preserves
  the `lsp` block but "does not run language servers, expose LSP tools, or produce LSP diagnostics"
  ([migrate-v1](https://opencode.ai/v2/docs/migrate-v1), accessed 2026-11-04). `ruff`, `pytest` and the
  verifiers remain the real signal — the LSP config is inert, kept for the day it is not.
- **It does not pin the model list.** Go's lineup changes; `/models` is the source of truth, and a
  model that disappears is a routing decision, not a bug.

## 8. Where the configuration lives

| Path | Holds |
|---|---|
| `~/.config/opencode/AGENTS.md` | **the contract** — every session, every project, loaded automatically |
| `~/.config/opencode/opencode.json` | default model, `default_agent`, `subagent_depth`, MCP and LSP |
| `~/.config/opencode/agents/*.md` | the seven agents: model, steps, permissions, system prompt |
| `~/.config/opencode/commands/*.md` | `/recon`, `/sprint`, `/ship`, `/deep-build`, `/muse-build` |

### How it reaches every session

`~/.config/opencode/AGENTS.md` is discovered automatically and merged into the context of every
session, in every project, with no command to remember and no opt-in. That is the enforcement
surface: the roster supplies the *capability*, the commands supply the *shortcut*, and this file
supplies the *default behaviour*. A project's own `AGENTS.md` is loaded on top of it, so domain rules
win where they conflict and the process rules hold everywhere else.

`default_agent` stays `build` on purpose. A custom primary agent replaces the provider's base coding
prompt with its own `system`, which means losing the tool-use and editing behaviour that `build` gets
right; the workflow is added as instructions instead of substituted for the agent.

`opencode debug agents` prints the merged roster with the resolved model and step cap — the fastest
way to confirm a change took effect. `opencode debug config` shows which configuration sources
merged. `steps` is the V2 field name (V1's `maxSteps`), and the resolved value is what that command
prints.

---

## Sources

Every number above traces to one of these. All accessed 2026-11-04. None of the benchmark figures
were reproduced on this machine or on this repo — they are third-party blog and analyst measurements,
which is exactly why §7 says the routing is a prior, not a result.

| Claim | Source |
|---|---|
| Go plan price, per-model monthly limits, 5 h / week / month shares, request estimates, geo-restrictions, privacy and ZDR table | <https://opencode.ai/v2/docs/console/go> |
| V2 agent fields, modes, permission ordering, subagent depth, `steps` | <https://opencode.ai/v2/docs/agents>, <https://opencode.ai/v2/docs/config> |
| Command `subagent` delegation, model precedence | <https://opencode.ai/v2/docs/commands> |
| Model references and variants; root selection carries no variant | <https://opencode.ai/v2/docs/models> |
| `lsp` accepted but not run in V2 | <https://opencode.ai/v2/docs/migrate-v1> |
| Kimi K3.1 Pro 67.2 % on Terminal-Bench 4.0 (third-party harness; vendor reports 65.7 %) | <https://artificialanalysis.ai/articles/kimi-k3-1-pro-launch-benchmarks> |
| Claude Opus 5.5 66.4 %, Sonnet 5.5 70.6 %, GPT-6 Astra 57.9 % on Terminal-Bench 4.0 | <https://www.morphllm.com/best-ai-model-for-coding> |
| DeepSeek V4.1 Flash ~80 % on long agentic sessions at ~$0.14/session; GLM-5.3 ~74 % | <https://bito.ai/blog/best-open-weight-model-for-coding-kimi-k3-1-pro-glm-5-3-deepseek> |
| MiniMax M3.1 Flash: Intelligence Index 42, 56 % correct on AA-Omniscience while attempting nearly every question | <https://venturebeat.com/technology/minimaxs-new-m3-1-flash-beats-deepseek-and-opus-5-on-a-key-business-benchmark-at-lower-cost-but-with-a-high-hallucination-rate> |
| Subagent spawn cost (~20k tokens fixed; one traced case of 160k) and the ~15× multi-agent token multiple | <https://getnadir.com/blog/multi-agent-orchestration-15x-token-cost> |
| 70–80k tokens for supervisor + 3; 130–150k for a 5-agent sequential pipeline | <https://resources.rework.com/tools/ai-agents/best-multi-agent-frameworks-2026> |
| Three focused agents beat five scattered; 3–5 is the sweet spot | <https://addyosmani.com/blog/code-agent-orchestra> |
| V4 Pro retired 14 Sep 2026; DeepSeek's statement that V4.1 Flash "comprehensively surpassed V4 Pro across all key metrics" | <https://flowtivity.ai/blog/deepseek-v4-1-flash-benchmarks>, <https://coursiv.io/blog/deepseek-v4-1-flash> |
| V4.1 Flash vs V4 Pro: agentic and coding lead (74.2 vs 62.7 DeepSWE; 90.6 vs 87.9 TB 2.1), cheaper and ~1.8× faster, but behind on GPQA Diamond, HLE and SimpleQA — vendor-run, independent replication pending | <https://flowtivity.ai/blog/deepseek-v4-1-flash-benchmarks>, <https://coursiv.io/blog/deepseek-v4-1-flash>, <https://artificialanalysis.ai/models/comparisons/deepseek-v4-1-flash-vs-deepseek-v4-pro> |
| One model across eight scaffolds varies by 8.7 DeepSWE points — more than the gap between competing models | <https://coursiv.io/blog/deepseek-v4-1-flash> |
| GLM-5.3-Flash: 63.4 DeepSWE, 84.3 Terminal-Bench 2.1, 78.4 Toolathlon, 1.31M context, MIT | <https://featherless.ai/blog/glm-5-3-flash-vs-qwen-3-8-flash-next-vs-qwen-3-8-27b>, <https://www.datacamp.com/blog/glm-5-3-flash-vs-qwen3-8-flash-next> |
| Qwen3.8-Flash: 91.9 LiveCodeBench v6, 91.7 GPQA, ~6B active, 32K served context | <https://featherless.ai/blog/glm-5-3-flash-vs-qwen-3-8-flash-next-vs-qwen-3-8-27b> |
| Muse Spark 1.3: 75.4 % DeepSWE, 88.8 % Terminal-Bench 2.1, 98.5 % MRCR (256k–512k) — vendor-published | <https://flowtivity.ai/blog/meta-muse-spark-1-3-benchmarks-ai-agents> |
| Muse Spark 1.3: hands-on output does not match the benchmark score | <https://www.mindstudio.ai/blog/meta-muse-spark-1-3-benchmark-confusion> |
| Muse Spark 1.3 Contributor forum consensus: decent instruction following, no odd hallucinations near 200–240k, best as an implementation subagent | <https://www.reddit.com/r/opencode/comments/1w5tuwx/> |
| Meta geographic policy: restricted territories do not include Nigeria; Contributor models are a separate designation | <https://ai.developer.meta.com/legal/geographic-use-policy> |
| Contributor tier is ~10× cheaper because prompts improve the model | <https://thenewstack.io/meta-muse-code> |
| MiMo-V2.6-Flash: weaker at coding than recent peers, fewer security findings than Qwen3.8 Flash, most prompt-injection-susceptible of the set | <https://www.youtube.com/watch?v=_2svNRbaVVI> |
| DeepSeek V4.1 Flash is the most-used model in OpenCode by tokens | <https://everpod.ai/guides/opencode-models> |
