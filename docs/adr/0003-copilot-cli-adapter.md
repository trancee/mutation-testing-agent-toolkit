# ADR-003: Native GitHub Copilot CLI adapter

- **Date**: 2026-10-03
- **Status**: Accepted

## Context

The existing mutation-testing skill and agents use OMP-specific `task` and
`hub` tools in `.omp/`. GitHub Copilot CLI supports Agent Skills and custom
agent profiles, but does not discover those OMP definitions as Copilot agents.
Calling the OMP CLI from Copilot would preserve the OMP runtime rather than
provide a native Copilot workflow.

## Decision

Maintain a separate Copilot adapter:

- `.github/skills/omp-mutation-test/` is the Copilot CLI entry point.
- `.github/agents/omp-mutation-test-*.agent.md` defines the reviewer and four
  least-privilege worker profiles.
- The reviewer uses Copilot's native `agent` tool; worker profiles cannot spawn
  more agents.
- The bootstrap installs both client adapters. It refuses symlinked Copilot
  destinations and differing files with matching names before modifying the
  target.
- OMP files and its `/mutation-test` entry point remain unchanged.

Both adapters preserve the same mutflow phases, result contract, and explicit
approval requirement for deleting tests. Client-specific dispatch and profile
metadata stay separate to avoid unsupported cross-client tool assumptions.

## Alternatives considered

- **Invoke OMP from Copilot shell**: lower implementation cost, but requires the
  OMP CLI and leaves orchestration in OMP.
- **Reuse the OMP skill without agent profiles**: the instructions reference
  OMP-only dispatch tools and would not run the five-role workflow natively.
- **Replace the OMP profiles with Copilot profiles**: rejected because it would
  break existing OMP users.

## Consequences

- The behavior contracts are intentionally represented in two client-specific
  profile sets and can drift; `docs/agents/mutation-testing-agents.md` records
  both sets, and the bootstrap test checks Copilot installation and conflict
  handling.
- Copilot CLI skill discovery and reviewer profile loading are verified
  locally. Full delegated mutation-test execution still depends on a configured
  Copilot session and a suitable Kotlin project.
- Existing bootstrapped projects receive the Copilot adapter when the current
  bootstrap script is run. Manual installations must copy both the skill and
  all five agent profiles.
