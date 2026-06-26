#!/usr/bin/env bash
# Royal Furniture Pro — deploy backend + frontend on the VPS. Run as root (or use sudo).
#
# Defaults match deploy/vps/README.md:
#   Django:  /root/royal-furniture-pro-django-backend
#   Next.js: /var/www/html/royal_furniture_pro_website/royal-furniture-pro-frontend
#
# Override if needed:
#   DJANGO_HOME=/path/to/backend FRONTEND_HOME=/path/to/frontend ./deploy.sh
#   VENV=/path/to/venv ./deploy.sh
#
# Use: ./deploy.sh or bash deploy.sh. If you run `sh deploy.sh`, we re-exec under bash.

if [ -z "${BASH_VERSION:-}" ]; then
  exec /usr/bin/env bash "$0" "$@"
fi

set -euo pipefail

DJANGO_HOME="${DJANGO_HOME:-/root/royal-furniture-pro-django-backend}"
FRONTEND_HOME="${FRONTEND_HOME:-/var/www/html/royal_furniture_pro_website/royal-furniture-pro-frontend}"
VENV="${VENV:-${DJANGO_HOME}/venv}"
REQUIREMENTS="${REQUIREMENTS:-${DJANGO_HOME}/requirements-py38.txt}"

if [[ ! -f "${DJANGO_HOME}/manage.py" ]]; then
  echo "ERROR: manage.py not found in ${DJANGO_HOME}. Set DJANGO_HOME to the folder that contains manage.py."
  exit 1
fi

if [[ ! -f "${REQUIREMENTS}" ]]; then
  echo "ERROR: requirements file not found: ${REQUIREMENTS}"
  exit 1
fi

if [[ ! -x "${VENV}/bin/python" ]]; then
  echo "ERROR: venv not found at ${VENV}."
  echo "Create it with Python 3.8+, e.g.:"
  echo "  python3.8 -m venv ${VENV}"
  echo "  ${VENV}/bin/pip install -r ${REQUIREMENTS}"
  exit 1
fi

if ! "${VENV}/bin/python" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)'; then
  echo "ERROR: venv must use Python 3.8+. Found:"
  "${VENV}/bin/python" -V
  exit 1
fi

if [[ ! -f "${DJANGO_HOME}/.env" ]]; then
  echo "WARN: ${DJANGO_HOME}/.env missing — copy from deploy/vps/env/backend.production.env.example"
fi

if [[ ! -f "${FRONTEND_HOME}/package.json" ]]; then
  echo "ERROR: frontend not found at ${FRONTEND_HOME}. Set FRONTEND_HOME."
  exit 1
fi

echo "==> Backend: install, migrate, collectstatic"
# shellcheck source=/dev/null
source "${VENV}/bin/activate"
pip install -r "${REQUIREMENTS}"
cd "${DJANGO_HOME}"
export DJANGO_ENV=production
python manage.py migrate --noinput 2>/dev/null || python manage.py migrate --run-syncdb --noinput 2>/dev/null || python manage.py migrate || true
python manage.py collectstatic --noinput
deactivate

echo "==> Frontend: build"
cd "${FRONTEND_HOME}"
if [[ ! -f .env.production ]]; then
  echo "WARN: .env.production missing — copy from deploy/vps/env/frontend.production.env.example"
fi
if [[ -f package-lock.json ]]; then
  npm ci
else
  npm install
fi
npm run build

echo "==> Restart services"
systemctl restart royalpro-gunicorn
systemctl restart royalpro-daphne
systemctl restart royalpro-nextjs

if nginx -t 2>/dev/null; then
  systemctl reload nginx
  echo "Nginx config OK — reloaded."
else
  echo "WARN: nginx -t failed — fix config before reload."
fi

echo "Done."
