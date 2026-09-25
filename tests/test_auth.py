from __future__ import annotations

from base64 import b64encode
from contextlib import asynccontextmanager
from os import environ
from pathlib import Path
from subprocess import CompletedProcess, run
from tempfile import NamedTemporaryFile
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from zyte_api import AsyncZyteAPI

from .test_x402 import HAS_X402
from .test_x402 import KEY as ETH_KEY

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from .mockserver import MockServer

ETH_KEY_2 = ETH_KEY[-1] + ETH_KEY[:-1]
assert ETH_KEY_2 != ETH_KEY


def run_zyte_api(
    args: list[str], env: dict[str, str], mockserver: MockServer
) -> CompletedProcess[bytes]:
    base_env = {
        key: value
        for key, value in environ.items()
        if key not in {"ZYTE_API_KEY", "ZYTE_API_ETH_KEY"}
    }
    with NamedTemporaryFile("w") as url_list:
        url_list.write("https://a.example\n")
        url_list.flush()
        return run(
            [
                "python",
                "-m",
                "zyte_api",
                "--api-url",
                mockserver.urljoin("/"),
                url_list.name,
                *args,
            ],
            capture_output=True,
            check=False,
            env={**base_env, **env},
        )


@pytest.mark.parametrize(
    ("scenario", "expected"),
    (
        ({}, {"stderr": "NoApiKey"}),
        ({"args": ["--api-key", "a"]}, {}),
        ({"env": {"ZYTE_API_KEY": "a"}}, {}),
        (
            {"args": ["--eth-key", ETH_KEY]},
            {} if HAS_X402 else {"stderr": "ModuleNotFoundError"},
        ),
        (
            {"env": {"ZYTE_API_ETH_KEY": ETH_KEY}},
            {} if HAS_X402 else {"stderr": "ModuleNotFoundError"},
        ),
    ),
)
def test(
    scenario: dict[str, Any], expected: dict[str, str], mockserver: MockServer
) -> None:
    result = run_zyte_api(
        scenario.get("args", []),
        scenario.get("env", {}),
        mockserver,
    )
    if "stderr" in expected:
        assert expected["stderr"].encode() in result.stderr
        assert result.returncode == 1
    else:
        assert result.returncode == 0


def test_dotenv_cli(mockserver: MockServer, tmp_path: Path) -> None:
    # The autouse fixture chdir'd into the empty tmp_path, so there is no key
    # anywhere yet.
    result = run_zyte_api([], {}, mockserver)
    assert b"NoApiKey" in result.stderr
    assert result.returncode == 1

    # ZYTE_API_KEY read from the nearest .env (the current directory).
    Path(".env").write_text("ZYTE_API_KEY=fromdotenv\n", encoding="utf8")
    result = run_zyte_api([], {}, mockserver)
    assert result.returncode == 0, result.stderr

    # --dotenv-path points at a different file.
    Path(".env").unlink()
    custom = tmp_path / "custom.env"
    custom.write_text("ZYTE_API_KEY=fromcustom\n", encoding="utf8")
    result = run_zyte_api(["--dotenv-path", str(custom)], {}, mockserver)
    assert result.returncode == 0, result.stderr


@pytest.mark.skipif(not HAS_X402, reason="x402 extra not installed")
def test_dotenv_cli_eth_key(mockserver: MockServer, tmp_path: Path) -> None:
    Path(".env").write_text(f"ZYTE_API_ETH_KEY={ETH_KEY}\n", encoding="utf8")
    result = run_zyte_api([], {}, mockserver)
    assert result.returncode == 0, result.stderr


@pytest.mark.skipif(not HAS_X402, reason="x402 extra not installed")
def test_dotenv_eth_key(tmp_path: Path) -> None:
    (tmp_path / ".env").write_text(f"ZYTE_API_ETH_KEY={ETH_KEY}\n", encoding="utf8")

    client = AsyncZyteAPI()

    assert client.auth.type == "eth"
    assert client.auth.key == ETH_KEY
    assert client.api_url == "https://api-x402.zyte.com/v1/"


@pytest.mark.parametrize(
    ("scenario", "expected"),
    (
        (
            {
                "kwargs": {"api_key": "a", "eth_key": ETH_KEY},
                "env": {
                    "ZYTE_API_KEY": "b",
                    "ZYTE_API_ETH_KEY": ETH_KEY_2,
                },
            },
            {"key_type": "zyte", "key": "a"},
        ),
        (
            {
                "kwargs": {"eth_key": ETH_KEY},
                "env": {
                    "ZYTE_API_KEY": "b",
                    "ZYTE_API_ETH_KEY": ETH_KEY_2,
                },
            },
            {"key_type": "eth", "key": ETH_KEY},
        ),
        (
            {
                "env": {
                    "ZYTE_API_KEY": "b",
                    "ZYTE_API_ETH_KEY": ETH_KEY_2,
                },
            },
            {"key_type": "zyte", "key": "b"},
        ),
        (
            {
                "env": {
                    "ZYTE_API_ETH_KEY": ETH_KEY_2,
                },
            },
            {"key_type": "eth", "key": ETH_KEY_2},
        ),
    ),
)
def test_precedence(
    scenario: dict[str, Any], expected: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    for key, value in scenario.get("env", {}).items():
        monkeypatch.setenv(key, value)
    if expected["key_type"] == "eth" and not HAS_X402:
        with pytest.raises(ImportError):
            AsyncZyteAPI(**scenario.get("kwargs", {}))
        return
    client = AsyncZyteAPI(**scenario.get("kwargs", {}))
    assert client.auth.type == expected["key_type"]
    assert client.auth.key == expected["key"]
    assert (
        client.api_url == "https://api-x402.zyte.com/v1/"
        if expected["key_type"] == "eth"
        else "https://api.zyte.com/v1/"
    )
    if expected["key_type"] == "zyte":
        with pytest.warns(DeprecationWarning, match="api_key property is deprecated"):
            assert client.api_key == expected["key"]
    else:
        with pytest.raises(
            NotImplementedError,
            match="api_key is not available when using an Ethereum private key",
        ):
            client.api_key  # noqa: B018


@pytest.mark.asyncio
async def test_basic_auth_header() -> None:
    api_key = "testkey"
    captured_headers = {}

    response_mock = MagicMock()
    response_mock.status = 200
    response_mock.headers = {}
    response_mock.__aenter__ = AsyncMock(return_value=response_mock)
    response_mock.__aexit__ = AsyncMock(return_value=False)
    response_mock.json = AsyncMock(return_value={"url": "https://a.example"})

    @asynccontextmanager
    async def fake_post(**kwargs: Any) -> AsyncIterator[MagicMock]:
        captured_headers.update(kwargs.get("headers", {}))
        yield response_mock

    with patch("zyte_api._async._post_func", return_value=fake_post):
        client = AsyncZyteAPI(api_key=api_key)
        await client.get({"url": "https://a.example", "httpResponseBody": True})

    expected = "Basic " + b64encode(f"{api_key}:".encode()).decode()
    assert captured_headers.get("Authorization") == expected
