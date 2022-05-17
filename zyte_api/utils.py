from .__version__ import __version__


def _to_lower_camel_case(snake_case_string):
    """Convert from snake case (foo_bar) to lower-case-initial camel case
    (fooBar)."""
    prefix, *rest = snake_case_string.split('_')
    return prefix + ''.join(part.title() for part in rest)


def user_agent(library):
    return 'python-zyte-api/{} {}/{}'.format(
        __version__,
        library.__name__,
        library.__version__)
