"""Persistence repositories for KnowledgeFlow Agent."""

from datetime import datetime, timezone

from app.storage.database import SQLiteDatabase
from app.storage.models import (
    Incident,
    IncidentCreate,
    IncidentNote,
    IncidentNoteCreate,
    IncidentStatus,
)


class IncidentRepository:
    """Repository for incident and incident-note persistence."""

    def __init__(self, database: SQLiteDatabase) -> None:
        self.database = database

    def create_incident(self, data: IncidentCreate) -> Incident:
        """Persist a new incident and generate its public INC identifier."""
        now = datetime.now(timezone.utc).isoformat()

        with self.database.connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO incidents (
                    public_id,
                    title,
                    description,
                    category,
                    severity,
                    status,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    None,
                    data.title,
                    data.description,
                    data.category.value,
                    data.severity.value,
                    data.status.value,
                    now,
                    now,
                ),
            )

            row_id = int(cursor.lastrowid)
            public_id = f"INC-{row_id:05d}"

            connection.execute(
                """
                UPDATE incidents
                SET public_id = ?
                WHERE id = ?
                """,
                (public_id, row_id),
            )

        incident = self.get_incident(public_id)
        if incident is None:
            raise RuntimeError("Incident was created but could not be reloaded")

        return incident

    def get_incident(self, public_id: str) -> Incident | None:
        """Return one incident by its public identifier."""
        with self.database.connect() as connection:
            row = connection.execute(
                """
                SELECT *
                FROM incidents
                WHERE public_id = ?
                """,
                (public_id,),
            ).fetchone()

        if row is None:
            return None

        return Incident(**dict(row))

    def search_incidents(
        self,
        query: str | None = None,
        status: IncidentStatus | None = None,
        limit: int = 20,
    ) -> list[Incident]:
        """Search incidents using text and optional status filters."""
        if limit < 1 or limit > 100:
            raise ValueError("limit must be between 1 and 100")

        conditions: list[str] = []
        parameters: list[object] = []

        if query and query.strip():
            like_query = f"%{query.strip()}%"
            conditions.append(
                "(title LIKE ? OR description LIKE ? OR public_id LIKE ?)"
            )
            parameters.extend([like_query, like_query, like_query])

        if status is not None:
            conditions.append("status = ?")
            parameters.append(status.value)

        where_clause = ""
        if conditions:
            where_clause = "WHERE " + " AND ".join(conditions)

        parameters.append(limit)

        sql = f"""
            SELECT *
            FROM incidents
            {where_clause}
            ORDER BY id DESC
            LIMIT ?
        """

        with self.database.connect() as connection:
            rows = connection.execute(sql, parameters).fetchall()

        return [Incident(**dict(row)) for row in rows]

    def append_note(
        self,
        incident_public_id: str,
        data: IncidentNoteCreate,
    ) -> IncidentNote:
        """Attach a follow-up note to an existing incident."""
        incident = self.get_incident(incident_public_id)
        if incident is None:
            raise ValueError(f"Incident not found: {incident_public_id}")

        now = datetime.now(timezone.utc).isoformat()

        with self.database.connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO incident_notes (
                    incident_id,
                    note,
                    created_at
                )
                VALUES (?, ?, ?)
                """,
                (
                    incident.id,
                    data.note,
                    now,
                ),
            )
            note_id = int(cursor.lastrowid)

            row = connection.execute(
                """
                SELECT
                    n.id,
                    i.public_id AS incident_public_id,
                    n.note,
                    n.created_at
                FROM incident_notes AS n
                JOIN incidents AS i
                    ON i.id = n.incident_id
                WHERE n.id = ?
                """,
                (note_id,),
            ).fetchone()

        if row is None:
            raise RuntimeError("Incident note was created but could not be reloaded")

        return IncidentNote(**dict(row))

    def list_notes(self, incident_public_id: str) -> list[IncidentNote]:
        """Return follow-up notes for one incident in chronological order."""
        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    n.id,
                    i.public_id AS incident_public_id,
                    n.note,
                    n.created_at
                FROM incident_notes AS n
                JOIN incidents AS i
                    ON i.id = n.incident_id
                WHERE i.public_id = ?
                ORDER BY n.id ASC
                """,
                (incident_public_id,),
            ).fetchall()

        return [IncidentNote(**dict(row)) for row in rows]
