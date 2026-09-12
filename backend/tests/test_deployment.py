from fastapi.testclient import TestClient

from main import app


def test_root_serves_frontend():

    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200

    assert (
        "Nexora"
        in response.text
    )


def test_ui_serves_frontend():

    client = TestClient(app)

    response = client.get("/ui")

    assert response.status_code == 200

    assert (
        "Autonomous"
        in response.text
    )


def test_health_endpoint():

    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "ok"

    assert (
        data["service"]
        == "nexora-negotiator"
    )


def test_autonomous_procurement_route_exists():

    routes = {
        route.path
        for route in app.routes
    }

    assert (
        "/api/autonomous/procure"
        in routes
    )