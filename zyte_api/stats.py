# -*- coding: utf-8 -*-
from typing import Optional
from collections import Counter
import functools
import time

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
        self.n_results = 0
        self.n_fatal_errors = 0

        self.n_attempts = 0
        self.n_429 = 0
        self.n_errors = 0

        self.n_input_queries = 0
        self.n_extracted_queries = 0  # Queries answered without any type of error
        self.n_query_responses = 0

        self.status_codes = Counter()
        self.exception_types = Counter()
        self.api_error_types = Counter()

    def __str__(self):
        return "conn:{:0.2f}s, resp:{:0.2f}s, throttle:{:.1%}, err:{}+{}({:.1%}) | success:{}/{}({:.1%})".format(
            self.time_connect_stats.mean(),
            self.time_total_stats.mean(),
            self.throttle_ratio(),
            self.n_errors - self.n_fatal_errors,
            self.n_fatal_errors,
            self.error_ratio(),
            self.n_extracted_queries,
            self.n_input_queries,
            self.success_ratio()
        )

    def summary(self):
        return (
            "\n" +
            "Summary\n" +
            "-------\n" +
            "Mean connection time:     {:0.2f}\n".format(self.time_connect_stats.mean()) +
            "Mean response time:       {:0.2f}\n".format(self.time_total_stats.mean()) +
            "Throttle ratio:           {:0.1%}\n".format(self.throttle_ratio()) +
            "Attempts:                 {}\n".format(self.n_attempts) +
            "Errors:                   {:0.1%}, fatal: {}, non fatal: {}\n".format(
                self.error_ratio(),
                self.n_fatal_errors,
                self.n_errors - self.n_fatal_errors) +
            "Successful URLs:          {} of {}\n".format(
                self.n_extracted_queries, self.n_input_queries) +
            "Success ratio:            {:0.1%}\n".format(self.success_ratio())
        )

    @zero_on_division_error
    def throttle_ratio(self):
        return self.n_429 / self.n_attempts

    @zero_on_division_error
    def error_ratio(self):
        return self.n_errors / self.n_attempts

    @zero_on_division_error
    def success_ratio(self):
        return self.n_extracted_queries / self.n_input_queries


@attr.s
class ResponseStats:
    _start = attr.ib(repr=False)  # type: float

    # Wait time, before this request is sent. Can be large in case of retries.
    time_delayed = attr.ib(default=None)  # type: Optional[float]

    # Time between sending a request and having a connection established
    time_connect = attr.ib(default=None)  # type: Optional[float]

    # Time to read & decode the response
    time_read = attr.ib(default=None)  # type: Optional[float]

    # time to get an exception (usually, a network error)
    time_exception = attr.ib(default=None)  # type: Optional[float]

    # Total time to process the response, excluding the wait time caused
    # by retries.
    time_total = attr.ib(default=None)  # type: Optional[float]

    # HTTP status code
    status = attr.ib(default=None)  # type: Optional[int]

    # error (parsed), in case of error response
    error = attr.ib(default=None)  # type: Optional[ParsedError]

    # exception raised
    exception = attr.ib(default=None)  # type: Optional[Exception]

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

    def record_read(self, agg_stats: Optional[AggStats] = None):
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
