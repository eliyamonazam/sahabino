import pytest


@pytest.mark.asyncio
async def test_create_app(client):
    resp = await client.post(
        "/apps",
        json={"package_name": "org.telegram.messenger", "name": "Telegram", "category": "messenger"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["id"] is not None
    assert body["package_name"] == "org.telegram.messenger"
    assert body["name"] == "Telegram"
    assert body["category"] == "messenger"
    assert body["is_active"] is True
    assert body["created_at"]
    assert body["updated_at"]


@pytest.mark.asyncio
async def test_create_app_duplicate_package_name_fails_cleanly(client):
    payload = {"package_name": "com.whatsapp", "name": "Whatsapp", "category": "messenger"}
    first = await client.post("/apps", json=payload)
    assert first.status_code == 201

    second = await client.post("/apps", json=payload)
    assert second.status_code == 409
    assert "already exists" in second.json()["detail"]


@pytest.mark.asyncio
async def test_create_app_rejects_invalid_category(client):
    resp = await client.post(
        "/apps",
        json={"package_name": "com.example.app", "name": "Example", "category": "not_a_category"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_list_apps(client):
    await client.post("/apps", json={"package_name": "a.one", "name": "One", "category": "social"})
    await client.post("/apps", json={"package_name": "a.two", "name": "Two", "category": "social"})

    resp = await client.get("/apps")
    assert resp.status_code == 200
    names = {row["name"] for row in resp.json()}
    assert {"One", "Two"} <= names


@pytest.mark.asyncio
async def test_list_apps_active_only_filters_inactive(client):
    create = await client.post("/apps", json={"package_name": "a.three", "name": "Three", "category": "social"})
    app_id = create.json()["id"]
    await client.delete(f"/apps/{app_id}")

    all_apps = await client.get("/apps")
    assert any(row["id"] == app_id for row in all_apps.json())

    active_apps = await client.get("/apps", params={"active_only": True})
    assert all(row["id"] != app_id for row in active_apps.json())


@pytest.mark.asyncio
async def test_patch_app_partial_update(client):
    create = await client.post(
        "/apps", json={"package_name": "a.four", "name": "Four", "category": "video"}
    )
    app_id = create.json()["id"]

    resp = await client.patch(f"/apps/{app_id}", json={"category": "word_game"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["category"] == "word_game"
    assert body["name"] == "Four"  # unchanged


@pytest.mark.asyncio
async def test_patch_app_package_name(client):
    create = await client.post(
        "/apps", json={"package_name": "a.old", "name": "Renamed App", "category": "video"}
    )
    app_id = create.json()["id"]

    resp = await client.patch(f"/apps/{app_id}", json={"package_name": "a.new"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["package_name"] == "a.new"
    assert body["name"] == "Renamed App"  # unchanged


@pytest.mark.asyncio
async def test_patch_app_package_name_duplicate_fails_cleanly(client):
    await client.post("/apps", json={"package_name": "a.taken", "name": "First", "category": "video"})
    create = await client.post("/apps", json={"package_name": "a.available", "name": "Second", "category": "video"})
    app_id = create.json()["id"]

    resp = await client.patch(f"/apps/{app_id}", json={"package_name": "a.taken"})
    assert resp.status_code == 409
    assert "already exists" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_patch_nonexistent_app_returns_404(client):
    resp = await client.patch("/apps/999999", json={"name": "Doesn't matter"})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_app_soft_deletes(client):
    create = await client.post(
        "/apps", json={"package_name": "a.five", "name": "Five", "category": "chat_dating"}
    )
    app_id = create.json()["id"]

    resp = await client.delete(f"/apps/{app_id}")
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False

    listed = await client.get("/apps")
    row = next(r for r in listed.json() if r["id"] == app_id)
    assert row["is_active"] is False


@pytest.mark.asyncio
async def test_delete_nonexistent_app_returns_404(client):
    resp = await client.delete("/apps/999999")
    assert resp.status_code == 404
