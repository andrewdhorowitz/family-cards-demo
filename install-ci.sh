#!/usr/bin/env bash
# One-command CI installer for this repo.
#
# The workflow file (.github/workflows/ci.yml) has to be added by the repo
# owner, so the CI files are staged under ci-src/ and this script moves them
# into place, removes the staging (including itself), and commits + pushes.
#
# Run from anywhere in the repo (e.g. a GitHub Codespace terminal):
#   bash install-ci.sh
set -euo pipefail
cd "$(dirname "$0")"

if [ -d ci-src ]; then
  mkdir -p .github/workflows
  cp ci-src/ci.yml .github/workflows/ci.yml
  cp ci-src/cards.schema.json ./cards.schema.json
  cp ci-src/ruff.toml ./ruff.toml
  rm -rf ci-src
  echo "Installed the staged files:"
  echo "  ci-src/ci.yml            -> .github/workflows/ci.yml"
  echo "  ci-src/cards.schema.json -> cards.schema.json"
  echo "  ci-src/ruff.toml         -> ruff.toml"
else
  echo "ci-src/ not found — the files may already be installed; tidying up anyway."
fi

# Self-cleanup: the staging and this script should not stay in the repo.
rm -f install-ci.sh

git add -A
if git diff --cached --quiet; then
  echo "Nothing to commit — CI is already in place."
  exit 0
fi
git commit -m "Add CI workflow, schema, and ruff baseline (via install-ci.sh)"
git push

echo ""
echo "Done! CI is installed:"
echo "  - .github/workflows/ci.yml  (the checks)"
echo "  - cards.schema.json         (data shape the checks validate against)"
echo "  - ruff.toml                 (lint baseline)"
echo "Open the repo's Actions tab — the first CI run should show up there shortly."
