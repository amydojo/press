from fastapi.testclient import TestClient


def test_healthz(client: TestClient) -> None:
    response = client.get("/healthz", headers={"x-request-id": "test-request-id"})

    assert response.status_code == 200
    assert response.headers["x-request-id"] == "test-request-id"
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["service"] == "press-generation-api"
    assert payload["version"] == "0.1.0"
    assert payload["environment"] == "test"
    assert payload["timestamp"]


def test_version(client: TestClient) -> None:
    response = client.get("/version")

    assert response.status_code == 200
    assert response.json() == {
        "version": "0.1.0",
        "commitSha": None,
        "buildTimestamp": None,
    }


def test_create_route_is_truthful_501(client: TestClient) -> None:
    response = client.post(
        "/v1/pressings",
        json={
            "sourceType": "fixture",
            "selectedFragment": "A precise fragment.",
            "personalNote": "The pacing feels like music.",
        },
    )

    assert response.status_code == 501
    assert response.json()["detail"]["code"] == "generation_not_implemented"
    assert response.json()["detail"]["arrivesIn"] == "PR 2"
