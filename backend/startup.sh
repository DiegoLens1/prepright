#!/bin/sh
set -e

# Create data directory for the database
mkdir -p /app/backend/data

# Seed the database
cd /app/backend
export DATABASE_URL="sqlite:////app/backend/data/prepright.db"
python seed.py
# Seed default receipt-parsing templates (idempotent; receipt parsing needs these)
python seed_templates.py

# Start backend
cd /app/backend/data
PYTHONPATH=/app/backend exec uvicorn prepright.main:app --host 0.0.0.0 --port 8000
