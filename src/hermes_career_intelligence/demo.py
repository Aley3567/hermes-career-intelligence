"""Offline acceptance demo."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
from pathlib import Path

from .mock_data import initial_profile, mock_samples
from .models import ResearchResult
from .repository import SQLiteKnowledgeRepository
from .research import CareerResearchEngine


QUESTION = "研究最近小红书上大厂 HR、AI 从业者和求职博主怎么看 AI Agent 实习生的核心竞争力，并结合我的情况告诉我未来 30 天最应该补什么。"


def run_demo(database: str | Path = ":memory:") -> ResearchResult:
    profile = initial_profile()
    engine = CareerResearchEngine(now=datetime(2026, 9, 5, tzinfo=UTC))
    pack = engine.run(QUESTION, profile, mock_samples())
    result = ResearchResult(run_id="mock_acceptance_run", pack=pack)

    with SQLiteKnowledgeRepository(database) as repository:
        repository.save_profile(profile)
        for claim in pack.important_claims:
            repository.save_claim(claim)
            for evidence in pack.evidence_index:
                if evidence.evidence_id in claim.supporting_evidence_ids:
                    repository.link_evidence(claim.claim_id, evidence)
        repository.save_research_result(result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the offline career intelligence acceptance demo")
    parser.add_argument("--database", default=":memory:")
    parser.add_argument("--output", choices=("json", "summary"), default="summary")
    args = parser.parse_args()
    result = run_demo(args.database)
    if args.output == "json":
        print(result.pack.model_dump_json(indent=2))
        return
    print(result.pack.executive_summary)
    print("Top claims:")
    for claim in result.pack.important_claims[:3]:
        print(f"- [{claim.confidence:.3f}] {claim.claim_text}")
    print("30-day priorities:")
    for action in result.pack.recommended_actions:
        print(f"- {action.title}: {action.success_metric}")


if __name__ == "__main__":
    main()
