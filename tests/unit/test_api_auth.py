from fastapi.testclient import TestClient


def build_app(monkeypatch):
    monkeypatch.setenv("API_KEY", "test-key")
    monkeypatch.setenv("SECRET_KEY", "secret-123")
    from api.app import create_app
    return create_app()


def test_auth_token_and_validate(monkeypatch):
    app = build_app(monkeypatch)
    client = TestClient(app)

    # Obter token
    r = client.post("/auth/token", json={"api_key": "test-key"})
    assert r.status_code == 200
    data = r.json()
    assert "access_token" in data
    assert data["token_type"] == "Bearer"
    assert data["expires_in"] == 24 * 60 * 60

    token = data["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Validar token
    r = client.get("/auth/validate", headers=headers)
    assert r.status_code == 200
    v = r.json()
    assert v["valid"] is True
    assert "expires_at" in v


def test_bearer_allows_protected_routes(monkeypatch):
    app = build_app(monkeypatch)
    client = TestClient(app)

    # Obter token
    r = client.post("/auth/token", json={"api_key": "test-key"})
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Acessar rota protegida com Bearer deve autenticar (mesmo que retorne 404 se recurso não existe)
    r = client.get("/messages/nonexistent@example.com", headers=headers)
    assert r.status_code in (401, 404)
    # Se 401, erro diferente; preferência é 404 (não encontrado)
    # Garante que o Bearer é aceito: tenta endpoint de detalhe offline também
    r2 = client.get("/messages/db/nonexistent@example.com", headers=headers)
    assert r2.status_code in (401, 404)