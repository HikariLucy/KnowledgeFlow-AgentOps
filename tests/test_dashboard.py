"""Dashboard contracts with explicitly synthetic events; no real provider/network."""
import asyncio
from base64 import b64encode
from datetime import timedelta
from types import SimpleNamespace

import httpx
import pytest
from fastapi import FastAPI
from pydantic import SecretStr

from tests.test_observability_metrics import NOW, store_at, synthetic_event, filters

PASSWORD = 'synthetic-dashboard-password-32-bytes'
PARAMS = 'execution_mode=mock&since=2026-11-12T00:00:00Z&until=2026-11-14T00:00:00Z'


@pytest.fixture
def dashboard(tmp_path):
    from app.api.dashboard_routes import router
    from app.api.observability_routes import router as original
    app = FastAPI()
    app.include_router(router)
    app.include_router(original)
    app.state.observability_settings = SimpleNamespace(
        obs_dashboard_enabled=True, obs_dashboard_password=SecretStr(PASSWORD),
        obs_read_key=SecretStr('synthetic-private-observability-key'))
    app.state.observability_store = store_at(tmp_path)
    return app


def call(app, path='/dashboard', *, auth=True, client='127.0.0.1', host='127.0.0.1', headers=None, method='GET'):
    async def run():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app, client=(client, 1234)),
                                    base_url='http://' + host) as session:
            h = dict(headers or {})
            if auth:
                h['Authorization'] = 'Basic ' + b64encode(f'observer:{PASSWORD}'.encode()).decode()
            return await session.request(method, path, headers=h)
    return asyncio.run(run())


@pytest.mark.parametrize('path', ['/dashboard', '/dashboard/api/summary?' + PARAMS,
    '/dashboard/api/events?execution_mode=mock', '/dashboard/api/quality?execution_mode=mock',
    '/dashboard/api/options'])
def test_requires_auth_on_every_dashboard_route(dashboard, path):
    response = call(dashboard, path, auth=False)
    assert response.status_code == 401
    assert response.headers['cache-control'] == 'no-store'
    assert response.headers['www-authenticate'].startswith('Basic')


@pytest.mark.parametrize('kwargs', [dict(client='192.0.2.1'), dict(host='evil.example'),
    dict(headers={'Origin': 'http://evil.example'}), dict(headers={'Origin': 'null'}),
    dict(headers={'X-Forwarded-For': '127.0.0.1'}), dict(headers={'Forwarded': 'for=127.0.0.1'}),
    dict(headers={'Sec-Fetch-Site': 'cross-site'})])
def test_rejects_remote_rebinding_and_cross_origin(dashboard, kwargs):
    assert call(dashboard, **kwargs).status_code == 403


def test_default_off_and_missing_password(dashboard):
    dashboard.state.observability_settings.obs_dashboard_enabled = False
    assert call(dashboard).status_code == 404
    dashboard.state.observability_settings.obs_dashboard_enabled = True
    dashboard.state.observability_settings.obs_dashboard_password = None
    assert call(dashboard).status_code == 503


def test_original_key_api_stays_protected(dashboard):
    assert call(dashboard, '/api/observability/events?execution_mode=mock').status_code == 401


def test_shell_never_contains_secrets_and_has_csp(dashboard):
    response = call(dashboard)
    assert response.status_code == 200
    assert PASSWORD not in response.text and 'synthetic-private-observability-key' not in response.text
    assert "frame-ancestors 'none'" in response.headers['content-security-policy']
    assert 'Vista general' in response.text


def test_empty_summary_and_quality_are_unknown(dashboard):
    response = call(dashboard, '/dashboard/api/summary?' + PARAMS)
    assert response.status_code == 200
    body = response.json()
    assert body['metrics']['request_latency_ms']['mean'] is None
    assert body['metrics']['tokens']['total_tokens']['observed_sum'] is None
    assert len(body['series']) == 24
    assert all(b['mean_ms'] is None and b['requests'] == 0 for b in body['series'])
    quality = call(dashboard, '/dashboard/api/quality?execution_mode=mock').json()
    assert quality['precision'] is None and quality['consistency'] is None


def test_summary_preserves_formulas_and_modes(dashboard):
    store = dashboard.state.observability_store
    for n, duration in enumerate([10, 20, 30, 40], 1):
        store.append(synthetic_event(n, duration_ms=duration, status='error' if n == 4 else 'ok'))
    store.append(synthetic_event(5, execution_mode='live', duration_ms=900))
    body = call(dashboard, '/dashboard/api/summary?' + PARAMS).json()
    assert body['metrics'] == store.metrics(filters(since=NOW-timedelta(days=1), until=NOW+timedelta(days=1)))
    bucket = next(b for b in body['series'] if b['requests'])
    assert bucket['mean_ms'] == 25 and bucket['errors'] == 1 and bucket['requests'] == 4
    assert body['cached_for_seconds'] == 10


def test_events_cursor_and_filters_are_lossless_on_stable_set(dashboard):
    store = dashboard.state.observability_store
    for n in range(1, 8):
        store.append(synthetic_event(n, execution_mode='mock' if n % 2 else 'live'))
    seen, cursor = [], 0
    for _ in range(5):
        response = call(dashboard, f'/dashboard/api/events?execution_mode=mock&limit=2&after={cursor}')
        assert response.status_code == 200
        body = response.json()
        seen += [e['event_id'] for e in body['items']]
        assert 'session_id' not in response.text
        cursor = body['next_after']
        if cursor is None:
            break
    assert seen == [f'{n:032x}' for n in [1, 3, 5, 7]]


@pytest.mark.parametrize('params', ['execution_mode=mock', PARAMS + '&component=PRIVATE',
    'execution_mode=mock&since=2026-01-01T00:00:00Z&until=2026-11-14T00:00:00Z'])
def test_summary_requires_bounded_valid_period(dashboard, params):
    response = call(dashboard, '/dashboard/api/summary?' + params)
    assert response.status_code == 422
    assert 'PRIVATE' not in response.text


def test_reads_never_write_and_store_failure_is_not_zero(dashboard):
    store = dashboard.state.observability_store
    store.append(synthetic_event())
    before = store.path.read_bytes()
    assert call(dashboard, '/dashboard/api/summary?' + PARAMS).status_code == 200
    assert store.path.read_bytes() == before
    assert call(dashboard, '/dashboard/api/events?execution_mode=mock', method='POST').status_code == 405
    dashboard.state.observability_store = None
    assert call(dashboard, '/dashboard/api/summary?' + PARAMS).status_code == 503


def test_dashboard_settings_do_not_enable_telemetry():
    from app.core.config import Settings
    settings = Settings(_env_file=None)
    assert not settings.obs_dashboard_enabled
    with pytest.raises(ValueError):
        Settings(_env_file=None, obs_dashboard_password='short')


def test_wrong_password_and_reused_key_are_rejected(dashboard):
    bad = 'Basic ' + b64encode(b'observer:wrong').decode()
    assert call(dashboard, auth=False, headers={'Authorization':bad}).status_code == 401
    from app.core.config import Settings
    with pytest.raises(ValueError):
        Settings(_env_file=None, obs_dashboard_password=PASSWORD, obs_read_key=PASSWORD)


def test_summary_cost_limit_returns_no_partial_metrics(dashboard, monkeypatch):
    from app.observability.dashboard import DashboardReader
    monkeypatch.setattr(DashboardReader, 'MAX_EVENTS', 1)
    store = dashboard.state.observability_store
    store.append(synthetic_event(1));store.append(synthetic_event(2))
    response = call(dashboard, '/dashboard/api/summary?' + PARAMS)
    assert response.status_code == 413
    assert 'metrics' not in response.json()


def test_cache_expires_and_bounds_cardinality(dashboard, monkeypatch):
    from app.observability.dashboard import DashboardReader
    from app.observability.models import EventFilters
    store = dashboard.state.observability_store
    clock = [0]
    reader = DashboardReader(store, clock=lambda:clock[0])
    monkeypatch.setattr(reader, 'MAX_QUERIES', 2)
    query = filters(since=NOW-timedelta(days=1), until=NOW+timedelta(days=1))
    assert reader.summary(query)['metrics']['requests']['total'] == 0
    store.append(synthetic_event())
    assert reader.summary(query)['metrics']['requests']['total'] == 0
    clock[0] = 11
    assert reader.summary(query)['metrics']['requests']['total'] == 1
    reader.summary(EventFilters(**{**query.model_dump(), 'execution_mode':'live'}))
    reader.summary(EventFilters(**{**query.model_dump(), 'execution_mode':'offline'}))
    assert len(reader._cache) == 2


def test_public_assets_never_serve_dashboard_html_or_credentials(dashboard, monkeypatch):
    from app.main import app
    monkeypatch.setattr(app.state, 'observability_settings', dashboard.state.observability_settings)
    assert call(app, '/static/observability.html', auth=False).status_code == 404
    assert call(app, '/dashboard', auth=False).status_code == 401
    for path in ['dashboard.css', 'dashboard.mjs', 'core.mjs', 'charts.mjs']:
        response = call(app, '/static/observability/' + path, auth=False)
        assert response.status_code == 200
        assert PASSWORD not in response.text
        assert 'synthetic-private-observability-key' not in response.text


def test_frontend_behavior_contracts():
    import os
    import shutil
    import subprocess
    from pathlib import Path
    node = shutil.which('node')
    if node is None:
        pytest.skip('Node.js is required for frontend behavior checks')
    env = dict(os.environ)
    env.pop('NODE_TEST_CONTEXT', None)
    result = subprocess.run([node, str(Path(__file__).with_name('dashboard_frontend.test.mjs'))],
                            capture_output=True, text=True, timeout=30, env=env)
    assert result.returncode == 0, result.stdout + result.stderr
    assert 'tests 6' in result.stdout or '# tests 6' in result.stdout
