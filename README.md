# Mutation Testing Agent Toolkit

A five-role mutation-testing toolkit for Kotlin (JVM-first) projects, powered by [mutflow](https://github.com/anschnapp/mutflow). It currently provides native adapters for [OMP](https://omp.sh/) and GitHub Copilot CLI, with shared mutation-testing contracts across clients.

**AI agents:** start with [AGENTS.md](AGENTS.md) and its
[agent-only usage guide](AGENT-USAGE.md), rather than the human tutorials below.

The toolkit adapts the five-role orchestration and test-quality workflow from [Scott-CC's mutation-testing plugin](https://github.com/citadelgrad/scott-cc/tree/main/plugins/mutation-testing). It is not feature- or behavior-equivalent: this Kotlin toolkit replaces Scott-CC's LLM-generated, per-mutant Git-worktree mutations with mutflow's predefined operators and test-only compilation. See [how the designs differ](docs/adr/0002-agent-structure-and-orchestration-model.md#adaptation-boundaries).

## Quick start

Clone this repository and run the installer from its root. The target project
must use an explicit Kotlin `2.4.20` plugin pin and a conventional multiline
`plugins` block. For version catalogs, existing convention builds, or migration,
use [manual setup](docs/how-to/manual-setup.md).

```bash
git clone https://github.com/trancee/mutation-testing-agent-toolkit.git
cd mutation-testing-agent-toolkit

# Install into a separate Kotlin JVM project
./.omp/bootstrap-mutation-testing.sh /path/to/kotlin-project
```

Validated with Java `26`, Gradle `9.8.0`, Kotlin `2.4.20`, and mutflow `1.6.0`.
For KMP JVM projects, append `--kmp`; see [KMP setup](docs/how-to/manual-setup.md#configure-kmp-jvm-projects).

The installer configures Gradle and installs both client adapters; it does not
annotate your sources. Choose your client from the target project:

| Client | Entry point |
|--------|-------------|
| OMP | `/mutation-testing` in OMP, or `omp mutation-testing /path/to/kotlin-project` |
| GitHub Copilot CLI | Start `copilot` and invoke `/mutation-testing` |

The agents select targets and prepare tests before running Gradle. See
[How to use mutation testing with Copilot CLI](docs/how-to/use-with-copilot.md).
Neither client is required to run an already-prepared suite:

```bash
gradle -p /path/to/kotlin-project mutationResults
```

Read `build/reports/mutation-results.json` in the target project. Strict
survivors and timeouts return a failing exit status even when the report is
complete; see [interpreting results](docs/how-to/interpret-results.md).

See the [documentation index](docs/index.md) for tutorials, how-to guides, reference material, and explanations.
Start with [your first mutation test](docs/tutorials/first-mutation-test.md),
then follow the [agent-assisted workflow](docs/tutorials/agent-assisted-mutation-test.md)
or [KMP JVM tutorial](docs/tutorials/kmp-jvm-mutation-test.md).
For failed or incomplete runs, use [troubleshooting](docs/how-to/troubleshoot-mutation-testing.md).

## Sample project

The `sample/` directory contains a reference Kotlin project with a `Calculator`
class: **32/32 mutations killed** (100% score, Excellent band, Medium
confidence). This is a result for the selected operators, not proof of complete
behavioral coverage. Reproduce it from the repository root:

```bash
gradle -p sample mutationResults
```

The sample exercises boundary, boolean, arithmetic, return-value, and
exception-type categories, not every operator in upstream's catalog.

## Maintenance and contribution

Use [the repository checks](docs/how-to/run-checks.md) before proposing changes.
The daily upstream monitor reports stable-release, compiler-compatibility, and
source drift; Dependabot proposes updates, but neither automatically makes an
incompatible upgrade. Contributor rules, including Conventional Commits, are
in [AGENTS.md](AGENTS.md).

## Known limitations

- **Kotlin Multiplatform (JVM-first)**: `--kmp` installs the toolkit's JVM mutation-task adapter. Upstream also supports Native and JUnit 4; those adapters are not validated here.
- **Setup scope**: the installer supports conventional Kotlin DSL module builds,
  not automatic migration of arbitrary version catalogs or multi-module layouts.
- **Results migration**: existing `io.omp.mutation` installations and schema 1
  consumers need the [coordinated migration](docs/how-to/manual-setup.md#upgrade-an-existing-installation).
- **Gradle configuration cache**: unsupported by the current results adapter;
  use `--no-configuration-cache` when the target enables it globally.
- **Test-quality findings**: killer data supports zombie/redundancy candidates,
  not proof that a test can safely be deleted.

See the [command reference](docs/reference/mutation-testing-command.md) for modes
and constraints, and [CONTEXT.md](CONTEXT.md) for domain terminology.
