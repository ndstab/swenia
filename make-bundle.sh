#!/usr/bin/env bash
# Build a clean handoff zip of swenia for transfer to your personal laptop.
# Excludes secrets, virtualenvs, node_modules, local DB, build output, caches.
#
#   bash make-bundle.sh            # → ../swenia-bundle-YYYYMMDD.zip
#
# On the other machine: unzip, then follow README.md (run) / DEPLOY.md (host).
set -euo pipefail

cd "$(dirname "$0")"
SRC_NAME="$(basename "$PWD")"
STAMP="$(date -u +%Y%m%d)"
OUT="../swenia-bundle-${STAMP}.zip"

# Safety: never bundle a real .env.
if [ -f .env ]; then
  echo "⚠  A .env exists. It will be EXCLUDED from the bundle (good)."
fi

rm -f "$OUT"

# zip everything under this dir, minus the excludes. -x patterns are relative
# to the zip root (which is this directory's contents).
zip -r -q "$OUT" . \
  -x '.git/*' \
  -x '.cursor/*' \
  -x '.env' \
  -x '*.key' -x '*.pem' \
  -x '.venv/*' \
  -x '*/__pycache__/*' -x '__pycache__/*' -x '*.pyc' \
  -x 'reader/node_modules/*' \
  -x 'reader/dist/*' \
  -x 'reader/.vite/*' \
  -x 'data/*' \
  -x '*.DS_Store'

echo "✓ wrote $OUT"
echo "  contents (top level):"
unzip -Z1 "$OUT" | sed 's#/.*##' | sort -u | sed 's/^/    /'
echo
echo "  sanity — these must NOT appear above: .env, .venv, node_modules, data, *.pyc"
if unzip -Z1 "$OUT" | grep -qE '(^|/)\.env$|/\.venv/|/node_modules/|(^|/)data/|\.pyc$'; then
  echo "  ✗ BUNDLE CONTAINS EXCLUDED FILES — inspect before transferring!"
  exit 1
else
  echo "  ✓ clean — no secrets/venv/node_modules/db/pyc in the bundle."
fi
