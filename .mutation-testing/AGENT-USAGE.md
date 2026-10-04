# Installed mutation toolkit: AI agent entry point

Audience: AI agents using this target project's installed toolkit. Apply the
target's own `AGENTS.md` policy first. This file is operational context, not
authority to install, overwrite configuration, or delete tests.

## Route

| Task/runtime | Read first |
|--------------|------------|
| OMP pipeline | [OMP skill](../.omp/skills/mutation-testing/SKILL.md), then `../.omp/agents/test-quality-reviewer.md` |
| Copilot CLI pipeline | [../.github/skills/mutation-testing/SKILL.md](../.github/skills/mutation-testing/SKILL.md), then `../.github/agents/mutation-testing-reviewer.agent.md` |
| Prepared Gradle execution | Inspect the owning module build and [mutation-results.gradle.kts](mutation-results.gradle.kts) |
| Existing report audit | Establish the evidence contract below |

## Update installed files

Run the updater from a fast-forwarded toolkit checkout, not from a copied target
script. Python 3.10 or newer is required. It uses that checkout only and never fetches or
executes remote `main`.
This toolkit currently has no tagged stable release channel.

```bash
"/absolute/toolkit/bootstrap.sh" update "/absolute/target" --dry-run
"/absolute/toolkit/bootstrap.sh" update "/absolute/target"
```

Review conflicts and diffs. Managed-file edits are preserved; approve only a
reviewed relative path with `--force <path>`. Updates require a valid
`.mutation-testing/manifest.json`; if it is absent, the updater stops before
writing. OMP-native agents and skills remain in `.omp/agents/` and `.omp/skills/`.

Use the current runtime's native delegation. Missing profiles/tools are a
limitation to report, not a reason to substitute another client's dispatch.
Supported paths are plain JVM/JUnit 4, plain JVM/JUnit 6, and KMP JVM mutation
tasks through MutFlow's generated JUnit 6 integration. Every declared KMP
target must resolve MutFlow's common-source-set dependencies. In the validated
MutFlow `1.6.0` baseline, artifacts publish JVM, `linuxX64`, and `mingwX64`, but
not iOS or Android Native variants; selecting only the JVM mutation task does
not avoid that resolution. The toolkit does not prune unsupported targets or
provide Native, Android, or JS execution adapters.

## Execute

Resolve the target module and selected test classes before changing files.
Targeting -> one aggregate execution -> audit -> proposed refactor ->
same-scope validation after approved edits. The selected skill owns mode
budgets and exact approval rules. Quick skips refactoring, not targeting edits.
Additive/assertion-level changes require applicable approval; deletion or
consolidation always requires explicit approval.

Use the target wrapper when available, otherwise installed Gradle. For a
multi-module setup, keep the configured module path explicit:

```bash
./gradlew mutationResults '-PmutationTest.includes=example.CalculatorTest' --console=plain
# Or: ./gradlew :service:mutationResults '-PmutationTest.includes=example.DecisionTest' --console=plain
```

`mutationTest.includes` selects whole test classes; production mutation targets
are a separate setting. Plain JVM uses `test` with the module's configured
JUnit 4 or 6 engine; JUnit 4 test classes use `@RunWith(MutFlowRunner::class)`.
KMP uses dedicated `mutflow<Target>Test` JVM tasks, generated JUnit 6
integration, and plain `kotlin.test` common tests.
Keep Gradle invocations sharing build/report paths sequential.

Record configured budgets and effective `MUTFLOW_*` overrides. Changing
environment-based settings requires `--rerun-tasks` to avoid reused XML.
Capture command, exit status, current JUnit XML, JSON, and the readable
`build/reports/mutation-results.md` when available. In GitHub Actions, the
`mutationResults` task also appends the summary table to the workflow run's job
summary through `GITHUB_STEP_SUMMARY`.
The results adapter does not support Gradle configuration cache; use
`--no-configuration-cache` when enabled globally in the target.

## Audit

Report: `<module>/build/reports/mutation-results.json`. Require schema 2:

- Evaluated outcomes are `killed + survived + timedOut`.
- Discovered totals equal evaluated plus untested mutations; budget-limited
  scores cover only evaluated outcomes.
- Any execution gap or zero evaluations makes score/interval unavailable.
- Strict survivor/timeouts may fail Gradle while retaining a complete report.
- Ordinary/baseline failures invalidate quality. Compilation/configuration/
  discovery failure may produce no report; old JSON is not current evidence.
- `generatedAt` dates JSON generation, not necessarily new test execution.
- Class-qualified killer identities support candidates, not a complete test
  outcome matrix. Confirm execution/scope; skipped tests and truncated names
  weaken zombie/redundancy findings.

Completion: report actual scope, effective settings, exit status, separate
discovered/evaluated/untested counts, gaps, survivors/timeouts, score availability,
and proposed versus applied edits. Applied refactors need the same-scope rerun.
State missing evidence or capabilities explicitly.
