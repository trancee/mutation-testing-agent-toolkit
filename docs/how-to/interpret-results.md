# How to interpret and act on mutation testing results

Use this guide when you have a mutation testing run and want to act on the results.

## Prerequisites

- You've run `gradle test` (or `gradle mutationResults`) and mutflow generated output
- You have the mutation summary (console) or `mutation-results.json` (Gradle task)

## Step 1: Read the mutation summary

mutflow prints a summary after all runs:

```
╔════════════════════════════════════════════════════════════════╗
║                    MUTATION TESTING SUMMARY                    ║
╠════════════════════════════════════════════════════════════════╣
║  Total mutations discovered:   6                               ║
║  Tested this run:              6                               ║
║  ├─ Killed:                    4  ✓                            ║
║  ├─ Survived:                  1  ✗                            ║
║  └─ Timed out:                 1  ⏱                            ║
╚════════════════════════════════════════════════════════════════╝
```

- **Killed** (✓): A test caught the mutation. No action is required for that mutation.
- **Survived** (✗): No test caught the mutation. Add a test that distinguishes the original behavior from the mutant.
- **Timed out** (⏱): The mutation likely caused an infinite loop. Add `// mutflow:ignore` to the affected line or add a timeout guard.

## Step 2: Calculate your mutation score

```
mutation score = killed / mutationsEvaluated
```

For schema 2, first check the run's exit status and `executionGaps`. Any gap or
zero evaluated mutations makes the score null. Gap records never subtract
recorded outcomes. Check `untestedMutations` too: a high score on a budgeted run
does not mean every discovered mutation was tested.

The mutation score is a fraction (0.0–1.0). For the quality bands (Excellent / Good / Fair / Poor) and the recommended action at each level, see [Quality bands in the mutation results reference](../reference/mutation-results-format.md#quality-bands).

## Step 3: Locate surviving mutations

Each survived mutation shows the source location and the operator change:

```
✗ (Calculator.kt:35) > → >=
    SURVIVED - no test caught this mutation!
```

- File: `Calculator.kt`, line 35
- Operator: `>` was mutated to `>=`

## Step 4: Choose the next action

For each surviving mutation, identify an input where the original and mutated operators produce different results. Add an assertion for that input.

Follow [How to fix surviving mutations](fix-surviving-mutations.md) for operator-specific boundary patterns and mutation traps.

## Step 5: Trap a mutation you're fixing

If you need to fix tests over multiple sessions, trap a survivor so it runs first every time:

```kotlin
@MutFlowTest(traps = ["(Calculator.kt:35) > → >="])
class CalculatorTest { ... }
```

Copy the display name from the survivor output. After fixing, remove the trap.

## Step 6: Handle infinite loops

If a mutation causes a timeout (⏱), mutflow suggests adding `// mutflow:ignore`:

```kotlin
fun processLoop(items: List<String>) {
    // mutflow:ignore  // loop condition mutation causes infinite loop
    for (item in items) {
        // ...
    }
}
```

## Step 7: Check confidence

For confidence levels based on mutation count, see [Confidence levels in the mutation results reference](../reference/mutation-results-format.md#confidence-levels).

With Low confidence, verify each survivor carefully because the run evaluated fewer than ten mutations.
