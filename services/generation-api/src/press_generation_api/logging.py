import json
import logging
from collections.abc import Mapping
from typing import Any

LOGGER_NAME = "press-generation-api"
_REDACTED_KEYS = frozenset(
    {
        "api_key",
        "authorization",
        "b2_application_key",
        "b2_key_id",
        "personal_note",
        "selected_fragment",
        "presigned_url",
    }
)


def configure_logging() -> logging.Logger:
    logger = logging.getLogger(LOGGER_NAME)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    return logger


def _redact(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            str(key): "[REDACTED]" if str(key).lower() in _REDACTED_KEYS else _redact(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_redact(item) for item in value]
    return value


def log_event(logger: logging.Logger, event: Mapping[str, Any]) -> None:
    logger.info(json.dumps(_redact(dict(event)), separators=(",", ":"), default=str))
