# API ENDPOINTS - Especificação Completa de Endpoints REST

## Visão Geral

Todos os endpoints usam **Base URL:** `http://localhost:5000/api/v1`

**Autenticação:** Header `Authorization: Bearer {token}` obrigatório em todos endpoints (exceto `/auth/token`)

**Rate Limiting:** 100 requests/minuto por IP, 1000/minuto por API key

## 1. AUTENTICAÇÃO - `/auth`

### 1.1 Gerar Token de Acesso
```
POST /auth/token
Content-Type: application/json

Request:
{
  "api_key": "your-api-key-here"
}

Response (200 OK):
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "expires_in": 86400,
  "user_id": "user-uuid"
}

Response (401 Unauthorized):
{
  "detail": "API key inválida"
}
```

**Descrição:** Obter JWT token usando API key. Token válido por 24 horas.

### 1.2 Validar Token Atual
```
GET /auth/validate
Authorization: Bearer {token}

Response (200 OK):
{
  "valid": true,
  "api_key_id": "key-uuid",
  "expires_at": "2025-11-07T19:45:00Z"
}

Response (401 Unauthorized):
{
  "detail": "Token expirado ou inválido"
}
```

---

## 2. EMAILS - `/emails`

### 2.1 Criar Múltiplos Emails
```
POST /emails/generate
Authorization: Bearer {token}
Content-Type: application/json

Request:
{
  "quantity": 10,
  "unique_domains": true,
  "auto_delete_seconds": null
}

Response (201 Created):
{
  "emails": [
    {
      "email": "abc123def@mail.tm",
      "account_id": "mail-tm-id-1",
      "domain": "mail.tm",
      "token": "auth-token-1",
      "created_at": "2025-11-06T19:45:00Z",
      "status": "active"
    },
    {
      "email": "xyz789abc@mail.tm",
      "account_id": "mail-tm-id-2",
      "domain": "mail.tm",
      "token": "auth-token-2",
      "created_at": "2025-11-06T19:45:05Z",
      "status": "active"
    }
  ],
  "total": 10,
  "created_in_seconds": 45.23,
  "batch_id": "batch-uuid-123"
}

Response (400 Bad Request):
{
  "detail": "Quantidade deve estar entre 1 e 10000",
  "error_code": "INVALID_QUANTITY"
}

Response (429 Too Many Requests):
{
  "detail": "Rate limit excedido",
  "retry_after": 60
}
```

**Descrição:** Criar batch de emails únicos. Suporta até 10.000 por requisição.

**Query Parameters (opcional):**
- `sync`: bool (default false) - Esperar conclusão antes de retornar
- `webhook_url`: string - Notificar quando concluir

### 2.2 Listar Todos os Emails
```
GET /emails?skip=0&limit=50&status=active&sort_by=created_at
Authorization: Bearer {token}

Response (200 OK):
{
  "emails": [
    {
      "email": "abc123def@mail.tm",
      "domain": "mail.tm",
      "created_at": "2025-11-06T19:45:00Z",
      "status": "active",
      "message_count": 3,
      "last_checked_at": "2025-11-06T20:00:00Z"
    }
  ],
  "total": 147,
  "page": 1,
  "pages": 3,
  "has_next": true
}
```

**Query Parameters:**
- `skip`: int (default 0) - Paginação offset
- `limit`: int (default 50, max 1000)
- `status`: string (active|expired|deleted)
- `sort_by`: string (created_at|email|domain)
- `search`: string - Buscar por email/domínio

### 2.3 Obter Detalhes de Um Email
```
GET /emails/{email}
Authorization: Bearer {token}

Response (200 OK):
{
  "email": "abc123def@mail.tm",
  "account_id": "mail-tm-id",
  "domain": "mail.tm",
  "created_at": "2025-11-06T19:45:00Z",
  "status": "active",
  "message_count": 5,
  "unread_count": 2,
  "last_checked_at": "2025-11-06T20:00:00Z",
  "code_count": 2,
  "messages": [
    {
      "id": "msg-uuid-1",
      "from": "noreply@example.com",
      "subject": "Verify your email",
      "received_at": "2025-11-06T19:50:00Z",
      "has_code": true,
      "code_type": "otp_6digit"
    }
  ]
}

Response (404 Not Found):
{
  "detail": "Email não encontrado"
}
```

### 2.4 Deletar Email
```
DELETE /emails/{email}
Authorization: Bearer {token}

Response (204 No Content):
(empty body)

Response (404 Not Found):
{
  "detail": "Email não encontrado"
}
```

**Descrição:** Deletar email de um serviço. Remove conta do Mail.tm também.

### 2.5 Deletar Múltiplos Emails
```
DELETE /emails
Authorization: Bearer {token}
Content-Type: application/json

Request:
{
  "emails": ["email1@mail.tm", "email2@mail.tm"],
  "older_than_days": null
}

Response (200 OK):
{
  "deleted": 2,
  "failed": 0,
  "duration_seconds": 5.23
}
```

---

## 3. MENSAGENS - `/messages`

### 3.1 Listar Mensagens de um Email
```
GET /messages/{email}?unread_only=false&limit=50
Authorization: Bearer {token}

Response (200 OK):
{
  "messages": [
    {
      "id": "msg-uuid-1",
      "from": "support@service.com",
      "subject": "Confirm your registration",
      "preview": "Click here to confirm your email...",
      "received_at": "2025-11-06T19:50:00Z",
      "is_read": false,
      "has_code": true,
      "code_type": "otp_6digit",
      "extracted_code": "123456"
    }
  ],
  "total": 5,
  "unread_count": 2,
  "with_codes": 2
}
```

**Query Parameters:**
- `unread_only`: bool (default false)
- `limit`: int (default 50)
- `with_codes_only`: bool (default false)
- `sort_by`: string (received_at|from)

### 3.2 Obter Detalhes Completos de Uma Mensagem
```
GET /messages/{email}/{message_id}
Authorization: Bearer {token}

Response (200 OK):
{
  "id": "msg-uuid-1",
  "email": "abc123def@mail.tm",
  "from": "noreply@example.com",
  "subject": "Verify your email",
  "text": "Your verification code is: 123456",
  "html": "<html><body>Your verification code is: <strong>123456</strong></body></html>",
  "received_at": "2025-11-06T19:50:00Z",
  "is_read": true,
  "extracted_codes": [
    {
      "code": "123456",
      "type": "otp_6digit",
      "confidence": 98,
      "context": "Your verification code is: 123456",
      "extracted_at": "2025-11-06T19:50:15Z"
    }
  ],
  "extracted_urls": [
    {
      "url": "https://example.com/verify?token=abc123",
      "type": "verification_link"
    }
  ],
  "extracted_emails": ["sender@domain.com"]
}
```

### 3.3 Marcar Mensagem como Lida
```
PATCH /messages/{email}/{message_id}
Authorization: Bearer {token}
Content-Type: application/json

Request:
{
  "is_read": true
}

Response (200 OK):
{
  "id": "msg-uuid-1",
  "is_read": true
}
```

### 3.4 Marcar Múltiplas Mensagens como Lidas
```
PATCH /messages/{email}
Authorization: Bearer {token}
Content-Type: application/json

Request:
{
  "is_read": true,
  "message_ids": ["msg-id-1", "msg-id-2"]
}

Response (200 OK):
{
  "updated": 2,
  "failed": 0
}
```

---

## 4. CÓDIGOS - `/codes`

### 4.1 Obter Códigos de um Email
```
GET /codes/{email}?code_type=all&limit=20
Authorization: Bearer {token}

Response (200 OK):
{
  "email": "abc123def@mail.tm",
  "codes": [
    {
      "id": "code-uuid-1",
      "code": "123456",
      "type": "otp_6digit",
      "confidence": 98,
      "message_id": "msg-uuid-1",
      "message_subject": "Verify your email",
      "context": "Your verification code is: 123456",
      "extracted_at": "2025-11-06T19:50:15Z"
    },
    {
      "id": "code-uuid-2",
      "code": "ABCD1234",
      "type": "token",
      "confidence": 95,
      "message_id": "msg-uuid-2",
      "message_subject": "Reset your password",
      "context": "Your reset token is: ABCD1234",
      "extracted_at": "2025-11-06T20:00:30Z"
    }
  ],
  "total": 2,
  "types_summary": {
    "otp_6digit": 1,
    "token": 1
  }
}
```

**Query Parameters:**
- `code_type`: string (otp_4|otp_6|otp_8|token|url|all) (default all)
- `limit`: int (default 20)
- `recent`: bool (default true) - Ordenar por mais recente

### 4.2 Verificar e Extrair Códigos
```
POST /codes/{email}/check
Authorization: Bearer {token}
Content-Type: application/json

Request:
{
  "force_refresh": false,
  "patterns": ["otp_6digit", "verification_url"]
}

Response (200 OK):
{
  "email": "abc123def@mail.tm",
  "checked_at": "2025-11-06T20:05:00Z",
  "new_messages": 2,
  "new_codes": 1,
  "codes_found": [
    {
      "code": "654321",
      "type": "otp_6digit",
      "message_subject": "Welcome!",
      "confidence": 99
    }
  ],
  "processing_time_ms": 523
}
```

**Request Parameters:**
- `force_refresh`: bool (forçar verificação mesmo se verificado recentemente)
- `patterns`: array de padrões a usar

---

## 5. WEBHOOKS - `/webhooks` (OPCIONAL)

### 5.1 Registrar Webhook
```
POST /webhooks/register
Authorization: Bearer {token}
Content-Type: application/json

Request:
{
  "url": "https://your-app.com/webhook",
  "events": ["message_received", "code_extracted"],
  "secret_key": "your-secret-key-for-signing"
}

Response (201 Created):
{
  "webhook_id": "webhook-uuid",
  "url": "https://your-app.com/webhook",
  "events": ["message_received", "code_extracted"],
  "active": true,
  "created_at": "2025-11-06T20:05:00Z",
  "last_triggered_at": null
}
```

### 5.2 Listar Webhooks
```
GET /webhooks
Authorization: Bearer {token}

Response (200 OK):
{
  "webhooks": [
    {
      "webhook_id": "webhook-uuid-1",
      "url": "https://your-app.com/webhook",
      "events": ["message_received", "code_extracted"],
      "active": true,
      "created_at": "2025-11-06T20:05:00Z",
      "last_triggered_at": "2025-11-06T20:30:00Z",
      "failures": 0
    }
  ],
  "total": 1
}
```

### 5.3 Deletar Webhook
```
DELETE /webhooks/{webhook_id}
Authorization: Bearer {token}

Response (204 No Content):
(empty body)
```

### 5.4 Webhook Payloads e Assinatura

Quando um evento ocorre, um POST é feito para a URL registrada. Os cabeçalhos incluem:

- `X-Webhook-Event`: nome do evento
- `X-Webhook-Signature` (opcional): HMAC-SHA256 do corpo JSON usando `secret_key` do webhook, em formato hex

Exemplo de payload para `message.received`:

```
POST https://your-app.com/webhook
X-Webhook-Event: message.received
X-Webhook-Signature: <hex hmac sha256>
Content-Type: application/json

{
  "event": "message.received",
  "email": "abc123def@mail.tm",
  "message_id": "msg-uuid-1",
  "subject": "Welcome",
  "sender": "noreply@example.com",
  "received_at": "2025-11-06T19:50:00Z",
  "preview": "Hello and welcome"
}
```

Exemplo de payload para `emails_generated` (quando geração síncrona ou job completa):

```
POST https://your-app.com/webhook
X-Webhook-Event: emails_generated
X-Webhook-Signature: <hex hmac sha256>
Content-Type: application/json

{
  "event": "emails_generated",
  "batch_id": "batch-uuid-123",
  "total": 10,
  "created_in_seconds": 45.23,
  "emails": [
    {
      "email": "abc123def@mail.tm",
      "account_id": "mail-tm-id-1",
      "domain": "mail.tm",
      "token": "auth-token-1",
      "status": "active",
      "created_at": 1730912700.123
    }
  ]
}
```

Assinatura HMAC:
- Algoritmo: SHA256
- Mensagem: corpo JSON exato enviado (minificado)
- Chave: `secret_key` definida no registro do webhook
- Header: `X-Webhook-Signature: <hexdigest>`

---

## 6. HEALTH CHECK - `/health`

### 6.1 Verificar Status
```
GET /health
(sem autenticação necessária)

Response (200 OK):
{
  "status": "healthy",
  "timestamp": "2025-11-06T20:30:00Z",
  "version": "1.0.0",
  "database": "connected",
  "mail_tm_api": "reachable",
  "uptime_seconds": 3600
}

Response (503 Service Unavailable):
{
  "status": "degraded",
  "issues": [
    "mail_tm_api: unreachable",
    "database: error"
  ]
}
```

---

## Tratamento de Erros Global

### Erro 400 - Bad Request
```json
{
  "detail": "Descrição do erro",
  "error_code": "INVALID_REQUEST",
  "validation_errors": [
    {
      "field": "quantity",
      "message": "Must be between 1 and 10000"
    }
  ]
}
```

### Erro 401 - Unauthorized
```json
{
  "detail": "Token inválido ou expirado",
  "error_code": "UNAUTHORIZED"
}
```

### Erro 403 - Forbidden
```json
{
  "detail": "Você não tem permissão para acessar este recurso",
  "error_code": "FORBIDDEN"
}
```

### Erro 404 - Not Found
```json
{
  "detail": "Email não encontrado",
  "error_code": "NOT_FOUND"
}
```

### Erro 429 - Rate Limit
```json
{
  "detail": "Rate limit excedido",
  "error_code": "RATE_LIMIT_EXCEEDED",
  "retry_after": 60
}
```

### Erro 500 - Internal Server Error
```json
{
  "detail": "Erro interno do servidor",
  "error_code": "INTERNAL_ERROR",
  "request_id": "req-uuid-123"
}
```

---

## Padrões de Resposta

### Sucesso (2xx)
```json
{
  "data": {...},
  "meta": {
    "timestamp": "2025-11-06T20:30:00Z",
    "request_id": "req-uuid-123"
  }
}
```

### Erro (4xx, 5xx)
```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Mensagem amigável",
    "details": {...}
  },
  "meta": {
    "timestamp": "2025-11-06T20:30:00Z",
    "request_id": "req-uuid-123"
  }
}
```

---

## Limites e Constraints

| Recurso | Limite |
|---------|--------|
| Emails por requisição | 10.000 |
| Resultados por página | 1.000 |
| Tamanho máximo request | 10MB |
| Timeout de requisição | 30 segundos |
| Retenção de dados | 30 dias |
| Rate limit por IP | 100/min |
| Rate limit por API key | 1.000/min |

---

## Exemplos de Integração

### Python com requests
```python
import requests

headers = {"Authorization": "Bearer YOUR_TOKEN"}

# Criar 5 emails
response = requests.post(
    "http://localhost:5000/api/v1/emails/generate",
    json={"quantity": 5, "unique_domains": True},
    headers=headers
)
emails = response.json()["emails"]

# Verificar códigos
for email in emails:
    response = requests.get(
        f"http://localhost:5000/api/v1/codes/{email['email']}",
        headers=headers
    )
    codes = response.json()["codes"]
    print(codes)
```

### cURL
```bash
# Criar emails
curl -X POST http://localhost:5000/api/v1/emails/generate \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"quantity": 5}'

# Listar emails
curl -X GET http://localhost:5000/api/v1/emails \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

**Versão:** 1.0  
**Última Atualização:** 2025-11-06