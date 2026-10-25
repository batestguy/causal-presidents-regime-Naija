// Guided flow — page behaviour.
//
// Four behaviours, no framework, no dependency, no network:
//   1. the cover's portraits move horizontally (scroll-snap, arrow buttons, drag, and a slow auto-advance that
//      pauses on hover, focus or a click and can be stopped outright — WCAG 2.2.2),
//   2. the study screen enables "Next" only when something is chosen and builds the next address,
//   3. each flow screen reveals the blocks for the outcomes in the query string and carries the query onward,
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
  if (note) note.textContent = `${chosen.length} outcome${chosen.length > 1 ? "s" : ""} · ${note.textContent}`;
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

// ------------------------------------------------------------------ chart grouping

function initGrouping() {
  const radios = Array.from(document.querySelectorAll('input[name="grouping"]'));
  if (!radios.length) return;
  const apply = () => {
    const value = radios.find((radio) => radio.checked)?.value;
    document.querySelectorAll(".group-list").forEach((list) => {
      list.hidden = list.dataset.grouping !== value;
    });
  };
  radios.forEach((radio) => radio.addEventListener("change", apply));
  apply();
}

document.addEventListener("DOMContentLoaded", () => {
  initCarousel();
  initStudy();
  initFlow();
  initGrouping();
});
