import os
import time
import sys
import types
import pytest
from fastapi.testclient import TestClient


# Configuração de ambiente para testes de API
def setup_module(module=None):
    os.environ["API_KEY"] = "test-key"
    os.environ["API_RATE_LIMIT_IP"] = "1000"
    os.environ["API_RATE_LIMIT_KEY"] = "1000"
    db_path = os.path.join("data", "test_proxies.db")
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"
    try:
        if os.path.exists(db_path):
            os.remove(db_path)
    except Exception:
        pass
    # Evitar erro de import de aiohttp_socks em validator
    if "aiohttp_socks" not in sys.modules:
        sys.modules["aiohttp_socks"] = types.SimpleNamespace(ProxyConnector=None)


HEADERS = {"x-api-key": "test-key"}


def get_client() -> TestClient:
    from api.app import create_app
    return TestClient(create_app())


def test_import_and_list_proxies():
    client = get_client()
    payload = {
        "proxies": [
            "http://1.2.3.4:8080",
            "2.2.2.2:3128",
        ],
        "auto_validate": False,
        "validation_urls": [],
    }
    r = client.post("/api/v1/proxies/import", json=payload, headers=HEADERS)
    assert r.status_code == 200
    data = r.json()
    assert data["success"] is True
    assert data["imported"] >= 2

    r2 = client.get("/api/v1/proxies?page=1&per_page=10", headers=HEADERS)
    assert r2.status_code == 200
    d2 = r2.json()
    assert d2["total"] >= 2
    assert len(d2["proxies"]) >= 2

    # Filtro por protocolo
    r3 = client.get("/api/v1/proxies?protocol=http", headers=HEADERS)
    assert r3.status_code == 200
    d3 = r3.json()
    assert d3["total"] >= 1


def test_random_proxy_returns_item(monkeypatch):
    client = get_client()
    # Tornar um proxy válido via endpoint de validação
    async def fake_validate_proxy(pdict, *args, **kwargs):
        return {
            "proxy": f"{pdict.get('ip')}:{pdict.get('port')}",
            "valid": True,
            "protocol": pdict.get("protocol"),
            "anonymity": "anonymous",
            "avg_response_time_ms": 50,
            "test_results": {},
        }

    # Patchar o símbolo utilizado dentro do router
    monkeypatch.setattr("api.routers.proxies.validate_proxy", fake_validate_proxy)
    client.post(
        "/api/v1/proxies/validate",
        json={
            "proxies": ["1.2.3.4:8080"],
            "test_urls": ["http://example.com"],
            "timeout": 1,
            "test_all_urls": False,
            "check_anonymity": False,
            "check_geolocation": False,
            "concurrent_tests": 1,
        },
        headers=HEADERS,
    )

    r = client.get("/api/v1/proxies/random?protocol=http", headers=HEADERS)
    assert r.status_code == 200
    jd = r.json()
    assert "proxy" in jd
    assert jd["protocol"] == "http"


def test_schedule_validate_returns_polling_url(monkeypatch):
    client = get_client()

    async def fake_validate_proxy(pdict, *args, **kwargs):
        return {
            "proxy": f"{pdict.get('ip')}:{pdict.get('port')}",
            "valid": True,
            "protocol": pdict.get("protocol"),
            "anonymity": "anonymous",
            "avg_response_time_ms": 10,
            "test_results": {},
        }

    monkeypatch.setattr("api.routers.proxies.validate_proxy", fake_validate_proxy)

    payload = {
        "type": "validate",
        "proxies": ["9.9.9.9:8080"],
        "test_urls": ["http://example.com"],
        "timeout": 1,
        "test_all_urls": False,
        "check_anonymity": False,
        "check_geolocation": False,
        "concurrent_tests": 1,
    }
    r = client.post("/api/v1/proxies/schedule", json=payload, headers=HEADERS)
    assert r.status_code == 200
    jr = r.json()
    assert "polling_url" in jr
    assert jr["polling_url"].startswith("/jobs/")
    job_id = jr["job_id"]

    s = client.get(jr["polling_url"], headers=HEADERS)
    assert s.status_code == 200
    js = s.json()
    assert js["job_id"] == job_id


def test_list_proxies_combined_filters_valid_and_protocol(monkeypatch):
    client = get_client()

    # Importar dois proxies, um http e um https
    payload = {
        "proxies": [
            "1.1.1.1:8080",  # será tratado como http
            "https://2.2.2.2:3128",
        ],
        "auto_validate": False,
        "validation_urls": [],
    }
    r = client.post("/api/v1/proxies/import", json=payload, headers=HEADERS)
    assert r.status_code == 200

    # Validar apenas o http para marcar como válido
    async def fake_validate_proxy(pdict, *args, **kwargs):
        return {
            "proxy": f"{pdict.get('ip')}:{pdict.get('port')}",
            "valid": pdict.get("protocol") == "http",
            "protocol": pdict.get("protocol"),
            "anonymity": "anonymous",
            "avg_response_time_ms": 30,
            "test_results": {},
        }

    monkeypatch.setattr("api.routers.proxies.validate_proxy", fake_validate_proxy)

    client.post(
        "/api/v1/proxies/validate",
        json={
            "proxies": [
                "1.1.1.1:8080",
                "https://2.2.2.2:3128",
            ],
            "test_urls": ["http://example.com"],
            "timeout": 1,
            "test_all_urls": False,
            "check_anonymity": False,
            "check_geolocation": False,
            "concurrent_tests": 2,
        },
        headers=HEADERS,
    )

    # Listar apenas válidos e protocolo http
    rlist = client.get("/api/v1/proxies?valid_only=true&protocol=http", headers=HEADERS)
    assert rlist.status_code == 200
    dlist = rlist.json()
    assert dlist["total"] >= 1
    assert all(p["protocol"] == "http" for p in dlist["proxies"])  # só http


def test_random_proxy_combined_filters_protocol_and_max_response_time(monkeypatch):
    client = get_client()

    # Garantir pelo menos um proxy http válido e com baixa latência
    async def fake_validate_proxy(pdict, *args, **kwargs):
        return {
            "proxy": f"{pdict.get('ip')}:{pdict.get('port')}",
            "valid": True,
            "protocol": pdict.get("protocol"),
            "anonymity": "anonymous",
            "avg_response_time_ms": 25,
            "test_results": {},
        }

    monkeypatch.setattr("api.routers.proxies.validate_proxy", fake_validate_proxy)
    client.post(
        "/api/v1/proxies/validate",
        json={
            "proxies": [
                "3.3.3.3:8080",
            ],
            "test_urls": ["http://example.com"],
            "timeout": 1,
            "test_all_urls": False,
            "check_anonymity": False,
            "check_geolocation": False,
            "concurrent_tests": 1,
        },
        headers=HEADERS,
    )

    r = client.get("/api/v1/proxies/random?protocol=http&max_response_time=40", headers=HEADERS)
    assert r.status_code == 200
    jd = r.json()
    assert jd["protocol"] == "http"
    assert (jd.get("avg_response_time_ms") or 0) <= 40


def test_list_ordering_by_latency_and_last_checked(monkeypatch):
    client = get_client()
    # Isolar estado entre testes
    client.delete("/api/v1/proxies", headers=HEADERS)

    # Importar dois proxies
    payload = {
        "proxies": [
            "10.10.10.10:8000",  # http
            "http://10.10.10.11:8001",  # http
        ],
        "auto_validate": False,
        "validation_urls": [],
    }
    r = client.post("/api/v1/proxies/import", json=payload, headers=HEADERS)
    assert r.status_code == 200

    # Validar ambos com latências distintas e last_checked setado
    async def fake_validate_proxy(pdict, *args, **kwargs):
        # Diferenciar latências por porta
        latency = 100 if pdict.get("port") == 8000 else 50
        return {
            "proxy": f"{pdict.get('ip')}:{pdict.get('port')}",
            "valid": True,
            "protocol": pdict.get("protocol"),
            "anonymity": "anonymous",
            "avg_response_time_ms": latency,
            "test_results": {},
        }

    monkeypatch.setattr("api.routers.proxies.validate_proxy", fake_validate_proxy)
    client.post(
        "/api/v1/proxies/validate",
        json={
            "proxies": [
                "10.10.10.10:8000",
                "10.10.10.11:8001",
            ],
            "test_urls": ["http://example.com"],
            "timeout": 1,
            "test_all_urls": False,
            "check_anonymity": False,
            "check_geolocation": False,
            "concurrent_tests": 2,
        },
        headers=HEADERS,
    )

    # Ordenar por avg_response_time_ms asc: menor latência primeiro (8001)
    rlist_asc = client.get("/api/v1/proxies?order_by=avg_response_time_ms&order=asc", headers=HEADERS)
    assert rlist_asc.status_code == 200
    d_asc = rlist_asc.json()
    assert d_asc["total"] >= 2
    assert d_asc["proxies"][0]["port"] == 8001

    # Ordenar por avg_response_time_ms desc: maior latência primeiro (8000)
    rlist_desc = client.get("/api/v1/proxies?order_by=avg_response_time_ms&order=desc", headers=HEADERS)
    assert rlist_desc.status_code == 200
    d_desc = rlist_desc.json()
    assert d_desc["total"] >= 2
    assert d_desc["proxies"][0]["port"] == 8000

    # Ordenar por last_checked desc deve ter valores definidos e ordenáveis
    rlist_last = client.get("/api/v1/proxies?order_by=last_checked&order=desc", headers=HEADERS)
    assert rlist_last.status_code == 200
    d_last = rlist_last.json()
    assert d_last["total"] >= 2
    # last_checked deve existir ao menos para os validados
    assert any(p.get("last_checked") for p in d_last["proxies"])  


def test_delete_invalid_only(monkeypatch):
    client = get_client()

    # Importar três proxies
    payload = {
        "proxies": [
            "20.20.20.20:9000",
            "20.20.20.21:9001",
            "20.20.20.22:9002",
        ],
        "auto_validate": False,
        "validation_urls": [],
    }
    r = client.post("/api/v1/proxies/import", json=payload, headers=HEADERS)
    assert r.status_code == 200

    # Validar: marcar dois inválidos e um válido
    async def fake_validate_proxy(pdict, *args, **kwargs):
        port = pdict.get("port")
        return {
            "proxy": f"{pdict.get('ip')}:{port}",
            "valid": port == 9002,  # apenas 9002 válido
            "protocol": pdict.get("protocol"),
            "anonymity": "anonymous",
            "avg_response_time_ms": 40,
            "test_results": {},
        }

    monkeypatch.setattr("api.routers.proxies.validate_proxy", fake_validate_proxy)
    client.post(
        "/api/v1/proxies/validate",
        json={
            "proxies": [
                "20.20.20.20:9000",
                "20.20.20.21:9001",
                "20.20.20.22:9002",
            ],
            "test_urls": ["http://example.com"],
            "timeout": 1,
            "test_all_urls": False,
            "check_anonymity": False,
            "check_geolocation": False,
            "concurrent_tests": 3,
        },
        headers=HEADERS,
    )

    # Antes do delete, contar total
    before = client.get("/api/v1/proxies", headers=HEADERS).json()["total"]
    assert before >= 3

    # Delete apenas inválidos
    rdel = client.delete("/api/v1/proxies?invalid_only=true", headers=HEADERS)
    assert rdel.status_code == 200
    jd = rdel.json()
    assert jd["success"] is True
    assert jd["deleted_count"] >= 2

    # Após delete, total deve ser reduzido
    after = client.get("/api/v1/proxies", headers=HEADERS).json()["total"]
    assert after == before - jd["deleted_count"]


def test_schedule_scrape_returns_polling_url(monkeypatch):
    client = get_client()

    async def fake_scrape_from_sources(country, protocols, sources, quantity, timeout=10, retries=2):
        return []

    monkeypatch.setattr("api.routers.proxies.scrape_from_sources", fake_scrape_from_sources)

    payload = {
        "type": "scrape",
        "quantity": 1,
        "protocols": ["http"],
        "sources": ["fake"],
        "scrape_timeout": 1,
        "scrape_retries": 0,
    }
    r = client.post("/api/v1/proxies/schedule", json=payload, headers=HEADERS)
    assert r.status_code == 200
    jr = r.json()
    assert "polling_url" in jr
    assert jr["polling_url"].startswith("/jobs/")
    job_id = jr["job_id"]

    s = client.get(jr["polling_url"], headers=HEADERS)
    assert s.status_code == 200
    js = s.json()
    assert js["job_id"] == job_id


def test_validate_with_monkeypatch(monkeypatch):
    client = get_client()

    async def fake_validate_proxy(pdict, test_urls, timeout=None, test_all_urls=False, check_anonymity=False, check_geolocation=False):
        return {
            "proxy": f"{pdict.get('ip')}:{pdict.get('port')}",
            "valid": pdict.get("port") == 8080,
            "protocol": pdict.get("protocol"),
            "anonymity": "anonymous",
            "avg_response_time_ms": 123,
            "test_results": {test_urls[0] if test_urls else "http://example.com": {"status_code": 200, "response_time_ms": 123}},
            "geolocation": {"country": "US"} if check_geolocation else None,
        }

    monkeypatch.setattr("api.routers.proxies.validate_proxy", fake_validate_proxy)

    payload = {
        "proxies": [
            "1.2.3.4:8080",
            "2.2.2.2:3128",
        ],
        "test_urls": ["http://example.com"],
        "timeout": 1,
        "test_all_urls": False,
        "check_anonymity": False,
        "check_geolocation": True,
        "concurrent_tests": 2,
    }
    r = client.post("/api/v1/proxies/validate", json=payload, headers=HEADERS)
    assert r.status_code == 200
    res = r.json()
    assert res["total_tested"] == 2
    assert res["valid_proxies"] == 1
    assert res["invalid_proxies"] == 1


def test_stats_endpoint():
    client = get_client()
    r = client.get("/api/v1/proxies/stats", headers=HEADERS)
    assert r.status_code == 200
    j = r.json()
    # Chaves esperadas básicas
    assert "total" in j
    assert "valid" in j
    assert "invalid" in j


def test_list_pagination_total_pages_and_items():
    client = get_client()
    # Resetar estado
    client.delete("/api/v1/proxies", headers=HEADERS)

    # Importar 7 proxies para testar paginação
    payload = {
        "proxies": [
            "http://100.0.0.1:8000",
            "http://100.0.0.2:8001",
            "http://100.0.0.3:8002",
            "http://100.0.0.4:8003",
            "http://100.0.0.5:8004",
            "http://100.0.0.6:8005",
            "http://100.0.0.7:8006",
        ],
        "auto_validate": False,
        "validation_urls": [],
    }
    r = client.post("/api/v1/proxies/import", json=payload, headers=HEADERS)
    assert r.status_code == 200

    # Página 1, per_page=3
    r1 = client.get("/api/v1/proxies?page=1&per_page=3", headers=HEADERS)
    assert r1.status_code == 200
    d1 = r1.json()
    assert d1["total"] >= 7
    assert d1["per_page"] == 3
    assert d1["page"] == 1
    assert d1["total_pages"] >= 3
    assert len(d1["proxies"]) == 3

    # Página 2, per_page=3
    r2 = client.get("/api/v1/proxies?page=2&per_page=3", headers=HEADERS)
    assert r2.status_code == 200
    d2 = r2.json()
    assert d2["page"] == 2
    assert len(d2["proxies"]) == 3

    # Página 3, per_page=3 — deve ter 1 item
    r3 = client.get("/api/v1/proxies?page=3&per_page=3", headers=HEADERS)
    assert r3.status_code == 200
    d3 = r3.json()
    assert d3["page"] == 3
    assert len(d3["proxies"]) >= 1


def test_list_filters_valid_only_and_country(monkeypatch):
    client = get_client()
    # Resetar estado
    client.delete("/api/v1/proxies", headers=HEADERS)

    # Importar dois proxies
    payload = {
        "proxies": [
            "1.1.1.1:8080",  # http
            "2.2.2.2:8080",  # http
        ],
        "auto_validate": False,
        "validation_urls": [],
    }
    r = client.post("/api/v1/proxies/import", json=payload, headers=HEADERS)
    assert r.status_code == 200

    # Validar com geolocalização: um válido US, outro inválido BR
    async def fake_validate_proxy(pdict, *args, **kwargs):
        ip = pdict.get("ip")
        is_valid = ip == "1.1.1.1"
        return {
            "proxy": f"{ip}:{pdict.get('port')}",
            "valid": is_valid,
            "protocol": pdict.get("protocol"),
            "anonymity": "anonymous",
            "avg_response_time_ms": 35,
            "test_results": {},
            "geolocation": {"country": "US" if is_valid else "BR"},
        }

    monkeypatch.setattr("api.routers.proxies.validate_proxy", fake_validate_proxy)

    client.post(
        "/api/v1/proxies/validate",
        json={
            "proxies": [
                "1.1.1.1:8080",
                "2.2.2.2:8080",
            ],
            "test_urls": ["http://example.com"],
            "timeout": 1,
            "test_all_urls": False,
            "check_anonymity": False,
            "check_geolocation": True,
            "concurrent_tests": 2,
        },
        headers=HEADERS,
    )

    # Listar apenas válidos no país US
    rlist = client.get("/api/v1/proxies?valid_only=true&country=US", headers=HEADERS)
    assert rlist.status_code == 200
    dlist = rlist.json()
    assert dlist["total"] >= 1
    assert all((p.get("country") or "") == "US" for p in dlist["proxies"])  # apenas US


def test_stats_detailed_aggregations(monkeypatch):
    client = get_client()
    # Resetar estado
    client.delete("/api/v1/proxies", headers=HEADERS)

    # Importar três proxies com protocolos distintos
    payload = {
        "proxies": [
            "http://11.11.11.11:8111",
            "https://12.12.12.12:8112",
            "socks4://13.13.13.13:8113",
        ],
        "auto_validate": False,
        "validation_urls": [],
    }
    r = client.post("/api/v1/proxies/import", json=payload, headers=HEADERS)
    assert r.status_code == 200

    # Validar: http US (40ms), https US (60ms), socks4 BR inválido
    async def fake_validate_proxy(pdict, *args, **kwargs):
        proto = pdict.get("protocol")
        ip = pdict.get("ip")
        if proto == "http":
            return {
                "proxy": f"{ip}:{pdict.get('port')}",
                "valid": True,
                "protocol": proto,
                "anonymity": "anonymous",
                "avg_response_time_ms": 40,
                "test_results": {},
                "geolocation": {"country": "US"},
            }
        if proto == "https":
            return {
                "proxy": f"{ip}:{pdict.get('port')}",
                "valid": True,
                "protocol": proto,
                "anonymity": "anonymous",
                "avg_response_time_ms": 60,
                "test_results": {},
                "geolocation": {"country": "US"},
            }
        # socks4 inválido BR
        return {
            "proxy": f"{ip}:{pdict.get('port')}",
            "valid": False,
            "protocol": proto,
            "anonymity": "anonymous",
            "avg_response_time_ms": 90,
            "test_results": {},
            "geolocation": {"country": "BR"},
        }

    monkeypatch.setattr("api.routers.proxies.validate_proxy", fake_validate_proxy)

    client.post(
        "/api/v1/proxies/validate",
        json={
            "proxies": [
                "http://11.11.11.11:8111",
                "https://12.12.12.12:8112",
                "socks4://13.13.13.13:8113",
            ],
            "test_urls": ["http://example.com"],
            "timeout": 1,
            "test_all_urls": False,
            "check_anonymity": False,
            "check_geolocation": True,
            "concurrent_tests": 3,
        },
        headers=HEADERS,
    )

    # Consultar /stats e validar agregações
    rstats = client.get("/api/v1/proxies/stats", headers=HEADERS)
    assert rstats.status_code == 200
    s = rstats.json()
    assert s["total"] >= 3
    assert s["valid"] >= 2
    assert s["invalid"] >= 1
    # by_protocol deve conter http, https, socks4
    assert s["by_protocol"].get("http", 0) >= 1
    assert s["by_protocol"].get("https", 0) >= 1
    assert s["by_protocol"].get("socks4", 0) >= 1
    # by_country deve conter US e BR
    countries = { (item.get("country") or ""): int(item.get("count") or 0) for item in s.get("by_country", []) }
    assert countries.get("US", 0) >= 2
    assert countries.get("BR", 0) >= 1
    # avg_response_time_ms deve ser a média dos válidos (40 e 60 => 50)
    assert s.get("avg_response_time_ms") in (50, 49, 51)  # tolerância de arredondamento


def test_list_pagination_exact_total_pages():
    client = get_client()
    # Resetar estado
    client.delete("/api/v1/proxies", headers=HEADERS)

    # Importar 6 proxies
    payload = {
        "proxies": [
            "http://200.0.0.1:7000",
            "http://200.0.0.2:7001",
            "http://200.0.0.3:7002",
            "http://200.0.0.4:7003",
            "http://200.0.0.5:7004",
            "http://200.0.0.6:7005",
        ],
        "auto_validate": False,
        "validation_urls": [],
    }
    r = client.post("/api/v1/proxies/import", json=payload, headers=HEADERS)
    assert r.status_code == 200

    # per_page=3, total_pages deve ser exatamente 2
    r1 = client.get("/api/v1/proxies?page=1&per_page=3", headers=HEADERS)
    assert r1.status_code == 200
    d1 = r1.json()
    assert d1["total"] >= 6
    assert d1["per_page"] == 3
    assert d1["total_pages"] == ((d1["total"] // 3) + (1 if d1["total"] % 3 else 0))
    assert d1["total_pages"] == 2
    assert len(d1["proxies"]) == 3

    r2 = client.get("/api/v1/proxies?page=2&per_page=3", headers=HEADERS)
    assert r2.status_code == 200
    d2 = r2.json()
    assert d2["page"] == 2
    assert len(d2["proxies"]) == 3

    r3 = client.get("/api/v1/proxies?page=3&per_page=3", headers=HEADERS)
    assert r3.status_code == 200
    d3 = r3.json()
    assert d3["page"] == 3
    assert len(d3["proxies"]) == 0


def test_list_ordering_by_created_at_asc_desc():
    client = get_client()
    # Resetar estado
    client.delete("/api/v1/proxies", headers=HEADERS)

    # Importar primeiro proxy
    r1 = client.post(
        "/api/v1/proxies/import",
        json={"proxies": ["http://210.0.0.1:7100"], "auto_validate": False, "validation_urls": []},
        headers=HEADERS,
    )
    assert r1.status_code == 200
    # Importar segundo proxy
    r2 = client.post(
        "/api/v1/proxies/import",
        json={"proxies": ["http://210.0.0.2:7101"], "auto_validate": False, "validation_urls": []},
        headers=HEADERS,
    )
    assert r2.status_code == 200

    # Ascendente: primeiro importado vem primeiro
    rasc = client.get("/api/v1/proxies?order_by=created_at&order=asc", headers=HEADERS)
    assert rasc.status_code == 200
    dasc = rasc.json()
    assert dasc["total"] >= 2
    first_ports = [p["port"] for p in dasc["proxies"][:2]]
    assert 7100 in first_ports  # o criado primeiro deve aparecer antes ou entre os primeiros itens

    # Descendente: último importado vem primeiro
    rdesc = client.get("/api/v1/proxies?order_by=created_at&order=desc", headers=HEADERS)
    assert rdesc.status_code == 200
    ddesc = rdesc.json()
    assert ddesc["total"] >= 2
    first_ports_desc = [p["port"] for p in ddesc["proxies"][:2]]
    assert 7101 in first_ports_desc


def test_random_proxy_not_found_returns_404(monkeypatch):
    client = get_client()
    # Resetar estado
    client.delete("/api/v1/proxies", headers=HEADERS)

    # Validar um proxy http como válido
    async def fake_validate_proxy(pdict, *args, **kwargs):
        return {
            "proxy": f"{pdict.get('ip')}:{pdict.get('port')}",
            "valid": True,
            "protocol": pdict.get("protocol"),
            "anonymity": "anonymous",
            "avg_response_time_ms": 30,
            "test_results": {},
        }

    monkeypatch.setattr("api.routers.proxies.validate_proxy", fake_validate_proxy)

    client.post(
        "/api/v1/proxies/validate",
        json={
            "proxies": ["1.2.3.4:8080"],
            "test_urls": ["http://example.com"],
            "timeout": 1,
            "test_all_urls": False,
            "check_anonymity": False,
            "check_geolocation": False,
            "concurrent_tests": 1,
        },
        headers=HEADERS,
    )

    # Solicitar random com protocolo inexistente no conjunto (https)
    r = client.get("/api/v1/proxies/random?protocol=https", headers=HEADERS)
    assert r.status_code == 404


def test_list_pagination_with_filters_valid_protocol(monkeypatch):
    client = get_client()
    # Resetar estado
    client.delete("/api/v1/proxies", headers=HEADERS)

    # Importar quatro proxies (3 http, 1 https)
    payload = {
        "proxies": [
            "http://30.0.0.1:8010",
            "http://30.0.0.2:8011",
            "https://30.0.0.3:8012",
            "http://30.0.0.4:8013",
        ],
        "auto_validate": False,
        "validation_urls": [],
    }
    r = client.post("/api/v1/proxies/import", json=payload, headers=HEADERS)
    assert r.status_code == 200

    # Validar: marcar apenas http como válidos
    async def fake_validate_proxy(pdict, *args, **kwargs):
        proto = pdict.get("protocol")
        return {
            "proxy": f"{pdict.get('ip')}:{pdict.get('port')}",
            "valid": proto == "http",
            "protocol": proto,
            "anonymity": "anonymous",
            "avg_response_time_ms": 40,
            "test_results": {},
        }

    monkeypatch.setattr("api.routers.proxies.validate_proxy", fake_validate_proxy)

    client.post(
        "/api/v1/proxies/validate",
        json={
            "proxies": [
                "http://30.0.0.1:8010",
                "http://30.0.0.2:8011",
                "https://30.0.0.3:8012",
                "http://30.0.0.4:8013",
            ],
            "test_urls": ["http://example.com"],
            "timeout": 1,
            "test_all_urls": False,
            "check_anonymity": False,
            "check_geolocation": False,
            "concurrent_tests": 4,
        },
        headers=HEADERS,
    )

    # Listar válidos http com paginação (per_page=2): total_pages deve ser 2
    r1 = client.get("/api/v1/proxies?valid_only=true&protocol=http&per_page=2&page=1", headers=HEADERS)
    assert r1.status_code == 200
    d1 = r1.json()
    assert d1["per_page"] == 2
    assert len(d1["proxies"]) == 2
    assert d1["total_pages"] >= 2

    r2 = client.get("/api/v1/proxies?valid_only=true&protocol=http&per_page=2&page=2", headers=HEADERS)
    assert r2.status_code == 200
    d2 = r2.json()
    assert d2["page"] == 2
    assert len(d2["proxies"]) >= 1


def test_list_order_case_insensitive_and_unknown_order_by():
    client = get_client()
    # Resetar estado
    client.delete("/api/v1/proxies", headers=HEADERS)

    # Importar proxies
    client.post(
        "/api/v1/proxies/import",
        json={"proxies": ["http://220.0.0.1:7200"], "auto_validate": False, "validation_urls": []},
        headers=HEADERS,
    )
    client.post(
        "/api/v1/proxies/import",
        json={"proxies": ["http://220.0.0.2:7201"], "auto_validate": False, "validation_urls": []},
        headers=HEADERS,
    )
    client.post(
        "/api/v1/proxies/import",
        json={"proxies": ["http://220.0.0.3:7202"], "auto_validate": False, "validation_urls": []},
        headers=HEADERS,
    )

    # order_by desconhecido deve funcionar sem erro
    r_unknown = client.get("/api/v1/proxies?order_by=nonexistent&order=DESC", headers=HEADERS)
    assert r_unknown.status_code == 200
    d_unknown = r_unknown.json()
    assert d_unknown["total"] >= 3

    # order case-insensitive: ASC em maiúsculo deve ordenar ascendente por created_at
    r_asc = client.get("/api/v1/proxies?order_by=created_at&order=ASC", headers=HEADERS)
    assert r_asc.status_code == 200
    d_asc = r_asc.json()
    assert d_asc["total"] >= 3
    # Primeiro importado deve aparecer entre os primeiros
    assert any(p["port"] == 7200 for p in d_asc["proxies"][:2])


def test_import_auto_validate_flag():
    client = get_client()
    # Resetar estado
    client.delete("/api/v1/proxies", headers=HEADERS)

    payload = {
        "proxies": [
            "http://230.0.0.1:7300",
            "http://230.0.0.2:7301",
        ],
        "auto_validate": True,
        "validation_urls": ["http://example.com"],
    }
    r = client.post("/api/v1/proxies/import", json=payload, headers=HEADERS)
    assert r.status_code == 200
    j = r.json()
    assert j["success"] is True
    assert j["imported"] >= 2
    assert j["validation_started"] is True
    # Quando auto_validate está ativo, polling_url deve ser retornado
    assert j.get("polling_url")
    # Verificar que o polling_url é um endpoint válido de job status
    status = client.get(j["polling_url"], headers=HEADERS)
    assert status.status_code == 200


def test_list_pagination_out_of_range_returns_empty():
    client = get_client()
    # Resetar estado
    client.delete("/api/v1/proxies", headers=HEADERS)

    # Importar 5 proxies
    payload = {
        "proxies": [
            "http://240.0.0.1:7400",
            "http://240.0.0.2:7401",
            "http://240.0.0.3:7402",
            "http://240.0.0.4:7403",
            "http://240.0.0.5:7404",
        ],
        "auto_validate": False,
        "validation_urls": [],
    }
    r = client.post("/api/v1/proxies/import", json=payload, headers=HEADERS)
    assert r.status_code == 200

    # per_page=2 => total_pages esperado 3; page=4 deve retornar vazio
    r4 = client.get("/api/v1/proxies?page=4&per_page=2", headers=HEADERS)
    assert r4.status_code == 200
    d4 = r4.json()
    assert d4["page"] == 4
    assert len(d4["proxies"]) == 0


def test_list_per_page_bounds():
    client = get_client()
    # Resetar estado
    client.delete("/api/v1/proxies", headers=HEADERS)

    # Importar 4 proxies
    payload = {
        "proxies": [
            "http://250.0.0.1:7500",
            "http://250.0.0.2:7501",
            "http://250.0.0.3:7502",
            "http://250.0.0.4:7503",
        ],
        "auto_validate": False,
        "validation_urls": [],
    }
    r = client.post("/api/v1/proxies/import", json=payload, headers=HEADERS)
    assert r.status_code == 200

    # per_page=1
    r_small = client.get("/api/v1/proxies?page=1&per_page=1", headers=HEADERS)
    assert r_small.status_code == 200
    d_small = r_small.json()
    assert d_small["per_page"] == 1
    assert len(d_small["proxies"]) == 1

    # per_page=100
    r_large = client.get("/api/v1/proxies?page=1&per_page=100", headers=HEADERS)
    assert r_large.status_code == 200
    d_large = r_large.json()
    assert d_large["per_page"] == 100
    assert len(d_large["proxies"]) >= 4


def test_random_proxy_filters_country_and_max_response_time(monkeypatch):
    client = get_client()
    # Resetar estado
    client.delete("/api/v1/proxies", headers=HEADERS)

    # Importar dois proxies
    client.post(
        "/api/v1/proxies/import",
        json={"proxies": ["http://260.0.0.1:7600", "http://260.0.0.2:7601"], "auto_validate": False, "validation_urls": []},
        headers=HEADERS,
    )

    # Validar: US com baixa latência (<=30), BR com alta latência (>=70)
    async def fake_validate_proxy(pdict, *args, **kwargs):
        is_us = pdict.get("ip") == "260.0.0.1"
        return {
            "proxy": f"{pdict.get('ip')}:{pdict.get('port')}",
            "valid": True,
            "protocol": pdict.get("protocol"),
            "anonymity": "anonymous",
            "avg_response_time_ms": 25 if is_us else 70,
            "test_results": {},
            "geolocation": {"country": "US" if is_us else "BR"},
        }

    monkeypatch.setattr("api.routers.proxies.validate_proxy", fake_validate_proxy)

    client.post(
        "/api/v1/proxies/validate",
        json={
            "proxies": ["http://260.0.0.1:7600", "http://260.0.0.2:7601"],
            "test_urls": ["http://example.com"],
            "timeout": 1,
            "test_all_urls": False,
            "check_anonymity": False,
            "check_geolocation": True,
            "concurrent_tests": 2,
        },
        headers=HEADERS,
    )

    # Random filtrado para US com max_response_time=30 deve retornar sucesso
    r_ok = client.get("/api/v1/proxies/random?protocol=http&country=US&max_response_time=30", headers=HEADERS)
    assert r_ok.status_code == 200
    d_ok = r_ok.json()
    assert d_ok["protocol"] == "http"
    assert d_ok["country"] == "US"
    assert (d_ok.get("avg_response_time_ms") or 0) <= 30

    # Random para BR com max_response_time=30 deve retornar 404
    r_404 = client.get("/api/v1/proxies/random?protocol=http&country=BR&max_response_time=30", headers=HEADERS)
    assert r_404.status_code == 404

def test_random_proxy_filters_with_anonymity(monkeypatch):
    client = get_client()
    # Resetar estado
    client.delete("/api/v1/proxies", headers=HEADERS)

    # Importar dois proxies
    client.post(
        "/api/v1/proxies/import",
        json={
            "proxies": ["http://270.0.0.1:7700", "http://270.0.0.2:7701"],
            "auto_validate": False,
            "validation_urls": [],
        },
        headers=HEADERS,
    )

    # Validar com anonimato distinto e latência
    async def fake_validate_proxy(pdict, *args, **kwargs):
        is_elite = pdict.get("port") == 7700
        return {
            "proxy": f"{pdict.get('ip')}:{pdict.get('port')}",
            "valid": True,
            "protocol": pdict.get("protocol"),
            "anonymity": "elite" if is_elite else "anonymous",
            "avg_response_time_ms": 28 if is_elite else 65,
            "test_results": {},
            "geolocation": {"country": "US" if is_elite else "BR"},
        }

    monkeypatch.setattr("api.routers.proxies.validate_proxy", fake_validate_proxy)

    client.post(
        "/api/v1/proxies/validate",
        json={
            "proxies": ["http://270.0.0.1:7700", "http://270.0.0.2:7701"],
            "test_urls": ["http://example.com"],
            "timeout": 1,
            "test_all_urls": False,
            "check_anonymity": True,
            "check_geolocation": True,
            "concurrent_tests": 2,
        },
        headers=HEADERS,
    )

    # Random filtrado para elite + US com max_response_time<=30 deve retornar sucesso
    r_ok = client.get(
        "/api/v1/proxies/random?protocol=http&country=US&max_response_time=30&anonymity=elite",
        headers=HEADERS,
    )
    assert r_ok.status_code == 200
    d_ok = r_ok.json()
    assert d_ok["protocol"] == "http"
    assert d_ok["country"] == "US"
    assert (d_ok.get("avg_response_time_ms") or 0) <= 30
    assert (d_ok.get("anonymity") or "") == "elite"

    # Random para anonymous + BR com max_response_time<=30 deve retornar 404
    r_404 = client.get(
        "/api/v1/proxies/random?protocol=http&country=BR&max_response_time=30&anonymity=anonymous",
        headers=HEADERS,
    )
    assert r_404.status_code == 404


def test_list_order_by_last_checked_desc_validated_first(monkeypatch):
    client = get_client()
    # Resetar estado
    client.delete("/api/v1/proxies", headers=HEADERS)

    # Importar dois proxies
    client.post(
        "/api/v1/proxies/import",
        json={"proxies": ["http://270.0.0.1:7700", "http://270.0.0.2:7701"], "auto_validate": False, "validation_urls": []},
        headers=HEADERS,
    )

    # Validar apenas o primeiro para setar last_checked
    async def fake_validate_proxy(pdict, *args, **kwargs):
        return {
            "proxy": f"{pdict.get('ip')}:{pdict.get('port')}",
            "valid": True,
            "protocol": pdict.get("protocol"),
            "anonymity": "anonymous",
            "avg_response_time_ms": 40,
            "test_results": {},
        }

    monkeypatch.setattr("api.routers.proxies.validate_proxy", fake_validate_proxy)
    client.post(
        "/api/v1/proxies/validate",
        json={
            "proxies": ["http://270.0.0.1:7700"],
            "test_urls": ["http://example.com"],
            "timeout": 1,
            "test_all_urls": False,
            "check_anonymity": False,
            "check_geolocation": False,
            "concurrent_tests": 1,
        },
        headers=HEADERS,
    )

    rlist = client.get("/api/v1/proxies?order_by=last_checked&order=desc", headers=HEADERS)
    assert rlist.status_code == 200
    dl = rlist.json()
    assert dl["total"] >= 2
    # Primeiro item deve ser o validado (porta 7700), pois tem last_checked definido
    assert dl["proxies"][0]["port"] == 7700


def test_list_pagination_with_restrictive_filters_country_protocol_valid_only(monkeypatch):
    client = get_client()
    # Resetar estado
    client.delete("/api/v1/proxies", headers=HEADERS)

    # Importar 6 proxies http/https
    client.post(
        "/api/v1/proxies/import",
        json={
            "proxies": [
                "http://280.0.0.1:7800",
                "http://280.0.0.2:7801",
                "http://280.0.0.3:7802",
                "https://280.0.0.4:7803",
                "https://280.0.0.5:7804",
                "https://280.0.0.6:7805",
            ],
            "auto_validate": False,
            "validation_urls": [],
        },
        headers=HEADERS,
    )

    # Validar alguns para definir país e latência, alternando validade
    async def fake_validate_proxy(pdict, *args, **kwargs):
        ip = pdict.get("ip")
        port = pdict.get("port")
        proto = pdict.get("protocol")
        # US válidos: 7800 (http), 7803 (https)
        # DE inválido: 7801 (http)
        # US válido: 7802 (http)
        # BR válido: 7804 (https)
        # US válido: 7805 (https)
        country = "US"
        valid = True
        if port == 7801:
            country = "DE"
            valid = False
        elif port == 7804:
            country = "BR"
            valid = True
        elif port in (7800, 7802, 7803, 7805):
            country = "US"
            valid = True
        return {
            "proxy": f"{ip}:{port}",
            "valid": valid,
            "protocol": proto,
            "anonymity": "anonymous",
            "avg_response_time_ms": 30 if valid else 80,
            "test_results": {},
            "geolocation": {"country": country},
        }

    monkeypatch.setattr("api.routers.proxies.validate_proxy", fake_validate_proxy)

    client.post(
        "/api/v1/proxies/validate",
        json={
            "proxies": [
                "http://280.0.0.1:7800",
                "http://280.0.0.2:7801",
                "http://280.0.0.3:7802",
                "https://280.0.0.4:7803",
                "https://280.0.0.5:7804",
                "https://280.0.0.6:7805",
            ],
            "test_urls": ["http://example.com"],
            "timeout": 1,
            "test_all_urls": False,
            "check_anonymity": False,
            "check_geolocation": True,
            "concurrent_tests": 3,
        },
        headers=HEADERS,
    )

    # Filtrar por US + http + valid_only
    r1 = client.get(
        "/api/v1/proxies?country=US&protocol=http&valid_only=true&per_page=1&page=1",
        headers=HEADERS,
    )
    assert r1.status_code == 200
    d1 = r1.json()
    # Esperado: 7800 e 7802 entram (http, US, válidos) => total 2, total_pages 2 com per_page=1
    assert d1["total"] == 2
    assert d1["total_pages"] == 2
    assert len(d1["proxies"]) == 1
    assert d1["proxies"][0]["protocol"] == "http"
    assert d1["proxies"][0]["country"] == "US"

    # Página 2 deve conter o outro item
    r2 = client.get(
        "/api/v1/proxies?country=US&protocol=http&valid_only=true&per_page=1&page=2",
        headers=HEADERS,
    )
    assert r2.status_code == 200
    d2 = r2.json()
    assert d2["total"] == 2
    assert d2["total_pages"] == 2
    assert len(d2["proxies"]) == 1
    assert d2["proxies"][0]["protocol"] == "http"
    assert d2["proxies"][0]["country"] == "US"


def test_list_order_by_avg_response_time_nulls_position(monkeypatch):
    client = get_client()
    # Resetar estado
    client.delete("/api/v1/proxies", headers=HEADERS)

    # Importar 3 proxies
    client.post(
        "/api/v1/proxies/import",
        json={
            "proxies": ["http://290.0.0.1:7900", "http://290.0.0.2:7901", "http://290.0.0.3:7902"],
            "auto_validate": False,
            "validation_urls": [],
        },
        headers=HEADERS,
    )

    # Validar apenas dois para que um fique com avg_response_time_ms=None
    async def fake_validate_proxy(pdict, *args, **kwargs):
        port = pdict.get("port")
        latency = 50 if port == 7900 else 20
        return {
            "proxy": f"{pdict.get('ip')}:{port}",
            "valid": True,
            "protocol": pdict.get("protocol"),
            "anonymity": "anonymous",
            "avg_response_time_ms": latency,
            "test_results": {},
        }

    monkeypatch.setattr("api.routers.proxies.validate_proxy", fake_validate_proxy)
    client.post(
        "/api/v1/proxies/validate",
        json={
            "proxies": ["http://290.0.0.1:7900", "http://290.0.0.2:7901"],
            "test_urls": ["http://example.com"],
            "timeout": 1,
            "test_all_urls": False,
            "check_anonymity": False,
            "check_geolocation": False,
            "concurrent_tests": 2,
        },
        headers=HEADERS,
    )

    # Ascendente: em SQLite, NULLs vem primeiro — o não validado (7902) deve aparecer antes
    rasc = client.get("/api/v1/proxies?order_by=avg_response_time_ms&order=asc", headers=HEADERS)
    assert rasc.status_code == 200
    dasc = rasc.json()
    assert dasc["total"] == 3
    assert dasc["proxies"][0]["avg_response_time_ms"] is None

    # Descendente: maior latência primeiro (7900, 50ms); NULLs por último
    rdesc = client.get("/api/v1/proxies?order_by=avg_response_time_ms&order=desc", headers=HEADERS)
    assert rdesc.status_code == 200
    ddesc = rdesc.json()
    assert ddesc["total"] == 3
    assert ddesc["proxies"][0]["port"] == 7900
    # Algum item ao final deve ter avg_response_time_ms == None
    assert any(p["avg_response_time_ms"] is None for p in ddesc["proxies"])  # NULLs ao fim


def test_random_https_filters_country_and_latency(monkeypatch):
    client = get_client()
    # Resetar estado
    client.delete("/api/v1/proxies", headers=HEADERS)

    # Importar proxies http e https
    client.post(
        "/api/v1/proxies/import",
        json={
            "proxies": [
                "https://300.0.0.1:8000",
                "https://300.0.0.2:8001",
                "http://300.0.0.3:8002",
            ],
            "auto_validate": False,
            "validation_urls": [],
        },
        headers=HEADERS,
    )

    async def fake_validate_proxy(pdict, *args, **kwargs):
        ip = pdict.get("ip")
        port = pdict.get("port")
        proto = pdict.get("protocol")
        country = "US" if port == 8000 else ("BR" if port == 8001 else "US")
        latency = 25 if port == 8000 else (70 if port == 8001 else 40)
        return {
            "proxy": f"{ip}:{port}",
            "valid": True,
            "protocol": proto,
            "anonymity": "anonymous",
            "avg_response_time_ms": latency,
            "test_results": {},
            "geolocation": {"country": country},
        }

    monkeypatch.setattr("api.routers.proxies.validate_proxy", fake_validate_proxy)
    client.post(
        "/api/v1/proxies/validate",
        json={
            "proxies": [
                "https://300.0.0.1:8000",
                "https://300.0.0.2:8001",
                "http://300.0.0.3:8002",
            ],
            "test_urls": ["http://example.com"],
            "timeout": 1,
            "test_all_urls": False,
            "check_anonymity": False,
            "check_geolocation": True,
            "concurrent_tests": 3,
        },
        headers=HEADERS,
    )

    # HTTPS + US + latência <= 30 => deve encontrar o 8000
    rok = client.get(
        "/api/v1/proxies/random?protocol=https&country=US&max_response_time=30",
        headers=HEADERS,
    )
    assert rok.status_code == 200
    dok = rok.json()
    assert dok["protocol"] == "https"
    assert dok["country"] == "US"
    assert (dok.get("avg_response_time_ms") or 0) <= 30

    # HTTPS + BR + latência <= 30 => não deve encontrar (8001 tem 70ms) => 404
    rnot = client.get(
        "/api/v1/proxies/random?protocol=https&country=BR&max_response_time=30",
        headers=HEADERS,
    )
    assert rnot.status_code == 404


def test_scrape_with_monkeypatch(monkeypatch):
    client = get_client()

    async def fake_scrape_from_sources(country, protocols, sources, quantity, timeout=30, retries=2):
        return [
            {"ip": "3.3.3.3", "port": 80, "protocol": "http", "country": country or None, "source": "mock"},
            {"ip": "4.4.4.4", "port": 443, "protocol": "https", "country": country or None, "source": "mock"},
        ]

    # Patchar o símbolo utilizado dentro do router
    monkeypatch.setattr("api.routers.proxies.scrape_from_sources", fake_scrape_from_sources)

    payload = {
        "country": "United States",
        "protocols": ["http", "https"],
        "sources": ["mock-source"],
        "quantity": 2,
        "timeout": 1,
        "retries": 0,
    }
    r = client.post("/api/v1/proxies/scrape", json=payload, headers=HEADERS)
    assert r.status_code == 200
    j = r.json()
    assert j["success"] is True
    assert j["total_found"] == 2
    assert len(j["proxies"]) == 2
    assert j["proxies"][0]["country"] == "United States"


def test_delete_all_then_list_empty():
    client = get_client()
    r = client.delete("/api/v1/proxies", headers=HEADERS)
    assert r.status_code == 200
    j = r.json()
    assert j["success"] is True

    r2 = client.get("/api/v1/proxies", headers=HEADERS)
    assert r2.status_code == 200
    d = r2.json()
    assert d["total"] == 0
    assert len(d["proxies"]) == 0


def test_schedule_validate_job(monkeypatch):
    client = get_client()
    # Reimportar um proxy para validar no job
    client.post("/api/v1/proxies/import", json={"proxies": ["5.5.5.5:8080"]}, headers=HEADERS)

    async def fake_validate_proxy(pdict, *args, **kwargs):
        return {
            "proxy": f"{pdict.get('ip')}:{pdict.get('port')}",
            "valid": True,
            "protocol": pdict.get("protocol"),
            "anonymity": "elite",
            "avg_response_time_ms": 50,
            "test_results": {"http://example.com": {"status_code": 200, "response_time_ms": 50}},
        }

    monkeypatch.setattr("api.routers.proxies.validate_proxy", fake_validate_proxy)

    payload = {
        "type": "validate",
        "proxies": ["5.5.5.5:8080"],
        "test_urls": ["http://example.com"],
        "timeout": 1,
        "test_all_urls": False,
        "check_anonymity": False,
        "check_geolocation": False,
    }
    r = client.post("/api/v1/proxies/schedule", json=payload, headers=HEADERS)
    assert r.status_code == 200
    jr = r.json()
    assert "job_id" in jr
    assert jr["status"] == "processing"
    # Polling imediato: deve existir o job
    # Opcional: polling não é necessário aqui; apenas confirmar criação do job


def test_schedule_validate_job_and_poll(monkeypatch):
    client = get_client()
    # Reimportar um proxy para validar no job
    client.post("/api/v1/proxies/import", json={"proxies": ["6.6.6.6:8080"]}, headers=HEADERS)

    async def fake_validate_proxy(pdict, *args, **kwargs):
        return {
            "proxy": f"{pdict.get('ip')}:{pdict.get('port')}",
            "valid": True,
            "protocol": pdict.get("protocol"),
            "anonymity": "anonymous",
            "avg_response_time_ms": 42,
            "test_results": {"http://example.com": {"status_code": 200, "response_time_ms": 42}},
        }

    monkeypatch.setattr("api.routers.proxies.validate_proxy", fake_validate_proxy)

    payload = {
        "type": "validate",
        "proxies": ["6.6.6.6:8080"],
        "test_urls": ["http://example.com"],
        "timeout": 1,
        "test_all_urls": False,
        "check_anonymity": False,
        "check_geolocation": False,
    }
    r = client.post("/api/v1/proxies/schedule", json=payload, headers=HEADERS)
    assert r.status_code == 200
    jr = r.json()
    assert "job_id" in jr
    assert jr["status"] == "processing"

    # Poll até concluir
    import time
    job_id = jr["job_id"]
    time.sleep(0.05)
    for _ in range(200):
        s = client.get(f"/jobs/{job_id}", headers=HEADERS)
        assert s.status_code == 200
        js = s.json()
        if js["status"] == "completed":
            assert js["progress"] == 1.0
            # Para jobs de proxies, result é um dict com contagens
            assert isinstance(js["result"], dict)
            assert set(js["result"].keys()) >= {"total_tested", "valid", "invalid"}
            break
        if js["status"] == "failed":
            assert False, f"Job falhou: {js.get('error')}"
        time.sleep(0.05)
    else:
        assert False, "Job de validação de proxies não completou a tempo"


def test_schedule_scrape_job_and_poll(monkeypatch):
    client = get_client()

    async def fake_scrape_from_sources(country, protocols, sources, quantity, timeout=10, retries=2):
        # Retorna dois proxies determinísticos
        return [
            {"ip": "7.7.7.7", "port": 8080, "protocol": "http", "country": "US", "source": "fake"},
            {"ip": "8.8.8.8", "port": 3128, "protocol": "http", "country": "US", "source": "fake"},
        ]

    monkeypatch.setattr("api.routers.proxies.scrape_from_sources", fake_scrape_from_sources)

    payload = {
        "type": "scrape",
        "quantity": 2,
        "protocols": ["http"],
        "sources": ["fake"],
        "scrape_timeout": 1,
        "scrape_retries": 0,
    }

    r = client.post("/api/v1/proxies/schedule", json=payload, headers=HEADERS)
    assert r.status_code == 200
    jr = r.json()
    assert "job_id" in jr
    assert jr["status"] == "processing"

    # Poll até concluir
    import time
    job_id = jr["job_id"]
    time.sleep(0.05)
    for _ in range(200):
        s = client.get(f"/jobs/{job_id}", headers=HEADERS)
        assert s.status_code == 200
        js = s.json()
        if js["status"] == "completed":
            assert js["progress"] == 1.0
            assert isinstance(js["result"], dict)
            assert js["result"].get("total_found") == 2
            assert js["result"].get("saved") == 2
            break
        if js["status"] == "failed":
            assert False, f"Job falhou: {js.get('error')}"
        time.sleep(0.05)
    else:
        assert False, "Job de scraping de proxies não completou a tempo"


def test_schedule_validate_job_failed(monkeypatch):
    client = get_client()
    # Importar proxy para validação
    client.post("/api/v1/proxies/import", json={"proxies": ["10.10.10.10:8080"]}, headers=HEADERS)

    async def fake_validate_proxy_raises(pdict, *args, **kwargs):
        raise RuntimeError("falha simulada na validação")

    monkeypatch.setattr("api.routers.proxies.validate_proxy", fake_validate_proxy_raises)

    payload = {
        "type": "validate",
        "proxies": ["10.10.10.10:8080"],
        "test_urls": ["http://example.com"],
        "timeout": 1,
        "test_all_urls": False,
        "check_anonymity": False,
        "check_geolocation": False,
    }
    r = client.post("/api/v1/proxies/schedule", json=payload, headers=HEADERS)
    assert r.status_code == 200
    jr = r.json()
    job_id = jr["job_id"]

    # Poll até falhar
    import time
    time.sleep(0.05)
    for _ in range(200):
        s = client.get(f"/jobs/{job_id}", headers=HEADERS)
        assert s.status_code == 200
        js = s.json()
        if js["status"] == "failed":
            assert js.get("error")
            break
        time.sleep(0.05)
    else:
        assert False, "Job de validação não falhou como esperado"


def test_schedule_scrape_job_failed(monkeypatch):
    client = get_client()

    async def fake_scrape_from_sources_raises(country, protocols, sources, quantity, timeout=10, retries=2):
        raise RuntimeError("falha simulada no scraping")

    monkeypatch.setattr("api.routers.proxies.scrape_from_sources", fake_scrape_from_sources_raises)

    payload = {
        "type": "scrape",
        "quantity": 1,
        "protocols": ["http"],
        "sources": ["fake"],
        "scrape_timeout": 1,
        "scrape_retries": 0,
    }
    r = client.post("/api/v1/proxies/schedule", json=payload, headers=HEADERS)
    assert r.status_code == 200
    jr = r.json()
    job_id = jr["job_id"]

    # Poll até falhar
    import time
    time.sleep(0.05)
    for _ in range(200):
        s = client.get(f"/jobs/{job_id}", headers=HEADERS)
        assert s.status_code == 200
        js = s.json()
        if js["status"] == "failed":
            assert js.get("error")
            break
        time.sleep(0.05)
    else:
        assert False, "Job de scraping não falhou como esperado"


def test_schedule_validate_job_progress(monkeypatch):
    client = get_client()
    # Importar múltiplos proxies
    client.post(
        "/api/v1/proxies/import",
        json={"proxies": ["11.11.11.11:8080", "11.11.11.12:8080", "11.11.11.13:8080"]},
        headers=HEADERS,
    )

    import asyncio as _asyncio

    async def fake_validate_proxy_slow(pdict, *args, **kwargs):
        await _asyncio.sleep(0.05)
        return {
            "proxy": f"{pdict.get('ip')}:{pdict.get('port')}",
            "valid": True,
            "protocol": pdict.get("protocol"),
            "anonymity": "anonymous",
            "avg_response_time_ms": 42,
            "test_results": {"http://example.com": {"status_code": 200, "response_time_ms": 42}},
        }

    monkeypatch.setattr("api.routers.proxies.validate_proxy", fake_validate_proxy_slow)

    payload = {
        "type": "validate",
        "proxies": ["11.11.11.11:8080", "11.11.11.12:8080", "11.11.11.13:8080"],
        "test_urls": ["http://example.com"],
        "timeout": 1,
        "test_all_urls": False,
        "check_anonymity": False,
        "check_geolocation": False,
    }
    r = client.post("/api/v1/proxies/schedule", json=payload, headers=HEADERS)
    assert r.status_code == 200
    jr = r.json()
    job_id = jr["job_id"]

    # Poll e verificar progresso intermediário
    import time
    saw_intermediate = False
    time.sleep(0.05)
    for _ in range(200):
        s = client.get(f"/jobs/{job_id}", headers=HEADERS)
        assert s.status_code == 200
        js = s.json()
        prog = js.get("progress") or 0.0
        if 0.0 < prog < 1.0:
            saw_intermediate = True
        if js["status"] == "completed":
            assert js["progress"] == 1.0
            assert saw_intermediate, "Progresso intermediário não observado"
            assert isinstance(js["result"], dict)
            assert js["result"].get("total_tested") == 3
            assert js["result"].get("valid") == 3
            assert js["result"].get("invalid") == 0
            break
        if js["status"] == "failed":
            assert False, f"Job falhou: {js.get('error')}"
        time.sleep(0.05)
    else:
        assert False, "Job de validação não completou a tempo"


def test_schedule_scrape_job(monkeypatch):
    client = get_client()

    async def fake_scrape_from_sources(country, protocols, sources, quantity, timeout=30, retries=2):
        return [{"ip": "6.6.6.6", "port": 8080, "protocol": "http", "country": "US", "source": "mock"}]

    monkeypatch.setattr("api.routers.proxies.scrape_from_sources", fake_scrape_from_sources)

    payload = {
        "type": "scrape",
        "country": "US",
        "protocols": ["http"],
        "sources": ["mock"],
        "quantity": 1,
        "scrape_timeout": 1,
        "scrape_retries": 0,
    }
    r = client.post("/api/v1/proxies/schedule", json=payload, headers=HEADERS)
    assert r.status_code == 200
    jr = r.json()
    assert "job_id" in jr
    assert jr["status"] == "processing"
    # Opcional: sem polling para evitar validação do tipo de resultado do job
def test_proxy_detail_and_patch_update_country_anonymity():
    client = get_client()
    # Resetar estado
    client.delete("/api/v1/proxies", headers=HEADERS)

    # Importar um proxy
    rimp = client.post(
        "/api/v1/proxies/import",
        json={"proxies": ["http://200.0.0.1:7000"], "auto_validate": False, "validation_urls": []},
        headers=HEADERS,
    )
    assert rimp.status_code == 200

    # Obter listagem para descobrir id
    rlist = client.get("/api/v1/proxies?order_by=created_at&order=desc", headers=HEADERS)
    assert rlist.status_code == 200
    dlist = rlist.json()
    assert dlist["total"] >= 1
    # Procurar o item pelo port
    item = next(p for p in dlist["proxies"] if p["port"] == 7000)
    assert item.get("id")

    # GET detail
    rdetail = client.get(f"/api/v1/proxies/{item['id']}", headers=HEADERS)
    assert rdetail.status_code == 200
    ddetail = rdetail.json()
    assert ddetail["proxy"]["ip"]

    # PATCH update country e anonymity
    rpatch = client.patch(
        f"/api/v1/proxies/{ddetail['proxy']['id']}",
        json={"country": "US", "anonymity": "elite"},
        headers=HEADERS,
    )
    assert rpatch.status_code == 200
    dpatch = rpatch.json()
    assert dpatch["proxy"]["country"] == "US"
    assert dpatch["proxy"]["anonymity"] == "elite"

def test_proxy_patch_not_found():
    client = get_client()
    r = client.patch("/api/v1/proxies/999999", json={"country": "BR"}, headers=HEADERS)
    assert r.status_code == 404
def test_list_filters_with_anonymity(monkeypatch):
    client = get_client()
    # Resetar estado
    client.delete("/api/v1/proxies", headers=HEADERS)

    # Importar dois proxies http
    payload = {
        "proxies": [
            "http://40.0.0.1:8100",
            "http://40.0.0.2:8101",
        ],
        "auto_validate": False,
        "validation_urls": [],
    }
    r = client.post("/api/v1/proxies/import", json=payload, headers=HEADERS)
    assert r.status_code == 200

    # Validar com anonimato distinto e geolocalização
    async def fake_validate_proxy(pdict, *args, **kwargs):
        is_elite = pdict.get("port") == 8100
        return {
            "proxy": f"{pdict.get('ip')}:{pdict.get('port')}",
            "valid": True,
            "protocol": pdict.get("protocol"),
            "anonymity": "elite" if is_elite else "anonymous",
            "avg_response_time_ms": 30 if is_elite else 60,
            "test_results": {},
            "geolocation": {"country": "US" if is_elite else "BR"},
        }

    monkeypatch.setattr("api.routers.proxies.validate_proxy", fake_validate_proxy)

    client.post(
        "/api/v1/proxies/validate",
        json={
            "proxies": [
                "http://40.0.0.1:8100",
                "http://40.0.0.2:8101",
            ],
            "test_urls": ["http://example.com"],
            "timeout": 1,
            "test_all_urls": False,
            "check_anonymity": True,
            "check_geolocation": True,
            "concurrent_tests": 2,
        },
        headers=HEADERS,
    )

    # Listar combinando filtros: apenas elite, US, http e válidos
    rlist = client.get(
        "/api/v1/proxies?valid_only=true&country=US&protocol=http&anonymity=elite",
        headers=HEADERS,
    )
    assert rlist.status_code == 200
    dlist = rlist.json()
    assert dlist["total"] >= 1
    assert all((p.get("country") or "") == "US" for p in dlist["proxies"])  # país
    assert all((p.get("protocol") or "") == "http" for p in dlist["proxies"])  # protocolo
    assert all((p.get("anonymity") or "") == "elite" for p in dlist["proxies"])  # anonimato

    # Export JSON deve refletir os filtros
    rjson = client.get(
        "/api/v1/proxies/export?format=json&valid_only=true&country=US&protocol=http&anonymity=elite",
        headers=HEADERS,
    )
    assert rjson.status_code == 200
    jdata = rjson.json()
    assert isinstance(jdata, list)
    assert len(jdata) >= 1
    assert all((i.get("anonymity") or "") == "elite" for i in jdata)

    # Export CSV deve conter apenas o proxy elite US
    rcsv = client.get(
        "/api/v1/proxies/export?format=csv&valid_only=true&country=US&protocol=http&anonymity=elite",
        headers=HEADERS,
    )
    assert rcsv.status_code == 200
    text = rcsv.text.strip()
    assert "40.0.0.1:8100" in text
    assert "40.0.0.2:8101" not in text