# How to use mutation testing with GitHub Copilot CLI

Use this guide to run the native Copilot adapter in a Kotlin project. The
adapter uses Copilot custom agents; it does not require the OMP CLI.

## Prerequisites

- GitHub Copilot CLI
- Java 26, Gradle 9.8.0, Kotlin 2.4.20, and mutflow 1.6.0 (validated baseline)
- A Kotlin/JVM project; Kotlin Multiplatform projects can target JVM source sets only

The installer requires an explicit compatible Kotlin pin and conventional
plugin block. For catalog-managed or customized builds, use
[manual setup](manual-setup.md).

## Install the adapter

From the mutation-testing repository, run the bootstrap script against the
target project:

```bash
./.omp/bootstrap-mutation-testing.sh /path/to/kotlin-project
```

The script installs the Copilot skill under
`.github/skills/omp-mutation-test/` and five custom agents under
`.github/agents/`, alongside the OMP and Gradle mutation-testing files. It
refuses to follow symlinks or overwrite conflicting Copilot files. Resolve any
reported conflict yourself, then rerun setup.

For KMP JVM installation, append `--kmp`. Bootstrap does not annotate sources;
the targeting agent prepares those on a subsequent mutation-test run.

For a manual installation, copy the complete
`.github/skills/omp-mutation-test/` directory and all
`.github/agents/omp-mutation-test-*.agent.md` files from this repository. This
installs only the Copilot client layer; also apply the Gradle and results-module
setup described in [Manual setup](manual-setup.md).

## Run mutation testing

Start Copilot CLI from the target project and invoke:

```text
/omp-mutation-test [project-path] [--targets <patterns>] [--auto-approve] [--mode quick|standard|deep]
```

The skill delegates to `omp-mutation-test-reviewer`, which coordinates the
targeting, execution, audit, and refactoring agents. The default mode is
`standard`. `--targets` filters Gradle test classes. Use `--mode quick` to skip
refactoring and allow at most 10 mutation runs per selected class; `--mode deep`
includes all available mutations and detailed killer data. The limit is per
class, not project-wide.

For KMP, common tests remain plain `kotlin.test` and the targeting agent sets
the DSL mutation budget. See the [mode reference](../reference/mutation-test-command.md#execution-modes).

To configure a new target project, explicitly request:

```text
/omp-mutation-test setup [project-path] [--kmp]
```

Setup changes Gradle files, `buildSrc/`, `.omp/`, and `.github/`. If setup adds
the skill while Copilot CLI is already running, reload skills with
`/skills reload` or start a new CLI session.

If the skill or reviewer is missing, verify that all installed files are in
the target workspace and start a fresh session. Do not substitute OMP dispatch
for missing Copilot agents. If existing files differ from the repository,
follow the [upgrade procedure](manual-setup.md#upgrade-an-existing-installation).

## Approval boundaries

Copilot CLI may ask permission before running shell commands or editing files.
Do not pre-approve shell access for unreviewed scripts. Without `--auto-approve`,
the refactor specialist proposes changes but does not write them. With it,
approved test refactors may be applied; deleting or consolidating tests always
requires explicit user approval.

After applied changes, the reviewer reruns the selected aggregate mutation
task. A report may exist even when strict survivors cause a nonzero Gradle
exit; compilation/discovery failures must not reuse old JSON. See
[interpreting results](interpret-results.md).

The OMP entry point `/mutation-test` remains available separately. It uses the
profiles in `.omp/agents/` and OMP's own dispatch tools; the Copilot adapter uses
the profiles in `.github/agents/` and Copilot's native agent delegation.
