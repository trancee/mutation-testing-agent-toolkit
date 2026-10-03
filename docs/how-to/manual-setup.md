# How to set up mutation testing manually

Use this guide when the bootstrap script does not fit your project, or when you want to control each step yourself.

## Prerequisites

- Java 21 (or newer)
- Gradle 9.x
- Kotlin 2.4.x

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
    id("io.github.anschnapp.mutflow") version "1.1.1"
    // ... existing plugins
}
```

## Apply the results task

Apply the custom Gradle task that captures mutation results:

```kotlin
apply(from = rootProject.file(".omp/mutation-results.gradle.kts"))
```

## Set up the typed results module (buildSrc)

The mutation-results task delegates to a typed Kotlin module in `buildSrc/`. Copy the module source and generate the build file:

```bash
mkdir -p buildSrc/src/main/kotlin/io/omp/mutation
mkdir -p buildSrc/src/test/kotlin/io/omp/mutation
cp .omp/mutation-results-src/main/kotlin/io/omp/mutation/*.kt buildSrc/src/main/kotlin/io/omp/mutation/
cp .omp/mutation-results-src/test/kotlin/io/omp/mutation/*.kt buildSrc/src/test/kotlin/io/omp/mutation/
cp .omp/mutation-results-src/build.gradle.kts buildSrc/build.gradle.kts
```

The `buildSrc/build.gradle.kts` template applies the `kotlin-dsl` plugin with `kotlinx-serialization` and depends on `kotlinx-serialization-json`. Adjust the Kotlin and serialization versions to match your project.

## Add test dependencies

Add the mutflow JUnit 6 integration and JUnit Jupiter to your dependencies:

```kotlin
dependencies {
    testImplementation("org.junit.jupiter:junit-jupiter-api:6.1.3")
    testImplementation("org.junit.platform:junit-platform-launcher:6.1.3")
    testImplementation("io.github.anschnapp.mutflow:mutflow-junit6:1.1.1")
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
