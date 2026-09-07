"""Client for the app-list-api-fastapi service — the source of truth for which
apps are currently tracked and should be scraped.
"""

from typing import Any

import httpx


class AppListClient:
    def __init__(self, http_client: httpx.AsyncClient) -> None:
        self._http_client = http_client

    async def fetch_active_apps(self) -> list[dict[str, Any]]:
        response = await self._http_client.get("/apps", params={"active_only": "true"})
        response.raise_for_status()
        return response.json()
