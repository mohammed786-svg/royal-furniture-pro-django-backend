#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install daphne

cp -n .env.example .env 2>/dev/null || true
mkdir -p logs media/products media/categories media/banners media/payments media/customers media/documents
python manage.py migrate --run-syncdb
echo "Development setup complete."
