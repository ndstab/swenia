// Copy the pipeline's freshly-built digest into the reader's public/ so the
// dev server (and a static build) can fetch /latest.json from the same origin.
//
//   npm run sync          # one-off copy before `npm run dev` / `npm run build`
//
// In production (Phase 3) the digest is published to the deploy output instead;
// see the deploy notes. This script is the local dev bridge between the two
// halves (Python pipeline → React reader).
import { copyFileSync, existsSync, mkdirSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const src = resolve(here, "../../output/latest.json");
const destDir = resolve(here, "../public");
const dest = resolve(destDir, "latest.json");

if (!existsSync(src)) {
  console.error(
    `✗ no digest at ${src}\n  Run the pipeline first:  .venv/bin/python -m swenia`,
  );
  process.exit(1);
}
mkdirSync(destDir, { recursive: true });
copyFileSync(src, dest);
console.log(`✓ synced digest → public/latest.json`);
