#!/bin/sh
set -e

# Create data directory for the database
mkdir -p /app/backend/data

# Seed the database
cd /app/backend
export DATABASE_URL="sqlite:////app/backend/data/prepright.db"
python seed.py

# Start backend
cd /app/backend/data
PYTHONPATH=/app/backend exec uvicorn prepright.main:app --host 0.0.0.0 --port 8000
