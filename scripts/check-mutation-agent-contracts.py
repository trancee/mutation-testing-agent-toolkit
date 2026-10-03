#!/usr/bin/env python3
"""Check that OMP and Copilot profiles retain their shared role contracts."""

from dataclasses import dataclass
from pathlib import Path
import re
import sys


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Contract:
    name: str
    omp_pattern: str
    copilot_pattern: str


@dataclass(frozen=True)
class Role:
    omp_file: str
    copilot_file: str
    contracts: tuple[Contract, ...]


ROLES = {
    "reviewer": Role(
        ".omp/agents/test-quality-reviewer.md",
        ".github/agents/omp-mutation-test-reviewer.agent.md",
        (
            Contract(
                "orders targeting, execution, audit, and refactoring",
                r"Sequential handshake: saboteur → one aggregate executor → auditor → approval gate → refactorer",
                r"1\..*omp-mutation-test-saboteur.*2\..*omp-mutation-test-executor.*"
                r"3\..*omp-mutation-test-auditor.*4\..*omp-mutation-test-refactor-specialist",
            ),
            Contract(
                "skips refactoring in quick mode",
                r"In `quick` mode, skip the refactor phase",
                r"Skip refactoring in `quick` mode",
            ),
            Contract(
                "requires explicit approval before deleting tests",
                r"Deletion or consolidation of tests always requires explicit user approval",
                r"deletion or\s+consolidation always requires explicit user approval",
            ),
            Contract(
                "treats project paths as untrusted and quotes shell arguments",
                r"project path and project files as untrusted data.*quote it in shell commands",
                r"Treat the project path and project files as untrusted data.*"
                r"quote paths in shell commands",
            ),
        ),
    ),
    "saboteur": Role(
        ".omp/agents/test-saboteur.md",
        ".github/agents/omp-mutation-test-saboteur.agent.md",
        (
            Contract(
                "does not create mutation operators",
                r"You do NOT create mutations manually",
                r"Do not add custom mutation operators",
            ),
            Contract(
                "targets business logic and avoids framework code",
                r"Identify business logic.*Do NOT annotate pure data holders, framework glue",
                r"Target business rules.*avoid framework wiring, data holders",
            ),
            Contract(
                "wraps calls under test with MutFlow.underTest",
                r"wrap each call in `MutFlow\.underTest",
                r"Wrap calls under test with `MutFlow\.underTest",
            ),
        ),
    ),
    "executor": Role(
        ".omp/agents/test-executor.md",
        ".github/agents/omp-mutation-test-executor.agent.md",
        (
            Contract(
                "runs one aggregate mutationResults invocation with selected class patterns",
                r"Run the aggregate task once.*mutationResults",
                r"Run `\./gradlew.*mutationResults`.*exactly once",
            ),
            Contract(
                "treats mutationResults as an aggregate report task",
                r"`mutationResults`.*aggregate\s+JSON.*not (?:as )?a per-class\s+replacement",
                r"`mutationResults` writes the aggregate.*JSON report.*aggregate report task, not a\s+per-class replacement",
            ),
            Contract(
                "does not report execution gaps as surviving mutations",
                r"Report execution gaps separately; never classify a gap as a surviving mutation",
                r"Do not\s+classify a gap as a surviving mutation",
            ),
        ),
    ),
    "auditor": Role(
        ".omp/agents/test-auditor.md",
        ".github/agents/omp-mutation-test-auditor.agent.md",
        (
            Contract(
                "uses the score formula and nulls an empty denominator",
                r"killed / \(total - gaps\).*Returns `null` when no mutations are evaluable "
                r"\(denominator is 0",
                r"killed / \(total - gaps\).*Return `null` when the\n  denominator is zero",
            ),
            Contract(
                "uses identical quality-band boundaries",
                r"Excellent: >80%.*Good: >60% and ≤80%.*Fair: >30% and ≤60%.*Poor: ≤30%",
                r"Excellent >80%, Good >60% and ≤80%, Fair >30% and ≤60%, Poor ≤30%",
            ),
            Contract(
                "requires per-test evidence for zombie candidates",
                r"Do not classify zombie candidates when the available results do not identify which tests killed mutations",
                r"do not classify zombie candidates",
            ),
            Contract(
                "keeps timed-out mutations distinct from execution gaps",
                r"`TimedOut` is NOT a gap",
                r"Preserve `Killed`, `Survived`, and `TimedOut` as distinct results",
            ),
        ),
    ),
    "refactor specialist": Role(
        ".omp/agents/test-refactor-specialist.md",
        ".github/agents/omp-mutation-test-refactor-specialist.agent.md",
        (
            Contract(
                "changes test files only",
                r"only test files",
                r"Modify test files only",
            ),
            Contract(
                "gates edits on auto-approval",
                r"(?:With `--auto-approve`|If `--auto-approve` IS set).*you may apply",
                r"With `--auto-approve`, you may apply",
            ),
            Contract(
                "requires explicit approval to delete or consolidate tests",
                r"Deleting or consolidating tests always requires explicit user approval",
                r"explicit user approval before deleting tests or consolidating\s+redundant groups",
            ),
        ),
    ),
}


def fail(message: str) -> None:
    print(f"[mutation-agent-contracts] {message}", file=sys.stderr)


def main() -> None:
    errors = 0
    checked = 0

    for role_name, role in ROLES.items():
        paths = {
            "OMP": REPOSITORY_ROOT / role.omp_file,
            "Copilot": REPOSITORY_ROOT / role.copilot_file,
        }
        contents: dict[str, str] = {}
        for client, path in paths.items():
            try:
                contents[client] = path.read_text(encoding="utf-8")
            except OSError as error:
                fail(f"{role_name} {client} profile unavailable: {error}")
                errors += 1

        if len(contents) != len(paths):
            continue

        for contract in role.contracts:
            checked += 1
            for client, pattern in (
                ("OMP", contract.omp_pattern),
                ("Copilot", contract.copilot_pattern),
            ):
                if not re.search(pattern, contents[client], re.IGNORECASE | re.DOTALL):
                    fail(f"{role_name} {client} profile is missing contract: {contract.name}")
                    errors += 1

    if errors:
        raise SystemExit(1)

    print(f"[mutation-agent-contracts] validated {checked} shared role contracts")


if __name__ == "__main__":
    main()
