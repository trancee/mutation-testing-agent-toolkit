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

- `.github/skills/mutation-testing/` is the Copilot CLI entry point.
- `.github/agents/mutation-testing-*.agent.md` defines the reviewer and four
  least-privilege worker profiles.
- The reviewer uses Copilot's native `agent` tool; worker profiles cannot spawn
  more agents.
- The root `bootstrap.sh install` command installs both client adapters. It refuses symlinked Copilot
  destinations and differing files with matching names before modifying the
  target.
- The OMP adapter remains separate and uses its own files and `task`/`hub`
  dispatch protocol; the shared skill name does not couple the two clients.

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
  both sets, and the root-command setup test checks Copilot installation and conflict
  handling.
- Package integrity, installation, profile metadata, and shared role contracts
  are checked locally and in CI. Fresh end-to-end delegated execution in both
  clients is not covered by those checks.
- Existing installations must merge changed toolkit-owned skill and profile
  files explicitly; the setup command refuses differing Copilot files and legacy
  results namespaces. See the [upgrade procedure](../how-to/manual-setup.md#upgrade-an-existing-installation).
