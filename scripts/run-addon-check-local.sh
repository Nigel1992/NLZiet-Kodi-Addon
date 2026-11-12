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
  --exclude '*.sha256' \
  --exclude '.gitignore'

# Ensure third-party dependencies are available to the checker/runtime by
# installing them into the temporary target's resources/lib. This mirrors how
# the addon should bundle dependencies for Kodi (or you can vendor them into
# `resources/lib` in-source).
mkdir -p "${TARGET_DIR}/resources/lib"
echo "Installing runtime dependencies into ${TARGET_DIR}/resources/lib"
if ! "${PYTHON_BIN}" -m pip install --upgrade pip setuptools wheel >/dev/null 2>&1; then
  echo "WARNING: failed to upgrade pip in the current Python environment; continuing" >&2
fi
if ! "${PYTHON_BIN}" -m pip install -t "${TARGET_DIR}/resources/lib" requests >/dev/null 2>&1; then
  echo "ERROR: failed to install 'requests' into ${TARGET_DIR}/resources/lib." >&2
  echo "Either ensure the current Python can install packages, or vendor 'requests' into resources/lib:" >&2
  echo "  pip install -t resources/lib requests" >&2
  exit 1
fi

# Clean up pip-installed cache/compiled artifacts that are not allowed in addons
find "${TARGET_DIR}/resources/lib" -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
find "${TARGET_DIR}/resources/lib" -name "*.pyc" -delete 2>/dev/null || true
find "${TARGET_DIR}/resources/lib" -name "*.pyo" -delete 2>/dev/null || true
find "${TARGET_DIR}/resources/lib" -name "*.so" -delete 2>/dev/null || true
find "${TARGET_DIR}/resources/lib" -name "*.pem" -delete 2>/dev/null || true
find "${TARGET_DIR}/resources/lib" -name "py.typed" -delete 2>/dev/null || true
find "${TARGET_DIR}/resources/lib" -type d -name "bin" -exec rm -rf {} + 2>/dev/null || true
find "${TARGET_DIR}/resources/lib" -type f -name "*__mypyc*" -delete 2>/dev/null || true

for branch in "${BRANCHES[@]}"; do
  echo "=== addon-checker ${branch} START $(date -Iseconds) ==="
  "${CHECKER_BIN}" "${TARGET_DIR}" --branch "${branch}" "${EXTRA_ARGS[@]}"
  echo "=== addon-checker ${branch} END $(date -Iseconds) ==="
done

echo "=== compileall START $(date -Iseconds) ==="
"${PYTHON_BIN}" -m compileall "${TARGET_DIR}/default.py" "${TARGET_DIR}/resources"
echo "=== compileall END $(date -Iseconds) ==="

echo "Local addon-check workflow completed successfully."
