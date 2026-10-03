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
║  Remaining untested:           0                               ║
╚════════════════════════════════════════════════════════════════╝
```

- **Killed** (✓): A test caught the mutation. No action is required for that mutation.
- **Survived** (✗): No test caught the mutation. Add a test that distinguishes the original behavior from the mutant.
- **Timed out** (⏱): Inspect the mutated loop or blocking call. This is a recorded
  mutation outcome, not automatically a test weakness or an infrastructure gap.
  Do not suppress business logic merely to make the build green.

## Step 2: Calculate your mutation score

For JSON, require `schemaVersion: 2`. Upgrade legacy reports using
[manual setup](manual-setup.md#upgrade-an-existing-installation); do not apply
schema 2 arithmetic to unversioned results.

```
mutation score = killed / mutationsEvaluated
```

For schema 2, first check the run's exit status and `executionGaps`. Any gap or
zero evaluated mutations makes the score null. Gap records never subtract
recorded outcomes. Check `untestedMutations` too: a high score on a budgeted run
does not mean every discovered mutation was tested.

The mutation score is a fraction (0.0–1.0). See
[quality bands](../reference/mutation-results-format.md#quality-bands) for the
toolkit thresholds. A nonzero exit with strict survivors can still have a
complete report; a compilation/discovery failure may have no report at all.

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

For plain JVM tests, trap a survivor so it runs first every time:

```kotlin
@MutFlowTest(traps = ["(Calculator.kt:35) > → >="])
class CalculatorTest { ... }
```

Copy the display name from the survivor output. After fixing, remove the trap.

## Step 6: Handle infinite loops

First inspect the reported source location and timeout settings. If a line is
genuinely out of scope or produces an accepted equivalent/noisy mutation,
document the reason and put suppression on the affected line:

```kotlin
fun processLoop(items: List<String>) {
    for (item in items) { // mutflow:ignore accepted out-of-scope loop mutation
        // ...
    }
}
```

For business logic, prefer tests or appropriate mutation timeout budgets over
removing it from scope. Rerun and check both recorded timeouts and execution
gaps. See [upstream configuration](https://github.com/anschnapp/mutflow#configuration)
for loop and per-test budget controls.

## Step 7: Check confidence

For confidence levels based on mutation count, see [Confidence levels in the mutation results reference](../reference/mutation-results-format.md#confidence-levels).

With Low confidence, verify each survivor carefully because the run evaluated fewer than ten mutations.

## Step 8: Treat test-quality findings as candidates

A missing `testKillerMatrix` entry is not proof that a test is unnecessary.
Confirm that the test executed, was in mutation scope, and has an exact
class-qualified identity. Skipped tests and truncated upstream display names
must not become confirmed zombies. Redundant groups are suggestions to
investigate; deleting or consolidating tests requires explicit approval.
