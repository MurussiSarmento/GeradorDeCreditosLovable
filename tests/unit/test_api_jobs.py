import time
from fastapi.testclient import TestClient


def build_app(monkeypatch):
    monkeypatch.setenv("API_KEY", "test-key")
    monkeypatch.setenv("API_RATE_LIMIT_IP", "1000")
    monkeypatch.setenv("API_RATE_LIMIT_KEY", "1000")
    import time
    db_suffix = int(time.time() * 1000)
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///data/test_emails_{db_suffix}.db")
    from api.app import create_app
    app = create_app()

    class DummyClient:
        def __init__(self):
            self.cnt = 0
        def get_all_domains(self):
            return {"hydra:member": []}
        def create_account(self, email=None, domain=None):
            self.cnt += 1
            return {
                "email": f"user{self.cnt}@mail.tm",
                "account_id": f"acc-{self.cnt}",
                "password": "pass",
                "token": "token",
                "domain": "mail.tm",
                "created_at": time.time(),
            }

    app.state.mail_client = DummyClient()
    return app


def test_generate_emails_job_and_poll(monkeypatch):
    app = build_app(monkeypatch)
    client = TestClient(app)

    headers = {"x-api-key": "test-key"}
    r = client.post("/emails/generate", json={"quantity": 3}, headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "processing"
    job_id = data["job_id"]

    # Pequeno atraso para thread iniciar
    time.sleep(0.05)
    # Poll until completed
    for _ in range(200):
        s = client.get(f"/jobs/{job_id}")
        assert s.status_code == 200
        js = s.json()
        if js["status"] == "completed":
            assert js["progress"] == 1.0
            assert isinstance(js["result"], list)
            assert len(js["result"]) == 3
            break
        if js["status"] == "failed":
            assert False, f"Job falhou: {js.get('error')}"
        time.sleep(0.05)
    else:
        assert False, "Job não completou a tempo"