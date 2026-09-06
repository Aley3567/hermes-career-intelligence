"""Domain models.

External observations and user-owned profile data are deliberately separate.
Claims never replace evidence: every important conclusion keeps traceable source
text or a timestamped transcript excerpt.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator


def _id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


def utc_now() -> datetime:
    return datetime.now(UTC)


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class Platform(StrEnum):
    XIAOHONGSHU = "xiaohongshu"
    DOUYIN = "douyin"
    WECHAT_MP = "wechat_mp"
    WECHAT_CHANNELS = "wechat_channels"
    OTHER = "other"


class ContentType(StrEnum):
    NOTE = "note"
    ARTICLE = "article"
    VIDEO = "video"
    COMMENT = "comment"


class EvidenceStance(StrEnum):
    SUPPORTS = "supports"
    COUNTERS = "counters"
    CONTEXT = "context"


class RunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ObservationState(StrEnum):
    PENDING = "pending"
    MERGED = "merged"
    REJECTED = "rejected"


class Source(StrictModel):
    source_id: str = Field(default_factory=lambda: _id("src"))
    platform: Platform
    kind: ContentType
    locator: str
    collected_at: datetime = Field(default_factory=utc_now)
    cache_url: HttpUrl | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class Creator(StrictModel):
    creator_id: str = Field(default_factory=lambda: _id("creator"))
    platform: Platform
    platform_creator_id: str
    nickname: str
    bio: str = ""
    profile_url: HttpUrl | None = None
    claimed_company: str | None = None
    claimed_role: str | None = None
    topics: list[str] = Field(default_factory=list)
    followers: int | None = Field(default=None, ge=0)
    engagement: float = Field(default=0.0, ge=0)
    content_count: int = Field(default=0, ge=0)
    career_relevance: float = Field(default=0.0, ge=0, le=1)
    signal_density: float = Field(default=0.0, ge=0, le=1)
    first_hand_experience_score: float = Field(default=0.0, ge=0, le=1)
    credibility_score: float = Field(default=0.0, ge=0, le=1)
    marketing_ratio: float = Field(default=0.0, ge=0, le=1)
    useful_note_ratio: float = Field(default=0.0, ge=0, le=1)
    last_seen: datetime = Field(default_factory=utc_now)


class Content(StrictModel):
    content_id: str = Field(default_factory=lambda: _id("content"))
    source_id: str
    creator_id: str | None = None
    platform_content_id: str
    title: str = ""
    url: HttpUrl
    content_type: ContentType
    published_at: datetime | None = None
    collected_at: datetime = Field(default_factory=utc_now)
    raw_text: str = ""
    engagement: float = Field(default=0.0, ge=0)
    metadata: dict[str, Any] = Field(default_factory=dict)


class TranscriptSegment(StrictModel):
    segment_id: str = Field(default_factory=lambda: _id("segment"))
    start_seconds: float = Field(ge=0)
    end_seconds: float = Field(gt=0)
    text: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_interval(self) -> "TranscriptSegment":
        if self.end_seconds <= self.start_seconds:
            raise ValueError("end_seconds must be greater than start_seconds")
        return self


class Transcript(StrictModel):
    transcript_id: str = Field(default_factory=lambda: _id("transcript"))
    content_id: str
    language: str = "zh"
    segments: list[TranscriptSegment]
    provider: str
    media_hash: str | None = None
    generated_at: datetime = Field(default_factory=utc_now)


class Topic(StrictModel):
    topic_id: str = Field(default_factory=lambda: _id("topic"))
    name: str
    aliases: list[str] = Field(default_factory=list)


class Evidence(StrictModel):
    evidence_id: str = Field(default_factory=lambda: _id("evidence"))
    platform: Platform
    creator_id: str
    content_id: str
    content_url: HttpUrl
    content_title: str = ""
    original_text: str = Field(min_length=1)
    stance: EvidenceStance = EvidenceStance.SUPPORTS
    transcript_segment_id: str | None = None
    transcript_start: float | None = Field(default=None, ge=0)
    transcript_end: float | None = Field(default=None, ge=0)
    collected_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def validate_timestamps(self) -> "Evidence":
        if (self.transcript_start is None) != (self.transcript_end is None):
            raise ValueError("transcript_start and transcript_end must appear together")
        if self.transcript_start is not None and self.transcript_end <= self.transcript_start:
            raise ValueError("transcript_end must be greater than transcript_start")
        return self


class Claim(StrictModel):
    claim_id: str = Field(default_factory=lambda: _id("claim"))
    claim_text: str = Field(min_length=1)
    normalized_claim: str = Field(min_length=1)
    topic: str
    confidence: float = Field(default=0.0, ge=0, le=1)
    source_count: int = Field(default=0, ge=0)
    creator_count: int = Field(default=0, ge=0)
    supporting_evidence_ids: list[str] = Field(default_factory=list)
    counter_evidence_ids: list[str] = Field(default_factory=list)
    first_seen: datetime = Field(default_factory=utc_now)
    last_seen: datetime = Field(default_factory=utc_now)


class Consensus(StrictModel):
    claim: Claim
    rationale: str


class DisagreementPosition(StrictModel):
    label: str
    claim_text: str
    evidence_ids: list[str]


class Disagreement(StrictModel):
    topic: str
    position_a: DisagreementPosition
    position_b: DisagreementPosition
    possible_explanation: str
    user_relevance: str


class EmergingSignal(StrictModel):
    signal: str
    first_seen: datetime
    recent_frequency: int = Field(ge=0)
    historical_frequency: int = Field(ge=0)
    supporting_evidence_ids: list[str]
    possible_implication: str


class Project(StrictModel):
    name: str
    description: str = ""
    technologies: list[str] = Field(default_factory=list)
    status: str = "planned"


class UserProfile(StrictModel):
    profile_id: str = "primary"
    education: str = "中国本科学生"
    major: str | None = None
    location: str = "中国"
    target_roles: list[str] = Field(default_factory=list)
    target_companies: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    learning_topics: list[str] = Field(default_factory=list)
    projects: list[Project] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    experience: list[str] = Field(default_factory=list)
    resume_state: str = "未记录"
    interview_history: list[str] = Field(default_factory=list)
    current_goals: list[str] = Field(default_factory=list)
    career_stage: str = "本科在读，准备实习"
    short_term_plan: list[str] = Field(default_factory=list)
    long_term_plan: list[str] = Field(default_factory=list)
    updated_at: datetime = Field(default_factory=utc_now)


class UserObservation(StrictModel):
    observation_id: str = Field(default_factory=lambda: _id("observation"))
    category: str
    observation: str
    confidence: float = Field(ge=0, le=1)
    state: ObservationState = ObservationState.PENDING
    observed_at: datetime = Field(default_factory=utc_now)
    merged_at: datetime | None = None


class SkillGap(StrictModel):
    skill: str
    evidence_claim_ids: list[str]
    current_state: str
    target_state: str
    priority: int = Field(ge=1, le=5)


class RecommendedAction(StrictModel):
    title: str
    rationale: str
    days: int = Field(ge=1)
    success_metric: str
    related_gap: str


class ResearchRun(StrictModel):
    run_id: str = Field(default_factory=lambda: _id("run"))
    question: str
    queries: list[str]
    status: RunStatus = RunStatus.PENDING
    started_at: datetime = Field(default_factory=utc_now)
    completed_at: datetime | None = None
    error: str | None = None


class ResearchPack(StrictModel):
    topic: str
    research_questions: list[str]
    queries_used: list[str]
    sources_scanned: int = Field(ge=0)
    sources_selected: int = Field(ge=0)
    creators_scanned: int = Field(ge=0)
    videos_transcribed: int = Field(ge=0)
    executive_summary: str
    consensus: list[Consensus]
    disagreements: list[Disagreement]
    emerging_signals: list[EmergingSignal]
    important_claims: list[Claim]
    top_creators: list[Creator]
    user_skill_gaps: list[SkillGap]
    recommended_actions: list[RecommendedAction]
    evidence_index: list[Evidence]
    limitations: list[str]
    generated_at: datetime = Field(default_factory=utc_now)


class ResearchResult(StrictModel):
    result_id: str = Field(default_factory=lambda: _id("result"))
    run_id: str
    pack: ResearchPack
    persisted_at: datetime = Field(default_factory=utc_now)
