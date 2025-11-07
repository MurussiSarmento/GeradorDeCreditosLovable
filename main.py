from pathlib import Path
from utils.logger import init_logger
from core.config import Settings, load_env


def main() -> None:
    # Ensure directories exist
    Path("logs").mkdir(parents=True, exist_ok=True)
    Path("data").mkdir(parents=True, exist_ok=True)

    load_env()
    settings = Settings()
    logger = init_logger(level=settings.LOG_LEVEL)

    logger.info(
        "Aplicação iniciada",
        extra={
            "api_host": settings.API_HOST,
            "api_port": settings.API_PORT,
            "database": settings.DATABASE_URL,
        },
    )

    print("Projeto base inicializado. Execute scripts/init_db.py para criar o banco.")


if __name__ == "__main__":
    main()