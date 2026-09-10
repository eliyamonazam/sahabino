from fastapi import Depends, FastAPI, Response, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.apps import router as apps_router
from app.database import get_db
from app.schemas.health import HealthStatus

app = FastAPI(
    title="App List API (FastAPI)",
    description="CRUD API for managing the list of Google Play apps to be tracked.",
    version="0.1.0",
)

app.include_router(apps_router)


@app.get("/health", response_model=HealthStatus, include_in_schema=False)
async def health(response: Response, db: AsyncSession = Depends(get_db)) -> HealthStatus:
    try:
        await db.execute(text("SELECT 1"))
    except Exception:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return HealthStatus(status="unhealthy")
    return HealthStatus(status="ok")
