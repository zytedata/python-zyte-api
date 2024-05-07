import asyncio
import logging
from collections import Counter

from aiohttp import client_exceptions
from tenacity import (
    AsyncRetrying,
    RetryCallState,
    after_log,
    before_log,
    before_sleep_log,
    retry_base,
    retry_if_exception,
    stop_after_delay,
    wait_chain,
    wait_fixed,
    wait_random,
    wait_random_exponential,
)
from tenacity.stop import stop_base, stop_never

from ._errors import RequestError

logger = logging.getLogger(__name__)


_NETWORK_ERRORS = (
    asyncio.TimeoutError,  # could happen while reading the response body
    client_exceptions.ClientResponseError,
    client_exceptions.ClientOSError,
    client_exceptions.ServerConnectionError,
    client_exceptions.ServerDisconnectedError,
    client_exceptions.ServerTimeoutError,
    client_exceptions.ClientPayloadError,
    client_exceptions.ClientConnectorSSLError,
    client_exceptions.ClientConnectorError,
)


def _is_network_error(exc: BaseException) -> bool:
    if isinstance(exc, RequestError):
        # RequestError is ClientResponseError, which is in the
        # _NETWORK_ERRORS list, but it should be handled
        # separately.
        return False
    return isinstance(exc, _NETWORK_ERRORS)


def _is_throttling_error(exc: BaseException) -> bool:
    return isinstance(exc, RequestError) and exc.status in (429, 503)


def _is_temporary_download_error(exc: BaseException) -> bool:
    return isinstance(exc, RequestError) and exc.status == 520


class stop_on_count(stop_base):
    """Keep a call count with the specified counter name, and stop after the
    specified number os calls.

    Unlike stop_after_attempt, this callable does not take into account
    attempts for which a different stop callable was used.
    """

    def __init__(self, max_count: int, counter_name: str) -> None:
        self._max_count = max_count - 1
        self._counter_name = counter_name

    def __call__(self, retry_state: "RetryCallState") -> bool:
        if not hasattr(retry_state, "counter"):
            retry_state.counter = Counter()
        if retry_state.counter[self._counter_name] >= self._max_count:
            return True
        retry_state.counter[self._counter_name] += 1
        return False


class RetryFactory:
    """Factory class that builds the :class:`tenacity.AsyncRetrying` object
    that defines the :ref:`default retry policy <default-retry-policy>`.

    To create a custom retry policy, you can subclass this factory class,
    modify it as needed, and then call :meth:`build` on your subclass to get
    the corresponding :class:`tenacity.AsyncRetrying` object.

    For example, to increase the maximum number of attempts for :ref:`temporary
    download errors <zyte-api-temporary-download-errors>` from 4 (i.e. 3
    retries) to 10 (i.e. 9 retries):

    .. code-block:: python

        from tenacity import stop_after_attempt
        from zyte_api import RetryFactory


        class CustomRetryFactory(RetryFactory):
            temporary_download_error_stop = stop_after_attempt(10)


        CUSTOM_RETRY_POLICY = CustomRetryFactory().build()

    To retry :ref:`permanent download errors
    <zyte-api-permanent-download-errors>`, treating them the same as
    :ref:`temporary download errors <zyte-api-temporary-download-errors>`:

    .. code-block:: python

        from tenacity import RetryCallState, retry_if_exception, stop_after_attempt
        from zyte_api import RequestError, RetryFactory


        def is_permanent_download_error(exc: BaseException) -> bool:
            return isinstance(exc, RequestError) and exc.status == 521


        class CustomRetryFactory(RetryFactory):

            retry_condition = RetryFactory.retry_condition | retry_if_exception(
                is_permanent_download_error
            )

            def wait(self, retry_state: RetryCallState) -> float:
                if is_permanent_download_error(retry_state.outcome.exception()):
                    return self.temporary_download_error_wait(retry_state=retry_state)
                return super().wait(retry_state)

            def stop(self, retry_state: RetryCallState) -> bool:
                if is_permanent_download_error(retry_state.outcome.exception()):
                    return self.temporary_download_error_stop(retry_state)
                return super().stop(retry_state)


        CUSTOM_RETRY_POLICY = CustomRetryFactory().build()
    """

    retry_condition: retry_base = (
        retry_if_exception(_is_throttling_error)
        | retry_if_exception(_is_network_error)
        | retry_if_exception(_is_temporary_download_error)
    )
    # throttling
    throttling_wait = wait_chain(
        # always wait 20-40s first
        wait_fixed(20) + wait_random(0, 20),
        # wait 20-40s again
        wait_fixed(20) + wait_random(0, 20),
        # wait from 30 to 630s, with full jitter and exponentially
        # increasing max wait time
        wait_fixed(30) + wait_random_exponential(multiplier=1, max=600),
    )

    # connection errors, other client and server failures
    network_error_wait = (
        # wait from 3s to ~1m
        wait_random(3, 7)
        + wait_random_exponential(multiplier=1, max=55)
    )
    temporary_download_error_wait = network_error_wait
    throttling_stop = stop_never
    network_error_stop = stop_after_delay(15 * 60)
    temporary_download_error_stop = stop_on_count(4, "temporary_download_error")

    def wait(self, retry_state: RetryCallState) -> float:
        assert retry_state.outcome, "Unexpected empty outcome"
        exc = retry_state.outcome.exception()
        assert exc, "Unexpected empty exception"
        if _is_throttling_error(exc):
            return self.throttling_wait(retry_state=retry_state)
        if _is_network_error(exc):
            return self.network_error_wait(retry_state=retry_state)
        assert _is_temporary_download_error(exc)  # See retry_condition
        return self.temporary_download_error_wait(retry_state=retry_state)

    def stop(self, retry_state: RetryCallState) -> bool:
        assert retry_state.outcome, "Unexpected empty outcome"
        exc = retry_state.outcome.exception()
        assert exc, "Unexpected empty exception"
        if _is_throttling_error(exc):
            return self.throttling_stop(retry_state)
        if _is_network_error(exc):
            return self.network_error_stop(retry_state)
        assert _is_temporary_download_error(exc)  # See retry_condition
        return self.temporary_download_error_stop(retry_state)

    def reraise(self) -> bool:
        return True

    def build(self) -> AsyncRetrying:
        return AsyncRetrying(
            wait=self.wait,
            retry=self.retry_condition,
            stop=self.stop,
            reraise=self.reraise(),
            before=before_log(logger, logging.DEBUG),
            after=after_log(logger, logging.DEBUG),
            before_sleep=before_sleep_log(logger, logging.DEBUG),
        )


zyte_api_retrying: AsyncRetrying = RetryFactory().build()


def _maybe_temporary_error(exc: BaseException) -> bool:
    return (
        isinstance(exc, RequestError)
        and exc.status >= 500
        and exc.status not in {503, 520}
    )


class AggresiveRetryFactory(RetryFactory):
    """Alternative factory class that builds :data:`aggresive_retrying`.

    To create a custom retry policy based on :data:`aggresive_retrying`, you
    can subclass this factory class, modify it as needed, and then call
    :meth:`build` on your subclass to get the corresponding
    :class:`tenacity.AsyncRetrying` object.

    For example, to increase the maximum number of attempts for errors treated
    as temporary download errors by :data:`aggresive_retrying` from 16 (i.e.
    15 retries) to 32 (i.e. 31 retries):

    .. code-block:: python

        from tenacity import stop_after_attempt
        from zyte_api import AggresiveRetryFactory


        class CustomRetryFactory(AggresiveRetryFactory):
            temporary_download_error_stop = stop_after_attempt(32)


        CUSTOM_RETRY_POLICY = CustomRetryFactory().build()
    """

    retry_condition = RetryFactory.retry_condition | retry_if_exception(
        _maybe_temporary_error
    )

    temporary_download_error_stop = stop_on_count(8, "temporary_download_error")

    def stop(self, retry_state: RetryCallState) -> bool:
        assert retry_state.outcome, "Unexpected empty outcome"
        exc = retry_state.outcome.exception()
        assert exc, "Unexpected empty exception"
        if _maybe_temporary_error(exc):
            return self.temporary_download_error_stop(retry_state)
        return super().stop(retry_state)

    def wait(self, retry_state: RetryCallState) -> float:
        assert retry_state.outcome, "Unexpected empty outcome"
        exc = retry_state.outcome.exception()
        assert exc, "Unexpected empty exception"
        if _maybe_temporary_error(exc):
            return self.temporary_download_error_wait(retry_state=retry_state)
        return super().wait(retry_state)


aggresive_retrying = AggresiveRetryFactory().build()
