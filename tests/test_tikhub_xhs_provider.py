from __future__ import annotations

import json
import unittest
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from hermes_career_intelligence.providers.base import ProviderError
from hermes_career_intelligence.providers.tikhub_xhs import TikHubXHSProvider


FIXTURES = Path(__file__).parent / "fixtures" / "tikhub_xhs"


class FakeMCPClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self.fixtures = {
            "xhs_search_notes": "search_notes.json",
            "xhs_get_note_detail": "get_note.json",
            "xhs_get_user_info": "get_creator.json",
            "xhs_search_users": "search_creators.json",
            "xhs_get_user_posted_notes": "creator_notes.json",
            "xhs_get_note_comments": "comments.json",
        }

    def call(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        self.calls.append((tool_name, arguments))
        fixture_name = self.fixtures[tool_name]
        return json.loads((FIXTURES / fixture_name).read_text(encoding="utf-8"))


class TikHubXHSProviderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = FakeMCPClient()
        self.provider = TikHubXHSProvider(self.client)

    def test_search_notes_normalizes_nested_note_card_and_metadata(self) -> None:
        page = self.provider.search_notes("  agent  ", page=2, sort_type="popular")
        item = page.items[0]
        self.assertEqual(self.client.calls, [("xhs_search_notes", {"keyword": "agent", "page": 2, "sort_type": "popular"})])
        self.assertEqual(item.platform_content_id, "note-video-001")
        self.assertEqual(item.content_type.value, "video")
        self.assertEqual(item.like_count, 12_000)
        self.assertEqual(item.collect_count, 2_001)
        self.assertEqual(item.published_at, datetime(2025, 1, 1, tzinfo=UTC))
        self.assertEqual(page.cache_url, "https://fictional.invalid/cache/search-001")
        self.assertEqual(page.provider_request_id, "req-search-001")
        self.assertEqual(page.next_cursor, "cursor-search-002")
        self.assertEqual(page.search_id, "search-001")
        self.assertEqual(page.search_session_id, "session-001")
        self.assertTrue(page.has_more)

    def test_get_note_video_normalizes_millisecond_timestamp(self) -> None:
        note = self.provider.get_note(note_id="note-video-001")
        self.assertEqual(self.client.calls, [("xhs_get_note_detail", {"note_id": "note-video-001", "note_type": "auto"})])
        self.assertEqual(note.content_type.value, "video")
        self.assertEqual(note.like_count, 12_000)
        self.assertEqual(note.collect_count, 34_000)
        self.assertEqual(note.published_at, datetime(2025, 1, 1, 0, 0, 0, 123000, tzinfo=UTC))

    def test_creator_and_search_creators_normalize_counts_and_cursor(self) -> None:
        creator = self.provider.get_creator(user_id="user-001")
        self.assertEqual(self.client.calls[-1], ("xhs_get_user_info", {"user_id": "user-001"}))
        self.assertEqual(creator.platform_creator_id, "user-001")
        self.assertEqual(creator.followers, 12_000)
        self.assertEqual(creator.following, 321)
        self.assertEqual(creator.likes_and_collects, 25_000)

        page = self.provider.search_creators("林舟")
        self.assertEqual(self.client.calls[-1], ("xhs_search_users", {"keyword": "林舟", "page": 1}))
        self.assertEqual(page.items[0].platform_creator_id, "user-002")
        self.assertEqual(page.items[0].followers, 12_000)
        self.assertEqual(page.next_cursor, "cursor-users-002")
        self.assertFalse(page.has_more)

    def test_creator_notes_and_comments_normalize_records_and_metadata(self) -> None:
        notes = self.provider.get_creator_notes(user_id="user-001", cursor="cursor-posts-001")
        self.assertEqual(self.client.calls[-1], ("xhs_get_user_posted_notes", {"user_id": "user-001", "cursor": "cursor-posts-001"}))
        self.assertEqual(notes.items[0].platform_content_id, "note-creator-001")
        self.assertEqual(notes.items[0].published_at, datetime(2025, 1, 1, tzinfo=UTC))
        self.assertEqual(notes.next_cursor, "cursor-posts-002")

        comments = self.provider.get_comments(note_id="note-video-001")
        self.assertEqual(self.client.calls[-1], ("xhs_get_note_comments", {"note_id": "note-video-001"}))
        self.assertEqual(comments.items[0].platform_comment_id, "comment-001")
        self.assertEqual(comments.items[0].content_id, "note-video-001")
        self.assertEqual(comments.items[0].like_count, 12_000)
        self.assertEqual(comments.items[0].published_at, datetime(2025, 1, 1, 0, 0, 0, 123000, tzinfo=UTC))
        self.assertEqual(comments.provider_request_id, "req-comments-001")

    def test_provider_error_is_structured_and_does_not_leak_response_body(self) -> None:
        self.client.fixtures["xhs_search_notes"] = "error.json"
        with self.assertRaises(ProviderError) as raised:
            self.provider.search_notes("agent")
        error = raised.exception
        self.assertEqual(error.code, "HTTP_ERROR")
        self.assertEqual(error.tool, "xhs_search_notes")
        self.assertTrue(error.retryable)
        self.assertNotIn("fictional-secret-token-should-not-leak", str(error))

    def test_billed_but_empty_upstream_data_is_not_treated_as_success(self) -> None:
        self.client.fixtures["xhs_search_notes"] = "empty_data.json"
        with self.assertRaises(ProviderError) as raised:
            self.provider.search_notes("agent")
        self.assertEqual(raised.exception.code, "UPSTREAM_DATA_ERROR")

    def test_blank_queries_and_missing_identities_are_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "keyword"):
            self.provider.search_notes("  ")
        with self.assertRaisesRegex(ValueError, "keyword"):
            self.provider.search_creators("")
        with self.assertRaisesRegex(ValueError, "note_id or share_text"):
            self.provider.get_note()
        with self.assertRaisesRegex(ValueError, "user_id or share_text"):
            self.provider.get_creator()
        with self.assertRaisesRegex(ValueError, "user_id or share_text"):
            self.provider.get_creator_notes()
        with self.assertRaisesRegex(ValueError, "note_id or share_text"):
            self.provider.get_comments()
        self.assertEqual(self.client.calls, [])


if __name__ == "__main__":
    unittest.main()
