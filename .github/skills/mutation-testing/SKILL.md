---
name: mutation-testing
description: Run, bootstrap, or analyze mutflow-powered mutation testing for Kotlin/JVM projects with the Mutation Testing Agent Toolkit's Copilot-native workflow. Use for explicit mutation-testing requests, not ordinary unit-test tasks.
compatibility: GitHub Copilot CLI with the project agents in .github/agents.
---

# Mutation testing in Copilot CLI

Use this skill as the Copilot CLI entry point. Delegate to the
`mutation-testing-reviewer` custom agent with Copilot's `agent` tool. Do not use
OMP's `task`, `hub`, or `tasks[]` interfaces.

```text
/mutation-testing [project path] [--module :path] [--targets <patterns>] [--auto-approve] [--mode quick|standard|deep]
/mutation-testing setup [project path] [--kmp] [--junit4] [--module :path]
```

- `--module` selects an installed Gradle subproject; the executor uses its
  qualified `:module:mutationResults` task.
- `--targets` selects Gradle test class patterns; by default, run all tests in the selected mutation task.
- `--mode quick` allows at most 10 mutation runs per selected class (`maxRuns=11`, including baseline) and skips refactoring.
- `--mode standard` allows at most 30 mutation runs per selected class (`maxRuns=31`, including baseline) and includes refactoring suggestions.
- `--mode deep` runs all available mutations per selected class and includes detailed killer data.
- `--auto-approve` permits applying proposed test refactors; it never permits deleting
  zombie tests or redundant groups without explicit user approval.
- `setup` invokes the toolkit checkout root command, `bootstrap.sh install [project-path] [--kmp] [--junit4] [--module :path]`, and changes Gradle files, `.mutation-testing/`, `buildSrc/`, and both native client adapters.
  Run it only when the user explicitly asks for setup.
- `--kmp` is setup-only; this toolkit validates the KMP JVM mutation task.
  The `bootstrap.sh install` command supports a conventional `gradle/libs.versions.toml` Kotlin
  plugin alias and a selected module using its default directory mapping.
- `--junit4` is setup-only and selects MutFlow's JUnit 4 runner for a plain
  Kotlin/JVM module. The default is JUnit 6; KMP JVM uses MutFlow's generated
  JUnit 6 integration. Select one adapter per module.
- Supported execution includes plain JVM/JUnit 4, plain JVM/JUnit 6, and KMP
  JVM when every declared KMP target can resolve MutFlow's common-source-set
  dependencies. In the validated MutFlow `1.6.1` baseline, artifacts publish
  JVM, `linuxX64`, and `mingwX64`, but not iOS or Android Native variants;
  selecting only the JVM task does not avoid dependency resolution. The toolkit
  does not prune unsupported targets or provide Native, Android, and JS
  execution adapters.
- Plain JVM/JUnit 4 test classes use `@RunWith(MutFlowRunner::class)` from
  `io.github.anschnapp.mutflow.junit4`; do not add the JUnit 6 `@MutFlowTest`
  annotation to those classes. KMP common tests remain plain `kotlin.test`.
- KMP common tests use plain `kotlin.test`; configure DSL `maxMutationRuns`
  as 10/30/`Int.MAX_VALUE` for quick/standard/deep, without counting baseline.
- Require schema 2 JSON with class-qualified identities, discovered/evaluated/
  untested totals, and null scores for gaps. Never reuse a report left by an
  earlier invocation after compilation or discovery failure.

Setup and update require Python 3.10 or newer in the toolkit checkout. To
update an existing installation, run `"/absolute/toolkit/bootstrap.sh"
update "/absolute/target" --dry-run` from a fast-forwarded checkout. Apply with
the same root command after reviewing the preview; conflicts are preserved unless
a reviewed file is named with `--force`. A valid `.mutation-testing/manifest.json`
is required; an absent manifest stops the update before writing.

If the Copilot agent profiles are unavailable, report that limitation rather than
falling back to OMP-specific dispatch. Preserve existing user changes and present
the affected paths and diffs in the final report.

The `mutationResults` task prints and writes a human-readable Markdown summary in
addition to schema 2 JSON. In GitHub Actions, it also appends the summary table
to the workflow run's job summary when `GITHUB_STEP_SUMMARY` is available.
