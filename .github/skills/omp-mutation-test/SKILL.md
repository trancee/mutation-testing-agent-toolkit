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
/omp-mutation-test [project path] [--targets <pattern>] [--focus <patterns>] [--auto-approve] [--mode quick|standard|deep]
/omp-mutation-test setup [project path] [--kmp]
```

- `--targets` selects test classes; by default, include all `@MutFlowTest` classes.
- `--focus` narrows Gradle test targets.
- `--mode quick` runs at most 10 mutations and skips refactoring.
- `--mode standard` runs at most 30 mutations and includes refactoring suggestions.
- `--mode deep` runs all available mutations and includes detailed killer matrices.
- `--auto-approve` permits applying proposed test refactors; it never permits deleting
  zombie tests or redundant groups without explicit user approval.
- `setup` runs the bootstrap script and changes the target project's Gradle, `.omp`,
  `buildSrc`, and Copilot configuration. Run it only when the user explicitly asks
  for setup.
- `--kmp` is setup-only; mutflow currently targets JVM source sets.

If the Copilot agent profiles are unavailable, report that limitation rather than
falling back to OMP-specific dispatch. Preserve existing user changes and present
the affected paths and diffs in the final report.
