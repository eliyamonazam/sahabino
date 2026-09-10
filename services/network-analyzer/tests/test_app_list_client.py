import httpx
import respx
from analyzer.app_list_client import AppListClient


@respx.mock
async def test_fetch_apps_requests_all_apps_without_active_only_filter():
    route = respx.get("http://app-list-api/apps").mock(
        return_value=httpx.Response(
            200,
            json=[
                {"id": 1, "package_name": "ir.android.baham", "name": "Baham", "category": "chat_dating"},
                {"id": 2, "package_name": "app.pinno", "name": "Pinno", "category": "chat_dating"},
            ],
        )
    )

    async with httpx.AsyncClient(base_url="http://app-list-api") as http_client:
        client = AppListClient(http_client)
        apps = await client.fetch_apps()

    assert route.called
    assert route.calls.last.request.url.params == httpx.QueryParams()
    assert [app["name"] for app in apps] == ["Baham", "Pinno"]


@respx.mock
async def test_fetch_apps_raises_on_error_response():
    respx.get("http://app-list-api/apps").mock(return_value=httpx.Response(500))

    async with httpx.AsyncClient(base_url="http://app-list-api") as http_client:
        client = AppListClient(http_client)
        try:
            await client.fetch_apps()
            assert False, "expected HTTPStatusError"
        except httpx.HTTPStatusError:
            pass
