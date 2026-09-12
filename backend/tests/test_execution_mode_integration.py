from fastapi.testclient import TestClient

from main import app


def buyer_policy():

    return {
        "price": {
            "target": 110000,
            "minimum": 100000,
            "maximum": 120000,
        },
        "delivery": {
            "target_days": 30,
            "minimum_days": 20,
            "maximum_days": 40,
        },
        "payment": {
            "preferred_days": 60,
            "minimum_days": 30,
            "maximum_days": 90,
        },
        "sla": {
            "minimum_uptime": 98,
            "maximum_uptime": 99.9,
            "minimum_penalty": 1,
            "maximum_penalty": 5,
        },
        "batna": "No-deal",
        "max_rounds": 8,
    }


def test_simulation_mode_is_explicit():

    client = TestClient(app)

    payload = {
        "buyer": buyer_policy(),
        "supplier": buyer_policy(),
        "buyer_name": "Buyer Corp",
        "supplier_name": "Supplier Corp",
        "product_name": "Industrial Servo Motors",
        "quantity": 1000,
        "execution_mode": "simulation",
    }

    response = client.post(
        "/api/negotiations",
        json=payload,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["mode"] == "simulation"


def test_lyzr_mode_requires_credentials(
    monkeypatch,
):

    monkeypatch.delenv(
        "LYZR_API_KEY",
        raising=False,
    )

    monkeypatch.delenv(
        "BUYER_AGENT_ID",
        raising=False,
    )

    monkeypatch.delenv(
        "SUPPLIER_AGENT_ID",
        raising=False,
    )

    client = TestClient(app)

    payload = {
        "buyer": buyer_policy(),
        "supplier": buyer_policy(),
        "buyer_name": "Buyer Corp",
        "supplier_name": "Supplier Corp",
        "product_name": "Industrial Servo Motors",
        "quantity": 1000,
        "execution_mode": "lyzr",
    }

    response = client.post(
        "/api/negotiations",
        json=payload,
    )

    assert response.status_code == 503