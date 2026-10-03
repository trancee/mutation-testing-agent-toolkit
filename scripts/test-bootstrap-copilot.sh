#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
bootstrap="$repo_root/.omp/bootstrap-mutation-testing.sh"
tmp_root="$(mktemp -d "${TMPDIR:-/tmp}/omp-copilot-bootstrap.XXXXXX")"
trap 'rm -rf "$tmp_root"' EXIT

write_minimal_project() {
  local project="$1"
  mkdir -p "$project"
  cat > "$project/build.gradle.kts" <<'EOF'
plugins {
    kotlin("jvm") version "2.4.20"
}

repositories {
    mavenCentral()
}

dependencies {
    testImplementation(kotlin("test"))
}
EOF
}

assert_file() {
  if [[ ! -f "$1" ]]; then
    echo "Expected bootstrap to install $1" >&2
    exit 1
  fi
}

project="$tmp_root/project"
write_minimal_project "$project"

if ! "$bootstrap" "$project" >"$tmp_root/install.log" 2>&1; then
  cat "$tmp_root/install.log" >&2
  exit 1
fi

assert_file "$project/.omp/skills/mutation-testing/SKILL.md"
assert_file "$project/.omp/skills/mutation-testing/agents/openai.yaml"
assert_file "$project/.github/skills/mutation-testing/SKILL.md"
assert_file "$project/.omp/AGENT-USAGE.md"
cmp "$repo_root/.omp/AGENT-USAGE.md" "$project/.omp/AGENT-USAGE.md"
cmp "$repo_root/.omp/skills/mutation-testing/SKILL.md" \
  "$project/.omp/skills/mutation-testing/SKILL.md"
cmp "$repo_root/.omp/skills/mutation-testing/agents/openai.yaml" \
  "$project/.omp/skills/mutation-testing/agents/openai.yaml"
grep -Fq '.omp/AGENT-USAGE.md' "$project/AGENTS.md"
cp "$project/AGENTS.md" "$tmp_root/installed-AGENTS.md"
"$bootstrap" "$project" >"$tmp_root/reinstall.log" 2>&1
cmp "$tmp_root/installed-AGENTS.md" "$project/AGENTS.md"
cmp "$repo_root/.github/skills/mutation-testing/SKILL.md" \
  "$project/.github/skills/mutation-testing/SKILL.md"
grep -Fq 'name: mutation-testing' "$project/.omp/skills/mutation-testing/SKILL.md"
grep -Fq 'name: mutation-testing' "$project/.github/skills/mutation-testing/SKILL.md"
grep -Fq '/mutation-testing' "$project/.omp/skills/mutation-testing/SKILL.md"
grep -Fq '/mutation-testing' "$project/.github/skills/mutation-testing/SKILL.md"
grep -Fq 'display_name: "Mutation Testing"' \
  "$project/.omp/skills/mutation-testing/agents/openai.yaml"
grep -Fq "Run: /mutation-testing $project" "$tmp_root/install.log"
grep -Fq 'use /mutation-testing' "$tmp_root/install.log"
for agent in \
  mutation-testing-reviewer \
  mutation-testing-saboteur \
  mutation-testing-executor \
  mutation-testing-auditor \
  mutation-testing-refactor-specialist; do
  assert_file "$project/.github/agents/$agent.agent.md"
  cmp "$repo_root/.github/agents/$agent.agent.md" \
    "$project/.github/agents/$agent.agent.md"
done

conflict_project="$tmp_root/conflict-project"
write_minimal_project "$conflict_project"
mkdir -p "$conflict_project/.github/agents"
printf '%s\n' 'user-owned agent profile' > \
  "$conflict_project/.github/agents/mutation-testing-reviewer.agent.md"
cp "$conflict_project/.github/agents/mutation-testing-reviewer.agent.md" \
  "$tmp_root/conflict-agent.agent.md"
cp "$conflict_project/build.gradle.kts" "$tmp_root/conflict-build.gradle.kts"

if "$bootstrap" "$conflict_project" >"$tmp_root/conflict.log" 2>&1; then
  echo "Expected bootstrap to refuse an existing Copilot agent profile." >&2
  exit 1
fi

if [[ -e "$conflict_project/.omp" ]]; then
  echo "Bootstrap changed the project before reporting a profile conflict." >&2
  exit 1
fi

cmp "$tmp_root/conflict-agent.agent.md" \
  "$conflict_project/.github/agents/mutation-testing-reviewer.agent.md"
cmp "$tmp_root/conflict-build.gradle.kts" "$conflict_project/build.gradle.kts"

owned_project="$tmp_root/owned-agents"
write_minimal_project "$owned_project"
printf 'User-owned policy without final newline' > "$owned_project/AGENTS.md"
"$bootstrap" "$owned_project" >"$tmp_root/owned.log" 2>&1
grep -Fxq 'User-owned policy without final newline' "$owned_project/AGENTS.md"
grep -Fq '.omp/AGENT-USAGE.md' "$owned_project/AGENTS.md"

cp "$owned_project/AGENTS.md" "$tmp_root/preserved-policy"
for kind in conflicting-guide symlink-agents symlink-guide directory-agents symlink-omp directory-guide; do
  rejected="$tmp_root/$kind"
  write_minimal_project "$rejected"
  cp "$rejected/build.gradle.kts" "$tmp_root/$kind-build"
  case "$kind" in
    conflicting-guide)
      mkdir -p "$rejected/.omp"
      printf 'User-owned guide\n' > "$rejected/.omp/AGENT-USAGE.md"
      ;;
    symlink-agents)
      ln -s "$owned_project/AGENTS.md" "$rejected/AGENTS.md"
      ;;
    symlink-guide)
      mkdir -p "$rejected/.omp"
      ln -s "$owned_project/AGENTS.md" "$rejected/.omp/AGENT-USAGE.md"
      ;;
    directory-agents)
      mkdir -p "$rejected/AGENTS.md"
      ;;
    symlink-omp)
      ln -s "$owned_project/.omp" "$rejected/.omp"
      ;;
    directory-guide)
      mkdir -p "$rejected/.omp/AGENT-USAGE.md"
      ;;
  esac
  if "$bootstrap" "$rejected" >"$tmp_root/$kind.log" 2>&1; then
    echo "Expected bootstrap to reject $kind." >&2
    exit 1
  fi
  cmp "$tmp_root/$kind-build" "$rejected/build.gradle.kts"
  [[ ! -e "$rejected/.github" ]]
done
grep -Fxq 'User-owned guide' "$tmp_root/conflicting-guide/.omp/AGENT-USAGE.md"
cmp "$tmp_root/preserved-policy" "$owned_project/AGENTS.md"

echo "OMP and Copilot adapter bootstrap checks passed."
