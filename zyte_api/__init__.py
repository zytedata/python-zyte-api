"""
Python client libraries and command line utilities for Zyte API
"""

from ._async import AsyncZyteAPI
from ._errors import RequestError
from ._retry import RetryFactory
from ._retry import zyte_api_retrying as _zyte_api_retrying
from ._sync import ZyteAPI
from .errors import ParsedError

# We re-define the variable here for Sphinx to pick the documentation.
#: :ref:`Default retry policy <default-retry-policy>`.
zyte_api_retrying = _zyte_api_retrying
