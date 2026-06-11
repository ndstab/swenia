# START HERE — instructions for the next Claude Code agent

**You are picking up the `swenia` project on the user's personal laptop.** It was
built on another machine and transferred as a zip. It is **feature-complete**; your
job is to get it running locally and then deployed. Be token-efficient: do NOT
re-explore or re-verify the codebase — it works. Follow the steps below in order.

## First, read these (once, then stop reading)
1. `CLAUDE.md` — full architecture + decisions (this is your context; trust it).
2. This file — the exact steps.
Do not read every source file. Do not re-audit the pipeline or reader. They are done
and were verified on the build machine.

## What's already done (do NOT redo)
- ✅ Python pipeline (`swenia/`) — fetches, filters, summarizes, writes `output/latest.json`. Fact-checked, accurate.
- ✅ React PWA reader (`reader/`) — Swiss Grid design, swipe deck, 4-font picker. Builds clean.
- ✅ All deploy configs written: `.github/workflows/daily.yml`, `reader/vercel.json`, `.gitignore`, `.env.example`, `DEPLOY.md`.
- ✅ A real seed digest is in `output/latest.json` and `reader/public/latest.json`.

## What you must NOT do
- Do NOT commit a real API key or `.env`. The key goes in GitHub Actions secrets only.
- Do NOT rewrite the design, pipeline, or prompts unless the user explicitly asks.
- Do NOT spend tokens re-running verification workflows. Trust the build machine's work.
- Do NOT use `git` if the user says GitHub is blocked on this machine — confirm first (Step 4).

---

## STEP 1 — Sanity check the project is intact (no API key needed)
Run these. They should all succeed without a key:
```bash
cd <swenia-folder>
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cd reader && npm install && npm run build && cd ..
```
If `npm run build` passes, the reader is healthy. If the Python install fails, report the
exact error to the user; otherwise continue. **Do not run the pipeline yet** (needs a key).

## STEP 2 — Get the API key from the user (ask ONCE, clearly)
Ask the user for their Anthropic API key. Tell them exactly:
> "Paste your Anthropic **API key** — it starts with `sk-ant-api03-`. Get it from
> console.anthropic.com → API keys. NOT a Claude subscription/OAuth token (`sk-ant-oat…`),
> which won't work. I'll set it in your shell for this session only, not commit it."

Then have THEM run it (so the key never passes through you):
```bash
export ANTHROPIC_API_KEY=sk-ant-api03-...
```
Suggest they prefix with `! ` in Claude Code so the export lands in this session.
If unsure the key is valid, run `.venv/bin/python check_key.py` (it diagnoses without leaking the secret).

## STEP 3 — Run the pipeline once + preview the reader locally
```bash
.venv/bin/python -m swenia            # builds a fresh output/latest.json + prints the digest
cd reader && npm run sync && npm run dev   # → http://localhost:5173
```
Show the user the localhost URL. Have them open it, swipe through, confirm it looks right.
On their phone (same wifi): `npm run dev -- --host`, then open the Network URL and
"Add to Home Screen" to install as a PWA. **Local milestone reached here.**

## STEP 4 — Confirm the deploy path (ask the user 3 short things, batched)
Ask all three at once:
1. **GitHub username** (for the repo URL).
2. **One repo or two?** Default = one repo (recommended; everything's already laid out for it).
3. **Digest time** — when do they want the daily digest ready? (Convert to UTC cron.
   e.g. 7:00 AM IST = `30 1 * * *`; default in the workflow is `30 6 * * *` = 06:30 UTC.)
If GitHub is blocked on this machine too, stop and tell the user — they may need a
different host (see DEPLOY.md "Alternative hosts").

## STEP 5 — Deploy (follow DEPLOY.md exactly — do not improvise)
`DEPLOY.md` has the full walkthrough. The path is:
1. `git init` → commit → push to their personal GitHub (verify `git status` shows **no `.env`** first).
2. They add `ANTHROPIC_API_KEY` as a repo Actions **secret** (GitHub UI — they do this, not you).
3. They set Actions → Workflow permissions → **Read and write**.
4. Connect the repo to **Vercel**, Root Directory = `reader`. Deploy → get the URL.
5. Seed: either commit the existing `output/latest.json` (already present) or trigger the
   workflow manually (Actions → daily-digest → Run workflow).
If the user picked a custom digest time in Step 4, edit the `cron:` line in
`.github/workflows/daily.yml` before pushing.

## STEP 6 — Confirm it's live
Have the user open the Vercel URL on their phone and install it. Confirm the daily
workflow is scheduled (Actions tab). Done — swenia now runs itself every morning.

---

## If the user wants to go further (Phase 4 — only if they ask)
Feedback loop (👍/👎 → taste profile), Opus on-demand deep-dives, audio/TTS, story
threads. See CLAUDE.md "Status". Don't start these unprompted.

## Token discipline (important)
- The user transferred this to save tokens. Honor that: act, don't re-explain the
  whole project back to them. Reference CLAUDE.md instead of re-deriving it.
- Ask questions in batches (like Step 4), not one at a time.
- Don't run the design-exploration or fact-check workflows again — they're done.
