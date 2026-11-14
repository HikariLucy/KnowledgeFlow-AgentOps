"""Offline contracts: safe metadata, isolation and business exception transparency."""
import asyncio
import io
import json
from types import SimpleNamespace

import pytest


def runtime(monkeypatch, **kwargs):
    from app.observability import telemetry
    stream = io.StringIO()
    observer = telemetry.Observer(enabled=True, stream=stream, session_key=b'x' * 32, **kwargs)
    monkeypatch.setattr(telemetry, 'observer', observer)
    return telemetry, stream


def events(stream):
    return [json.loads(line) for line in stream.getvalue().splitlines()]


def test_nested_spans_monotonic_and_private_session(monkeypatch):
    t, stream = runtime(monkeypatch, clock=iter([1.0, 1.1, 1.3, 1.5]).__next__)
    with t.span('http', 'agent'):
        t.bind_session('persona@example.com')
        with t.span('tool', 'search_incidents'):
            pass
    child, root = events(stream)
    assert child['parent_span_id'] == root['span_id']
    assert root['parent_span_id'] is None
    assert child['trace_id'] == root['trace_id']
    assert child['session_id'] == root['session_id']
    assert child['duration_ms'] == pytest.approx(200)
    assert root['duration_ms'] == pytest.approx(500)
    assert 'persona@example.com' not in stream.getvalue()
    assert t.current_span() is None


def test_exception_identity_and_no_sensitive_message(monkeypatch):
    t, stream = runtime(monkeypatch)
    error = ValueError('password=secret persona@example.com prompt privado')
    with pytest.raises(ValueError) as caught:
        with t.span('tool', 'create_incident'):
            raise error
    assert caught.value is error
    record = events(stream)[0]
    assert record['status'] == 'error'
    assert record['error_code'] == 'validation_error'
    assert 'secret' not in stream.getvalue()
    assert 'prompt privado' not in stream.getvalue()
    assert t.current_span() is None


def test_concurrent_traces_and_stable_session(monkeypatch):
    t, stream = runtime(monkeypatch)
    async def worker(conversation):
        with t.span('http', 'agent'):
            t.bind_session(conversation)
            await asyncio.sleep(0)
            with t.span('planner', 'plan'):
                await asyncio.sleep(0)
    async def run():
        await asyncio.gather(worker('same'), worker('same'), worker('other'))
    asyncio.run(run())
    roots = [e for e in events(stream) if e['parent_span_id'] is None]
    assert len({e['trace_id'] for e in roots}) == 3
    assert len({e['session_id'] for e in roots}) == 2
    by_trace = {e['trace_id']: e for e in roots}
    for event in events(stream):
        assert event['session_id'] == by_trace[event['trace_id']]['session_id']


def test_sink_failure_does_not_break_operation(monkeypatch):
    t, _ = runtime(monkeypatch)
    class Broken(io.StringIO):
        def write(self, value):
            raise OSError('secret disk path')
    t.observer.stream = Broken()
    with t.span('tool', 'create_incident'):
        result = 42
    assert result == 42
    assert t.observer.dropped_events == 1


def test_disabled_no_events_and_same_return(monkeypatch):
    t, stream = runtime(monkeypatch)
    t.observer.enabled = False
    @t.instrument('tool', 'search_incidents')
    def operation():
        return ['original']
    assert operation() == ['original']
    assert stream.getvalue() == ''


def test_provider_usage_only_integer_metadata(monkeypatch):
    t, stream = runtime(monkeypatch)
    response = SimpleNamespace(text='secret', usage_metadata=SimpleNamespace(
        prompt_token_count=12, candidates_token_count=3, total_token_count=19))
    with t.span('http', 'agent'):
        assert t.provider_call('generate', lambda: response) is response
        t.provider_call('embed', lambda: SimpleNamespace())
    generate, embed, _ = events(stream)
    assert (generate['input_tokens'], generate['output_tokens'], generate['total_tokens']) == (12, 3, 19)
    assert embed['total_tokens'] is None
    assert 'secret' not in stream.getvalue()


def test_attributes_allowlist_and_log_sanitization(monkeypatch):
    t, stream = runtime(monkeypatch)
    with t.span('http', 'agent') as active:
        active.set_attributes(prompt='secret', http_status=200, tool='secret', result_count=True)
        t.safe_log('workflow_error', error=RuntimeError('secret'))
    records = events(stream)
    assert 'secret' not in stream.getvalue()
    assert records[-1]['attributes'] == {'http_status': 200}
    assert records[0]['trace_id'] == records[-1]['trace_id']
    assert records[0]['event'] == 'log'


def test_cancelled_span_restores_context(monkeypatch):
    t, stream = runtime(monkeypatch)
    with pytest.raises(asyncio.CancelledError):
        with t.span('http', 'agent'):
            raise asyncio.CancelledError('private')
    assert events(stream)[0]['status'] == 'cancelled'
    assert events(stream)[0]['error_code'] == 'cancelled'
    assert t.current_span() is None
    assert 'private' not in stream.getvalue()


def test_invalid_token_metadata_is_unknown_and_zero_is_valid(monkeypatch):
    t, stream = runtime(monkeypatch)
    response = SimpleNamespace(usage_metadata=SimpleNamespace(
        prompt_token_count=True, candidates_token_count=-1, total_token_count='private'))
    t.provider_call('generate', lambda: response)
    t.provider_call('generate', lambda: SimpleNamespace(usage_metadata=SimpleNamespace(
        prompt_token_count=0, candidates_token_count=0, total_token_count=0)))
    invalid, zero = events(stream)
    assert invalid['input_tokens'] is invalid['output_tokens'] is invalid['total_tokens'] is None
    assert zero['total_tokens'] == 0
    assert 'private' not in stream.getvalue()


def test_embedding_statistics_from_provider_are_not_estimated(monkeypatch):
    t, stream = runtime(monkeypatch)
    response = SimpleNamespace(embeddings=[SimpleNamespace(
        values=[0.1, 0.2], statistics=SimpleNamespace(token_count=7.0))])
    t.provider_call('embed', lambda: response)
    record = events(stream)[0]
    assert record['input_tokens'] == 7
    assert record['output_tokens'] is None
    assert record['total_tokens'] is None
    assert 'values' not in stream.getvalue()


def test_event_severity_and_safe_result_aggregates(monkeypatch):
    t, stream = runtime(monkeypatch)
    with t.span('tool', 'search_knowledge') as active:
        active.result(SimpleNamespace(source_scope='internal', sources=['secret'], citations=['S1'], abstained=False))
    with pytest.raises(TimeoutError):
        t.provider_call('generate', lambda: (_ for _ in ()).throw(TimeoutError('secret')))
    success, failure = events(stream)
    assert success['level'] == 'INFO'
    assert failure['level'] == 'ERROR'
    assert success['attributes']['source_count'] == 1
    assert success['attributes']['citation_count'] == 1
    assert success['attributes']['source_scope'] == 'internal'
    assert failure['error_code'] == 'timeout'
    assert 'secret' not in stream.getvalue()


def test_unicode_session_and_clock_failure_never_change_domain_result(monkeypatch):
    t, stream = runtime(monkeypatch)
    class Service:
        @t.instrument('agent', 'execute', session=True)
        def execute(self, request):
            return 42
    assert Service().execute(SimpleNamespace(conversation_id='\ud800')) == 42
    def broken_clock():
        raise OSError('private')
    t.observer.clock = broken_clock
    assert Service().execute(SimpleNamespace(conversation_id='normal')) == 42
    assert t.current_span() is None


def test_enum_intent_uses_canonical_value(monkeypatch):
    from enum import Enum
    t, stream = runtime(monkeypatch)
    class Intent(str, Enum):
        SEARCH = 'incident_search'
    with t.span('planner', 'plan') as active:
        active.result(SimpleNamespace(intent=Intent.SEARCH))
    assert events(stream)[0]['attributes']['intent'] == 'incident_search'


def test_safe_log_failure_cannot_mask_original_exception(monkeypatch):
    t, stream = runtime(monkeypatch)
    def broken_timestamp():
        raise OSError('private')
    monkeypatch.setattr(t, 'utc_now', broken_timestamp)
    t.safe_log('workflow_error', error=ValueError('original'))
    assert stream.getvalue() == ''
    assert t.observer.dropped_events == 1
