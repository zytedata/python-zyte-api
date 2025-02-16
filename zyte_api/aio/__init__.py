"""
Asyncio client for Zyte API
"""

from warnings import warn

warn(
    (
        "The zyte_api.aio module is deprecated. Replace "
        "zyte_api.aio.client.AsyncClient with zyte_api.AsyncZyteAPI (note "
        "that method names are different), zyte_api.aio.client.create_session "
        "with zyte_api.AsyncZyteAPI.session, zyte_api.aio.errors.RequestError "
        "with zyte_api.RequestError, zyte_api.aio.retry.RetryFactory with "
        "zyte_api.RetryFactory, and zyte_api.aio.retry.zyte_api_retrying with "
        "zyte_api.zyte_api_retrying."
    ),
    DeprecationWarning,
    stacklevel=2,
)
