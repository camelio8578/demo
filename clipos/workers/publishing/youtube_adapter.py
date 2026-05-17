"""YouTube Data API v3 publishing adapter.

Required environment variables:
  YOUTUBE_CLIENT_ID       — OAuth 2.0 client ID (from Google Cloud Console)
  YOUTUBE_CLIENT_SECRET   — OAuth 2.0 client secret
  YOUTUBE_REFRESH_TOKEN   — Per-account refresh token (long-lived)
  YOUTUBE_API_KEY         — API key for public-data requests

Implementation notes:
  - Uses resumable upload for large files (required for videos > a few MB).
  - Requires the `google-api-python-client` and `google-auth-oauthlib` packages.
  - OAuth credentials must have the `https://www.googleapis.com/auth/youtube.upload` scope.
  - See docs/credential-checklist.md for full setup instructions.
"""

from __future__ import annotations

import os

import structlog

from workers.publishing.adapter import PublishResult, PublishingAdapter

log = structlog.get_logger(__name__)


class YouTubeAdapter(PublishingAdapter):
    """YouTube Shorts publishing via the YouTube Data API v3."""

    # ---------------------------------------------------------------------------
    # Configuration check
    # ---------------------------------------------------------------------------

    async def is_configured(self) -> bool:
        return bool(
            os.getenv("YOUTUBE_CLIENT_ID") and os.getenv("YOUTUBE_CLIENT_SECRET")
        )

    # ---------------------------------------------------------------------------
    # Upload
    # ---------------------------------------------------------------------------

    async def upload_video(
        self,
        video_path: str,
        thumbnail_path: str | None,
        title: str,
        caption: str,
        hashtags: list[str],
    ) -> PublishResult:
        if not await self.is_configured():
            msg = (
                "YouTube adapter not configured. "
                "Set YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET, and YOUTUBE_REFRESH_TOKEN. "
                "See docs/credential-checklist.md."
            )
            log.warning("youtube_adapter_not_configured")
            return PublishResult(
                success=False,
                platform_post_id=None,
                response_data={},
                error_message=msg,
            )

        # Full implementation requires:
        # 1. pip install google-api-python-client google-auth-oauthlib
        # 2. OAuth 2.0 credentials from Google Cloud Console with
        #    youtube.upload scope enabled.
        # 3. Exchange refresh token for access token, then:
        #    - Build a MediaFileUpload object for resumable upload.
        #    - POST to videos.insert with snippet + status body.
        #    - Optionally set thumbnail via thumbnails.set.
        raise NotImplementedError(
            "YouTube upload requires OAuth credentials. "
            "See docs/credential-checklist.md for setup instructions."
        )

    # ---------------------------------------------------------------------------
    # Post status
    # ---------------------------------------------------------------------------

    async def get_post_status(self, platform_post_id: str) -> dict:
        """Fetch video status from the YouTube Data API."""
        raise NotImplementedError(
            "YouTube get_post_status requires YouTube Data API v3 credentials."
        )

    # ---------------------------------------------------------------------------
    # Delete
    # ---------------------------------------------------------------------------

    async def delete_post(self, platform_post_id: str) -> bool:
        """Delete a YouTube video by ID."""
        raise NotImplementedError(
            "YouTube delete_post requires YouTube Data API v3 credentials."
        )
