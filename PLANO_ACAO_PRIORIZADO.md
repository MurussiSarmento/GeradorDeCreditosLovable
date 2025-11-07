# PLANO DE AÇÃO PRIORIZADO - GeradorDeCreditosLovable

**Baseado em:** AUDITORIA_COMPLETA.md  
**Objetivo:** Roadmap prático para completar o projeto  
**Status Atual:** 65% completo

---

## OVERVIEW RÁPIDO

### Progresso por Componente

| Componente | Status | Prioridade | Esforço |
|------------|--------|------------|---------|
| ✅ API REST Core | 90% | - | - |
| ✅ Auth & Security | 95% | - | - |
| ✅ Database & Models | 100% | - | - |
| ✅ Webhooks System | 95% | - | - |
| ✅ Telegram Integration | 85% | - | - |
| ❌ Code Extraction | 0% | 🔴 CRÍTICO | 15-20h |
| ❌ UI Desktop (PyQt6) | 0% | 🔴 CRÍTICO | 40-50h |
| ❌ Services Layer | 0% | 🟡 ALTO | 10-12h |
| ❌ Integration Tests | 0% | 🟡 ALTO | 10-12h |
| ❌ Deployment (Docker) | 0% | 🟡 ALTO | 6-8h |

### Estimativa Total para 100%
- **Mínimo (MVP):** 6-8 semanas
- **Completo:** 12-16 semanas

---

## FASE 1: FEATURES CRÍTICAS (4-6 semanas)

### 📦 TAREFA 1: Sistema de Extração de Códigos

**Prioridade:** 🔴 CRÍTICA  
**Esforço:** 15-20 horas  
**Status:** Não iniciado

#### Subtarefas:

- [ ] **1.1 Criar estrutura do módulo** (2h)
  ```bash
  mkdir -p core/extraction
  touch core/extraction/__init__.py
  touch core/extraction/code_extractor.py
  touch core/extraction/patterns.py
  touch core/extraction/validators.py
  ```

- [ ] **1.2 Implementar patterns.py** (3h)
  - [ ] Padrão OTP 4 dígitos
  - [ ] Padrão OTP 5 dígitos
  - [ ] Padrão OTP 6 dígitos
  - [ ] Padrão OTP 8 dígitos
  - [ ] Padrão URLs de verificação
  - [ ] Padrão tokens alfanuméricos
  - [ ] Padrão recovery codes
  - [ ] Padrão Google Authenticator
  - [ ] Padrão códigos com keywords (ex: "code:", "código:")
  - [ ] Documentar cada padrão

- [ ] **1.3 Implementar code_extractor.py** (4h)
  - [ ] Classe `CodeExtractor`
  - [ ] Método `extract_codes(text, patterns=None)`
  - [ ] Método `extract_with_context(text, window=50)`
  - [ ] Método `extract_from_html(html_content)`
  - [ ] Cálculo de confidence score
  - [ ] Documentação e type hints

- [ ] **1.4 Criar modelo ExtractedCode** (2h)
  - [ ] Adicionar tabela `extracted_codes` ao models.py
  - [ ] Campos: id, message_id, code, type, confidence, context, extracted_at
  - [ ] Relationship com Message
  - [ ] Migration script ou atualizar init_db.py

- [ ] **1.5 Implementar endpoints /codes** (4h)
  - [ ] `GET /codes/{email}` - Listar códigos extraídos
    - Query params: type, limit, recent
  - [ ] `POST /codes/{email}/check` - Verificar e extrair novos códigos
    - Body: force_refresh, patterns
  - [ ] Schemas Pydantic para request/response
  - [ ] Integrar com auth_required

- [ ] **1.6 Integração automática** (2h)
  - [ ] Extrair códigos ao persistir mensagem nova
  - [ ] Salvar em `extracted_codes` table
  - [ ] Webhook event opcional: "code.extracted"

- [ ] **1.7 Testes unitários** (4h)
  - [ ] `test_code_extractor.py` - 10+ test cases
  - [ ] `test_api_codes.py` - Endpoints
  - [ ] Testar todos os patterns
  - [ ] Testar edge cases (sem código, múltiplos códigos)

**Critérios de Aceitação:**
- ✅ 8+ patterns implementados e testados
- ✅ Endpoints /codes funcionando
- ✅ Extração automática em mensagens novas
- ✅ 10+ testes passando
- ✅ Documentação no README atualizada

**Arquivos a Criar:**
- `core/extraction/__init__.py`
- `core/extraction/code_extractor.py`
- `core/extraction/patterns.py`
- `core/extraction/validators.py`
- `api/routers/codes.py`
- `tests/unit/test_code_extractor.py`
- `tests/unit/test_api_codes.py`

**Referência:**
- Ver `CODE_EXTRACTION.md` para especificações

---

### 🖥️ TAREFA 2: Interface Gráfica (UI Desktop)

**Prioridade:** 🔴 CRÍTICA  
**Esforço:** 40-50 horas  
**Status:** Não iniciado

#### Subtarefas:

- [ ] **2.1 Setup inicial** (4h)
  - [ ] Instalar PyQt6: `pip install pyqt6`
  - [ ] Atualizar requirements.txt
  - [ ] Criar estrutura de diretórios:
    ```bash
    mkdir -p ui/{tabs,widgets,dialogs}
    touch ui/__init__.py
    touch ui/main_window.py
    touch ui/styles.qss
    ```
  - [ ] MainWindow básico com menu e status bar

- [ ] **2.2 Aba Generator** (8h)
  - [ ] Criar `ui/tabs/generator_tab.py`
  - [ ] Layout:
    - Input: quantidade (1-10000)
    - Checkbox: unique_domains
    - Input: auto_delete_seconds (opcional)
    - Botão: "GERAR EMAILS"
    - ProgressBar com ETA
    - Tabela de resultados (email, domain, status, actions)
  - [ ] Ações na tabela:
    - Copiar email
    - Ver detalhes
    - Deletar
    - Exportar selecionados (CSV)
  - [ ] Worker para geração em background
  - [ ] Signals para atualizar UI

- [ ] **2.3 Aba Inbox** (10h)
  - [ ] Criar `ui/tabs/inbox_tab.py`
  - [ ] Layout:
    - Dropdown: Selecionar email
    - Lista: Mensagens (subject, from, date, has_code)
    - Viewer: Conteúdo da mensagem (HTML ou plain text)
    - Panel lateral: Códigos extraídos com destaque
  - [ ] Botão: "Atualizar mensagens"
  - [ ] Auto-refresh a cada 30s (configurável)
  - [ ] Worker para buscar mensagens
  - [ ] Display de códigos com copy button

- [ ] **2.4 Aba Settings** (4h)
  - [ ] Criar `ui/tabs/settings_tab.py`
  - [ ] Seções:
    - API Configuration (API_KEY, SECRET_KEY)
    - Telegram Settings (token, chat_id, parse_mode)
    - UI Preferences (theme, auto_refresh_interval)
    - Mail.tm Settings (rate_limit)
  - [ ] Botão: "Salvar" → atualizar .env
  - [ ] Botão: "Testar Telegram" → enviar mensagem de teste
  - [ ] Toggle: Dark/Light mode

- [ ] **2.5 Aba Status/API** (4h)
  - [ ] Criar `ui/tabs/status_tab.py`
  - [ ] Display:
    - Status da API (rodando/parado)
    - Botão: Start/Stop API
    - URL da API (http://localhost:5000)
    - Logs recentes (tail de logs/api.log)
    - Estatísticas: total emails, total mensagens, códigos extraídos
  - [ ] Gráficos simples (opcional):
    - Emails criados por dia (últimos 7 dias)
    - Taxa de mensagens recebidas

- [ ] **2.6 Widgets customizados** (4h)
  - [ ] `ui/widgets/email_table.py` - Tabela reutilizável
  - [ ] `ui/widgets/message_viewer.py` - Viewer HTML/plain
  - [ ] `ui/widgets/code_display.py` - Display de códigos com highlight
  - [ ] `ui/widgets/progress_dialog.py` - Dialog de progresso

- [ ] **2.7 Workers de threading** (6h)
  - [ ] Criar `workers/__init__.py`
  - [ ] `workers/email_generator_worker.py`
    - Herdar de QRunnable
    - Gerar emails em background
    - Emitir signals: progress, finished, error
  - [ ] `workers/message_checker_worker.py`
    - Verificar mensagens periodicamente
    - Emitir signal quando nova mensagem
  - [ ] `workers/code_extractor_worker.py`
    - Extrair códigos em background

- [ ] **2.8 Integração com API** (4h)
  - [ ] Cliente HTTP para chamar API local
  - [ ] Gerenciar token JWT (obter, armazenar, renovar)
  - [ ] Error handling (API offline, timeout, auth failed)
  - [ ] Feedback visual de erros

- [ ] **2.9 Styles e polish** (4h)
  - [ ] `ui/styles.qss` - Stylesheet Qt
  - [ ] Tema dark e light
  - [ ] Ícones (opcional, usar Qt icons)
  - [ ] Tooltips em todos botões
  - [ ] Keyboard shortcuts (Ctrl+G para gerar, Ctrl+R para refresh)

- [ ] **2.10 Testes de UI** (4h)
  - [ ] `tests/unit/test_ui_widgets.py`
  - [ ] Testar signals
  - [ ] Testar workers
  - [ ] Smoke test de cada aba

**Critérios de Aceitação:**
- ✅ UI inicia sem erros
- ✅ 4 abas funcionais
- ✅ Gerar 100 emails sem travar UI
- ✅ Inbox atualiza automaticamente
- ✅ Settings salva corretamente
- ✅ Dark/Light mode funciona

**Arquivos a Criar:**
- `ui/__init__.py`
- `ui/main_window.py`
- `ui/styles.qss`
- `ui/tabs/{generator,inbox,settings,status}_tab.py`
- `ui/widgets/{email_table,message_viewer,code_display,progress_dialog}.py`
- `workers/{email_generator,message_checker,code_extractor}_worker.py`
- `tests/unit/test_ui_*.py`

**Referência:**
- Ver `UI_REQUIREMENTS.md` para especificações detalhadas

---

## FASE 2: QUALIDADE E ARQUITETURA (2-3 semanas)

### 🏗️ TAREFA 3: Camada de Serviços

**Prioridade:** 🟡 ALTA  
**Esforço:** 10-12 horas

#### Subtarefas:

- [ ] **3.1 Criar módulo services/** (6h)
  - [ ] `services/__init__.py`
  - [ ] `services/email_service.py`
    - Classe EmailService
    - Métodos: create_email, create_batch, get_email, list_emails, delete_email
    - Lógica de negócio extraída de routers/emails.py
  - [ ] `services/message_service.py`
    - Classe MessageService
    - Métodos: get_messages, get_message_detail, persist_message, list_offline
  - [ ] `services/webhook_service.py`
    - Classe WebhookService
    - Métodos: register, dispatch, get_webhooks_for_event
  - [ ] `services/cache_service.py`
    - Classe CacheService (in-memory ou Redis)
    - Métodos: get_domains, set_domains, invalidate

- [ ] **3.2 Refatorar routers** (3h)
  - [ ] api/routers/emails.py usar EmailService
  - [ ] api/routers/messages.py usar MessageService
  - [ ] api/routers/webhooks.py usar WebhookService
  - [ ] Simplificar routers (<100 linhas cada)

- [ ] **3.3 Testes de services** (3h)
  - [ ] `tests/unit/test_email_service.py`
  - [ ] `tests/unit/test_message_service.py`
  - [ ] Mock do DB e MailTmClient

**Critérios de Aceitação:**
- ✅ Routers < 150 linhas cada
- ✅ Lógica de negócio em services/
- ✅ Testes de services passando

---

### 🧪 TAREFA 4: Testes de Integração

**Prioridade:** 🟡 ALTA  
**Esforço:** 10-12 horas

#### Subtarefas:

- [ ] **4.1 Setup de testes E2E** (2h)
  - [ ] Criar `tests/integration/__init__.py`
  - [ ] Fixture: TestClient do FastAPI
  - [ ] Fixture: Database temporário
  - [ ] Mock global do MailTmClient

- [ ] **4.2 Testes de fluxos completos** (6h)
  - [ ] `tests/integration/test_full_flow.py`
    - Fluxo 1: Auth → Criar email → Listar → Deletar
    - Fluxo 2: Criar batch → Polling → Webhook dispatch
    - Fluxo 3: Criar email → Receber mensagem → Extrair código
    - Fluxo 4: Registrar webhook → Trigger evento → Verificar HMAC
  - [ ] `tests/integration/test_api_endpoints.py`
    - Testar todos endpoints com dados reais
    - Testar error cases (404, 401, 400)

- [ ] **4.3 Testes de rate limiting** (2h)
  - [ ] `tests/integration/test_rate_limiting.py`
    - Simular 100+ requests
    - Verificar headers X-RateLimit-*
    - Verificar 429 Too Many Requests

- [ ] **4.4 Testes de concorrência** (2h)
  - [ ] Criar múltiplos emails simultaneamente
  - [ ] Verificar locks do SQLite
  - [ ] Testar race conditions

**Critérios de Aceitação:**
- ✅ 15+ testes de integração
- ✅ Cobertura de todos fluxos principais
- ✅ Testes de error scenarios

---

## FASE 3: DEPLOYMENT E OPS (1-2 semanas)

### 🐳 TAREFA 5: Containerização (Docker)

**Prioridade:** 🟡 ALTA  
**Esforço:** 6-8 horas

#### Subtarefas:

- [ ] **5.1 Criar Dockerfile** (3h)
  - [ ] Multi-stage build
  - [ ] Stage 1: Builder (instalar deps)
  - [ ] Stage 2: Runtime (copiar apenas necessário)
  - [ ] User não-root
  - [ ] Healthcheck
  - [ ] Exemplo:
    ```dockerfile
    FROM python:3.11-slim as builder
    WORKDIR /app
    COPY requirements.txt .
    RUN pip install --no-cache-dir -r requirements.txt
    
    FROM python:3.11-slim
    WORKDIR /app
    COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
    COPY . .
    RUN useradd -m appuser && chown -R appuser:appuser /app
    USER appuser
    EXPOSE 5000
    HEALTHCHECK CMD curl --fail http://localhost:5000/health || exit 1
    CMD ["python", "main.py"]
    ```

- [ ] **5.2 docker-compose.yml** (2h)
  - [ ] Service: api
  - [ ] Volumes: data/, logs/
  - [ ] Env file: .env
  - [ ] Networks
  - [ ] Exemplo:
    ```yaml
    version: '3.8'
    services:
      api:
        build: .
        ports:
          - "5000:5000"
        volumes:
          - ./data:/app/data
          - ./logs:/app/logs
        env_file:
          - .env
        restart: unless-stopped
    ```

- [ ] **5.3 Scripts de deploy** (2h)
  - [ ] `scripts/build.sh` - Build da imagem
  - [ ] `scripts/deploy.sh` - Deploy em servidor
  - [ ] `scripts/health_check.sh` - Verificar saúde
  - [ ] `.dockerignore` - Ignorar .venv, logs, data

- [ ] **5.4 Documentação de deploy** (1h)
  - [ ] Criar `DEPLOYMENT.md`
  - [ ] Seções:
    - Pré-requisitos (Docker, docker-compose)
    - Build local
    - Deploy em produção
    - Variáveis de ambiente obrigatórias
    - Troubleshooting comum

**Critérios de Aceitação:**
- ✅ `docker build .` funciona
- ✅ `docker-compose up` inicia a API
- ✅ Healthcheck responde 200
- ✅ Volumes persistem dados

---

### 🔧 TAREFA 6: Features Operacionais

**Prioridade:** 🟢 MÉDIA  
**Esforço:** 4-5 horas

#### Subtarefas:

- [ ] **6.1 Backup automático** (2h)
  - [ ] Script `scripts/backup_db.sh`
    - Copiar data/emails.db para data/backups/
    - Timestamp no nome: `emails_backup_YYYYMMDD_HHMMSS.db`
    - Manter últimos 7 backups, deletar antigos
  - [ ] Agendar via cron (Linux) ou Task Scheduler (Windows)
  - [ ] Exemplo cron: `0 * * * * /path/to/backup_db.sh` (hourly)

- [ ] **6.2 Cleanup automático** (2h)
  - [ ] Script `scripts/cleanup_old_data.py`
    - Deletar emails com status "deleted" >30 dias
    - Deletar mensagens >60 dias
    - VACUUM do SQLite
  - [ ] Agendar diariamente
  - [ ] Logs de quantos itens foram removidos

**Critérios de Aceitação:**
- ✅ Backup roda automaticamente
- ✅ Cleanup remove dados antigos sem erros

---

## FASE 4: MELHORIAS INCREMENTAIS (Opcional)

### 📝 TAREFA 7: Endpoints Faltantes

**Prioridade:** 🟢 MÉDIA  
**Esforço:** 3-4 horas

#### Subtarefas:

- [ ] **7.1 PATCH /messages/{email}/{id}** (1h)
  - [ ] Schema: `MessageUpdateRequest` (is_read: bool)
  - [ ] Atualizar campo is_read no DB
  - [ ] Retornar mensagem atualizada

- [ ] **7.2 PATCH /messages/{email}** (1h)
  - [ ] Schema: `BulkMessageUpdateRequest` (is_read, message_ids)
  - [ ] Atualizar múltiplas mensagens
  - [ ] Retornar contadores (updated, failed)

- [ ] **7.3 DELETE /emails (batch)** (1h)
  - [ ] Schema: `BulkDeleteRequest` (emails[], older_than_days)
  - [ ] Deletar em lote
  - [ ] Retornar contadores (deleted, failed, duration)

- [ ] **7.4 Testes** (1h)

---

### 📊 TAREFA 8: Observabilidade

**Prioridade:** 🟢 BAIXA  
**Esforço:** 4-5 horas

#### Subtarefas:

- [ ] **8.1 Request ID tracking** (2h)
  - [ ] Middleware para gerar request_id (UUID)
  - [ ] Adicionar em logs
  - [ ] Header de resposta: `X-Request-ID`

- [ ] **8.2 Métricas básicas** (2h)
  - [ ] Contador de requests por endpoint
  - [ ] Histograma de latência
  - [ ] Contador de erros (4xx, 5xx)
  - [ ] Exportar via endpoint `/metrics` (formato Prometheus)

- [ ] **8.3 Dashboard simples** (opcional, 3h)
  - [ ] Página HTML simples em `/dashboard`
  - [ ] Gráficos com Chart.js
  - [ ] Estatísticas em tempo real

---

## QUICK WINS (Próximos 3-5 dias)

### 🚀 TAREFA 9: Melhorias Rápidas

**Prioridade:** 🟢 BAIXA  
**Esforço:** 8-10 horas total

- [ ] **9.1 Adicionar docstrings** (3h)
  - [ ] Formato Google ou Numpy
  - [ ] Todas funções públicas
  - [ ] Incluir exemplos de uso

- [ ] **9.2 Melhorar cobertura de testes** (3h)
  - [ ] utils/crypto.py: 52% → 85%
  - [ ] api/auth.py: 60% → 80%
  - [ ] core/mail_tm/client.py: 62% → 75%

- [ ] **9.3 Atualizar README** (1h)
  - [ ] Corrigir nome do projeto
  - [ ] Adicionar badges (tests, coverage)
  - [ ] Seção de limitações conhecidas
  - [ ] Link para AUDITORIA_COMPLETA.md

- [ ] **9.4 Criar .github/workflows/** (2h)
  - [ ] CI: Rodar testes em push/PR
  - [ ] Lint com flake8
  - [ ] Type check com mypy (opcional)

---

## CHECKLIST DE CONCLUSÃO

### Para considerar o projeto 100% completo:

#### Features:
- [ ] ✅ Sistema de extração de códigos funcionando
- [ ] ✅ UI desktop com 4 abas funcionais
- [ ] ✅ Camada de serviços implementada
- [ ] ✅ Todos endpoints da API_ENDPOINTS.md implementados

#### Qualidade:
- [ ] ✅ Cobertura de testes ≥ 90%
- [ ] ✅ Testes de integração cobrindo fluxos principais
- [ ] ✅ Zero TODOs/FIXMEs críticos
- [ ] ✅ Docstrings em 100% das funções públicas

#### Deployment:
- [ ] ✅ Dockerfile funcional
- [ ] ✅ docker-compose.yml pronto
- [ ] ✅ Scripts de backup e cleanup
- [ ] ✅ Documentação de deploy completa

#### Performance:
- [ ] ✅ Criar 1000 emails sem travamentos
- [ ] ✅ API P95 latency < 500ms
- [ ] ✅ UI responsiva durante operações pesadas

#### Documentação:
- [ ] ✅ README atualizado e completo
- [ ] ✅ DEPLOYMENT.md criado
- [ ] ✅ API docs (Swagger) acessível
- [ ] ✅ AUDITORIA_COMPLETA.md revisada

---

## TRACKING DE PROGRESSO

### Como usar este documento:

1. **Escolha uma tarefa** da Fase 1 (críticas)
2. **Marque as subtarefas** com `[x]` conforme completa
3. **Commit após cada subtarefa** completa
4. **Rode os testes** antes de marcar como concluído
5. **Atualize este arquivo** regularmente

### Progresso Atual (exemplo):

```
Fase 1: Features Críticas
├── Tarefa 1: Extração de Códigos [0/7] 🔴
├── Tarefa 2: UI Desktop [0/10] 🔴
└── Status: NÃO INICIADO

Fase 2: Qualidade e Arquitetura
├── Tarefa 3: Services [0/3] 🟡
├── Tarefa 4: Testes Integração [0/4] 🟡
└── Status: NÃO INICIADO

Fase 3: Deployment
├── Tarefa 5: Docker [0/4] 🟡
├── Tarefa 6: Ops [0/2] 🟢
└── Status: NÃO INICIADO
```

### Próxima Sessão de Trabalho:

**Tarefa Recomendada:** Tarefa 1 - Sistema de Extração de Códigos  
**Subtarefa:** 1.1 Criar estrutura do módulo  
**Estimativa:** 2 horas  
**Dependências:** Nenhuma

---

**IMPORTANTE:** Este plano assume desenvolvimento sequencial. Ajuste conforme sua disponibilidade e prioridades específicas.

**Última Atualização:** 2025-01-XX  
**Mantido por:** Equipe de Desenvolvimento
