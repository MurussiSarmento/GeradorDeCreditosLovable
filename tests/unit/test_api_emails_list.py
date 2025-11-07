import time
from fastapi.testclient import TestClient


def build_app(monkeypatch):
    monkeypatch.setenv("API_KEY", "test-key")
    # Banco isolado por teste
    db_url = "sqlite:///data/test_emails_list.db"
    monkeypatch.setenv("DATABASE_URL", db_url)
    import os
    if db_url.startswith("sqlite///"):
        db_path = db_url.replace("sqlite:///", "")
        os.makedirs("data", exist_ok=True)
        try:
            if os.path.exists(db_path):
                os.remove(db_path)
        except OSError:
            pass
    from api.app import create_app
    app = create_app()

    class DummyClient:
        def __init__(self):
            self.base_url = "https://api.mail.tm"
            self._cnt = 0

            class Sess:
                def get(self, url, headers=None):
                    class Resp:
                        def json(self_inner):
                            return {"hydra:member": []}
                    return Resp()

            self.session = Sess()

        def create_account(self, email=None, domain=None):
            from uuid import uuid4
            self._cnt += 1
            return {
                "email": f"user{self._cnt}_{uuid4().hex[:6]}@mail.tm",
                "account_id": f"acc-{self._cnt}",
                "password": "secret-pass",
                "token": "jwt-token",
                "domain": "mail.tm",
                "created_at": time.time(),
            }

    app.state.mail_client = DummyClient()
    return app


def test_list_emails_pagination(monkeypatch):
    app = build_app(monkeypatch)
    client = TestClient(app)
    headers = {"x-api-key": "test-key"}

    # Baseline total antes de criar
    r0 = client.get("/emails?skip=0&limit=100", headers=headers)
    assert r0.status_code == 200
    base = r0.json()["pagination"]["total"]

    # Criar 3 contas
    for _ in range(3):
        r = client.post("/emails", json={}, headers=headers)
        assert r.status_code == 200

    # Listar com limit=2
    r = client.get("/emails?skip=0&limit=2", headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert data["pagination"]["total"] == base + 3
    assert data["pagination"]["skip"] == 0
    assert data["pagination"]["limit"] == 2
    assert len(data["items"]) == 2
    assert data["pagination"]["page"] == 1
    import math
    expected_pages_first = max(math.ceil((base + 3) / 2), 1)
    assert data["pagination"]["pages"] == expected_pages_first
    assert data["pagination"]["has_next"] is (1 < expected_pages_first)

    # Segunda página
    r2 = client.get("/emails?skip=2&limit=2", headers=headers)
    assert r2.status_code == 200
    data2 = r2.json()
    expected_second_len = min(2, max(0, (base + 3) - 2))
    assert len(data2["items"]) == expected_second_len
    assert data2["pagination"]["skip"] == 2
    assert data2["pagination"]["limit"] == 2
    assert data2["pagination"]["page"] == 2
    # Cálculo de pages baseado no total atualizado e limit=2
    import math
    expected_pages = max(math.ceil((base + 3) / 2), 1)
    assert data2["pagination"]["pages"] == expected_pages
    assert data2["pagination"]["has_next"] is (2 < expected_pages)
    assert data2["pagination"]["has_previous"] is True