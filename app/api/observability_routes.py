"""Administrative, metadata-only GET API. No incident/service dependencies."""
import secrets
import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.routing import APIRoute
from fastapi.security import APIKeyHeader
from pydantic import ValidationError
from starlette.responses import JSONResponse

from app.evaluation.quality_store import read_quality_summary
from app.observability.models import EventFilters, ExecutionMode, Status
from app.observability import telemetry


class PrivateReadRoute(APIRoute):
    def get_route_handler(self):
        handler = super().get_route_handler()
        async def safe(request):
            try:
                response = await handler(request)
            except (RequestValidationError, ValidationError, ValueError):
                response = JSONResponse({'detail': 'Invalid observability query'}, status_code=422)
            except HTTPException as error:
                response = JSONResponse({'detail': error.detail}, status_code=error.status_code, headers=error.headers)
            except (sqlite3.Error, OSError):
                response = JSONResponse({'detail': 'Observability store unavailable'}, status_code=503)
            response.headers['Cache-Control'] = 'no-store'
            return response
        return safe


key_header = APIKeyHeader(name='X-Observability-Key', auto_error=False)


def authorize(request: Request, key: str | None = Depends(key_header)):
    settings = request.app.state.observability_settings
    expected = settings.obs_read_key
    if expected is None:
        raise HTTPException(503, 'Observability access disabled')
    if key is None or not secrets.compare_digest(key.encode('utf-8'), expected.get_secret_value().encode('utf-8')):
        raise HTTPException(401, 'Not authenticated', headers={'WWW-Authenticate': 'APIKey'})


router = APIRouter(prefix='/api/observability', tags=['Observability'],
                   route_class=PrivateReadRoute, dependencies=[Depends(authorize)])


def filters(execution_mode: ExecutionMode, trace_id: str | None = None,
            since: str | None = None, until: str | None = None,
            component: str | None = None, operation: str | None = None, status: Status | None = None):
    return EventFilters(execution_mode=execution_mode, trace_id=trace_id, since=since,
                        until=until, component=component, operation=operation, status=status)


def get_store(request: Request):
    store = request.app.state.observability_store
    if store is None:
        raise HTTPException(503, 'Observability store unavailable')
    return store


@router.get('/events')
def events(query: EventFilters = Depends(filters), store=Depends(get_store),
           limit: int = Query(100, ge=1, le=500), after: int = Query(0, ge=0, le=2**63 - 1)):
    return store.events(query, limit=limit, after=after)


@router.get('/metrics')
def metrics(query: EventFilters = Depends(filters), store=Depends(get_store)):
    return {**store.metrics(query), 'collection': {
        'enabled_in_this_process': telemetry.observer.enabled,
        'dropped_events_in_this_process': telemetry.observer.dropped_events,
        'complete_history': False,
    }}


@router.get('/quality')
def quality(request: Request, execution_mode: ExecutionMode):
    settings = getattr(request.app.state, 'observability_settings', None)
    quality_dir = getattr(settings, 'obs_quality_dir', None)
    return read_quality_summary(quality_dir, execution_mode)
