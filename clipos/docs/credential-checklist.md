# Credential Checklist

## Works Locally Without Any Credentials

These features run fully without external API keys:
- Video ingestion (yt-dlp, local download)
- Transcription (Whisper, runs locally on CPU)
- Candidate scoring (heuristic scorer)
- Clip rendering (FFmpeg)
- Caption generation (FFmpeg subtitle burn-in)
- Rule-based copy generation
- Admin UI
- All database operations

## Optional: LLM Enhancement

Improves copy generation and scoring quality.

| Variable | Purpose | Where to get |
|---|---|---|
| OPENAI_API_KEY | GPT-4o copy gen + LLM scoring | platform.openai.com |
| ANTHROPIC_API_KEY | Claude copy gen + LLM scoring | console.anthropic.com |

Set LLM_PROVIDER=openai or LLM_PROVIDER=anthropic in .env.

## Required for YouTube Publishing

| Variable | Purpose | Where to get |
|---|---|---|
| YOUTUBE_API_KEY | API access | Google Cloud Console → YouTube Data API v3 |
| YOUTUBE_CLIENT_ID | OAuth app | Google Cloud Console → OAuth 2.0 Credentials |
| YOUTUBE_CLIENT_SECRET | OAuth app | Google Cloud Console |
| YOUTUBE_REFRESH_TOKEN | Per-account auth | OAuth flow (run auth script) |

Steps:
1. Create project in Google Cloud Console
2. Enable YouTube Data API v3
3. Create OAuth 2.0 credentials (Desktop app type)
4. Run: python scripts/auth_youtube.py to get refresh token
5. Add credentials to .env

## Required for TikTok Publishing

| Variable | Purpose | Where to get |
|---|---|---|
| TIKTOK_CLIENT_KEY | App credentials | developers.tiktok.com |
| TIKTOK_CLIENT_SECRET | App credentials | developers.tiktok.com |
| TIKTOK_ACCESS_TOKEN | Per-account auth | OAuth flow after app approval |

Steps:
1. Apply for TikTok Developer account
2. Create app, request Content Posting API permission
3. Wait for TikTok approval (days to weeks)
4. Implement OAuth flow to get access tokens per creator account

## Required for Instagram Publishing

| Variable | Purpose | Where to get |
|---|---|---|
| INSTAGRAM_ACCESS_TOKEN | Long-lived page token | Meta for Developers |
| INSTAGRAM_ACCOUNT_ID | Business account ID | Meta Business Suite |

Steps:
1. Create Meta Developer account
2. Create app with instagram_content_publish permission
3. Submit for App Review (required for non-test accounts)
4. Generate long-lived access token via Graph API

## Required for Cloud Storage (Optional)

By default, assets stored on local filesystem.
For production, configure S3 or MinIO:

| Variable | Purpose |
|---|---|
| USE_S3=true | Enable S3 storage |
| S3_ENDPOINT_URL | MinIO or AWS S3 endpoint |
| S3_BUCKET | Bucket name |
| AWS_ACCESS_KEY_ID | Credentials |
| AWS_SECRET_ACCESS_KEY | Credentials |
