"""Structured logging for the UEM agent."""
import logging
import sys
from pathlib import Path

import structlog

from src.config import LOG_DIR, AGENT_VERSION


def setup_logging(level: str = "INFO", log_to_file: bool = True) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    log_level = getattr(logging, level.upper(), logging.INFO)

    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]

    if log_to_file:
        from logging.handlers import RotatingFileHandler
        file_handler = RotatingFileHandler(
            LOG_DIR / "uem-agent.log",
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=5,
        )
        handlers.append(file_handler)

    logging.basicConfig(
        format="%(message)s",
        level=log_level,
        handlers=handlers,
    )

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    structlog.contextvars.bind_contextvars(agent_version=AGENT_VERSION)


def get_logger(name: str):
    return structlog.get_logger(name)
