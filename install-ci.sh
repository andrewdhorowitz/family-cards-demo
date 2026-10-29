#!/usr/bin/env bash
# One-command CI installer + repo settings for this repo.
#
# The workflow file (.github/workflows/ci.yml) has to be added by the repo
# owner, so the CI files are staged under ci-src/ and this script moves them
# into place, removes the staging (including itself), commits + pushes, and
# then applies the repo's standard settings via the GitHub CLI (gh api).
#
# Run from anywhere in the repo (e.g. a GitHub Codespace terminal):
#   bash install-ci.sh
set -euo pipefail
cd "$(dirname "$0")"

echo "== Installing CI files =="
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
  echo "Nothing to commit — CI files were already in place."
else
  git commit -m "Add CI workflow, schema, and ruff baseline (via install-ci.sh)"
  git push
  echo "Pushed. Now in the repo:"
  echo "  - .github/workflows/ci.yml  (the checks)"
  echo "  - cards.schema.json         (data shape the checks validate against)"
  echo "  - ruff.toml                 (lint baseline)"
fi

echo ""
echo "== Repo settings (via gh api) =="
# Settings are best-effort: a failed step prints a ✗ line and the script
# carries on — the file install above is already done and pushed either way.
RESULTS=""
report() { # report <ok|fail> <label>
  local mark="✓"
  [ "$1" = "fail" ] && mark="✗"
  echo "$mark $2"
  RESULTS+="$mark $2"$'\n'
}
attempt() { # attempt <label> <command...>
  local label="$1"
  shift
  if "$@" >/dev/null 2>&1; then
    report ok "$label"
  else
    report fail "$label (failed — continuing)"
  fi
}

# Work out owner/repo from the git remote instead of hard-coding them.
REMOTE_URL="$(git remote get-url origin 2>/dev/null || true)"
OWNER_REPO="$(printf '%s' "$REMOTE_URL" | sed -E 's#^(git@github\.com:|https://github\.com/)##; s#\.git$##')"
OWNER="${OWNER_REPO%%/*}"
REPO="${OWNER_REPO##*/}"

if ! command -v gh >/dev/null 2>&1 || ! gh auth status >/dev/null 2>&1; then
  echo "Skipped: the GitHub CLI (gh) is missing or not signed in here."
  echo "The CI files above are installed either way; settings can be done in the web UI."
  RESULTS="  – Repo settings skipped (gh unavailable)"$'\n'
elif [ "$OWNER" = "$OWNER_REPO" ] || [ -z "$OWNER" ] || [ -z "$REPO" ]; then
  echo "Skipped: could not read owner/repo from the git remote ($REMOTE_URL)."
  RESULTS="  – Repo settings skipped (remote not parsed)"$'\n'
else
  echo "Repo: $OWNER/$REPO"

  attempt "Wiki + Projects features off" gh api -X PATCH "repos/$OWNER/$REPO" --input - <<'JSON'
{"has_wiki": false, "has_projects": false}
JSON

  attempt "Dependabot alerts on" gh api -X PUT "repos/$OWNER/$REPO/vulnerability-alerts"

  attempt "Dependabot security updates on" gh api -X PUT "repos/$OWNER/$REPO/automated-security-fixes"

  attempt "Secret scanning on" gh api -X PATCH "repos/$OWNER/$REPO" --input - <<'JSON'
{"security_and_analysis": {"secret_scanning": {"status": "enabled"}}}
JSON

  attempt "Secret scanning push protection on" gh api -X PATCH "repos/$OWNER/$REPO" --input - <<'JSON'
{"security_and_analysis": {"secret_scanning_push_protection": {"status": "enabled"}}}
JSON

  attempt "CodeQL default setup on (JavaScript/TypeScript + Python)" gh api -X PATCH "repos/$OWNER/$REPO/code-scanning/default-setup" --input - <<'JSON'
{"state": "configured", "languages": ["javascript-typescript", "python"]}
JSON

  # Main ruleset — only create it if no ruleset already covers the default branch.
  EXISTING="$(gh api "repos/$OWNER/$REPO/rulesets" --jq '[.[] | select(((.conditions.ref_name.include) // []) | index("~DEFAULT_BRANCH"))] | length' 2>/dev/null || echo error)"
  if [ "$EXISTING" != "error" ] && [ "${EXISTING:-0}" -gt 0 ]; then
    report ok "Main ruleset already exists — skipped creating another"
  else
    attempt "Main ruleset 'main-basics' created (blocks deletions + force pushes; repo admins always bypass)" gh api -X POST "repos/$OWNER/$REPO/rulesets" --input - <<'JSON'
{
  "name": "main-basics",
  "target": "branch",
  "enforcement": "active",
  "bypass_actors": [
    {"actor_id": 5, "actor_type": "RepositoryRole", "bypass_mode": "always"}
  ],
  "conditions": {"ref_name": {"include": ["~DEFAULT_BRANCH"], "exclude": []}},
  "rules": [{"type": "deletion"}, {"type": "non_fast_forward"}]
}
JSON
  fi
fi

echo ""
echo "== Summary =="
printf '%s' "$RESULTS"
echo "Open the repo's Actions tab — the first CI run should show up there shortly."
