import pytest

from zyte_api.aio.client import AsyncClient
from zyte_api.utils import USER_AGENT


@pytest.mark.parametrize(
    "user_agent,expected",
    (
        (
            None,
            USER_AGENT,
        ),
        (
            f'{USER_AGENT}, scrapy-zyte-api/0.11.1',
            f'{USER_AGENT}, scrapy-zyte-api/0.11.1',
        ),
    ),
)
def test_user_agent(user_agent, expected):
    client = AsyncClient(api_key='123', api_url='http:\\test', user_agent=user_agent)
    assert client.user_agent == expected
