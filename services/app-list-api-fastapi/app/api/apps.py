import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.app import App
from app.schemas.app import AppCreate, AppRead, AppUpdate

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("app-list-api-fastapi")

router = APIRouter(prefix="/apps", tags=["apps"])


async def _get_app_or_404(app_id: int, db: AsyncSession) -> App:
    app = await db.get(App, app_id)
    if app is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"App {app_id} not found.")
    return app


@router.post(
    "",
    response_model=AppRead,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new app to track",
)
async def create_app(payload: AppCreate, db: AsyncSession = Depends(get_db)) -> App:
    app = App(package_name=payload.package_name, name=payload.name, category=payload.category)
    db.add(app)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        logger.warning("Rejected create: package_name '%s' already exists", payload.package_name)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"An app with package_name '{payload.package_name}' already exists.",
        )
    await db.refresh(app)
    logger.info("Created app id=%s name=%r", app.id, app.name)
    return app


@router.get(
    "",
    response_model=list[AppRead],
    summary="List tracked apps",
)
async def list_apps(
    active_only: bool = Query(
        default=False,
        description="If true, only return apps with is_active = true.",
    ),
    db: AsyncSession = Depends(get_db),
) -> list[App]:
    stmt = select(App).order_by(App.id)
    if active_only:
        stmt = stmt.where(App.is_active.is_(True))
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.patch(
    "/{app_id}",
    response_model=AppRead,
    summary="Partially update an app's package_name, name, and/or category",
)
async def update_app(app_id: int, payload: AppUpdate, db: AsyncSession = Depends(get_db)) -> App:
    app = await _get_app_or_404(app_id, db)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(app, field, value)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        logger.warning(
            "Rejected update for app id=%s: package_name '%s' already exists", app_id, payload.package_name
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"An app with package_name '{payload.package_name}' already exists.",
        )
    await db.refresh(app)
    logger.info("Updated app id=%s name=%r", app.id, app.name)
    return app


@router.delete(
    "/{app_id}",
    response_model=AppRead,
    summary="Deactivate an app (soft delete)",
)
async def deactivate_app(app_id: int, db: AsyncSession = Depends(get_db)) -> App:
    app = await _get_app_or_404(app_id, db)
    app.is_active = False
    await db.commit()
    await db.refresh(app)
    logger.info("Deactivated app id=%s name=%r", app.id, app.name)
    return app
