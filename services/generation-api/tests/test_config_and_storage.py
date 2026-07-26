from __future__ import annotations

import sys
import types
from dataclasses import dataclass

import pytest

from press_generation_api.config import Settings
from press_generation_api.domain.models import FailureCategory
from press_generation_api.errors import StorageOperationError, map_storage_exception
from press_generation_api.storage import (
    GenblazeB2ObjectStore,
    InMemoryObjectStore,
    ObjectHead,
    validate_object_key,
)


def test_settings_reject_partial_b2_configuration() -> None:
    with pytest.raises(ValueError, match="complete server-only group"):
        Settings(B2_KEY_ID="id")


def test_settings_reject_non_https_b2_endpoint() -> None:
    with pytest.raises(ValueError, match="absolute HTTPS"):
        Settings(
            B2_KEY_ID="id",
            B2_APPLICATION_KEY="secret",
            B2_BUCKET_NAME="bucket",
            B2_ENDPOINT="http://example.invalid",
            B2_REGION="us-west-004",
        )


def test_live_configuration_names_exact_missing_values() -> None:
    settings = Settings()
    with pytest.raises(ValueError) as exc_info:
        settings.require_live_configuration()
    message = str(exc_info.value)
    assert "GENBLAZE_PROVIDER_API_KEY" in message
    assert "B2_APPLICATION_KEY" in message


@pytest.mark.parametrize(
    "key",
    ["", "/absolute", "pressings/../secret", "pressings//x", "pressings\\x", "a/./b"],
)
def test_object_key_validation_rejects_unsafe_paths(key: str) -> None:
    with pytest.raises(ValueError):
        validate_object_key(key)


def test_memory_store_round_trip_metadata_and_private_url() -> None:
    store = InMemoryObjectStore()
    key = "pressings/p1/source/source.json"
    store.put_bytes(
        key,
        b"{}",
        content_type="application/json",
        metadata={"kind": "source"},
    )
    assert store.get_bytes(key) == b"{}"
    assert store.head(key) == ObjectHead(key, 2, "application/json", {"kind": "source"}, None)
    assert store.list_keys("pressings/p1/") == [key]
    url = store.presign_get(key, expires_in=300)
    assert "expires=300" in url
    assert "signature=redacted" in url
    store.delete_keys([key])
    assert store.head(key) is None


def test_storage_error_mapping_is_stable() -> None:
    error = map_storage_exception(RuntimeError("AccessDenied"), operation="get")
    assert error.category is FailureCategory.STORAGE_AUTHORIZATION_FAILED
    assert "denied" in error.public_message.lower()


@dataclass
class _FakeEntry:
    key: str


@dataclass
class _FakePage:
    entries: list[_FakeEntry]
    next_token: str | None = None


@dataclass
class _FakeMeta:
    size: int
    content_type: str
    metadata: dict[str, str]
    etag: str


class _FakeBackend:
    instances: list["_FakeBackend"] = []

    def __init__(self, **kwargs: object) -> None:
        self.kwargs = kwargs
        self.objects: dict[str, tuple[bytes, str, dict[str, str]]] = {}
        self.closed = False
        self.instances.append(self)

    def put(
        self,
        key: str,
        data: bytes,
        *,
        content_type: str,
        metadata: dict[str, str],
    ) -> str:
        self.objects[key] = (data, content_type, metadata)
        return key

    def get(self, key: str) -> bytes:
        return self.objects[key][0]

    def head(self, key: str) -> _FakeMeta | None:
        value = self.objects.get(key)
        if value is None:
            return None
        return _FakeMeta(len(value[0]), value[1], value[2], "etag")

    def list(self, *, prefix: str, continuation_token: str | None) -> _FakePage:
        del continuation_token
        return _FakePage([_FakeEntry(key) for key in sorted(self.objects) if key.startswith(prefix)])

    def delete_many(self, keys: list[str]) -> object:
        for key in keys:
            self.objects.pop(key, None)
        return types.SimpleNamespace(errors=[])

    def get_url(self, key: str, *, expires_in: int) -> str:
        return f"https://b2.invalid/{key}?X-Amz-Expires={expires_in}"

    def close(self) -> None:
        self.closed = True


def test_genblaze_b2_adapter_uses_private_s3_boundary(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_module = types.ModuleType("genblaze_s3")
    fake_module.S3StorageBackend = _FakeBackend  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "genblaze_s3", fake_module)
    settings = Settings(
        GENBLAZE_PROVIDER_API_KEY="provider-secret",
        B2_KEY_ID="key-id",
        B2_APPLICATION_KEY="app-key",
        B2_BUCKET_NAME="private-bucket",
        B2_ENDPOINT="https://s3.us-west-004.backblazeb2.com",
        B2_REGION="us-west-004",
    )
    store = GenblazeB2ObjectStore(settings)
    backend = _FakeBackend.instances[-1]
    assert backend.kwargs["bucket"] == "private-bucket"
    assert backend.kwargs["access_key_id"] == "key-id"
    key = "pressings/p1/source/source.json"
    store.put_bytes(key, b"{}", content_type="application/json")
    assert store.get_bytes(key) == b"{}"
    assert store.head(key) is not None
    assert store.list_keys("pressings/p1/") == [key]
    assert "X-Amz-Expires=120" in store.presign_get(key, expires_in=120)
    store.delete_keys([key])
    store.close()
    assert backend.closed


def test_memory_store_failure_maps_to_application_error() -> None:
    store = InMemoryObjectStore()
    store.fail_next_operation = "put"
    with pytest.raises(StorageOperationError) as exc_info:
        store.put_bytes("safe/key.json", b"{}", content_type="application/json")
    assert exc_info.value.category is FailureCategory.STORAGE_UPLOAD_FAILED
