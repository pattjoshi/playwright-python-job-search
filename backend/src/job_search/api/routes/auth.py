"""Sign in, first-run account setup, sign out and password change."""

import secrets

from fastapi import APIRouter, Request, Response

from job_search.api.auth import COOKIE, clear_session_cookie, client_address, current_user, set_session_cookie
from job_search.api.dependencies import ApiContext
from job_search.repositories import User
from job_search.schemas.common import ApiError
from job_search.services.auth import AuthError


def user_to_dict(user: User) -> dict:
    return {"id": user.id, "email": user.email, "name": user.name, "role": user.role, "created_at": user.created_at}


async def _body(request: Request) -> dict:
    try:
        body = await request.json()
    except ValueError:
        body = None
    if not isinstance(body, dict):
        raise ApiError("Send the details as JSON.")
    return {key: str(value) if value is not None else "" for key, value in body.items()}


def build_router(ctx: ApiContext) -> APIRouter:
    router = APIRouter(prefix="/api/auth")
    auth = ctx.auth

    def check_setup_code(given: str) -> None:
        """Online, anyone could open the page first: creating the account needs the SETUP_CODE you set in Vercel."""
        expected = ctx.settings.setup_code
        if ctx.settings.hosted and not expected:
            raise ApiError("Set SETUP_CODE in the hosting settings first, then create your account with it.", status=403)
        if expected and not secrets.compare_digest(given.encode(), expected.encode()):
            raise ApiError("That setup code isn't right.", status=403)

    def run(action):
        try:
            return action()
        except AuthError as error:
            raise ApiError(error.message, status=error.status) from None

    @router.get("/status")
    def status(request: Request):
        user = auth.user_for(request.cookies.get(COOKIE))
        return {"setup_required": auth.setup_required(), "setup_code_required": bool(ctx.settings.setup_code or ctx.settings.hosted),
                "user": user_to_dict(user) if user else None}

    @router.post("/setup")
    async def setup(request: Request, response: Response):
        body = await _body(request)
        check_setup_code(str(body.get("setup_code") or ""))
        user, token = run(lambda: auth.create_owner(body.get("name", ""), body.get("email", ""), body.get("password", "")))
        set_session_cookie(response, token, secure=ctx.settings.hosted)
        return {"user": user_to_dict(user)}

    @router.post("/login")
    async def login(request: Request, response: Response):
        body = await _body(request)
        client = client_address(request, ctx.settings.hosted)
        user, token = run(lambda: auth.sign_in(body.get("email", ""), body.get("password", ""), client))
        set_session_cookie(response, token, secure=ctx.settings.hosted)
        return {"user": user_to_dict(user)}

    @router.post("/logout")
    def logout(request: Request, response: Response):
        auth.sign_out(request.cookies.get(COOKIE))
        clear_session_cookie(response)
        return {"ok": True}

    @router.post("/password")
    async def change_password(request: Request):
        user = _signed_in(request)
        body = await _body(request)
        run(lambda: auth.change_password(user, body.get("current", ""), body.get("new", ""), request.cookies.get(COOKIE)))
        return {"ok": True}

    @router.post("/logout-everywhere")
    def logout_everywhere(request: Request, response: Response):
        auth.sign_out_everywhere(_signed_in(request))
        clear_session_cookie(response)
        return {"ok": True}

    def _signed_in(request: Request) -> User:
        # /api/auth/* skips the sign-in check in the middleware, so check here.
        request.state.user = auth.user_for(request.cookies.get(COOKIE))
        return current_user(request)

    return router
