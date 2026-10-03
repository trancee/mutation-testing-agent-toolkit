#!/usr/bin/env python3
"""Validate the Copilot mutation-testing profile metadata and delegation boundary."""

from pathlib import Path
import sys

import yaml


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
AGENT_DIRECTORY = REPOSITORY_ROOT / ".github" / "agents"
EXPECTED_NAMES = {
    "omp-mutation-test-reviewer",
    "omp-mutation-test-saboteur",
    "omp-mutation-test-executor",
    "omp-mutation-test-auditor",
    "omp-mutation-test-refactor-specialist",
}
ALLOWED_TOOLS = {"read", "search", "edit", "execute", "agent"}


def fail(message: str) -> None:
    print(f"[copilot-agents] {message}", file=sys.stderr)
    raise SystemExit(1)


def read_profile(path: Path) -> dict[str, object]:
    contents = path.read_text(encoding="utf-8")
    delimiter = "\n---\n"
    if not contents.startswith("---\n"):
        fail(f"{path}: missing YAML frontmatter")
    end = contents.find(delimiter, 4)
    if end < 0:
        fail(f"{path}: unterminated YAML frontmatter")

    try:
        profile = yaml.safe_load(contents[4:end])
    except yaml.YAMLError as error:
        fail(f"{path}: invalid YAML frontmatter: {error}")
    if not isinstance(profile, dict):
        fail(f"{path}: frontmatter must be a YAML mapping")
    return profile


def main() -> None:
    paths = sorted(AGENT_DIRECTORY.glob("omp-mutation-test-*.agent.md"))
    profiles: dict[str, tuple[Path, dict[str, object]]] = {}

    for path in paths:
        profile = read_profile(path)
        name = profile.get("name")
        description = profile.get("description")
        tools = profile.get("tools")
        if not isinstance(name, str) or not name:
            fail(f"{path}: name must be a non-empty string")
        if path.name != f"{name}.agent.md":
            fail(f"{path}: filename must match profile name '{name}'")
        if name in profiles:
            fail(f"{path}: duplicate profile name '{name}'")
        if not isinstance(description, str) or not description.strip():
            fail(f"{path}: description must be a non-empty string")
        if not isinstance(tools, list) or not all(isinstance(tool, str) for tool in tools):
            fail(f"{path}: tools must be a list of strings")
        unknown_tools = set(tools) - ALLOWED_TOOLS
        if unknown_tools:
            fail(f"{path}: unknown tools: {', '.join(sorted(unknown_tools))}")
        profiles[name] = (path, profile)

    actual_names = set(profiles)
    if actual_names != EXPECTED_NAMES:
        missing = sorted(EXPECTED_NAMES - actual_names)
        unexpected = sorted(actual_names - EXPECTED_NAMES)
        fail(f"agent set mismatch; missing={missing}, unexpected={unexpected}")

    reviewer_tools = profiles["omp-mutation-test-reviewer"][1]["tools"]
    if "agent" not in reviewer_tools:
        fail("reviewer must be able to delegate through Copilot's agent tool")
    if profiles["omp-mutation-test-reviewer"][1].get("user-invocable", True) is not True:
        fail("reviewer must remain user-invocable")

    for name in EXPECTED_NAMES - {"omp-mutation-test-reviewer"}:
        _, profile = profiles[name]
        if profile.get("user-invocable") is not False:
            fail(f"{name}: worker profiles must be programmatic-only")
        if "agent" in profile["tools"]:
            fail(f"{name}: worker profiles must not spawn additional agents")

    print(f"[copilot-agents] validated {len(profiles)} agent profiles")


if __name__ == "__main__":
    main()
