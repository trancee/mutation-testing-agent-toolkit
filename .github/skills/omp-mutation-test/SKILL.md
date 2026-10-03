---
name: omp-mutation-test
description: Run, bootstrap, or analyze mutflow-powered mutation testing for Kotlin/JVM projects with the Mutation Testing Agent Toolkit's Copilot-native workflow. Use for explicit mutation-testing requests, not ordinary unit-test tasks.
compatibility: GitHub Copilot CLI with the project agents in .github/agents.
---

# Mutation testing in Copilot CLI

Use this skill as the Copilot CLI entry point. Delegate to the
`omp-mutation-test-reviewer` custom agent with Copilot's `agent` tool. Do not use
OMP's `task`, `hub`, or `tasks[]` interfaces.

```text
/omp-mutation-test [project path] [--targets <patterns>] [--auto-approve] [--mode quick|standard|deep]
/omp-mutation-test setup [project path] [--kmp]
```

- `--targets` selects Gradle test class patterns; by default, include all `@MutFlowTest` classes.
- `--mode quick` allows at most 10 mutation runs per selected class (`maxRuns=11`, including baseline) and skips refactoring.
- `--mode standard` allows at most 30 mutation runs per selected class (`maxRuns=31`, including baseline) and includes refactoring suggestions.
- `--mode deep` runs all available mutations per selected class and includes detailed killer data.
- `--auto-approve` permits applying proposed test refactors; it never permits deleting
  zombie tests or redundant groups without explicit user approval.
- `setup` runs the bootstrap script and changes the target project's Gradle, `.omp`,
  `buildSrc`, and Copilot configuration. Run it only when the user explicitly asks
  for setup.
- `--kmp` is setup-only; this toolkit validates KMP JVM mutation tasks.
  Upstream Native and JUnit 4 support is not implemented in the adapter.
- KMP common tests use plain `kotlin.test`; configure DSL `maxMutationRuns`
  as 10/30/`Int.MAX_VALUE` for quick/standard/deep, without counting baseline.
- Require schema 2 JSON with class-qualified identities, discovered/evaluated/
  untested totals, and null scores for gaps. Never reuse a report left by an
  earlier invocation after compilation or discovery failure.

If the Copilot agent profiles are unavailable, report that limitation rather than
falling back to OMP-specific dispatch. Preserve existing user changes and present
the affected paths and diffs in the final report.
