import ssl
from typing import Optional, Union

import pytest
from aiohttp import TCPConnector

from zyte_api.aio.client import create_session


@pytest.mark.parametrize(
    "verify_ssl, expected_ssl_mode",
    [
        (None, None),
        (False, False),
        (True, None)
    ],
)
def test_verify_ssl(verify_ssl: Optional[bool], expected_ssl_mode: Optional[bool]):
    session = create_session(verify_ssl=verify_ssl)
    assert session.connector._ssl == expected_ssl_mode  # NOQA


@pytest.mark.parametrize(
    "ssl_mode",
    [
        None,
        False,
        True,
        ssl.SSLContext()
    ],
)
def test_connector_ssl(ssl_mode: Optional[Union[bool, ssl.SSLContext]]):
    connector = TCPConnector(ssl=ssl_mode)
    session = create_session(connector=connector)
    assert session.connector._ssl == ssl_mode  # NOQA


@pytest.mark.parametrize(
    "verify_ssl, ssl_mode, error_message",
    [
        (False, None, r"Provided `verify_ssl` argument \(False\) conflicts "
                      r"with `connector` argument \(connector\._ssl=None\)"),
        (False, ssl.SSLContext(), r"Provided `verify_ssl` argument \(False\) conflicts "
                                  r"with `connector` argument \(connector\._ssl=<ssl\.SSLContext.*>\)"),
        (None, ssl.SSLContext(), r"Provided `verify_ssl` argument \(None\) conflicts "
                                 r"with `connector` argument \(connector\._ssl=<ssl\.SSLContext.*>\)")
    ]
)
def test_verify_connector_conflict(verify_ssl: Optional[bool],
                                   ssl_mode: Optional[Union[bool, ssl.SSLContext]],
                                   error_message: str):
    connector = TCPConnector(ssl=ssl_mode)
    with pytest.raises(ValueError, match=error_message):
        create_session(connector=connector, verify_ssl=verify_ssl)
