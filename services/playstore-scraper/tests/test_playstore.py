from unittest.mock import patch

from scraper.playstore import build_stats_payload, scrape_app_details

RAW_PLAY_STORE_RESPONSE = {
    "title": "WhatsApp Messenger",
    "score": 4.3,
    "ratings": 190_000_000,
    "reviews": 12_000_000,
    "installs": "10,000,000,000+",
    "minInstalls": 10_000_000_000,
    "realInstalls": 10_500_000_000,
    "free": True,
    "price": 0,
    "currency": "USD",
    "genre": "Communication",
    "contentRating": "Everyone",
    "version": "2.24.1.1",
    "updated": 1732000000,
    "adSupported": False,
    "some_field_we_dont_care_about": "ignored",
}

TRACKED_APP = {
    "id": 1,
    "package_name": "com.whatsapp",
    "name": "Whatsapp",
    "category": "messenger",
    "is_active": True,
}


async def test_scrape_app_details_calls_google_play_scraper_with_locale():
    with patch("scraper.playstore.fetch_play_store_app", return_value=RAW_PLAY_STORE_RESPONSE) as mock_fetch:
        result = await scrape_app_details("com.whatsapp", lang="fa", country="ir")

    mock_fetch.assert_called_once_with("com.whatsapp", lang="fa", country="ir")
    assert result == RAW_PLAY_STORE_RESPONSE


def test_build_stats_payload_shapes_and_renames_fields():
    payload = build_stats_payload(TRACKED_APP, RAW_PLAY_STORE_RESPONSE)

    assert payload["app_id"] == 1
    assert payload["package_name"] == "com.whatsapp"
    assert payload["category"] == "messenger"
    assert payload["title"] == "WhatsApp Messenger"
    assert payload["score"] == 4.3
    assert payload["min_installs"] == 10_000_000_000
    assert payload["real_installs"] == 10_500_000_000
    assert payload["store_last_updated"] == 1732000000
    assert payload["ad_supported"] is False
    assert "some_field_we_dont_care_about" not in payload
    assert "scraped_at" in payload


def test_build_stats_payload_tolerates_missing_play_details_fields():
    payload = build_stats_payload(TRACKED_APP, {})

    assert payload["package_name"] == "com.whatsapp"
    assert payload["title"] is None
    assert payload["score"] is None
    assert payload["ad_supported"] is None
