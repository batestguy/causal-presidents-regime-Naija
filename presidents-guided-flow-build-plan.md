# Guided flow — build plan

**Companion to:** `presidents-guided-flow-spec.md` (what is being built and why), `docs/comparisons-and-changepoints.md`
(field-by-field contract), `docs/portraits.md` (the cover's images).

**The rule that orders everything below:** a spec is declared and frozen before the engine that applies it runs,
an engine publishes before a screen renders from it, a screen verifies before the chain is called green, and
nothing deploys except from a green chain. This is the order every earlier stage in this project took, and each
time it was skipped the project found a defect it could not have found by reading (C-42, C-44, C-49, C-52).

---

## 1. Dependency graph

```
P0  declarations  ──┬─► P1 site skeleton (cover, study, compare) ──┬─► P4 screens 3–5 ──┬─► P6 CI + deploy
                    │                                              │                      │
                    ├─► P2 comparisons engine + verifier ──────────┘                      │
                    └─► P3 changepoints engine + verifier ────────────────────────────────┤
                                                                                          │
                     P5 JS answer layer + parity verifier ────────────────────────────────┘
                                                                                          │
                                                                          P7 docs + break-tests + green chain
```

P1 can run in parallel with P2/P3 because the cover and study screens read only artifacts that already exist.
P4 needs P2 and P3 for the chart screen and already-published artifacts for the graph and estimate screens.
P5 is deliberately last among the builds: it is the only piece with **two implementations**, so it is the piece
most likely to drift, and it should be built when everything it quotes is final.

---

## 2. Phases

### P0 — Declarations (no numbers, no screens)

| Deliverable | Path | Gate |
|---|---|---|
| Comparison groups, mean rule, windows, caption templates | `analysis/specs/comparisons.yml` | declared and md5-recorded before P2 runs |
| Changepoint method, cut-offs, forbidden fields, attribution rule | `analysis/specs/changepoints.yml` | declared and md5-recorded before P3 runs |
| Plain-words dictionary (design, status, reason, grouping) | `analysis/specs/guide.yml` | every artefact vocabulary item has an entry, and every entry is used |
| Administrations reference + its builder | `registry/reference/administrations.json`, `scripts/build_administrations.py` | dates equal the seed's; one open-ended row |
| Schemas | `registry/schema/{comparisons,changepoints,administrations}.schema.json` | **done** — all three validate as draft 2020-12 |

**Exit gate:** the four specs are committed before any engine exists, because a method chosen after seeing its
results is not a method. `guide.yml` is the wording's home: if a sentence can be read on the site and is not in
it, the site is doing something the specs do not describe.

### P1 — Site skeleton: cover, study, compare

| Deliverable | Gate |
|---|---|
| `site/build.py` — reads registry + specs, writes `site/dist/` | no literal numeric value in the script except 0/1 and index offsets |
| `site/assets/` — CSS + ES modules, no npm, no network | page works from `file://` and over HTTP |
| Cover at `/`, study at `/study/`, minimal compare at `/outcomes/<ids>/compare/` | every rendered figure, count and reason equals its artifact field |
| `tests/verify_site.py` — builds into a temp dir, parses HTML with `html.parser` | fails on a typed count, a dropped reason, a wrong date, a missing vintage stamp |

**Exit gate:** a person can walk cover → study → compare without a document, and the compare rows name a reason
for every outcome that has no usable design.

### P2 — Comparisons engine

| Deliverable | Gate |
|---|---|
| `analysis/R/08_comparisons.R` | writes `registry/comparisons/<vintage>/comparisons.json` + `figures/*.svg`, byte counts recorded |
| `analysis/specs/comparisons.yml` applied, not reinterpreted | the artifact's `rules` block equals the spec's declared values |
| `tests/verify_comparisons.py` | recomputes every count, both means, every caption's numbers, every byte count; walks the JSON for forbidden fields |

**Exit gate:** the artifact validates against its schema, the verifier passes, and **seven mutations were applied
and caught** (a count moved by one, a mean moved by 0.01, a caption number changed, a byte count changed, a group
dropped below `min_units_per_group`, a `p_value` inserted, the vintage changed), each restored byte-for-byte.

### P3 — Changepoints engine

| Deliverable | Gate |
|---|---|
| `analysis/R/09_changepoints.R` | native observations only; known definition breaks passed in; no statistical field written |
| `tests/verify_changepoints.py` | re-derives regime/status from native counts; re-runs the declared search and requires the same months; fails on a break in an unobserved month (K-6); fails on a break captioned as an administration's effect |

**Exit gate:** coverage is published per outcome rather than implied — 2 searched, the annual block fixed-date,
the four short education series refused with a reason, and the counts in `counts` sum to 12.

### P4 — Screens 3–5

| Deliverable | Gate |
|---|---|
| Graph screen: chosen graph as exhibit, alternatives collapsed with their failed check | browsing cannot change the estimate screen |
| Estimate screen: plain reading first, number with verdict, reason when there is none, technical expander | a Design B number never appears on an outcome page |
| Chart screen: grouping control, trend lines, definition breaks, changepoint markers, "description, not a causal comparison" | every chart label and stamp comes from `guide.yml` |
| `tests/verify_site.py` extended to all six screens | all 12 outcomes reachable; the 36-card contract still holds on the card pages |

**Exit gate:** all 12 outcomes answer something, and the site's text is provably the artifacts' text.

### P5 — JS answer layer

| Deliverable | Gate |
|---|---|
| `site/assets/answer.js` — gate rules, BM25, three-shape contract, post-check, glossary reading | rules loaded from JSON the build emits from `analysis/specs/intent_gate.yml` and `rag.yml`; no rule, weight or threshold retyped in JS |
| `tests/verify_answer_js.py` — `node --test` against `answer_eval.json` | the JS reproduces the artifact's citations, needles and plain readings for all 38 measured questions |
| `registry/…/answer_eval.json` unchanged | the Python layer's numbers stay the reference; the JS must match them, not the reverse |

**Exit gate:** parity, or the chat ships behind a "not yet measured" note and the flow goes public without it
(open question 4 in the spec).

### P6 — Chain and deploy

| Deliverable | Gate |
|---|---|
| `scripts/verify.sh` gains: P2, P3, site build, `verify_site.py`, `verify_comparisons.py`, `verify_changepoints.py`, `verify_guide.py`, `verify_answer_js.py` | one command, one exit status, as today |
| `.github/workflows/verify.yml` gains a `pages` job | deploys **only** on a green chain; uploads `site/dist/` as the Pages artifact |
| Vintage stamp + licence footer on every page | read from the index and the licence register, never typed |
| Deploy verified, not assumed | the live URL is fetched and a known string from a known artifact is found in it |

**Exit gate:** the deployed page and the local build are byte-identical except for the build timestamp, and a
stale vintage cannot be published without the stamp saying so.

### P7 — Documentation and break-tests

| Deliverable | Gate |
|---|---|
| `docs/app.md` describes the flow and the static build; its counts derived and verified | `verify_site.py` requires the page's numbers to equal the artifacts' |
| Break-tests in `.probe/` (gitignored), described in `PROGRESS.md` | ten mutations, each red, each restored byte-for-byte |
| `PROGRESS.md` session entry; `PHASES.md` Stage 9 status updated | the handoff is readable without this plan |

**Exit gate:** the chain is green end to end, every new verifier is in it, and the record says what was not done.

### P8 — Screen 6b: the design-level results (built 2026-10-27)

The plan above stopped at seven screens because the three figures Stage 8 published — the forest plot, the
specification curve, the event study — are not per-outcome and had no home in the flow. They were therefore
reachable from **nowhere** on the published site. This phase is the reader they were missing.

| Deliverable | Gate |
|---|---|
| `site/build.py` renders `/designs/` from `registry/{estimates,robustness,events}/<vintage>/` | every string is an artifact field or a `guide.yml` entry; no number typed |
| `analysis/specs/guide.yml` gains a `design_results` section | every figure label, verdict line and event-status word is declared there |
| `tests/verify_site.py` extends to the screen | three figures byte-matched to their artifacts, A's number and failed check, the grid's support and flips, C's reason and next step, one line per transition verdict, the verdict rule, every `not_claimed` statement |
| Every `src`/`href` on every page resolves from that page's URL | **the check that found the defect** — figure paths were written root-relative on pages served one directory down, so `/chart/` and `/graph/` 404ed every image while the verifier stayed green |

**Exit gate:** the chain is green with the screen in it, the figures load over HTTP, and six mutations — a dropped
figure, a dropped failed check, a dropped next step, dropped transition rows, a support count with its positive
tally removed, and a byte count one out — each turn the verifier red and are restored byte-for-byte.

**Not in this phase:** the chat cannot point at a figure (no `figure` answer shape, no figure chunks in the
corpus), the Model card and What-this-reads halves of the "go deeper" screens are still unbuilt, and the forest
plot's right-hand labels are clipped at the SVG's own edge — an artifact layout question for `03_estimate.R`, not
for this page.

### P9 — Ask in the navigation, and charts with the presidents over them (next)

Two changes the requester queued on 2026-10-28. Both are site-only: no artifact, count or verdict moves.

| Deliverable | Gate |
|---|---|
| `guide.yml → nav.ask` and one more entry in `site/build.py::page()` | `tests/verify_site.py` checks the Ask link on all 11 pages, with the same per-page href resolution as the other four |
| `/ask/` stays a flow step and becomes a nav destination | the nav does not break the step rail or the selection carried in the URL; the answer layer still loads only on its own page |
| the chart screen takes the wide measure (1240 px) and a taller cap | figures are scaled in CSS, so the artifact byte counts recorded by R do not move; the comparison and changepoint panels stay readable at 420 px |
| portraits over each chart as **period markers** aligned to the tenure bands | `alt=""` and `aria-hidden` on the portrait, no name and no verdict word; the surname scan gets an explicit, named exception for the block rather than a loosened pattern |
| portrait reuse respects the licence record | the files come from `site/assets/presidents/` via the manifest; the credit list is repeated on `/chart/` or linked to the cover footer, and `docs/licences.md` is not edited |

**Open before coding:** the composition. One row of five portraits above the panel, aligned to the tenure bands
(recommended — it reads as a time axis and cannot be mistaken for a result), or one portrait per band as a faint
watermark behind the line. The first is cheaper to verify: the row has an explicit order, the watermark does not.
The portraits apply to the time-axis panels — the comparison charts and the changepoint panels — and not to the
forest plot or the specification curve, which have no time axis.

**Exit gate:** the chain is green, the Ask tab answers the same measured questions from a bookmarked page as
from the flow, and the surname scan fails on a portrait that carries a name.

---

## 3. Risks, and what each one costs if ignored

| Risk | Why it bites here | Mitigation in the plan |
|---|---|---|
| Two renderers drift | Streamlit and the site both render the registry; they can disagree a year from now | `verify_app.py` and `verify_site.py` both stay in the chain; the card JSON is the only source |
| Two answer layers drift | JS reimplements BM25 + contract; a paraphrase or a threshold edit silently changes answers | rules emitted from the same YAML; parity verifier compares against `answer_eval.json`, not against the Python code |
| Changepoints read as history | a break near a handover invites "the president caused it" | `attribution_rule`, `coincides_with_inauguration` for timing only, a caption grep, and no p-values at all |
| Interpolated months detected as breaks | 1,826 filled months would dominate any search (C-30) | `input_rule` + invariant K-6 as a hard failure |
| Pages serving a stale vintage | a fixed snapshot at a URL, which UI-08 named as the governance question | vintage stamp on every page; deploy only from a green chain |
| Portrait licensing | a president's photograph is not public domain because they are public | `docs/portraits.md` procedure; frames ship empty until a row exists in the licence register |
| Group means over a rule | annual series carry 275–286 interpolated months | `group_mean_native_only` published beside `group_mean`, and the caption says which is which |

---

## 4. What this plan deliberately does not do

- No new dependency: Python stdlib + PyYAML + jsonschema (all present), R `strucchange`/`segmented` (present),
  Node's built-in test runner (present). No npm, no pip install, no R install.
- No change to any published number: the two new families are descriptive, and the estimates, robustness, events,
  registry and RAG artifacts are read-only inputs to this build.
- No hosted runtime: Pages serves files; the chat's Python original stays the local tool.
- No second source of truth: every string the site shows is either an artifact field or a `guide.yml` entry.

---

## 5. Definition of done for the whole build

1. Six screens, shareable addresses, phone-readable, no document needed.
2. 12 of 12 outcomes answer something; none is silent.
3. Two new artifact families schema-valid, verifier-backed, break-tested, in `verify.sh`.
4. One command green locally and in CI, with every pre-existing verifier still passing.
5. The page's every number traceable to a card or an artifact, proven by a verifier that parses the built HTML.
6. The chat either reproduces `answer_eval.json` or is labelled unmeasured.
7. The deployed site stamps its vintage and its attribution.
