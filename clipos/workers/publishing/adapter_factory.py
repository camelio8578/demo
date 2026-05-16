"""Factory function for creating publishing adapters by platform name."""

from __future__ import annotations

from workers.publishing.adapter import PublishingAdapter
from workers.publishing.instagram_adapter import InstagramAdapter
from workers.publishing.tiktok_adapter import TikTokAdapter
from workers.publishing.youtube_adapter import YouTubeAdapter

_ADAPTER_REGISTRY: dict[str, type[PublishingAdapter]] = {
    "youtube": YouTubeAdapter,
    "tiktok": TikTokAdapter,
    "instagram": InstagramAdapter,
}


def get_adapter(platform: str) -> PublishingAdapter:
    """Return the appropriate publishing adapter for the given platform name.

    Args:
        platform: One of 'youtube', 'tiktok', 'instagram'.

    Raises:
        ValueError: If the platform is not registered.
    """
    cls = _ADAPTER_REGISTRY.get(platform.lower())
    if not cls:
        supported = ", ".join(sorted(_ADAPTER_REGISTRY))
        raise ValueError(
            f"Unknown platform: {platform!r}. Supported platforms: {supported}"
        )
    return cls()
