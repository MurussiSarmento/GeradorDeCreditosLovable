from typing import Optional
from dotenv import load_dotenv
import os


def load_env() -> None:
    """Carrega variáveis de ambiente do .env, se existir."""
    load_dotenv()


class Settings:
    def __init__(self) -> None:
        # Environment
        self.ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")

        # Mail.tm
        self.MAIL_TM_API_URL: str = os.getenv("MAIL_TM_API_URL", "https://api.mail.tm")
        self.MAIL_TM_RATE_LIMIT: int = int(os.getenv("MAIL_TM_RATE_LIMIT", "8"))

        # Database
        self.DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///data/emails.db")

        # API
        self.API_PORT: int = int(os.getenv("API_PORT", "5000"))
        self.API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
        self.API_KEY: Optional[str] = os.getenv("API_KEY")
        self.API_RATE_LIMIT_IP: int = int(os.getenv("API_RATE_LIMIT_IP", "100"))
        self.API_RATE_LIMIT_KEY: int = int(os.getenv("API_RATE_LIMIT_KEY", "1000"))

        # Logging
        self.LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

        # Security
        self.SECRET_KEY: Optional[str] = os.getenv("SECRET_KEY")
        self.ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
        self.FERNET_KEY: Optional[str] = os.getenv("FERNET_KEY")

        # Telegram (opcional)
        self.TELEGRAM_BOT_TOKEN: Optional[str] = os.getenv("TELEGRAM_BOT_TOKEN")
        self.TELEGRAM_CHAT_ID: Optional[str] = os.getenv("TELEGRAM_CHAT_ID")
        self.TELEGRAM_PARSE_MODE: Optional[str] = os.getenv("TELEGRAM_PARSE_MODE")
        # Telegram parâmetros de envio
        def _int_env(name: str, default: Optional[int] = None) -> Optional[int]:
            val = os.getenv(name)
            if val is None:
                return default
            try:
                return int(val)
            except Exception:
                return default
        self.TELEGRAM_RATE_LIMIT_PER_SEC: Optional[int] = _int_env("TELEGRAM_RATE_LIMIT_PER_SEC", 5)
        self.TELEGRAM_MAX_RETRIES: Optional[int] = _int_env("TELEGRAM_MAX_RETRIES", 3)
        self.TELEGRAM_RETRY_BASE_DELAY_MS: Optional[int] = _int_env("TELEGRAM_RETRY_BASE_DELAY_MS", 250)
        self.TELEGRAM_TIMEOUT_SEC: Optional[int] = _int_env("TELEGRAM_TIMEOUT_SEC", 10)
        self.TELEGRAM_PREVIEW_MAX_CHARS: Optional[int] = _int_env("TELEGRAM_PREVIEW_MAX_CHARS", 280)