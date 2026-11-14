"""Local-only, independently authenticated dashboard. Never forwards OBS_READ_KEY."""
import ipaddress
from pathlib import Path
import secrets

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from starlette.responses import JSONResponse

from app.api.observability_routes import PrivateReadRoute, filters, get_store, quality
from app.observability import telemetry
from app.observability.dashboard import DashboardReader, QueryTooLarge
from app.observability.models import EventFilters


class DashboardRoute(PrivateReadRoute):
    def get_route_handler(self):
        handler = super().get_route_handler()
        async def secure(request):
            response = await handler(request)
            response.headers['Content-Security-Policy'] = (
                "default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; "
                "img-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'")
            response.headers['X-Content-Type-Options'] = 'nosniff'
            response.headers['Referrer-Policy'] = 'no-referrer'
            response.headers['X-Frame-Options'] = 'DENY'
            return response
        return secure


basic = HTTPBasic(auto_error=False, realm='KnowledgeFlow local')


def local_access(request: Request, credentials: HTTPBasicCredentials | None = Depends(basic)):
    settings = request.app.state.observability_settings
    if not settings.obs_dashboard_enabled:
        raise HTTPException(404, 'Dashboard disabled')
    try:
        loopback = request.client is not None and ipaddress.ip_address(request.client.host).is_loopback
    except ValueError:
        loopback = False
    # No DNS names, proxy headers or external fetches: fail closed against rebinding/proxying.
    if (not loopback or request.url.hostname not in {'127.0.0.1', '::1'}
            or any(k.lower() == 'forwarded' or k.lower().startswith('x-forwarded-') for k in request.headers)
            or request.headers.get('sec-fetch-site') not in {None, 'none', 'same-origin'}
            or request.headers.get('origin') not in {None, f'{request.url.scheme}://{request.url.netloc}'}):
        raise HTTPException(403, 'Local same-origin access required')
    password = settings.obs_dashboard_password
    if password is None:
        raise HTTPException(503, 'Dashboard access not configured')
    valid_user = credentials is not None and secrets.compare_digest(credentials.username.encode(), b'observer')
    valid_password = credentials is not None and secrets.compare_digest(
        credentials.password.encode(), password.get_secret_value().encode())
    if not (valid_user and valid_password):
        raise HTTPException(401, 'Authentication required',
                            headers={'WWW-Authenticate': 'Basic realm="KnowledgeFlow local"'})


router = APIRouter(prefix='/dashboard', tags=['Local dashboard'], route_class=DashboardRoute,
                   dependencies=[Depends(local_access)])


@router.get('', include_in_schema=False)
def dashboard():
    # Kept outside the public /static mount; no templated secrets.
    return FileResponse(Path(__file__).resolve().parents[1] / 'ui' / 'observability.html')


@router.get('/api/options')
def options():
    return {'operations': {k: sorted(v) for k, v in telemetry.OPERATIONS.items()},
            'modes': ['offline', 'mock', 'live', 'unknown', 'offline_mock']}


@router.get('/api/events')
def events(query: EventFilters = Depends(filters), store=Depends(get_store),
           limit: int = Query(50, ge=1, le=100), after: int = Query(0, ge=0, le=2**63 - 1)):
    return store.events(query, limit=limit, after=after)


@router.get('/api/summary')
def summary(request: Request, query: EventFilters = Depends(filters), store=Depends(get_store)):
    reader = getattr(request.app.state, 'dashboard_reader', None)
    if reader is None or reader.store is not store:
        reader = DashboardReader(store)
        request.app.state.dashboard_reader = reader
    try:
        result = reader.summary(query)
    except QueryTooLarge:
        return JSONResponse({'detail': 'Seleccione un período menor: máximo 50000 eventos.'}, status_code=413)
    return {**result, 'collection': {'enabled': telemetry.observer.enabled,
                                   'dropped_events': telemetry.observer.dropped_events,
                                   'complete_history': False}}


# Same evaluated-quality contract, protected by the independent local access dependency.
router.add_api_route('/api/quality', quality, methods=['GET'])
