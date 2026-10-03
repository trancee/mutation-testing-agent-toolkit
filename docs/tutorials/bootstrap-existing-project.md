# Tutorial: Bootstrap mutation testing into an existing Kotlin project

In this tutorial, we'll take an existing Kotlin project and add mutation testing to it. We will run a bootstrap script that installs all the necessary files, configure mutflow, annotate our code, and run our first mutation test. By the end, we'll have mutation testing running on our existing code.

This tutorial assumes you have a Kotlin JVM project with Gradle. If you don't, see the [first mutation test tutorial](first-mutation-test.md) instead.

## Prerequisites

- An existing Kotlin JVM project with Kotlin `2.4.20` pinned directly or
  through the conventional `gradle/libs.versions.toml` plugin alias, using a
  multiline `plugins` block
- Java 26 and Gradle 9.8.0
- The Mutation Testing Agent Toolkit cloned to a known location

Start with a clean worktree or save your changes. The script edits the build
in place; it preserves existing `.bak` files but does not create a backup.
If you have a custom catalog, nonstandard module directory mapping, user-owned
`buildSrc`, or legacy toolkit installation, follow
[manual setup](../how-to/manual-setup.md) instead.

## Step 1: Run the bootstrap script

We'll use the bootstrap script to copy the .omp files and configure Gradle. From your project root:

```bash
# Replace with the path to the Mutation Testing Agent Toolkit
MUTATION_TOOLKIT_DIR="/path/to/mutation-testing-agent-toolkit"

"$MUTATION_TOOLKIT_DIR/.omp/bootstrap-mutation-testing.sh" .
```

We'll see output like:

```
Bootstrapping mutation testing into: .
Mode: JVM
Module: :
Test framework: JUnit 6

Copying .omp agents, skills, and scripts...
Installing GitHub Copilot skill and agents...
Configuring settings.gradle.kts...
  Added pluginManagement block
Configuring module build.gradle.kts...
  Added mutflow plugin
  Applied mutation-results.gradle.kts
  Added JUnit 6 dependencies
  Added mutflow configuration
  Enabled JUnit Platform
  Verified compiler-coupled Kotlin 2.4.20
Setting up typed mutation-results module (buildSrc)...
  Created buildSrc/ with typed MutationResults module (Kotlin 2.4.20)

✅ Bootstrap complete!
```

The script modified our Gradle configuration and installed `.omp/`, `buildSrc/`,
and the Copilot files. It has not changed production or test sources yet.
If `pluginManagement` already existed, verify that its repositories include
`mavenCentral()`; the script leaves existing plugin-management blocks alone.

It also installs `.github/skills/mutation-testing/` and the five
`.github/agents/mutation-testing-*.agent.md` profiles. Start Copilot CLI in the
target project and invoke `/mutation-testing`; if Copilot is already running,
use `/skills reload` first.

For a plain JVM project that already uses JUnit 4, append `--junit4` to the
bootstrap command. The installed runner uses
`@RunWith(MutFlowRunner::class)`; it does not convert the project to JUnit 6.
For a catalog-based KMP subproject, use `--kmp --module :module` and run the
qualified task from the build root. See [manual setup](../how-to/manual-setup.md)
for both configurations and their limits.

## Step 2: Verify the Gradle setup

Open `build.gradle.kts`. We should see:

1. The mutflow plugin in the `plugins` block:

```kotlin
plugins {
    id("io.github.anschnapp.mutflow") version "1.6.0"
    // ... existing plugins
}
```

1. The mutation-results script applied:

```kotlin
apply(from = rootProject.file(".omp/mutation-results.gradle.kts"))
```

1. JUnit 6 dependencies added:

```kotlin
dependencies {
    testImplementation("org.junit.jupiter:junit-jupiter-api:6.1.3")
    testImplementation("org.junit.platform:junit-platform-launcher:6.1.3")
}
```

1. The mutflow configuration block:

```kotlin
mutflow {
    enabled = true
}
```

1. A `buildSrc/` directory with the typed mutation-results module (data classes and pure parser functions).

## Step 3: Annotate business logic with @MutationTarget

We need to tell mutflow which classes to mutate. Let's say our project has a `UserService` class with business rules:

```kotlin
package com.example.service

class UserService {
    fun isEligible(age: Int, isActive: Boolean): Boolean {
        return age >= 18 && isActive
    }
}
```

We add `@MutationTarget`:

```kotlin
package com.example.service

import io.github.anschnapp.mutflow.MutationTarget

@MutationTarget
class UserService {
    fun isEligible(age: Int, isActive: Boolean): Boolean {
        return age >= 18 && isActive
    }
}
```

The `@MutationTarget` annotation marks classes that mutflow should mutate. See [About mutflow's architecture](../explanation/mutflow-architecture.md) for what gets mutated.

## Step 4: Annotate tests with @MutFlowTest

Open our existing test file. We'll add the `@MutFlowTest` annotation and wrap business logic calls in `MutFlow.underTest { }`:

Before:

```kotlin
package com.example.service

import org.junit.jupiter.api.Test
import org.junit.jupiter.api.Assertions.*

class UserServiceTest {
    private val service = UserService()

    @Test
    fun `isEligible returns true for adult active users`() {
        assertTrue(service.isEligible(25, true))
    }
}
```

After:

```kotlin
package com.example.service

import io.github.anschnapp.mutflow.MutFlow
import io.github.anschnapp.mutflow.junit.MutFlowTest
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.Assertions.*

@MutFlowTest
class UserServiceTest {
    private val service = UserService()

    @Test
    fun `isEligible returns true for adult active users`() {
        assertTrue(MutFlow.underTest { service.isEligible(25, true) })
    }
}
```

We wrap the call to the `@MutationTarget` instance in `MutFlow.underTest { }` so mutflow can inject mutations. We wrap the code under test, not the `assertTrue` call.

For more on this pattern, see [how to fix surviving mutations](../how-to/fix-surviving-mutations.md).

## Step 5: Run mutation testing

Run the `mutationResults` task:

```bash
gradle mutationResults
```

The mutflow plugin supplies its matching JUnit integration. Bootstrap requires
the compatible Kotlin pin before changing files; it does not guess a compiler
version or fall back to a default.

We'll see the mutation summary with discovered, tested, killed, survived,
timed-out, and remaining-untested counts. Exact counts depend on the selected
business logic and operators. For our eligibility rule, look for a survivor
that changes `>=` to `>`: the test at age 25 does not cover the age-18 boundary.

Our deliberately weak test leaves survivors. With upstream's default strict
mode, `mutationResults` writes schema 2 JSON and then exits unsuccessfully.
Survivors are mutation outcomes, not infrastructure gaps. The report is at
`build/reports/mutation-results.json`; its `gaps` should be zero for a complete
run. Compilation or discovery failures can prevent a report from being written.

If some mutations survived, we can add boundary tests to kill them. See the [interpret results](../how-to/interpret-results.md) guide for details.

## Summary

We bootstrapped the Mutation Testing Agent Toolkit into our existing Kotlin project. The bootstrap script handled file copying and Gradle configuration. We annotated our business logic with `@MutationTarget` and our tests with `@MutFlowTest`, wrapping calls in `MutFlow.underTest { }`. Our first mutation test run shows the results.
