from types import GeneratorType
from unittest.mock import AsyncMock

import pytest

from zyte_api import ZyteAPI
from zyte_api.apikey import NoApiKey


def test_api_key():
    ZyteAPI(api_key="a")
    with pytest.raises(NoApiKey):
        ZyteAPI()


def test_get(mockserver):
    client = ZyteAPI(api_key="a", api_url=mockserver.urljoin("/"))
    expected_result = {
        "url": "https://a.example",
        "httpResponseBody": "PGh0bWw+PGJvZHk+SGVsbG88aDE+V29ybGQhPC9oMT48L2JvZHk+PC9odG1sPg==",
    }
    actual_result = client.get({"url": "https://a.example", "httpResponseBody": True})
    assert actual_result == expected_result


def test_iter(mockserver):
    client = ZyteAPI(api_key="a", api_url=mockserver.urljoin("/"))
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
    actual_results = client.iter(queries)
    assert isinstance(actual_results, GeneratorType)
    actual_results_list = list(actual_results)
    assert len(actual_results_list) == len(expected_results)
    for actual_result in actual_results_list:
        if isinstance(actual_result, Exception):
            assert Exception in expected_results
        else:
            assert actual_result in expected_results


def test_semaphore(mockserver):
    client = ZyteAPI(api_key="a", api_url=mockserver.urljoin("/"))
    client._async_client._semaphore = AsyncMock(wraps=client._async_client._semaphore)
    queries = [
        {"url": "https://a.example", "httpResponseBody": True},
        {"url": "https://b.example", "httpResponseBody": True},
        {"url": "https://c.example", "httpResponseBody": True},
    ]
    client.get(queries[0])
    next(iter(client.iter(queries[1:2])))
    client.get(queries[2])
    assert client._async_client._semaphore.__aenter__.call_count == len(queries)
    assert client._async_client._semaphore.__aexit__.call_count == len(queries)


def test_session_context_manager(mockserver):
    client = ZyteAPI(api_key="a", api_url=mockserver.urljoin("/"))
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
    with client.session() as session:
        assert session._session.connector.limit == client._async_client.n_conn
        actual_results.append(session.get(queries[0]))
        actual_results.extend(session.iter(queries[1:]))
        aiohttp_session = session._session
        assert not aiohttp_session.closed
    assert aiohttp_session.closed

    with pytest.raises(RuntimeError):
        session.get(queries[0])

    assert isinstance(next(iter(session.iter(queries[1:]))), RuntimeError)

    assert len(actual_results) == len(expected_results)
    for actual_result in actual_results:
        if isinstance(actual_result, Exception):
            assert Exception in expected_results
        else:
            assert actual_result in expected_results


def test_session_no_context_manager(mockserver):
    client = ZyteAPI(api_key="a", api_url=mockserver.urljoin("/"))
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
    assert session._session.connector.limit == client._async_client.n_conn
    actual_results.append(session.get(queries[0]))
    actual_results.extend(session.iter(queries[1:]))
    aiohttp_session = session._session
    assert not aiohttp_session.closed
    session.close()
    assert aiohttp_session.closed

    with pytest.raises(RuntimeError):
        session.get(queries[0])

    assert isinstance(next(iter(session.iter(queries[1:]))), RuntimeError)

    assert len(actual_results) == len(expected_results)
    for actual_result in actual_results:
        if isinstance(actual_result, Exception):
            assert Exception in expected_results
        else:
            assert actual_result in expected_results
