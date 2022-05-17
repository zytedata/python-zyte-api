.. _`command_line`:

======================
Command-line interface
======================

The most basic way to use the client is from a command line.
First, create a file with urls, an URL per line (e.g. ``urls.txt``).

Second, set ``ZYTE_API_KEY`` env variable with your
API key (you can also pass API key as ``--api-key`` script
argument).

Then run a script, to get the results:

.. code-block:: shell

    python -m zyte_api urls.txt --output res.jl

.. note::
    The results can be stored in an order which is different from the input
    order. If you need to match the output results to the input URLs, the
    best way is to use the ``echoData`` field (see below); it is passed through,
    and returned as-is in the ``echoData`` attribute. By default it will
    contain the input URL the content belongs to.

If you need more flexibility, you can customize the requests by creating
a JsonLines file with queries: a JSON object per line. You can pass any
`Zyte Data API`_ options there. For example, you could create the following
``requests.jsonl`` file:

.. code-block:: json

    {"url": "http://example.com", "browserHtml": true, "geolocation": "GB", "echoData": "homepage"}
    {"url": "http://example.com/foo", "browserHtml": true, "javascript": false}
    {"url": "http://example.com/bar", "browserHtml": true, "geolocation": "US"}

See `API docs`_ for a description of all supported parameters.

.. _API docs: https://docs.zyte.com/zyte-api/openapi.html
.. _Zyte Data API: https://docs.zyte.com/zyte-api/get-started.html

To get results for this ``requests.jsonl`` file, run:

.. code-block:: shell

    python -m zyte_api requests.jsonl --output res.jsonl

Processing speed
~~~~~~~~~~~~~~~~

Each API key has a limit on RPS. To get your URLs processed faster you can
increase the number concurrent connections.

Best options depend on the RPS limit and on websites you're extracting
data from. For example, if your API key has a limit of 3RPS, and average
response time you observe for your websites is 10s, then to get to these
3RPS you may set the number of concurrent connections to 30.

To set these options in the CLI, use the ``--n-conn`` argument:

.. code-block:: shell

    python -m zyte_api urls.txt --n-conn 30 --output res.jl

If too many requests are being processed in parallel, you'll be getting
throttling errors. They are handled by CLI automatically, but they make
extraction less efficient; please tune the concurrency options to
not hit the throttling errors (HTTP 429) often.

You may be also limited by the website speed. The Zyte Data API tries not to hit
any individual website too hard, but it could be better to limit this on
a client side as well. If you're extracting data from a single website,
it could make sense to decrease the amount of parallel requests; it can ensure
higher success ratio overall.

If you're extracting data from multiple websites, it makes sense to spread the
load across time: if you have websites A, B and C, don't send requests in
AAAABBBBCCCC order, send them in ABCABCABCABC order instead.

To do so, you can change the order of the queries in your input file.
Alternatively, you can pass ``--shuffle`` options; it randomly shuffles
input queries before sending them to the API:

.. code-block:: shell

    python -m zyte_api urls.txt --shuffle --output res.jl

Run ``python -m zyte_api --help`` to get description of all supported
options.
