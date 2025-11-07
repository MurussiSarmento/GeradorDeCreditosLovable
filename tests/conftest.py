import os
from dotenv import load_dotenv


def pytest_configure(config):
    # Garantir que env seja carregado para testes
    load_dotenv()
    os.environ["DATABASE_URL"] = "sqlite:///data/test_emails.db"
    # Resetar banco de testes antes da suíte
    db_url = os.environ["DATABASE_URL"]
    if db_url.startswith("sqlite///"):
        db_path = db_url.replace("sqlite:///", "")
        os.makedirs("data", exist_ok=True)
        try:
            if os.path.exists(db_path):
                os.remove(db_path)
        except OSError:
            pass