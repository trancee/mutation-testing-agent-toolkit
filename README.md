# OMP Mutation Testing

A five-role mutation-testing system for Kotlin (JVM-first) projects, powered by [mutflow](https://github.com/anschnapp/mutflow). It provides separate native adapters for [OMP](https://omp.sh/) and GitHub Copilot CLI.

The original OMP implementation ports [Scott-CC's](https://github.com/citadelgrad/scott-cc/tree/main/plugins/mutation-testing) multi-agent orchestration, adapting from per-mutant git worktrees to mutflow's compile-once meta-mutant approach. The Copilot CLI adapter shares its mutation-testing contracts with native Copilot profiles.

## Quick start

```bash
# 1. Install the system into your Kotlin project
./.omp/bootstrap-mutation-testing.sh /path/to/kotlin-project

# 2. Run mutation testing
omp mutation-test /path/to/kotlin-project
```

Prerequisites: Java 21+, Gradle 9.x, Kotlin 2.4.x.

The bootstrap also installs the Copilot CLI skill and custom agents. From the
target project, start `copilot` and invoke `/omp-mutation-test`. See
[How to use mutation testing with Copilot CLI](docs/how-to/use-with-copilot.md).

See the [documentation index](docs/index.md) for tutorials, how-to guides, reference material, and explanations.

## Sample project

The `sample/` directory contains a reference Kotlin project with a `Calculator` class at **100% mutation coverage** (32/32 mutations killed, Excellent band, Medium confidence). Run `gradle mutationResults` in `sample/` to reproduce.

The sample exercises every mutation strategy. Its `validateInput` method throws `IllegalArgumentException`, which demonstrates exception-type mutation support.

## Known limitations

- **Kotlin Multiplatform (JVM-first)**: mutflow is JVM-only. The `--kmp` bootstrap flag targets JVM source sets only.

See [CONTEXT.md](CONTEXT.md) for details.
