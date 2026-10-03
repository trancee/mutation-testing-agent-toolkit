# ADR-001: Use mutflow as the mutation testing engine

- **Date**: 2026-08-22
- **Status**: Accepted
- **Decision Maker**: Grilling session (D1-D4 wayfinder tickets)

## Context

We need to choose a mutation testing engine for Kotlin (JVM-first) projects that:

1. Integrates with Kotlin/JVM via a compiler plugin
2. Supports JUnit 6
3. Can inject mutations during test compilation
4. Provides a mutation score calculation

Three candidates were evaluated:

- **mutflow** (https://github.com/anschnapp/mutflow): Kotlin compiler plugin that instruments test compilation while keeping production artifacts clean. JUnit 6 native via `@MutFlowTest`.
- **mutant-kraken** (Rust CLI): Standalone CLI with 5 stages. Operators include Arithmetic, Unary, Logical, Relational, etc. Beta quality (30 GitHub stars).
- **pitest/Arcmutate**: Java-first mutation testing via Maven/Gradle. Arcmutate extends with Kotlin/Spring/Git support. Fast for Java but KMP pain.

## Decision

Use **mutflow** as the mutation engine.

## Rationale

- **Kotlin-first**: mutflow is a native Kotlin compiler plugin — no Java interoperability layer needed
- **JUnit 6 native**: `@MutFlowTest` + `MutFlow.underTest { }` API is idiomatic Kotlin
- **Test-only mutation compilation**: Mutations are injected during test compilation, keeping production artifacts free of mutation code and eliminating per-mutant git worktrees.
- **Operator categories**: mutflow has predefined operators that map broadly to Scott-CC's boundary, return-value, boolean, arithmetic, and exception categories. This is a category mapping, not feature or behavioral parity; mutflow does not generate arbitrary context-aware return-value mutations.
- **Active maintenance**: mutflow tracks the current Kotlin compiler release; the plugin and Kotlin versions must match.

## Consequences

### Positive

- No git worktree management — mutflow isolates mutation instrumentation to test compilation
- Simpler orchestration: one aggregate Gradle invocation for selected test classes, not one process per mutant
- Fast iteration: a single instrumented test compilation covers all mutations
- Per-mutation killer evidence: mutflow records the tests that killed each mutation (`MutationResult.Killed(testNames: Set<String>)`), enabling zombie-candidate analysis. It does not provide every test's outcome for every mutation, so a missing killer entry is not proof that a test is unnecessary.

### Negative

- Non-JVM targets: Kotlin Multiplatform projects can mutate JVM source sets only. Kotlin/JS and Kotlin/Native are unsupported. Supporting them requires changes to the Gradle and compiler plugins.
- No LLM-guided mutations: all operators are predefined and static. LLM serves as targeting specialist (suppression annotations), not as a mutation generator
- Per-JVM synchronized lock: one active mutation session runs at a time inside each JVM.

### Current engine baseline

The toolkit validates against mutflow 1.6.0, Kotlin 2.4.20, Gradle 9.8.0, and
Java 26. Kotlin 2.4.20 does not yet support Java 27 bytecode targets, so Java
26 is the latest compatible toolchain baseline. mutflow versions are
compiler-coupled; update the Kotlin plugin and mutflow plugin together to their
latest compatible stable releases. The
maintained architecture description is in
[About mutflow's test-only mutation compilation](../explanation/mutflow-architecture.md).

## Alternatives considered

- **mutant-kraken**: Rejected — Rust CLI with less Kotlin-specific support, beta quality (30 stars vs mutflow's active development)
- **pitest/Arcmutate**: Rejected — Java-first engine; KMP support via Arcmutate is an add-on, adds complexity
- **Building a custom engine**: Rejected — significant engineering effort, reinvention of proven approaches

## Tags

- engine
- kotlin
- jvm
