import time
from unittest.mock import patch

import pytest
from scraper.config import Config
from scraper.heartbeat import write_heartbeat
from scraper.main import main


def test_write_heartbeat_creates_file_with_fresh_mtime(tmp_path):
    path = tmp_path / "heartbeat"
    before = time.time()

    write_heartbeat(str(path))

    assert path.exists()
    assert path.stat().st_mtime >= before


def test_write_heartbeat_updates_mtime_on_existing_file(tmp_path):
    path = tmp_path / "heartbeat"
    write_heartbeat(str(path))
    old_mtime = path.stat().st_mtime

    time.sleep(0.01)
    write_heartbeat(str(path))

    assert path.stat().st_mtime > old_mtime


class _FakeBroker:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False


async def test_main_writes_heartbeat_before_each_scrape_pass():
    """The healthcheck relies on the heartbeat landing before the (possibly
    long-running or failing) scrape pass, not after it -- otherwise a stuck
    or crashing pass would never get a fresh heartbeat at all.
    """
    config = Config()
    config.heartbeat_file = "/fake/heartbeat"
    config.scrape_interval_seconds = 1

    calls = []

    async def fake_run_once(*args, **kwargs):
        calls.append("run_once")

    def fake_write_heartbeat(path):
        assert path == config.heartbeat_file
        calls.append("heartbeat")

    async def fake_sleep(seconds):
        calls.append("sleep")
        if calls.count("sleep") >= 2:
            raise RuntimeError("stop loop")

    with (
        patch("scraper.main.get_config", return_value=config),
        patch("scraper.main.get_broker", return_value=_FakeBroker()),
        patch("scraper.main.run_once", side_effect=fake_run_once),
        patch("scraper.main.write_heartbeat", side_effect=fake_write_heartbeat),
        patch("scraper.main.asyncio.sleep", side_effect=fake_sleep),
        pytest.raises(RuntimeError, match="stop loop"),
    ):
        await main()

    assert calls == ["heartbeat", "run_once", "sleep", "heartbeat", "run_once", "sleep"]
