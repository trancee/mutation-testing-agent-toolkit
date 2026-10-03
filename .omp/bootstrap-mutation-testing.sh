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
cp -r "$SCRIPT_DIR/mutation-results-src" "$target_dir/"

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

cp "$build_file" "$build_file.bak"

# --- Add mutflow plugin ---
if ! grep -q 'io.github.anschnapp.mutflow' "$build_file"; then
    if grep -q '^plugins {' "$build_file"; then
        sed -i.bak '/^plugins {/a\
    id("io.github.anschnapp.mutflow") version "1.1.1"' "$build_file"
        rm -f "$build_file.bak"
        echo "  Added mutflow plugin"
    else
        {
            echo 'plugins {'
            echo '    id("io.github.anschnapp.mutflow") version "1.1.1"'
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
        sed -i.bak "${first_close}a\\
\\
apply(from = rootProject.file(\".omp/mutation-results.gradle.kts\"))" "$build_file"
        rm -f "$build_file.bak"
        echo "  Applied mutation-results.gradle.kts"
    fi
fi

# --- Add dependencies + mutflow config ---
if [[ "$IS_KMP" == "1" ]]; then
    # For KMP, add jvmTestImplementation dependencies + mutflow block
    if ! grep -q 'junit-jupiter-api' "$build_file"; then
        cat >> "$build_file" << 'EOF'

dependencies {
    jvmTestImplementation("org.junit.jupiter:junit-jupiter-api:6.1.3")
    jvmTestImplementation("org.junit.platform:junit-platform-launcher:6.1.3")
    jvmTestImplementation("io.github.anschnapp.mutflow:mutflow-junit6:1.1.1")
}
EOF
        echo "  Added KMP JVM test dependencies"
    fi
    if ! grep -q '^mutflow {' "$build_file"; then
        cat >> "$build_file" << 'EOF'

mutflow {
    enabled = true
    targets = listOf("jvmTest")
}
EOF
        echo "  Added mutflow KMP configuration (jvmTest)"
    fi
else
    # For JVM, use testImplementation
    if ! grep -q 'junit-jupiter-api' "$build_file"; then
        if grep -q '^dependencies {' "$build_file"; then
            sed -i.bak '/^dependencies {/a\
    testImplementation("org.junit.jupiter:junit-jupiter-api:6.1.3")\
    testImplementation("org.junit.platform:junit-platform-launcher:6.1.3")\
    testImplementation("io.github.anschnapp.mutflow:mutflow-junit6:1.1.1")' "$build_file"
            rm -f "$build_file.bak"
        else
            cat >> "$build_file" << 'EOF'

dependencies {
    testImplementation("org.junit.jupiter:junit-jupiter-api:6.1.3")
    testImplementation("org.junit.platform:junit-platform-launcher:6.1.3")
    testImplementation("io.github.anschnapp.mutflow:mutflow-junit6:1.1.1")
}
EOF
        fi
        echo "  Added JUnit 6 + mutflow-junit6 dependencies"
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

rm -f "$build_file.bak"

# --- Detect Kotlin version from target project ---
KOTLIN_VERSION=$(grep -oE 'kotlin\("(jvm|multiplatform)"\) version "[0-9]+\.[0-9]+\.[0-9]+"' "$build_file" 2>/dev/null || true)
if [[ "$KOTLIN_VERSION" =~ [0-9]+\.[0-9]+\.[0-9]+ ]]; then
    KOTLIN_VERSION="${BASH_REMATCH[0]}"
else
    KOTLIN_VERSION=""
fi
if [[ -z "$KOTLIN_VERSION" ]]; then
    KOTLIN_VERSION=$(grep -oE 'kotlin\("plugin\.serialization"\) version "[0-9]+\.[0-9]+\.[0-9]+"' "$build_file" 2>/dev/null || true)
    if [[ "$KOTLIN_VERSION" =~ [0-9]+\.[0-9]+\.[0-9]+ ]]; then
        KOTLIN_VERSION="${BASH_REMATCH[0]}"
    else
        KOTLIN_VERSION=""
    fi
fi
if [[ -z "$KOTLIN_VERSION" ]]; then
    KOTLIN_VERSION="2.4.0"
    echo "  Warning: Could not detect Kotlin version from build.gradle.kts — using default $KOTLIN_VERSION"
else
    echo "  Detected Kotlin $KOTLIN_VERSION from build.gradle.kts"
fi

# --- Step 3b: Generate buildSrc for typed mutation-results module ---
echo ""
echo "Setting up typed mutation-results module (buildSrc)..."

buildsrc_dir="$PROJECT_PATH/buildSrc"
if [[ ! -d "$buildsrc_dir" ]]; then
    mkdir -p "$buildsrc_dir/src/main/kotlin/io/omp/mutation"
    mkdir -p "$buildsrc_dir/src/test/kotlin/io/omp/mutation"
    cp "$target_dir/mutation-results-src/main/kotlin/io/omp/mutation/"*.kt "$buildsrc_dir/src/main/kotlin/io/omp/mutation/"
    cp "$target_dir/mutation-results-src/test/kotlin/io/omp/mutation/"*.kt "$buildsrc_dir/src/test/kotlin/io/omp/mutation/"
    cp "$target_dir/mutation-results-src/build.gradle.kts" "$buildsrc_dir/build.gradle.kts"
    # Inject detected Kotlin version into buildSrc build.gradle.kts
    sed -i.bak "s/kotlin(\"plugin.serialization\") version \"[0-9.]*\"/kotlin(\"plugin.serialization\") version \"$KOTLIN_VERSION\"/" "$buildsrc_dir/build.gradle.kts"
    rm -f "$buildsrc_dir/build.gradle.kts.bak"
    echo "  Created buildSrc/ with typed MutationResults module (Kotlin $KOTLIN_VERSION)"
else
    # Merge: copy source files
    mkdir -p "$buildsrc_dir/src/main/kotlin/io/omp/mutation"
    mkdir -p "$buildsrc_dir/src/test/kotlin/io/omp/mutation"
    cp "$target_dir/mutation-results-src/main/kotlin/io/omp/mutation/"*.kt "$buildsrc_dir/src/main/kotlin/io/omp/mutation/"
    cp "$target_dir/mutation-results-src/test/kotlin/io/omp/mutation/"*.kt "$buildsrc_dir/src/test/kotlin/io/omp/mutation/"
    cp "$target_dir/mutation-results-src/build.gradle.kts" "$buildsrc_dir/build.gradle.kts"
    # Inject detected Kotlin version into buildSrc build.gradle.kts
    sed -i.bak "s/kotlin(\"plugin.serialization\") version \"[0-9.]*\"/kotlin(\"plugin.serialization\") version \"$KOTLIN_VERSION\"/" "$buildsrc_dir/build.gradle.kts"
    rm -f "$buildsrc_dir/build.gradle.kts.bak"
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
