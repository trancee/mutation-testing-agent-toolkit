# How agents use domain documentation

Use this guide before exploring or changing this toolkit.

## Read the project context

Read [CONTEXT.md](../../CONTEXT.md) for terminology and scope, then read the
relevant decisions in [docs/adr](../index.md#architecture). This repository
uses a single-context layout: one root `CONTEXT.md` and root `docs/adr/`.
Do not introduce a context map or per-module ADR trees without a concrete need.

For contributor constraints, approval boundaries, and Conventional Commits,
read [AGENTS.md](../../AGENTS.md). Domain terminology and contributor rules
have different owners; keep them in their respective files.

## Use the domain vocabulary

Use terms as defined in `CONTEXT.md` in issues, hypotheses, tests, and reports.
In particular, distinguish mutation outcomes from execution gaps and
zombie-test candidates from confirmed unnecessary tests.

If a needed term is missing, first check whether an existing term describes
the same concept. Add a definition only when a real domain distinction is
resolved, not as speculative scaffolding.

## Surface decision conflicts

If a proposed change contradicts an accepted ADR, name the conflicting
decision and explain why it needs reconsideration. Do not silently replace
the established design or treat historical design tables as current metadata;
the [agent reference](mutation-testing-agents.md) owns current profile details.
