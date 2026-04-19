import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes.health import router as health_router
from app.core.config import build_config_summary, get_settings
from app.core.logging import setup_logging

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    setup_logging()
    settings = get_settings()
    logger.info(
        "Starting service app_name=%s symbol=%s testnet=%s",
        settings.app.name,
        settings.exchange.symbol,
        settings.credentials.use_testnet,
    )
    logger.info("Configuration summary: %s", build_config_summary(settings))
    yield
    logger.info("Stopping service app_name=%s", settings.app.name)


def create_app() -> FastAPI:
    settings = get_settings()

    application = FastAPI(
        title=settings.app.name,
        version="0.1.0",
        lifespan=lifespan,
    )
    application.include_router(health_router)

    return application
