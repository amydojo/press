from fastapi.testclient import TestClient


def test_healthz(client: TestClient) -> None:
    response = client.get("/healthz", headers={"x-request-id": "test-request-id"})
    assert response.status_code == 200
    assert response.headers["x-request-id"] == "test-request-id"
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["service"] == "press-generation-api"
    assert payload["version"] == "0.2.0"
    assert payload["environment"] == "test"
    assert payload["timestamp"]
    assert payload["liveProviderConfigured"] is False
    assert payload["durableStorageConfigured"] is False


def test_version(client: TestClient) -> None:
    response = client.get("/version")
    assert response.status_code == 200
    assert response.json() == {
        "version": "0.2.0",
        "commitSha": None,
        "buildTimestamp": None,
        "sponsorBackbone": "pr-2",
    }


def test_create_route_executes_fixture_pipeline(client: TestClient) -> None:
    response = client.post(
        "/v1/pressings",
        json={
            "sourceType": "fixture",
            "selectedFragment": "A precise fragment.",
            "personalNote": "The pacing feels like music.",
        },
    )
    assert response.status_code == 202
    pressing_id = response.json()["pressing"]["id"]
    reconstructed = client.get(f"/v1/pressings/{pressing_id}")
    assert reconstructed.status_code == 200
    assert reconstructed.json()["pressing"]["status"] == "ready"
