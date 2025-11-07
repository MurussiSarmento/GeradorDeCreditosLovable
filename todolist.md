# TODO List – Sistema de Gerenciamento de Emails Temporários (Mail.tm)

Este plano em fases organiza a implementação do projeto conforme PROMPT_PRINCIPAL.md, PROJECT_STRUCTURE.md, API_ENDPOINTS.md, API_SPECIFICATIONS.md, MAIL_TM_INTEGRATION.md, UI_REQUIREMENTS.md e DATA_FLOWS.md.

## Fase 1: Fundação (Semana 1) — Status
- [x] Preparar estrutura de pastas conforme `PROJECT_STRUCTURE.md`
- [x] Configurar `venv`, `requirements.txt` e `requirements-dev.txt` (versões fixadas)
- [x] Criar `.env.example` e carregar variáveis com `python-dotenv`
- [x] Implementar `core/config.py` e `utils/logger.py` (loguru com rotação)
- [x] Implementar `core/mail_tm/client.py` com:
  - [x] Cache de domínios com TTL 1h (`GET /domains`)
  - [x] `create_account()` (POST `/accounts`) e `obter token` (POST `/token`)
  - [x] Respeitar rate limit 8 req/seg (delay mínimo entre chamadas)
  - [x] Geração de email e senha aleatórios conforme requisitos
- [x] Implementar `core/database` (SQLAlchemy 2.x): models, session e operações CRUD
- [x] Script `scripts/init_db.py` para inicializar schema
- [x] Testes unitários mínimos: `test_mail_tm_client.py`, `test_database.py`

Pronto quando:
- [x] `python -m pytest` roda com sucesso (cobertura inicial)
- [x] `scripts/init_db.py` cria `data/emails.db`
- [x] Cliente Mail.tm cria 1 conta e obtém token (validação unitária básica)

## Fase 2: API inicial e Core (Semana 2) — Em andamento
- [x] Esqueleto FastAPI (`api/app.py`) e rota `GET /health`
- [x] Teste unitário de health (`tests/unit/test_api_health.py`)
- [x] Autenticação básica por API Key/JWT (middleware e dependências)
- [x] Endpoints iniciais:
  - [x] `POST /emails` (criar/generar email temporário)
  - [x] `GET /emails/{email}` (detalhes)
  - [x] `DELETE /emails/{email}` (excluir)
  - [x] `GET /messages/{email}` (listar mensagens)
- [x] Validação de entrada com Pydantic
- [x] Paginação (`offset`/`limit`) e rate limiting (headers, 429)
- [x] Integração com DB e MailTmClient nas rotas
- [x] Testes unitários para rotas acima

- [x] Extensões implementadas na Fase 2
  - [x] `GET /messages/{email}/{message_id}` (detalhe online, persiste corpo no SQLite)
  - [x] `GET /messages/db/{email}` (lista offline com `offset`/`limit`, filtros e ordenação por `received_at`)
  - [x] `GET /messages/db/{email}/{message_id}` (detalhe offline completo do SQLite)
  - [x] Filtros (`sender`, `subject_contains`, `is_read`) e ordenação (`order=asc|desc`) na lista offline
  - [x] Notificações Telegram opcionais (`notify=true`) apenas em novas inserções; evita duplicações
  - [x] Configuração Telegram (`TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `TELEGRAM_PARSE_MODE`) e utilitário `utils/telegram.py`
  - [x] Ajuste de datas timezone-aware (substitui `datetime.utcnow()` por `datetime.now(timezone.utc)`)
  - [x] Testes unitários cobrindo offline e Telegram (suíte atual `11 passed`)

## Fase 3 - Webhooks

- [x] Modelo `Webhook` no SQLite (id, url, events, secret_key, active, created_at, last_triggered_at, failures)
- [x] Schemas Pydantic para `WebhookRegisterRequest`, `WebhookResponse`, `WebhooksListResponse`
- [x] Endpoints `/webhooks`:
  - [x] `POST /webhooks/register` (criar webhook)
  - [x] `GET /webhooks` (listar com paginação `skip`/`limit`)
  - [x] `DELETE /webhooks/{webhook_id}` (excluir)
- [x] Router incluído na `api/app.py`
- [x] Teste unitário `tests/unit/test_api_webhooks.py` (registrar, listar, deletar) – `passed`
- [x] Revalidação dos testes de jobs e geração síncrona – `passed`
- [x] Disparo de webhooks registrados no evento `emails_generated` após criação de batch
- [x] Teste unitário de disparo global de webhooks em geração síncrona – `passed`
  - [x] Helper de formatação rica para Telegram (MarkdownV2/HTML com escape seguro)
  - [x] Rate limit/backoff no envio ao Telegram (limite por segundo e retry exponencial em 429)
  - [x] Documentação atualizada (`README.md`) e `.env.example` com novos parâmetros
  - [x] Truncamento de preview configurável nas notificações (`TELEGRAM_PREVIEW_MAX_CHARS`)
  - [x] Parâmetro `preview_max` nas rotas com `notify=true` para override por requisição
  - [x] `GET /emails` alinhado ao formato documentado (`items` + `pagination`)
  - [x] Schemas atualizados para `Pagination` e `EmailsListResponse`
  - [x] Teste unitário de paginação de emails atualizado e passando
  - [x] Busca (`search`) e ordenação por `email|domain` em `GET /emails` com testes
- [x] `POST /emails/generate` com `sync=true` retornando batch e `webhook_url` opcional

Pronto quando:
- [x] Endpoints básicos funcionam com validação, paginação e rate limiting
- [x] Testes para rotas passam e logs estruturados são gerados

## Próximos passos – Webhooks

- [x] Disparo de webhooks para evento `message.received` ao inserir nova mensagem
- [x] Utilitário de disparo com assinatura HMAC (`X-Webhook-Signature`)
- [x] Atualizar `last_triggered_at` em sucesso e incrementar `failures` em erro
- [x] Testes unitários para entrega, assinatura e falhas de webhooks
- [x] Documentar payload e cabeçalhos de `message.received` em `API_ENDPOINTS.md`
- [x] Assinatura HMAC opcional no webhook de `POST /emails/generate` via `webhook_secret` (inclui `X-Webhook-Event: emails_generated` e `X-Webhook-Signature` quando presente)
- [x] Documentar `webhook_secret` e cabeçalhos do webhook opcional em `API_ENDPOINTS.md`
- [x] Atualizar métricas de webhooks globais `emails_generated` (setar `last_triggered_at` em sucesso, incrementar `failures` em erro)
 - [x] Criar teste unitário para `POST /emails/generate` com `webhook_secret`, validando `X-Webhook-Signature`

## Fase 3: API Completa (Semana 3)
- [ ] Implementar todos endpoints de `API_ENDPOINTS.md` (emails, messages, codes, webhooks, auth, health)
  - [x] `GET /emails` listar com paginação, filtros, busca e ordenação
  - [x] `POST /emails/generate` com suporte `sync=true` e `webhook_url`
  - [ ] Endpoints `codes` para extração de códigos/verificação
  - [ ] Endpoints `webhooks` para notificações externas
  - [ ] Persistir status de jobs em DB (`jobs` table) em vez de memória
  - [ ] Suportar `sync=true` e `webhook_url` em `POST /emails/generate`
- [x] Autenticação: API key + JWT (payload e permissões conforme `API_SPECIFICATIONS.md`)
  - [x] `POST /auth/token` (troca `API_KEY` por `access_token` JWT 24h)
  - [x] `GET /auth/validate` (valida token e retorna `expires_at`)
  - [x] Dependência unificada aceita `Authorization: Bearer` e `X-API-Key`
  - [x] Routers atualizados para usar a nova dependência
- [x] Rate limiting: 100/min por IP e 1000/min por API key (headers e 429)
- [x] Background jobs para geração em batch com polling (`/jobs/{id}`)
- [x] Documentação Swagger/OpenAPI automática
- [ ] Testes de integração: endpoints, rate limit e fluxo end-to-end

Pronto quando:
- [ ] Suite de integração passa e documentação OpenAPI está acessível
- [ ] Logs estruturados (`logs/api.log`) mostram métricas e correlação (request_id)

## Fase 4: Interface Gráfica (Semana 4)
- [ ] Setup PyQt6 e `ui/main_window.py` com tabs: Generator, Inbox, Settings, Status
- [ ] Widgets principais: tabela de emails, viewer de mensagens, barra de progresso, code display
- [ ] Workers (`workers/*`): criação de emails, verificação de mensagens, extração de códigos
- [ ] Conectar UI ↔ serviços (signals, threading, não bloquear UI)
- [ ] Aplicar estilos `styles.qss`, dark/light mode básico
- [ ] Ações de tabela: copiar, exportar CSV, deletar selecionados, atualizar

Pronto quando:
- [ ] UI cria 100 emails sem travamentos e mostra progresso/ETA
- [ ] Inbox auto-verifica a cada 30s e exibe códigos com contexto

## Fase 5: Polish e Deploy (Semana 5)
- [ ] Tratamento de erros abrangente e mensagens amigáveis na UI
- [ ] Logging completo em todos módulos (app.log, api.log, extraction.log)
- [ ] Backup automático do DB (hora em hora) e cleanup >30 dias
- [ ] Build executável para Windows (PyInstaller) e README de deploy
- [ ] Documentação final: `README.md`, `docs/API.md`, `docs/DEPLOYMENT.md`

Pronto quando:
- [ ] Executável inicia UI e API localmente com `.env` configurado
- [ ] Cobertura de testes ≥80% e benchmarks atendem métricas de sucesso

---

Critérios Globais e Checks
- [ ] Respeitar rate limit Mail.tm: 8 req/seg com backoff/retry
- [ ] Criptografar senhas de email com Fernet (nunca logar segredos)
- [ ] Validação de entrada 100% nas APIs (Pydantic)
- [ ] CORS configurado corretamente e segurança JWT
- [ ] Paginação em listas >100 itens
- [ ] Cache de domínios com TTL 1h

Referências Rápidas
- `PROMPT_PRINCIPAL.md` – visão geral e metas
- `PROJECT_STRUCTURE.md` – organização de arquivos
- `MAIL_TM_INTEGRATION.md` – detalhes da API Mail.tm
- `API_ENDPOINTS.md` + `API_SPECIFICATIONS.md` – design da API
- `UI_REQUIREMENTS.md` – layout e comportamento da UI
- `DATA_FLOWS.md` – interações entre módulos
- `ERROR_HANDLING.md` – estratégia de erros