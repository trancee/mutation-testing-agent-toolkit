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
| `test-executor` | Project path and selected JVM test-class patterns (plain JVM or KMP) | One aggregate Gradle status, current JUnit XML, schema 2 JSON, and Markdown summary when generation succeeds; GitHub Actions job summary when available | No |
| `test-auditor` | Executor evidence, schema 2 results when available, and source | Evaluated/discovered/untested totals, scores, confidence, gaps, survivors, zombie candidates, and redundant groups | No |
| `test-refactor-specialist` | Audit report and original tests | Proposed or approved test refactors, diffs, and rollback instructions | Only when approval permits |

## Spawn permissions

`test-quality-reviewer` declares these agents in its `spawns` list:

- `test-saboteur`
- `test-executor`
- `test-auditor`
- `test-refactor-specialist`

The other four agents do not declare child agents.

## Copilot CLI agent profiles

The Copilot skill at `.github/skills/mutation-testing/SKILL.md` delegates to
the reviewer with Copilot's native `agent` tool. The worker profiles are
programmatic-only (`user-invocable: false`) and cannot spawn further agents.

| Role | Profile | Tools | User selectable |
|------|---------|-------|-----------------|
| Reviewer | [`mutation-testing-reviewer`](../../.github/agents/mutation-testing-reviewer.agent.md) | `read`, `search`, `execute`, `agent` | Yes |
| Saboteur | [`mutation-testing-saboteur`](../../.github/agents/mutation-testing-saboteur.agent.md) | `read`, `search`, `edit` | No |
| Executor | [`mutation-testing-executor`](../../.github/agents/mutation-testing-executor.agent.md) | `read`, `search`, `execute` | No |
| Auditor | [`mutation-testing-auditor`](../../.github/agents/mutation-testing-auditor.agent.md) | `read`, `search` | No |
| Refactor specialist | [`mutation-testing-refactor-specialist`](../../.github/agents/mutation-testing-refactor-specialist.agent.md) | `read`, `search`, `edit` | No |

The Copilot adapter does not use OMP's `task`, `hub`, or `tasks[]` protocols.
Both clients share the phase order, mutflow result contract, a single aggregate
Gradle execution per run, and the rule that test deletion or consolidation
requires explicit approval.

Profile/schema consistency checks verify these static contracts; they do not
prove fresh end-to-end client delegation. The real integration gate exercises
Gradle and mutflow independently of either agent runtime. See
[repository checks](../how-to/run-checks.md) for the validation boundaries.

## Dispatch examples

```text
task with agent: "test-saboteur", task: "Annotate source in <project-path>"
task with agent: "test-executor", task: "Run one aggregate mutationResults for <class-patterns> in <project-path>"
task with agent: "test-auditor", task: "Audit results in <project-path>"
task with agent: "test-refactor-specialist", task: "Improve tests based on audit"
```

For pipeline relationships and ordering, see [About the mutation-testing agent system](../explanation/agent-system.md). For the accepted design, see [ADR-002](../adr/0002-agent-structure-and-orchestration-model.md).
