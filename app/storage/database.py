"""SQLite database management for KnowledgeFlow Agent."""

import sqlite3
from pathlib import Path


class SQLiteDatabase:
    """Minimal SQLite database wrapper for operational and memory persistence."""

    def __init__(self, path: str | Path = "data/knowledgeflow-agent.db") -> None:
        self.path = Path(path)

    def connect(self) -> sqlite3.Connection:
        """Open a configured SQLite connection."""
        self.path.parent.mkdir(parents=True, exist_ok=True)

        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")

        return connection

    def initialize(self) -> None:
        """Create the application schema if it does not already exist."""
        with self.connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS incidents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    public_id TEXT UNIQUE,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    category TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_incidents_public_id
                    ON incidents(public_id);

                CREATE INDEX IF NOT EXISTS idx_incidents_status
                    ON incidents(status);

                CREATE INDEX IF NOT EXISTS idx_incidents_category
                    ON incidents(category);

                CREATE TABLE IF NOT EXISTS incident_notes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    incident_id INTEGER NOT NULL,
                    note TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (incident_id)
                        REFERENCES incidents(id)
                        ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_incident_notes_incident_id
                    ON incident_notes(incident_id);

                CREATE TABLE IF NOT EXISTS memory_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    public_id TEXT UNIQUE,
                    conversation_id TEXT NOT NULL,
                    content TEXT NOT NULL,
                    memory_type TEXT NOT NULL,
                    metadata_json TEXT NOT NULL,
                    embedding_json TEXT,
                    created_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_memory_conversation
                    ON memory_records(conversation_id);

                CREATE INDEX IF NOT EXISTS idx_memory_type
                    ON memory_records(memory_type);
                """
            )
