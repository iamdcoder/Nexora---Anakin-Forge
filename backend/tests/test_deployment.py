from fastapi.testclient import TestClient

from main import app


def test_root_serves_frontend():

    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200

    assert "Nexora" in response.text


def test_ui_serves_frontend():

    client = TestClient(app)

    response = client.get("/ui")

    assert response.status_code == 200

    assert "Autonomous" in response.text


def test_health_endpoint():

    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "ok"

    assert data["service"] == "nexora-negotiator"

    assert "version" in data
    assert "data_dir" in data


def test_ready_endpoint_reports_configuration_state():

    client = TestClient(app)

    response = client.get("/ready")

    assert response.status_code in {200, 503}

    if response.status_code == 200:
        data = response.json()
        assert data["status"] == "ready"
        assert data["ready"] is True
    else:
        detail = response.json()["detail"]
        assert detail["status"] == "not_ready"
        assert detail["ready"] is False
        assert isinstance(detail["checks"], dict)


def test_autonomous_procurement_route_exists():

    # Newer FastAPI versions wrap included routers in an internal
    # `_IncludedRouter` object that has no `.path` attribute, so walking
    # `app.routes` directly is not version-safe. The OpenAPI schema is a
    # stable public API for enumerating registered paths across versions.
    paths = set(app.openapi()["paths"].keys())

    assert "/api/autonomous/procure" in paths
