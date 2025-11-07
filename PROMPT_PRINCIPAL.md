# PROJETO: Sistema Completo de Gerenciamento de Emails Temporários Mail.tm

## Visão Geral do Projeto

Você está sendo solicitado a criar uma **aplicação Python enterprise-grade** que oferece:

1. **Interface Gráfica Moderna (Desktop UI)** - Permitir que usuários criem múltiplos emails temporários via Mail.tm API com controle total
2. **API REST Escalável** - Disponibilizar funcionalidades via HTTP para integração com outros programas e sistemas
3. **Sistema de Extração Inteligente de Códigos** - Automaticamente extrair códigos de verificação, tokens e links de emails recebidos
4. **Banco de Dados Persistente** - Gerenciar todas as contas, emails, mensagens e códigos extraídos
5. **Autenticação e Segurança** - Proteger a API com tokens, rate limiting e validações

## Objetivos Principais

### Objetivo 1: Interface Gráfica Profissional
Criar uma UI intuitiva onde o usuário pode:
- Especificar quantidade de emails a criar
- Gerar emails completamente aleatórios com domínios Mail.tm aleatórios
- Visualizar todos os emails em tabela interativa
- Verificar mensagens recebidas em tempo real
- Ver códigos extraídos automaticamente com contexto
- Gerenciar configurações da aplicação
- Monitorar status da API local

### Objetivo 2: API REST Compartilhável
Criar endpoints HTTP que permitem:
- Programas externos gerarem emails sob demanda
- Verificar emails recebidos e extrair códigos automaticamente
- Consultar histórico de mensagens
- Registrar webhooks para eventos
- Todos os dados persistidos e recuperáveis

### Objetivo 3: Automação de Extração de Códigos
Sistema capaz de:
- Reconhecer múltiplos formatos de código (OTP 4/5/6/8 dígitos)
- Extrair URLs com tokens de verificação
- Extrair emails mencionados nas mensagens
- Encontrar padrões customizados via regex
- Retornar com contexto e confiança

### Objetivo 4: Robustez e Escalabilidade
- Suportar criação de milhares de emails sem travamentos
- Tratamento automático de erros e retries
- Rate limiting respeitado (8 req/seg da API Mail.tm)
- Logging detalhado de todas operações
- Performance otimizada com caching e índices

## Documentos de Referência Obrigatória

Este projeto é documentado em múltiplos arquivos especializados. **Consulte-os durante a implementação**:

### 📋 Documentação Técnica
- **[TECHNICAL_STACK.md](TECHNICAL_STACK.md)** - Tecnologias, versões e dependências exatas
- **[PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md)** - Estrutura de pastas e organização do código
- **[DATA_FLOWS.md](DATA_FLOWS.md)** - Fluxos de dados entre componentes

### 🔌 Integração e APIs
- **[MAIL_TM_INTEGRATION.md](MAIL_TM_INTEGRATION.md)** - Como integrar com Mail.tm API
- **[API_ENDPOINTS.md](API_ENDPOINTS.md)** - Especificação completa de todos endpoints REST
- **[API_SPECIFICATIONS.md](API_SPECIFICATIONS.md)** - Detalhes de request/response, autenticação, rate limiting

### 💻 Interface e Código
- **[UI_REQUIREMENTS.md](UI_REQUIREMENTS.md)** - Layout, componentes, interações e UX
- **[CODE_EXTRACTION.md](CODE_EXTRACTION.md)** - Padrões regex, algoritmos e validação
- **[ERROR_HANDLING.md](ERROR_HANDLING.md)** - Estratégias de erro, retries, logging

## Requisitos Não-Funcionais Globais

### Performance
- Criar 1000 emails sem travamento da UI
- Resposta de API < 500ms (p95)
- Usar threading para operações de rede
- Cache de domínios com TTL de 1 hora
- Suportar paginação em listas > 100 itens

### Segurança
- Criptografar senhas de email com Fernet
- Validação de entrada em 100% das APIs
- CORS configurado corretamente
- Rate limiting: 100 req/min por IP, 1000 req/min por API key
- Nenhuma senha/token logada em arquivo

### Confiabilidade
- Retry automático com exponential backoff (3 tentativas)
- Timeout configurável (default 30s)
- Tratamento de todas exceções possíveis
- Backup automático de banco de dados (hora em hora)
- Cleanup automático de dados antigos (>30 dias)

### Manutenibilidade
- Código com type hints (Python 3.9+)
- Docstrings em todos métodos públicos
- Testes unitários com cobertura >80%
- Logging estruturado com loguru
- README completo e documentação API

## Casos de Uso Principais

### Caso 1: Tester de Software
Uma equipe de QA precisa criar 50 emails para testar fluxo de registro.
```
1. Abre aplicação, vai em "Generator"
2. Coloca 50 em "Quantidade de Emails"
3. Marca "Usar domínios únicos"
4. Clica "GERAR EMAILS"
5. Aguarda 30 segundos
6. Copia todos os emails para clipboard
7. Usa em seu software de teste
8. Quando receber emails, verifica os códigos automaticamente na aba "Inbox"
```

### Caso 2: Integração via API
Um script Python externo precisa:
```python
import requests

headers = {"Authorization": "Bearer YOUR_API_TOKEN"}

# 1. Criar 5 emails
response = requests.post(
    "http://localhost:5000/api/v1/emails/generate",
    json={"quantity": 5, "unique_domains": True},
    headers=headers
)
emails = response.json()["emails"]

# 2. Usar os emails para algo
# ... seu código aqui ...

# 3. Depois buscar os códigos
for email in emails:
    response = requests.get(
        f"http://localhost:5000/api/v1/emails/{email['email']}/codes",
        headers=headers
    )
    codes = response.json()["codes"]
    if codes:
        verification_code = codes[0]["code"]
        # ... usar o código ...
```

### Caso 3: Monitoramento em Tempo Real
```
1. Usuário abre UI e vai em "Inbox"
2. Seleciona um dos emails criados
3. Marca "Auto-verificar a cada 30 segundos"
4. Sistema verifica automaticamente e mostra códigos quando chegarem
5. Usuário vê notificação quando novo código é extraído
```

## Fluxo de Desenvolvimento Recomendado

### Fase 1: Fundação (semana 1)
- [ ] Setup projeto: pasta, venv, requirements.txt
- [ ] Implementar MailTmClient com batch_create_accounts()
- [ ] Implementar Database com SQLite
- [ ] Testes unitários dos acima

### Fase 2: Extração e Core (semana 2)
- [ ] Implementar CodeExtractor com todos padrões regex
- [ ] Testar com emails reais
- [ ] Implementar Flask app básico
- [ ] Implementar 3 endpoints principais GET/POST

### Fase 3: API Completa (semana 3)
- [ ] Todos 10 endpoints REST
- [ ] Autenticação API key + JWT
- [ ] Rate limiting
- [ ] Documentação Swagger
- [ ] Testes de integração

### Fase 4: Interface Gráfica (semana 4)
- [ ] Setup PyQt6
- [ ] Aba de Generator com tabela
- [ ] Aba de Inbox com visualizador
- [ ] Aba de Configurações
- [ ] Threading para operações de rede

### Fase 5: Polish e Deploy (semana 5)
- [ ] Dark mode / Light mode
- [ ] Tratamento completo de erros
- [ ] Logging em todos os módulos
- [ ] Build executável Windows/Linux/Mac
- [ ] Documentação final

## Estrutura de Dados Principal

### Email Account
```json
{
  "id": "uuid",
  "email": "abc123@domain.com",
  "account_id": "mail_tm_id",
  "password": "encrypted_password",
  "token": "jwt_token",
  "domain": "domain.com",
  "created_at": "2025-11-06T19:45:00Z",
  "last_checked_at": "2025-11-06T20:00:00Z",
  "status": "active",
  "message_count": 5
}
```

### Message
```json
{
  "id": "uuid",
  "email_id": "uuid",
  "message_id_remote": "mail_tm_message_id",
  "from": "sender@example.com",
  "subject": "Verify your email",
  "text_preview": "Your code is...",
  "full_text": "Complete message body",
  "html_content": "<html>...</html>",
  "extracted_codes": [
    {
      "code": "123456",
      "type": "otp_6digit",
      "confidence": 95,
      "context": "Your verification code is: 123456"
    }
  ],
  "is_read": false,
  "received_at": "2025-11-06T19:50:00Z",
  "processed_at": "2025-11-06T19:51:00Z"
}
```

## Métricas de Sucesso

- ✅ Criar 1000 emails em < 2 minutos sem erros
- ✅ Extrair códigos com 95%+ de acurácia
- ✅ API responde em < 200ms (p95)
- ✅ Zero crashes durante operações normais
- ✅ UI responsiva mesmo criando 100 emails simultâneos
- ✅ Suportar 100+ requisições simultâneas na API
- ✅ Código com cobertura de testes > 80%
- ✅ Documentação completa e atualizada

## Como Usar Este Prompt

1. **Leia primeiro este arquivo inteiro** para entender visão geral
2. **Consulte os documentos especializados** conforme necessário:
   - Implementando UI? → Veja UI_REQUIREMENTS.md
   - Criando API? → Veja API_ENDPOINTS.md e API_SPECIFICATIONS.md
   - Integrando Mail.tm? → Veja MAIL_TM_INTEGRATION.md
   - etc.
3. **Use como especificação técnica** durante desenvolvimento
4. **Consulte ERROR_HANDLING.md** quando encontrar problemas
5. **Refira-se a DATA_FLOWS.md** para entender interações entre módulos

## Padrões de Código Obrigatórios

### Type Hints Sempre
```python
def create_accounts(quantity: int, unique_domains: bool = True) -> List[Dict[str, Any]]:
    pass
```

### Docstrings Detalhadas
```python
def extract_code(self, email_body: str, pattern_name: str = 'otp_6digit') -> Optional[str]:
    """
    Extrair código de verificação do corpo do email.
    
    Args:
        email_body: Texto completo do email
        pattern_name: Nome do padrão regex a usar
        
    Returns:
        Código extraído ou None se não encontrado
        
    Raises:
        InvalidPatternException: Se padrão inválido
        
    Example:
        >>> extractor = CodeExtractor()
        >>> extractor.extract_code("Your code is 123456")
        '123456'
    """
    pass
```

### Logging Estruturado
```python
from loguru import logger

logger.info("Email criado", extra={"email": email, "domain": domain})
logger.error("Falha ao conectar Mail.tm", extra={"retry": 2, "duration_ms": 5000})
```

### Error Handling Apropriado
```python
try:
    response = self.client.post(url, json=data, timeout=30)
    response.raise_for_status()
except requests.Timeout:
    logger.warning("Timeout na requisição", extra={"url": url})
    # retry com backoff
except requests.HTTPError as e:
    logger.error("HTTP error", extra={"status": e.response.status_code})
    # handle específico
except Exception as e:
    logger.critical("Erro inesperado", extra={"error": str(e)})
    raise
```

## Dependências Externas

**Todas as dependências devem estar listadas em requirements.txt com versões fixadas:**

```
Flask==2.3.2
FastAPI==0.104.1
PyQt6==6.6.1
requests==2.31.0
Pydantic==2.5.0
SQLAlchemy==2.0.23
cryptography==41.0.7
loguru==0.7.2
pytest==7.4.3
python-dotenv==1.0.0
```

## Próximos Passos

1. Leia **TECHNICAL_STACK.md** para entender tecnologias
2. Leia **PROJECT_STRUCTURE.md** para setup inicial
3. Leia **MAIL_TM_INTEGRATION.md** antes de implementar MailTmClient
4. Leia **API_ENDPOINTS.md** para design dos endpoints
5. Leia **UI_REQUIREMENTS.md** antes de criar interface
6. Use **DATA_FLOWS.md** como referência durante integração
7. Consulte **ERROR_HANDLING.md** regularmente
8. Valide extração com **CODE_EXTRACTION.md**

---

**Versão do Prompt:** 2.0  
**Última Atualização:** 2025-11-06  
**Status:** Pronto para Implementação