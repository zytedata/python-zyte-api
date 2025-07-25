import asyncio
from unittest.mock import AsyncMock

import pytest

from zyte_api import AggressiveRetryFactory, AsyncZyteAPI, RequestError
from zyte_api.aio.client import AsyncClient
from zyte_api.apikey import NoApiKey
from zyte_api.errors import ParsedError
from zyte_api.utils import USER_AGENT


@pytest.mark.parametrize(
    "client_cls",
    (
        AsyncZyteAPI,
        AsyncClient,
    ),
)
@pytest.mark.parametrize(
    ("user_agent", "expected"),
    (
        (
            None,
            USER_AGENT,
        ),
        (
            f"scrapy-zyte-api/0.11.1 {USER_AGENT}",
            f"scrapy-zyte-api/0.11.1 {USER_AGENT}",
        ),
    ),
)
def test_user_agent(client_cls, user_agent, expected):
    client = client_cls(api_key="123", api_url="http:\\test", user_agent=user_agent)
    assert client.user_agent == expected


@pytest.mark.parametrize(
    "client_cls",
    (
        AsyncZyteAPI,
        AsyncClient,
    ),
)
def test_api_key(client_cls):
    client_cls(api_key="a")
    with pytest.raises(NoApiKey):
        client_cls()


@pytest.mark.parametrize(
    ("client_cls", "get_method"),
    (
        (AsyncZyteAPI, "get"),
        (AsyncClient, "request_raw"),
    ),
)
@pytest.mark.asyncio
async def test_get(client_cls, get_method, mockserver):
    client = client_cls(api_key="a", api_url=mockserver.urljoin("/"))
    expected_result = {
        "url": "https://a.example",
        "httpResponseBody": "PGh0bWw+PGJvZHk+SGVsbG88aDE+V29ybGQhPC9oMT48L2JvZHk+PC9odG1sPg==",
    }
    actual_result = await getattr(client, get_method)(
        {"url": "https://a.example", "httpResponseBody": True}
    )
    assert actual_result == expected_result


@pytest.mark.parametrize(
    ("client_cls", "get_method"),
    (
        (AsyncZyteAPI, "get"),
        (AsyncClient, "request_raw"),
    ),
)
@pytest.mark.asyncio
async def test_get_request_error(client_cls, get_method, mockserver):
    client = client_cls(api_key="a", api_url=mockserver.urljoin("/"))
    with pytest.raises(RequestError) as request_error_info:
        await getattr(client, get_method)(
            {"url": "https://exception.example", "browserHtml": True},
        )
    parsed_error = request_error_info.value.parsed
    assert isinstance(parsed_error, ParsedError)
    assert parsed_error.data == {
        "detail": "The authentication key is not valid or can't be matched.",
        "status": 401,
        "title": "Authentication Key Not Found",
        "type": "/auth/key-not-found",
    }


@pytest.mark.parametrize(
    ("client_cls", "get_method"),
    (
        (AsyncZyteAPI, "get"),
        (AsyncClient, "request_raw"),
    ),
)
@pytest.mark.asyncio
async def test_get_request_error_empty_body(client_cls, get_method, mockserver):
    client = client_cls(api_key="a", api_url=mockserver.urljoin("/"))
    with pytest.raises(RequestError) as request_error_info:
        await getattr(client, get_method)(
            {"url": "https://empty-body-exception.example", "browserHtml": True},
        )
    parsed_error = request_error_info.value.parsed
    assert isinstance(parsed_error, ParsedError)
    assert parsed_error.data is None


@pytest.mark.parametrize(
    ("client_cls", "get_method"),
    (
        (AsyncZyteAPI, "get"),
        (AsyncClient, "request_raw"),
    ),
)
@pytest.mark.asyncio
async def test_get_request_error_non_json(client_cls, get_method, mockserver):
    client = client_cls(api_key="a", api_url=mockserver.urljoin("/"))
    with pytest.raises(RequestError) as request_error_info:
        await getattr(client, get_method)(
            {"url": "https://nonjson-exception.example", "browserHtml": True},
        )
    parsed_error = request_error_info.value.parsed
    assert isinstance(parsed_error, ParsedError)
    assert parsed_error.data is None


@pytest.mark.parametrize(
    ("client_cls", "get_method"),
    (
        (AsyncZyteAPI, "get"),
        (AsyncClient, "request_raw"),
    ),
)
@pytest.mark.asyncio
async def test_get_request_error_unexpected_json(client_cls, get_method, mockserver):
    client = client_cls(api_key="a", api_url=mockserver.urljoin("/"))
    with pytest.raises(RequestError) as request_error_info:
        await getattr(client, get_method)(
            {"url": "https://array-exception.example", "browserHtml": True},
        )
    parsed_error = request_error_info.value.parsed
    assert isinstance(parsed_error, ParsedError)
    assert parsed_error.data is None


@pytest.mark.parametrize(
    ("client_cls", "iter_method"),
    (
        (AsyncZyteAPI, "iter"),
        (AsyncClient, "request_parallel_as_completed"),
    ),
)
@pytest.mark.asyncio
async def test_iter(client_cls, iter_method, mockserver):
    client = client_cls(api_key="a", api_url=mockserver.urljoin("/"))
    queries = [
        {"url": "https://a.example", "httpResponseBody": True},
        {"url": "https://exception.example", "httpResponseBody": True},
        {"url": "https://b.example", "httpResponseBody": True},
    ]
    expected_results = [
        {
            "url": "https://a.example",
            "httpResponseBody": "PGh0bWw+PGJvZHk+SGVsbG88aDE+V29ybGQhPC9oMT48L2JvZHk+PC9odG1sPg==",
        },
        Exception,
        {
            "url": "https://b.example",
            "httpResponseBody": "PGh0bWw+PGJvZHk+SGVsbG88aDE+V29ybGQhPC9oMT48L2JvZHk+PC9odG1sPg==",
        },
    ]
    actual_results = []
    for future in getattr(client, iter_method)(queries):
        try:
            actual_result = await future
        except Exception as exception:
            actual_result = exception
        actual_results.append(actual_result)
    assert len(actual_results) == len(expected_results)
    for actual_result in actual_results:
        if isinstance(actual_result, Exception):
            assert Exception in expected_results
        else:
            assert actual_result in expected_results


@pytest.mark.parametrize(
    ("client_cls", "get_method", "iter_method"),
    (
        (AsyncZyteAPI, "get", "iter"),
        (AsyncClient, "request_raw", "request_parallel_as_completed"),
    ),
)
@pytest.mark.asyncio
async def test_semaphore(client_cls, get_method, iter_method, mockserver):
    client = client_cls(api_key="a", api_url=mockserver.urljoin("/"))
    client._semaphore = AsyncMock(wraps=client._semaphore)
    queries = [
        {"url": "https://a.example", "httpResponseBody": True},
        {"url": "https://b.example", "httpResponseBody": True},
        {"url": "https://c.example", "httpResponseBody": True},
    ]
    futures = [
        getattr(client, get_method)(queries[0]),
        next(iter(getattr(client, iter_method)(queries[1:2]))),
        getattr(client, get_method)(queries[2]),
    ]
    for future in asyncio.as_completed(futures):
        await future
    assert client._semaphore.__aenter__.call_count == len(queries)
    assert client._semaphore.__aexit__.call_count == len(queries)


@pytest.mark.asyncio
async def test_session_context_manager(mockserver):
    client = AsyncZyteAPI(api_key="a", api_url=mockserver.urljoin("/"))
    queries = [
        {"url": "https://a.example", "httpResponseBody": True},
        {"url": "https://exception.example", "httpResponseBody": True},
        {"url": "https://b.example", "httpResponseBody": True},
    ]
    expected_results = [
        {
            "url": "https://a.example",
            "httpResponseBody": "PGh0bWw+PGJvZHk+SGVsbG88aDE+V29ybGQhPC9oMT48L2JvZHk+PC9odG1sPg==",
        },
        Exception,
        {
            "url": "https://b.example",
            "httpResponseBody": "PGh0bWw+PGJvZHk+SGVsbG88aDE+V29ybGQhPC9oMT48L2JvZHk+PC9odG1sPg==",
        },
    ]
    actual_results = []
    async with client.session() as session:
        assert session._session.connector.limit == client.n_conn
        actual_results.append(await session.get(queries[0]))
        for future in session.iter(queries[1:]):
            try:
                result = await future
            except Exception as e:
                result = e
            actual_results.append(result)
        aiohttp_session = session._session
        assert not aiohttp_session.closed
    assert aiohttp_session.closed

    with pytest.raises(RuntimeError):
        await session.get(queries[0])

    future = next(iter(session.iter(queries[1:])))
    with pytest.raises(RuntimeError):
        await future

    assert len(actual_results) == len(expected_results)
    for actual_result in actual_results:
        if isinstance(actual_result, Exception):
            assert Exception in expected_results
        else:
            assert actual_result in expected_results


@pytest.mark.asyncio
async def test_session_no_context_manager(mockserver):
    client = AsyncZyteAPI(api_key="a", api_url=mockserver.urljoin("/"))
    queries = [
        {"url": "https://a.example", "httpResponseBody": True},
        {"url": "https://exception.example", "httpResponseBody": True},
        {"url": "https://b.example", "httpResponseBody": True},
    ]
    expected_results = [
        {
            "url": "https://a.example",
            "httpResponseBody": "PGh0bWw+PGJvZHk+SGVsbG88aDE+V29ybGQhPC9oMT48L2JvZHk+PC9odG1sPg==",
        },
        Exception,
        {
            "url": "https://b.example",
            "httpResponseBody": "PGh0bWw+PGJvZHk+SGVsbG88aDE+V29ybGQhPC9oMT48L2JvZHk+PC9odG1sPg==",
        },
    ]
    actual_results = []
    session = client.session()
    assert session._session.connector.limit == client.n_conn
    actual_results.append(await session.get(queries[0]))
    for future in session.iter(queries[1:]):
        try:
            result = await future
        except Exception as e:
            result = e
        actual_results.append(result)
    aiohttp_session = session._session
    assert not aiohttp_session.closed
    await session.close()
    assert aiohttp_session.closed

    with pytest.raises(RuntimeError):
        await session.get(queries[0])

    future = next(iter(session.iter(queries[1:])))
    with pytest.raises(RuntimeError):
        await future

    assert len(actual_results) == len(expected_results)
    for actual_result in actual_results:
        if isinstance(actual_result, Exception):
            assert Exception in expected_results
        else:
            assert actual_result in expected_results


def test_retrying_class():
    """A descriptive exception is raised when creating a client with an
    AsyncRetrying subclass or similar instead of an instance of it."""
    with pytest.raises(ValueError, match="must be an instance of AsyncRetrying"):
        AsyncZyteAPI(api_key="foo", retrying=AggressiveRetryFactory)
