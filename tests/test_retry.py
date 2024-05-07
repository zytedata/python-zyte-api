from collections import deque
from copy import copy

import pytest

from zyte_api import RequestError, aggresive_retrying, zyte_api_retrying


def test_deprecated_imports():
    from zyte_api import RetryFactory, zyte_api_retrying
    from zyte_api.aio.retry import RetryFactory as DeprecatedRetryFactory
    from zyte_api.aio.retry import zyte_api_retrying as deprecated_zyte_api_retrying

    assert RetryFactory is DeprecatedRetryFactory
    assert zyte_api_retrying is deprecated_zyte_api_retrying


def mock_request_error(*, status=200):
    return RequestError(
        history=None,
        request_info=None,
        response_content=None,
        status=status,
    )


# Number of times to test request errors that must be retried forever.
FOREVER_TIMES = 100


@pytest.mark.parametrize(
    ("retrying", "exceptions", "exhausted"),
    (
        *(
            (zyte_api_retrying, exceptions, exhausted)
            for exceptions, exhausted in (
                (
                    (mock_request_error(status=429),) * FOREVER_TIMES,
                    False,
                ),
                (
                    (mock_request_error(status=503),) * FOREVER_TIMES,
                    False,
                ),
                (
                    (mock_request_error(status=520),) * 3,
                    False,
                ),
                (
                    (mock_request_error(status=520),) * 4,
                    True,
                ),
                (
                    (
                        mock_request_error(status=429),
                        mock_request_error(status=429),
                        mock_request_error(status=520),
                    ),
                    False,
                ),
                (
                    (
                        mock_request_error(status=429),
                        mock_request_error(status=429),
                        mock_request_error(status=429),
                        mock_request_error(status=520),
                    ),
                    True,
                ),
            )
        ),
        *(
            (aggresive_retrying, exceptions, exhausted)
            for exceptions, exhausted in (
                (
                    (mock_request_error(status=429),) * FOREVER_TIMES,
                    False,
                ),
                (
                    (mock_request_error(status=503),) * FOREVER_TIMES,
                    False,
                ),
                (
                    (mock_request_error(status=520),) * 7,
                    False,
                ),
                (
                    (mock_request_error(status=520),) * 8,
                    True,
                ),
                (
                    (
                        *(mock_request_error(status=429),) * 6,
                        mock_request_error(status=520),
                    ),
                    False,
                ),
                (
                    (
                        *(mock_request_error(status=429),) * 7,
                        mock_request_error(status=520),
                    ),
                    True,
                ),
            )
        ),
    ),
)
@pytest.mark.asyncio
async def test_retrying_attempt_based_stop(retrying, exceptions, exhausted):
    """Test retry stops based on a number of attempts (as opposed to those
    based on time passed)."""
    last_exception = exceptions[-1]
    exceptions = deque(exceptions)

    def wait(retry_state):
        return 0.0

    retrying = copy(retrying)
    retrying.wait = wait

    async def run():
        try:
            exception = exceptions.popleft()
        except IndexError:
            return
        else:
            raise exception

    run = retrying.wraps(run)
    try:
        await run()
    except Exception as exception:
        assert exhausted
        assert exception == last_exception
    else:
        assert not exhausted
