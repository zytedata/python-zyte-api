import importlib.util
from os import environ
from unittest import mock

import pytest

from zyte_api.aio.client import AsyncClient

HAS_X402 = importlib.util.find_spec("x402") is not None
KEY = "c85ef7d79691fe79573b1a7064c5232332f53bb1b44a08f1a737f57a68a4706e"


def test_eth_key_param():
    if HAS_X402:
        AsyncClient(eth_key=KEY)
    else:
        with pytest.raises(ImportError, match="No module named 'eth_account'"):
            AsyncClient(eth_key=KEY)


@mock.patch.dict(environ, {"ZYTE_API_ETH_KEY": KEY})
def test_eth_key_env_var():
    if HAS_X402:
        AsyncClient()
    else:
        with pytest.raises(ImportError, match="No module named 'eth_account'"):
            AsyncClient()


def test_eth_key_short():
    if HAS_X402:
        with pytest.raises(ValueError, match="must be exactly 32 bytes long"):
            AsyncClient(eth_key="a")
    else:
        with pytest.raises(ImportError, match="No module named 'eth_account'"):
            AsyncClient(eth_key="a")
