"""Research caching, call budgeting, and artifact de-duplication."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from collections import Counter
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from .models import ResearchRun
from .providers.base import MCPToolClient, NormalizedContent


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def request_fingerprint(
    tool_name: str,
    arguments: dict[str, Any],
    *,
    provider: str = "tikhub_xhs",
    schema_version: str = "v1",
) -> str:
    payload = {
        "provider": provider,
        "schema_version": schema_version,
        "operation": tool_name,
        "arguments": arguments,
    }
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def content_fingerprint(content: NormalizedContent) -> str:
    # Deliberately exclude mutable engagement counts and expiring media URLs.
    payload = {
        "platform": content.platform.value,
        "platform_content_id": content.platform_content_id,
        "creator_id": content.creator_id,
        "title": content.title,
        "text": content.text,
        "content_type": content.content_type.value,
    }
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def media_fingerprint(locator: str, *, etag: str | None = None, content_length: int | None = None) -> str:
    payload = {"locator": locator, "etag": etag, "content_length": content_length}
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def bytes_fingerprint(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


class BudgetExceeded(RuntimeError):
    pass


class ResearchBudget:
    def __init__(
        self,
        max_provider_calls: int = 10,
        unit_costs: dict[str, float] | None = None,
        *,
        run: ResearchRun | None = None,
    ) -> None:
        if max_provider_calls < 1:
            raise ValueError("max_provider_calls must be at least 1")
        self.max_provider_calls = max_provider_calls
        self.unit_costs = unit_costs or {}
        self.provider_calls: Counter[str] = Counter()
        self.cache_hits = 0
        self.estimated_cost_units = 0.0
        self.run = run
        self._sync_run()

    @property
    def total_provider_calls(self) -> int:
        return sum(self.provider_calls.values())

    def _sync_run(self) -> None:
        if self.run is None:
            return
        self.run.provider_calls = dict(self.provider_calls)
        self.run.cache_hits = self.cache_hits
        self.run.estimated_cost_units = round(self.estimated_cost_units, 4)

    def record_provider_call(self, tool_name: str) -> None:
        if self.total_provider_calls >= self.max_provider_calls:
            raise BudgetExceeded(f"provider call budget exhausted before {tool_name}")
        self.provider_calls[tool_name] += 1
        self.estimated_cost_units += self.unit_costs.get(tool_name, 1.0)
        self._sync_run()

    def record_cache_hit(self) -> None:
        self.cache_hits += 1
        self._sync_run()

    def apply_to(self, run: ResearchRun) -> ResearchRun:
        return run.model_copy(
            update={
                "provider_calls": dict(self.provider_calls),
                "cache_hits": self.cache_hits,
                "estimated_cost_units": round(self.estimated_cost_units, 4),
            }
        )


class SQLiteResponseCache:
    def __init__(self, path: str | Path = ":memory:") -> None:
        self.path = str(path)
        self._connection = sqlite3.connect(self.path)
        self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS response_cache (
                cache_key TEXT PRIMARY KEY,
                payload_json TEXT NOT NULL,
                provider_cache_url TEXT,
                expires_at TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        self._connection.commit()

    def get(self, cache_key: str, *, now: datetime | None = None) -> dict[str, Any] | None:
        instant = now or _utc_now()
        row = self._connection.execute(
            "SELECT payload_json, expires_at FROM response_cache WHERE cache_key = ?",
            (cache_key,),
        ).fetchone()
        if row is None:
            return None
        expires_at = datetime.fromisoformat(row[1])
        if expires_at <= instant:
            with self._connection:
                self._connection.execute("DELETE FROM response_cache WHERE cache_key = ?", (cache_key,))
            return None
        return json.loads(row[0])

    def put(
        self,
        cache_key: str,
        payload: dict[str, Any],
        *,
        ttl: timedelta,
        provider_cache_url: str | None = None,
        now: datetime | None = None,
    ) -> None:
        instant = now or _utc_now()
        with self._connection:
            self._connection.execute(
                """
                INSERT INTO response_cache(cache_key, payload_json, provider_cache_url, expires_at, created_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(cache_key) DO UPDATE SET
                    payload_json = excluded.payload_json,
                    provider_cache_url = excluded.provider_cache_url,
                    expires_at = excluded.expires_at,
                    created_at = excluded.created_at
                """,
                (
                    cache_key,
                    _canonical_json(payload),
                    provider_cache_url,
                    (instant + ttl).isoformat(),
                    instant.isoformat(),
                ),
            )

    def close(self) -> None:
        self._connection.close()

    def __enter__(self) -> "SQLiteResponseCache":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()


class BudgetedMCPClient:
    """Decorate any MCP client with deterministic response reuse and a hard cap."""

    def __init__(
        self,
        client: MCPToolClient,
        cache: SQLiteResponseCache,
        budget: ResearchBudget,
        *,
        ttl: timedelta = timedelta(hours=24),
        clock: Callable[[], datetime] = _utc_now,
        provider_name: str = "tikhub_xhs",
        schema_version: str = "v1",
    ) -> None:
        self.client = client
        self.cache = cache
        self.budget = budget
        self.ttl = ttl
        self.clock = clock
        self.provider_name = provider_name
        self.schema_version = schema_version

    def call(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        cache_key = request_fingerprint(
            tool_name,
            arguments,
            provider=self.provider_name,
            schema_version=self.schema_version,
        )
        now = self.clock()
        cached = self.cache.get(cache_key, now=now)
        if cached is not None:
            self.budget.record_cache_hit()
            return cached

        self.budget.record_provider_call(tool_name)
        response = self.client.call(tool_name, arguments)
        if self._cacheable(response):
            cache_url = response.get("cache_url")
            self.cache.put(
                cache_key,
                response,
                ttl=self.ttl,
                provider_cache_url=str(cache_url) if cache_url else None,
                now=now,
            )
        return response

    @staticmethod
    def _cacheable(response: dict[str, Any]) -> bool:
        if not isinstance(response, dict) or response.get("ok") is False or response.get("error"):
            return False
        code = response.get("code")
        if code not in (None, 200):
            return False
        data = response.get("data")
        if data is None:
            return False
        if isinstance(data, (dict, list, tuple, set, str, bytes)) and not data:
            return False
        return True


def build_budgeted_xhs_provider(
    client: MCPToolClient,
    run: ResearchRun,
    cache: SQLiteResponseCache,
    *,
    max_provider_calls: int = 10,
    unit_costs: dict[str, float] | None = None,
    ttl: timedelta = timedelta(hours=24),
    schema_version: str = "v1",
):
    """Production construction path for an XHS provider with cache/budget accounting.

    The returned budget is bound to ``run`` so provider calls, cache hits, and
    estimated cost units are reflected on the live ResearchRun automatically.
    """
    from .providers.tikhub_xhs import TikHubXHSProvider

    budget = ResearchBudget(max_provider_calls=max_provider_calls, unit_costs=unit_costs, run=run)
    budgeted_client = BudgetedMCPClient(
        client,
        cache,
        budget,
        ttl=ttl,
        provider_name="tikhub_xhs",
        schema_version=schema_version,
    )
    return TikHubXHSProvider(budgeted_client), budget


class ArtifactLedger:
    """Reserve expensive derived artifacts exactly once per stable input hash."""

    def __init__(self, path: str | Path = ":memory:") -> None:
        self._connection = sqlite3.connect(str(path))
        self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS artifact_ledger (
                artifact_kind TEXT NOT NULL,
                input_fingerprint TEXT NOT NULL,
                status TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (artifact_kind, input_fingerprint)
            )
            """
        )
        self._connection.commit()

    def reserve(self, artifact_kind: str, input_fingerprint: str, *, now: datetime | None = None) -> bool:
        instant = now or _utc_now()
        with self._connection:
            cursor = self._connection.execute(
                """
                INSERT OR IGNORE INTO artifact_ledger(artifact_kind, input_fingerprint, status, updated_at)
                VALUES (?, ?, 'pending', ?)
                """,
                (artifact_kind, input_fingerprint, instant.isoformat()),
            )
        return cursor.rowcount == 1

    def complete(self, artifact_kind: str, input_fingerprint: str, *, now: datetime | None = None) -> None:
        instant = now or _utc_now()
        with self._connection:
            cursor = self._connection.execute(
                """
                UPDATE artifact_ledger SET status = 'completed', updated_at = ?
                WHERE artifact_kind = ? AND input_fingerprint = ?
                """,
                (instant.isoformat(), artifact_kind, input_fingerprint),
            )
        if cursor.rowcount != 1:
            raise KeyError(f"artifact was not reserved: {artifact_kind}/{input_fingerprint}")

    def status(self, artifact_kind: str, input_fingerprint: str) -> str | None:
        row = self._connection.execute(
            "SELECT status FROM artifact_ledger WHERE artifact_kind = ? AND input_fingerprint = ?",
            (artifact_kind, input_fingerprint),
        ).fetchone()
        return None if row is None else str(row[0])

    def close(self) -> None:
        self._connection.close()

    def __enter__(self) -> "ArtifactLedger":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
