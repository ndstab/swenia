# swenia — project context for Claude Code

> 👉 **If this project was just transferred to a new machine: read `START_HERE.md` first.**
> It is the exact, ordered playbook to get running + deployed with minimal tokens.
> This file (CLAUDE.md) is your reference; START_HERE.md is your to-do list.


**swenia** ("ai news" reversed) is a **personal, anti-scroll AI/tech/quantum news digest**.
Open it once a day for ~10–15 min, get caught up on niche + mainstream frontier AI,
then *stop*. It is built to **end** (finite daily digest, "you're caught up" screen) —
no infinite feed. Built for one user (an AI/research engineer), but should be
shareable.

The product is **curation, not aggregation**: surfacing what matters (both the big
mainstream releases everyone discusses *and* niche frontier research) while killing
SEO/listicle sludge.

---

## Architecture — two halves

The thing that *makes* the digest and the thing that *shows* it are decoupled.

```
PIPELINE (backend, Python)              READER (frontend, the PWA)
"makes the digest"                      "shows the digest"
  fetch sources                           any device opens the app
   → select (recency + balance)           → fetch(/latest.json)
   → filter unseen (SQLite)               → swipe-deck of cards
   → tier+categorize (Haiku)              → "you're caught up" end screen
   → cluster dups (embeddings)
   → fetch full article text
   → write cards (Sonnet)         ┌──────────────────────┐
   → score (recency decay)        │  output/latest.json  │ ← the CONTRACT
   → write latest.json  ──────────▶│  (frozen daily digest)│ ──▶ reader fetches this
                                   └──────────────────────┘
```

The only interface between halves is **`output/latest.json`** (the "digest contract").
Get that shape right and the two halves evolve independently.

---

## Layout

```
swenia/                 # ── the PIPELINE (Python package) ──
  config.py             #   the TWO KNOBS: SOURCES + TASTE_PROFILE, plus tunables & paths
  models.py             #   Item dataclass (+ card_dict() → digest contract), Source
  sources.py            #   fetch RSS / arXiv / HN → Item[]
  fulltext.py           #   fetch real article body (trafilatura) — the ACCURACY FIX
  ranking.py            #   select() recency+balance, cluster() embeddings dedup, score() decay
  store.py              #   SQLite seen-state: each item shown once ever
  llm.py                #   Haiku filter (tier+category) & Sonnet cards: prompts/schemas/handlers
  runner.py             #   run_sync (dev) / run_batch (Batch API, 50% cheaper)
  digest.py             #   build + write output/latest.json + archive/YYYY-MM-DD.json
  pipeline.py           #   orchestrates everything; rich terminal preview
  __main__.py           #   `python -m swenia`

reader/                 # ── the READER (Vite + React + TS PWA) ──
  src/digest.ts         #   TS mirror of the digest contract + loadDigest/toDeck
  src/App.tsx           #   load → swipe deck → caught-up; header, progress pips, font picker
  src/SwipeCard.tsx     #   framer-motion drag-to-dismiss + tap-to-expand card
  src/CaughtUp.tsx      #   "you're caught up" end screen
  src/fonts.ts          #   font themes (default Space Grotesk) + live picker logic
  src/FontPicker.tsx    #   "Aa" bottom-sheet font switcher
  src/app.css/index.css #   minimal monochrome styles (auto dark/light)
  scripts/sync-digest.mjs  # `npm run sync`: copy pipeline output/latest.json → reader/public/

output/latest.json      # the current digest (the contract the reader fetches)
spike.py                # Phase 0 throwaway spike (kept for reference; superseded by swenia/)
check_key.py            # diagnoses ANTHROPIC_API_KEY issues without leaking the secret
verify_phase1.py        # offline pipeline verification (mocks the LLM calls)
```

---

## How to run

**Pipeline** (needs `ANTHROPIC_API_KEY` in env; Python 3.12+, a venv is used because
Homebrew Python is externally-managed):
```bash
python -m venv .venv && .venv/bin/pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-api03-...        # real API key, NOT an OAuth/subscription token
.venv/bin/python -m swenia                        # sync calls + terminal preview + writes latest.json
.venv/bin/python -m swenia --batch                # use Batch API (half price, async ~1h)
.venv/bin/python -m swenia --no-store             # don't record seen-state (re-runnable for testing)
```

**Reader:**
```bash
cd reader && npm install
npm run sync     # copy ../output/latest.json into public/
npm run dev      # localhost:5173 — open, "Add to Home Screen" to install as PWA
npm run build    # production build (tsc + vite)
```

---

## Locked decisions (do not relitigate without reason)

- **Models, 3 tiers:** Haiku (`claude-haiku-4-5`) filters raw items → Sonnet
  (`claude-sonnet-4-6`) writes cards → Opus (`claude-opus-4-8`) reserved for on-demand
  deep dives (Phase 4). Filter+cards go through the **Batch API** (50% off) in prod.
- **Embeddings are LOCAL.** Anthropic has no embeddings endpoint. Use `fastembed`
  (`BAAI/bge-small-en-v1.5`, ONNX, no torch — installs on Python 3.14). Cosine ≥0.80
  = near-duplicate. Free, runs on CPU.
- **Accuracy via full text.** The summarizer reads the real article body
  (`fulltext.py`), NOT the thin RSS snippet. This is the #1 correctness mechanism —
  see "Accuracy" below. Never revert to summarizing from snippets.
- **Curation principle:** importance = mainstream significance **OR** niche frontier
  signal. NEVER penalize an item for being popular/widely-covered. The user wants BOTH
  the big releases (Claude Fable 5, Gemma 4 — must-know *because* they're big deals)
  AND deep niche research.
- **Two-section digest:** every card has `category` = **headline** (mainstream
  big-deal) or **frontier** (deeper research/papers). Reader shows them as two decks.
  Tier (`must_know`/`worth_knowing`/`skim`) and category are independent.
- **Freshness = decay score**, not a hard gate: `tier_weight × exp(-age_days/τ)`.
  A big 4-day-old story can still surface.
- **Catch-up:** show everything UNSEEN since last open (SQLite seen-state), newest first.
- **Reader UX:** Tinder-style one-card-at-a-time swipe deck, **minimal monochrome**,
  default font **Space Grotesk** (switchable via the "Aa" picker).
- **Hosting plan:** personal GitHub. Daily **GitHub Actions cron** runs the pipeline,
  commits `latest.json` + seen-state back to the repo; reader auto-deploys on **Vercel**.
  (Set up from the user's personal laptop — see DEPLOY.md.)

## The two tuning knobs

Everything about *what* gets surfaced lives at the top of `swenia/config.py`:
- **`TASTE_PROFILE`** — the heart of curation (what's interesting to this reader).
- **`SOURCES`** — `RSS_FEEDS` / `ARXIV_CATEGORIES` / `HN_QUERIES`.

## Accuracy (the thing the project lives or dies on)

A confidently-wrong summary is worse than useless. History: the early spike
summarized from thin RSS teasers and **hallucinated** — e.g. expanded "RSI"
(recursive self-improvement) as "repetitive strain injury" and invented a story.
Fix: fetch the full article (`fulltext.py`) so the model summarizes real content.
**Verified** via a 15-source adversarial fact-check: 0 hallucinations, 12/15 fully
accurate. Residual (much safer) failure mode: occasional *compression* imprecision
(merging two stats) — guarded against in the `llm.py` card prompt. If you touch
summarization, re-run a fact-check before trusting it.

## Gotchas

- Use a real **API key** (`sk-ant-api03-…`), not an OAuth/subscription token
  (`sk-ant-oat…`) — the latter 400s as `x-api-key`. `check_key.py` diagnoses this.
- Python 3.14 argparse: a bare `%` in a help string is a hard error (`%c requires…`).
- Verifying the reader: **measure the DOM via Chrome DevTools Protocol**, not headless
  `--screenshot` — headless screenshots served stale cached rasters here (identical
  byte counts across rebuilds). Use CDP `Runtime.evaluate` for layout truth.
- Seen-state DB is per-machine; on GitHub Actions the runner is ephemeral, so the
  daily workflow must commit the DB (or a seen-list) back to the repo — see DEPLOY.md.

## Status

- ✅ Phase 0 — curation spike (proved the idea)
- ✅ Phase 1 — pipeline (built, fact-checked, 0 hallucinations)
- ✅ Phase 2 — PWA reader (swipe deck + font picker, DOM-verified)
- ⬜ Phase 3 — deploy on personal GitHub (configs written in DEPLOY.md, run from laptop)
- ⬜ Phase 4 — feedback loop (👍/👎 → profile), Opus deep-dives, audio/TTS, story threads
- ⬜ Design polish — explore more appealing visual directions (planned, share-ready)
