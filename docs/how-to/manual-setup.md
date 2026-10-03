# How to set up mutation testing manually

Use this guide when the bootstrap script does not fit your project, or when you want to control each step yourself.

## Prerequisites

- Java 26
- Gradle 9.8.0
- Kotlin 2.4.20

## Copy files

Copy these from the mutation testing repo into your project root:

- `.omp/agents/`
- `.omp/skills/mutation-test/`
- `.omp/mutation-results.gradle.kts`
- `.omp/mutation-results-src/`, the typed module source copied to `buildSrc/`
- `.github/skills/omp-mutation-test/` for GitHub Copilot CLI
- `.github/agents/omp-mutation-test-*.agent.md` for the Copilot mutation-testing roles

The Copilot skill and agent files are independent of the OMP files. Keep both
sets if users of the project need both client entry points.

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
upgrade or downgrade the compiler. Bootstrap rejects unknown alias/catalog
versions, nonstandard plugin-block layouts, and user-owned `buildSrc` builds;
configure those manually.

For installations using `io.omp.mutation`, replace the toolkit-owned source
directories with the new `ch/trancee/mutation` copies and update the results
script together. Preserve all unrelated sources and convention plugins. Schema 2
changes score/count semantics and test identities; migrate consumers using the
[results reference](../reference/mutation-results-format.md#compatibility).

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

## Configure mutflow

Add the mutflow configuration block to `build.gradle.kts`:

```kotlin
mutflow {
    enabled = true
}
```

## Annotate your code

Add `@MutationTarget` to business-logic classes and `@MutFlowTest` to test classes. The `test-saboteur` agent handles this automatically when you run `/mutation-test`. To do it by hand, see the [bootstrap tutorial](../tutorials/bootstrap-existing-project.md) for the annotation patterns.

## Configure KMP JVM projects

Use the same plugin and results script with a `kotlin("multiplatform")` project
and a JVM target. Put `kotlin("test")` in `commonTest` dependencies. Keep common
tests free of JUnit annotations; upstream synthesizes `@MutFlowTest` in its
mutated JVM compilation. `targets` contains production class/file patterns,
not source-set or task names.

```kotlin
mutflow {
    enabled = true
    maxMutationRuns = 30
}
```

Run `gradle mutationResults`; the adapter selects dedicated `mutflow<Target>Test`
tasks and their report directories. Normal `jvmTest` is not a mutation run.
This toolkit does not collect Native or JUnit 4 results.
