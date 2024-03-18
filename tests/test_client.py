import pytest

from zyte_api.aio.client import AsyncZyteAPI
from zyte_api.utils import USER_AGENT


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
