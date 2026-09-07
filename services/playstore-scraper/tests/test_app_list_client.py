import httpx
import respx
from scraper.app_list_client import AppListClient


@respx.mock
async def test_fetch_active_apps_requests_active_only():
    route = respx.get("http://app-list-api/apps", params={"active_only": "true"}).mock(
        return_value=httpx.Response(
            200,
            json=[
                {
                    "id": 1,
                    "package_name": "com.whatsapp",
                    "name": "Whatsapp",
                    "category": "messenger",
                    "is_active": True,
                }
            ],
        )
    )

    async with httpx.AsyncClient(base_url="http://app-list-api") as http_client:
        client = AppListClient(http_client)
        apps = await client.fetch_active_apps()

    assert route.called
    assert apps == [
        {
            "id": 1,
            "package_name": "com.whatsapp",
            "name": "Whatsapp",
            "category": "messenger",
            "is_active": True,
        }
    ]


@respx.mock
async def test_fetch_active_apps_raises_on_error_response():
    respx.get("http://app-list-api/apps", params={"active_only": "true"}).mock(
        return_value=httpx.Response(500)
    )

    async with httpx.AsyncClient(base_url="http://app-list-api") as http_client:
        client = AppListClient(http_client)
        try:
            await client.fetch_active_apps()
            assert False, "expected HTTPStatusError"
        except httpx.HTTPStatusError:
            pass
