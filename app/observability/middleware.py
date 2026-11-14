"""Pure ASGI middleware: preserve request/response bodies and context propagation."""
from app.observability import telemetry


class ObservabilityMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if (scope['type'] != 'http' or scope.get('path') != '/api/agent'
                or not telemetry.observer.enabled):
            return await self.app(scope, receive, send)

        with telemetry.span('http', 'agent') as active:
            status = 500

            async def traced_send(message):
                nonlocal status
                if message['type'] == 'http.response.start':
                    status = message['status']
                    # Never read incoming IDs, headers, body, query string or client IP.
                    headers = [(k, v) for k, v in message.get('headers', [])
                               if k.lower() != b'x-trace-id']
                    if isinstance(active, telemetry.Span):
                        headers.append((b'x-trace-id', active.trace.trace_id.encode('ascii')))
                    message = {**message, 'headers': headers}
                await send(message)

            try:
                await self.app(scope, receive, traced_send)
            finally:
                active.set_attributes(http_status=status)
                if status >= 400:
                    active.status = 'error'
                    active.error = 'http_client_error' if status < 500 else 'http_server_error'
