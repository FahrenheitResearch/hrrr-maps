#!/usr/bin/env python3
"""
Auto-Update Script for HRRR Cross-Section Dashboard

Monitors for new HRRR cycles and automatically downloads GRIB data.

Usage:
    python tools/auto_update.py --interval 15  # Check every 15 minutes
    python tools/auto_update.py --once         # Run once and exit
"""

import argparse
import logging
import sys
import time
import signal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

running = True
current_cycle = None


def signal_handler(sig, frame):
    global running
    logger.info("Shutting down...")
    running = False


def run_update_cycle(max_hours: int = 18):
    """Check for and download new HRRR cycle."""
    global current_cycle

    from smart_hrrr.availability import get_latest_cycle
    from smart_hrrr.orchestrator import download_gribs_parallel
    from smart_hrrr.io import create_output_structure

    cycle, cycle_time = get_latest_cycle('hrrr')
    if cycle is None:
        logger.warning("No available cycles found")
        return None

    if cycle == current_cycle:
        logger.info(f"Still on cycle {cycle}, no update needed")
        return None

    logger.info(f"New cycle available: {cycle}")
    date_str = cycle_time.strftime("%Y%m%d")
    hour = cycle_time.hour

    # Download GRIBs
    output_dirs = create_output_structure('hrrr', date_str, hour)
    forecast_hours = list(range(max_hours + 1))

    results = download_gribs_parallel(
        model='hrrr',
        date_str=date_str,
        cycle_hour=hour,
        forecast_hours=forecast_hours,
        max_threads=8
    )

    success_count = sum(1 for ok in results.values() if ok)
    logger.info(f"Downloaded {success_count}/{len(forecast_hours)} hours")

    current_cycle = cycle
    return str(output_dirs['run'])


def main():
    global running

    parser = argparse.ArgumentParser(description="Auto-Update for HRRR Dashboard")
    parser.add_argument("--interval", type=int, default=15, help="Check interval in minutes")
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    parser.add_argument("--max-hours", type=int, default=18, help="Max forecast hours")

    args = parser.parse_args()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    logger.info("=" * 60)
    logger.info("HRRR Auto-Update Service")
    logger.info(f"Interval: {args.interval} minutes")
    logger.info(f"Max hours: {args.max_hours}")
    logger.info("=" * 60)

    if args.once:
        data_dir = run_update_cycle(args.max_hours)
        if data_dir:
            logger.info(f"Data ready at: {data_dir}")
        return

    while running:
        try:
            data_dir = run_update_cycle(args.max_hours)
            if data_dir:
                logger.info(f"Data ready at: {data_dir}")
        except Exception as e:
            logger.exception(f"Update failed: {e}")

        logger.info(f"Sleeping for {args.interval} minutes...")
        for _ in range(args.interval * 60):
            if not running:
                break
            time.sleep(1)

    logger.info("Auto-update service stopped")


if __name__ == "__main__":
    main()
