# Proxy Manager & Validator — To‑do List

Este documento consolida o status atual, pendências e plano de ação para concluir o Proxy Manager & Validator, cobrindo API e UI Desktop, conforme o PRD "Proxy Manager & Validator Tool.md".

## Visão Geral
- Objetivo: coletar, validar, gerenciar e servir proxies (HTTP/HTTPS, com expansão para SOCKS) via API e UI.
- Stack: `FastAPI`, `SQLite/SQLAlchemy`, `aiohttp`, `CustomTkinter`.
- Autenticação: `X-API-Key` e suporte opcional a JWT (`/auth/token`).

## Status Atual
- [x] Modelo `Proxy` no banco (`core/database/models.py`).
- [x] Operações CRUD e utilitárias (`core/database/operations.py`).
- [x] Scraper assíncrono de fontes iniciais (`core/proxy/scraper.py`).
- [x] Validator assíncrono com métricas básicas (`core/proxy/validator.py`).
- [x] Schemas Pydantic para endpoints (`api/schemas.py`).
- [x] Roteador FastAPI `/api/v1/proxies` com endpoints principais (`api/routers/proxies.py`).
- [x] Registro do roteador na aplicação (`api/app.py`).
- [x] UI Desktop básica em `CustomTkinter` (`proxy_manager/ui.py`).
- [x] Dependências atualizadas (`requirements.txt`).

## Decisões Tomadas
- Protocolos suportados: `http`, `https` e validação `socks4/socks5`.
- Validação realizada via `aiohttp` com cálculo de tempo médio e flag `valid`.
- Fontes implementadas: `ProxyScrape` e `Free-Proxy-List.net`.
- UI com scraping, import e validação; tarefas em threads para não bloquear.

## Pendências Imediatas (Prioridade Alta)
- [x] Suporte a `SOCKS4/SOCKS5` na validação (via `aiohttp_socks`).
- [x] Implementar `auto_validate` como job em background (integração com módulo de jobs).
- [ ] Expandir fontes de scraping conforme PRD (SSLProxies, GatherProxy, Spys.one, PubProxy, Proxify etc.).
  - Implementadas: `sslproxies`, `pubproxy` (JSON com país), `gatherproxy`, `Spys.one` (básico).
  - Novas: `us-proxy` (us-proxy.org) adicionada; `proxyscrape` já disponível.
  - Novas (API): `proxy-list.download` (HTTP/HTTPS via API) adicionada.
  - Novas (API): `proxyscan.io` (HTTP/HTTPS/SOCKS com país) adicionada.
  - Novas (listas públicas): `github-speedx` (TheSpeedX/PROXY-List — HTTP/HTTPS/SOCKS) adicionada.
  - Novas (listas públicas): `github-shiftytr` (ShiftyTR/Proxy-List — HTTP/HTTPS/SOCKS) adicionada.
  - Novas (listas públicas): `github-monosans` (monosans/proxy-list — HTTP/HTTPS/SOCKS) adicionada.
  - Novas (listas públicas): `github-jetkai` (jetkai/proxy-list — HTTP/HTTPS/SOCKS) adicionada.
  - Testes: adicionados testes unitários para fontes GitHub e agregador com deduplicação.
  - Testes: adicionados testes de parser HTML para `free-proxy-list`, `sslproxies` e `us-proxy`.
  - Testes: adicionados testes unitários para `gatherproxy` (portas HEX/decimal, filtros) e `pubproxy` (JSON com país/protocolo).
  - Testes: adicionados testes unitários para `spys.one` (regex IP:PORT, filtros) e `proxy-list.download` (http/https).
- [x] Ordenação na listagem por latência e última checagem (API).
- [x] Filtros avançados na listagem (país, protocolo, anonimato com combinações).
- [x] Geolocalização e nível de anonimato (básico via `httpbin.org` e `ip-api.com`).
 - [x] Aprimorar geolocalização/anonimato (fontes extras e heurísticas mais robustas).
- [ ] Suporte a SOCKS na UI (seleção de protocolos e exibição nas colunas).
- [x] Suporte a SOCKS na UI (seleção de protocolos e exibição nas colunas).

## Backlog Prioritário
- [ ] Scheduler de scraping/validação (periodicidade configurável; UI + API endpoints).
 - [x] Métricas e observabilidade (contadores, tempos médios, taxa de sucesso, status por fonte).
 - [x] Limites de taxa e concorrência dedicados às rotas de proxies.
- [x] Rate limit por fonte de scraping (cap/min configurável por env).
- [ ] Rotação de proxies integrada ao `core/mail_tm/client.py` quando aplicável.
- [ ] Tabela interativa na UI (sorting, seleção, ações em lote, filtros).
- [ ] Import/Export avançado (CSV/JSON; parsing robusto; deduplicação).
- [x] Tratamento de timeouts por fonte de scraping (configurado via função).
- [x] Cache leve de scraping (TTL ~120s) para reduzir chamadas.
- [ ] Persistência de preferências da UI entre sessões.

## API — Itens de Implementação
- [x] `POST /api/v1/proxies/scrape` — scraping básico com persistência.
- [x] `POST /api/v1/proxies/validate` — validação com múltiplas URLs e métricas.
- [x] `GET /api/v1/proxies` — listagem paginada com filtros simples.
- [x] `GET /api/v1/proxies/random` — seleção aleatória com filtros.
- [x] `DELETE /api/v1/proxies` — limpeza (todos ou apenas inválidos).
- [x] `POST /api/v1/proxies/import` — import básico (lista simples `ip:port`).
- [x] `POST /api/v1/proxies/schedule` — agendar validação e scraping básico (integração com jobs).
- [x] `GET /api/v1/proxies/stats` — métricas agregadas (por fonte, protocolo, país, latência).
 - [x] `PATCH /api/v1/proxies/{id}` — atualizar metadados (ex.: `country`, `anonymity`).
 - [x] `GET /api/v1/proxies/{id}` — detalhe do proxy.

### Critérios de Aceite (API)
- [ ] Endpoints autenticados via `X-API-Key` e retornos consistentes com `api/schemas.py`.
- [ ] Validação suporta `http/https/socks4/socks5` e calcula latência média.
- [x] Listagem com paginação e ordenação por `avg_response_time_ms` e `last_checked`.
- [ ] Filtros avançados por país, protocolo e anonimato.
- [ ] Métricas acessíveis e úteis para decisão de uso.

## UI Desktop — Itens de Implementação
- [x] Painel scraping, import e validação com barra de status.
- [x] Tabela com colunas: IP, Porta, Protocolo, País, Anonimato, Latência, Validez, Última checagem.
- [x] Filtros na UI (país, protocolo, validade, latência máx.).
- [x] Ações em lote (validar selecionados, excluir inválidos, exportar CSV/JSON).
- [ ] Configurações persistentes (timeout, fontes, URLs de teste, concorrência).
- [ ] Agendador na UI (cron simples / repetição) e indicadores de jobs ativos.

### Critérios de Aceite (UI)
- [ ] UI responsiva, não bloqueia durante operações.
- [ ] Feedback claro de progresso e erros; contadores e totais visíveis.
- [ ] Persistência das preferências e última sessão.

## Infra/Arquitetura
- [x] Adicionar `aiohttp_socks` a `requirements.txt` para SOCKS.
- [ ] Separar limites de concorrência por tarefa (scrape vs validate) e por fonte.
- [ ] Padronizar logging nas rotas e módulos (`utils/logger.py`).
- [ ] Padronizar logging nas rotas e módulos (`utils/logger.py`) — iniciado nas rotas de proxies.
- [ ] Feature flags para habilitar/desabilitar fontes e modos de validação.
- [x] Habilitar CORS na aplicação FastAPI.
- [x] Restringir CORS por ambiente (produção com `allow_origins` específico).

## Testes e Validação
- [x] Testes unitários para `core/proxy/scraper.py` e `validator.py`.
- [x] Testes de API: `tests/unit/test_api_proxies.py` cobrindo todos endpoints.
- [ ] Testes de performance em validação (tempo, timeouts, concorrência).
- [ ] Testes de integração com banco: persistência, filtros e deleção.
- [x] Mock de fontes externas para scraping determinístico.

### Cobertura adicionada nos testes de API
- Import, listagem com filtros, `random` (requer proxy válido), `validate` com `monkeypatch`, `stats`, `scrape` com `monkeypatch`, `delete` e `schedule` (scrape/validate).
- Ajustes de compatibilidade de schema: mocks retornam campos exigidos por `ProxyValidationResult`.
- Evitada dependência externa ausente (`aiohttp_socks`) via stub isolado nos testes.
- Adicionado polling de jobs para validação e scraping de proxies; `JobStatusResponse.result` ajustado para aceitar `dict` e `list`, cobrindo progresso e resultados agregados.
- Cobertos cenários de falha em jobs (validate e scrape) com asserts de `status=failed` e `error`.
- Coberto progresso intermediário em validação com múltiplos proxies (observação de `progress` entre 0 e 1).
 - Cobertura adicional do router de jobs: `GET /jobs/{id}` retorna 404 para IDs inexistentes; asserts de `duration_seconds > 0` e `eta_seconds == None` após conclusão.
- Verificado `polling_url` nos agendamentos: `POST /emails/generate` e `POST /api/v1/proxies/schedule` retornam URL válida; `GET` no `polling_url` corresponde ao mesmo `job_id`.
- Validação de campos opcionais ausentes: quando `progress` não está presente no job, o endpoint de status retorna `progress == None` corretamente.
- Filtros combinados: listagem com `valid_only=true` + `protocol=http`; endpoint `random` com `protocol=http` + `max_response_time` verificado com proxies mockados de baixa latência.
- Ordenação: verificado `order_by=avg_response_time_ms` com `order=asc/desc` e `order_by=last_checked` na listagem; latências e timestamps definidos via validação mock.
- Deleção: `DELETE /api/v1/proxies?invalid_only=true` remove apenas inválidos; contagem total ajustada conforme retorno.
 - Export: `GET /api/v1/proxies/export` (json/csv) com filtros combinados, incluindo `anonymity`.
 - Paginação: verificado `page` e `per_page` com cálculo correto de `total_pages` e distribuição consistente de itens por página.
 - Paginação (fora de faixa): `page > total_pages` retorna lista vazia mantendo metadados consistentes.
 - Limites de `per_page`: validado `per_page=1` (um item) e `per_page=100` (todos os itens disponíveis).
- Estatísticas: `/api/v1/proxies/stats` validado com agregações `by_protocol`, `by_country` e média de latência apenas sobre proxies válidos.
- Paginação (caso exato): `total_pages` calculado corretamente quando `total % per_page == 0`.
 - Ordenação por criação: `order_by=created_at` validado em `asc` e `desc` com importações sequenciais.
 - Ordenação por última checagem: `order_by=last_checked` com `order=desc` prioriza proxies validados quando existem valores nulos.
 - Random 404: `/api/v1/proxies/random` retorna 404 quando não há proxies válidos que atendam aos filtros.
 - Random com filtros combinados: `country=US` + `max_response_time=30` retorna proxy válido; `country=BR` + `max_response_time=30` retorna 404 sem correspondência.
 - Paginação com filtros: verificado `valid_only=true` + `protocol=http` com `per_page` e páginas subsequentes.
 - Paginação com filtros restritivos: `country=US` + `protocol=http` + `valid_only=true` com `per_page=1` distribui corretamente entre páginas.
 - Ordenação case-insensitive e `order_by` desconhecido: `order=ASC/DESC` funciona via lowercasing; `order_by` inválido não quebra e retorna listagem.
 - Import com auto-validate: `POST /api/v1/proxies/import` com `auto_validate=true` e `validation_urls` retorna `validation_started=true` e `polling_url` para acompanhar o job.
 - Ordenação por latência com nulos: `order_by=avg_response_time_ms` coloca `NULL` primeiro em `asc` e por último em `desc` (SQLite).
 - Random HTTPS com filtros: `protocol=https` + `country=US` + `max_response_time=30` retorna sucesso; `country=BR` + `max_response_time=30` retorna 404.

## Riscos e Mitigação
- Fontes externas instáveis: adicionar fallback e cache curto.
- Bloqueios por uso de scraping: respeitar termos, limitar taxa, alternar fontes.
- Proxies maliciosos: validar apenas URLs de teste seguras; isolar timeouts.

## Tarefas Concluídas (Audit Trail)
- DB: `Proxy` e operações — concluído.
- Core: `scraper` e `validator` — concluído (HTTP/HTTPS/SOCKS).
- API: schemas e roteador — concluído (endpoints principais).
- API: `GET /api/v1/proxies/stats` — concluído.
- App: registro de rotas — concluído.
- App: CORS habilitado — concluído.
- UI: base funcional — concluído.
- Requirements: atualização — concluído (`customtkinter`, `validators`, `aiohttp-socks`).
 - API: scraping com `timeout`/`retries` configuráveis por requisição — concluído.
 - Core/API: agendamento de scraping com `timeout`/`retries` (jobs) — concluído.
 - Testes: API `/api/v1/proxies` — concluído (35 testes passando). Router de jobs coberto com 4 testes adicionais.
 - API: limites específicos de rate e concorrência em `/api/v1/proxies/*` — concluído.

## Roadmap Sugerido
- Sprint 1 (Alta prioridade): SOCKS, auto_validate, filtros/ordenação, métricas básicas.
- Sprint 2: novas fontes, scheduler, UI tabela e ações em lote.
- Sprint 3: geolocalização/anonimato, integração com `mail_tm` client e testes avançados.

---

Referências úteis:
- API base: `http://localhost:5000/api/v1/proxies`
- Headers: `X-API-Key: <sua_api_key>`
- Arquivos principais:
  - `core/proxy/scraper.py`
  - `core/proxy/validator.py`
  - `api/routers/proxies.py`
  - `api/schemas.py`
  - `core/database/models.py`
  - `core/database/operations.py`
  - `proxy_manager/ui.py`
### Cobertura adicionada nos testes de Core
- Scraper: parsing de `proxylisttable`, `proxy-list.download` (HTTP/HTTPS), `gatherproxy` (portas HEX/decimal, filtro de protocolos), deduplicação em `scrape_from_sources`.
- Validator: construção de URL com credenciais, validação com sucesso total e sucesso parcial (`test_all_urls`), mocks assíncronos de sessão, anonimato e geolocalização para evitar rede.