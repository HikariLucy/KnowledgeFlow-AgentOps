"""Explicitly synthetic fixtures; these values are NOT benchmark/live evidence."""
import json
from datetime import datetime, timezone, timedelta

import pytest

NOW = datetime(2026, 11, 13, tzinfo=timezone.utc)


def synthetic_event(n=1, **changes):
    event = dict(schema_version=1, event='span', event_id=f'{n:032x}',
                 trace_id=f'{42:032x}', session_id='a' * 64, span_id=f'{n:016x}',
                 parent_span_id=None, component='http', operation='agent',
                 started_at=NOW.isoformat(), ended_at=NOW.isoformat(), duration_ms=10.0,
                 status='ok', outcome=None, error_code=None, attributes={},
                 execution_mode='mock', dropped_events=0, input_tokens=None,
                 output_tokens=None, total_tokens=None, level='INFO')
    event.update(changes)
    return event


def store_at(tmp_path, **kwargs):
    from app.observability.store import EventStore
    return EventStore(tmp_path / 'events.sqlite3', now=lambda: NOW, **kwargs)


def filters(**kwargs):
    from app.observability.models import EventFilters
    return EventFilters(execution_mode=kwargs.pop('execution_mode', 'mock'), **kwargs)


def test_persist_real_observer_event_and_hide_session(tmp_path, monkeypatch):
    from app.observability import telemetry as t
    store = store_at(tmp_path)
    owner = t.Observer(enabled=True, mode='mock', store=store)
    monkeypatch.setattr(t, 'observer', owner)
    # Deterministic synthetic clock, no provider invoked.
    monkeypatch.setattr(t, 'utc_now', lambda: NOW.isoformat())
    with t.span('http', 'agent'):
        t.safe_log('workflow_error')
    page = store.events(filters(), limit=10)
    assert len(page['items']) == 2
    assert {e['event'] for e in page['items']} == {'span', 'log'}
    assert 'session_id' not in json.dumps(page)
    assert store.metrics(filters())['requests']['total'] == 1


def test_dedup_pagination_filters_and_modes(tmp_path):
    store = store_at(tmp_path)
    for n, mode in enumerate(['mock', 'live', 'offline', 'offline_mock', 'unknown', 'mock'], 1):
        store.append(synthetic_event(n, execution_mode=mode))
    store.append(synthetic_event(1))
    first = store.events(filters(), limit=1)
    assert first['items'][0]['event_id'] == f'{1:032x}'
    second = store.events(filters(), limit=1, after=first['next_after'])
    assert second['items'][0]['event_id'] == f'{6:032x}'
    assert second['next_after'] is None
    for mode in ['live', 'offline', 'offline_mock', 'unknown']:
        assert len(store.events(filters(execution_mode=mode))['items']) == 1
    assert store.events(filters(status='error'))['items'] == []
    assert len(store.events(filters(trace_id=f'{42:032x}', operation='agent'))['items']) == 2


def test_aggregates_do_not_double_count_or_invent_usage(tmp_path):
    store = store_at(tmp_path)
    for n, duration in enumerate([10, 20, 30, 40], 1):
        store.append(synthetic_event(n, duration_ms=duration, status='error' if n == 4 else 'ok'))
    store.append(synthetic_event(5, component='agent', operation='execute', outcome='failed'))
    store.append(synthetic_event(6, component='agent', operation='execute', outcome='abstained'))
    store.append(synthetic_event(7, component='tool', operation='search_knowledge', duration_ms=7))
    store.append(synthetic_event(8, component='provider', operation='generate', input_tokens=0, total_tokens=12))
    store.append(synthetic_event(9, component='provider', operation='generate'))
    result = store.metrics(filters())
    assert result['requests'] == dict(total=4, successful=3, failed=1, cancelled=0, error_rate=0.25)
    assert result['request_latency_ms'] == dict(count=4, mean=25.0, p50=25.0, p95=38.5)
    assert result['executions']['failed'] == 1
    assert result['executions']['abstained'] == 1
    assert result['tools']['search_knowledge']['mean'] == 7
    assert result['tokens']['input_tokens'] == dict(observed_sum=0, observed_spans=1, total_spans=2)
    assert result['tokens']['output_tokens']['observed_sum'] is None
    assert result['tokens']['total_tokens']['observed_sum'] == 12
    empty = store.metrics(filters(execution_mode='live'))
    assert empty['requests']['error_rate'] is None
    assert empty['request_latency_ms']['mean'] is None
    assert empty['tokens']['total_tokens']['observed_sum'] is None


def test_rotation_retention_and_restart(tmp_path):
    store = store_at(tmp_path, max_events=3, retention_days=1)
    for n in range(1, 6):
        store.append(synthetic_event(n))
    assert [e['event_id'] for e in store.events(filters())['items']] == [f'{n:032x}' for n in [3, 4, 5]]
    reopened = store_at(tmp_path, max_events=3, retention_days=1)
    assert len(reopened.events(filters())['items']) == 3
    reopened.now = lambda: NOW + timedelta(days=2)
    assert reopened.events(filters())['items'] == []
    reopened.maintain()
    assert reopened.metrics(filters())['requests']['total'] == 0
    assert (tmp_path / 'events.sqlite3').stat().st_mode & 0o777 == 0o600


@pytest.mark.parametrize('changes', [dict(component='secret@email.test'), dict(duration_ms=float('nan')),
    dict(execution_mode='mixed'), dict(event_id='secret'), dict(total_tokens=-1), dict(schema_version=2)])
def test_reject_invalid_events(tmp_path, changes):
    store = store_at(tmp_path)
    with pytest.raises(ValueError):
        store.append(synthetic_event(**changes))
    assert store.events(filters())['items'] == []


def test_strip_unknown_fields_and_attributes(tmp_path):
    store = store_at(tmp_path)
    store.append(synthetic_event(prompt='SECRET', attributes={'prompt': 'SECRET', 'http_status': 200}))
    assert 'SECRET' not in json.dumps(store.events(filters()))
    assert b'SECRET' not in (tmp_path / 'events.sqlite3').read_bytes()


def test_storage_failure_and_disabled_observer_preserve_business(tmp_path, monkeypatch):
    from app.observability import telemetry as t
    store = store_at(tmp_path)
    def fail(event):
        raise OSError('PRIVATE')
    monkeypatch.setattr(store, 'append', fail)
    owner = t.Observer(enabled=True, store=store)
    monkeypatch.setattr(t, 'observer', owner)
    with t.span('http', 'agent'):
        result = 42
    assert result == 42 and owner.dropped_events == 1
    owner.enabled = False
    with t.span('http', 'agent'):
        pass
    assert owner.dropped_events == 1


def test_physical_cap_rotates_and_continues_accepting(tmp_path):
    store = store_at(tmp_path, max_bytes=1024 * 1024)
    for n in range(1, 1301):
        store.append(synthetic_event(n))
    assert store.path.stat().st_size <= 1024 * 1024
    result = store.events(filters(trace_id=f'{42:032x}'), limit=500)
    assert result['items'][0]['event_id'] != f'{1:032x}'
    assert store.metrics(filters())['requests']['total'] < 1300
    with store.connection(readonly=True) as db:
        assert db.execute('SELECT event_id FROM events ORDER BY seq DESC LIMIT 1').fetchone()[0] == f'{1300:032x}'


def test_period_boundaries_and_timezone(tmp_path):
    store = store_at(tmp_path)
    store.append(synthetic_event())
    assert len(store.events(filters(since=NOW, until=NOW + timedelta(seconds=1)))['items']) == 1
    assert store.events(filters(until=NOW))['items'] == []
    assert len(store.events(filters(since='2026-11-12T21:00:00-03:00'))['items']) == 1


def test_quality_requires_evaluated_evidence():
    from app.observability.models import QualityMeasurement
    data = dict(benchmark_id='a'*32, dataset_sha256='b'*64, evaluator_version='synthetic-v1',
                execution_mode='mock', synthetic=True, evaluated_at=NOW,
                metric='precision', numerator=3, denominator=4)
    assert QualityMeasurement(**data).value == .75
    with pytest.raises(ValueError):
        QualityMeasurement(**{**data, 'denominator': 0})
    with pytest.raises(ValueError):
        QualityMeasurement(**{**data, 'numerator': 5})


@pytest.mark.parametrize('kwargs', [dict(obs_read_key='short'), dict(obs_max_events=0),
    dict(obs_retention_days=0), dict(obs_max_bytes=1024)])
def test_invalid_storage_configuration(kwargs):
    from app.core.config import Settings
    with pytest.raises(ValueError):
        Settings(_env_file=None, **kwargs)


def test_store_lifecycle_and_collection_modes(tmp_path, monkeypatch):
    import asyncio
    from app import main
    from app.observability import telemetry as t
    from app.core.config import Settings
    settings = Settings(_env_file=None, obs_enabled=True, obs_store_enabled=True,
                        obs_execution_mode='mock', obs_store_path=str(tmp_path / 'lifecycle.sqlite3'))
    monkeypatch.setattr(main, 'settings', settings)
    monkeypatch.setattr(t, 'observer', t.Observer(enabled=True, mode='mock'))
    async def run():
        async with main.observability_lifespan(main.app):
            with t.span('http', 'agent'):
                pass
            store = main.app.state.observability_store
            assert store.metrics(filters())['requests']['total'] == 1
            t.observer.enabled = False
            with t.span('http', 'agent'):
                pass
            assert store.metrics(filters())['requests']['total'] == 1
    asyncio.run(run())


def test_foreign_database_is_never_modified(tmp_path):
    import sqlite3
    from app.observability.store import EventStore
    path = tmp_path / 'incidents.sqlite3'
    with sqlite3.connect(path) as db:
        db.execute('CREATE TABLE incidents (id INTEGER PRIMARY KEY, description TEXT)')
        db.execute("INSERT INTO incidents VALUES (1, 'synthetic private content')")
    path.chmod(0o640)
    before, mode = path.read_bytes(), path.stat().st_mode
    with pytest.raises(ValueError):
        EventStore(path)
    assert path.read_bytes() == before
    assert path.stat().st_mode == mode


def test_metrics_accept_validated_mapping(tmp_path):
    store = store_at(tmp_path)
    assert store.metrics({'execution_mode': 'mock'})['requests']['total'] == 0


def test_real_agent_http_response_parity_with_storage(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from app.main import app
    from app.api.agent_routes import get_agent_service
    from app.observability import telemetry as t
    from tests.test_observability_integration import service
    from app.observability.store import EventStore
    store = EventStore(tmp_path / 'operational.sqlite3')
    agent, repo = service(tmp_path)
    previous = app.dependency_overrides.copy()
    app.dependency_overrides[get_agent_service] = lambda: agent
    owner = t.Observer(enabled=False, mode='mock', store=store)
    monkeypatch.setattr(t, 'observer', owner)
    try:
        client = TestClient(app)
        payload = {'conversation_id': 'synthetic-private@example.test',
                   'message': 'Buscar incidentes', 'search_incidents': {'query': 'no match'}}
        off = client.post('/api/agent', json=payload)
        assert store.metrics(filters())['requests']['total'] == 0
        owner.enabled = True
        on = client.post('/api/agent', json=payload)
        assert on.status_code == off.status_code == 200
        assert on.json() == off.json()
        assert repo.search_incidents() == []
        result = store.metrics(filters())
        assert result['requests']['total'] == 1
        assert result['executions']['total'] == 1
        assert len(result['components']) >= 4
        assert owner.dropped_events == 0
        assert b'synthetic-private@example.test' not in store.path.read_bytes()
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)
