# ADR-002: 5-agent architecture and orchestration model

- **Date**: 2026-08-22
- **Status**: Accepted
- **Decision Maker**: Grilling session (D1, D3, D4 wayfinder tickets)

## Context

Scott-CC's mutation-testing plugin uses 5 domain-specific agents dispatched via Claude Code's `Task(subagent_type="mutation-testing:test-X")` API. We need to port this to OMP's agent/task/skill system while adapting to mutflow's test-only mutation compilation.

Key architectural differences:

- Scott-CC: per-mutant git worktrees, batches of up to five executors, and its own mutation/test evidence
- mutflow: separate mutation compilation, runtime mutation selection, a per-JVM overlap guard, and per-mutation killer verdicts

## Decision

Use 5 separate OMP agent files in `.omp/agents/`, orchestrated via a sequential handshake pattern, with the `/mutation-testing` skill as a thin entry point. Copilot CLI has a corresponding native adapter with the same role boundaries and result contracts.

### Adaptation boundaries

This toolkit adapts Scott-CC's five-role collaboration and broad test-quality
workflow; it does not port the mutation engine or promise feature parity.
Scott-CC's saboteur creates context-aware semantic mutations in separate Git
worktrees. Here, the saboteur identifies Kotlin business logic and configures
mutflow's predefined operators through annotations. Mutflow instruments test
compilation and reports its supported mutation variants.

Scott-CC runs a bounded executor per mutant. This toolkit runs one aggregate
Gradle mutation-results task for the selected test classes. The single
invocation avoids overlapping build and JUnit report outputs; mutflow's
session guard is JVM-local and does not coordinate separate Gradle processes.
Plain JVM budgets use the selected JUnit adapter's `@MutFlowTest` annotation
and include the baseline; KMP budgets use `maxMutationRuns` and exclude it.

The toolkit's score bands, mutation-run budgets, and mock-count heuristic are
its own policy choices. Killer data supports candidate analysis but does not
record every test's result against every mutation. A test without a killer
entry is therefore a candidate for investigation, not a confirmed zombie.

## Rationale

### Why 5 separate agent files (not a single orchestrator)

- **Clean separation of concerns**: Each agent has a single responsibility (targeting, execution, auditing, refactoring, orchestration)
- **Per-agent tool restrictions**: `tools` frontmatter field allows least-privilege — executor can't edit files, saboteur can't spawn subagents, auditor is read-only
- **Adapts Scott-CC's architecture**: Preserves role separation and broad phase ordering while replacing engine-specific execution and mutation generation

### Why sequential phase handoffs

- mutflow's run model requires **baseline before mutation runs**: mutflow discovers mutation points during run 0, then activates one mutation per run 1+. This ordering must be preserved
- Saboteur must complete before executors start (source annotations needed for mutflow to find mutation targets)
- Executors must complete before auditor (results aggregation) and auditor before refactorer (audit findings needed for refactoring)
- The executor phase is one aggregate Gradle invocation, not a per-test-class
  parallel batch. Separate Gradle processes share build and JUnit report paths.

### Why project-level location (`.omp/agents/`)

- Version-controlled with the project — users get agents by cloning the repo
- Follows OMP's discovery precedence (project > user > bundled)

### Why thin skill entry point

- The skill is a wrapper that spawns the test-quality-reviewer agent via `task` tool
- All orchestration logic lives in the orchestrator agent, not the skill
- Skills are prompt-driven, not tool-restricted in OMP

## Agent structure

| Agent | Dispatch Key | Tools | Model | Role |
|-------|-------------|-------|-------|------|
| test-quality-reviewer | `test-quality-reviewer` | task, hub, read, grep, glob, bash | @review | Orchestrator |
| test-saboteur | `test-saboteur` | bash, read, write, edit, grep, glob | @default | Mutation targeting |
| test-executor | `test-executor` | bash, read, grep, glob | @default | Test execution |
| test-auditor | `test-auditor` | read, grep, glob, bash | @default | Results analysis |
| test-refactor-specialist | `test-refactor-specialist` | read, edit, write, grep, glob, bash | @review | Test improvement |

This table records the accepted design. The [mutation-testing agent reference](../agents/mutation-testing-agents.md) reflects the current agent metadata.

## Data flow

1. **Saboteur → Executor**: Source files with `@MutationTarget`, the selected JUnit adapter, and `// mutflow:ignore` annotations
2. **Executor → Auditor**: mutflow stdout + JUnit XML + `mutation-results.json` (custom Gradle task)
3. **Auditor → Refactorer**: JSON audit report (mutation score, zombie candidates, over-mocked tests)
4. **Refactorer → Orchestrator**: Refactored test file content

## Consequences

- **No namespace needed**: OMP uses the `name` field as the dispatch key — `mutation-testing:` prefix is optional (unlike Scott-CC)
- **mutflow adaptation**: The saboteur configures the selected plain JVM adapter (JUnit 6 extension or JUnit 4 runner), or KMP's generated JUnit 6 integration, without git worktrees. One executor runs the selected tests through a single aggregate Gradle task.
- **Zombie analysis**: mutflow reports all tests that kill each mutation (not only the first). The results task builds a killer matrix, which supports candidate analysis but is not a complete per-test-per-mutation outcome matrix.
- **Refactor verification**: When approved changes are applied, the reviewer reruns the aggregate mutation-results task before reporting the changes as validated.
