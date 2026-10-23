"""A local web server for the saved career-page forms in tests/fixtures/forms (tests never open real sites)."""

import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

FORMS = Path(__file__).parents[1] / "fixtures" / "forms"


class _Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *args) -> None:
        pass


@pytest.fixture(scope="module")
def form_site():
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(_Quiet, directory=str(FORMS)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()
