# Mutation results JSON format

This reference describes the structured output produced by the `mutationResults` Gradle task for the test-auditor agent.

## Compatibility

The JSON field names, types, and meanings are consumed by toolkit agents and
are part of the report contract. The current format is **schema 2**.
Reports without `schemaVersion` are legacy schema 1; do not reinterpret them.
Upgrade the results module, Gradle script, both client profiles, and consumers
together. Schema 2 changes total/evaluated/gap accounting and class-qualifies
test identities; namespace migration is described in the
[upgrade procedure](../how-to/manual-setup.md#upgrade-an-existing-installation).

## File location

```
<project>/build/reports/mutation-results.json
```

## JSON schema

| Field | Type | Description |
|-------|------|-------------|
| `schemaVersion` | number | `2`; reports without this field use the legacy contract |
| `generatedAt` | number | Unix timestamp (milliseconds) when JSON was generated; test XML may have been reused by Gradle |
| `mutationScore` | number/null | `killed / mutationsEvaluated` (0.0–1.0). `null` for zero evaluations or any execution gap. |
| `qualityBand` | string | Excellent / Good / Fair / Poor (see quality bands table) |
| `confidence` | string | Low / Medium / High (based on evaluated outcomes, not discovered totals) |
| `totalMutations` | number | Discovered mutations summed across selected test-class sessions, not globally deduplicated |
| `killed` | number | Mutations caught by at least one test |
| `survived` | number | Mutations not caught by any test |
| `timedOut` | number | Mutations exceeding loop or wall-clock budgets |
| `gaps` | number | Infrastructure-gap records; never subtracted from evaluated mutation counts |
| `mutationsEvaluated` | number | Recorded outcomes: `killed + survived + timedOut` |
| `untestedMutations` | number | `totalMutations - mutationsEvaluated`; budget limits are not execution gaps |
| `confidenceIntervalLow` | number/null | Wilson score 95% CI lower bound (z=1.96). `null` when mutationScore is null. |
| `confidenceIntervalHigh` | number/null | Wilson score 95% CI upper bound (z=1.96). `null` when mutationScore is null. |
| `testMethods` | array[string] | `testClass::displayName` identities from XML, excluding synthetic `executionError`; may include skipped tests |
| `testKillerMatrix` | object | Map: class-qualified identity → mutation `sourceLocation` strings it killed. Records killers, not every test outcome. Missing entries are not proof a test is unnecessary. |
| `mutations` | array[object] | Per-mutation details |
| `executionGaps` | array[object] | Execution gap entries (see executionGaps[].type) |
| `redundantGroups` | array[object] | Redundant test group entries (see redundantGroups[].tests) |

### mutations[].sourceLocation

File and line of the mutated code, e.g. `Calculator.kt:8`.

### mutations[].testClass

JUnit suite name associated with this mutation, or `null` for manually assembled
results. Sessions from different classes are not merged by display name.

### mutations[].originalOperator

The original operator or value before mutation, e.g. `>`, `0`, `100`, `&&`.

### mutations[].variantOperator

The mutated operator or value, e.g. `>=`, `1`, `101`, `||`.

### mutations[].result

One of `Killed`, `Survived`, `TimedOut`.

### mutations[].killedByTest

Class-qualified name of the first test that caught the mutation. `null` if the
mutation survived or timed out. The field name is retained from schema 1.

### mutations[].killedByTests

Array of class-qualified killer names. Empty for survivors and timeouts.
Upstream records every killer but truncates long display names in its console
summary; unresolved identities must not be treated as exact zombie/redundancy
evidence.

### executionGaps[].type

One of `NO_OUTPUT`, `PARTIAL_RUN`, `TEST_FAILURE`, `COMPILATION_FAILURE`, `BACKSTOP_TIMEOUT`,
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

The task emits `NO_OUTPUT` for missing reports or missing mutation output,
`PARTIAL_RUN` when actual upstream tested counters disagree with detail records
or discovered/tested/remaining counters are missing or inconsistent,
and `TEST_FAILURE` for ordinary/baseline XML failures. Strict survivors and
mutation timeouts remain outcomes, not gaps. All gaps invalidate aggregate
scores and Wilson intervals.

If a discovered counter is smaller than the recorded outcome count, the report
retains those outcomes and uses their count as the minimum total, with a
`PARTIAL_RUN` gap. Totals in a gapped report are incomplete evidence, not a
validated discovery count. Strict survivor or timeout exceptions without
captured mutation output also produce gaps.

The executor reports compilation/process failures separately when they prevent
the report task from running. A pre-existing JSON file is not current evidence
after compilation or discovery failure. The report task writes JSON before
restoring nonzero status for JUnit failures; a strict survivor can therefore
produce a complete current report while Gradle fails.

### redundantGroups[].tests

Array of class-qualified test identities that share an identical failure signature.

### redundantGroups[].count

Number of tests in the group.

### redundantGroups[].failureSignature

Composite mutation keys (`sourceLocation:originalOperator->variantOperator`)
shared across the group.

**Abbreviated example** from the `Calculator` sample. Array fields contain representative entries from the full report.

```json
{
  "schemaVersion": 2,
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
  "untestedMutations": 0,
  "confidenceIntervalLow": 0.8928172849426366,
  "confidenceIntervalHigh": 1.0,
  "testMethods": ["example.CalculatorTest::testValidateInput()"],
  "testKillerMatrix": {
    "example.CalculatorTest::testValidateInput()": ["Calculator.kt:51"]
  },
  "mutations": [
    {
      "sourceLocation": "Calculator.kt:51",
      "originalOperator": "IllegalArgumentException",
      "variantOperator": "IllegalStateException",
      "result": "Killed",
      "killedByTest": "example.CalculatorTest::testValidateInput()",
      "killedByTests": ["example.CalculatorTest::testValidateInput()"],
      "testClass": "example.CalculatorTest"
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

| Level | Evaluated mutation count |
|-------|---------------|
| Low | <10 |
| Medium | 10–50 |
| High | >50 |
