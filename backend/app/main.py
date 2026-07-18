import asyncio
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.errors import AppError, Reason
from app.middleware.rate_limit import RateLimitMiddleware
from app.routers import download, metadata
from app.services.cleanup import cleanup_loop

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("fetchly")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    os.makedirs(settings.download_dir, exist_ok=True)

    import shutil

    if shutil.which("ffmpeg") is None:
        logger.error(
            "ffmpeg was not found on PATH. Merging separate audio/video "
            "streams will fail for every download. Check the Dockerfile "
            "and deployment image."
        )

    cleanup_task = asyncio.create_task(cleanup_loop())
    logger.info("Fetchly API started (env=%s)", settings.environment)
    yield
    cleanup_task.cancel()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )
    app.add_middleware(RateLimitMiddleware)

    app.include_router(metadata.router)
    app.include_router(download.router)

    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "platform": exc.platform,
                "reason": exc.reason.value,
                "message": exc.message,
            },
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "success": False,
                "platform": "unknown",
                "reason": Reason.INVALID_URL.value,
                "message": "The request was malformed.",
            },
        )

    @app.exception_handler(HTTPException)
    async def handle_http_exception(request: Request, exc: HTTPException) -> JSONResponse:
        # Catches plain HTTPException raised anywhere that didn't go
        # through AppError (e.g. FastAPI internals, 404s) — still
        # normalized to the same response shape.
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "platform": "unknown",
                "reason": Reason.UNKNOWN.value,
                "message": str(exc.detail),
            },
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        # Last-resort catch-all. Full detail goes to the server log;
        # the client only ever sees a generic message — never a
        # traceback, stack frame, or internal file path.
        logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "platform": "unknown",
                "reason": Reason.UNKNOWN.value,
                "message": "An unexpected error occurred. Please try again.",
            },
        )

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    return app


app = create_app()
