from __future__ import annotations

import functools
import time
from collections import Counter
from typing import Optional

import attr
from runstats import Statistics

from zyte_api.errors import ParsedError


def zero_on_division_error(meth):
    @functools.wraps(meth)
    def wrapper(*args, **kwargs):
        try:
            return meth(*args, **kwargs)
        except ZeroDivisionError:
            return 0

    return wrapper


class AggStats:
    def __init__(self):
        self.time_connect_stats = Statistics()
        self.time_total_stats = Statistics()

        self.n_success = 0  # number of successful results returned to the user
        self.n_fatal_errors = (
            0  # number of errors returned to the user, after all retries
        )

        self.n_attempts = (
            0  # total amount of requests made to Zyte API, including retries
        )
        self.n_429 = 0  # number of 429 (throttling) responses
        self.n_errors = 0  # number of errors, including errors which were retried
        self.n_402_req = 0  # requests for a 402 (payment required) response

        self.status_codes = Counter()
        self.exception_types = Counter()
        self.api_error_types = Counter()

    def __str__(self):
        return (
            f"conn:{self.time_connect_stats.mean():0.2f}s, "
            f"resp:{self.time_total_stats.mean():0.2f}s, "
            f"throttle:{self.throttle_ratio():.1%}, "
            f"err:{self.n_errors - self.n_fatal_errors}+{self.n_fatal_errors}({self.error_ratio():.1%}) | "
            f"success:{self.n_success}/{self.n_processed}({self.success_ratio():.1%})"
        )

    def summary(self):
        return (
            "\n"
            "Summary\n"
            "-------\n"
            f"Mean connection time:     {self.time_connect_stats.mean():0.2f}\n"
            f"Mean response time:       {self.time_total_stats.mean():0.2f}\n"
            f"Throttle ratio:           {self.throttle_ratio():0.1%}\n"
            f"Attempts:                 {self.n_attempts}\n"
            f"Errors:                   {self.error_ratio():0.1%}, fatal: {self.n_fatal_errors}, non fatal: {self.n_errors - self.n_fatal_errors}\n"
            f"Successful URLs:          {self.n_success} of {self.n_processed}\n"
            f"Success ratio:            {self.success_ratio():0.1%}\n"
        )

    @zero_on_division_error
    def throttle_ratio(self):
        return self.n_429 / self.n_attempts

    @zero_on_division_error
    def error_ratio(self):
        return self.n_errors / self.n_attempts

    @zero_on_division_error
    def success_ratio(self):
        return self.n_success / self.n_processed

    @property
    def n_processed(self):
        """Total number of processed URLs"""
        return self.n_success + self.n_fatal_errors


@attr.s
class ResponseStats:
    _start: float = attr.ib(repr=False)

    # Wait time, before this request is sent. Can be large in case of retries.
    time_delayed: Optional[float] = attr.ib(default=None)

    # Time between sending a request and having a connection established
    time_connect: Optional[float] = attr.ib(default=None)

    # Time to read & decode the response
    time_read: Optional[float] = attr.ib(default=None)

    # time to get an exception (usually, a network error)
    time_exception: Optional[float] = attr.ib(default=None)

    # Total time to process the response, excluding the wait time caused
    # by retries.
    time_total: Optional[float] = attr.ib(default=None)

    # HTTP status code
    status: Optional[int] = attr.ib(default=None)

    # error (parsed), in case of error response
    error: Optional[ParsedError] = attr.ib(default=None)

    # exception raised
    exception: Optional[Exception] = attr.ib(default=None)

    @classmethod
    def create(cls, start_global):
        start = time.perf_counter()
        return cls(
            start=start,
            time_delayed=start - start_global,
        )

    def record_connected(self, status: int, agg_stats: AggStats):
        self.status = status
        self.time_connect = time.perf_counter() - self._start
        agg_stats.time_connect_stats.push(self.time_connect)
        agg_stats.status_codes[self.status] += 1

    def record_read(self, agg_stats: AggStats | None = None):
        now = time.perf_counter()
        self.time_total = now - self._start
        self.time_read = self.time_total - (self.time_connect or 0)
        if agg_stats:
            agg_stats.time_total_stats.push(self.time_total)

    def record_exception(self, exception: Exception, agg_stats: AggStats):
        self.time_exception = time.perf_counter() - self._start
        self.exception = exception
        agg_stats.status_codes[0] += 1
        agg_stats.exception_types[exception.__class__] += 1

    def record_request_error(self, error_body: bytes, agg_stats: AggStats):
        self.error = ParsedError.from_body(error_body)

        if self.status == 429:  # XXX: status must be set already!
            agg_stats.n_429 += 1
        else:
            agg_stats.n_errors += 1

        agg_stats.api_error_types[self.error.type] += 1
