from __future__ import annotations

import unittest
from datetime import UTC, datetime, timedelta
from typing import Any

from hermes_career_intelligence.cache import (
    ArtifactLedger,
    BudgetExceeded,
    BudgetedMCPClient,
    ResearchBudget,
    SQLiteResponseCache,
    build_budgeted_xhs_provider,
    bytes_fingerprint,
    content_fingerprint,
    media_fingerprint,
    request_fingerprint,
)
from hermes_career_intelligence.models import ContentType, Platform, ResearchRun
from hermes_career_intelligence.providers.base import NormalizedContent


class FakeMCPClient:
    def __init__(self, responses: list[dict[str, Any]] | None = None) -> None:
        self.responses = responses or [{"ok": True, "data": {"value": 1}, "cache_url": "https://fictional.invalid/cache/1"}]
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def call(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        self.calls.append((tool_name, arguments))
        return self.responses[min(len(self.calls) - 1, len(self.responses) - 1)]


class CacheTests(unittest.TestCase):
    def test_identical_calls_use_cache_and_increment_hits(self) -> None:
        delegate = FakeMCPClient()
        budget = ResearchBudget(max_provider_calls=3)
        with SQLiteResponseCache() as cache:
            client = BudgetedMCPClient(delegate, cache, budget)
            first = client.call("search", {"q": "agent"})
            second = client.call("search", {"q": "agent"})
        self.assertEqual(first, second)
        self.assertEqual(len(delegate.calls), 1)
        self.assertEqual(budget.total_provider_calls, 1)
        self.assertEqual(budget.cache_hits, 1)

    def test_request_fingerprint_is_canonical_and_namespaced(self) -> None:
        base = request_fingerprint("search", {"q": "agent", "page": 1})
        self.assertEqual(base, request_fingerprint("search", {"page": 1, "q": "agent"}))
        self.assertNotEqual(base, request_fingerprint("other", {"q": "agent", "page": 1}))
        self.assertNotEqual(base, request_fingerprint("search", {"q": "career", "page": 1}))
        self.assertNotEqual(base, request_fingerprint("search", {"q": "agent", "page": 1}, provider="other"))
        self.assertNotEqual(base, request_fingerprint("search", {"q": "agent", "page": 1}, schema_version="v2"))

    def test_expired_response_calls_delegate_again_with_injected_clock(self) -> None:
        now = [datetime(2026, 1, 1, tzinfo=UTC)]
        delegate = FakeMCPClient()
        with SQLiteResponseCache() as cache:
            client = BudgetedMCPClient(delegate, cache, ResearchBudget(3), ttl=timedelta(seconds=10), clock=lambda: now[0])
            client.call("search", {"q": "agent"})
            now[0] += timedelta(seconds=11)
            client.call("search", {"q": "agent"})
        self.assertEqual(len(delegate.calls), 2)

    def test_error_response_is_not_cached(self) -> None:
        delegate = FakeMCPClient([{"ok": False, "error": {"code": "TEMP"}}, {"ok": True, "data": {"value": 2}}])
        with SQLiteResponseCache() as cache:
            client = BudgetedMCPClient(delegate, cache, ResearchBudget(3))
            client.call("search", {"q": "agent"})
            client.call("search", {"q": "agent"})
        self.assertEqual(len(delegate.calls), 2)

    def test_empty_data_response_is_not_cached(self) -> None:
        delegate = FakeMCPClient([{"ok": True, "data": []}, {"ok": True, "data": {"value": 2}}])
        with SQLiteResponseCache() as cache:
            client = BudgetedMCPClient(delegate, cache, ResearchBudget(3))
            client.call("search", {"q": "agent"})
            client.call("search", {"q": "agent"})
        self.assertEqual(len(delegate.calls), 2)

    def test_budget_exceeded_before_extra_delegate_call(self) -> None:
        delegate = FakeMCPClient()
        budget = ResearchBudget(max_provider_calls=1)
        with SQLiteResponseCache() as cache:
            client = BudgetedMCPClient(delegate, cache, budget)
            client.call("first", {})
            with self.assertRaises(BudgetExceeded):
                client.call("second", {})
        self.assertEqual([call[0] for call in delegate.calls], ["first"])

    def test_budget_apply_to_copies_counts_and_cost(self) -> None:
        budget = ResearchBudget(max_provider_calls=4, unit_costs={"search": 1.5})
        budget.record_provider_call("search")
        budget.record_cache_hit()
        run = ResearchRun(question="q", queries=["q"])
        applied = budget.apply_to(run)
        self.assertEqual(applied.provider_calls, {"search": 1})
        self.assertEqual(applied.cache_hits, 1)
        self.assertEqual(applied.estimated_cost_units, 1.5)
        self.assertEqual(run.provider_calls, {})

    def test_bound_budget_updates_live_research_run(self) -> None:
        run = ResearchRun(question="q", queries=["agent"])
        budget = ResearchBudget(max_provider_calls=3, unit_costs={"search": 1.5}, run=run)
        delegate = FakeMCPClient()
        with SQLiteResponseCache() as cache:
            client = BudgetedMCPClient(delegate, cache, budget)
            client.call("search", {"q": "agent"})
            client.call("search", {"q": "agent"})
        self.assertEqual(run.provider_calls, {"search": 1})
        self.assertEqual(run.cache_hits, 1)
        self.assertEqual(run.estimated_cost_units, 1.5)

    def test_budgeted_xhs_provider_is_the_production_wiring_path(self) -> None:
        run = ResearchRun(question="q", queries=["AI Agent"])
        delegate = FakeMCPClient(
            [
                {
                    "ok": True,
                    "data": {
                        "items": [
                            {
                                "note_card": {
                                    "note_id": "note-1",
                                    "type": "normal",
                                    "display_title": "Agent internship",
                                    "desc": "evidence",
                                }
                            }
                        ]
                    },
                }
            ]
        )
        with SQLiteResponseCache() as cache:
            provider, _ = build_budgeted_xhs_provider(delegate, run, cache, max_provider_calls=2)
            first = provider.search_notes("AI Agent")
            second = provider.search_notes("AI Agent")
        self.assertEqual(first.items[0].platform_content_id, "note-1")
        self.assertEqual(second.items[0].platform_content_id, "note-1")
        self.assertEqual(run.provider_calls, {"xhs_search_notes": 1})
        self.assertEqual(run.cache_hits, 1)

    def test_content_media_and_bytes_fingerprints_are_deterministic_and_sensitive(self) -> None:
        content = NormalizedContent(
            platform=Platform.XIAOHONGSHU,
            platform_content_id="note-1",
            title="Title",
            text="Body",
            content_type=ContentType.NOTE,
            url="https://fictional.invalid/note-1",
        )
        same_content = content.model_copy(update={"published_at": datetime(2030, 1, 1, tzinfo=UTC), "like_count": 99, "media_urls": ["https://fictional.invalid/expired"]})
        changed_content = content.model_copy(update={"text": "Changed"})
        self.assertEqual(content_fingerprint(content), content_fingerprint(same_content))
        self.assertNotEqual(content_fingerprint(content), content_fingerprint(changed_content))
        self.assertEqual(media_fingerprint("https://fictional.invalid/a", etag="e1", content_length=4), media_fingerprint("https://fictional.invalid/a", etag="e1", content_length=4))
        self.assertNotEqual(media_fingerprint("https://fictional.invalid/a", etag="e1"), media_fingerprint("https://fictional.invalid/a", etag="e2"))
        self.assertEqual(bytes_fingerprint(b"abc"), bytes_fingerprint(b"abc"))
        self.assertNotEqual(bytes_fingerprint(b"abc"), bytes_fingerprint(b"abd"))

    def test_artifact_ledger_reserves_once_and_tracks_completion(self) -> None:
        with ArtifactLedger() as ledger:
            self.assertTrue(ledger.reserve("transcript", "hash-1"))
            self.assertFalse(ledger.reserve("transcript", "hash-1"))
            self.assertEqual(ledger.status("transcript", "hash-1"), "pending")
            ledger.complete("transcript", "hash-1")
            self.assertEqual(ledger.status("transcript", "hash-1"), "completed")
            with self.assertRaises(KeyError):
                ledger.complete("transcript", "never-reserved")


if __name__ == "__main__":
    unittest.main()
