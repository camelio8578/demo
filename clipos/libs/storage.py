"""File path helpers based on DATA_DIR environment variable."""

import os
from pathlib import Path


def get_data_dir() -> Path:
    return Path(os.getenv("DATA_DIR", "/data"))


def videos_dir() -> Path:
    path = get_data_dir() / "videos"
    path.mkdir(parents=True, exist_ok=True)
    return path


def audio_dir() -> Path:
    path = get_data_dir() / "audio"
    path.mkdir(parents=True, exist_ok=True)
    return path


def thumbnails_dir() -> Path:
    path = get_data_dir() / "thumbnails"
    path.mkdir(parents=True, exist_ok=True)
    return path


def rendered_dir() -> Path:
    path = get_data_dir() / "rendered"
    path.mkdir(parents=True, exist_ok=True)
    return path


def subtitles_dir() -> Path:
    path = get_data_dir() / "subtitles"
    path.mkdir(parents=True, exist_ok=True)
    return path


def video_path(video_id: str) -> Path:
    return videos_dir() / f"{video_id}.mp4"


def audio_path(video_id: str) -> Path:
    return audio_dir() / f"{video_id}.wav"


def thumbnail_path(asset_id: str) -> Path:
    return thumbnails_dir() / f"{asset_id}.jpg"


def rendered_path(asset_id: str) -> Path:
    return rendered_dir() / f"{asset_id}.mp4"


def srt_path(asset_id: str) -> Path:
    return subtitles_dir() / f"{asset_id}.srt"


def ass_path(asset_id: str) -> Path:
    return subtitles_dir() / f"{asset_id}.ass"
