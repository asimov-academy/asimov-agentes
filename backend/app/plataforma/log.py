import logging

import structlog


def configura_log(nivel: str = "INFO") -> None:
    """JSON em uma linha por evento. Conteúdo de mensagem e credenciais nunca entram aqui."""
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.getLevelName(nivel.upper())),
    )
