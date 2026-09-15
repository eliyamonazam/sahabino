"""Heartbeat file the Docker healthcheck reads to confirm the consumer's
event loop is still alive, independent of message arrival.
"""

import time
from pathlib import Path


def write_heartbeat(path: str) -> None:
    """Update the heartbeat file's mtime to the current time."""
    Path(path).write_text(str(time.time()))
