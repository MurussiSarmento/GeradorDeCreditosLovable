import time
from fastapi.testclient import TestClient


def build_app(monkeypatch):
    monkeypatch.setenv("API_KEY", "test-key")
    # Banco isolado por teste
    db_url = "sqlite:///data/test_emails_list.db"
    monkeypatch.setenv("DATABASE_URL", db_url)
    import os
    if db_url.startswith("sqlite///"):
        db_path = db_url.replace("sqlite:///", "")
        os.makedirs("data", exist_ok=True)
        try:
            if os.path.exists(db_path):
                os.remove(db_path)
        except OSError:
            pass
    from api.app import create_app
    app = create_app()

    class DummyClient:
        def __init__(self):
            self.base_url = "https://api.mail.tm"
            self._cnt = 0

            class Sess:
                def get(self, url, headers=None):
                    class Resp:
                        def json(self_inner):
                            return {"hydra:member": []}
                    return Resp()

            self.session = Sess()

        def create_account(self, email=None, domain=None):
            from uuid import uuid4
            self._cnt += 1
            return {
                "email": f"user{self._cnt}_{uuid4().hex[:6]}@mail.tm",
                "account_id": f"acc-{self._cnt}",
                "password": "secret-pass",
                "token": "jwt-token",
                "domain": "mail.tm",
                "created_at": time.time(),
            }

    app.state.mail_client = DummyClient()
    return app


def test_list_emails_pagination(monkeypatch):
    app = build_app(monkeypatch)
    client = TestClient(app)
    headers = {"x-api-key": "test-key"}

    # Baseline total antes de criar
    r0 = client.get("/emails?skip=0&limit=100", headers=headers)
    assert r0.status_code == 200
    base = r0.json()["pagination"]["total"]

    # Criar 3 contas
    for _ in range(3):
        r = client.post("/emails", json={}, headers=headers)
        assert r.status_code == 200

    # Listar com limit=2
    r = client.get("/emails?skip=0&limit=2", headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert data["pagination"]["total"] == base + 3
    assert data["pagination"]["skip"] == 0
    assert data["pagination"]["limit"] == 2
    assert len(data["items"]) == 2
    assert data["pagination"]["page"] == 1
    import math
    expected_pages_first = max(math.ceil((base + 3) / 2), 1)
    assert data["pagination"]["pages"] == expected_pages_first
    assert data["pagination"]["has_next"] is (1 < expected_pages_first)

    # Segunda página
    r2 = client.get("/emails?skip=2&limit=2", headers=headers)
    assert r2.status_code == 200
    data2 = r2.json()
    expected_second_len = min(2, max(0, (base + 3) - 2))
    assert len(data2["items"]) == expected_second_len
    assert data2["pagination"]["skip"] == 2
    assert data2["pagination"]["limit"] == 2
    assert data2["pagination"]["page"] == 2
    # Cálculo de pages baseado no total atualizado e limit=2
    import math
    expected_pages = max(math.ceil((base + 3) / 2), 1)
    assert data2["pagination"]["pages"] == expected_pages
    assert data2["pagination"]["has_next"] is (2 < expected_pages)
    assert data2["pagination"]["has_previous"] is True


# --- Agrupamento: adicionar teste de busca e ordenação no mesmo arquivo ---
import os


def create_app_with_dummy_client_for_search_order():
    from api.app import create_app
    app = create_app()

    class DummyClient:
        def __init__(self):
            self._seq = 0
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


def test_emails_search_and_ordering(monkeypatch):
    # Isolar banco
    monkeypatch.setenv('API_KEY', 'test-key')
    db_path = os.path.join('data', 'test_emails_search_order.db')
    monkeypatch.setenv('DATABASE_URL', f'sqlite:///{db_path}')
    try:
        if os.path.exists(db_path):
            os.remove(db_path)
    except Exception:
        pass

    app = create_app_with_dummy_client_for_search_order()
    from fastapi.testclient import TestClient
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
    # Espera pelo menos 2 itens com domínio beta.com
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