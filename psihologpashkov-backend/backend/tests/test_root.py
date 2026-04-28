from fastapi.testclient import TestClient


def test_root_returns_service_info(client: TestClient) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {
        "app": "Test API",
        "status": "ok",
        "docs_url": "/docs",
        "health_url": "/api/v1/healthz",
    }
