import pytest

from agents.lyzr_client import LyzrClient

def test_lyzr_client_uses_current_v3_inference_route(monkeypatch):
    monkeypatch.setenv("LYZR_API_KEY", "sk-test")
    monkeypatch.setenv("LYZR_BASE_URL", "https://example.test")
    calls = {}

    class Response:
        ok = True
        def json(self):
            return {"response": "{\\\"ok\\\":true}"}

    def fake_post(url, headers, json, timeout):
        calls.update(url=url, headers=headers, json=json, timeout=timeout)
        return Response()

    monkeypatch.setattr("agents.lyzr_client.requests.post", fake_post)
    result = LyzrClient().chat("agent-1", "user-1", "session-1", "hello")

    assert result == '{\\"ok\\":true}'
    assert calls["url"] == "https://example.test/v3/inference/chat/"
    assert calls["headers"]["x-api-key"] == "sk-test"
    assert calls["json"]["agent_id"] == "agent-1"
    assert calls["json"]["session_id"] == "session-1"

def test_lyzr_client_accepts_agent_response_compatibility(monkeypatch):
    monkeypatch.setenv("LYZR_API_KEY", "sk-test")

    class Response:
        ok = True
        def json(self):
            return {"agent_response": "hello"}

    monkeypatch.setattr("agents.lyzr_client.requests.post", lambda *a, **k: Response())
    assert LyzrClient().chat("agent-1", "user-1", "session-1", "hello") == "hello"

def test_lyzr_client_reports_http_errors_without_secret(monkeypatch):
    monkeypatch.setenv("LYZR_API_KEY", "sk-super-secret")

    class Response:
        ok = False
        status_code = 401
        text = "unauthorized"

    monkeypatch.setattr("agents.lyzr_client.requests.post", lambda *a, **k: Response())
    with pytest.raises(RuntimeError) as exc:
        LyzrClient().chat("agent-1", "user-1", "session-1", "hello")
    assert "401" in str(exc.value)
    assert "sk-super-secret" not in str(exc.value)
