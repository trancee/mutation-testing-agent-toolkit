# About the mutation-testing agent system

The mutation-testing pipeline separates source targeting, execution, analysis, and test improvement. A fifth agent coordinates those four responsibilities.

## Why the work is separated

Mutation testing combines two kinds of authority that should not sit in one agent. Some steps change production and test sources. Other steps judge the resulting test quality. Separate agents keep those decisions reviewable and allow each role to operate with narrower permissions.

The roles are:

- The reviewer coordinates the run and combines the findings.
- The saboteur identifies business logic and configures mutflow annotations.
- Executors run annotated test classes and capture their results.
- The auditor calculates metrics and identifies weak tests.
- The refactor specialist proposes or applies test improvements within the approval rules.

The exact dispatch keys, inputs, outputs, and declared tools are listed in the [mutation-testing agent reference](../agents/mutation-testing-agents.md).

## How work moves through the pipeline

The OMP `/mutation-test` skill sends the project and command options to the OMP
reviewer. The Copilot CLI `/omp-mutation-test` skill sends the same contract to
the Copilot reviewer. Each reviewer then coordinates four phases:

1. The saboteur selects mutation targets, applies the mode budget, and prepares their tests.
2. One executor runs the selected test classes together and collects aggregate mutflow output.
3. The auditor turns those results into scores, execution gaps, survivor lists, and test-quality findings.
4. The refactor specialist uses the audit to propose stronger tests.

This division keeps each handoff explicit. Executors receive prepared source. The auditor receives completed runs. The refactor specialist receives interpreted findings rather than raw logs.

## Why the order is fixed

mutflow discovers mutation points during a baseline run before it activates individual variants. That engine constraint fixes the central sequence.

The saboteur must finish first because mutflow relies on `@MutationTarget`, `@MutFlowTest`, and `MutFlow.underTest`. Executors must finish before the auditor can calculate a complete score. The refactor specialist must wait for the audit because surviving mutations and zombie candidates determine which tests need attention.

## Executor dispatch

Each reviewer dispatches one executor for a single aggregate Gradle invocation
covering the selected test classes. The results task reads JUnit XML from that
same invocation and emits one JSON report. Competing Gradle processes would
share build and JUnit result paths; mutflow's session guard is JVM-local
and cannot protect separate Gradle processes. KMP selects dedicated JVM
mutation tasks rather than ordinary `jvmTest`.

## Why approval remains separate

The refactor specialist may apply additive or assertion-level test changes when
`--auto-approve` is present. Deleting or consolidating tests always requires
explicit approval. After any applied change, the reviewer reruns the same
aggregate mutation task and reports whether validation passed. This boundary
keeps quality heuristics from removing tests and prevents unverified changes
from being presented as successful.

## Client-specific adapters

OMP keeps its profiles in `.omp/agents/` and dispatches them with `task` and
`hub`. Copilot CLI uses `.github/agents/` profiles and delegates through its
native `agent` tool. The OMP and Copilot skill entry points are separate because
their orchestration tools and profile formats differ; both retain the same
targeting, execution, audit, refactor, and approval contracts.

For the engine model behind these constraints, see [About mutflow's test-only mutation compilation](mutflow-architecture.md). For the orchestration design and alternatives, see [ADR-002](../adr/0002-agent-structure-and-orchestration-model.md). For the Copilot adapter, see [ADR-003](../adr/0003-copilot-cli-adapter.md).
