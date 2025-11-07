import time
from fastapi.testclient import TestClient


def build_app(monkeypatch, post_spy):
    monkeypatch.setenv("API_KEY", "test-key")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "bot-123")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat-456")

    # Espionar requests.post
    import utils.telegram as tg
    import requests

    class SpyResponse:
        def __init__(self):
            self._json = {"ok": True, "result": {"message_id": 1}}

        def raise_for_status(self):
            return None

        def json(self):
            return self._json

        @property
        def text(self):
            return "ok"

    def fake_post(url, json=None, timeout=None):
        post_spy.append((url, json))
        return SpyResponse()

    monkeypatch.setattr(tg.requests, "post", fake_post)

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
                                        "id": "t1",
                                        "subject": "Sub 1",
                                        "from": {"address": "a@b.com"},
                                        "intro": "p1",
                                        "createdAt": "2024-01-01T00:00:00Z",
                                    },
                                    {
                                        "id": "t2",
                                        "subject": "Sub 2",
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
                "email": f"tg.user.{uuid4().hex[:6]}@mail.tm",
                "account_id": "acc-888",
                "password": "secret-pass",
                "token": "jwt-token",
                "domain": "mail.tm",
                "created_at": time.time(),
            }

    app.state.mail_client = DummyClient()
    return app


def test_telegram_notifications_on_list(monkeypatch):
    post_spy = []
    app = build_app(monkeypatch, post_spy)
    client = TestClient(app)
    headers = {"x-api-key": "test-key"}

    r = client.post("/emails", json={}, headers=headers)
    assert r.status_code == 200
    email = r.json()["email"]

    r = client.get(f"/messages/{email}?notify=true", headers=headers)
    assert r.status_code == 200
    assert len(post_spy) == 2
    # Checar que payload contém chat_id e texto formatado (contendo assunto e remetente)
    for url, payload in post_spy:
        assert "/sendMessage" in url
        assert payload["chat_id"] == "chat-456"
        assert "De:" in payload["text"]
        assert any(sub in payload["text"] for sub in ["Sub 1", "Sub 2"])  # assunto presente