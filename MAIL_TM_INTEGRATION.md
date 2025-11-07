# MAIL_TM_INTEGRATION - Integração Completa com Mail.tm API

## Visão Geral de Mail.tm

**Mail.tm** é um serviço de email temporário/descartável que fornece:
- ✅ Emails temporários com vida útil configurável
- ✅ API REST aberta e bem documentada
- ✅ Sem registro necessário
- ✅ Rate limit: 8 requisições por segundo
- ✅ Múltiplos domínios disponíveis
- ✅ 100% gratuito

**Base URL:** `https://api.mail.tm`

## Autenticação Mail.tm

Mail.tm usa **dois níveis de autenticação**:

### 1. Criar Conta (sem autenticação)
```
POST /accounts
Content-Type: application/json

Request:
{
  "address": "user123@domain.com",
  "password": "SecurePassword123!"
}

Response:
{
  "id": "account-uuid-123",
  "address": "user123@domain.com",
  "domain": {
    "id": "domain-uuid",
    "domain": "domain.com",
    "maxRecipientsPerDay": 50
  },
  "createdAt": "2025-11-06T19:45:00Z"
}
```

### 2. Autenticar com Conta (obter token)
```
POST /token
Content-Type: application/json

Request:
{
  "address": "user123@domain.com",
  "password": "SecurePassword123!"
}

Response:
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "id": "account-uuid-123"
}
```

Token de vida útil: **indefinido** (não expira)

## Domínios Disponíveis

Obter lista de domínios antes de criar conta:

```
GET /domains
Content-Type: application/json

Response:
{
  "hydra:member": [
    {
      "id": "domain-uuid-1",
      "domain": "mail.tm",
      "isActive": true,
      "isPrivate": false
    },
    {
      "id": "domain-uuid-2",
      "domain": "domain2.com",
      "isActive": true,
      "isPrivate": false
    }
  ],
  "hydra:totalItems": 2
}
```

**Importantes:**
- Alguns domínios podem estar privados (`isPrivate: true`)
- Sempre verificar `isActive` antes de usar
- Usar domínios públicos apenas

## Implementação do MailTmClient

### Classe Principal

```python
import asyncio
import random
import string
import requests
from typing import List, Dict, Any, Optional
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import time

class MailTmClient:
    """Cliente para API Mail.tm com suporte a criação em batch"""
    
    def __init__(self, base_url: str = "https://api.mail.tm", rate_limit: int = 8):
        """
        Inicializar cliente Mail.tm
        
        Args:
            base_url: URL base da API
            rate_limit: Máximo de requisições por segundo (padrão 8)
        """
        self.base_url = base_url
        self.rate_limit = rate_limit
        self.min_delay = 1.0 / rate_limit  # Delay mínimo entre requisições
        self.session = requests.Session()
        self._domain_cache = None
        self._domain_cache_time = None
        self._cache_ttl = 3600  # 1 hora
    
    # ============ GERENCIAMENTO DE DOMÍNIOS ============
    
    def get_all_domains(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """
        Obter todos domínios disponíveis.
        
        Usa cache com TTL de 1 hora para reduzir requisições.
        
        Args:
            force_refresh: Forçar atualizar cache
            
        Returns:
            Lista de dicionários com domínios
            
        Raises:
            MailTmException: Se erro ao obter domínios
        """
        # Verificar cache
        if (self._domain_cache is not None and 
            not force_refresh and 
            time.time() - self._domain_cache_time < self._cache_ttl):
            return self._domain_cache
        
        try:
            response = self.session.get(f"{self.base_url}/domains")
            response.raise_for_status()
            domains = response.json()['hydra:member']
            
            # Filtrar apenas domínios ativos e públicos
            domains = [d for d in domains if d.get('isActive') and not d.get('isPrivate')]
            
            # Cache
            self._domain_cache = domains
            self._domain_cache_time = time.time()
            
            return domains
        except Exception as e:
            raise MailTmException(f"Erro ao obter domínios: {str(e)}")
    
    def get_random_domain(self) -> str:
        """Obter domínio aleatório da lista disponível"""
        domains = self.get_all_domains()
        if not domains:
            raise MailTmException("Nenhum domínio disponível")
        return random.choice(domains)['domain']
    
    # ============ CRIAÇÃO DE CONTAS ============
    
    def _generate_random_email(self, domain: Optional[str] = None) -> tuple[str, str]:
        """
        Gerar email aleatório único.
        
        Returns:
            Tupla (email, username)
        """
        # Gerar username aleatório 12-16 caracteres
        username_length = random.randint(12, 16)
        username = ''.join(
            random.choices(string.ascii_lowercase + string.digits, k=username_length)
        )
        
        if domain is None:
            domain = self.get_random_domain()
        
        email = f"{username}@{domain}"
        return email, username
    
    def _generate_random_password(self, length: int = 16) -> str:
        """
        Gerar senha aleatória forte.
        
        Requisitos Mail.tm:
        - Mínimo 8 caracteres
        - Letras (maiúsculas e minúsculas)
        - Números
        - Símbolos especiais
        """
        password_chars = (
            string.ascii_lowercase +
            string.ascii_uppercase +
            string.digits +
            "!@#$%^&*()_+-=[]{}|;:,.<>?"
        )
        
        password = ''.join(random.choices(password_chars, k=length))
        return password
    
    def create_account(
        self,
        email: Optional[str] = None,
        domain: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Criar uma única conta de email.
        
        Args:
            email: Email específico (se None, gerar aleatório)
            domain: Domínio específico (se None, escolher aleatório)
            
        Returns:
            Dicionário com dados da conta criada:
            {
                'email': str,
                'account_id': str,
                'password': str,
                'token': str,
                'domain': str,
                'created_at': datetime
            }
            
        Raises:
            MailTmException: Se email já existe ou outro erro
        """
        try:
            # Respeitar rate limit
            time.sleep(self.min_delay)
            
            if email is None:
                email, _ = self._generate_random_email(domain)
            
            password = self._generate_random_password()
            
            # 1. Criar conta
            response = self.session.post(
                f"{self.base_url}/accounts",
                json={
                    "address": email,
                    "password": password
                },
                timeout=30
            )
            response.raise_for_status()
            account_data = response.json()
            account_id = account_data['id']
            
            # 2. Obter token
            time.sleep(self.min_delay)
            response = self.session.post(
                f"{self.base_url}/token",
                json={
                    "address": email,
                    "password": password
                },
                timeout=30
            )
            response.raise_for_status()
            token_data = response.json()
            token = token_data['token']
            
            return {
                'email': email,
                'account_id': account_id,
                'password': password,
                'token': token,
                'domain': email.split('@')[1],
                'created_at': datetime.utcnow()
            }
            
        except requests.HTTPError as e:
            if e.response.status_code == 422:
                raise MailTmException(f"Email já existe: {email}")
            raise MailTmException(f"Erro ao criar conta: {e}")
        except Exception as e:
            raise MailTmException(f"Erro inesperado: {str(e)}")
    
    # ============ CRIAÇÃO EM BATCH ============
    
    def batch_create_accounts(
        self,
        quantity: int,
        unique_domains: bool = True,
        max_workers: int = 8
    ) -> List[Dict[str, Any]]:
        """
        Criar múltiplas contas em paralelo.
        
        Args:
            quantity: Número de contas a criar (1-10000)
            unique_domains: Se True, cada conta usa domínio diferente
            max_workers: Máximo de threads paralelas (respeita rate limit)
            
        Returns:
            Lista de contas criadas
            
        Raises:
            MailTmException: Se erro durante criação
        """
        if quantity < 1 or quantity > 10000:
            raise ValueError("Quantidade deve estar entre 1 e 10000")
        
        accounts = []
        domains = self.get_all_domains()
        
        if unique_domains and quantity > len(domains):
            raise MailTmException(
                f"Somente {len(domains)} domínios disponíveis, "
                f"mas {quantity} solicitados com unique_domains=True"
            )
        
        created_count = 0
        errors = []
        
        # Criar com thread pool, respeitando rate limit
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = []
            
            for i in range(quantity):
                # Escolher domínio
                domain = None
                if unique_domains:
                    domain = domains[i % len(domains)]['domain']
                
                # Submeter task
                future = executor.submit(self.create_account, domain=domain)
                futures.append((future, i + 1))
            
            # Coletar resultados
            for future, index in futures:
                try:
                    account = future.result(timeout=60)
                    accounts.append(account)
                    created_count += 1
                except Exception as e:
                    errors.append({
                        'index': index,
                        'error': str(e)
                    })
        
        if errors:
            print(f"⚠️  {len(errors)} erros durante criação em batch")
            for err in errors:
                print(f"   - Item {err['index']}: {err['error']}")
        
        return accounts
    
    # ============ LEITURA DE MENSAGENS ============
    
    def get_messages(
        self,
        token: str,
        page: int = 1,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Obter mensagens recebidas em uma conta.
        
        Args:
            token: JWT token da conta
            page: Número da página (paginação)
            limit: Itens por página
            
        Returns:
            Lista de mensagens
            
        Raises:
            MailTmException: Se erro ao obter mensagens
        """
        try:
            time.sleep(self.min_delay)
            
            headers = {"Authorization": f"Bearer {token}"}
            response = self.session.get(
                f"{self.base_url}/messages",
                headers=headers,
                params={"page": page, "limit": limit},
                timeout=30
            )
            response.raise_for_status()
            
            return response.json()['hydra:member']
            
        except Exception as e:
            raise MailTmException(f"Erro ao obter mensagens: {str(e)}")
    
    def get_message_detail(
        self,
        token: str,
        message_id: str
    ) -> Dict[str, Any]:
        """
        Obter detalhes completos de uma mensagem.
        
        Args:
            token: JWT token da conta
            message_id: ID da mensagem (retorna de get_messages())
            
        Returns:
            Dicionário com corpo completo da mensagem
        """
        try:
            time.sleep(self.min_delay)
            
            headers = {"Authorization": f"Bearer {token}"}
            response = self.session.get(
                f"{self.base_url}/messages/{message_id}",
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            raise MailTmException(f"Erro ao obter detalhes: {str(e)}")
    
    def mark_as_read(
        self,
        token: str,
        message_id: str
    ) -> bool:
        """
        Marcar mensagem como lida.
        
        Args:
            token: JWT token da conta
            message_id: ID da mensagem
            
        Returns:
            True se sucesso
        """
        try:
            time.sleep(self.min_delay)
            
            headers = {"Authorization": f"Bearer {token}"}
            response = self.session.patch(
                f"{self.base_url}/messages/{message_id}",
                headers=headers,
                json={"isRead": True},
                timeout=30
            )
            response.raise_for_status()
            return True
            
        except Exception as e:
            raise MailTmException(f"Erro ao marcar como lido: {str(e)}")
    
    # ============ LIMPEZA ============
    
    def delete_account(
        self,
        token: str,
        account_id: str
    ) -> bool:
        """
        Deletar uma conta.
        
        Args:
            token: JWT token da conta
            account_id: ID da conta
            
        Returns:
            True se sucesso
        """
        try:
            time.sleep(self.min_delay)
            
            headers = {"Authorization": f"Bearer {token}"}
            response = self.session.delete(
                f"{self.base_url}/accounts/{account_id}",
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            return True
            
        except Exception as e:
            raise MailTmException(f"Erro ao deletar conta: {str(e)}")

class MailTmException(Exception):
    """Exceção base para erros Mail.tm"""
    pass
```

## Tratamento de Rate Limit

Mail.tm permite **8 requisições por segundo**. Implementação:

```python
import time
from datetime import datetime, timedelta

class RateLimiter:
    """Controlar taxa de requisições"""
    
    def __init__(self, rate: int = 8):
        """
        Args:
            rate: Requisições por segundo
        """
        self.rate = rate
        self.min_interval = 1.0 / rate
        self.last_request = None
    
    def wait_if_needed(self):
        """Aguardar se necessário para respeitar rate limit"""
        if self.last_request is None:
            self.last_request = datetime.now()
            return
        
        elapsed = (datetime.now() - self.last_request).total_seconds()
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        
        self.last_request = datetime.now()
```

## Retry Logic com Exponential Backoff

```python
from functools import wraps
import random

def retry_with_backoff(max_attempts: int = 3, base_delay: float = 1.0):
    """
    Decorador para retry automático com exponential backoff.
    
    Args:
        max_attempts: Número máximo de tentativas
        base_delay: Delay base em segundos
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except MailTmException as e:
                    if attempt == max_attempts - 1:
                        raise
                    
                    # Exponential backoff com jitter
                    delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                    print(f"Tentativa {attempt + 1} falhou, aguardando {delay:.1f}s...")
                    time.sleep(delay)
            
        return wrapper
    return decorator

# Uso:
@retry_with_backoff(max_attempts=3)
def create_account_with_retry():
    client = MailTmClient()
    return client.create_account()
```

## Fluxo Completo de Uso

```python
# 1. Criar cliente
client = MailTmClient()

# 2. Obter domínios disponíveis
domains = client.get_all_domains()
print(f"Domínios disponíveis: {len(domains)}")

# 3. Criar 10 emails em paralelo
accounts = client.batch_create_accounts(quantity=10, unique_domains=True)
print(f"✅ {len(accounts)} emails criados")

# 4. Para cada email, verificar mensagens
for account in accounts:
    email = account['email']
    token = account['token']
    
    # Aguardar chegada de emails
    time.sleep(30)
    
    # Obter mensagens
    messages = client.get_messages(token)
    
    for msg in messages:
        # Obter corpo completo
        detail = client.get_message_detail(token, msg['id'])
        
        # Processar (ex: extrair código)
        body = detail.get('text', '')
        print(f"Email: {email}")
        print(f"De: {detail['from']}")
        print(f"Assunto: {detail['subject']}")
        print(f"Corpo: {body[:100]}...")
    
    # Deletar account quando terminar
    client.delete_account(token, account['account_id'])
```

---

## Limites e Considerações

| Aspecto | Limite |
|--------|--------|
| Taxa máxima | 8 req/seg |
| Timeout recomendado | 30 segundos |
| Vida útil do email | Até 24 horas |
| Domínios disponíveis | ~10 |
| Mensagens por email | Ilimitado |
| Tamanho máximo email | Depende do remetente |

---

**Versão:** 1.0  
**Última Atualização:** 2025-11-06