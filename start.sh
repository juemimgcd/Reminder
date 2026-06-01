#!/usr/bin/env bash

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRONTEND_DIR="${REPO_ROOT}/app/mneme_frontend_v0.2.1"

BACKEND_ONLY=0
FRONTEND_ONLY=0
DRY_RUN=0
BACKEND_HOST="127.0.0.1"
BACKEND_PORT="8000"

usage() {
  cat <<'EOF'
Usage: ./start.sh [options]

Start the FastAPI backend and embedded frontend watcher together.

Options:
  --backend-only          Only start the backend.
  --frontend-only         Only start the frontend watcher.
  --backend-host HOST     Backend host. Default: 127.0.0.1
  --backend-port PORT     Backend port. Default: 8000
  --dry-run               Print commands without starting processes.
  -h, --help              Show this help message.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --backend-only)
      BACKEND_ONLY=1
      shift
      ;;
    --frontend-only)
      FRONTEND_ONLY=1
      shift
      ;;
    --backend-host)
      BACKEND_HOST="${2:-}"
      shift 2
      ;;
    --backend-port)
      BACKEND_PORT="${2:-}"
      shift 2
      ;;
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

if [[ "${BACKEND_ONLY}" -eq 1 && "${FRONTEND_ONLY}" -eq 1 ]]; then
  echo "--backend-only and --frontend-only cannot be used together." >&2
  exit 1
fi

if [[ -x "${REPO_ROOT}/.venv/bin/python" ]]; then
  PYTHON_BIN="${REPO_ROOT}/.venv/bin/python"
else
  PYTHON_BIN="${PYTHON_BIN:-python3}"
fi

if [[ "${PYTHON_BIN}" != */* ]]; then
  if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
    echo "Python executable not found: ${PYTHON_BIN}" >&2
    exit 1
  fi
elif [[ ! -x "${PYTHON_BIN}" ]]; then
  echo "Python executable not found: ${PYTHON_BIN}" >&2
  exit 1
fi

if [[ ! -d "${FRONTEND_DIR}" ]]; then
  echo "Frontend directory not found: ${FRONTEND_DIR}" >&2
  exit 1
fi

if ! command -v npm >/dev/null 2>&1; then
  echo "npm was not found in PATH. Please install Node.js first." >&2
  exit 1
fi

quote_cmd() {
  local quoted=()
  for arg in "$@"; do
    quoted+=("$(printf '%q' "${arg}")")
  done
  printf '%s\n' "${quoted[*]}"
}

cleanup() {
  local exit_code=$?
  trap - EXIT INT TERM

  if [[ -n "${BACKEND_PID:-}" ]] && kill -0 "${BACKEND_PID}" >/dev/null 2>&1; then
    kill "${BACKEND_PID}" >/dev/null 2>&1 || true
  fi

  if [[ -n "${FRONTEND_PID:-}" ]] && kill -0 "${FRONTEND_PID}" >/dev/null 2>&1; then
    kill "${FRONTEND_PID}" >/dev/null 2>&1 || true
  fi

  wait "${BACKEND_PID:-}" >/dev/null 2>&1 || true
  wait "${FRONTEND_PID:-}" >/dev/null 2>&1 || true
  exit "${exit_code}"
}

trap cleanup EXIT INT TERM

BACKEND_CMD=(
  "${PYTHON_BIN}"
  -m
  uvicorn
  main:app
  --reload
  --host
  "${BACKEND_HOST}"
  --port
  "${BACKEND_PORT}"
  --proxy-headers
  --forwarded-allow-ips
  "${FORWARDED_ALLOW_IPS:-127.0.0.1}"
)

FRONTEND_CMD=(
  npm
  run
  dev:embed
)

if [[ "${FRONTEND_ONLY}" -eq 0 ]]; then
  echo "[backend] cwd=${REPO_ROOT}"
  echo "[backend] cmd=$(quote_cmd "${BACKEND_CMD[@]}")"
fi

if [[ "${BACKEND_ONLY}" -eq 0 ]]; then
  echo "[frontend] cwd=${FRONTEND_DIR}"
  echo "[frontend] cmd=$(quote_cmd "${FRONTEND_CMD[@]}")"
fi

if [[ "${DRY_RUN}" -eq 1 ]]; then
  exit 0
fi

if [[ "${FRONTEND_ONLY}" -eq 0 ]]; then
  (
    cd "${REPO_ROOT}"
    exec "${BACKEND_CMD[@]}"
  ) &
  BACKEND_PID=$!
fi

if [[ "${BACKEND_ONLY}" -eq 0 ]]; then
  (
    cd "${FRONTEND_DIR}"
    exec "${FRONTEND_CMD[@]}"
  ) &
  FRONTEND_PID=$!
fi

if [[ -n "${BACKEND_PID:-}" && -n "${FRONTEND_PID:-}" ]]; then
  set +e
  wait -n "${BACKEND_PID}" "${FRONTEND_PID}"
  EXIT_STATUS=$?
  set -e
  echo "[start] one process exited, shutting down the others..."
  exit "${EXIT_STATUS}"
fi

if [[ -n "${BACKEND_PID:-}" ]]; then
  wait "${BACKEND_PID}"
fi

if [[ -n "${FRONTEND_PID:-}" ]]; then
  wait "${FRONTEND_PID}"
fi
