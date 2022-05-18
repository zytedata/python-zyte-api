import re
from os.path import splitext

from .__version__ import __version__


def _guess_intype(file_name, lines):
    _, dot_extension = splitext(file_name)
    extension = dot_extension[1:]
    if extension in {"jl", "jsonl"}:
        return "jl"
    if extension == "txt":
        return "txt"

    if re.search(r'^\s*\{', lines[0]):
        return "jl"

    return "txt"


def user_agent(library):
    return 'python-zyte-api/{} {}/{}'.format(
        __version__,
        library.__name__,
        library.__version__)
