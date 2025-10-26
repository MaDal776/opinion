"""Centralised logging utilities for the opinion spread strategy."""

from __future__ import annotations

import json
import logging
from logging import Logger
from typing import Any, Dict, Optional

from ..config.schema import LoggingConfig


_LOGGER_NAME = "opinion_spread"


def _json_formatter(record: logging.LogRecord) -> str:
    payload = {
        "level": record.levelname,
        "name": record.name,
        "message": record.getMessage(),
        "module": record.module,
        "function": record.funcName,
        "line": record.lineno,
    }
    if record.exc_info:
        payload["exc_info"] = logging.Formatter().formatException(record.exc_info)
    if hasattr(record, "extra_data") and isinstance(record.extra_data, dict):
        payload.update(record.extra_data)
    return json.dumps(payload, ensure_ascii=False)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:  # type: ignore[override]
        return _json_formatter(record)


class StructuredFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:  # type: ignore[override]
        base = super().format(record)
        if hasattr(record, "extra_data") and isinstance(record.extra_data, dict):
            return f"{base} | extra={record.extra_data}"
        return base


def configure_logging(config: LoggingConfig) -> Logger:
    logger = logging.getLogger(_LOGGER_NAME)
    if logger.handlers:
        return logger

    logger.setLevel(getattr(logging, config.level.upper(), logging.INFO))

    if config.log_to_console:
        console_handler = logging.StreamHandler()
        formatter: logging.Formatter
        if config.json_format:
            formatter = JsonFormatter()
        else:
            formatter = StructuredFormatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    if config.log_to_file and config.log_file:
        file_handler = logging.FileHandler(config.log_file, encoding="utf-8")
        formatter: logging.Formatter
        if config.json_format:
            formatter = JsonFormatter()
        else:
            formatter = StructuredFormatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def get_logger() -> Logger:
    return logging.getLogger(_LOGGER_NAME)


def log_with_context(logger: Logger, level: int, message: str, **context: Any) -> None:
    logger.log(level, message, extra={"extra_data": context} if context else None)

