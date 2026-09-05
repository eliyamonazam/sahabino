from fastapi import FastAPI

from app.api.apps import router as apps_router

app = FastAPI(
    title="App List API (FastAPI)",
    description="CRUD API for managing the list of Google Play apps to be tracked.",
    version="0.1.0",
)

app.include_router(apps_router)


@app.get("/health", include_in_schema=False)
async def health() -> dict[str, str]:
    return {"status": "ok"}
