# PROJECT STRUCTURE - Estrutura Completa do Projeto

## Estrutura de Pastas

```
temp-email-system/
│
├── main.py                           # Ponto de entrada principal
├── requirements.txt                  # Dependências production
├── requirements-dev.txt              # Dependências desenvolvimento
├── .env.example                      # Template de variáveis ambiente
├── .gitignore                        # Arquivos a ignorar no git
├── README.md                         # Documentação principal
├── Dockerfile                        # Container configuration
├── docker-compose.yml                # Orquestração (opcional)
│
├── core/                             # Lógica de negócio
│   ├── __init__.py
│   ├── config.py                    # Configurações globais
│   ├── exceptions.py                # Exceções customizadas
│   │
│   ├── mail_tm/
│   │   ├── __init__.py
│   │   ├── client.py                # MailTmClient principal
│   │   ├── models.py                # Dataclasses para Mail.tm
│   │   └── constants.py             # URLs, domínios, padrões
│   │
│   ├── extraction/
│   │   ├── __init__.py
│   │   ├── code_extractor.py        # CodeExtractor principal
│   │   ├── patterns.py              # Regex patterns
│   │   └── validators.py            # Validação de códigos
│   │
│   └── database/
│       ├── __init__.py
│       ├── models.py                # SQLAlchemy models
│       ├── session.py               # Session management
│       ├── operations.py            # CRUD operations
│       └── migrations/              # Alembic migrations
│
├── api/                              # API REST
│   ├── __init__.py
│   ├── app.py                       # Criação FastAPI app
│   ├── middleware.py                # Middleware (logging, CORS)
│   ├── dependencies.py              # Dependency injection
│   ├── security.py                  # Autenticação, JWT, API keys
│   │
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── emails.py                # Endpoints /emails
│   │   ├── messages.py              # Endpoints /messages
│   │   ├── codes.py                 # Endpoints /codes
│   │   ├── webhooks.py              # Endpoints /webhooks
│   │   ├── auth.py                  # Endpoints /auth
│   │   └── health.py                # Health check
│   │
│   └── schemas/
│       ├── __init__.py
│       ├── requests.py              # Request models (Pydantic)
│       ├── responses.py             # Response models (Pydantic)
│       └── errors.py                # Error response models
│
├── ui/                               # Interface Gráfica
│   ├── __init__.py
│   ├── main_window.py               # Janela principal
│   ├── styles.qss                   # Stylesheet Qt
│   │
│   ├── tabs/
│   │   ├── __init__.py
│   │   ├── generator_tab.py         # Aba Generator
│   │   ├── inbox_tab.py             # Aba Inbox
│   │   ├── settings_tab.py          # Aba Settings
│   │   └── status_tab.py            # Aba Status/API
│   │
│   ├── widgets/
│   │   ├── __init__.py
│   │   ├── email_table.py           # Tabela de emails
│   │   ├── message_viewer.py        # Visualizador de mensagens
│   │   ├── progress_dialog.py       # Diálogo de progresso
│   │   └── code_display.py          # Widget de códigos extraídos
│   │
│   ├── dialogs/
│   │   ├── __init__.py
│   │   ├── settings_dialog.py       # Diálogo de configurações
│   │   ├── about_dialog.py          # Sobre a aplicação
│   │   └── confirmation_dialog.py   # Confirmação de ações
│   │
│   ├── signals.py                   # Signals customizados
│   ├── utils.py                     # Utilitários da UI
│   └── constants.py                 # Constantes da UI (colors, sizes)
│
├── workers/                          # Threading workers
│   ├── __init__.py
│   ├── email_generator_worker.py    # Worker criação de emails
│   ├── message_checker_worker.py    # Worker verificar mensagens
│   └── code_extractor_worker.py     # Worker extração de códigos
│
├── services/                         # Serviços de integração
│   ├── __init__.py
│   ├── email_service.py             # Lógica de negócio emails
│   ├── message_service.py           # Lógica de negócio mensagens
│   ├── webhook_service.py           # Gerenciar webhooks
│   └── cache_service.py             # Cache (domínios, etc)
│
├── utils/                            # Utilitários gerais
│   ├── __init__.py
│   ├── logger.py                    # Setup de logging
│   ├── crypto.py                    # Criptografia (Fernet)
│   ├── http_client.py               # HTTP client com retry
│   ├── validators.py                # Validadores comuns
│   └── decorators.py                # Decoradores úteis
│
├── tests/                            # Suite de testes
│   ├── __init__.py
│   ├── conftest.py                  # Fixtures pytest
│   │
│   ├── unit/
│   │   ├── __init__.py
│   │   ├── test_mail_tm_client.py   # Testes MailTmClient
│   │   ├── test_code_extractor.py   # Testes CodeExtractor
│   │   ├── test_database.py         # Testes Database ops
│   │   └── test_validators.py       # Testes validadores
│   │
│   ├── integration/
│   │   ├── __init__.py
│   │   ├── test_api_endpoints.py    # Testes endpoints
│   │   ├── test_full_flow.py        # Fluxo completo end-to-end
│   │   └── test_rate_limiting.py    # Testes rate limit
│   │
│   └── fixtures/
│       ├── __init__.py
│       ├── mock_emails.json         # Emails mock para testes
│       ├── mock_messages.json       # Mensagens mock
│       └── sample_codes.txt         # Códigos de exemplo
│
├── docs/                             # Documentação
│   ├── API.md                       # Docs API
│   ├── ARCHITECTURE.md              # Arquitetura
│   ├── DEPLOYMENT.md                # Deploy guia
│   └── TROUBLESHOOTING.md           # Solução de problemas
│
├── logs/                             # Arquivos de log
│   ├── app.log                      # Log geral
│   ├── api.log                      # Log da API
│   └── extraction.log               # Log de extração
│
├── data/                             # Data local
│   ├── emails.db                    # Banco SQLite
│   └── backups/                     # Backups do DB
│
└── scripts/                          # Scripts utilitários
    ├── init_db.py                   # Inicializar banco
    ├── reset_db.py                  # Resetar dados
    ├── export_data.py               # Exportar para CSV/JSON
    └── benchmark.py                 # Testes de performance
```

## Descrição Detalhada de Cada Componente

### 1. `core/` - Núcleo de Negócio

#### `core/config.py`
Centraliza todas as configurações:
```python
class Settings:
    # Mail.tm
    MAIL_TM_API_URL: str = "https://api.mail.tm"
    MAIL_TM_RATE_LIMIT: int = 8  # req/sec
    
    # Database
    DATABASE_URL: str = "sqlite:///data/emails.db"
    
    # API
    API_PORT: int = 5000
    API_HOST: str = "0.0.0.0"
    
    # Logging
    LOG_LEVEL: str = "INFO"
    
    # Security
    SECRET_KEY: str  # Carregado de .env
    ALGORITHM: str = "HS256"
    
    class Config:
        env_file = ".env"
```

#### `core/exceptions.py`
Exceções customizadas da aplicação:
```python
class MailTmException(Exception):
    """Base para erros Mail.tm"""
    pass

class RateLimitException(MailTmException):
    """Rate limit excedido"""
    pass

class DatabaseException(Exception):
    """Erros de banco de dados"""
    pass

class ExtractionException(Exception):
    """Erros de extração de código"""
    pass
```

#### `core/mail_tm/client.py`
Cliente principal da API Mail.tm:
```python
class MailTmClient:
    def __init__(self, base_url: str, rate_limit: int = 8):
        self.base_url = base_url
        self.rate_limit = rate_limit
        self.session = requests.Session()
        self._domain_cache = {}
    
    async def create_random_account(self) -> Dict[str, Any]:
        """Criar email aleatório único"""
        pass
    
    async def batch_create_accounts(self, quantity: int) -> List[Dict]:
        """Criar múltiplos emails em paralelo"""
        pass
    
    async def get_messages(self, token: str) -> List[Dict]:
        """Obter mensagens de um email"""
        pass
```

#### `core/extraction/code_extractor.py`
Extrator de códigos com múltiplos padrões:
```python
class CodeExtractor:
    PATTERNS = {
        'otp_4digit': r'\b\d{4}\b',
        'otp_6digit': r'\b\d{6}\b',
        'otp_8digit': r'\b\d{8}\b',
        # ... mais padrões
    }
    
    def extract_code(self, text: str, pattern: str = 'all') -> Union[str, Dict]:
        """Extrair código usando padrão específico"""
        pass
    
    def extract_with_context(self, text: str) -> List[Dict]:
        """Extrair com contexto (linhas antes/depois)"""
        pass
```

#### `core/database/models.py`
Modelos SQLAlchemy:
```python
class EmailAccount(Base):
    __tablename__ = 'email_accounts'
    
    id = Column(String, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    account_id = Column(String, nullable=False)
    password_encrypted = Column(String, nullable=False)
    token = Column(String)
    domain = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String, default='active')
    
    messages = relationship('Message', back_populates='email_account')

class Message(Base):
    __tablename__ = 'messages'
    
    id = Column(String, primary_key=True)
    email_id = Column(String, ForeignKey('email_accounts.id'))
    from_address = Column(String)
    subject = Column(String)
    body_text = Column(Text)
    body_html = Column(Text)
    extracted_codes = Column(JSON)  # Array de códigos
    received_at = Column(DateTime)
    processed_at = Column(DateTime)
```

### 2. `api/` - API REST

#### `api/app.py`
Criação e configuração da app FastAPI:
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Mail.tm API",
    description="API para gerenciar emails temporários",
    version="1.0.0"
)

# Adicionar routes
app.include_router(router_emails, prefix="/api/v1/emails")
app.include_router(router_messages, prefix="/api/v1/messages")
# ...
```

#### `api/security.py`
Autenticação e autorização:
```python
class APIKeyAuth:
    """Validar API key do header"""
    async def __call__(self, request: Request) -> str:
        api_key = request.headers.get("X-API-Key")
        if not api_key:
            raise HTTPException(status_code=401)
        # Validar API key
        return api_key

class TokenAuth:
    """Validar JWT token"""
    async def __call__(self, request: Request) -> str:
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        if not token:
            raise HTTPException(status_code=401)
        # Validar JWT
        return token
```

#### `api/routes/emails.py`
Endpoints para gerenciar emails:
```python
@router.post("/generate", status_code=201)
async def generate_emails(
    request: GenerateEmailsRequest,
    db: Session = Depends(get_db)
) -> GenerateEmailsResponse:
    """Criar múltiplos emails"""
    pass

@router.get("/", status_code=200)
async def list_emails(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
) -> ListEmailsResponse:
    """Listar emails criados"""
    pass
```

### 3. `ui/` - Interface Gráfica

#### `ui/main_window.py`
Janela principal com abas:
```python
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Mail.tm Email Manager")
        self.setGeometry(100, 100, 1200, 800)
        
        # Setup abas
        self.tabs = QTabWidget()
        self.tabs.addTab(GeneratorTab(), "Generator")
        self.tabs.addTab(InboxTab(), "Inbox")
        self.tabs.addTab(SettingsTab(), "Settings")
        self.tabs.addTab(StatusTab(), "Status")
        
        self.setCentralWidget(self.tabs)
```

#### `ui/tabs/generator_tab.py`
Aba para gerar emails:
```python
class GeneratorTab(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Input quantidade
        self.quantity_input = QSpinBox()
        self.quantity_input.setMinimum(1)
        self.quantity_input.setMaximum(10000)
        
        # Botão gerar
        self.generate_btn = QPushButton("GERAR EMAILS")
        self.generate_btn.clicked.connect(self.on_generate)
        
        # Barra progresso
        self.progress_bar = QProgressBar()
        
        # Tabela resultados
        self.table = QTableWidget()
        
        layout.addWidget(QLabel("Quantidade:"))
        layout.addWidget(self.quantity_input)
        layout.addWidget(self.generate_btn)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.table)
        
        self.setLayout(layout)
```

#### `ui/widgets/email_table.py`
Tabela customizada de emails:
```python
class EmailTable(QTableWidget):
    """Tabela mostrando todos emails com sorting/filtering"""
    
    COLUMNS = ['Email', 'Domain', 'Created', 'Status', 'Actions']
    
    def populate(self, emails: List[Dict]):
        """Popular tabela com emails"""
        pass
    
    def on_copy(self, email: str):
        """Copiar email para clipboard"""
        pass
```

### 4. `workers/` - Workers para Threading

#### `workers/email_generator_worker.py`
Worker que roda em thread separada:
```python
class EmailGeneratorWorker(QRunnable):
    """Gerar emails sem bloquear UI"""
    
    def __init__(self, quantity: int):
        super().__init__()
        self.quantity = quantity
        self.signals = WorkerSignals()
    
    def run(self):
        """Executar geração em background"""
        for i in range(self.quantity):
            # Criar email
            # Emitir sinal de progresso
            self.signals.progress.emit(i + 1)
```

### 5. `services/` - Serviços de Negócio

#### `services/email_service.py`
Lógica de negócio para emails:
```python
class EmailService:
    def __init__(self, db: Session, mail_tm: MailTmClient):
        self.db = db
        self.mail_tm = mail_tm
    
    async def create_emails_batch(self, quantity: int) -> List[Dict]:
        """Criar batch de emails e salvar DB"""
        pass
    
    async def get_email_with_messages(self, email: str) -> Dict:
        """Retornar email com mensagens associadas"""
        pass
    
    async def cleanup_expired_emails(self):
        """Deletar emails expirados"""
        pass
```

### 6. `tests/` - Testes

#### `tests/conftest.py`
Fixtures compartilhadas:
```python
@pytest.fixture
def mail_tm_client():
    """Mock client Mail.tm"""
    return MagicMock(spec=MailTmClient)

@pytest.fixture
def code_extractor():
    """Instância real do extrator"""
    return CodeExtractor()

@pytest.fixture
def test_db():
    """Banco de dados temporário para testes"""
    engine = create_engine("sqlite:///:memory:")
    # ...
```

#### `tests/unit/test_code_extractor.py`
Testes unitários:
```python
def test_extract_otp_6digit(code_extractor):
    """Testar extração de OTP 6 dígitos"""
    text = "Your code is 123456"
    result = code_extractor.extract_code(text, 'otp_6digit')
    assert result == '123456'

def test_extract_multiple_codes(code_extractor):
    """Testar extração de múltiplos códigos"""
    text = "Code 1234 or backup 5678"
    result = code_extractor.extract_code(text, 'all')
    assert len(result) == 2
```

### 7. `docs/` - Documentação

- **API.md**: Documentação completa dos endpoints
- **ARCHITECTURE.md**: Diagrama de componentes
- **DEPLOYMENT.md**: Como fazer deploy em produção
- **TROUBLESHOOTING.md**: Problemas comuns e soluções

## Arquivos Importantes na Raiz

### `.env.example`
Template de variáveis de ambiente:
```env
# Mail.tm
MAIL_TM_API_URL=https://api.mail.tm

# Database
DATABASE_PATH=./data/emails.db

# API
API_PORT=5000
API_HOST=0.0.0.0

# Security
SECRET_KEY=your-super-secret-key-here-change-in-production

# Logging
LOG_LEVEL=INFO
```

### `Dockerfile`
Para containerização:
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "api.app:app", "--host", "0.0.0.0", "--port", "5000"]
```

### `docker-compose.yml`
Orquestração local:
```yaml
version: '3.8'
services:
  api:
    build: .
    ports:
      - "5000:5000"
    environment:
      - LOG_LEVEL=INFO
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
```

## Convensões de Código

### Nomenclatura
- Classes: `PascalCase` (ex: `MailTmClient`)
- Funções/métodos: `snake_case` (ex: `create_email`)
- Constantes: `UPPER_SNAKE_CASE` (ex: `MAX_RETRIES`)
- Variáveis: `snake_case` (ex: `email_count`)

### Imports
```python
# 1. Standard library
import os
import json
from typing import Dict, List

# 2. Third-party
import requests
from fastapi import FastAPI
from sqlalchemy import create_engine

# 3. Local
from core.config import settings
from core.exceptions import MailTmException
```

### Type Hints Obrigatórios
```python
def create_emails(quantity: int, unique: bool = True) -> List[EmailAccount]:
    """Sempre use type hints em assinatura"""
    pass
```

---

**Status:** Pronto para Implementação  
**Última Atualização:** 2025-11-06