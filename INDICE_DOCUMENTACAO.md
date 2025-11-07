# ÍNDICE DE DOCUMENTAÇÃO - Guia Completo

## 📋 Documentos Criados

### 1. **PROMPT_PRINCIPAL.md** 
Visão geral do projeto, objetivos, requisitos não-funcionais, casos de uso e fluxo de desenvolvimento.

**Quando usar:** Leia PRIMEIRO para entender a visão geral do projeto.

---

### 2. **TECHNICAL_STACK.md**
Stack tecnológico completo com versões exatas, dependências, ferramentas e compatibilidade de plataformas.

**Quando usar:** Antes de começar qualquer implementação. Instale exatamente as versões especificadas.

**Seções principais:**
- Python 3.11+
- FastAPI + Uvicorn (Backend)
- PyQt6 (UI Desktop)
- SQLite + SQLAlchemy (Database)
- Cryptography (Segurança)
- Pytest + Loguru (Testes e Logging)

---

### 3. **PROJECT_STRUCTURE.md**
Estrutura completa de pastas, organização de código e convenções de codificação.

**Quando usar:** Ao criar a estrutura do projeto. Use como template para criar pastas e arquivos.

**Seções principais:**
- Árvore de diretórios completa
- Descrição de cada módulo
- Convenções de nomenclatura
- Padrões de imports

---

### 4. **MAIL_TM_INTEGRATION.md**
Como integrar com Mail.tm API, incluindo cliente Python completo com retry e rate limiting.

**Quando usar:** Ao implementar `core/mail_tm/client.py`

**Conteúdo:**
- Autenticação Mail.tm
- Código completo de MailTmClient
- Rate limiting (8 req/seg)
- Retry com exponential backoff
- Exemplos de uso

---

### 5. **CODE_EXTRACTION.md**
Sistema completo de extração de códigos com múltiplos padrões regex pré-definidos.

**Quando usar:** Ao implementar `core/extraction/code_extractor.py`

**Padrões inclusos:**
- OTP (4/5/6/8 dígitos)
- Códigos com palavras-chave
- URLs de verificação
- Tokens e Recovery codes
- Google Authenticator
- 10+ padrões diferentes

---

### 6. **API_ENDPOINTS.md**
Especificação completa de todos os endpoints REST com exemplos de request/response.

**Quando usar:** Ao implementar `api/routes/`

**Endpoints:**
- `/auth/token` - Autenticação
- `/emails/generate` - Criar emails
- `/emails` - Listar/Deletar
- `/messages` - Gerenciar mensagens
- `/codes` - Verificar códigos
- `/webhooks` - Registrar webhooks

---

### 7. **API_SPECIFICATIONS.md**
Especificações técnicas detalhadas: autenticação, rate limiting, validação, paginação, error handling.

**Quando usar:** Ao implementar `api/`

**Seções:**
- Autenticação JWT + API Key
- Rate limiting implementação
- Validação Pydantic
- Paginação offset/limit
- Error handling global
- Async/Await com connection pooling
- CORS configuration
- Logging estruturado

---

### 8. **UI_REQUIREMENTS.md**
Especificação detalhada da interface gráfica com layouts ASCII, componentes, interações e UX.

**Quando usar:** Ao implementar `ui/`

**Abas:**
1. **Generator** - Criar emails com progresso
2. **Inbox** - Verificar mensagens e códigos
3. **Settings** - Configurações
4. **Status** - Monitoramento e gráficos

---

### 9. **DATA_FLOWS.md**
Fluxos completos de dados entre componentes, diagramas de sequência e eventos.

**Quando usar:** Durante implementação para entender interações entre módulos.

**Fluxos:**
1. Criação de emails em batch via UI
2. Verificação de mensagens e extração
3. Criação via API RESTful
4. Sistema de webhooks
5. Auto-delete de expirados
6. Sincronização UI ↔ API

---

### 10. **ERROR_HANDLING.md**
Estratégia completa de tratamento de erros, retry logic, logging, monitoring e alerting.

**Quando usar:** Durante implementação de qualquer componente que fale com rede/DB.

**Conteúdo:**
- Taxonomia de erros (4xx vs 5xx)
- Retry com exponential backoff
- Circuit breaker pattern
- Logging estruturado
- Error messages amigáveis para UI
- Monitoring e alerting

---

## 🚀 Fluxo de Desenvolvimento Recomendado

### Fase 1: Setup (1-2 horas)
1. Ler TECHNICAL_STACK.md
2. Ler PROJECT_STRUCTURE.md
3. Criar estrutura de pastas
4. Instalar dependências: `pip install -r requirements.txt`
5. Setup de git e versionamento

### Fase 2: Core (4-6 horas)
1. Ler MAIL_TM_INTEGRATION.md
2. Implementar `core/mail_tm/client.py` - MailTmClient
3. Implementar `core/database/models.py` - Modelos SQLAlchemy
4. Implementar `core/database/operations.py` - CRUD

### Fase 3: Extração (2-3 horas)
1. Ler CODE_EXTRACTION.md
2. Implementar `core/extraction/code_extractor.py`
3. Escrever testes unitários em `tests/unit/test_code_extractor.py`

### Fase 4: API (6-8 horas)
1. Ler API_ENDPOINTS.md
2. Ler API_SPECIFICATIONS.md
3. Implementar `api/app.py` - Setup FastAPI
4. Implementar `api/routes/emails.py`
5. Implementar `api/routes/messages.py`
6. Implementar `api/routes/codes.py`
7. Implementar autenticação e rate limiting

### Fase 5: UI (8-10 horas)
1. Ler UI_REQUIREMENTS.md
2. Implementar `ui/main_window.py` - Janela principal
3. Implementar abas:
   - `ui/tabs/generator_tab.py`
   - `ui/tabs/inbox_tab.py`
   - `ui/tabs/settings_tab.py`
   - `ui/tabs/status_tab.py`
4. Implementar workers e threading

### Fase 6: Integração (4-5 horas)
1. Ler DATA_FLOWS.md
2. Conectar UI com MailTmClient
3. Implementar sincronização UI ↔ API
4. Testar fluxos completos

### Fase 7: Robustez (4-5 horas)
1. Ler ERROR_HANDLING.md
2. Adicionar tratamento de erros em todos componentes
3. Implementar logging em todos módulos
4. Adicionar retry logic

### Fase 8: Testes (4-6 horas)
1. Testes unitários para MailTmClient
2. Testes para CodeExtractor
3. Testes de API endpoints
4. Testes de fluxos E2E

### Fase 9: Polish (2-3 horas)
1. Dark mode / Light mode
2. Internacionalização (pt-BR, en-US)
3. Documentação inline
4. Build executáveis

---

## 📚 Como Usar Esta Documentação

### Para Implementar uma Feature
1. Consulte o documento relevante
2. Siga os padrões e convenções
3. Implemente com type hints
4. Adicione docstrings
5. Escreva testes
6. Refira-se a ERROR_HANDLING para erros

### Para Entender Arquitetura
1. Leia PROMPT_PRINCIPAL.md (visão geral)
2. Leia PROJECT_STRUCTURE.md (organização)
3. Leia DATA_FLOWS.md (interações)

### Para Troubleshooting
1. Consulte ERROR_HANDLING.md
2. Verifique logging em `logs/` diretório
3. Procure por request_id nos logs
4. Implemente circuit breaker se necessário

---

## 🎯 Pontos-Chave de Implementação

### Security
- Criptografar todas senhas com Fernet
- Validar todas entradas com Pydantic
- Rate limiting: 8 req/sec para Mail.tm, 100/min por IP
- JWT tokens com 24h de vida útil

### Performance
- ThreadPoolExecutor com max 8 workers
- Caching de domínios (1 hora TTL)
- Connection pooling SQLAlchemy
- Paginação com limit max 1000

### Reliability
- Retry com exponential backoff
- Circuit breaker para serviços externos
- Health checks cada 5 minutos
- Logging estruturado com request_id

### UX
- Todas operações de rede em thread separada
- Feedback visual: spinner, barra progresso
- Notificações toast para eventos
- Dark/Light mode support

---

## 📞 Suporte e Recursos

### Documentação Externa
- FastAPI: https://fastapi.tiangolo.com/
- PyQt6: https://www.riverbankcomputing.com/static/Docs/PyQt6/
- SQLAlchemy: https://docs.sqlalchemy.org/
- Mail.tm API: https://mail.tm/

### Testes
- Pytest: https://docs.pytest.org/
- Loguru: https://loguru.readthedocs.io/

### Ferramentas
- Git: https://git-scm.com/
- Docker: https://www.docker.com/
- Swagger: http://localhost:5000/docs (quando API está rodando)

---

## ✅ Checklist de Implementação

- [ ] Setup ambiente (Python, venv, dependências)
- [ ] Criar estrutura de pastas
- [ ] Implementar MailTmClient
- [ ] Implementar CodeExtractor
- [ ] Implementar Database models
- [ ] Implementar API endpoints
- [ ] Implementar UI (4 abas)
- [ ] Conectar UI com API
- [ ] Adicionar tratamento de erros
- [ ] Adicionar logging em todos módulos
- [ ] Escrever testes unitários
- [ ] Escrever testes de integração
- [ ] Build executável
- [ ] Documentação final

---

## 📝 Última Atualização

**Data:** 2025-11-06  
**Versão:** 2.0  
**Status:** Pronto para Implementação

---

**Criado por:** Fabio Sarmento  
**Projeto:** Mail.tm Email Manager - Sistema Completo com UI + API