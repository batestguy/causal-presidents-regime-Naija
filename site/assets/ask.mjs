/**
 * The Ask screen: the same answer layer the local app runs, over the published corpus.
 *
 * It loads three same-origin JSON files the build emits (the gate's rules, the contract and glossary, the
 * corpus) and the layer module. No model, no network call, no database — and no rule of its own: this file
 * only puts the answer on the page.
 */

// The layer module is imported with the same version query this module was served with, so a rebuild
// never pairs a new ask screen with the last build's answer code.
const version = import.meta.url.split("?")[1] || "";
const { loadLayer } = await import(new URL(`./answer.mjs${version ? `?${version}` : ""}`, import.meta.url).href);

const form = document.getElementById("ask-form");
const input = document.getElementById("ask-input");
const status = document.getElementById("ask-status");
const panel = document.getElementById("ask-answer");
const emptyCopy = status.textContent;

const escapeHtml = (text) =>
  String(text).replace(/[&<>"']/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[ch]));

/** The artifact's own Markdown, rendered: bold labels, bullets, blank-line paragraphs. */
function render(text) {
  const lines = String(text).split(/\r?\n/);
  const out = [];
  let bullets = [];
  const flush = () => {
    if (bullets.length) {
      out.push(`<ul class="tight">${bullets.map((item) => `<li>${item}</li>`).join("")}</ul>`);
      bullets = [];
    }
  };
  for (const raw of lines) {
    const line = raw.trim();
    if (!line) {
      flush();
      continue;
    }
    if (line.startsWith("- ") || line.startsWith("* ")) {
      bullets.push(`<span>${bold(escapeHtml(line.slice(2)))}</span>`);
      continue;
    }
    flush();
    out.push(`<p>${bold(escapeHtml(line))}</p>`);
  }
  flush();
  return out.join("\n");
}

function bold(text) {
  let out = text;
  while (out.includes("**")) {
    out = out.replace("**", "<strong>");
    if (out.includes("**")) out = out.replace("**", "</strong>");
  }
  return out;
}

async function fetchJson(path) {
  const response = await fetch(path);
  if (!response.ok) throw new Error(`${path}: ${response.status}`);
  return response.json();
}

let layerPromise = null;

function layer() {
  if (!layerPromise) {
    layerPromise = Promise.all([
      fetchJson("../data/gate.json"),
      fetchJson("../data/contract.json"),
      fetchJson("../data/corpus.json"),
    ]).then(([gate, contract, corpus]) => loadLayer({ gate, contract, corpus }));
  }
  return layerPromise;
}

/** The artifact's text split on its `**Label:**` headings. */
function splitSections(text) {
  const sections = [];
  let current = null;
  for (const raw of String(text).split(/\r?\n/)) {
    const match = raw.match(/^\s*\*\*([^*]{2,60}):\*\*\s*(.*)$/);
    if (match) {
      current = { title: match[1].trim(), lines: match[2] ? [match[2]] : [] };
      sections.push(current);
    } else if (current) {
      current.lines.push(raw);
    }
  }
  return sections.map((s) => ({ title: s.title, body: s.lines.join("\n").trim() }));
}

/** First n sentences, so a fact answer keeps its headline and its number but not the essay. */
function firstSentences(text, n) {
  const parts = String(text).split(/(?<=[.!?])\s+/);
  return parts.slice(0, n).join(" ").trim();
}

/** The short answer: one section of the plain text, cut to the two sentences a reader needs. */
function plainReading(answer) {
  if (!answer.plain || !answer.plain.text) return answer.text;
  const sections = splitSections(answer.plain.text);
  const record = sections.find((s) => /^the record says/i.test(s.title));
  if (record) return firstSentences(record.body, 2); // headline plus the number
  const short = sections.find((s) => /^short answer/i.test(s.title));
  if (!short) return answer.plain.text;
  // The machine reason code is technical vocabulary; it stays in the collapsed section.
  const plainOnly = short.body.replace(/\bReason code:\s*\S+\s*[.;]\s*/i, "");
  return firstSentences(plainOnly, 2);
}

/**
 * The technical pass, trimmed: question echo and duplicated prefixes dropped, the artifact path removed
 * from the source line, and every section a bold label with its body. Only what a checking reader needs.
 */
function technicalReading(text) {
  const sections = splitSections(text).filter((s) => !/^question/i.test(s.title));
  const parts = [];
  for (const section of sections) {
    const label = section.title
      .replace(/^the check that decided it$/i, "Deciding check")
      .replace(/^identifying assumption$/i, "Assumption")
      .replace(/^what it cannot rule out$/i, "Cannot rule out")
      .replace(/^citation$/i, "Source");
    let body = section.body
      .replace(/^(?:the )?check that decided it:\s*/i, "")
      .replace(/^identifying assumption:\s*/i, "")
      .replace(/^what this design cannot rule out:\s*/i, "")
      .replace(/^the published specification is\s*/i, "")
      .replace(/registry\/\S+\.json\s*/g, "")
      .replace(/\s+—\s+/g, " · ")
      .trim();
    if (/^citation$/i.test(section.title)) {
      // Source, compact: drop the redundant "Card estimate" prefix and the word "vintage".
      body = body.replace(/^Card estimate · /i, "").replace(/\(vintage ([\d-]+)\)/g, "$1");
    }
    if (body) parts.push(`**${label}.** ${body}`);
  }
  return parts.length ? render(parts.join("\n\n")) : "";
}

function paint(answer) {
  if (!answer) return;
  const badge = answer.status === "answered"
    ? `<span class="pill good">answered · ${escapeHtml(answer.shape)}</span>`
    : `<span class="pill bad">${escapeHtml(answer.status)}${answer.refusal_code ? ` · ${escapeHtml(answer.refusal_code)}` : ""}</span>`;
  // Plain first, in ordinary prose and with no label: just the answer. The checking version, with the
  // assumption, the caveats and the citation, sits behind one collapsed control.
  const plain = plainReading(answer);
  const technical = answer.plain && answer.plain.text ? technicalReading(answer.text) : "";
  const tech = technical
    ? `<details class="technical"><summary>Technical</summary><div class="prose">${technical}</div></details>`
    : "";
  panel.innerHTML = `<div class="ask-head">${badge}</div>${render(plain)}${tech}`;
  panel.hidden = false;
}

document.getElementById("ask-clear")?.addEventListener("click", () => {
  input.value = "";
  panel.hidden = true;
  panel.innerHTML = "";
  status.textContent = emptyCopy;
  input.focus();
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  // Snap to the closest measured question before asking. The layer is only measured on its own question set, so
  // submitting free text would be a question nobody scored; the reader sees the snapped text in the field.
  // `datalist.options` is an HTMLCollection in Chromium (truthy, but no .map), so it is converted explicitly.
  const list = document.getElementById("ask-questions");
  const questions = Array.from(list?.options || []).map((option) => option.value);
  const snap = (text) => {
    const words = (s) => new Set((s.toLowerCase().match(/[a-z0-9']+/g) || []));
    const target = words(text);
    let best = "", score = 0;
    for (const candidate of questions) {
      const set = words(candidate);
      let hit = 0;
      target.forEach((w) => { if (set.has(w)) hit += 1; });
      const jaccard = hit / (target.size + set.size - hit);
      if (jaccard > score) { score = jaccard; best = candidate; }
    }
    return score >= 0.34 ? best : text;
  };
  const snapped = snap(input.value.trim());
  if (snapped && snapped !== input.value.trim()) input.value = snapped;
  const question = input.value.trim();
  if (!question) {
    panel.hidden = true;
    status.textContent = emptyCopy;
    return;
  }
  status.textContent = "Reading the corpus…";
  panel.hidden = true;
  try {
    const built = await layer();
    paint(built.answer(question));
    status.textContent = "";
  } catch (error) {
    status.textContent = "The answer layer did not load in this browser. The local app's Ask tab reads the same corpus.";
    panel.hidden = true;
  }
});

// A query string carries a question in, so a link can point at an answer.
const asked = new URLSearchParams(window.location.search).get("q");
if (asked) {
  input.value = asked;
  form.dispatchEvent(new Event("submit"));
}
