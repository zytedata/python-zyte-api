.. _`asyncio_api`:

===========
asyncio API
===========

Create an instance of the ``AsyncZyteAPI`` to use the asyncio client API.
You can use the method ``request_raw`` to perform individual requests:

.. code-block:: python

    import asyncio
    from zyte_api import AsyncZyteAPI

    client = AsyncZyteAPI(api_key="YOUR_API_KEY")


    async def single_request(url):
        return await client.get({"url": url, "browserHtml": True})


    response = asyncio.run(single_request("https://books.toscrape.com"))

.. tip:: You can skip the ``api_key`` parameter if you :ref:`use an environment
    variable instead <api-key>`.

There is also an ``iter`` method, which allows to process many URLs in
parallel, using multiple connections:

.. code-block:: python

    import asyncio
    import json
    import sys

    from zyte_api import AsyncZyteAPI
    from zyte_api.aio.errors import RequestError


    async def extract_from(urls, n_conn):
        client = AsyncZyteAPI(n_conn=n_conn)
        requests = [{"url": url, "browserHtml": True} for url in urls]
        async with client.session() as session:
            res_iter = session.iter(requests)
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

``iter`` yields results as they come, not necessarily in their original order.

``iter`` and ``get`` methods handle throttling (http 429 errors) and network
errors, retrying a request in these cases.
