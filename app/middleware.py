import time
from uuid import uuid4

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from logging_config import ContextLogger

# Prometheus scrapes this path every few seconds; skip access-style logs for it.
_SKIP_ACCESS_LOG_PATHS = {"/metrics"}


def _response_size_bytes(response) -> int:
    content_length = response.headers.get("content-length")
    if content_length:
        try:
            return int(content_length)
        except ValueError:
            pass
    body = getattr(response, "body", None)
    if body is not None:
        return len(body)
    return 0


class LoggingMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, logger):
        super().__init__(app)
        self.logger = logger

    async def dispatch(self, request: Request, call_next):
        start_time = time.perf_counter()
        trace_id = request.headers.get("X-Trace-ID") or str(uuid4())
        request_id = request.headers.get("X-Request-ID") or str(uuid4())
        request.state.trace_id = trace_id
        request.state.request_id = request_id

        context = {
            "trace_id": trace_id,
            "request_id": request_id,
            "user_id": request.headers.get("X-User-Id", "anonymous"),
            "endpoint": request.url.path,
            "method": request.method,
            "client_ip": request.client.host if request.client else None,
            "user_agent": request.headers.get("User-Agent"),
        }
        request.state.logger = ContextLogger(self.logger, context)

        skip_access_log = request.url.path in _SKIP_ACCESS_LOG_PATHS
        if not skip_access_log:
            request.state.logger.info(
                "Incoming request",
                extra={"path": request.url.path, "query": str(request.query_params)},
            )

        try:
            response = await call_next(request)
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            if not skip_access_log:
                request.state.logger.info(
                    "Request finished",
                    extra={
                        "status_code": response.status_code,
                        "duration_ms": duration_ms,
                        "size_bytes": _response_size_bytes(response),
                    },
                )
        except Exception:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            request.state.logger.error(
                "Request failed",
                extra={"duration_ms": duration_ms, "status_code": 500},
                exc_info=True,
            )
            response = Response(content="Internal Server Error", status_code=500)

        response.headers["X-Trace-ID"] = trace_id
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time"] = str(duration_ms)
        return response
