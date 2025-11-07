from pathlib import Path
from loguru import logger


def init_logger(level: str = "INFO"):
    """Inicializa logging estruturado com rotação automática."""
    Path("logs").mkdir(parents=True, exist_ok=True)

    logger.remove()
    logger.add(
        Path("logs/app.log"),
        rotation="10 MB",
        retention="7 days",
        level=level,
        enqueue=True,
        backtrace=True,
        diagnose=False,
        format="{time} | {level} | {message} | {extra}",
    )
    logger.add(
        Path("logs/api.log"),
        rotation="10 MB",
        retention="7 days",
        level=level,
        enqueue=True,
        backtrace=False,
        diagnose=False,
        format="{time} | {level} | {message} | {extra}",
    )
    logger.add(
        Path("logs/extraction.log"),
        rotation="10 MB",
        retention="7 days",
        level=level,
        enqueue=True,
        backtrace=False,
        diagnose=False,
        format="{time} | {level} | {message} | {extra}",
    )
    return logger