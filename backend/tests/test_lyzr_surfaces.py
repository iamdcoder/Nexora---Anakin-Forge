import importlib


def test_architecture_endpoint(monkeypatch):
    monkeypatch.setenv("BUYER_AGENT_ID", "buyer")
    monkeypatch.setenv("SUPPLIER_AGENT_ID", "supplier")
    monkeypatch.setenv("LYZR_USE_SDK", "1")
    main = importlib.import_module("main")
    data = main.architecture_status()
    assert data["separation_ok"] is True
    assert [x["name"] for x in data["layers"][:3]] == ["Environment", "Agent", "Inference"]


def test_agent_status_never_returns_api_key(monkeypatch):
    monkeypatch.setenv("LYZR_API_KEY", "top-secret")
    monkeypatch.setenv("BUYER_AGENT_ID", "buyer")
    monkeypatch.setenv("SUPPLIER_AGENT_ID", "supplier")
    main = importlib.import_module("main")
    data = main.agent_status()
    assert data["security"]["api_key_exposed"] is False
    assert "top-secret" not in str(data)
