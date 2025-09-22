import pytest


@pytest.fixture(scope="session")
def mockserver():
    from .mockserver import MockServer  # noqa: PLC0415

    with MockServer() as server:
        yield server
