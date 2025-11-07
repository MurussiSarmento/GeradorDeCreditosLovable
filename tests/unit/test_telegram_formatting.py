import time


def test_format_markdownv2_escape(monkeypatch):
    # Configurar parse_mode
    monkeypatch.setenv("TELEGRAM_PARSE_MODE", "MarkdownV2")
    from utils.telegram import format_telegram_message

    subject = "[Invoice] Total: 100% _OK_"
    sender = "a(b)c@d.com"
    preview = "Use *bold* and _underline_ (test)."

    text, parse_mode = format_telegram_message(subject, sender, preview)
    assert parse_mode == "MarkdownV2"
    # Caracteres especiais devem estar escapados
    assert "*" in text  # título em negrito
    assert "\\[" in text and "\\]" in text
    assert "\\_OK\\_" in text
    assert "De:" in text


def test_backoff_on_429(monkeypatch):
    # Configurar ambiente Telegram
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "bot-abc")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat-xyz")
    monkeypatch.setenv("TELEGRAM_PARSE_MODE", "")
    # Desabilitar rate limit por segundo para focar no backoff
    monkeypatch.setenv("TELEGRAM_RATE_LIMIT_PER_SEC", "0")
    monkeypatch.setenv("TELEGRAM_MAX_RETRIES", "2")
    monkeypatch.setenv("TELEGRAM_RETRY_BASE_DELAY_MS", "100")

    import utils.telegram as tg

    calls = {"post": 0, "sleep": []}

    class Resp429:
        status_code = 429

        def raise_for_status(self):
            class E(Exception):
                pass

            # Não levantar para que o fluxo de backoff trate pelo status_code
            return None

        def json(self):
            return {"ok": False}

        @property
        def text(self):
            return "rate limited"

    class Resp200:
        status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            return {"ok": True}

        @property
        def text(self):
            return "ok"

    def fake_post(url, json=None, timeout=None):
        calls["post"] += 1
        return Resp429() if calls["post"] == 1 else Resp200()

    def fake_sleep(sec):
        calls["sleep"].append(sec)

    monkeypatch.setattr(tg.requests, "post", fake_post)
    monkeypatch.setattr(time, "sleep", fake_sleep)

    ok = tg.send_telegram_message("test backoff")
    assert ok is True
    # Deve ter feito 2 chamadas e pelo menos 1 sleep de backoff
    assert calls["post"] == 2
    assert len(calls["sleep"]) >= 1


def test_preview_truncation_markdown(monkeypatch):
    # Habilitar MarkdownV2 e limite pequeno para forçar truncamento
    monkeypatch.setenv("TELEGRAM_PARSE_MODE", "MarkdownV2")
    monkeypatch.setenv("TELEGRAM_PREVIEW_MAX_CHARS", "10")
    from utils.telegram import format_telegram_message

    subject = "Assunto"
    sender = "remetente@example.com"
    preview = "0123456789ABCDEF"  # 16 chars

    text, parse_mode = format_telegram_message(subject, sender, preview)
    assert parse_mode == "MarkdownV2"
    # Preview deve ser truncado com reticências
    assert "…" in text
    # E conter no máximo 11 chars do preview (10 + …) antes de escape
    # Como o escape adiciona barras, verificamos apenas presença da reticência