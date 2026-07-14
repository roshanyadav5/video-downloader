import asyncio
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.middleware.rate_limit import RateLimitMiddleware
from app.routers import download, metadata
from app.services.cleanup import cleanup_loop

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("fetchly")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    os.makedirs(settings.download_dir, exist_ok=True)
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

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    return app


app = create_app()
