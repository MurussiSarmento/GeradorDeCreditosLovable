from typing import Optional
from fastapi import Header, HTTPException, Depends
from core.config import Settings
import jwt


def get_settings() -> Settings:
    return Settings()


def api_key_auth(x_api_key: Optional[str] = Header(default=None), settings: Settings = Depends(get_settings)):
    if settings.API_KEY and x_api_key == settings.API_KEY:
        return {"method": "api_key", "subject": "api_key"}
    raise HTTPException(status_code=401, detail="API key inválida ou ausente")


def jwt_auth(authorization: Optional[str] = Header(default=None), settings: Settings = Depends(get_settings)):
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Token ausente")
    token = authorization.split()[1]
    try:
        payload = jwt.decode(token, settings.SECRET_KEY or "", algorithms=[settings.ALGORITHM])
        return {"method": "jwt", "subject": payload.get("sub")}
    except Exception:
        raise HTTPException(status_code=401, detail="Token inválido")


def auth_required(
    authorization: Optional[str] = Header(default=None),
    x_api_key: Optional[str] = Header(default=None),
    settings: Settings = Depends(get_settings),
):
    """Aceita Bearer JWT ou X-API-Key; prioriza JWT se presente."""
    # Tentar JWT primeiro
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split()[1]
        try:
            payload = jwt.decode(token, settings.SECRET_KEY or "", algorithms=[settings.ALGORITHM])
            return {"method": "jwt", "subject": payload.get("sub")}
        except Exception:
            # Se JWT inválido, falhar imediatamente
            raise HTTPException(status_code=401, detail="Token inválido")
    # Fallback para API key
    if settings.API_KEY and x_api_key == settings.API_KEY:
        return {"method": "api_key", "subject": "api_key"}
    raise HTTPException(status_code=401, detail="Credenciais ausentes ou inválidas")