import os
import time
from fastapi.testclient import TestClient


def setup_module(module=None):
    os.environ['API_KEY'] = 'test-key'
    db_path = os.path.join('data', 'test_emails_generate_sync.db')
    os.environ['DATABASE_URL'] = f'sqlite:///{db_path}'
    try:
        if os.path.exists(db_path):
            os.remove(db_path)
    except Exception:
        pass


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
            name = f"sync{self._seq}"
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


def test_generate_emails_sync_and_webhook(monkeypatch):
    calls = []

    class SpyResp:
        def raise_for_status(self):
            return None
        def json(self):
            return {'ok': True}

    def fake_post(url, json=None, timeout=None):
        calls.append((url, json))
        return SpyResp()

    import requests
    monkeypatch.setattr(requests, 'post', fake_post)

    app = build_app()
    client = TestClient(app)
    headers = {'x-api-key': 'test-key'}

    r = client.post('/emails/generate', json={'quantity': 3, 'sync': True, 'webhook_url': 'https://example.test/hook'}, headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert 'emails' in data and data['total'] == 3
    assert isinstance(data['emails'], list) and len(data['emails']) == 3
    # Verifica enriquecimento dos itens
    item = data['emails'][0]
    for k in ('email', 'account_id', 'token', 'domain', 'status', 'created_at'):
        assert k in item

    # Webhook foi chamado
    assert len(calls) == 1
    url, payload = calls[0]
    assert url == 'https://example.test/hook'
    assert payload['event'] == 'emails_generated'
    assert payload['total'] == 3