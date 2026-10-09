# How to set up mutation testing manually

Use this guide when the root `bootstrap.sh install` command does not fit your
project, or when you want to control each step yourself.

## Prerequisites

- Java 26
- Gradle 9.8.0 to reproduce the repository's integration-tested baseline
- Kotlin 2.4.21
- Python 3.10 or newer (required by the root `bootstrap.sh` install/update command)

Kotlin `2.4.21` lists Gradle `9.7.0` as its latest fully supported version.
The toolkit integration tests pass on Gradle `9.8.0`, but that does not extend
Kotlin's documented support range. Check the
[Kotlin Gradle plugin compatibility table](https://kotlinlang.org/docs/gradle-configure-project.html#check-for-compatibility)
when choosing a version for your project.

## Copy files

Commit or save your target project's existing changes first. Review and merge
toolkit-owned files rather than overwriting customizations.

Copy these shared assets from the toolkit checkout into your project root:

- `.mutation-testing/AGENT-USAGE.md`, the client-neutral installed agent guide
- `.mutation-testing/mutation-results.gradle.kts`
- `.mutation-testing/mutation-results-src/`, the typed module source copied to `buildSrc/`

The root installer creates `.mutation-testing/manifest.json`. Do not copy or
edit that metadata file by hand. A manual installation without a manifest
cannot use `bootstrap.sh update`. The updater stops before writing. Update the
files manually. Do not copy internal installer or updater scripts into the
target project.

Copy each client layer you plan to use:

| Client | Files |
|--------|-------|
| OMP | `.omp/agents/` and `.omp/skills/mutation-testing/` |
| Copilot CLI | `.github/skills/mutation-testing/` and all five `.github/agents/mutation-testing-*.agent.md` profiles |

Gradle-only execution needs neither client. For a dual-client installation,
copy both client layers. The root installer installs both adapters when the
project fits its supported layout.

Append a mutation-testing pointer to the existing `AGENTS.md` without
replacing project policy: `For mutation-testing setup, execution, audits, or
troubleshooting, read [.mutation-testing/AGENT-USAGE.md](.mutation-testing/AGENT-USAGE.md) first.`
The setup command installs this guide and adds the pointer once. Conflicts and
symlinked destinations stop setup before modification.

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
    id("io.github.anschnapp.mutflow") version "1.7.0"
    // ... existing plugins
}
```

## Apply the results task

Apply the custom Gradle task that captures mutation results:

```kotlin
apply(from = rootProject.file(".mutation-testing/mutation-results.gradle.kts"))
```

## Set up the typed results module (buildSrc)

The mutation-results task delegates to `ch.trancee.mutation` in `buildSrc/`.
For a new `buildSrc`, copy the source and build template:

```bash
mkdir -p buildSrc/src/main/kotlin/ch/trancee/mutation
mkdir -p buildSrc/src/test/kotlin/ch/trancee/mutation
cp .mutation-testing/mutation-results-src/main/kotlin/ch/trancee/mutation/*.kt buildSrc/src/main/kotlin/ch/trancee/mutation/
cp .mutation-testing/mutation-results-src/test/kotlin/ch/trancee/mutation/*.kt buildSrc/src/test/kotlin/ch/trancee/mutation/
cp .mutation-testing/mutation-results-src/build.gradle.kts buildSrc/build.gradle.kts
```

The template applies Kotlin JVM and serialization plugins, not `kotlin-dsl`.
For an existing `buildSrc`, merge its dependencies and source files. Do not
overwrite the build. The toolkit validates MutFlow `1.7.0` with Kotlin
`2.4.21`; keep the compiler pinned to this tested version unless you update
and revalidate the pair. The setup command resolves direct Kotlin
plugin pins and aliases in the default `gradle/libs.versions.toml` catalog,
including version references. Custom catalog names, nonstandard plugin blocks,
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

Pass `--junit4` to the root `bootstrap.sh install` command instead of the
default JUnit 6 adapter. For manual
setup, keep the project's JUnit 4 engine and add the MutFlow runner:

```kotlin
dependencies {
    testImplementation("io.github.anschnapp.mutflow:mutflow-junit4:1.7.0")
    testImplementation("junit:junit:4.13.2")
}

extra["mutationTest.junitFramework"] = "junit4"
```

The results script selects Gradle's JUnit 4 runner for the `test` task. A
mutation-tested class uses `@RunWith(MutFlowRunner::class)` from
`io.github.anschnapp.mutflow.junit4`. If you need a per-class budget, use
that package's `@MutFlowTest(maxRuns = ...)`. Do not combine JUnit 4 and
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

Add `@MutationTarget` to business-logic classes. Plain JVM projects that use
JUnit 6 use `@MutFlowTest`. Plain JVM projects that use JUnit 4 use
`@RunWith(MutFlowRunner::class)`. KMP common tests stay plain `kotlin.test`.
The targeting agent handles these annotations through either client entry
point. To annotate code by hand, see the
[bootstrap tutorial](../tutorials/bootstrap-existing-project.md) for examples
of `@MutationTarget` and `MutFlow.underTest`. Put `@file:MutationTarget`
before the package declaration for top-level functions. Target nested classes
independently.

## Configure KMP JVM projects

For KMP, replace the plain JVM plugin and test-dependency instructions above
with this module build (keep the shared results module in `buildSrc`):

```kotlin
plugins {
    kotlin("multiplatform") version "2.4.21"
    id("io.github.anschnapp.mutflow") version "1.7.0"
}

apply(from = rootProject.file(".mutation-testing/mutation-results.gradle.kts"))

repositories { mavenCentral() }

kotlin {
    jvm()
    jvmToolchain(26)
    sourceSets {
        commonTest.dependencies { implementation(kotlin("test")) }
    }
}
```

Keep common tests free of JUnit annotations. Upstream adds `@MutFlowTest` in
the mutated JVM compilation. `targets` contains production class or file
patterns, not source-set or task names.

```kotlin
mutflow {
    enabled = true
    maxMutationRuns = 30
}
```

Run `gradle mutationResults`. The adapter selects dedicated
`mutflow<Target>Test` JVM tasks and their report directories. Normal `jvmTest`
is not a mutation run.
KMP JVM uses MutFlow's generated JUnit 6 integration. Use `--junit4` only for
plain JVM modules.
MutFlow dependencies are added to common source sets, so all declared targets
must resolve compatible variants. In the validated `1.7.0` baseline, MutFlow
publishes JVM, `linuxX64`, and `mingwX64`, but not iOS or Android Native
variants. Selecting only `mutflowJvmTest` does not avoid those dependencies.
Use a separate JVM-only build model for unsupported target combinations.

For a conventional multi-module project with a catalog alias and the default
module directory mapping, install from the build root and select the module:

```bash
"/absolute/toolkit/bootstrap.sh" install "/absolute/target" --kmp --module :module
./gradlew :module:mutationResults
```

The toolkit files and `buildSrc` are installed at the root. Only the selected
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

Use the root command from a toolkit checkout that has been fast-forwarded to an
approved source revision. The updater reads only that local checkout. It does
not fetch or execute remote code. This repository currently has no tagged stable
release channel, so updates use the exact local checkout and record its Git
revision when available.

```bash
git -C "/absolute/toolkit" pull --ff-only
"/absolute/toolkit/bootstrap.sh" update "/absolute/target" --dry-run
"/absolute/toolkit/bootstrap.sh" update "/absolute/target"
```

The updater requires a valid `.mutation-testing/manifest.json`. If it is absent
or invalid, the updater stops before writing. It does not adopt an untracked
installation. The manifest records the source revision and SHA-256 hashes for
managed toolkit files, including generated `buildSrc` copies. Files matching
their last installed hash can be updated. Local edits, missing managed files,
symlinks, and incompatible file types are preserved and reported. After
reviewing a specific diff, approve only that exact project-relative file with a
repeated `--force <path>` option. Do not use `--force` as a blanket merge
strategy.

The dry run previews creates, updates, conflicts, and diffs. If a canonical
results source conflicts, its generated `buildSrc` copy is not refreshed. The
updater does not rewrite Gradle build wiring, change dependency pins, or alter
the schema 2 report contract. OMP-native agents and skills remain under
`.omp/agents/` and `.omp/skills/`.

For older `io.omp.mutation` namespace installations, namespace changes are not a
path-only migration. Manually compare the `buildSrc` sources and tests, preserve
unrelated convention code, update imports and the results script together, and
validate schema 2 consumers. Never delete legacy code merely to clear an
installer conflict. See the
[results contract](../reference/mutation-results-format.md).

After updating, inspect the selected module build, verify `buildSrc` source
parity, and run the configured `mutationResults` task. Compilation or discovery
failure invalidates retained JSON. Use current JUnit XML and reports as
described in the [results contract](../reference/mutation-results-format.md).

## Configure a multi-module project

The root `bootstrap.sh install` command can configure one conventional Gradle
module at a time with `--module :path`. Keep the shared typed module in root
`buildSrc`. Module-local results go under the selected module's build
directory:

```bash
./gradlew :service:mutationResults
```

The toolkit does not install every subproject automatically or combine
module reports into one score. Repeat setup for each supported module. Use
qualified tasks. See
[multi-module CI](run-in-github-actions.md#adjust-a-multi-module-build).
