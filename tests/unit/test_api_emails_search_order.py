import os
import uuid
from fastapi.testclient import TestClient


def setup_module(module=None):
    os.environ['API_KEY'] = 'test-key'
    # Isolar banco
    db_path = os.path.join('data', 'test_emails_search_order.db')
    os.environ['DATABASE_URL'] = f'sqlite:///{db_path}'
    try:
        if os.path.exists(db_path):
            os.remove(db_path)
    except Exception:
        pass


def create_app_with_dummy_client():
    from api.app import create_app
    app = create_app()

    class DummyClient:
        def __init__(self):
            self._seq = 0
            self._emails = []
        def get_all_domains(self):
            return {'hydra:member': []}
        def create_account(self, domain=None):
            self._seq += 1
            # gerar email determinístico para testes
            name = f"user{self._seq}"
            dom = domain or "mail.tm"
            email = f"{name}@{dom}"
            account_id = f"acc-{self._seq}"
            return {
                'email': email,
                'account_id': account_id,
                'password': 'pass',
                'token': 'token',
                'domain': dom,
                'created_at': float(self._seq),
            }

    app.state.mail_client = DummyClient()
    return app


def test_emails_search_and_ordering():
    app = create_app_with_dummy_client()
    client = TestClient(app)
    headers = {'x-api-key': 'test-key'}

    # Criar 4 emails com domínios controlados
    domains = ['alpha.com', 'beta.com', 'gamma.com', 'beta.com']
    for d in domains:
        r = client.post('/emails', json={'domain': d}, headers=headers)
        assert r.status_code == 200, r.text

    # Valida busca por substring no domínio
    s1 = client.get('/emails', params={'search': 'beta', 'limit': 100}, headers=headers)
    assert s1.status_code == 200
    data1 = s1.json()
    # Espera 2 itens com domínio beta.com
    assert data1['pagination']['total'] >= 2
    emails1 = [it['email'] for it in data1['items']]
    assert any(e.endswith('@beta.com') for e in emails1)

    # Ordenação por email ascendente
    s2 = client.get('/emails', params={'sort_by': 'email', 'order': 'asc', 'limit': 100}, headers=headers)
    assert s2.status_code == 200
    items2 = s2.json()['items']
    emails2 = [it['email'] for it in items2]
    assert emails2 == sorted(emails2)

    # Ordenação por domínio descendente
    s3 = client.get('/emails', params={'sort_by': 'domain', 'order': 'desc', 'limit': 100}, headers=headers)
    assert s3.status_code == 200
    items3 = s3.json()['items']
    domains3 = [it['domain'] for it in items3]
    assert domains3 == sorted(domains3, reverse=True)