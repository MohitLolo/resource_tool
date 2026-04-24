#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="${ROOT_DIR}/backend"
FRONTEND_DIR="${ROOT_DIR}/frontend"
LOG_DIR="${LOG_DIR:-/tmp/gameasset}"
CONDA_ENV="${CONDA_ENV:-gameasset}"

REDIS_PATTERN="redis-server.*:6379"
API_PATTERN="uvicorn app.main:app"
WORKER_PATTERN="celery -A app.tasks.worker worker"
FRONTEND_PATTERN="npm run dev --host --port 5173"

mkdir -p "${LOG_DIR}"

usage() {
  cat <<'EOF'
Usage:
  bash scripts/project_service.sh <start|stop|restart|status>

Environment variables:
  CONDA_ENV=<name>   Conda env name (default: gameasset)
  LOG_DIR=<path>     Log directory (default: /tmp/gameasset)
EOF
}

ensure_cmd() {
  local cmd="$1"
  if ! command -v "${cmd}" >/dev/null 2>&1; then
    echo "[error] missing command: ${cmd}" >&2
    exit 1
  fi
}

is_running() {
  local pattern="$1"
  pgrep -f "${pattern}" >/dev/null 2>&1
}

print_running() {
  local name="$1"
  local pattern="$2"
  if is_running "${pattern}"; then
    local pids
    pids="$(pgrep -f "${pattern}" | tr '\n' ' ')"
    echo "[ok] ${name} running (pid: ${pids})"
  else
    echo "[--] ${name} stopped"
  fi
}

start_redis() {
  if is_running "${REDIS_PATTERN}"; then
    echo "[skip] redis already running"
    return
  fi
  echo "[run] starting redis-server"
  nohup redis-server >"${LOG_DIR}/redis.log" 2>&1 &
}

start_api() {
  if is_running "${API_PATTERN}"; then
    echo "[skip] api already running"
    return
  fi
  echo "[run] starting backend api"
  (
    cd "${BACKEND_DIR}"
    nohup conda run -n "${CONDA_ENV}" uvicorn app.main:app --host 0.0.0.0 --port 8000 \
      >"${LOG_DIR}/api.log" 2>&1 &
  )
}

start_worker() {
  if is_running "${WORKER_PATTERN}"; then
    echo "[skip] celery worker already running"
    return
  fi
  echo "[run] starting celery worker"
  (
    cd "${ROOT_DIR}"
    nohup conda run -n "${CONDA_ENV}" bash backend/scripts/start_celery_worker.sh \
      >"${LOG_DIR}/worker.log" 2>&1 &
  )
}

start_frontend() {
  if is_running "${FRONTEND_PATTERN}"; then
    echo "[skip] frontend already running"
    return
  fi
  echo "[run] starting frontend dev server"
  (
    cd "${FRONTEND_DIR}"
    nohup npm run dev --host --port 5173 >"${LOG_DIR}/frontend.log" 2>&1 &
  )
}

stop_by_pattern() {
  local name="$1"
  local pattern="$2"
  if ! is_running "${pattern}"; then
    echo "[skip] ${name} already stopped"
    return
  fi
  echo "[run] stopping ${name}"
  pkill -f "${pattern}" || true
}

wait_brief() {
  sleep 1
}

check_health() {
  if curl -sS --max-time 2 http://127.0.0.1:8000/api/health >/dev/null 2>&1; then
    echo "[ok] api health reachable: http://127.0.0.1:8000/api/health"
  else
    echo "[warn] api health not reachable yet"
  fi
}

start_all() {
  ensure_cmd conda
  ensure_cmd npm
  ensure_cmd curl
  ensure_cmd pgrep
  ensure_cmd pkill
  ensure_cmd redis-server

  start_redis
  start_api
  start_worker
  start_frontend
  wait_brief
  status_all
  check_health
}

stop_all() {
  stop_by_pattern "frontend" "${FRONTEND_PATTERN}"
  stop_by_pattern "worker" "${WORKER_PATTERN}"
  stop_by_pattern "api" "${API_PATTERN}"
  stop_by_pattern "redis" "${REDIS_PATTERN}"
  wait_brief
  status_all
}

status_all() {
  print_running "redis" "${REDIS_PATTERN}"
  print_running "api" "${API_PATTERN}"
  print_running "worker" "${WORKER_PATTERN}"
  print_running "frontend" "${FRONTEND_PATTERN}"
  echo "[info] logs dir: ${LOG_DIR}"
}

cmd="${1:-}"
case "${cmd}" in
start)
  start_all
  ;;
stop)
  stop_all
  ;;
restart)
  stop_all
  start_all
  ;;
status)
  status_all
  check_health
  ;;
*)
  usage
  exit 1
  ;;
esac
