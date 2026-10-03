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
| `--targets` | Comma-separated Gradle test class patterns | All classes annotated with `@MutFlowTest` | Limits the test classes run by the aggregate Gradle invocation. |
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
| `.github/` | Installs the Copilot skill and its five custom agent profiles. Existing conflicting Copilot files cause setup to stop before modifying the target. |
| `settings.gradle.kts` | Adds plugin repositories through `pluginManagement`. |
| `build.gradle.kts` | Applies mutflow, adds JUnit and mutflow dependencies, applies the results script, and enables mutflow. |
| `buildSrc/` | Installs the typed mutation-results module. |
| Production sources | Adds `@MutationTarget` and applicable mutation suppressions. |
| Test sources | Adds `@MutFlowTest` and wraps tested calls in `MutFlow.underTest`. |

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
| Project type | Kotlin JVM project using Gradle. |
| Java | 26 (validated baseline; latest bytecode target supported by Kotlin 2.4.20). |
| Gradle | 9.8.0 (validated baseline). |
| Kotlin | 2.4.20 (validated baseline; must match the mutflow compiler plugin). |
| Kotlin Multiplatform | Dedicated `mutflow<Target>Test` JVM tasks; common tests stay plain `kotlin.test`. |
| Unsupported toolkit adapters | Native, JUnit 4/Android, and JS. Upstream Native/JUnit 4 support is separate. |
| Mutation execution | A mutflow lock serializes active mutation sessions within one JVM; it does not coordinate separate Gradle processes. |

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
