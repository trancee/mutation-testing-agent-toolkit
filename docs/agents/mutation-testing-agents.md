# Mutation-testing agent reference

This reference lists the OMP and GitHub Copilot CLI agents that implement the mutation-testing pipeline. The client adapters have separate dispatch keys and profile formats.

## OMP agent definitions

| Agent | Definition | Model | Thinking level | Declared tools |
|-------|------------|-------|----------------|----------------|
| `test-quality-reviewer` | [`.omp/agents/test-quality-reviewer.md`](../../.omp/agents/test-quality-reviewer.md) | `@review` | High | `task`, `hub`, `read`, `grep`, `glob`, `bash` |
| `test-saboteur` | [`.omp/agents/test-saboteur.md`](../../.omp/agents/test-saboteur.md) | `@default` | High | `bash`, `read`, `write`, `edit`, `grep`, `glob`, `ast_grep`, `lsp` |
| `test-executor` | [`.omp/agents/test-executor.md`](../../.omp/agents/test-executor.md) | `@default` | Medium | `bash`, `read`, `grep`, `glob` |
| `test-auditor` | [`.omp/agents/test-auditor.md`](../../.omp/agents/test-auditor.md) | `@default` | High | `read`, `grep`, `glob`, `bash` |
| `test-refactor-specialist` | [`.omp/agents/test-refactor-specialist.md`](../../.omp/agents/test-refactor-specialist.md) | `@review` | High | Not specified in frontmatter |

## Agent contracts

| Agent | Input | Output | May change project files |
|-------|-------|--------|--------------------------|
| `test-quality-reviewer` | Project path, target filters, mode, approval setting | Combined mutation-quality report | Through spawned agents |
| `test-saboteur` | Kotlin production and test sources | Mutflow configuration, annotations, and wrapped test calls | Yes |
| `test-executor` | Project path and an annotated test class | Gradle status, stdout, JUnit XML, and mutation-results path when the separate `mutationResults` task has been run | No |
| `test-auditor` | Executor results, optional structured mutation results, and source | Scores, confidence, gaps, survivors, zombie candidates, and redundant groups | No |
| `test-refactor-specialist` | Audit report and original tests | Proposed or approved test refactors, diffs, and rollback instructions | Only when approval permits |

## Spawn permissions

`test-quality-reviewer` declares these agents in its `spawns` list:

- `test-saboteur`
- `test-executor`
- `test-auditor`
- `test-refactor-specialist`

The other four agents do not declare child agents.

## Copilot CLI agent profiles

The Copilot skill at `.github/skills/omp-mutation-test/SKILL.md` delegates to
the reviewer with Copilot's native `agent` tool. The worker profiles are
programmatic-only (`user-invocable: false`) and cannot spawn further agents.

| Role | Profile | Tools | User selectable |
|------|---------|-------|-----------------|
| Reviewer | [`omp-mutation-test-reviewer`](../../.github/agents/omp-mutation-test-reviewer.agent.md) | `read`, `search`, `execute`, `agent` | Yes |
| Saboteur | [`omp-mutation-test-saboteur`](../../.github/agents/omp-mutation-test-saboteur.agent.md) | `read`, `search`, `edit` | No |
| Executor | [`omp-mutation-test-executor`](../../.github/agents/omp-mutation-test-executor.agent.md) | `read`, `search`, `execute` | No |
| Auditor | [`omp-mutation-test-auditor`](../../.github/agents/omp-mutation-test-auditor.agent.md) | `read`, `search` | No |
| Refactor specialist | [`omp-mutation-test-refactor-specialist`](../../.github/agents/omp-mutation-test-refactor-specialist.agent.md) | `read`, `search`, `edit` | No |

The Copilot adapter does not use OMP's `task`, `hub`, or `tasks[]` protocols.
Both clients share the phase order, mutflow result contract, a single aggregate
Gradle execution per run, and the rule that test deletion or consolidation
requires explicit approval.

## Dispatch examples

```text
task with agent: "test-saboteur", task: "Annotate source in <project-path>"
task with agent: "test-executor", task: "Run tests for <TestClass> in <project-path>"
task with agent: "test-auditor", task: "Audit results in <project-path>"
task with agent: "test-refactor-specialist", task: "Improve tests based on audit"
```

For pipeline relationships and ordering, see [About the mutation-testing agent system](../explanation/agent-system.md). For the accepted design, see [ADR-002](../adr/0002-agent-structure-and-orchestration-model.md).
