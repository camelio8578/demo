"""YouTube Analytics API ingestor.

Required environment variables:
  YOUTUBE_API_KEY     — YouTube Data / Analytics API key
  YOUTUBE_CLIENT_ID   — OAuth 2.0 client ID (optional; needed for private video analytics)

API reference:
  GET https://youtubeanalytics.googleapis.com/v2/reports
  Parameters:
    ids=channel==MINE
    metrics=views,likes,comments,shares,estimatedMinutesWatched,averageViewPercentage
    dimensions=video
    filters=video=={platform_post_id}
    startDate=2020-01-01
    endDate=<today>

Returns a dict matching AnalyticsSnapshot fields, or None if not configured.
"""

from __future__ import annotations

import os

import structlog

log = structlog.get_logger(__name__)


class YouTubeAnalyticsIngestor:
    """Ingest analytics for a published YouTube Shorts post.

    Falls back gracefully (returns None) if credentials are not configured,
    so that missing analytics never crash the rest of the pipeline.
    """

    def ingest(self, platform_post_id: str) -> dict | None:
        """Fetch latest analytics for the given YouTube video ID.

        Args:
            platform_post_id: The YouTube video ID (e.g. "dQw4w9WgXcQ").

        Returns:
            A dict with keys: views, likes, comments, shares, watch_time_seconds,
            completion_rate, platform_raw.  Returns None if not configured or on error.
        """
        if not os.getenv("YOUTUBE_API_KEY"):
            log.debug("youtube_analytics_not_configured")
            return None

        try:
            # TODO: Implement YouTube Analytics API call.
            # GET https://youtubeanalytics.googleapis.com/v2/reports
            # Required params:
            #   key=<YOUTUBE_API_KEY>
            #   ids=channel==MINE
            #   metrics=views,likes,comments,shares,estimatedMinutesWatched,averageViewPercentage
            #   dimensions=video
            #   filters=video=={platform_post_id}
            #   startDate=2020-01-01
            #   endDate=<today>
            raise NotImplementedError(
                "YouTube Analytics API requires credentials. "
                "See docs/credential-checklist.md."
            )
        except Exception as exc:
            log.warning(
                "youtube_analytics_ingest_failed",
                platform_post_id=platform_post_id,
                error=str(exc),
            )
            return None
