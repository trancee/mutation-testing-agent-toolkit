# Tutorial: Bootstrap mutation testing into an existing Kotlin project

We'll add mutation testing to an existing Kotlin/JVM project, annotate one
business rule and its test, then inspect the first results.

This tutorial assumes you have a Kotlin/JVM project that uses Gradle. If you
do not, create one with
[the first mutation test tutorial](first-mutation-test.md).

## Prerequisites

- A Kotlin/JVM project with a multiline `plugins` block and Kotlin `2.4.20`
  pinned directly or through the default `gradle/libs.versions.toml` catalog
- Java 26 and Gradle 9.8.0
- Python 3.10 or newer for the root `bootstrap.sh` command
- The Mutation Testing Agent Toolkit cloned to a known location

These versions match the repository's integration-test baseline. For the
Kotlin and Gradle support range, see
[toolchain compatibility](../how-to/run-checks.md#toolchain-compatibility).

Commit or save your current work before you run the installer. The installer
edits Gradle files in place and does not create backups. It preserves existing
`.bak` files.

If you have a custom catalog, a nonstandard module directory, or user-owned
`buildSrc`, follow [manual setup](../how-to/manual-setup.md). If the
project already has a toolkit installation, review the
[update guide](../how-to/update-installation.md) first.

## Step 1: Run the root `bootstrap.sh install` command

Run the root command from your toolkit checkout. It installs shared files and
configures Gradle:

```bash
# Replace with the path to the Mutation Testing Agent Toolkit
MUTATION_TOOLKIT_DIR="/path/to/mutation-testing-agent-toolkit"

"$MUTATION_TOOLKIT_DIR/bootstrap.sh" install .
```

The command prints a summary like this. The file list depends on the target
project:

```
Bootstrapping mutation testing into: .
Mode: JVM
Module: :
Test framework: JUnit 6

Checking and installing toolkit-managed files...
CREATE .mutation-testing/AGENT-USAGE.md
CREATE .mutation-testing/mutation-results.gradle.kts
CREATE .omp/agents/test-quality-reviewer.md
CREATE .omp/skills/mutation-testing/SKILL.md
CREATE .github/skills/mutation-testing/SKILL.md
CREATE buildSrc/src/main/kotlin/ch/trancee/mutation/MutationResults.kt
UPDATED .mutation-testing/manifest.json
Configuring settings.gradle.kts...
  Added pluginManagement block
Configuring module build.gradle.kts...
  Added mutflow plugin
  Applied mutation-results.gradle.kts
  Added JUnit 6 dependencies
  Added mutflow configuration
  Enabled JUnit Platform
  Verified compiler-coupled Kotlin 2.4.20
Typed mutation-results sources are installed in buildSrc/

✅ Bootstrap complete!
```

The installer modifies Gradle configuration and installs shared assets under
`.mutation-testing/`, OMP-native files under `.omp/`, Copilot files under
`.github/`, and generated sources under `buildSrc/`. It does not change
production or test sources.

If `pluginManagement` already exists, verify that its repositories include
`mavenCentral()`. The installer leaves existing blocks unchanged.

Start Copilot CLI in the target project and invoke `/mutation-testing`. If
Copilot is already running, use `/skills reload` first.

For a plain JVM project that already uses JUnit 4, add `--junit4` to the setup
command. The installer uses `@RunWith(MutFlowRunner::class)`. It does not
convert the project to JUnit 6.

For a catalog-based KMP subproject, use `--kmp --module :module` and run the
qualified task from the build root. See [manual setup](../how-to/manual-setup.md)
for both configurations and their limits.

## Step 2: Verify the Gradle setup

Open `build.gradle.kts` and check for these entries:

1. The mutflow plugin in the `plugins` block:

```kotlin
plugins {
    id("io.github.anschnapp.mutflow") version "1.6.1"
    // ... existing plugins
}
```

1. The mutation-results script applied:

```kotlin
apply(from = rootProject.file(".mutation-testing/mutation-results.gradle.kts"))
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

Add `@MutationTarget` to the classes with business rules. For example:

```kotlin
package com.example.service

class UserService {
    fun isEligible(age: Int, isActive: Boolean): Boolean {
        return age >= 18 && isActive
    }
}
```

Add the annotation to `UserService`:

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

`@MutationTarget` marks classes that mutflow mutates. See
[About mutflow's architecture](../explanation/mutflow-architecture.md) for
the available mutation variants.

## Step 4: Annotate tests with @MutFlowTest

Open the existing test file. Add `@MutFlowTest` and wrap business-logic calls
in `MutFlow.underTest { }`:

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

Wrap the call to the `@MutationTarget` instance in `MutFlow.underTest { }`.
Do not wrap the `assertTrue` call.

For more on this pattern, see
[How to fix surviving mutations](../how-to/fix-surviving-mutations.md).

## Step 5: Run mutation testing

Run the `mutationResults` task:

```bash
gradle mutationResults
```

The mutflow plugin supplies its matching JUnit integration. The installer
checks the Kotlin pin before changing files. It does not guess a compiler
version or use a default.

The mutation summary lists discovered, tested, killed, survived,
timed-out, and remaining-untested counts. Exact counts depend on the selected
business logic and operators. For this eligibility rule, look for a survivor
that changes `>=` to `>`. A test at age 25 does not cover the age-18 boundary.
The task also writes a human-readable summary to
`build/reports/mutation-results.md`. When run in GitHub Actions, it appends the
summary table to the workflow run's job summary.

The deliberately weak test leaves survivors. With upstream's default strict
mode, `mutationResults` writes the Markdown summary and schema 2 JSON before it
returns a nonzero exit status. Survivors are mutation outcomes, not execution
gaps. The structured report is
`build/reports/mutation-results.json`. Its `gaps` field should be zero for a
complete run. Compilation or discovery failures can prevent current reports
from being written.

If mutations survive, add boundary tests to kill them. See
[How to interpret and act on results](../how-to/interpret-results.md).

## Continue

Follow [the agent-assisted tutorial](agent-assisted-mutation-test.md) to review
mutation results and improve a test with either client.
