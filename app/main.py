import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes.health import router as health_router
from app.core.config import get_runtime_config, get_settings
from app.core.logging import setup_logging

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    setup_logging()
    settings = get_settings()
    runtime_config = get_runtime_config()
    logger.info(
        "Starting service app_name=%s environment=%s exchange=%s",
        settings.app_name,
        settings.environment,
        runtime_config.exchange.name,
    )
    yield
    logger.info("Stopping service app_name=%s", settings.app_name)


def create_app() -> FastAPI:
    settings = get_settings()

    application = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        lifespan=lifespan,
    )
    application.include_router(health_router)

    return application
