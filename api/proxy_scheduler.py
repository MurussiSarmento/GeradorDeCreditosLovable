import threading
import time
from datetime import datetime, timezone, timedelta
from typing import Optional, List

from sqlalchemy.orm import Session

from api.schemas import ProxyScheduleRequest
from api.routers.proxies import start_proxy_job
from core.database.session import get_session
from core.database.operations import get_proxies_for_validation


class ProxyScheduler:
    """Scheduler simples para scraping e validação periódica de proxies.

    Controla execuções com base em configurações dinâmicas em app.state.settings.
    """

    def __init__(self, app):
        self.app = app
        self.settings = getattr(app.state, "settings", None)
        # Configurações
        self.enabled: bool = getattr(self.settings, "PROXY_SCHEDULER_ENABLED", False)
        self.validate_interval_min: int = getattr(
            self.settings, "PROXY_SCHEDULER_VALIDATE_EVERY_MINUTES", 30
        )
        self.scrape_interval_min: int = getattr(
            self.settings, "PROXY_SCHEDULER_SCRAPE_EVERY_MINUTES", 60
        )
        self.validate_batch_size: int = getattr(
            self.settings, "PROXY_SCHEDULER_VALIDATE_MAX_COUNT", 200
        )
        self.scrape_quantity: int = getattr(
            self.settings, "PROXY_SCHEDULER_SCRAPE_QUANTITY", 200
        )

        # Estado
        self.last_validate_at: Optional[datetime] = None
        self.last_scrape_at: Optional[datetime] = None
        self.last_validate_job_id: Optional[str] = None
        self.last_scrape_job_id: Optional[str] = None
        self.thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()

    def start(self) -> None:
        with self._lock:
            if self.thread and self.thread.is_alive():
                return
            self._stop_event.clear()
            self.thread = threading.Thread(target=self._run_loop, name="ProxyScheduler", daemon=True)
            self.thread.start()

    def stop(self) -> None:
        with self._lock:
            self._stop_event.set()
            if self.thread and self.thread.is_alive():
                # Aguarda saída do loop
                self.thread.join(timeout=2)
            self.thread = None

    def update_config(
        self,
        *,
        enabled: Optional[bool] = None,
        validate_interval_min: Optional[int] = None,
        scrape_interval_min: Optional[int] = None,
        validate_batch_size: Optional[int] = None,
        scrape_quantity: Optional[int] = None,
    ) -> None:
        with self._lock:
            if enabled is not None:
                self.enabled = bool(enabled)
            if validate_interval_min is not None and validate_interval_min > 0:
                self.validate_interval_min = int(validate_interval_min)
            if scrape_interval_min is not None and scrape_interval_min > 0:
                self.scrape_interval_min = int(scrape_interval_min)
            if validate_batch_size is not None and validate_batch_size > 0:
                self.validate_batch_size = int(validate_batch_size)
            if scrape_quantity is not None and scrape_quantity > 0:
                self.scrape_quantity = int(scrape_quantity)

    def status(self) -> dict:
        # Enriquecer status com métricas de última execução
        metrics_validate = None
        metrics_scrape = None
        try:
            jobs = getattr(self.app.state, "jobs", {})
            if self.last_validate_job_id and self.last_validate_job_id in jobs:
                j = jobs[self.last_validate_job_id]
                result = j.get("result") or {}
                dur = j.get("duration_seconds")
                total = result.get("total_tested")
                valid = result.get("valid")
                invalid = result.get("invalid")
                success_rate = None
                if isinstance(total, int) and total > 0 and isinstance(valid, int):
                    success_rate = round(valid / total, 4)
                metrics_validate = {
                    "job_id": self.last_validate_job_id,
                    "duration_seconds": dur,
                    "total_tested": total,
                    "valid": valid,
                    "invalid": invalid,
                    "success_rate": success_rate,
                    "avg_response_time_ms_valid": result.get("avg_response_time_ms_valid"),
                }
            if self.last_scrape_job_id and self.last_scrape_job_id in jobs:
                j = jobs[self.last_scrape_job_id]
                result = j.get("result") or {}
                dur = j.get("duration_seconds")
                metrics_scrape = {
                    "job_id": self.last_scrape_job_id,
                    "duration_seconds": dur,
                    "total_found": result.get("total_found"),
                    "saved": result.get("saved"),
                    "by_source": result.get("by_source") or {},
                }
        except Exception:
            pass
        return {
            "enabled": self.enabled,
            "validate_interval_min": self.validate_interval_min,
            "scrape_interval_min": self.scrape_interval_min,
            "validate_batch_size": self.validate_batch_size,
            "scrape_quantity": self.scrape_quantity,
            "last_validate_at": self._iso(self.last_validate_at),
            "last_scrape_at": self._iso(self.last_scrape_at),
            "running": bool(self.thread and self.thread.is_alive()),
            "last_validate_metrics": metrics_validate,
            "last_scrape_metrics": metrics_scrape,
        }

    def _iso(self, dt: Optional[datetime]) -> Optional[str]:
        return dt.astimezone(timezone.utc).isoformat() if dt else None

    def _run_loop(self) -> None:
        # Loop leve com checagens a cada 5s
        interval_sec = 5
        while not self._stop_event.is_set():
            try:
                if self.enabled:
                    now = datetime.now(timezone.utc)
                    # Validar
                    if self._due(self.last_validate_at, self.validate_interval_min, now):
                        self._run_validation_job()
                        self.last_validate_at = now
                    # Scrape
                    if self._due(self.last_scrape_at, self.scrape_interval_min, now):
                        self._run_scrape_job()
                        self.last_scrape_at = now
                time.sleep(interval_sec)
            except Exception:
                # Mantém loop mesmo com erro; logs podem ser adicionados se houver infra de logging
                time.sleep(interval_sec)

    def _due(self, last: Optional[datetime], interval_min: int, now: datetime) -> bool:
        if interval_min <= 0:
            return False
        if last is None:
            return True
        return now - last >= timedelta(minutes=interval_min)

    def _run_validation_job(self) -> None:
        # Seleciona proxies e dispara job de validação
        db: Session = get_session()
        try:
            proxies = get_proxies_for_validation(db, limit=self.validate_batch_size)
            if not proxies:
                return
            proxy_lines = [
                f"{row.protocol}://{row.ip}:{row.port}" if getattr(row, "protocol", None) else f"{row.ip}:{row.port}"
                for row in proxies
            ]
            payload = ProxyScheduleRequest(
                type="validate",
                proxies=proxy_lines,
                test_urls=["http://example.com"],
                timeout=10,
                concurrent_tests=20,
                test_all_urls=True,
                check_anonymity=False,
                check_geolocation=False,
            )
            # Start job e rastrear job_id
            job_id = start_proxy_job(self.app, payload)
            with self._lock:
                self.last_validate_job_id = job_id
        finally:
            db.close()

    def _run_scrape_job(self) -> None:
        payload = ProxyScheduleRequest(
            type="scrape",
            quantity=self.scrape_quantity,
        )
        job_id = start_proxy_job(self.app, payload)
        with self._lock:
            self.last_scrape_job_id = job_id