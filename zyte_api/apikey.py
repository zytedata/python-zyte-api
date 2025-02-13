from __future__ import annotations

import os

from .constants import ENV_VARIABLE


class NoApiKey(Exception):
    pass


def get_apikey(key: str | None = None) -> str:
    """Return API key, probably loading it from an environment variable"""
    if key is not None:
        return key
    try:
        return os.environ[ENV_VARIABLE]
    except KeyError:
        raise NoApiKey(
            f"API key not found. Please set {ENV_VARIABLE} environment variable."
        ) from None
