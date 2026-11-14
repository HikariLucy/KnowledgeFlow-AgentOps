"""Read-only API tests using explicitly synthetic telemetry, no network/provider."""
import asyncio
import hashlib
from types import SimpleNamespace

import httpx
import pytest
from fastapi import FastAPI
from pydantic import SecretStr

from tests.test_observability_metrics import store_at, synthetic_event


@pytest.fixture
def api(tmp_path):
    from app.api.observability_routes import router
    app = FastAPI()
    app.include_router(router)
    app.state.observability_store = store_at(tmp_path)
    app.state.observability_store.append(synthetic_event())
    app.state.observability_settings = SimpleNamespace(obs_read_key=SecretStr('x' * 32))
    return app


def request(app, path='/api/observability/events?execution_mode=mock', *, key='x' * 32, method='GET'):
    async def call():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as client:
            return await client.request(method, path, headers={'X-Observability-Key': key} if key else {})
    return asyncio.run(call())


@pytest.mark.parametrize('key', [None, 'wrong', 'á'])
def test_access_is_denied(api, key):
    if key == 'á':
        key = b'\xff'
    result = request(api, key=key)
    assert result.status_code == 401
    assert result.headers['cache-control'] == 'no-store'
    assert 'items' not in result.json()


def test_disabled_key_fails_closed(api):
    api.state.observability_settings.obs_read_key = None
    assert request(api).status_code == 503


def test_read_contract_and_no_db_writes(api):
    path = api.state.observability_store.path
    before = hashlib.sha256(path.read_bytes()).digest()
    result = request(api)
    assert result.status_code == 200
    assert result.headers['cache-control'] == 'no-store'
    assert len(result.json()['items']) == 1
    assert 'session_id' not in result.text
    result = request(api, '/api/observability/metrics?execution_mode=mock')
    assert result.json()['requests']['total'] == 1
    assert hashlib.sha256(path.read_bytes()).digest() == before
    assert request(api, method='POST').status_code == 405


@pytest.mark.parametrize('query', ['execution_mode=all', '', 'execution_mode=mock&limit=501',
    'execution_mode=mock&trace_id=PRIVATE', 'execution_mode=mock&since=2026-11-13',
    'execution_mode=mock&since=2026-11-14T00:00:00Z&until=2026-11-13T00:00:00Z',
    'execution_mode=mock&after=-1', 'execution_mode=mock&operation=PRIVATE'])
def test_invalid_queries_do_not_echo_input(api, query):
    response = request(api, '/api/observability/events?' + query)
    assert response.status_code == 422
    assert 'PRIVATE' not in response.text


def test_store_unavailable_is_not_zero(api):
    api.state.observability_store = None
    response = request(api, '/api/observability/metrics?execution_mode=mock')
    assert response.status_code == 503
    assert 'total' not in response.text


def test_quality_has_no_fabricated_values(api):
    response = request(api, '/api/observability/quality?execution_mode=mock')
    assert response.status_code == 200
    assert response.json()['precision'] is None
    assert response.json()['consistency'] is None
    assert response.json()['source'] == 'evaluated_benchmarks'
