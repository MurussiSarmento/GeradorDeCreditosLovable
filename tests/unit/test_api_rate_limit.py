from fastapi.testclient import TestClient


def test_rate_limit_api_key(monkeypatch):
    # Limitar por API key para comportamento determinístico
    monkeypatch.setenv("API_RATE_LIMIT_IP", "1000")
    monkeypatch.setenv("API_RATE_LIMIT_KEY", "1")
    from api.app import create_app
    client = TestClient(create_app())

    headers = {"x-api-key": "rate-test"}
    r1 = client.get("/health", headers=headers)
    assert r1.status_code == 200
    assert "X-RateLimit-Limit-Key" in r1.headers

    r2 = client.get("/health", headers=headers)
    assert r2.status_code == 429
    assert r2.headers.get("Retry-After") is not None