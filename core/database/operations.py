from typing import Optional, List, Tuple
import json
from sqlalchemy.orm import Session
from core.database.models import EmailAccount, Message, Webhook


def add_email_account(db: Session, account: EmailAccount) -> None:
    db.add(account)
    db.commit()


def get_email_account_by_email(db: Session, email: str) -> Optional[EmailAccount]:
    return db.query(EmailAccount).filter(EmailAccount.email == email).one_or_none()


def get_message_by_remote_id(db: Session, email_id: str, remote_id: str) -> Optional[Message]:
    return (
        db.query(Message)
        .filter(Message.email_id == email_id, Message.message_id_remote == remote_id)
        .one_or_none()
    )


def upsert_message(
    db: Session,
    email_id: str,
    remote_id: str,
    sender: Optional[str] = None,
    subject: Optional[str] = None,
    text_preview: Optional[str] = None,
    received_at=None,
    full_text: Optional[str] = None,
    html_content: Optional[str] = None,
) -> Tuple[Message, bool]:
    msg = get_message_by_remote_id(db, email_id, remote_id)
    if msg is None:
        # Usar remote_id como id local por simplicidade se único por email
        msg = Message(
            id=f"{email_id}:{remote_id}",
            email_id=email_id,
            message_id_remote=remote_id,
            sender=sender,
            subject=subject,
            text_preview=text_preview,
            received_at=received_at,
            full_text=full_text,
            html_content=html_content,
        )
        db.add(msg)
        created = True
    else:
        msg.sender = sender or msg.sender
        msg.subject = subject or msg.subject
        msg.text_preview = text_preview or msg.text_preview
        msg.received_at = received_at or msg.received_at
        msg.full_text = full_text or msg.full_text
        msg.html_content = html_content or msg.html_content
        created = False
    db.commit()
    return msg, created


def list_messages_for_email(db: Session, email_id: str) -> List[Message]:
    return db.query(Message).filter(Message.email_id == email_id).all()


def get_active_webhooks_for_event(db: Session, event_name: str) -> List[Webhook]:
    """Retorna webhooks ativos que estão inscritos no evento fornecido.
    Como os eventos são armazenados em texto JSON, filtramos em Python.
    """
    hooks = db.query(Webhook).filter(Webhook.active == True).all()
    result: List[Webhook] = []
    for h in hooks:
        try:
            events = json.loads(h.events or "[]")
            if event_name in events:
                result.append(h)
        except Exception:
            # Ignorar webhooks com eventos inválidos
            continue
    return result