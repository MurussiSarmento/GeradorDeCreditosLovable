import os
import time
import pytest
from fastapi.testclient import TestClient


# Configuração de ambiente para testes de API (isolado)
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


HEADERS = {"x-api-key": "test-key"}


def get_client() -> TestClient:
    from api.app import create_app
    return TestClient(create_app())


def test_scheduler_status_default():
    client = get_client()

    # Garantir que estado inicial esteja consistente
    r = client.get("/api/v1/proxies/scheduler/status", headers=HEADERS)
    assert r.status_code == 200
    data = r.json()
    assert data["enabled"] in (False, True)  # pode estar ligado via .env, default False
    # Campos numéricos presentes
    assert "validate_interval_min" in data
    assert "scrape_interval_min" in data
    assert "validate_batch_size" in data
    assert "scrape_quantity" in data
    assert "running" in data


def test_scheduler_update_and_status_roundtrip():
    client = get_client()

    # Desligar para garantir estado conhecido
    r0 = client.post(
        "/api/v1/proxies/scheduler/update",
        json={"enabled": False},
        headers=HEADERS,
    )
    assert r0.status_code == 200
    s0 = r0.json()
    assert s0["enabled"] is False

    # Atualizar configuração e ligar
    payload = {
        "enabled": True,
        "validate_interval_min": 1,
        "scrape_interval_min": 2,
        "validate_batch_size": 3,
        "scrape_quantity": 4,
    }
    r1 = client.post("/api/v1/proxies/scheduler/update", json=payload, headers=HEADERS)
    assert r1.status_code == 200
    s1 = r1.json()
    assert s1["enabled"] is True
    assert s1["validate_interval_min"] == 1
    assert s1["scrape_interval_min"] == 2
    assert s1["validate_batch_size"] == 3
    assert s1["scrape_quantity"] == 4
    assert s1["running"] is True

    # Consultar status novamente
    r2 = client.get("/api/v1/proxies/scheduler/status", headers=HEADERS)
    assert r2.status_code == 200
    s2 = r2.json()
    assert s2["enabled"] is True
    assert s2["running"] is True