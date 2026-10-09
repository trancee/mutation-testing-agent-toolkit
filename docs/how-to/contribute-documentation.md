# How to contribute documentation following the Diataxis framework

Use this guide when adding or editing maintained documentation. Start with
[CONTRIBUTING.md](../../CONTRIBUTING.md) for the contributor workflow. The
[README](../../README.md) introduces the toolkit, and
[CONTEXT.md](../../CONTEXT.md) owns domain vocabulary.

## Choose the reader's need

Give each reader-facing page one primary type:

| Reader needs to... | Type | Directory |
|-------------------|------|-----------|
| Learn through a guided exercise | Tutorial | `docs/tutorials/` |
| Complete a concrete task | How-to guide | `docs/how-to/` |
| Look up fields, options, or constraints | Reference | `docs/reference/` |
| Understand rationale and relationships | Explanation | `docs/explanation/` |

`docs/agents/` groups contributor pages by audience. Each page still has a
primary type. ADRs retain their decision-record format. Do not create empty categories
or split pages solely to satisfy a template.

## Edit the authoritative page

Before adding a page, check [the documentation index](../index.md) for an
existing owner. Put complete field definitions in the results reference,
options in the command reference, and procedures in the relevant how-to guide.
Link to those pages instead of copying their tables into README or tutorials.

Use lowercase hyphenated filenames and relative repository links. Add or
update the index when a page or navigational entry changes. Preserve linked
headings or update their incoming links.

## Match the content to its type

- Tutorials provide executable steps and verified expected results, without
  unexplained layout assumptions or long design digressions.
- How-to guides assume competence and cover relevant failures and setup
  conflicts, not just the happy path.
- References state exact contracts, types, defaults, and limitations.
- Explanations describe the reasoning and link to operational details.

Write to the reader as "you". Give instructions as direct commands, and put a
condition before the step it guards. Name the exact file, symbol, or command.
Split sentences that carry more than one action or claim. Replace filler and
abstract metaphors with the concrete action or result.

For full writing guidance, use the repository's
[Diataxis skill](../../.agents/skills/diataxis/SKILL.md) and its
[quality checklist](../../.agents/skills/diataxis/references/quality-checklist.md).

## Verify accuracy

Check examples against the current scripts, profiles, and released plugin
behavior. Label illustrative output rather than presenting invented counts as
executed evidence. Run changed executable examples when their behavior is not
already covered by an equivalent fixture.

Verify updated version pins against authoritative release metadata and
compiler compatibility. Update mutflow and Kotlin as one tested toolchain
change; only accept a compiler-version mismatch when the exact pair has a
passing real-plugin integration test.
Historical ADR rationale should not contain volatile star counts or unsupported
claims of current validation.

Run the [repository documentation checks](run-checks.md):

```bash
./scripts/check-markdown.sh
python3 scripts/check-upstream.py --offline
```

Use [Conventional Commits](../../AGENTS.md#commit-messages) when committing.
Keep the change focused on the reader's need.
