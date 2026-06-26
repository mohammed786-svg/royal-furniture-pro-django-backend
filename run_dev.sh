#!/usr/bin/env bash
# Royal Furniture Pro — Django dev server + Daphne (public bind for remote local UI).
#
#   python manage.py runserver 0.0.0.0:4002
#   daphne -b 0.0.0.0 -p 4003 config.asgi:application
#
# Defaults: BIND_HOST=0.0.0.0, HTTP :4002, WebSocket :4003
# Open TCP 4002 and 4003 in ufw + cloud firewall when hitting the API from another machine.
#
# Examples:
#   ./run_dev.sh
#   BIND_HOST=127.0.0.1 ./run_dev.sh              # loopback only (no remote API)
#   HTTP_PORT=4002 DAPHNE_PORT=4003 ./run_dev.sh
#   VENV=/path/to/venv ./run_dev.sh
#
# Run from django_backend (directory with manage.py):
#   chmod +x run_dev.sh && ./run_dev.sh
#
# Frontend (local dev → VPS API) — set frontend/.env.local:
#   NEXT_PUBLIC_API_URL=http://62.72.57.222:4002/api/v1
#   NEXT_PUBLIC_MEDIA_BASE_URL=http://62.72.57.222:4002
#   NEXT_PUBLIC_WS_URL=ws://62.72.57.222:4003/ws/
#
# VPS backend .env must include:
#   CORS_ALLOWED_ORIGINS=http://localhost:3000,https://royalfurniturepro.azdeploy.com
#   ALLOWED_HOSTS=royalfurniturepro.azdeploy.com,62.72.57.222,localhost,127.0.0.1

if [ -z "${BASH_VERSION:-}" ]; then
  exec /usr/bin/env bash "$0" "$@"
fi

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

HTTP_PORT="${HTTP_PORT:-${GUNICORN_PORT:-4002}}"
DAPHNE_PORT="${DAPHNE_PORT:-4003}"
BIND_HOST="${BIND_HOST:-0.0.0.0}"
VENV="${VENV:-${SCRIPT_DIR}/venv}"
export DJANGO_ENV="${DJANGO_ENV:-development}"

if [[ ! -f "${SCRIPT_DIR}/manage.py" ]]; then
  echo "ERROR: manage.py not found in ${SCRIPT_DIR}"
  exit 1
fi

if [[ ! -f "${SCRIPT_DIR}/.env" ]]; then
  echo "WARN: .env not found — copy from .env.example or deploy/vps/env/backend.production.env.example"
fi

if [[ -x "${VENV}/bin/python" ]]; then
  PYTHON="${VENV}/bin/python"
elif [[ -x "${SCRIPT_DIR}/.venv/bin/python" ]]; then
  PYTHON="${SCRIPT_DIR}/.venv/bin/python"
  VENV="${SCRIPT_DIR}/.venv"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON="$(command -v python3)"
else
  echo "ERROR: No venv at ${VENV} (bin/python) and no python3 on PATH."
  echo "Create: python3 -m venv venv && ./venv/bin/pip install -r requirements-py38.txt"
  exit 1
fi

if [[ -x "${VENV}/bin/daphne" ]]; then
  DAPHNE="${VENV}/bin/daphne"
elif command -v daphne >/dev/null 2>&1; then
  DAPHNE="$(command -v daphne)"
else
  echo "ERROR: daphne not found. Install: ${VENV}/bin/pip install -r requirements-py38.txt"
  exit 1
fi

cleanup() {
  if [[ -n "${RUNSERVER_PID:-}" ]]; then kill "$RUNSERVER_PID" 2>/dev/null || true; fi
  if [[ -n "${DAPHNE_PID:-}" ]]; then kill "$DAPHNE_PID" 2>/dev/null || true; fi
}
trap cleanup EXIT INT TERM

if [[ "$BIND_HOST" == "127.0.0.1" || "$BIND_HOST" == "localhost" ]]; then
  echo "Note: bind is ${BIND_HOST} (loopback only). Other machines cannot use your public IP until BIND_HOST=0.0.0.0."
fi

echo "==> Django runserver http://${BIND_HOST}:${HTTP_PORT}/  (DJANGO_ENV=${DJANGO_ENV})"
"$PYTHON" manage.py runserver "${BIND_HOST}:${HTTP_PORT}" &
RUNSERVER_PID=$!

echo "==> Daphne ws://${BIND_HOST}:${DAPHNE_PORT}/"
"$DAPHNE" -b "$BIND_HOST" -p "$DAPHNE_PORT" config.asgi:application &
DAPHNE_PID=$!

echo ""
echo "Running. Ctrl+C stops both."
echo "  API (HTTP) : http://${BIND_HOST}:${HTTP_PORT}/api/v1/"
echo "  WebSocket  : ws://${BIND_HOST}:${DAPHNE_PORT}/ws/"
if [[ "$BIND_HOST" == "0.0.0.0" ]]; then
  echo ""
  echo "Remote local UI (frontend/.env.local on your laptop):"
  echo "  NEXT_PUBLIC_API_URL=http://<VPS-IP>:${HTTP_PORT}/api/v1"
  echo "  NEXT_PUBLIC_MEDIA_BASE_URL=http://<VPS-IP>:${HTTP_PORT}"
  echo "  NEXT_PUBLIC_WS_URL=ws://<VPS-IP>:${DAPHNE_PORT}/ws/"
  echo ""
  echo "Then run: ./dev.sh remote"
fi
wait
