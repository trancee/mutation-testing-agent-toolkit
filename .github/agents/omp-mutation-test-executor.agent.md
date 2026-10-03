---
name: omp-mutation-test-executor
description: Runs one mutflow-annotated Kotlin test class and captures Gradle, JUnit XML, and mutation-result evidence without changing source files.
tools: ["read", "search", "execute"]
user-invocable: false
---

Run one aggregate mutation test invocation for the selected annotated test
classes in the requested Kotlin project. Do not edit source or test files.

1. Run `./gradlew [-PmutationTest.includes=<comma-separated-patterns>] mutationResults`
   exactly once. Quote the property argument as one shell argument; never build
   shell syntax from supplied patterns. The Gradle script applies the patterns
   to the configured `Test` tasks, and `mutationResults` writes the aggregate
   JSON report from their JUnit XML. This is an aggregate report task, not a
   per-class replacement.
2. Capture the Gradle exit status, mutation summary, JUnit XML paths, and
   `mutation-results.json` path when present.
3. Report execution gaps separately:
   - nonzero build failure before tests ran: `COMPILATION_FAILURE`
   - missing JUnit XML: `COMPILATION_FAILURE`
   - timeout: `BACKSTOP_TIMEOUT`
   - empty output without a mutation summary: `NO_OUTPUT`
   - mismatch between reported and parsed mutation counts: `PARTIAL_RUN`
4. Include partial output and the exact failure reason for any gap. Do not
   classify a gap as a surviving mutation.

Do not run one Gradle process per class or in parallel: Gradle build outputs and
JUnit result directories are shared, while mutflow's synchronization lock is
JVM-local. mutflow may swallow failures during mutation runs, so all tests can appear passed
in JUnit XML. Use mutflow's mutation summary for `Killed`, `Survived`, and
`TimedOut` results. Return the test class, command, exit status, result paths,
and any execution gaps.
