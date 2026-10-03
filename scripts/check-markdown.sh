#!/usr/bin/env bash
# Checks Markdown files for style/syntax correctness (markdownlint-cli2)
# and broken links (lychee): internal file/anchor links always, external
# URLs unless --offline is given.
#
# Usage: ./scripts/check-markdown.sh [--offline] [file ...]

set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

offline=0
files=()
for arg in "$@"; do
  if [[ "$arg" == "--offline" ]]; then
    offline=1
  else
    files+=("$arg")
  fi
done

if ! command -v npx >/dev/null 2>&1; then
  echo "[check-markdown] npx (Node.js) is required for markdownlint-cli2." >&2
  echo "[check-markdown] Install Node.js, or see docs/how-to/run-checks.md." >&2
  exit 1
fi

if ! command -v lychee >/dev/null 2>&1; then
  echo "[check-markdown] lychee is required for link checking." >&2
  echo "[check-markdown] Install with: brew install lychee" >&2
  echo "[check-markdown] Or: curl -LsSf https://github.com/lycheeverse/lychee/releases/latest/download/lychee-installer.sh | sh" >&2
  exit 1
fi

if [[ ${#files[@]} -eq 0 ]]; then
  files=("**/*.md")
fi

# markdownlint patterns: include negation patterns for directories to skip
# Do NOT exclude README.md — it must pass markdownlint too.
ml_files=("${files[@]}" "!.scratch/**" "!.agents/**" "!build/**" "!.gradle/**")

echo "[check-markdown] Running markdownlint-cli2: ${ml_files[*]}"
npx --yes markdownlint-cli2@0.23.3 "${ml_files[@]}"

# lychee uses lychee.toml for exclude_path settings
lychee_args=(--no-progress "${files[@]}")
if [[ "$offline" -eq 1 ]]; then
  lychee_args+=(--offline)
  echo "[check-markdown] Running lychee (offline — internal links only): ${files[*]}"
else
  echo "[check-markdown] Running lychee (internal + external links): ${files[*]}"
fi
lychee "${lychee_args[@]}"

echo "[check-markdown] OK"
