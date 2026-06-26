#!/usr/bin/env bash
# Royal Furniture Pro — VPS bootstrap (run as root on Ubuntu 20.04+ with Python 3.8)
set -euo pipefail

BACKEND_DIR="/root/royal-furniture-pro-django-backend"
FRONTEND_DIR="/var/www/html/royal_furniture_pro_website/royal-furniture-pro-frontend"
MEDIA_DIR="/var/www/html/royal_furniture_pro_media"
STATIC_DIR="/var/www/html/royal_furniture_pro_static"
DEPLOY_DIR="${BACKEND_DIR}/deploy/vps"

echo "==> Creating media & static directories"
mkdir -p "$MEDIA_DIR" "$STATIC_DIR" /var/www/certbot
chown -R www-data:www-data "$MEDIA_DIR" "$STATIC_DIR" 2>/dev/null || true
chmod -R 755 "$MEDIA_DIR" "$STATIC_DIR"

echo "==> Backend venv (Python 3.8) + requirements-py38.txt"
cd "$BACKEND_DIR"
python3.8 -m venv venv
source venv/bin/activate
pip install --upgrade pip setuptools wheel
pip install -r requirements-py38.txt

if [[ ! -f .env ]]; then
  cp deploy/vps/env/backend.production.env.example .env
  echo "Created .env — edit secrets before going live."
fi

echo "==> Django migrate + collectstatic"
export DJANGO_ENV=production
python manage.py migrate --run-syncdb 2>/dev/null || python manage.py migrate || true
python manage.py collectstatic --noinput

echo "==> Frontend build"
cd "$FRONTEND_DIR"
if [[ ! -f .env.production ]]; then
  cp "${DEPLOY_DIR}/env/frontend.production.env.example" .env.production
  echo "Created .env.production — edit before build."
fi
npm ci
npm run build
chown -R www-data:www-data "$FRONTEND_DIR"

echo "==> Install systemd units"
cp "${DEPLOY_DIR}/systemd/"*.service /etc/systemd/system/
systemctl daemon-reload

echo "==> Install nginx site"
cp "${DEPLOY_DIR}/nginx/royalfurniturepro.conf" /etc/nginx/sites-available/royalfurniturepro.conf
ln -sf /etc/nginx/sites-available/royalfurniturepro.conf /etc/nginx/sites-enabled/royalfurniturepro.conf
nginx -t

echo ""
echo "Next steps:"
echo "  1. Edit ${BACKEND_DIR}/.env and ${FRONTEND_DIR}/.env.production"
echo "  2. Point DNS A record: royalfurniturepro.azdeploy.com -> this server"
echo "  3. SSL: certbot certonly --webroot -w /var/www/certbot -d royalfurniturepro.azdeploy.com -d www.royalfurniturepro.azdeploy.com"
echo "  4. systemctl enable --now royalpro-gunicorn royalpro-daphne royalpro-nextjs"
echo "  5. systemctl reload nginx"
echo "  6. Upload media files to ${MEDIA_DIR}"
