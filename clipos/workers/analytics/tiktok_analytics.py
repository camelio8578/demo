"""TikTok Analytics API ingestor.

Required environment variables:
  TIKTOK_ACCESS_TOKEN  — Per-creator OAuth access token with research scope

API reference:
  POST https://open.tiktokapis.com/v2/research/video/query/
  Authorization: Bearer <access_token>
  Body: { filters: { video_ids: [platform_post_id] },
          fields: ["view_count", "like_count", "comment_count", "share_count",
                   "play_count", "average_play_time"] }

Returns a dict matching AnalyticsSnapshot fields, or None if not configured.
"""

from __future__ import annotations

import os

import structlog

log = structlog.get_logger(__name__)


class TikTokAnalyticsIngestor:
    """Ingest analytics for a published TikTok video.

    Falls back gracefully (returns None) if credentials are not configured.
    """

    def ingest(self, platform_post_id: str) -> dict | None:
        """Fetch analytics for the given TikTok video ID.

        Args:
            platform_post_id: The TikTok video ID.

        Returns:
            A dict with analytics data, or None if not configured / on error.
        """
        if not os.getenv("TIKTOK_ACCESS_TOKEN"):
            log.debug("tiktok_analytics_not_configured")
            return None

        try:
            # TODO: TikTok Research API call
            # POST https://open.tiktokapis.com/v2/research/video/query/
            # Headers: Authorization: Bearer <TIKTOK_ACCESS_TOKEN>
            # Body: {
            #   "filters": { "video_ids": [platform_post_id] },
            #   "fields": ["view_count", "like_count", "comment_count",
            #              "share_count", "play_count", "average_play_time"]
            # }
            raise NotImplementedError(
                "TikTok Analytics requires Developer credentials. "
                "See docs/credential-checklist.md."
            )
        except Exception as exc:
            log.warning(
                "tiktok_analytics_ingest_failed",
                platform_post_id=platform_post_id,
                error=str(exc),
            )
            return None
