
"""Independent CodeMentor Web entry point. Legacy local administration is never mounted."""

from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.workbench import router
from app.core.config import get_settings
from app.core.database import dispose_engine, init_db
from app.core.llm_client import LLMClient, close_llm_clients
from app.core.workbench_security import RequestBoundary, SessionIdentity

from app.services.workbench_tutor import Tutor

WEB_BUILD = Path(__file__).resolve().parents[1] / "workbench-web" / "dist"
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    get_settings().ensure_directories()
    await init_db()
    try:
        yield
    finally:
        await close_llm_clients()
        await dispose_engine()


def create_workbench(*, model: LLMClient | None = None) -> FastAPI:
    app = FastAPI(title="CodeMentor AI 2.0", docs_url=None, redoc_url=None,
                  openapi_url=None, lifespan=lifespan)
    app.state.identity = SessionIdentity()
    app.state.tutor = Tutor(model, live=os.getenv("CODEMENTOR_AI_MODE") == "live")
    app.state.diagnosis_locks = tuple(asyncio.Lock() for _ in range(32))
    app.add_middleware(RequestBoundary)

    @app.exception_handler(Exception)
    async def unexpected_error(request: Request, exc: Exception):
        logger.error("Workbench request failed: %s (%s)", request.method, type(exc).__name__)
        return JSONResponse({"detail": "服务暂时不可用，请重试。"}, status_code=500)

    @app.get("/api/health")
    async def health():
        return {"status": "ok"}

    @app.post("/api/session")
    async def session(request: Request, response: Response):
        app.state.identity.establish(request, response)
        return {"ready": True}

    app.include_router(router)

    if WEB_BUILD.is_dir():
        app.mount("/", StaticFiles(directory=WEB_BUILD, html=True), name="workbench")

    return app


app = create_workbench()
