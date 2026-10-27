"""Access control for the API: who is signed in (session cookie), and what they may do.

Every /api/* and /reports/* request needs a signed-in user, except /api/auth/* (sign-in itself).
Requests that change something must come from this app's own page (checked with the Origin header).
/api/extension/* is for the Chrome extension: it sends its key ("Authorization: Bearer …") instead of a cookie.
"""

from collections.abc import Callable
from urllib.parse import urlsplit

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response

from job_search.repositories import User
from job_search.schemas.common import ApiError
from job_search.services.auth import SESSION_DAYS, AuthService

COOKIE = "job_search_session"
PROTECTED_PREFIXES = ("/api/", "/reports/")
PUBLIC_PREFIXES = ("/api/auth/",)
EXTENSION_PREFIX = "/api/extension/"
# `npm run dev` serves the page on :3000 and forwards /api to the app; those requests carry its Origin.
DEV_ORIGINS = frozenset({"http://localhost:3000", "http://127.0.0.1:3000"})
UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def install_auth(app: FastAPI, auth: AuthService, extension_user: Callable[[str | None], User | None] = lambda key: None) -> None:
    @app.middleware("http")
    async def require_sign_in(request: Request, call_next) -> Response:
        path = request.url.path
        if path.startswith(EXTENSION_PREFIX):
            header = request.headers.get("authorization", "")
            user = extension_user(header.removeprefix("Bearer ").strip() if header.startswith("Bearer ") else None)
            if user is None:
                return JSONResponse({"error": "The extension isn't connected: paste a new key from the Auto-apply page."},
                                    status_code=401)
            request.state.user = user
            return await call_next(request)
        if request.method in UNSAFE_METHODS and path.startswith("/api/") and not _same_site(request):
            return JSONResponse({"error": "This request didn't come from the job search page."}, status_code=403)
        if path.startswith(PROTECTED_PREFIXES) and not path.startswith(PUBLIC_PREFIXES):
            user = auth.user_for(request.cookies.get(COOKIE))
            if user is None:
                return JSONResponse({"error": "Please sign in."}, status_code=401)
            request.state.user = user
        return await call_next(request)


def _same_site(request: Request) -> bool:
    """True for requests from this app's page (or tools that send no Origin, like the command line).

    The Origin must be this very address (port included): another web page on your computer, e.g. on localhost:5000,
    is a different origin and can't make changes, even though the browser would send it the cookie.
    """
    origin = request.headers.get("origin")
    if not origin:
        return True
    return origin.rstrip("/").lower() in DEV_ORIGINS or urlsplit(origin).netloc.lower() == request.headers.get("host", "").lower()


def current_user(request: Request) -> User:
    user = getattr(request.state, "user", None)
    if user is None:
        raise ApiError("Please sign in.", status=401)
    return user


def require_owner(request: Request) -> User:
    """Authorization for actions that change the whole app (e.g. scheduled tasks on this computer)."""
    user = current_user(request)
    if not user.is_owner:
        raise ApiError("Only the owner of this app can do that.", status=403)
    return user


def set_session_cookie(response: Response, token: str) -> None:
    # HttpOnly: page scripts can't read it. SameSite=Lax: other websites can't send it with their requests.
    response.set_cookie(COOKIE, token, max_age=SESSION_DAYS * 86_400, httponly=True, samesite="lax", path="/")


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(COOKIE, path="/")
