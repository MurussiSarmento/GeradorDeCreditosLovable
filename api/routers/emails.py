from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Dict
from core.database.session import get_session
from core.database.models import EmailAccount
from core.database.operations import get_email_account_by_email
from api.auth import auth_required
from api.schemas import (
    EmailCreateRequest,
    EmailResponse,
    EmailDetailResponse,
    EmailListItem,
    EmailsListResponse,
    GenerateEmailsRequest,
    GenerateEmailsResponse,
    GenerateEmailsBatchResponse,
)
from core.mail_tm.client import MailTmClient
from utils.crypto import encrypt_text
from uuid import uuid4

router = APIRouter(prefix="/emails")


def get_db() -> Session:
    return get_session()


def get_client(request: Request) -> MailTmClient:
    return request.app.state.mail_client


@router.get("", response_model=EmailsListResponse)
def list_emails(
    skip: int = 0,
    limit: int = 50,
    status: str | None = None,
    search: str | None = None,
    sort_by: str = "created_at",
    order: str = "desc",
    auth=Depends(auth_required),
    db: Session = Depends(get_db),
):
    q = db.query(EmailAccount)
    if status:
        q = q.filter(EmailAccount.status == status)
    # Busca por substring em email ou domínio (case-insensitive)
    if search:
        from sqlalchemy import or_
        like = f"%{search}%"
        q = q.filter(or_(EmailAccount.email.ilike(like), EmailAccount.domain.ilike(like)))
    # Ordenação simples por created_at
    from sqlalchemy import desc, asc
    if sort_by in ("created_at", "email", "domain"):
        column = (
            EmailAccount.created_at if sort_by == "created_at" else (
                EmailAccount.email if sort_by == "email" else EmailAccount.domain
            )
        )
        q = q.order_by(desc(column) if order == "desc" else asc(column))
    total = q.count()
    rows = q.offset(skip).limit(limit).all()
    items = []
    for r in rows:
        last_checked = r.last_checked_at.timestamp() if getattr(r, "last_checked_at", None) else None
        items.append(
            EmailListItem(
                email=r.email,
                domain=r.domain,
                created_at=r.created_at.timestamp() if r.created_at else 0.0,
                status=r.status,
                message_count=getattr(r, "message_count", None),
                last_checked_at=last_checked,
            )
        )
    # Paginação derivada de skip/limit
    page = (skip // max(limit, 1)) + 1
    import math
    pages = max(math.ceil(total / max(limit, 1)), 1)
    has_next = (skip + limit) < total
    has_previous = page > 1
    return EmailsListResponse(
        items=items,
        pagination={
            "total": total,
            "skip": skip,
            "limit": limit,
            "page": page,
            "pages": pages,
            "has_next": has_next,
            "has_previous": has_previous,
        },
    )


@router.post("", response_model=EmailResponse)
def create_email(payload: EmailCreateRequest, auth=Depends(auth_required), db: Session = Depends(get_db), client: MailTmClient = Depends(get_client)):
    account = client.create_account(domain=payload.domain)
    if get_email_account_by_email(db, account["email"]):
        raise HTTPException(status_code=409, detail="Email já existe")
    enc_pass = encrypt_text(account["password"])
    email_acc = EmailAccount(
        id=str(uuid4()),
        email=account["email"],
        account_id=account["account_id"],
        password_encrypted=enc_pass,
        token=account["token"],
        domain=account["domain"],
    )
    db.add(email_acc)
    db.commit()
    return EmailResponse(email=email_acc.email, domain=email_acc.domain, status=email_acc.status, created_at=account["created_at"]) 


@router.get("/{email}", response_model=EmailDetailResponse)
def get_email(email: str, auth=Depends(auth_required), db: Session = Depends(get_db)):
    acc = get_email_account_by_email(db, email)
    if not acc:
        raise HTTPException(status_code=404, detail="Email não encontrado")
    return EmailDetailResponse(email=acc.email, domain=acc.domain, status=acc.status, created_at=acc.created_at.timestamp() if acc.created_at else 0.0, account_id=acc.account_id)


@router.delete("/{email}")
def delete_email(email: str, auth=Depends(auth_required), db: Session = Depends(get_db)) -> Dict[str, str]:
    acc = get_email_account_by_email(db, email)
    if not acc:
        raise HTTPException(status_code=404, detail="Email não encontrado")
    db.delete(acc)
    db.commit()
    return {"status": "deleted"}


@router.post("/generate", response_model=GenerateEmailsResponse | GenerateEmailsBatchResponse)
def generate_emails(
    payload: GenerateEmailsRequest,
    background_tasks: BackgroundTasks,
    request: Request,
    auth=Depends(auth_required),
):
    app = request.app
    import uuid, time

    job_id = str(uuid.uuid4())
    start_request = time.time()
    with app.state.jobs_lock:
        app.state.jobs[job_id] = {
            "status": "processing",
            "progress": 0.0,
            "result": None,
            "error": None,
            "created_at": time.time(),
            "webhook_url": payload.webhook_url,
        }

    def _run_job(app_ref, job_id_ref, payload_ref):
        start = time.time()
        created_items = []
        try:
            db_local = get_session()
            client_local = app_ref.state.mail_client
            domains = []
            if payload_ref.unique_domains:
                try:
                    domains = [d.get("domain") for d in client_local.get_all_domains()]
                except Exception:
                    domains = []
            qty = payload_ref.quantity
            for i in range(qty):
                domain = None
                if domains:
                    domain = domains[i % len(domains)]
                account = client_local.create_account(domain=domain)
                # Evitar erro de unicidade caso email já exista
                existing = get_email_account_by_email(db_local, account["email"])
                if existing:
                    with app_ref.state.jobs_lock:
                        app_ref.state.jobs[job_id_ref]["progress"] = (i + 1) / qty
                    continue
                enc_pass = encrypt_text(account["password"])
                email_acc = EmailAccount(
                    id=str(uuid4()),
                    email=account["email"],
                    account_id=account["account_id"],
                    password_encrypted=enc_pass,
                    token=account["token"],
                    domain=account["domain"],
                )
                db_local.add(email_acc)
                db_local.commit()
                created_items.append({
                    "email": email_acc.email,
                    "account_id": email_acc.account_id,
                    "domain": email_acc.domain,
                    "token": email_acc.token,
                    "status": email_acc.status,
                    "created_at": account["created_at"],
                })
                with app_ref.state.jobs_lock:
                    app_ref.state.jobs[job_id_ref]["progress"] = (i + 1) / qty

            with app_ref.state.jobs_lock:
                app_ref.state.jobs[job_id_ref].update({
                    "status": "completed",
                    "progress": 1.0,
                    "result": created_items,
                    "duration_seconds": time.time() - start,
                })
            # Webhook opcional específico da requisição
            try:
                wh = app_ref.state.jobs[job_id_ref].get("webhook_url")
                if wh:
                    import requests
                    payload_opt = {
                        "event": "emails_generated",
                        "batch_id": job_id_ref,
                        "total": len(created_items),
                        "created_in_seconds": time.time() - start,
                        "emails": created_items,
                    }
                    # Assinatura HMAC opcional quando webhook_secret fornecido na requisição
                    headers_opt = {"X-Webhook-Event": "emails_generated"}
                    try:
                        secret = getattr(payload_ref, "webhook_secret", None)
                        if secret:
                            from utils.webhooks import _compute_signature
                            sig = _compute_signature(secret, payload_opt)
                            if sig:
                                headers_opt["X-Webhook-Signature"] = sig
                    except Exception:
                        # Se não conseguir assinar, envia sem assinatura
                        pass
                    # Só inclui headers se existirem (mantém compatibilidade com testes sem headers)
                    if headers_opt:
                        try:
                            requests.post(wh, json=payload_opt, headers=headers_opt, timeout=5)
                        except TypeError:
                            # Fallback para ambientes/mock que não aceitam headers
                            requests.post(wh, json=payload_opt, timeout=5)
                    else:
                        requests.post(wh, json=payload_opt, timeout=5)
            except Exception:
                pass
            # Disparar webhooks registrados para eventos globais
            try:
                from core.database.operations import get_active_webhooks_for_event
                hooks = get_active_webhooks_for_event(db_local, "emails_generated")
                if hooks:
                    import requests
                    from datetime import datetime, timezone
                    payload_evt = {
                        "event": "emails_generated",
                        "batch_id": job_id_ref,
                        "total": len(created_items),
                        "created_in_seconds": time.time() - start,
                        "emails": created_items,
                    }
                    for h in hooks:
                        try:
                            requests.post(h.url, json=payload_evt, timeout=5)
                            # sucesso: atualizar last_triggered_at
                            try:
                                h.last_triggered_at = datetime.now(timezone.utc)
                                db_local.commit()
                            except Exception:
                                pass
                        except Exception:
                            # atualizar contador de falhas
                            try:
                                h.failures = (h.failures or 0) + 1
                                db_local.commit()
                            except Exception:
                                pass
            except Exception:
                pass
        except Exception as e:
            with app_ref.state.jobs_lock:
                app_ref.state.jobs[job_id_ref].update({
                    "status": "failed",
                    "error": str(e),
                    "duration_seconds": time.time() - start,
                })

    # Execução síncrona
    if payload.sync:
        _run_job(app, job_id, payload)
        with app.state.jobs_lock:
            res = app.state.jobs[job_id]
        return GenerateEmailsBatchResponse(
            emails=res["result"] or [],
            total=len(res["result"] or []),
            created_in_seconds=time.time() - start_request,
            batch_id=job_id,
        )
    # Execução assíncrona
    import threading
    threading.Thread(target=_run_job, args=(app, job_id, payload), daemon=True).start()
    return GenerateEmailsResponse(job_id=job_id, status="processing", polling_url=f"/jobs/{job_id}")