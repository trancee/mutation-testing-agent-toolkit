#!/usr/bin/env python3
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "install_manager", ROOT / ".mutation-testing/manage-installation.py"
)
MANAGER = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MANAGER
SPEC.loader.exec_module(MANAGER)

class InstallManagerTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="mutation-update-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.source = self.root / "toolkit"
        self.target = self.root / "target"
        self.target.mkdir()
        self.write_source("1")

    def write(self, base, relative, content):
        path = base / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def write_source(self, version):
        self.write(self.source, ".mutation-testing/AGENT-USAGE.md", "guide-" + version + "\n")
        self.write(self.source, ".mutation-testing/mutation-results.gradle.kts", "// task-" + version + "\n")
        self.write(self.source, ".mutation-testing/mutation-results-src/build.gradle.kts", "// build-" + version + "\n")
        self.write(self.source, ".mutation-testing/mutation-results-src/main/kotlin/ch/trancee/mutation/Results.kt", "// source-" + version + "\n")
        self.write(self.source, ".mutation-testing/mutation-results-src/test/kotlin/ch/trancee/mutation/ResultsTest.kt", "// test-" + version + "\n")
        self.write(self.source, ".omp/agents/test-quality-reviewer.md", "omp-agent-" + version + "\n")
        self.write(self.source, ".omp/skills/mutation-testing/SKILL.md", "omp-skill-" + version + "\n")
        self.write(self.source, ".github/skills/mutation-testing/SKILL.md", "copilot-skill-" + version + "\n")
        names = [
            "reviewer", "saboteur", "executor", "auditor", "refactor-specialist",
        ]
        for name in names:
            self.write(
                self.source,
                ".github/agents/mutation-testing-" + name + ".agent.md",
                "copilot-agent-" + name + "-" + version + "\n",
            )

    def run_manager(self, dry_run=False, force_paths=None, target=None, bootstrap=False):
        manager = MANAGER.InstallManager(
            target or self.target,
            repo_root=self.source,
            dry_run=dry_run,
            force_paths=force_paths,
            bootstrap=bootstrap,
        )
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            status = manager.run()
        return status, output.getvalue()

    def install_initial(self):
        status, output = self.run_manager(bootstrap=True)
        self.assertEqual(0, status, output)
        return output

    def test_clean_update_syncs_canonical_sources_to_build_src(self):
        self.install_initial()
        self.write_source("2")
        status, output = self.run_manager()
        self.assertEqual(0, status, output)
        self.assertEqual("guide-2\n", (self.target / ".mutation-testing/AGENT-USAGE.md").read_text())
        self.assertEqual("// source-2\n", (self.target / "buildSrc/src/main/kotlin/ch/trancee/mutation/Results.kt").read_text())
        self.assertEqual("// test-2\n", (self.target / "buildSrc/src/test/kotlin/ch/trancee/mutation/ResultsTest.kt").read_text())
        manifest = json.loads((self.target / ".mutation-testing/manifest.json").read_text())
        self.assertIn("buildSrc/src/main/kotlin/ch/trancee/mutation/Results.kt", manifest["managedFiles"])
        self.assertEqual(64, len(manifest["managedFiles"][".mutation-testing/AGENT-USAGE.md"]))
        self.assertIn("UPDATE .mutation-testing/AGENT-USAGE.md", output)

    def test_dry_run_previews_diffs_without_writing(self):
        self.install_initial()
        self.write_source("2")
        guide = self.target / ".mutation-testing/AGENT-USAGE.md"
        manifest = self.target / ".mutation-testing/manifest.json"
        guide_before = guide.read_bytes()
        manifest_before = manifest.read_bytes()
        status, output = self.run_manager(dry_run=True)
        self.assertEqual(0, status, output)
        self.assertIn("UPDATE .mutation-testing/AGENT-USAGE.md", output)
        self.assertIn("DRY RUN: no target files were changed", output)
        self.assertEqual(guide_before, guide.read_bytes())
        self.assertEqual(manifest_before, manifest.read_bytes())

    def test_canonical_source_conflict_blocks_generated_copy_until_canonical_is_approved(self):
        self.install_initial()
        canonical = self.target / ".mutation-testing/mutation-results-src/main/kotlin/ch/trancee/mutation/Results.kt"
        generated = self.target / "buildSrc/src/main/kotlin/ch/trancee/mutation/Results.kt"
        canonical.write_text("local canonical edit\n")
        self.write_source("2")
        original_generated = generated.read_bytes()
        status, output = self.run_manager(force_paths=["buildSrc/src/main/kotlin/ch/trancee/mutation/Results.kt"])
        self.assertEqual(2, status, output)
        self.assertIn("canonical source .mutation-testing/mutation-results-src/main/kotlin/ch/trancee/mutation/Results.kt has a local conflict", output)
        self.assertEqual("local canonical edit\n", canonical.read_text())
        self.assertEqual(original_generated, generated.read_bytes())
        status, output = self.run_manager(force_paths=[".mutation-testing/mutation-results-src/main/kotlin/ch/trancee/mutation/Results.kt"])
        self.assertEqual(0, status, output)
        self.assertEqual("// source-2\n", canonical.read_text())
        self.assertEqual(canonical.read_bytes(), generated.read_bytes())

    def test_absent_manifest_is_rejected_without_writing(self):
        marker = self.write(self.target, "keep.txt", "user data\n")
        original = marker.read_bytes()
        errors = io.StringIO()
        with contextlib.redirect_stderr(errors):
            status = MANAGER.main([str(self.target), "--dry-run"])
        self.assertEqual(1, status)
        self.assertIn("Missing .mutation-testing/manifest.json", errors.getvalue())
        self.assertIn("No files were changed", errors.getvalue())
        self.assertEqual(original, marker.read_bytes())
        self.assertEqual([marker], list(self.target.iterdir()))
        self.assertFalse((self.target / ".mutation-testing").exists())
        public_update = subprocess.run(
            [str(ROOT / "bootstrap.sh"), "update", str(self.target), "--dry-run"],
            text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30,
        )
        self.assertEqual(1, public_update.returncode, public_update.stdout + public_update.stderr)
        self.assertIn("Missing .mutation-testing/manifest.json", public_update.stderr)
        self.assertIn("No files were changed", public_update.stderr)
        self.assertEqual(original, marker.read_bytes())
        self.assertEqual([marker], list(self.target.iterdir()))

    def test_managed_local_edit_is_preserved_and_force_is_per_file(self):
        self.install_initial()
        relative = ".github/agents/mutation-testing-reviewer.agent.md"
        target_file = self.target / relative
        target_file.write_text("target customization\n")
        self.write_source("2")
        status, output = self.run_manager()
        self.assertEqual(2, status, output)
        self.assertIn("diverged from its last installed hash", output)
        self.assertEqual("target customization\n", target_file.read_text())
        status, output = self.run_manager(force_paths=[relative])
        self.assertEqual(0, status, output)
        self.assertEqual("copilot-agent-reviewer-2\n", target_file.read_text())

    def test_symlinked_destinations_and_target_roots_are_not_followed(self):
        self.install_initial()
        shutil.rmtree(self.target / ".github")
        external = self.root / "external"
        external.mkdir()
        self.write(external, "mutation-testing-reviewer.agent.md", "outside\n")
        (self.target / ".github").symlink_to(external, target_is_directory=True)
        status, output = self.run_manager()
        self.assertEqual(2, status, output)
        self.assertIn("symlinked parent directory", output)
        self.assertEqual("outside\n", (external / "mutation-testing-reviewer.agent.md").read_text())
        root_link = self.root / "target-link"
        root_link.symlink_to(self.target, target_is_directory=True)
        with self.assertRaises(MANAGER.ManagerError):
            MANAGER.InstallManager(root_link, repo_root=self.source)

    def test_symlinked_neutral_root_stops_before_writing_outside(self):
        external = self.root / "external-neutral"
        external.mkdir()
        (self.target / ".mutation-testing").symlink_to(external, target_is_directory=True)
        with self.assertRaises(MANAGER.ManagerError):
            MANAGER.InstallManager(self.target, repo_root=self.source)
        self.assertEqual([], list(external.iterdir()))

    def test_repeat_update_is_idempotent(self):
        first = self.install_initial()
        self.assertIn("UPDATED", first)
        manifest = self.target / ".mutation-testing/manifest.json"
        original = manifest.read_bytes()
        timestamp = manifest.stat().st_mtime_ns
        status, output = self.run_manager()
        self.assertEqual(0, status, output)
        self.assertIn("CURRENT .mutation-testing/manifest.json", output)
        self.assertIn("Update complete: 0 file(s) changed", output)
        self.assertEqual(original, manifest.read_bytes())
        self.assertEqual(timestamp, manifest.stat().st_mtime_ns)

    def test_manifest_records_exact_git_source_revision(self):
        subprocess.run(["git", "-C", str(self.source), "init"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["git", "-C", str(self.source), "add", "."], check=True)
        subprocess.run([
            "git", "-C", str(self.source), "-c", "user.name=Fixture",
            "-c", "user.email=fixture@example.invalid", "commit", "-m", "toolkit source fixture",
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        expected = subprocess.run(
            ["git", "-C", str(self.source), "rev-parse", "HEAD"],
            check=True, text=True, stdout=subprocess.PIPE,
        ).stdout.strip()
        status, output = self.run_manager(bootstrap=True)
        self.assertEqual(0, status, output)
        manifest = json.loads((self.target / ".mutation-testing/manifest.json").read_text())
        self.assertEqual(expected, manifest["sourceRevision"])
        self.assertFalse(manifest["sourceWorkingTreeDirty"])

    def test_force_path_traversal_is_rejected(self):
        with self.assertRaises(MANAGER.UnsafePath):
            MANAGER.InstallManager(
                self.target,
                repo_root=self.source,
                force_paths=["../../outside"],
            )

if __name__ == "__main__":
    unittest.main(verbosity=2)
