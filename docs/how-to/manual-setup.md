# How to set up mutation testing manually

Use this guide when the bootstrap script does not fit your project, or when you want to control each step yourself.

## Prerequisites

- Java 26
- Gradle 9.8.0
- Kotlin 2.4.20

## Copy files

Commit or save your target project's existing changes first. Review and merge
toolkit-owned files rather than overwriting customizations.

Copy these from the mutation testing repo into your project root:

- `.omp/mutation-results.gradle.kts`
- `.omp/mutation-results-src/`, the typed module source copied to `buildSrc/`
- `.omp/AGENT-USAGE.md`, the self-contained installed agent guide
- `.omp/bootstrap-mutation-testing.sh` if you need the agent-driven `setup` command

Copy the complete client layer(s) you intend to use:

| Client | Files |
|--------|-------|
| OMP | `.omp/agents/` and `.omp/skills/mutation-testing/` |
| Copilot CLI | `.github/skills/mutation-testing/` and all five `.github/agents/mutation-testing-*.agent.md` profiles |

Gradle-only execution needs neither client. Agent-driven setup expects the
bootstrap's source layout and both client file sets; use the installer for a
complete dual-client installation.

Append a mutation-testing pointer to the target's existing `AGENTS.md` without
replacing its policy: `For mutation-testing setup, execution, audits, or
troubleshooting, read [.omp/AGENT-USAGE.md](.omp/AGENT-USAGE.md) first.`
Bootstrap installs this guide and adds the pointer once. A differing installed
guide or symlinked destination stops setup before modification; merge updates
explicitly.

## Add plugin management

Edit `settings.gradle.kts` to add the plugin management block:

```kotlin
pluginManagement {
    repositories {
        mavenCentral()
        gradlePluginPortal()
    }
}
```

mutflow is published to Maven Central only, not the Gradle Plugin Portal. `mavenCentral()` is required.

## Add the mutflow plugin

Edit `build.gradle.kts` to apply the plugin:

```kotlin
plugins {
    id("io.github.anschnapp.mutflow") version "1.6.0"
    // ... existing plugins
}
```

## Apply the results task

Apply the custom Gradle task that captures mutation results:

```kotlin
apply(from = rootProject.file(".omp/mutation-results.gradle.kts"))
```

## Set up the typed results module (buildSrc)

The mutation-results task delegates to `ch.trancee.mutation` in `buildSrc/`.
For a new `buildSrc`, copy the source and build template:

```bash
mkdir -p buildSrc/src/main/kotlin/ch/trancee/mutation
mkdir -p buildSrc/src/test/kotlin/ch/trancee/mutation
cp .omp/mutation-results-src/main/kotlin/ch/trancee/mutation/*.kt buildSrc/src/main/kotlin/ch/trancee/mutation/
cp .omp/mutation-results-src/test/kotlin/ch/trancee/mutation/*.kt buildSrc/src/test/kotlin/ch/trancee/mutation/
cp .omp/mutation-results-src/build.gradle.kts buildSrc/build.gradle.kts
```

The template applies Kotlin JVM and serialization plugins, not `kotlin-dsl`.
For an existing `buildSrc`, merge its dependencies and source files instead of
overwriting the build. mutflow 1.6.0 requires Kotlin 2.4.20; do not independently
upgrade or downgrade the compiler. Bootstrap resolves direct Kotlin plugin pins
and aliases in the default `gradle/libs.versions.toml` catalog, including
version references. Custom catalog names, nonstandard plugin-block layouts,
custom `projectDir` mappings, and user-owned `buildSrc` builds require manual
setup.

## Add test dependencies

Add JUnit Jupiter dependencies. The mutflow plugin supplies its matching
JUnit 6 integration automatically:

```kotlin
dependencies {
    testImplementation("org.junit.jupiter:junit-jupiter-api:6.1.3")
    testImplementation("org.junit.platform:junit-platform-launcher:6.1.3")
}

tasks.test {
    useJUnitPlatform()
}
```

### Use JUnit 4 in a plain JVM module

Pass `--junit4` to bootstrap instead of the default JUnit 6 adapter. For manual
setup, keep the project's JUnit 4 engine and add the MutFlow runner:

```kotlin
dependencies {
    testImplementation("io.github.anschnapp.mutflow:mutflow-junit4:1.6.0")
    testImplementation("junit:junit:4.13.2")
}

extra["mutationTest.junitFramework"] = "junit4"
```

The results script selects Gradle's JUnit 4 runner for the `test` task. A
mutation-tested class uses `@RunWith(MutFlowRunner::class)` from
`io.github.anschnapp.mutflow.junit4`. If a per-class budget is required, use
that package's `@MutFlowTest(maxRuns = ...)`; do not combine the JUnit 4 and
JUnit 6 integrations in one test source set. Existing custom JUnit 4 runners
need a manual MutFlow adapter.

## Configure mutflow

Add the mutflow configuration block to `build.gradle.kts`:

```kotlin
mutflow {
    enabled = true
}
```

## Annotate your code

Add `@MutationTarget` to business-logic classes. Plain JVM/JUnit 6 classes use
`@MutFlowTest`; plain JVM/JUnit 4 classes use
`@RunWith(MutFlowRunner::class)`; KMP common tests stay plain `kotlin.test`.
The targeting agent handles this through either client entry point. To do it
by hand, see the [bootstrap tutorial](../tutorials/bootstrap-existing-project.md)
for annotation and `MutFlow.underTest` patterns. Use `@file:MutationTarget`
before the package declaration for top-level functions; nested classes must
be targeted independently.

## Configure KMP JVM projects

For KMP, replace the plain JVM plugin and test-dependency instructions above
with this module build (keep the shared results module in `buildSrc`):

```kotlin
plugins {
    kotlin("multiplatform") version "2.4.20"
    id("io.github.anschnapp.mutflow") version "1.6.0"
}

apply(from = rootProject.file(".omp/mutation-results.gradle.kts"))

repositories { mavenCentral() }

kotlin {
    jvm()
    jvmToolchain(26)
    sourceSets {
        commonTest.dependencies { implementation(kotlin("test")) }
    }
}
```

Keep common tests free of JUnit annotations; upstream synthesizes
`@MutFlowTest` in its mutated JVM compilation. `targets` contains production class/file patterns,
not source-set or task names.

```kotlin
mutflow {
    enabled = true
    maxMutationRuns = 30
}
```

Run `gradle mutationResults`; the adapter selects dedicated `mutflow<Target>Test`
JVM tasks and their report directories. Normal `jvmTest` is not a mutation run.
KMP JVM uses MutFlow's generated JUnit 6 integration; `--junit4` is for plain
JVM modules, not KMP.
MutFlow dependencies are added to common source sets, so all declared targets
must resolve compatible variants. In the validated `1.6.0` baseline, MutFlow
publishes JVM, `linuxX64`, and `mingwX64`, but not iOS or Android Native
variants. Selecting only `mutflowJvmTest` does not avoid those dependencies;
use a separate JVM-only build model for unsupported target combinations.

For a conventional multi-module project with a catalog alias and the default
module directory mapping, install from the build root and select the module:

```bash
bash "/absolute/toolkit/.omp/bootstrap-mutation-testing.sh" "/absolute/target" --kmp --module :module
./gradlew :module:mutationResults
```

The toolkit files and `buildSrc` are installed at the root; only the selected
module build file receives the mutflow and results wiring.

## Verify setup

Run from the configured module, using its wrapper when available:

```bash
gradle mutationResults '-PmutationTest.includes=example.CalculatorTest'
```

Replace the filter with your test class. Expect
`build/reports/mutation-results.md` for the human-readable summary and
`build/reports/mutation-results.json` with `schemaVersion: 2` and current
class-qualified identities. GitHub Actions also adds the summary table to the
workflow run's job summary. Strict survivors/timeouts fail the task after
writing both reports. Compilation or no-match discovery failures may produce
no current report. For direct filters and exit semantics, see the
[command reference](../reference/mutation-testing-command.md#direct-gradle-execution).

## Upgrade an existing installation

1. Save existing changes and compare installed toolkit-owned files with this
   repository. The installer overwrites same-path OMP/results files but refuses
   differing Copilot profiles; do not treat rerunning it as a safe merge.
2. For `io.omp.mutation` installations, remove only the legacy toolkit-owned
   Kotlin files from `buildSrc/src/main/kotlin/io/omp/mutation` and the matching
   test directory. Replace them with the `ch/trancee/mutation` copies. Also
   replace the installed `.omp/mutation-results-src` template sources and update
   imports in the shared results script. Preserve unrelated convention code.
3. Merge the current build template, results script, both client skills, role
   profiles, and installed agent guide. Resolve differing Copilot files and
   guide explicitly; never delete user-owned customizations merely to satisfy
   it.
4. Update JSON consumers for [schema 2](../reference/mutation-results-format.md#compatibility):
   discovered/evaluated/untested totals, null scores for gaps, and qualified
   identities. Unversioned schema 1 data is not interchangeable.
5. Rerun the configured mutation task and check current JSON and JUnit XML.
   Validate any custom consumers before adopting the new report.

## Configure a multi-module project

Bootstrap can configure one conventional Gradle module at a time with
`--module :path`. Keep the shared typed module in root `buildSrc`; module-local
results go under the selected module's build directory:

```bash
./gradlew :service:mutationResults
```

The toolkit does not install every subproject automatically or combine
module reports into one score. Repeat setup for each supported module, and use
qualified tasks; see
[multi-module CI](run-in-github-actions.md#adjust-a-multi-module-build).
