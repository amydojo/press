from __future__ import annotations

import json
import re
from dataclasses import dataclass
from threading import RLock
from typing import Any, Protocol

from press_generation_api.config import Settings
from press_generation_api.errors import StorageOperationError, map_storage_exception

_ALLOWED_KEY = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,1023}$")
_ALLOWED_MIME_TYPES = frozenset(
    {
        "application/json",
        "application/x-ndjson",
        "image/png",
        "image/jpeg",
        "image/webp",
    }
)


@dataclass(frozen=True, slots=True)
class ObjectHead:
    key: str
    size_bytes: int
    content_type: str | None
    metadata: dict[str, str]
    etag: str | None = None


class ObjectStore(Protocol):
    def put_bytes(
        self,
        key: str,
        data: bytes,
        *,
        content_type: str,
        metadata: dict[str, str] | None = None,
    ) -> str: ...

    def get_bytes(self, key: str) -> bytes: ...

    def head(self, key: str) -> ObjectHead | None: ...

    def list_keys(self, prefix: str) -> list[str]: ...

    def delete_keys(self, keys: list[str]) -> None: ...

    def presign_get(self, key: str, *, expires_in: int) -> str: ...

    def close(self) -> None: ...


def validate_object_key(key: str) -> str:
    if not key or key.startswith("/") or key.endswith("/"):
        raise ValueError("Object key must be a non-empty relative object path")
    if "\\" in key or "//" in key or any(part in {"", ".", ".."} for part in key.split("/")):
        raise ValueError("Object key contains an unsafe path segment")
    if not _ALLOWED_KEY.fullmatch(key):
        raise ValueError("Object key contains unsupported characters")
    return key


def validate_payload(data: bytes, content_type: str, *, max_bytes: int) -> None:
    if content_type not in _ALLOWED_MIME_TYPES:
        raise ValueError(f"Unsupported MIME type: {content_type}")
    if not data:
        raise ValueError("Payload cannot be empty")
    if len(data) > max_bytes:
        raise ValueError(f"Payload exceeds {max_bytes} bytes")


def json_bytes(value: Any) -> bytes:
    return json.dumps(value, separators=(",", ":"), sort_keys=True, default=str).encode("utf-8")


def parse_json(data: bytes) -> Any:
    return json.loads(data.decode("utf-8"))


class InMemoryObjectStore:
    """Deterministic test store with the same key and MIME validation as B2."""

    def __init__(self, *, max_bytes: int = 50 * 1024 * 1024) -> None:
        self._max_bytes = max_bytes
        self._objects: dict[str, tuple[bytes, str, dict[str, str]]] = {}
        self._lock = RLock()
        self.fail_next_operation: str | None = None

    def _maybe_fail(self, operation: str) -> None:
        if self.fail_next_operation == operation:
            self.fail_next_operation = None
            raise map_storage_exception(
                RuntimeError(f"forced {operation} failure"), operation=operation
            )

    def put_bytes(
        self,
        key: str,
        data: bytes,
        *,
        content_type: str,
        metadata: dict[str, str] | None = None,
    ) -> str:
        self._maybe_fail("put")
        validate_object_key(key)
        validate_payload(data, content_type, max_bytes=self._max_bytes)
        with self._lock:
            self._objects[key] = (bytes(data), content_type, dict(metadata or {}))
        return key

    def get_bytes(self, key: str) -> bytes:
        self._maybe_fail("get")
        validate_object_key(key)
        with self._lock:
            try:
                return self._objects[key][0]
            except KeyError as exc:
                raise FileNotFoundError(key) from exc

    def head(self, key: str) -> ObjectHead | None:
        self._maybe_fail("head")
        validate_object_key(key)
        with self._lock:
            value = self._objects.get(key)
            if value is None:
                return None
            data, content_type, metadata = value
            return ObjectHead(key, len(data), content_type, dict(metadata), None)

    def list_keys(self, prefix: str) -> list[str]:
        self._maybe_fail("list")
        if prefix:
            validate_object_key(prefix.rstrip("/") + "/placeholder")
        with self._lock:
            return sorted(key for key in self._objects if key.startswith(prefix))

    def delete_keys(self, keys: list[str]) -> None:
        self._maybe_fail("delete")
        with self._lock:
            for key in keys:
                validate_object_key(key)
                self._objects.pop(key, None)

    def presign_get(self, key: str, *, expires_in: int) -> str:
        validate_object_key(key)
        if self.head(key) is None:
            raise FileNotFoundError(key)
        return f"https://private.invalid/{key}?expires={expires_in}&signature=redacted"

    def close(self) -> None:
        return None


class GenblazeB2ObjectStore:
    """Private Backblaze B2 adapter backed by the official genblaze-s3 connector."""

    def __init__(self, settings: Settings) -> None:
        settings.require_live_configuration()
        try:
            from genblaze_s3 import S3StorageBackend  # type: ignore[import-not-found]
        except ImportError as exc:  # pragma: no cover - exercised by live environment
            raise RuntimeError("genblaze-s3 is required for live Backblaze B2 persistence") from exc
        key_id = settings.B2_KEY_ID
        app_key = settings.B2_APPLICATION_KEY
        assert key_id is not None and app_key is not None
        assert settings.B2_BUCKET_NAME is not None
        assert settings.B2_ENDPOINT is not None
        assert settings.B2_REGION is not None
        self._backend = S3StorageBackend(
            bucket=settings.B2_BUCKET_NAME,
            endpoint_url=settings.B2_ENDPOINT,
            region=settings.B2_REGION,
            access_key_id=key_id.get_secret_value(),
            secret_access_key=app_key.get_secret_value(),
        )
        self._max_bytes = max(settings.MAX_SOURCE_BYTES, settings.MAX_GENERATED_ASSET_BYTES)

    def put_bytes(
        self,
        key: str,
        data: bytes,
        *,
        content_type: str,
        metadata: dict[str, str] | None = None,
    ) -> str:
        try:
            validate_object_key(key)
            validate_payload(data, content_type, max_bytes=self._max_bytes)
            return str(
                self._backend.put(
                    key,
                    data,
                    content_type=content_type,
                    metadata=dict(metadata or {}),
                )
            )
        except Exception as exc:
            if isinstance(exc, StorageOperationError):
                raise
            raise map_storage_exception(exc, operation="put") from exc

    def get_bytes(self, key: str) -> bytes:
        try:
            validate_object_key(key)
            return bytes(self._backend.get(key))
        except Exception as exc:
            raise map_storage_exception(exc, operation="get") from exc

    def head(self, key: str) -> ObjectHead | None:
        try:
            validate_object_key(key)
            value = self._backend.head(key)
            if value is None:
                return None
            size = int(getattr(value, "size", getattr(value, "size_bytes", 0)))
            content_type = getattr(value, "content_type", None)
            metadata = dict(getattr(value, "metadata", {}) or {})
            etag = getattr(value, "etag", None)
            return ObjectHead(key, size, content_type, metadata, etag)
        except Exception as exc:
            raise map_storage_exception(exc, operation="head") from exc

    def list_keys(self, prefix: str) -> list[str]:
        try:
            if prefix:
                validate_object_key(prefix.rstrip("/") + "/placeholder")
            keys: list[str] = []
            token: str | None = None
            while True:
                page = self._backend.list(prefix=prefix, continuation_token=token)
                keys.extend(str(entry.key) for entry in page.entries)
                token = page.next_token
                if token is None:
                    return sorted(keys)
        except Exception as exc:
            raise map_storage_exception(exc, operation="list") from exc

    def delete_keys(self, keys: list[str]) -> None:
        try:
            for key in keys:
                validate_object_key(key)
            if not keys:
                return
            result = self._backend.delete_many(keys)
            errors = list(getattr(result, "errors", []) or [])
            if errors:
                raise RuntimeError(f"partial delete failure for {len(errors)} objects")
        except Exception as exc:
            raise map_storage_exception(exc, operation="delete") from exc

    def presign_get(self, key: str, *, expires_in: int) -> str:
        try:
            validate_object_key(key)
            return str(self._backend.get_url(key, expires_in=expires_in))
        except Exception as exc:
            raise map_storage_exception(exc, operation="presign") from exc

    def close(self) -> None:
        self._backend.close()
