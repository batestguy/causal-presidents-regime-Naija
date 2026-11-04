// Demo capture for the published site: one 16:9 take, with a shot log the builder turns into captions.
//
// Usage:
//   set NODE_PATH=%LOCALAPPDATA%\npm-cache\_npx\<hash>\node_modules
//   node tools/record_demo.mjs [desktop]
//
// The site is recorded as published, on the same URL a reader gets. Nothing is typed into the Ask box:
// a demo question would exercise the answer layer against a corpus it is not verifying here, and the
// screen's own text already says what it does.
//
// A mark is written at the instant the frame changes, not after the hold, because a caption that lands
// half a second late reads as a mistake and is invisible in a contact sheet.

import { mkdirSync, writeFileSync, readdirSync } from 'node:fs';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
const { chromium } = require('playwright');

const SITE = process.env.DEMO_SITE ?? 'https://batestguy.github.io/causal-presidents-regime-Naija';
const OUT = 'build/demo';
const which = process.argv[2] ?? 'desktop';

const TAKES = {
  desktop: { viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1, isMobile: false },
  phone: { viewport: { width: 430, height: 932 }, deviceScaleFactor: 2, isMobile: true },
};

mkdirSync(OUT, { recursive: true });

const browser = await chromium.launch({ channel: process.env.DEMO_CHANNEL ?? 'chrome' });
const context = await browser.newContext({
  ...TAKES[which],
  recordVideo: { dir: `${OUT}/raw-${which}`, size: TAKES[which].viewport },
  reducedMotion: 'reduce',
  locale: 'en-GB',
});
const page = await context.newPage();

const t0 = Date.now();
const marks = [];
/** Log a cut: the frame changed to `label` at this instant. */
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
    const stuck = await page.evaluate(() =>
      [...document.images].filter((i) => !(i.complete && i.naturalWidth > 0)).map((i) => i.currentSrc || i.src),
    );
    if (stuck.length) console.warn(`  (still loading after 8s: ${stuck.join(', ')})`);
  }
}

async function go(path) {
  await page.goto(`${SITE}${path}`, { waitUntil: 'commit', timeout: 90000 });
  await page.waitForLoadState('domcontentloaded', { timeout: 30000 }).catch(() => {});
  await imagesReady();
}

/** Scroll a heading into view by its text, because the site keys sections by heading, not by id. */
async function scrollToHeading(text, offset = 90) {
  const found = await page.evaluate(
    ([needle, off]) => {
      const h = [...document.querySelectorAll('h1, h2, h3, h4')].find((e) =>
        (e.textContent || '').toLowerCase().includes(needle.toLowerCase()),
      );
      if (!h) return false;
      window.scrollTo({ top: window.scrollY + h.getBoundingClientRect().top - off, behavior: 'instant' });
      return true;
    },
    [text, offset],
  );
  if (!found) throw new Error(`no heading matching ${text}`);
  await page.waitForTimeout(250);
}

async function expectText(needle, where) {
  const ok = await page.evaluate((n) => document.body.innerText.includes(n), needle);
  if (!ok) throw new Error(`${where}: expected to find ${needle!r} on screen`);
}

// 1. Home
await go('/');
await cut('home hero', 'the premise and the five administrations', 3000);

// 2. The study screen: twelve outcomes with their coverage.
await go('/study/');
await cut('the study screen', 'twelve outcomes, coverage stated', 2600);

// 3. What gets compared, for two outcomes.
await go('/compare/?outcomes=u5mr,fatalities');
await cut('what gets compared', 'two outcomes, each with its assumption', 2800);

// 4. The graph and the adjustment set.
await go('/graph/?outcomes=u5mr');
await cut('the assumption', 'computed by dagitty, not hand-listed', 3000);

// 5. The refused card: no number, and the reason.
await go('/estimates/?outcomes=u5mr');
await expectText('Widest trend gap', 'the refused card');
await cut('the estimate refused', 'no number, one descriptive line', 3200);

// 6. The card that carries a number.
await go('/estimates/?outcomes=fatalities');
await expectText('1 % higher federal allocation', 'the published card');
await expectText('0.4678', 'the published card');
await cut('the estimate published', 'a number, its interval, its failed check', 3600);

// 7. The series: breaks and each tenure against the trend.
await go('/chart/?outcomes=u5mr');
await scrollToHeading('When the series changes');
await cut('the series', 'breaks and tenures against the trend', 3400);

// 8. The design-level results: the country comparison that refused.
await go('/designs/');
await scrollToHeading('The synthetic counterfactual');
await expectText('fitted a second way', 'the design-level results');
await cut('the design-level results', '99 countries, four windows, none identified', 3800);

// 9. What it does not claim.
await go('/methodology/');
await scrollToHeading('What it does not claim');
await cut('what it does not claim', 'a 99-country match was tried and refused', 3200);

// 10. End card, drawn in the site's own colours.
await page.setContent(
  `<!doctype html><html lang="en"><head><meta charset="utf-8"><style>
     html,body{margin:0;height:100%}
     body{background:#008751;color:#eef6f0;font-family:Georgia,'Times New Roman',serif;
          display:flex;align-items:center;justify-content:center;flex-direction:column;gap:22px;
          text-align:center;padding:60px}
     .eyebrow{font-family:'Segoe UI',system-ui,sans-serif;letter-spacing:.28em;text-transform:uppercase;
              font-size:17px;color:#c9e8d8}
     h1{font-size:68px;margin:0;line-height:1.06;font-weight:400}
     .url{font-family:'Segoe UI',system-ui,sans-serif;font-size:28px;color:#eef6f0;
          border-top:1px solid rgba(238,246,240,.5);padding-top:18px}
     .small{font-family:'Segoe UI',system-ui,sans-serif;font-size:17px;line-height:1.7;
            color:#d6ecdf;max-width:1020px}
   </style></head><body>
     <div class="eyebrow">Causal Presidents &middot; Nigeria, 1999 to present</div>
     <h1>Thirty-six model cards.<br>Two published numbers.</h1>
     <div class="url">batestguy.github.io/causal-presidents-regime-Naija</div>
     <div class="small">Every displayed number is a field of a committed artifact.<br>
       Where the design cannot identify an effect, the card says why, and the site carries the reason.</div>
   </body></html>`,
  { waitUntil: 'load' },
);
await cut('end card', '', 3600);

await context.close();
await browser.close();

const webm = readdirSync(`${OUT}/raw-${which}`).find((f) => f.endsWith('.webm'));
writeFileSync(`${OUT}/shots-${which}.json`, JSON.stringify(marks, null, 2));
console.log(`\nraw video: ${OUT}/raw-${which}/${webm}`);
console.log(`shot log:  ${OUT}/shots-${which}.json`);
