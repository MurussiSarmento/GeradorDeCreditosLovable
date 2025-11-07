from typing import Optional
from cryptography.fernet import Fernet, InvalidToken
from core.config import Settings


def get_fernet() -> Optional[Fernet]:
    settings = Settings()
    key = settings.FERNET_KEY
    if not key:
        return None
    try:
        return Fernet(key)
    except Exception:
        return None


def encrypt_text(plain: str) -> str:
    f = get_fernet()
    if f is None:
        return plain
    return f.encrypt(plain.encode()).decode()


def decrypt_text(token: str) -> str:
    f = get_fernet()
    if f is None:
        return token
    try:
        return f.decrypt(token.encode()).decode()
    except InvalidToken:
        return token