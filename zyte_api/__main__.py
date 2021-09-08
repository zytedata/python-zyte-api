# -*- coding: utf-8 -*-
""" Basic command-line interface for Zyte Data APIs. """
import argparse
import json
import sys
import asyncio
import logging
import random

import tqdm

from zyte_api.aio.client import (
    create_session,
    AsyncClient
)
from zyte_api.constants import ENV_VARIABLE


logger = logging.getLogger('zyte_api')
log_file = open("logs", "w")

async def run(queries, out, n_conn, stop_on_errors,
              api_key=None):

    client = AsyncClient(n_conn=n_conn, api_key=api_key)
    async with create_session(connection_pool_size=n_conn) as session:
        result_iter = client.request_parallel_as_completed(
            queries=queries,
            session=session,
        )
        pbar = tqdm.tqdm(smoothing=0, leave=True, total=len(queries), miniters=1,
                         unit="url")
        pbar.set_postfix_str(str(client.agg_stats))
        try:
            for fut in result_iter:
                try:
                    result = await fut
                    json.dump(result, out, ensure_ascii=False)
                    out.write("\n")
                    out.flush()
                    pbar.update()
                except Exception as e:
                    if stop_on_errors:
                        raise
                    logger.error(str(e))
                    log_file.write(str(e) + "\n")
                finally:
                    pbar.set_postfix_str(str(client.agg_stats))
        finally:
            pbar.close()
    logger.info(client.agg_stats.summary())
    logger.info(f"\nAPI error types:\n{client.agg_stats.api_error_types.most_common()}")
    logger.info(f"\nStatus codes:\n{client.agg_stats.status_codes.most_common()}")
    logger.info(f"\nException types:\n{client.agg_stats.exception_types.most_common()}")


def read_input(input_fp, intype):
    assert intype in {"txt", "jl", ""}
    if intype == "txt":
        urls = [u.strip() for u in input_fp.readlines() if u.strip()]
        return [{"url": url, "browserHtml": True} for url in urls]
    elif intype == "jl":
        records = [
            json.loads(line.strip())
            for line in input_fp.readlines() if line.strip()
        ]
        return records


if __name__ == '__main__':
    """ Process urls from input file through Zyte Data API """
    p = argparse.ArgumentParser(
        prog='python -m zyte_api',
        description="""
        Process input URLs from a file using Zyte Data API.
        """,
    )
    p.add_argument("input",
                   type=argparse.FileType("r", encoding='utf8'),
                   help="Input file with urls, url per line by default. The "
                        "Format can be changed using `--intype` argument.")
    p.add_argument("--intype", default="txt", choices=["txt", "jl"],
                   help='Type of the input file (default: %(default)s). '
                        'Allowed values are "txt": input should be one '
                        'URL per line, and "jl": input should be a jsonlines '
                        'file, with {"url": "...", ..} dicts')
    p.add_argument("--limit", type=int,
                   help="Max number of URLs to take from the input")
    p.add_argument("--output", "-o",
                   default=sys.stdout,
                   type=argparse.FileType("w", encoding='utf8'),
                   help=".jsonlines file to store extracted data. "
                        "By default, results are printed to stdout.")
    p.add_argument("--n-conn", type=int, default=20,
                   help="number of connections to the API server "
                        "(default: %(default)s)")
    p.add_argument("--api-key",
                   help="Zyte Data API key. "
                        "You can also set %s environment variable instead "
                        "of using this option." % ENV_VARIABLE)
    p.add_argument("--api-endpoint",
                   help="Zyte Data API endpoint.")
    p.add_argument("--loglevel", "-L", default="INFO",
                   choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                   help="log level")
    p.add_argument("--shuffle", help="Shuffle input URLs", action="store_true")
    args = p.parse_args()
    logging.basicConfig(
        stream=sys.stderr,
        level=getattr(logging, args.loglevel)
    )

    queries = read_input(args.input, args.intype)
    if args.shuffle:
        random.shuffle(queries)
    if args.limit:
        queries = queries[:args.limit]

    logger.info(f"Loaded {len(queries)} urls from {args.input.name}; shuffled: {args.shuffle}")
    logger.info(f"Running Zyte Data API (connections: {args.n_conn})")

    loop = asyncio.get_event_loop()
    coro = run(queries,
               out=args.output,
               n_conn=args.n_conn,
               stop_on_errors=False,
               api_key=args.api_key)
    loop.run_until_complete(coro)
    loop.close()
