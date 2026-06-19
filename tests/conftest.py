import pytest


@pytest.fixture(autouse=True)
def isolated_apikey_env(tmp_path, monkeypatch):
    """Keep API-key resolution hermetic: drop ambient key env vars and run from
    an empty directory so ``find_dotenv()`` can't pick up a stray ``.env`` from
    the developer's working tree. Tests that need a ``.env`` create it in the
    (now empty) working directory."""
    monkeypatch.delenv("ZYTE_API_KEY", raising=False)
    monkeypatch.delenv("ZYTE_API_ETH_KEY", raising=False)
    monkeypatch.chdir(tmp_path)


@pytest.fixture(scope="session")
def mockserver():
    from .mockserver import MockServer  # noqa: PLC0415

    with MockServer() as server:
        yield server
