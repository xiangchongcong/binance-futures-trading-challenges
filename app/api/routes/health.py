from fastapi import APIRouter

from app.core.config import get_settings
from app.schemas.health import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(
        status="ok",
        service_name=settings.app.name,
        environment="testnet" if settings.credentials.use_testnet else "production",
        exchange="binance_futures",
    )
