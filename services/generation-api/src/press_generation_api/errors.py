from __future__ import annotations

from dataclasses import dataclass
from http import HTTPStatus

from press_generation_api.domain.models import FailureCategory


@dataclass(frozen=True, slots=True)
class PressError(Exception):
    category: FailureCategory
    public_message: str
    status_code: int = HTTPStatus.INTERNAL_SERVER_ERROR
    retryable: bool = False

    def __str__(self) -> str:
        return self.public_message


class PressingNotFoundError(PressError):
    def __init__(self, pressing_id: str) -> None:
        super().__init__(
            FailureCategory.INVALID_INPUT,
            f"Pressing {pressing_id} was not found",
            HTTPStatus.NOT_FOUND,
            False,
        )


class PressingConflictError(PressError):
    def __init__(self, message: str) -> None:
        super().__init__(FailureCategory.CONFLICT, message, HTTPStatus.CONFLICT, False)


class RetryLimitReachedError(PressError):
    def __init__(self) -> None:
        super().__init__(
            FailureCategory.RETRY_LIMIT_REACHED,
            "The pressing has reached its bounded retry limit",
            HTTPStatus.CONFLICT,
            False,
        )


class LiveConfigurationError(PressError):
    def __init__(self, message: str) -> None:
        super().__init__(
            FailureCategory.INVALID_INPUT, message, HTTPStatus.SERVICE_UNAVAILABLE, False
        )


class StorageOperationError(PressError):
    pass


def map_storage_exception(exc: Exception, *, operation: str) -> StorageOperationError:
    text = str(exc).lower()
    name = type(exc).__name__.lower()
    combined = f"{name} {text}"
    if "invalid" in combined and "key" in combined:
        return StorageOperationError(
            FailureCategory.STORAGE_INVALID_KEY,
            "The storage object key is invalid",
            HTTPStatus.BAD_REQUEST,
            False,
        )
    if any(
        token in combined for token in ("invalidaccesskeyid", "signaturedoesnotmatch", "credential")
    ):
        return StorageOperationError(
            FailureCategory.STORAGE_AUTHENTICATION_FAILED,
            "Backblaze B2 credentials were rejected",
            HTTPStatus.SERVICE_UNAVAILABLE,
            False,
        )
    if any(token in combined for token in ("accessdenied", "forbidden", "not authorized")):
        return StorageOperationError(
            FailureCategory.STORAGE_AUTHORIZATION_FAILED,
            "Backblaze B2 denied the requested operation",
            HTTPStatus.SERVICE_UNAVAILABLE,
            False,
        )
    if any(token in combined for token in ("nosuchbucket", "bucket does not exist")):
        return StorageOperationError(
            FailureCategory.STORAGE_BUCKET_MISSING,
            "The configured Backblaze B2 bucket was not found",
            HTTPStatus.SERVICE_UNAVAILABLE,
            False,
        )
    if any(token in combined for token in ("nosuchkey", "not found", "404")):
        return StorageOperationError(
            FailureCategory.STORAGE_OBJECT_MISSING,
            "The requested durable object was not found",
            HTTPStatus.NOT_FOUND,
            False,
        )
    if any(token in combined for token in ("timeout", "timed out", "readtimeouterror")):
        return StorageOperationError(
            FailureCategory.STORAGE_TIMED_OUT,
            "Backblaze B2 timed out",
            HTTPStatus.GATEWAY_TIMEOUT,
            True,
        )
    if any(token in combined for token in ("slowdown", "throttl", "rate")):
        return StorageOperationError(
            FailureCategory.STORAGE_RATE_LIMITED,
            "Backblaze B2 rate limited the request",
            HTTPStatus.SERVICE_UNAVAILABLE,
            True,
        )
    category = (
        FailureCategory.STORAGE_UPLOAD_FAILED
        if operation.startswith("put")
        else FailureCategory.STORAGE_DOWNLOAD_FAILED
    )
    return StorageOperationError(
        category,
        f"Durable storage {operation} failed",
        HTTPStatus.SERVICE_UNAVAILABLE,
        True,
    )
