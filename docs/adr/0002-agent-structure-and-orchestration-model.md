# ADR-002: 5-agent architecture and orchestration model

- **Date**: 2026-08-22
- **Status**: Accepted
- **Decision Maker**: Grilling session (D1, D3, D4 wayfinder tickets)

## Context

Scott-CC's mutation-testing plugin uses 5 domain-specific agents dispatched via Claude Code's `Task(subagent_type="mutation-testing:test-X")` API. We need to port this to OMP's agent/task/skill system while adapting to mutflow's test-only mutation compilation.

Key architectural differences:

- Scott-CC: per-mutant git worktrees, 15 parallel executors, per-test-per-mutation matrix
- mutflow: mutation instrumentation during test compilation, runtime mutation selection, a per-JVM synchronized lock, and aggregate verdicts that track all killers

## Decision

Use 5 separate OMP agent files in `.omp/agents/`, orchestrated via a sequential handshake pattern, with the `/mutation-test` skill as a thin entry point.

## Rationale

### Why 5 separate agent files (not a single orchestrator)

- **Clean separation of concerns**: Each agent has a single responsibility (targeting, execution, auditing, refactoring, orchestration)
- **Per-agent tool restrictions**: `tools` frontmatter field allows least-privilege — executor can't edit files, saboteur can't spawn subagents, auditor is read-only
- **Matches Scott-CC's architecture**: Direct port preserves the multi-agent orchestration that makes this system distinctive

### Why sequential handshake (not parallel batch)

- mutflow's run model requires **baseline before mutation runs**: mutflow discovers mutation points during run 0, then activates one mutation per run 1+. This ordering must be preserved
- Saboteur must complete before executors start (source annotations needed for mutflow to find mutation targets)
- Executors must complete before auditor (results aggregation) and auditor before refactorer (audit findings needed for refactoring)
- Parallel execution is used WITHIN phases (multiple executors in one `tasks[]` batch)

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

1. **Saboteur → Executor**: Source files with `@MutationTarget`, `@MutFlowTest`, `// mutflow:ignore` annotations
2. **Executor → Auditor**: mutflow stdout + JUnit XML + `mutation-results.json` (custom Gradle task)
3. **Auditor → Refactorer**: JSON audit report (mutation score, zombie candidates, over-mocked tests)
4. **Refactorer → Orchestrator**: Refactored test file content

## Consequences

- **No namespace needed**: OMP uses the `name` field as the dispatch key — `mutation-testing:` prefix is optional (unlike Scott-CC)
- **mutflow adaptation**: The saboteur configures `@MutFlowTest` without git worktrees. Each executor runs `./gradlew test`, and the JUnit extension handles the baseline and mutation runs for its test class.
- **Zombie detection**: mutflow tracks ALL tests that kill each mutation (not just the first). The `mutation-results.gradle.kts` task builds a `testKillerMatrix` and the test-auditor uses it for precise zombie candidate identification.
