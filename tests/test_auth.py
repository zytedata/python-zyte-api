from os import environ
from subprocess import run
from tempfile import NamedTemporaryFile

import pytest

from zyte_api import AsyncZyteAPI
from zyte_api._x402 import _x402Handler

from .test_x402 import HAS_X402
from .test_x402 import KEY as ETH_KEY

ETH_KEY_2 = ETH_KEY[-1] + ETH_KEY[:-1]
assert ETH_KEY_2 != ETH_KEY


def run_zyte_api(args, env, mockserver):
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
            env={**environ, **env},
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
def test(scenario, expected, mockserver):
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
def test_precedence(scenario, expected, monkeypatch):
    for key, value in scenario.get("env", {}).items():
        monkeypatch.setenv(key, value)
    if expected["key_type"] == "eth" and not HAS_X402:
        with pytest.raises(ImportError):
            AsyncZyteAPI(**scenario.get("kwargs", {}))
        return
    client = AsyncZyteAPI(**scenario.get("kwargs", {}))
    if expected["key_type"] == "zyte":
        assert client.auth == expected["key"]
    else:
        assert expected["key_type"] == "eth"
        assert isinstance(client.auth, _x402Handler)
        assert client.auth.client.account.key.hex() == expected["key"]
