import argparse
import json
import socket
import sys
import time
from base64 import b64encode
from collections import defaultdict
from importlib import import_module
from subprocess import PIPE, Popen
from typing import Any
from urllib.parse import urlparse

from twisted.internet import reactor
from twisted.internet.task import deferLater
from twisted.web.resource import Resource
from twisted.web.server import NOT_DONE_YET, Site

SCREENSHOT = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAACklEQVR4nGMAAQAABQABDQott"
    "AAAAABJRU5ErkJggg=="
)


# https://github.com/scrapy/scrapy/blob/02b97f98e74a994ad3e4d74e7ed55207e508a576/tests/mockserver.py#L27C1-L33C19
def getarg(request, name, default=None, type=None):
    if name in request.args:
        value = request.args[name][0]
        if type is not None:
            value = type(value)
        return value
    return default


def get_ephemeral_port():
    s = socket.socket()
    s.bind(("", 0))
    return s.getsockname()[1]


class DropResource(Resource):
    isLeaf = True

    def deferRequest(self, request, delay, f, *a, **kw):
        def _cancelrequest(_):
            # silence CancelledError
            d.addErrback(lambda _: None)
            d.cancel()

        d = deferLater(reactor, delay, f, *a, **kw)
        request.notifyFinish().addErrback(_cancelrequest)
        return d

    def render_POST(self, request):
        request.setHeader(b"Content-Length", b"1024")
        self.deferRequest(request, 0, self._delayedRender, request)
        return NOT_DONE_YET

    def _delayedRender(self, request):
        abort = getarg(request, b"abort", 0, type=int)
        request.write(b"this connection will be dropped\n")
        tr = request.channel.transport
        try:
            if abort and hasattr(tr, "abortConnection"):
                tr.abortConnection()
            else:
                tr.loseConnection()
        finally:
            request.finish()


RESPONSE_402 = {
    "x402Version": 1,
    "accepts": [
        {
            "scheme": "exact",
            "network": "base-sepolia",
            "maxAmountRequired": "1000",
            "resource": "https://api.zyte.com/v1/extract",
            "description": "",
            "mimeType": "",
            "payTo": "0xFACEdD967ea0592bbb9410fA4877Df9AeB628CB7",
            "maxTimeoutSeconds": 130,
            "asset": "0xFACEbD53842c5426634e7929541eC2318f3dCF7e",
            "extra": {"name": "USDC", "version": "2"},
        }
    ],
    "error": "Use basic auth or x402",
}

WORKFLOWS: defaultdict[str, dict[str, Any]] = defaultdict(dict)


class DefaultResource(Resource):
    request_count = 0

    def getChild(self, path, request):
        return self

    def render_POST(self, request):
        request.responseHeaders.setRawHeaders(
            b"Content-Type",
            [b"application/json"],
        )
        request.responseHeaders.setRawHeaders(
            b"request-id",
            [b"abcd1234"],
        )

        request_data = json.loads(request.content.read())

        url = request_data["url"]
        domain = urlparse(url).netloc
        if domain == "e429.example":
            request.setResponseCode(429)
            response_data = {"status": 429, "type": "/limits/over-user-limit"}
            return json.dumps(response_data).encode()
        if domain == "e404.example":
            request.setResponseCode(404)
            return b""
        if domain == "e500.example":
            request.setResponseCode(500)
            return ""
        if domain == "e520.example":
            request.setResponseCode(520)
            response_data = {"status": 520, "type": "/download/temporary-error"}
            return json.dumps(response_data).encode()
        if domain == "e521.example":
            request.setResponseCode(521)
            response_data = {"status": 521, "type": "/download/internal-error"}
            return json.dumps(response_data).encode()
        if domain == "exception.example":
            request.setResponseCode(401)
            response_data = {
                "status": 401,
                "type": "/auth/key-not-found",
                "title": "Authentication Key Not Found",
                "detail": "The authentication key is not valid or can't be matched.",
            }
            return json.dumps(response_data).encode()
        if domain == "empty-body-exception.example":
            request.setResponseCode(500)
            return b""
        if domain == "nonjson.example":
            request.setResponseCode(200)
            return b"foo"
        if domain == "nonjson-exception.example":
            request.setResponseCode(500)
            return b"foo"
        if domain == "array-exception.example":
            request.setResponseCode(500)
            return b'["foo"]'

        auth_header = request.getHeader("Authorization")
        payment_header = request.getHeader("X-Payment")
        if not auth_header and not payment_header:
            request.setResponseCode(402)
            return json.dumps(RESPONSE_402).encode()

        echo_data = request_data.get("echoData")
        if echo_data:
            session_data = WORKFLOWS.setdefault(echo_data, {})
            if echo_data in {"402-payment-retry", "402-payment-retry-2"}:
                assert request.getHeader("X-Payment")
                # Return 402 on the first request, then 200 on the second
                if not session_data:
                    session_data["payment_attempts"] = 1
                    request.setResponseCode(402)
                    return json.dumps(RESPONSE_402).encode()
            elif echo_data == "402-payment-retry-exceeded":
                assert request.getHeader("X-Payment")
                # Return 402 on the first 2 requests, then 200 on the third
                # (the client will give up after 2 attempts, so there will be no
                # third in practice)
                if not session_data:
                    session_data["payment_attempts"] = 1
                    session_data["payment"] = request.getHeader("X-Payment")
                    request.setResponseCode(402)
                    return json.dumps(RESPONSE_402).encode()
                if session_data["payment_attempts"] == 1:
                    session_data["payment_attempts"] = 2
                    # Make sure the client refreshed the payment header
                    assert session_data["payment"] != request.getHeader("X-Payment")
                    request.setResponseCode(402)
                    return json.dumps(RESPONSE_402).encode()
            elif echo_data == "402-no-payment-retry":
                assert not request.getHeader("X-Payment")
                # Return 402 on the first request, then 200 on the second
                if not session_data:
                    session_data["payment_attempts"] = 1
                    request.setResponseCode(402)
                    return json.dumps(RESPONSE_402).encode()
            elif echo_data == "402-no-payment-retry-exceeded":
                assert not request.getHeader("X-Payment")
                # Return 402 on the first 2 requests, then 200 on the third
                # (the client will give up after 2 attempts, so there will be no
                # third in practice)
                if not session_data:
                    session_data["payment_attempts"] = 1
                    request.setResponseCode(402)
                    return json.dumps(RESPONSE_402).encode()
                if session_data["payment_attempts"] == 1:
                    session_data["payment_attempts"] = 2
                    request.setResponseCode(402)
                    return json.dumps(RESPONSE_402).encode()
            elif echo_data == "402-long-error":
                request.setResponseCode(402)
                response_data = {
                    **RESPONSE_402,
                    "error": (
                        "This is a long error message that exceeds the 32 "
                        "character limit for the error type prefix. It should "
                        "not be parsed as an error type."
                    ),
                }
                return json.dumps(response_data).encode()

        response_data: dict[str, Any] = {
            "url": url,
        }

        html = "<html><body>Hello<h1>World!</h1></body></html>"
        if "httpResponseBody" in request_data:
            body = b64encode(html.encode()).decode()
            response_data["httpResponseBody"] = body
        if "browserHtml" in request_data:
            assert "browserHtml" in request_data
            response_data["browserHtml"] = html
        if "screenshot" in request_data:
            assert "screenshot" in request_data
            response_data["screenshot"] = SCREENSHOT

        return json.dumps(response_data).encode()


class MockServer:
    def __init__(self, resource=None, port=None):
        resource = resource or DefaultResource
        self.resource = f"{resource.__module__}.{resource.__name__}"
        self.proc = None
        self.host = socket.gethostbyname(socket.gethostname())
        self.port = port or get_ephemeral_port()
        self.root_url = f"http://{self.host}:{self.port}"

    def __enter__(self):
        self.proc = Popen(
            [
                sys.executable,
                "-u",
                "-m",
                "tests.mockserver",
                self.resource,
                "--port",
                str(self.port),
            ],
            stdout=PIPE,
        )
        assert self.proc.stdout is not None
        self.proc.stdout.readline()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        assert self.proc is not None
        self.proc.kill()
        self.proc.wait()
        time.sleep(0.2)

    def urljoin(self, path):
        return self.root_url + path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("resource")
    parser.add_argument("--port", type=int)
    args = parser.parse_args()
    module_name, name = args.resource.rsplit(".", 1)
    sys.path.append(".")
    resource = getattr(import_module(module_name), name)()
    # Typing issue: https://github.com/twisted/twisted/issues/9909
    http_port = reactor.listenTCP(args.port, Site(resource))  # type: ignore[attr-defined]

    def print_listening():
        host = http_port.getHost()
        print(f"Mock server {resource} running at http://{host.host}:{host.port}")

    # Typing issue: https://github.com/twisted/twisted/issues/9909
    reactor.callWhenRunning(print_listening)  # type: ignore[attr-defined]
    reactor.run()  # type: ignore[attr-defined]


if __name__ == "__main__":
    main()
