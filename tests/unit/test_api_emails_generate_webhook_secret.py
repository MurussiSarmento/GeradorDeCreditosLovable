import os
import time
import json
import hmac
import hashlib
from fastapi.testclient import TestClient


def build_app():
    from api.app import create_app
    app = create_app()

    class DummyClient:
        def __init__(self):
            self._seq = 0
        def get_all_domains(self):
            return {'hydra:member': []}
        def create_account(self, domain=None):
            self._seq += 1
            name = f"whsec{self._seq}"
            dom = domain or "mail.tm"
            return {
                'email': f'{name}@{dom}',
                'account_id': f'acc-{self._seq}',
                'password': 'pass',
                'token': f'tok-{self._seq}',
                'domain': dom,
                'created_at': float(self._seq),
            }
    app.state.mail_client = DummyClient()
    return app


def test_generate_emails_sync_webhook_secret_hmac(monkeypatch):
    # Ambiente
    monkeypatch.setenv('API_KEY', 'test-key')
    db_path = os.path.join('data', 'test_emails_generate_secret.db')
    monkeypatch.setenv('DATABASE_URL', f'sqlite:///{db_path}')
    try:
        if os.path.exists(db_path):
            os.remove(db_path)
    except Exception:
        pass

    calls = []

    class SpyResp:
        def __init__(self, status_code=200):
            self.status_code = status_code

    def fake_post(url, json=None, headers=None, timeout=None):
        calls.append((url, json, headers))
        return SpyResp(200)

    import requests
    monkeypatch.setattr(requests, 'post', fake_post)

    app = build_app()
    client = TestClient(app)
    headers = {'x-api-key': 'test-key'}

    secret = 'mysecret'
    r = client.post('/emails/generate', json={'quantity': 2, 'sync': True, 'webhook_url': 'https://example.test/hook', 'webhook_secret': secret}, headers=headers)
    assert r.status_code == 200, r.text
    data = r.json()
    assert 'emails' in data and data['total'] == 2

    # Verificar chamada ao webhook com assinatura
    assert len(calls) == 1
    url, payload, hdrs = calls[0]
    assert url == 'https://example.test/hook'
    assert payload['event'] == 'emails_generated'
    # Cabeçalhos presentes
    assert hdrs is not None
    assert hdrs.get('X-Webhook-Event') == 'emails_generated'
    sig = hdrs.get('X-Webhook-Signature')
    assert sig is not None
    # Assinatura HMAC correta
    body = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode('utf-8')
    expected = hmac.new(secret.encode('utf-8'), body, hashlib.sha256).hexdigest()
    assert sig == expected