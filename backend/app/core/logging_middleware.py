import contextvars
import json
import logging
import time
import uuid
from typing import Callable
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.metrics import record_request_metric

# Context variable for correlating logs across async tasks
request_id_ctx: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="")

logger = logging.getLogger("devhire.access")


class StructuredLoggingMiddleware(BaseHTTPMiddleware):
    """
    Production-grade structured observability middleware:
    1. Extracts or generates unique X-Request-ID for distributed tracing.
    2. Measures exact wall-clock request processing duration.
    3. Emits structured JSON access logs with request metadata and timing.
    4. Appends X-Request-ID and X-Process-Time headers to the response.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Correlation ID extraction or generation
        req_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        token = request_id_ctx.set(req_id)

        start_time = time.perf_counter()
        status_code = 500

        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        except Exception:
            raise
        finally:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            record_request_metric(request.method, request.url.path, status_code, duration_ms)
            
            # Append correlation and latency headers if response was generated
            try:
                response.headers["X-Request-ID"] = req_id
                response.headers["X-Process-Time"] = f"{duration_ms}ms"
            except Exception:
                pass

            # Structured JSON log payload
            log_record = {
                "timestamp": time.time(),
                "request_id": req_id,
                "client_ip": request.client.host if request.client else "unknown",
                "method": request.method,
                "path": request.url.path,
                "query_params": str(request.query_params),
                "status_code": status_code,
                "duration_ms": duration_ms
            }

            if status_code >= 500:
                logger.error(json.dumps(log_record))
            elif status_code >= 400:
                logger.warning(json.dumps(log_record))
            else:
                logger.info(json.dumps(log_record))

            request_id_ctx.reset(token)
