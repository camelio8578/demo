# ClipOS Sample Files

This directory contains sample fixtures for testing.

## Test Videos

For the demo seed, the system will attempt to download a YouTube video.
For local testing without YouTube, place a video file here:

  samples/test_video.mp4

Requirements:
- Duration: 5+ minutes recommended
- Format: MP4, MOV, MKV, or WebM
- Resolution: 1920x1080 recommended (16:9)

The seed script will use this local file if VIDEO_URL is set to:
  file:///clipos/samples/test_video.mp4

## Finding a Test Video

Public domain options:
- https://www.videvo.net (free HD stock footage)
- https://www.pexels.com/videos (CC0 licensed)
- NASA public domain videos: https://images.nasa.gov

For pipeline testing, any 5-10 minute video with speech works.
