from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Generator
    from pathlib import Path

    from .mockserver import MockServer


@pytest.fixture(autouse=True)
def isolated_apikey_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep API-key resolution hermetic: drop ambient key env vars and run from
    an empty directory so ``find_dotenv()`` can't pick up a stray ``.env`` from
    the developer's working tree. Tests that need a ``.env`` create it in the
    (now empty) working directory."""
    monkeypatch.delenv("ZYTE_API_KEY", raising=False)
    monkeypatch.delenv("ZYTE_API_ETH_KEY", raising=False)
    monkeypatch.chdir(tmp_path)


@pytest.fixture(scope="session")
def mockserver() -> Generator[MockServer]:
    from .mockserver import MockServer  # noqa: PLC0415

    with MockServer() as server:
        yield server
