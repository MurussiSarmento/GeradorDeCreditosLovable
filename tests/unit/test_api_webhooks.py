import os
from fastapi.testclient import TestClient


def setup_module(module=None):
    os.environ['API_KEY'] = 'test-key'
    db_path = os.path.join('data', 'test_webhooks.db')
    os.environ['DATABASE_URL'] = f'sqlite:///{db_path}'
    try:
        if os.path.exists(db_path):
            os.remove(db_path)
    except Exception:
        pass


def build_app():
    from api.app import create_app
    return create_app()


def test_register_list_delete_webhook(monkeypatch):
    app = build_app()
    client = TestClient(app)

    # Registrar um webhook
    payload = {
        "url": "http://example.com/webhook",
        "events": ["email.created", "message.received"],
        "secret_key": "abc123",
    }
    r = client.post("/webhooks/register", json=payload)
    assert r.status_code == 200, r.text
    data = r.json()
    assert "webhook_id" in data
    assert data["url"] == payload["url"]
    assert data["events"] == payload["events"]
    assert data["active"] is True
    assert data["failures"] == 0
    webhook_id = data["webhook_id"]

    # Listar webhooks
    r_list = client.get("/webhooks?skip=0&limit=10")
    assert r_list.status_code == 200
    lst = r_list.json()
    assert lst["total"] == 1
    assert isinstance(lst["webhooks"], list)
    assert lst["webhooks"][0]["webhook_id"] == webhook_id

    # Deletar webhook
    r_del = client.delete(f"/webhooks/{webhook_id}")
    assert r_del.status_code == 200
    d = r_del.json()
    assert d["webhook_id"] == webhook_id

    # Listar novamente deve retornar 0
    r_list2 = client.get("/webhooks")
    assert r_list2.status_code == 200
    lst2 = r_list2.json()
    assert lst2["total"] == 0


def test_emails_generate_dispatch_registered_webhooks(monkeypatch):
    app = build_app()
    client = TestClient(app)

    # Dummy mail client para geração controlada
    class DummyClient:
        def __init__(self):
            self.cnt = 0
        def get_all_domains(self):
            return {"hydra:member": []}
        def create_account(self, email=None, domain=None):
            self.cnt += 1
            import time
            return {
                "email": f"user{self.cnt}@mail.tm",
                "account_id": f"acc-{self.cnt}",
                "password": "pass",
                "token": "token",
                "domain": domain or "mail.tm",
                "created_at": time.time(),
            }

    app.state.mail_client = DummyClient()

    # Registrar dois webhooks para emails_generated
    w1 = client.post("/webhooks/register", json={
        "url": "http://example.com/hook1",
        "events": ["emails_generated"],
    })
    assert w1.status_code == 200
    w2 = client.post("/webhooks/register", json={
        "url": "http://example.com/hook2",
        "events": ["emails_generated"],
    })
    assert w2.status_code == 200

    calls = []
    class SpyResp:
        def raise_for_status(self):
            return None
        def json(self):
            return {"ok": True}

    def fake_post(url, json=None, timeout=None):
        calls.append((url, json))
        return SpyResp()

    import requests
    monkeypatch.setattr(requests, 'post', fake_post)

    # Gerar emails de forma síncrona sem webhook_url específico
    headers = {"x-api-key": "test-key"}
    r = client.post("/emails/generate", json={"quantity": 2, "sync": True}, headers=headers)
    assert r.status_code == 200, r.text

    # Deve ter disparado os dois webhooks registrados
    assert len(calls) == 2
    urls = sorted([u for (u, _) in calls])
    assert urls == ["http://example.com/hook1", "http://example.com/hook2"]