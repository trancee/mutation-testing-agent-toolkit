# Toolkit usage for AI agents

Audience: AI agents operating this repository or using its checkout to configure
a target project. Entry point: root [AGENTS.md](AGENTS.md). This is an execution
guide, not a human tutorial or an installed client skill. Repository policy
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
Supported execution: plain Kotlin JVM/JUnit 6 and KMP JVM mutation tasks.
Native, JUnit 4/Android, and JS are not validated toolkit adapters.

**Ready:** request, client, target module, setup authority, and supported
execution path are explicit. Report unsupported or missing capabilities.

## 2. Install

Inspect [the installer](.omp/bootstrap-mutation-testing.sh) before executing it:

```bash
bash "/absolute/toolkit/.omp/bootstrap-mutation-testing.sh" "/absolute/target"
# For a KMP JVM module, append --kmp.
```

Preflight: explicit compatible Kotlin plugin pin, conventional multiline
`plugins` block, matching JVM/KMP mode, and no conflicting user-owned `buildSrc`,
legacy namespace, or Copilot files. Use the installer's actual checked pins;
the canonical plugin pins live in [sample/build.gradle.kts](sample/build.gradle.kts).
Inspect existing `pluginManagement` for Maven Central: bootstrap preserves an
existing block without repairing its repositories.

Installation copies Gradle/results and both client layers. It edits builds in
place, preserves existing `.bak` files, and does not itself annotate sources.
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
| OMP | [.omp/skills/mutation-test/SKILL.md](.omp/skills/mutation-test/SKILL.md) | `test-quality-reviewer` through OMP `task`/`hub` |
| Copilot CLI | [.github/skills/omp-mutation-test/SKILL.md](.github/skills/omp-mutation-test/SKILL.md) | `omp-mutation-test-reviewer` through native `agent` |

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

For a standalone module use `mutationResults` without `:service:`. Without a
wrapper use its installed `gradle`; this toolkit checkout has no wrapper.
Run one aggregate invocation, not competing per-class Gradle processes sharing
build/report paths. Plain JVM selects `test`; KMP selects dedicated
`mutflow<Target>Test` JVM tasks, not ordinary `jvmTest`.

Check effective `MUTFLOW_*` overrides and configured mutation budgets.
Environment changes require `--rerun-tasks` to avoid reusing XML from another
verification/budget setting. A JSON timestamp is not a test-execution timestamp.
For full-scope evidence, require zero untested mutations as well as zero gaps.

**Executed:** capture command, effective overrides/budget, exit status, current
JUnit XML under the owning module's `build/test-results/`, and JSON when present.

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
approval. Configuration-cache compatibility and fresh live agent orchestration
are not established by the real Gradle integration tests.
