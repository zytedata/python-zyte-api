.. _api-key:

=======
API key
=======

.. include:: /../README.rst
   :start-after: key-get-start
   :end-before: key-get-end

It is recommended to configure your API key through an environment variable, so
that it can be picked by both the :ref:`command-line client <command_line>` and
the :ref:`Python client library <api>`:

-  On Windows:

   .. code-block:: shell

        > set ZYTE_API_KEY=YOUR_API_KEY

-  On macOS and Linux:

   .. code-block:: shell

        $ export ZYTE_API_KEY=YOUR_API_KEY

Instead of exporting the variable yourself, you can store it in a ``.env`` file
and let it be loaded automatically:

.. code-block:: shell
    :caption: .env

    ZYTE_API_KEY=YOUR_API_KEY

The nearest ``.env`` file is looked up in the current working directory and its
parent directories. Only the ``ZYTE_API_KEY`` variable is read from it; any
other variables are ignored, a ``ZYTE_API_KEY`` set in the environment takes
precedence over the file, and your environment is never modified.

To read a ``.env`` file from a different location, use the ``--dotenv-path``
switch of the :ref:`command-line client <command_line>`, or the ``dotenv_path``
parameter of the :ref:`Python client classes <api>`:

.. code-block:: shell

    zyte-api --dotenv-path /path/to/.env …

.. code-block:: python

    from zyte_api import ZyteAPI

    client = ZyteAPI(dotenv_path="/path/to/.env")

Alternatively, you may pass your API key to the clients directly:

-   To pass your API key directly to the command-line client, use the
    ``--api-key`` switch:

    .. code-block:: shell

        zyte-api --api-key YOUR_API_KEY …

-   To pass your API key directly to the Python client classes, use the
    ``api_key`` parameter when creating a client object:

    .. code-block:: python

        from zyte_api import ZyteAPI

        client = ZyteAPI(api_key="YOUR_API_KEY")

    .. code-block:: python

        from zyte_api import AsyncZyteAPI

        client = AsyncZyteAPI(api_key="YOUR_API_KEY")
