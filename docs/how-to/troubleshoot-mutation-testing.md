# How to troubleshoot mutation-testing runs

Use this guide when setup, execution, or analysis fails. Preserve the command,
effective `MUTFLOW_*` overrides, Gradle exit status, console output, and current
JUnit XML before deciding whether the problem is a mutation outcome or an
execution gap.

## Establish whether the report is current

Run one aggregate `mutationResults` invocation for the intended test classes.
Use `--rerun-tasks` when changing environment-based budgets or verification:

```bash
gradle mutationResults '-PmutationTest.includes=example.CalculatorTest' --rerun-tasks --console=plain
```

Use the project's wrapper and qualified module task when appropriate. Check
`build/reports/mutation-results.json` for schema 2, then examine `executionGaps`,
evaluated/untested counts, and matching JUnit XML. A new `generatedAt` means JSON
was generated, not necessarily that tests executed again.

Compilation, configuration, or discovery failure can prevent JSON generation.
Do not reuse a report from an earlier invocation, even when it still exists
after an early configuration failure.

## Diagnose by symptom

| Symptom | Check | Action |
|---------|-------|--------|
| Bootstrap rejects compiler or plugin layout | Explicit Kotlin pin, module type, catalog aliases | Use the compatible pair and [manual setup](manual-setup.md); do not bypass the preflight |
| Plugin cannot resolve | Existing `pluginManagement.repositories` | Include Maven Central; bootstrap leaves an existing plugin-management block unchanged |
| Bootstrap rejects `buildSrc` or differing Copilot files | User-owned conventions or installed customizations | Follow [upgrade/merge instructions](manual-setup.md#upgrade-an-existing-installation), preserving unrelated files |
| No tests match the filter | Fully qualified class name and selected task | Correct `mutationTest.includes`; remove method-only filtering for complete sessions |
| KMP runs ordinary `jvmTest` only | Applied results script, mutflow enabled, JVM target | Invoke `mutationResults`; it must select `mutflow<Target>Test` |
| Common tests fail to compile | JUnit imports or `@MutFlowTest` in common sources | Use `kotlin.test`; follow [KMP setup](manual-setup.md#configure-kmp-jvm-projects) |
| Strict survivors fail Gradle but JSON has no gaps | `survived`, verification mode, current XML | Strengthen tests; for a deliberate threshold policy use the [CI guide](run-in-github-actions.md) |
| Baseline/ordinary tests fail | `TEST_FAILURE` and XML failure/error entries | Fix the original failing test before interpreting mutation quality |
| `NO_OUTPUT` or `PARTIAL_RUN` | Missing summary, counters, or truncated output | Inspect XML and console; do not calculate a complete score |
| Score is null | Zero evaluations or any gap | Resolve gaps and confirm mutation execution was not disabled |
| High score but untested mutations remain | Annotation/DSL budget and `MUTFLOW_MAX_RUNS` | Run deep/full scope or explicitly report budget-limited evidence |
| A second active session fails | JUnit parallelism or concurrent runs sharing output | Avoid overlapping sessions within one JVM and competing Gradle processes |
| Configuration-cache serialization fails | `prepareMutationResults` script references | Run with `--no-configuration-cache`; current adapter does not support it |
| Client skill or role is unavailable | Installed skill/profile paths and active workspace | Start a fresh session; do not replace missing native delegation with another client's tools |

## Investigate timeouts without hiding them

`TimedOut` is a recorded mutation outcome. A loop mutation or blocked call may
be intentional fault detection; an abandoned process or missing report is a
different problem. Inspect the affected source, actual timeout exception, and
loop/per-test budget configuration.

Do not automatically raise budgets, weaken assertions, or suppress business
logic. If suppression is justified by accepted scope or an equivalent/noisy
mutation, record the reason on the affected line and rerun. See
[handling infinite loops](interpret-results.md#step-6-handle-infinite-loops).

## Investigate suspicious test-quality findings

Confirm the test executed in the selected mutation scope before calling it a
zombie candidate. `testMethods` can include skipped tests, and upstream may
truncate long killer display names. Missing or ambiguous killer identities
are not permission to delete tests.

Review redundant groups against distinct business assertions. Deleting or
consolidating tests requires explicit approval, and any applied refactor must
be followed by the same selected aggregate validation.

## Report unresolved failures

Include the project/module type, toolchain/plugin pins, task and filters,
effective overrides, exit status, and the relevant error/report excerpts.
Remove credentials and unrelated private data. State missing evidence and
unsupported targets explicitly rather than supplying a plausible default score.
Use [repository checks](run-checks.md) to distinguish a toolkit regression from
a target-project setup failure.
