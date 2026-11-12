"""Windowed short-term conversational memory."""

from collections import defaultdict, deque

from app.memory.models import MemoryRole, ShortTermMessage


class ShortTermMemory:
    """Keep only the most recent conversational messages.

    max_turns represents user/assistant interaction pairs, therefore the
    underlying window stores up to max_turns * 2 messages.
    """

    def __init__(self, max_turns: int = 10) -> None:
        if max_turns < 1:
            raise ValueError("max_turns must be at least 1")

        self.max_turns = max_turns
        self.max_messages = max_turns * 2

        self._messages: dict[str, deque[ShortTermMessage]] = defaultdict(
            lambda: deque(maxlen=self.max_messages)
        )

    def add_message(
        self,
        conversation_id: str,
        role: MemoryRole | str,
        content: str,
    ) -> ShortTermMessage:
        """Append one validated message to a conversation window."""
        conversation_id = conversation_id.strip()
        if not conversation_id:
            raise ValueError("conversation_id cannot be empty")

        message = ShortTermMessage(
            role=role,
            content=content,
        )

        self._messages[conversation_id].append(message)
        return message

    def get_messages(self, conversation_id: str) -> list[ShortTermMessage]:
        """Return the active conversational window in chronological order."""
        return list(self._messages.get(conversation_id, []))

    def clear(self, conversation_id: str) -> None:
        """Remove the active window for one conversation."""
        self._messages.pop(conversation_id, None)
