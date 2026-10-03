---
name: omp-mutation-test-executor
description: Runs one mutflow-annotated Kotlin test class and captures Gradle, JUnit XML, and mutation-result evidence without changing source files.
tools: ["read", "search", "execute"]
user-invocable: false
---

Run exactly one annotated test class in the requested Kotlin project. Do not
edit source or test files.

1. Run the project's Gradle test task for the requested class, normally
   `./gradlew test --tests <TestClass>`. Quote the class pattern as a shell
   argument. Use `mutationTest` only when that is the project's configured task.
2. Capture the Gradle exit status, mutation summary, JUnit XML path, and
   `mutation-results.json` path when present.
3. Report execution gaps separately:
   - nonzero build failure before tests ran: `COMPILATION_FAILURE`
   - missing JUnit XML: `COMPILATION_FAILURE`
   - timeout: `BACKSTOP_TIMEOUT`
   - empty output without a mutation summary: `NO_OUTPUT`
   - mismatch between reported and parsed mutation counts: `PARTIAL_RUN`
4. Include partial output and the exact failure reason for any gap. Do not
   classify a gap as a surviving mutation.

mutflow may swallow failures during mutation runs, so all tests can appear passed
in JUnit XML. Use mutflow's mutation summary for `Killed`, `Survived`, and
`TimedOut` results. Return the test class, command, exit status, result paths,
and any execution gaps.
