# Royal Furniture Pro — VPS deployment (Ubuntu, Python 3.8.10)

End-to-end guide for **royalfurniturepro.azdeploy.com**.

## Server paths

| Item | Path |
|------|------|
| Django backend | `/root/royal-furniture-pro-django-backend` |
| Next.js frontend | `/var/www/html/royal_furniture_pro_website/royal-furniture-pro-frontend` |
| Media uploads | `/var/www/html/royal_furniture_pro_media` |
| Django static | `/var/www/html/royal_furniture_pro_static` |
| Deploy configs | `django_backend/deploy/vps/` |

## Ports (no conflict with azdeploy)

| Service | Port |
|---------|------|
| Gunicorn (production) | **4000** |
| Gunicorn (dev/testing) | **4002** |
| `run_dev.sh` HTTP (runserver) | **4002** |
| `run_dev.sh` Daphne (WebSocket) | **4003** |
| Daphne WebSocket (systemd prod) | **7002** |
| Next.js | **3010** |

### Remote local UI (laptop → VPS dev API)

On the VPS:

```bash
cd /root/royal-furniture-pro-django-backend
chmod +x run_dev.sh
# Stop production gunicorn if port 4002 conflicts with royalpro-gunicorn-dev
sudo ufw allow 4002/tcp
sudo ufw allow 4003/tcp
./run_dev.sh
```

On your laptop, `frontend/.env.local` should use `http://<VPS-IP>:4002/api/v1` and `ws://<VPS-IP>:4003/ws/`, then:

```bash
./dev.sh remote
```

Backend `.env` must include `CORS_ALLOWED_ORIGINS=http://localhost:3000,...` and `ALLOWED_HOSTS` with your VPS IP.

`API_CRYPTO_KEY` must be **64 hex characters** (32 bytes). Generate with `openssl rand -hex 32` and set the **same value** in backend `.env` and frontend `NEXT_PUBLIC_API_CRYPTO_KEY`. A placeholder like `change-me-...` will crash or disable encryption.

---

## 1. System packages

```bash
sudo apt update
sudo apt install -y python3.8 python3.8-venv python3.8-dev \
  postgresql postgresql-contrib redis-server nginx certbot \
  build-essential libpq-dev nodejs npm
```

Ensure Node 18+ (use nvm or NodeSource if `node -v` is too old):

```bash
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs
```

---

## 2. Database

```bash
sudo -u postgres psql
```

```sql
CREATE DATABASE royal_furniture_db;
CREATE USER royal_user WITH PASSWORD 'royal@2026';
GRANT ALL PRIVILEGES ON DATABASE royal_furniture_db TO royal_user;
\q
```

Import schema (first time):

```bash
cd /root/royal-furniture-pro-django-backend
sudo -u postgres psql -d royal_furniture_db -f royal_furniture.sql
```

**Seed admin logins** (Super Admin + Admin Manager, password `royal@2026`):

```bash
cd /root/royal-furniture-pro-django-backend
source venv/bin/activate
export DJANGO_ENV=production
python scripts/seed_admin_users.py
```

| Role | Email | Password |
|------|-------|----------|
| Super Admin | `super@royal.com` | `royal@2026` |
| Admin Manager | `admin@royal.com` | `royal@2026` |

Login at `https://royalfurniturepro.azdeploy.com/my-admin/login`. Safe to re-run — updates passwords if users already exist.

---

## 3. Media & static directories

```bash
sudo mkdir -p /var/www/html/royal_furniture_pro_media
sudo mkdir -p /var/www/html/royal_furniture_pro_static
sudo mkdir -p /var/www/certbot
sudo chown -R www-data:www-data /var/www/html/royal_furniture_pro_media
sudo chown -R www-data:www-data /var/www/html/royal_furniture_pro_static
sudo chmod -R 755 /var/www/html/royal_furniture_pro_media
```

Upload product/category images into `/var/www/html/royal_furniture_pro_media` preserving paths like `products/`, `categories/`, `banners/`.

---

## 4. Backend (Python 3.8 — use requirements-py38.txt)

> **Important:** `requirements.txt` pins Django 5+ (needs Python 3.10+).  
> On the VPS with Python 3.8.10 use **`requirements-py38.txt`** (Django 4.2 LTS).

```bash
cd /root/royal-furniture-pro-django-backend
python3.8 -m venv venv
source venv/bin/activate
pip install --upgrade pip setuptools wheel
pip install -r requirements-py38.txt

cp deploy/vps/env/backend.production.env.example .env
nano .env   # set SECRET_KEY, DB_*, JWT_*, API_CRYPTO_KEY, etc.
```

Key `.env` values:

```env
DJANGO_ENV=production
ALLOWED_HOSTS=royalfurniturepro.azdeploy.com,localhost,127.0.0.1
CORS_ALLOWED_ORIGINS=https://royalfurniturepro.azdeploy.com
MEDIA_ROOT=/var/www/html/royal_furniture_pro_media
STATIC_ROOT=/var/www/html/royal_furniture_pro_static
CDN_URL=https://royalfurniturepro.azdeploy.com
```

```bash
export DJANGO_ENV=production
python manage.py collectstatic --noinput
# Optional seed:
# python scripts/seed_storefront_demo.py --force
```

---

## 5. Frontend

```bash
cd /var/www/html/royal_furniture_pro_website/royal-furniture-pro-frontend
cp .env.production.example .env.production
nano .env.production
npm ci
npm run build
sudo chown -R www-data:www-data .
```

**Media URL (single config):** set `NEXT_PUBLIC_MEDIA_BASE_URL` in `.env.production`.  
All images use `frontend/src/config/media.config.ts` → `{baseUrl}/media/...`.  
When you move to `https://royalfurniturepro.in`, change only this env var and rebuild.

---

## 6. systemd services

```bash
sudo cp /root/royal-furniture-pro-django-backend/deploy/vps/systemd/*.service /etc/systemd/system/
sudo systemctl daemon-reload

sudo systemctl enable royalpro-gunicorn royalpro-daphne royalpro-nextjs
sudo systemctl start royalpro-gunicorn royalpro-daphne royalpro-nextjs

# Optional dev gunicorn on port 4002 (disable in production if unused):
# sudo systemctl enable --now royalpro-gunicorn-dev
```

Check status:

```bash
sudo systemctl status royalpro-gunicorn royalpro-daphne royalpro-nextjs
curl -sI http://127.0.0.1:4000/api/v1/ | head
curl -sI http://127.0.0.1:3010/ | head
```

---

## 7. Nginx + SSL

```bash
sudo cp /root/royal-furniture-pro-django-backend/deploy/vps/nginx/royalfurniturepro.conf \
  /etc/nginx/sites-available/royalfurniturepro.conf
sudo ln -sf /etc/nginx/sites-available/royalfurniturepro.conf /etc/nginx/sites-enabled/
sudo nginx -t
```

**DNS:** A record `royalfurniturepro.azdeploy.com` → your VPS IP.

**Certificate (after DNS propagates):**

```bash
sudo certbot certonly --webroot -w /var/www/certbot \
  -d royalfurniturepro.azdeploy.com \
  -d www.royalfurniturepro.azdeploy.com
sudo systemctl reload nginx
```

Renewal is usually automatic via certbot timer.

---

## 8. Quick bootstrap script

After cloning repos to the paths above:

```bash
chmod +x /root/royal-furniture-pro-django-backend/deploy/vps/scripts/bootstrap.sh
/root/royal-furniture-pro-django-backend/deploy/vps/scripts/bootstrap.sh
```

Then complete SSL + `.env` secrets manually.

---

## 9. Deploy updates

**One command (backend + frontend + services):**

```bash
cd /root/royal-furniture-pro-django-backend
git pull
./deploy/vps/deploy.sh
```

**Or manually:**

**Backend:**

```bash
cd /root/royal-furniture-pro-django-backend
git pull
source venv/bin/activate
pip install -r requirements-py38.txt
export DJANGO_ENV=production
python manage.py collectstatic --noinput
sudo systemctl restart royalpro-gunicorn royalpro-daphne
```

**Frontend:**

```bash
cd /var/www/html/royal_furniture_pro_website/royal-furniture-pro-frontend
git pull
npm ci
npm run build
sudo systemctl restart royalpro-nextjs
```

---

## 10. Remote dev API (port 4002) for local Next.js

On the VPS, expose Django dev server + Daphne for local frontend development:

```bash
cd /root/royal-furniture-pro-django-backend
chmod +x run_dev.sh
# Stop production gunicorn on 4000 if you need the same machine quiet, or run dev alongside:
./run_dev.sh
```

Defaults: **HTTP `0.0.0.0:4002`**, **WebSocket `0.0.0.0:4003`**

```bash
sudo ufw allow 4002/tcp
sudo ufw allow 4003/tcp
```

Backend `.env` (development):

```env
DJANGO_ENV=development
ALLOWED_HOSTS=royalfurniturepro.azdeploy.com,62.72.57.222,localhost,127.0.0.1
CORS_ALLOWED_ORIGINS=http://localhost:3000,https://royalfurniturepro.azdeploy.com
```

Local machine `frontend/.env.local`:

```env
NEXT_PUBLIC_API_URL=http://62.72.57.222:4002/api/v1
NEXT_PUBLIC_MEDIA_BASE_URL=http://62.72.57.222:4002
NEXT_PUBLIC_WS_URL=ws://62.72.57.222:4003/ws/
```

Then locally: `./dev.sh remote`

---

## 11. Troubleshooting

| Issue | Fix |
|-------|-----|
| Django 5 install error on Python 3.8 | Use `requirements-py38.txt`, not `requirements.txt` |
| 502 Bad Gateway | `systemctl status royalpro-gunicorn royalpro-nextjs` |
| Media 404 | Files in `/var/www/html/royal_furniture_pro_media`, nginx `alias` correct |
| CORS errors | `CORS_ALLOWED_ORIGINS` includes `https://royalfurniturepro.azdeploy.com` |
| Images wrong domain | Update `NEXT_PUBLIC_MEDIA_BASE_URL`, rebuild frontend |
| Permission denied on media upload | `chown www-data` on media dir or run gunicorn as user that can write |

---

## File map

```
deploy/vps/
├── README.md                          (this file)
├── nginx/royalfurniturepro.conf
├── systemd/
│   ├── royalpro-gunicorn.service      (port 4000)
│   ├── royalpro-gunicorn-dev.service  (port 4002)
│   ├── royalpro-daphne.service        (port 7002)
│   └── royalpro-nextjs.service        (port 3010)
├── env/
│   ├── backend.production.env.example
│   └── frontend.production.env.example
└── scripts/bootstrap.sh
```
