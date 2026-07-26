#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

if [[ -n "${PYTHON_BIN:-}" ]]; then
    PYTHON_CMD="${PYTHON_BIN}"
elif [[ -x "${PROJECT_ROOT}/.venv/bin/python" ]]; then
    PYTHON_CMD="${PROJECT_ROOT}/.venv/bin/python"
elif command -v python3.10 >/dev/null 2>&1; then
    PYTHON_CMD="python3.10"
else
    PYTHON_CMD="python3"
fi

SMOKE_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/s-researcher-cases.XXXXXX")"
trap 'rm -rf "${SMOKE_ROOT}"' EXIT

COMMON_ARGS=(
    --replicate 1
    --smoke
    --prepare-only
    --model-config "${PROJECT_ROOT}/config/model_config.json"
    --artifact-root "${SMOKE_ROOT}"
)

"${PYTHON_CMD}" "${PROJECT_ROOT}/examples/paper_cases/run_case.py" \
    --case cultural_dissemination \
    "${COMMON_ARGS[@]}"

"${PYTHON_CMD}" "${PROJECT_ROOT}/examples/paper_cases/run_case.py" \
    --case teacher_attention \
    --condition expression \
    "${COMMON_ARGS[@]}"

"${PYTHON_CMD}" "${PROJECT_ROOT}/examples/paper_cases/run_case.py" \
    --case public_goods \
    --condition voluntary-high \
    "${COMMON_ARGS[@]}"

check_relationship_file() {
    local path="$1"
    local expected_lines="$2"
    if [[ ! -s "${path}" ]]; then
        echo "Error: relationship file was not generated: ${path}" >&2
        exit 1
    fi
    local actual_lines
    actual_lines="$(wc -l < "${path}" | tr -d ' ')"
    if [[ "${actual_lines}" != "${expected_lines}" ]]; then
        echo "Error: ${path} has ${actual_lines} lines; expected ${expected_lines}." >&2
        exit 1
    fi
}

check_relationship_file \
    "${SMOKE_ROOT}/cultural_dissemination/baseline/replicate_1/profiles/Relationship.csv" \
    25
check_relationship_file \
    "${SMOKE_ROOT}/teacher_attention/expression/replicate_1/profiles/Relationship.csv" \
    11
check_relationship_file \
    "${SMOKE_ROOT}/public_goods/voluntary-high/replicate_1/profiles/Relationship.csv" \
    11

echo "Paper case preparation smoke test passed."
