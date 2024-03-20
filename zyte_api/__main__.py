""" Basic command-line interface for Zyte API. """

import argparse
import asyncio
import json
import logging
import random
import sys

import tqdm
from tenacity import retry_if_exception

from zyte_api._async import AsyncZyteAPI
from zyte_api._retry import RetryFactory, _is_throttling_error
from zyte_api._utils import create_session
from zyte_api.constants import API_URL, ENV_VARIABLE
from zyte_api.utils import _guess_intype


class DontRetryErrorsFactory(RetryFactory):
    retry_condition = retry_if_exception(_is_throttling_error)


logger = logging.getLogger("zyte_api")

_UNSET = object()


async def run(
    queries,
    out,
    *,
    n_conn,
    stop_on_errors,
    api_url,
    api_key=None,
    retry_errors=True,
    store_errors=None,
):
    def write_output(content):
        json.dump(content, out, ensure_ascii=False)
        out.write("\n")
        out.flush()
        pbar.update()

    retrying = None if retry_errors else DontRetryErrorsFactory().build()
    client = AsyncZyteAPI(
        n_conn=n_conn, api_key=api_key, api_url=api_url, retrying=retrying
    )
    async with create_session(connection_pool_size=n_conn) as session:
        result_iter = client.iter(
            queries=queries,
            session=session,
        )
        pbar = tqdm.tqdm(
            smoothing=0, leave=True, total=len(queries), miniters=1, unit="url"
        )
        pbar.set_postfix_str(str(client.agg_stats))
        try:
            for fut in result_iter:
                try:
                    result = await fut
                except Exception as e:
                    if store_errors:
                        write_output(e.parsed.response_body.decode())

                    if stop_on_errors:
                        raise

                    logger.error(str(e))
                else:
                    write_output(result)
                finally:
                    pbar.set_postfix_str(str(client.agg_stats))
        finally:
            pbar.close()
    logger.info(client.agg_stats.summary())
    logger.info(f"\nAPI error types:\n{client.agg_stats.api_error_types.most_common()}")
    logger.info(f"\nStatus codes:\n{client.agg_stats.status_codes.most_common()}")
    logger.info(f"\nException types:\n{client.agg_stats.exception_types.most_common()}")


def read_input(input_fp, intype):
    assert intype in {"txt", "jl", _UNSET}
    lines = input_fp.readlines()
    if intype is _UNSET:
        intype = _guess_intype(input_fp.name, lines)
    if intype == "txt":
        urls = [u.strip() for u in lines if u.strip()]
        records = [{"url": url, "browserHtml": True} for url in urls]
    else:
        records = [json.loads(line.strip()) for line in lines if line.strip()]
    # Automatically replicating the url in echoData to being able to
    # to match URLs with content in the responses
    for record in records:
        record.setdefault("echoData", record.get("url"))
    return records


def _main(program_name="zyte-api"):
    """Process urls from input file through Zyte API"""
    p = argparse.ArgumentParser(
        prog=program_name,
        description="""
        Process input URLs from a file using Zyte API.
        """,
    )
    p.add_argument(
        "input",
        type=argparse.FileType("r", encoding="utf8"),
        help="Input file with urls, url per line by default. The "
        "Format can be changed using `--intype` argument.",
    )
    p.add_argument(
        "--intype",
        default=_UNSET,
        choices=["txt", "jl"],
        help="Type of the input file. "
        "Allowed values are 'txt' (1 URL per line) and 'jl' "
        "(JSON Lines file, each object describing the "
        "parameters of a request). "
        "If not specified, the input type is guessed based on "
        "the input file name extension (.jl, .jsonl, .txt) or "
        "content, and assumed to be txt if guessing fails.",
    )
    p.add_argument(
        "--limit", type=int, help="Max number of URLs to take from the input"
    )
    p.add_argument(
        "--output",
        "-o",
        default=sys.stdout,
        type=argparse.FileType("w", encoding="utf8"),
        help=".jsonlines file to store extracted data. "
        "By default, results are printed to stdout.",
    )
    p.add_argument(
        "--n-conn",
        type=int,
        default=20,
        help="number of connections to the API server " "(default: %(default)s)",
    )
    p.add_argument(
        "--api-key",
        help="Zyte API key. "
        "You can also set %s environment variable instead "
        "of using this option." % ENV_VARIABLE,
    )
    p.add_argument(
        "--api-url", help="Zyte API endpoint (default: %(default)s)", default=API_URL
    )
    p.add_argument(
        "--loglevel",
        "-L",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="log level (default: %(default)s)",
    )
    p.add_argument("--shuffle", help="Shuffle input URLs", action="store_true")
    p.add_argument(
        "--dont-retry-errors",
        help="Don't retry request and network errors",
        action="store_true",
    )
    p.add_argument(
        "--store-errors",
        help="when set to true, it includes all types of responses, and when set to false,"
        " it includes only error-free responses in the output.",
    )
    args = p.parse_args()
    logging.basicConfig(stream=sys.stderr, level=getattr(logging, args.loglevel))

    queries = read_input(args.input, args.intype)
    if args.shuffle:
        random.shuffle(queries)
    if args.limit:
        queries = queries[: args.limit]

    logger.info(
        f"Loaded {len(queries)} urls from {args.input.name}; shuffled: {args.shuffle}"
    )
    logger.info(f"Running Zyte API (connections: {args.n_conn})")

    loop = asyncio.get_event_loop()
    coro = run(
        queries,
        out=args.output,
        n_conn=args.n_conn,
        stop_on_errors=False,
        api_url=args.api_url,
        api_key=args.api_key,
        retry_errors=not args.dont_retry_errors,
        store_errors=args.store_errors,
    )
    loop.run_until_complete(coro)
    loop.close()


if __name__ == "__main__":
    _main(program_name="python -m zyte_api")
