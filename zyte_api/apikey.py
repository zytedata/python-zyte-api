from __future__ import annotations

import os

from dotenv import dotenv_values, find_dotenv

from .constants import ENV_VARIABLE, ETH_ENV_VARIABLE


class NoApiKey(Exception):
    pass


def read_apikey_from_dotenv(dotenv_path: str | None = None) -> str | None:
    """Return the ``ZYTE_API_KEY`` value from a ``.env`` file, or None.

    The file at *dotenv_path* is used, or, when *dotenv_path* is None, the
    nearest ``.env`` file in the current working directory or its parents. Any
    other variables in the file are ignored, and the process environment is left
    untouched.
    """
    return dotenv_values(dotenv_path or find_dotenv(usecwd=True)).get(ENV_VARIABLE)


def read_dotenv_auth(dotenv_path: str | None = None) -> dict[str, str]:
    """Return Zyte API auth credentials found in a ``.env`` file.

    Reads ``ZYTE_API_KEY`` and ``ZYTE_API_ETH_KEY`` and returns a
    ``{var: value}`` dict with those that are set. Any other variables in the
    file are ignored, and the process environment is left untouched.

    The two credentials are looked up differently when *dotenv_path* is None:
    ``ZYTE_API_KEY`` comes from the nearest ``.env`` file in the current
    directory or its parents, while ``ZYTE_API_ETH_KEY`` is read *only* from a
    ``.env`` file in the current directory (parent directories are not searched,
    to limit the risk of loading a fund-controlling private key from an
    unrelated ``.env``). When *dotenv_path* is given, both are read from it.
    """
    auth: dict[str, str] = {}
    apikey = read_apikey_from_dotenv(dotenv_path)
    if apikey:
        auth[ENV_VARIABLE] = apikey
    # The Ethereum private key is never looked up in parent directories.
    eth_key = dotenv_values(dotenv_path or ".env").get(ETH_ENV_VARIABLE)
    if eth_key:
        auth[ETH_ENV_VARIABLE] = eth_key
    return auth


def get_apikey(key: str | None = None, *, dotenv_path: str | None = None) -> str:
    """Return the API key.

    If *key* is None, the key is read from the ``ZYTE_API_KEY`` environment
    variable, falling back to a ``ZYTE_API_KEY`` entry in a ``.env`` file
    (*dotenv_path*, or the nearest ``.env`` by default). The environment
    variable takes precedence, and the environment is never modified.
    """
    if key is not None:
        return key
    apikey = os.environ.get(ENV_VARIABLE) or read_apikey_from_dotenv(dotenv_path)
    if apikey:
        return apikey
    raise NoApiKey(
        f"API key not found. Please set the {ENV_VARIABLE} environment "
        f"variable or define it in a .env file."
    )
