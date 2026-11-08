
"""Browser session identity and request limits for the standalone workbench."""

import hashlib
import hmac
import os
import secrets
import time

from fastapi import HTTPException, Request, Response
from starlette.responses import JSONResponse

COOKIE = "cm_session"
SESSION_SECONDS = 7 * 24 * 60 * 60
MAX_BODY_BYTES = 80_000


class SessionIdentity:
    def __init__(self):
        configured = os.getenv("CODEMENTOR_SESSION_SECRET")
        if configured is not None and len(configured) < 32:
            raise ValueError("CODEMENTOR_SESSION_SECRET must contain at least 32 characters")
        self.secret = configured.encode() if configured else secrets.token_bytes(32)

    def _sign(self, value: str) -> str:
        return hmac.new(self.secret, value.encode(), hashlib.sha256).hexdigest()

    def resolve(self, request: Request) -> str | None:
        cookie = request.cookies.get(COOKIE, "")
        if len(cookie) != 32 + 1 + 10 + 1 + 64 or not cookie.isascii():
            return None
        owner, expiry, signature = cookie.split(".") if cookie.count(".") == 2 else ("", "", "")
        if not expiry.isdecimal() or int(expiry) <= time.time():
            return None
        if not hmac.compare_digest(signature, self._sign(f"{owner}.{expiry}")):
            return None
        return owner

    def establish(self, request: Request, response: Response) -> None:
        if self.resolve(request):
            return
        owner = secrets.token_hex(16)
        value = f"{owner}.{int(time.time()) + SESSION_SECONDS}"
        response.set_cookie(COOKIE, f"{value}.{self._sign(value)}", max_age=SESSION_SECONDS,
                            httponly=True, samesite="strict", secure=request.url.scheme == "https")


def require_owner(request: Request) -> str:
    owner = request.app.state.identity.resolve(request)
    if owner is None:
        raise HTTPException(401, "请先建立工作台会话。")
    return owner


class RequestBoundary:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or not scope["path"].startswith("/api/"):
            await self.app(scope, receive, send)
            return

        async def send_api(message):
            if message["type"] == "http.response.start":
                message["headers"] = [*message.get("headers", []),
                                      (b"cache-control", b"no-store"),
                                      (b"x-content-type-options", b"nosniff")]
            await send(message)

        if scope["method"] in {"GET", "HEAD", "OPTIONS"}:
            await self.app(scope, receive, send_api)
            return

        request = Request(scope)
        origin = request.headers.get("origin")
        if origin and origin.rstrip("/") != f"{request.url.scheme}://{request.url.netloc}":
            await JSONResponse({"detail": "跨站请求已拦截。"}, 403)(scope, receive, send_api)
            return

        content_length = request.headers.get("content-length", "")
        if content_length.isdecimal() and int(content_length) > MAX_BODY_BYTES:
            await self._reject_size(scope, receive, send_api)
            return
        body = bytearray()
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            if len(body) + len(message.get("body", b"")) > MAX_BODY_BYTES:
                await self._reject_size(scope, receive, send_api)
                return
            body.extend(message.get("body", b""))
            if not message.get("more_body", False):
                break

        sent = False

        async def replay_body():
            nonlocal sent
            if sent:
                return await receive()
            sent = True
            return {"type": "http.request", "body": bytes(body), "more_body": False}

        await self.app(scope, replay_body, send_api)

    @staticmethod
    async def _reject_size(scope, receive, send):
        await JSONResponse({"detail": "提交内容超过大小限制。"}, 413)(scope, receive, send)
