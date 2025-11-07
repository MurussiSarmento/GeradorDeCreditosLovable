from typing import Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel
from datetime import datetime, timedelta, timezone
import jwt

from core.config import Settings


router = APIRouter(prefix="/auth")


class TokenRequest(BaseModel):
    api_key: str


def get_settings() -> Settings:
    return Settings()


@router.post("/token")
def generate_token(payload: TokenRequest, settings: Settings = Depends(get_settings)) -> Dict[str, str | int]:
    if not settings.API_KEY:
        raise HTTPException(status_code=500, detail="API key não configurada")
    if payload.api_key != settings.API_KEY:
        raise HTTPException(status_code=401, detail="API key inválida")

    if not settings.SECRET_KEY:
        raise HTTPException(status_code=500, detail="SECRET_KEY não configurada")

    now = datetime.now(timezone.utc)
    exp = now + timedelta(hours=24)
    token_payload = {
        "sub": "api-key-user",
        "api_key_id": "key-default",
        "iss": "mail.tm-api",
        "aud": "clients",
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
        "permissions": [
            "emails:create",
            "emails:read",
            "messages:read",
            "codes:read",
        ],
    }
    token = jwt.encode(token_payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return {
        "access_token": token,
        "token_type": "Bearer",
        "expires_in": 24 * 60 * 60,
        "user_id": token_payload["sub"],
    }


@router.get("/validate")
def validate_token(authorization: Optional[str] = Header(None), settings: Settings = Depends(get_settings)) -> Dict[str, str | bool]:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Token ausente")
    token = authorization.split()[1]
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY or "",
            algorithms=[settings.ALGORITHM],
            options={"verify_aud": False},
        )
        exp_ts = payload.get("exp")
        expires_at = datetime.fromtimestamp(exp_ts, tz=timezone.utc).isoformat() if exp_ts else ""
        return {
            "valid": True,
            "api_key_id": payload.get("api_key_id", ""),
            "expires_at": expires_at,
        }
    except Exception:
        raise HTTPException(status_code=401, detail="Token inválido")