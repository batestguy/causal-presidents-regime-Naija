/**
 * The answer layer, in the browser and under node — gate -> retrieve -> assemble -> post-check.
 *
 * This is the second implementation of `app/answer_layer.py` + `app/intent_gate.py`, and it is held to the
 * same measurement: `tests/verify_answer_js.py` runs it over every question in the published answer artifact
 * and accepts it only if it reproduces those answers — status, shape, citation, passages and text.
 *
 * It carries no rules of its own. The gate's rules, the answer contract, the glossary and the corpus are
 * JSON the build emits from the same specs the Python layer reads, so a rule is edited in one place.
 *
 * No model, no network, no database: the only input is the question string.
 */

const PREFIX = 4;

const STOPWORDS = new Set([
  "the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "with", "by", "at", "from", "as", "is",
  "are", "was", "were", "be", "been", "being", "it", "its", "this", "that", "these", "those", "there",
  "which", "who", "whom", "whose", "what", "when", "where", "why", "how", "does", "do", "did", "done",
  "can", "could", "would", "should", "will", "shall", "may", "might", "must", "have", "has", "had",
  "not", "no", "but", "if", "then", "than", "so", "such", "into", "about", "over", "under", "between",
  "after", "before", "during", "any", "all", "each", "every", "more", "most", "some", "much", "many",
  "you", "your", "we", "our", "they", "their", "he", "she", "his", "her", "i", "me", "my", "us",
]);

const GENERIC_TERMS = new Set([
  "under", "over", "rate", "net", "real", "level", "index", "value", "share", "series", "year", "month",
  "state", "national", "primary", "change", "current", "total", "other",
]);

const ESTIMATE_ASK = /\b(?:estimates?|estimated|estimation|coefficients?|elasticity|interval|identified|identify|results?|magnitude|pass[- ]?through|how much|standard error|point estimate|significant)\b/i;
const EFFECT_ASK = /\b(?:effects?|impacts?)\b/i;
const INTERVAL = /\[\s*[−+\-]?\d[\d,.]*\s*,\s*[−+\-]?\d[\d,.]*\s*\]/;
const ASSUMPTION = /\bassum\w*/i;
const CANNOT_RULE_OUT = /cannot\s+rule\s+out/i;
const PART_HEADER = /^\[.*?\bpart \d+ of \d+\]\s*$/;
const YEAR = /\b((?:19|20)\d{2})\b/g;
const DATE_RANGE = /(\d{4}-\d{2}-\d{2})\s+to\s+(\d{4}-\d{2}-\d{2})/g;
// Anchored at the paragraph's first character, not at any line start: a card's paragraph can begin with the
// design and carry the assumption further down, and only a paragraph that *is* the assumption is skipped.
const BLOCK_ASSUMPTION = /^Identifying assumption:/;
const BLOCK_CANNOT = /^What this design cannot rule out:/;
const REASON_PATTERN = /Reason code:|Status:\s*not_run|not estimated here|infeasible|not estimated|No estimate for this/i;
const CHECK_PATTERN = /Failed checks:|Verdict rule:|The check that decided:|^Verdict:|placebo|lead-shift/im;
const COEFFICIENT = /=\s*([−+\-]?\d[\d,]*\.?\d*)/;
const SAMPLE = /n\s*=\s*([\d,]+)\s+state-months over ([\d,]+) states/;
const SPAN = /(\d{4}-\d{2}) to (\d{4}-\d{2})/;

const normalise = (text) =>
  String(text).toLowerCase().replace(/['’]/g, "").replace(/[^a-z0-9]+/g, " ").split(" ").filter(Boolean).join(" ");

const countryText = (text) =>
  String(text).toLowerCase().replace(/['’]/g, " ").replace(/[^a-z0-9]+/g, " ").split(" ").filter(Boolean).join(" ");

function firstSentence(text) {
  const flat = String(text).split(/\s+/).filter(Boolean).join(" ");
  const match = /[.!?]\s+/.exec(flat);
  return (match ? flat.slice(0, match.index + 1) : flat).trim();
}

function sentenceWith(text, needle) {
  for (const sentence of String(text).split(/(?<=[.!?])\s+/)) {
    if (sentence.toLowerCase().includes(needle)) return sentence.trim();
  }
  return null;
}

const tokenize = (text) =>
  (String(text).toLowerCase().match(/[a-z0-9]+/g) || []).filter((t) => t.length > 1 && !STOPWORDS.has(t));

function sameTerm(left, right) {
  if (left.length < PREFIX || right.length < PREFIX) return left === right;
  return left.slice(0, PREFIX) === right.slice(0, PREFIX);
}

function matchedTerms(terms, passageTerms) {
  const out = new Set();
  for (const term of terms) {
    for (const other of passageTerms) {
      if (sameTerm(term, other)) {
        out.add(term);
        break;
      }
    }
  }
  return out;
}

function normaliseTerm(token) {
  if (token.endsWith("ies") && token.length > 4) return token.slice(0, -3) + "y";
  if (token.endsWith("ses") && token.length > 4) return token.slice(0, -2);
  if (token.endsWith("s") && !token.endsWith("ss") && token.length > 3) return token.slice(0, -1);
  return token;
}

const words = (text) => (String(text).toLowerCase().match(/[a-z0-9]+/g) || []).map(normaliseTerm);
const labelWords = words;
const questionWords = words;

class BM25 {
  constructor(documents, k1 = 1.5, b = 0.75) {
    this.k1 = k1;
    this.b = b;
    this.ids = [...documents.keys()];
    this.tokens = new Map();
    this.lengths = new Map();
    this.tf = new Map();
    let total = 0;
    for (const id of this.ids) {
      const toks = tokenize(documents.get(id) || "");
      this.tokens.set(id, toks);
      this.lengths.set(id, toks.length || 1);
      total += toks.length || 1;
      const counts = new Map();
      for (const token of toks) counts.set(token, (counts.get(token) || 0) + 1);
      this.tf.set(id, counts);
    }
    this.avgdl = total / Math.max(this.ids.length, 1);
    const df = new Map();
    for (const toks of this.tokens.values()) {
      for (const term of new Set(toks)) df.set(term, (df.get(term) || 0) + 1);
    }
    const n = this.ids.length;
    this.idf = new Map();
    for (const [term, count] of df) this.idf.set(term, Math.log(1 + (n - count + 0.5) / (count + 0.5)));
  }

  scores(query) {
    const terms = tokenize(query);
    const out = new Map();
    for (const id of this.ids) {
      let score = 0;
      const counts = this.tf.get(id);
      const length = this.lengths.get(id);
      for (const term of terms) {
        const frequency = counts.get(term) || 0;
        if (!frequency) continue;
        const denominator = frequency + this.k1 * (1 - this.b + (this.b * length) / this.avgdl);
        score += ((this.idf.get(term) || 0) * frequency * (this.k1 + 1)) / denominator;
      }
      out.set(id, score);
    }
    return out;
  }

  rank(query, k) {
    return [...this.scores(query)]
      .sort((a, b) => (b[1] - a[1]) || (a[0] < b[0] ? -1 : a[0] > b[0] ? 1 : 0))
      .slice(0, k);
  }
}

class Gate {
  constructor(spec, corpus, windowStart, vintage, countries) {
    this.spec = spec;
    this.rules = [...(spec.rules || [])].sort((a, b) => a.priority - b.priority);
    this.chunks = new Map((corpus.chunks || []).map((chunk) => [chunk.chunk_id, chunk]));
    this.windowStartYear = windowStart ? parseInt(String(windowStart).slice(0, 4), 10) : null;
    this.vintageYear = parseInt(String(vintage).slice(0, 4), 10);
    this.sectionCache = new Map();
    const names = [];
    for (const country of countries || []) {
      if (String(country.iso3) === "NGA") continue;
      for (const alias of country.aliases || [country.name]) {
        if (alias) names.push([normalise(alias), String(country.iso3)]);
      }
    }
    names.sort((a, b) => b[0].length - a[0].length);
    this.countryNames = names;
  }

  decide(question) {
    const text = normalise(question);
    const countries = countryText(question);
    for (const rule of this.rules) {
      if (!this.conditionsHold(rule, text, countries)) continue;
      const [route, routeStatus] = this.resolveRoute(rule);
      if (rule.intent !== "answerable" && routeStatus !== "pinned") {
        return {
          intent: "answerable",
          ruleId: rule.id,
          route: null,
          routeStatus: "unresolved",
          reason: `rule ${rule.id} matched but its route did not resolve, so the question is answered rather than refused without a citation`,
          matched: this.matched(rule, text),
        };
      }
      return {
        intent: rule.intent,
        ruleId: rule.id,
        route,
        routeStatus,
        reason: firstSentence(rule.why || rule.implements || ""),
        matched: this.matched(rule, text),
      };
    }
    return {
      intent: "answerable",
      ruleId: null,
      route: null,
      routeStatus: "not_applicable",
      reason: "no rule matched, and the default is answerable",
      matched: {},
    };
  }

  conditionsHold(rule, text, countries) {
    const conditions = rule.conditions || {};
    for (const group of conditions.all_of || []) {
      if (!group.some((pattern) => new RegExp(pattern).test(text))) return false;
    }
    const anyOf = conditions.any_of || [];
    if (anyOf.length && !anyOf.some((group) => group.some((pattern) => new RegExp(pattern).test(text)))) return false;
    for (const entry of conditions.none_of || []) {
      const patterns = Array.isArray(entry) ? entry : [entry];
      if (patterns.some((pattern) => new RegExp(pattern).test(text))) return false;
    }
    const window = conditions.year_window || rule.year_window;
    if (window && !this.yearWindowHolds(window, text)) return false;
    if (conditions.mentions_country && !this.mentionsCountry(countries || text)) return false;
    return true;
  }

  mentionsCountry(text) {
    const padded = ` ${text} `;
    return this.countryNames.some(([name]) => name && padded.includes(` ${name} `));
  }

  yearWindowHolds(mode, text) {
    const years = [...String(text).matchAll(/\b((?:19|20)\d{2})\b/g)].map((m) => parseInt(m[1], 10));
    if (!years.length || this.windowStartYear === null) return false;
    if (mode === "outside") return years.some((year) => year < this.windowStartYear || year > this.vintageYear);
    if (mode === "future") return years.some((year) => year > this.vintageYear);
    if (mode === "past") return years.some((year) => year < this.windowStartYear);
    throw new Error(`unknown year_window mode ${mode}`);
  }

  matched(rule, text) {
    const conditions = rule.conditions || {};
    const hits = [];
    for (const group of [...(conditions.all_of || []), ...(conditions.any_of || [])]) {
      for (const pattern of group) if (new RegExp(pattern).test(text)) hits.push(pattern);
    }
    return { patterns: [...new Set(hits)].sort() };
  }

  resolveRoute(rule) {
    const route = rule.route;
    if (route === null || route === undefined) return [null, "not_applicable"];
    if (typeof route === "string") return this.chunks.has(route) ? [route, "pinned"] : [null, "unresolved"];
    if (route.selector === "chunk") {
      return this.chunks.has(route.chunk_id) ? [route.chunk_id, "pinned"] : [null, "unresolved"];
    }
    if (route.selector === "section") {
      const resolved = this.resolveSection(route);
      return resolved ? [resolved, "pinned"] : [null, "unresolved"];
    }
    return [null, "unresolved"];
  }

  resolveSection(route) {
    const document = String(route.document || "");
    const stem = document.split(/[\\/]/).pop().replace(/\.[^.]+$/, "");
    const needle = String(route.heading_contains || "").toLowerCase();
    const key = `${stem}|${needle}`;
    if (this.sectionCache.has(key)) return this.sectionCache.get(key);
    const prefix = `doc:${stem}#`;
    const hits = [];
    for (const [chunkId, chunk] of this.chunks) {
      if (!chunkId.startsWith(prefix)) continue;
      if ((chunkId.match(/#/g) || []).length !== 1) continue;
      if (String(chunk.title || "").toLowerCase().includes(needle)) hits.push(chunkId);
    }
    const resolved = hits.length === 1 ? hits[0] : null;
    this.sectionCache.set(key, resolved);
    return resolved;
  }

  partsOf(chunkId) {
    const out = [];
    for (const cid of this.chunks.keys()) {
      if (cid === chunkId || cid.startsWith(`${chunkId}#p`)) out.push(cid);
    }
    return out;
  }

  chunkText(chunkId) {
    return String((this.chunks.get(chunkId) || {}).text || "");
  }
}

export class AnswerLayer {
  constructor(gate, corpus, contract, k, glossary) {
    this.gate = gate;
    this.corpus = corpus;
    this.contract = contract;
    this.k = k;
    this.glossary = glossary || {};
    this.template = String(contract.refusal_template || "I don't have a model for that. {reason} — see {citation}.");
    this.shapes = contract.shapes || {};
    this.factOverlapMin = Number(contract.fact_overlap_min || 0);
    this.factMaxPassages = Number(contract.fact_max_passages || 1);
    this.refusalCodes = contract.refusal_codes || {};
    this.chunks = new Map((corpus.chunks || []).map((chunk) => [chunk.chunk_id, chunk]));
    this.bm25 = new BM25(new Map([...this.chunks].map(([cid, chunk]) => [cid, String(chunk.text || "")])));
    this.outcomes = new Map();
    this.cards = new Map();
    this.designs = new Map();
    for (const chunk of this.chunks.values()) {
      const metadata = chunk.metadata || {};
      const outcomeId = metadata.outcome_id;
      const designId = metadata.design_id;
      if (outcomeId && metadata.outcome_label && !this.outcomes.has(String(outcomeId))) {
        this.outcomes.set(String(outcomeId), String(metadata.outcome_label));
      }
      if (outcomeId && designId) {
        const key = `${outcomeId}::${designId}`;
        if (metadata.design_name && !this.designs.has(String(designId))) {
          this.designs.set(String(designId), String(metadata.design_name));
        }
        if (chunk.doc_type === "card_estimate" || !this.cards.has(key)) this.cards.set(key, chunk.chunk_id);
      }
    }
    this.defaultIdf = Math.log(1 + (this.bm25.ids.length + 0.5) / 0.5);
  }

  answer(question) {
    const decision = this.gate.decide(question);
    if (decision.intent !== "answerable") return this.refused(question, decision);
    if (this.asksForANumber(question)) {
      const answer = this.numberAnswer(question, decision);
      if (answer !== null) return answer;
      return this.declined(question, decision, "L01");
    }
    const fact = this.factAnswer(question, decision);
    if (fact !== null) return fact;
    return this.declined(question, decision, "L02");
  }

  refused(question, decision) {
    const [citation, quote] = this.pin(decision.route);
    const reason = templateReason(decision.reason);
    let text = this.refusal(reason, citation);
    if (quote) text = `${text}\n\n**What the record says:** ${quote}`;
    const code = decision.ruleId;
    return {
      status: "refused", question, text, intent: decision.intent, rule_id: decision.ruleId,
      route: decision.route, citation, chunks_used: decision.route ? [decision.route] : [],
      check: { cited: Boolean(citation), quote: Boolean(quote) },
      plain: this.plainRefusal(reason, citation, quote, code), shape: "refusal", refusal_code: code,
    };
  }

  declined(question, decision, code) {
    const reason = this.refusalCodes[code] || "the corpus does not carry an answer in any shape";
    const [citation, quote] = this.pin(null);
    const text = this.refusal(templateReason(reason), citation);
    return {
      status: "declined", question, text, intent: decision.intent, rule_id: code, route: null,
      citation, chunks_used: [], check: { cited: Boolean(citation) },
      plain: this.plainRefusal(templateReason(reason), citation, "", code), shape: "decline",
      refusal_code: code,
    };
  }

  asksForANumber(question) {
    if (EFFECT_ASK.test(question) && this.namedOutcomes(question).size) return true;
    if (!ESTIMATE_ASK.test(question)) return false;
    if (this.namedOutcomes(question).size || this.namedDesigns(question).size) return true;
    for (const [chunkId] of this.bm25.rank(question, 1)) return this.carriesInterval(chunkId);
    return false;
  }

  numberAnswer(question, decision) {
    const outcomes = this.namedOutcomes(question);
    const designs = this.namedDesigns(question);
    for (const source of this.numberSources(question, outcomes, designs)) {
      const assembled = this.assemble(question, source, outcomes, designs);
      if (assembled === null) continue;
      if (assembled.required.every((part) => assembled.check[part])) {
        return this.answered(question, decision, source, assembled);
      }
    }
    return null;
  }

  numberSources(question, outcomes, designs) {
    const sources = [];
    if (outcomes.size) {
      for (const outcomeId of [...outcomes].sort()) {
        for (const designId of [...this.designs.keys()].sort()) {
          if (designs.size && !designs.has(designId)) continue;
          const chunkId = this.cards.get(`${outcomeId}::${designId}`);
          if (chunkId) sources.push(chunkId);
        }
      }
      if (!sources.length) {
        for (const designId of [...designs].sort()) {
          const chunkId = `result:${designId}`;
          if (this.chunks.has(chunkId)) sources.push(chunkId);
        }
      }
      sources.sort((a, b) => (this.carriesInterval(a) ? 0 : 1) - (this.carriesInterval(b) ? 0 : 1) || (a < b ? -1 : a > b ? 1 : 0));
    } else if (designs.size) {
      for (const designId of [...designs].sort()) {
        const chunkId = `result:${designId}`;
        if (this.chunks.has(chunkId)) sources.push(chunkId);
      }
    }
    if (!sources.length) {
      for (const [chunkId] of this.bm25.rank(question, this.k * 8)) {
        const parent = chunkId.split("#p")[0];
        if (sources.includes(parent)) continue;
        if (this.carriesInterval(parent)) sources.push(parent);
        if (sources.length >= 3) break;
      }
    }
    return sources;
  }

  assemble(question, source, outcomes, designs) {
    const blocks = this.blocks(source);
    if (!blocks.length) return null;
    const terms = tokenize(question);
    const designId = this.designOf(source);

    const estimate = this.pick(blocks, terms, INTERVAL, []);
    const reason = this.pick(blocks, terms, REASON_PATTERN, []);
    const checkBlock = this.pick(blocks, terms, CHECK_PATTERN, []);
    let assumption = this.pick(blocks, terms, ASSUMPTION, []);
    let cannot = this.pick(blocks, terms, CANNOT_RULE_OUT, []);
    // The assembly path has no "passage that answers this" block: a fact answer supplies `focus` itself,
    // and an estimate or a reason answer quotes its slots. A pattern that never matches is how the Python
    // layer says the same thing, and this port keeps that behaviour rather than inventing a block.
    const focus = null;

    const borrowed = [];
    const citations = [String((this.chunks.get(source) || {}).citation || source)];
    if (designId && this.designs.has(designId) && (assumption === null || cannot === null)) {
      const donor = this.designDonor(designId);
      if (donor && donor !== source) {
        const donorBlocks = this.blocks(donor);
        assumption = assumption || this.pick(donorBlocks, terms, ASSUMPTION, []);
        cannot = cannot || this.pick(donorBlocks, terms, CANNOT_RULE_OUT, []);
        borrowed.push(donor);
        citations.push(String((this.chunks.get(donor) || {}).citation || donor));
      }
    }

    const shape = estimate ? "estimate" : "no_estimate";
    const shapeSpec = this.shapes[shape] || {};
    const required = [...(shapeSpec.requires || [])];
    const forbidden = [...(shapeSpec.forbids || [])];
    const check = {
      interval: Boolean(estimate && INTERVAL.test(estimate)),
      reason_code: Boolean(reason),
      identifying_assumption: Boolean(assumption && ASSUMPTION.test(assumption)),
      cannot_rule_out: Boolean(cannot && CANNOT_RULE_OUT.test(cannot)),
      citation: Boolean(citations[0]),
    };
    if (required.some((part) => !check[part])) return null;
    if (forbidden.some((part) => check[part])) return null;
    return {
      shape, required, estimate, reason, check_block: checkBlock, assumption, cannot, focus,
      citation: [...new Set(citations)].join("; "), chunks_used: [source, ...borrowed], check,
    };
  }

  designDonor(designId) {
    const candidates = [...this.cards.entries()]
      .filter(([key]) => key.split("::")[1] === designId)
      .map(([, chunkId]) => chunkId)
      .sort();
    return candidates.length ? candidates[0] : null;
  }

  answered(question, decision, source, assembled) {
    return {
      status: "answered", question, text: this.render(question, source, assembled),
      intent: decision.intent, rule_id: decision.ruleId, route: null, citation: assembled.citation,
      chunks_used: assembled.chunks_used, check: assembled.check, plain: this.plain(assembled, source),
      shape: assembled.shape, refusal_code: null,
    };
  }

  factAnswer(question, decision) {
    const outcomes = this.namedOutcomes(question);
    const terms = tokenize(question);
    const years = new Set([...String(question).matchAll(/\b((?:19|20)\d{2})\b/g)].map((m) => parseInt(m[1], 10)));
    const passages = this.factPassages(question, terms, years, outcomes);
    if (!passages.length) return null;
    const body = passages.map((row) => row[2]).join("\n\n");
    const citations = [...new Set(passages.map((row) => String((this.chunks.get(row[0]) || {}).citation || row[0])))];
    const citation = citations.join("; ");
    if (!citation) return null;
    return this.answered(question, decision, passages[0][0], {
      shape: "fact", estimate: null, reason: null, check_block: null, assumption: null, cannot: null,
      focus: body, citation, chunks_used: passages.map((row) => row[1]),
      check: { citation: true, interval: false, reason_code: false, identifying_assumption: false, cannot_rule_out: false },
      required: [],
    });
  }

  factPassages(question, terms, years, outcomes) {
    const candidates = [];
    const ranked = this.parentsInOrder(this.bm25.rank(question, this.k * 8));
    ranked.forEach(([parent, parts], rank) => {
      if (outcomes.size && !this.covers(parent, outcomes)) return;
      for (const chunkId of parts) {
        for (const paragraph of this.paragraphs(chunkId)) {
          if (INTERVAL.test(paragraph)) continue;
          if (BLOCK_ASSUMPTION.test(paragraph) || BLOCK_CANNOT.test(paragraph)) continue;
          const score = this.overlap(terms, years, paragraph);
          if (score <= 0) continue;
          candidates.push([score, rank, parent, chunkId, paragraph]);
        }
      }
    });
    if (!candidates.length) return [];
    candidates.sort((a, b) => (b[0] - a[0]) || (a[1] - b[1]) || (a[3] < b[3] ? -1 : a[3] > b[3] ? 1 : 0));
    if (candidates[0][0] < this.factOverlapMin) return [];
    const document = candidates[0][2];
    return candidates.filter((row) => row[2] === document).slice(0, this.factMaxPassages)
      .map((row) => [row[2], row[3], row[4]]);
  }

  weight(term) {
    return this.bm25.idf.has(term) ? this.bm25.idf.get(term) : this.defaultIdf;
  }

  overlap(terms, years, body) {
    if (!terms.length) return 1;
    const bodyTerms = new Set(tokenize(body));
    const hits = matchedTerms(terms, bodyTerms);
    const spans = [...String(body).matchAll(/(\d{4}-\d{2}-\d{2})\s+to\s+(\d{4}-\d{2}-\d{2})/g)];
    for (const year of years) {
      const key = String(year);
      if (hits.has(key)) continue;
      if (body.includes(key) || spans.some((m) => parseInt(m[1].slice(0, 4), 10) <= year && year <= parseInt(m[2].slice(0, 4), 10))) {
        hits.add(key);
      }
    }
    let total = 0;
    let got = 0;
    for (const term of terms) total += this.weight(term);
    for (const term of hits) got += this.weight(term);
    return got / Math.max(total, 1e-9);
  }

  namedOutcomes(question) {
    if (!this.outcomes.size) return new Set();
    const qWords = questionWords(question);
    const distinctive = this.distinctiveTerms();
    let best = null;
    for (const [outcomeId, label] of this.outcomes) {
      const run = longestRun(labelWords(label), qWords);
      const own = distinctive.get(outcomeId) || new Set();
      const hits = [...own].filter((word) => qWords.includes(word)).length;
      if (run === 0 || (run === 1 && hits === 0)) continue;
      const score = [run, hits];
      if (best === null || score[0] > best[0][0] || (score[0] === best[0][0] && score[1] > best[0][1])) {
        best = [score, outcomeId];
      }
    }
    return best ? new Set([best[1]]) : new Set();
  }

  distinctiveTerms() {
    const labels = new Map();
    for (const [outcomeId, label] of this.outcomes) labels.set(outcomeId, labelWords(label));
    const counts = new Map();
    for (const entry of labels.values()) {
      for (const word of new Set(entry)) counts.set(word, (counts.get(word) || 0) + 1);
    }
    const out = new Map();
    for (const [outcomeId, entry] of labels) {
      out.set(outcomeId, new Set([...new Set(entry)].filter(
        (word) => counts.get(word) === 1 && word.length >= 4 && !GENERIC_TERMS.has(word))));
    }
    return out;
  }

  namedDesigns(question) {
    const named = new Set([...String(question).toLowerCase().matchAll(/\bdesign\s*([abc])\b/g)].map((m) => m[1].toUpperCase()));
    if (named.size) return named;
    const terms = new Set(tokenize(question));
    for (const [designId, name] of this.designs) {
      const distinctive = new Set(tokenize(name).filter((term) => !GENERIC_TERMS.has(term)));
      const hits = [...distinctive].filter((term) => terms.has(term)).length;
      if (hits >= 2) named.add(designId);
    }
    return named;
  }

  designOf(source) {
    const metadata = (this.chunks.get(source) || {}).metadata || {};
    if (metadata.design_id) return String(metadata.design_id);
    if (source.startsWith("result:")) return source.slice(7);
    return null;
  }

  covers(parent, named) {
    const metadata = (this.chunks.get(parent) || {}).metadata || {};
    if (metadata.outcome_id) return named.has(String(metadata.outcome_id));
    const cells = metadata.cells || {};
    if (Object.keys(cells).length) return Object.keys(cells).some((outcomeId) => named.has(String(outcomeId)));
    const body = this.gate.partsOf(parent).map((cid) => String((this.chunks.get(cid) || {}).text || "")).join(" ");
    const qWords = new Set(questionWords(body));
    for (const outcomeId of named) {
      if (qWords.has(outcomeId)) return true;
      const label = labelWords(this.outcomes.get(outcomeId) || "");
      if (label.some((word) => qWords.has(word))) return true;
    }
    return false;
  }

  blocks(source) {
    const out = [];
    for (const chunkId of this.gate.partsOf(source)) out.push(...this.paragraphs(chunkId));
    return out;
  }

  paragraphs(chunkId) {
    return this.body(chunkId).split(/\n\s*\n/).map((block) => block.trim()).filter(Boolean);
  }

  body(chunkId) {
    const text = String((this.chunks.get(chunkId) || {}).text || "");
    return text.split("\n").filter((line) => !PART_HEADER.test(line)).join("\n").trim();
  }

  pick(blocks, terms, pattern, exclude) {
    const candidates = blocks.filter((block) => !exclude.includes(block) && pattern.test(block));
    if (!candidates.length) return null;
    let best = candidates[0];
    let bestMatched = matchedTerms(terms, new Set(tokenize(best))).size;
    for (const block of candidates.slice(1)) {
      const matched = matchedTerms(terms, new Set(tokenize(block))).size;
      if (matched > bestMatched || (matched === bestMatched && block.length < best.length)) {
        best = block;
        bestMatched = matched;
      }
    }
    return best;
  }

  carriesInterval(chunkId) {
    return this.gate.partsOf(chunkId).some((part) => INTERVAL.test(this.body(part)));
  }

  parentsInOrder(retrieved) {
    const seen = [];
    for (const [chunkId] of retrieved) {
      const parent = chunkId.split("#p")[0];
      if (!seen.includes(parent)) seen.push(parent);
    }
    return seen.map((parent) => [parent, this.gate.partsOf(parent)]);
  }

  render(question, source, assembled) {
    const lines = [`**Question:** ${question}`, ""];
    if (assembled.shape === "estimate") {
      lines.push(`**Estimate:** ${assembled.estimate}`, "");
      if (assembled.check_block) lines.push(`**The check that decided it:** ${assembled.check_block}`, "");
    } else if (assembled.shape === "no_estimate") {
      lines.push(`**Why there is no number:** ${assembled.reason}`, "");
      if (assembled.check_block) lines.push(`**The check that decided it:** ${assembled.check_block}`, "");
    } else {
      lines.push(`**The record says:** ${assembled.focus}`, "");
    }
    if (assembled.assumption) lines.push(`**Identifying assumption:** ${assembled.assumption}`, "");
    if (assembled.cannot) lines.push(`**What it cannot rule out:** ${assembled.cannot}`, "");
    if (assembled.focus && assembled.shape !== "fact") {
      lines.push(`**The passage that answers this:** ${assembled.focus}`, "");
    }
    lines.push(`**Citation:** ${assembled.citation} — ${source}`);
    return lines.join("\n").trim();
  }

  plain(assembled, source) {
    const quoted = ["estimate", "reason", "check_block", "assumption", "cannot", "focus"]
      .map((slot) => String(assembled[slot] || "")).join(" ");
    const terms = [];
    for (const [term, meaning] of Object.entries(this.glossary)) {
      const escaped = term.toLowerCase().replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
      if (new RegExp(`\\b${escaped}\\b`).test(quoted.toLowerCase())) terms.push({ term, meaning });
    }
    const lines = [];
    let headline;
    if (assembled.shape === "estimate") {
      const estimateFull = String(assembled.estimate || "").split(/\s+/).filter(Boolean).join(" ");
      const estimate = sentenceWith(estimateFull, "interval") || estimateFull;
      const reading = readingOf(estimate);
      headline = (reading || {}).sentence
        || "The corpus answers this from the passage below; it carries no single coefficient to read.";
      lines.push(`**Short answer:** ${headline}`, "", `**The number:** ${estimate}`, "");
    } else if (assembled.shape === "no_estimate") {
      const reason = String(assembled.reason || "").split(/\s+/).filter(Boolean).join(" ");
      // The Python layer looks for the literal `Reason code` in the lowercased sentence, so it never
      // matches and the headline is the whole reason. Reproduced deliberately: this module is measured
      // against the artifact, not against a tidier reading of it.
      headline = sentenceWith(reason, "Reason code") || reason;
      lines.push(`**Short answer:** ${headline}`, "", `**Why there is no number:** ${reason}`, "");
      if (assembled.check_block) lines.push(`**What decided it:** ${assembled.check_block}`, "");
    } else {
      const passage = String(assembled.focus || "").split(/\s+/).filter(Boolean).join(" ");
      const match = /[.!?]\s+/.exec(passage);
      headline = (match ? passage.slice(0, match.index + 1) : passage).trim();
      lines.push(`**Short answer:** ${headline}`, "", `**The record says:** ${passage}`, "");
    }
    if (assembled.assumption) {
      const full = String(assembled.assumption || "").split(/\s+/).filter(Boolean).join(" ");
      lines.push(`**What it assumes:** ${sentenceWith(full, "identifying assumption") || full}`, "");
    }
    if (assembled.cannot) {
      const full = String(assembled.cannot || "");
      const bullets = full.split(/\r?\n/).map((line) => line.trim()).filter((line) => line.startsWith("-") || line.startsWith("*"));
      lines.push(`**What it cannot tell you:** ${bullets.length ? bullets.join("\n") : full.split(/\s+/).filter(Boolean).join(" ")}`, "");
    }
    lines.push(`**Where this comes from:** ${assembled.citation} — ${source}`);
    if (terms.length) {
      lines.push("", "**What the words mean:**", "");
      for (const item of terms) lines.push(`- **${item.term}** — ${item.meaning}`);
    }
    let reading = null;
    if (assembled.shape === "estimate") {
      const full = String(assembled.estimate || "").split(/\s+/).filter(Boolean).join(" ");
      reading = readingOf(sentenceWith(full, "interval") || full);
    }
    return { headline, reading, terms, text: lines.join("\n") };
  }

  plainRefusal(reason, citation, quote, code) {
    const meaning = code ? this.glossary[String(code)] : null;
    const lines = [`**Short answer:** ${reason}`, ""];
    if (meaning) lines.push(`**In plain English (${code}):** ${meaning}`, "");
    if (quote) lines.push(`**What the record says:** ${quote}`, "");
    lines.push(`**Where this comes from:** ${citation || "no citable chunk"}`);
    return { headline: reason, reading: null, terms: [], text: lines.join("\n") };
  }

  pin(chunkId) {
    if (!chunkId || !this.chunks.has(chunkId)) return [null, ""];
    const chunk = this.chunks.get(chunkId);
    const quote = this.body(chunkId).split(/\s+/).filter(Boolean).join(" ");
    return [String(chunk.citation || chunkId), quote];
  }

  refusal(reason, citation) {
    return this.template.replace("{reason}", reason).replace("{citation}", citation || "no citable chunk");
  }
}

function templateReason(reason) {
  const flat = String(reason).split(/\s+/).filter(Boolean).join(" ");
  return flat ? flat[0].toUpperCase() + flat.slice(1) : "No rule matched";
}

function longestRun(labelTerms, qTerms) {
  let best = 0;
  for (let start = 0; start < labelTerms.length; start += 1) {
    for (let end = start + 1; end <= labelTerms.length; end += 1) {
      const run = labelTerms.slice(start, end);
      if (run.length <= best) break;
      if (containsRun(run, qTerms)) best = run.length;
    }
  }
  return best;
}

function containsRun(run, sequence) {
  if (!run.length || run.length > sequence.length) return false;
  for (let index = 0; index <= sequence.length - run.length; index += 1) {
    if (run.every((term, offset) => sequence[index + offset] === term)) return true;
  }
  return false;
}

function readingOf(estimate) {
  const interval = INTERVAL.exec(estimate);
  const coefficient = COEFFICIENT.exec(estimate);
  if (!interval || !coefficient) return null;
  const [lowText, highText] = interval[0].replace(/^\[|\]$/g, "").split(",").map((part) => part.trim());
  const number = (text) => Number(text.replace(/−/g, "-").replace(/,/g, ""));
  const low = number(lowText);
  const high = number(highText);
  const value = number(coefficient[1]);
  if (![low, high, value].every(Number.isFinite)) return null;
  const includesZero = low <= 0 && high >= 0;
  const direction = value < 0 ? "negative" : value > 0 ? "positive" : "zero";
  let sentence = `The published estimate is ${direction} (${coefficient[1]}). `;
  sentence += `The range the data cannot rule out runs from ${lowText} to ${highText}`;
  sentence += includesZero
    ? ", and it includes zero, so this answer does not establish a direction."
    : ", and it does not include zero, so the data are consistent with a relationship — the assumption below is what makes it credible.";
  const reading = { coefficient: coefficient[1], interval_low: lowText, interval_high: highText, includes_zero: includesZero, direction };
  const sample = SAMPLE.exec(estimate);
  if (sample) {
    reading.n_state_months = sample[1];
    reading.n_states = sample[2];
    sentence += ` It rests on ${sample[1]} state-months across ${sample[2]} states`;
    const span = SPAN.exec(estimate);
    if (span) {
      reading.first_month = span[1];
      reading.last_month = span[2];
      sentence += `, ${span[1]} to ${span[2]}`;
    }
    sentence += ".";
  }
  reading.sentence = sentence;
  return reading;
}

/** Build the layer from the JSON the site emits — no spec is parsed here. */
export function loadLayer(data) {
  const gate = new Gate(data.gate.spec, data.corpus, data.gate.window_start, data.gate.vintage, data.gate.countries);
  return new AnswerLayer(gate, data.corpus, data.contract.contract, data.contract.k, data.contract.glossary);
}
