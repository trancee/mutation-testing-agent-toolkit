# About mutflow's test-only mutation compilation

mutflow instruments test compilation so mutation code is present in test runs
without changing production artifacts. This keeps mutation testing integrated
with the normal Gradle test task while avoiding compilation once per mutation.

## Production and test compilation

The Kotlin compiler produces the ordinary production artifact without mutation
instrumentation. During test compilation, mutflow transforms targeted
production logic into guarded variants and includes those variants in the
instrumented test artifact.

```text
Production source
    │
    ▼
Production compilation ───────────────► clean production artifact
    │
    ▼
Test compilation with mutflow
    │  discovers and injects guarded mutation variants
    ▼
Instrumented test artifact
    │
    ├─ baseline run: no mutation active
    ├─ mutation run: activate variant 1
    ├─ mutation run: activate variant 2
    └─ ...
```

The instrumented artifact contains the available variants, while each mutation
run activates one variant. The run records whether tests kill, survive, or time
out that mutation.

## Implications for the toolkit

1. **Production artifacts stay clean.** Mutation instrumentation is applied for
   test compilation rather than shipped with production output.
2. **No per-mutation builds or worktrees are required.** The test artifact
   includes the mutation variants, and the test extension selects variants for
   mutation runs.
3. **JUnit orchestrates the test runs.** `@MutFlowTest` supplies the test
   integration, and `MutFlow.underTest { }` marks the code whose mutations are
   activated.
4. **Do not overlap sessions within a JVM.** Upstream guards overlapping sessions;
   separate test JVMs are independent. The toolkit uses one aggregate Gradle
   invocation rather than competing processes sharing output directories.
5. **The results task reads test reports.** The toolkit's `mutationResults`
   task captures mutflow output from JUnit XML and serializes mutation results,
   gaps, per-test killer data, and redundant groups.

Plain JVM uses `test`; KMP JVM uses dedicated `mutflow<Target>Test` tasks,
with compiler-synthesized annotations on common tests. Upstream additionally
supports Kotlin/Native and JUnit 4. Those engines are not yet toolkit adapters.

The schema 2 results task declares its XML inputs, so changed tests and filters
invalidate cached JSON. A repeated invocation can reuse up-to-date test XML and
regenerate JSON; a fresh `generatedAt` is the report-generation timestamp, not
proof that tests executed again. Environment-based mutation overrides require
an explicit rerun when they change. It collects test failures before restoring a failing
Gradle exit status; baseline failures invalidate aggregate scores, whereas
strict survivors and mutation timeouts remain recorded mutation outcomes.
Compilation or discovery failures may prevent report generation, so executors
must not reuse a report from a prior invocation.

Killer data identifies the tests that caught each recorded mutation, not every
test's verdict. Class qualification prevents cross-class display-name
collisions, but upstream can truncate long names in its console summary. This
limits how confidently an auditor can match killer names to XML identities.

For agent responsibilities and phase ordering, see [About the
mutation-testing agent system](agent-system.md). For the version decision and
current validated baseline, see [ADR-001](../adr/0001-use-mutflow-as-mutation-engine.md).
