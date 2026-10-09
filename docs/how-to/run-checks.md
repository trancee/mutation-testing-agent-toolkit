# How to run repository checks

Use this guide to check documentation, client contracts, mutation integration,
and upstream alignment before proposing repository changes.

## Prerequisites

- **Node.js 26** for Markdown style checks
- **lychee** for internal and external link checks
- **Python 3** for adapter, integration, and upstream checks
- **Java 26 and Gradle 9.8.0** for Kotlin and real integration tests

## Toolchain compatibility

The integration suite uses Gradle `9.8.0`. Kotlin's compatibility table lists
Gradle `9.7.0` as the latest fully supported version for the Kotlin Gradle
plugin `2.4.21`. The repository passes on `9.8.0`, but that result does not
extend the plugin's documented support range. Check the
[Kotlin Gradle plugin compatibility table](https://kotlinlang.org/docs/gradle-configure-project.html#check-for-compatibility)
when choosing versions for another project.

### Install Node.js

Install Node.js 26 from [nodejs.org](https://nodejs.org/) or your version
manager. Verify the installation:

```bash
node --version
npx --version
```

### Install lychee

Install lychee with your package manager or follow the
[official installation instructions](https://github.com/lycheeverse/lychee#installation).

## Running the checks

### Check a single file

```bash
./scripts/check-markdown.sh docs/how-to/contribute-documentation.md
```

### Check all markdown files

```bash
./scripts/check-markdown.sh
```

### Check offline (internal links only)

```bash
./scripts/check-markdown.sh --offline 'docs/**/*.md'
```

The `--offline` flag skips external URL checks. `npx` still needs its pinned
lint package installed or cached. Quote recursive globs so the tools expand
them. The checker uses repository-root-relative paths.

## What the checks do

1. **markdownlint-cli2** checks Markdown headings, formatting, and blank lines. Configuration lives in `.markdownlint-cli2.jsonc`.
2. **lychee** checks internal and external links. Offline mode checks internal links only.

## Common issues and fixes

| Error | Cause | Fix |
|-------|-------|-----|
| `npx: command not found` | Node.js not installed | Install Node.js (see above) |
| `lychee: command not found` | lychee not installed | Install lychee (see above) |
| MD047 | File does not end with one newline | End the file with exactly one newline |
| MD024 | Duplicate headings | Use unique headings or leave the existing project exemption in place |
| MD013 | Line too long | The project configuration disables this rule. |

## CI behavior

CI runs on pushes to `main` and pull requests targeting `main`. It checks
internal links. Run without `--offline` to check external destinations too.
See [the workflow](../../.github/workflows/ci.yml).

## Check the mutation integration and upstream alignment

With the repository's Java 26 and Gradle 9.8.0 baseline installed:

```bash
gradle -p sample/buildSrc test --rerun-tasks
gradle -p sample mutationResults --rerun-tasks
python3 scripts/test-mutation-testing-command.py
python3 scripts/test-update-installation.py
bash scripts/test-bootstrap-copilot.sh
python3 scripts/test-upstream-check.py
python3 scripts/check-copilot-agent-profiles.py
python3 scripts/check-mutation-agent-contracts.py
python3 scripts/test-mutflow-integration.py
python3 scripts/test-documentation-examples.py
python3 scripts/check-upstream.py --offline
```

The integration test creates isolated JVM and KMP projects and runs the
published plugin. It checks strong and weak tests, strict survivors, ordinary
failures, timeouts, changed filters, class identities, budget counters, clean
production artifacts, setup conflicts, cached-test report regeneration, named
KMP JVM targets, and report freshness. CI runs the same test. Parser-only tests
do not cover these behaviors.

The documentation-example test extracts runnable Kotlin snippets and the CI
score check from Markdown. It runs JVM survivor-and-fix and KMP budget-and-full
scenarios. It rejects missing, legacy, gapped, empty, and budget-limited
reports. It does not invoke either live AI client.

To verify released versions and upstream source drift online:

```bash
python3 scripts/check-upstream.py
```

`upstream-sync.yml` runs that check daily and on manual dispatch. It compares
stable Maven versions, the release's compiler pin, and upstream `master`.
Drift or network failure fails visibly and opens or updates a review issue.
Unreleased changes are review signals, not automatically pinned snapshots.
Dependabot proposes weekly Gradle and GitHub Actions updates. CI groups
compiler-coupled updates and checks copied sources and version pins. Update
bootstrap, examples, and docs in the same pull request before accepting a
dependency update. The updater does not bypass compatibility tests.

To run the remaining workflow checks locally, install the pinned versions in
the CI workflow, then run:

```bash
actionlint
yamllint --strict .omp/skills/mutation-testing/agents/openai.yaml .github/workflows/ .github/dependabot.yml
./scripts/check-markdown.sh --offline
```

There is no repository Gradle wrapper. The integration runner uses `gradle`
from `PATH`. Pass `--gradle /path/to/gradle` to select another executable.
It creates temporary projects, removes ambient `MUTFLOW_*` overrides, and
cleans those projects after success or failure.
