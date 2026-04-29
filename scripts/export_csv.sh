#!/usr/bin/env bash
# Proceeds Navigator — Export leads to CSV
# Usage: ./scripts/export_csv.sh [--county fresno] [--min-score 60]

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

TIMESTAMP=$(date -u '+%Y%m%d_%H%M%S')
OUTPUT="${DATA_DIR:-./data}/exports/leads_${TIMESTAMP}.csv"

cd proceeds_navigator
python3 -m proceeds_navigator.cli.commands export --output "$OUTPUT" "$@"

echo "Export saved to: $OUTPUT"
