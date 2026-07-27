#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

if [[ -n "${PYTHON_BIN:-}" ]]; then
    PYTHON_CMD="${PYTHON_BIN}"
elif command -v python3.10 >/dev/null 2>&1; then
    PYTHON_CMD="python3.10"
elif command -v python3 >/dev/null 2>&1; then
    PYTHON_CMD="python3"
else
    echo "Error: Python 3.10 or newer is required." >&2
    exit 1
fi

"${PYTHON_CMD}" -c \
    'import sys; assert sys.version_info >= (3, 10), f"Python 3.10+ required, found {sys.version.split()[0]}"'

cd "${PROJECT_ROOT}"
"${PYTHON_CMD}" -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pip install --no-deps -e .

echo
echo "Setup complete. Run ./researcher.sh --help to view workflow options."
