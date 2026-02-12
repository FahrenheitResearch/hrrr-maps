"""
Simplified GRIB Download Orchestrator

Handles parallel downloading of HRRR GRIB files for cross-section processing.
"""

import time
import logging
import urllib.request
import urllib.error
import socket
from pathlib import Path
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from requests.adapters import HTTPAdapter

from model_config import get_model_registry
from .io import create_output_structure, get_forecast_hour_dir

# Minimum valid GRIB file size (bytes).  Even the smallest wrfsfc subsets are >1MB.
# HTML error pages from NOMADS are typically <5KB.
MIN_GRIB_SIZE = 500_000  # 500KB

logger = logging.getLogger(__name__)


def _detect_source(url: str) -> str:
    """Classify URL source for logging and source-priority ordering."""
    u = (url or "").lower()
    if "nomads.ncep.noaa.gov" in u:
        return "nomads"
    if "ftpprd.ncep.noaa.gov" in u:
        return "ftpprd"
    if "s3.amazonaws.com" in u or "noaa-" in u:
        return "aws"
    if "pando" in u:
        return "pando"
    return "other"


def _source_display_name(source: str) -> str:
    names = {
        "nomads": "NOMADS",
        "ftpprd": "NCEP FTPPRD",
        "aws": "AWS",
        "pando": "Pando",
        "other": "Source",
    }
    return names.get(source, "Source")


def _apply_source_preference(urls: List[str], source_preference: Optional[List[str]] = None) -> List[str]:
    """Reorder URLs based on preferred source list.

    source_preference examples:
      ['aws', 'pando', 'nomads']
      ['ftpprd', 'nomads']
    """
    if not source_preference:
        return urls
    order = {src.lower(): idx for idx, src in enumerate(source_preference)}
    ranked = []
    for original_idx, url in enumerate(urls):
        src = _detect_source(url)
        rank = order.get(src, len(order))
        ranked.append((rank, original_idx, url))
    ranked.sort(key=lambda t: (t[0], t[1]))
    return [url for _, _, url in ranked]


def download_grib_file(url: str, output_path: Path, timeout: int = 600) -> bool:
    """Download a single GRIB file from URL.

    Downloads to a .partial temp file first, validates the response (HTTP status,
    content type, file size), then atomically renames to the final path.
    Returns False and cleans up on any validation failure — never writes
    HTML error pages or truncated files to the final path.
    """
    partial_path = Path(str(output_path) + '.partial')
    try:
        resp = requests.get(url, timeout=timeout, stream=True)

        # Reject non-200 responses (rate-limit 429, server error 503, etc.)
        if resp.status_code != 200:
            logger.warning(f"HTTP {resp.status_code} from {url}")
            return False

        # Reject HTML error pages masquerading as GRIB data
        ct = (resp.headers.get('Content-Type') or '').lower()
        if 'html' in ct or 'text' in ct:
            logger.warning(f"Non-binary Content-Type '{ct}' from {url} (likely rate-limit page)")
            return False

        # Stream to .partial file
        written = 0
        with open(partial_path, 'wb') as f:
            for chunk in resp.iter_content(chunk_size=256 * 1024):
                f.write(chunk)
                written += len(chunk)

        # Reject tiny files (HTML error bodies, truncated downloads)
        if written < MIN_GRIB_SIZE:
            logger.warning(f"Downloaded file too small ({written} bytes) from {url}")
            partial_path.unlink(missing_ok=True)
            return False

        # Sanity: first 4 bytes of a valid GRIB file are 'GRIB'
        with open(partial_path, 'rb') as f:
            magic = f.read(4)
        if magic != b'GRIB':
            logger.warning(f"File does not start with GRIB magic (got {magic!r}) from {url}")
            partial_path.unlink(missing_ok=True)
            return False

        partial_path.rename(output_path)
        return True
    except requests.exceptions.RequestException as e:
        logger.debug(f"Failed to download from {url}: {e}")
        partial_path.unlink(missing_ok=True)
        return False
    except OSError as e:
        logger.debug(f"I/O error downloading from {url}: {e}")
        partial_path.unlink(missing_ok=True)
        return False


def download_forecast_hour(
    model: str,
    date_str: str,
    cycle_hour: int,
    forecast_hour: int,
    output_dir: Path,
    file_types: List[str] = None,
    source_preference: Optional[List[str]] = None,
) -> bool:
    """Download GRIB files for a single forecast hour."""

    if file_types is None:
        file_types = ['pressure', 'surface', 'native']  # wrfprs, wrfsfc, wrfnat

    registry = get_model_registry()
    model_config = registry.get_model(model)

    if not model_config:
        logger.error(f"Unknown model: {model}")
        return False

    output_dir.mkdir(parents=True, exist_ok=True)
    all_file_types_ok = True

    for file_type in file_types:
        filename = model_config.get_filename(cycle_hour, file_type, forecast_hour)
        output_path = output_dir / filename
        file_ok = False

        if output_path.exists():
            # Validate existing file isn't corrupted (0-byte, HTML error page, etc.)
            fsize = output_path.stat().st_size
            if fsize < MIN_GRIB_SIZE:
                logger.warning(f"Existing file {filename} too small ({fsize} bytes) — re-downloading")
                output_path.unlink()
            else:
                logger.debug(f"File exists: {filename}")
                file_ok = True
                continue

        urls = model_config.get_download_urls(date_str, cycle_hour, file_type, forecast_hour)
        urls = _apply_source_preference(urls, source_preference)

        for i, url in enumerate(urls):
            source = _source_display_name(_detect_source(url))
            logger.info(f"Downloading {filename} from {source}...")

            if download_grib_file(url, output_path):
                logger.info(f"Downloaded {filename}")
                file_ok = True
                break
            else:
                if i < len(urls) - 1:
                    logger.warning(f"{source} failed, trying next source...")
                else:
                    logger.error(f"Failed to download {filename} from all sources")

        if not file_ok:
            all_file_types_ok = False

    return all_file_types_ok


def download_gribs_parallel(
    model: str,
    date_str: str,
    cycle_hour: int,
    forecast_hours: List[int],
    output_base_dir: Path = None,
    max_threads: int = 8,
    file_types: List[str] = None,
    on_complete=None,
    on_start=None,
    should_cancel=None,
    source_preference: Optional[List[str]] = None,
) -> Dict[int, bool]:
    """Download GRIB files for multiple forecast hours in parallel.

    Args:
        on_complete: Optional callback(fhr, success) called as each FHR finishes.
        on_start: Optional callback(fhr) called when each FHR starts downloading.
        should_cancel: Optional callable() returning True to abort remaining downloads.
    Returns dict mapping forecast_hour -> success status.
    """

    if output_base_dir is None:
        output_dirs = create_output_structure(model, date_str, cycle_hour)
        output_base_dir = output_dirs['run']

    def download_single(fhr: int) -> tuple:
        # Skip if cancelled before starting
        if should_cancel and should_cancel():
            return fhr, False
        if on_start:
            on_start(fhr)
        fhr_dir = get_forecast_hour_dir(output_base_dir, fhr)
        start = time.time()
        ok = download_forecast_hour(
            model,
            date_str,
            cycle_hour,
            fhr,
            fhr_dir,
            file_types=file_types,
            source_preference=source_preference,
        )
        dur = time.time() - start
        if ok:
            logger.info(f"  F{fhr:02d} downloaded ({dur:.1f}s)")
        return fhr, ok

    results = {}
    with ThreadPoolExecutor(max_workers=max_threads) as executor:
        futures = {executor.submit(download_single, fhr): fhr for fhr in forecast_hours}
        for future in as_completed(futures):
            fhr, ok = future.result()
            results[fhr] = ok
            if on_complete:
                on_complete(fhr, ok)
            # Cancel remaining futures
            if should_cancel and should_cancel():
                for f in futures:
                    f.cancel()
                break

    return results


def download_latest_cycle(
    model: str = 'hrrr',
    max_hours: int = 18,
    max_threads: int = 8,
    forecast_hours: List[int] = None
) -> tuple:
    """Download the latest available model cycle.

    Args:
        model: Model name (default 'hrrr')
        max_hours: Maximum forecast hour to download
        max_threads: Number of parallel download threads
        forecast_hours: Specific forecast hours to download (e.g., [0, 6, 12, 18]).
                       If None, downloads all hours from 0 to max_hours.

    Returns (date_str, cycle_hour, results_dict) or (None, None, {}) if failed.
    """
    from .availability import get_latest_cycle

    cycle, cycle_time = get_latest_cycle(model)
    if cycle is None:
        logger.error(f"No available cycles for {model}")
        return None, None, {}

    date_str = cycle_time.strftime("%Y%m%d")
    cycle_hour = cycle_time.hour

    # Determine forecast hours based on cycle type
    registry = get_model_registry()
    model_config = registry.get_model(model)
    max_fhr = model_config.get_max_forecast_hour(cycle_hour) if model_config else 18
    max_fhr = min(max_fhr, max_hours)

    if forecast_hours is not None:
        # Use specific forecast hours, filtered by what's available
        fhrs_to_download = [f for f in forecast_hours if f <= max_fhr]
    else:
        # Download all hours
        fhrs_to_download = list(range(max_fhr + 1))

    fhr_str = ','.join(f'F{f:02d}' for f in fhrs_to_download)
    logger.info(f"Downloading {model.upper()} {date_str} {cycle_hour:02d}Z [{fhr_str}]")

    results = download_gribs_parallel(
        model=model,
        date_str=date_str,
        cycle_hour=cycle_hour,
        forecast_hours=fhrs_to_download,
        max_threads=max_threads
    )

    success_count = sum(1 for ok in results.values() if ok)
    logger.info(f"Downloaded {success_count}/{len(fhrs_to_download)} forecast hours")

    return date_str, cycle_hour, results
