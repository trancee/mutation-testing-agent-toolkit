#!/usr/bin/env bash
set -euo pipefail

# bootstrap-mutation-testing.sh
# Installs the Mutation Testing Agent Toolkit's OMP and Copilot adapters into
# a Kotlin project.
#
# Usage:
#   ./bootstrap-mutation-testing.sh <project-root> [--kmp] [--junit4] [--module :path]
#
# Copies .omp/ agents, skills, and Gradle scripts into the target project,
# configures build.gradle.kts and settings.gradle.kts.

PROJECT_PATH="."
IS_KMP=0
JUNIT4_MODE=0
MODULE_PATH=":"
if [[ $# -gt 0 && "$1" != --* ]]; then
    PROJECT_PATH="$1"
    shift
fi
while [[ $# -gt 0 ]]; do
    case "$1" in
        --kmp)
            IS_KMP=1
            ;;
        --jvm)
            IS_KMP=0
            ;;
        --junit4)
            JUNIT4_MODE=1
            ;;
        --module)
            if [[ $# -lt 2 ]]; then
                echo "Usage: $0 <project-root> [--kmp] [--junit4] [--module :path]" >&2
                exit 1
            fi
            MODULE_PATH="$2"
            shift
            ;;
        *)
            echo "Usage: $0 <project-root> [--kmp] [--junit4] [--module :path]"
            exit 1
            ;;
    esac
    shift
done
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPOSITORY_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

if [[ ! -d "$PROJECT_PATH" ]]; then
    echo "Error: project path '$PROJECT_PATH' does not exist"
    exit 1
fi
PROJECT_PATH="$(cd "$PROJECT_PATH" && pwd -P)"
if [[ "$MODULE_PATH" != ":" ]]; then
    if [[ ! "$MODULE_PATH" =~ ^(:[A-Za-z0-9_-][A-Za-z0-9_.-]*)+$ ]]; then
        echo "Error: module must be a Gradle project path such as :service or :backend:core." >&2
        exit 1
    fi
    if [[ ! -f "$PROJECT_PATH/settings.gradle.kts" && ! -f "$PROJECT_PATH/settings.gradle" ]]; then
        echo "Error: --module requires a Gradle settings file at the project root." >&2
        exit 1
    fi
    module_relative_path="${MODULE_PATH#:}"
    module_relative_path="${module_relative_path//:/\/}"
    module_candidate="$PROJECT_PATH/$module_relative_path"
    if [[ ! -d "$module_candidate" ]]; then
        echo "Error: Gradle module '$MODULE_PATH' does not map to directory '$module_candidate'." >&2
        exit 1
    fi
    module_real_path="$(cd "$module_candidate" && pwd -P)"
    case "$module_real_path/" in
        "$PROJECT_PATH/"*) ;;
        *)
            echo "Error: module '$MODULE_PATH' resolves outside the project root." >&2
            exit 1
            ;;
    esac
    MODULE_DIR="$module_real_path"
else
    MODULE_DIR="$PROJECT_PATH"
fi
if [[ "$IS_KMP" == "1" && "$JUNIT4_MODE" == "1" ]]; then
    echo "Error: --junit4 supports plain Kotlin/JVM projects; KMP JVM uses MutFlow's generated JUnit 6 adapter." >&2
    exit 1
fi

build_file="$MODULE_DIR/build.gradle.kts"
if [[ ! -f "$build_file" ]]; then
    echo "Error: build.gradle.kts not found for module '$MODULE_PATH' at '$MODULE_DIR'." >&2
    exit 1
fi
if [[ -L "$build_file" ]]; then
    echo "Error: refusing to modify a symlinked module build file '$build_file'." >&2
    exit 1
fi
if ! grep -q '^plugins {$' "$build_file"; then
    echo "Error: bootstrap requires a conventional multiline plugins block; use manual setup for other layouts." >&2
    exit 1
fi
REQUIRED_KOTLIN_VERSION="2.4.20"
version_catalog="$PROJECT_PATH/gradle/libs.versions.toml"

catalog_plugin_records() {
    local expected_plugin_id="$1"
    [[ -f "$version_catalog" ]] || return 0
    awk -v expected_id="$expected_plugin_id" '
        function trim(value) {
            sub(/^[[:space:]]*/, "", value)
            sub(/[[:space:]]*$/, "", value)
            return value
        }
        /^\[plugins\][[:space:]]*$/ { in_plugins = 1; next }
        /^\[/ { in_plugins = 0 }
        in_plugins {
            line = $0
            if (line ~ /^[[:space:]]*#/) next
            if (!collecting) {
                if (line !~ /^[[:space:]]*[^=]+=[[:space:]]*\{/) next
                alias = line
                sub(/^[[:space:]]*/, "", alias)
                sub(/[[:space:]]*=.*/, "", alias)
                alias = trim(alias)
                if (alias ~ /^".*"$/) {
                    sub(/^"/, "", alias)
                    sub(/"$/, "", alias)
                }
                entry = line
                collecting = 1
            } else {
                entry = entry "\n" line
            }
            if (entry ~ /}/) {
                if (index(entry, expected_id)) {
                    spec = ""
                    if (match(entry, /version[.]ref[[:space:]]*=[[:space:]]*"[^"]*"/)) {
                        spec = substr(entry, RSTART, RLENGTH)
                        sub(/^[^"]*"/, "", spec)
                        sub(/".*$/, "", spec)
                        spec = "ref:" spec
                    } else if (match(entry, /version[[:space:]]*=[[:space:]]*"[^"]*"/)) {
                        spec = substr(entry, RSTART, RLENGTH)
                        sub(/^[^"]*"/, "", spec)
                        sub(/".*$/, "", spec)
                        spec = "direct:" spec
                    }
                    print alias "|" spec
                }
                collecting = 0
                entry = ""
            }
        }
    ' "$version_catalog"
}

catalog_version_value() {
    local expected_name="$1"
    awk -v expected_name="$expected_name" '
        function trim(value) {
            sub(/^[[:space:]]*/, "", value)
            sub(/[[:space:]]*$/, "", value)
            return value
        }
        /^\[versions\][[:space:]]*$/ { in_versions = 1; next }
        /^\[/ { in_versions = 0; next }
        in_versions {
            line = $0
            sub(/[[:space:]]+#.*/, "", line)
            key = line
            sub(/=.*/, "", key)
            key = trim(key)
            if (key ~ /^".*"$/) {
                sub(/^"/, "", key)
                sub(/"$/, "", key)
            }
            if (key != expected_name) next
            value = line
            sub(/^[^=]*=[[:space:]]*/, "", value)
            if (match(value, /"[^"]*"/)) {
                print substr(value, RSTART + 1, RLENGTH - 2)
            }
            exit
        }
    ' "$version_catalog"
}

resolve_catalog_plugin_version() {
    local expected_plugin_id="$1"
    local records alias_name version_spec accessor escaped_accessor plugin_version version_ref
    records="$(catalog_plugin_records "$expected_plugin_id")"
    while IFS='|' read -r alias_name version_spec; do
        [[ "$alias_name" =~ ^[A-Za-z0-9_.-]+$ ]] || continue
        accessor="${alias_name//[-_]/.}"
        escaped_accessor="${accessor//./\\.}"
        if ! grep -Eq "alias[[:space:]]*\\([[:space:]]*libs\\.plugins\\.${escaped_accessor}[[:space:]]*\\)" "$build_file"; then
            continue
        fi
        case "$version_spec" in
            ref:*)
                version_ref="${version_spec#ref:}"
                plugin_version="$(catalog_version_value "$version_ref")"
                ;;
            direct:*)
                plugin_version="${version_spec#direct:}"
                ;;
            *)
                plugin_version=""
                ;;
        esac
        printf '%s\n' "$plugin_version"
        return 0
    done <<< "$records"
    return 1
}

KOTLIN_PLUGIN_KIND=""
KOTLIN_PLUGIN_VERSION=""
if grep -q 'kotlin("multiplatform")' "$build_file"; then
    KOTLIN_PLUGIN_KIND="multiplatform"
    KOTLIN_PLUGIN_VERSION="$(sed -nE 's/.*kotlin\("multiplatform"\)[[:space:]]+version[[:space:]]+"([^"]+)".*/\1/p' "$build_file" | head -n 1)"
elif grep -q 'kotlin("jvm")' "$build_file"; then
    KOTLIN_PLUGIN_KIND="jvm"
    KOTLIN_PLUGIN_VERSION="$(sed -nE 's/.*kotlin\("jvm"\)[[:space:]]+version[[:space:]]+"([^"]+)".*/\1/p' "$build_file" | head -n 1)"
elif KOTLIN_PLUGIN_VERSION="$(resolve_catalog_plugin_version "org.jetbrains.kotlin.multiplatform")"; then
    KOTLIN_PLUGIN_KIND="multiplatform"
elif KOTLIN_PLUGIN_VERSION="$(resolve_catalog_plugin_version "org.jetbrains.kotlin.jvm")"; then
    KOTLIN_PLUGIN_KIND="jvm"
fi

if [[ -z "$KOTLIN_PLUGIN_KIND" ]]; then
    echo "Error: could not resolve a Kotlin JVM or Multiplatform plugin pin from the module build or gradle/libs.versions.toml." >&2
    exit 1
fi
if [[ "$IS_KMP" == "1" && "$KOTLIN_PLUGIN_KIND" != "multiplatform" ]]; then
    echo "Error: --kmp requires a Kotlin Multiplatform plugin in module '$MODULE_PATH'." >&2
    exit 1
fi
if [[ "$IS_KMP" == "0" && "$KOTLIN_PLUGIN_KIND" == "multiplatform" ]]; then
    echo "Error: use --kmp for Kotlin Multiplatform projects." >&2
    exit 1
fi
if [[ "$KOTLIN_PLUGIN_VERSION" != "$REQUIRED_KOTLIN_VERSION" ]]; then
    echo "Error: mutflow 1.6.0 requires Kotlin $REQUIRED_KOTLIN_VERSION; module '$MODULE_PATH' resolves '${KOTLIN_PLUGIN_VERSION:-an unpinned version}'." >&2
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

copilot_skill_source="$REPOSITORY_ROOT/.github/skills/mutation-testing/SKILL.md"
copilot_agent_sources=(
    "$REPOSITORY_ROOT/.github/agents/mutation-testing-reviewer.agent.md"
    "$REPOSITORY_ROOT/.github/agents/mutation-testing-saboteur.agent.md"
    "$REPOSITORY_ROOT/.github/agents/mutation-testing-executor.agent.md"
    "$REPOSITORY_ROOT/.github/agents/mutation-testing-auditor.agent.md"
    "$REPOSITORY_ROOT/.github/agents/mutation-testing-refactor-specialist.agent.md"
)
copilot_destination_dirs=(
    "$PROJECT_PATH/.github"
    "$PROJECT_PATH/.github/agents"
    "$PROJECT_PATH/.github/skills"
    "$PROJECT_PATH/.github/skills/mutation-testing"
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
    "$PROJECT_PATH/.github/skills/mutation-testing/SKILL.md"
for source_file in "${copilot_agent_sources[@]}"; do
    assert_copilot_file_available \
        "$source_file" \
        "$PROJECT_PATH/.github/agents/$(basename "$source_file")"
done

echo "Bootstrapping mutation testing into: $PROJECT_PATH"
echo "Mode: $( ((IS_KMP)) && echo "KMP" || echo "JVM" )"
echo "Module: $MODULE_PATH"
if [[ "$JUNIT4_MODE" == "1" ]]; then
    echo "Test framework: JUnit 4"
else
    echo "Test framework: JUnit 6"
fi

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
copilot_skill_dir="$PROJECT_PATH/.github/skills/mutation-testing"
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
if [[ ! -f "$settings_file" && -f "$PROJECT_PATH/settings.gradle" ]]; then
    echo "  Existing Groovy settings.gradle — skipping Kotlin settings updates"
elif [[ ! -f "$settings_file" ]]; then
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
echo "Configuring module build.gradle.kts..."

build_file="$MODULE_DIR/build.gradle.kts"
if [[ ! -f "$build_file" ]]; then
    echo "  Error: build.gradle.kts not found for module '$MODULE_PATH' at '$MODULE_DIR'."
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
    if [[ "$JUNIT4_MODE" == "1" ]]; then
        if ! grep -q 'mutflow-junit4' "$build_file"; then
            if grep -q '^dependencies {' "$build_file"; then
                sed -i '/^dependencies {/a\
    testImplementation("io.github.anschnapp.mutflow:mutflow-junit4:1.6.0")' "$build_file"
            else
                cat >> "$build_file" << 'EOF'

dependencies {
    testImplementation("io.github.anschnapp.mutflow:mutflow-junit4:1.6.0")
}
EOF
            fi
            echo "  Added MutFlow JUnit 4 runner"
        fi
        if ! grep -q 'mutationTest.junitFramework' "$build_file"; then
            cat >> "$build_file" << 'EOF'

extra["mutationTest.junitFramework"] = "junit4"
EOF
        fi
    else
        # For JVM, use JUnit 6 testImplementation
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
    fi
    if ! grep -q '^mutflow {' "$build_file"; then
        cat >> "$build_file" << 'EOF'

mutflow {
    enabled = true
}
EOF
        echo "  Added mutflow configuration"
    fi
fi

if [[ "$IS_KMP" == "0" && "$JUNIT4_MODE" == "0" ]] && ! grep -q 'useJUnitPlatform' "$build_file"; then
    cat >> "$build_file" << 'EOF'

tasks.withType<org.gradle.api.tasks.testing.Test>().configureEach {
    useJUnitPlatform()
}
EOF
    echo "  Enabled JUnit Platform"
fi

KOTLIN_VERSION="$REQUIRED_KOTLIN_VERSION"
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
if [[ "$MODULE_PATH" != ":" ]]; then
    echo "  1. Run: /mutation-testing $PROJECT_PATH --module $MODULE_PATH"
else
    echo "  1. Run: /mutation-testing $PROJECT_PATH"
fi
echo "     The saboteur agent will annotate @MutationTarget and configure the selected test integration"
if [[ "$JUNIT4_MODE" == "1" ]]; then
    echo "     For JUnit 4, test classes use @RunWith(MutFlowRunner::class)"
fi
if [[ "$MODULE_PATH" == ":" ]]; then
    gradle_task="mutationResults"
else
    gradle_task="${MODULE_PATH}:mutationResults"
fi
echo "  2. test-executor runs: gradle $gradle_task"
echo "  3. test-auditor parses results and reports score"
echo "  4. test-refactor-specialist proposes boundary tests for survivors"
echo "  5. Copilot CLI: restart or run /skills reload, then use /mutation-testing"
echo ""
echo "Or run directly: cd $PROJECT_PATH && gradle $gradle_task"
