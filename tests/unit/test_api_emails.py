import time
import os
from fastapi.testclient import TestClient


def build_app(monkeypatch):
    monkeypatch.setenv("API_KEY", "test-key")
    from api.app import create_app
    app = create_app()
    class DummyClient:
        def __init__(self):
            self.base_url = "https://api.mail.tm"
            class Sess:
                def get(self, url, headers=None):
                    class Resp:
                        def json(self_inner):
                            return {"hydra:member": []}
                    return Resp()
            self.session = Sess()
        def create_account(self, email=None, domain=None):
            return {
                "email": "new.user@mail.tm",
                "account_id": "acc-123",
                "password": "secret-pass",
                "token": "jwt-token",
                "domain": "mail.tm",
                "created_at": time.time(),
            }
    app.state.mail_client = DummyClient()
    return app


def test_auth_required_on_emails(monkeypatch):
    app = build_app(monkeypatch)
    client = TestClient(app)
    r = client.get("/emails/nonexistent@example.com")
    assert r.status_code == 401


def test_create_get_delete_email_flow(monkeypatch):
    app = build_app(monkeypatch)
    client = TestClient(app)
    headers = {"x-api-key": "test-key"}

    # create
    r = client.post("/emails", json={}, headers=headers)
    assert r.status_code == 200
    payload = r.json()
    assert payload["email"] == "new.user@mail.tm"
    assert payload["domain"] == "mail.tm"
    assert payload["status"] == "active"

    # get
    r = client.get(f"/emails/{payload['email']}", headers=headers)
    assert r.status_code == 200
    detail = r.json()
    assert detail["account_id"] == "acc-123"

    # delete
    r = client.delete(f"/emails/{payload['email']}", headers=headers)
    assert r.status_code == 200
    assert r.json()["status"] == "deleted"