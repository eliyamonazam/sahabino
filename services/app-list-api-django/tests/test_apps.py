import pytest
from rest_framework.test import APIClient


@pytest.fixture
def client():
    return APIClient()


@pytest.mark.django_db
def test_create_app(client):
    resp = client.post(
        "/apps/",
        {"package_name": "org.telegram.messenger", "name": "Telegram", "category": "messenger"},
        format="json",
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


@pytest.mark.django_db
def test_create_app_duplicate_package_name_fails_cleanly(client):
    payload = {"package_name": "com.whatsapp", "name": "Whatsapp", "category": "messenger"}
    first = client.post("/apps/", payload, format="json")
    assert first.status_code == 201

    second = client.post("/apps/", payload, format="json")
    assert second.status_code == 409
    assert "already exists" in second.json()["detail"]


@pytest.mark.django_db
def test_create_app_rejects_invalid_category(client):
    resp = client.post(
        "/apps/",
        {"package_name": "com.example.app", "name": "Example", "category": "not_a_category"},
        format="json",
    )
    assert resp.status_code == 400


@pytest.mark.django_db
def test_list_apps(client):
    client.post("/apps/", {"package_name": "a.one", "name": "One", "category": "social"}, format="json")
    client.post("/apps/", {"package_name": "a.two", "name": "Two", "category": "social"}, format="json")

    resp = client.get("/apps/")
    assert resp.status_code == 200
    names = {row["name"] for row in resp.json()}
    assert {"One", "Two"} <= names


@pytest.mark.django_db
def test_list_apps_active_only_filters_inactive(client):
    create = client.post(
        "/apps/", {"package_name": "a.three", "name": "Three", "category": "social"}, format="json"
    )
    app_id = create.json()["id"]
    client.delete(f"/apps/{app_id}/")

    all_apps = client.get("/apps/")
    assert any(row["id"] == app_id for row in all_apps.json())

    active_apps = client.get("/apps/", {"active_only": "true"})
    assert all(row["id"] != app_id for row in active_apps.json())


@pytest.mark.django_db
def test_patch_app_partial_update(client):
    create = client.post(
        "/apps/", {"package_name": "a.four", "name": "Four", "category": "video"}, format="json"
    )
    app_id = create.json()["id"]

    resp = client.patch(f"/apps/{app_id}/", {"category": "word_game"}, format="json")
    assert resp.status_code == 200
    body = resp.json()
    assert body["category"] == "word_game"
    assert body["name"] == "Four"  # unchanged


@pytest.mark.django_db
def test_patch_app_package_name(client):
    create = client.post(
        "/apps/", {"package_name": "a.old", "name": "Renamed App", "category": "video"}, format="json"
    )
    app_id = create.json()["id"]

    resp = client.patch(f"/apps/{app_id}/", {"package_name": "a.new"}, format="json")
    assert resp.status_code == 200
    body = resp.json()
    assert body["package_name"] == "a.new"
    assert body["name"] == "Renamed App"  # unchanged


@pytest.mark.django_db
def test_patch_app_package_name_duplicate_fails_cleanly(client):
    client.post("/apps/", {"package_name": "a.taken", "name": "First", "category": "video"}, format="json")
    create = client.post(
        "/apps/", {"package_name": "a.available", "name": "Second", "category": "video"}, format="json"
    )
    app_id = create.json()["id"]

    resp = client.patch(f"/apps/{app_id}/", {"package_name": "a.taken"}, format="json")
    assert resp.status_code == 409
    assert "already exists" in resp.json()["detail"]


@pytest.mark.django_db
def test_patch_nonexistent_app_returns_404(client):
    resp = client.patch("/apps/999999/", {"name": "Doesn't matter"}, format="json")
    assert resp.status_code == 404


@pytest.mark.django_db
def test_delete_app_soft_deletes(client):
    create = client.post(
        "/apps/", {"package_name": "a.five", "name": "Five", "category": "chat_dating"}, format="json"
    )
    app_id = create.json()["id"]

    resp = client.delete(f"/apps/{app_id}/")
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False

    listed = client.get("/apps/")
    row = next(r for r in listed.json() if r["id"] == app_id)
    assert row["is_active"] is False


@pytest.mark.django_db
def test_delete_nonexistent_app_returns_404(client):
    resp = client.delete("/apps/999999/")
    assert resp.status_code == 404
