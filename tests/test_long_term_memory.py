"""Tests for persistent long-term memory."""

from app.memory.long_term import LongTermMemoryStore
from app.memory.models import MemoryCreate
from app.storage.database import SQLiteDatabase


def _store(tmp_path):
    database = SQLiteDatabase(tmp_path / "memory.db")
    database.initialize()
    return LongTermMemoryStore(database)


def test_long_term_memory_persists_record(tmp_path):
    store = _store(tmp_path)

    memory = store.add_memory(
        MemoryCreate(
            conversation_id="conv-1",
            content="El usuario perdió su dispositivo MFA.",
            memory_type="event",
            metadata={"incident": "INC-00001"},
        ),
        embedding=[1.0, 0.0],
    )

    assert memory.public_id == "MEM-00001"
    assert memory.content == "El usuario perdió su dispositivo MFA."
    assert memory.metadata["incident"] == "INC-00001"
    assert memory.embedding == [1.0, 0.0]


def test_long_term_memory_can_reload_record(tmp_path):
    store = _store(tmp_path)

    created = store.add_memory(
        MemoryCreate(
            conversation_id="conv-1",
            content="Se creó el incidente INC-00001.",
            memory_type="tool_result",
        )
    )

    loaded = store.get_memory(created.public_id)

    assert loaded is not None
    assert loaded.public_id == created.public_id
    assert loaded.memory_type.value == "tool_result"


def test_long_term_memory_filters_conversation(tmp_path):
    store = _store(tmp_path)

    store.add_memory(
        MemoryCreate(
            conversation_id="conv-a",
            content="Memoria A",
        )
    )

    store.add_memory(
        MemoryCreate(
            conversation_id="conv-b",
            content="Memoria B",
        )
    )

    results = store.list_memories(
        conversation_id="conv-a"
    )

    assert len(results) == 1
    assert results[0].content == "Memoria A"


def test_long_term_memory_unknown_id_returns_none(tmp_path):
    store = _store(tmp_path)

    assert store.get_memory("MEM-99999") is None
