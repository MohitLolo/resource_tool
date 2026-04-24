#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${BACKEND_DIR}"

export PYTHONPATH="${PYTHONPATH:-.}"

PRECHECK_ONLY=0
if [[ "${1:-}" == "--precheck-only" ]]; then
  PRECHECK_ONLY=1
  shift
fi

REDIS_ARGS=()
if [[ -n "${REDIS_URL:-}" ]]; then
  REDIS_ARGS=(--redis-url "${REDIS_URL}")
fi

echo "[precheck] checking celery redis transport keys..."
if ! python scripts/check_celery_redis_state.py "${REDIS_ARGS[@]}"; then
  echo "[precheck] detected stale/wrong-type keys, applying fix..."
  python scripts/check_celery_redis_state.py "${REDIS_ARGS[@]}" --fix
fi

if [[ "${PRECHECK_ONLY}" == "1" ]]; then
  echo "[precheck] done"
  exit 0
fi

LOGLEVEL="${CELERY_LOGLEVEL:-info}"
MAX_RESTARTS="${MAX_RESTARTS:-5}"
RESTART_DELAY="${RESTART_DELAY:-2}"
restart_count=0

while true; do
  attempt=$((restart_count + 1))
  echo "[worker] starting celery worker (attempt=${attempt}, loglevel=${LOGLEVEL}, pool=solo)..."
  set +e
  celery -A app.tasks.worker worker --loglevel="${LOGLEVEL}" -P solo "$@"
  exit_code=$?
  set -e

  if [[ "${exit_code}" -eq 0 ]]; then
    echo "[worker] exited normally"
    exit 0
  fi

  restart_count=$((restart_count + 1))
  echo "[worker] crashed with exit code ${exit_code}"
  if [[ "${restart_count}" -ge "${MAX_RESTARTS}" ]]; then
    echo "[worker] too many restarts (${restart_count}), giving up" >&2
    exit "${exit_code}"
  fi

  echo "[worker] restarting in ${RESTART_DELAY}s..."
  sleep "${RESTART_DELAY}"
done
