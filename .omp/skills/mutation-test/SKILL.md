---
name: mutation-test
description: Run mutflow-powered mutation testing on a Kotlin project via the toolkit's 5-agent OMP adapter (test-quality-reviewer orchestrator, test-saboteur, test-executor, test-auditor, test-refactor-specialist). JVM-first.
---

## Mutation Testing

Runs a mutation-testing analysis on a Kotlin (JVM-first) project using mutflow as the engine and the toolkit's OMP adapter for orchestration.

### Usage

- `project path`: Path to the Kotlin project root (default: current directory)
- `--targets`: Optional comma-separated Gradle test class patterns (default: all `@MutFlowTest` classes)
- `--kmp`: (setup only) Configure the toolkit's KMP JVM integration. Native and JUnit 4 adapters are not validated here, although upstream supports them.
- `--auto-approve`: Permits additive or assertion-level test changes to be applied. Deleting or consolidating tests always requires explicit approval.
- `--mode quick`: At most 10 mutation runs per selected test class (`maxRuns=11`, including the baseline). Skip refactoring — only audit and report.
- `--mode standard`: (default) At most 30 mutation runs per selected test class (`maxRuns=31`, including the baseline). Run the full pipeline and provide refactoring suggestions.
- `--mode deep`: Run all available mutations per selected test class. Include full redundant-group details and per-mutation killer data in the report.

```
/mutation-test [project path] [--targets <patterns>] [--auto-approve] [--mode quick|standard|deep]
/mutation-test setup [project path] [--kmp]
```

### Setup subcommand

`/mutation-test setup [project path] [--kmp]` bootstraps the entire system into a new project:

1. **`.omp/` files copied**: agents, skills, `mutation-results.gradle.kts`, `mutation-results-src/` copied to `project-path/.omp/`
2. **`settings.gradle.kts`**: `pluginManagement` block added with `mavenCentral()` + `gradlePluginPortal()`
3. **`build.gradle.kts`**: mutflow plugin, JUnit 6 dependencies, `apply(from = ...)` for mutation-results added
4. **`buildSrc/` generated**: typed `MutationResults` module copied from `.omp/mutation-results-src/` with Kotlin JVM and serialization plugins
5. **`test-saboteur`** (via `task`) annotates business-logic and test classes, applies the per-class mode budget, and wraps applicable calls in `MutFlow.underTest { }`

### What happens (full mutation test run, standard mode by default)

1. **`test-quality-reviewer`** (orchestrator) receives the task and coordinates the pipeline
2. **`test-saboteur`** analyzes source code, adds `@MutationTarget` to business-logic classes, `@MutFlowTest` to test classes, and suppression comments to framework noise
3. **`test-executor`** runs one `mutationResults` Gradle invocation, optionally filtered by `--targets`; this produces the aggregate report and avoids concurrent Gradle processes writing shared results
4. **`test-auditor`** parses JSON results + JUnit XML, calculates mutation score, identifies zombie test candidates, detects over-mocked tests
5. **`test-refactor-specialist`** generates improved test code for flagged issues

- In `--mode quick`, step 5 is skipped — only audit + report output
- In `--mode deep`, step 4 includes full redundant group details and per-mutation killer data
- When approved changes are applied, the reviewer reruns the same aggregate `mutationResults` task and reports its outcome before describing the change as validated

### Prerequisites

- Kotlin JVM project with Gradle
- Java 26, Gradle 9.8.0, Kotlin 2.4.20, mutflow 1.6.0 (validated baseline)
- For fresh projects, use `/mutation-test setup` first

### mutflow architecture notes

Key mutflow constraints that affect orchestration:

- Toolkit support: plain JVM/JUnit 6 and KMP JVM. Upstream Native/JUnit 4 support is separate and not implemented in this adapter.
- Test-only mutation compilation — production artifacts stay free of mutation code
- Per-JVM overlap guard — avoid concurrent sessions; separate test JVMs are independent
- Per-mutation killer evidence — mutflow records all tests that kill each mutation, supporting zombie-candidate analysis but not a complete test-outcome matrix
- Mutation limits are applied per `@MutFlowTest` class. `maxRuns` includes the baseline run, so quick uses 11 and standard 31.
- KMP common tests stay plain `kotlin.test`; set DSL `maxMutationRuns` to 10/30/`Int.MAX_VALUE` for quick/standard/deep. `mutationResults` selects dedicated JVM mutation tasks.
- Require schema 2 reports: `killed / mutationsEvaluated`, null for gaps or zero evaluations; preserve discovered/untested totals and `testClass::displayName` identities. Do not reuse old JSON after failed compilation.
- Score bands and the mock-count review heuristic are toolkit policy, not Scott-CC thresholds.

The toolkit repository documents architecture in `docs/explanation/mutflow-architecture.md`
and role handoffs in `docs/explanation/agent-system.md`. These repository docs are
not resources shipped inside the installed skill.

### Issue tracking

Decisions and issues tracked in `.scratch/omp-mutation-testing/`. See `docs/agents/issue-tracker.md` for the tracking workflow.

### Dispatch

This skill spawns subagents via the `task` tool:

- **Setup**: `task with agent: "test-quality-reviewer", task: "Bootstrap mutation testing system into [project path] with kmp=[--kmp]"` — the orchestrator runs the bootstrap script, then invokes test-saboteur to annotate existing tests.
- **Mutation test**: `task with agent: "test-quality-reviewer", task: "Run mutation testing on [project path] with targets [targets] mode [quick|standard|deep] autoApprove [true|false]"` — the orchestrator dispatches the pipeline with the specified mode, selected tests, and approval gate.
