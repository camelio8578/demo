"""Meta Graph API adapter for Instagram Reels publishing.

Required environment variables:
  INSTAGRAM_ACCESS_TOKEN  — Long-lived page/user access token
                            (requires instagram_content_publish permission)
  INSTAGRAM_ACCOUNT_ID    — Instagram Business Account ID

Implementation notes:
  - Two-step publish:
    1. POST /v18.0/{ig-user-id}/media
       { media_type: REELS, video_url: <public HTTPS URL>, caption: ..., share_to_feed: true }
       → receive creation_id
    2. Poll /v18.0/{creation_id}?fields=status_code until FINISHED
    3. POST /v18.0/{ig-user-id}/media_publish { creation_id: ... }
       → receive post_id
  - IMPORTANT: Instagram requires the video to be at a publicly accessible HTTPS URL.
    Local file paths are NOT supported — video must be uploaded to S3/CDN first.
  - Requires Meta App Review for instagram_content_publish permission.
  - See docs/credential-checklist.md for full setup instructions.
"""

from __future__ import annotations

import os

import structlog

from workers.publishing.adapter import PublishResult, PublishingAdapter

log = structlog.get_logger(__name__)

GRAPH_BASE = "https://graph.facebook.com/v18.0"


class InstagramAdapter(PublishingAdapter):
    """Instagram Reels publishing via the Meta Graph API."""

    async def is_configured(self) -> bool:
        return bool(
            os.getenv("INSTAGRAM_ACCESS_TOKEN")
            and os.getenv("INSTAGRAM_ACCOUNT_ID")
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
                "Instagram adapter not configured. "
                "Set INSTAGRAM_ACCESS_TOKEN and INSTAGRAM_ACCOUNT_ID. "
                "Requires Meta App Review for instagram_content_publish permission. "
                "See docs/credential-checklist.md."
            )
            log.warning("instagram_adapter_not_configured")
            return PublishResult(
                success=False,
                platform_post_id=None,
                response_data={},
                error_message=msg,
            )

        # Full implementation:
        # Step 1 — Create media container:
        #   POST {GRAPH_BASE}/{account_id}/media
        #   Params: access_token, media_type=REELS, video_url=<public_url>,
        #           caption=<caption + hashtags>, share_to_feed=true
        #   → {"id": creation_id}
        #
        # Step 2 — Poll for container to be ready:
        #   GET {GRAPH_BASE}/{creation_id}?fields=status_code&access_token=...
        #   Poll until status_code == "FINISHED" (may take 30–120s)
        #
        # Step 3 — Publish:
        #   POST {GRAPH_BASE}/{account_id}/media_publish
        #   Body: { creation_id: ..., access_token: ... }
        #   → {"id": post_id}
        #
        # NOTE: video_path must be a public HTTPS URL, not a local path.
        # Upload to S3/R2/GCS and use the signed URL before calling this adapter.
        raise NotImplementedError(
            "Instagram requires a public video URL and an approved Meta app. "
            "See docs/credential-checklist.md for setup instructions."
        )

    async def get_post_status(self, platform_post_id: str) -> dict:
        raise NotImplementedError(
            "Instagram get_post_status requires Meta Graph API credentials."
        )

    async def delete_post(self, platform_post_id: str) -> bool:
        raise NotImplementedError(
            "Instagram delete_post requires Meta Graph API credentials."
        )
