"""Bounded local SQLite event sink. Queries never write or access business databases."""
from contextlib import closing, contextmanager
from datetime import datetime, timezone, timedelta
import json
import math
import os
from pathlib import Path
import sqlite3
from collections import defaultdict

from app.observability.models import EventFilters, StoredEvent


STORE_APPLICATION_ID = 0x4B464F42


class EventStore:
    def __init__(self, path, *, retention_days=7, max_events=50000, max_bytes=64 * 1024 * 1024, now=None):
        if not 1 <= retention_days <= 365 or not 1 <= max_events <= 1000000 or max_bytes < 1024 * 1024:
            raise ValueError('Invalid storage limits')
        self.path = Path(path).resolve()
        self.retention_days, self.max_events, self.max_bytes = retention_days, max_events, max_bytes
        self.now = now or (lambda: datetime.now(timezone.utc))
        if self.path.exists():
            # Inspect identity read-only before chmod, PRAGMAs, DDL or pruning.
            with closing(sqlite3.connect(self.path.as_uri() + '?mode=ro', uri=True)) as existing:
                identity = existing.execute('PRAGMA application_id').fetchone()[0]
                version = existing.execute('PRAGMA user_version').fetchone()[0]
            if identity != STORE_APPLICATION_ID or version != 1:
                raise ValueError('Not a supported observability store')
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        fd = os.open(self.path, os.O_CREAT | os.O_WRONLY, 0o600)
        os.close(fd)
        os.chmod(self.path, 0o600)
        with self.connection() as db:
            db.execute('PRAGMA journal_mode=DELETE')
            db.execute('PRAGMA secure_delete=ON')
            if db.execute('PRAGMA user_version').fetchone()[0] not in (0, 1):
                raise ValueError('Unsupported store version')
            db.executescript('''
                CREATE TABLE IF NOT EXISTS events (
                    seq INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT NOT NULL UNIQUE,
                    occurred_at TEXT NOT NULL,
                    execution_mode TEXT NOT NULL,
                    trace_id TEXT, component TEXT, operation TEXT, status TEXT,
                    payload TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS events_time ON events(occurred_at);
                CREATE INDEX IF NOT EXISTS events_mode_time ON events(execution_mode, occurred_at);
                CREATE INDEX IF NOT EXISTS events_mode_seq ON events(execution_mode, seq);
                CREATE INDEX IF NOT EXISTS events_trace ON events(execution_mode, trace_id, seq);
                CREATE INDEX IF NOT EXISTS events_operation ON events(execution_mode, operation, occurred_at);
                CREATE INDEX IF NOT EXISTS events_status ON events(execution_mode, status, occurred_at);
                CREATE INDEX IF NOT EXISTS events_component ON events(execution_mode, component, occurred_at);
                PRAGMA application_id=1262899010;
                PRAGMA user_version=1;
            ''')
        self.maintain()

    @contextmanager
    def connection(self, *, readonly=False):
        db = sqlite3.connect(self.path.as_uri() + ('?mode=ro' if readonly else '?mode=rw'),
                             uri=True, timeout=0.1)
        try:
            db.execute('PRAGMA temp_store=MEMORY')
            if readonly:
                db.execute('PRAGMA query_only=ON')
            else:
                size = db.execute('PRAGMA page_size').fetchone()[0]
                cap = self.max_bytes // size
                if db.execute('PRAGMA page_count').fetchone()[0] > cap:
                    raise ValueError('Existing store exceeds configured limit')
                db.execute(f'PRAGMA max_page_count={cap}')
                db.execute('PRAGMA secure_delete=ON')
            with db:
                yield db
        finally:
            db.close()

    def cutoff(self):
        return (self.now() - timedelta(days=self.retention_days)).isoformat(timespec='microseconds')

    def _prune(self, db, reserve=0):
        db.execute('DELETE FROM events WHERE occurred_at < ?', (self.cutoff(),))
        excess = db.execute('SELECT count(*) FROM events').fetchone()[0] - self.max_events + reserve
        if excess > 0:
            db.execute('DELETE FROM events WHERE seq IN (SELECT seq FROM events ORDER BY seq LIMIT ?)', (excess,))

    def maintain(self):
        """Startup/periodic maintenance, never invoked by a GET endpoint."""
        with self.connection() as db:
            db.execute('BEGIN IMMEDIATE')
            self._prune(db)

    def append(self, event):
        item = StoredEvent.model_validate(event)
        payload = item.model_dump(mode='json')
        # Normalize all indexed times with fixed precision to preserve lexical ordering.
        stamp = (item.ended_at if item.event == 'span' else item.timestamp).isoformat(timespec='microseconds')
        encoded = json.dumps(payload, allow_nan=False, separators=(',', ':'))
        if len(encoded.encode()) > 16384:
            raise ValueError('Event exceeds size limit')
        for attempt in range(3):
            try:
                with self.connection() as db:
                    db.execute('BEGIN IMMEDIATE')
                    if db.execute('SELECT 1 FROM events WHERE event_id=?', (item.event_id,)).fetchone():
                        return
                    self._prune(db, reserve=1)
                    db.execute("""INSERT INTO events(event_id, occurred_at, execution_mode, trace_id,
                                component, operation, status, payload) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                               (item.event_id, stamp, item.execution_mode, item.trace_id, item.component,
                                item.operation, item.status, encoded))
                return
            except sqlite3.OperationalError as error:
                if getattr(error, 'sqlite_errorcode', None) != sqlite3.SQLITE_FULL or attempt == 2:
                    raise
                # Commit a bounded logical rotation before retrying the failed transaction.
                with self.connection() as db:
                    db.execute('BEGIN IMMEDIATE')
                    count = db.execute('SELECT count(*) FROM events').fetchone()[0]
                    db.execute('DELETE FROM events WHERE seq IN (SELECT seq FROM events ORDER BY seq LIMIT ?)',
                               (max(1, count // 4),))

    def _where(self, filters):
        # Revalidate even callers outside HTTP. All values are bound parameters.
        f = EventFilters.model_validate(filters)
        start = max(f.since or datetime.min.replace(tzinfo=timezone.utc),
                    self.now() - timedelta(days=self.retention_days))
        terms, values = ['execution_mode=?', 'occurred_at>=?'], [f.execution_mode, start.isoformat(timespec='microseconds')]
        if f.until is not None:
            terms.append('occurred_at<?')
            values.append(f.until.isoformat(timespec='microseconds'))
        for key in ['trace_id', 'component', 'operation', 'status']:
            value = getattr(f, key)
            if value is not None:
                terms.append(f'{key}=?')
                values.append(value)
        return ' AND '.join(terms), values

    def events(self, filters, *, limit=100, after=0):
        if not 1 <= limit <= 500 or not 0 <= after <= 2**63 - 1:
            raise ValueError('Invalid pagination')
        where, values = self._where(filters)
        with self.connection(readonly=True) as db:
            rows = db.execute(f'SELECT seq, payload FROM events WHERE {where} AND seq>? ORDER BY seq LIMIT ?',
                              [*values, after, limit + 1]).fetchall()
        items = []
        for seq, payload in rows[:limit]:
            item = json.loads(payload)
            item.pop('session_id', None)
            items.append({'sequence': seq, **item})
        return {'contract_version': 1, 'items': items,
                'next_after': rows[limit - 1][0] if len(rows) > limit else None}

    def metrics(self, filters):
        filters = EventFilters.model_validate(filters)
        where, values = self._where(filters)
        with self.connection(readonly=True) as db:
            # Bounded by max_events; single read transaction supplies a coherent aggregate.
            events = [json.loads(row[0]) for row in db.execute(f'SELECT payload FROM events WHERE {where}', values)]
        return aggregate_events(events, filters)


def aggregate_events(events, filters):
    """Shared aggregation formulas for the API and bounded dashboard snapshot."""
    spans = [e for e in events if e['event'] == 'span']
    requests = [e for e in spans if e['component'] == 'http' and e['operation'] == 'agent']
    executions = [e for e in spans if e['component'] == 'agent' and e['operation'] == 'execute']
    providers = [e for e in spans if e['component'] == 'provider']
    components, tools = defaultdict(list), defaultdict(list)
    for e in spans:
        components[e['component']].append(e['duration_ms'])
        if e['component'] == 'tool':
            tools[e['operation']].append(e['duration_ms'])
    failed = sum(e['status'] == 'error' for e in requests)
    cancelled = sum(e['status'] == 'cancelled' for e in requests)
    return {
        'contract_version': 1, 'execution_mode': filters.execution_mode,
        'scope': 'retained_events', 'matched_events': len(events),
        'requests': {'total': len(requests), 'successful': sum(e['status'] == 'ok' for e in requests),
                     'failed': failed, 'cancelled': cancelled,
                     'error_rate': failed / len(requests) if requests else None},
        'executions': {
            'total': len(executions),
            'successful': sum(e['status'] == 'ok' and e['outcome'] == 'completed' for e in executions),
            'failed': sum(e['status'] == 'error' or e['outcome'] == 'failed' for e in executions),
            'cancelled': sum(e['status'] == 'cancelled' for e in executions),
            'abstained': sum(e['status'] == 'ok' and e['outcome'] == 'abstained' for e in executions),
            'needs_clarification': sum(e['status'] == 'ok' and e['outcome'] == 'needs_clarification' for e in executions),
            'unknown': sum(e['status'] == 'ok' and e['outcome'] is None for e in executions),
        },
        'request_latency_ms': latency([e['duration_ms'] for e in requests]),
        'components': {k: latency(v) for k, v in sorted(components.items())},
        'tools': {k: latency(v) for k, v in sorted(tools.items())},
        'tokens': {key: {'observed_sum': sum(observed) if observed else None,
                        'observed_spans': len(observed), 'total_spans': len(providers)}
                   for key in ['input_tokens', 'output_tokens', 'total_tokens']
                   for observed in [[e[key] for e in providers if e[key] is not None]]},
    }


def latency(values):
    ordered = sorted(values)
    def percentile(p):
        if not ordered:
            return None
        index = (len(ordered) - 1) * p
        lower, upper = math.floor(index), math.ceil(index)
        return ordered[lower] + (ordered[upper] - ordered[lower]) * (index - lower)
    return {'count': len(ordered), 'mean': math.fsum(ordered) / len(ordered) if ordered else None,
            'p50': percentile(0.5), 'p95': percentile(0.95)}
