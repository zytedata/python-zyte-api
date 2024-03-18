from types import GeneratorType

from zyte_api import AsyncZyteAPI
from zyte_api.apikey import NoApiKey
from zyte_api.utils import USER_AGENT

import pytest


@pytest.mark.parametrize(
    "user_agent,expected",
    (
        (
            None,
            USER_AGENT,
        ),
        (
            f'scrapy-zyte-api/0.11.1 {USER_AGENT}',
            f'scrapy-zyte-api/0.11.1 {USER_AGENT}',
        ),
    ),
)
def test_user_agent(user_agent, expected):
    client = AsyncZyteAPI(api_key='123', api_url='http:\\test', user_agent=user_agent)
    assert client.user_agent == expected


def test_api_key():
    AsyncZyteAPI(api_key="a")
    with pytest.raises(NoApiKey):
        AsyncZyteAPI()


@pytest.mark.asyncio
async def test_get(mockserver):
    client = AsyncZyteAPI(api_key="a", api_url=mockserver.urljoin("/"))
    expected_result = {"url": "https://a.example", "httpResponseBody": "PGh0bWw+PGJvZHk+SGVsbG88aDE+V29ybGQhPC9oMT48L2JvZHk+PC9odG1sPg=="}
    actual_result = await client.get({"url": "https://a.example", "httpResponseBody": True})
    assert actual_result == expected_result


@pytest.mark.asyncio
async def test_iter(mockserver):
    client = AsyncZyteAPI(api_key="a", api_url=mockserver.urljoin("/"))
    queries = [
        {"url": "https://a.example", "httpResponseBody": True},
        {"url": "https://exception.example", "httpResponseBody": True},
        {"url": "https://b.example", "httpResponseBody": True},
    ]
    expected_results = [
        {"url": "https://a.example", "httpResponseBody": "PGh0bWw+PGJvZHk+SGVsbG88aDE+V29ybGQhPC9oMT48L2JvZHk+PC9odG1sPg=="},
        Exception,
        {"url": "https://b.example", "httpResponseBody": "PGh0bWw+PGJvZHk+SGVsbG88aDE+V29ybGQhPC9oMT48L2JvZHk+PC9odG1sPg=="},
    ]
    actual_results = []
    for future in client.iter(queries):
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


@pytest.mark.asyncio
async def test_session(mockserver):
    client = AsyncZyteAPI(api_key="a", api_url=mockserver.urljoin("/"))
    queries = [
        {"url": "https://a.example", "httpResponseBody": True},
        {"url": "https://exception.example", "httpResponseBody": True},
        {"url": "https://b.example", "httpResponseBody": True},
    ]
    expected_results = [
        {"url": "https://a.example", "httpResponseBody": "PGh0bWw+PGJvZHk+SGVsbG88aDE+V29ybGQhPC9oMT48L2JvZHk+PC9odG1sPg=="},
        Exception,
        {"url": "https://b.example", "httpResponseBody": "PGh0bWw+PGJvZHk+SGVsbG88aDE+V29ybGQhPC9oMT48L2JvZHk+PC9odG1sPg=="},
    ]
    actual_results = []
    async with client.session() as session:
        assert session._context.connector.limit == client.n_conn
        actual_results.append(await session.get(queries[0]))
        for future in session.iter(queries[1:]):
            try:
                result = await future
            except Exception as e:
                result = e
            actual_results.append(result)
        aiohttp_session = session._context
        assert not aiohttp_session.closed
    assert aiohttp_session.closed
    assert session._context is None

    with pytest.raises(RuntimeError):
        await session.get(queries[0])

    with pytest.raises(RuntimeError):
        session.iter(queries[1:])

    assert len(actual_results) == len(expected_results)
    for actual_result in actual_results:
        if isinstance(actual_result, Exception):
            assert Exception in expected_results
        else:
            assert actual_result in expected_results
