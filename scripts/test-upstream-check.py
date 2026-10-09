#!/usr/bin/env python3
"""Deterministic tests for release filtering and upstream drift detection."""

import contextlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


SPEC = importlib.util.spec_from_file_location("upstream", Path(__file__).with_name("check-upstream.py"))
CHECKER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CHECKER)


class UpstreamCheckTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="upstream-check-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.write("sample/build.gradle.kts", """
plugins {
    kotlin("jvm") version "2.4.21"
    id("io.github.anschnapp.mutflow") version "1.7.0"
}
dependencies {
    testImplementation("org.junit.jupiter:junit-jupiter-api:6.1.3")
    testImplementation("io.github.anschnapp.mutflow:mutflow-junit4:1.7.0")
    testImplementation("junit:junit:4.13.2")
}
""")
        self.write(".mutation-testing/mutation-results-src/build.gradle.kts", """
plugins { kotlin("plugin.serialization") version "2.4.21" }
dependencies { implementation("org.jetbrains.kotlinx:kotlinx-serialization-json:1.11.0") }
""")
        self.write("sample/buildSrc/build.gradle.kts",
                   (self.root / ".mutation-testing/mutation-results-src/build.gradle.kts").read_text())
        self.write(".mutation-testing/bootstrap-mutation-testing.sh",
                   'REQUIRED_KOTLIN_VERSION="2.4.21"\n# mutflow preflight pin: 1\\.7\\.0\n')
        for path in [".github/workflows/ci.yml", "scripts/test-bootstrap-copilot.sh",
                     "scripts/test-mutflow-integration.py"]:
            self.write(path, "")
        (self.root / "docs").mkdir()
        self.compiler = "2.4.21"
        self.status = "identical"
        self.latest_mutflow = "1.7.0"
        self.latest_mutflow_junit4 = "1.7.0"
        self.latest_junit4 = "4.13.2"

    def write(self, path, text):
        destination = self.root / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(text)

    def fetch(self, url):
        if url.endswith("maven-metadata.xml"):
            versions = {
                "mutflow-gradle-plugin": [self.latest_mutflow, "1.7.0-RC1"],
                "mutflow-junit4": [self.latest_mutflow_junit4, "1.7.0-RC1"],
                "kotlin-gradle-plugin": ["2.4.21", "2.5.0-Beta1"],
                "junit-jupiter-api": ["6.1.3", "6.2.0-M1"],
                "junit/junit": [self.latest_junit4, "4.14-Beta1"],
                "kotlinx-serialization-json": ["1.11.0", "1.12.0-RC"],
            }
            values = next(values for key, values in versions.items() if key in url)
            return "<metadata><versioning><versions>" + "".join(
                f"<version>{value}</version>" for value in values
            ) + "</versions></versioning></metadata>"
        if url.endswith("gradle.properties"):
            return f"kotlinVersion={self.compiler}\n"
        return json.dumps({"status": self.status, "html_url": "https://example.test/compare",
                           "base_commit": {"sha": "release-sha"}})

    def check(self):
        with patch.object(CHECKER, "ROOT", self.root), patch.object(CHECKER, "fetch", self.fetch), \
                patch("sys.argv", ["check-upstream.py"]), \
                contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            CHECKER.main()

    def test_prereleases_are_ignored(self):
        self.check()

    def test_validated_mutflow_kotlin_patch_mismatch_passes(self):
        self.compiler = "2.4.20"
        self.check()

    def test_new_stable_junit4_release_requires_review(self):
        self.latest_junit4 = "4.14"
        with self.assertRaises(SystemExit):
            self.check()

    def test_new_stable_mutflow_junit4_release_requires_review(self):
        self.latest_mutflow_junit4 = "1.8.0"
        with self.assertRaises(SystemExit):
            self.check()

    def test_new_stable_release_requires_review(self):
        self.latest_mutflow = "1.8.0"
        with self.assertRaises(SystemExit) as failure:
            self.check()
        self.assertEqual(1, failure.exception.code)

    def test_compiler_mismatch_requires_review(self):
        self.compiler = "2.4.22"
        with self.assertRaises(SystemExit):
            self.check()

    def test_stale_bootstrap_compiler_pin_is_rejected(self):
        self.write(".mutation-testing/bootstrap-mutation-testing.sh",
                   'REQUIRED_KOTLIN_VERSION="2.3.0"\n# mutflow preflight pin: 1\\.6\\.1\n')
        with self.assertRaises(SystemExit):
            self.check()

    def test_unreleased_upstream_changes_require_review(self):
        self.status = "ahead"
        with self.assertRaises(SystemExit):
            self.check()

    def test_stale_ci_pin_is_rejected(self):
        self.write(".github/workflows/ci.yml", 'kotlin("jvm") version "2.3.0"')
        with self.assertRaises(SystemExit):
            self.check()

    def test_stale_sample_source_is_rejected(self):
        self.write(".mutation-testing/mutation-results-src/main/kotlin/ch/trancee/mutation/Example.kt", "source")
        self.write("sample/buildSrc/src/main/kotlin/ch/trancee/mutation/Example.kt", "stale")
        with self.assertRaises(SystemExit):
            self.check()

    def test_extra_legacy_sample_source_is_rejected(self):
        self.write("sample/buildSrc/src/main/kotlin/io/omp/mutation/Legacy.kt", "legacy")
        with self.assertRaises(SystemExit):
            self.check()

    def test_missing_sample_source_is_rejected(self):
        self.write(".mutation-testing/mutation-results-src/main/kotlin/ch/trancee/mutation/Example.kt", "source")

        with self.assertRaises(SystemExit) as failure:
            self.check()

        self.assertEqual(1, failure.exception.code)

    def test_changed_sample_build_configuration_is_rejected(self):
        self.write("sample/buildSrc/build.gradle.kts", "// changed configuration")

        with self.assertRaises(SystemExit) as failure:
            self.check()

        self.assertEqual(1, failure.exception.code)

    def test_offline_check_never_requests_network(self):
        with patch.object(CHECKER, "ROOT", self.root), \
                patch.object(CHECKER, "fetch", side_effect=AssertionError("network forbidden")) as fetch, \
                patch("sys.argv", ["check-upstream.py", "--offline"]), \
                contextlib.redirect_stdout(io.StringIO()):
            CHECKER.main()

        fetch.assert_not_called()

    def test_network_failure_is_not_silently_accepted(self):
        with patch.object(CHECKER, "fetch", side_effect=ConnectionError("offline")):
            # A request failure propagates as a failing check, not a successful fallback.
            with patch.object(CHECKER, "ROOT", self.root), patch("sys.argv", ["check-upstream.py"]):
                with self.assertRaises(ConnectionError):
                    CHECKER.main()


if __name__ == "__main__":
    unittest.main()
