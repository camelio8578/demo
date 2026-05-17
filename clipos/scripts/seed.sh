#!/bin/bash
set -e

# ClipOS Seed Script
# Demonstrates the full pipeline on a sample video
#
# Usage:
#   bash scripts/seed.sh                     # Uses default sample video
#   bash scripts/seed.sh <youtube_url>       # Custom video URL
#   bash scripts/seed.sh <youtube_url> <creator_name>

API_URL="${API_URL:-http://localhost:8000}"
VIDEO_URL="${1:-https://www.youtube.com/watch?v=dQw4w9WgXcQ}"  # Replace with a short test video
CREATOR_NAME="${2:-Demo Creator}"

echo "=== ClipOS Seed Demo ==="
echo "API: $API_URL"
echo "Video: $VIDEO_URL"
echo "Creator: $CREATOR_NAME"
echo ""

# Wait for API
echo "Waiting for API..."
for i in {1..30}; do
  if curl -sf "$API_URL/api/v1/health" >/dev/null 2>&1; then
    echo "API is ready."
    break
  fi
  sleep 2
done

# 1. Create a rights profile
echo ""
echo "Step 1: Creating rights profile..."
RIGHTS_RESPONSE=$(curl -sf -X POST "$API_URL/api/v1/rights-profiles" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Standard Demo Profile",
    "allow_repost": true,
    "require_attribution": false,
    "commercial_use_allowed": true,
    "manual_review_required": false,
    "risk_level": "low",
    "notes": "Default demo profile"
  }')
RIGHTS_ID=$(echo "$RIGHTS_RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
echo "Rights profile created: $RIGHTS_ID"

# 2. Create a creator
echo ""
echo "Step 2: Creating creator..."
CREATOR_SLUG=$(echo "$CREATOR_NAME" | tr '[:upper:]' '[:lower:]' | tr ' ' '-')
CREATOR_RESPONSE=$(curl -sf -X POST "$API_URL/api/v1/creators" \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"$CREATOR_NAME\",
    \"slug\": \"$CREATOR_SLUG\",
    \"rights_profile_id\": \"$RIGHTS_ID\"
  }")
CREATOR_ID=$(echo "$CREATOR_RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
echo "Creator created: $CREATOR_ID"

# 3. Trigger ingestion
echo ""
echo "Step 3: Triggering video ingestion..."
INGEST_RESPONSE=$(curl -sf -X POST "$API_URL/api/v1/ingest" \
  -H "Content-Type: application/json" \
  -d "{
    \"source_url\": \"$VIDEO_URL\",
    \"creator_id\": \"$CREATOR_ID\"
  }")
VIDEO_ID=$(echo "$INGEST_RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('source_video_id', d.get('id', 'unknown')))")
JOB_ID=$(echo "$INGEST_RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin).get('celery_task_id', 'unknown'))")
echo "Ingestion triggered. Video ID: $VIDEO_ID, Job: $JOB_ID"

echo ""
echo "=== Pipeline Started ==="
echo ""
echo "The pipeline is now running asynchronously:"
echo "  1. Downloading video..."
echo "  2. Transcribing with Whisper..."
echo "  3. Scoring candidate clips..."
echo "  4. Rendering top clips..."
echo "  5. Generating captions + copy..."
echo ""
echo "Monitor progress:"
echo "  - Flower UI: http://localhost:5555"
echo "  - API health: $API_URL/api/v1/health"
echo "  - Video status: $API_URL/api/v1/videos/$VIDEO_ID"
echo "  - Admin UI: http://localhost:3001"
echo ""
echo "Candidate clips (available after transcription):"
echo "  $API_URL/api/v1/videos/$VIDEO_ID/candidates"
echo ""
echo "To approve a candidate and trigger rendering:"
echo "  curl -X PUT $API_URL/api/v1/candidates/{candidate_id}/status -H 'Content-Type: application/json' -d '{\"status\": \"approved\"}'"
echo ""
echo "To manually render a candidate:"
echo "  curl -X POST $API_URL/api/v1/candidates/{candidate_id}/render"
