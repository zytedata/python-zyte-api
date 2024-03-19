from .._async import AsyncZyteAPI
from .._utils import create_session  # noqa: F401


class AsyncClient(AsyncZyteAPI):
    request_raw = AsyncZyteAPI.get
    request_parallel_as_completed = AsyncZyteAPI.iter
