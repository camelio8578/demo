#!/usr/bin/env bash
# Proceeds Navigator — Setup Script
# Run this once after cloning the repo.
# Usage: ./scripts/setup.sh

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

echo "=== Proceeds Navigator Setup ==="
echo ""

# ── Python version check ─────────────────────────────────────────────────────
python_version=$(python3 --version 2>&1 | awk '{print $2}')
required="3.11"
if python3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" 2>/dev/null; then
    echo "[OK] Python $python_version"
else
    echo "[ERROR] Python 3.11+ required. Found: $python_version"
    exit 1
fi

# ── Virtual environment ───────────────────────────────────────────────────────
if [ ! -d ".venv" ]; then
    echo "[...] Creating virtual environment..."
    python3 -m venv .venv
    echo "[OK] .venv created"
else
    echo "[OK] .venv already exists"
fi

source .venv/bin/activate

# ── Install Python dependencies ───────────────────────────────────────────────
echo "[...] Installing Python dependencies..."
pip install --upgrade pip --quiet
pip install -r proceeds_navigator/requirements-dev.txt --quiet
echo "[OK] Python dependencies installed"

# ── Playwright (optional — only needed for JS-heavy county pages) ─────────────
if command -v playwright &>/dev/null; then
    echo "[...] Installing Playwright browsers..."
    playwright install chromium --quiet 2>/dev/null || echo "[WARN] Playwright install failed — JS-heavy pages will not scrape"
else
    echo "[WARN] Playwright not found in PATH. JS-heavy page scraping will be unavailable."
    echo "       Install with: pip install playwright && playwright install chromium"
fi

# ── Data directories ──────────────────────────────────────────────────────────
echo "[...] Creating data directories..."
mkdir -p data/snapshots data/exports
echo "[OK] data/ directories created"

# ── Environment file ──────────────────────────────────────────────────────────
if [ ! -f ".env" ]; then
    cp .env.example .env
    SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    # Replace placeholder in .env
    if [[ "$OSTYPE" == "darwin"* ]]; then
        sed -i '' "s/REPLACE_WITH_RANDOM_64_CHAR_HEX/$SECRET/" .env
    else
        sed -i "s/REPLACE_WITH_RANDOM_64_CHAR_HEX/$SECRET/" .env
    fi
    echo "[OK] .env created from .env.example (secret key generated)"
    echo "     Edit .env to fill in OPERATOR_NAME, OPERATOR_ADDRESS, etc."
else
    echo "[OK] .env already exists — not overwritten"
fi

# ── Initialize database ───────────────────────────────────────────────────────
echo "[...] Initializing database..."
cd proceeds_navigator
python3 -c "
import sys, os
sys.path.insert(0, '..')
from dotenv import load_dotenv
load_dotenv('../.env')
from proceeds_navigator.db.session import init_db
init_db()
print('[OK] Database initialized')
"
cd ..

# ── Node (dashboard) ─────────────────────────────────────────────────────────
if command -v node &>/dev/null; then
    NODE_VERSION=$(node --version)
    echo "[OK] Node.js $NODE_VERSION found"
    if command -v npm &>/dev/null; then
        echo "[...] Installing dashboard dependencies..."
        cd dashboard
        npm install --silent
        cd ..
        echo "[OK] Dashboard dependencies installed"
        # Create dashboard env
        if [ ! -f "dashboard/.env.local" ]; then
            echo "VITE_API_BASE_URL=http://localhost:8000/api/v1" > dashboard/.env.local
            echo "[OK] dashboard/.env.local created"
        fi
    fi
else
    echo "[WARN] Node.js not found — dashboard will not be available locally."
    echo "       Install Node.js 18+ to run the dashboard."
fi

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Next steps:"
echo "  1. Edit .env with your operator name, address, phone, email"
echo "  2. Verify county URLs in proceeds_navigator/config/counties.yaml"
echo "  3. Start the API:       source .venv/bin/activate && cd proceeds_navigator && uvicorn api.main:app --reload"
echo "  4. Start the dashboard: cd dashboard && npm run dev"
echo "  5. Run a test scrape:   source .venv/bin/activate && proceeds-navigator scrape --dry-run"
echo ""
echo "IMPORTANT: Review CLAUDE.md before running in production."
echo "           Legal review items LR-001 through LR-010 must be resolved before client contact."
