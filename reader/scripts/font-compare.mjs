// Generate a side-by-side font comparison page from the live FONT_THEMES list.
// Renders a real swenia card in every font so you can judge reading feel at a glance.
//   node scripts/font-compare.mjs   →   font-compare.html (open it in a browser)
import { writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { FONT_THEMES } from "../src/fonts.ts";

const here = dirname(fileURLToPath(import.meta.url));
const out = resolve(here, "../../design-explorations/font-compare.html");

// one real card (shortened body) for the preview
const CARD = {
  tier: "MUST KNOW",
  category: "HEADLINE",
  title: "Claude Fable 5 Released: Anthropic's Strongest Model Yet",
  why: "A flagship capability jump from a leading lab — the kind of release the entire field will discuss.",
  summary:
    "Anthropic released Claude Fable 5 publicly, a major leap on benchmarks, priced ~2× current Opus models. Reportedly held back 2+ months post-training; some prompts are quietly downgraded to Opus 4.8 via safety filters without user disclosure.",
  tags: ["anthropic", "claude", "frontier models", "safety"],
  source: "Interconnects",
};

// collect all google font families across themes for one <link>
const fams = new Set();
for (const t of FONT_THEMES) (t.google || []).forEach((f) => fams.add(f));
const fontLink = `https://fonts.googleapis.com/css2?${[...fams]
  .map((f) => `family=${f}`)
  .join("&")}&display=swap`;

const cardHTML = (t) => `
  <figure class="cell">
    <figcaption><b>${t.label}</b><span>${t.note}</span></figcaption>
    <article class="card" style="--fd:${t.display.replace(/"/g, "'")};--fb:${t.body.replace(/"/g, "'")}">
      <div class="head"><span class="tier">▪ ${CARD.tier}</span><span class="cat">${CARD.category}</span></div>
      <h2>${CARD.title}</h2>
      <div class="why"><span class="lbl">Why It Matters</span><p>${CARD.why}</p></div>
      <div class="sum"><span class="lbl">Summary</span><p>${CARD.summary}</p></div>
      <div class="foot"><span class="tags">${CARD.tags.map((x) => `<i>${x}</i>`).join("")}</span><span class="src">${CARD.source} ↗</span></div>
    </article>
  </figure>`;

const html = `<!doctype html><html lang="en"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>swenia — font comparison</title>
<link rel="preconnect" href="https://fonts.googleapis.com"/>
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin/>
<link href="${fontLink}" rel="stylesheet"/>
<style>
  :root{--ink:#111;--ink2:#3a3a3a;--ink3:#6e6e6e;--ink4:#9a9a9a;--line:#e0e0e0;--lineS:#cfcfcf;--accent:#e4341e;}
  *{box-sizing:border-box;margin:0;padding:0}
  body{background:#dcdcd8;font-family:ui-sans-serif,system-ui,sans-serif;color:var(--ink);padding:28px 20px 80px}
  h1{font-size:22px;font-weight:700}
  .intro{color:var(--ink3);font-size:14px;margin:6px 0 24px;max-width:640px;line-height:1.5}
  .grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(330px,1fr));gap:22px}
  .cell figcaption{display:flex;flex-direction:column;gap:1px;margin-bottom:8px}
  .cell figcaption b{font-size:13px;letter-spacing:.04em;text-transform:uppercase}
  .cell figcaption span{font-size:12px;color:var(--ink3)}
  .card{background:#fff;border:1px solid var(--ink);padding:18px 16px 15px;display:flex;flex-direction:column}
  .head{display:flex;justify-content:space-between;border-bottom:1px solid var(--line);padding-bottom:9px;margin-bottom:12px;font-family:var(--fd)}
  .tier{font-size:10px;letter-spacing:.15em;font-weight:600;color:var(--accent)}
  .cat{font-size:10px;letter-spacing:.16em;color:var(--ink3);font-weight:500}
  h2{font-family:var(--fd);font-weight:600;font-size:20px;line-height:1.18;letter-spacing:-.01em;margin-bottom:13px}
  .lbl{font-family:var(--fd);font-size:9px;letter-spacing:.18em;text-transform:uppercase;font-weight:600;color:var(--ink3);display:block;margin-bottom:4px}
  .why{border-left:2px solid var(--accent);padding-left:11px;margin-bottom:13px}
  .why p{font-family:var(--fb);font-size:14px;line-height:1.5}
  .sum{border-top:1px solid var(--line);padding-top:11px;margin-bottom:13px}
  .sum p{font-family:var(--fb);font-size:13px;line-height:1.55;color:var(--ink2)}
  .foot{border-top:1px solid var(--ink);padding-top:10px;display:flex;justify-content:space-between;align-items:baseline;gap:8px}
  .tags{display:flex;flex-wrap:wrap;gap:5px}
  .tags i{font-family:var(--fd);font-style:normal;font-size:8.5px;letter-spacing:.08em;text-transform:uppercase;color:var(--ink2);border:1px solid var(--lineS);padding:3px 6px}
  .src{font-family:var(--fd);font-size:10px;font-weight:600;white-space:nowrap}
</style></head><body>
<h1>swenia · font comparison</h1>
<p class="intro">The same card rendered in every font in the picker (${FONT_THEMES.length} total). The reading-optimized serifs are the lower rows — compare how the <em>Summary</em> body text feels for a longer read. Pick the ones you like and I'll trim the picker to those.</p>
<div class="grid">
${FONT_THEMES.map(cardHTML).join("\n")}
</div>
</body></html>`;

writeFileSync(out, html);
console.log(`✓ wrote ${out} (${FONT_THEMES.length} fonts)`);
