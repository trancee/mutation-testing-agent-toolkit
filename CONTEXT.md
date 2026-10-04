# Context: Mutation Testing Agent Toolkit

## Overview

This five-role toolkit runs mutflow mutation tests in Kotlin/JVM projects.
It has separate OMP and GitHub Copilot CLI adapters.

mutflow compiles mutation variants for tests and uses predefined operators.
Agents select targets, run tests, analyze results, and propose test
improvements. They do not create mutation operators.

## Key concepts

### Mutation testing

Mutation testing injects small faults into code during test compilation and
runs tests against them. A test kills a mutation when it fails under that
variant. The schema 2 score is `killed / mutationsEvaluated`. A higher score
means tests detected a larger share of recorded outcomes. The score is null
when no mutations were evaluated or an execution gap exists.

### Meta-mutant (mutflow)

mutflow keeps production compilation clean. During test compilation, it adds
guarded mutation variants to the test artifact. Each mutation run activates
one variant, so mutflow does not compile once per mutation.

### Zombie test

A zombie candidate is a test that appears in no recorded mutation killer set.
Count a test as a candidate only when the run evidence confirms it executed in
the selected mutation scope. The report lists tests that kill each mutation,
not every test outcome for every mutation. A missing killer entry alone does
not prove that a test is unnecessary. Skipped and out-of-scope tests are not
zombie candidates.

### Over-mocked test

A test that uses many mocks may hide real logic and reduce mutation sensitivity.
More than three mock calls triggers review in this toolkit. That count alone
does not prove that a test is weak.

## Agent architecture

| Agent | Responsibility |
|-------|----------------|
| `test-quality-reviewer` | Coordinates the selected client's workflow. |
| `test-saboteur` | Selects production and test classes, adds `@MutationTarget`, configures the module's JUnit adapter and mode budget, and applies applicable `// mutflow:ignore` annotations. |
| `test-executor` | Runs one aggregate `mutationResults` Gradle invocation and captures stdout, JUnit XML, and JSON. |
| `test-auditor` | Analyzes the aggregate output, calculates the score, and identifies evidence-qualified zombie candidates. |
| `test-refactor-specialist` | Proposes or applies approved test changes. |

## Client adapters

- **OMP:** `/mutation-testing` uses `.omp/skills/mutation-testing/` and
  `.omp/agents/`. It dispatches through OMP's `task` and `hub` tools.
- **GitHub Copilot CLI:** `/mutation-testing` uses
  `.github/skills/mutation-testing/` and five profiles in `.github/agents/`.
  It dispatches through Copilot's `agent` tool.

Both adapters use the same mutation-testing phases and approval rules. Their
dispatch tools and profile formats differ. The bootstrap command installs both.

## Mutation strategies

| Scott-CC strategy category | Representative mutflow operators | Relationship |
|---|---|---|
| Boundary conditions | RelationalComparisonOperator + ConstantBoundaryOperator | Category mapping. Mutflow generates only its supported cases. |
| Return values | BooleanReturnOperator + NullableReturnOperator | Limited to supported return forms. |
| Boolean logic | BooleanInversionOperator + EqualitySwapOperator + BooleanLogicOperator | Category mapping, not semantic mutation parity. |
| Arithmetic | ArithmeticOperator | Category mapping. Mutflow generates only its supported cases. |
| Exception types | ExceptionTypeSwapOperator | Category mapping. Mutflow generates only its supported cases. |
| Zombie analysis | Per-mutation killing-test data | Candidate analysis, not a complete test-outcome matrix. |

These rows map strategy categories. They do not claim feature parity.
Scott-CC generates context-aware semantic mutations in isolated worktrees.
This toolkit uses mutflow's predefined Kotlin operators and does not create
arbitrary return-value replacements.

The toolkit sets its own mutation-score bands and mock-count heuristic.
Scott-CC does not define those policies.

## Data contracts

The `mutationResults` Gradle task writes `mutation-results.json`.
`killedByTests` lists the recorded tests that killed each mutation.
`testKillerMatrix` maps each test to mutation source locations it killed.
These fields describe killer relationships, not every test outcome for every
mutation. Consumers rely on the field names, types, and meanings. See the
[mutation results reference](docs/reference/mutation-results-format.md).

## Current support limits

The toolkit supports plain JVM with JUnit 4 or JUnit 6, and KMP JVM through
MutFlow's generated JUnit 6 integration. Native, Android, and JS execution
adapters are outside the current scope. The repository has set no release or
schedule for them.

## Results module ownership

The shared results module uses `ch.trancee.mutation`, not a client-specific
namespace. Schema 2 reports discovered, evaluated, and untested counts.
It qualifies tests as `testClass::displayName` and sets the score to null when
execution gaps exist. Existing `io.omp.mutation` installations need a
coordinated source and consumer migration.

## References

- [mutflow](https://github.com/anschnapp/mutflow)
- [ADR-001: Use mutflow as the mutation engine](docs/adr/0001-use-mutflow-as-mutation-engine.md)
- [ADR-002: Agent structure and orchestration](docs/adr/0002-agent-structure-and-orchestration-model.md)
- [ADR-003: Native GitHub Copilot CLI adapter](docs/adr/0003-copilot-cli-adapter.md)
- `.scratch/omp-mutation-testing/map.md`, the Wayfinder map
