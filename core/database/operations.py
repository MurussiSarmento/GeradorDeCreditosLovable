from typing import Optional, List, Tuple
import json
from sqlalchemy.orm import Session
from sqlalchemy import func, asc, desc
from core.database.models import EmailAccount, Message, Webhook, Proxy
from datetime import datetime, timezone
from uuid import uuid4


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


# ---- Proxy operations ----

def upsert_proxy(
    db: Session,
    ip: str,
    port: int,
    protocol: str,
    country: str | None = None,
    source: str | None = None,
) -> Proxy:
    row = (
        db.query(Proxy)
        .filter(Proxy.ip == ip, Proxy.port == port, Proxy.protocol == protocol)
        .one_or_none()
    )
    now = datetime.now(timezone.utc)
    if row is None:
        row = Proxy(
            id=str(uuid4()),
            ip=ip,
            port=port,
            protocol=protocol,
            country=country,
            source=source,
            created_at=now,
            last_updated=now,
        )
        db.add(row)
    else:
        row.country = country or row.country
        row.source = source or row.source
        row.last_updated = now
    db.commit()
    return row


def set_proxy_validation(
    db: Session,
    proxy_id: str,
    valid: bool,
    anonymity: str | None = None,
    avg_response_time_ms: float | None = None,
):
    row = db.query(Proxy).filter(Proxy.id == proxy_id).one_or_none()
    if not row:
        return
    row.valid = bool(valid)
    row.anonymity = anonymity
    row.avg_response_time_ms = avg_response_time_ms
    row.last_checked = datetime.now(timezone.utc)
    row.last_updated = row.last_checked
    db.commit()


def list_proxies(
    db: Session,
    page: int = 1,
    per_page: int = 50,
    valid_only: bool = False,
    country: str | None = None,
    protocol: str | None = None,
    anonymity: str | None = None,
    order_by: str | None = None,
    order_desc: bool = True,
) -> tuple[list[Proxy], int]:
    q = db.query(Proxy)
    if valid_only:
        q = q.filter(Proxy.valid == True)
    if country:
        q = q.filter(Proxy.country == country)
    if protocol:
        q = q.filter(Proxy.protocol == protocol)
    if anonymity:
        q = q.filter(Proxy.anonymity == anonymity)
    # Ordering support
    if order_by:
        col_map = {
            "avg_response_time_ms": Proxy.avg_response_time_ms,
            "last_checked": Proxy.last_checked,
            "created_at": Proxy.created_at,
        }
        col = col_map.get(order_by)
        if col is not None:
            q = q.order_by(desc(col) if order_desc else asc(col))
    total = q.count()
    rows = q.offset((page - 1) * per_page).limit(per_page).all()
    return rows, total


def get_proxies_filtered(
    db: Session,
    valid_only: bool = False,
    country: str | None = None,
    protocol: str | None = None,
    anonymity: str | None = None,
    order_by: str | None = None,
    order_desc: bool = True,
) -> list[Proxy]:
    q = db.query(Proxy)
    if valid_only:
        q = q.filter(Proxy.valid == True)
    if country:
        q = q.filter(Proxy.country == country)
    if protocol:
        q = q.filter(Proxy.protocol == protocol)
    if anonymity:
        q = q.filter(Proxy.anonymity == anonymity)
    # Ordering (reusar lógica da listagem)
    if order_by:
        ob = order_by.lower()
        if ob == "avg_response_time_ms":
            if order_desc:
                q = q.order_by(Proxy.avg_response_time_ms.desc().nulls_last())
            else:
                q = q.order_by(Proxy.avg_response_time_ms.asc().nulls_last())
        elif ob == "last_checked":
            if order_desc:
                q = q.order_by(Proxy.last_checked.desc().nulls_last())
            else:
                q = q.order_by(Proxy.last_checked.asc().nulls_last())
        elif ob == "created_at":
            if order_desc:
                q = q.order_by(Proxy.created_at.desc())
            else:
                q = q.order_by(Proxy.created_at.asc())
    return q.all()


def delete_proxies(db: Session, invalid_only: bool = False) -> int:
    q = db.query(Proxy)
    if invalid_only:
        q = q.filter(Proxy.valid == False)
    deleted = q.delete()
    db.commit()
    return deleted


def get_random_proxy(
    db: Session,
    protocol: str | None = None,
    country: str | None = None,
    max_response_time_ms: float | None = None,
    anonymity: str | None = None,
) -> Proxy | None:
    q = db.query(Proxy).filter(Proxy.valid == True)
    if protocol:
        q = q.filter(Proxy.protocol == protocol)
    if country:
        q = q.filter(Proxy.country == country)
    if anonymity:
        q = q.filter(Proxy.anonymity == anonymity)
    if max_response_time_ms is not None:
        q = q.filter((Proxy.avg_response_time_ms <= max_response_time_ms))
    rows = q.all()
    if not rows:
        return None
    import random
    return random.choice(rows)


def get_proxy_stats(db: Session) -> dict:
    total = db.query(func.count(Proxy.id)).scalar() or 0
    valid = db.query(func.count(Proxy.id)).filter(Proxy.valid == True).scalar() or 0
    invalid = db.query(func.count(Proxy.id)).filter(Proxy.valid == False).scalar() or 0

    prot_counts = db.query(Proxy.protocol, func.count(Proxy.id)).group_by(Proxy.protocol).all()
    by_protocol = { (p or "unknown"): int(c or 0) for p, c in prot_counts }

    country_counts = (
        db.query(Proxy.country, func.count(Proxy.id))
        .filter(Proxy.country.isnot(None))
        .group_by(Proxy.country)
        .order_by(func.count(Proxy.id).desc())
        .limit(10)
        .all()
    )
    by_country = [{"country": (c or "unknown"), "count": int(cnt or 0)} for c, cnt in country_counts]

    avg_resp = (
        db.query(func.avg(Proxy.avg_response_time_ms))
        .filter(Proxy.valid == True, Proxy.avg_response_time_ms.isnot(None))
        .scalar()
    )
    avg_response_time_ms = int(avg_resp) if avg_resp is not None else None

    # Métricas por fonte: total, válidos, inválidos, taxa de sucesso e latência média (válidos)
    src_totals = db.query(Proxy.source, func.count(Proxy.id)).group_by(Proxy.source).all()
    src_valids = (
        db.query(Proxy.source, func.count(Proxy.id))
        .filter(Proxy.valid == True)
        .group_by(Proxy.source)
        .all()
    )
    src_invalids = (
        db.query(Proxy.source, func.count(Proxy.id))
        .filter(Proxy.valid == False)
        .group_by(Proxy.source)
        .all()
    )
    src_avg_resp = (
        db.query(Proxy.source, func.avg(Proxy.avg_response_time_ms))
        .filter(Proxy.valid == True, Proxy.avg_response_time_ms.isnot(None))
        .group_by(Proxy.source)
        .all()
    )
    valid_map = { (s or "unknown"): int(c or 0) for s, c in src_valids }
    invalid_map = { (s or "unknown"): int(c or 0) for s, c in src_invalids }
    avg_map = { (s or "unknown"): (int(a) if a is not None else None) for s, a in src_avg_resp }
    by_source = []
    for s, cnt in src_totals:
        name = s or "unknown"
        v = valid_map.get(name, 0)
        inv = invalid_map.get(name, 0)
        rate = (v / cnt) if cnt else 0.0
        by_source.append({
            "source": name,
            "total": int(cnt or 0),
            "valid": v,
            "invalid": inv,
            "success_rate": round(rate, 4),
            "avg_response_time_ms": avg_map.get(name),
        })

    success_rate = round((valid / total), 4) if total else 0.0

    return {
        "total": int(total),
        "valid": int(valid),
        "invalid": int(invalid),
        "by_protocol": by_protocol,
        "by_country": by_country,
        "avg_response_time_ms": avg_response_time_ms,
        "success_rate": success_rate,
        "by_source": by_source,
    }


def get_proxies_for_validation(
    db: Session,
    limit: int = 200,
    valid_only: bool = False,
    protocols: Optional[List[str]] = None,
) -> List[Proxy]:
    """Seleciona proxies priorizando os nunca checados e os mais antigos.
    Retorna até `limit` itens.
    """
    q = db.query(Proxy)
    if valid_only:
        q = q.filter(Proxy.valid == True)
    if protocols:
        q = q.filter(Proxy.protocol.in_(protocols))
    try:
        q = q.order_by(Proxy.last_checked.asc().nullsfirst())
    except Exception:
        # Fallback caso nullsfirst não seja suportado na engine
        q = q.order_by(asc(Proxy.last_checked))
    return q.limit(limit).all()