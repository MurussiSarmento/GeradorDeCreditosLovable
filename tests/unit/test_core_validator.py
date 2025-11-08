import sys
import types
import pytest


def setup_module(module=None):
    # Stub para evitar erro de import de aiohttp_socks
    if "aiohttp_socks" not in sys.modules:
        sys.modules["aiohttp_socks"] = types.SimpleNamespace(ProxyConnector=types.SimpleNamespace(from_url=lambda url: None))


class FakeResp:
    def __init__(self, status=200, json_data=None):
        self.status = status
        self._json = json_data or {"headers": {}}

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def json(self, content_type=None):
        return self._json


class FakeSession:
    def __init__(self, url_status_map=None):
        # Mapear URL -> status
        self.url_status_map = url_status_map or {}

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    def get(self, url, timeout=10):
        # Retorna 200 por padrão; se url estiver no mapa, usar status customizado
        status = self.url_status_map.get(url, 200)
        # Para httpbin anonimato, retornar headers adequados
        if "httpbin.org/get" in url:
            # headers sem XFF/Via => elite
            return FakeResp(status=200, json_data={"headers": {}})
        return FakeResp(status=status)


@pytest.mark.asyncio
async def test_build_proxy_url():
    from core.proxy.validator import _build_proxy_url
    assert _build_proxy_url("http", "1.2.3.4", 8080) == "http://1.2.3.4:8080"
    assert _build_proxy_url("http", "1.2.3.4", 8080, "u", "p") == "http://u:p@1.2.3.4:8080"


@pytest.mark.asyncio
async def test_validate_proxy_all_success(monkeypatch):
    from core.proxy import validator

    # Substituir criação de sessão por fake
    monkeypatch.setattr(validator, "_build_session_for_proxy", lambda proxy_url: FakeSession())
    # Evitar rede na geolocalização/anonimato
    async def fake_detect_anonymity(session, timeout):
        return "elite"
    async def fake_detect_geolocation(ip, timeout):
        return {"country": "US"}
    monkeypatch.setattr(validator, "_detect_anonymity", fake_detect_anonymity)
    monkeypatch.setattr(validator, "_detect_geolocation", fake_detect_geolocation)

    proxy = {"ip": "1.2.3.4", "port": 8080, "protocol": "http"}
    res = await validator.validate_proxy(proxy, ["http://example.com","http://example.org"], timeout=1, test_all_urls=True, check_anonymity=True, check_geolocation=True)
    assert res["valid"] is True
    assert res["protocol"] == "http"
    assert res["anonymity"] == "elite"
    assert res["geolocation"]["country"] == "US"
    assert isinstance(res["avg_response_time_ms"], int)
    assert all(v["success"] for v in res["test_results"].values())


@pytest.mark.asyncio
async def test_validate_proxy_partial_success(monkeypatch):
    from core.proxy import validator

    # Configurar uma sessão que retorna falha para a segunda URL
    bad_map = {"http://example.org": 500}
    monkeypatch.setattr(validator, "_build_session_for_proxy", lambda proxy_url: FakeSession(url_status_map=bad_map))
    # Sem anonimato/geo
    proxy = {"ip": "2.2.2.2", "port": 3128, "protocol": "http"}
    # Quando test_all_urls=False, deve ser válido
    res_ok = await validator.validate_proxy(proxy, ["http://example.com","http://example.org"], timeout=1, test_all_urls=False)
    assert res_ok["valid"] is True
    # Quando test_all_urls=True, deve ser inválido
    res_bad = await validator.validate_proxy(proxy, ["http://example.com","http://example.org"], timeout=1, test_all_urls=True)
    assert res_bad["valid"] is False