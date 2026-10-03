# Tutorial: Improve a test with the Copilot mutation-testing agents

We'll use the five-role Copilot workflow to find a missing boundary assertion,
review a proposed test improvement, and verify the result. This lesson uses
Copilot CLI; the equivalent OMP entry point is linked at the end.

## Prerequisites

- Complete [your first mutation test](first-mutation-test.md), keeping its
  `mutation-tutorial` project
- Clone this toolkit and note its absolute path
- A configured GitHub Copilot CLI session with custom-agent support

The project's Gradle behavior is exercised independently by the integration
tests. This walkthrough describes the client contract; a fresh live delegated
Copilot session has not been validated end-to-end by the repository gates.
Agent wording and proposed edits may differ.

## Step 1: Restore a deliberate test gap

In `CalculatorTest`, remove only the `zeroAndOne` method added in the first
tutorial. Keep `positiveAndNegative`.

Run `gradle test --console=plain`. The baseline passes, but mutations survive
and strict verification fails. Save your existing work before installation.

## Step 2: Install the toolkit

From the tutorial project:

```bash
MUTATION_TOOLKIT_DIR="/path/to/mutation-testing-agent-toolkit"
bash "$MUTATION_TOOLKIT_DIR/.omp/bootstrap-mutation-testing.sh" .
```

Replace the path with your clone. The installer adds the shared results module
and both client adapters; it does not edit business logic or tests.

Start a fresh session from this project:

```bash
copilot
```

## Step 3: Run an audit without refactoring

Invoke:

```text
/omp-mutation-test . --targets example.CalculatorTest --mode quick
```

Review requested command/edit permissions before approving them. Targeting may
update mutation configuration; quick mode skips the refactor phase, not all
project edits.

The reviewer should coordinate targeting, one aggregate executor, and an audit.
Look for discovered/evaluated/untested counts, zero execution gaps, surviving
boundary variants, and a score below 100%. For this four-mutation example,
quick's ten-mutation budget is sufficient to evaluate the whole selected scope.
Strict survivor failures do not by themselves make the report incomplete.

If delegation, compilation, or discovery fails, stop and follow
[troubleshooting](../how-to/troubleshoot-mutation-testing.md). Do not accept a
score derived from old JSON.

## Step 4: Review proposed improvements

Invoke:

```text
/omp-mutation-test . --targets example.CalculatorTest --mode standard
```

Without `--auto-approve`, the refactor specialist should propose changes only.
Review the diff: assertions for zero and one should distinguish the boundary
mutants without changing production behavior. Do not delete tests merely
because they have no recorded killer entry.

## Step 5: Apply and verify a focused change

After reviewing the proposal, request the additive change:

```text
/omp-mutation-test . --targets example.CalculatorTest --mode standard --auto-approve
```

This permits additive/assertion-level refactors, not test deletion or
consolidation. The reviewer must rerun the same selected aggregate task after
applying changes and report its actual exit status.

Inspect the changed test and `build/reports/mutation-results.json`. Confirm
schema 2, four evaluated mutations, zero untested mutations/gaps, and all four
killed. Independently reproduce the result:

```bash
gradle mutationResults '-PmutationTest.includes=example.CalculatorTest' --rerun-tasks
```

If the agent did not apply a suitable fix, apply the boundary method from
[the first tutorial](first-mutation-test.md#step-5-add-boundary-assertions)
yourself and rerun. Do not treat a proposal as an applied, verified change.

## Continue

OMP uses `/mutation-test` with the same options and approval boundaries; see
the [command reference](../reference/mutation-test-command.md). For a shared
source-set project, continue with [the KMP JVM tutorial](kmp-jvm-mutation-test.md).
