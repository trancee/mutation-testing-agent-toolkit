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

The toolkit checkout also provides a root command for installing or updating
target files. It is separate from the client skill invocation:

```bash
./bootstrap.sh install [project-path] [--kmp] [--junit4] [--module :path]
./bootstrap.sh update [project-path] [--dry-run] [--force RELATIVE_PATH]...
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

### Option

| Option | Value | Default | Description |
|--------|-------|---------|-------------|
| `--kmp` | None | Disabled | Configures the selected KMP module. KMP JVM uses MutFlow's generated JUnit 6 integration. |
| `--junit4` | None | JUnit 6 | Selects the MutFlow JUnit 4 runner for plain JVM. It does not apply to KMP. |
| `--module` | Gradle project path such as `:module` | Root project | Configures the selected module and applies the matching qualified Gradle task. |

### Effects

| Area | Effect |
|------|--------|
| `.mutation-testing/` | Installs the neutral guide, results script, canonical typed sources, and hash manifest. |
| `.omp/` | Installs OMP-native agents and skills only. Their native discovery paths stay unchanged. |
| `AGENTS.md` | Adds the current toolkit discovery pointer while preserving project policy. Symlinked destinations stop setup. |
| `.github/` | Installs the Copilot skill and five custom agent profiles. Manifest-backed updates preserve local edits and report conflicts. |
| `settings.gradle.kts` | Adds plugin repositories through `pluginManagement` when a Kotlin settings file is used. |
| Selected module build | Applies mutflow and the results script, enables mutflow, and configures the selected JUnit adapter. JUnit 6 is the default. `--junit4` selects `mutflow-junit4` for plain JVM. |
| `buildSrc/` | Installs generated copies of the typed mutation-results module and tracks their hashes for safe synchronization. |
| Production sources | The setup agent adds `@MutationTarget` and applicable suppressions. The shell installer does not annotate source. |
| Test sources | The agent wraps calls in `MutFlow.underTest`. Plain JVM uses JUnit 6 `@MutFlowTest` or JUnit 4 `@RunWith(MutFlowRunner::class)`. KMP common tests retain `kotlin.test`. |

For an executable setup walkthrough, see [Tutorial: Bootstrap mutation testing into an existing Kotlin project](../tutorials/bootstrap-existing-project.md).

## Update an existing installation

Updates use the root `bootstrap.sh update` command from a local toolkit
checkout. The `bootstrap.sh install` command is the separate first-install
path. Fast-forward the checkout yourself, review
`--dry-run` output, and use repeated per-file `--force` options only after
reviewing each conflict. A valid `.mutation-testing/manifest.json` is required.
If it is absent or invalid, the updater stops before writing. The manifest
records the source revision and managed-file SHA-256 hashes. See the
[update guide](../how-to/update-installation.md).

## Execution modes

| Mode | Plain JVM run limit per selected test class | Refactor phase | Report detail |
|------|-----------------------------------------------|----------------|---------------|
| `quick` | 10 (`maxRuns=11`, including baseline) | Skipped | Audit and summary report. |
| `standard` | 30 (`maxRuns=31`, including baseline) | Included | Audit, refactoring suggestions, and summary report. |
| `deep` | All available mutations (`maxRuns` omitted) | Included | Full redundant-group details and per-mutation killer data. |

The limit applies independently to each selected test class. It is not a
project-wide mutation ceiling. The command runs the selected classes in one
aggregate `mutationResults` Gradle invocation.

For KMP, the equivalent DSL budget is `maxMutationRuns = 10`, `30`, or
`Int.MAX_VALUE`. It excludes the baseline. Common tests stay plain `kotlin.test`.
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

Deep mode also includes full redundant-test-group details and per-mutation
killer matrices. See the
[Mutation results JSON format](mutation-results-format.md) for the structured
Gradle report.

## Requirements and constraints

| Item | Requirement or constraint |
|------|---------------------------|
| Project type | Plain Kotlin/JVM with JUnit 4 or 6, or KMP with a JVM target and the generated JUnit 6 integration. Every declared target must resolve a compatible MutFlow variant. Uses Gradle Kotlin DSL. |
| Python | 3.10 or newer for the root `bootstrap.sh` install and update commands. |
| Java | 26 (validated baseline). Kotlin 2.4.21 supports this bytecode target. |
| Gradle | `9.8.0` (repository test baseline). Kotlin `2.4.21` lists `9.7.0` as the latest fully supported version. See the [compatibility table](https://kotlinlang.org/docs/gradle-configure-project.html#check-for-compatibility). |
| Kotlin | 2.4.21 (validated baseline with MutFlow 1.7.0). |
| Kotlin Multiplatform | Uses dedicated `mutflow<Target>Test` JVM tasks. Common tests stay plain `kotlin.test`. Every declared target must resolve MutFlow's common-source-set dependencies. Selecting only the JVM task does not bypass missing variants. |
| Unsupported toolkit adapters | Native, Android, and JS. Upstream support does not imply a toolkit adapter. |
| Bootstrap module support | Supports standard `gradle/libs.versions.toml` Kotlin plugin aliases and default module directories. Custom catalogs or `projectDir` mappings require manual setup. |
| Mutation execution | A per-JVM overlap guard rejects overlapping sessions. It does not queue them or coordinate separate Gradle processes. |
| Configuration cache | Unsupported: `prepareMutationResults` captures script references that fail cache storage. Use `--no-configuration-cache` when enabled globally. |

## Direct Gradle execution

For a configured project with annotated/wrapped tests:

```bash
gradle mutationResults '-PmutationTest.includes=example.OrderTest,example.PriceTest'
```

For a selected subproject, use its qualified task, such as
`gradle :module:mutationResults`. KMP runs also require compatible MutFlow
variants for every declared target. See
[troubleshooting](../how-to/troubleshoot-mutation-testing.md#diagnose-by-symptom).

Use the project's `./gradlew` instead of `gradle` when a wrapper is present.
`mutationTest.includes` accepts nonempty comma-separated Gradle test patterns,
not production-class targets. Do not filter individual test methods when you
need a complete mutation session. `mutflow.targets` selects production classes
or files instead.

Plain JVM selects `test`. KMP selects dedicated `mutflow<Target>Test` JVM
tasks. Without a filter, ordinary tests on those tasks can also run. JSON is
written to `build/reports/mutation-results.json`. The human-readable summary
is written to `build/reports/mutation-results.md` and printed in Gradle output.
GitHub Actions also appends that summary to the workflow run's job summary when
`GITHUB_STEP_SUMMARY` is available. Strict survivors, mutation timeouts, test
failures, and gaps produce nonzero status after the reports are written.
Compilation or discovery failures may leave no current report. Never reuse an
earlier report.

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
