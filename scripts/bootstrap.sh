#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
VENV_DIR="${VENV_DIR:-${PROJECT_ROOT}/.venv}"

if [[ -n "${PYTHON_BIN:-}" ]]; then
    PYTHON_CMD="${PYTHON_BIN}"
elif command -v python3.10 >/dev/null 2>&1; then
    PYTHON_CMD="python3.10"
else
    echo "Error: Python 3.10 or newer is required." >&2
    echo "Set PYTHON_BIN to a compatible Python executable." >&2
    exit 1
fi

"${PYTHON_CMD}" -c \
    'import sys; assert sys.version_info >= (3, 10), f"Python 3.10+ required, found {sys.version.split()[0]}"'

"${PYTHON_CMD}" -m venv "${VENV_DIR}"
"${VENV_DIR}/bin/python" -m pip install --upgrade pip
"${VENV_DIR}/bin/python" -m pip install -r "${PROJECT_ROOT}/requirements.txt"
"${VENV_DIR}/bin/python" -m pip install --no-deps -e "${PROJECT_ROOT}"

PYTHON_BIN="${VENV_DIR}/bin/python" "${PROJECT_ROOT}/researcher.sh" --check

echo "Installation complete."
echo "Activate the environment with: source ${VENV_DIR}/bin/activate"
