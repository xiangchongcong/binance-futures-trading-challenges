from fastapi import APIRouter

from app.core.config import get_runtime_config, get_settings
from app.schemas.health import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    settings = get_settings()
    runtime_config = get_runtime_config()
    return HealthResponse(
        status="ok",
        service_name=settings.app_name,
        environment=settings.environment,
        exchange=runtime_config.exchange.name,
    )
