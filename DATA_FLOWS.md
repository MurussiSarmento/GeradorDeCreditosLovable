# DATA_FLOWS - Fluxos de Dados e Interações entre Componentes

## Fluxo 1: Criação de Emails em Batch via UI

```
┌─────────────────────────────────────────────────────────┐
│ Usuário clica "GERAR EMAILS" na UI                      │
└─────────────┬───────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────┐
│ UI: Validar entrada (quantidade, domínios)              │
│ - Quantity: 1-10000? ✓                                  │
│ - Domínios únicos possível? ✓                           │
│ - Desabilitar botão, mostrar progresso                  │
└─────────────┬───────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────┐
│ UI: Spawn EmailGeneratorWorker em thread separada       │
│ - Não bloqueia UI                                       │
│ - Conectar signals para progresso                       │
└─────────────┬───────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────┐
│ EmailService.create_emails_batch()                      │
│ - Chamar MailTmClient.batch_create_accounts()           │
│ - ThreadPool com max 8 workers (respita rate limit)    │
│ - Cada worker cria email único com domínio aleatório   │
└─────────────┬───────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────┐
│ MailTmClient.batch_create_accounts()                    │
│ - GET /domains (com cache)                              │
│ - Para cada email:                                      │
│   1. Gerar username aleatório                          │
│   2. Gerar password forte                              │
│   3. POST /accounts (criar conta)                       │
│   4. POST /token (obter JWT)                            │
│   5. Respeitar rate limit (8 req/sec)                   │
└─────────────┬───────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────┐
│ Mail.tm API                                              │
│ - Retorna account_id e token para cada email            │
└─────────────┬───────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────┐
│ EmailService: Salvar no banco de dados                  │
│ - INSERT INTO email_accounts                            │
│   (email, account_id, password_encrypted, token, ...)   │
│ - Criptografar senha com Fernet                         │
│ - Status: 'active'                                      │
└─────────────┬───────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────┐
│ Worker: Emitir signals de progresso                     │
│ - A cada email criado: emit progress(current, total)    │
│ - Calcular ETA                                          │
│ - Atualizar velocidade (emails/seg)                     │
└─────────────┬───────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────┐
│ UI: Atualizar barra de progresso                        │
│ - Conectado via signal                                  │
│ - Não faz requisição, apenas atualiza visualmente       │
└─────────────┬───────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────┐
│ Batch concluído                                          │
│ - Worker retorna list de emails criados                 │
│ - UI desabilita progresso                               │
│ - UI popula tabela com emails                           │
│ - Notificação: "✓ 100 emails criados em 2 minutos"     │
└─────────────────────────────────────────────────────────┘
```

## Fluxo 2: Verificar Emails e Extrair Códigos via UI

```
┌─────────────────────────────────────────────────────────┐
│ Usuário seleciona email e clica "Verificar Agora"       │
└─────────────┬───────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────┐
│ UI: Spawn MessageCheckerWorker em thread                │
└─────────────┬───────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────┐
│ MessageService.get_messages(email_token)                │
│ - Chamar MailTmClient.get_messages(token)               │
│ - Respeitar rate limit                                  │
└─────────────┬───────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────┐
│ Mail.tm API: GET /messages                              │
│ - Retorna lista de mensagens com:                       │
│   {id, from, subject, received_at, isRead}             │
│ - Sem corpo completo ainda                              │
└─────────────┬───────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────┐
│ Para cada mensagem nova:                                │
│ - MailTmClient.get_message_detail(token, msg_id)       │
│ - Obter texto completo e HTML                           │
└─────────────┬───────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────┐
│ CodeExtractor.extract_with_context(body)                │
│ - Buscar todos padrões regex                            │
│ - Calcular confidence para cada match                   │
│ - Retornar com contexto (antes/depois)                 │
└─────────────┬───────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────┐
│ Salvar no banco de dados                                │
│ - INSERT INTO messages                                  │
│ - INSERT INTO extracted_codes                           │
│ - Marcar como processada                                │
└─────────────┬───────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────┐
│ Worker: Emitir signals                                  │
│ - messages_found(count)                                 │
│ - new_codes_extracted(codes)                            │
└─────────────┬───────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────┐
│ UI: Atualizar tabela de mensagens                       │
│ - Mostrar novas mensagens                               │
│ - Destacar mensagens com código em verde                │
│ - Notificação toast: "✓ 2 novos códigos encontrados"   │
│ - Se fone habilitado: Som de notificação                │
└─────────────────────────────────────────────────────────┘
```

## Fluxo 3: Criar Emails via API RESTful

```
┌─────────────────────────────────────────────────────────┐
│ Cliente HTTP faz:                                        │
│ POST /api/v1/emails/generate                            │
│ Authorization: Bearer {token}                           │
│ {quantity: 5, unique_domains: true}                     │
└─────────────┬───────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────┐
│ FastAPI Middleware:                                      │
│ - Validar token JWT                                     │
│ - Verificar rate limit                                  │
│ - Extrair user_id                                       │
│ - Gerar request_id único                                │
└─────────────┬───────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────┐
│ Validação Pydantic:                                      │
│ - quantity: 1-10000? ✓                                  │
│ - unique_domains: bool? ✓                               │
│ - Se erro: retornar 422 com detalhes                    │
└─────────────┬───────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────┐
│ Route Handler: /emails/generate                         │
│ - Retornar job_id imediatamente                         │
│ - Retorno: 202 Accepted                                 │
│ {job_id: uuid, status: 'processing', polling_url: ...} │
└─────────────┬───────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────┐
│ BackgroundTask (async):                                  │
│ - EmailService.create_emails_batch()                    │
│ - Salvar progresso em DB (job table)                    │
│ - A cada email: UPDATE job SET progress=X%              │
│ - Salvar resultado quando completo                      │
└─────────────┬───────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────┐
│ Cliente faz pooling:                                     │
│ GET /api/v1/jobs/{job_id}                               │
│ - Verificar status                                      │
│ - Repetir até status = 'completed'                      │
└─────────────┬───────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────┐
│ Quando completo, cliente faz:                           │
│ GET /api/v1/emails?created_after={timestamp}            │
│ - Obter todos emails desse batch                        │
└─────────────┬───────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────┐
│ API retorna:                                             │
│ {                                                        │
│   "emails": [{email, account_id, token, ...}],         │
│   "pagination": {...}                                   │
│ }                                                        │
└─────────────────────────────────────────────────────────┘
```

## Fluxo 4: Webhooks - Notificação de Novo Código

```
┌─────────────────────────────────────────────────────────┐
│ Cliente registra webhook:                                │
│ POST /api/v1/webhooks/register                          │
│ {                                                        │
│   url: "https://app.com/webhook",                       │
│   events: ["code_extracted"],                           │
│   secret_key: "secret123"                               │
│ }                                                        │
└─────────────┬───────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────┐
│ API salva webhook no DB:                                 │
│ INSERT INTO webhooks                                    │
│ (url, events, secret_key, active)                       │
└─────────────┬───────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────┐
│ (Momento posterior) Código é extraído:                  │
│ - CodeExtractor encontra "123456"                       │
│ - Salvar em DB                                          │
└─────────────┬───────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────┐
│ WebhookService.trigger_webhook()                        │
│ - Buscar webhooks com event="code_extracted"            │
│ - Para cada webhook:                                    │
│   1. Criar payload:                                     │
│      {                                                  │
│        event: "code_extracted",                         │
│        timestamp: "...",                                │
│        data: {code, type, email, ...}                   │
│      }                                                  │
│   2. Assinar payload com HMAC-SHA256 + secret_key       │
│   3. POST para webhook URL                              │
│   4. Retry com exponential backoff se falhar            │
└─────────────┬───────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────┐
│ Cliente recebe POST com:                                 │
│ Headers:                                                │
│   X-Webhook-Signature: sha256=abc123...                │
│ Body:                                                   │
│   {event: "code_extracted", data: {...}}               │
│                                                         │
│ Cliente valida signature e processa                     │
└─────────────────────────────────────────────────────────┘
```

## Fluxo 5: Auto-Delete de Emails Expirados

```
┌─────────────────────────────────────────────────────────┐
│ Scheduler job executa a cada 10 minutos                 │
│ (background task)                                       │
└─────────────┬───────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────┐
│ EmailService.cleanup_expired_emails()                   │
│ - Query: WHERE created_at < (now - auto_delete_secs)   │
│ - E status = 'active'                                   │
└─────────────┬───────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────┐
│ Para cada email a expirar:                              │
│ - MailTmClient.delete_account(token, account_id)       │
│ - DELETE /accounts/{account_id}                         │
└─────────────┬───────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────┐
│ Mail.tm API: Confirma deleção                           │
│ - Retorna 204 No Content                                │
└─────────────┬───────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────┐
│ Salvar no DB:                                            │
│ - UPDATE email_accounts SET status='deleted'            │
│ - updated_at = now()                                    │
│ - Log do cleanup                                        │
└─────────────┬───────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────┐
│ Trigger webhook (se existe):                            │
│ - event: "email_deleted"                                │
│ - data: {email, reason: "auto_expired"}                │
└─────────────────────────────────────────────────────────┘
```

## Fluxo 6: Sincronização entre UI e API

```
┌─────────────────────────────────────────────────────────┐
│ Cenário: App rodando em 2 lugares simultaneamente       │
│ - UI Desktop local                                      │
│ - Script remoto via API                                 │
└─────────────┬───────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────┐
│ Script remoto cria emails via API:                      │
│ POST /api/v1/emails/generate {quantity: 10}             │
└─────────────┬───────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────┐
│ Emails salvos no banco de dados                         │
└─────────────┬───────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────┐
│ UI Desktop: Auto-refresh a cada 30 segundos             │
│ GET /api/v1/emails (se auto-refresh ativado)            │
└─────────────┬───────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────┐
│ UI recebe novos emails do script remoto                 │
│ - Tabela atualiza automaticamente                       │
│ - Mostra notificação: "10 novos emails adicionados"     │
│ - Sincronizado!                                         │
└─────────────────────────────────────────────────────────┘
```

## Estrutura de Eventos

```
Application Events (UI ↔ API):

1. Email Created
   - UI: gerado novo email
   - Trigger: webhook "email_created"
   - Data: {email, domain, created_at}

2. Message Received
   - Mail.tm: novo email chegou
   - Trigger: auto-check detecta
   - Trigger: webhook "message_received"
   - Data: {email, from, subject}

3. Code Extracted
   - CodeExtractor: código encontrado
   - Trigger: webhook "code_extracted"
   - Trigger: UI notification toast
   - Data: {email, code, type, confidence}

4. Email Deleted
   - Email expirou ou usuário deletou
   - Trigger: webhook "email_deleted"
   - Data: {email, reason}

5. Rate Limit
   - Mail.tm retorna 429
   - Trigger: automatic retry com backoff
   - Trigger: UI warning notification
```

---

**Versão:** 1.0  
**Última Atualização:** 2025-11-06