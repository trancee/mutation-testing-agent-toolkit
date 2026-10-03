#!/usr/bin/env bash
set -euo pipefail

# bootstrap-mutation-testing.sh
# Installs the Mutation Testing Agent Toolkit's OMP and Copilot adapters into
# a Kotlin project.
#
# Usage:
#   ./bootstrap-mutation-testing.sh <project-path> [--kmp]
#
# Copies .omp/ agents, skills, and Gradle scripts into the target project,
# configures build.gradle.kts and settings.gradle.kts.

PROJECT_PATH="${1:-.}"
KMP_MODE="${2:---jvm}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPOSITORY_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

if [[ "$KMP_MODE" == "--kmp" ]]; then
    IS_KMP=1
elif [[ "$KMP_MODE" == "--jvm" ]]; then
    IS_KMP=0
else
    echo "Usage: $0 <project-path> [--kmp]"
    exit 1
fi

if [[ ! -d "$PROJECT_PATH" ]]; then
    echo "Error: project path '$PROJECT_PATH' does not exist"
    exit 1
fi

build_file="$PROJECT_PATH/build.gradle.kts"
if [[ ! -f "$build_file" ]]; then
    echo "Error: build.gradle.kts not found in '$PROJECT_PATH'" >&2
    exit 1
fi
if ! grep -q '^plugins {$' "$build_file"; then
    echo "Error: bootstrap requires a conventional multiline plugins block; use manual setup for other layouts." >&2
    exit 1
fi
if [[ "$IS_KMP" == "1" ]] && ! grep -q 'kotlin("multiplatform")' "$build_file"; then
    echo "Error: --kmp requires a Kotlin Multiplatform project." >&2
    exit 1
fi
if [[ "$IS_KMP" == "0" ]] && grep -q 'kotlin("multiplatform")' "$build_file"; then
    echo "Error: use --kmp for Kotlin Multiplatform projects." >&2
    exit 1
fi
if ! grep -Eq 'kotlin\("(jvm|multiplatform)"\) version "2\.4\.20"' "$build_file"; then
    echo "Error: mutflow 1.6.0 requires Kotlin 2.4.20. Bootstrap requires an explicit compatible Kotlin plugin pin; configure catalog/alias builds manually." >&2
    exit 1
fi
if grep -q 'io.github.anschnapp.mutflow' "$build_file" &&
    ! grep -Eq 'id\("io.github.anschnapp.mutflow"\) version "1\.6\.0"' "$build_file"; then
    echo "Error: existing mutflow plugin is not pinned to the supported version 1.6.0." >&2
    exit 1
fi
if [[ -e "$PROJECT_PATH/buildSrc/build.gradle.kts" ]] &&
    ! cmp -s "$SCRIPT_DIR/mutation-results-src/build.gradle.kts" "$PROJECT_PATH/buildSrc/build.gradle.kts"; then
    echo "Error: existing buildSrc/build.gradle.kts is user-owned; follow the manual setup guide to merge the results module without overwriting it." >&2
    exit 1
fi
if [[ -d "$PROJECT_PATH/buildSrc/src/main/kotlin/io/omp/mutation" ||
      -d "$PROJECT_PATH/buildSrc/src/test/kotlin/io/omp/mutation" ]]; then
    echo "Error: legacy io.omp.mutation sources found. Follow the schema 2 migration guide before installing ch.trancee.mutation." >&2
    exit 1
fi

agent_usage_source="$SCRIPT_DIR/AGENT-USAGE.md"
agent_usage_destination="$PROJECT_PATH/.omp/AGENT-USAGE.md"
agent_pointer='For mutation-testing setup, execution, audits, or troubleshooting, read [.omp/AGENT-USAGE.md](.omp/AGENT-USAGE.md) first.'
if [[ ! -f "$agent_usage_source" ]]; then
    echo "Error: installed agent usage guide is missing: '$agent_usage_source'" >&2
    exit 1
fi
if [[ -L "$PROJECT_PATH/.omp" || -L "$agent_usage_destination" ||
      -L "$PROJECT_PATH/AGENTS.md" ]]; then
    echo "Error: refusing symlinked agent guide destinations." >&2
    exit 1
fi
if [[ -e "$PROJECT_PATH/.omp" && ! -d "$PROJECT_PATH/.omp" ]] ||
    [[ -e "$PROJECT_PATH/AGENTS.md" && ! -f "$PROJECT_PATH/AGENTS.md" ]]; then
    echo "Error: agent guide destinations have incompatible file types." >&2
    exit 1
fi
if [[ -e "$agent_usage_destination" ]] &&
    ! cmp -s "$agent_usage_source" "$agent_usage_destination"; then
    echo "Error: existing .omp/AGENT-USAGE.md differs; merge the installed guide explicitly." >&2
    exit 1
fi

copilot_skill_source="$REPOSITORY_ROOT/.github/skills/omp-mutation-test/SKILL.md"
copilot_agent_sources=(
    "$REPOSITORY_ROOT/.github/agents/omp-mutation-test-reviewer.agent.md"
    "$REPOSITORY_ROOT/.github/agents/omp-mutation-test-saboteur.agent.md"
    "$REPOSITORY_ROOT/.github/agents/omp-mutation-test-executor.agent.md"
    "$REPOSITORY_ROOT/.github/agents/omp-mutation-test-auditor.agent.md"
    "$REPOSITORY_ROOT/.github/agents/omp-mutation-test-refactor-specialist.agent.md"
)
copilot_destination_dirs=(
    "$PROJECT_PATH/.github"
    "$PROJECT_PATH/.github/agents"
    "$PROJECT_PATH/.github/skills"
    "$PROJECT_PATH/.github/skills/omp-mutation-test"
)

for source_file in "$copilot_skill_source" "${copilot_agent_sources[@]}"; do
    if [[ ! -f "$source_file" ]]; then
        echo "Error: Copilot adapter source file is missing: '$source_file'" >&2
        exit 1
    fi
done

for destination_dir in "${copilot_destination_dirs[@]}"; do
    if [[ -L "$destination_dir" ]]; then
        echo "Error: refusing to follow symlink at Copilot destination '$destination_dir'" >&2
        exit 1
    fi
    if [[ -e "$destination_dir" && ! -d "$destination_dir" ]]; then
        echo "Error: Copilot destination '$destination_dir' is not a directory" >&2
        exit 1
    fi
done

assert_copilot_file_available() {
    local source_file="$1"
    local destination_file="$2"

    if [[ -L "$destination_file" ]]; then
        echo "Error: refusing to follow symlink at Copilot file '$destination_file'" >&2
        exit 1
    fi
    if [[ -e "$destination_file" ]] && ! cmp -s "$source_file" "$destination_file"; then
        echo "Error: refusing to overwrite existing Copilot file '$destination_file'" >&2
        exit 1
    fi
}

assert_copilot_file_available \
    "$copilot_skill_source" \
    "$PROJECT_PATH/.github/skills/omp-mutation-test/SKILL.md"
for source_file in "${copilot_agent_sources[@]}"; do
    assert_copilot_file_available \
        "$source_file" \
        "$PROJECT_PATH/.github/agents/$(basename "$source_file")"
done

echo "Bootstrapping mutation testing into: $PROJECT_PATH"
echo "Mode: $( ((IS_KMP)) && echo "KMP" || echo "JVM" )"

# --- Step 1: Copy .omp directory ---
echo ""
echo "Copying .omp agents, skills, and scripts..."

target_dir="$PROJECT_PATH/.omp"
if [[ -d "$target_dir" ]]; then
    echo "  Warning: .omp directory already exists — merging"
fi
mkdir -p "$target_dir"
cp -r "$SCRIPT_DIR/agents" "$target_dir/"
cp -r "$SCRIPT_DIR/skills" "$target_dir/"
cp "$SCRIPT_DIR/mutation-results.gradle.kts" "$target_dir/"
cp "$agent_usage_source" "$agent_usage_destination"
if [[ ! -f "$PROJECT_PATH/AGENTS.md" ]] ||
    ! grep -Fxq "$agent_pointer" "$PROJECT_PATH/AGENTS.md"; then
    printf '\n%s\n' "$agent_pointer" >> "$PROJECT_PATH/AGENTS.md"
fi
mkdir -p "$target_dir/mutation-results-src"
cp "$SCRIPT_DIR/mutation-results-src/build.gradle.kts" "$target_dir/mutation-results-src/"
cp -r "$SCRIPT_DIR/mutation-results-src/main" "$SCRIPT_DIR/mutation-results-src/test" "$target_dir/mutation-results-src/"

# --- Install the Copilot-native adapter ---
echo ""
echo "Installing GitHub Copilot skill and agents..."

copilot_agents_dir="$PROJECT_PATH/.github/agents"
copilot_skill_dir="$PROJECT_PATH/.github/skills/omp-mutation-test"
mkdir -p "$copilot_agents_dir" "$copilot_skill_dir"
copy_copilot_file() {
    local source_file="$1"
    local destination_file="$2"

    if [[ -f "$destination_file" ]] && cmp -s "$source_file" "$destination_file"; then
        return
    fi
    cp "$source_file" "$destination_file"
}

copy_copilot_file "$copilot_skill_source" "$copilot_skill_dir/SKILL.md"
for source_file in "${copilot_agent_sources[@]}"; do
    copy_copilot_file "$source_file" "$copilot_agents_dir/$(basename "$source_file")"
done

# --- Step 2: Configure settings.gradle.kts ---
echo ""
echo "Configuring settings.gradle.kts..."

settings_file="$PROJECT_PATH/settings.gradle.kts"
if [[ ! -f "$settings_file" ]]; then
    if [[ "$IS_KMP" == "1" ]]; then
        root_name='rootProject.name = "my-kmp-app"'
    else
        root_name='rootProject.name = "my-jvm-project"'
    fi
    cat > "$settings_file" << EOF
pluginManagement {
    repositories {
        mavenCentral()
        gradlePluginPortal()
    }
}

$root_name
EOF
    echo "  Created settings.gradle.kts with pluginManagement"
else
    if grep -q "pluginManagement" "$settings_file"; then
        echo "  pluginManagement already present — skipping"
    else
        tmp=$(mktemp)
        cat > "$tmp" << 'EOF'
pluginManagement {
    repositories {
        mavenCentral()
        gradlePluginPortal()
    }
}

EOF
        cat "$settings_file" >> "$tmp"
        mv "$tmp" "$settings_file"
        echo "  Added pluginManagement block"
    fi
fi

# --- Step 3: Configure build.gradle.kts ---
echo ""
echo "Configuring build.gradle.kts..."

build_file="$PROJECT_PATH/build.gradle.kts"
if [[ ! -f "$build_file" ]]; then
    echo "  Error: build.gradle.kts not found in $PROJECT_PATH"
    exit 1
fi

# --- Add mutflow plugin ---
if ! grep -q 'io.github.anschnapp.mutflow' "$build_file"; then
    if grep -q '^plugins {' "$build_file"; then
        sed -i '/^plugins {/a\
    id("io.github.anschnapp.mutflow") version "1.6.0"' "$build_file"
        echo "  Added mutflow plugin"
    else
        {
            echo 'plugins {'
            echo '    id("io.github.anschnapp.mutflow") version "1.6.0"'
            echo '}'
            echo ''
            cat "$build_file"
        } > "$build_file.tmp"
        mv "$build_file.tmp" "$build_file"
        echo "  Added plugins block with mutflow"
    fi
fi

# --- Apply mutation-results script ---
if ! grep -q 'mutation-results.gradle.kts' "$build_file"; then
    if grep -q '^}$' "$build_file"; then
        first_close=$(grep -n '^}$' "$build_file" | head -1 | cut -d: -f1)
        sed -i "${first_close}a\\
\\
apply(from = rootProject.file(\".omp/mutation-results.gradle.kts\"))" "$build_file"
        echo "  Applied mutation-results.gradle.kts"
    fi
fi

# --- Add dependencies + mutflow config ---
if [[ "$IS_KMP" == "1" ]]; then
    if ! grep -q '^mutflow {' "$build_file"; then
        cat >> "$build_file" << 'EOF'

mutflow {
    enabled = true
}
EOF
        echo "  Added mutflow KMP configuration (dedicated mutflow JVM test task)"
    fi
else
    # For JVM, use testImplementation
    if ! grep -q 'junit-jupiter-api' "$build_file"; then
        if grep -q '^dependencies {' "$build_file"; then
            sed -i '/^dependencies {/a\
    testImplementation("org.junit.jupiter:junit-jupiter-api:6.1.3")\
    testImplementation("org.junit.platform:junit-platform-launcher:6.1.3")' "$build_file"
        else
            cat >> "$build_file" << 'EOF'

dependencies {
    testImplementation("org.junit.jupiter:junit-jupiter-api:6.1.3")
    testImplementation("org.junit.platform:junit-platform-launcher:6.1.3")
}
EOF
        fi
        echo "  Added JUnit 6 dependencies"
    fi
    if ! grep -q '^mutflow {' "$build_file"; then
        cat >> "$build_file" << 'EOF'

mutflow {
    enabled = true
}
EOF
        echo "  Added mutflow configuration"
    fi
    # Merge: copy source files
fi

if [[ "$IS_KMP" == "0" ]] && ! grep -q 'useJUnitPlatform' "$build_file"; then
    cat >> "$build_file" << 'EOF'

tasks.withType<org.gradle.api.tasks.testing.Test>().configureEach {
    useJUnitPlatform()
}
EOF
    echo "  Enabled JUnit Platform"
fi

KOTLIN_VERSION="2.4.20"
echo "  Verified compiler-coupled Kotlin $KOTLIN_VERSION"

# --- Step 3b: Generate buildSrc for typed mutation-results module ---
echo ""
echo "Setting up typed mutation-results module (buildSrc)..."

buildsrc_dir="$PROJECT_PATH/buildSrc"
if [[ ! -d "$buildsrc_dir" ]]; then
    mkdir -p "$buildsrc_dir/src/main/kotlin/ch/trancee/mutation"
    mkdir -p "$buildsrc_dir/src/test/kotlin/ch/trancee/mutation"
    cp "$target_dir/mutation-results-src/main/kotlin/ch/trancee/mutation/"*.kt "$buildsrc_dir/src/main/kotlin/ch/trancee/mutation/"
    cp "$target_dir/mutation-results-src/test/kotlin/ch/trancee/mutation/"*.kt "$buildsrc_dir/src/test/kotlin/ch/trancee/mutation/"
    cp "$target_dir/mutation-results-src/build.gradle.kts" "$buildsrc_dir/build.gradle.kts"
    echo "  Created buildSrc/ with typed MutationResults module (Kotlin $KOTLIN_VERSION)"
else
    # Merge: copy source files
    mkdir -p "$buildsrc_dir/src/main/kotlin/ch/trancee/mutation"
    mkdir -p "$buildsrc_dir/src/test/kotlin/ch/trancee/mutation"
    cp "$target_dir/mutation-results-src/main/kotlin/ch/trancee/mutation/"*.kt "$buildsrc_dir/src/main/kotlin/ch/trancee/mutation/"
    cp "$target_dir/mutation-results-src/test/kotlin/ch/trancee/mutation/"*.kt "$buildsrc_dir/src/test/kotlin/ch/trancee/mutation/"
    cp "$target_dir/mutation-results-src/build.gradle.kts" "$buildsrc_dir/build.gradle.kts"
    echo "  Updated buildSrc/ with typed MutationResults module (Kotlin $KOTLIN_VERSION)"
fi

# --- Step 4: Summary ---
echo ""
echo "✅ Bootstrap complete!"
echo ""
echo "Next steps:"
echo "  1. Run: /mutation-test $PROJECT_PATH"
echo "     The saboteur agent will annotate @MutationTarget and @MutFlowTest"
echo "  2. test-executor runs: gradle mutationResults"
echo "  3. test-auditor parses results and reports score"
echo "  4. test-refactor-specialist proposes boundary tests for survivors"
echo "  5. Copilot CLI: restart or run /skills reload, then use /omp-mutation-test"
echo ""
echo "Or run directly: cd $PROJECT_PATH && gradle mutationResults"
