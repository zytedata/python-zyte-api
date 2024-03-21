.. _command_line:

======================
Command-line interface
======================

Once you have :ref:`installed python-zyte-api <install>` and :ref:`configured
your API key <api-key>`, you can use the ``zyte-api`` command-line client.

To use ``zyte-api``, pass an :ref:`input file <input-file>` as the first
parameter and specify an :ref:`output file <output-file>` with ``--output``.
For example:

.. code-block:: shell

    zyte-api urls.txt --output result.jsonl

.. _input-file:

Input file
==========

The input file can be either of the following:

-   A plain-text file with a list of target URLs, one per line. For example:

    .. code-block:: none

        https://books.toscrape.com
        https://quotes.toscrape.com

    For each URL, a Zyte API request will be sent with browserHtml_ set to
    ``True``.

    .. _browserHtml: https://docs.zyte.com/zyte-api/usage/reference.html#operation/extract/request/browserHtml

-   A `JSON Lines <https://jsonlines.org/>`_ file with a object of `Zyte API
    request parameters`_ per line. For example:

    .. _Zyte API request parameters: https://docs.zyte.com/zyte-api/usage/reference.html

    .. code-block:: json

        {"url": "https://a.example", "browserHtml": true, "geolocation": "GB"}
        {"url": "https://b.example", "httpResponseBody": true}
        {"url": "https://books.toscrape.com", "productNavigation": true}


.. _output-file:

Output file
===========

You can specify the path to an output file with the ``--output``/``-o`` switch.
If not specified, the output is printed on the standard output.

.. warning:: The output path is overwritten.

The output file is in `JSON Lines`_ format. Each line contains a JSON object
with a response from Zyte API.

By default, ``zyte-api`` uses multiple concurrent connections for
:ref:`performance reasons <cli-optimization>` and, as a result, the order of
responses will probably not match the order of the source requests from the
:ref:`input file <input-file>`. If you need to match the output results to the
input requests, the best way is to use echoData_. By default, ``zyte-api``
fills echoData_ with the input URL.

.. _echoData: https://docs.zyte.com/zyte-api/usage/reference.html#operation/extract/request/echoData


.. _cli-optimization:

Optimization
============

By default, ``zyte-api`` uses 20 concurrent connections for requests. Use the
``--n-conn`` switch yo change that:

.. code-block:: shell

    zyte-api --n-conn 40 …

Your ideal number of concurrent connections depends on your `account rate
limit`_ and on your target websites. For example, if your account rate limit is
500 requests per minute, and the average response time you observe for your
websites is 10s, then to reach your rate limit you may set the number of
concurrent connections to 84.

.. _account rate limit: https://docs.zyte.com/zyte-api/usage/errors.html#rate-limiting-responses

If too many requests are being processed in parallel, you will be getting many
`rate-limiting responses`_. ``zyte-api`` retries them automatically, but to
maximize efficiency, please use a number of concurrent connections that
minimizes the number of rate-limiting responses.

.. _rate-limiting responses: https://docs.zyte.com/zyte-api/usage/errors.html#rate-limiting-responses

For some websites, increasing concurrent connections will slow down their
responses and/or increase the ratio of `unsuccessful responses`_. Zyte API
does its best to prevent these issues, but if you notice this happening to you,
please consider decreasing your concurrent connections.

.. _unsuccessful responses: https://docs.zyte.com/zyte-api/usage/errors.html#unsuccessful-responses

If you target multiple websites, consider sorting your :ref:`input requests
<input-file>` to spread the load. That is, if you have websites A, B, and C, do
not send requests in AAABBBCCC order, send them in ABCABCABC order instead.
Alternatively, use the ``--shuffle`` option to send requests in random order:

.. code-block:: shell

    zyte-api urls.txt --shuffle …


.. seealso:: :ref:`cli-ref`