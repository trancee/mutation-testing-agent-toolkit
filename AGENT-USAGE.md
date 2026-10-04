# Toolkit usage for AI agents

Audience: AI agents operating this repository or using its checkout to configure
a target project. Entry point: root [AGENTS.md](AGENTS.md). This is an execution
guide, not a human tutorial or an installed client skill. Bootstrap installs a
target-specific [.omp/AGENT-USAGE.md](.omp/AGENT-USAGE.md) and appends its
discovery pointer to the target's `AGENTS.md`, preserving existing policy.
Repository policy
remains in `AGENTS.md`; domain terms remain in [CONTEXT.md](CONTEXT.md).

## 1. Route the request

| Request | Action |
|---------|--------|
| Install into a target project | Follow section 2 only with explicit setup approval |
| Run the five-role pipeline | Load the matching native skill in section 3 |
| Execute prepared tests without a client | Follow section 4 |
| Audit existing results | Check evidence in section 5 before assigning a score |
| Diagnose a failed run | Classify exit/report state in section 5, then inspect the first failing boundary |
| Change toolkit code or dependencies | Follow section 6 and repository policy |

Resolve the toolkit checkout and target module separately. Scope writes and
commands to the approved target; inspect its instructions and existing changes.
Supported execution: plain Kotlin JVM with JUnit 4 or JUnit 6, and KMP JVM
mutation tasks through MutFlow's generated JUnit 6 integration. Every declared
KMP target must also resolve MutFlow's common-source-set dependencies. In the
validated MutFlow `1.6.0` baseline, the artifacts publish JVM, `linuxX64`, and
`mingwX64`, but not iOS or Android Native variants; selecting only the JVM
mutation task does not avoid that resolution. The toolkit does not prune
unsupported targets or provide Native, Android, or JS execution adapters.

**Ready:** request, client, target module, setup authority, and supported
execution path are explicit. Report unsupported or missing capabilities.

## 2. Install

Inspect [the installer](.omp/bootstrap-mutation-testing.sh) before executing it:

```bash
bash "/absolute/toolkit/.omp/bootstrap-mutation-testing.sh" "/absolute/target"
# For a KMP JVM module, select its Gradle path, for example:
bash "/absolute/toolkit/.omp/bootstrap-mutation-testing.sh" "/absolute/target" --kmp --module :module
# For a plain JVM project that uses JUnit 4:
bash "/absolute/toolkit/.omp/bootstrap-mutation-testing.sh" "/absolute/target" --junit4
```

Preflight: compatible Kotlin plugin pin (direct or through the default
`gradle/libs.versions.toml` plugin alias), conventional multiline `plugins`
block, matching JVM/KMP mode, a conventional module-directory mapping, and no
conflicting user-owned `buildSrc`, legacy namespace, or Copilot files. Use the
installer's actual checked pins; the canonical plugin pins live in
[sample/build.gradle.kts](sample/build.gradle.kts). `--junit4` is for plain
JVM only; KMP JVM uses the generated JUnit 6 integration.
Inspect existing `pluginManagement` for Maven Central: bootstrap preserves an
existing block without repairing its repositories.

Installation copies toolkit files to the project root, edits the selected
module's build and the root `buildSrc`, preserves existing `.bak` files, and
does not itself annotate sources.
For custom builds or an upgrade, merge toolkit-owned files explicitly while
preserving convention code. Legacy `io.omp.mutation` sources, current
`ch.trancee.mutation` sources, the results script, and schema consumers require
a coordinated migration.

**Installed:** setup exits zero, the expected client files and typed module
exist, and build configuration resolves. A preflight conflict is a stop, not
permission to overwrite customizations.

## 3. Use native client orchestration

| Runtime | Load | Reviewer dispatch |
|---------|------|-------------------|
| OMP | [.omp/skills/mutation-testing/SKILL.md](.omp/skills/mutation-testing/SKILL.md) | `test-quality-reviewer` through OMP `task`/`hub` |
| Copilot CLI | [.github/skills/mutation-testing/SKILL.md](.github/skills/mutation-testing/SKILL.md) | `mutation-testing-reviewer` through native `agent` |

Load the selected skill and its reviewer profile; they own exact role prompts,
mode budgets, and approval behavior. Keep client dispatch native. If profiles
or delegation tools are unavailable, report that limitation.

Handoff order: targeting -> one aggregate execution -> audit -> proposed
refactor -> same-scope validation after approved edits. Quick skips refactoring.
`--targets` selects test classes, not production mutation targets.
`--auto-approve` permits additive/assertion-level refactors; test deletion or
consolidation still needs explicit approval. Quick runs can still edit targeting
configuration. Preserve the original tests' behavioral contracts.

**Delegated:** every phase has returned evidence; proposals and applied changes
are distinguished. Static profile checks are not proof of live client execution.

## 4. Execute prepared tests

Inspect the target build for the task/module and use its wrapper when present:

```bash
./gradlew :service:mutationResults '-PmutationTest.includes=example.OrderTest,example.PriceTest' --console=plain
```

For a standalone module use `mutationResults` without `:service:`. A
multi-module setup selected with `--module :service` runs
`:service:mutationResults`. Without a wrapper use its installed `gradle`; this
toolkit checkout has no wrapper. Run one aggregate invocation, not competing
per-class Gradle processes sharing build/report paths. Plain JVM selects `test`
with its configured JUnit 4 or 6 engine; KMP selects dedicated
`mutflow<Target>Test` JVM tasks, not ordinary `jvmTest`.

Check effective `MUTFLOW_*` overrides and configured mutation budgets.
Environment changes require `--rerun-tasks` to avoid reusing XML from another
verification/budget setting. A JSON timestamp is not a test-execution timestamp.
The task prints a human-readable summary and writes
`build/reports/mutation-results.md`; GitHub Actions runs also append it to the
workflow job summary when `GITHUB_STEP_SUMMARY` is available.
For full-scope evidence, require zero untested mutations as well as zero gaps.

**Executed:** capture command, effective overrides/budget, exit status, current
JUnit XML under the owning module's `build/test-results/`, JSON, and Markdown
summary when present.

## 5. Audit and classify evidence

Read `<module>/build/reports/mutation-results.json` only as current-run evidence.
Contract owners: [MutationResults.kt](.omp/mutation-results-src/main/kotlin/ch/trancee/mutation/MutationResults.kt),
[the XML reader](.omp/mutation-results-src/main/kotlin/ch/trancee/mutation/JUnitMutationReport.kt),
and [the results task](.omp/mutation-results.gradle.kts).

| Evidence | Interpretation |
|----------|----------------|
| `schemaVersion != 2` or absent | Legacy/unsupported contract; migrate before schema 2 analysis |
| Recorded outcomes | `mutationsEvaluated = killed + survived + timedOut` |
| Budget-limited run | `totalMutations = mutationsEvaluated + untestedMutations`; score covers evaluated outcomes only |
| Any execution gap or zero evaluations | Score and Wilson interval unavailable; gaps never subtract recorded outcomes |
| Nonzero exit, survivors/timeouts, current JSON without gaps | Recorded mutation outcomes; strict failures do not imply incomplete reporting |
| Ordinary/baseline failure or inconsistent/missing summary | Gap; aggregate quality is not valid |
| Configuration/compilation/discovery failure, missing current JSON | Report failure and unavailable evidence; retained old JSON is not a fallback |

Confirm class-qualified identities, actual execution, and mutation scope before
reporting zombie candidates. Killer data omits complete per-test outcome
history; skipped tests and truncated names weaken conclusions. Redundant groups
are review candidates, not deletion authority. Diagnose the first error rather
than weakening assertions, suppressing business logic, or guessing a score.

**Audited:** report scope, exit status, discovered/evaluated/untested counts,
gap types, score availability, survivors/timeouts, identity limitations, and
proposed versus applied changes. Validation after an applied refactor uses the
same selection and effective settings.

## 6. Maintain the toolkit

Canonical results sources/tests: `.omp/mutation-results-src/`.
Generated copies: `sample/buildSrc/src/`. Preserve byte parity. Contract changes
also affect both client skills/profiles, bootstrap, sample, and documentation.
Use [CI](.github/workflows/ci.yml) for the exact authoritative gate sequence:

```bash
gradle -p sample/buildSrc test --rerun-tasks
python3 scripts/test-mutflow-integration.py
python3 scripts/test-documentation-examples.py
bash scripts/test-bootstrap-copilot.sh
python3 scripts/test-upstream-check.py
python3 scripts/check-copilot-agent-profiles.py
python3 scripts/check-mutation-agent-contracts.py
python3 scripts/check-upstream.py --offline
./scripts/check-markdown.sh --offline
```

For dependency work, run `python3 scripts/check-upstream.py` online. Stable
release drift, compiler mismatch, unreleased upstream changes, and network
failures are visible review signals; use latest compatible stable releases,
not snapshots. Inspect [the scheduled monitor](.github/workflows/upstream-sync.yml)
and [Dependabot](.github/dependabot.yml) for automation ownership.

**Verified:** changed behavior and applicable CI gates pass, source copies are
synchronized, limitations are disclosed, and external actions have explicit
approval. The results adapter currently fails configuration-cache storage
because `prepareMutationResults` captures script references; use
`--no-configuration-cache` if enabled globally. Fresh live agent orchestration
is not established by real Gradle integration tests.
