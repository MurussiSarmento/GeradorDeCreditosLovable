from typing import Optional, List, Union
from pydantic import BaseModel, Field, EmailStr
from typing import Any


class EmailCreateRequest(BaseModel):
    domain: Optional[str] = Field(default=None, description="Domínio opcional para o email")


class EmailResponse(BaseModel):
    email: EmailStr
    domain: str
    status: str
    created_at: float


class EmailDetailResponse(EmailResponse):
    account_id: str


class EmailListItem(BaseModel):
    email: EmailStr
    domain: str
    created_at: float
    status: str
    message_count: int | None = None
    last_checked_at: float | None = None

class Pagination(BaseModel):
    total: int
    skip: int
    limit: int
    page: int
    pages: int
    has_next: bool
    has_previous: bool


class EmailsListResponse(BaseModel):
    items: List[EmailListItem]
    pagination: Pagination


class MessageItem(BaseModel):
    id: str
    subject: Optional[str]
    sender: Optional[str]
    received_at: Optional[str]


class MessagesResponse(BaseModel):
    email: EmailStr
    items: List[MessageItem]
    total: int
    offset: int
    limit: int


class MessageDetailResponse(BaseModel):
    id: str
    subject: Optional[str]
    sender: Optional[str]
    text: Optional[str]
    html: Optional[str]
    received_at: Optional[str]
    email: EmailStr


class GenerateEmailsRequest(BaseModel):
    quantity: int = Field(ge=1, le=10000, description="Número de emails a criar")
    unique_domains: bool = Field(default=True, description="Tentar domínios distintos")
    auto_delete_seconds: Optional[int] = Field(default=None, ge=300, le=86400)
    sync: bool = Field(default=False, description="Executa criação de forma síncrona e retorna resultado")
    webhook_url: Optional[str] = Field(default=None, description="URL para notificação via webhook ao concluir")
    webhook_secret: Optional[str] = Field(default=None, description="Segredo opcional para assinatura HMAC do webhook opcional")


class GenerateEmailsResponse(BaseModel):
    job_id: str
    status: str
    polling_url: str


class GenerateEmailsBatchResponse(BaseModel):
    emails: List[dict]
    total: int
    created_in_seconds: float
    batch_id: str


class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    progress: Optional[float] = None
    eta_seconds: Optional[float] = None
    duration_seconds: Optional[float] = None
    # Em jobs de emails, result é uma lista; em proxies, um dict com contagens
    result: Optional[Union[List[dict], dict]] = None
    error: Optional[str] = None


class WebhookRegisterRequest(BaseModel):
    url: str
    events: List[str]
    secret_key: Optional[str] = None


class WebhookResponse(BaseModel):
    webhook_id: str
    url: str
    events: List[str]
    active: bool
    created_at: str
    last_triggered_at: Optional[str] = None
    failures: int = 0


class WebhooksListResponse(BaseModel):
    webhooks: List[WebhookResponse]
    total: int


# ---- Proxy Manager Schemas ----

class ProxyItem(BaseModel):
    id: Optional[str] = None
    ip: str
    port: int
    protocol: str
    country: Optional[str] = None
    source: Optional[str] = None
    valid: Optional[bool] = None
    anonymity: Optional[str] = None
    last_checked: Optional[str] = None
    avg_response_time_ms: Optional[int] = None


class ProxyScrapeRequest(BaseModel):
    quantity: int = Field(default=100, ge=1, le=1000)
    country: Optional[str] = Field(default=None, description="ISO country code")
    protocols: List[str] = Field(default_factory=list)
    sources: List[str] = Field(default_factory=list)
    timeout: Optional[int] = Field(default=None, ge=1, le=120)
    retries: Optional[int] = Field(default=None, ge=0, le=5)


class ProxyScrapeResponse(BaseModel):
    success: bool
    total_found: int
    proxies: List[ProxyItem]
    execution_time_ms: int


class ProxyValidateRequest(BaseModel):
    proxies: List[str]
    test_urls: List[str]
    timeout: int = Field(default=10, ge=1, le=60)
    check_anonymity: bool = False
    check_geolocation: bool = False
    concurrent_tests: int = Field(default=20, ge=1, le=100)
    test_all_urls: bool = True


class ProxyValidationResult(BaseModel):
    proxy: str
    valid: bool
    protocol: Optional[str] = None
    anonymity: Optional[str] = None
    avg_response_time_ms: Optional[int] = None
    test_results: dict
    geolocation: Optional[dict] = None
    error: Optional[str] = None


class ProxyValidateResponse(BaseModel):
    success: bool
    total_tested: int
    valid_proxies: int
    invalid_proxies: int
    results: List[ProxyValidationResult]
    execution_time_ms: int


class ProxyListResponse(BaseModel):
    total: int
    page: int
    per_page: int
    total_pages: int
    proxies: List[ProxyItem]


class ProxyRandomResponse(BaseModel):
    proxy: str
    protocol: str
    country: Optional[str]
    anonymity: Optional[str]
    last_checked: Optional[str]
    avg_response_time_ms: Optional[int]


class ProxyUpdateRequest(BaseModel):
    country: Optional[str] = None
    anonymity: Optional[str] = None

class ProxyDetailResponse(BaseModel):
    proxy: ProxyItem


class ProxyDeleteResponse(BaseModel):
    success: bool
    deleted_count: int


class ProxyImportRequest(BaseModel):
    proxies: List[str]
    auto_validate: bool = False
    validation_urls: List[str] = Field(default_factory=list)


class ProxyImportResponse(BaseModel):
    success: bool
    imported: int
    duplicates: int
    validation_started: bool
    polling_url: Optional[str] = None


class ProxyStatsResponse(BaseModel):
    total: int
    valid: int
    invalid: int
    by_protocol: dict
    by_country: List[dict]
    avg_response_time_ms: Optional[int] = None
    success_rate: Optional[float] = None
    by_source: List[dict] = []


class ProxyScheduleRequest(BaseModel):
    type: str = Field(default="validate", pattern="^(validate|scrape)$")
    # Campos para job de validação
    proxies: List[str] = Field(default_factory=list)
    test_urls: List[str] = Field(default_factory=list)
    timeout: int = Field(default=10, ge=1, le=60)
    concurrent_tests: int = Field(default=20, ge=1, le=100)
    test_all_urls: bool = True
    check_anonymity: bool = False
    check_geolocation: bool = False
    # Campos para job de scraping (para futura expansão)
    quantity: Optional[int] = Field(default=None, ge=1, le=1000)
    country: Optional[str] = None
    protocols: List[str] = Field(default_factory=list)
    sources: List[str] = Field(default_factory=list)
    scrape_timeout: Optional[int] = Field(default=None, ge=1, le=120)
    scrape_retries: Optional[int] = Field(default=None, ge=0, le=5)


class ProxyJobResponse(BaseModel):
    job_id: str
    status: str
    polling_url: str


class ProxySchedulerStatusResponse(BaseModel):
    enabled: bool
    validate_interval_min: int
    scrape_interval_min: int
    validate_batch_size: int
    scrape_quantity: int
    last_validate_at: Optional[str] = None
    last_scrape_at: Optional[str] = None
    running: bool
    # Métricas da última execução (opcionais)
    last_validate_metrics: Optional[dict] = None
    last_scrape_metrics: Optional[dict] = None


class ProxySchedulerUpdateRequest(BaseModel):
    enabled: Optional[bool] = None
    validate_interval_min: Optional[int] = Field(default=None, gt=0)
    scrape_interval_min: Optional[int] = Field(default=None, gt=0)
    validate_batch_size: Optional[int] = Field(default=None, gt=0)
    scrape_quantity: Optional[int] = Field(default=None, gt=0)