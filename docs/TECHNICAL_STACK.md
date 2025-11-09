# TECHNICAL STACK - Stack Técnico Completo

## Visão Geral da Stack

Esta é uma aplicação **Python full-stack** com backend (API REST), frontend (UI Desktop) e banco de dados. Todas as versões devem ser **exatamente como especificado** para garantir compatibilidade.

## Python e Versão

```
Python: 3.11.0 ou superior (recomendado 3.12.x)
- Type hints modernos
- Performance melhorada
- Suporte a async/await completo
```

**Verificar versão:**
```bash
python --version  # Deve retornar Python 3.11.0+
```

## Backend - API REST

### Opção A: FastAPI (RECOMENDADO para performance)
```yaml
fastapi: 0.104.1
uvicorn: 0.24.0
  - servidor ASGI
pydantic: 2.5.0
  - validação de dados
pydantic-settings: 2.1.0
  - configuração via env vars
python-multipart: 0.0.6
  - upload de arquivos (opcional)
```

**Vantagens FastAPI:**
- Auto-documentação Swagger/OpenAPI
- Validação automática com Pydantic
- Performance superior (async)
- Type hints nativos

### Opção B: Flask (se preferir framework leve)
```yaml
flask: 2.3.2
flask-cors: 4.0.0
  - CORS handling
flask-limiter: 3.5.0
  - rate limiting
werkzeug: 2.3.0
  - WSGI server
```

## Frontend - Interface Gráfica Desktop

### PyQt6 (OBRIGATÓRIO)
```yaml
PyQt6: 6.6.1
  - framework principal de UI
PyQt6-WebEngine: 6.6.0
  - renderização de HTML/CSS (opcional para visualizar emails)
PyQtWebEngine: 6.6.0
  - integração com web engine
```

**Por que PyQt6:**
- Nativo, não é Electron (mais leve)
- Comunidade ativa
- Suporta dark mode nativo
- Threading built-in (QThread)

**Alternativa:** Tkinter (vem com Python, mais simples mas limitado)

## HTTP e Requisições

### Requests (client HTTP para chamadas API)
```yaml
requests: 2.31.0
  - chamadas HTTP simples
httpx: 0.25.2
  - alternativa com async/await
aiohttp: 3.9.1
  - client HTTP assíncrono
urllib3: 2.1.0
  - pool de conexões
```

**Principal:** Requests para síncrono, httpx/aiohttp para async

## Banco de Dados

### SQLite (built-in, nenhuma dependência extra)
- Arquivo: `./data/emails.db`
- Perfeito para aplicação single-user
- Suporta transações ACID
- Backup simples (copiar arquivo)

### ORM: SQLAlchemy
```yaml
SQLAlchemy: 2.0.23
  - ORM e query builder
alembic: 1.13.0
  - migrations de schema
```

**Schema Management:**
```python
# SQLAlchemy + Alembic para migrações
from sqlalchemy import create_engine, Column, String, DateTime
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class EmailAccount(Base):
    __tablename__ = 'emails'
    id = Column(String, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    # ...
```

## Segurança

### Criptografia
```yaml
cryptography: 41.0.7
  - Fernet para criptografia simétrica (senhas)
  - RSA para keys assíncronas (opcional)

PyJWT: 2.8.1
  - Geração e validação de JWT tokens
  - Para autenticação da API
```

**Usar para criptografar:**
```python
from cryptography.fernet import Fernet

key = Fernet.generate_key()
cipher = Fernet(key)
encrypted_password = cipher.encrypt(password.encode())
```

### Validação e Sanitização
```yaml
pydantic: 2.5.0
  - validar all inputs automático
email-validator: 2.1.0
  - validar email format
bleach: 6.1.0
  - sanitizar HTML (para emails)
```

## Logging e Monitoramento

### Loguru (logging estruturado)
```yaml
loguru: 0.7.2
  - logging colorido e estruturado
  - rotação automática de arquivos
  - níveis: DEBUG, INFO, WARNING, ERROR, CRITICAL
```

**Estrutura de logs:**
```
./logs/
├── app.log          # Logs gerais da aplicação
├── api.log          # Logs da API REST
└── extraction.log   # Logs de extração de códigos
```

### Monitoramento (opcional)
```yaml
psutil: 5.9.6
  - monitorar CPU, memória, processos
prometheus-client: 0.19.0
  - métricas Prometheus
```

## Processamento de Texto e Regex

### Regex (built-in)
```python
import re
# Usar biblioteca padrão Python
```

### Regex Avançado (opcional)
```yaml
regex: 2023.12.25
  - suporta lookahead/lookbehind mais avançado
  - named groups
```

### HTML/XML Parsing
```yaml
beautifulsoup4: 4.12.2
  - parsear HTML de emails
lxml: 4.9.3
  - backend rápido para BeautifulSoup
```

## Testes

### Framework de Testes
```yaml
pytest: 7.4.3
  - test runner padrão Python
pytest-cov: 4.1.0
  - code coverage
pytest-mock: 3.12.0
  - mocking
pytest-asyncio: 0.21.1
  - testes de código assíncrono
```

**Estrutura de testes:**
```
tests/
├── unit/
│   ├── test_mail_tm_client.py
│   ├── test_code_extractor.py
│   └── test_database.py
├── integration/
│   └── test_api_endpoints.py
└── conftest.py  # fixtures compartilhadas
```

### Mocking
```yaml
responses: 0.24.1
  - mock de requests HTTP
unittest.mock: built-in
  - mocking nativo Python
```

## Configuração e Ambiente

### Variáveis de Ambiente
```yaml
python-dotenv: 1.0.0
  - carregar .env automaticamente
```

**.env file:**
```
ENVIRONMENT=development
FLASK_DEBUG=True
MAIL_TM_API_URL=https://api.mail.tm
DATABASE_PATH=./data/emails.db
API_PORT=5000
API_HOST=0.0.0.0
LOG_LEVEL=INFO
```

## Visualização de Dados (opcional)

### Gráficos
```yaml
matplotlib: 3.8.2
  - gráficos estáticos
plotly: 5.18.0
  - gráficos interativos
pandas: 2.1.3
  - análise de dados
```

## Build e Distribuição

### Executável Windows/Linux/Mac
```yaml
PyInstaller: 6.1.0
  - build executável único
auto-py-to-exe: 2.42.0
  - GUI para PyInstaller (opcional)
```

**Comando build:**
```bash
pyinstaller --onefile --windowed --icon=app.ico main.py
```

### Containers
```yaml
Docker: (não é pip package)
  - Dockerfile fornecido
  - docker-compose.yml para orquestração
```

**Dockerfile exemplo:**
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
CMD ["python", "main.py"]
```

## Ferramentas de Desenvolvimento

### Linting e Formatação
```yaml
black: 23.12.0
  - formatação automática (PEP 8)
isort: 5.13.2
  - ordenar imports
flake8: 6.1.0
  - linting
pylint: 3.0.3
  - análise de código
```

**Pre-commit hooks:**
```yaml
pre-commit: 3.5.0
  - rodar checks antes de commit
```

### Type Checking
```yaml
mypy: 1.7.1
  - verificação de tipos estática
types-requests: 2.31.0.10
  - type stubs para requests
```

## Dependências de Tempo de Execução vs Desenvolvimento

### Production (requirements.txt)
```
fastapi==0.104.1
uvicorn==0.24.0
requests==2.31.0
PyQt6==6.6.1
SQLAlchemy==2.0.23
cryptography==41.0.7
loguru==0.7.2
python-dotenv==1.0.0
PyJWT==2.8.1
pydantic==2.5.0
```

### Development (requirements-dev.txt)
```
-r requirements.txt
pytest==7.4.3
pytest-cov==4.1.0
pytest-mock==3.12.0
black==23.12.0
isort==5.13.2
flake8==6.1.0
mypy==1.7.1
pre-commit==3.5.0
PyInstaller==6.1.0
```

**Instalar ambiente:**
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows

pip install -r requirements-dev.txt
pre-commit install
```

## Especificações de Hardware Recomendado

Para desenvolvimento:
- CPU: Dual-core 2GHz+
- RAM: 4GB mínimo, 8GB recomendado
- Disk: 2GB espaço livre

Para produção (servidor):
- CPU: Quad-core 2GHz+
- RAM: 8GB+
- Disk: 10GB+ (para banco de dados crescer)

## Performance Esperado

Com a stack especificada:
- Criar 1000 emails: ~2 minutos
- Resposta API (p95): < 200ms
- Memória da aplicação: < 200MB
- Throughput API: 100+ req/sec

## Compatibilidade de Plataforma

| Componente | Windows 10+ | Linux | macOS |
|-----------|----------|-------|-------|
| Python 3.11+ | ✅ | ✅ | ✅ |
| PyQt6 | ✅ | ✅ | ✅ |
| SQLite | ✅ | ✅ | ✅ |
| FastAPI | ✅ | ✅ | ✅ |
| Cryptography | ✅ | ✅ | ✅ |

## Versões Fixadas vs Flexíveis

**NUNCA mude:** FastAPI, PyQt6, SQLAlchemy, cryptography (core crítico)

**OK atualizar:** Black, isort, pytest, logging (tools não core)

**Procedimeneto para atualizar:**
1. Testar localmente com nova versão
2. Rodar suite de testes completa
3. Se ok, atualizar requirements.txt com nova versão
4. Documentar mudança no CHANGELOG

---

**Versão Stack:** 2025-11-06  
**Status:** Produção Pronto