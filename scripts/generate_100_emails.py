"""
Script: Geração de 100 emails e gravação em arquivo

Este script inicializa o app em modo de teste, substitui o cliente Mail.tm por
um cliente dummy (determinístico) e realiza uma chamada ao endpoint
`POST /emails/generate` com `quantity=100` e `sync=True`. Ao final, grava os
emails gerados em `data/generated_100_emails.txt`.

Instruções de uso (Windows/PowerShell):
1) Defina a variável de ambiente para a execução local do app se for testar manualmente:
   $env:API_KEY = "test-key"

2) Rode o script de geração:
   python scripts/generate_100_emails.py

3) Verifique o arquivo gerado:
   Get-Content data/generated_100_emails.txt | Select-Object -First 10

4) Teste manual (se desejar via servidor):
   - Inicie o servidor: python main.py
   - Gere emails via API:
     curl.exe -s -X POST "http://localhost:8000/emails/generate" \
       -H "Content-Type: application/json" -H "x-api-key: test-key" \
       -d '{"quantity": 100, "sync": true}'
   - Liste emails (ordenados por email ascendente):
     curl.exe -s "http://localhost:8000/emails?sort_by=email&order=asc" -H "x-api-key: test-key"
   - Busque por substring no domínio:
     curl.exe -s "http://localhost:8000/emails?search=mail.tm" -H "x-api-key: test-key"

Observação: Este script usa um banco isolado em `data/test_emails_generate_100.db`,
não impactando outros bancos de testes. O cliente dummy evita chamadas externas.
"""

import os
import sys
from pathlib import Path
from fastapi.testclient import TestClient

# Garante que o diretório raiz do projeto está no sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def build_app_for_generation(prefix: str = "gen"):
    # Isola o banco para este script
    db_url = "sqlite:///data/test_emails_generate_100.db"
    os.environ.setdefault("API_KEY", "test-key")
    os.environ["DATABASE_URL"] = db_url

    # Cria diretório data e zera o banco se existir
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)
    db_path = Path(db_url.replace("sqlite:///", ""))
    try:
        if db_path.exists():
            db_path.unlink()
    except OSError:
        pass

    from api.app import create_app
    app = create_app()

    # Cliente dummy determinístico
    class DummyClient:
        def __init__(self):
            self._seq = 0
        def get_all_domains(self):
            return {"hydra:member": []}
        def create_account(self, domain=None):
            self._seq += 1
            name = f"{prefix}{self._seq}"
            dom = domain or "mail.tm"
            return {
                "email": f"{name}@{dom}",
                "account_id": f"acc-{self._seq}",
                "password": "pass",
                "token": f"tok-{self._seq}",
                "domain": dom,
                "created_at": float(self._seq),
            }

    app.state.mail_client = DummyClient()
    return app


def main():
    app = build_app_for_generation(prefix="batch")
    client = TestClient(app)
    headers = {"x-api-key": os.environ.get("API_KEY", "test-key")}

    # Faz a geração síncrona de 100 emails
    payload = {"quantity": 100, "sync": True}
    resp = client.post("/emails/generate", json=payload, headers=headers)
    if resp.status_code != 200:
        raise SystemExit(f"Falha ao gerar emails: HTTP {resp.status_code} - {resp.text}")

    data = resp.json()
    emails = [item["email"] for item in data.get("emails", [])]

    # Grava em arquivo TXT e CSV (com senhas do cliente dummy)
    out_path = Path("data/generated_100_emails.txt")
    csv_path = Path("data/generated_100_emails.csv")

    # As senhas são fixas (cliente dummy usa "pass"). Em produção, senhas são aleatórias e não retornadas pela API.
    default_password = "pass"

    with out_path.open("w", encoding="utf-8") as f:
        for e in emails:
            f.write(e + "\n")
        f.write("\n")
        f.write("# Instruções de teste manual\n")
        f.write("# 1) Defina a chave da API nesta sessão:\n")
        f.write("#    $env:API_KEY=\"test-key\"\n")
        f.write("# 2) Inicie o servidor:\n")
        f.write("#    python main.py\n")
        f.write("# 3) Gere emails via API (opcional):\n")
        f.write("#    curl.exe -s -X POST \"http://localhost:8000/emails/generate\" -H \"Content-Type: application/json\" -H \"x-api-key: test-key\" -d '{\"quantity\": 100, \"sync\": true}'\n")
        f.write("# 4) Liste emails (ordenados por email ascendente):\n")
        f.write("#    curl.exe -s \"http://localhost:8000/emails?sort_by=email&order=asc\" -H \"x-api-key: test-key\"\n")
        f.write("# 5) Busque por substring (domínio ou email):\n")
        f.write("#    curl.exe -s \"http://localhost:8000/emails?search=mail.tm\" -H \"x-api-key: test-key\"\n")
        f.write("# Observação: As senhas no arquivo CSV associado são \"pass\" (cliente dummy). Em produção, as senhas são armazenadas criptografadas e não são retornadas pela API.\n")

    # CSV com pares email,senha
    with csv_path.open("w", encoding="utf-8") as cf:
        cf.write("email,password\n")
        for e in emails:
            cf.write(f"{e},{default_password}\n")

    print(f"Gerados {len(emails)} emails. Arquivos: {out_path}, {csv_path}")


if __name__ == "__main__":
    main()