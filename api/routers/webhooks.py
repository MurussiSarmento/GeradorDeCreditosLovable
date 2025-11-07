from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List
import json
import uuid
from datetime import timezone

from api.schemas import WebhookRegisterRequest, WebhookResponse, WebhooksListResponse
from core.database.session import get_session
from core.database.models import Webhook


router = APIRouter(prefix="/webhooks", tags=["webhooks"])


def _to_response(w: Webhook) -> WebhookResponse:
    return WebhookResponse(
        webhook_id=w.id,
        url=w.url,
        events=json.loads(w.events),
        active=w.active,
        created_at=w.created_at.isoformat(),
        last_triggered_at=w.last_triggered_at.isoformat() if w.last_triggered_at else None,
        failures=w.failures or 0,
    )


@router.post("/register", response_model=WebhookResponse)
def register_webhook(payload: WebhookRegisterRequest, db: Session = Depends(get_session)):
    if not payload.events:
        raise HTTPException(status_code=400, detail="events must not be empty")

    webhook = Webhook(
        id=str(uuid.uuid4()),
        url=payload.url,
        events=json.dumps(payload.events),
        secret_key=payload.secret_key,
        active=True,
    )
    db.add(webhook)
    db.commit()
    db.refresh(webhook)
    return _to_response(webhook)


@router.get("/", response_model=WebhooksListResponse)
def list_webhooks(
    db: Session = Depends(get_session),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    q = db.query(Webhook).order_by(Webhook.created_at.desc())
    total = q.count()
    items: List[Webhook] = q.offset(skip).limit(limit).all()
    return WebhooksListResponse(webhooks=[_to_response(w) for w in items], total=total)


@router.delete("/{webhook_id}", response_model=WebhookResponse)
def delete_webhook(webhook_id: str, db: Session = Depends(get_session)):
    w: Webhook | None = db.query(Webhook).filter(Webhook.id == webhook_id).first()
    if not w:
        raise HTTPException(status_code=404, detail="Webhook not found")
    db.delete(w)
    db.commit()
    # Return the deleted one for confirmation
    return _to_response(w)