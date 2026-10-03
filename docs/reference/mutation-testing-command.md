# Mutation testing command reference

`mutation-testing` runs or configures the mutation-testing pipeline for a Kotlin
project. OMP and GitHub Copilot CLI use separate native skill packages and
dispatch protocols, but expose the same command name in their respective clients.

## Invocation

```text
/mutation-testing [project-path] [--module :path] [--targets <patterns>] [--auto-approve] [--mode quick|standard|deep]
/mutation-testing setup [project-path] [--kmp] [--junit4] [--module :path]
```

The shell form prefixes the skill name with `omp`:

```text
omp mutation-testing [project-path] [options]
```

## Copilot CLI invocation

```text
/mutation-testing [project-path] [--module :path] [--targets <patterns>] [--auto-approve] [--mode quick|standard|deep]
/mutation-testing setup [project-path] [--kmp] [--junit4] [--module :path]
```

The Copilot skill delegates to the `mutation-testing-*` custom agents in
`.github/agents/`. It uses Copilot's native `agent` tool, not OMP's `task` or
`hub` tools. For installation and activation steps, see
[How to use mutation testing with Copilot CLI](../how-to/use-with-copilot.md).

## Mutation test command

```text
/mutation-testing [project-path] [options]
```

### Argument

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `project-path` | No | Current directory | Root directory of the Kotlin project. |
| `--module` | No | Root project | Gradle path such as `:module`; selects one configured subproject for targeting, execution, and reporting. |

### Options

| Option | Value | Default | Description |
|--------|-------|---------|-------------|
| `--module` | Gradle project path such as `:module` | Root project | Selects the module whose `mutationResults` task is run. |
| `--targets` | Comma-separated Gradle test class patterns | No filter on the selected mutation test tasks | Limits the test classes run by the aggregate Gradle invocation. |
| `--auto-approve` | None | Disabled | Permits the refactor specialist to apply additive or assertion-level test refactors. Deleting or consolidating tests always requires explicit user approval. |
| `--mode` | `quick`, `standard`, or `deep` | `standard` | Selects the mutation limit and report detail described under [Execution modes](#execution-modes). |

## Setup command

```text
/mutation-testing setup [project-path] [--kmp] [--junit4] [--module :path]
```

The `setup` subcommand installs and configures the mutation-testing system.

### Argument

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `project-path` | No | Current directory | Root directory of the Kotlin project. |
| `--module` | No | Root project | Gradle path such as `:module`; configures one module using its default directory mapping. Toolkit files and `buildSrc` stay at the root. |

### Option

| Option | Value | Default | Description |
|--------|-------|---------|-------------|
| `--kmp` | None | Disabled | Configures the selected KMP module. KMP JVM uses MutFlow's generated JUnit 6 integration. |
| `--junit4` | None | JUnit 6 | Selects the MutFlow JUnit 4 runner for plain JVM; not applicable to KMP. |
| `--module` | Gradle project path such as `:module` | Root project | Configures the selected module and applies the matching qualified Gradle task. |

### Effects

| Area | Effect |
|------|--------|
| `.omp/` | Copies the agents, mutation-testing skill, Gradle results script, and typed results source. |
| `AGENTS.md` | Appends a single pointer to the installed `.omp/AGENT-USAGE.md`, preserving existing project policy. Differing guides or symlinked destinations stop setup. |
| `.github/` | Installs the Copilot skill and its five custom agent profiles. Existing conflicting Copilot files cause setup to stop before modifying the target. |
| `settings.gradle.kts` | Adds plugin repositories through `pluginManagement` when a Kotlin settings file is used. |
| Selected module build | Applies mutflow and the results script, enables mutflow, and configures the selected JUnit adapter. JUnit 6 is the default; `--junit4` selects `mutflow-junit4` for plain JVM. |
| `buildSrc/` | Installs the typed mutation-results module. |
| Production sources | The setup agent adds `@MutationTarget` and applicable suppressions; the shell installer alone does not annotate source. |
| Test sources | The agent wraps calls in `MutFlow.underTest`; plain JVM uses JUnit 6 `@MutFlowTest` or JUnit 4 `@RunWith(MutFlowRunner::class)`, while KMP common tests retain `kotlin.test`. |

For an executable setup walkthrough, see [Tutorial: Bootstrap mutation testing into an existing Kotlin project](../tutorials/bootstrap-existing-project.md).

## Execution modes

| Mode | Mode | Maximum mutation runs per selected plain JVM test class | Refactor phase | Report detail |
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
| Project type | Plain Kotlin/JVM with JUnit 4 or 6, or KMP with a JVM target using the generated JUnit 6 integration and a MutFlow-compatible variant for every declared target; Gradle Kotlin DSL. |
| Java | 26 (validated baseline; latest bytecode target supported by Kotlin 2.4.20). |
| Gradle | 9.8.0 (validated baseline). |
| Kotlin | 2.4.20 (validated baseline; must match the mutflow compiler plugin). |
| Kotlin Multiplatform | Dedicated `mutflow<Target>Test` JVM tasks; common tests stay plain `kotlin.test`. Every declared target must resolve MutFlow's common-source-set dependencies; selecting only the JVM task does not bypass missing variants. |
| Unsupported toolkit adapters | Native, Android, and JS. Upstream support does not imply a toolkit adapter. |
| Bootstrap module support | Standard `gradle/libs.versions.toml` Kotlin plugin aliases and default module directories; custom catalogs or `projectDir` mappings require manual setup. |
| Mutation execution | A per-JVM overlap guard rejects overlapping sessions; it does not queue them or coordinate separate Gradle processes. |
| Configuration cache | Unsupported: `prepareMutationResults` captures script references that fail cache storage. Use `--no-configuration-cache` when enabled globally. |

## Direct Gradle execution

For a configured project with annotated/wrapped tests:

```bash
gradle mutationResults '-PmutationTest.includes=example.OrderTest,example.PriceTest'
```

For a selected subproject, use its qualified task, for example
`gradle :module:mutationResults`. KMP runs also require compatible MutFlow
variants for every declared target; see
[troubleshooting](../how-to/troubleshoot-mutation-testing.md#diagnose-by-symptom).

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
/mutation-testing
```

Quick mode for selected test classes:

```text
/mutation-testing /work/orders --targets "*OrderServiceTest" --mode quick
```

Kotlin Multiplatform setup:

```text
/mutation-testing setup /work/shared-library --kmp
```
