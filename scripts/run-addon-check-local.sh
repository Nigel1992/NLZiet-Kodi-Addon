#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

if [[ -x "${REPO_ROOT}/.venv/bin/python" ]]; then
  PYTHON_BIN="${REPO_ROOT}/.venv/bin/python"
else
  PYTHON_BIN="python3"
fi

if [[ -x "${REPO_ROOT}/.venv/bin/kodi-addon-checker" ]]; then
  CHECKER_BIN="${REPO_ROOT}/.venv/bin/kodi-addon-checker"
elif command -v kodi-addon-checker >/dev/null 2>&1; then
  CHECKER_BIN="$(command -v kodi-addon-checker)"
else
  echo "ERROR: kodi-addon-checker not found. Install with: pip install kodi-addon-checker" >&2
  exit 1
fi

EXTRA_ARGS=()
BRANCHES=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --pr|--PR)
      EXTRA_ARGS+=("--PR")
      shift
      ;;
    --branch)
      if [[ $# -lt 2 ]]; then
        echo "ERROR: --branch requires a value." >&2
        exit 2
      fi
      BRANCHES+=("$2")
      shift 2
      ;;
    *)
      echo "ERROR: Unknown argument: $1" >&2
      echo "Usage: scripts/run-addon-check-local.sh [--branch <branch>]... [--pr]" >&2
      exit 2
      ;;
  esac
done

if [[ ${#BRANCHES[@]} -eq 0 ]]; then
  BRANCHES=(nexus omega piers)
fi

ADDON_ID="$(${PYTHON_BIN} - <<'PY'
from xml.etree import ElementTree as ET
root = ET.parse('addon.xml').getroot()
print(root.attrib['id'])
PY
)"

WORKDIR="$(mktemp -d "${TMPDIR:-/tmp}/addon-check-src-XXXXXX")"
TARGET_DIR="${WORKDIR}/${ADDON_ID}"
trap 'rm -rf "${WORKDIR}"' EXIT

mkdir -p "${TARGET_DIR}"

# Mirror CI source filtering so checker only sees addon-relevant files.
rsync -a "${REPO_ROOT}/" "${TARGET_DIR}/" \
  --exclude '.git/' \
  --exclude '.github/' \
  --exclude '.venv/' \
  --exclude 'venv/' \
  --exclude '.env/' \
  --exclude '.vscode/' \
  --exclude '.idea/' \
  --exclude '.cache/' \
  --exclude 'cache/' \
  --exclude '__pycache__/' \
  --exclude '.pytest_cache/' \
  --exclude '.mypy_cache/' \
  --exclude '.ruff_cache/' \
  --exclude '.tox/' \
  --exclude '.nox/' \
  --exclude '.addon-check-run.log' \
  --exclude '*.pyc' \
  --exclude '*.pyo' \
  --exclude '.DS_Store' \
  --exclude 'tests/' \
  --exclude 'scripts/' \
  --exclude 'package_build/' \
  --exclude 'package_clean/' \
  --exclude '*.zip' \
  --exclude '.gitignore'

for branch in "${BRANCHES[@]}"; do
  echo "=== addon-checker ${branch} START $(date -Iseconds) ==="
  "${CHECKER_BIN}" "${TARGET_DIR}" --branch "${branch}" "${EXTRA_ARGS[@]}"
  echo "=== addon-checker ${branch} END $(date -Iseconds) ==="
done

echo "=== compileall START $(date -Iseconds) ==="
"${PYTHON_BIN}" -m compileall "${REPO_ROOT}/default.py" "${REPO_ROOT}/resources"
echo "=== compileall END $(date -Iseconds) ==="

echo "Local addon-check workflow completed successfully."
