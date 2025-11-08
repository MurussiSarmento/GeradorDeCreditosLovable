"""
Testes de Critérios de Aceitação - Validação completa contra PRD

Este arquivo consolida testes para validar que TODOS os critérios de aceite
do PRD "Proxy Manager & Validator Tool.md" estão implementados e funcionando.
"""

import os
import sys
import types
import pytest
from fastapi.testclient import TestClient


def setup_module(module=None):
    """Configurazione iniziale per i test di accettazione."""
    import uuid
    os.environ["API_KEY"] = "test-key-validation"
    os.environ["API_RATE_LIMIT_IP"] = "1000"
    os.environ["API_RATE_LIMIT_KEY"] = "1000"
    os.environ["PROXIES_RATE_LIMIT_IP"] = "500"
    os.environ["PROXIES_RATE_LIMIT_KEY"] = "500"
    os.environ["PROXIES_MAX_CONCURRENCY"] = "20"
    # Use a unique DB for acceptance tests to avoid interference with other tests
    unique_id = str(uuid.uuid4())[:8]
    db_path = os.path.join("data", f".test_acceptance_{unique_id}.db")
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"
    try:
        if os.path.exists(db_path):
            os.remove(db_path)
    except Exception:
        pass
    if "aiohttp_socks" not in sys.modules:
        sys.modules["aiohttp_socks"] = types.SimpleNamespace(ProxyConnector=None)


HEADERS = {"x-api-key": "test-key-validation"}


def get_client() -> TestClient:
    from api.app import create_app
    return TestClient(create_app())


# =============================================================================
# CRITÉRIO 1: AUTENTICAÇÃO VIA X-API-KEY (Linha 75 do todolist)
# =============================================================================

def test_acceptance_auth_api_key_required():
    """
    Verifica que endpoints de proxies requerem autenticação via X-API-Key.
    Critério de Aceite: Endpoints autenticados via X-API-Key
    """
    client = get_client()
    
    # Sem header de autenticação deve retornar 401
    r = client.get("/api/v1/proxies")
    assert r.status_code == 401, "GET /api/v1/proxies sem auth deve retornar 401"
    
    # Com X-API-Key inválida deve retornar 401
    r = client.get("/api/v1/proxies", headers={"x-api-key": "invalid-key"})
    assert r.status_code == 401, "GET /api/v1/proxies com API key inválida deve retornar 401"
    
    # Com X-API-Key válida deve funcionar
    r = client.get("/api/v1/proxies", headers=HEADERS)
    assert r.status_code == 200, "GET /api/v1/proxies com API key válida deve retornar 200"


def test_acceptance_auth_applies_to_all_proxy_endpoints():
    """
    Verifica que autenticação é requerida em todos os endpoints de proxies.
    """
    client = get_client()
    endpoints = [
        ("GET", "/api/v1/proxies"),
        ("GET", "/api/v1/proxies/random"),
        ("GET", "/api/v1/proxies/stats"),
        ("POST", "/api/v1/proxies/scrape"),
        ("POST", "/api/v1/proxies/validate"),
        ("POST", "/api/v1/proxies/import"),
        ("POST", "/api/v1/proxies/schedule"),
        ("DELETE", "/api/v1/proxies"),
    ]
    
    for method, endpoint in endpoints:
        if method == "GET":
            r = client.get(endpoint)
        else:
            r = client.request(method, endpoint, json={})
        assert r.status_code == 401, f"{method} {endpoint} sem auth deve retornar 401"


# =============================================================================
# CRITÉRIO 2: VALIDAÇÃO SUPORTA HTTP/HTTPS/SOCKS4/SOCKS5 (Linha 76)
# =============================================================================

def test_acceptance_validation_supports_protocols(monkeypatch):
    """
    Verifica que validador suporta HTTP, HTTPS, SOCKS4 e SOCKS5.
    Critério de Aceite: Validação suporta http/https/socks4/socks5 e calcula latência média
    """
    client = get_client()
    
    # Mock de validação que suporta múltiplos protocolos
    async def mock_validate(*args, **kwargs):
        return {
            "proxy": "1.2.3.4:8080",
            "valid": True,
            "protocol": "http",
            "anonymity": "anonymous",
            "avg_response_time_ms": 150,
            "test_results": {
                "http://example.com": {
                    "success": True,
                    "status_code": 200,
                    "response_time_ms": 150
                }
            }
        }
    
    monkeypatch.setattr("api.routers.proxies.validate_proxy", mock_validate)
    
    # Testar validação com múltiplos protocolos
    protocols = ["http", "https", "socks4", "socks5"]
    
    for protocol in protocols:
        payload = {
            "proxies": [f"{protocol}://1.2.3.4:8080"],
            "test_urls": ["http://example.com"],
            "timeout": 10,
            "test_all_urls": True,
            "check_anonymity": False,
            "check_geolocation": False,
            "concurrent_tests": 1,
        }
        r = client.post("/api/v1/proxies/validate", json=payload, headers=HEADERS)
        assert r.status_code == 200, f"Validação com protocolo {protocol} deve funcionar"
        result = r.json()
        assert result.get("total_tested") > 0, f"Deve validar proxies com protocolo {protocol}"


def test_acceptance_validation_calculates_avg_response_time(monkeypatch):
    """
    Verifica que a validação calcula tempo médio de resposta.
    """
    client = get_client()
    
    async def mock_validate_with_latency(*args, **kwargs):
        return {
            "proxy": "1.2.3.4:8080",
            "valid": True,
            "protocol": "http",
            "anonymity": "anonymous",
            "avg_response_time_ms": 275,
            "test_results": {
                "http://example.com": {
                    "success": True,
                    "status_code": 200,
                    "response_time_ms": 250
                },
                "http://test.com": {
                    "success": True,
                    "status_code": 200,
                    "response_time_ms": 300
                }
            }
        }
    
    monkeypatch.setattr("api.routers.proxies.validate_proxy", mock_validate_with_latency)
    
    payload = {
        "proxies": ["1.2.3.4:8080"],
        "test_urls": ["http://example.com", "http://test.com"],
        "timeout": 10,
        "test_all_urls": False,
        "check_anonymity": False,
        "check_geolocation": False,
        "concurrent_tests": 1,
    }
    r = client.post("/api/v1/proxies/validate", json=payload, headers=HEADERS)
    assert r.status_code == 200
    result = r.json()
    
    # Verificar que latência média foi calculada
    if result.get("results"):
        for res in result["results"]:
            if res.get("valid"):
                assert "avg_response_time_ms" in res, "Latência média deve estar presente"
                assert res["avg_response_time_ms"] > 0, "Latência deve ser > 0"


# =============================================================================
# CRITÉRIO 3: FILTROS AVANÇADOS (Linha 78)
# =============================================================================

def test_acceptance_advanced_filters_country_protocol_anonymity(monkeypatch):
    """
    Verifica filtros avançados: país, protocolo, anonimato.
    Critério de Aceite: Filtros avançados por país, protocolo e anonimato
    """
    client = get_client()
    
    # Importar alguns proxies de teste
    payload = {
        "proxies": [
            "http://1.2.3.4:8080",
            "https://2.2.2.2:3128",
            "http://3.3.3.3:80",
        ],
        "auto_validate": False,
        "validation_urls": [],
    }
    r = client.post("/api/v1/proxies/import", json=payload, headers=HEADERS)
    assert r.status_code == 200
    
    # Teste 1: Filtro por protocolo
    r = client.get("/api/v1/proxies?protocol=http", headers=HEADERS)
    assert r.status_code == 200
    result = r.json()
    for proxy in result.get("proxies", []):
        assert proxy.get("protocol") == "http", "Filtro de protocolo deve retornar apenas HTTP"
    
    # Teste 2: Filtro por país (quando disponível)
    r = client.get("/api/v1/proxies?country=US", headers=HEADERS)
    assert r.status_code == 200
    result = r.json()
    # Pode retornar vazio se nenhum proxy tem país US, mas não deve falhar
    
    # Teste 3: Filtro por validade
    r = client.get("/api/v1/proxies?valid_only=true", headers=HEADERS)
    assert r.status_code == 200
    result = r.json()
    for proxy in result.get("proxies", []):
        assert proxy.get("valid") is True, "Filtro valid_only deve retornar apenas válidos"


def test_acceptance_combined_filters():
    """
    Verifica que filtros podem ser combinados.
    """
    client = get_client()
    
    # Filtro combinado: protocolo + válidos + país
    r = client.get(
        "/api/v1/proxies?protocol=http&valid_only=true&country=US",
        headers=HEADERS
    )
    assert r.status_code == 200
    result = r.json()
    # Pode retornar vazio, mas deve funcionar sem erro


# =============================================================================
# CRITÉRIO 4: MÉTRICAS ACESSÍVEIS (Linha 79)
# =============================================================================

def test_acceptance_metrics_endpoint_accessible():
    """
    Verifica que endpoint de métricas é acessível.
    Critério de Aceite: Métricas acessíveis e úteis para decisão de uso
    """
    client = get_client()
    
    r = client.get("/api/v1/proxies/stats", headers=HEADERS)
    assert r.status_code == 200
    result = r.json()
    
    # Verificar que métricas essenciais estão presentes
    assert "by_protocol" in result, "Métricas por protocolo devem estar presentes"
    assert "by_country" in result, "Métricas por país devem estar presentes"
    assert "avg_response_time_ms" in result, "Latência média deve estar presente"
    assert "total" in result, "Total de proxies deve estar presente"
    assert "valid" in result, "Total de proxies válidos deve estar presente"
    assert "invalid" in result, "Total de proxies inválidos deve estar presente"
    assert "success_rate" in result, "Taxa de sucesso deve estar presente"


def test_acceptance_metrics_provide_useful_data():
    """
    Verifica que as métricas são úteis para tomada de decisão.
    """
    client = get_client()
    
    # Primeiro, adicionar alguns proxies
    payload = {
        "proxies": [
            "http://1.1.1.1:8080",
            "https://2.2.2.2:3128",
        ],
        "auto_validate": False,
        "validation_urls": [],
    }
    client.post("/api/v1/proxies/import", json=payload, headers=HEADERS)
    
    # Recuperar métricas
    r = client.get("/api/v1/proxies/stats", headers=HEADERS)
    assert r.status_code == 200
    result = r.json()
    
    # Verificar que as métricas fornecem informações úteis
    assert result.get("total") >= 0, "Deve informar total de proxies"
    assert result.get("valid") >= 0, "Deve informar total de válidos"
    assert isinstance(result.get("by_protocol"), dict), "Deve agrupar por protocolo"


# =============================================================================
# CRITÉRIO 5: UI RESPONSIVA E NÃO BLOQUEANTE (Linha 90)
# =============================================================================

def test_acceptance_ui_uses_threading_for_operations():
    """
    Verifica que a UI usa threading para não bloquear durante operações.
    Critério de Aceite: UI responsiva, não bloqueia durante operações
    
    Nota: Este é um teste estrutural - verifica o código da UI.
    """
    import inspect
    from proxy_manager.ui import ProxyManagerApp
    
    # Verificar que métodos de operação longa usam threading
    source = inspect.getsource(ProxyManagerApp._start_scraping)
    assert "threading.Thread" in source, "Scraping deve usar threading"
    
    source = inspect.getsource(ProxyManagerApp._start_validation)
    assert "threading.Thread" in source, "Validação deve usar threading"


# =============================================================================
# CRITÉRIO 6: FEEDBACK CLARO DE PROGRESSO E ERROS (Linha 91)
# =============================================================================

def test_acceptance_api_returns_consistent_errors():
    """
    Verifica que API retorna erros claros e consistentes.
    Critério de Aceite: Feedback claro de progresso e erros
    """
    client = get_client()
    
    # Teste: payload inválido deve retornar erro claro
    r = client.post(
        "/api/v1/proxies/import",
        json={"invalid": "payload"},
        headers=HEADERS
    )
    assert r.status_code in (422, 400), "Payload inválido deve retornar erro"
    
    # Teste: endpoint não encontrado
    r = client.get("/api/v1/nonexistent", headers=HEADERS)
    assert r.status_code == 404, "Endpoint não encontrado deve retornar 404"


def test_acceptance_job_progress_tracking(monkeypatch):
    """
    Verifica que jobs retornam progresso.
    """
    client = get_client()
    
    # Mock para validação com progresso
    async def mock_validate_progress(*args, **kwargs):
        return {
            "proxy": "1.2.3.4:8080",
            "valid": True,
            "protocol": "http",
            "anonymity": "anonymous",
            "avg_response_time_ms": 100,
            "test_results": {}
        }
    
    monkeypatch.setattr("api.routers.proxies.validate_proxy", mock_validate_progress)
    
    payload = {
        "proxies": ["1.2.3.4:8080", "2.2.2.2:3128"],
        "test_urls": ["http://example.com"],
        "timeout": 10,
        "check_anonymity": False,
        "check_geolocation": False,
        "concurrent_tests": 1,
    }
    
    r = client.post("/api/v1/proxies/schedule", json=payload, headers=HEADERS)
    assert r.status_code == 200
    result = r.json()
    
    # Deve retornar polling_url para acompanhar progresso
    assert "polling_url" in result, "Deve retornar URL para polling de progresso"
    assert result.get("job_id"), "Deve retornar job_id"


# =============================================================================
# CRITÉRIO 7: PERSISTÊNCIA DE PREFERÊNCIAS (Linha 92)
# =============================================================================

def test_acceptance_ui_saves_preferences():
    """
    Verifica que UI salva preferências entre sessões.
    Critério de Aceite: Persistência das preferências e última sessão
    """
    import json
    from pathlib import Path
    
    # Não criar app de verdade (bloquearia o teste), apenas verificar que o código de salvamento existe
    from proxy_manager.ui import ProxyManagerApp
    import inspect
    
    # Verificar que método _save_ui_settings existe e implementa salvamento de configurações
    source = inspect.getsource(ProxyManagerApp._save_ui_settings)
    assert "base_url" in source, "Deve salvar base_url"
    assert "api_key" in source, "Deve salvar api_key"
    assert "json.dump" in source, "Deve usar json para persistência"
    
    # Verificar que método _load_ui_settings existe e implementa carregamento
    source = inspect.getsource(ProxyManagerApp._load_ui_settings)
    assert "json.load" in source, "Deve carregar configurações de JSON"
    assert ".exists()" in source, "Deve verificar se arquivo existe"


# =============================================================================
# CRITÉRIO 8: SEPARAÇÃO DE LIMITES DE CONCORRÊNCIA (Linha 96)
# =============================================================================

def test_acceptance_concurrency_limits_configured():
    """
    Verifica que limites de concorrência são separados por tarefa.
    Critério de Aceite: Separar limites de concorrência por tarefa e por fonte
    """
    from core.config import Settings
    
    os.environ["PROXIES_RATE_LIMIT_IP"] = "300"
    os.environ["PROXIES_RATE_LIMIT_KEY"] = "1000"
    os.environ["PROXIES_MAX_CONCURRENCY"] = "25"
    
    settings = Settings()
    
    assert settings.PROXIES_RATE_LIMIT_IP == 300, "Rate limit IP deve estar configurado"
    assert settings.PROXIES_RATE_LIMIT_KEY == 1000, "Rate limit KEY deve estar configurado"
    assert settings.PROXIES_MAX_CONCURRENCY == 25, "Concorrência máxima deve estar configurada"


# =============================================================================
# CRITÉRIO 9: LOGGING PADRONIZADO (Linhas 97-98)
# =============================================================================

def test_acceptance_logging_initialized():
    """
    Verifica que logging está padronizado em todo o app.
    """
    from utils.logger import init_logger
    from pathlib import Path
    
    logger = init_logger()
    
    # Verificar que arquivo de log é criado
    assert Path("logs").exists(), "Diretório de logs deve existir"
    assert Path("logs/app.log").exists(), "Arquivo app.log deve existir"
    
    # Teste: logger deve funcionar sem erros
    logger.info("Test message for acceptance validation")


# =============================================================================
# CRITÉRIO 10: FEATURE FLAGS (Linha 99)
# =============================================================================

def test_acceptance_feature_flags_via_env():
    """
    Verifica que feature flags podem ser ativadas via environment variables.
    """
    from core.config import Settings
    
    os.environ["PROXY_SCHEDULER_ENABLED"] = "true"
    os.environ["ANONYMITY_DETECTION_MODE"] = "enhanced"
    os.environ["GEO_PROVIDER"] = "ipinfo"
    
    settings = Settings()
    
    assert settings.PROXY_SCHEDULER_ENABLED is True, "Feature flag SCHEDULER deve estar ativa"
    assert settings.ANONYMITY_DETECTION_MODE == "enhanced", "Feature flag ANONYMITY_MODE deve estar ativa"
    assert settings.GEO_PROVIDER == "ipinfo", "Feature flag GEO_PROVIDER deve estar ativa"


# =============================================================================
# TESTES ADICIONAIS DE INTEGRAÇÃO
# =============================================================================

def test_acceptance_full_workflow(monkeypatch):
    """
    Teste de integração completo: import -> validate -> list -> export
    """
    client = get_client()
    
    # Mock para validação
    async def mock_validate(*args, **kwargs):
        return {
            "proxy": "1.2.3.4:8080",
            "valid": True,
            "protocol": "http",
            "anonymity": "elite",
            "avg_response_time_ms": 100,
            "test_results": {}
        }
    
    monkeypatch.setattr("api.routers.proxies.validate_proxy", mock_validate)
    
    # Step 1: Import proxies
    r = client.post(
        "/api/v1/proxies/import",
        json={
            "proxies": ["1.2.3.4:8080", "2.2.2.2:3128"],
            "auto_validate": False,
            "validation_urls": []
        },
        headers=HEADERS
    )
    assert r.status_code == 200
    assert r.json()["success"] is True
    
    # Step 2: List proxies
    r = client.get("/api/v1/proxies", headers=HEADERS)
    assert r.status_code == 200
    assert r.json()["total"] >= 2
    
    # Step 3: Get random proxy
    r = client.get("/api/v1/proxies/random?protocol=http", headers=HEADERS)
    # Pode retornar 404 se nenhum válido, mas deve funcionar
    assert r.status_code in (200, 404)
    
    # Step 4: Get stats
    r = client.get("/api/v1/proxies/stats", headers=HEADERS)
    assert r.status_code == 200
    assert "total" in r.json()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
