"""Small SQLite persistence layer for career knowledge.

The first milestone stores validated model JSON while indexing identity, type,
and claim-evidence relationships. This keeps migrations simple without turning
the database into an opaque transcript dump.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

from .models import (
    Claim,
    Evidence,
    ResearchResult,
    UserObservation,
    UserProfile,
    utc_now,
)

ModelT = TypeVar("ModelT", bound=BaseModel)


class SQLiteKnowledgeRepository:
    def __init__(self, path: str | Path) -> None:
        self.path = str(path)
        self._connection = sqlite3.connect(self.path)
        self._connection.execute("PRAGMA foreign_keys = ON")
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        return self._connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS entities (
                    entity_type TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (entity_type, entity_id)
                );

                CREATE TABLE IF NOT EXISTS claim_evidence (
                    claim_id TEXT NOT NULL,
                    evidence_id TEXT NOT NULL,
                    stance TEXT NOT NULL,
                    PRIMARY KEY (claim_id, evidence_id)
                );

                CREATE INDEX IF NOT EXISTS idx_claim_evidence_claim
                    ON claim_evidence(claim_id);
                CREATE INDEX IF NOT EXISTS idx_entity_type
                    ON entities(entity_type);
                """
            )

    def put(self, entity_type: str, entity_id: str, model: BaseModel) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO entities(entity_type, entity_id, payload_json, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(entity_type, entity_id) DO UPDATE SET
                    payload_json = excluded.payload_json,
                    updated_at = excluded.updated_at
                """,
                (entity_type, entity_id, model.model_dump_json(), utc_now().isoformat()),
            )

    def get(self, entity_type: str, entity_id: str, model_type: type[ModelT]) -> ModelT | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload_json FROM entities WHERE entity_type = ? AND entity_id = ?",
                (entity_type, entity_id),
            ).fetchone()
        return None if row is None else model_type.model_validate_json(row[0])

    def save_profile(self, profile: UserProfile) -> None:
        self.put("user_profile", profile.profile_id, profile)

    def get_profile(self, profile_id: str = "primary") -> UserProfile | None:
        return self.get("user_profile", profile_id, UserProfile)

    def save_observation(self, observation: UserObservation) -> None:
        self.put("user_observation", observation.observation_id, observation)

    def save_claim(self, claim: Claim) -> None:
        self.put("claim", claim.claim_id, claim)

    def save_evidence(self, evidence: Evidence) -> None:
        self.put("evidence", evidence.evidence_id, evidence)

    def link_evidence(self, claim_id: str, evidence: Evidence) -> None:
        self.save_evidence(evidence)
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO claim_evidence(claim_id, evidence_id, stance)
                VALUES (?, ?, ?)
                ON CONFLICT(claim_id, evidence_id) DO UPDATE SET stance = excluded.stance
                """,
                (claim_id, evidence.evidence_id, evidence.stance.value),
            )

    def get_claim_evidence(self, claim_id: str) -> list[Evidence]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT e.payload_json
                FROM entities e
                JOIN claim_evidence ce ON ce.evidence_id = e.entity_id
                WHERE ce.claim_id = ? AND e.entity_type = 'evidence'
                ORDER BY e.updated_at
                """,
                (claim_id,),
            ).fetchall()
        return [Evidence.model_validate_json(row[0]) for row in rows]

    def save_research_result(self, result: ResearchResult) -> None:
        self.put("research_result", result.result_id, result)

    def close(self) -> None:
        self._connection.close()

    def __enter__(self) -> "SQLiteKnowledgeRepository":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
