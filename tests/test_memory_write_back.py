"""Tests for execution memory write-back and multi-turn continuity."""

from app.agentic.orchestrator import (
    AdaptiveOrchestrator,
    ExecutionStatus,
)
from app.agentic.planner import RuleBasedPlanner
from app.agentic.state import AgentState
from app.memory.long_term import LongTermMemoryStore
from app.memory.semantic import SemanticMemory
from app.memory.short_term import ShortTermMemory
from app.memory.write_back import MemoryWriteBack
from app.rag.embeddings import BaseEmbeddings
from app.storage.database import SQLiteDatabase
from app.storage.repositories import IncidentRepository
from app.tools.incidents import (
    AppendIncidentNoteTool,
    CreateIncidentTool,
    SearchIncidentsTool,
)
from app.tools.schemas import (
    AppendIncidentNoteDraft,
    AppendIncidentNoteInput,
    CreateIncidentInput,
    KnowledgeQueryResult,
    KnowledgeSource,
)


class ConstantEmbeddings(BaseEmbeddings):
    """Small deterministic embedding provider with perfect cross-text similarity."""

    def __init__(self, dimension: int = 4) -> None:
        self.dimension = dimension

    def _vector(self) -> list[float]:
        return [1.0] + [0.0] * (self.dimension - 1)

    def embed_document(self, document, metadata=None):
        return self._vector()

    def embed_documents(self, documents):
        return [self._vector() for _ in documents]

    def embed_query(self, query):
        return self._vector()


class StubKnowledgeTool:
    """Grounded deterministic knowledge tool for orchestration tests."""

    name = "search_knowledge"

    def run(self, arguments):
        return KnowledgeQueryResult(
            query=arguments.query,
            source_scope="internal",
            answer="Procedimiento recuperado [S1].",
            citations=["S1"],
            sources=[
                KnowledgeSource(
                    id="S1",
                    file_name="faq_interna.txt",
                    source_type="internal",
                    chunk_index=1,
                    score=0.92,
                )
            ],
            abstained=False,
        )


def _state(request: str) -> AgentState:
    return AgentState(
        conversation_id="conv-memory",
        user_request=request,
    )


def _incident_input() -> CreateIncidentInput:
    return CreateIncidentInput(
        title="Pérdida de autenticador MFA",
        description="Usuario perdió el dispositivo utilizado para MFA.",
        category="access",
        severity="medium",
    )


def test_write_back_records_short_term_user_and_assistant():
    short_term = ShortTermMemory()
    write_back = MemoryWriteBack(
        short_term_memory=short_term
    )

    write_back.record(
        state=_state("¿Qué recomienda la política?"),
        output="Respuesta grounded [S1].",
        status="completed",
    )

    messages = short_term.get_messages("conv-memory")

    assert [message.role.value for message in messages] == [
        "user",
        "assistant",
    ]
    assert messages[0].content == "¿Qué recomienda la política?"
    assert messages[1].content == "Respuesta grounded [S1]."


def test_write_back_persists_incident_creation_semantically(tmp_path):
    database = SQLiteDatabase(tmp_path / "memory-write-back.db")
    database.initialize()

    store = LongTermMemoryStore(database)
    semantic = SemanticMemory(
        store=store,
        embeddings=ConstantEmbeddings(),
    )
    write_back = MemoryWriteBack(
        semantic_memory=semantic
    )

    state = _state(
        "Registra un incidente por pérdida de MFA."
    )
    state.intent = "incident_create"
    state.incident_id = "INC-00001"
    state.observations.append(
        {
            "tool": "create_incident",
            "status": "completed",
            "incident_id": "INC-00001",
        }
    )

    persisted = write_back.record(
        state=state,
        output="Incidente creado: INC-00001.",
        status="completed",
    )

    assert len(persisted) == 1
    assert persisted[0].metadata["incident_id"] == "INC-00001"
    assert persisted[0].metadata["tool"] == "create_incident"
    assert persisted[0].embedding is not None


def test_write_back_does_not_persist_read_only_tool_results(tmp_path):
    database = SQLiteDatabase(tmp_path / "memory-read-only.db")
    database.initialize()

    store = LongTermMemoryStore(database)
    semantic = SemanticMemory(
        store=store,
        embeddings=ConstantEmbeddings(),
    )
    write_back = MemoryWriteBack(
        semantic_memory=semantic
    )

    state = _state("¿Qué exige la política MFA?")
    state.intent = "knowledge_query"
    state.observations.append(
        {
            "tool": "search_knowledge",
            "status": "completed",
            "citations": ["S1"],
        }
    )

    persisted = write_back.record(
        state=state,
        output="Respuesta grounded [S1].",
        status="completed",
    )

    assert persisted == []
    assert store.list_memories("conv-memory") == []


def test_orchestrator_recovers_incident_from_semantic_memory_next_turn(tmp_path):
    database = SQLiteDatabase(tmp_path / "memory-multiturn.db")
    database.initialize()

    repository = IncidentRepository(database)
    store = LongTermMemoryStore(database)
    semantic = SemanticMemory(
        store=store,
        embeddings=ConstantEmbeddings(),
    )
    write_back = MemoryWriteBack(
        semantic_memory=semantic
    )

    planner = RuleBasedPlanner(
        semantic_memory=semantic
    )

    orchestrator = AdaptiveOrchestrator(
        planner=planner,
        knowledge_tool=StubKnowledgeTool(),
        create_incident_tool=CreateIncidentTool(repository),
        search_incidents_tool=SearchIncidentsTool(repository),
        append_incident_note_tool=AppendIncidentNoteTool(repository),
        memory_write_back=write_back,
    )

    first = orchestrator.execute(
        _state(
            "Perdí mi autenticador. "
            "Revisa el procedimiento y registra un incidente."
        ),
        tool_inputs={
            "create_incident": _incident_input(),
        },
    )

    assert first.status == ExecutionStatus.COMPLETED
    assert first.state.incident_id == "INC-00001"

    memories = store.list_memories("conv-memory")
    assert len(memories) == 1
    assert memories[0].metadata["incident_id"] == "INC-00001"

    second = orchestrator.execute(
        _state(
            "Agrega que la identidad ya fue validada."
        ),
        tool_inputs={
            "append_incident_note": AppendIncidentNoteDraft(
                note="Identidad del usuario validada.",
            )
        },
    )

    assert second.status == ExecutionStatus.COMPLETED
    assert second.state.incident_id == "INC-00001"
    assert second.state.tool_calls == [
        "search_incidents",
        "append_incident_note",
    ]

    notes = repository.list_notes("INC-00001")
    assert len(notes) == 1
    assert notes[0].note == "Identidad del usuario validada."
