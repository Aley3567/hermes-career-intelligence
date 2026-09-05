"""Reproducible social samples for offline acceptance tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from .models import Creator, Evidence, Platform, UserProfile
from .research import ResearchSample


def initial_profile() -> UserProfile:
    return UserProfile(
        target_roles=["AI Agent 实习", "LLM Application", "大模型应用开发"],
        skills=[],
        learning_topics=[
            "dict",
            "list",
            "tuple",
            "set",
            "function",
            "class/object",
            "exceptions",
            "module/package",
            "async/await",
            "typing",
            "JSON",
            "HTTP/API",
            "Pydantic",
            "FastAPI",
            "Tool Calling",
            "Memory",
            "RAG",
            "Workflow/DAG",
            "AgentScope 2.0",
        ],
        current_goals=["尽快形成真正具有实习竞争力的 AI Agent 项目和技术能力"],
        short_term_plan=["围绕 AgentScope 2.0 项目反向补齐 Python 与 Agent 工程能力"],
        long_term_plan=["具备 AI Agent / LLM Application 实习竞争力"],
    )


def _creator(index: int, role: str, *, marketing: float = 0.05) -> Creator:
    return Creator(
        creator_id=f"creator_{index}",
        platform=Platform.XIAOHONGSHU,
        platform_creator_id=f"mock_{index}",
        nickname=f"Mock {role} {index}",
        claimed_role=role,
        topics=["AI Agent", "实习", "求职"],
        engagement=2500 + index * 450,
        career_relevance=0.88,
        signal_density=0.80 + index * 0.01,
        first_hand_experience_score=0.84,
        credibility_score=0.82,
        marketing_ratio=marketing,
        useful_note_ratio=0.79,
    )


def _sample(
    index: int,
    creator: Creator,
    claim: str,
    normalized: str,
    topic: str,
    days_ago: int,
    *,
    required_skill: str | None = None,
    opposes: str | None = None,
    historical_mentions: int = 0,
    timestamped: bool = False,
) -> ResearchSample:
    now = datetime(2026, 9, 5, tzinfo=UTC)
    evidence = Evidence(
        evidence_id=f"evidence_{index}",
        platform=Platform.XIAOHONGSHU,
        creator_id=creator.creator_id,
        content_id=f"note_{index}",
        content_url=f"https://www.xiaohongshu.com/mock/{index}",
        content_title=f"Mock note {index}",
        original_text=claim,
        transcript_segment_id=f"segment_{index}" if timestamped else None,
        transcript_start=12.0 if timestamped else None,
        transcript_end=27.0 if timestamped else None,
        collected_at=now,
    )
    return ResearchSample(
        creator=creator,
        evidence=evidence,
        claim_text=claim,
        normalized_claim=normalized,
        topic=topic,
        published_at=now - timedelta(days=days_ago),
        source_quality=0.85,
        required_skill=required_skill,
        opposes=opposes,
        historical_mentions=historical_mentions,
    )


def mock_samples() -> list[ResearchSample]:
    creators = [
        _creator(1, "大厂 HR"),
        _creator(2, "AI 工程师"),
        _creator(3, "校招博主"),
        _creator(4, "算法工程师"),
        _creator(5, "Agent 开发者"),
        _creator(6, "招聘经理", marketing=0.35),
    ]
    evaluation = "Agent 项目应提供 evaluation 数据，证明工具成功率、成本与任务完成率。"
    engineering = "Agent 实习更看重可运行的工程闭环，而不是只展示 API 调用。"
    algorithm = "算法与模型基础仍是部分 Agent 岗位筛选的首要门槛。"
    return [
        _sample(1, creators[0], evaluation, "agent_evaluation_required", "项目质量", 4, required_skill="Agent Evaluation", timestamped=True),
        _sample(2, creators[1], evaluation, "agent_evaluation_required", "项目质量", 9, required_skill="Agent Evaluation"),
        _sample(3, creators[4], evaluation, "agent_evaluation_required", "项目质量", 18, required_skill="Agent Evaluation", timestamped=True),
        _sample(4, creators[1], engineering, "engineering_loop_priority", "能力侧重", 7, required_skill="工程闭环", opposes="algorithm_first"),
        _sample(5, creators[2], engineering, "engineering_loop_priority", "能力侧重", 21, required_skill="工程闭环", opposes="algorithm_first"),
        _sample(6, creators[3], algorithm, "algorithm_first", "能力侧重", 13, required_skill="算法基础", opposes="engineering_loop_priority", historical_mentions=4),
        _sample(7, creators[5], "证书数量是 Agent 实习筛选的决定性指标。", "certificate_first", "简历筛选", 5),
    ]

