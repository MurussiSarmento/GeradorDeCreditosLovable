from typing import Optional, Tuple
import requests
from loguru import logger
import re
import html
import time
import threading
from collections import deque

from core.config import Settings


_rate_lock = threading.Lock()
_send_timestamps = deque()


def escape_markdown_v2(text: Optional[str]) -> str:
    """Escapa caracteres especiais do MarkdownV2 do Telegram.

    Lista de caracteres: _ * [ ] ( ) ~ ` > # + - = | { } . !
    """
    if not text:
        return ""
    pattern = r"([_\*\[\]\(\)~`>#+\-=\|{}\.!])"
    return re.sub(pattern, r"\\\1", text)


def format_telegram_message(
    subject: Optional[str],
    sender: Optional[str],
    preview: Optional[str],
    parse_mode: Optional[str] = None,
    override_preview_max: Optional[int] = None,
) -> Tuple[str, Optional[str]]:
    """Compõe uma mensagem com título, remetente e preview.

    Respeita `parse_mode` (MarkdownV2, HTML ou texto puro). Retorna `(text, parse_mode)`.
    """
    settings = Settings()
    parse_mode = parse_mode or settings.TELEGRAM_PARSE_MODE
    s = subject or "(sem assunto)"
    de = sender or "-"
    # Truncamento configurável do preview
    max_chars = (override_preview_max if override_preview_max is not None else settings.TELEGRAM_PREVIEW_MAX_CHARS) or 0
    raw_preview = preview or ""
    if max_chars and max_chars > 0 and len(raw_preview) > max_chars:
        if max_chars <= 1:
            raw_preview = "…"
        else:
            raw_preview = raw_preview[: max_chars - 1] + "…"
    p = raw_preview
    if (parse_mode or "").lower() == "markdownv2":
        text = f"*{escape_markdown_v2(s)}*\nDe: {escape_markdown_v2(de)}\n{escape_markdown_v2(p)}"
        return text, "MarkdownV2"
    if (parse_mode or "").lower() == "html":
        text = f"<b>{html.escape(s)}</b>\nDe: {html.escape(de)}\n{html.escape(p)}"
        return text, "HTML"
    # Texto puro
    text = f"{s}\nDe: {de}\n{p}"
    return text, None


def _respect_rate_limit(settings: Settings) -> None:
    """Garante um limite de mensagens por segundo usando janela deslizante."""
    limit_per_sec = settings.TELEGRAM_RATE_LIMIT_PER_SEC or 0
    if not limit_per_sec or limit_per_sec <= 0:
        return
    window = 1.0
    with _rate_lock:
        now = time.monotonic()
        while _send_timestamps and now - _send_timestamps[0] > window:
            _send_timestamps.popleft()
        if len(_send_timestamps) >= limit_per_sec:
            sleep_time = window - (now - _send_timestamps[0])
            if sleep_time > 0:
                time.sleep(sleep_time)
        _send_timestamps.append(time.monotonic())


def send_telegram_message(text: str, parse_mode: Optional[str] = None) -> bool:
    """Envia uma mensagem para o chat configurado no Telegram.

    Retorna True em caso de envio bem-sucedido, False caso não configurado ou erro.
    """
    settings = Settings()
    token = settings.TELEGRAM_BOT_TOKEN
    chat_id = settings.TELEGRAM_CHAT_ID
    if not token or not chat_id:
        # Integração não configurada
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
    }
    if parse_mode is None:
        parse_mode = settings.TELEGRAM_PARSE_MODE
    if parse_mode:
        payload["parse_mode"] = parse_mode

    timeout = settings.TELEGRAM_TIMEOUT_SEC or 10
    max_retries = settings.TELEGRAM_MAX_RETRIES or 3
    base_delay_ms = settings.TELEGRAM_RETRY_BASE_DELAY_MS or 250

    for attempt in range(max_retries):
        try:
            _respect_rate_limit(settings)
            resp = requests.post(url, json=payload, timeout=timeout)
            # 429 → backoff
            if getattr(resp, "status_code", 200) == 429 and attempt < max_retries - 1:
                delay = (2 ** attempt) * (base_delay_ms / 1000.0)
                time.sleep(delay)
                continue
            resp.raise_for_status()
            ok = resp.json().get("ok", False)
            if not ok:
                logger.warning("Envio Telegram retornou ok=False", extra={"response": resp.text})
            return bool(ok)
        except Exception as e:
            if attempt < max_retries - 1:
                delay = (2 ** attempt) * (base_delay_ms / 1000.0)
                time.sleep(delay)
                continue
            logger.error("Falha ao enviar mensagem para Telegram", extra={"error": str(e)})
            return False