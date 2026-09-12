
from autonomous import anakin_client


class FakeResponse:
    def __init__(self, status_code, payload=None, text="error"):
        self.status_code = status_code
        self._payload = payload
        self.text = text
        self.ok = 200 <= status_code < 300
        self.content = b"{}" if payload is not None else b"error"

    def json(self):
        return self._payload


def test_anakin_retries_transient_http_failure(monkeypatch):
    responses = [
        FakeResponse(503, text="temporarily unavailable"),
        FakeResponse(
            200,
            {
                "markdown": "# Supplier\nDelivery in 30 days.",
                "requestId": "REQ-1",
            },
        ),
    ]

    def fake_post(*args, **kwargs):
        return responses.pop(0)

    sleeps = []

    monkeypatch.setattr(
        anakin_client.requests,
        "post",
        fake_post,
    )
    monkeypatch.setattr(
        anakin_client.time,
        "sleep",
        lambda value: sleeps.append(value),
    )
    monkeypatch.setenv("ANAKIN_MAX_RETRIES", "2")

    result = anakin_client.scrape_url(
        "https://supplier.example"
    )

    assert result["status"] == "read"
    assert result["attempts"] == 2
    assert sleeps


def test_anakin_does_not_retry_permanent_client_error(monkeypatch):
    responses = [
        FakeResponse(404, text="not found"),
    ]

    monkeypatch.setattr(
        anakin_client.requests,
        "post",
        lambda *args, **kwargs: responses.pop(0),
    )

    try:
        anakin_client.scrape_url(
            "https://supplier.example/missing"
        )
    except anakin_client.AnakinScrapeError as exc:
        assert "404" in str(exc)
    else:
        raise AssertionError(
            "Permanent Anakin error was not raised."
        )
