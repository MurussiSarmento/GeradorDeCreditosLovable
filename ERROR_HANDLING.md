# ERROR_HANDLING - Estratégia Completa de Tratamento de Erros

## Taxonomia de Erros

### 1. Erros de Validação (4xx - Client Responsibility)

```
Categoria: Quando cliente envia dados inválidos

Exemplos:
- 400 Bad Request: Formato inválido
- 422 Unprocessable Entity: Dados válidos mas impossíveis
- 429 Too Many Requests: Rate limit excedido
- 400 Bad Quantity: Quantidade fora de range (1-10000)

Resposta:
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Erro na validação dos dados",
    "details": [
      {
        "field": "quantity",
        "value": 15000,
        "constraint": "max",
        "message": "Deve ser menor ou igual a 10000"
      }
    ]
  }
}

Ação Recomendada:
- Logar como WARNING
- Retornar imediatamente
- Cliente deve corrigir entrada
```

### 2. Erros de Autenticação e Autorização (401/403)

```
Categoria: Quando cliente não tem acesso

401 - Token inválido/expirado:
{
  "error": {
    "code": "UNAUTHORIZED",
    "message": "Token inválido ou expirado"
  }
}

403 - Sem permissão:
{
  "error": {
    "code": "FORBIDDEN",
    "message": "Você não tem permissão para acessar este recurso"
  }
}

Ação Recomendada:
- Logar como WARNING
- Cliente deve autenticar novamente
- Se API key expirada: cliente gera nova
```

### 3. Erros de Recurso Não Encontrado (404)

```
Categoria: Quando recurso solicitado não existe

{
  "error": {
    "code": "NOT_FOUND",
    "message": "Email abc123@mail.tm não encontrado"
  }
}

Ação Recomendada:
- Logar como INFO
- Cliente deve listar e tentar com email válido
- Pode ser erro transitório (email deletado)
```

### 4. Erros de Rate Limiting (429)

```
Categoria: Quando cliente faz requisições demais

{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Rate limit excedido",
    "retry_after": 60
  }
}

Headers:
Retry-After: 60
X-RateLimit-Reset: 1667000060

Ação Recomendada:
- Logar como WARNING
- Cliente implementar exponential backoff
- Esperar retry_after segundos
- Tentar novamente
```

### 5. Erros de Serviço Externo (5xx - Server Responsibility)

```
Categoria: Quando Mail.tm ou dependência falha

Tipos:
a) Mail.tm API indisponível
b) Banco de dados desconectou
c) Email service fora do ar

{
  "error": {
    "code": "EXTERNAL_SERVICE_ERROR",
    "message": "Falha ao conectar com Mail.tm API",
    "request_id": "req-uuid-123",
    "timestamp": "2025-11-06T20:30:00Z"
  }
}

Ação Recomendada:
- Logar como ERROR com stacktrace
- Retry automático com exponential backoff
- Se persistir: enviar alerta/notificação
- Retornar 503 Service Unavailable para cliente
- Cliente pode tentar novamente depois
```

### 6. Erros de Servidor Interno (500)

```
Categoria: Quando há bug ou exceção inesperada

Nunca expor detalhes internos!

{
  "error": {
    "code": "INTERNAL_ERROR",
    "message": "Erro interno do servidor",
    "request_id": "req-uuid-123"
  }
}

Ação Recomendada:
- Logar como CRITICAL com FULL stacktrace
- Não expor detalhes ao cliente
- request_id permite rastrear no log
- Cliente pode contactar suporte com request_id
- Implementar alerting (Sentry, etc)
```

## Retry Strategies

### 1. Retry Automático com Exponential Backoff

```python
import random
import time
from functools import wraps

def retry_on_exception(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff_factor: float = 2.0,
    jitter: bool = True
):
    """
    Decorador para retry com exponential backoff.
    
    Args:
        max_attempts: Máximo de tentativas
        base_delay: Delay inicial em segundos
        max_delay: Delay máximo
        backoff_factor: Multiplicador de delay
        jitter: Adicionar aleatoriedade
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                
                except Exception as e:
                    last_exception = e
                    
                    # Se última tentativa, relançar
                    if attempt == max_attempts:
                        raise
                    
                    # Calcular delay
                    delay = min(
                        base_delay * (backoff_factor ** (attempt - 1)),
                        max_delay
                    )
                    
                    # Adicionar jitter para evitar thundering herd
                    if jitter:
                        delay *= (0.5 + random.random())
                    
                    logger.warning(
                        f"Tentativa {attempt}/{max_attempts} falhou, "
                        f"aguardando {delay:.1f}s",
                        extra={
                            "attempt": attempt,
                            "delay": delay,
                            "error": str(e)
                        }
                    )
                    
                    time.sleep(delay)
            
            raise last_exception
        
        return wrapper
    return decorator

# Uso
@retry_on_exception(max_attempts=3, base_delay=1.0)
def create_email_with_retry():
    client = MailTmClient()
    return client.create_account()
```

### 2. Retry Seletivo (não retry em alguns erros)

```python
def should_retry(exception: Exception, attempt: int) -> bool:
    """Determinar se deve fazer retry baseado no tipo de erro"""
    
    # Não retry em validação (erro do cliente)
    if isinstance(exception, ValidationException):
        return False
    
    # Não retry em 404 (recurso não existe)
    if isinstance(exception, HTTPException):
        if exception.status_code == 404:
            return False
    
    # Retry em timeouts e erros de servidor
    if isinstance(exception, (TimeoutError, ConnectionError)):
        return True
    
    # Se status 5xx, retry
    if isinstance(exception, HTTPException):
        if 500 <= exception.status_code < 600:
            return True
    
    # Default: não retry
    return False

# Uso
for attempt in range(1, max_attempts + 1):
    try:
        return func(*args, **kwargs)
    except Exception as e:
        if not should_retry(e, attempt):
            raise  # Falha imediatamente
        # ... fazer retry ...
```

### 3. Circuit Breaker Pattern

```python
from enum import Enum
from datetime import datetime, timedelta

class CircuitBreakerState(Enum):
    CLOSED = "closed"      # Normal, aceita requisições
    OPEN = "open"          # Falha detectada, rejeta requisições
    HALF_OPEN = "half_open"  # Testando se recuperou

class CircuitBreaker:
    """Circuit breaker para evitar retry em cascata"""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitBreakerState.CLOSED
    
    def call(self, func, *args, **kwargs):
        """Executar função protegida por circuit breaker"""
        
        if self.state == CircuitBreakerState.OPEN:
            # Verificar se deve tentar recuperar
            if self._should_attempt_reset():
                self.state = CircuitBreakerState.HALF_OPEN
            else:
                raise CircuitBreakerOpenException(
                    f"Circuit breaker open, retry em "
                    f"{self._time_until_retry()}s"
                )
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        
        except Exception as e:
            self._on_failure()
            raise
    
    def _on_success(self):
        self.failure_count = 0
        self.state = CircuitBreakerState.CLOSED
    
    def _on_failure(self):
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitBreakerState.OPEN
            logger.error(
                "Circuit breaker ABERTO após múltiplas falhas",
                extra={"failures": self.failure_count}
            )
    
    def _should_attempt_reset(self) -> bool:
        if self.last_failure_time is None:
            return False
        
        elapsed = (datetime.now() - self.last_failure_time).total_seconds()
        return elapsed >= self.recovery_timeout
    
    def _time_until_retry(self) -> int:
        elapsed = (datetime.now() - self.last_failure_time).total_seconds()
        return int(max(0, self.recovery_timeout - elapsed))

# Uso
circuit_breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=60)

try:
    circuit_breaker.call(mail_tm_client.create_account)
except CircuitBreakerOpenException:
    logger.warning("Mail.tm indisponível, tente mais tarde")
```

## Logging de Erros

### 1. Estrutura de Log

```python
from loguru import logger
import traceback
import sys

# Configurar loguru
logger.remove()  # Remover handler padrão

# Log em arquivo
logger.add(
    "logs/app.log",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
    level="DEBUG",
    rotation="00:00",  # Rotação diária
    retention="30 days"
)

# Log em console (apenas producção)
if ENVIRONMENT == "production":
    logger.add(
        sys.stderr,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
        level="INFO"
    )
```

### 2. Logging de Diferentes Situações

```python
# Erro de validação (cliente)
logger.warning(
    "Validação falhou",
    extra={
        "request_id": request_id,
        "errors": validation_errors,
        "endpoint": "/api/v1/emails/generate"
    }
)

# Falha em serviço externo (retry)
logger.error(
    "Falha ao conectar Mail.tm",
    extra={
        "request_id": request_id,
        "attempt": 2,
        "error": str(e),
        "retry_in": 5
    }
)

# Erro inesperado (crítico)
logger.critical(
    "Erro inesperado durante criação de email",
    extra={
        "request_id": request_id,
        "email": email,
        "stacktrace": traceback.format_exc()
    }
)

# Sucesso (info)
logger.info(
    "Batch de 100 emails criados com sucesso",
    extra={
        "request_id": request_id,
        "count": 100,
        "duration_seconds": 45.23
    }
)
```

### 3. Rastreamento de Request

```python
from contextvars import ContextVar
import uuid

# Context var para rastrear request em toda stack
request_context: ContextVar[str] = ContextVar("request_id")

@app.middleware("http")
async def add_request_context(request: Request, call_next):
    request_id = str(uuid.uuid4())
    request_context.set(request_id)
    
    try:
        response = await call_next(request)
        return response
    except Exception as e:
        logger.exception(
            "Request falhou",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "error": str(e)
            }
        )
        raise

# Usar em qualquer lugar
def log_operation(message: str, **extra):
    try:
        request_id = request_context.get()
    except LookupError:
        request_id = "unknown"
    
    logger.info(
        message,
        extra={**extra, "request_id": request_id}
    )
```

## Tratamento de Erros na UI

### 1. User-Friendly Error Messages

```python
# Mapeamento de erros para mensagens amigáveis
ERROR_MESSAGES = {
    "VALIDATION_ERROR": "Os dados enviados são inválidos. Verifique e tente novamente.",
    "UNAUTHORIZED": "Sua sessão expirou. Por favor, faça login novamente.",
    "RATE_LIMIT_EXCEEDED": "Muitas requisições. Aguarde um momento e tente novamente.",
    "INTERNAL_ERROR": "Erro interno do servidor. Tente novamente mais tarde.",
    "MAIL_TM_UNAVAILABLE": "Serviço de email indisponível. Tente novamente em alguns minutos.",
}

def show_error_notification(error_code: str, request_id: str = None):
    """Mostrar notificação de erro para usuário"""
    
    message = ERROR_MESSAGES.get(error_code, "Erro desconhecido")
    
    # Se erro crítico, incluir request_id para suporte
    if error_code == "INTERNAL_ERROR" and request_id:
        message += f"\nCódigo: {request_id}"
    
    # Mostrar toast notification
    show_toast(
        type="error",
        message=message,
        duration=5000
    )
    
    # Log local
    logger.warning(f"Error notification shown: {error_code}")
```

### 2. Retry UI para Usuário

```python
def attempt_recovery(error_code: str):
    """Sugerir próximas ações após erro"""
    
    if error_code == "RATE_LIMIT_EXCEEDED":
        # Sugerir esperar
        show_dialog(
            title="Taxa Limitada",
            message="Você fez muitas requisições. Aguarde 1 minuto antes de tentar novamente.",
            buttons=["OK", "Tentar Agora"]
        )
    
    elif error_code == "UNAUTHORIZED":
        # Sugerir re-autenticação
        show_login_dialog()
    
    elif error_code == "MAIL_TM_UNAVAILABLE":
        # Sugerir retry
        if show_dialog(
            title="Serviço Indisponível",
            message="Tentar novamente em alguns minutos?",
            buttons=["Não", "Sim"]
        ):
            schedule_retry(delay=5)
```

## Monitoring e Alerting

### 1. Métricas de Erro

```python
from prometheus_client import Counter, Histogram

# Contar erros por tipo
errors_total = Counter(
    'errors_total',
    'Total de erros',
    ['error_code', 'endpoint']
)

# Latência de requisições (para detectar slowness)
request_duration = Histogram(
    'request_duration_seconds',
    'Duração de requisição',
    ['endpoint', 'status']
)

# Uso
errors_total.labels(error_code="RATE_LIMIT_EXCEEDED", endpoint="/emails/generate").inc()
```

### 2. Alerting

```python
# Se error rate > 5% em 5 min: alerta
# Se response time p95 > 1s: alerta
# Se externa API down > 2 min: alerta crítico
# Se disk space < 10%: alerta

def check_health():
    """Health check para monitoramento"""
    
    issues = []
    
    # Verificar Mail.tm
    try:
        response = requests.get(
            "https://api.mail.tm/domains",
            timeout=5
        )
        response.raise_for_status()
    except Exception as e:
        issues.append(f"mail_tm_api: unreachable ({e})")
    
    # Verificar Database
    try:
        db.execute("SELECT 1")
    except Exception as e:
        issues.append(f"database: error ({e})")
    
    # Verificar Disk Space
    import shutil
    usage = shutil.disk_usage("/")
    if usage.free < 1e9:  # < 1GB
        issues.append(f"disk: low ({usage.free / 1e9:.1f}GB)")
    
    if issues:
        return {
            "status": "degraded",
            "issues": issues
        }
    
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow()
    }
```

---

**Versão:** 1.0  
**Última Atualização:** 2025-11-06