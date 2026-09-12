import os


def pytest_configure():
    # Keep the deterministic test suite offline. Individual Anakin integration
    # tests explicitly enable the provider with monkeypatch.setenv().
    os.environ.setdefault("ANAKIN_ENABLED", "0")
