# How to update an existing toolkit installation

Use the root `bootstrap.sh` command from the toolkit checkout to update a
target project. Python 3.10 or newer is required. Updates use the local checkout
only and do not change dependency pins or the schema 2 report contract.

## Select the update source

Fast-forward the toolkit checkout to the revision you intend to install. The
updater does not fetch or execute remote `main`. This repository currently has
no Git tags or published releases, so the update source is the exact local
checkout, not an automatically resolved stable release channel. The target
manifest records the checkout commit SHA when Git metadata is available and
notes whether the checkout is dirty.

```bash
git -C "/absolute/toolkit" pull --ff-only
"/absolute/toolkit/bootstrap.sh" update "/absolute/target" --dry-run
```

Inspect creates, updates, conflicts, and diffs. Apply only after review:

```bash
"/absolute/toolkit/bootstrap.sh" update "/absolute/target"
```

An update requires a valid `.mutation-testing/manifest.json`. If the manifest is
missing or invalid, the updater stops before writing; it does not adopt an
untracked installation. Use setup only when you explicitly intend to install
the current layout, not as an implicit migration.

## Conflict behavior

The manifest records a format version, source revision, source working-tree
state, and a SHA-256 hash for each toolkit-managed target file. Managed targets
include the neutral payload, both native client adapters, and generated results
files under `buildSrc/`.

If a file still matches its last installed hash, the updater can replace it with
the current source. If it differs, is missing, is a symlink, or has an
incompatible file type, the updater preserves it and reports a conflict with a
diff when text comparison is possible. Safe unrelated files may still update.
The command returns a conflict status so automation cannot mistake a partial
update for a clean one.

After reviewing a conflict, approve only that project-relative path:

```bash
"/absolute/toolkit/bootstrap.sh" update "/absolute/target" --force .github/agents/mutation-testing-reviewer.agent.md
```

Repeat `--force` for each individually reviewed path. Force does not follow a
symlink and does not approve deletion of unrelated files. Do not use it as a
blanket overwrite switch. A dry run with the same force options previews those
exact writes without changing the target.

The updater synchronizes canonical typed sources under
`.mutation-testing/mutation-results-src/` to generated `buildSrc/` files. If a
canonical source conflicts, the corresponding generated copy is not refreshed.
The updater does not rewrite Gradle build wiring or validate a mutation report.
For older `io.omp.mutation` namespace installations, follow the separate
[manual upgrade guide](manual-setup.md#upgrade-an-existing-installation); this
results-contract migration is distinct from file updates.

After a clean update, inspect the selected module wiring and run the configured
`mutationResults` task. Never use retained JSON after compilation or discovery
failure.
