#!/usr/bin/env bash
set -e

# Start FastAPI application in foreground on Render's assigned $PORT with 1 worker
exec uvicorn src.main:app --host 0.0.0.0 --port "${PORT:-8000}" --workers 1
