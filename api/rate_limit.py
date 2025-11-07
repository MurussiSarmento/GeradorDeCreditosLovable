import time
from typing import Dict, Tuple, Optional
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class RateLimiterMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.ip_buckets: Dict[str, Tuple[int, float]] = {}
        self.key_buckets: Dict[str, Tuple[int, float]] = {}

    async def dispatch(self, request: Request, call_next):
        settings = request.app.state.settings
        now = time.time()
        minute = 60.0

        client_ip = request.client.host if request.client else "unknown"
        api_key = request.headers.get("x-api-key") or "unknown"

        limit_ip = settings.API_RATE_LIMIT_IP
        limit_key = settings.API_RATE_LIMIT_KEY

        # IP bucket
        count, start = self.ip_buckets.get(client_ip, (0, now))
        if now - start >= minute:
            count, start = 0, now
        count += 1
        self.ip_buckets[client_ip] = (count, start)

        # Key bucket
        kcount, kstart = self.key_buckets.get(api_key, (0, now))
        if now - kstart >= minute:
            kcount, kstart = 0, now
        kcount += 1
        self.key_buckets[api_key] = (kcount, kstart)

        remaining_ip = max(limit_ip - count, 0)
        remaining_key = max(limit_key - kcount, 0)

        if count > limit_ip or kcount > limit_key:
            retry_after = int(minute - (now - min(start, kstart)))
            return Response(
                status_code=429,
                headers={
                    "X-RateLimit-Limit-IP": str(limit_ip),
                    "X-RateLimit-Remaining-IP": str(remaining_ip),
                    "X-RateLimit-Limit-Key": str(limit_key),
                    "X-RateLimit-Remaining-Key": str(remaining_key),
                    "Retry-After": str(retry_after),
                },
                content=b"Rate limit exceeded",
            )

        response = await call_next(request)
        response.headers.update({
            "X-RateLimit-Limit-IP": str(limit_ip),
            "X-RateLimit-Remaining-IP": str(remaining_ip),
            "X-RateLimit-Limit-Key": str(limit_key),
            "X-RateLimit-Remaining-Key": str(remaining_key),
        })
        return response