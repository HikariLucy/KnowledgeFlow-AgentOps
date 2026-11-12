"""Tests for windowed short-term conversational memory."""

import pytest
from pydantic import ValidationError

from app.memory.short_term import ShortTermMemory


def test_short_term_memory_preserves_order():
    memory = ShortTermMemory(max_turns=2)

    memory.add_message("conv-1", "user", "Hola")
    memory.add_message("conv-1", "assistant", "Hola, ¿en qué ayudo?")

    messages = memory.get_messages("conv-1")

    assert [message.role.value for message in messages] == [
        "user",
        "assistant",
    ]
    assert [message.content for message in messages] == [
        "Hola",
        "Hola, ¿en qué ayudo?",
    ]


def test_short_term_memory_keeps_only_recent_window():
    memory = ShortTermMemory(max_turns=2)

    for index in range(5):
        memory.add_message(
            "conv-1",
            "user",
            f"mensaje-{index}",
        )

    messages = memory.get_messages("conv-1")

    assert len(messages) == 4
    assert messages[0].content == "mensaje-1"
    assert messages[-1].content == "mensaje-4"


def test_short_term_memory_isolates_conversations():
    memory = ShortTermMemory()

    memory.add_message("conv-a", "user", "Mensaje A")
    memory.add_message("conv-b", "user", "Mensaje B")

    assert memory.get_messages("conv-a")[0].content == "Mensaje A"
    assert memory.get_messages("conv-b")[0].content == "Mensaje B"


def test_short_term_memory_rejects_blank_content():
    memory = ShortTermMemory()

    with pytest.raises(ValidationError):
        memory.add_message(
            "conv-1",
            "user",
            "   ",
        )
