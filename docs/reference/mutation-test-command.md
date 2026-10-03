# mutation-test command reference

`mutation-test` runs or configures the OMP mutation-testing pipeline for a Kotlin project. GitHub Copilot CLI has a separate native entry point, `/omp-mutation-test`.

## Invocation

```text
/mutation-test [project-path] [--targets <patterns>] [--auto-approve] [--mode quick|standard|deep]
/mutation-test setup [project-path] [--kmp]
```

The shell form prefixes the skill name with `omp`:

```text
omp mutation-test [project-path] [options]
```

## Copilot CLI invocation

```text
/omp-mutation-test [project-path] [--targets <patterns>] [--auto-approve] [--mode quick|standard|deep]
/omp-mutation-test setup [project-path] [--kmp]
```

The Copilot skill delegates to the `omp-mutation-test-*` custom agents in
`.github/agents/`. It uses Copilot's native `agent` tool, not OMP's `task` or
`hub` tools. For installation and activation steps, see
[How to use mutation testing with Copilot CLI](../how-to/use-with-copilot.md).

## Mutation test command

```text
/mutation-test [project-path] [options]
```

### Argument

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `project-path` | No | Current directory | Root directory of the Kotlin project. |

### Options

| Option | Value | Default | Description |
|--------|-------|---------|-------------|
| `--targets` | Comma-separated Gradle test class patterns | No filter on the selected mutation test tasks | Limits the test classes run by the aggregate Gradle invocation. |
| `--auto-approve` | None | Disabled | Permits the refactor specialist to apply additive or assertion-level test refactors. Deleting or consolidating tests always requires explicit user approval. |
| `--mode` | `quick`, `standard`, or `deep` | `standard` | Selects the mutation limit and report detail described under [Execution modes](#execution-modes). |

## Setup command

```text
/mutation-test setup [project-path] [--kmp]
```

The `setup` subcommand installs and configures the mutation-testing system.

### Argument

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `project-path` | No | Current directory | Root directory of the Kotlin project. |

### Option

| Option | Value | Default | Description |
|--------|-------|---------|-------------|
| `--kmp` | None | Disabled | Configures Kotlin Multiplatform setup. Only JVM source sets participate in mutation testing. |

### Effects

| Area | Effect |
|------|--------|
| `.omp/` | Copies the agents, mutation-test skill, Gradle results script, and typed results source. |
| `AGENTS.md` | Appends a single pointer to the installed `.omp/AGENT-USAGE.md`, preserving existing project policy. Differing guides or symlinked destinations stop setup. |
| `.github/` | Installs the Copilot skill and its five custom agent profiles. Existing conflicting Copilot files cause setup to stop before modifying the target. |
| `settings.gradle.kts` | Adds plugin repositories through `pluginManagement`. |
| `build.gradle.kts` | Applies mutflow and the results script, enables mutflow, and configures JUnit dependencies/Platform for plain JVM. The plugin supplies mutflow integration. |
| `buildSrc/` | Installs the typed mutation-results module. |
| Production sources | The setup agent adds `@MutationTarget` and applicable suppressions; the shell installer alone does not annotate source. |
| Test sources | The agent wraps calls in `MutFlow.underTest` and adds `@MutFlowTest` for plain JVM; KMP common tests retain `kotlin.test`. |

For an executable setup walkthrough, see [Tutorial: Bootstrap mutation testing into an existing Kotlin project](../tutorials/bootstrap-existing-project.md).

## Execution modes

| Mode | Maximum mutation runs per selected `@MutFlowTest` class | Refactor phase | Report detail |
|------|-----------------------|----------------|---------------|
| `quick` | 10 (`maxRuns=11`, including baseline) | Skipped | Audit and summary report. |
| `standard` | 30 (`maxRuns=31`, including baseline) | Included | Audit, refactoring suggestions, and summary report. |
| `deep` | All available mutations (`maxRuns` omitted) | Included | Full redundant-group details and per-mutation killer data. |

The limit applies independently to each selected test class; it is not a
project-wide mutation ceiling. The command runs the selected classes in one
aggregate `mutationResults` Gradle invocation.

For KMP, the equivalent DSL budget is `maxMutationRuns = 10`, `30`, or
`Int.MAX_VALUE`; it excludes baseline. Common tests stay plain `kotlin.test`.
Ambient `MUTFLOW_MAX_RUNS` overrides must be reported because they can alter
the effective budget.

## Final report

The pipeline's final report contains:

- Mutation score and quality band
- Confidence level and 95% Wilson confidence interval
- Execution gaps
- Surviving mutations and their source locations
- Zombie-test candidates
- Over-mocked tests
- Refactoring suggestions
- Applied refactoring diffs and rollback instructions, when applicable

Deep mode also includes full redundant-test-group details and per-mutation killer matrices. The structured Gradle report is documented in [Mutation results JSON format](mutation-results-format.md).

## Requirements and constraints

| Item | Requirement or constraint |
|------|---------------------------|
| Project type | Kotlin JVM or KMP with a JVM target, using Gradle Kotlin DSL. |
| Java | 26 (validated baseline; latest bytecode target supported by Kotlin 2.4.20). |
| Gradle | 9.8.0 (validated baseline). |
| Kotlin | 2.4.20 (validated baseline; must match the mutflow compiler plugin). |
| Kotlin Multiplatform | Dedicated `mutflow<Target>Test` JVM tasks; common tests stay plain `kotlin.test`. |
| Unsupported toolkit adapters | Native, JUnit 4/Android, and JS. Upstream Native/JUnit 4 support is separate. |
| Mutation execution | A per-JVM overlap guard rejects overlapping sessions; it does not queue them or coordinate separate Gradle processes. |
| Configuration cache | Unsupported: `prepareMutationResults` captures script references that fail cache storage. Use `--no-configuration-cache` when enabled globally. |

## Direct Gradle execution

For a configured project with annotated/wrapped tests:

```bash
gradle mutationResults '-PmutationTest.includes=example.OrderTest,example.PriceTest'
```

Use the project's `./gradlew` instead of `gradle` when a wrapper is present.
`mutationTest.includes` accepts nonempty comma-separated Gradle test patterns,
not production-class targets. Do not filter individual test methods when you
need a complete mutation session. `mutflow.targets` selects production classes
or files instead.

Plain JVM selects `test`; KMP selects dedicated `mutflow<Target>Test` JVM
tasks. No filter means ordinary tests on those tasks can also run. JSON is
written to `build/reports/mutation-results.json`. Strict survivors, mutation
timeouts, test failures, and gaps produce nonzero status; compilation or
discovery failures may leave no JSON. Never reuse an earlier report.

Upstream `MUTFLOW_VERIFICATION_MODE` can override verification with `STRICT`,
`LENIENT`, or `DISABLED`. Disabled mutation execution is not a quality result.
Record effective environment overrides alongside the run budget. For a
threshold-based CI policy, see [the GitHub Actions guide](../how-to/run-in-github-actions.md).

For pipeline ordering and agent responsibilities, see [About the mutation-testing agent system](../explanation/agent-system.md). For the mutation engine constraints, see [About mutflow's test-only mutation compilation](../explanation/mutflow-architecture.md).

## Examples

Standard mode against the current directory:

```text
/mutation-test
```

Quick mode for selected test classes:

```text
/mutation-test /work/orders --targets "*OrderServiceTest" --mode quick
```

Kotlin Multiplatform setup:

```text
/mutation-test setup /work/shared-library --kmp
```
