"""
Python client libraries and command line utilities for Zyte API
"""

from ._async import AsyncZyteAPI
from ._errors import RequestError
from ._retry import ConservativeRetryFactory, RetryFactory
from ._retry import conservative_retrying as _conservative_retrying
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
conservative_retrying = _conservative_retrying
