"""Safe structured logging and synchronous spans shared by ASGI and domain code."""
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import wraps
from enum import Enum
import hashlib
import hmac
import json
import logging
import secrets
import sys
import time
from uuid import uuid4

TOOLS = {'search_knowledge', 'create_incident', 'search_incidents', 'append_incident_note'}
OUTCOMES = {'completed', 'failed', 'abstained', 'needs_clarification'}
INTENTS = {'knowledge_query', 'incident_create', 'incident_search', 'incident_note'}
OPERATIONS = {
    'http': {'agent'}, 'agent': {'execute'}, 'orchestrator': {'execute'},
    'planner': {'plan', 'hydrate_memory'}, 'tool': TOOLS,
    'memory': {'search', 'remember', 'write_back'},
    'rag': {'run', 'retrieve', 'generate', 'route'},
    'provider': {'generate', 'route', 'embed'},
}
LOG_CODES = {
    'workflow_error', 'pipeline_error', 'index_unavailable', 'index_stale',
    'routing_fallback', 'provider_retry', 'citation_repair', 'citation_repair_failed',
    'document_load_failed', 'document_skipped',
}
_current = ContextVar('knowledgeflow_span', default=None)


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def error_code(error, component):
    """Never inspect error messages, class names, request bodies or provider text."""
    if isinstance(error, TimeoutError):
        return 'timeout'
    if isinstance(error, ValueError):
        return 'validation_error'
    if isinstance(error, KeyError):
        return 'not_found'
    if isinstance(error, OSError):
        return 'io_error'
    if not isinstance(error, Exception):
        return 'cancelled'
    return 'provider_error' if component == 'provider' else 'internal_error'


def attributes(values):
    """Only bounded scalars with known semantics can cross the logging boundary."""
    clean = {}
    for key, value in values.items():
        if isinstance(value, Enum):
            value = value.value
        if key in {'http_status', 'result_count', 'source_count', 'citation_count',
                   'iteration_count', 'tool_count'} and type(value) is int and 0 <= value <= 10**9:
            clean[key] = value
        elif key in {'abstained', 'degraded'} and type(value) is bool:
            clean[key] = value
        elif key == 'intent' and isinstance(value, str) and value in INTENTS:
            clean[key] = str(value)
        elif key == 'source_scope' and isinstance(value, str) and value in {'internal', 'external', 'all'}:
            clean[key] = value
        elif key == 'tools' and isinstance(value, (list, tuple)):
            clean[key] = [str(v) for v in value[:64] if isinstance(v, str) and v in TOOLS]
    return clean


class JsonHandler(logging.Handler):
    """A dedicated handler; failures never invoke logging.handleError with payloads."""
    def __init__(self, owner):
        super().__init__()
        self.owner = owner

    def emit(self, record):
        try:
            if self.owner.store is not None:
                self.owner.store.append(record.msg)
                return
            self.owner.stream.write(json.dumps(record.msg, ensure_ascii=True, allow_nan=False) + '\n')
            self.owner.stream.flush()
        except Exception:
            self.owner.dropped_events += 1


class Observer:
    def __init__(self, *, enabled=False, stream=None, session_key=None, clock=None, mode='unknown', store=None):
        self.enabled = enabled
        self.store = store
        self.stream = stream if stream is not None else sys.stderr
        self.session_key = session_key or secrets.token_bytes(32)
        self.clock = clock or time.perf_counter
        self.mode = mode if mode in {'offline', 'mock', 'offline_mock', 'live', 'unknown'} else 'unknown'
        self.dropped_events = 0
        self.logger = logging.Logger('knowledgeflow.observability', logging.INFO)
        self.logger.propagate = False
        self.logger.addHandler(JsonHandler(self))

    def emit(self, event):
        try:
            level = logging.ERROR if event.get('error_code') or event.get('status') in {'error', 'cancelled'} else logging.INFO
            self.logger.log(level, {**event, 'level': logging.getLevelName(level)})
        except Exception:
            self.dropped_events += 1


observer = Observer()


@dataclass
class Trace:
    trace_id: str
    session_id: str


class Span:
    def __init__(self, component, operation, owner, parent):
        self.owner = owner
        self.component = component
        self.operation = operation
        self.trace = parent.trace if parent else Trace(uuid4().hex, uuid4().hex)
        self.span_id = uuid4().hex[:16]
        self.parent_span_id = parent.span_id if parent else None
        self.started_at = utc_now()
        self.start = owner.clock()
        self.status = 'ok'
        self.error = None
        self.outcome = None
        self.metadata = {}
        self.usage = {'input_tokens': None, 'output_tokens': None, 'total_tokens': None}

    def set_attributes(self, **values):
        self.metadata.update(attributes(values))

    def result(self, result):
        """Extract known aggregate fields only; never serialize a model or arbitrary object."""
        try:
            outcome = getattr(result, 'status', None)
            if isinstance(outcome, str) and outcome in OUTCOMES:
                self.outcome = str(outcome.value if hasattr(outcome, 'value') else outcome)
            state = getattr(result, 'state', result)
            tools = getattr(state, 'tool_calls', None)
            if isinstance(tools, list):
                self.set_attributes(tools=tools, tool_count=len(tools))
            self.set_attributes(intent=getattr(state, 'intent', None),
                                iteration_count=getattr(state, 'iteration_count', None))
            observations = getattr(state, 'observations', None)
            if isinstance(observations, list):
                self.set_attributes(degraded=any(isinstance(o, dict) and o.get('status') == 'unavailable'
                                                for o in observations))
            self.set_attributes(source_scope=getattr(result, 'source_scope', None))
            for source, target in [('sources', 'source_count'), ('citations', 'citation_count')]:
                items = getattr(result, source, None)
                if isinstance(items, list):
                    self.set_attributes(**{target: len(items)})
            abstained = getattr(result, 'abstained', None)
            if type(abstained) is bool:
                self.set_attributes(abstained=abstained)
            if isinstance(result, list):
                self.set_attributes(result_count=len(result))
        except Exception:
            # Metadata extraction must not change successful domain operations.
            pass

    def event(self, kind='span'):
        return {
            'schema_version': 1, 'event': kind, 'event_id': uuid4().hex,
            'session_id': self.trace.session_id, 'trace_id': self.trace.trace_id,
            'span_id': self.span_id, 'parent_span_id': self.parent_span_id,
            'component': self.component, 'operation': self.operation,
            'started_at': self.started_at, 'ended_at': utc_now(),
            'duration_ms': max(0.0, (self.owner.clock() - self.start) * 1000),
            'status': self.status, 'outcome': self.outcome, 'error_code': self.error,
            'attributes': self.metadata.copy(), 'execution_mode': self.owner.mode,
            'dropped_events': self.owner.dropped_events, **self.usage,
        }


class NullSpan:
    def set_attributes(self, **values):
        pass

    def result(self, result):
        pass


def current_span():
    return _current.get()


def bind_session(conversation_id):
    """Pseudonymous session, stable only for this secret; never an authorization boundary."""
    active = current_span()
    if active is not None and isinstance(conversation_id, str):
        try:
            active.trace.session_id = hmac.new(
                active.owner.session_key, conversation_id.encode('utf-8', errors='surrogatepass'),
                hashlib.sha256).hexdigest()
        except Exception:
            active.owner.dropped_events += 1


@contextmanager
def span(component, operation):
    owner = observer
    if not owner.enabled:
        yield NullSpan()
        return
    if operation not in OPERATIONS.get(component, set()):
        # Unknown operation names may contain user data; do not log them.
        yield NullSpan()
        return
    try:
        active = Span(component, operation, owner, current_span())
        token = _current.set(active)
    except Exception:
        owner.dropped_events += 1
        yield NullSpan()
        return
    try:
        yield active
    except BaseException as error:
        active.status = 'error' if isinstance(error, Exception) else 'cancelled'
        active.error = error_code(error, component)
        raise
    finally:
        _current.reset(token)
        try:
            owner.emit(active.event())
        except Exception:
            owner.dropped_events += 1


def instrument(component, operation, *, session=False):
    """Synchronous domain functions only. Preserve signature, return and exception identity."""
    def decorate(function):
        @wraps(function)
        def wrapped(*args, **kwargs):
            with span(component, operation) as active:
                if session:
                    request = args[1] if len(args) > 1 else kwargs.get('request')
                    bind_session(getattr(request, 'conversation_id', None))
                result = function(*args, **kwargs)
                active.result(result)
                return result
        return wrapped
    return decorate


def provider_call(operation, function, **kwargs):
    """One span per SDK attempt. No token counting calls or estimates."""
    with span('provider', operation) as active:
        response = function(**kwargs)
        if isinstance(active, Span):
            try:
                usage = getattr(response, 'usage_metadata', None)
                for target, source in [('input_tokens', 'prompt_token_count'),
                                       ('output_tokens', 'candidates_token_count'),
                                       ('total_tokens', 'total_token_count')]:
                    value = getattr(usage, source, None)
                    if type(value) is int and 0 <= value <= 10**12:
                        active.usage[target] = value
                # SDK 1.65: Vertex embeddings can report per-input statistics.
                # Do not infer total/output tokens or convert billable characters.
                if operation == 'embed' and active.usage['input_tokens'] is None:
                    embeddings = getattr(response, 'embeddings', None)
                    if isinstance(embeddings, list) and embeddings:
                        counts = [getattr(getattr(e, 'statistics', None), 'token_count', None)
                                  for e in embeddings]
                        if all(type(n) in {int, float} and 0 <= n <= 10**12 and int(n) == n for n in counts):
                            active.usage['input_tokens'] = sum(int(n) for n in counts)
            except Exception:
                pass
        return response


def safe_log(code, *, error=None):
    """Replace legacy free-text logs with fixed codes; no exception text or stack."""
    if not observer.enabled or code not in LOG_CODES:
        return
    try:
        active = current_span()
        event = {
            'schema_version': 1, 'event': 'log', 'event_id': uuid4().hex,
            'timestamp': utc_now(), 'code': code,
            'session_id': active.trace.session_id if active else None,
            'trace_id': active.trace.trace_id if active else None,
            'span_id': active.span_id if active else None,
            'parent_span_id': active.parent_span_id if active else None,
            'error_code': error_code(error, active.component if active else '') if error is not None else None,
            'execution_mode': observer.mode,
        }
        observer.emit(event)
    except Exception:
        observer.dropped_events += 1
