"""Persistent long-term memory backed by SQLite."""

import json
from datetime import datetime, timezone

from app.memory.models import MemoryCreate, MemoryRecord
from app.storage.database import SQLiteDatabase


class LongTermMemoryStore:
    """Persist and retrieve long-term memories."""

    def __init__(self, database: SQLiteDatabase) -> None:
        self.database = database

    def add_memory(
        self,
        data: MemoryCreate,
        embedding: list[float] | None = None,
    ) -> MemoryRecord:
        """Persist one memory and optionally its embedding vector."""
        now = datetime.now(timezone.utc).isoformat()

        metadata_json = json.dumps(
            data.metadata,
            ensure_ascii=False,
            sort_keys=True,
        )

        embedding_json = None
        if embedding is not None:
            embedding_json = json.dumps(embedding)

        with self.database.connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO memory_records (
                    public_id,
                    conversation_id,
                    content,
                    memory_type,
                    metadata_json,
                    embedding_json,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    None,
                    data.conversation_id,
                    data.content,
                    data.memory_type.value,
                    metadata_json,
                    embedding_json,
                    now,
                ),
            )

            row_id = int(cursor.lastrowid)
            public_id = f"MEM-{row_id:05d}"

            connection.execute(
                """
                UPDATE memory_records
                SET public_id = ?
                WHERE id = ?
                """,
                (public_id, row_id),
            )

        memory = self.get_memory(public_id)
        if memory is None:
            raise RuntimeError("Memory was created but could not be reloaded")

        return memory

    def get_memory(self, public_id: str) -> MemoryRecord | None:
        """Return a memory by public identifier."""
        with self.database.connect() as connection:
            row = connection.execute(
                """
                SELECT *
                FROM memory_records
                WHERE public_id = ?
                """,
                (public_id,),
            ).fetchone()

        if row is None:
            return None

        return self._to_model(row)

    def list_memories(
        self,
        conversation_id: str | None = None,
    ) -> list[MemoryRecord]:
        """List memories, optionally restricted to one conversation."""
        with self.database.connect() as connection:
            if conversation_id is None:
                rows = connection.execute(
                    """
                    SELECT *
                    FROM memory_records
                    ORDER BY id ASC
                    """
                ).fetchall()
            else:
                rows = connection.execute(
                    """
                    SELECT *
                    FROM memory_records
                    WHERE conversation_id = ?
                    ORDER BY id ASC
                    """,
                    (conversation_id,),
                ).fetchall()

        return [self._to_model(row) for row in rows]

    @staticmethod
    def _to_model(row) -> MemoryRecord:
        """Deserialize one SQLite row into the domain model."""
        raw = dict(row)

        metadata = json.loads(raw.pop("metadata_json"))

        embedding_json = raw.pop("embedding_json")
        embedding = (
            json.loads(embedding_json)
            if embedding_json is not None
            else None
        )

        return MemoryRecord(
            **raw,
            metadata=metadata,
            embedding=embedding,
        )
