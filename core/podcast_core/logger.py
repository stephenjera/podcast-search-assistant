import json
import logging
import sys
from pathlib import Path
from typing import Any

from podcast_core.config import settings


class JSONFormatter(logging.Formatter):
    """Emit logs as single-line JSON for easier machine parsing."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": self.formatTime(record, "%Y-%m-%d %H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "file": record.filename,
            "line": record.lineno,
            "function": record.funcName,
            "message": record.getMessage(),
        }
        return json.dumps(payload)


def get_logger(name: str | None = None, json_logs: bool = True) -> logging.Logger:
    logger_name = name or Path(__file__).name
    logger = logging.getLogger(logger_name)
    if logger.handlers:
        return logger

    level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    logger.setLevel(level)

    handler = logging.StreamHandler(sys.stdout)
    if json_logs:
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    logger.addHandler(handler)
    logger.propagate = False
    return logger
