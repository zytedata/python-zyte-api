from collections import deque
from copy import copy
from unittest.mock import patch

import pytest
from aiohttp.client_exceptions import ServerConnectionError
from tenacity import AsyncRetrying, RetryCallState

from zyte_api import (
    AggressiveRetryFactory,
    AsyncZyteAPI,
    RequestError,
    RetryFactory,
    aggressive_retrying,
    zyte_api_retrying,
)

from .mockserver import DropResource, MockServer


def test_deprecated_imports():
    from zyte_api import RetryFactory, zyte_api_retrying
    from zyte_api.aio.retry import RetryFactory as DeprecatedRetryFactory
    from zyte_api.aio.retry import zyte_api_retrying as deprecated_zyte_api_retrying

    assert RetryFactory is DeprecatedRetryFactory
    assert zyte_api_retrying is deprecated_zyte_api_retrying


UNSET = object()


class OutlierException(RuntimeError):
    pass


@pytest.mark.parametrize(
    ("value", "exception"),
    (
        (UNSET, OutlierException),
        (True, OutlierException),
        (False, RequestError),
    ),
)
@pytest.mark.asyncio
async def test_get_handle_retries(value, exception, mockserver):
    kwargs = {}
    if value is not UNSET:
        kwargs["handle_retries"] = value

    def broken_stop(_):
        raise OutlierException

    retrying = AsyncRetrying(stop=broken_stop)
    client = AsyncZyteAPI(
        api_key="a", api_url=mockserver.urljoin("/"), retrying=retrying
    )
    with pytest.raises(exception):
        await client.get(
            {"url": "https://exception.example", "browserHtml": True},
            **kwargs,
        )


@pytest.mark.parametrize(
    ("retry_factory", "status", "waiter"),
    (
        (RetryFactory, 429, "throttling"),
        (RetryFactory, 520, "download_error"),
        (AggressiveRetryFactory, 429, "throttling"),
        (AggressiveRetryFactory, 500, "undocumented_error"),
        (AggressiveRetryFactory, 520, "download_error"),
    ),
)
@pytest.mark.asyncio
async def test_retry_wait(retry_factory, status, waiter, mockserver):
    def broken_wait(self, retry_state):
        raise OutlierException

    class CustomRetryFactory(retry_factory):
        pass

    setattr(CustomRetryFactory, f"{waiter}_wait", broken_wait)
    retrying = CustomRetryFactory().build()
    client = AsyncZyteAPI(
        api_key="a", api_url=mockserver.urljoin("/"), retrying=retrying
    )
    with pytest.raises(OutlierException):
        await client.get(
            {"url": f"https://e{status}.example", "browserHtml": True},
        )


@pytest.mark.parametrize(
    "retry_factory",
    (
        RetryFactory,
        AggressiveRetryFactory,
    ),
)
@pytest.mark.asyncio
async def test_retry_wait_network_error(retry_factory):
    waiter = "network_error"

    def broken_wait(self, retry_state):
        raise OutlierException

    class CustomRetryFactory(retry_factory):
        pass

    setattr(CustomRetryFactory, f"{waiter}_wait", broken_wait)

    retrying = CustomRetryFactory().build()
    with MockServer(resource=DropResource) as mockserver:
        client = AsyncZyteAPI(
            api_key="a", api_url=mockserver.urljoin("/"), retrying=retrying
        )
        with pytest.raises(OutlierException):
            await client.get(
                {"url": "https://example.com", "browserHtml": True},
            )


def mock_request_error(*, status=200):
    return RequestError(
        history=None,
        request_info=None,
        response_content=None,
        status=status,
        query={},
    )


# Number of times to test request errors that must be retried forever.
FOREVER_TIMES = 100


class fast_forward:
    def __init__(self, time):
        self.time = time


class scale:
    def __init__(self, factor):
        self.factor = factor

    def __call__(self, number, add=0):
        return int(number * self.factor) + add


@pytest.mark.parametrize(
    ("retrying", "outcomes", "exhausted"),
    (
        # Shared behaviors of all retry policies
        *(
            (retrying, outcomes, exhausted)
            for retrying in (zyte_api_retrying, aggressive_retrying)
            for outcomes, exhausted in (
                # Rate limiting is retried forever.
                (
                    (mock_request_error(status=429),) * FOREVER_TIMES,
                    False,
                ),
                (
                    (mock_request_error(status=503),) * FOREVER_TIMES,
                    False,
                ),
                # Network errors are retried until there have only been network
                # errors (of any kind) for 15 minutes straight or more.
                (
                    (
                        ServerConnectionError(),
                        fast_forward(15 * 60 - 1),
                        ServerConnectionError(),
                    ),
                    False,
                ),
                (
                    (
                        ServerConnectionError(),
                        fast_forward(15 * 60),
                        ServerConnectionError(),
                    ),
                    True,
                ),
                (
                    (
                        mock_request_error(status=429),
                        fast_forward(15 * 60 - 1),
                        ServerConnectionError(),
                    ),
                    False,
                ),
                (
                    (
                        mock_request_error(status=429),
                        fast_forward(15 * 60),
                        ServerConnectionError(),
                    ),
                    False,
                ),
                (
                    (
                        ServerConnectionError(),
                        fast_forward(7 * 60),
                        mock_request_error(status=429),
                        fast_forward(8 * 60 - 1),
                        ServerConnectionError(),
                    ),
                    False,
                ),
                (
                    (
                        ServerConnectionError(),
                        fast_forward(7 * 60),
                        mock_request_error(status=429),
                        fast_forward(8 * 60),
                        ServerConnectionError(),
                    ),
                    False,
                ),
                (
                    (
                        ServerConnectionError(),
                        fast_forward(7 * 60),
                        mock_request_error(status=429),
                        fast_forward(8 * 60),
                        ServerConnectionError(),
                        fast_forward(15 * 60 - 1),
                        ServerConnectionError(),
                    ),
                    False,
                ),
                (
                    (
                        ServerConnectionError(),
                        fast_forward(7 * 60),
                        mock_request_error(status=429),
                        fast_forward(8 * 60),
                        ServerConnectionError(),
                        fast_forward(15 * 60),
                        ServerConnectionError(),
                    ),
                    True,
                ),
            )
        ),
        # Scaled behaviors, where the default retry policy uses half as many
        # attempts as the aggressive retry policy.
        *(
            (retrying, outcomes, exhausted)
            for retrying, scaled in (
                (zyte_api_retrying, scale(0.5)),
                (aggressive_retrying, scale(1)),
            )
            for outcomes, exhausted in (
                # Temporary download errors are retried until they have
                # happened 8*factor times in total. Permanent download errors
                # also count towards that limit.
                (
                    (mock_request_error(status=520),) * scaled(8, -1),
                    False,
                ),
                (
                    (mock_request_error(status=520),) * scaled(8),
                    True,
                ),
                (
                    (
                        *(mock_request_error(status=429),) * scaled(8, -2),
                        mock_request_error(status=520),
                    ),
                    False,
                ),
                (
                    (
                        *(mock_request_error(status=429),) * scaled(8, -1),
                        mock_request_error(status=520),
                    ),
                    False,
                ),
                (
                    (
                        *(
                            mock_request_error(status=429),
                            mock_request_error(status=520),
                        )
                        * scaled(8, -1),
                    ),
                    False,
                ),
                (
                    (
                        *(
                            mock_request_error(status=429),
                            mock_request_error(status=520),
                        )
                        * scaled(8),
                    ),
                    True,
                ),
                (
                    (
                        *(mock_request_error(status=520),) * scaled(8, -3),
                        *(mock_request_error(status=521),) * 1,
                        *(mock_request_error(status=520),) * 1,
                    ),
                    False,
                ),
                (
                    (
                        *(mock_request_error(status=520),) * scaled(8, -2),
                        *(mock_request_error(status=521),) * 1,
                        *(mock_request_error(status=520),) * 1,
                    ),
                    True,
                ),
                (
                    (
                        *(mock_request_error(status=520),) * scaled(8, -2),
                        *(mock_request_error(status=521),) * 1,
                    ),
                    False,
                ),
                (
                    (
                        *(mock_request_error(status=520),) * scaled(8, -1),
                        *(mock_request_error(status=521),) * 1,
                    ),
                    True,
                ),
                # Permanent download errors are retried until they have
                # happened 4*factor times in total.
                (
                    (*(mock_request_error(status=521),) * scaled(4, -1),),
                    False,
                ),
                (
                    (*(mock_request_error(status=521),) * scaled(4),),
                    True,
                ),
                # Undocumented 5xx errors are retried until they have happened
                # 4*factor times.
                *(
                    scenario
                    for status in (
                        500,
                        502,
                        504,
                    )
                    for scenario in (
                        (
                            (*(mock_request_error(status=status),) * scaled(4, -1),),
                            False,
                        ),
                        (
                            (*(mock_request_error(status=status),) * scaled(4),),
                            True,
                        ),
                        (
                            (
                                *(mock_request_error(status=status),) * scaled(4, -2),
                                mock_request_error(status=429),
                                mock_request_error(status=503),
                                ServerConnectionError(),
                                mock_request_error(status=status),
                            ),
                            False,
                        ),
                        (
                            (
                                *(mock_request_error(status=status),) * scaled(4, -1),
                                mock_request_error(status=429),
                                mock_request_error(status=503),
                                ServerConnectionError(),
                                mock_request_error(status=status),
                            ),
                            True,
                        ),
                        (
                            (
                                mock_request_error(status=555),
                                *(mock_request_error(status=status),) * scaled(4, -2),
                            ),
                            False,
                        ),
                        (
                            (
                                mock_request_error(status=555),
                                *(mock_request_error(status=status),) * scaled(4, -1),
                            ),
                            True,
                        ),
                    )
                ),
            )
        ),
    ),
)
@pytest.mark.asyncio
@patch("time.monotonic")
async def test_retry_stop(monotonic_mock, retrying, outcomes, exhausted):
    monotonic_mock.return_value = 0
    last_outcome = outcomes[-1]
    outcomes = deque(outcomes)

    def wait(retry_state):
        return 0.0

    retrying = copy(retrying)
    retrying.wait = wait

    async def run():
        while True:
            try:
                outcome = outcomes.popleft()
            except IndexError:
                return
            else:
                if isinstance(outcome, fast_forward):
                    monotonic_mock.return_value += outcome.time
                    continue
                raise outcome

    run = retrying.wraps(run)
    try:
        await run()
    except Exception as outcome:
        assert exhausted, outcome  # noqa: PT017
        assert outcome is last_outcome  # noqa: PT017
    else:
        assert not exhausted


@pytest.mark.asyncio
async def test_deprecated_temporary_download_error():
    class CustomRetryFactory(RetryFactory):
        def wait(self, retry_state: RetryCallState) -> float:
            self.temporary_download_error_wait(retry_state=retry_state)
            return 0.0

        def stop(self, retry_state: RetryCallState) -> bool:
            self.temporary_download_error_stop(retry_state)
            return super().stop(retry_state)

    retrying = CustomRetryFactory().build()

    outcomes = deque((mock_request_error(status=520), None))

    async def run():
        outcome = outcomes.popleft()
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    run = retrying.wraps(run)
    with (
        pytest.warns(DeprecationWarning, match="temporary_download_error_stop"),
        pytest.warns(DeprecationWarning, match="temporary_download_error_wait"),
    ):
        await run()
    assert not outcomes
