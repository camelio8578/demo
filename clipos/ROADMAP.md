# ClipOS Roadmap

## MVP (v1.0) — Current

### Fully Working (No Credentials Required)
- [x] Creator registry + rights profiles
- [x] Source monitoring setup
- [x] Video ingestion via yt-dlp
- [x] Whisper transcription with timestamps
- [x] 9-signal candidate scoring
- [x] FFmpeg clip extraction
- [x] 9:16 vertical reframe (center crop)
- [x] ASS/SRT subtitle generation
- [x] Caption burn-in
- [x] Rule-based copy generation
- [x] Admin review dashboard
- [x] Job queue (Celery + Redis)
- [x] Docker Compose deployment
- [x] Full API surface
- [x] Publishing adapter interfaces

### Requires External Credentials
- [ ] YouTube Shorts publishing (needs OAuth app)
- [ ] TikTok publishing (needs Developer app approval)
- [ ] Instagram Reels publishing (needs Meta App Review)
- [ ] LLM-enhanced copy + scoring (needs OpenAI/Anthropic key)
- [ ] YouTube analytics ingestion
- [ ] TikTok analytics ingestion
- [ ] Instagram Insights ingestion
- [ ] Cloud storage (S3/MinIO — local filesystem works without)

## Phase 2

- [ ] Livestream clipping (real-time buffer processing)
- [ ] Multi-language transcription (Whisper supports 99 languages)
- [ ] Speaker diarization (pyannote.audio)
- [ ] AI face-tracking reframe (OpenCV tracking model)
- [ ] Creator-facing portal (self-serve)
- [ ] n8n workflow templates
- [ ] LinkedIn + Twitter publishing adapters
- [ ] Source polling automation (cron-based channel monitoring)
- [ ] Scoring feedback loop (performance → weights)

## Phase 3

- [ ] B-roll overlay generation
- [ ] Multi-clip series threading
- [ ] White-label licensing mode
- [ ] Social listening integration
- [ ] Brand safety AI layer
- [ ] Kubernetes deployment manifests
