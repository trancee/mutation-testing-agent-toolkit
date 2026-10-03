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
    kotlin("jvm") version "2.4.0"
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

assert_file "$project/.github/skills/omp-mutation-test/SKILL.md"
cmp "$repo_root/.github/skills/omp-mutation-test/SKILL.md" \
  "$project/.github/skills/omp-mutation-test/SKILL.md"
for agent in \
  omp-mutation-test-reviewer \
  omp-mutation-test-saboteur \
  omp-mutation-test-executor \
  omp-mutation-test-auditor \
  omp-mutation-test-refactor-specialist; do
  assert_file "$project/.github/agents/$agent.agent.md"
  cmp "$repo_root/.github/agents/$agent.agent.md" \
    "$project/.github/agents/$agent.agent.md"
done

conflict_project="$tmp_root/conflict-project"
write_minimal_project "$conflict_project"
mkdir -p "$conflict_project/.github/agents"
printf '%s\n' 'user-owned agent profile' > \
  "$conflict_project/.github/agents/omp-mutation-test-reviewer.agent.md"
cp "$conflict_project/.github/agents/omp-mutation-test-reviewer.agent.md" \
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
  "$conflict_project/.github/agents/omp-mutation-test-reviewer.agent.md"
cmp "$tmp_root/conflict-build.gradle.kts" "$conflict_project/build.gradle.kts"

echo "Copilot adapter bootstrap checks passed."
