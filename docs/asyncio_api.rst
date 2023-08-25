.. _`asyncio_api`:

===========
asyncio API
===========

Create an instance of the ``AsyncClient`` to use the asyncio client API.
You can use the method ``request_raw`` to perform individual requests:

.. code-block:: python

    import asyncio
    from zyte_api.aio.client import AsyncClient

    client = AsyncClient(api_key="YOUR_API_KEY")


    async def single_request(url):
        return await client.request_raw({"url": url, "browserHtml": True})


    response = asyncio.run(single_request("https://books.toscrape.com"))
    # Do something with the response…

.. tip:: You can skip the ``api_key`` parameter if you :ref:`use an environment
    variable instead <api-key>`.

There is also ``request_parallel_as_completed`` method, which allows
to process many URLs in parallel, using multiple connections:

.. code-block:: python

    import asyncio
    import json
    import sys

    from zyte_api.aio.client import AsyncClient, create_session
    from zyte_api.aio.errors import RequestError

    async def extract_from(urls, n_conn):
        client = AsyncClient(n_conn=n_conn)
        requests = [
            {"url": url, "browserHtml": True}
            for url in urls
        ]
        async with create_session(n_conn) as session:
            res_iter = client.request_parallel_as_completed(requests, session=session)
            for fut in res_iter:
                try:
                    res = await fut
                    # do something with a result, e.g.
                    print(json.dumps(res))
                except RequestError as e:
                    print(e, file=sys.stderr)
                    raise

    urls = ["https://toscrape.com", "https://books.toscrape.com"]
    asyncio.run(extract_from(urls, n_conn=15))

``request_parallel_as_completed`` is modelled after ``asyncio.as_completed``
(see https://docs.python.org/3/library/asyncio-task.html#asyncio.as_completed),
and actually uses it under the hood.

``request_parallel_as_completed`` and ``request_raw`` methods handle
throttling (http 429 errors) and network errors, retrying a request in
these cases.

CLI interface implementation (``zyte_api/__main__.py``) can serve
as an usage example.
