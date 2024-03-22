from .._async import AsyncZyteAPI
from .._utils import deprecated_create_session as create_session  # noqa: F401


class AsyncClient(AsyncZyteAPI):
    request_raw = AsyncZyteAPI.get
    request_parallel_as_completed = AsyncZyteAPI.iter
