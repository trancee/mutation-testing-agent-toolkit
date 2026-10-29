#!/usr/bin/env python3
"""Deterministic tests for release filtering and upstream drift detection."""

import contextlib
import importlib.util
import io
import json
import os
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
    id("io.github.anschnapp.mutflow") version "1.7.1"
}
dependencies {
    testImplementation("org.junit.jupiter:junit-jupiter-api:6.1.3")
    testImplementation("io.github.anschnapp.mutflow:mutflow-junit4:1.7.1")
    testImplementation("junit:junit:4.13.2")
}
""")
        self.write(".mutation-testing/mutation-results-src/build.gradle.kts", """
plugins { kotlin("plugin.serialization") version "2.4.21" }
dependencies { implementation("org.jetbrains.kotlinx:kotlinx-serialization-json:1.12.0") }
""")
        self.write("sample/buildSrc/build.gradle.kts",
                   (self.root / ".mutation-testing/mutation-results-src/build.gradle.kts").read_text())
        self.write(".mutation-testing/bootstrap-mutation-testing.sh",
                   'REQUIRED_KOTLIN_VERSION="2.4.21"\n# mutflow preflight pin: 1\\.7\\.1\n')
        for path in [".github/workflows/ci.yml", "scripts/test-bootstrap-copilot.sh",
                     "scripts/test-mutflow-integration.py"]:
            self.write(path, "")
        (self.root / "docs").mkdir()
        self.compiler = "2.4.21"
        self.status = "identical"
        self.changed_files = []
        self.latest_mutflow = "1.7.1"
        self.latest_mutflow_junit4 = "1.7.1"
        self.latest_junit4 = "4.13.2"
        self.latest_serialization = "1.12.0"

    def write(self, path, text):
        destination = self.root / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(text)

    def fetch(self, url):
        if url.endswith("maven-metadata.xml"):
            versions = {
                "mutflow-gradle-plugin": [self.latest_mutflow, "1.7.1-RC1"],
                "mutflow-junit4": [self.latest_mutflow_junit4, "1.7.1-RC1"],
                "kotlin-gradle-plugin": ["2.4.21", "2.5.0-Beta1"],
                "junit-jupiter-api": ["6.1.3", "6.2.0-M1"],
                "junit/junit": [self.latest_junit4, "4.14-Beta1"],
                "kotlinx-serialization-json": [self.latest_serialization, "1.13.0-RC"],
            }
            values = next(values for key, values in versions.items() if key in url)
            return "<metadata><versioning><versions>" + "".join(
                f"<version>{value}</version>" for value in values
            ) + "</versions></versioning></metadata>"
        if url.endswith("gradle.properties"):
            return f"kotlinVersion={self.compiler}\n"
        return json.dumps({
            "status": self.status,
            "html_url": "https://example.test/compare",
            "base_commit": {"sha": "release-sha"},
            "files": self.changed_files,
        })

    def check(self):
        output = io.StringIO()
        with patch.object(CHECKER, "ROOT", self.root), patch.object(CHECKER, "fetch", self.fetch), \
                patch("sys.argv", ["check-upstream.py"]), \
                contextlib.redirect_stdout(output), contextlib.redirect_stderr(io.StringIO()):
            CHECKER.main()
        return output.getvalue()

    def test_prereleases_are_ignored(self):
        self.check()

    def test_validated_mutflow_kotlin_patch_mismatch_passes(self):
        self.compiler = "2.4.20"
        self.latest_mutflow = "1.7.0"
        self.latest_mutflow_junit4 = "1.7.0"
        sample = (self.root / "sample/build.gradle.kts").read_text()
        self.write("sample/build.gradle.kts", sample.replace("1.7.1", "1.7.0"))
        bootstrap = (self.root / ".mutation-testing/bootstrap-mutation-testing.sh").read_text()
        self.write(
            ".mutation-testing/bootstrap-mutation-testing.sh",
            bootstrap.replace(r"1\.7\.1", r"1\.7\.0"),
        )
        self.check()

    def test_new_stable_junit4_release_requires_review(self):
        self.latest_junit4 = "4.14"
        with self.assertRaises(SystemExit):
            self.check()

    def test_new_stable_mutflow_junit4_release_requires_review(self):
        self.latest_mutflow_junit4 = "1.8.0"
        with self.assertRaises(SystemExit):
            self.check()

    def test_new_stable_serialization_release_requires_review(self):
        self.latest_serialization = "1.13.0"
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
        self.changed_files = [
            {"filename": "README.md"},
            {"filename": "mutflow-core/src/MutFlow.kt"},
        ]
        with self.assertRaises(SystemExit):
            self.check()

    def test_documentation_only_upstream_changes_do_not_require_review(self):
        self.status = "ahead"
        self.changed_files = [{"filename": "DESIGN.md"}, {"filename": "README.md"}]

        output = self.check()

        self.assertIn("only in documentation", output)

    def test_upstream_drift_without_file_details_requires_review(self):
        self.status = "ahead"
        with self.assertRaises(SystemExit):
            self.check()

    def test_documentation_changes_do_not_hide_a_diverged_release(self):
        self.status = "diverged"
        self.changed_files = [{"filename": "README.md"}]
        with self.assertRaises(SystemExit):
            self.check()

    def test_truncated_documentation_file_list_requires_review(self):
        self.status = "ahead"
        self.changed_files = [{"filename": f"docs/{index}.md"} for index in range(300)]
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

    def test_fetch_sends_workflow_token_only_to_github_api(self):
        requests = []

        def open_request(request, timeout):
            requests.append(request)
            return io.BytesIO(b"{}")

        urls = [
            "https://api.github.com/repos/anschnapp/mutflow/compare/v1.7.1...master",
            "https://raw.githubusercontent.com/anschnapp/mutflow/v1.7.1/gradle.properties",
            "https://repo.maven.apache.org/maven2/org/jetbrains/kotlin/kotlin-gradle-plugin/maven-metadata.xml",
            "http://api.github.com/repos/anschnapp/mutflow/compare/v1.7.1...master",
            "https://api.github.com.attacker.example/repos/anschnapp/mutflow/compare",
        ]
        with patch.dict(os.environ, {"GH_TOKEN": "github-test-token"}), \
                patch.object(CHECKER.urllib.request, "urlopen", side_effect=open_request):
            for url in urls:
                CHECKER.fetch(url)

        self.assertEqual("Bearer github-test-token", requests[0].get_header("Authorization"))
        for request in requests[1:]:
            self.assertIsNone(request.get_header("Authorization"))

    def test_upstream_workflow_passes_token_to_checker(self):
        workflow = (Path(__file__).resolve().parents[1] / ".github/workflows/upstream-sync.yml").read_text()
        check_step = workflow.split("      - name: Publish upstream status", maxsplit=1)[0]
        self.assertIn("      - name: Verify latest stable versions and upstream API drift", check_step)
        self.assertIn("          GH_TOKEN: ${{ github.token }}", check_step)


if __name__ == "__main__":
    unittest.main()
