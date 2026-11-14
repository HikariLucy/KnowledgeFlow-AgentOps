"""Pure ASGI tests require neither credentials nor external sockets."""
import asyncio
import pytest
from tests.test_observability_core import runtime, events


@pytest.mark.parametrize('status', [200, 422, 503])
def test_asgi_response_preserved_and_correlated(monkeypatch, status):
    t, stream = runtime(monkeypatch)
    from app.observability.middleware import ObservabilityMiddleware
    sent = []
    async def application(scope, receive, send):
        with t.span('planner', 'plan'):
            pass
        await send({'type': 'http.response.start', 'status': status, 'headers': []})
        await send({'type': 'http.response.body', 'body': b'original'})
    async def send(message):
        sent.append(message)
    asyncio.run(ObservabilityMiddleware(application)(
        {'type': 'http', 'path': '/api/agent', 'headers': [(b'x-trace-id', b'secret')]}, None, send))
    root = events(stream)[-1]
    assert sent[0]['status'] == status
    assert sent[1]['body'] == b'original'
    assert dict(sent[0]['headers'])[b'x-trace-id'].decode() == root['trace_id']
    assert root['attributes']['http_status'] == status
    assert root['status'] == ('ok' if status == 200 else 'error')
    assert 'secret' not in stream.getvalue()
    assert t.current_span() is None


def test_unhandled_exception_keeps_original_and_records_500(monkeypatch):
    t, stream = runtime(monkeypatch)
    from app.observability.middleware import ObservabilityMiddleware
    error = RuntimeError('private')
    async def application(scope, receive, send):
        raise error
    with pytest.raises(RuntimeError) as caught:
        asyncio.run(ObservabilityMiddleware(application)({'type': 'http', 'path': '/api/agent'}, None, None))
    assert caught.value is error
    assert events(stream)[0]['attributes']['http_status'] == 500
    assert 'private' not in stream.getvalue()


def test_non_agent_path_passes_through(monkeypatch):
    t, stream = runtime(monkeypatch)
    from app.observability.middleware import ObservabilityMiddleware
    scopes = []
    async def application(scope, receive, send):
        scopes.append(scope)
    scope = {'type': 'http', 'path': '/health'}
    asyncio.run(ObservabilityMiddleware(application)(scope, None, None))
    assert scopes == [scope]
    assert stream.getvalue() == ''


def test_clock_failure_does_not_break_http_response(monkeypatch):
    t, stream = runtime(monkeypatch)
    from app.observability.middleware import ObservabilityMiddleware
    def broken_clock():
        raise OSError('private')
    t.observer.clock = broken_clock
    sent = []
    async def application(scope, receive, send):
        await send({'type': 'http.response.start', 'status': 200, 'headers': []})
        await send({'type': 'http.response.body', 'body': b'original'})
    async def send(message):
        sent.append(message)
    asyncio.run(ObservabilityMiddleware(application)({'type': 'http', 'path': '/api/agent'}, None, send))
    assert sent[1]['body'] == b'original'
    assert stream.getvalue() == ''
    assert t.observer.dropped_events == 1
