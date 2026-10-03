# Tutorial: Mutation-test shared Kotlin code on the JVM

We'll create a minimal Kotlin Multiplatform project, mutation-test its common
business logic using the JVM target, and compare budgeted and full reports.
No agent client is needed for this lesson.

## Prerequisites

- Java 26 and Gradle 9.8.0 on `PATH`
- This toolkit cloned to a known absolute path
- Network access for the first build
- No ambient `MUTFLOW_*` overrides

## Step 1: Create the project

```bash
mkdir mutation-kmp-tutorial
cd mutation-kmp-tutorial
mkdir -p src/commonMain/kotlin src/commonTest/kotlin
```

Create `settings.gradle.kts`:

```kotlin
rootProject.name = "mutation-kmp-tutorial"
```

Create `build.gradle.kts`:

```kotlin
plugins {
    kotlin("multiplatform") version "2.4.20"
}

repositories { mavenCentral() }

kotlin {
    jvm()
    jvmToolchain(26)
    sourceSets {
        commonTest.dependencies { implementation(kotlin("test")) }
    }
}
```

We declare only a JVM target. This lesson does not validate Native, Android,
JS, or arbitrary multi-target dependency compatibility.

## Step 2: Add common business logic and tests

Create `src/commonMain/kotlin/Decision.kt`:

```kotlin
package example

import io.github.anschnapp.mutflow.MutationTarget

@MutationTarget
class Decision {
    fun positive(value: Int): Boolean = value > 0
}
```

Create `src/commonTest/kotlin/DecisionTest.kt`:

```kotlin
package example

import io.github.anschnapp.mutflow.MutFlow
import kotlin.test.Test
import kotlin.test.assertFalse
import kotlin.test.assertTrue

class DecisionTest {
    @Test
    fun boundary() {
        assertTrue(MutFlow.underTest { Decision().positive(1) })
        assertFalse(MutFlow.underTest { Decision().positive(0) })
        assertFalse(MutFlow.underTest { Decision().positive(-1) })
    }
}
```

Keep common tests free of JUnit imports and `@MutFlowTest`. Upstream supplies
the JVM annotation in the dedicated mutated test compilation.

## Step 3: Install KMP JVM reporting

```bash
MUTATION_TOOLKIT_DIR="/path/to/mutation-testing-agent-toolkit"
bash "$MUTATION_TOOLKIT_DIR/.omp/bootstrap-mutation-testing.sh" . --kmp
```

Use the absolute path to your clone. The installer adds mutflow, its plugin
repository, and the typed results module. Our annotation imports now resolve.

Append to `build.gradle.kts`:

```kotlin
mutflow {
    maxMutationRuns = 1
}
```

This DSL budget allows one mutation in addition to the baseline; it is not
plain JVM annotation `maxRuns`, which includes the baseline.

## Step 4: Inspect a budgeted run

```bash
gradle mutationResults '-PmutationTest.includes=example.DecisionTest' --console=plain
```

The executed mutation task is `mutflowJvmTest`, not ordinary `jvmTest`. Open
`build/reports/mutation-results.json`. For the pinned plugin, expect:

```json
{
  "schemaVersion": 2,
  "totalMutations": 4,
  "mutationsEvaluated": 1,
  "killed": 1,
  "untestedMutations": 3,
  "gaps": 0,
  "mutationScore": 1.0
}
```

This excerpt omits other report fields. A 100% score here describes only one
evaluated mutation, not full discovery coverage.

## Step 5: Evaluate the full scope

Replace `maxMutationRuns = 1` with:

```kotlin
mutflow {
    maxMutationRuns = Int.MAX_VALUE
}
```

Run the same command again. Expect four discovered/evaluated/killed mutations,
zero untested mutations, zero gaps, and a successful build. The report's
identities use `example.DecisionTest::boundary()`.

## Continue

For named JVM targets, manual wiring, or module-local tasks, see
[manual setup](../how-to/manual-setup.md). For CI policies that reject
budget-limited evidence, see [the GitHub Actions guide](../how-to/run-in-github-actions.md).
