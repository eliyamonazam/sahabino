from unittest.mock import patch

import pytest


@pytest.mark.django_db
def test_health_ok_when_db_is_reachable(client):
    resp = client.get("/health/")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


@pytest.mark.django_db
def test_health_returns_503_when_db_is_unreachable(client):
    with patch("apps_api.views.connection.cursor", side_effect=Exception("connection refused")):
        resp = client.get("/health/")
    assert resp.status_code == 503
    assert resp.json() == {"status": "unhealthy"}
