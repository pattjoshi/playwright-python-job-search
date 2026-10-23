"""Access control for the API: who is signed in (session cookie), and what they may do.

Every /api/* and /reports/* request needs a signed-in user, except /api/auth/* (sign-in itself).
Requests that change something must come from this app's own page (checked with the Origin header).
"""

from urllib.parse import urlsplit

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response

from job_search.repositories import User
from job_search.schemas.common import ApiError
from job_search.services.auth import SESSION_DAYS, AuthService

COOKIE = "job_search_session"
PROTECTED_PREFIXES = ("/api/", "/reports/")
PUBLIC_PREFIXES = ("/api/auth/",)
LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1", "[::1]"}
UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def install_auth(app: FastAPI, auth: AuthService) -> None:
    @app.middleware("http")
    async def require_sign_in(request: Request, call_next) -> Response:
        path = request.url.path
        if request.method in UNSAFE_METHODS and path.startswith("/api/") and not _same_site(request):
            return JSONResponse({"error": "This request didn't come from the job search page."}, status_code=403)
        if path.startswith(PROTECTED_PREFIXES) and not path.startswith(PUBLIC_PREFIXES):
            user = auth.user_for(request.cookies.get(COOKIE))
            if user is None:
                return JSONResponse({"error": "Please sign in."}, status_code=401)
            request.state.user = user
        return await call_next(request)


def _same_site(request: Request) -> bool:
    """True for requests from this app's page (or tools that send no Origin, like the command line)."""
    origin = request.headers.get("origin")
    if not origin:
        return True
    host = urlsplit(origin).hostname or ""
    return host in LOCAL_HOSTS or urlsplit(origin).netloc == request.headers.get("host")


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
