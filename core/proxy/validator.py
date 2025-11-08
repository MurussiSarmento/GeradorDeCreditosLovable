import asyncio
from typing import List, Dict, Optional, Tuple
import time
import aiohttp
import json
from core.config import Settings
import os

# Import opcional: em ambientes de testes ou instalação mínima, "aiohttp_socks"
# pode não estar presente. Tornamos o import seguro para evitar erro na
# coleta de testes ao importar módulos que referenciam o validador.
try:
    from aiohttp_socks import ProxyConnector  # type: ignore
except Exception:  # ImportError em instalações sem aiohttp_socks
    ProxyConnector = None  # Fallback: definido em runtime quando necessário


async def _test_url(session: aiohttp.ClientSession, test_url: str, timeout: int) -> Tuple[bool, int, Optional[int]]:
    start = time.time()
    try:
        async with session.get(test_url, timeout=timeout) as resp:
            ok = (resp.status == 200)
            elapsed_ms = int((time.time() - start) * 1000)
            return ok, resp.status, elapsed_ms
    except Exception:
        elapsed_ms = int((time.time() - start) * 1000)
        return False, None, elapsed_ms


def _build_proxy_url(protocol: str, ip: str, port: int, username: Optional[str] = None, password: Optional[str] = None) -> str:
    if username and password:
        return f"{protocol}://{username}:{password}@{ip}:{port}"
    return f"{protocol}://{ip}:{port}"


def _build_session_for_proxy(proxy_url: str) -> aiohttp.ClientSession:
    # Se a dependência opcional não estiver instalada, falhamos aqui de forma
    # explícita e amigável. Isso evita falha no import do módulo e só acusa
    # erro quando de fato tentamos validar via proxy.
    if ProxyConnector is None:
        raise ImportError(
            "Optional dependency 'aiohttp_socks' is not installed. "
            "Install it to enable proxy validation: pip install aiohttp-socks"
        )
    connector = ProxyConnector.from_url(proxy_url)
    return aiohttp.ClientSession(connector=connector)


async def _detect_anonymity(session: aiohttp.ClientSession, timeout: int) -> Optional[str]:
    # Heurística via httpbin: examina cabeçalhos para inferir anonimato.
    # Modo 'basic' mantém comportamento atual; 'enhanced' verifica mais cabeçalhos comuns de proxies.
    try:
        async with session.get("https://httpbin.org/get", timeout=timeout) as resp:
            if resp.status != 200:
                return None
            data = await resp.json(content_type=None)
            headers = data.get("headers", {})
            # Normaliza chaves para lookup case-insensitive
            norm = {k.title(): v for k, v in headers.items()}
            xff = norm.get("X-Forwarded-For")
            via = norm.get("Via")
            mode = os.getenv("ANONYMITY_DETECTION_MODE", "basic").strip().lower()
            if mode not in ("basic", "enhanced"):
                mode = "basic"
            if mode == "basic":
                if xff:
                    return "transparent"
                if via:
                    return "anonymous"
                return "elite"
            # enhanced: considerar cabeçalhos adicionais
            forwarded = norm.get("Forwarded")
            x_real_ip = norm.get("X-Real-Ip")
            proxy_conn = norm.get("Proxy-Connection")
            # Classificação:
            # - Transparent: expõe IP do cliente ou encaminhamento explícito
            if xff or forwarded or x_real_ip:
                return "transparent"
            # - Anonymous: oculta IP mas evidencia presença de proxy (Via/Proxy-Connection)
            if via or proxy_conn:
                return "anonymous"
            # - Elite: não expõe nenhum cabeçalho típico de proxy
            return "elite"
    except Exception:
        return None


async def _detect_geolocation(ip: str, timeout: int) -> Optional[Dict]:
    # Suporta provedores: ip-api (default), ipapi, ipinfo. Tenta fallback se falhar.
    provider_order = [
        os.getenv("GEO_PROVIDER", "ip-api").strip().lower(),
        # fallback chain
        "ipapi",
        "ipinfo",
    ]
    # Remover duplicados mantendo ordem
    seen = set()
    providers = []
    for p in provider_order:
        if p not in seen:
            providers.append(p)
            seen.add(p)
    try:
        async with aiohttp.ClientSession() as session:
            for prov in providers:
                try:
                    if prov == "ip-api":
                        url = f"http://ip-api.com/json/{ip}?fields=status,countryCode"
                        async with session.get(url, timeout=timeout) as resp:
                            if resp.status != 200:
                                continue
                            data = await resp.json(content_type=None)
                            if data.get("status") == "success":
                                code = data.get("countryCode")
                                return {"country": code}
                    elif prov == "ipapi":
                        url = f"https://ipapi.co/{ip}/json/"
                        async with session.get(url, timeout=timeout) as resp:
                            if resp.status != 200:
                                continue
                            data = await resp.json(content_type=None)
                            code = data.get("country_code") or data.get("country")
                            if code:
                                return {"country": str(code).upper()}
                    elif prov == "ipinfo":
                        url = f"https://ipinfo.io/{ip}/json"
                        async with session.get(url, timeout=timeout) as resp:
                            if resp.status != 200:
                                continue
                            data = await resp.json(content_type=None)
                            code = data.get("country")
                            if code:
                                return {"country": str(code).upper()}
                except Exception:
                    # tenta próximo provedor
                    continue
    except Exception:
        return None
    return None


async def validate_proxy(
    proxy_item: Dict,
    test_urls: List[str],
    timeout: int = 10,
    test_all_urls: bool = True,
    check_anonymity: bool = False,
    check_geolocation: bool = False,
) -> Dict:
    protocol = proxy_item.get("protocol", "http")
    ip = proxy_item.get("ip")
    port = proxy_item.get("port")
    username = proxy_item.get("username")
    password = proxy_item.get("password")
    proxy_url = _build_proxy_url(protocol, ip, port, username, password)

    results: Dict[str, Dict] = {}
    # Roteia todo tráfego via proxy (HTTP/HTTPS/SOCKS) usando ProxyConnector
    async with _build_session_for_proxy(proxy_url) as session:
        tasks = [_test_url(session, url, timeout) for url in test_urls]
        url_results = await asyncio.gather(*tasks, return_exceptions=True)
        valid_count = 0
        total_ms: List[int] = []
        for url, res in zip(test_urls, url_results):
            if isinstance(res, Exception):
                results[url] = {"success": False, "status_code": None, "response_time_ms": None}
                continue
            success, status_code, elapsed_ms = res
            total_ms.append(elapsed_ms or 0)
            if success:
                valid_count += 1
            results[url] = {
                "success": success,
                "status_code": status_code,
                "response_time_ms": elapsed_ms,
            }

        anonymity_val: Optional[str] = None
        geo_val: Optional[Dict] = None
        if check_anonymity:
            anonymity_val = await _detect_anonymity(session, timeout)
        if check_geolocation:
            geo_val = await _detect_geolocation(ip, timeout)

    if test_all_urls:
        valid = (valid_count == len(test_urls))
    else:
        valid = (valid_count >= 1)
    avg_ms = int(sum(total_ms) / max(len(total_ms), 1)) if total_ms else None
    return {
        "proxy": f"{ip}:{port}",
        "valid": valid,
        "protocol": protocol,
        "anonymity": anonymity_val,
        "avg_response_time_ms": avg_ms,
        "test_results": results,
        "geolocation": geo_val,
    }