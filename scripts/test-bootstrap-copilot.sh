#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
bootstrap_command="$repo_root/bootstrap.sh"
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

if ! "$bootstrap_command" install "$project" >"$tmp_root/install.log" 2>&1; then
  cat "$tmp_root/install.log" >&2
  exit 1
fi

assert_file "$project/.omp/skills/mutation-testing/SKILL.md"
assert_file "$project/.omp/skills/mutation-testing/agents/openai.yaml"
assert_file "$project/.mutation-testing/mutation-results-src/main/kotlin/ch/trancee/mutation/MutationResultsSummary.kt"
assert_file "$project/.github/skills/mutation-testing/SKILL.md"
assert_file "$project/.mutation-testing/AGENT-USAGE.md"
assert_file "$project/.mutation-testing/mutation-results.gradle.kts"
assert_file "$project/.mutation-testing/manifest.json"
assert_file "$project/buildSrc/src/main/kotlin/ch/trancee/mutation/MutationResultsSummary.kt"
cmp "$repo_root/.mutation-testing/AGENT-USAGE.md" "$project/.mutation-testing/AGENT-USAGE.md"
cmp "$repo_root/.omp/skills/mutation-testing/SKILL.md" \
  "$project/.omp/skills/mutation-testing/SKILL.md"
cmp "$repo_root/.omp/skills/mutation-testing/agents/openai.yaml" \
  "$project/.omp/skills/mutation-testing/agents/openai.yaml"
grep -Fq '.mutation-testing/AGENT-USAGE.md' "$project/AGENTS.md"
cp "$project/AGENTS.md" "$tmp_root/installed-AGENTS.md"
"$bootstrap_command" install "$project" >"$tmp_root/reinstall.log" 2>&1
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

invalid_module_project="$tmp_root/invalid-module-project"
write_minimal_project "$invalid_module_project"
cp "$invalid_module_project/build.gradle.kts" "$tmp_root/invalid-module-build.gradle.kts"
if "$bootstrap_command" install "$invalid_module_project" --module ":../outside" >"$tmp_root/invalid-module.log" 2>&1; then
  echo "Expected bootstrap to reject a module path that escapes the project root." >&2
  exit 1
fi
cmp "$tmp_root/invalid-module-build.gradle.kts" "$invalid_module_project/build.gradle.kts"
[[ ! -e "$invalid_module_project/.mutation-testing" ]]
[[ ! -e "$invalid_module_project/.omp" ]]

module_project="$tmp_root/module-project"
mkdir -p "$module_project/service"
printf '%s\n' 'plugins {' '}' > "$module_project/build.gradle.kts"
printf '%s\n' 'rootProject.name = "module-project"' 'include(":service")' > \
  "$module_project/settings.gradle.kts"
write_minimal_project "$module_project/service"
cp "$module_project/build.gradle.kts" "$tmp_root/module-root-build.gradle.kts"
"$bootstrap_command" install "$module_project" --module :service >"$tmp_root/module-project.log" 2>&1
cmp "$tmp_root/module-root-build.gradle.kts" "$module_project/build.gradle.kts"
grep -Fq 'id("io.github.anschnapp.mutflow") version "1.6.0"' \
  "$module_project/service/build.gradle.kts"
grep -Fq 'Run: /mutation-testing' "$tmp_root/module-project.log"
grep -Fq 'gradle :service:mutationResults' "$tmp_root/module-project.log"

conflict_project="$tmp_root/conflict-project"
write_minimal_project "$conflict_project"
mkdir -p "$conflict_project/.github/agents"
printf '%s\n' 'user-owned agent profile' > \
  "$conflict_project/.github/agents/mutation-testing-reviewer.agent.md"
cp "$conflict_project/.github/agents/mutation-testing-reviewer.agent.md" \
  "$tmp_root/conflict-agent.agent.md"
cp "$conflict_project/build.gradle.kts" "$tmp_root/conflict-build.gradle.kts"

if "$bootstrap_command" install "$conflict_project" >"$tmp_root/conflict.log" 2>&1; then
  echo "Expected bootstrap to refuse an existing Copilot agent profile." >&2
  exit 1
fi

if [[ -e "$conflict_project/.omp" || -e "$conflict_project/.mutation-testing" ]]; then
  echo "Bootstrap changed the project before reporting a profile conflict." >&2
  exit 1
fi

cmp "$tmp_root/conflict-agent.agent.md" \
  "$conflict_project/.github/agents/mutation-testing-reviewer.agent.md"
cmp "$tmp_root/conflict-build.gradle.kts" "$conflict_project/build.gradle.kts"

owned_project="$tmp_root/owned-agents"
write_minimal_project "$owned_project"
printf 'User-owned policy without final newline' > "$owned_project/AGENTS.md"
"$bootstrap_command" install "$owned_project" >"$tmp_root/owned.log" 2>&1
grep -Fxq 'User-owned policy without final newline' "$owned_project/AGENTS.md"
grep -Fq '.mutation-testing/AGENT-USAGE.md' "$owned_project/AGENTS.md"

cp "$owned_project/AGENTS.md" "$tmp_root/preserved-policy"
for kind in symlink-agents directory-agents symlink-omp; do
  rejected="$tmp_root/$kind"
  write_minimal_project "$rejected"
  cp "$rejected/build.gradle.kts" "$tmp_root/$kind-build"
  case "$kind" in
    symlink-agents)
      ln -s "$owned_project/AGENTS.md" "$rejected/AGENTS.md"
      ;;
    directory-agents)
      mkdir -p "$rejected/AGENTS.md"
      ;;
    symlink-omp)
      ln -s "$owned_project/.omp" "$rejected/.omp"
      ;;
  esac
  if "$bootstrap_command" install "$rejected" >"$tmp_root/$kind.log" 2>&1; then
    echo "Expected bootstrap to reject $kind." >&2
    exit 1
  fi
  cmp "$tmp_root/$kind-build" "$rejected/build.gradle.kts"
  [[ ! -e "$rejected/.github" ]]
done
cmp "$tmp_root/preserved-policy" "$owned_project/AGENTS.md"

echo "OMP and Copilot adapter bootstrap checks passed."
