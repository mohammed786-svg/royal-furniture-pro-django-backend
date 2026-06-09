#!/usr/bin/env bash
# Apply raw PostgreSQL schema (royal schema)
set -euo pipefail
psql -h "${DB_HOST:-127.0.0.1}" -p "${DB_PORT:-5432}" -U "${DB_USER:-postgres}" -d "${DB_NAME:-royal_furniture_db}" -f database/migrations_sql/royal_furniture.sql
