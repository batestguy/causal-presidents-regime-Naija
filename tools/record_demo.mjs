// Demo capture: a real walk through the built site, with the pointer, the clicks and the scrolling.
//
// Usage:
//   set NODE_PATH=%LOCALAPPDATA%\npm-cache\_npx\<hash>\node_modules
//   node tools/record_demo.mjs [desktop]
//
// Two selection passes, because the estimate screen leads with the cards that carry a number and collapses
// the rest behind one line. Pass one picks two refused outcomes and walks the flow to the chart; pass two
// picks the one outcome with a published figure so the number card, its interval and its failed check are on
// screen. Everything else - the graph, the expanders, the grouping switch, the Ask box - is exercised once.
//
// A mark is written at the instant the frame changes, not after the hold. `cut()` is called the moment the
// new state is on screen; the hold that follows is the shot's duration, and the builder's caption window runs
// from one mark to the next.

import { mkdirSync, writeFileSync, readdirSync, rmSync } from 'node:fs';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
const { chromium } = require('playwright');

const SITE = process.env.DEMO_SITE ?? 'http://127.0.0.1:8765';
const OUT = 'build/demo';
const which = process.argv[2] ?? 'desktop';

const TAKES = {
  desktop: { viewport: { width: 1600, height: 900 }, deviceScaleFactor: 1, isMobile: false },
  phone: { viewport: { width: 430, height: 932 }, deviceScaleFactor: 2, isMobile: true },
};

rmSync(`${OUT}/raw-${which}`, { recursive: true, force: true });
mkdirSync(`${OUT}/raw-${which}`, { recursive: true });

const browser = await chromium.launch({ channel: process.env.DEMO_CHANNEL ?? 'chrome' });
const context = await browser.newContext({
  ...TAKES[which],
  recordVideo: { dir: `${OUT}/raw-${which}`, size: TAKES[which].viewport },
  reducedMotion: 'reduce',
  locale: 'en-GB',
});
const page = await context.newPage();
// A demo must not sit still for thirty seconds because one control was styled off-screen; every action
// fails fast and the take keeps moving.
page.setDefaultTimeout(6000);

const t0 = Date.now();
const marks = [];
function cut(label, note = '', holdMs = 2200) {
  const at = +((Date.now() - t0) / 1000).toFixed(2);
  marks.push({ label, at, note });
  console.log(`${String(at).padStart(6)}s  ${label}${note ? '  — ' + note : ''}  (+${holdMs}ms)`);
  return page.waitForTimeout(holdMs);
}

async function imagesReady() {
  try {
    await page.waitForFunction(
      () => {
        const inView = [...document.images].filter((i) => {
          const r = i.getBoundingClientRect();
          return r.bottom > 0 && r.top < innerHeight;
        });
        return inView.length > 0 && inView.every((i) => i.complete && i.naturalWidth > 0);
      },
      null,
      { timeout: 8000, polling: 150 },
    );
  } catch {
    /* a slow image is not worth stalling a take for */
  }
}

async function go(path) {
  await page.goto(`${SITE}${path}`, { waitUntil: 'commit', timeout: 90000 });
  await page.waitForLoadState('domcontentloaded', { timeout: 30000 }).catch(() => {});
  await imagesReady();
  await page.waitForTimeout(400);
}

/** A smooth scroll the viewer can follow, rather than a teleport between frames. */
async function scrollTo(selectorOrY, offset = 110, settle = 900) {
  await page.evaluate(
    ([target, off]) => {
      const y =
        typeof target === 'number'
          ? target
          : (() => {
              const el = document.querySelector(target);
              if (!el) throw new Error(`no element for ${target}`);
              return window.scrollY + el.getBoundingClientRect().top - off;
            })();
      window.scrollTo({ top: y, behavior: 'smooth' });
    },
    [selectorOrY, offset],
  );
  await page.waitForTimeout(settle);
}

async function scrollBy(px, settle = 900) {
  await page.evaluate((d) => window.scrollBy({ top: d, behavior: 'smooth' }), px);
  await page.waitForTimeout(settle);
}

async function expectText(needle, where) {
  const ok = await page.evaluate((n) => document.body.innerText.includes(n), needle);
  if (!ok) throw new Error(`${where}: expected to find ${needle} on screen`);
}

// ---------------------------------------------------------------- 1. home
await go('/');
await page.hover('.president:nth-child(3)').catch(() => {});
await cut('home', 'hover a portrait', 3200);
await scrollBy(520, 1100);
await cut('home scrolled', 'the premise, and the photographs behind it', 3000);
await scrollBy(360, 1000);
await cut('home about', 'about this study, and the credits', 2400);
await page.evaluate(() => window.scrollTo({ top: 0, behavior: 'instant' }));
await page.waitForTimeout(500);
await page.click('a.primary');            // Begin
await page.waitForLoadState('domcontentloaded');
await imagesReady();

// ---------------------------------------------------------------- 2. study: two outcomes
await cut('study', 'twelve outcomes, coverage stated', 1600);
await page.click('#pick-u5mr');
await page.waitForTimeout(450);
await page.click('#pick-mmr');
await page.waitForTimeout(600);
await scrollBy(420, 900);
await cut('study chosen', 'two outcomes ticked, Next enabled', 2200);
await page.click('#next');
await page.waitForLoadState('domcontentloaded');

// ---------------------------------------------------------------- 3. compare
await cut('compare', 'what gets compared, assuming what', 2400);
await scrollBy(700, 900);
await cut('compare scrolled', 'each outcome, one sentence', 2000);

// ---------------------------------------------------------------- 4. graph
await go('/graph/?outcomes=u5mr,mmr');
await cut('graph', 'the assumption, drawn', 2200);
await scrollBy(620, 900);
await cut('graph adjustment', 'the adjustment set, computed from the graph', 2400);

// ---------------------------------------------------------------- 5. estimates: two refused cards
await go('/estimates/?outcomes=u5mr,mmr');
await expectText('Widest trend gap', 'the refused card');
await cut('estimate refused', 'no number, and the reason', 2600);
await scrollBy(300, 900);
await cut('estimate second', 'the second outcome, the same shape', 2600);

// ---------------------------------------------------------------- 6. chart: two outcomes, grouping switch
await go('/chart/?outcomes=u5mr,mmr');
await cut('chart', 'the series, drawn', 2200);
await scrollTo('h3 + p, .block h3', 90, 900).catch(() => {});
await scrollBy(560, 900);
await cut('chart breaks', 'when the series changes', 2600);
// The radios are visually hidden behind their labels, so the label is what a person clicks.
await page.getByText('by how much money a state received').click({ timeout: 5000 }).catch(() => {});
await page.waitForTimeout(900);
await cut('chart grouping', 'the other grouping: no state series for this outcome', 2400);
await page.getByText('by who was in power').click({ timeout: 5000 }).catch(() => {});
await page.waitForTimeout(700);
await scrollBy(900, 1000);
await cut('chart tenure', 'each tenure against the trend', 2800);

// ---------------------------------------------------------------- 7. the number: one outcome with a figure
await go('/study/?outcomes=fatalities');
await cut('study one', 'one outcome, the one with a published figure', 2200);
await page.click('#next');
await page.waitForLoadState('domcontentloaded');
await go('/estimates/?outcomes=fatalities');
await expectText('1 % higher federal allocation', 'the published card');
await cut('estimate published', '+0.4678: what is associated with what', 3000);
await page.locator('details.technical:visible summary').first().click();
await page.waitForTimeout(600);
await scrollBy(300, 800);
await cut('published technical', 'p-value, standard error, formula, covariance', 2800);

// ---------------------------------------------------------------- 8. designs
await go('/designs/');
await cut('designs top', 'the forest plot', 2400);
await scrollBy(700, 950);
await cut('designs grid', '129 specifications: support and flips', 2600);
await scrollTo('h2:nth-of-type(1)', 100, 700).catch(() => {});
await scrollBy(1100, 1000);
await cut('designs synthetic', '99 countries, four windows, none identified', 3000);
await scrollBy(900, 1000);
await cut('designs transitions', 'what moved at a transition', 2400);

// ---------------------------------------------------------------- 9. methodology
await go('/methodology/');
await scrollBy(700, 900);
await cut('methodology', 'what it does not claim', 2800);

// ---------------------------------------------------------------- 10. ask: three questions, three answer shapes
await go('/ask/');
await cut('ask', 'ask the corpus', 1800);
// Three questions whose answers are right, checked against the deployed layer on 2026-11-04. Two of the
// datalist's own suggestions answer badly (the oil-shock question returns the fatality interval; the
// quality-gates one returns a Markdown heading), so they are not used here.
const questions = [
  ['ask one', 'How many of the 36 model cards carry a published number?', 3400],
  ['ask two', "Why can't you tell me whether PDP or APC tenures did better?", 3800],
  ['ask three', 'How much of the monthly data series is actually observed rather than interpolated?', 3800],
];
for (const [label, question, hold] of questions) {
  const previous = await page.evaluate(
    () => (document.querySelector('#ask-answer')?.innerText || '').trim(),
  );
  await page.fill('#ask-input', question);
  await page.waitForTimeout(400);
  await page.click('button.primary[type="submit"]');
  // Wait for the answer to *change*. The panel keeps the previous answer while the new one resolves, so a
  // length test alone passes instantly and the cut lands on the old answer.
  await page.waitForFunction(
    (prev) => {
      const text = (document.querySelector('#ask-answer')?.innerText || '').trim();
      return text.length > 60 && text !== prev;
    },
    previous,
    { timeout: 10000 },
  ).catch(() => {});
  await page.waitForTimeout(500);
  await cut(label, question, hold);
}
await page.locator('details:visible summary').first().click().catch(() => {});
await page.waitForTimeout(600);
await scrollBy(320, 800);
await cut('ask technical', 'the technical section, collapsed by default', 2600);

// ---------------------------------------------------------------- 11. end card
await page.setContent(
  `<!doctype html><html lang="en"><head><meta charset="utf-8"><style>
     html,body{margin:0;height:100%}
     body{background:#008751;color:#eef6f0;font-family:Georgia,'Times New Roman',serif;
          display:flex;align-items:center;justify-content:center;flex-direction:column;gap:22px;
          text-align:center;padding:60px}
     .eyebrow{font-family:'Segoe UI',system-ui,sans-serif;letter-spacing:.28em;text-transform:uppercase;
              font-size:16px;color:#c9e8d8}
     h1{font-size:58px;margin:0;line-height:1.08;font-weight:400}
     .url{font-family:'Segoe UI',system-ui,sans-serif;font-size:26px;color:#eef6f0;
          border-top:1px solid rgba(238,246,240,.5);padding-top:18px}
     .small{font-family:'Segoe UI',system-ui,sans-serif;font-size:16px;line-height:1.7;
            color:#d6ecdf;max-width:1000px}
   </style></head><body>
     <div class="eyebrow">Causal Presidents &middot; Nigeria, 1999 to present</div>
     <h1>Thirty-six model cards.<br>Two published numbers.</h1>
     <div class="url">batestguy.github.io/causal-presidents-regime-Naija</div>
     <div class="small">Every displayed number is a field of a committed artifact.<br>
       Install it from the browser and it reads offline. Where the design cannot identify an effect,
       the card says why.</div>
   </body></html>`,
  { waitUntil: 'load' },
);
await cut('end card', '', 3800);

await context.close();
await browser.close();

const webm = readdirSync(`${OUT}/raw-${which}`).find((f) => f.endsWith('.webm'));
writeFileSync(`${OUT}/shots-${which}.json`, JSON.stringify(marks, null, 2));
console.log(`\nraw video: ${OUT}/raw-${which}/${webm}`);
console.log(`shot log:  ${OUT}/shots-${which}.json`);
