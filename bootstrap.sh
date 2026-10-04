#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  ./bootstrap.sh install [project-path] [--kmp] [--junit4] [--module :path]
  ./bootstrap.sh update [project-path] [--dry-run] [--force RELATIVE_PATH]...
  ./bootstrap.sh --help

Commands:
  install Install and configure mutation testing in a Kotlin project.
  update  Safely update an installation with .mutation-testing/manifest.json.

Python 3.10 or newer is required. Update reads only this local toolkit checkout.
USAGE
}

if [[ $# -eq 0 ]]; then
  usage >&2
  exit 2
fi

command_name="$1"
shift
case "$command_name" in
  -h|--help|help)
    if [[ $# -ne 0 ]]; then
      echo "Error: help does not accept additional arguments." >&2
      usage >&2
      exit 2
    fi
    usage
    exit 0
    ;;
  install|update)
    if [[ $# -gt 0 && "$1" == "--help" ]]; then
      usage
      exit 0
    fi
    ;;
  *)
    echo "Error: expected the install or update subcommand, got '$command_name'." >&2
    usage >&2
    exit 2
    ;;
esac

if [[ "$command_name" == "update" ]]; then
  for argument in "$@"; do
    if [[ "$argument" == "--bootstrap" ]]; then
      echo "Error: --bootstrap is reserved for the install implementation." >&2
      usage >&2
      exit 2
    fi
  done
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "Error: Python 3.10 or newer is required by the bootstrap command." >&2
  exit 1
fi
if ! python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)'; then
  echo "Error: Python 3.10 or newer is required by the bootstrap command." >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
case "$command_name" in
  install)
    exec bash "$SCRIPT_DIR/.mutation-testing/bootstrap-mutation-testing.sh" "$@"
    ;;
  update)
    exec python3 "$SCRIPT_DIR/.mutation-testing/manage-installation.py" "$@"
    ;;
esac
