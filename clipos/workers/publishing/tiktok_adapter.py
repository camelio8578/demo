"""TikTok Content Posting API v2 adapter.

Required environment variables:
  TIKTOK_CLIENT_KEY    — App client key from TikTok Developer Portal
  TIKTOK_CLIENT_SECRET — App client secret
  TIKTOK_ACCESS_TOKEN  — Per-creator OAuth access token
                         (requires content_posting scope approval)

Implementation notes:
  - Two-step upload:
    1. POST https://open.tiktokapis.com/v2/post/publish/video/init/
       → receive upload_url and publish_id
    2. PUT video bytes to upload_url
    3. Poll https://open.tiktokapis.com/v2/post/publish/status/fetch/
  - Requires TikTok Developer app approval for the content_publishing scope.
  - See docs/credential-checklist.md for full setup instructions.
"""

from __future__ import annotations

import os

import structlog

from workers.publishing.adapter import PublishResult, PublishingAdapter

log = structlog.get_logger(__name__)

TIKTOK_INIT_URL = "https://open.tiktokapis.com/v2/post/publish/video/init/"
TIKTOK_STATUS_URL = "https://open.tiktokapis.com/v2/post/publish/status/fetch/"


class TikTokAdapter(PublishingAdapter):
    """TikTok Shorts publishing via the TikTok Content Posting API v2."""

    async def is_configured(self) -> bool:
        return bool(
            os.getenv("TIKTOK_CLIENT_KEY") and os.getenv("TIKTOK_ACCESS_TOKEN")
        )

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
                "TikTok adapter not configured. "
                "Set TIKTOK_CLIENT_KEY and TIKTOK_ACCESS_TOKEN. "
                "Requires TikTok Developer app approval for content_publishing scope. "
                "See docs/credential-checklist.md."
            )
            log.warning("tiktok_adapter_not_configured")
            return PublishResult(
                success=False,
                platform_post_id=None,
                response_data={},
                error_message=msg,
            )

        # Full implementation:
        # 1. POST TIKTOK_INIT_URL with Authorization: Bearer <access_token>
        #    Body: {"post_info": {"title": ..., "privacy_level": "PUBLIC_TO_EVERYONE"},
        #           "source_info": {"source": "FILE_UPLOAD", "video_size": ...}}
        # 2. Receive {"data": {"upload_url": ..., "publish_id": ...}}
        # 3. PUT video bytes to upload_url (chunked for large files)
        # 4. Poll TIKTOK_STATUS_URL with publish_id until status == "PUBLISH_COMPLETE"
        raise NotImplementedError(
            "TikTok upload requires approved developer app with content_publishing scope. "
            "See docs/credential-checklist.md for setup instructions."
        )

    async def get_post_status(self, platform_post_id: str) -> dict:
        raise NotImplementedError(
            "TikTok get_post_status requires TikTok Developer credentials."
        )

    async def delete_post(self, platform_post_id: str) -> bool:
        raise NotImplementedError(
            "TikTok delete_post requires TikTok Developer credentials."
        )
