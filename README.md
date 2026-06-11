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

**Tune what you see** by editing the two knobs at the top of `swenia/config.py`:
`TASTE_PROFILE` (what's interesting to you) and `SOURCES` (which feeds).

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

The intended home is **your personal GitHub**: a daily GitHub Actions cron runs the
pipeline and commits a fresh `latest.json` (+ seen-state) back to the repo; the reader
auto-deploys on Vercel. Step-by-step in **[DEPLOY.md](./DEPLOY.md)**.

## Project docs

- **[CLAUDE.md](./CLAUDE.md)** — full context for AI coding agents (architecture,
  decisions, gotchas). Auto-loads in Claude Code.
- **[DEPLOY.md](./DEPLOY.md)** — deployment walkthrough.

## Status

Phase 0 (curation) ✅ · Phase 1 (pipeline) ✅ · Phase 2 (reader) ✅ ·
Phase 3 (deploy) — configs ready, run from your laptop · Phase 4 (feedback loop,
deep dives, audio) — planned.
