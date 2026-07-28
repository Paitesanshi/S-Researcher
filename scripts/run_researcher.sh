#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
RESEARCHER_PY="${PROJECT_ROOT}/src/researcher.py"
INVOCATION_DIR="$(pwd)"

if [[ -n "${PYTHON_BIN:-}" ]]; then
    PYTHON_CMD="${PYTHON_BIN}"
elif [[ -x "${PROJECT_ROOT}/.venv/bin/python" ]]; then
    PYTHON_CMD="${PROJECT_ROOT}/.venv/bin/python"
elif command -v python3.10 >/dev/null 2>&1; then
    PYTHON_CMD="python3.10"
else
    PYTHON_CMD="python3"
fi

usage() {
    cat <<'EOF'
OneSim Researcher command-line workflow

Usage:
  ./researcher.sh --project-name NAME [OPTIONS]

Required for a new full workflow:
  -p, --project-name NAME      Output project name
  -s, --scenario TEXT          Research scenario (or use --topic)

Options:
  -q, --question TEXT          Research question
  -t, --topic TEXT             Legacy research-topic input
      --theory TEXT            Social-science theory
      --condition TEXT         Theory condition
      --observation TEXT       Observed phenomenon
      --paradigm NAME          auto|deductive|inductive|abductive
      --phase NAME             design|scenario|execute|analysis|report|full
  -m, --model-name NAME        Model config_name (default: default-chat)
  -c, --model-config PATH      Model JSON (default: config/model_config.json)
  -d, --projects-dir DIR       Output base directory (default: projects)
      --config PATH            Research workflow JSON
      --skip-design            Skip design in supported modes
      --skip-execution         Skip execution in supported modes
      --skip-report            Skip report generation in supported modes
  -h, --help                   Show this help

Environment:
  LLM_API_KEY                  API credential for the bundled configuration
  LLM_MODEL                    API model identifier for the bundled configuration
  LLM_BASE_URL                 OpenAI-compatible base URL (default: OpenAI)
  LLM_PROVIDER                 OneSim provider adapter (default: openai)
  OPENAI_* / DEEPSEEK_*        Accepted as backward-compatible aliases
  PYTHON_BIN                   Optional Python executable override
EOF
}

if [[ ! -f "${RESEARCHER_PY}" ]]; then
    echo "Error: researcher entry point not found: ${RESEARCHER_PY}" >&2
    exit 1
fi

PROJECT_NAME=""
MODEL_NAME=""
MODEL_CONFIG=""
ARGS=()

require_value() {
    if [[ $# -lt 2 || -z "${2:-}" ]]; then
        echo "Error: option $1 requires a value" >&2
        exit 2
    fi
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        -p|--project-name|--project_name)
            require_value "$@"
            PROJECT_NAME="$2"
            ARGS+=("--project_name" "$2")
            shift 2
            ;;
        -s|--scenario)
            require_value "$@"
            ARGS+=("--scenario" "$2")
            shift 2
            ;;
        -q|--question)
            require_value "$@"
            ARGS+=("--question" "$2")
            shift 2
            ;;
        -t|--topic)
            require_value "$@"
            ARGS+=("--topic" "$2")
            shift 2
            ;;
        --theory|--condition|--observation|--paradigm|--phase|--config)
            require_value "$@"
            ARGS+=("$1" "$2")
            shift 2
            ;;
        -m|--model-name|--model_name)
            require_value "$@"
            MODEL_NAME="$2"
            shift 2
            ;;
        -c|--model-config|--model_config)
            require_value "$@"
            MODEL_CONFIG="$2"
            shift 2
            ;;
        -d|--projects-dir|--projects_dir)
            require_value "$@"
            ARGS+=("--projects_dir" "$2")
            shift 2
            ;;
        --skip-design|--skip_design)
            ARGS+=("--skip_design")
            shift
            ;;
        --skip-execution|--skip_execution)
            ARGS+=("--skip_execution")
            shift
            ;;
        --skip-report|--skip_report)
            ARGS+=("--skip_report")
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Error: unknown option: $1" >&2
            usage >&2
            exit 2
            ;;
    esac
done

cd "${PROJECT_ROOT}"

export PYTHONDONTWRITEBYTECODE="${PYTHONDONTWRITEBYTECODE:-1}"
export MPLBACKEND="${MPLBACKEND:-Agg}"

normalize_model_environment() {
    # Generic variables take precedence. Standard OpenAI and the previously
    # documented DeepSeek variables remain accepted for convenience.
    if [[ -z "${LLM_API_KEY:-}" && -n "${OPENAI_API_KEY:-}" ]]; then
        export LLM_API_KEY="${OPENAI_API_KEY}"
        export LLM_PROVIDER="${LLM_PROVIDER:-openai}"
        export LLM_BASE_URL="${LLM_BASE_URL:-${OPENAI_BASE_URL:-https://api.openai.com/v1}}"
        if [[ -n "${OPENAI_MODEL:-}" ]]; then
            export LLM_MODEL="${OPENAI_MODEL}"
        fi
    elif [[ -z "${LLM_API_KEY:-}" && -n "${DEEPSEEK_API_KEY:-}" ]]; then
        export LLM_API_KEY="${DEEPSEEK_API_KEY}"
        export LLM_PROVIDER="${LLM_PROVIDER:-deepseek}"
        export LLM_BASE_URL="${LLM_BASE_URL:-${DEEPSEEK_BASE_URL:-https://api.deepseek.com}}"
        export LLM_MODEL="${LLM_MODEL:-${DEEPSEEK_MODEL:-deepseek-v4-flash}}"
    fi

    if [[ -z "${LLM_MODEL:-}" && -n "${OPENAI_MODEL:-}" ]]; then
        export LLM_MODEL="${OPENAI_MODEL}"
    elif [[ -z "${LLM_MODEL:-}" && -n "${DEEPSEEK_MODEL:-}" ]]; then
        export LLM_MODEL="${DEEPSEEK_MODEL}"
    fi
}

normalize_model_environment

if [[ -z "${MODEL_NAME}" ]]; then
    MODEL_NAME="default-chat"
fi

BUNDLED_MODEL_CONFIG=0
if [[ -z "${MODEL_CONFIG}" ]]; then
    MODEL_CONFIG="${PROJECT_ROOT}/config/model_config.json"
    BUNDLED_MODEL_CONFIG=1
elif [[ "${MODEL_CONFIG}" != /* ]]; then
    MODEL_CONFIG="${INVOCATION_DIR}/${MODEL_CONFIG}"
fi

MPL_CACHE_DIR="${MPLCONFIGDIR:-${TMPDIR:-/tmp}/onesim-matplotlib-${UID:-user}}"
mkdir -p "${MPL_CACHE_DIR}"
export MPLCONFIGDIR="${MPL_CACHE_DIR}"
XDG_CACHE_DIR="${XDG_CACHE_HOME:-${TMPDIR:-/tmp}/onesim-cache-${UID:-user}}"
mkdir -p "${XDG_CACHE_DIR}"
export XDG_CACHE_HOME="${XDG_CACHE_DIR}"

"${PYTHON_CMD}" -c 'import sys; assert sys.version_info >= (3, 10), f"Python 3.10+ required, found {sys.version.split()[0]}"'

if [[ -z "${PROJECT_NAME}" ]]; then
    echo "Error: --project-name is required" >&2
    usage >&2
    exit 2
fi

if [[ "${BUNDLED_MODEL_CONFIG}" -eq 1 && -z "${LLM_API_KEY:-}" ]]; then
    echo "Error: LLM_API_KEY is not set for the bundled model configuration." >&2
    echo "Set LLM_API_KEY and LLM_MODEL, or pass a different --model-config." >&2
    exit 2
fi
if [[ "${BUNDLED_MODEL_CONFIG}" -eq 1 && -z "${LLM_MODEL:-}" ]]; then
    echo "Error: LLM_MODEL is not set for the bundled model configuration." >&2
    echo "Set LLM_MODEL, or pass a different --model-config." >&2
    exit 2
fi

ARGS+=("--model_name" "${MODEL_NAME}" "--model_config" "${MODEL_CONFIG}")

echo "Running researcher workflow for project: ${PROJECT_NAME}"
exec "${PYTHON_CMD}" "${RESEARCHER_PY}" "${ARGS[@]}"
