from core.mail_tm.client import MailTmClient


class DummySession:
    def __init__(self, responses):
        self._responses = responses

    def get(self, url):
        return self._responses["GET"][url]

    def post(self, url, json=None):
        return self._responses["POST"][url]


class DummyResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception("HTTP Error")

    def json(self):
        return self._payload


def test_generate_random_email_and_password(monkeypatch):
    client = MailTmClient()

    # mock domains
    responses = {
        "GET": {
            f"{client.base_url}/domains": DummyResponse(
                {
                    "hydra:member": [
                        {"domain": "mail.tm", "isActive": True, "isPrivate": False}
                    ]
                }
            )
        }
    }

    dummy = DummySession(responses)
    monkeypatch.setattr(client, "session", dummy)

    email, username = client._generate_random_email()
    assert "@mail.tm" in email
    assert 12 <= len(username) <= 16