# Contributing

Thanks for improving the Mutation Testing Agent Toolkit. This guide covers the
change, test, and pull request workflow.

## Start with the right documentation

- Read [the README](README.md) for the toolkit's purpose and supported paths.
- Read [CONTEXT.md](CONTEXT.md) for domain terms.
- Read the relevant [architecture decision record](docs/index.md#architecture)
  before changing an accepted design.
- Read [AGENTS.md](AGENTS.md) for repository policies and contract boundaries.

## Update every consumer

Shared installer files live in `.mutation-testing/`. OMP-native files live in
`.omp/`, and Copilot CLI files live in `.github/`. Keep the two client
adapters and their native skills or profiles current when a shared contract
changes.

The canonical typed results sources live in
`.mutation-testing/mutation-results-src/`. The sample contains generated copies
under `sample/buildSrc/`. After changing the canonical sources, regenerate the
sample copies from the repository root:

```bash
./bootstrap.sh install sample
```

Keep the `mutation-results.json` field names, types, and meanings stable.
Update every consumer, example, and reference when you change a shared contract.

## Run the relevant checks

For documentation changes, run the Markdown and internal-link checks:

```bash
./scripts/check-markdown.sh --offline
```

If you change a runnable tutorial or the GitHub Actions score check, run its
example test:

```bash
python3 scripts/test-documentation-examples.py
```

If you change an agent profile or shared role contract, run both checks:

```bash
python3 scripts/check-copilot-agent-profiles.py
python3 scripts/check-mutation-agent-contracts.py
```

Run the narrow test for each code change. Use
[How to run repository checks](docs/how-to/run-checks.md) for the full check
list, prerequisites, and validation limits.

## Write or update documentation

Check the [documentation index](docs/index.md) before adding a page. Keep each
page focused on one reader need, and update the index when you add or move a
page. Follow [How to contribute documentation](docs/how-to/contribute-documentation.md)
for page types, examples, links, and writing guidance.

Use exact file names, symbols, and commands. Address the reader as "you", write
instructions as direct commands, and split sentences that carry multiple
actions. State what an example demonstrates, and label sample output when you
did not run it.

## Submit a pull request

Use a feature branch and keep the change focused. Update related docs, examples,
and generated files in the same change. Open a pull request after the checks
pass. State the problem, the behavior that changed, the checks you ran, and
any known limitations in its description.

Use Conventional Commits. For example:

```text
docs: clarify mutation result reporting
fix(bootstrap): preserve local Gradle configuration
```
