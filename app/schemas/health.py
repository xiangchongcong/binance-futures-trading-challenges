from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    service_name: str
    environment: str
    exchange: str
