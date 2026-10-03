# Context: Mutation Testing Agent Toolkit

## Overview

A five-role mutation-testing toolkit for Kotlin (JVM-first) projects, powered by [mutflow](https://github.com/anschnapp/mutflow), with separate OMP and GitHub Copilot CLI adapters.

The toolkit uses mutflow's compile-once engine and predefined operators. Agents select targets, execute tests, calculate quality metrics, and propose test improvements. They do not generate mutation operators.

## Key concepts

### Mutation testing

Injecting small faults (mutations) into source code and running tests to see whether they catch the faults. The mutation score is `killed / (total - gaps)`. A higher score means the tests detected a larger share of evaluated mutations. The score is null when no mutations are evaluable.

### Meta-mutant (mutflow)

mutflow injects all mutation variants into the compiled code, guarded by conditional branches with `MutationRegistry.check()` calls. At runtime, one variant is active per test run. This compile-once approach avoids per-mutation recompilation.

### Zombie test

A test that passes even when the code is mutated. In Scott-CC's model, a zombie test passes for every mutation. In this system, a zombie candidate is a test that never appears in the `testKillerMatrix` for any killed mutation. It executes during mutation runs but never kills a mutation. mutflow records every test that catches each mutation, not only the first.

### Over-mocked test

A test that uses excessive mocking (`mockk()`, `mock()`), potentially masking real logic and reducing mutation sensitivity. Flagged when a test method has >3 mock calls.

## Agent architecture

| Agent | Role |
|-------|------|
| test-quality-reviewer | Orchestrator — coordinates the pipeline via `task` tool dispatch |
| test-saboteur | Mutation targeting — adds `@MutationTarget`, `@MutFlowTest`, `// mutflow:ignore` |
| test-executor | Test execution — runs selected `./gradlew test` classes and captures stdout + JUnit XML; the separate `mutationResults` task generates aggregate JSON |
| test-auditor | Results analysis — parses output, calculates score, identifies zombies |
| test-refactor-specialist | Test improvement — generates refactored test code |

## Client adapters

- **OMP**: `/mutation-test` dispatches through `.omp/skills/mutation-test/` and
  `.omp/agents/` using OMP's `task` and `hub` tools.
- **GitHub Copilot CLI**: `/omp-mutation-test` dispatches through
  `.github/skills/omp-mutation-test/` and the five `omp-mutation-test-*`
  profiles in `.github/agents/` using Copilot's `agent` tool.

The adapters keep the same mutation-testing phases and approval boundaries but
use client-specific dispatch and profile formats. The bootstrap installs both.

## Mutation strategies

| Scott-CC Strategy | mutflow Operator | Coverage |
|---|---|---|
| Boundary conditions | RelationalComparisonOperator + ConstantBoundaryOperator | Full |
| Return values | BooleanReturnOperator + NullableReturnOperator | Full |
| Boolean logic | BooleanInversionOperator + EqualitySwapOperator + BooleanLogicOperator | Full |
| Arithmetic | ArithmeticOperator | Full |
| Exception types | ExceptionTypeSwapOperator | Full |
| Zombie detection | Per-test-per-mutation matrix | Full |

## Data contracts

The `mutationResults` Gradle task outputs `mutation-results.json` including `killedByTests` (all killing tests per mutation) and `testKillerMatrix` (test → mutation source locations). Field names, types, and meanings are a consumer contract; the format and quality bands are documented in the [mutation results reference](docs/reference/mutation-results-format.md).

## Decisions deferred to v2

- Kotlin/JS and Kotlin/Native mutation targets. Kotlin Multiplatform setup currently covers JVM source sets only.

## References

- [mutflow](https://github.com/anschnapp/mutflow)
- [ADR-001: Use mutflow as the mutation engine](docs/adr/0001-use-mutflow-as-mutation-engine.md)
- [ADR-002: Agent structure and orchestration](docs/adr/0002-agent-structure-and-orchestration-model.md)
- [ADR-003: Native GitHub Copilot CLI adapter](docs/adr/0003-copilot-cli-adapter.md)
- `.scratch/omp-mutation-testing/map.md`, the Wayfinder map
