import time
from unittest.mock import patch

import pytest
from consumer.heartbeat import write_heartbeat
from consumer.main import _heartbeat_loop


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


async def test_heartbeat_loop_writes_on_every_timer_tick_not_per_message():
    """This loop runs independently of the two Kafka consume loops, so it
    must keep ticking on its own timer even when nothing is being consumed.
    """
    calls = []

    def fake_write_heartbeat(path):
        calls.append(("heartbeat", path))

    async def fake_sleep(seconds):
        calls.append(("sleep", seconds))
        if len(calls) >= 4:
            raise RuntimeError("stop loop")

    with (
        patch("consumer.main.write_heartbeat", side_effect=fake_write_heartbeat),
        patch("consumer.main.asyncio.sleep", side_effect=fake_sleep),
        pytest.raises(RuntimeError, match="stop loop"),
    ):
        await _heartbeat_loop("/fake/heartbeat", 60)

    assert calls == [
        ("heartbeat", "/fake/heartbeat"),
        ("sleep", 60),
        ("heartbeat", "/fake/heartbeat"),
        ("sleep", 60),
    ]
