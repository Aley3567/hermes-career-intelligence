from __future__ import annotations

import unittest
from datetime import UTC, datetime

from hermes_career_intelligence.mock_data import initial_profile, mock_samples
from hermes_career_intelligence.research import CareerResearchEngine, creator_score


class ResearchEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.samples = mock_samples()
        self.pack = CareerResearchEngine(datetime(2026, 9, 5, tzinfo=UTC)).run(
            "AI Agent 实习生核心竞争力是什么？",
            initial_profile(),
            self.samples,
        )

    def test_acceptance_pack_contains_required_analysis(self) -> None:
        self.assertTrue(self.pack.consensus)
        self.assertTrue(self.pack.disagreements)
        self.assertTrue(self.pack.emerging_signals)
        self.assertTrue(self.pack.user_skill_gaps)
        self.assertTrue(self.pack.recommended_actions)

    def test_every_important_claim_has_traceable_evidence(self) -> None:
        evidence_ids = {item.evidence_id for item in self.pack.evidence_index}
        for claim in self.pack.important_claims:
            self.assertTrue(claim.supporting_evidence_ids)
            self.assertTrue(set(claim.supporting_evidence_ids) <= evidence_ids)

    def test_marketing_penalty_affects_creator_rank(self) -> None:
        normal = self.samples[0].creator
        marketing = self.samples[-1].creator
        self.assertGreater(creator_score(normal), creator_score(marketing))

    def test_evaluation_is_detected_as_emerging_gap(self) -> None:
        signals = {item.signal for item in self.pack.emerging_signals}
        gaps = {item.skill for item in self.pack.user_skill_gaps}
        self.assertTrue(any("evaluation" in item.casefold() for item in signals))
        self.assertIn("Agent Evaluation", gaps)


if __name__ == "__main__":
    unittest.main()

