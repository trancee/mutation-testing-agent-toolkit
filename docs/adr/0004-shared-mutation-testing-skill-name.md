# ADR-004: Shared mutation-testing skill name

- **Date**: 2026-10-03
- **Status**: Accepted

## Context

OMP and Copilot CLI expose the same mutation-testing workflow through separate
client-scoped skill packages. The public command should not be tied to either
client, while the client-specific agent roles and dispatch protocols remain
separate.

## Decision

Both clients expose `/mutation-testing`. Copilot roles use `mutation-testing-*`
IDs; OMP roles and dispatch protocols remain unchanged. Since the old skill and
command names were not used by installations, bootstrap supports only the new
paths and names, without aliases or migration guards for them.
