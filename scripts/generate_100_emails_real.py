"""
Script: Geração de 100 e-mails reais (Mail.tm) e gravação em arquivo/DB

Este script cria 100 contas reais na API Mail.tm usando o cliente oficial
(`MailTmClient`) e persiste no banco via SQLAlchemy, com senha criptografada
quando `FERNET_KEY` está configurada (senão em texto). Também grava dois
arquivos:
 - `data/generated_real_100_emails.txt`: lista simples de e-mails
 - `data/generated_real_100_emails.csv`: e-mail, senha, token, domínio, account_id

Pré-requisitos (Windows/PowerShell):
1) (Opcional) Configure variáveis para o app:
   $env:API_KEY = "test-key"
   # Chave Fernet opcional (para criptografar senhas no DB)
   # Exemplo de geração (Python):
   #  python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   #  $env:FERNET_KEY = "<coloque_sua_chave_aqui>"

2) Execute o script:
   python scripts/generate_100_emails_real.py

3) Verifique os arquivos gerados:
   Get-Content data/generated_real_100_emails.txt | Select-Object -First 10
   Get-Content data/generated_real_100_emails.csv | Select-Object -First 10

Observações:
- Isto cria contas reais em Mail.tm. Respeitamos rate limit interno (8 req/s por padrão).
- As senhas são aleatórias e gravadas no CSV; no banco elas ficam criptografadas se `FERNET_KEY` estiver definido.
"""

import os
import sys
import time
from pathlib import Path
from typing import List, Dict

from uuid import uuid4

# Garante que o diretório raiz do projeto está no sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Imports do projeto
from core.mail_tm.client import MailTmClient
from core.database.session import get_session
from core.database.operations import get_email_account_by_email
from core.database.models import EmailAccount
from utils.crypto import encrypt_text


def generate_real_emails(quantity: int = 100) -> List[Dict[str, str]]:
    """Cria `quantity` contas reais no Mail.tm e persiste no DB.

    Retorna lista de dicts com chaves: email, password, token, domain, account_id.
    """
    # Tornar mais conservador para evitar 429 do serviço
    os.environ.setdefault("MAIL_TM_RATE_LIMIT", "1")
    client = MailTmClient()
    db = get_session()

    created: List[Dict[str, str]] = []
    attempts = 0
    max_attempts = quantity * 20  # espaço para retentativas com rate limit
    while len(created) < quantity and attempts < max_attempts:
        attempts += 1
        try:
            acc = client.create_account()
            # Evitar duplicidade
            if get_email_account_by_email(db, acc["email"]):
                continue

            enc_pass = encrypt_text(acc["password"])  # usa Fernet se disponível
            email_acc = EmailAccount(
                id=str(uuid4()),
                email=acc["email"],
                account_id=acc["account_id"],
                password_encrypted=enc_pass,
                token=acc["token"],
                domain=acc["domain"],
            )
            db.add(email_acc)
            db.commit()

            created.append(
                {
                    "email": acc["email"],
                    "password": acc["password"],
                    "token": acc["token"],
                    "domain": acc["domain"],
                    "account_id": acc["account_id"],
                }
            )
        except Exception as e:
            # Log simples em console (sem falhar toda a execução)
            print(f"[WARN] Falha ao criar conta (tentativa {attempts}): {e}")
            # Pausas maiores em caso de rate limit
            msg = str(e).lower()
            if "429" in msg or "too many requests" in msg:
                time.sleep(10.0)
            else:
                time.sleep(1.0)

    return created


def write_outputs(rows: List[Dict[str, str]]) -> None:
    Path("data").mkdir(parents=True, exist_ok=True)
    txt_path = Path("data/generated_real_100_emails.txt")
    csv_path = Path("data/generated_real_100_emails.csv")

    # TXT
    with txt_path.open("w", encoding="utf-8") as tf:
        for r in rows:
            tf.write(r["email"] + "\n")
        tf.write("\n")
        tf.write("# Instruções de teste manual\n")
        tf.write("# 1) Inicie o servidor: python main.py\n")
        tf.write("# 2) Liste e-mails: curl.exe -s \"http://localhost:8000/emails?sort_by=email&order=asc\" -H \"x-api-key: %s\"\n" % (os.environ.get("API_KEY", "test-key")))
        tf.write("# 3) Mensagens: curl.exe -s \"http://localhost:8000/messages/<email>\" -H \"x-api-key: %s\"\n" % (os.environ.get("API_KEY", "test-key")))
        tf.write("#    (Use o e-mail exibido no arquivo TXT para substituir <email>)\n")
        tf.write("# Observação: As senhas reais estão no CSV. No DB, ficam criptografadas quando FERNET_KEY está definido.\n")

    # CSV
    with csv_path.open("w", encoding="utf-8") as cf:
        cf.write("email,password,token,domain,account_id\n")
        for r in rows:
            cf.write(
                f"{r['email']},{r['password']},{r['token']},{r['domain']},{r['account_id']}\n"
            )

    print(
        f"Gerados {len(rows)} e-mails reais. Arquivos: {txt_path}, {csv_path}"
    )


def main() -> None:
    qty = int(os.environ.get("REAL_EMAILS_QUANTITY", "100"))
    rows = generate_real_emails(quantity=qty)
    write_outputs(rows)


if __name__ == "__main__":
    main()