from fastapi.testclient import TestClient

from main import app

def test_api_demo_smoke(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("LYZR_API_KEY", raising=False)
    monkeypatch.delenv("BUYER_AGENT_ID", raising=False)
    monkeypatch.delenv("SUPPLIER_AGENT_ID", raising=False)
    client = TestClient(app)
    payload = {
        "buyer": {
            "price": {"target": 100000, "maximum": 120000},
            "delivery": {"target_days": 30, "maximum_days": 45},
            "payment": {"preferred_days": 60, "minimum_days": 30},
            "sla": {"minimum_uptime": 98, "minimum_penalty": 1, "maximum_penalty": 5},
            "batna": "backup",
            "max_rounds": 6,
        },
        "supplier": {
            "price": {"target": 110000, "minimum": 95000},
            "delivery": {"target_days": 35, "maximum_days": 50},
            "payment": {"preferred_days": 30, "minimum_days": 15},
            "sla": {"minimum_uptime": 97, "minimum_penalty": 1, "maximum_penalty": 5},
            "batna": "other buyer",
            "max_rounds": 6,
        },
    }
    response = client.post("/api/negotiations", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "agreed"
    assert data["contract"]["contract_hash"]
    assert data["audit_integrity"]["valid"] is True
