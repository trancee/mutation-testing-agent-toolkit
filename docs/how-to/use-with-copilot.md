# How to use mutation testing with GitHub Copilot CLI

Use this guide to run the native Copilot adapter in a Kotlin project. The
adapter uses Copilot custom agents; it does not require the OMP CLI.

## Prerequisites

- GitHub Copilot CLI
- Java 26, Gradle 9.8.0, Kotlin 2.4.20, and mutflow 1.6.0 (validated baseline)
- A Kotlin/JVM project; Kotlin Multiplatform projects can target JVM source sets only

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

For a manual installation, copy the complete
`.github/skills/omp-mutation-test/` directory and all
`.github/agents/omp-mutation-test-*.agent.md` files from this repository. This
installs only the Copilot client layer; also apply the Gradle and results-module
setup described in [Manual setup](manual-setup.md).

## Run mutation testing

Start Copilot CLI from the target project and invoke:

```text
/omp-mutation-test [project-path] [--targets <pattern>] [--focus <patterns>] [--auto-approve] [--mode quick|standard|deep]
```

The skill delegates to `omp-mutation-test-reviewer`, which coordinates the
targeting, execution, audit, and refactoring agents. The default mode is
`standard`. Use `--mode quick` to skip refactoring and limit the run to 10
mutations; `--mode deep` includes all available mutations and detailed killer
matrices.

To configure a new target project, explicitly request:

```text
/omp-mutation-test setup [project-path] [--kmp]
```

Setup changes Gradle files, `buildSrc/`, `.omp/`, and `.github/`. If setup adds
the skill while Copilot CLI is already running, reload skills with
`/skills reload` or start a new CLI session.

## Approval boundaries

Copilot CLI may ask permission before running shell commands or editing files.
Do not pre-approve shell access for unreviewed scripts. Without `--auto-approve`,
the refactor specialist proposes changes but does not write them. With it,
approved test refactors may be applied; deleting zombie tests or redundant test
groups still requires explicit user approval.

The OMP entry point `/mutation-test` remains available separately. It uses the
profiles in `.omp/agents/` and OMP's own dispatch tools; the Copilot adapter uses
the profiles in `.github/agents/` and Copilot's native agent delegation.
