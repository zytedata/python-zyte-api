from __future__ import annotations

import asyncio
import logging
from collections import Counter
from datetime import timedelta
from itertools import count
from typing import Callable, Union
from warnings import warn

from aiohttp import client_exceptions
from tenacity import (
    AsyncRetrying,
    RetryCallState,
    after_log,
    before_log,
    before_sleep_log,
    retry_base,
    retry_if_exception,
    wait_chain,
    wait_fixed,
    wait_none,
    wait_random,
    wait_random_exponential,
)
from tenacity.stop import stop_base, stop_never

from ._errors import RequestError

logger = logging.getLogger(__name__)

_IDS = count()


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


class stop_on_count(stop_base):
    """Keep a call count with the specified counter name, and stop after the
    specified number os calls.

    Unlike stop_after_attempt, this callable does not take into account
    attempts for which a different stop callable was used.
    """

    def __init__(self, max_count: int) -> None:
        self._max_count = max_count
        self._counter_id = next(_IDS)

    def __call__(self, retry_state: RetryCallState) -> bool:
        if not hasattr(retry_state, "counter"):
            retry_state.counter = Counter()  # type: ignore[attr-defined]
        retry_state.counter[self._counter_id] += 1  # type: ignore[attr-defined]
        return retry_state.counter[self._counter_id] >= self._max_count  # type: ignore[attr-defined]


time_unit_type = Union[int, float, timedelta]


def to_seconds(time_unit: time_unit_type) -> float:
    return float(
        time_unit.total_seconds() if isinstance(time_unit, timedelta) else time_unit
    )


class stop_after_uninterrupted_delay(stop_base):
    """Stop when this stop callable has been called for the specified time
    uninterrupted, i.e. without calls to different stop callables.

    Unlike stop_after_delay, this callable resets its timer after any attempt
    for which a different stop callable was used.
    """

    def __init__(self, max_delay: time_unit_type) -> None:
        self._max_delay = to_seconds(max_delay)
        self._timer_id = next(_IDS)

    def __call__(self, retry_state: RetryCallState) -> bool:
        if not hasattr(retry_state, "uninterrupted_start_times"):
            retry_state.uninterrupted_start_times = {}  # type: ignore[attr-defined]
        if self._timer_id not in retry_state.uninterrupted_start_times:  # type: ignore[attr-defined]
            # First time.
            retry_state.uninterrupted_start_times[self._timer_id] = [  # type: ignore[attr-defined]
                retry_state.attempt_number,
                retry_state.outcome_timestamp,
            ]
            return False
        attempt_number, start_time = retry_state.uninterrupted_start_times[  # type: ignore[attr-defined]
            self._timer_id
        ]
        if retry_state.attempt_number - attempt_number > 1:
            # There was a different stop reason since the last attempt,
            # resetting the timer.
            retry_state.uninterrupted_start_times[self._timer_id] = [  # type: ignore[attr-defined]
                retry_state.attempt_number,
                retry_state.outcome_timestamp,
            ]
            return False
        if retry_state.outcome_timestamp - start_time < self._max_delay:
            # Within time, do not stop, only increase the attempt count.
            retry_state.uninterrupted_start_times[self._timer_id][0] += 1  # type: ignore[attr-defined]
            return False
        return True


class stop_on_download_error(stop_base):
    """Stop after the specified max numbers of total or permanent download
    errors."""

    def __init__(self, max_total: int, max_permanent: int) -> None:
        self._max_total = max_total
        self._max_permanent = max_permanent

    def __call__(self, retry_state: RetryCallState) -> bool:
        if not hasattr(retry_state, "counter"):
            retry_state.counter = Counter()  # type: ignore[attr-defined]
        assert retry_state.outcome, "Unexpected empty outcome"
        exc = retry_state.outcome.exception()
        assert exc, "Unexpected empty exception"
        if exc.status == 521:  # type: ignore[attr-defined]
            retry_state.counter["permanent_download_error"] += 1  # type: ignore[attr-defined]
            if retry_state.counter["permanent_download_error"] >= self._max_permanent:  # type: ignore[attr-defined]
                return True
        retry_state.counter["download_error"] += 1  # type: ignore[attr-defined]
        return retry_state.counter["download_error"] >= self._max_total  # type: ignore[attr-defined]


def _download_error(exc: BaseException) -> bool:
    return isinstance(exc, RequestError) and exc.status in {520, 521}


def _undocumented_error(exc: BaseException) -> bool:
    return (
        isinstance(exc, RequestError)
        and exc.status >= 500
        and exc.status not in {503, 520, 521}
    )


def _402_error(exc: BaseException) -> bool:
    return isinstance(exc, RequestError) and exc.status == 402


def _deprecated(message: str, callable: Callable) -> Callable:
    def wrapper(factory, retry_state: RetryCallState):
        warn(message, DeprecationWarning, stacklevel=3)
        return callable(retry_state=retry_state)

    return wrapper


class RetryFactory:
    """Factory class that builds the :class:`tenacity.AsyncRetrying` object
    that defines the :ref:`default retry policy <default-retry-policy>`.

    To create a custom retry policy, you can subclass this factory class,
    modify it as needed, and then call :meth:`build` on your subclass to get
    the corresponding :class:`tenacity.AsyncRetrying` object.

    For example, to double the number of attempts for download errors and the
    time network errors are retried:

    .. code-block:: python

        from zyte_api import (
            RetryFactory,
            stop_after_uninterrupted_delay,
            stop_on_download_error,
        )


        class CustomRetryFactory(RetryFactory):
            network_error_stop = stop_after_uninterrupted_delay(30 * 60)
            download_error_stop = stop_on_download_error(max_total=8, max_permanent=4)


        CUSTOM_RETRY_POLICY = CustomRetryFactory().build()
    """

    retry_condition: retry_base = (
        retry_if_exception(_is_throttling_error)
        | retry_if_exception(_is_network_error)
        | retry_if_exception(_download_error)
        | retry_if_exception(_undocumented_error)
        | retry_if_exception(_402_error)
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
    network_error_stop = stop_after_uninterrupted_delay(15 * 60)
    network_error_wait = (
        # wait from 3s to ~1m
        wait_random(3, 7) + wait_random_exponential(multiplier=1, max=55)
    )

    download_error_stop = stop_on_download_error(max_total=4, max_permanent=2)
    download_error_wait = network_error_wait

    temporary_download_error_stop = _deprecated(
        (
            "The zyte_api.RetryFactory.temporary_download_error_stop() method "
            "is deprecated and will be removed in a future version. Use "
            "download_error_stop() instead."
        ),
        download_error_stop,
    )
    temporary_download_error_wait = _deprecated(
        (
            "The zyte_api.RetryFactory.temporary_download_error_wait() method "
            "is deprecated and will be removed in a future version. Use "
            "download_error_wait() instead."
        ),
        download_error_wait,
    )

    throttling_stop = stop_never

    undocumented_error_stop = stop_on_count(2)
    undocumented_error_wait = network_error_wait

    x402_error_stop = stop_on_count(2)
    x402_error_wait = wait_none()

    def wait(self, retry_state: RetryCallState) -> float:
        assert retry_state.outcome, "Unexpected empty outcome"
        exc = retry_state.outcome.exception()
        assert exc, "Unexpected empty exception"
        if _is_throttling_error(exc):
            return self.throttling_wait(retry_state=retry_state)
        if _is_network_error(exc):
            return self.network_error_wait(retry_state=retry_state)
        if _undocumented_error(exc):
            return self.undocumented_error_wait(retry_state=retry_state)
        if _402_error(exc):
            return self.x402_error_wait(retry_state=retry_state)
        assert _download_error(exc)  # See retry_condition
        return self.download_error_wait(retry_state=retry_state)

    def stop(self, retry_state: RetryCallState) -> bool:
        assert retry_state.outcome, "Unexpected empty outcome"
        exc = retry_state.outcome.exception()
        assert exc, "Unexpected empty exception"
        if _is_throttling_error(exc):
            return self.throttling_stop(retry_state)
        if _is_network_error(exc):
            return self.network_error_stop(retry_state)
        if _undocumented_error(exc):
            return self.undocumented_error_stop(retry_state)
        if _402_error(exc):
            return self.x402_error_stop(retry_state)
        assert _download_error(exc)  # See retry_condition
        return self.download_error_stop(retry_state)

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


class AggressiveRetryFactory(RetryFactory):
    """Factory class that builds the :class:`tenacity.AsyncRetrying` object
    that defines the :ref:`aggressive retry policy <aggressive-retry-policy>`.

    To create a custom retry policy, you can subclass this factory class,
    modify it as needed, and then call :meth:`build` on your subclass to get
    the corresponding :class:`tenacity.AsyncRetrying` object.

    For example, to double the maximum number of attempts for all error
    responses and double the time network errors are retried:

    .. code-block:: python

        from zyte_api import (
            AggressiveRetryFactory,
            stop_after_uninterrupted_delay,
            stop_on_count,
            stop_on_download_error,
        )


        class CustomRetryFactory(AggressiveRetryFactory):
            download_error_stop = stop_on_download_error(max_total=16, max_permanent=8)
            network_error_stop = stop_after_uninterrupted_delay(30 * 60)
            undocumented_error_stop = stop_on_count(8)


        CUSTOM_RETRY_POLICY = CustomRetryFactory().build()
    """

    download_error_stop = stop_on_download_error(max_total=8, max_permanent=4)
    undocumented_error_stop = stop_on_count(4)


aggressive_retrying = AggressiveRetryFactory().build()
