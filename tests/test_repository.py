from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from hermes_career_intelligence.mock_data import initial_profile, mock_samples
from hermes_career_intelligence.models import Claim
from hermes_career_intelligence.repository import SQLiteKnowledgeRepository


class RepositoryTests(unittest.TestCase):
    def test_profile_and_claim_evidence_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "knowledge.sqlite3"
            with SQLiteKnowledgeRepository(path) as repository:
                profile = initial_profile()
                repository.save_profile(profile)
                self.assertEqual(repository.get_profile(), profile)

                evidence = mock_samples()[0].evidence
                claim = Claim(
                    claim_id="claim_test",
                    claim_text="Evaluation matters",
                    normalized_claim="evaluation_matters",
                    topic="project quality",
                    supporting_evidence_ids=[evidence.evidence_id],
                )
                repository.save_claim(claim)
                repository.link_evidence(claim.claim_id, evidence)
                loaded = repository.get_claim_evidence(claim.claim_id)
                self.assertEqual([item.evidence_id for item in loaded], [evidence.evidence_id])


if __name__ == "__main__":
    unittest.main()

