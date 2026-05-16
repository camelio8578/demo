#!/bin/bash
# Run API + workers locally without Docker (for development)

set -e
cd "$(dirname "$0")/.."

source apps/api/.venv/bin/activate

# Export env vars
export $(grep -v '^#' infra/.env | xargs) 2>/dev/null || true
export DATABASE_URL="${DATABASE_URL:-postgresql://clipos:clipos@localhost:5432/clipos}"
export REDIS_URL="${REDIS_URL:-redis://localhost:6379/0}"
export DATA_DIR="${DATA_DIR:-./data}"

mkdir -p "$DATA_DIR"

echo "Starting API server on :8000..."
cd apps/api
uvicorn app.main:app --reload --port 8000 &
API_PID=$!

echo "Starting workers..."
celery -A workers.celery_app worker -Q ingestion,transcription,scoring,rendering,publishing -c 2 --loglevel=info &
WORKER_PID=$!

echo ""
echo "ClipOS running locally:"
echo "  API: http://localhost:8000"
echo "  Docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop..."
trap "kill $API_PID $WORKER_PID 2>/dev/null; exit" SIGINT SIGTERM
wait
