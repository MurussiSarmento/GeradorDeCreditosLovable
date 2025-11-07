# API_SPECIFICATIONS - Especificações Técnicas Detalhadas da API

## Autenticação e Segurança

### 1. Fluxo de Autenticação

```
1. Cliente registra e obtém API_KEY
2. Cliente faz POST /auth/token com api_key
3. Sistema retorna JWT access_token válido por 24 horas
4. Cliente usa token em Authorization header: "Bearer {token}"
5. Sistema valida token em todas requisições
6. Token expira: Cliente precisa fazer novo login
```

### 2. API Key Management

```python
# Estrutura de API Key
class APIKey:
    key_id: str = "key_uuid_123"
    api_key: str = "sk_live_abc123def456xyz789..."  # 40+ chars
    user_id: str = "user_uuid"
    name: str = "My Application"
    created_at: datetime
    last_used_at: datetime
    expires_at: Optional[datetime]  # None = never
    permissions: List[str]  # ["emails:create", "emails:read", ...]
    rate_limit: int = 1000  # requisições/minuto
    status: str = "active"  # ou "revoked"
```

### 3. JWT Token Payload

```json
{
  "sub": "user-uuid",
  "api_key_id": "key-uuid",
  "iss": "mail.tm-api",
  "aud": "clients",
  "exp": 1667000000,
  "iat": 1666900000,
  "permissions": ["emails:create", "emails:read", "messages:read", "codes:read"]
}
```

## Rate Limiting

### 1. Estratégia

```
- 100 requisições/minuto por IP (anonymous)
- 1.000 requisições/minuto por API Key (autenticado)
- Rate limit headers em todas respostas
```

### 2. Headers de Rate Limit

```
Response Headers:
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 876
X-RateLimit-Reset: 1667000060

429 Too Many Requests Response:
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Rate limit excedido",
    "retry_after": 60
  }
}
```

### 3. Implementação

```python
from functools import wraps
from datetime import datetime, timedelta
import time

class RateLimiter:
    def __init__(self, requests_per_minute: int = 100):
        self.requests_per_minute = requests_per_minute
        self.requests = {}  # {ip/key: [timestamp, timestamp, ...]}
    
    def is_allowed(self, identifier: str) -> tuple[bool, int]:
        """
        Verificar se requisição é permitida.
        
        Returns:
            (allowed: bool, retry_after_seconds: int)
        """
        now = time.time()
        minute_ago = now - 60
        
        if identifier not in self.requests:
            self.requests[identifier] = []
        
        # Limpar timestamps antigos
        self.requests[identifier] = [
            ts for ts in self.requests[identifier] if ts > minute_ago
        ]
        
        if len(self.requests[identifier]) >= self.requests_per_minute:
            # Calcular quando será permitido
            retry_after = int(self.requests[identifier][0] + 60 - now)
            return False, retry_after
        
        self.requests[identifier].append(now)
        return True, 0

def rate_limit_check(limiter: RateLimiter):
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            # Obter identificador (IP ou API key)
            if request.headers.get("Authorization"):
                identifier = extract_user_id(request)
            else:
                identifier = request.client.host
            
            allowed, retry_after = limiter.is_allowed(identifier)
            
            if not allowed:
                raise HTTPException(
                    status_code=429,
                    detail="Rate limit exceeded",
                    headers={"Retry-After": str(retry_after)}
                )
            
            return await func(request, *args, **kwargs)
        
        return wrapper
    return decorator
```

## Validação de Entrada

### 1. Validação Automática com Pydantic

```python
from pydantic import BaseModel, Field, validator

class GenerateEmailsRequest(BaseModel):
    quantity: int = Field(
        ...,
        ge=1,
        le=10000,
        description="Número de emails (1-10000)"
    )
    unique_domains: bool = Field(
        default=True,
        description="Cada email com domínio diferente"
    )
    auto_delete_seconds: Optional[int] = Field(
        default=None,
        ge=300,
        le=86400,
        description="Deletar após X segundos (300-86400)"
    )
    
    @validator("quantity")
    def validate_quantity(cls, v):
        if v % 1 != 0:
            raise ValueError("Quantity deve ser número inteiro")
        return v

# FastAPI automaticamente valida e retorna 422 se inválido
```

### 2. Error Responses

```
400 Bad Request:
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Erro de validação",
    "details": [
      {
        "field": "quantity",
        "type": "value_error.number.not_ge",
        "message": "Ensure this value is greater than or equal to 1"
      }
    ]
  }
}

422 Unprocessable Entity:
{
  "error": {
    "code": "VALIDATION_FAILED",
    "message": "Falha na validação dos dados"
  }
}
```

## Paginação

### 1. Offset/Limit Pagination

```python
# Query string: ?skip=0&limit=50

Response:
{
  "items": [...],
  "pagination": {
    "total": 247,
    "skip": 0,
    "limit": 50,
    "page": 1,
    "pages": 5,
    "has_next": true,
    "has_previous": false
  }
}
```

### 2. Implementação

```python
from sqlalchemy.orm import Session

def paginate_query(
    query: Query,
    skip: int = 0,
    limit: int = 50
) -> tuple[List, Dict]:
    """Paginar query e retornar items + metadata"""
    
    # Validar
    skip = max(0, skip)
    limit = min(limit, 1000)  # Max 1000 por página
    
    # Contar total
    total = query.count()
    
    # Executar query paginada
    items = query.offset(skip).limit(limit).all()
    
    # Calcular metadata
    page = (skip // limit) + 1
    pages = (total + limit - 1) // limit  # ceiling division
    
    pagination = {
        "total": total,
        "skip": skip,
        "limit": limit,
        "page": page,
        "pages": pages,
        "has_next": page < pages,
        "has_previous": page > 1
    }
    
    return items, pagination
```

## Error Handling

### 1. Exceções Customizadas

```python
class APIException(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400):
        self.code = code
        self.message = message
        self.status_code = status_code

class ValidationException(APIException):
    def __init__(self, errors: List[Dict]):
        super().__init__(
            "VALIDATION_ERROR",
            "Erro na validação dos dados",
            400
        )
        self.errors = errors

class RateLimitException(APIException):
    def __init__(self, retry_after: int):
        super().__init__(
            "RATE_LIMIT_EXCEEDED",
            "Rate limit excedido",
            429
        )
        self.retry_after = retry_after

class NotFound(APIException):
    def __init__(self, resource: str):
        super().__init__(
            "NOT_FOUND",
            f"{resource} não encontrado",
            404
        )

class Unauthorized(APIException):
    def __init__(self):
        super().__init__(
            "UNAUTHORIZED",
            "Token inválido ou expirado",
            401
        )
```

### 2. Exception Handler Global

```python
@app.exception_handler(APIException)
async def api_exception_handler(request: Request, exc: APIException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "timestamp": datetime.utcnow().isoformat(),
                "request_id": request.headers.get("X-Request-ID", "unknown")
            }
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    # Log do erro
    logger.exception(f"Unhandled exception: {exc}")
    
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "Erro interno do servidor",
                "request_id": request.headers.get("X-Request-ID", "unknown")
            }
        }
    )
```

## Async/Await para Performance

### 1. Operações Async

```python
from fastapi import FastAPI, BackgroundTasks

@app.post("/emails/generate")
async def generate_emails(
    request: GenerateEmailsRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Criar emails assincronamente"""
    
    # Iniciar job em background
    job_id = str(uuid4())
    background_tasks.add_task(
        create_emails_batch,
        job_id=job_id,
        quantity=request.quantity,
        db=db
    )
    
    return {
        "job_id": job_id,
        "status": "processing",
        "polling_url": f"/api/v1/jobs/{job_id}"
    }

@app.get("/jobs/{job_id}")
async def get_job_status(job_id: str, db: AsyncSession = Depends(get_db)):
    """Verificar status de job"""
    
    job = await db.get_job(job_id)
    
    if job.status == "completed":
        return {
            "job_id": job_id,
            "status": "completed",
            "result": job.result,
            "duration_seconds": job.duration
        }
    elif job.status == "failed":
        return {
            "job_id": job_id,
            "status": "failed",
            "error": job.error_message
        }
    else:
        return {
            "job_id": job_id,
            "status": "processing",
            "progress": job.progress,
            "eta_seconds": job.eta
        }
```

### 2. Connection Pooling

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.pool import QueuePool

# Criar engine com pool
engine = create_async_engine(
    "sqlite+aiosqlite:///./data/emails.db",
    echo=False,
    poolclass=QueuePool,
    pool_size=20,  # Máximo conexões simultâneas
    max_overflow=10,  # Conexões extras antes de esperar
    pool_pre_ping=True,  # Verificar conexão antes usar
)

async def get_db():
    async with AsyncSession(engine) as session:
        yield session
```

## CORS (Cross-Origin Resource Sharing)

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5000",
        "https://yourdomain.com"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["*"],
    expose_headers=["X-RateLimit-Limit", "X-RateLimit-Remaining"],
    max_age=3600
)
```

## Logging Estruturado

```python
from loguru import logger
import json
from contextvars import ContextVar

request_id_var: ContextVar[str] = ContextVar("request_id")

@app.middleware("http")
async def log_requests(request: Request, call_next):
    request_id = str(uuid4())
    request_id_var.set(request_id)
    
    start = time.time()
    response = await call_next(request)
    duration = time.time() - start
    
    logger.info(
        "HTTP Request",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "duration_ms": int(duration * 1000)
        }
    )
    
    return response

# Em handlers
logger.info(
    "Email created",
    extra={
        "request_id": request_id_var.get(),
        "email": email,
        "domain": domain
    }
)
```

---

**Versão:** 1.0  
**Última Atualização:** 2025-11-06