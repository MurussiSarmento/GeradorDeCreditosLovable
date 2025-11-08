# Guia de Continuidade — GeradorDeContasLovable

Este guia resume o estado atual do projeto e fornece passos práticos para você pausar e retomar com segurança em outra oportunidade.

## Visão Geral
- Objetivo: gerenciar contas de e-mail temporárias (Mail.tm), gerar lotes de contas, listar e-mails, acessar mensagens, e expor uma API REST para automação.
- Stack: FastAPI, SQLAlchemy (SQLite), Pydantic, Loguru, Requests.
- Organização principal: `api/` (FastAPI), `core/` (config, cliente Mail.tm, DB), `scripts/` (utilitários), `utils/` (logger, crypto), `data/` (saídas e bancos), `tests/`.

## Estado Atual
- API estruturada com routers: `health`, `auth`, `emails`, `messages`, `jobs`, `webhooks`.
- App FastAPI criado em `api/app.py` via `create_app()` e exportado como `app`.
- Entrypoint `main.py` faz bootstrap (logs e diretórios). Para servir HTTP, usar `uvicorn` apontando para `api.app:app`.
- Scripts de geração disponíveis e funcionais:
  - `scripts/generate_100_emails.py` (dummy, determinístico, sem chamadas externas).
  - `scripts/generate_100_emails_real.py` (real, usa Mail.tm, respeita rate limit).
- Dados gerados presentes em `data/` (arquivos `.txt`, `.csv` e bancos SQLite de teste).

## Artefatos Gerados (exemplos)
- `data/generated_100_emails.txt` e `data/generated_100_emails.csv` — geração dummy.
- `data/generated_real_100_emails.txt` e `data/generated_real_100_emails.csv` — contas reais Mail.tm.
- Bancos SQLite de teste (ex.: `data/test_emails_generate_100.db`, `data/test_emails_*.db`).

## Como Executar (Windows/PowerShell)
1) Instalar dependências:
   - `pip install -r requirements.txt`
2) Configurar variáveis de ambiente mínimas:
   - `cp .env.example .env` (ou configure manualmente)
   - Defina `API_KEY`: `setx API_KEY "test-key"` (ou ` $env:API_KEY = "test-key"` para a sessão)
3) Inicializar banco (opcional em primeiro uso):
   - `python scripts/init_db.py`
4) Rodar testes:
   - `python -m pytest -v`
5) Iniciar a API (HTTP):
   - `uvicorn api.app:app --host 127.0.0.1 --port 8000`
6) Abrir docs Swagger (quando API ativa):
   - `http://127.0.0.1:8000/docs`

## Scripts de Geração
- Dummy (rápido, sem externo):
  - `python scripts/generate_100_emails.py`
  - Saídas: `data/generated_100_emails.txt`, `data/generated_100_emails.csv`
- Real (Mail.tm, respeita rate limit):
  - (Opcional) `FERNET_KEY` para criptografia de senhas no DB
  - `python scripts/generate_100_emails_real.py`
  - Saídas: `data/generated_real_100_emails.txt`, `data/generated_real_100_emails.csv`
  - Observação: o script define `MAIL_TM_RATE_LIMIT=1` por segurança contra 429.

## Endpoints Principais
- `GET /health` — status da API.
- `POST /auth/login` — fluxo de autenticação (quando aplicável).
- `GET /emails` — listar e filtrar e-mails (headers: `x-api-key`).
- `POST /emails/generate` — gerar e-mails (dummy ou real conforme cliente configurado).
- `GET /messages/{email}` — listar mensagens de um e-mail.
- `POST /jobs` / `GET /jobs/{id}` — submissão e acompanhamento de jobs.
- `POST /webhooks` — registro de webhooks.

Exemplos de uso (`PowerShell`):
- Listar e-mails: `curl.exe -s "http://localhost:8000/emails?sort_by=email&order=asc" -H "x-api-key: $env:API_KEY"`
- Gerar e-mails: `curl.exe -s -X POST "http://localhost:8000/emails/generate" -H "Content-Type: application/json" -H "x-api-key: $env:API_KEY" -d '{"quantity": 100, "sync": true}'`
- Mensagens do e-mail: `curl.exe -s "http://localhost:8000/messages/<email>" -H "x-api-key: $env:API_KEY"`

## Variáveis de Ambiente
- `API_KEY` — chave usada pela API para autorizar chamadas.
- `DATABASE_URL` — padrão `sqlite:///data/emails.db`.
- `LOG_LEVEL` — níveis (`INFO`, `DEBUG`, etc.).
- `FERNET_KEY` — opcional; ativa criptografia de senhas no banco.
- `MAIL_TM_API_URL` — endpoint da API Mail.tm (padrão oficial).
- `MAIL_TM_RATE_LIMIT` — limite interno para evitar 429.

## Próximos Passos (quando retomar)
- Validar e, se necessário, ajustar documentação dos endpoints em `API_ENDPOINTS.md`.
- Consolidar testes de integração para `emails`, `messages` e `webhooks`.
- Considerar persistência de `jobs` além de memória.
- Completar itens prioritários em `PLANO_ACAO_PRIORIZADO.md` e acompanhar `DASHBOARD_STATUS.md`.

## Retomar Trabalho com Segurança
1) Ler este `GUIA_CONTINUIDADE.md` para situar-se rapidamente.
2) Verificar `.env` e variáveis de ambiente críticas (`API_KEY`, `FERNET_KEY`).
3) Subir a API com `uvicorn api.app:app --port 8000`.
4) Recriar dados de teste, se necessário, rodando os scripts de geração.
5) Executar testes (`pytest`) e validar integração local.
6) Prosseguir com a próxima fase/feature do roadmap.

## Referências e Documentação
- `README.md` — início rápido e comandos básicos.
- `PROJECT_STRUCTURE.md` — estrutura detalhada do projeto.
- `API_ENDPOINTS.md` / `API_SPECIFICATIONS.md` — contratos da API.
- `MAIL_TM_INTEGRATION.md` — integração com Mail.tm.
- `DATA_FLOWS.md` — fluxos de dados e interações.
- `PLANO_ACAO_PRIORIZADO.md` — planejamento e checklists.
- `DASHBOARD_STATUS.md` — status e roadmap de alto nível.
- `ERROR_HANDLING.md` — padrões de tratamento de erros.