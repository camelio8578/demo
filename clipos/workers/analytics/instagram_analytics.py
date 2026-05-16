"""Instagram Insights API ingestor.

Required environment variables:
  INSTAGRAM_ACCESS_TOKEN  — Long-lived access token with instagram_manage_insights permission
  INSTAGRAM_ACCOUNT_ID    — Instagram Business Account ID

API reference:
  GET https://graph.facebook.com/v18.0/{media_id}/insights
  Params:
    metric=plays,reach,likes,comments,shares,saved,ig_reels_video_view_total_time
    access_token=<INSTAGRAM_ACCESS_TOKEN>

Returns a dict matching AnalyticsSnapshot fields, or None if not configured.
"""

from __future__ import annotations

import os

import structlog

log = structlog.get_logger(__name__)

GRAPH_BASE = "https://graph.facebook.com/v18.0"


class InstagramAnalyticsIngestor:
    """Ingest analytics for a published Instagram Reel.

    Falls back gracefully (returns None) if credentials are not configured.
    """

    def ingest(self, platform_post_id: str) -> dict | None:
        """Fetch analytics for the given Instagram media ID.

        Args:
            platform_post_id: The Instagram media ID.

        Returns:
            A dict with analytics data, or None if not configured / on error.
        """
        if not os.getenv("INSTAGRAM_ACCESS_TOKEN"):
            log.debug("instagram_analytics_not_configured")
            return None

        try:
            # TODO: Instagram Graph API insights call
            # GET {GRAPH_BASE}/{platform_post_id}/insights
            # Params:
            #   metric=plays,reach,likes,comments,shares,saved,
            #          ig_reels_video_view_total_time,ig_reels_avg_watch_time
            #   access_token=<INSTAGRAM_ACCESS_TOKEN>
            #
            # Response: {"data": [{"name": "plays", "values": [{"value": N}]}, ...]}
            raise NotImplementedError(
                "Instagram Analytics requires Graph API credentials. "
                "See docs/credential-checklist.md."
            )
        except Exception as exc:
            log.warning(
                "instagram_analytics_ingest_failed",
                platform_post_id=platform_post_id,
                error=str(exc),
            )
            return None
