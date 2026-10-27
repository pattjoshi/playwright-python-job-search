"""Protections every request gets, because the app runs a web server on your computer.

- Host check: the server only answers to 127.0.0.1 / localhost. A website using "DNS rebinding" (pointing its own
  name at your computer) can't talk to the app, so it can't claim the first account or read anything.
- Size limit: a request body over MAX_BODY_BYTES is refused before it's read.
- Browser headers: no framing by other sites (clickjacking), no MIME sniffing, no full URLs in Referer.
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response

LOCAL_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})
MAX_BODY_BYTES = 25 * 1024 * 1024  # the biggest real request: a 10 MB resume, or a saved page + screenshot
HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Content-Security-Policy": "frame-ancestors 'none'",
    "Referrer-Policy": "same-origin",
}


def host_name(host_header: str) -> str:
    """ "127.0.0.1:8000" -> "127.0.0.1", "[::1]:8000" -> "::1"."""
    host = host_header.strip().lower()
    if host.startswith("["):
        return host[1:].split("]", 1)[0]
    return host.rsplit(":", 1)[0] if host.count(":") == 1 else host


def install_security(app: FastAPI, extra_hosts: tuple[str, ...] = ()) -> None:
    allowed = LOCAL_HOSTS | {h.strip().lower() for h in extra_hosts if h.strip()}

    @app.middleware("http")
    async def protect(request: Request, call_next) -> Response:
        if host_name(request.headers.get("host", "")) not in allowed:
            return JSONResponse({"error": "This app only answers on 127.0.0.1 or localhost."}, status_code=400)
        length = request.headers.get("content-length", "")
        if length.isdigit() and int(length) > MAX_BODY_BYTES:
            return JSONResponse({"error": "That request is too big."}, status_code=413)
        response = await call_next(request)
        for name, value in HEADERS.items():
            response.headers.setdefault(name, value)
        return response
