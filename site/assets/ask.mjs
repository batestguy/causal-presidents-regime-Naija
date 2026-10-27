/**
 * The Ask screen: the same answer layer the local app runs, over the published corpus.
 *
 * It loads three same-origin JSON files the build emits (the gate's rules, the contract and glossary, the
 * corpus) and the layer module. No model, no network call, no database — and no rule of its own: this file
 * only puts the answer on the page.
 */

import { loadLayer } from "./answer.mjs";

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

function paint(answer) {
  if (!answer) return;
  const badge = answer.status === "answered"
    ? `<span class="pill good">answered · ${escapeHtml(answer.shape)}</span>`
    : `<span class="pill bad">${escapeHtml(answer.status)}${answer.refusal_code ? ` · ${escapeHtml(answer.refusal_code)}` : ""}</span>`;
  const plain = (answer.plain && answer.plain.text) ? `<details class="technical"><summary>The plain reading</summary><div class="prose">${render(answer.plain.text)}</div></details>` : "";
  panel.innerHTML = `<div class="ask-head">${badge}</div>${render(answer.text)}${plain}`;
  panel.hidden = false;
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
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
