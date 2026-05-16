# ClipOS Credential Checklist

Fill in all credentials in `infra/.env` before running in production.

## Required

- [ ] `DATABASE_URL` — PostgreSQL connection string
- [ ] `REDIS_URL` — Redis connection string
- [ ] `SECRET_KEY` — 32+ random hex bytes (`openssl rand -hex 32`)
- [ ] `DATA_DIR` — Absolute path for video/audio/rendered storage

## AI Providers (at least one required)

- [ ] `OPENAI_API_KEY` — For Whisper transcription + GPT copy generation
- [ ] `ANTHROPIC_API_KEY` — For Claude copy generation (if LLM_PROVIDER=anthropic)

## Platform Publishing APIs (per platform you publish to)

### YouTube
- [ ] OAuth 2.0 client credentials in `creator_platform_accounts`
- [ ] YouTube Data API v3 key (`YOUTUBE_API_KEY`)

### TikTok
- [ ] TikTok for Developers app credentials
- [ ] Content Posting API access

### Instagram / Meta
- [ ] Meta Business App with Instagram Content Publishing permission
- [ ] Long-lived access tokens per creator account

### Twitter / X
- [ ] X Developer App with OAuth 2.0 + write permissions

### LinkedIn
- [ ] LinkedIn Developer App with `w_member_social` scope

## Security Notes

- Never commit `.env` to git (it is in `.gitignore`)
- Rotate `SECRET_KEY` if it is ever exposed
- Store platform tokens encrypted at rest (future enhancement)
- Access tokens in `creator_platform_accounts` are stored plaintext — add
  encryption before production use with real creator credentials
