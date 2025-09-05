"""FastAPI middleware for request correlation and timing."""

import time
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable

from .logging import generate_request_id, set_request_context, TimingContext


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to add request correlation and timing to all HTTP requests."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with correlation ID and timing."""
        # Generate request ID
        req_id = generate_request_id()
        
        # Set context
        set_request_context(req_id=req_id, actor="api")
        
        # Add to request state for access in route handlers
        request.state.req_id = req_id
        
        # Time the request
        start_time = time.time()
        
        try:
            response = await call_next(request)
            duration_ms = (time.time() - start_time) * 1000
            
            # Add correlation headers
            response.headers["X-Request-ID"] = req_id
            response.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"
            
            # Log request completion
            import logging
            logger = logging.getLogger("http")
            logger.info(
                f"{request.method} {request.url.path} -> {response.status_code}",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": duration_ms,
                    "user_agent": request.headers.get("user-agent", ""),
                    "remote_addr": request.client.host if request.client else "unknown"
                }
            )
            
            return response
            
        except Exception as exc:
            duration_ms = (time.time() - start_time) * 1000
            
            # Log error
            import logging
            logger = logging.getLogger("http")
            logger.error(
                f"{request.method} {request.url.path} -> ERROR",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": duration_ms,
                    "error": str(exc)
                },
                exc_info=True
            )
            
            raise exc
