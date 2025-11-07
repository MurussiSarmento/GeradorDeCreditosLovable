import random
import string
import time
from typing import Any, Dict, List, Optional

import requests
from loguru import logger

from core.config import Settings
from core.exceptions import MailTmException


class MailTmClient:
    """Cliente para API Mail.tm com suporte a cache de domínios e rate limit."""

    def __init__(self, base_url: Optional[str] = None, rate_limit: Optional[int] = None):
        settings = Settings()
        self.base_url = base_url or settings.MAIL_TM_API_URL
        self.rate_limit = rate_limit or settings.MAIL_TM_RATE_LIMIT
        self.min_delay = 1.0 / max(self.rate_limit, 1)
        self.session = requests.Session()
        self._domain_cache: Optional[List[Dict[str, Any]]] = None
        self._domain_cache_time: Optional[float] = None
        self._cache_ttl: int = 3600  # 1 hora

    # ============ DOMÍNIOS ============
    def get_all_domains(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        if (
            self._domain_cache is not None
            and not force_refresh
            and self._domain_cache_time is not None
            and time.time() - self._domain_cache_time < self._cache_ttl
        ):
            logger.debug("Usando cache de domínios Mail.tm")
            return self._domain_cache

        try:
            resp = self.session.get(f"{self.base_url}/domains")
            resp.raise_for_status()
            domains = resp.json().get("hydra:member", [])
            domains = [d for d in domains if d.get("isActive") and not d.get("isPrivate")]
            self._domain_cache = domains
            self._domain_cache_time = time.time()
            logger.info("Domínios obtidos", extra={"count": len(domains)})
            return domains
        except Exception as e:
            logger.error("Falha ao obter domínios", extra={"error": str(e)})
            raise MailTmException(f"Erro ao obter domínios: {e}")

    def get_random_domain(self) -> str:
        domains = self.get_all_domains()
        if not domains:
            raise MailTmException("Nenhum domínio disponível")
        return random.choice(domains)["domain"]

    # ============ AUXILIARES DE CRIAÇÃO ============
    def _generate_random_email(self, domain: Optional[str] = None) -> tuple[str, str]:
        username_length = random.randint(12, 16)
        username = "".join(
            random.choices(string.ascii_lowercase + string.digits, k=username_length)
        )
        domain = domain or self.get_random_domain()
        return f"{username}@{domain}", username

    def _generate_random_password(self, length: int = 16) -> str:
        password_chars = (
            string.ascii_lowercase
            + string.ascii_uppercase
            + string.digits
            + "!@#$%^&*()_+-=[]{}|;:,.<>?"
        )
        return "".join(random.choices(password_chars, k=length))

    # ============ CONTAS ============
    def create_account(self, email: Optional[str] = None, domain: Optional[str] = None) -> Dict[str, Any]:
        try:
            time.sleep(self.min_delay)  # respeitar rate limit
            if email is None:
                email, _ = self._generate_random_email(domain)
            password = self._generate_random_password()

            # Criar conta
            resp_acc = self.session.post(
                f"{self.base_url}/accounts", json={"address": email, "password": password}
            )
            resp_acc.raise_for_status()
            account_id = resp_acc.json().get("id")

            # Obter token
            resp_tok = self.session.post(
                f"{self.base_url}/token", json={"address": email, "password": password}
            )
            resp_tok.raise_for_status()
            token = resp_tok.json().get("token")

            logger.info("Conta Mail.tm criada", extra={"email": email, "account_id": account_id})
            return {
                "email": email,
                "account_id": account_id,
                "password": password,
                "token": token,
                "domain": email.split("@")[-1],
                "created_at": time.time(),
            }
        except Exception as e:
            logger.error("Erro ao criar conta Mail.tm", extra={"email": email, "error": str(e)})
            raise MailTmException(f"Erro ao criar conta: {e}")