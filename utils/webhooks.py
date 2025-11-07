from typing import Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime, timezone
import hmac
import hashlib
import json


def _compute_signature(secret_key: str, payload: Dict[str, Any]) -> str:
    try:
        body = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        return hmac.new(secret_key.encode("utf-8"), body, hashlib.sha256).hexdigest()
    except Exception:
        return ""


def trigger_webhooks_for_event(db: Session, event_name: str, payload: Dict[str, Any], timeout_seconds: int = 5) -> None:
    """Dispara webhooks ativos inscritos em `event_name`, com assinatura HMAC opcional.

    - Envia cabeçalhos `X-Webhook-Event` e opcionalmente `X-Webhook-Signature` (HMAC-SHA256)
    - Atualiza `last_triggered_at` em sucesso e incrementa `failures` em erro
    """
    try:
        from core.database.operations import get_active_webhooks_for_event
        hooks = get_active_webhooks_for_event(db, event_name)
    except Exception:
        hooks = []
    if not hooks:
        return

    import requests

    for h in hooks:
        headers = {"X-Webhook-Event": event_name}
        if getattr(h, "secret_key", None):
            sig = _compute_signature(h.secret_key, payload)
            if sig:
                headers["X-Webhook-Signature"] = sig
        success = False
        try:
            resp = requests.post(h.url, json=payload, headers=headers, timeout=timeout_seconds)
            success = 200 <= resp.status_code < 300
        except Exception:
            success = False

        # Atualizar métricas
        try:
            if success:
                h.last_triggered_at = datetime.now(timezone.utc)
            else:
                h.failures = (h.failures or 0) + 1
            db.commit()
        except Exception:
            # Não bloquear fluxo por falha de atualização de métricas
            pass