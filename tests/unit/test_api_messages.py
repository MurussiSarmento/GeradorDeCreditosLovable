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
                                    {"id": "m1", "subject": "Hello", "from": {"address": "a@b.com"}, "intro": "hi"},
                                    {"id": "m2", "subject": "World", "from": {"address": "c@d.com"}, "intro": "yo"},
                                    {"id": "m3", "subject": "!", "from": {"address": "e@f.com"}, "intro": "ho"},
                                ]
                            }
                    return Resp()
            self.session = Sess()
        def create_account(self, email=None, domain=None):
            from uuid import uuid4
            return {
                "email": f"msgs.user.{uuid4().hex[:6]}@mail.tm",
                "account_id": "acc-999",
                "password": "secret-pass",
                "token": "jwt-token",
                "domain": "mail.tm",
                "created_at": time.time(),
            }
    app.state.mail_client = DummyClient()
    return app


def test_messages_list_with_pagination(monkeypatch):
    app = build_app(monkeypatch)
    client = TestClient(app)
    headers = {"x-api-key": "test-key"}

    # Ensure account exists
    r = client.post("/emails", json={}, headers=headers)
    assert r.status_code == 200
    email = r.json()["email"]

    r = client.get(f"/messages/{email}?offset=1&limit=1", headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 3
    assert data["offset"] == 1
    assert data["limit"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["id"] == "m2"