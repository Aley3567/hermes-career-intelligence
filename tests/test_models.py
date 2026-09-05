from __future__ import annotations

import unittest
from pathlib import Path

from pydantic import ValidationError

from hermes_career_intelligence.models import Evidence, Platform, TranscriptSegment, UserProfile


class ModelInvariantTests(unittest.TestCase):
    def test_transcript_interval_must_be_positive(self) -> None:
        with self.assertRaises(ValidationError):
            TranscriptSegment(start_seconds=10, end_seconds=9, text="invalid")

    def test_evidence_timestamps_must_appear_together(self) -> None:
        with self.assertRaises(ValidationError):
            Evidence(
                platform=Platform.XIAOHONGSHU,
                creator_id="creator",
                content_id="content",
                content_url="https://example.com/note",
                original_text="evidence",
                transcript_start=1,
            )

    def test_unknown_fields_are_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            TranscriptSegment(start_seconds=0, end_seconds=1, text="ok", invented=True)

    def test_initial_user_profile_is_valid(self) -> None:
        profile_path = Path(__file__).resolve().parents[1] / "data" / "user_profile.json"
        profile = UserProfile.model_validate_json(profile_path.read_text(encoding="utf-8"))
        self.assertIn("AgentScope 2.0", profile.learning_topics)
        self.assertNotIn("Agent Evaluation", profile.learning_topics)


if __name__ == "__main__":
    unittest.main()
