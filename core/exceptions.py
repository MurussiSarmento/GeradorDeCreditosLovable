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