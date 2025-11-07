import time
import json
import hmac
import hashlib
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
                            # Apenas uma mensagem para facilitar a asserção
                            return {
                                "hydra:member": [
                                    {
                                        "id": "whmsg1",
                                        "subject": "Webhook Test",
                                        "from": {"address": "sender@test.com"},
                                        "intro": "hello",
                                        "createdAt": "2024-01-01T00:00:00Z",
                                    }
                                ]
                            }

                    return Resp()

            self.session = Sess()

        def create_account(self, email=None, domain=None):
            from uuid import uuid4
            return {
                "email": f"wh.user.{uuid4().hex[:6]}@mail.tm",
                "account_id": "acc-111",
                "password": "secret-pass",
                "token": "jwt-token",
                "domain": "mail.tm",
                "created_at": time.time(),
            }

    app.state.mail_client = DummyClient()
    return app


def test_webhooks_message_received_hmac_and_failures(monkeypatch):
    app = build_app(monkeypatch)
    client = TestClient(app)
    headers = {"x-api-key": "test-key"}

    # Registrar conta
    r = client.post("/emails", json={}, headers=headers)
    assert r.status_code == 200
    email = r.json()["email"]

    # Capturar chamadas de webhook
    calls = []

    class DummyResp:
        def __init__(self, status_code):
            self.status_code = status_code

    def fake_post(url, json=None, headers=None, timeout=None):
        calls.append({"url": url, "json": json, "headers": headers})
        # Simular sucesso para URL ok e erro para URL fail
        if url == "http://hook-ok":
            return DummyResp(200)
        if url == "http://hook-fail":
            raise RuntimeError("network error")
        return DummyResp(200)

    import requests
    monkeypatch.setattr(requests, "post", fake_post)

    # Registrar webhooks para message.received
    r = client.post(
        "/webhooks/register",
        json={"url": "http://hook-ok", "events": ["message.received"], "secret_key": "s3cr3t"},
        headers=headers,
    )
    assert r.status_code == 200
    ok_hook = r.json()

    r = client.post(
        "/webhooks/register",
        json={"url": "http://hook-fail", "events": ["message.received"]},
        headers=headers,
    )
    assert r.status_code == 200
    fail_hook = r.json()

    # Disparar listagem que persiste e aciona webhooks
    r = client.get(f"/messages/{email}", headers=headers)
    assert r.status_code == 200

    # Houve chamadas
    assert len(calls) >= 2
    # Verificar cabeçalhos do evento
    evt_calls = [c for c in calls if c["json"].get("event") == "message.received"]
    assert len(evt_calls) >= 2
    for c in evt_calls:
        assert c["headers"].get("X-Webhook-Event") == "message.received"

    # Verificar assinatura HMAC para hook-ok
    ok_call = next((c for c in calls if c["url"] == "http://hook-ok"), None)
    assert ok_call is not None
    sig = ok_call["headers"].get("X-Webhook-Signature")
    assert sig is not None
    # Calcular assinatura esperada
    body = json.dumps(ok_call["json"], separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    expected = hmac.new(b"s3cr3t", body, hashlib.sha256).hexdigest()
    assert sig == expected

    # Verificar métricas: failures incrementado para hook-fail e last_triggered_at para ok
    r = client.get("/webhooks", headers=headers)
    assert r.status_code == 200
    data = r.json()
    items = data["webhooks"]
    ok_item = next(i for i in items if i["webhook_id"] == ok_hook["webhook_id"])  # type: ignore
    fail_item = next(i for i in items if i["webhook_id"] == fail_hook["webhook_id"])  # type: ignore
    assert ok_item["last_triggered_at"] is not None
    assert fail_item["failures"] >= 1