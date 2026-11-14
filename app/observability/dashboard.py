"""Bounded read model for the local dashboard; Hito 3 formulas stay unchanged."""
from collections import OrderedDict
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
from threading import Lock
import time

from app.observability.store import aggregate_events, latency


class QueryTooLarge(ValueError):
    pass


class DashboardReader:
    TTL_SECONDS = 10
    MAX_QUERIES = 8
    MAX_EVENTS = 50000

    def __init__(self, store, clock=time.monotonic):
        self.store, self.clock = store, clock
        self._cache = OrderedDict()
        self._lock = Lock()

    def summary(self, query):
        if query.since is None or query.until is None or query.until - query.since > timedelta(days=7):
            raise ValueError('A period of at most seven days is required')
        key = query.model_dump_json()
        with self._lock:
            cached = self._cache.get(key)
            if cached is not None and self.clock() - cached[0] < self.TTL_SECONDS:
                self._cache.move_to_end(key)
                return deepcopy(cached[1])
            where, values = self.store._where(query)
            with self.store.connection(readonly=True) as db:
                rows = db.execute(f'SELECT payload FROM events WHERE {where} LIMIT ?',
                                  [*values, self.MAX_EVENTS + 1]).fetchall()
            if len(rows) > self.MAX_EVENTS:
                raise QueryTooLarge('Reduce the selected period')
            events = [json.loads(row[0]) for row in rows]
            metrics = aggregate_events(events, query)
            # One bounded snapshot; exact Hito 3 formulas reused, never sampled.
            width = (query.until - query.since).total_seconds() / 24
            durations = [[] for _ in range(24)]
            errors = [0] * 24
            for event in events:
                if event['event'] != 'span' or event['component'] != 'http' or event['operation'] != 'agent':
                    continue
                index = min(23, int((datetime.fromisoformat(event['ended_at']) - query.since).total_seconds() / width))
                durations[index].append(event['duration_ms'])
                errors[index] += event['status'] == 'error'
            series = [{'since': (query.since + timedelta(seconds=i * width)).isoformat(),
                       'until': (query.since + timedelta(seconds=(i + 1) * width)).isoformat(),
                       'requests': len(samples), 'errors': errors[i], 'mean_ms': latency(samples)['mean']}
                      for i, samples in enumerate(durations)]
            result = {'contract_version': 1, 'metrics': metrics, 'series': series,
                      'since': query.since.isoformat(), 'until': query.until.isoformat(),
                      'generated_at': datetime.now(timezone.utc).isoformat(),
                      'cached_for_seconds': self.TTL_SECONDS,
                      'coverage': 'retained_events_only'}
            self._cache[key] = (self.clock(), result)
            self._cache.move_to_end(key)
            while len(self._cache) > self.MAX_QUERIES:
                self._cache.popitem(last=False)
            return deepcopy(result)
