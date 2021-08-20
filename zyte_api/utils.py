# -*- coding: utf-8 -*-
from .__version__ import __version__


def user_agent(library):
    return 'python-zyte-api/{} {}/{}'.format(
        __version__,
        library.__name__,
        library.__version__)
