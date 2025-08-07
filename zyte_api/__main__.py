"""Basic command-line interface for Zyte API."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import random
import sys
from warnings import warn

import tqdm
from tenacity import retry_if_exception

from zyte_api._async import AsyncZyteAPI
from zyte_api._errors import RequestError
from zyte_api._retry import RetryFactory, _is_throttling_error
from zyte_api._utils import create_session
from zyte_api.constants import API_URL
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
    stop_on_errors=_UNSET,
    api_url: str | None,
    api_key=None,
    retry_errors=True,
    store_errors=None,
    eth_key=None,
):
    if stop_on_errors is not _UNSET:
        warn(
            "The stop_on_errors parameter is deprecated.",
            DeprecationWarning,
            stacklevel=2,
        )
    else:
        stop_on_errors = False

    def write_output(content):
        json.dump(content, out, ensure_ascii=False)
        out.write("\n")
        out.flush()
        pbar.update()

    retrying = None if retry_errors else DontRetryErrorsFactory().build()
    auth_kwargs = {}
    if api_key:
        auth_kwargs["api_key"] = api_key
    elif eth_key:
        auth_kwargs["eth_key"] = eth_key
    client = AsyncZyteAPI(
        n_conn=n_conn, api_url=api_url, retrying=retrying, **auth_kwargs
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
                    if store_errors and isinstance(e, RequestError):
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
    if not lines:
        return []
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


def _get_argument_parser(program_name="zyte-api"):
    p = argparse.ArgumentParser(
        prog=program_name,
        description="Send Zyte API requests.",
    )
    p.add_argument(
        "INPUT",
        type=argparse.FileType("r", encoding="utf8"),
        help=(
            "Path to an input file (see 'Command-line client > Input file' in "
            "the docs for details)."
        ),
    )
    p.add_argument(
        "--intype",
        default=_UNSET,
        choices=["txt", "jl"],
        help=(
            "Type of the input file, either 'txt' (plain text) or 'jl' (JSON "
            "Lines).\n"
            "\n"
            "If not specified, the input type is guessed based on the input "
            "file extension ('.jl', '.jsonl', or '.txt'), or in its content, "
            "with 'txt' as fallback."
        ),
    )
    p.add_argument("--limit", type=int, help="Maximum number of requests to send.")
    p.add_argument(
        "--output",
        "-o",
        default=sys.stdout,
        type=argparse.FileType("w", encoding="utf8"),
        help=(
            "Path for the output file. Results are written into the output "
            "file in JSON Lines format.\n"
            "\n"
            "If not specified, results are printed to the standard output."
        ),
    )
    p.add_argument(
        "--n-conn",
        type=int,
        default=20,
        help=("Number of concurrent connections to use (default: %(default)s)."),
    )
    group = p.add_mutually_exclusive_group(required=False)
    group.add_argument(
        "--api-key",
        help=(
            "Zyte API key.\n"
            "\n"
            "If not specified, it is read from the ZYTE_API_KEY environment "
            "variable."
            "\n"
            "Cannot be combined with --eth-key."
        ),
    )
    group.add_argument(
        "--eth-key",
        help=(
            "Ethereum private key, as a hexadecimal string.\n"
            "\n"
            "If not specified, it is read from the ZYTE_API_ETH_KEY "
            "environment variable."
            "\n"
            "Cannot be combined with --api-key."
        ),
    )
    p.add_argument(
        "--api-url",
        help=(
            f"Zyte API endpoint (default: {API_URL}).\n"
            f"\n"
            f"Using an Ethereum private key, e.g. through --eth-key or "
            f"through the ZYTE_API_ETH_KEY environment variable, changes the "
            f"default API URL to https://api-x402.zyte.com/v1/.\n"
        ),
    )
    p.add_argument(
        "--loglevel",
        "-L",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Log level (default: %(default)s).",
    )
    p.add_argument(
        "--shuffle",
        help="Shuffle request order.",
        action="store_true",
    )
    p.add_argument(
        "--dont-retry-errors",
        help="Do not retry unsuccessful responses and network errors, only rate-limiting responses.",
        action="store_true",
    )
    p.add_argument(
        "--store-errors",
        help=(
            "Store error responses in the output file.\n"
            "\n"
            "If omitted, only successful responses are stored."
        ),
        action="store_true",
    )
    return p


def _main(program_name="zyte-api"):
    """Process urls from input file through Zyte API"""
    p = _get_argument_parser(program_name=program_name)
    args = p.parse_args()
    logging.basicConfig(stream=sys.stderr, level=getattr(logging, args.loglevel))

    queries = read_input(args.INPUT, args.intype)
    if not queries:
        print("No input queries found. Is the input file empty?", file=sys.stderr)
        sys.exit(-1)

    if args.shuffle:
        random.shuffle(queries)
    if args.limit:
        queries = queries[: args.limit]

    logger.info(
        f"Loaded {len(queries)} urls from {args.INPUT.name}; shuffled: {args.shuffle}"
    )
    logger.info(f"Running Zyte API (connections: {args.n_conn})")

    loop = asyncio.get_event_loop()
    coro = run(
        queries,
        out=args.output,
        n_conn=args.n_conn,
        api_url=args.api_url,
        api_key=args.api_key,
        eth_key=args.eth_key,
        retry_errors=not args.dont_retry_errors,
        store_errors=args.store_errors,
    )
    loop.run_until_complete(coro)
    loop.close()


if __name__ == "__main__":
    _main(program_name="python -m zyte_api")
