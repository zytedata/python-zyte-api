.. _api-ref:

=============
API reference
=============

.. module:: zyte_api

Sync API
========

.. autoclass:: ZyteAPI
    :members:


Async API
=========

.. autoclass:: AsyncZyteAPI
    :members:


Retries
=======

.. autodata:: zyte_api_retrying
    :no-value:

.. autodata:: aggresive_retrying
    :no-value:

.. autoclass:: RetryFactory

.. autoclass:: AggresiveRetryFactory


Errors
======

.. autoexception:: RequestError
    :members:

.. autoclass:: ParsedError
    :members:
