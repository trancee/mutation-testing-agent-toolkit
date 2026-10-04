#!/usr/bin/env python3
from __future__ import annotations

import argparse
from dataclasses import dataclass
import difflib
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import sys
import tempfile

FORMAT_VERSION = 1
MANIFEST_PATH = ".mutation-testing/manifest.json"
NEW_POINTER = "For mutation-testing setup, execution, audits, or troubleshooting, read [.mutation-testing/AGENT-USAGE.md](.mutation-testing/AGENT-USAGE.md) first."
IGNORED_SOURCE_DIRS = {".gradle", "build", "__pycache__"}
SKIPPED_TARGET_DIRS = {".git", ".gradle", ".kotlin", "build", "buildSrc", ".mutation-testing", ".omp"}

class ManagerError(Exception):
    pass

class UnsafePath(Exception):
    pass

@dataclass
class FilePlan:
    relative: str
    source: bytes
    current: bytes | None
    status: str
    reason: str = ""

class InstallManager:
    def __init__(self, target_path, repo_root=None, dry_run=False, force_paths=None, bootstrap=False):
        self.repo_root = Path(repo_root or Path(__file__).resolve().parents[1]).resolve(strict=True)
        self.target_root = self.resolve_target(target_path)
        self.dry_run = dry_run
        self.bootstrap = bootstrap
        self.force_paths = set(force_paths or [])
        self.previous_hashes = {}
        self.manifest_current = None
        self.asset_sources = self.collect_asset_sources()
        self.validate_force_paths()
        self.source_revision, self.source_dirty = self.read_source_revision()
        self.load_manifest()
        self.plans = {}
        self.conflicts = []
        self.conflict_diffs = []
        self.pointer_write = None

    @staticmethod
    def resolve_target(target_path):
        candidate = Path(target_path).expanduser().absolute()
        try:
            info = candidate.lstat()
        except OSError as error:
            raise ManagerError("Target path is unavailable: {}".format(error)) from error
        if stat.S_ISLNK(info.st_mode):
            raise ManagerError("Refusing a symlinked target root: {}".format(candidate))
        resolved = candidate.resolve(strict=True)
        if not resolved.is_dir():
            raise ManagerError("Target root is not a directory: {}".format(resolved))
        return resolved

    @staticmethod
    def digest(data):
        return hashlib.sha256(data).hexdigest()

    @staticmethod
    def validate_relative(relative):
        if not isinstance(relative, str) or not relative or "\\" in relative:
            raise UnsafePath("invalid relative path")
        path = PurePosixPath(relative)
        if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
            raise UnsafePath("path is not a normalized project-relative path")
        if path.as_posix() != relative:
            raise UnsafePath("path is not normalized")
        return path

    def source_file(self, relative):
        source = self.repo_root.joinpath(*self.validate_relative(relative).parts)
        try:
            info = source.lstat()
        except OSError as error:
            raise ManagerError("Missing toolkit source {}: {}".format(relative, error)) from error
        if not stat.S_ISREG(info.st_mode):
            raise ManagerError("Toolkit source is not a regular file: {}".format(source))
        return source.read_bytes()

    def add_source_tree(self, source_relative, target_prefix, assets):
        root = self.repo_root.joinpath(*self.validate_relative(source_relative).parts)
        if root.is_symlink() or not root.is_dir():
            raise ManagerError("Toolkit source directory is unavailable: {}".format(root))
        for current, directories, files in os.walk(root, topdown=True, followlinks=False):
            current_path = Path(current)
            for name in directories:
                if (current_path / name).is_symlink():
                    raise ManagerError("Refusing symlinked toolkit source directory: {}".format(current_path / name))
            directories[:] = sorted(name for name in directories if name not in IGNORED_SOURCE_DIRS)
            for name in sorted(files):
                source = current_path / name
                if source.is_symlink() or not source.is_file():
                    raise ManagerError("Refusing non-regular toolkit source: {}".format(source))
                suffix = source.relative_to(root).as_posix()
                destination = PurePosixPath(target_prefix, suffix).as_posix()
                assets[destination] = source.read_bytes()

    def collect_asset_sources(self):
        assets = {}
        fixed_files = [
            ".mutation-testing/AGENT-USAGE.md",
            ".mutation-testing/mutation-results.gradle.kts",
        ]
        for relative in fixed_files:
            assets[relative] = self.source_file(relative)
        self.add_source_tree(
            ".mutation-testing/mutation-results-src",
            ".mutation-testing/mutation-results-src",
            assets,
        )
        self.add_source_tree(".omp/agents", ".omp/agents", assets)
        self.add_source_tree(".omp/skills/mutation-testing", ".omp/skills/mutation-testing", assets)
        self.add_source_tree(".github/skills/mutation-testing", ".github/skills/mutation-testing", assets)
        copilot_agents = sorted((self.repo_root / ".github/agents").glob("mutation-testing-*.agent.md"))
        if len(copilot_agents) != 5:
            raise ManagerError("Expected the five Copilot mutation-testing agent profiles; found {}".format(len(copilot_agents)))
        for source in copilot_agents:
            if source.is_symlink() or not source.is_file():
                raise ManagerError("Refusing non-regular Copilot profile source: {}".format(source))
            assets[PurePosixPath(".github/agents", source.name).as_posix()] = source.read_bytes()
        generated = {}
        canonical_prefix = ".mutation-testing/mutation-results-src/"
        for relative, data in tuple(assets.items()):
            if not relative.startswith(canonical_prefix):
                continue
            suffix = relative[len(canonical_prefix):]
            if suffix == "build.gradle.kts":
                generated["buildSrc/build.gradle.kts"] = data
            elif suffix.startswith("main/") or suffix.startswith("test/"):
                generated[PurePosixPath("buildSrc/src", suffix).as_posix()] = data
        assets.update(generated)
        return dict(sorted(assets.items()))

    def validate_force_paths(self):
        for relative in self.force_paths:
            self.validate_relative(relative)
            if relative not in self.asset_sources:
                raise ManagerError("--force path is not a managed toolkit file: {}".format(relative))

    def read_source_revision(self):
        try:
            revision = subprocess.run(
                ["git", "-C", str(self.repo_root), "rev-parse", "HEAD"],
                check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=10,
            ).stdout.strip()
            dirty_output = subprocess.run(
                ["git", "-C", str(self.repo_root), "status", "--porcelain", "--untracked-files=normal"],
                check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=10,
            ).stdout
            return revision, bool(dirty_output)
        except (OSError, subprocess.SubprocessError):
            return None, None

    def safe_read(self, relative):
        parts = self.validate_relative(relative).parts
        cursor = self.target_root
        for part in parts[:-1]:
            cursor = cursor / part
            try:
                info = cursor.lstat()
            except FileNotFoundError:
                return None
            except OSError as error:
                raise UnsafePath("cannot inspect {}: {}".format(cursor, error)) from error
            if stat.S_ISLNK(info.st_mode):
                raise UnsafePath("symlinked parent directory: {}".format(cursor))
            if not stat.S_ISDIR(info.st_mode):
                raise UnsafePath("parent path is not a directory: {}".format(cursor))
        destination = cursor / parts[-1]
        try:
            info = destination.lstat()
        except FileNotFoundError:
            return None
        except OSError as error:
            raise UnsafePath("cannot inspect {}: {}".format(destination, error)) from error
        if stat.S_ISLNK(info.st_mode):
            raise UnsafePath("symlinked file: {}".format(destination))
        if not stat.S_ISREG(info.st_mode):
            raise UnsafePath("destination is not a regular file: {}".format(destination))
        return destination.read_bytes()

    def load_manifest(self):
        try:
            data = self.safe_read(MANIFEST_PATH)
        except UnsafePath as error:
            raise ManagerError("Unsafe installation manifest path: {}".format(error)) from error
        if data is None:
            if not self.bootstrap:
                raise ManagerError(
                    "Missing {}: update requires a manifest-managed installation. "
                    "No files were changed; run the toolkit checkout's `bootstrap.sh install <project-path>` "
                    "only if you intend to install the current layout.".format(MANIFEST_PATH)
                )
            return
        try:
            manifest = json.loads(data.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ManagerError("Invalid installation manifest; preserve it and repair it manually: {}".format(error)) from error
        if not isinstance(manifest, dict) or type(manifest.get("formatVersion")) is not int or manifest.get("formatVersion") != FORMAT_VERSION:
            raise ManagerError("Unsupported installation manifest format; no files were changed")
        managed = manifest.get("managedFiles")
        if not isinstance(managed, dict):
            raise ManagerError("Invalid installation manifest managedFiles map; no files were changed")
        for relative, digest in managed.items():
            try:
                self.validate_relative(relative)
            except UnsafePath as error:
                raise ManagerError("Invalid path in installation manifest: {}".format(error)) from error
            if not isinstance(digest, str) or re.fullmatch(r"[0-9a-f]{64}", digest) is None:
                raise ManagerError("Invalid managed-file hash in installation manifest: {}".format(relative))
        self.previous_hashes = managed
        self.manifest_current = data

    def record_conflict(self, relative, reason, current=None, desired=None, diff_name=None):
        message = "CONFLICT {}: {}".format(relative, reason)
        self.conflicts.append(message)
        print(message)
        if current is not None and desired is not None:
            self.conflict_diffs.append((diff_name or relative, current, desired))

    def plan_asset(self, relative, source, blocked_reason=None):
        try:
            current = self.safe_read(relative)
        except UnsafePath as error:
            plan = FilePlan(relative, source, None, "conflict", str(error))
            self.plans[relative] = plan
            self.record_conflict(relative, str(error))
            return plan
        source_hash = self.digest(source)
        current_hash = self.digest(current) if current is not None else None
        force = relative in self.force_paths
        if current_hash == source_hash:
            plan = FilePlan(relative, source, current, "current")
            self.plans[relative] = plan
            return plan
        if blocked_reason is not None:
            reason = "{}; generated copy was not changed".format(blocked_reason)
            plan = FilePlan(relative, source, current, "conflict", reason)
            self.plans[relative] = plan
            self.record_conflict(relative, reason, current, source)
            return plan
        if force:
            plan = FilePlan(relative, source, current, "force-create" if current is None else "force")
            self.plans[relative] = plan
            return plan
        if current is None:
            baseline = self.previous_hashes.get(relative)
            if baseline is not None:
                reason = "managed file is missing; refusing to recreate it without per-file approval"
                plan = FilePlan(relative, source, current, "conflict", reason)
                self.plans[relative] = plan
                self.record_conflict(relative, reason, None, source)
                return plan
            plan = FilePlan(relative, source, current, "create")
            self.plans[relative] = plan
            return plan
        baseline = self.previous_hashes.get(relative)
        if baseline is not None and current_hash == baseline:
            plan = FilePlan(relative, source, current, "update")
            self.plans[relative] = plan
            return plan
        if baseline is None:
            reason = "untracked file differs from current toolkit source and was preserved"
        else:
            reason = "managed file diverged from its last installed hash and was preserved"
        plan = FilePlan(relative, source, current, "conflict", reason)
        self.plans[relative] = plan
        self.record_conflict(relative, reason, current, source)
        return plan

    def plan_assets(self):
        canonical_status = {}
        canonical_prefix = ".mutation-testing/mutation-results-src/"
        for relative in self.asset_sources:
            if relative.startswith("buildSrc/"):
                continue
            plan = self.plan_asset(relative, self.asset_sources[relative])
            if relative.startswith(canonical_prefix):
                canonical_status[relative] = plan.status
        for relative in self.asset_sources:
            if not relative.startswith("buildSrc/"):
                continue
            matching_source = None
            if relative == "buildSrc/build.gradle.kts":
                matching_source = canonical_prefix + "build.gradle.kts"
            elif relative.startswith("buildSrc/src/"):
                matching_source = canonical_prefix + relative[len("buildSrc/src/"):]
            blocked = None
            if matching_source is not None and canonical_status.get(matching_source) in {"conflict", "blocked"}:
                blocked = "canonical source {} has a local conflict".format(matching_source)
            self.plan_asset(relative, self.asset_sources[relative], blocked)

    def source_is_ready(self, relative):
        plan = self.plans.get(relative)
        return plan is not None and plan.status not in {"conflict", "blocked"}

    def plan_agent_pointer(self):
        if not self.source_is_ready(".mutation-testing/AGENT-USAGE.md"):
            return
        try:
            current = self.safe_read("AGENTS.md")
        except UnsafePath as error:
            self.record_conflict("AGENTS.md", "discovery pointer destination is unsafe: {}".format(error))
            return
        if current is None:
            updated = (NEW_POINTER + "\n").encode("utf-8")
            self.pointer_write = FilePlan("AGENTS.md", updated, None, "create", "discovery pointer")
            return
        try:
            text = current.decode("utf-8")
        except UnicodeDecodeError:
            self.record_conflict("AGENTS.md", "discovery pointer destination is not UTF-8")
            return
        if any(line.rstrip("\r\n") == NEW_POINTER for line in text.splitlines(keepends=True)):
            return
        separator = "" if not text or text.endswith("\n\n") else ("\n" if text.endswith("\n") else "\n\n")
        updated = text + separator + NEW_POINTER + "\n"
        new_data = updated.encode("utf-8")
        if new_data != current:
            self.pointer_write = FilePlan("AGENTS.md", new_data, current, "update", "discovery pointer")

    @staticmethod
    def sanitize(value):
        result = []
        for char in value:
            code = ord(char)
            if char in "\t" or code >= 32 and code != 127:
                result.append(char)
            else:
                result.append("\\x{:02x}".format(code))
        return "".join(result)

    def show_diff(self, name, current, desired):
        try:
            before = current.decode("utf-8").splitlines(keepends=True) if current is not None else []
            after = desired.decode("utf-8").splitlines(keepends=True)
        except UnicodeDecodeError:
            before_hash = self.digest(current) if current is not None else "missing"
            after_hash = self.digest(desired)
            print("      binary/non-UTF-8 diff: current={} proposed={}".format(before_hash, after_hash))
            return
        lines = list(difflib.unified_diff(before, after, fromfile="target/" + name, tofile="toolkit/" + name))
        limit = 100
        for line in lines[:limit]:
            print("      " + self.sanitize(line.rstrip("\n")))
        if len(lines) > limit:
            print("      ... diff truncated after {} lines ...".format(limit))

    def report_plan(self):
        revision = self.source_revision or "unavailable"
        state = "unknown" if self.source_dirty is None else ("dirty" if self.source_dirty else "clean")
        print("SOURCE revision={} working-tree={}".format(revision, state))
        for relative, plan in sorted(self.plans.items()):
            if plan.status == "create":
                print("CREATE {}".format(relative))
            elif plan.status == "update":
                print("UPDATE {}".format(relative))
            elif plan.status in {"force", "force-create"}:
                print("FORCE {}".format(relative))
            elif plan.status == "current":
                print("CURRENT {}".format(relative))
            if self.dry_run and plan.status in {"create", "update", "force", "force-create"}:
                self.show_diff(relative, plan.current, plan.source)
        if self.pointer_write is not None:
            print("{} {} ({})".format("CREATE" if self.pointer_write.current is None else "UPDATE", self.pointer_write.relative, self.pointer_write.reason))
            if self.dry_run:
                self.show_diff(self.pointer_write.relative, self.pointer_write.current, self.pointer_write.source)
        for name, current, desired in self.conflict_diffs:
            self.show_diff(name, current, desired)
        if self.dry_run:
            print("DRY RUN: no target files were changed")

    def write_bytes(self, relative, data, mode=None):
        parts = self.validate_relative(relative).parts
        parent = self.target_root
        for part in parts[:-1]:
            parent = parent / part
            try:
                info = parent.lstat()
            except FileNotFoundError:
                parent.mkdir()
                info = parent.lstat()
            if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
                raise UnsafePath("unsafe parent path during write: {}".format(parent))
        destination = parent / parts[-1]
        try:
            info = destination.lstat()
        except FileNotFoundError:
            info = None
        if info is not None and (stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode)):
            raise UnsafePath("unsafe destination during write: {}".format(destination))
        if mode is None:
            mode = stat.S_IMODE(info.st_mode) if info is not None else 0o644
        descriptor, temporary = tempfile.mkstemp(prefix=".mutation-toolkit-", dir=str(parent))
        try:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(data)
            os.chmod(temporary, mode)
            os.replace(temporary, destination)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    def apply_asset_writes(self):
        changed = 0
        failed_assets = set()
        canonical_prefix = ".mutation-testing/mutation-results-src/"
        for relative, plan in sorted(self.plans.items()):
            if plan.status not in {"create", "update", "force", "force-create"}:
                continue
            if relative.startswith("buildSrc/") and relative not in self.force_paths:
                if relative == "buildSrc/build.gradle.kts":
                    canonical = canonical_prefix + "build.gradle.kts"
                else:
                    canonical = canonical_prefix + relative[len("buildSrc/src/"):]
                if canonical in failed_assets:
                    plan.status = "conflict"
                    failed_assets.add(relative)
                    self.record_conflict(relative, "canonical source write failed; generated copy was not changed")
                    continue
            source_path = self.repo_root.joinpath(*self.validate_relative(relative).parts)
            mode = stat.S_IMODE(source_path.stat().st_mode) if source_path.exists() else 0o644
            try:
                self.write_bytes(relative, plan.source, mode)
            except (OSError, UnsafePath) as error:
                plan.status = "conflict"
                failed_assets.add(relative)
                self.record_conflict(relative, "write failed: {}".format(error))
                continue
            changed += 1
        guide_plan = self.plans.get(".mutation-testing/AGENT-USAGE.md")
        if self.pointer_write is not None:
            if guide_plan is None or guide_plan.status == "conflict":
                self.record_conflict("AGENTS.md", "neutral guide was not installed; discovery pointer was preserved")
            else:
                try:
                    self.write_bytes(self.pointer_write.relative, self.pointer_write.source)
                except (OSError, UnsafePath) as error:
                    self.record_conflict(self.pointer_write.relative, "discovery pointer update failed: {}".format(error))
                else:
                    changed += 1
        return changed

    def write_manifest(self):
        clean_status = {"create", "update", "current", "force", "force-create"}
        if not self.dry_run:
            for relative, plan in self.plans.items():
                if plan.status not in clean_status:
                    continue
                try:
                    installed = self.safe_read(relative)
                except UnsafePath as error:
                    plan.status = "conflict"
                    self.record_conflict(relative, "post-write verification failed: {}".format(error))
                    continue
                if installed != plan.source:
                    plan.status = "conflict"
                    self.record_conflict(relative, "post-write verification did not match the proposed hash", installed, plan.source)
        managed = dict(self.previous_hashes)
        clean_count = 0
        for relative, plan in self.plans.items():
            if plan.status in clean_status:
                managed[relative] = self.digest(plan.source)
                clean_count += 1
        if clean_count == 0:
            print("MANIFEST unchanged: no toolkit files had a safe baseline")
            return
        payload = {
            "formatVersion": FORMAT_VERSION,
            "sourceRevision": self.source_revision,
            "sourceWorkingTreeDirty": self.source_dirty,
            "managedFiles": dict(sorted(managed.items())),
        }
        encoded = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")
        if self.dry_run:
            if encoded != self.manifest_current:
                print("UPDATE {} (source revision and managed-file hashes)".format(MANIFEST_PATH))
                self.show_diff(MANIFEST_PATH, self.manifest_current, encoded)
            else:
                print("CURRENT {}".format(MANIFEST_PATH))
            return
        if encoded == self.manifest_current:
            print("CURRENT {}".format(MANIFEST_PATH))
            return
        try:
            self.write_bytes(MANIFEST_PATH, encoded)
        except (OSError, UnsafePath) as error:
            self.record_conflict(MANIFEST_PATH, "manifest write failed: {}".format(error))
            return
        print("UPDATED {}".format(MANIFEST_PATH))

    def run(self):
        self.plan_assets()
        self.plan_agent_pointer()
        self.report_plan()
        if self.dry_run:
            self.write_manifest()
            if self.conflicts:
                print("{} conflict(s); no files were changed".format(len(self.conflicts)))
                return 2
            return 0
        changed = self.apply_asset_writes()
        self.write_manifest()
        if self.conflicts:
            print("Update applied to safe files; {} conflict(s) were preserved".format(len(self.conflicts)))
            return 2
        print("Update complete: {} file(s) changed".format(changed))
        return 0

def main(argv=None):
    if sys.version_info < (3, 10):
        print("[mutation-toolkit-update] Python 3.10 or newer is required.", file=sys.stderr)
        return 1
    parser = argparse.ArgumentParser(
        description="Safely update a manifest-managed installation from this local toolkit checkout."
    )
    parser.add_argument("--bootstrap", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("project_path", nargs="?", default=".", help="Target project root (default: current directory)")
    parser.add_argument("--dry-run", action="store_true", help="Preview writes, conflicts, and diffs without changing files")
    parser.add_argument(
        "--force", action="append", default=[], metavar="RELATIVE_PATH",
        help="Approve replacing one exact managed path; repeat for each file whose diff you reviewed",
    )
    arguments = parser.parse_args(argv)
    try:
        manager = InstallManager(
            arguments.project_path,
            dry_run=arguments.dry_run,
            force_paths=arguments.force,
            bootstrap=arguments.bootstrap,
        )
        return manager.run()
    except (ManagerError, UnsafePath, OSError) as error:
        print("[mutation-toolkit-update] {}".format(error), file=sys.stderr)
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
