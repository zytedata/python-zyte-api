import json
import ssl
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from threading import Thread
from urllib.parse import urljoin

CERT_PATH = (Path(__file__).resolve().parents[0] / "cert").resolve()


class MockServer:
    def __enter__(self):
        # Using HTTPs to test SSL
        self.httpd = HTTPServer(("127.0.0.1", 4443), _RequestHandler)
        self.httpd.socket = ssl.wrap_socket(self.httpd.socket,
                                            keyfile=(CERT_PATH / "key.pem").resolve(),
                                            certfile=(CERT_PATH / "cert.pem").resolve(),
                                            server_side=True)
        self.address, self.port = self.httpd.server_address
        self.thread = Thread(target=self.httpd.serve_forever)
        self.thread.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.httpd.shutdown()
        self.thread.join()

    def urljoin(self, url: str) -> str:
        return urljoin("http://{}:{}".format(self.address, self.port), url)


class _RequestHandler(BaseHTTPRequestHandler):
    def _send_response(self, status: int, content: str, content_type: str):
        self.send_response(status)
        self.send_header("Content-type", content_type)
        self.end_headers()
        self.wfile.write(content.encode("utf-8"))

    def do_POST(self):  # NOQA
        content_length = int(self.headers["Content-Length"])
        try:
            post_data = json.loads(self.rfile.read(content_length).decode("utf-8"))  # NOQA
        except (AttributeError, TypeError, ValueError, KeyError) as er:
            self._send_response(400, str(er), "text/html")
            return
        else:
            self._send_response(
                200,
                # Mirror data
                json.dumps(post_data),
                "application/json"
            )
