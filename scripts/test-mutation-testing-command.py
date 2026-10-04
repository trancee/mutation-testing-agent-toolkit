#!/usr/bin/env python3
"""Verify bootstrap.sh dispatches install/update with intact arguments."""

import json
import os
from pathlib import Path
import subprocess
import sys
import shutil
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
COMMAND = ROOT / "bootstrap.sh"
BOOTSTRAP = ROOT / ".mutation-testing/bootstrap-mutation-testing.sh"
MANAGER = ROOT / ".mutation-testing/manage-installation.py"
REAL_BASH = shutil.which("bash")


class BootstrapCommandTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="bootstrap-command-")
        self.addCleanup(self.temporary.cleanup)
        self.bin_dir = Path(self.temporary.name) / "bin"
        self.bin_dir.mkdir()
        self.write_shim(
            "bash",
            "import json, sys\nprint(json.dumps(sys.argv[1:]))\n",
        )
        self.write_shim(
            "python3",
            "import json, os, sys\n"
            "args = sys.argv[1:]\n"
            "if args and args[0] == '-c':\n"
            "    if 'version_info' not in args[1]: raise SystemExit(93)\n"
            "    raise SystemExit(0 if os.environ.get('FAKE_PYTHON_310', 'yes') == 'yes' else 1)\n"
            "print(json.dumps(args))\n",
        )
        self.environment = os.environ.copy()
        self.environment["PATH"] = str(self.bin_dir) + os.pathsep + self.environment.get("PATH", "")

    def write_shim(self, name, body):
        shim = self.bin_dir / name
        shim.write_text(f"#!{sys.executable}\n{body}", encoding="utf-8")
        shim.chmod(0o755)
        return shim

    def run_command(self, *arguments, environment=None):
        return subprocess.run(
            [REAL_BASH, str(COMMAND), *arguments], text=True, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, env=environment or self.environment, timeout=30,
        )

    def test_entrypoint_is_executable(self):
        self.assertTrue(os.access(COMMAND, os.X_OK))

    def test_install_dispatches_bootstrap_and_preserves_argument_boundaries(self):
        target = "/tmp/project path with spaces"
        result = self.run_command("install", target, "--kmp", "--module", ":service")
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(
            [str(BOOTSTRAP), target, "--kmp", "--module", ":service"],
            json.loads(result.stdout),
        )

    def test_update_dispatches_manager_and_preserves_argument_boundaries(self):
        target = "/tmp/target project"
        force_path = ".github/agents/reviewer with space.agent.md"
        result = self.run_command("update", target, "--dry-run", "--force", force_path)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(
            [str(MANAGER), target, "--dry-run", "--force", force_path],
            json.loads(result.stdout),
        )

    def test_invalid_calls_print_usage(self):
        invalid = self.run_command("setup")
        self.assertEqual(2, invalid.returncode)
        self.assertIn("Usage:", invalid.stderr)
        self.assertIn("install", invalid.stderr)
        self.assertIn("update", invalid.stderr)
        help_result = self.run_command("--help")
        self.assertEqual(0, help_result.returncode, help_result.stderr)
        self.assertIn("Usage:", help_result.stdout)
        reserved = self.run_command("update", "--bootstrap", "/tmp/untracked")
        self.assertEqual(2, reserved.returncode)
        self.assertIn("reserved for the install implementation", reserved.stderr)
        self.assertIn("Usage:", reserved.stderr)

    def test_python_310_gate_stops_before_dispatch(self):
        environment = self.environment.copy()
        environment["FAKE_PYTHON_310"] = "no"
        result = self.run_command("install", "/tmp/project", environment=environment)
        self.assertEqual(1, result.returncode)
        self.assertIn("Python 3.10 or newer", result.stderr)
        self.assertEqual("", result.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
