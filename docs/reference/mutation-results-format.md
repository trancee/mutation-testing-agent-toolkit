# Mutation results JSON format

This reference describes the structured output produced by the `mutationResults` Gradle task for the test-auditor agent.

## Compatibility

The JSON field names, types, and meanings are consumed by toolkit agents and
are part of the report contract. Additive optional fields are preferred. Do
not remove or repurpose fields or enum values without updating every consumer,
example, and this reference in the same change. Introduce schema versioning
before making an incompatible format change.

## File location

```
<project>/build/reports/mutation-results.json
```

## JSON schema

| Field | Type | Description |
|-------|------|-------------|
| `generatedAt` | number | Unix timestamp (milliseconds) when the results were generated |
| `mutationScore` | number | Fraction of mutations killed (0.0–1.0). `null` when no mutations are evaluable (denominator is 0). |
| `qualityBand` | string | Excellent / Good / Fair / Poor (see quality bands table) |
| `confidence` | string | Low / Medium / High (based on mutation count) |
| `totalMutations` | number | Total mutations discovered |
| `killed` | number | Mutations caught by at least one test |
| `survived` | number | Mutations not caught by any test |
| `timedOut` | number | Mutations that caused infinite loops |
| `gaps` | number | Number of detected execution-gap records excluded from the score denominator |
| `mutationsEvaluated` | number | `totalMutations - gaps`, clamped to 0 |
| `confidenceIntervalLow` | number | Wilson score 95% CI lower bound (z=1.96). `null` when mutationScore is null. |
| `confidenceIntervalHigh` | number | Wilson score 95% CI upper bound (z=1.96). `null` when mutationScore is null. |
| `testMethods` | array[string] | Test method names found in JUnit XML; may include skipped tests |
| `testKillerMatrix` | object | Map: test displayName → array of mutation `sourceLocation` strings it killed. Records killers, not every test's result for every mutation; a missing entry is not proof that a test is unnecessary. |
| `mutations` | array[object] | Per-mutation details |
| `executionGaps` | array[object] | Execution gap entries (see executionGaps[].type) |
| `redundantGroups` | array[object] | Redundant test group entries (see redundantGroups[].tests) |

### mutations[].sourceLocation

File and line of the mutated code, e.g. `Calculator.kt:8`.

### mutations[].originalOperator

The original operator or value before mutation, e.g. `>`, `0`, `100`, `&&`.

### mutations[].variantOperator

The mutated operator or value, e.g. `>=`, `1`, `101`, `||`.

### mutations[].result

One of `Killed`, `Survived`, `TimedOut`.

### mutations[].killedByTest

Name of the first test that caught the mutation (JUnit display name). `null` if the mutation survived. Kept for backward compatibility.

### mutations[].killedByTests

Array of all test display names that caught the mutation. Empty array `[]` if the mutation survived or timed out. mutflow records every test that fails during a mutation run, not only the first.

### executionGaps[].type

One of `NO_OUTPUT`, `PARTIAL_RUN`, `COMPILATION_FAILURE`, `BACKSTOP_TIMEOUT`,
or `IR_TRANSFORMATION_ERROR`. The current task/parser-produced types are
described below.

### executionGaps[].reason

Human-readable description of why the gap occurred.

### executionGaps[].testClass

Optional test class associated with the gap.

### executionGaps[].affectedSourceLocation

Optional source location associated with the gap.

### executionGaps[].gradleExitCode

Gradle process exit code when the gap occurred, if available.

### execution gap types

The `mutationResults` Gradle task currently emits `NO_OUTPUT`, `PARTIAL_RUN`,
and `COMPILATION_FAILURE`. A missing JUnit XML report is classified as
`COMPILATION_FAILURE`; its reason may mention an IR transformation error.
`BACKSTOP_TIMEOUT` and `IR_TRANSFORMATION_ERROR` can be supplied by an
orchestration executor, but are not emitted as separate types by the current
Gradle task. Gaps are detected at per-test-class granularity because mutations
for a test class share an instrumented test compilation.

### redundantGroups[].tests

Array of test method display names that share an identical failure signature.

### redundantGroups[].count

Number of mutations that all fail under the same set of tests.

### redundantGroups[].failureSignature

List of mutation source location strings shared across the group.

**Abbreviated example** from the `Calculator` sample. Array fields contain representative entries from the full report.

```json
{
  "generatedAt": 1788029817104,
  "mutationScore": 1.0,
  "qualityBand": "Excellent",
  "confidence": "Medium",
  "totalMutations": 32,
  "killed": 32,
  "survived": 0,
  "timedOut": 0,
  "gaps": 0,
  "mutationsEvaluated": 32,
  "confidenceIntervalLow": 0.8928172849426366,
  "confidenceIntervalHigh": 1.0,
  "testMethods": ["testValidateInput()"],
  "testKillerMatrix": {
    "testValidateInput()": ["Calculator.kt:51"]
  },
  "mutations": [
    {
      "sourceLocation": "Calculator.kt:51",
      "originalOperator": "IllegalArgumentException",
      "variantOperator": "IllegalStateException",
      "result": "Killed",
      "killedByTest": "testValidateInput()",
      "killedByTests": ["testValidateInput()"]
    }
  ],
  "executionGaps": [],
  "redundantGroups": []
}
```

## Quality bands

These thresholds are toolkit policy and are not inherited from Scott-CC.

| Band | Score |
|------|-------|
| Excellent | >80% |
| Good | >60% and ≤80% |
| Fair | >30% and ≤60% |
| Poor | ≤30% |

## Confidence levels

| Level | Mutation count |
|-------|---------------|
| Low | <10 |
| Medium | 10–50 |
| High | >50 |
