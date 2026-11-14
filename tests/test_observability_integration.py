"""Real HTTP/domain/SQLite parity with deterministic provider doubles."""
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.main import app
from app.api.agent_routes import get_agent_service
from app.agentic.service import AgentService
from app.agentic.orchestrator import AdaptiveOrchestrator
from app.agentic.planner import RuleBasedPlanner
from app.storage.database import SQLiteDatabase
from app.storage.repositories import IncidentRepository
from app.tools.incidents import CreateIncidentTool, SearchIncidentsTool, AppendIncidentNoteTool
from app.tools.knowledge import KnowledgeRAGTool
from app.tools.schemas import KnowledgeQueryResult, KnowledgeSource
from tests.test_observability_core import runtime, events


class Pipeline:
    def run(self, **kwargs):
        return KnowledgeQueryResult(query=kwargs['query'], source_scope='internal',
            answer='private response [S1]', citations=['S1'], abstained=False,
            sources=[KnowledgeSource(id='S1', file_name='private.md', source_type='internal',
                                     chunk_index=0, score=0.9)])


def service(tmp_path):
    db = SQLiteDatabase(tmp_path / 'obs.db')
    db.initialize()
    repo = IncidentRepository(db)
    return AgentService(AdaptiveOrchestrator(planner=RuleBasedPlanner(),
        knowledge_tool=KnowledgeRAGTool(Pipeline()),
        create_incident_tool=CreateIncidentTool(repo),
        search_incidents_tool=SearchIncidentsTool(repo),
        append_incident_note_tool=AppendIncidentNoteTool(repo))), repo


@pytest.fixture(autouse=True)
def clean_overrides():
    before = app.dependency_overrides.copy()
    yield
    app.dependency_overrides.clear()
    app.dependency_overrides.update(before)


def test_agent_writes_and_searches_with_complete_trace(monkeypatch, tmp_path):
    t, stream = runtime(monkeypatch)
    agent, repo = service(tmp_path)
    app.dependency_overrides[get_agent_service] = lambda: agent
    client = TestClient(app)
    response = client.post('/api/agent', json={
        'conversation_id': 'alice@example.com', 'message': 'Crear incidente privado',
        'create_incident': {'title': 'secret title', 'description': 'secret description',
                            'category': 'access', 'severity': 'medium'}})
    assert response.status_code == 200
    assert response.json()['status'] == 'completed'
    incident_id = response.json()['incident_id']
    assert repo.get_incident(incident_id).title == 'secret title'
    records = events(stream)
    root = records[-1]
    assert root['component'] == 'http'
    assert root['outcome'] == 'completed'
    assert response.headers['x-trace-id'] == root['trace_id']
    assert {e['component'] for e in records} >= {'http', 'agent', 'orchestrator', 'planner', 'tool'}
    tool_events = [e['operation'] for e in records if e['component'] == 'tool']
    assert tool_events == ['search_knowledge', 'create_incident']
    ids = {e['span_id'] for e in records}
    assert all(e['parent_span_id'] is None or e['parent_span_id'] in ids for e in records)
    assert len({e['trace_id'] for e in records}) == 1
    assert len({e['session_id'] for e in records}) == 1
    assert all(secret not in stream.getvalue() for secret in
               ['alice@example.com', 'secret title', 'secret description', 'private response', 'private.md'])
    previous_session = root['session_id']
    followup = client.post('/api/agent', json={
        'conversation_id': 'alice@example.com', 'message': f'Agregar nota a {incident_id}',
        'append_incident_note': {'incident_id': incident_id, 'note': 'private note'}})
    assert followup.json()['status'] == 'completed'
    assert repo.list_notes(incident_id)[0].note == 'private note'
    root2 = events(stream)[-1]
    assert root2['session_id'] == previous_session
    assert root2['trace_id'] != root['trace_id']
    assert 'private note' not in stream.getvalue()
    assert {'search_incidents', 'append_incident_note'} <= {
        e['operation'] for e in events(stream) if e.get('component') == 'tool'}


def test_enabled_disabled_response_and_effect_parity(monkeypatch, tmp_path):
    t, stream = runtime(monkeypatch)
    agent, repo = service(tmp_path)
    app.dependency_overrides[get_agent_service] = lambda: agent
    client = TestClient(app)
    payload = {'conversation_id': 'private', 'message': 'Buscar incidentes',
               'search_incidents': {'query': 'no match'}}
    t.observer.enabled = False
    off = client.post('/api/agent', json=payload)
    assert stream.getvalue() == ''
    t.observer.enabled = True
    on = client.post('/api/agent', json=payload)
    assert on.status_code == off.status_code == 200
    assert on.json() == off.json()
    assert repo.search_incidents() == []
    assert len(events(stream)) >= 5


@pytest.mark.parametrize('failure,status', [('dependency',503), ('service',500), ('validation',422)])
def test_http_error_logs_are_safe(monkeypatch, failure, status):
    t, stream = runtime(monkeypatch)
    def dependency():
        if failure == 'dependency':
            raise HTTPException(503, 'original')
        class Broken:
            def execute(self, request):
                raise RuntimeError('secret provider exception')
        return Broken()
    app.dependency_overrides[get_agent_service] = dependency
    body = {'conversation_id': 'private', 'message': 'hello'} if failure != 'validation' else {}
    response = TestClient(app).post('/api/agent', json=body)
    assert response.status_code == status
    root = events(stream)[-1]
    assert root['status'] == 'error'
    assert root['attributes']['http_status'] == status
    assert 'secret provider exception' not in stream.getvalue()
    assert response.headers['x-trace-id'] == root['trace_id']


def test_gemini_mock_response_usage_without_paid_call(monkeypatch):
    from unittest.mock import MagicMock
    from app.rag.generator import GeminiRAGGenerator
    from app.core.config import Settings
    t, stream = runtime(monkeypatch)
    client = MagicMock()
    client.get_client.return_value.models.generate_content.return_value = SimpleNamespace(
        text='answer [S1]', usage_metadata=SimpleNamespace(
            prompt_token_count=5, candidates_token_count=2, total_token_count=9))
    generator = GeminiRAGGenerator(gemini_client=client, settings=Settings(_env_file=None))
    with t.span('http', 'agent'):
        assert generator._call_gemini('private prompt') == 'answer [S1]'
    attempts = [e for e in events(stream) if e.get('component') == 'provider']
    assert len(attempts) == 1
    assert attempts[0]['total_tokens'] == 9
    assert 'private prompt' not in stream.getvalue()


@pytest.mark.parametrize('mode,expected', [('missing','failed'), ('clarification','needs_clarification'), ('abstain','abstained')])
def test_domain_outcome_is_distinct_from_http_status(monkeypatch, tmp_path, mode, expected):
    t, stream = runtime(monkeypatch)
    agent, _ = service(tmp_path)
    payload = {'conversation_id': 'private', 'message': 'Consultar procedimiento'}
    if mode == 'missing':
        agent.orchestrator.knowledge_tool = None
    elif mode == 'clarification':
        payload['append_incident_note'] = {'note': 'private note'}
    else:
        class Abstaining(Pipeline):
            def run(self, **kwargs):
                result = super().run(**kwargs)
                result.abstained = True
                return result
        agent.orchestrator.knowledge_tool = KnowledgeRAGTool(Abstaining())
    app.dependency_overrides[get_agent_service] = lambda: agent
    response = TestClient(app).post('/api/agent', json=payload)
    assert response.status_code == 200
    assert response.json()['status'] == expected
    root = events(stream)[-1]
    assert root['outcome'] == expected
    assert root['status'] == 'ok'


def test_memory_failure_stays_degraded_without_changing_response(monkeypatch, tmp_path):
    from app.memory.write_back import MemoryWriteBack
    t, stream = runtime(monkeypatch)
    agent, _ = service(tmp_path)
    class BrokenMemory:
        def add_message(self, *args):
            raise OSError('secret memory contents')
    agent.orchestrator.memory_write_back = MemoryWriteBack(short_term_memory=BrokenMemory())
    app.dependency_overrides[get_agent_service] = lambda: agent
    response = TestClient(app).post('/api/agent', json={'conversation_id': 'private', 'message': 'Consulta'})
    assert response.status_code == 200
    assert response.json()['status'] == 'completed'
    assert response.json()['observations'][-1]['status'] == 'unavailable'
    records = events(stream)
    assert records[-1]['attributes']['degraded'] is True
    failed = next(e for e in records if e.get('component') == 'memory')
    assert failed['error_code'] == 'io_error'
    assert 'secret memory contents' not in stream.getvalue()


def test_sdk_retry_preserves_calls_and_records_each_attempt(monkeypatch):
    from unittest.mock import MagicMock
    from app.rag.generator import GeminiRAGGenerator
    from app.core.config import Settings
    t, stream = runtime(monkeypatch)
    monkeypatch.setattr('time.sleep', lambda seconds: None)
    client = MagicMock()
    response = SimpleNamespace(text='answer [S1]', usage_metadata=SimpleNamespace(
        prompt_token_count=5, candidates_token_count=2, total_token_count=7))
    client.get_client.return_value.models.generate_content.side_effect = [TimeoutError('private'), response]
    generator = GeminiRAGGenerator(gemini_client=client, settings=Settings(_env_file=None))
    with t.span('http', 'agent'):
        assert generator._call_gemini('secret prompt') == 'answer [S1]'
    attempts = [e for e in events(stream) if e.get('component') == 'provider']
    assert [e['status'] for e in attempts] == ['error', 'ok']
    assert [e['total_tokens'] for e in attempts] == [None, 7]
    assert attempts[0]['parent_span_id'] == attempts[1]['parent_span_id']
    assert 'private' not in stream.getvalue()


def test_session_key_configuration_is_secret_and_validated():
    from app.core.config import Settings
    from pydantic import ValidationError
    settings = Settings(_env_file=None, obs_session_key='test-only-secret-key-32-bytes-long')
    assert 'test-only-secret' not in repr(settings)
    with pytest.raises(ValidationError):
        Settings(_env_file=None, obs_session_key='short')


def test_router_and_embedding_real_sdk_metadata_are_captured(monkeypatch):
    from unittest.mock import MagicMock
    from google.genai import types
    from app.agents.source_router import GeminiSourceRouter
    from app.rag.embeddings import GeminiEmbeddings
    from app.core.config import Settings
    t, stream = runtime(monkeypatch)
    client = MagicMock()
    client.get_client.return_value.models.generate_content.return_value = types.GenerateContentResponse(
        candidates=[types.Candidate(content=types.Content(parts=[types.Part(text='{"source_scope":"internal","confidence":0.99,"routing_reason":"private"}')]))],
        usage_metadata=types.GenerateContentResponseUsageMetadata(prompt_token_count=4, candidates_token_count=2, total_token_count=6))
    # Use actual SDK models without creating a real API client.
    client.get_client.return_value.models.embed_content.return_value = types.EmbedContentResponse(
        embeddings=[types.ContentEmbedding(values=[0.1, 0.2], statistics=types.ContentEmbeddingStatistics(token_count=3))])
    settings = Settings(_env_file=None, embedding_dimension=2)
    with t.span('http', 'agent'):
        routed = GeminiSourceRouter(gemini_client=client, settings=settings).route('private request')
        embedded = GeminiEmbeddings(gemini_client=client, settings=settings).embed_query('private request')
    assert routed.source_scope == 'internal'
    assert embedded == [0.1, 0.2]
    attempts = [e for e in events(stream) if e.get('component') == 'provider']
    assert [(e['operation'],e['input_tokens']) for e in attempts] == [('route',4), ('embed',3)]
    assert 'private' not in stream.getvalue()
