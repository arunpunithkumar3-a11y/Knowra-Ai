#!/usr/bin/env bash
set -e

# Start Celery worker in background (limit concurrency to conserve memory on free instances)
celery -A src.celery_tasks.celery_app worker --loglevel=info --concurrency=2 &

# Start FastAPI application in foreground on Render's assigned $PORT
exec uvicorn src.main:app --host 0.0.0.0 --port "${PORT:-8000}"
