#!/usr/bin/env bash
set -e

# Start Celery worker in background using solo pool (minimal memory footprint for 512MB RAM instances)
celery -A src.celery_tasks.celery_app worker --loglevel=info --pool=solo &

# Start FastAPI application in foreground on Render's assigned $PORT with 1 worker
exec uvicorn src.main:app --host 0.0.0.0 --port "${PORT:-8000}" --workers 1
