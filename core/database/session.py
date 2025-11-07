from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from core.config import Settings


def get_engine():
    settings = Settings()
    Path("data").mkdir(parents=True, exist_ok=True)
    return create_engine(settings.DATABASE_URL, future=True)


def get_session() -> Session:
    engine = get_engine()
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)()