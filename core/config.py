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
        # Limites específicos para rotas de proxies (opcionais)
        def _opt_int(name: str) -> Optional[int]:
            val = os.getenv(name)
            if val is None or val == "":
                return None
            try:
                return int(val)
            except Exception:
                return None
        self.PROXIES_RATE_LIMIT_IP: Optional[int] = _opt_int("PROXIES_RATE_LIMIT_IP")
        self.PROXIES_RATE_LIMIT_KEY: Optional[int] = _opt_int("PROXIES_RATE_LIMIT_KEY")
        self.PROXIES_MAX_CONCURRENCY: Optional[int] = _opt_int("PROXIES_MAX_CONCURRENCY")
        # Validador de Proxies (opcional)
        # Provedor de geolocalização: ip-api (default), ipapi, ipinfo
        self.GEO_PROVIDER: str = os.getenv("GEO_PROVIDER", "ip-api").strip()
        # Modo de detecção de anonimato: basic (default) ou enhanced
        self.ANONYMITY_DETECTION_MODE: str = os.getenv("ANONYMITY_DETECTION_MODE", "basic").strip()
        # Proxy Scheduler
        self.PROXY_SCHEDULER_ENABLED: bool = os.getenv("PROXY_SCHEDULER_ENABLED", "false").lower() in ("1", "true", "yes")
        self.PROXY_SCHEDULER_VALIDATE_EVERY_MINUTES: int = int(os.getenv("PROXY_SCHEDULER_VALIDATE_EVERY_MINUTES", "30"))
        self.PROXY_SCHEDULER_SCRAPE_EVERY_MINUTES: int = int(os.getenv("PROXY_SCHEDULER_SCRAPE_EVERY_MINUTES", "60"))
        self.PROXY_SCHEDULER_VALIDATE_MAX_COUNT: int = int(os.getenv("PROXY_SCHEDULER_VALIDATE_MAX_COUNT", "200"))
        self.PROXY_SCHEDULER_SCRAPE_QUANTITY: int = int(os.getenv("PROXY_SCHEDULER_SCRAPE_QUANTITY", "200"))
        # CORS
        cors_env = os.getenv("CORS_ALLOW_ORIGINS", "")
        if cors_env:
            self.CORS_ALLOW_ORIGINS: list[str] = [o.strip() for o in cors_env.split(",") if o.strip()]
        else:
            self.CORS_ALLOW_ORIGINS = []

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

        # Scraper settings
        self.SCRAPER_TIMEOUT_SEC: int = int(os.getenv("SCRAPER_TIMEOUT_SEC", "30"))
        self.SCRAPER_MAX_RETRIES: int = int(os.getenv("SCRAPER_MAX_RETRIES", "2"))
        self.SCRAPER_CACHE_TTL_SEC: int = int(os.getenv("SCRAPER_CACHE_TTL_SEC", "120"))
        self.SCRAPER_RATE_LIMIT_PER_MIN: int = int(os.getenv("SCRAPER_RATE_LIMIT_PER_MIN", "30"))