import argparse
import json
import socket
import sys
import time
from base64 import b64encode
from importlib import import_module
from subprocess import PIPE, Popen
from typing import Any, Dict
from urllib.parse import urlparse

from twisted.internet import reactor
from twisted.internet.task import deferLater
from twisted.web.resource import Resource
from twisted.web.server import NOT_DONE_YET, Site


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


class DefaultResource(Resource):
    request_count = 0

    def getChild(self, path, request):
        return self

    def render_POST(self, request):
        request_data = json.loads(request.content.read())

        request.responseHeaders.setRawHeaders(
            b"Content-Type",
            [b"application/json"],
        )
        request.responseHeaders.setRawHeaders(
            b"request-id",
            [b"abcd1234"],
        )

        url = request_data["url"]
        domain = urlparse(url).netloc
        if domain == "e429.example":
            request.setResponseCode(429)
            response_data = {"status": 429, "type": "/limits/over-user-limit"}
            return json.dumps(response_data).encode()
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

        response_data: Dict[str, Any] = {
            "url": url,
        }

        html = "<html><body>Hello<h1>World!</h1></body></html>"
        if "httpResponseBody" in request_data:
            body = b64encode(html.encode()).decode()
            response_data["httpResponseBody"] = body
        else:
            assert "browserHtml" in request_data
            response_data["browserHtml"] = html

        return json.dumps(response_data).encode()


class MockServer:
    def __init__(self, resource=None, port=None):
        resource = resource or DefaultResource
        self.resource = "{}.{}".format(resource.__module__, resource.__name__)
        self.proc = None
        self.host = socket.gethostbyname(socket.gethostname())
        self.port = port or get_ephemeral_port()
        self.root_url = "http://%s:%d" % (self.host, self.port)

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
        print(
            "Mock server {} running at http://{}:{}".format(
                resource, host.host, host.port
            )
        )

    # Typing issue: https://github.com/twisted/twisted/issues/9909
    reactor.callWhenRunning(print_listening)  # type: ignore[attr-defined]
    reactor.run()  # type: ignore[attr-defined]


if __name__ == "__main__":
    main()
