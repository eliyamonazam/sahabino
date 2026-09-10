"""Client for the app-list-api-fastapi service - the source of truth for which
apps are currently tracked, used here to resolve a pcap filename's app name
to a real app_id.
"""

from typing import Any

import httpx


class AppListClient:
    def __init__(self, http_client: httpx.AsyncClient) -> None:
        self._http_client = http_client

    async def fetch_apps(self) -> list[dict[str, Any]]:
        """Fetch every tracked app, active or not.

        Unlike the scraper (which only cares about apps it should currently
        scrape), a pcap capture may reference an app that's since been
        deactivated but still needs its historical metrics attributed
        correctly, so this intentionally doesn't filter on active_only.
        """
        response = await self._http_client.get("/apps")
        response.raise_for_status()
        return response.json()
