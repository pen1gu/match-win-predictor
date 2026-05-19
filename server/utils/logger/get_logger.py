import logging
from typing import Literal

LogFormat = Literal["text", "json"]


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
