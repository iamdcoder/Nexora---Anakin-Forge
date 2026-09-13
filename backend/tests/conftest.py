import os


def pytest_configure():
    os.environ.setdefault("ANAKIN_ENABLED", "0")
