from pydantic import BaseModel, Field


class HealthStatus(BaseModel):
    status: str = Field(..., description="'ok' if the service and its database connection are healthy.")
