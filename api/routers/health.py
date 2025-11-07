from fastapi import APIRouter
from typing import Dict
import time

router = APIRouter()
_START_TIME = time.time()


@router.get("/health")
def health() -> Dict[str, str | float]:
    """Healthcheck simples para confirmar que a API está viva."""
    uptime = time.time() - _START_TIME
    return {"status": "ok", "uptime": round(uptime, 3)}