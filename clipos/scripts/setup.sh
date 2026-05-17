#!/bin/bash
set -e

echo "=== ClipOS Setup ==="
echo ""

# Check dependencies
command -v docker >/dev/null 2>&1 || { echo "ERROR: docker required"; exit 1; }
command -v docker-compose >/dev/null 2>&1 || command -v docker >/dev/null 2>&1 || { echo "ERROR: docker compose required"; exit 1; }
command -v ffmpeg >/dev/null 2>&1 || echo "WARNING: ffmpeg not found locally (required in Docker)"
command -v python3 >/dev/null 2>&1 || { echo "ERROR: python3 required for local dev"; exit 1; }

# Setup .env
if [ ! -f infra/.env ]; then
  echo "Creating infra/.env from .env.example..."
  cp infra/.env.example infra/.env
  echo "  -> Edit infra/.env to configure your environment"
fi

# Setup Python venv for local dev
if [ ! -d apps/api/.venv ]; then
  echo "Creating Python virtual environment..."
  python3 -m venv apps/api/.venv
fi

echo "Installing Python dependencies..."
source apps/api/.venv/bin/activate
pip install -r apps/api/requirements.txt -q

echo ""
echo "=== Setup complete ==="
echo ""
echo "Next steps:"
echo "  1. Edit clipos/infra/.env with your settings"
echo "  2. cd clipos && docker-compose -f infra/docker-compose.yml up -d"
echo "  3. Run migrations: docker-compose -f infra/docker-compose.yml exec api alembic upgrade head"
echo "  4. Run seed: bash scripts/seed.sh"
echo "  5. Open admin: http://localhost:3001"
echo "  6. API docs: http://localhost:8000/docs"
echo "  7. Flower (jobs): http://localhost:5555"
