import ssl
from typing import Optional, Union

import pytest
from aiohttp import ClientConnectorCertificateError, TCPConnector

from tests.server.mockserver import MockServer
from zyte_api.aio.client import create_session, AsyncClient


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
    assert session.connector._ssl == expected_ssl_mode  # type: ignore


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
    assert session.connector._ssl == ssl_mode  # type: ignore


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


@pytest.mark.asyncio
async def test_disabled_ssl_verification():
    with MockServer():
        session = create_session(verify_ssl=False)
        data = {'url': 'https://example.com', 'browserHtml': True}
        client = AsyncClient(api_url="https://127.0.0.1:4443/", api_key="TEST")
        resp = await client.request_raw(data,
                                        handle_retries=False,
                                        session=session)
        # Check mirorred data
        assert resp == data


@pytest.mark.asyncio
async def test_enabled_ssl_verification():
    with MockServer():
        session = create_session()
        data = {'url': 'https://example.com', 'browserHtml': True}
        client = AsyncClient(api_url="https://127.0.0.1:4443/", api_key="TEST")
        with pytest.raises(ClientConnectorCertificateError):
            await client.request_raw(data,
                                     handle_retries=False,
                                     session=session)
