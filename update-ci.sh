#!/usr/bin/env bash
# update-ci.sh — one-command CI backfill for family-cards-demo.
#
# Run it from the repo root, signed in as the repo owner (Termux or a
# GitHub Codespace):
#   bash update-ci.sh
#
# What it does:
#   1. Installs every staged workflow in ci-src/ (actionlint.yml,
#      lighthouse.yml, links.yml) into .github/workflows/, SKIPPING
#      any file already present — the existing ci.yml in this repo is
#      never overwritten. (The workflows travel at ci-src/ because
#      the Muse GitHub App cannot push files under
#      .github/workflows/; the repo owner can.)
#   2. Deletes itself and ci-src/, and lands the removal plus the
#      installed workflows in ONE cleanup commit, which it pushes.
# It is safe to re-run: installs are idempotent, and after a
# successful run there is nothing left to install.
#
# Divergence notes (deliberate — see the template's BOOTSTRAP-NOTES):
#   * actionlint ships here as a STANDALONE workflow because ci.yml
#     already exists in this repo and must not be overwritten; in
#     the repo-template standard it is a job inside ci.yml.
#   * lighthouse.yml is preset to this demo's public Pages URL and
#     runs REPORT-ONLY (no assertions, never fails a build). The
#     private live repo gets no Lighthouse workflow — its site is
#     behind an access-code gate Lighthouse cannot see past.
set -uo pipefail
cd "$(dirname "$0")"

RESULTS=""
report() { # report <ok|fail|skip> <label>
  local mark="✓"
  [ "$1" = "fail" ] && mark="✗"
  [ "$1" = "skip" ] && mark="–"
  echo "$mark $2"
  RESULTS+="$mark $2"$'\n'
}

echo "== File install =="
if [ -d ci-src ] && ls ci-src/*.yml >/dev/null 2>&1; then
  mkdir -p .github/workflows
  for staged in ci-src/*.yml; do
    base="$(basename "$staged")"
    if [ -f ".github/workflows/$base" ]; then
      report skip "Workflow $base already present (.github/workflows/$base) — not overwritten"
    else
      cp "$staged" ".github/workflows/$base"
      report ok "Workflow installed (.github/workflows/$base)"
    fi
  done
else
  report skip "No staged workflows found (ci-src/*.yml) — nothing to install"
fi

echo ""
echo "== Summary =="
printf '%s' "$RESULTS"

echo ""
echo "== Cleanup =="
# One commit: this script removed, ci-src/ removed, the installed
# workflows added. If the commit or push fails, the installs above
# still stand — tidy the files by hand.
git rm -q update-ci.sh >/dev/null 2>&1 || rm -f update-ci.sh
if [ -d ci-src ]; then
  git rm -rq ci-src >/dev/null 2>&1 || rm -rf ci-src
fi
[ -d .github/workflows ] && git add -- .github/workflows 2>/dev/null || true
git add -A -- update-ci.sh ci-src 2>/dev/null || true
push_cleanup() { # plain push, retrying with an upstream if the branch has none
  git push -q 2>/dev/null || git push -q -u origin "$(git branch --show-current 2>/dev/null || echo main)"
}
if git diff --cached --quiet; then
  echo "Nothing staged — cleanup already done."
elif git commit -q -m "Install backfilled workflows (via update-ci.sh)" && push_cleanup; then
  echo "Cleanup committed and pushed."
else
  echo "NOTE: couldn't commit/push the cleanup. Everything above still applied;"
  echo "commit the removal of update-ci.sh + ci-src/ by hand whenever convenient."
fi
