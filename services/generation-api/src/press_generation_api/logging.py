import json
import logging
from collections.abc import Mapping
from typing import Any

LOGGER_NAME = "press-generation-api"


def configure_logging() -> logging.Logger:
    logger = logging.getLogger(LOGGER_NAME)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    return logger


def log_event(logger: logging.Logger, event: Mapping[str, Any]) -> None:
    logger.info(json.dumps(dict(event), separators=(",", ":"), default=str))
