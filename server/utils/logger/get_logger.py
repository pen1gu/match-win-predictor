from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Literal

from server.config.settings import settings

LogFormat = Literal["text", "json"]

_NOISY_LOGGERS = (
    "root",  # soccerdata가 사용하는 logger 이름
    "TLSLibrary",
    "TLSRequests",
    "httpx",
    "httpcore",
    "urllib3",
    "asyncio",
    "sqlalchemy.engine",
    "selenium",
    "seleniumbase",
)

_configured = False


class SafeStreamHandler(logging.StreamHandler):
    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            stream = self.stream
            encoding = getattr(stream, "encoding", None) or "utf-8"
            stream.write(msg.encode(encoding, errors="replace").decode(encoding) + self.terminator)
            self.flush()
        except RecursionError:
            raise
        except Exception:
            self.handleError(record)


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def prepare_third_party_logging() -> None:
    os.environ.setdefault("SOCCERDATA_LOGLEVEL", "ERROR")


def suppress_noisy_loggers() -> None:
    for name in _NOISY_LOGGERS:
        noisy = logging.getLogger(name)
        noisy.handlers.clear()
        noisy.addHandler(logging.NullHandler())
        noisy.propagate = False
        noisy.setLevel(logging.CRITICAL + 1)

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(logging.NullHandler())
    root.setLevel(logging.WARNING)


def configure_logging(
    *,
    level: str | None = None,
    log_format: LogFormat | None = None,
) -> None:
    global _configured

    log_level = getattr(logging, (level or settings.log_level).upper(), logging.INFO)
    fmt: LogFormat = log_format or settings.log_format  # type: ignore[assignment]

    prepare_third_party_logging()
    suppress_noisy_loggers()

    server_logger = logging.getLogger("server")
    if not server_logger.handlers:
        handler = SafeStreamHandler(sys.stdout)
        if fmt == "json":
            handler.setFormatter(_JsonFormatter())
        else:
            handler.setFormatter(
                logging.Formatter(
                    fmt="%(asctime)s %(levelname)s %(name)s - %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S",
                )
            )
        server_logger.addHandler(handler)

    server_logger.setLevel(log_level)
    server_logger.propagate = False
    _configured = True


def get_logger(name: str) -> logging.Logger:
    if not _configured:
        configure_logging()
    return logging.getLogger(name)
