# How to use mutation testing with GitHub Copilot CLI

Use this guide to run the native Copilot adapter in a Kotlin project. The
adapter uses Copilot custom agents; it does not require the OMP CLI.

## Prerequisites

- GitHub Copilot CLI
- Java 26, Gradle 9.8.0, Kotlin 2.4.20, and mutflow 1.6.0 (validated baseline)
- A Kotlin/JVM project using JUnit 4 or 6, or a Kotlin Multiplatform project
  whose mutation run targets JVM source sets

The installer accepts a direct Kotlin pin or a conventional
`gradle/libs.versions.toml` plugin alias and module directory. Custom catalogs,
custom `projectDir` mappings, or customized builds require
[manual setup](manual-setup.md).

## Install the adapter

From the mutation-testing repository, run the bootstrap script against the
target project:

```bash
./.omp/bootstrap-mutation-testing.sh /path/to/kotlin-project
```

The script installs the Copilot skill under
`.github/skills/mutation-testing/` and five custom agents under
`.github/agents/`, alongside the OMP and Gradle mutation-testing files. It
refuses to follow symlinks or overwrite conflicting Copilot files. Resolve any
reported conflict yourself, then rerun setup.

It also installs `.omp/AGENT-USAGE.md` and appends its discovery pointer once
to the project's existing `AGENTS.md` without replacing project policy.

For KMP JVM installation, append `--kmp`; for a multi-module build, select its
Gradle path with `--module :module`. For a plain JVM module that already uses
JUnit 4, append `--junit4`; KMP JVM uses MutFlow's generated JUnit 6
integration. Bootstrap does not annotate sources; the targeting agent prepares
those on a subsequent mutation-test run.
KMP JVM execution still requires compatible MutFlow variants for every
declared target; see
[troubleshooting](troubleshoot-mutation-testing.md#diagnose-by-symptom).

For a manual installation, copy the complete
`.github/skills/mutation-testing/` directory and all
`.github/agents/mutation-testing-*.agent.md` files from this repository. This
installs only the Copilot client layer; also apply the Gradle and results-module
setup described in [Manual setup](manual-setup.md).

## Run mutation testing

Start Copilot CLI from the target project and invoke:

```text
/mutation-testing [project-path] [--module :path] [--targets <patterns>] [--auto-approve] [--mode quick|standard|deep]
```

The skill delegates to `mutation-testing-reviewer`, which coordinates the
targeting, execution, audit, and refactoring agents. The default mode is
`standard`. `--targets` filters Gradle test classes. Use `--mode quick` to skip
refactoring and allow at most 10 mutation runs per selected class; `--mode deep`
includes all available mutations and detailed killer data. The limit is per
class, not project-wide.

For KMP, common tests remain plain `kotlin.test` and the targeting agent sets
the DSL mutation budget. Plain JVM/JUnit 4 tests use
`@RunWith(MutFlowRunner::class)`; JUnit 6 uses `@MutFlowTest`. See the
[mode reference](../reference/mutation-testing-command.md#execution-modes).

To configure a new target project, explicitly request:

```text
/mutation-testing setup [project-path] [--kmp] [--junit4] [--module :path]
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

OMP also exposes `/mutation-testing` in its own CLI, using `.omp/agents/` and
OMP's `task`/`hub` dispatch. The Copilot adapter uses `.github/agents/` and
Copilot's native agent delegation.
