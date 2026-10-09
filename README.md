# Mutation Testing Agent Toolkit

Run mutflow mutation tests in Kotlin/JVM projects with this five-role toolkit.
It provides native adapters for [OMP](https://omp.sh/) and GitHub Copilot CLI.
Both clients use the same mutation-results contract.

**AI agents:** start with [AGENTS.md](AGENTS.md) and its
[agent-only usage guide](AGENT-USAGE.md), rather than the human tutorials below.

The five roles adapt the workflow from
[Scott-CC's mutation-testing plugin](https://github.com/citadelgrad/scott-cc/tree/main/plugins/mutation-testing).
This toolkit uses mutflow's predefined Kotlin operators and test-only
compilation instead of LLM-generated mutations in separate Git worktrees. It
does not promise feature parity. See
[how the designs differ](docs/adr/0002-agent-structure-and-orchestration-model.md#adaptation-boundaries).

## Quick start

Clone this repository and run the installer from its root. The target project
must use a conventional multiline Kotlin DSL `plugins` block and pin Kotlin
`2.4.21` directly or through the default `gradle/libs.versions.toml` plugin
alias. Custom catalogs, convention builds, or project-directory mappings need
[manual setup](docs/how-to/manual-setup.md).

```bash
git clone https://github.com/trancee/mutation-testing-agent-toolkit.git
cd mutation-testing-agent-toolkit

# Install into a separate Kotlin JVM project
./bootstrap.sh install /path/to/kotlin-project
```

The repository's integration checks use Java `26`, Gradle `9.8.0`, Kotlin
`2.4.21`, and MutFlow `1.7.0`. Kotlin's compatibility table lists Gradle
`9.7.0` as the latest fully supported version for Kotlin `2.4.21`. The
repository passes on `9.8.0`, but that does not extend Kotlin's support range.
See [toolchain compatibility](docs/how-to/run-checks.md#toolchain-compatibility).
Python 3.10 or newer is required by the root `./bootstrap.sh` install and
update commands.
For KMP JVM projects, append `--kmp` and select a subproject with
`--module :module` when needed. For a plain JVM project already using JUnit 4,
append `--junit4`. See [manual setup](docs/how-to/manual-setup.md).

The installer configures Gradle and installs both client adapters. It does not
annotate your source files. Choose a client from the target project:

| Client | Entry point |
|--------|-------------|
| OMP | `/mutation-testing` in OMP, or `omp mutation-testing /path/to/kotlin-project` |
| GitHub Copilot CLI | Start `copilot` and invoke `/mutation-testing` |

The agents select targets and prepare tests before running Gradle. Follow
[How to use mutation testing with Copilot CLI](docs/how-to/use-with-copilot.md)
to install and start the Copilot adapter. Neither client is required to run an
already-prepared suite. Use the project's Gradle wrapper when available.
Otherwise, run:

```bash
gradle -p /path/to/kotlin-project mutationResults
```

The task prints an aggregate summary and writes
`build/reports/mutation-results.md` and
`build/reports/mutation-results.json`. GitHub Actions also shows the summary
table in the workflow run's job summary. Strict survivors and timeouts return a
failing exit status even when the reports are complete. See
[How to interpret results](docs/how-to/interpret-results.md).

Browse the [documentation index](docs/index.md) for tutorials, task guides,
references, and explanations. Start with
[your first mutation test](docs/tutorials/first-mutation-test.md). Then try the
[agent-assisted workflow](docs/tutorials/agent-assisted-mutation-test.md) or
[KMP JVM tutorial](docs/tutorials/kmp-jvm-mutation-test.md). For failed or
incomplete runs, use
[How to troubleshoot mutation testing](docs/how-to/troubleshoot-mutation-testing.md).

## Update an existing installation

Fast-forward the toolkit checkout, preview the target changes, review conflicts,
then apply the update. The script does not fetch remote code. This repository has
no tagged stable release channel, so updates use the current local checkout and
record its commit SHA when available.

```bash
git -C "/path/to/mutation-testing-agent-toolkit" pull --ff-only
"/path/to/mutation-testing-agent-toolkit/bootstrap.sh" update "/path/to/kotlin-project" --dry-run
"/path/to/mutation-testing-agent-toolkit/bootstrap.sh" update "/path/to/kotlin-project"
```

The updater preserves local edits and prints diffs. Approve only reviewed files
with repeated `--force <project-relative-path>` options. Updates require a valid
`.mutation-testing/manifest.json`. If it is absent, the updater stops before
writing. See the [update guide](docs/how-to/update-installation.md). The
[results-contract upgrade guide](docs/how-to/manual-setup.md#upgrade-an-existing-installation)
covers `io.omp.mutation` and schema 1 migrations.

## Sample project

The `sample/` directory contains a reference Kotlin project with a `Calculator`
class and the JUnit 4 `MutFlowRunner`: **32/32 mutations killed** (100% score,
Excellent band, Medium confidence). The real Gradle integration harness also
keeps the JUnit 6 path covered. These results apply to the selected operators,
not proof of complete behavioral coverage. Reproduce the JUnit 4 sample from
the repository root:

```bash
gradle -p sample mutationResults
```

The sample run writes its human-readable summary to
`sample/build/reports/mutation-results.md` and its machine-readable results to
`sample/build/reports/mutation-results.json`.

The sample exercises boundary, boolean, arithmetic, return-value, and
exception-type categories, not every operator in upstream's catalog.

## Contribute

Read [CONTRIBUTING.md](CONTRIBUTING.md) for the branch, documentation, and
testing workflow. Use
[repository checks](docs/how-to/run-checks.md) for the complete validation list.

## Maintenance

The daily upstream monitor reports stable-release, compiler-compatibility, and
source drift. Dependabot proposes dependency updates. Neither tool accepts an
incompatible update automatically.

## Known limitations

- **Kotlin Multiplatform:** `--kmp` configures mutation tests for a selected
  module's JVM target. Every declared target must resolve MutFlow's
  common-source-set dependencies. MutFlow `1.7.0` publishes JVM, `linuxX64`,
  and `mingwX64` variants, but not iOS or Android Native variants. A project
  with those targets can fail dependency resolution before the JVM mutation
  task runs. The toolkit does not provide Native, Android, or JS adapters.
- **JUnit:** plain JVM supports JUnit 4 (`--junit4`) and JUnit 6 (default).
  KMP JVM uses MutFlow's generated JUnit 6 integration.
- **Setup scope:** custom version catalogs, nonstandard plugin-block layouts,
  and `projectDir` mappings require manual setup.
- **Results migration**: existing `io.omp.mutation` installations and schema 1
  consumers need the [coordinated migration](docs/how-to/manual-setup.md#upgrade-an-existing-installation).
- **Gradle configuration cache:** the current results adapter does not support
  it. Use `--no-configuration-cache` when the target enables it globally.
- **Test-quality findings**: killer data supports zombie/redundancy candidates,
  not proof that a test can safely be deleted.

See the [command reference](docs/reference/mutation-testing-command.md) for
modes and constraints. Read [CONTEXT.md](CONTEXT.md) for domain terminology.
