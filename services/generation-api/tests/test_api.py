from __future__ import annotations

from fastapi.testclient import TestClient

from press_generation_api.config import Settings
from press_generation_api.main import create_app
from press_generation_api.storage import InMemoryObjectStore


def payload() -> dict[str, str]:
    return {
        "sourceType": "fixture",
        "selectedFragment": "The exact fragment.",
        "personalNote": "This felt like something worth keeping.",
    }


def test_create_get_events_and_idempotency() -> None:
    app = create_app(Settings(PRESS_ENV="test", FIXTURE_MODE=True))
    client = TestClient(app)
    first = client.post(
        "/v1/pressings",
        headers={"Idempotency-Key": "fixture-create"},
        json=payload(),
    )
    assert first.status_code == 202
    pressing_id = first.json()["pressing"]["id"]
    detail = client.get(f"/v1/pressings/{pressing_id}")
    assert detail.status_code == 200
    assert detail.json()["pressing"]["status"] == "ready"
    assert detail.json()["finalAssetAccess"]["url"].startswith("https://private.invalid/")
    events = client.get(f"/v1/pressings/{pressing_id}/events")
    assert events.status_code == 200
    assert events.json()["terminal"] is True
    assert events.json()["events"][-1]["stage"] == "ready"
    duplicate = client.post(
        "/v1/pressings",
        headers={"Idempotency-Key": "fixture-create"},
        json=payload(),
    )
    assert duplicate.status_code == 200
    assert duplicate.json()["pressing"]["id"] == pressing_id


def test_not_found_error_contract_is_stable() -> None:
    client = TestClient(create_app(Settings(PRESS_ENV="test", FIXTURE_MODE=True)))
    response = client.get("/v1/pressings/missing")
    assert response.status_code == 404
    body = response.json()["detail"]
    assert body["code"] == "invalid_input"
    assert body["retryable"] is False
    assert body["requestId"]


def test_retry_conflict_after_ready() -> None:
    client = TestClient(create_app(Settings(PRESS_ENV="test", FIXTURE_MODE=True)))
    created = client.post("/v1/pressings", json=payload())
    pressing_id = created.json()["pressing"]["id"]
    retry = client.post(
        f"/v1/pressings/{pressing_id}/retry",
        headers={"Idempotency-Key": "retry-1"},
        json={"reason": "try again"},
    )
    assert retry.status_code == 409
    assert retry.json()["detail"]["code"] == "conflict"


def test_delete_endpoint_tombstones_pressing() -> None:
    client = TestClient(create_app(Settings(PRESS_ENV="test", FIXTURE_MODE=True)))
    created = client.post("/v1/pressings", json=payload())
    pressing_id = created.json()["pressing"]["id"]
    deleted = client.delete(f"/v1/pressings/{pressing_id}")
    assert deleted.status_code == 200
    assert deleted.json()["status"] == "deleted"
    assert client.get(f"/v1/pressings/{pressing_id}").status_code == 404


def test_process_replacement_reconstructs_through_api() -> None:
    settings = Settings(PRESS_ENV="test", FIXTURE_MODE=True)
    store = InMemoryObjectStore()
    first_app = create_app(settings, store=store)
    first_client = TestClient(first_app)
    created = first_client.post("/v1/pressings", json=payload())
    pressing_id = created.json()["pressing"]["id"]
    first_record = first_client.get(f"/v1/pressings/{pressing_id}").json()["pressing"]

    second_app = create_app(settings, store=store)
    second_client = TestClient(second_app)
    second_record = second_client.get(f"/v1/pressings/{pressing_id}").json()["pressing"]
    assert second_record == first_record


def test_health_and_version_report_truthful_boundary() -> None:
    client = TestClient(create_app(Settings(PRESS_ENV="test", FIXTURE_MODE=True)))
    health = client.get("/healthz")
    assert health.status_code == 200
    assert health.json()["liveProviderConfigured"] is False
    assert health.json()["durableStorageConfigured"] is False
    version = client.get("/version")
    assert version.json()["sponsorBackbone"] == "pr-2"


def test_list_reads_durable_records() -> None:
    store = InMemoryObjectStore()
    settings = Settings(PRESS_ENV="test", FIXTURE_MODE=True)
    client = TestClient(create_app(settings, store=store))
    client.post("/v1/pressings", headers={"Idempotency-Key": "a"}, json=payload())
    client.post("/v1/pressings", headers={"Idempotency-Key": "b"}, json=payload())
    restarted = TestClient(create_app(settings, store=store))
    response = restarted.get("/v1/pressings")
    assert response.status_code == 200
    assert len(response.json()) == 2
