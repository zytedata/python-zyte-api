# -*- coding: utf-8 -*-
"""
Zyte Data Extraction retrying logic.

TODO: add sync support; only aio is supported at the moment.
TODO: Implement retry logic for temparary errors (520) using the proposed retry-after header.
"""
import asyncio
import logging

from aiohttp import client_exceptions
from tenacity import (
    wait_chain,
    wait_fixed,
    wait_random_exponential,
    wait_random,
    stop_after_attempt,
    stop_after_delay,
    retry_if_exception,
    RetryCallState,
    before_sleep_log,
    after_log, AsyncRetrying, before_log,
)
from tenacity.stop import stop_never

from .errors import RequestError


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


# def _is_temporary_download_error(exc: Exception) -> bool:
#     return isinstance(exc, RequestError) and exc.status == 520


class RetryFactory:
    """
    Build custom retry configuration
    """
    retry_condition = (
        retry_if_exception(_is_throttling_error) |
        retry_if_exception(_is_network_error)
        # retry_if_exception(_is_temporary_download_error)
    )
    # throttling
    throttling_wait = wait_chain(
        # always wait 20-40s first
        wait_fixed(20) + wait_random(0, 20),

        # wait 20-40s again
        wait_fixed(20) + wait_random(0, 20),

        # wait from 30 to 630s, with full jitter and exponentially
        # increasing max wait time
        wait_fixed(30) + wait_random_exponential(multiplier=1, max=600)
    )

    # connection errors, other client and server failures
    network_error_wait = (
        # wait from 3s to ~1m
        wait_random(3, 7) + wait_random_exponential(multiplier=1, max=55)
    )
    # temporary_download_error_wait = network_error_wait
    throttling_stop = stop_never
    network_error_stop = stop_after_delay(5 * 60)
    # temporary_download_error_stop = stop_after_delay(15 * 60)

    def wait(self, retry_state: RetryCallState) -> float:
        assert retry_state.outcome, "Unexpected empty outcome"
        exc = retry_state.outcome.exception()
        assert exc, "Unexpected empty exception"
        if _is_throttling_error(exc):
            return self.throttling_wait(retry_state=retry_state)
        elif _is_network_error(exc):
            return self.network_error_wait(retry_state=retry_state)
        # elif _is_temporary_download_error(exc):
        #     return self.temporary_download_error_wait(retry_state=retry_state)
        else:
            raise RuntimeError("Invalid retry state exception: %s" % exc)

    def stop(self, retry_state: RetryCallState) -> bool:
        assert retry_state.outcome, "Unexpected empty outcome"
        exc = retry_state.outcome.exception()
        assert exc, "Unexpected empty exception"
        if _is_throttling_error(exc):
            return self.throttling_stop(retry_state)
        elif _is_network_error(exc):
            return self.network_error_stop(retry_state)
        # elif _is_temporary_download_error(exc):
        #     return self.temporary_download_error_stop(retry_state)
        else:
            raise RuntimeError("Invalid retry state exception: %s" % exc)

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
