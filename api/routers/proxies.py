from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import Dict, List
import time
import asyncio

from api.auth import auth_required
from api.schemas import (
    ProxyScrapeRequest,
    ProxyScrapeResponse,
    ProxyValidateRequest,
    ProxyValidateResponse,
    ProxyValidationResult,
    ProxyListResponse,
    ProxyRandomResponse,
    ProxyDeleteResponse,
    ProxyImportRequest,
    ProxyImportResponse,
    ProxyStatsResponse,
    ProxyScheduleRequest,
    ProxyJobResponse,
    ProxyItem,
    ProxyUpdateRequest,
    ProxyDetailResponse,
    ProxySchedulerStatusResponse,
    ProxySchedulerUpdateRequest,
)
from core.database.session import get_session
from core.database.operations import (
    upsert_proxy,
    set_proxy_validation,
    list_proxies,
    delete_proxies,
    get_random_proxy,
    get_proxies_filtered,
)
from core.database.models import Proxy as ProxyModel
from core.proxy.scraper import scrape_from_sources
from core.proxy.validator import validate_proxy


router = APIRouter(prefix="/api/v1/proxies")


def get_db() -> Session:
    return get_session()


# Helper para iniciar jobs de proxies fora do contexto de requisição
def start_proxy_job(app, payload: ProxyScheduleRequest) -> str:
    import uuid, time, threading, asyncio

    job_id = str(uuid.uuid4())
    with app.state.jobs_lock:
        app.state.jobs[job_id] = {
            "status": "processing",
            "progress": 0.0,
            "result": None,
            "error": None,
            "created_at": time.time(),
            "type": payload.type,
        }

    # Reutilizar lógica de parsing de proxies
    def parse_proxy_line(line: str) -> Dict:
        line = line.strip()
        username = None
        password = None
        protocol = None
        ip = None
        port = None
        try:
            if "://" in line:
                protocol, rest = line.split("://", 1)
                if "@" in rest:
                    cred, host = rest.split("@", 1)
                    if ":" in cred:
                        username, password = cred.split(":", 1)
                else:
                    host = rest
                ip, port = host.split(":", 1)
            else:
                ip, port = line.split(":", 1)
                protocol = "http"
        except Exception:
            return {}
        try:
            return {
                "ip": ip,
                "port": int(port),
                "protocol": protocol or "http",
                "username": username,
                "password": password,
            }
        except Exception:
            return {}

    def _run_validate_job(app_ref, job_id_ref, payload_ref):
        start = time.time()
        valid_count = 0
        total_tested = 0
        errors = None
        sum_resp_valid_ms = 0
        count_resp_valid = 0
        try:
            from core.database.session import get_session
            db_local = get_session()
            proxy_dicts = [parse_proxy_line(p) for p in (payload_ref.proxies or [])]
            proxy_dicts = [p for p in proxy_dicts if p]
            for i, pd in enumerate(proxy_dicts):
                res = asyncio.run(
                    validate_proxy(
                        pd,
                        payload_ref.test_urls,
                        timeout=payload_ref.timeout,
                        test_all_urls=payload_ref.test_all_urls,
                        check_anonymity=payload_ref.check_anonymity,
                        check_geolocation=payload_ref.check_geolocation,
                    )
                )
                total_tested += 1
                if res.get("valid"):
                    valid_count += 1
                    # Acumular latência média dos válidos, se disponível
                    avg_ms = res.get("avg_response_time_ms")
                    if isinstance(avg_ms, (int, float)):
                        sum_resp_valid_ms += float(avg_ms)
                        count_resp_valid += 1
                # Persist
                try:
                    from core.database.models import Proxy as ProxyModel
                    row = (
                        db_local.query(ProxyModel)
                        .filter(
                            ProxyModel.ip == pd.get("ip"),
                            ProxyModel.port == pd.get("port"),
                            ProxyModel.protocol == pd.get("protocol"),
                        )
                        .one_or_none()
                    )
                    if row:
                        set_proxy_validation(
                            db_local,
                            row.id,
                            res.get("valid"),
                            res.get("anonymity"),
                            res.get("avg_response_time_ms"),
                        )
                        geo = res.get("geolocation") or {}
                        country_code = geo.get("country")
                        if country_code:
                            row.country = country_code
                            db_local.commit()
                except Exception:
                    pass
                with app_ref.state.jobs_lock:
                    app_ref.state.jobs[job_id_ref]["progress"] = (i + 1) / max(len(proxy_dicts), 1)
            duration = time.time() - start
            with app_ref.state.jobs_lock:
                app_ref.state.jobs[job_id_ref]["status"] = "completed"
                app_ref.state.jobs[job_id_ref]["duration_seconds"] = duration
                avg_valid = None
                if count_resp_valid > 0:
                    avg_valid = int(sum_resp_valid_ms / count_resp_valid)
                app_ref.state.jobs[job_id_ref]["result"] = {
                    "total_tested": total_tested,
                    "valid": valid_count,
                    "invalid": total_tested - valid_count,
                    "avg_response_time_ms_valid": avg_valid,
                }
        except Exception as e:
            errors = str(e)
            with app_ref.state.jobs_lock:
                app_ref.state.jobs[job_id_ref]["status"] = "failed"
                app_ref.state.jobs[job_id_ref]["error"] = errors

    def _run_scrape_job(app_ref, job_id_ref, payload_ref):
        start = time.time()
        saved_count = 0
        total_found = 0
        by_source_counts: dict[str, int] = {}
        try:
            from core.database.session import get_session
            db_local = get_session()
            # Config defaults from settings
            settings = getattr(app_ref.state, "settings", None)
            timeout = payload_ref.scrape_timeout if getattr(payload_ref, "scrape_timeout", None) is not None else getattr(settings, "SCRAPER_TIMEOUT_SEC", 30)
            retries = payload_ref.scrape_retries if getattr(payload_ref, "scrape_retries", None) is not None else getattr(settings, "SCRAPER_MAX_RETRIES", 2)
            protocols = payload_ref.protocols or ["http", "https"]
            sources = payload_ref.sources or []
            quantity = payload_ref.quantity or 100
            # Run scraping
            proxies = asyncio.run(
                scrape_from_sources(
                    payload_ref.country,
                    protocols,
                    sources,
                    quantity,
                    timeout=timeout,
                    retries=retries,
                )
            )
            total_found = len(proxies)
            for i, p in enumerate(proxies):
                src = p.get("source") or "unknown"
                by_source_counts[src] = by_source_counts.get(src, 0) + 1
                try:
                    row = upsert_proxy(
                        db_local,
                        p.get("ip"),
                        int(p.get("port")),
                        p.get("protocol"),
                        p.get("country"),
                        p.get("source"),
                    )
                    saved_count += 1
                except Exception:
                    pass
                with app_ref.state.jobs_lock:
                    app_ref.state.jobs[job_id_ref]["progress"] = (i + 1) / max(total_found, 1)
            duration = time.time() - start
            with app_ref.state.jobs_lock:
                app_ref.state.jobs[job_id_ref]["status"] = "completed"
                app_ref.state.jobs[job_id_ref]["duration_seconds"] = duration
                app_ref.state.jobs[job_id_ref]["result"] = {
                    "total_found": total_found,
                    "saved": saved_count,
                    "by_source": by_source_counts,
                }
        except Exception as e:
            errors = str(e)
            with app_ref.state.jobs_lock:
                app_ref.state.jobs[job_id_ref]["status"] = "failed"
                app_ref.state.jobs[job_id_ref]["error"] = errors

    if payload.type == "validate":
        threading.Thread(target=_run_validate_job, args=(app, job_id, payload), daemon=True).start()
    else:
        threading.Thread(target=_run_scrape_job, args=(app, job_id, payload), daemon=True).start()

    try:
        from loguru import logger as _logger
        _logger.info(f"proxy_job_started job_id={job_id} type={payload.type}")
    except Exception:
        pass

    return job_id


@router.post("/scrape", response_model=ProxyScrapeResponse)
async def scrape_proxies(payload: ProxyScrapeRequest, request: Request, auth=Depends(auth_required), db: Session = Depends(get_db)):
    start = time.time()
    protocols = payload.protocols or ["http", "https"]
    settings = getattr(request.app.state, "settings", None)
    timeout = payload.timeout if payload.timeout is not None else getattr(settings, "SCRAPER_TIMEOUT_SEC", 30)
    retries = payload.retries if payload.retries is not None else getattr(settings, "SCRAPER_MAX_RETRIES", 2)
    proxies = await scrape_from_sources(
        payload.country,
        protocols,
        payload.sources,
        payload.quantity,
        timeout=timeout,
        retries=retries,
    )
    saved_count = 0
    items: List[ProxyItem] = []
    for p in proxies:
        try:
            row = upsert_proxy(db, p.get("ip"), int(p.get("port")), p.get("protocol"), p.get("country"), p.get("source"))
            saved_count += 1
            items.append(
                ProxyItem(
                    ip=row.ip,
                    port=row.port,
                    protocol=row.protocol,
                    country=row.country,
                    source=row.source,
                    valid=row.valid,
                    anonymity=row.anonymity,
                    last_checked=row.last_checked.isoformat() if row.last_checked else None,
                    avg_response_time_ms=int(row.avg_response_time_ms) if row.avg_response_time_ms is not None else None,
                )
            )
        except Exception:
            continue
    exec_ms = int((time.time() - start) * 1000)
    try:
        # Log simples
        from loguru import logger as _logger
        _logger.info(f"/proxies/scrape total={saved_count} ms={exec_ms}")
    except Exception:
        pass
    return ProxyScrapeResponse(success=True, total_found=saved_count, proxies=items, execution_time_ms=exec_ms)


@router.post("/validate", response_model=ProxyValidateResponse)
async def validate_proxies(payload: ProxyValidateRequest, auth=Depends(auth_required), db: Session = Depends(get_db)):
    try:
        from loguru import logger as _logger
        _logger.info("/proxies/validate started")
    except Exception:
        pass
    start = time.time()
    # Parse proxies list into dicts
    def parse_proxy_line(line: str) -> Dict:
        line = line.strip()
        username = None
        password = None
        protocol = None
        ip = None
        port = None
        try:
            if "://" in line:
                # protocol://[username:password@]ip:port
                protocol, rest = line.split("://", 1)
                if "@" in rest:
                    cred, host = rest.split("@", 1)
                    if ":" in cred:
                        username, password = cred.split(":", 1)
                else:
                    host = rest
                ip, port = host.split(":", 1)
            else:
                # ip:port
                ip, port = line.split(":", 1)
                protocol = "http"
        except Exception:
            return {}
        try:
            return {
                "ip": ip,
                "port": int(port),
                "protocol": protocol or "http",
                "username": username,
                "password": password,
            }
        except Exception:
            return {}

    proxy_dicts = [parse_proxy_line(p) for p in payload.proxies]
    proxy_dicts = [p for p in proxy_dicts if p]

    # Concurrency control
    sem = asyncio.Semaphore(payload.concurrent_tests)
    results: List[ProxyValidationResult] = []

    async def _worker(pdict: Dict) -> ProxyValidationResult:
        async with sem:
            res = await validate_proxy(
                pdict,
                payload.test_urls,
                timeout=payload.timeout,
                test_all_urls=payload.test_all_urls,
                check_anonymity=payload.check_anonymity,
                check_geolocation=payload.check_geolocation,
            )
            # Persist basic validation
            try:
                # Find row and update by identity (ip/port/protocol)
                from core.database.models import Proxy as ProxyModel
                row = (
                    db.query(ProxyModel)
                    .filter(
                        ProxyModel.ip == pdict.get("ip"),
                        ProxyModel.port == pdict.get("port"),
                        ProxyModel.protocol == pdict.get("protocol"),
                    )
                    .one_or_none()
                )
                if row:
                    set_proxy_validation(db, row.id, res.get("valid"), res.get("anonymity"), res.get("avg_response_time_ms"))
                    # Atualizar país se geolocalização retornou
                    geo = res.get("geolocation") or {}
                    country_code = geo.get("country")
                    if country_code:
                        row.country = country_code
                        db.commit()
            except Exception:
                pass
            return ProxyValidationResult(**res)

    tasks = [_worker(p) for p in proxy_dicts]
    exec_results = await asyncio.gather(*tasks)
    valid_count = sum(1 for r in exec_results if r.valid)
    invalid_count = len(exec_results) - valid_count
    exec_ms = int((time.time() - start) * 1000)
    try:
        from loguru import logger as _logger
        _logger.info(f"/proxies/validate total={len(exec_results)} valid={valid_count} ms={exec_ms}")
    except Exception:
        pass
    return ProxyValidateResponse(
        success=True,
        total_tested=len(exec_results),
        valid_proxies=valid_count,
        invalid_proxies=invalid_count,
        results=exec_results,
        execution_time_ms=exec_ms,
    )


@router.get("/stats", response_model=ProxyStatsResponse)
def proxy_stats(auth=Depends(auth_required), db: Session = Depends(get_db)):
    try:
        from loguru import logger as _logger
        _logger.info("/proxies/stats called")
    except Exception:
        pass
    from core.database.operations import get_proxy_stats
    stats = get_proxy_stats(db)
    return ProxyStatsResponse(**stats)


@router.get("", response_model=ProxyListResponse)
def list_all_proxies(
    page: int = 1,
    per_page: int = 50,
    valid_only: bool = False,
    country: str | None = None,
    protocol: str | None = None,
    anonymity: str | None = None,
    order_by: str | None = None,
    order: str = "desc",
    auth=Depends(auth_required),
    db: Session = Depends(get_db),
):
    rows, total = list_proxies(
        db,
        page=page,
        per_page=per_page,
        valid_only=valid_only,
        country=country,
        protocol=protocol,
        anonymity=anonymity,
        order_by=order_by,
        order_desc=(order.lower() == "desc"),
    )
    proxies = [
        ProxyItem(
            id=r.id,
            ip=r.ip,
            port=r.port,
            protocol=r.protocol,
            country=r.country,
            source=r.source,
            valid=r.valid,
            anonymity=r.anonymity,
            last_checked=r.last_checked.isoformat() if r.last_checked else None,
            avg_response_time_ms=int(r.avg_response_time_ms) if r.avg_response_time_ms is not None else None,
        )
        for r in rows
    ]
    total_pages = (total // per_page) + (1 if total % per_page else 0)
    return ProxyListResponse(total=total, page=page, per_page=per_page, total_pages=total_pages, proxies=proxies)


@router.get("/random", response_model=ProxyRandomResponse)
def random_proxy(
    protocol: str | None = None,
    country: str | None = None,
    max_response_time: int | None = None,
    anonymity: str | None = None,
    auth=Depends(auth_required),
    db: Session = Depends(get_db),
):
    row = get_random_proxy(db, protocol=protocol, country=country, max_response_time_ms=max_response_time, anonymity=anonymity)
    if not row:
        raise HTTPException(status_code=404, detail="No proxy found matching criteria")
    return ProxyRandomResponse(
        proxy=f"{row.ip}:{row.port}",
        protocol=row.protocol,
        country=row.country,
        anonymity=row.anonymity,
        last_checked=row.last_checked.isoformat() if row.last_checked else None,
        avg_response_time_ms=int(row.avg_response_time_ms) if row.avg_response_time_ms is not None else None,
    )


@router.get("/export")
def export_proxies(
    format: str = "json",
    valid_only: bool = False,
    country: str | None = None,
    protocol: str | None = None,
    anonymity: str | None = None,
    order_by: str | None = None,
    order: str = "desc",
    auth=Depends(auth_required),
    db: Session = Depends(get_db),
):
    rows = get_proxies_filtered(
        db,
        valid_only=valid_only,
        country=country,
        protocol=protocol,
        anonymity=anonymity,
        order_by=order_by,
        order_desc=(order.lower() == "desc"),
    )
    if format.lower() == "json":
        items = [
            {
                "ip": r.ip,
                "port": r.port,
                "protocol": r.protocol,
                "country": r.country,
                "source": r.source,
                "valid": r.valid,
                "anonymity": r.anonymity,
                "last_checked": r.last_checked.isoformat() if r.last_checked else None,
                "avg_response_time_ms": int(r.avg_response_time_ms) if r.avg_response_time_ms is not None else None,
            }
            for r in rows
        ]
        from fastapi.responses import JSONResponse
        return JSONResponse(content=items)
    elif format.lower() == "csv":
        # Exportar em linhas "ip:port" (simples, útil para re-importação)
        lines = [f"{r.ip}:{r.port}" for r in rows]
        from fastapi import Response
        return Response("\n".join(lines), media_type="text/plain")
    else:
        raise HTTPException(status_code=400, detail="Invalid format. Use 'json' or 'csv'.")


@router.get("/{id}", response_model=ProxyDetailResponse)
def get_proxy_detail(id: str, auth=Depends(auth_required), db: Session = Depends(get_db)):
    row = db.query(ProxyModel).filter(ProxyModel.id == id).one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Proxy not found")
    item = ProxyItem(
        id=row.id,
        ip=row.ip,
        port=row.port,
        protocol=row.protocol,
        country=row.country,
        source=row.source,
        valid=row.valid,
        anonymity=row.anonymity,
        last_checked=row.last_checked.isoformat() if row.last_checked else None,
        avg_response_time_ms=int(row.avg_response_time_ms) if row.avg_response_time_ms is not None else None,
    )
    return ProxyDetailResponse(proxy=item)


@router.patch("/{id}", response_model=ProxyDetailResponse)
def update_proxy(id: str, payload: ProxyUpdateRequest, auth=Depends(auth_required), db: Session = Depends(get_db)):
    row = db.query(ProxyModel).filter(ProxyModel.id == id).one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Proxy not found")
    # Atualizar campos permitidos
    updated = False
    if payload.country is not None:
        row.country = payload.country
        updated = True
    if payload.anonymity is not None:
        row.anonymity = payload.anonymity
        updated = True
    if updated:
        try:
            db.commit()
        except Exception:
            db.rollback()
            raise HTTPException(status_code=500, detail="Failed to update proxy")
    item = ProxyItem(
        id=row.id,
        ip=row.ip,
        port=row.port,
        protocol=row.protocol,
        country=row.country,
        source=row.source,
        valid=row.valid,
        anonymity=row.anonymity,
        last_checked=row.last_checked.isoformat() if row.last_checked else None,
        avg_response_time_ms=int(row.avg_response_time_ms) if row.avg_response_time_ms is not None else None,
    )
    return ProxyDetailResponse(proxy=item)


@router.post("/schedule", response_model=ProxyJobResponse)
def schedule_proxy_job(payload: ProxyScheduleRequest, request: Request, auth=Depends(auth_required)):
    app = request.app
    job_id = start_proxy_job(app, payload)
    try:
        from loguru import logger as _logger
        _logger.info(f"/proxies/schedule job_id={job_id} type={payload.type}")
    except Exception:
        pass
    return ProxyJobResponse(job_id=job_id, status=app.state.jobs[job_id]["status"], polling_url=f"/jobs/{job_id}")


@router.get("/scheduler/status", response_model=ProxySchedulerStatusResponse)
def get_scheduler_status(request: Request, auth=Depends(auth_required)):
    sched = getattr(request.app.state, "scheduler", None)
    if not sched:
        # Retorna estado padrão quando não inicializado
        return ProxySchedulerStatusResponse(
            enabled=False,
            validate_interval_min=0,
            scrape_interval_min=0,
            validate_batch_size=0,
            scrape_quantity=0,
            last_validate_at=None,
            last_scrape_at=None,
            running=False,
        )
    return ProxySchedulerStatusResponse(**sched.status())


@router.post("/scheduler/update", response_model=ProxySchedulerStatusResponse)
def update_scheduler(payload: ProxySchedulerUpdateRequest, request: Request, auth=Depends(auth_required)):
    sched = getattr(request.app.state, "scheduler", None)
    if not sched:
        # Inicializa scheduler se não existir
        from api.proxy_scheduler import ProxyScheduler
        request.app.state.scheduler = ProxyScheduler(request.app)
        sched = request.app.state.scheduler
    sched.update_config(
        enabled=payload.enabled,
        validate_interval_min=payload.validate_interval_min,
        scrape_interval_min=payload.scrape_interval_min,
        validate_batch_size=payload.validate_batch_size,
        scrape_quantity=payload.scrape_quantity,
    )
    # Gerenciar ciclo de vida
    if sched.enabled:
        sched.start()
    else:
        sched.stop()
    return ProxySchedulerStatusResponse(**sched.status())


@router.delete("", response_model=ProxyDeleteResponse)
def clear_proxies(invalid_only: bool = False, auth=Depends(auth_required), db: Session = Depends(get_db)):
    deleted = delete_proxies(db, invalid_only=invalid_only)
    return ProxyDeleteResponse(success=True, deleted_count=deleted)


@router.post("/import", response_model=ProxyImportResponse)
def import_proxies(payload: ProxyImportRequest, request: Request, auth=Depends(auth_required), db: Session = Depends(get_db)):
    imported = 0
    duplicates = 0
    for line in payload.proxies:
        try:
            entry = line.strip()
            protocol = None
            host = None
            if "://" in entry:
                protocol, host = entry.split("://", 1)
            else:
                protocol = "http"
                host = entry
            ip, port = host.split(":", 1)
            row = upsert_proxy(db, ip, int(port), protocol)
            if row.created_at and (row.last_checked is None and row.valid is False):
                imported += 1
            else:
                imported += 1  # contar como importado mesmo que atualizado
        except Exception:
            duplicates += 1
            continue
    validation_started = False
    polling_url: str | None = None
    if payload.auto_validate and payload.validation_urls:
        # Disparar job de validação reutilizando o agendador de jobs
        try:
            from api.schemas import ProxyScheduleRequest
            schedule_payload = ProxyScheduleRequest(
                type="validate",
                proxies=payload.proxies,
                test_urls=payload.validation_urls,
                # usar defaults de timeout/concurrency do schema
                timeout=10,
                concurrent_tests=20,
                test_all_urls=True,
                check_anonymity=False,
                check_geolocation=False,
            )
            job_resp = schedule_proxy_job(schedule_payload, request, auth=None)
            validation_started = True
            polling_url = getattr(job_resp, "polling_url", None)
        except Exception:
            # Em caso de falha ao agendar, manter comportamento anterior e não quebrar import
            validation_started = True
            polling_url = None
    return ProxyImportResponse(success=True, imported=imported, duplicates=duplicates, validation_started=validation_started, polling_url=polling_url)