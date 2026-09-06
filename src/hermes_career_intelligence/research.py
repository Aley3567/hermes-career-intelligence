"""Deterministic first vertical slice of the Career Research Engine.

Production providers can later replace the mock samples. Aggregation, evidence
traceability, disagreement preservation, and user-gap generation remain stable.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime

from pydantic import Field, field_validator

from .models import (
    Claim,
    Consensus,
    Creator,
    Disagreement,
    DisagreementPosition,
    EmergingSignal,
    Evidence,
    RecommendedAction,
    ResearchPack,
    SkillGap,
    StrictModel,
    UserProfile,
)


class ResearchSample(StrictModel):
    creator: Creator
    evidence: Evidence
    claim_text: str
    normalized_claim: str
    topic: str
    published_at: datetime
    source_quality: float = Field(ge=0, le=1)
    required_skill: str | None = None
    opposes: str | None = None
    historical_mentions: int = Field(default=0, ge=0)

    @field_validator("published_at")
    @classmethod
    def published_at_must_be_timezone_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("published_at must be timezone-aware")
        return value.astimezone(UTC)


DEFAULT_QUERIES = [
    "AI Agent 实习",
    "Agent 开发实习",
    "大模型应用开发 实习",
    "AI Agent 面试",
    "Agent 项目 简历",
    "大厂 AI 实习",
    "HR AI Agent",
    "Agent Evaluation 项目",
]


def creator_score(creator: Creator) -> float:
    """Rank for usefulness, not follower count."""
    positive = (
        0.25 * creator.career_relevance
        + 0.20 * creator.first_hand_experience_score
        + 0.20 * creator.signal_density
        + 0.15 * creator.credibility_score
        + 0.10 * creator.useful_note_ratio
        + 0.05 * min(creator.engagement / 10_000, 1)
    )
    return round(max(0.0, min(1.0, positive - 0.15 * creator.marketing_ratio)), 4)


def _known_skills(profile: UserProfile) -> set[str]:
    return {item.casefold() for item in [*profile.skills, *profile.learning_topics]}


class CareerResearchEngine:
    def __init__(self, now: datetime | None = None) -> None:
        resolved_now = now or datetime.now(UTC)
        if resolved_now.tzinfo is None or resolved_now.utcoffset() is None:
            raise ValueError("now must be timezone-aware")
        self.now = resolved_now.astimezone(UTC)

    def run(
        self,
        question: str,
        profile: UserProfile,
        samples: list[ResearchSample],
    ) -> ResearchPack:
        selected = sorted(
            samples,
            key=lambda item: (creator_score(item.creator), item.source_quality, item.published_at),
            reverse=True,
        )
        grouped: dict[str, list[ResearchSample]] = defaultdict(list)
        for sample in selected:
            grouped[sample.normalized_claim].append(sample)

        claims: dict[str, Claim] = {}
        for normalized, group in grouped.items():
            evidence_ids = [item.evidence.evidence_id for item in group]
            creator_count = len({item.creator.creator_id for item in group})
            recency = sum((self.now - item.published_at).days <= 30 for item in group) / len(group)
            quality = sum(item.source_quality * creator_score(item.creator) for item in group) / len(group)
            confidence = min(0.95, 0.25 + 0.12 * len(group) + 0.10 * creator_count + 0.25 * quality + 0.12 * recency)
            claims[normalized] = Claim(
                claim_id=f"claim_{normalized}",
                claim_text=group[0].claim_text,
                normalized_claim=normalized,
                topic=group[0].topic,
                confidence=round(confidence, 3),
                source_count=len(group),
                creator_count=creator_count,
                supporting_evidence_ids=evidence_ids,
                first_seen=min(item.published_at for item in group),
                last_seen=max(item.published_at for item in group),
            )

        consensus = [
            Consensus(
                claim=claim,
                rationale=f"{claim.creator_count} 位独立创作者、{claim.source_count} 条证据共同支持。",
            )
            for claim in claims.values()
            if claim.creator_count >= 2
        ]

        disagreements: list[Disagreement] = []
        seen_pairs: set[tuple[str, str]] = set()
        for normalized, group in grouped.items():
            for sample in group:
                if not sample.opposes or sample.opposes not in claims:
                    continue
                pair = tuple(sorted((normalized, sample.opposes)))
                if pair in seen_pairs:
                    continue
                seen_pairs.add(pair)
                other = claims[sample.opposes]
                current = claims[normalized]
                disagreements.append(
                    Disagreement(
                        topic=current.topic,
                        position_a=DisagreementPosition(
                            label="Position A",
                            claim_text=current.claim_text,
                            evidence_ids=current.supporting_evidence_ids,
                        ),
                        position_b=DisagreementPosition(
                            label="Position B",
                            claim_text=other.claim_text,
                            evidence_ids=other.supporting_evidence_ids,
                        ),
                        possible_explanation="岗位类型与团队成熟度不同，评价标准可能偏工程交付或算法基础。",
                        user_relevance="应同时保留工程闭环证据和必要算法基础，不把单一观点当成统一招聘标准。",
                    )
                )

        emerging: list[EmergingSignal] = []
        for normalized, group in grouped.items():
            recent = sum((self.now - item.published_at).days <= 30 for item in group)
            historical = max(item.historical_mentions for item in group)
            if recent >= 2 and historical <= 1:
                claim = claims[normalized]
                emerging.append(
                    EmergingSignal(
                        signal=claim.claim_text,
                        first_seen=claim.first_seen,
                        recent_frequency=recent,
                        historical_frequency=historical,
                        supporting_evidence_ids=claim.supporting_evidence_ids,
                        possible_implication="近期需求密度上升，适合进入下一轮项目迭代与简历证据。",
                    )
                )

        known = _known_skills(profile)
        gaps: list[SkillGap] = []
        for normalized, group in grouped.items():
            skill = group[0].required_skill
            if not skill or skill.casefold() in known:
                continue
            claim = claims[normalized]
            priority = 5 if claim.creator_count >= 2 else 4
            gaps.append(
                SkillGap(
                    skill=skill,
                    evidence_claim_ids=[claim.claim_id],
                    current_state="用户画像中尚未记录",
                    target_state="在可运行项目中实现，并提供可量化结果",
                    priority=priority,
                )
            )

        gaps.sort(key=lambda gap: gap.priority, reverse=True)
        actions = [
            RecommendedAction(
                title=f"补齐 {gap.skill}",
                rationale="该能力由高价值来源重复提及，且用户画像尚无完成证据。",
                days=10 if index == 0 else 7,
                success_metric=f"项目中存在可运行的 {gap.skill} 实现、测试与结果记录",
                related_gap=gap.skill,
            )
            for index, gap in enumerate(gaps[:3])
        ]

        creators = {item.creator.creator_id: item.creator for item in selected}
        top_creators = sorted(creators.values(), key=creator_score, reverse=True)
        evidence = [item.evidence for item in selected]
        return ResearchPack(
            topic="AI Agent 实习生核心竞争力",
            research_questions=[question],
            queries_used=DEFAULT_QUERIES,
            sources_scanned=len(samples),
            sources_selected=len(selected),
            creators_scanned=len(creators),
            videos_transcribed=sum(item.evidence.transcript_start is not None for item in selected),
            executive_summary="Mock 垂直切片显示：工程闭环与可衡量的 Agent Evaluation 是当前最强信号，同时保留算法基础与工程交付侧重点的分歧。",
            consensus=sorted(consensus, key=lambda item: item.claim.confidence, reverse=True),
            disagreements=disagreements,
            emerging_signals=emerging,
            important_claims=sorted(claims.values(), key=lambda item: item.confidence, reverse=True),
            top_creators=top_creators,
            user_skill_gaps=gaps,
            recommended_actions=actions,
            evidence_index=evidence,
            limitations=["当前结果来自 MockSocialProvider，用于验证闭环，不代表真实平台结论。"],
            generated_at=self.now,
        )
