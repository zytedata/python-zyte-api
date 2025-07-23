.. _command_line:

===================
Command-line client
===================

Once you have :ref:`installed python-zyte-api <install>` and configured your
:ref:`API key <api-key>` or :ref:`Ethereum private key <x402>`, you can use the
``zyte-api`` command-line client.

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

    For each URL, a Zyte API request will be sent with
    :http:`request:browserHtml` set to ``True``.

-   A `JSON Lines <https://jsonlines.org/>`_ file with a object of :ref:`Zyte
    API request parameters <zapi-reference>` per line. For example:

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
:ref:`performance reasons <cli-optimize>` and, as a result, the order of
responses will probably not match the order of the source requests from the
:ref:`input file <input-file>`. If you need to match the output results to the
input requests, the best way is to use :http:`request:echoData`. By default,
``zyte-api`` fills :http:`request:echoData` with the input URL.


.. _cli-optimize:

Optimization
============

By default, ``zyte-api`` uses 20 concurrent connections for requests. Use the
``--n-conn`` switch to change that:

.. code-block:: shell

    zyte-api --n-conn 40 …

The ``--shuffle`` option can be useful if you target multiple websites and your
:ref:`input file <input-file>` is sorted by website, to randomize the request
order and hence distribute the load somewhat evenly:

.. code-block:: shell

    zyte-api urls.txt --shuffle …

For guidelines on how to choose the optimal ``--n-conn`` value for you, and
other optimization tips, see :ref:`zapi-optimize`.


Errors and retries
==================

``zyte-api`` automatically handles retries for :ref:`rate-limiting
<zapi-rate-limit>` and :ref:`unsuccessful
<zapi-unsuccessful-responses>` responses, as well as network errors,
following the :ref:`default retry policy <default-retry-policy>`.

Use ``--dont-retry-errors`` to disable the retrying of error responses, and
retrying only :ref:`rate-limiting responses <zapi-rate-limit>`:

.. code-block:: shell

    zyte-api --dont-retry-errors …

By default, errors are only logged in the standard error output (``stderr``).
If you want to include error responses in the output file, use
``--store-errors``:

.. code-block:: shell

    zyte-api --store-errors …


.. seealso:: :ref:`cli-ref`
