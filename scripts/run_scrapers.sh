#!/usr/bin/env bash
# Proceeds Navigator — Run All Scrapers
# Designed to be run manually or via cron.
# Usage: ./scripts/run_scrapers.sh [--county fresno] [--dry-run]
#
# Cron example (weekly on Monday at 6am):
#   0 6 * * 1 /path/to/demo/scripts/run_scrapers.sh >> /path/to/demo/data/scraper.log 2>&1

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

VENV="$REPO_ROOT/.venv"
if [ ! -d "$VENV" ]; then
    echo "[ERROR] Virtual environment not found. Run ./scripts/setup.sh first."
    exit 1
fi

source "$VENV/bin/activate"

if [ -f ".env" ]; then
    set -a
    source .env
    set +a
fi

echo "=== Proceeds Navigator Scraper Run: $(date -u '+%Y-%m-%d %H:%M:%S UTC') ==="

COUNTY_ARG=""
DRY_RUN_ARG=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --county) COUNTY_ARG="--county $2"; shift 2 ;;
        --dry-run) DRY_RUN_ARG="--dry-run"; shift ;;
        *) echo "[WARN] Unknown argument: $1"; shift ;;
    esac
done

cd proceeds_navigator
python3 -m proceeds_navigator.cli.commands scrape $COUNTY_ARG $DRY_RUN_ARG

echo "=== Scraper Run Complete: $(date -u '+%Y-%m-%d %H:%M:%S UTC') ==="
