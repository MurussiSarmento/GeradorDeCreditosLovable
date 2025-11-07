from fastapi.testclient import TestClient


def build_app(monkeypatch, post_spy):
    monkeypatch.setenv("API_KEY", "k")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "bot-x")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat-y")
    monkeypatch.setenv("TELEGRAM_PARSE_MODE", "MarkdownV2")
    # Define um valor alto no env para confirmar override por query
    monkeypatch.setenv("TELEGRAM_PREVIEW_MAX_CHARS", "999")

    import utils.telegram as tg

    class SpyResponse:
        def __init__(self):
            self._json = {"ok": True}

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

    # Monkeypatch requests.post
    import requests
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
                                        "id": "m1",
                                        "subject": "Assunto grande",
                                        "from": {"address": "a@b.com"},
                                        "intro": "0123456789ABCDEFGHIJ0123456789",  # 30+
                                        "createdAt": "2024-01-01T00:00:00Z",
                                    }
                                ]
                            }

                    return Resp()

            self.session = Sess()

        def create_account(self, email=None, domain=None):
            from uuid import uuid4
            return {
                "email": f"p.user.{uuid4().hex[:6]}@mail.tm",
                "account_id": "acc-xyz",
                "password": "pw",
                "token": "tkn",
                "domain": "mail.tm",
                "created_at": 0,
            }

    app.state.mail_client = DummyClient()
    return app


def test_preview_max_query_override(monkeypatch):
    post_spy = []
    app = build_app(monkeypatch, post_spy)
    client = TestClient(app)
    headers = {"x-api-key": "k"}

    r = client.post("/emails", json={}, headers=headers)
    assert r.status_code == 200
    email = r.json()["email"]

    # Usa preview_max=5 para forçar truncamento curto
    r = client.get(f"/messages/{email}?notify=true&preview_max=5", headers=headers)
    assert r.status_code == 200
    assert len(post_spy) == 1
    url, payload = post_spy[0]
    assert "/sendMessage" in url
    # Em MarkdownV2, reticências devem estar presentes e preview pequeno
    assert "…" in payload["text"]