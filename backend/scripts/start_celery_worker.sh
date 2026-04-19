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
echo "[worker] starting celery worker (loglevel=${LOGLEVEL})..."
exec celery -A app.tasks.worker worker --loglevel="${LOGLEVEL}" "$@"
