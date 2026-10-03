# mutation-test command reference

`mutation-test` runs or configures the OMP mutation-testing pipeline for a Kotlin project. GitHub Copilot CLI has a separate native entry point, `/omp-mutation-test`.

## Invocation

```text
/mutation-test [project-path] [--targets <pattern>] [--focus <patterns>] [--auto-approve] [--mode quick|standard|deep]
/mutation-test setup [project-path] [--kmp]
```

The shell form prefixes the skill name with `omp`:

```text
omp mutation-test [project-path] [options]
```

## Copilot CLI invocation

```text
/omp-mutation-test [project-path] [--targets <pattern>] [--focus <patterns>] [--auto-approve] [--mode quick|standard|deep]
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
| `--targets` | Glob pattern | All classes annotated with `@MutFlowTest` | Limits the included test classes. |
| `--focus` | Comma-separated class patterns | All included test classes | Passes class patterns to the Gradle test task's `includeTargets` filtering. |
| `--auto-approve` | None | Disabled | Permits the refactor specialist to apply proposed test refactors. Deleting zombie tests or redundant test groups still requires explicit approval. |
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

| Mode | Maximum mutation runs | Refactor phase | Report detail |
|------|-----------------------|----------------|---------------|
| `quick` | 10 | Skipped | Audit and summary report. |
| `standard` | 30 | Included | Audit, refactoring suggestions, and summary report. |
| `deep` | All available mutations | Included | Full redundant-group details and per-mutation killer matrices. |

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
| Kotlin Multiplatform | JVM source sets only. |
| Unsupported targets | Kotlin/JS, Kotlin/Native, and Android. |
| Mutation execution | A global mutflow lock serializes active mutation sessions within each JVM. |

For pipeline ordering and agent responsibilities, see [About the mutation-testing agent system](../explanation/agent-system.md). For the mutation engine constraints, see [About mutflow's test-only mutation compilation](../explanation/mutflow-architecture.md).

## Examples

Standard mode against the current directory:

```text
/mutation-test
```

Quick mode for selected test classes:

```text
/mutation-test /work/orders --focus "*OrderServiceTest" --mode quick
```

Kotlin Multiplatform setup:

```text
/mutation-test setup /work/shared-library --kmp
```
