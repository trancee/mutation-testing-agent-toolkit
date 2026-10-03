# How to run repository checks

Use this guide to check documentation, client contracts, mutation integration,
and upstream alignment before proposing repository changes.

## Prerequisites

- **Node.js**, required for `markdownlint-cli2` style checks
- **lychee**, required for internal and external link checks
- **Python 3**, required for adapter, integration, and upstream checks
- **Java 26 and Gradle 9.8.0**, required for Kotlin and real integration tests

### Install Node.js

Install a supported release from [nodejs.org](https://nodejs.org/) or your
Node version manager. CI uses Node 26. Verify:

```bash
node --version
npx --version
```

### Install lychee

```bash
brew install lychee
```

Or via curl:

```bash
curl -LsSf https://github.com/lycheeverse/lychee/releases/latest/download/lychee-installer.sh | sh
```

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

The `--offline` flag skips external URL checks; `npx` still needs its pinned
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
| MD013 | Line too long | No action; the project configuration disables this rule |

## CI behavior

CI runs on pushes to `main` and pull requests targeting `main`. It uses
internal link checks; run without `--offline` to inspect external destinations.
See [the workflow](../../.github/workflows/ci.yml).

## Check the mutation integration and upstream alignment

With the repository's Java 26 and Gradle 9.8.0 baseline installed:

```bash
gradle -p sample/buildSrc test --rerun-tasks
gradle -p sample mutationResults --rerun-tasks
bash scripts/test-bootstrap-copilot.sh
python3 scripts/test-upstream-check.py
python3 scripts/check-copilot-agent-profiles.py
python3 scripts/check-mutation-agent-contracts.py
python3 scripts/test-mutflow-integration.py
python3 scripts/check-upstream.py --offline
```

The integration gate creates isolated JVM and KMP projects and runs the
published plugin. It checks strong/weak tests, strict survivors, ordinary
failures, timeouts, changed filters, class identities, budget counters, clean
production artifacts, setup conflicts, cached-test report regeneration, named
KMP JVM targets, and report freshness. CI runs the same
gate; parser-only tests are not a substitute.

To verify released versions and upstream source drift online:

```bash
python3 scripts/check-upstream.py
```

`upstream-sync.yml` runs that check daily and on manual dispatch. It compares
stable Maven versions, the release's compiler pin, and upstream `master`;
drift or network failure fails visibly and opens or updates a review issue.
Unreleased changes are review signals, never automatically pinned snapshots.
Dependabot proposes weekly Gradle and GitHub Actions updates. Compiler-coupled
updates are grouped; CI also requires copied sources and every checked version
pin to stay consistent. Update bootstrap, examples, and docs in the same PR
before accepting a dependency update. No updater bypasses compatibility tests.

To run the remaining workflow gates locally, install the pinned versions in
the CI workflow, then run:

```bash
actionlint
yamllint --strict .omp/skills/mutation-test/agents/openai.yaml .github/workflows/ .github/dependabot.yml
./scripts/check-markdown.sh --offline
```

There is no repository Gradle wrapper. The real integration runner uses
`gradle` from `PATH`; pass `--gradle /path/to/gradle` to select another
executable. It creates temporary projects, removes ambient `MUTFLOW_*`
overrides, and cleans those projects after success or failure.
