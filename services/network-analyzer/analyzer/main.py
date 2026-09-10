import argparse
import asyncio
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy.ext.asyncio import async_sessionmaker

from analyzer.app_list_client import AppListClient
from analyzer.config import Config, get_config
from analyzer.database import build_session_factory
from analyzer.filename_parser import InvalidFilenameError, parse_filename
from analyzer.pcap_metrics import extract_metrics
from analyzer.persistence import insert_network_metrics, source_file_already_analyzed

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("network-analyzer")


async def _process_file(
    pcap_path: Path, apps_by_name: dict[str, dict[str, Any]], session_factory: async_sessionmaker
) -> None:
    """Analyze one pcap file and store its metrics, unless it should be skipped.

    A file is skipped (logged, not raised) if its filename doesn't match the
    naming convention, its app name isn't a tracked app, or it's already
    been analyzed (source_file dedup). The dedup check runs before the
    (comparatively expensive) tshark pass, not after.
    """
    try:
        parsed = parse_filename(pcap_path.name)
    except InvalidFilenameError:
        logger.warning(
            "Skipping %s: filename doesn't match the '{app}_{send|receive}_{NN}.pcap' convention",
            pcap_path.name,
        )
        return

    app = apps_by_name.get(parsed.app_name.lower())
    if app is None:
        logger.warning("Skipping %s: no tracked app matches name %r", pcap_path.name, parsed.app_name)
        return

    async with session_factory() as session:
        if await source_file_already_analyzed(session, pcap_path.name):
            logger.info("Skipping %s: already analyzed", pcap_path.name)
            return

    # pyshark's FileCapture drives its own (synchronous) asyncio event loop
    # internally, which can't run inside the loop this coroutine is already
    # executing under - run it in its own thread instead, same as the
    # playstore-scraper's use of asyncio.to_thread for another blocking,
    # non-async-native library.
    metrics = await asyncio.to_thread(extract_metrics, str(pcap_path))

    async with session_factory() as session:
        await insert_network_metrics(
            session,
            {
                "app_id": app["id"],
                "scenario": parsed.scenario,
                "source_file": pcap_path.name,
                **metrics,
                "analyzed_at": datetime.now(UTC),
            },
        )
    logger.info("Analyzed %s (app_id=%s, scenario=%s)", pcap_path.name, app["id"], parsed.scenario)


async def run_once(
    directory: Path, app_list_client: AppListClient, session_factory: async_sessionmaker
) -> None:
    apps = await app_list_client.fetch_apps()
    apps_by_name = {app["name"].lower(): app for app in apps}

    pcap_files = sorted(directory.glob("*.pcap"))
    logger.info("Found %d pcap file(s) in %s", len(pcap_files), directory)

    for pcap_path in pcap_files:
        await _process_file(pcap_path, apps_by_name, session_factory)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analyze captured pcap files and store network-quality metrics in Postgres."
    )
    parser.add_argument(
        "directory",
        nargs="?",
        default=None,
        help="Directory of .pcap files to process (default: PCAP_DIR env var, or data/pcap-samples)",
    )
    return parser.parse_args()


async def main() -> None:
    args = _parse_args()
    config: Config = get_config()
    directory = Path(args.directory) if args.directory else Path(config.pcap_dir)
    session_factory = build_session_factory()

    async with httpx.AsyncClient(base_url=config.app_list_api_url) as http_client:
        app_list_client = AppListClient(http_client)
        await run_once(directory, app_list_client, session_factory)


if __name__ == "__main__":
    asyncio.run(main())
