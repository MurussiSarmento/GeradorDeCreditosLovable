import time
from fastapi.testclient import TestClient


def test_format_markdownv2_escape(monkeypatch):
    monkeypatch.setenv("TELEGRAM_PARSE_MODE", "MarkdownV2")
    from utils.telegram import format_telegram_message

    subject = "[Invoice] Total: 100% _OK_"
    sender = "a(b)c@d.com"
    preview = "Use *bold* and _underline_ (test)."

    text, parse_mode = format_telegram_message(subject, sender, preview)
    assert parse_mode == "MarkdownV2"
    assert "*" in text
    assert "\\[" in text and "\\]" in text
    assert "\\_OK\\_" in text
    assert "De:" in text


def test_backoff_on_429(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "bot-abc")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat-xyz")
    monkeypatch.setenv("TELEGRAM_PARSE_MODE", "")
    monkeypatch.setenv("TELEGRAM_RATE_LIMIT_PER_SEC", "0")
    monkeypatch.setenv("TELEGRAM_MAX_RETRIES", "2")
    monkeypatch.setenv("TELEGRAM_RETRY_BASE_DELAY_MS", "100")

    import utils.telegram as tg

    calls = {"post": 0, "sleep": []}

    class Resp429:
        status_code = 429
        def raise_for_status(self):
            return None
        def json(self):
            return {"ok": False}
        @property
        def text(self):
            return "rate limited"

    class Resp200:
        status_code = 200
        def raise_for_status(self):
            return None
        def json(self):
            return {"ok": True}
        @property
        def text(self):
            return "ok"

    def fake_post(url, json=None, timeout=None):
        calls["post"] += 1
        return Resp429() if calls["post"] == 1 else Resp200()

    def fake_sleep(sec):
        calls["sleep"].append(sec)

    monkeypatch.setattr(tg.requests, "post", fake_post)
    monkeypatch.setattr(time, "sleep", fake_sleep)

    ok = tg.send_telegram_message("test backoff")
    assert ok is True
    assert calls["post"] == 2
    assert len(calls["sleep"]) >= 1


def build_app_notifications(monkeypatch, post_spy):
    monkeypatch.setenv("API_KEY", "test-key")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "bot-123")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat-456")

    import utils.telegram as tg

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
    app = build_app_notifications(monkeypatch, post_spy)
    client = TestClient(app)
    headers = {"x-api-key": "test-key"}

    r = client.post("/emails", json={}, headers=headers)
    assert r.status_code == 200
    email = r.json()["email"]

    r = client.get(f"/messages/{email}?notify=true", headers=headers)
    assert r.status_code == 200
    assert len(post_spy) == 2
    for url, payload in post_spy:
        assert "/sendMessage" in url
        assert payload["chat_id"] == "chat-456"
        assert "De:" in payload["text"]
        assert any(sub in payload["text"] for sub in ["Sub 1", "Sub 2"])


def build_app_preview(monkeypatch, post_spy):
    monkeypatch.setenv("API_KEY", "k")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "bot-x")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat-y")
    monkeypatch.setenv("TELEGRAM_PARSE_MODE", "MarkdownV2")
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
                                        "intro": "0123456789ABCDEFGHIJ0123456789",
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
    app = build_app_preview(monkeypatch, post_spy)
    client = TestClient(app)
    headers = {"x-api-key": "k"}

    r = client.post("/emails", json={}, headers=headers)
    assert r.status_code == 200
    email = r.json()["email"]

    r = client.get(f"/messages/{email}?notify=true&preview_max=5", headers=headers)
    assert r.status_code == 200
    assert len(post_spy) == 1
    url, payload = post_spy[0]
    assert "/sendMessage" in url
    assert "…" in payload["text"]