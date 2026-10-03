# How to fix surviving mutations

Use this guide when your mutation testing run shows survived mutations that your tests didn't catch.

## Prerequisites

- You've run `gradle test` or `gradle mutationResults` and have results
- At least one mutation survived (shown as ✗ in the summary)

## Workflow

1. Find surviving mutations in the output
2. Identify the source location and operator change
3. Add a boundary test that distinguishes original from mutant
4. Re-run to confirm the mutation is killed

## Step 1: Identify surviving mutations

mutflow's summary shows survivors:

```
║  ✗ (Calculator.kt:35) > → >=                                    ║
║      SURVIVED - no test caught this mutation!                   ║
```

- **Source location**: `Calculator.kt:35`, the file and line of the mutated code
- **Operator change**: `>` → `>=`, the original operator and the mutated variant

## Step 2: Understand the mutation

Read the source at the flagged line:

```kotlin
// Calculator.kt:35
fun isValid(x: Int): Boolean = x > 0 && x < 100
```

The `>` was mutated to `>=`. Under the mutant, `isValid(0)` returns `0 >= 0 = true` instead of `0 > 0 = false`. Your existing tests don't test `x = 0`, so they pass under both original and mutant.

## Step 3: Add a boundary test

Add a test assertion at the boundary value where the operator change produces a different result:

```kotlin
// Original: 0 > 0 = false,  Mutant: 0 >= 0 = true
assertFalse(MutFlow.underTest { calc.isValid(0) })
```

This assertion fails under the mutant (assertFalse expects false, but mutant returns true), killing it.

## Step 4: Use traps for persistent survivors

For plain JVM tests, [trap the survivor](interpret-results.md#step-5-trap-a-mutation-youre-fixing)
so it runs first while iterating. Remove the trap after confirming the fix.

## Common patterns for each operator type

### Relational comparison (`>` → `>=`, `<` → `<=`)

Test the exact boundary value. For `x > 0`, test `x = 0` (false under original, true under `>`→`>=` mutant).

### Constant boundary (`0` → `1`, `100` → `99`)

Test the value just above and below the constant. For `x > 0` with the `0 → 1` mutant, test `x = 1` because the original returns true and the mutant returns false. Testing `x = 0` does not distinguish them because both return false.

### Boolean logic (`&&` → `||`, `==` → `!=`)

Test all branches. For `a && b`, test: true/true, true/false, false/true, false/false.

### Arithmetic (`+` → `-`, `*` → `/`)

Choose non-neutral operands. For `a + b` mutated to `a - b`, use `3` and `4`:
expect `7`, not `-1`. Adding zero cannot distinguish these operators. For
`a * b` mutated to `a / b`, use `6` and `2`: expect `12`, not `3`.
Multiplication by one cannot distinguish these operators either. Add zero and
one cases separately when those values matter to the business contract.

### Boolean return (`return true` → `return false`)

Assert the method's expected return value for the relevant inputs. Upstream
return-value replacements and boolean-expression mutations are different
operators; use the actual reported variant rather than assuming every boolean
mutation flips every result.

### Exception type (`IllegalArgumentException` → `IllegalStateException`)

If the reported mutation changes the exception type, asserting only that
something throws will not distinguish the behaviors. Assert the contract's
specific type around the wrapped business call:

```kotlin
val failure = org.junit.jupiter.api.Assertions.assertThrows(
    IllegalArgumentException::class.java,
) {
    MutFlow.underTest { validator.requireNonnegative(-1) }
}
```

The source contract for this example throws `IllegalArgumentException` for
negative input. Assert stable message or domain fields too when those are part
of the contract, not incidental text. For KMP common tests, use
`kotlin.test.assertFailsWith<IllegalArgumentException>` instead of JUnit.

### Nullable return (non-null result → `null`)

Upstream's nullable-return operator applies to explicit returns in block-bodied
functions returning nullable types. For a source contract like:

```kotlin
fun label(value: String): String? {
    return value
}
```

assert the expected value, not merely that the call did not throw:

```kotlin
assertEquals("ready", MutFlow.underTest { labels.label("ready") })
```

This kills a return replaced with `null`. An expression-bodied function or a
non-null return type is not a reliable example of that operator; confirm the
actual mutation appeared in the report. These are assertion patterns, not a
claim that arbitrary semantic return replacements are generated.

## Verify

Re-run `gradle test` or `gradle mutationResults`. The summary should show the previously surviving mutations as killed (✓). If new mutations survive, repeat the workflow.

## When to stop

- All evaluated mutations are killed and no discovered mutations remain untested
- Remaining survivors are behaviorally equivalent mutations or explicitly accepted gaps in test coverage
- You reach your target mutation score, such as a score above 80% for the Excellent band
