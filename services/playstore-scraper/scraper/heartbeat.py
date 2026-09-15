"""Heartbeat file the Docker healthcheck reads to confirm the scrape loop is
actually cycling, not just that the process is still running.
"""

import time
from pathlib import Path


def write_heartbeat(path: str) -> None:
    """Update the heartbeat file's mtime to the current time."""
    Path(path).write_text(str(time.time()))
