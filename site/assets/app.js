// Guided flow — page behaviour.
//
// Four behaviours, no framework, no dependency, no network:
//   1. the cover's portraits move horizontally (scroll-snap, arrow buttons, drag, and a slow auto-advance that
//      pauses on hover, focus or a click and can be stopped outright — WCAG 2.2.2),
//   2. the study screen enables "Next" only when something is chosen and builds the next address,
//   3. each flow screen reveals the blocks for the outcomes in the query string and carries the query onward
//      and back, and the study screen re-ticks the boxes the query names, so a step back loses nothing,
//   4. the chart screen switches which grouping's captions are shown.
//
// It computes no statistic: every number, word and reason it displays was written into the page by the build
// from the registry artifacts and `analysis/specs/guide.yml`.

const data = (() => {
  const node = document.getElementById("page-data");
  return node ? JSON.parse(node.textContent) : null;
})();

const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)");

// ------------------------------------------------------------------ cover carousel

function initCarousel() {
  const track = document.getElementById("track");
  if (!track) return;
  const slides = Array.from(track.children);
  const motion = document.getElementById("motion");
  let timer = null;
  let running = false;

  const step = () => {
    const first = slides[0];
    const gap = parseFloat(getComputedStyle(track).columnGap || "0") || 0;
    return first ? first.getBoundingClientRect().width + gap : track.clientWidth * 0.8;
  };

  const advance = (direction) => {
    track.scrollBy({ left: direction * step(), behavior: reduceMotion.matches ? "auto" : "smooth" });
  };

  document.getElementById("prev")?.addEventListener("click", () => advance(-1));
  document.getElementById("next")?.addEventListener("click", () => advance(1));

  const stop = () => {
    running = false;
    if (timer) window.clearInterval(timer);
    timer = null;
    if (motion) {
      motion.setAttribute("aria-pressed", "false");
      motion.textContent = "Play";
    }
  };
  const start = () => {
    if (reduceMotion.matches) return;
    running = true;
    timer = window.setInterval(() => {
      const end = track.scrollWidth - track.clientWidth - 4;
      if (track.scrollLeft >= end) {
        track.scrollTo({ left: 0, behavior: "smooth" });
      } else {
        advance(1);
      }
    }, 6000);
    if (motion) {
      motion.setAttribute("aria-pressed", "true");
      motion.textContent = "Pause";
    }
  };

  motion?.addEventListener("click", () => (running ? stop() : start()));
  ["pointerenter", "focusin", "pointerdown", "wheel", "touchstart"].forEach((event) => {
    track.addEventListener(event, stop, { passive: true });
    track.addEventListener(event, stop, true);
  });
  reduceMotion.addEventListener?.("change", () => (reduceMotion.matches ? stop() : null));

  if (!reduceMotion.matches) start();
}

// ------------------------------------------------------------------ study screen

function initStudy() {
  const boxes = Array.from(document.querySelectorAll('input[name="outcome"]'));
  const next = document.getElementById("next");
  const note = document.getElementById("next-note");
  if (!boxes.length || !next) return;
  const disabledText = note ? note.textContent : "";

  // The URL is the memory. A reader who comes back here from the flow, or reloads, or opens a bookmark,
  // finds the same boxes ticked: the address carried the selection, and the selection drives the page.
  const remembered = (new URLSearchParams(window.location.search).get("outcomes") || "")
    .split(",").map((s) => s.trim()).filter(Boolean);
  const select = document.getElementById("domain-select");
  boxes.forEach((box) => {
    if (!remembered.includes(box.value)) return;
    box.checked = true;
    // If the restored box sits behind another category, surface that category.
    const section = box.closest(".domain[data-domain]");
    if (select && section) select.value = section.dataset.domain;
  });

  const update = () => {
    const picked = boxes.filter((box) => box.checked).map((box) => box.value);
    if (picked.length === 0) {
      next.classList.add("is-disabled");
      next.setAttribute("aria-disabled", "true");
      next.setAttribute("href", "#");
      if (note) note.textContent = disabledText;
      return;
    }
    next.classList.remove("is-disabled");
    next.setAttribute("aria-disabled", "false");
    next.setAttribute("href", `../compare/?outcomes=${encodeURIComponent(picked.join(","))}`);
    if (note) note.textContent = `${picked.length} outcome${picked.length > 1 ? "s" : ""} chosen`;
  };

  boxes.forEach((box) => box.addEventListener("change", update));
  update();
}

// ------------------------------------------------------------------ study category

function initDomains() {
  const select = document.getElementById("domain-select");
  if (!select) return;
  const apply = () => {
    document.querySelectorAll(".domain[data-domain]").forEach((section) => {
      section.hidden = section.dataset.domain !== select.value;
    });
  };
  select.addEventListener("change", apply);
  apply();
}

// ------------------------------------------------------------------ flow screens

function initFlow() {
  const blocks = Array.from(document.querySelectorAll(".block[data-outcome]"));
  if (!blocks.length) return;
  const params = new URLSearchParams(window.location.search);
  const wanted = (params.get("outcomes") || "").split(",").map((s) => s.trim()).filter(Boolean);
  const chosen = blocks.filter((block) => wanted.includes(block.dataset.outcome));
  blocks.forEach((block) => (block.hidden = true));
  chosen.forEach((block) => (block.hidden = false));

  const note = document.getElementById("count-note");
  const next = document.getElementById("next");
  const query = `?outcomes=${encodeURIComponent(wanted.join(","))}`;

  if (chosen.length === 0) {
    if (next) {
      next.classList.add("is-disabled");
      next.setAttribute("aria-disabled", "true");
      next.setAttribute("href", "#");
    }
    return;
  }

  // Both controls carry the selection, back and forth: the address is the memory, so no step of the flow
  // can strip it. (D-16: a real URL per step, with Back and Next links that carry the selection.)
  document.querySelectorAll(".controls a.ghost").forEach((link) => {
    const target = link.getAttribute("href") || "";
    if (target && target !== "#" && !target.includes("outcomes=")) {
      link.setAttribute("href", `${target.replace(/\/$/, "")}/${query}`);
    }
  });
  if (note) note.textContent = `${chosen.length} outcome${chosen.length > 1 ? "s" : ""} chosen`;
  if (next) {
    const target = next.getAttribute("href") || "";
    if (target && target !== "#") next.setAttribute("href", `${target.replace(/\/$/, "")}/${query}`);
    next.classList.remove("is-disabled");
    next.removeAttribute("aria-disabled");
  }

  // The details panels ("the other graphs", "the technical version") stay shut until asked for, so a reader
  // meets the assumption before the specification — the same order the app keeps.
  chosen.forEach((block) => {
    block.querySelectorAll("details").forEach((details) => details.classList.add("is-folded"));
  });
}

// The Ask screen has no per-outcome blocks, so initFlow returns before it is reached; its Back link still
// carries the selection to the chart, so the reader's step back does not empty the flow.
function initAskCarry() {
  const wanted = (new URLSearchParams(window.location.search).get("outcomes") || "")
    .split(",").map((s) => s.trim()).filter(Boolean);
  if (!wanted.length) return;
  document.querySelectorAll(".controls a.ghost").forEach((link) => {
    const target = link.getAttribute("href") || "";
    if (target && target !== "#" && !target.includes("outcomes=")) {
      link.setAttribute("href", `${target.replace(/\/$/, "")}/?outcomes=${encodeURIComponent(wanted.join(","))}`);
    }
  });
}

// ------------------------------------------------------------------ chart grouping

function initGrouping() {
  const radios = Array.from(document.querySelectorAll('input[name="grouping"]'));
  if (!radios.length) return;
  const dose = radios.find((radio) => radio.value === "state_dose_quartile");
  const doseLabel = dose?.closest("label");
  const mutedNote = doseLabel?.querySelector(".dose-note");

  // The window follows the radio: the comparison figure stacks the two groupings' panels in one tall
  // image, and the build records the split point it read from the SVG. Without JS, or before the image
  // loads, the whole figure simply shows.
  const windows = Array.from(document.querySelectorAll(".panel-window"));
  const apply = () => {
    const state = radios.find((radio) => radio.checked)?.value;
    document.querySelectorAll(".group-list").forEach((list) => {
      list.hidden = list.dataset.grouping !== state;
    });
    windows.forEach((windowPane) => {
      const img = windowPane.querySelector("img");
      const split = parseFloat(windowPane.dataset.split || "");
      if (!img || !split) return;
      const fit = () => {
        const width = windowPane.clientWidth || img.clientWidth;
        if (!width || !img.naturalWidth) return;
        const displayHeight = width * (img.naturalHeight / img.naturalWidth);
        const showFirst = state === "party_tenure";
        windowPane.style.height = `${Math.round(displayHeight * (showFirst ? split : 1 - split))}px`;
        img.style.transform = showFirst ? "translateY(0)" : `translateY(${-Math.round(displayHeight * split)}px)`;
        windowPane.closest("figure").classList.toggle("state-dose", !showFirst);
      };
      if (img.complete) fit();
      else {
        img.addEventListener("load", fit, { once: true });
        // If the load event raced the script (the SVG was cached and finished before the listener
        // attached), the animation frames catch up once the image is decodable.
        let frames = 0;
        const retry = () => {
          if (img.complete || frames++ > 240) fit();
          else requestAnimationFrame(retry);
        };
        requestAnimationFrame(retry);
      }
    });
  };

  // A dead control is a lie: when none of the outcomes on screen carries a state panel in its figure,
  // the dose radio dims and says why, instead of letting a reader click it and see nothing happen.
  const updateUsable = () => {
    if (!dose) return;
    const visible = Array.from(document.querySelectorAll("article.block")).filter((a) => !a.hidden);
    const anyPanel = visible.some((a) => a.querySelector(".panel-window[data-split]"));
    dose.disabled = !anyPanel;
    doseLabel?.classList.toggle("is-muted", !anyPanel);
  };
  radios.forEach((radio) => radio.addEventListener("change", apply));
  window.addEventListener("resize", apply);
  window.addEventListener("load", apply);
  apply();
  updateUsable();
}

document.addEventListener("DOMContentLoaded", () => {
  initCarousel();
  initStudy();
  initDomains();
  initFlow();
  initAskCarry();
  initGrouping();
});
