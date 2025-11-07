import time
from fastapi.testclient import TestClient


def build_app(monkeypatch):
    monkeypatch.setenv("API_KEY", "test-key")
    from api.app import create_app
    app = create_app()

    class DummyClient:
        def __init__(self):
            self.base_url = "https://api.mail.tm"

            class Sess:
                def get(self, url, headers=None, params=None):
                    class Resp:
                        def raise_for_status(self_inner):
                            return None

                        def json(self_inner):
                            return {
                                "hydra:member": [
                                    {
                                        "id": "o1",
                                        "subject": "Offline 1",
                                        "from": {"address": "a@b.com"},
                                        "intro": "p1",
                                        "createdAt": "2024-01-01T00:00:00Z",
                                    },
                                    {
                                        "id": "o2",
                                        "subject": "Offline 2",
                                        "from": {"address": "c@d.com"},
                                        "intro": "p2",
                                        "createdAt": "2024-01-02T00:00:00Z",
                                    },
                                ]
                            }

                    return Resp()

            self.session = Sess()

        def create_account(self, email=None, domain=None):
            from uuid import uuid4
            return {
                "email": f"offline.user.{uuid4().hex[:6]}@mail.tm",
                "account_id": "acc-555",
                "password": "secret-pass",
                "token": "jwt-token",
                "domain": "mail.tm",
                "created_at": time.time(),
            }

    app.state.mail_client = DummyClient()
    return app


def test_messages_offline_list(monkeypatch):
    app = build_app(monkeypatch)
    client = TestClient(app)
    headers = {"x-api-key": "test-key"}

    # Criar conta
    r = client.post("/emails", json={}, headers=headers)
    assert r.status_code == 200
    email = r.json()["email"]

    # Listar online para persistir
    r = client.get(f"/messages/{email}", headers=headers)
    assert r.status_code == 200
    assert r.json()["total"] == 2

    # Listar offline do SQLite
    r = client.get(f"/messages/db/{email}?offset=0&limit=1", headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 2
    assert data["offset"] == 0
    assert data["limit"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["id"] in ("o1", "o2")