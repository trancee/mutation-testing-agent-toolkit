# About the OMP 5-agent mutation testing system

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

1. The saboteur selects mutation targets and prepares their tests.
2. Executors run the prepared test classes and collect mutflow output.
3. The auditor turns those results into scores, execution gaps, survivor lists, and test-quality findings.
4. The refactor specialist uses the audit to propose stronger tests.

This division keeps each handoff explicit. Executors receive prepared source. The auditor receives completed runs. The refactor specialist receives interpreted findings rather than raw logs.

## Why the order is fixed

mutflow discovers mutation points during a baseline run before it activates individual variants. That engine constraint fixes the central sequence.

The saboteur must finish first because mutflow relies on `@MutationTarget`, `@MutFlowTest`, and `MutFlow.underTest`. Executors must finish before the auditor can calculate a complete score. The refactor specialist must wait for the audit because surviving mutations and zombie candidates determine which tests need attention.

## Why executor dispatch is parallel

The reviewer dispatches one executor per annotated test class in a single task batch. This lets the orchestration layer prepare independent work together. Each executor still runs its baseline before that class's mutation variants, so dispatch concurrency does not change the required per-class ordering.

## Why approval remains separate

The refactor specialist may write approved test refactors when `--auto-approve` is present. Deleting zombie tests or redundant groups always requires explicit approval. This boundary prevents a quality heuristic from removing tests without a human decision.

## Client-specific adapters

OMP keeps its profiles in `.omp/agents/` and dispatches them with `task` and
`hub`. Copilot CLI uses `.github/agents/` profiles and delegates through its
native `agent` tool. The OMP and Copilot skill entry points are separate because
their orchestration tools and profile formats differ; both retain the same
targeting, execution, audit, refactor, and approval contracts.

For the engine model behind these constraints, see [About mutflow's compile-once meta-mutant architecture](mutflow-architecture.md). For the OMP design and alternatives, see [ADR-002](../adr/0002-agent-structure-and-orchestration-model.md). For the Copilot adapter, see [ADR-003](../adr/0003-copilot-cli-adapter.md).
