# Deploying swenia (from your personal laptop)

The goal: swenia runs itself every morning — a daily job builds a fresh digest and
your phone reads it — all on **your personal GitHub + Vercel**, free.

You do this from your **personal laptop** (not the work PC). Everything's already
configured in the repo; you just connect the accounts and add the secret.

```
GitHub Actions cron (daily)              Vercel (hosts the reader)
  runs the Python pipeline                 rebuilds on every push
  → writes output/latest.json              → serves the PWA + /latest.json
  → copies it to reader/public/            → your phone fetches it
  → commits latest.json + seen-state ──────▶ (push triggers redeploy)
```

---

## One-time setup

### 1. Push to your personal GitHub
```bash
cd swenia
git init
git add .
git commit -m "swenia: initial"
git branch -M main
git remote add origin https://github.com/<you>/swenia.git
git push -u origin main
```
> The `.gitignore` already excludes `.env`, `.venv/`, `node_modules/`, etc.
> Double-check `git status` shows **no `.env`** before the first push.

### 2. Add your API key as a GitHub secret
Repo → **Settings → Secrets and variables → Actions → New repository secret**
- Name: `ANTHROPIC_API_KEY`
- Value: your real key (`sk-ant-api03-…`)

### 3. Let the workflow commit back
Repo → **Settings → Actions → General → Workflow permissions** →
select **"Read and write permissions"** → Save.
(This lets the daily job push the new digest + seen-state.)

### 4. Connect Vercel (hosts the reader)
- Sign in to **vercel.com** with your GitHub.
- **Add New → Project →** import the `swenia` repo.
- **Root Directory:** set to **`reader`**.
- Framework preset auto-detects **Vite**. Build/output are already in `reader/vercel.json`.
- Deploy. You'll get a URL like `https://swenia-<you>.vercel.app`.
- On your phone, open it → **Add to Home Screen**.

### 5. (First run) seed a digest
The reader needs a `latest.json` to show. Either:
- **Run the pipeline once locally** and commit the result:
  ```bash
  export ANTHROPIC_API_KEY=sk-ant-api03-...
  .venv/bin/python -m swenia --batch
  cp output/latest.json reader/public/latest.json
  git add -f output/latest.json reader/public/latest.json data/swenia.db
  git commit -m "seed: first digest" && git push
  ```
- **Or** trigger the workflow manually: repo → **Actions → daily-digest → Run workflow**.

---

## How it runs after setup

- **Schedule:** `.github/workflows/daily.yml` runs at **06:30 UTC** daily
  (edit the `cron:` line for your timezone). Also runnable on demand from the Actions tab.
- Each run: pipeline (`--batch`) → commit `latest.json` + `data/swenia.db` →
  Vercel sees the push → redeploys the reader. Your phone shows the new digest.
- **"Nothing new" days:** the workflow detects no changes and skips the commit — no
  empty redeploys.

## Notes & gotchas

- **Seen-state persistence:** the runner is ephemeral, so the workflow commits
  `data/swenia.db` back to the repo — that's what makes "everything since last open"
  work across days. Don't remove that step.
- **Cost:** Batch API ≈ half price; a daily run is a few cents → ~$3–6/month.
- **Tuning:** edit `swenia/config.py` (`TASTE_PROFILE`, `SOURCES`), commit, push. Next
  run uses the new settings.
- **Secrets:** the API key lives ONLY in GitHub Actions secrets — never in the repo,
  never in a committed `.env`.
- **Timezone:** GitHub cron is UTC. For a 7:00 AM IST digest, use `30 1 * * *`
  (01:30 UTC). Pick a time a bit before you usually read.

## Alternative hosts (if you ever move off GitHub/Vercel)

The two halves only need: (a) something that runs Python daily, (b) something that
serves the reader + `latest.json`. A single small VPS (cron + Caddy) does both; or a
serverless scheduled container writing to object storage + any static host. See
CLAUDE.md for the architecture if you want to re-home it.
