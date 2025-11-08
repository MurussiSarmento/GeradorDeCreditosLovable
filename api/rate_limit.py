import time
from typing import Dict, Tuple, Optional
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class RateLimiterMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        # Buckets globais (todas as rotas)
        self.ip_buckets: Dict[str, Tuple[int, float]] = {}
        self.key_buckets: Dict[str, Tuple[int, float]] = {}
        # Buckets dedicados às rotas de proxies
        self.ip_buckets_proxies: Dict[str, Tuple[int, float]] = {}
        self.key_buckets_proxies: Dict[str, Tuple[int, float]] = {}
        # Controle simples de concorrência para rotas de proxies
        self.proxies_inflight: int = 0

    async def dispatch(self, request: Request, call_next):
        settings = request.app.state.settings
        now = time.time()
        minute = 60.0

        client_ip = request.client.host if request.client else "unknown"
        api_key = request.headers.get("x-api-key") or "unknown"

        # Detecta se é rota de proxies
        path = request.url.path
        is_proxies_route = path.startswith("/api/v1/proxies")
        # Seleciona limites: específicos para proxies se definidos, senão globais
        limit_ip = settings.API_RATE_LIMIT_IP
        limit_key = settings.API_RATE_LIMIT_KEY
        if is_proxies_route:
            if settings.PROXIES_RATE_LIMIT_IP is not None:
                limit_ip = settings.PROXIES_RATE_LIMIT_IP
            if settings.PROXIES_RATE_LIMIT_KEY is not None:
                limit_key = settings.PROXIES_RATE_LIMIT_KEY

        # Seleciona buckets conforme a rota
        if is_proxies_route:
            # IP bucket (proxies)
            count, start = self.ip_buckets_proxies.get(client_ip, (0, now))
            if now - start >= minute:
                count, start = 0, now
            count += 1
            self.ip_buckets_proxies[client_ip] = (count, start)
            # Key bucket (proxies)
            kcount, kstart = self.key_buckets_proxies.get(api_key, (0, now))
            if now - kstart >= minute:
                kcount, kstart = 0, now
            kcount += 1
            self.key_buckets_proxies[api_key] = (kcount, kstart)
        else:
            # IP bucket (global)
            count, start = self.ip_buckets.get(client_ip, (0, now))
            if now - start >= minute:
                count, start = 0, now
            count += 1
            self.ip_buckets[client_ip] = (count, start)
            # Key bucket (global)
            kcount, kstart = self.key_buckets.get(api_key, (0, now))
            if now - kstart >= minute:
                kcount, kstart = 0, now
            kcount += 1
            self.key_buckets[api_key] = (kcount, kstart)

        remaining_ip = max(limit_ip - count, 0)
        remaining_key = max(limit_key - kcount, 0)

        if count > limit_ip or kcount > limit_key:
            retry_after = int(minute - (now - min(start, kstart)))
            # Cabeçalhos informativos incluem limites selecionados
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
        # Controle de concorrência para proxies, se definido
        if is_proxies_route and settings.PROXIES_MAX_CONCURRENCY and settings.PROXIES_MAX_CONCURRENCY > 0:
            if self.proxies_inflight >= settings.PROXIES_MAX_CONCURRENCY:
                return Response(
                    status_code=429,
                    headers={
                        "X-Concurrency-Limit-Proxies": str(settings.PROXIES_MAX_CONCURRENCY),
                        "X-RateLimit-Limit-IP": str(limit_ip),
                        "X-RateLimit-Remaining-IP": str(remaining_ip),
                        "X-RateLimit-Limit-Key": str(limit_key),
                        "X-RateLimit-Remaining-Key": str(remaining_key),
                    },
                    content=b"Concurrency limit exceeded",
                )
            self.proxies_inflight += 1
            try:
                response = await call_next(request)
            finally:
                self.proxies_inflight -= 1
        else:
            response = await call_next(request)
        response.headers.update({
            "X-RateLimit-Limit-IP": str(limit_ip),
            "X-RateLimit-Remaining-IP": str(remaining_ip),
            "X-RateLimit-Limit-Key": str(limit_key),
            "X-RateLimit-Remaining-Key": str(remaining_key),
        })
        if is_proxies_route and settings.PROXIES_MAX_CONCURRENCY and settings.PROXIES_MAX_CONCURRENCY > 0:
            response.headers["X-Concurrency-Limit-Proxies"] = str(settings.PROXIES_MAX_CONCURRENCY)
        return response