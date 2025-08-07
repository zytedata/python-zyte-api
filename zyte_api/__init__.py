"""
Python client libraries and command line utilities for Zyte API
"""

from ._async import AsyncZyteAPI, AuthInfo
from ._errors import RequestError
from ._retry import (
    AggressiveRetryFactory,
    RetryFactory,
    stop_after_uninterrupted_delay,
    stop_on_count,
    stop_on_download_error,
)
from ._retry import aggressive_retrying as _aggressive_retrying
from ._retry import zyte_api_retrying as _zyte_api_retrying
from ._sync import ZyteAPI
from .errors import ParsedError

# We re-define the variables here for Sphinx to pick the documentation.

#: :ref:`Default retry policy <default-retry-policy>`.
zyte_api_retrying = _zyte_api_retrying

#: :ref:`Aggresive retry policy <aggressive-retry-policy>`.
aggressive_retrying = _aggressive_retrying
