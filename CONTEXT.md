# Context: Mutation Testing Agent Toolkit

## Overview

A five-role mutation-testing toolkit for Kotlin (JVM-first) projects, powered by [mutflow](https://github.com/anschnapp/mutflow), with separate OMP and GitHub Copilot CLI adapters.

The toolkit uses mutflow's test-only mutation compilation and predefined operators. Agents select targets, execute tests, calculate quality metrics, and propose test improvements. They do not generate mutation operators.

## Key concepts

### Mutation testing

Injecting small faults (mutations) into source code and running tests to see whether they catch the faults. The schema 2 score is `killed / mutationsEvaluated`. A higher score means tests detected a larger share of recorded mutation outcomes. The score is null for zero evaluations or any infrastructure gap.

### Meta-mutant (mutflow)

mutflow keeps production compilation clean and injects mutation variants during test compilation. The test artifact contains guarded variants; runtime activates one variant per mutation run, avoiding a separate compile for each mutation.

### Zombie test

A test that passes even when the code is mutated. In this system, a test is only a zombie candidate when the run evidence confirms it executed, it was in the selected mutation scope, and it never appears in any mutation's killer set. A missing killer entry alone is not proof: skipped or out-of-scope tests must not be classified as zombies. mutflow records all tests that kill each mutation, not every test's outcome for every mutation, so candidates are not confirmed unnecessary tests.

### Over-mocked test

A test that uses excessive mocking (`mockk()`, `mock()`), potentially masking real logic and reducing mutation sensitivity. More than three mock calls is a toolkit-specific review heuristic, not evidence by itself that a test is weak.

## Agent architecture

| Agent | Role |
|-------|------|
| test-quality-reviewer | Orchestrator — coordinates the pipeline via `task` tool dispatch |
| test-saboteur | Mutation targeting — selects source/test classes, adds `@MutationTarget`, configures the module's JUnit adapter and mode budget, and applies applicable `// mutflow:ignore` annotations |
| test-executor | Test execution — runs one aggregate `mutationResults` Gradle invocation for the selected classes and captures stdout, JUnit XML, and JSON |
| test-auditor | Results analysis — parses aggregate output, calculates score, and identifies evidence-qualified zombie candidates |
| test-refactor-specialist | Test improvement — generates refactored test code |

## Client adapters

- **OMP**: `/mutation-testing` dispatches through `.omp/skills/mutation-testing/` and
  `.omp/agents/` using OMP's `task` and `hub` tools.
- **GitHub Copilot CLI**: `/mutation-testing` dispatches through
  `.github/skills/mutation-testing/` and the five `mutation-testing-*`
  profiles in `.github/agents/` using Copilot's `agent` tool.

The adapters keep the same mutation-testing phases and approval boundaries but
use client-specific dispatch and profile formats. The bootstrap installs both.

## Mutation strategies

| Scott-CC strategy category | Representative mutflow operators | Relationship |
|---|---|---|
| Boundary conditions | RelationalComparisonOperator + ConstantBoundaryOperator | Category mapping; operator-generated cases only |
| Return values | BooleanReturnOperator + NullableReturnOperator | Limited to supported return forms |
| Boolean logic | BooleanInversionOperator + EqualitySwapOperator + BooleanLogicOperator | Category mapping; not semantic mutation parity |
| Arithmetic | ArithmeticOperator | Category mapping; operator-generated cases only |
| Exception types | ExceptionTypeSwapOperator | Category mapping; operator-generated cases only |
| Zombie analysis | Per-mutation killing-test data | Candidate analysis; not complete test-outcome matrix |

These are broad strategy mappings, not feature-equivalence claims. Scott-CC
generates context-aware semantic mutations in isolated worktrees; this toolkit
uses mutflow's predefined Kotlin/JVM operators and does not create arbitrary
return-value replacements.

Mutation score quality bands and the mock-count heuristic are toolkit policy;
they are not inherited Scott-CC thresholds.

## Data contracts

The `mutationResults` Gradle task outputs `mutation-results.json` including `killedByTests` (all recorded killing tests per mutation) and `testKillerMatrix` (test → mutation source locations it killed). These are killer relationships, not a complete test-by-mutation outcome matrix. Field names, types, and meanings are a consumer contract; the format and quality bands are documented in the [mutation results reference](docs/reference/mutation-results-format.md).

## Decisions deferred to v2

- Native, Android, and JS toolkit adapters. The toolkit validates plain
  JVM/JUnit 4, plain JVM/JUnit 6, and KMP JVM through MutFlow's generated
  JUnit 6 integration.

## Results module ownership

The shared results module uses `ch.trancee.mutation`, not a client-specific
namespace. Schema 2 distinguishes discovered/evaluated/untested counts,
qualifies tests as `testClass::displayName`, and makes scores null when
infrastructure gaps exist. Legacy `io.omp.mutation` installations require a
coordinated source and consumer migration.

## References

- [mutflow](https://github.com/anschnapp/mutflow)
- [ADR-001: Use mutflow as the mutation engine](docs/adr/0001-use-mutflow-as-mutation-engine.md)
- [ADR-002: Agent structure and orchestration](docs/adr/0002-agent-structure-and-orchestration-model.md)
- [ADR-003: Native GitHub Copilot CLI adapter](docs/adr/0003-copilot-cli-adapter.md)
- `.scratch/omp-mutation-testing/map.md`, the Wayfinder map
