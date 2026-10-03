#!/usr/bin/env python3
"""Fail visibly on upstream drift, mismatched pins, or stale generated sources."""

import argparse
from pathlib import Path
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
import json


ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = {
    "mutflow": "io/github/anschnapp/mutflow/mutflow-gradle-plugin",
    "kotlin": "org/jetbrains/kotlin/kotlin-gradle-plugin",
    "junit": "org/junit/jupiter/junit-jupiter-api",
    "serialization": "org/jetbrains/kotlinx/kotlinx-serialization-json",
}
PATTERNS = {
    "mutflow": r'id\("io\.github\.anschnapp\.mutflow"\) version "([^"]+)"',
    "kotlin": r'kotlin\("(?:jvm|multiplatform|plugin\.serialization)"\) version "([^"]+)"',
    "junit": r'org\.junit\.(?:jupiter|platform):[^:"]+:([^"]+)"',
    "serialization": r'org\.jetbrains\.kotlinx:kotlinx-serialization-json:([^"]+)"',
}


def fetch(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": "mutation-testing-agent-toolkit"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true", help="Check local consistency without network access")
    args = parser.parse_args()
    errors = []
    sample = (ROOT / "sample/build.gradle.kts").read_text()
    template = (ROOT / ".omp/mutation-results-src/build.gradle.kts").read_text()
    pins = {}
    for name, pattern in PATTERNS.items():
        matches = re.findall(pattern, sample + template)
        if not matches or len(set(matches)) != 1:
            errors.append(f"Inconsistent or missing canonical {name} pins: {matches}")
        else:
            pins[name] = matches[0]

    paths = [
        ROOT / ".omp/bootstrap-mutation-testing.sh",
        ROOT / ".github/workflows/ci.yml",
        ROOT / "scripts/test-bootstrap-copilot.sh",
        ROOT / "scripts/test-mutflow-integration.py",
    ]
    paths += list((ROOT / "docs").rglob("*.md"))
    for path in paths:
        text = path.read_text()
        for name, pattern in PATTERNS.items():
            for value in re.findall(pattern, text):
                # The negative integration fixture intentionally uses an incompatible compiler.
                if path.name == "test-mutflow-integration.py" and name == "kotlin" and value == "2.3.0":
                    continue
                if value != pins.get(name):
                    errors.append(f"{path.relative_to(ROOT)}: {name} {value} != {pins.get(name)}")
    bootstrap = (ROOT / ".omp/bootstrap-mutation-testing.sh").read_text()
    for name in ["mutflow", "kotlin"]:
        escaped_pin = pins[name].replace(".", r"\.")
        if escaped_pin not in bootstrap:
            errors.append(f"Bootstrap {name} compatibility preflight does not match canonical pin")
    compiler_pin = re.search(r'^KOTLIN_VERSION="([^"]+)"$', bootstrap, re.MULTILINE)
    if not compiler_pin or compiler_pin.group(1) != pins.get("kotlin"):
        errors.append("Bootstrap buildSrc compiler pin differs from canonical Kotlin")

    canonical = ROOT / ".omp/mutation-results-src"
    for source, destination in [("main/kotlin", "main/kotlin"), ("test/kotlin", "test/kotlin")]:
        source_root = canonical / source
        copy_root = ROOT / "sample/buildSrc/src" / destination
        source_paths = {file.relative_to(source_root) for file in source_root.rglob("*.kt")}
        copy_paths = {file.relative_to(copy_root) for file in copy_root.rglob("*.kt")}
        for extra in sorted(copy_paths - source_paths):
            errors.append(f"Extra stale sample source: {(copy_root / extra).relative_to(ROOT)}")
        for file in (canonical / source).rglob("*.kt"):
            copied = ROOT / "sample/buildSrc/src" / destination / file.relative_to(canonical / source)
            if not copied.exists() or copied.read_bytes() != file.read_bytes():
                errors.append(f"Sample copy differs from canonical source: {copied.relative_to(ROOT)}")
    if (ROOT / "sample/buildSrc/build.gradle.kts").read_bytes() != (canonical / "build.gradle.kts").read_bytes():
        errors.append("Sample buildSrc build differs from its bootstrap template")

    if not args.offline:
        for name, artifact in ARTIFACTS.items():
            metadata = ET.fromstring(fetch(f"https://repo.maven.apache.org/maven2/{artifact}/maven-metadata.xml"))
            stable = [
                node.text for node in metadata.findall("./versioning/versions/version")
                if re.fullmatch(r"\d+(?:\.\d+)+", node.text or "")
            ]
            latest = max(stable, key=lambda version: tuple(map(int, version.split("."))))
            if latest != pins.get(name):
                errors.append(f"Upstream {name} stable is {latest}; toolkit pins {pins.get(name)}. Review compatibility before updating.")
        version = pins["mutflow"]
        upstream = fetch(f"https://raw.githubusercontent.com/anschnapp/mutflow/v{version}/gradle.properties")
        compiler = re.search(r"^kotlinVersion=(.+)$", upstream, re.MULTILINE)
        if not compiler or compiler.group(1).strip() != pins["kotlin"]:
            errors.append(f"mutflow {version} is not built against pinned Kotlin {pins['kotlin']}")
        comparison = json.loads(fetch(f"https://api.github.com/repos/anschnapp/mutflow/compare/v{version}...master"))
        if comparison["status"] != "identical":
            errors.append(f"Upstream master differs from v{version}: {comparison['html_url']}. Review unreleased API changes; do not pin snapshots.")
        print(f"Verified upstream mutflow v{version}, release commit {comparison['base_commit']['sha']}")

    if errors:
        for error in errors:
            print(f"[upstream] {error}", file=sys.stderr)
        raise SystemExit(1)
    print(f"Upstream {'local consistency' if args.offline else 'release and compatibility'} checks passed: {pins}")


if __name__ == "__main__":
    main()
