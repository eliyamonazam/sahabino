import pytest
from app.database import get_db
from app.main import app
from sqlalchemy.exc import OperationalError


@pytest.mark.asyncio
async def test_health_ok_when_db_is_reachable(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_health_returns_503_when_db_is_unreachable(client):
    async def failing_get_db():
        class _FailingSession:
            async def execute(self, *args, **kwargs):
                raise OperationalError("SELECT 1", {}, Exception("connection refused"))

        yield _FailingSession()

    app.dependency_overrides[get_db] = failing_get_db
    resp = await client.get("/health")
    assert resp.status_code == 503
    assert resp.json() == {"status": "unhealthy"}
