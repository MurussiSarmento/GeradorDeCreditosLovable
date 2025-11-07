import os
import sys
sys.path.append(os.getcwd())
import time
from fastapi.testclient import TestClient

os.environ['API_KEY'] = 'test-key'

from api.app import create_app

app = create_app()

class DummyClient:
    def __init__(self):
        self.cnt = 0
    def get_all_domains(self):
        return {'hydra:member': []}
    def create_account(self, email=None, domain=None):
        self.cnt += 1
        return {
            'email': f'user{self.cnt}@mail.tm',
            'account_id': f'acc-{self.cnt}',
            'password': 'pass',
            'token': 'token',
            'domain': 'mail.tm',
            'created_at': time.time(),
        }

app.state.mail_client = DummyClient()

client = TestClient(app)
headers = {'x-api-key': 'test-key'}
r = client.post('/emails/generate', json={'quantity': 3}, headers=headers)
print('generate:', r.status_code, r.text)
job_id = r.json()['job_id']

for i in range(100):
    s = client.get(f'/jobs/{job_id}')
    print('poll', i, s.status_code, s.text)
    js = s.json()
    if js['status'] in ('completed','failed'):
        break
    time.sleep(0.1)