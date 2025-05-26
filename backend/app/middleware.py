import time
from collections import defaultdict
from typing import Dict, Tuple

from fastapi import HTTPException, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware for authentication attempts.
    Uses in-memory storage for simplicity.
    """

    # Class variable to store attempts across all instances
    _attempts: Dict[str, list[Tuple[float, bool]]] = defaultdict(list)

    def __init__(self, app, max_attempts: int = 5, window_seconds: int = 300):
        """
        Initialize rate limiting middleware.

        Args:
            app: FastAPI application
            max_attempts: Maximum attempts allowed per window
            window_seconds: Time window in seconds (default: 5 minutes)
        """
        super().__init__(app)
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds

    def _clean_old_attempts(self, ip: str) -> None:
        """Remove attempts older than the time window."""
        current_time = time.time()
        cutoff_time = current_time - self.window_seconds
        RateLimitMiddleware._attempts[ip] = [
            (timestamp, success)
            for timestamp, success in RateLimitMiddleware._attempts[ip]
            if timestamp > cutoff_time
        ]

    def _is_rate_limited(self, ip: str) -> bool:
        """Check if IP is rate limited."""
        self._clean_old_attempts(ip)
        failed_attempts = [
            attempt
            for attempt in RateLimitMiddleware._attempts[ip]
            if not attempt[1]  # success = False
        ]
        return len(failed_attempts) >= self.max_attempts

    def record_attempt(self, ip: str, success: bool) -> None:
        """Record an authentication attempt."""
        current_time = time.time()
        RateLimitMiddleware._attempts[ip].append((current_time, success))
        self._clean_old_attempts(ip)

    @classmethod
    def reset_attempts(cls) -> None:
        """Reset all rate limiting attempts. Useful for testing."""
        cls._attempts.clear()

    async def dispatch(self, request: Request, call_next) -> Response:
        """Process the request and apply rate limiting."""
        client_ip = request.client.host if request.client else "unknown"

        # Check rate limiting for authentication-related endpoints
        # BEFORE processing
        if (
            request.url.path.startswith("/api/")
            and request.url.path
            not in ["/api/users"]  # Exclude user creation endpoint
            and request.headers.get("X-API-Key")
        ):
            if self._is_rate_limited(client_ip):
                raise HTTPException(
                    status_code=429,
                    detail="Too many failed authentication attempts. "
                    "Please try again later.",
                )

        response = await call_next(request)

        # Record authentication attempts based on response status
        # for protected endpoints
        if (
            request.url.path.startswith("/api/")
            and request.url.path
            not in ["/api/users"]  # Exclude user creation endpoint
            and request.headers.get("X-API-Key")
        ):
            # Record success if 200, failure if 401
            if response.status_code == 200:
                self.record_attempt(client_ip, success=True)
            elif response.status_code == 401:
                self.record_attempt(client_ip, success=False)

        return response
