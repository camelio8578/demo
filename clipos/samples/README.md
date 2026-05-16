# Sample Videos

Place sample video files here for seeding the development environment.

These files are gitignored (binaries). To seed a demo run:

```bash
cd /path/to/clipos
./scripts/seed.sh
```

The seed script will create a demo creator and trigger ingestion of a public
YouTube video via the API. The downloaded file will be stored in `$DATA_DIR/videos/`.

## Manual sample download

```bash
yt-dlp -f "best[height<=720]" \
  "https://www.youtube.com/watch?v=dQw4w9WgXcQ" \
  -o samples/sample_video.mp4
```
