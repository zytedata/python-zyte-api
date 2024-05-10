"""
Python client libraries and command line utilities for Zyte API
"""

from ._async import AsyncZyteAPI
from ._errors import RequestError
from ._retry import AggressiveRetryFactory, RetryFactory
from ._retry import aggressive_retrying as _aggressive_retrying
from ._retry import (
    stop_after_uninterrupted_delay,
    stop_on_count,
    stop_on_download_error,
    stop_on_uninterrupted_status,
)
from ._retry import zyte_api_retrying as _zyte_api_retrying
from ._sync import ZyteAPI
from .errors import ParsedError

# We re-define the variables here for Sphinx to pick the documentation.

#: :ref:`Default retry policy <default-retry-policy>`.
zyte_api_retrying = _zyte_api_retrying

#: Alternative :ref:`retry policy <retry-policy>` that builds on top of
#: :data:`zyte_api_retrying`, but increases the number of attempts for
#: temporary download errors from 4 to 16, and retries as temporary download
#: errors any 5xx HTTP status code other than 503 (retried as rate-limiting).
aggressive_retrying = _aggressive_retrying
