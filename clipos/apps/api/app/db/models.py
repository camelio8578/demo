import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base import Base


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

CreatorStatus = Enum("active", "paused", "blocked", name="creator_status")
RiskLevel = Enum("low", "medium", "high", "blocked", name="risk_level")
Platform = Enum(
    "youtube", "tiktok", "instagram", "twitter", "linkedin", name="platform"
)
SourceVideoStatus = Enum(
    "discovered", "downloading", "downloaded", "failed", name="source_video_status"
)
TranscriptStatus = Enum(
    "pending", "processing", "completed", "failed", name="transcript_status"
)
CandidateClipStatus = Enum(
    "candidate", "approved", "rejected", "rendered", name="candidate_clip_status"
)
RenderedAssetStatus = Enum(
    "pending", "rendering", "completed", "failed", name="rendered_asset_status"
)
PublishingJobStatus = Enum(
    "queued", "in_progress", "published", "failed", "cancelled",
    name="publishing_job_status",
)
PublishAttemptStatus = Enum("success", "failed", name="publish_attempt_status")
ModerationSourceType = Enum(
    "video", "clip", "asset", "copy", name="moderation_source_type"
)
ModerationSeverity = Enum(
    "low", "medium", "high", "block", name="moderation_severity"
)
ActorType = Enum("system", "user", "api", name="actor_type")
ReviewTaskType = Enum(
    "review_clip", "approve_copy", "review_flag", "manual_check",
    name="review_task_type",
)
ReviewTaskStatus = Enum(
    "pending", "in_progress", "approved", "rejected", "escalated",
    name="review_task_status",
)


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class RightsProfile(Base):
    __tablename__ = "rights_profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    allow_repost: Mapped[bool] = mapped_column(Boolean, default=False)
    require_attribution: Mapped[bool] = mapped_column(Boolean, default=False)
    commercial_use_allowed: Mapped[bool] = mapped_column(Boolean, default=False)
    manual_review_required: Mapped[bool] = mapped_column(Boolean, default=False)
    risk_level: Mapped[str] = mapped_column(RiskLevel, nullable=False, default="medium")
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now()
    )

    creators: Mapped[list["Creator"]] = relationship("Creator", back_populates="rights_profile")


class Creator(Base):
    __tablename__ = "creators"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(CreatorStatus, nullable=False, default="active")
    rights_profile_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("rights_profiles.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now()
    )

    rights_profile: Mapped[Optional[RightsProfile]] = relationship(
        "RightsProfile", back_populates="creators"
    )
    platform_accounts: Mapped[list["CreatorPlatformAccount"]] = relationship(
        "CreatorPlatformAccount", back_populates="creator"
    )
    monitored_sources: Mapped[list["MonitoredSource"]] = relationship(
        "MonitoredSource", back_populates="creator"
    )
    source_videos: Mapped[list["SourceVideo"]] = relationship(
        "SourceVideo", back_populates="creator"
    )
    publishing_targets: Mapped[list["PublishingTarget"]] = relationship(
        "PublishingTarget", back_populates="creator"
    )


class CreatorPlatformAccount(Base):
    __tablename__ = "creator_platform_accounts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    creator_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("creators.id"), nullable=False
    )
    platform: Mapped[str] = mapped_column(Platform, nullable=False)
    platform_user_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    channel_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    display_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    access_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    refresh_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    token_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now()
    )

    creator: Mapped[Creator] = relationship("Creator", back_populates="platform_accounts")
    publishing_targets: Mapped[list["PublishingTarget"]] = relationship(
        "PublishingTarget", back_populates="platform_account"
    )


class MonitoredSource(Base):
    __tablename__ = "monitored_sources"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    creator_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("creators.id"), nullable=False
    )
    platform: Mapped[str] = mapped_column(Platform, nullable=False)
    source_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    source_identifier: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    polling_interval_minutes: Mapped[int] = mapped_column(Integer, default=60)
    last_polled_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now()
    )

    creator: Mapped[Creator] = relationship("Creator", back_populates="monitored_sources")
    source_videos: Mapped[list["SourceVideo"]] = relationship(
        "SourceVideo", back_populates="monitored_source"
    )


class SourceVideo(Base):
    __tablename__ = "source_videos"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    creator_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("creators.id"), nullable=False
    )
    monitored_source_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("monitored_sources.id"), nullable=True
    )
    platform_video_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    title: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    duration_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    downloaded_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    local_path: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    file_size_bytes: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    status: Mapped[str] = mapped_column(
        SourceVideoStatus, nullable=False, default="discovered"
    )
    failure_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now()
    )

    creator: Mapped[Creator] = relationship("Creator", back_populates="source_videos")
    monitored_source: Mapped[Optional[MonitoredSource]] = relationship(
        "MonitoredSource", back_populates="source_videos"
    )
    transcripts: Mapped[list["Transcript"]] = relationship(
        "Transcript", back_populates="source_video"
    )
    candidate_clips: Mapped[list["CandidateClip"]] = relationship(
        "CandidateClip", back_populates="source_video"
    )


class Transcript(Base):
    __tablename__ = "transcripts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    source_video_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("source_videos.id"), nullable=False
    )
    model_used: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    language: Mapped[str] = mapped_column(String(10), default="en")
    full_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    word_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    processing_time_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(TranscriptStatus, nullable=False, default="pending")
    failure_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now()
    )

    source_video: Mapped[SourceVideo] = relationship(
        "SourceVideo", back_populates="transcripts"
    )
    segments: Mapped[list["TranscriptSegment"]] = relationship(
        "TranscriptSegment", back_populates="transcript"
    )
    candidate_clips: Mapped[list["CandidateClip"]] = relationship(
        "CandidateClip", back_populates="transcript"
    )


class TranscriptSegment(Base):
    __tablename__ = "transcript_segments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    transcript_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("transcripts.id"), nullable=False
    )
    segment_index: Mapped[int] = mapped_column(Integer, nullable=False)
    start_time: Mapped[float] = mapped_column(Float, nullable=False)
    end_time: Mapped[float] = mapped_column(Float, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    speaker_label: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    transcript: Mapped[Transcript] = relationship("Transcript", back_populates="segments")


class CandidateClip(Base):
    __tablename__ = "candidate_clips"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    source_video_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("source_videos.id"), nullable=False
    )
    transcript_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("transcripts.id"), nullable=True
    )
    start_time: Mapped[float] = mapped_column(Float, nullable=False)
    end_time: Mapped[float] = mapped_column(Float, nullable=False)
    duration_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    segment_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        CandidateClipStatus, nullable=False, default="candidate"
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now()
    )

    source_video: Mapped[SourceVideo] = relationship(
        "SourceVideo", back_populates="candidate_clips"
    )
    transcript: Mapped[Optional[Transcript]] = relationship(
        "Transcript", back_populates="candidate_clips"
    )
    scores: Mapped[list["ClipScore"]] = relationship(
        "ClipScore", back_populates="candidate_clip"
    )
    rendered_assets: Mapped[list["RenderedAsset"]] = relationship(
        "RenderedAsset", back_populates="candidate_clip"
    )
    copy_variants: Mapped[list["CopyVariant"]] = relationship(
        "CopyVariant", back_populates="candidate_clip"
    )
    review_tasks: Mapped[list["UserReviewTask"]] = relationship(
        "UserReviewTask", back_populates="candidate_clip"
    )


class ClipScore(Base):
    __tablename__ = "clip_scores"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    candidate_clip_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("candidate_clips.id"), nullable=False
    )
    total_score: Mapped[float] = mapped_column(Float, nullable=False)
    speech_density: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    sentiment_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    hook_phrase_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    pause_burst_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    novelty_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    completeness_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    duration_fit_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    risk_flag_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    prior_performance_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    llm_rescore: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    scoring_version: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    candidate_clip: Mapped[CandidateClip] = relationship(
        "CandidateClip", back_populates="scores"
    )


class RenderedAsset(Base):
    __tablename__ = "rendered_assets"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    candidate_clip_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("candidate_clips.id"), nullable=False
    )
    output_path: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    thumbnail_path: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    file_size_bytes: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    resolution: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    fps: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    duration_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    render_job_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(
        RenderedAssetStatus, nullable=False, default="pending"
    )
    failure_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now()
    )

    candidate_clip: Mapped[CandidateClip] = relationship(
        "CandidateClip", back_populates="rendered_assets"
    )
    subtitle_assets: Mapped[list["SubtitleAsset"]] = relationship(
        "SubtitleAsset", back_populates="rendered_asset"
    )
    publishing_jobs: Mapped[list["PublishingJob"]] = relationship(
        "PublishingJob", back_populates="rendered_asset"
    )


class SubtitleAsset(Base):
    __tablename__ = "subtitle_assets"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    rendered_asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("rendered_assets.id"), nullable=False
    )
    srt_path: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    ass_path: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    style_config: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    burn_in_complete: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    rendered_asset: Mapped[RenderedAsset] = relationship(
        "RenderedAsset", back_populates="subtitle_assets"
    )


class CopyVariant(Base):
    __tablename__ = "copy_variants"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    candidate_clip_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("candidate_clips.id"), nullable=False
    )
    platform: Mapped[str] = mapped_column(Platform, nullable=False)
    variant_index: Mapped[int] = mapped_column(Integer, default=0)
    hook: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    title: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    caption: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    hashtags: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    llm_model_used: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    prompt_version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    candidate_clip: Mapped[CandidateClip] = relationship(
        "CandidateClip", back_populates="copy_variants"
    )
    publishing_jobs: Mapped[list["PublishingJob"]] = relationship(
        "PublishingJob", back_populates="copy_variant"
    )


class PublishingTarget(Base):
    __tablename__ = "publishing_targets"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    creator_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("creators.id"), nullable=False
    )
    platform: Mapped[str] = mapped_column(Platform, nullable=False)
    platform_account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("creator_platform_accounts.id"), nullable=False
    )
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    default_for_platform: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now()
    )

    creator: Mapped[Creator] = relationship("Creator", back_populates="publishing_targets")
    platform_account: Mapped[CreatorPlatformAccount] = relationship(
        "CreatorPlatformAccount", back_populates="publishing_targets"
    )
    publishing_jobs: Mapped[list["PublishingJob"]] = relationship(
        "PublishingJob", back_populates="publishing_target"
    )


class PublishingJob(Base):
    __tablename__ = "publishing_jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    rendered_asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("rendered_assets.id"), nullable=False
    )
    copy_variant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("copy_variants.id"), nullable=False
    )
    publishing_target_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("publishing_targets.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(
        PublishingJobStatus, nullable=False, default="queued"
    )
    scheduled_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    platform_post_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    failure_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now()
    )

    rendered_asset: Mapped[RenderedAsset] = relationship(
        "RenderedAsset", back_populates="publishing_jobs"
    )
    copy_variant: Mapped[CopyVariant] = relationship(
        "CopyVariant", back_populates="publishing_jobs"
    )
    publishing_target: Mapped[PublishingTarget] = relationship(
        "PublishingTarget", back_populates="publishing_jobs"
    )
    publish_attempts: Mapped[list["PublishAttempt"]] = relationship(
        "PublishAttempt", back_populates="publishing_job"
    )
    analytics_snapshots: Mapped[list["AnalyticsSnapshot"]] = relationship(
        "AnalyticsSnapshot", back_populates="publishing_job"
    )


class PublishAttempt(Base):
    __tablename__ = "publish_attempts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    publishing_job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("publishing_jobs.id"), nullable=False
    )
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    attempted_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    status: Mapped[str] = mapped_column(PublishAttemptStatus, nullable=False)
    response_code: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    response_body: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    failure_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    publishing_job: Mapped[PublishingJob] = relationship(
        "PublishingJob", back_populates="publish_attempts"
    )


class AnalyticsSnapshot(Base):
    __tablename__ = "analytics_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    publishing_job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("publishing_jobs.id"), nullable=False
    )
    snapshot_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    views: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    likes: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    comments: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    shares: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    saves: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    watch_time_seconds: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    completion_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    platform_raw: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    publishing_job: Mapped[PublishingJob] = relationship(
        "PublishingJob", back_populates="analytics_snapshots"
    )


class Experiment(Base):
    __tablename__ = "experiments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    scoring_weights_config: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    results_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class ModerationFlag(Base):
    __tablename__ = "moderation_flags"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    source_type: Mapped[str] = mapped_column(ModerationSourceType, nullable=False)
    source_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    flag_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    flag_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    severity: Mapped[str] = mapped_column(ModerationSeverity, nullable=False, default="low")
    resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    resolved_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    actor_type: Mapped[str] = mapped_column(ActorType, nullable=False)
    actor_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    action: Mapped[str] = mapped_column(String(255), nullable=False)
    target_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    target_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    payload: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())


class UserReviewTask(Base):
    __tablename__ = "user_review_tasks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    task_type: Mapped[str] = mapped_column(ReviewTaskType, nullable=False)
    candidate_clip_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("candidate_clips.id"), nullable=True
    )
    assigned_to: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(ReviewTaskStatus, nullable=False, default="pending")
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now()
    )

    candidate_clip: Mapped[Optional[CandidateClip]] = relationship(
        "CandidateClip", back_populates="review_tasks"
    )


class SystemSetting(Base):
    __tablename__ = "system_settings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    value: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    updated_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now()
    )
