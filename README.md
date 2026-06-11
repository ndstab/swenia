# swenia

> *"ai news" backwards.* A personal, **anti-scroll** AI/tech/quantum news digest.

Open it once a day for ~10–15 minutes, get caught up on the frontier — both the major
releases everyone's talking about and the niche research worth knowing — then stop.
No infinite feed. It's designed to **end**: a finite daily digest and a "you're caught
up" screen.

It curates rather than aggregates: an LLM filters a few hundred raw items down to a
ranked, summarized handful against *your* taste profile, killing the SEO/listicle
sludge that generic news apps drown you in.

---

## How it works — two halves

| Half | What it does | Tech |
|---|---|---|
| **Pipeline** (`swenia/`) | Once a day: fetch sources → filter → summarize → freeze a digest | Python |
| **Reader** (`reader/`) | Shows the frozen digest as a swipeable card deck | Vite + React + TS PWA |

They're connected by a single file — **`output/latest.json`** (the "digest contract").
The pipeline writes it; the reader fetches it. Any device reads the same frozen digest.

The pipeline runs three LLM tiers to stay cheap and accurate:
**Haiku** filters the firehose → **Sonnet** writes the cards (from *full article text*,
not thin snippets, so it doesn't hallucinate) → **Opus** is reserved for on-demand deep
dives. Near-duplicate stories are merged with local (free) embeddings; freshness is a
decay score so a big older story can still surface; a SQLite seen-list means each item
shows up once, ever. Runs through the Batch API for ~50% off — roughly **$3–6/month**.

---

## Quick start

### 1. Pipeline (makes the digest)

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt

export ANTHROPIC_API_KEY=sk-ant-api03-...   # see .env.example
.venv/bin/python -m swenia                   # → writes output/latest.json + a terminal preview
```

Flags: `--batch` (Batch API, half price, async) · `--no-store` (don't record seen-state,
re-runnable while testing).

**Tune what you see** by editing the two knobs at the top of `swenia/config.py` —
see [Make it yours](#make-it-yours) below.

### 2. Reader (shows the digest)

```bash
cd reader
npm install
npm run sync     # copies ../output/latest.json into public/
npm run dev      # → http://localhost:5173
```

On your phone, open the URL and **"Add to Home Screen"** to install it as an app.
Swipe through cards, tap to expand, hit "caught up." Tap **"Aa"** to change the font.

---

## Make it yours

swenia is built around *your* interests, not a generic feed. Everything about **what
gets surfaced** lives in two knobs at the very top of **`swenia/config.py`** — edit
them, re-run, and the digest reshapes to you. No other code needs touching.

**1. `TASTE_PROFILE`** — a plain-English description of what you care about. This is the
heart of the curation; the filter model reads it to decide what's a must-know, what's
worth knowing, and what to drop. It's organised as three buckets — *always must-know*,
*also interested in*, and *not interested in (drop)* — written as ordinary prose.
Rewrite it in your own words. A few examples:

- *Robotics engineer* → must-know: humanoid/manipulation releases, new control
  policies, sim-to-real; drop: pure-LLM chatbot news.
- *Biotech / bioinformatics* → must-know: protein/structure models, lab-automation;
  also: new datasets, benchmarks; drop: consumer gadgets.
- *Indie web dev* → must-know: framework releases, browser APIs; drop: academic
  preprints, hardware.

**2. `SOURCES`** — where raw items come from:

| Setting | What it is |
|---|---|
| `RSS_FEEDS` | `(name, url)` pairs — any blog, newsletter, or journal that has an RSS feed |
| `ARXIV_CATEGORIES` | arXiv category codes, e.g. `cs.LG`, `cs.CL`, `quant-ph`, `q-bio` |
| `HN_QUERIES` | Hacker News search terms (only stories above `HN_MIN_POINTS` are pulled) |

After editing, **re-run** `.venv/bin/python -m swenia` to preview your new digest. If
you've deployed (below), just commit + push — the next daily run picks up your changes.

> Optional dials further down in `config.py`: `MAX_CARDS` (digest size), `RECENCY_DAYS`
> (how far back to look), `DECAY_TAU_DAYS` (how fast old news fades). The defaults are
> sensible — start with the two knobs above.

---

## The digest contract (`output/latest.json`)

```jsonc
{
  "date": "2026-06-10",
  "generated_at": "2026-06-10T07:00:00Z",
  "summary_line": "2 must-know · 5 worth knowing",
  "counts": { "total": 15, "headlines": 6, "frontier": 9 },
  "sections": [
    { "key": "headlines", "title": "Headlines", "cards": [ /* … */ ] },
    { "key": "frontier",  "title": "Frontier & Papers", "cards": [ /* … */ ] }
  ]
}
```

Each **card**:
```jsonc
{
  "id": "b0a55051a235",
  "tier": "must_know",          // must_know | worth_knowing | skim
  "category": "headline",       // headline (mainstream) | frontier (research)
  "title": "Claude Fable 5 Released…",
  "why_it_matters": "One line on why THIS reader should care.",
  "summary": "40–60 word factual blurb.",
  "tags": ["anthropic", "claude"],
  "sources": [{ "name": "Interconnects", "url": "https://…" }],
  "published": "2026-06-09T15:16:25+00:00",
  "score": 2.19
}
```

---

## Deploying

The intended home is **your personal GitHub**: the included GitHub Actions workflow
(`.github/workflows/daily.yml`) runs the pipeline on a daily cron and commits a fresh
`latest.json` (+ seen-state) back to the repo; point **Vercel** at the `reader/`
directory and it auto-deploys on every push. You only need to add your
`ANTHROPIC_API_KEY` as a repo **Actions secret** and enable read/write workflow
permissions.

## Project docs

- **[CLAUDE.md](./CLAUDE.md)** — full context for AI coding agents (architecture,
  decisions, gotchas). Auto-loads in Claude Code.

## Status

Phase 0 (curation) ✅ · Phase 1 (pipeline) ✅ · Phase 2 (reader) ✅ ·
Phase 3 (deploy) — configs ready, run from your laptop · Phase 4 (feedback loop,
deep dives, audio) — planned.
