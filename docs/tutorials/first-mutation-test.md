# Tutorial: Your first mutation test

We'll create a small Kotlin JVM project, see a mutation survive, and add
boundary assertions that kill it. This lesson uses mutflow directly; no agent
client or toolkit installation is needed.

## Prerequisites

- Java 26 and Gradle 9.8.0 available on `PATH`
- An empty working directory for the project
- Network access to Maven Central for the first build

## Step 1: Create a minimal project

```bash
mkdir mutation-tutorial
cd mutation-tutorial
mkdir -p src/main/kotlin src/test/kotlin
```

Create `settings.gradle.kts`:

```kotlin
pluginManagement {
    repositories {
        mavenCentral()
        gradlePluginPortal()
    }
}

rootProject.name = "mutation-tutorial"
```

Create `build.gradle.kts`:

```kotlin
plugins {
    kotlin("jvm") version "2.4.21"
    id("io.github.anschnapp.mutflow") version "1.7.0"
}

kotlin { jvmToolchain(26) }

repositories { mavenCentral() }

dependencies {
    testImplementation("org.junit.jupiter:junit-jupiter-api:6.1.3")
    testImplementation("org.junit.platform:junit-platform-launcher:6.1.3")
}

tasks.test {
    useJUnitPlatform()
    testLogging.showStandardStreams = true
}
```

We use a minimal build rather than `gradle init`, whose generated module and
version-catalog layout may differ.

## Step 2: Write the business rule

Create `src/main/kotlin/Calculator.kt`:

```kotlin
package example

import io.github.anschnapp.mutflow.MutationTarget

@MutationTarget
class Calculator {
    fun isPositive(x: Int): Boolean = x > 0
}
```

`@MutationTarget` selects the class for mutation compilation.

## Step 3: Write an initial test

Create `src/test/kotlin/CalculatorTest.kt`:

```kotlin
package example

import io.github.anschnapp.mutflow.MutFlow
import io.github.anschnapp.mutflow.junit.MutFlowTest
import org.junit.jupiter.api.Assertions.assertFalse
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.Test

@MutFlowTest
class CalculatorTest {
    @Test
    fun positiveAndNegative() {
        assertTrue(MutFlow.underTest { Calculator().isPositive(5) })
        assertFalse(MutFlow.underTest { Calculator().isPositive(-1) })
    }
}
```

We wrap the business call, not the assertion, in `MutFlow.underTest`.

## Step 4: Observe a survivor

Before running, clear any `MUTFLOW_*` environment overrides from earlier
experiments. Run:

```bash
gradle test --console=plain
```

The baseline passes, but strict mutation verification fails the task because
our test does not distinguish some variants. Look for:

```text
✗ (Calculator.kt:7) > → >=
    SURVIVED - no test caught this mutation!
```

The exact source line depends on file formatting. At zero, the original
`0 > 0` is false, while the mutant's `0 >= 0` is true.

## Step 5: Add boundary assertions

Add this method inside `CalculatorTest`:

```kotlin
@Test
fun zeroAndOne() {
    assertFalse(MutFlow.underTest { Calculator().isPositive(0) })
    assertTrue(MutFlow.underTest { Calculator().isPositive(1) })
}
```

Zero distinguishes `>` from `>=`; one also catches a boundary constant
changed from `0` to `1`.

Run again:

```bash
gradle test --console=plain
```

With this pinned version, the summary reports four discovered and tested
mutations, all killed, none survived or timed out, and zero remaining untested.
The build succeeds. We now have a 100% score for this small selected scope;
that does not prove every possible fault is covered.

## Continue

To install agent orchestration and schema 2 JSON reporting, follow
[the bootstrap tutorial](bootstrap-existing-project.md). For a larger
working example, run the repository's
[sample project](../../README.md#sample-project).
