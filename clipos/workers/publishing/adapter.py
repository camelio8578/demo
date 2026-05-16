"""Abstract base class for platform publishing adapters."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class PublishResult:
    """Result returned by every publishing adapter's upload_video()."""

    success: bool
    platform_post_id: str | None
    response_data: dict = field(default_factory=dict)
    error_message: str | None = None


class PublishingAdapter(ABC):
    """Abstract base for platform-specific publishing adapters.

    Each adapter is responsible for:
    - Checking whether its required credentials are present.
    - Uploading and publishing a rendered video clip.
    - Querying the status of a previously published post.
    - Deleting a post if needed.

    Adapters MUST return a PublishResult rather than raising on API errors
    so that the publishing_worker can handle retries and error persistence
    consistently.
    """

    @abstractmethod
    async def is_configured(self) -> bool:
        """Return True if all required credentials are present in the environment."""
        pass

    @abstractmethod
    async def upload_video(
        self,
        video_path: str,
        thumbnail_path: str | None,
        title: str,
        caption: str,
        hashtags: list[str],
    ) -> PublishResult:
        """Upload and publish a video to the target platform.

        Args:
            video_path: Absolute filesystem path to the rendered MP4.
            thumbnail_path: Optional path to a thumbnail image.
            title: Video title (used by YouTube; ignored by TikTok/Instagram).
            caption: Post caption / description.
            hashtags: List of hashtag strings (without leading #).

        Returns:
            PublishResult with success flag, platform_post_id, and any error detail.
        """
        pass

    @abstractmethod
    async def get_post_status(self, platform_post_id: str) -> dict:
        """Return platform-specific status dict for a published post."""
        pass

    @abstractmethod
    async def delete_post(self, platform_post_id: str) -> bool:
        """Delete a published post.  Return True on success."""
        pass
