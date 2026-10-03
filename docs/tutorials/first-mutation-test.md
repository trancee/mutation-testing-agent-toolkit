# Tutorial: Your first mutation test in 10 minutes

In this tutorial, we'll create a Kotlin project with mutation testing using mutflow. We will build a small `Calculator` class, write tests for it, and use mutation testing to find gaps in those tests. By the end we'll have a project that achieves **100% mutation coverage**.

This tutorial assumes no prior knowledge of mutation testing.

## Prerequisites

- Java 26
- Gradle 9.8.0
- Kotlin 2.4.20

If you have [SDKMAN](https://sdkman.io), install Gradle:

```bash
sdk install gradle 9.8.0
```

## Step 1: Create a new Kotlin project

We'll start from scratch. Create a project directory and run Gradle's init:

```bash
mkdir mutation-tutorial
cd mutation-tutorial
gradle init --type kotlin-application
```

Open the project in your IDE. You should see `build.gradle.kts` and `settings.gradle.kts` in the root, plus a `src/` directory with `main/` and `test/` subdirectories.

## Step 2: Add the mutflow plugin

Edit `settings.gradle.kts` to add the plugin management block:

```kotlin
pluginManagement {
    repositories {
        mavenCentral()
        gradlePluginPortal()
    }
}

rootProject.name = "mutation-tutorial"
```

Then edit `build.gradle.kts` to apply the mutflow plugin:

```kotlin
plugins {
    kotlin("jvm") version "2.4.20"
    id("io.github.anschnapp.mutflow") version "1.6.0"
    application
}

kotlin {
    jvmToolchain(26)
}

repositories {
    mavenCentral()
}

dependencies {
    testImplementation("org.junit.jupiter:junit-jupiter-api:6.1.3")
    testImplementation("org.junit.platform:junit-platform-launcher:6.1.3")
}

tasks.test {
    useJUnitPlatform()
    testLogging {
        showStandardStreams = true
        events("passed", "skipped", "failed")
    }
}
```

## Step 3: Write the Calculator class

Create `src/main/kotlin/Calculator.kt`:

```kotlin
package example

import io.github.anschnapp.mutflow.MutationTarget

@MutationTarget
class Calculator {
    fun isPositive(x: Int): Boolean = x > 0

    fun add(a: Int, b: Int): Int = a + b

    fun divide(a: Int, b: Int): Int = a / b
}
```

The `@MutationTarget` annotation marks classes that mutflow should mutate.

## Step 4: Write tests

Create `src/test/kotlin/CalculatorTest.kt`:

```kotlin
package example

import io.github.anschnapp.mutflow.MutFlow
import io.github.anschnapp.mutflow.junit.MutFlowTest
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.Assertions.*

@MutFlowTest
class CalculatorTest {
    private val calc = Calculator()

    @Test
    fun `isPositive returns true for positive numbers`() {
        assertTrue(MutFlow.underTest { calc.isPositive(5) })
    }

    @Test
    fun `isPositive returns false for negative numbers`() {
        assertFalse(MutFlow.underTest { calc.isPositive(-1) })
    }

    @Test
    fun `add returns correct sum`() {
        assertEquals(7, MutFlow.underTest { calc.add(3, 4) })
    }

    @Test
    fun `divide returns correct quotient`() {
        assertEquals(2, MutFlow.underTest { calc.divide(10, 5) })
    }
}
```

The `@MutFlowTest` annotation enables mutflow's JUnit 6 extension. Every call to business logic is wrapped in `MutFlow.underTest { }` so mutflow can inject mutations.

## Step 5: Run the tests

Run the test task:

```bash
gradle test
```

Gradle reports surviving mutations as failed dynamic tests, so the task fails at this point. The mutflow summary still appears at the bottom of the output:

```
╔════════════════════════════════╗
║      MUTATION TESTING SUMMARY  ║
╠════════════════════════════════╣
║  Killed:  3  ✓                 ║
║  Survived: 3  ✗                ║
║  Timed out: 0  ✓               ║
╚════════════════════════════════╝
```

Three mutations survived. This is expected because our tests do not cover boundary values yet.

## Step 6: Add boundary tests to kill survivors

mutflow found mutations our initial tests missed — mutations to `>` and `0` produce the same results at `x = 5` and `x = -1`. We need boundary tests at `x = 0` and `x = 1`. For the full strategy on reading mutation output and choosing test values, see [How to fix surviving mutations](../how-to/fix-surviving-mutations.md).

```kotlin
@Test
fun `isPositive returns false for zero`() {
    assertFalse(MutFlow.underTest { calc.isPositive(0) })
}
```

This catches the `>` → `>=` and `0` → `-1` mutations. The `0` → `1` mutation still survives. Test `x = 1`:

```kotlin
@Test
fun `isPositive returns true for one`() {
    assertTrue(MutFlow.underTest { calc.isPositive(1) })
}
```

Under the mutant, `1 > 1` is `false`, so our assertion catches it.

Re-run `gradle test`. The summary now shows all mutations killed:

```
╔════════════════════════════════╗
║      MUTATION TESTING SUMMARY  ║
╠════════════════════════════════╣
║  Killed:  6  ✓                 ║
║  Survived: 0  ✓                ║
║  Timed out: 0  ✓               ║
╚════════════════════════════════╝
```

**100% mutation coverage achieved.**

## Summary

We created a Kotlin project with mutflow mutation testing. We wrote a `Calculator` with `@MutationTarget`, tests with `@MutFlowTest`, and found that the initial tests missed mutations at boundary values. By adding boundary tests (`isPositive(0)`, `isPositive(1)`), we killed all mutations and achieved **100% mutation coverage**.

For how to interpret mutation testing results and quality bands, see the [How to interpret mutation testing results](../how-to/interpret-results.md) guide.

To understand how mutflow works under the hood, see [About mutflow's test-only mutation compilation](../explanation/mutflow-architecture.md).
