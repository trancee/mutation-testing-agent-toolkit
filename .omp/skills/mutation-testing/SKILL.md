---
name: mutation-testing
description: Run mutflow-powered mutation testing on a Kotlin project via the toolkit's 5-agent OMP adapter (test-quality-reviewer orchestrator, test-saboteur, test-executor, test-auditor, test-refactor-specialist). JVM-first.
---

## Mutation Testing

Runs a mutation-testing analysis on a Kotlin (JVM-first) project using mutflow as the engine and the toolkit's OMP adapter for orchestration.

### Usage

- `project path`: Path to the Kotlin project root (default: current directory)
- `--module`: Optional Gradle project path to select within a multi-module build
- `--targets`: Optional comma-separated Gradle test class patterns (default: all tests in the selected mutation task)
- `--kmp`: (setup only) Configure the toolkit's KMP JVM integration.
- `--junit4`: (setup only) Select the plain JVM JUnit 4 runner instead of the default JUnit 6 integration. KMP JVM uses its generated JUnit 6 integration.
- `--auto-approve`: Permits additive or assertion-level test changes to be applied. Deleting or consolidating tests always requires explicit approval.
- `--mode quick`: At most 10 mutation runs per selected test class (`maxRuns=11`, including the baseline for plain JVM; KMP excludes baseline). Skip refactoring — only audit and report.
- `--mode standard`: (default) At most 30 mutation runs per selected test class (`maxRuns=31`, including the baseline for plain JVM; KMP excludes baseline). Run the full pipeline and provide refactoring suggestions.
- `--mode deep`: Run all available mutations per selected test class. Include full redundant-group details and per-mutation killer data in the report.

```
/mutation-testing [project path] [--module :path] [--targets <patterns>] [--auto-approve] [--mode quick|standard|deep]
/mutation-testing setup [project path] [--kmp] [--junit4] [--module :path]
```

### Setup subcommand

`/mutation-testing setup [project path] [--kmp] [--junit4] [--module :path]`
sets up the system in the selected project or Gradle module:

1. **Shared toolkit payload**: guide, Gradle results script, canonical typed sources, and manifest installed under `project-path/.mutation-testing/`; OMP agents and skills remain under `.omp/`
2. **`settings.gradle.kts`**: `pluginManagement` block added with `mavenCentral()` + `gradlePluginPortal()`
3. **Selected module `build.gradle.kts`**: mutflow plugin, results script, and framework-specific wiring; `--junit4` installs the JUnit 4 runner for plain JVM, while the default and KMP JVM use JUnit 6
4. **`buildSrc/` generated**: typed `MutationResults` module copied from `.mutation-testing/mutation-results-src/` with Kotlin JVM and serialization plugins
5. **`test-saboteur`** (via `task`) annotates business-logic and test classes, applies the per-class mode budget, and wraps applicable calls in `MutFlow.underTest { }`

Setup and update use the root command in the toolkit checkout. For example,
run `"/absolute/toolkit/bootstrap.sh" install "/absolute/target"` for an
explicitly requested setup. To update, fast-forward the toolkit checkout and run
`"/absolute/toolkit/bootstrap.sh" update "/absolute/target" --dry-run`, then
apply after reviewing conflicts. A valid `.mutation-testing/manifest.json` is
required; an absent manifest stops the update before writing. OMP agents and
skills remain OMP-native under `.omp/agents/` and `.omp/skills/`.

### What happens (full mutation test run, standard mode by default)

1. **`test-quality-reviewer`** (orchestrator) receives the task and coordinates the pipeline
2. **`test-saboteur`** analyzes source code, adds `@MutationTarget` to business-logic classes, uses the selected JUnit integration (`@MutFlowTest`, JUnit 4 `@RunWith(MutFlowRunner::class)`, or KMP common tests), and adds suppression comments to framework noise
3. **`test-executor`** runs one `mutationResults` Gradle invocation in the
   selected module, optionally filtered by `--targets`; this produces aggregate
   JSON and a readable Markdown summary, which is also added to the GitHub
   Actions job summary when available
4. **`test-auditor`** parses JSON results + JUnit XML, calculates mutation score, identifies zombie test candidates, detects over-mocked tests
5. **`test-refactor-specialist`** generates improved test code for flagged issues

- In `--mode quick`, step 5 is skipped — only audit + report output
- In `--mode deep`, step 4 includes full redundant group details and per-mutation killer data
- When approved changes are applied, the reviewer reruns the same aggregate `mutationResults` task and reports its outcome before describing the change as validated

### Prerequisites

- Kotlin JVM project with Gradle
- Python 3.10 or newer for setup/update; Java 26, Gradle 9.8.0, Kotlin 2.4.20, mutflow 1.6.0 (validated baseline)
- For fresh projects, use `/mutation-testing setup` first

### mutflow architecture notes

Key mutflow constraints that affect orchestration:

- Toolkit support: plain JVM/JUnit 4 or JUnit 6, plus KMP JVM through MutFlow's
  generated JUnit 6 integration when every declared target can resolve its
  common-source-set dependencies. In the validated MutFlow `1.6.0` baseline,
  artifacts publish JVM, `linuxX64`, and `mingwX64`, but not iOS or Android
  Native variants; selecting only the JVM task does not avoid dependency
  resolution. The toolkit does not prune unsupported targets or provide
  Native, Android, and JS execution adapters.
- Test-only mutation compilation — production artifacts stay free of mutation code
- Per-JVM overlap guard — avoid concurrent sessions; separate test JVMs are independent
- Per-mutation killer evidence — mutflow records all tests that kill each mutation, supporting zombie-candidate analysis but not a complete test-outcome matrix
- Plain JVM limits apply per test class; `maxRuns` includes the baseline run, so quick uses 11 and standard 31. Use the selected JUnit adapter's `@MutFlowTest` annotation when setting a per-class budget.
- Plain JVM/JUnit 4 uses `MutFlowRunner` and the JUnit 4 `@MutFlowTest` annotation only when a per-class budget is needed; KMP JVM uses its generated JUnit 6 integration.
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

- **Setup**: `task with agent: "test-quality-reviewer", task: "Bootstrap mutation testing into [project path], module [Gradle path], KMP [true|false], JUnit 4 [true|false]"` — the orchestrator runs the toolkit checkout root `bootstrap.sh install` command, then invokes test-saboteur to configure tests.
- **Mutation test**: `task with agent: "test-quality-reviewer", task: "Run mutation testing on [project path], module [Gradle path], targets [targets], mode [quick|standard|deep], autoApprove [true|false]"` — the orchestrator dispatches the pipeline with the specified module, mode, selected tests, and approval gate.
