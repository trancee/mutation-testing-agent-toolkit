# Documentation index

## Getting started

| Goal | Document |
|------|----------|
| Learn mutation testing from scratch | [Tutorial: Your first mutation test](tutorials/first-mutation-test.md) |
| Add mutation testing to an existing project | [Tutorial: Bootstrap an existing project](tutorials/bootstrap-existing-project.md) |
| Set up Gradle manually without the bootstrap script | [How-to: Manual Gradle setup](how-to/manual-setup.md) |
| Use the native GitHub Copilot CLI adapter | [How-to: Use mutation testing with Copilot CLI](how-to/use-with-copilot.md) |
| Run mutation testing in GitHub Actions | [How-to: Run mutation testing in GitHub Actions](how-to/run-in-github-actions.md) |

## Command reference

| Topic | Document |
|-------|----------|
| `mutation-test` arguments, options, and modes | [Reference: mutation-test command](reference/mutation-test-command.md) |

## Working with results

| Goal | Document |
|------|----------|
| Read the mutation summary and calculate your score | [How-to: Interpret mutation testing results](how-to/interpret-results.md) |
| Fix surviving mutations with boundary tests | [How-to: Fix surviving mutations](how-to/fix-surviving-mutations.md) |
| Understand the JSON output format | [Reference: mutation-results.json](reference/mutation-results-format.md) |

## Architecture

| Topic | Document |
|-------|----------|
| How mutflow's test-only mutation compilation works | [Explanation: mutflow architecture](explanation/mutflow-architecture.md) |
| How the 5 agents work together | [Explanation: Agent system architecture](explanation/agent-system.md) |
| Engine choice | [ADR-001](adr/0001-use-mutflow-as-mutation-engine.md) |
| Agent structure and orchestration | [ADR-002](adr/0002-agent-structure-and-orchestration-model.md) |
| Native GitHub Copilot CLI adapter | [ADR-003](adr/0003-copilot-cli-adapter.md) |

## Domain

| Topic | Document |
|-------|----------|
| Key concepts and glossary | [CONTEXT.md](../CONTEXT.md) |

## Agent contributor documentation

| Need | Document |
|------|----------|
| Look up mutation-testing agent contracts | [Reference: Mutation-testing agents](agents/mutation-testing-agents.md) |
| Work with the local Markdown issue tracker | [Reference: Local issue tracker](agents/issue-tracker.md) |
| Look up canonical triage roles | [Reference: Triage labels](agents/triage-labels.md) |
| Use domain context before changing code | [How-to: Use domain documentation](agents/domain.md) |

## Contributing

| Goal | Document |
|------|----------|
| Write documentation following the Diataxi framework | [How-to: Contribute documentation](how-to/contribute-documentation.md) |
| Run markdown lint and link checks | [How-to: Run documentation checks](how-to/run-checks.md) |
