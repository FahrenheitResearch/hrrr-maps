#!/usr/bin/env python3
"""Download and convert historical weather events from AWS to mmap cache.

Pipeline: Download GRIB → NVMe staging, convert → NVMe staging, move both → D: archive.
Processes events from most recent to oldest. Resume-friendly.

Usage:
    python tools/download_archive_events.py                    # full run
    python tools/download_archive_events.py --dry-run          # preview
    python tools/download_archive_events.py --event 20200817_12z --max-fhr 2
    python tools/download_archive_events.py --category tornado
"""

import argparse
import json
import shutil
import sys
import time
import threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from queue import Queue, Empty
from dataclasses import dataclass, field
from typing import List, Optional

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from smart_hrrr.orchestrator import download_forecast_hour
from core.cross_section_interactive import InteractiveCrossSection

# Defaults
DEFAULT_ARCHIVE_DIR = Path(r"D:\hrrr\archive-events")
DEFAULT_STAGING_DIR = Path(r"C:\Users\drew\hrrr-maps\cache\staging")
DEFAULT_EVENTS_FILE = PROJECT_ROOT / "events.json"
DEFAULT_THREADS = 12
DEFAULT_CONVERT_WORKERS = 4
DEFAULT_MAX_FHR = 24

# Synoptic cycles have F00-F48; non-synoptic have F00-F18
SYNOPTIC_HOURS = {0, 6, 12, 18}


@dataclass
class EventWork:
    """All work for a single event."""
    event_key: str
    event_name: str
    date_str: str
    cycle_hour: int         # Mapped synoptic hour for download
    original_hour: int
    fhrs: List[int]         # FHRs that still need processing
    fhrs_need_download: List[int]   # Subset that need GRIB download
    fhrs_need_convert: List[int]    # Subset that need mmap conversion


def map_to_synoptic(hour: int) -> int:
    """Map a cycle hour to the closest previous synoptic cycle."""
    if hour in SYNOPTIC_HOURS:
        return hour
    candidates = [h for h in SYNOPTIC_HOURS if h <= hour]
    if candidates:
        return max(candidates)
    return 18


def parse_event_key(key: str):
    """Parse '20200303_03z' -> (date_str='20200303', hour=3)."""
    parts = key.split("_")
    return parts[0], int(parts[1].replace("z", ""))


def get_prs_filename(model_config, cycle_hour: int, fhr: int) -> str:
    return model_config.get_filename(cycle_hour, 'pressure', fhr)


def get_sfc_filename(model_config, cycle_hour: int, fhr: int) -> str:
    return model_config.get_filename(cycle_hour, 'surface', fhr)


def build_event_work_list(events: dict, archive_dir: Path, max_fhr: int,
                          category: str = None, event_filter: str = None) -> List[EventWork]:
    """Build per-event work list, sorted newest first. Checks archive dir for resume."""
    from model_config import get_model_registry
    model_config = get_model_registry().get_model('hrrr')

    work_list = []
    for event_key, event_info in events.items():
        if category and event_info.get("category") != category:
            continue
        if event_filter and event_key != event_filter:
            continue

        date_str, original_hour = parse_event_key(event_key)
        synoptic_hour = map_to_synoptic(original_hour)

        fhrs_need_download = []
        fhrs_need_convert = []
        all_fhrs = []

        for fhr in range(0, max_fhr + 1):
            # Check final archive location
            final_grib_dir = archive_dir / "hrrr" / date_str / f"{synoptic_hour:02d}z" / f"F{fhr:02d}"
            final_cache_dir = archive_dir / "cache" / "xsect" / "hrrr"
            prs_fn = get_prs_filename(model_config, synoptic_hour, fhr)
            sfc_fn = get_sfc_filename(model_config, synoptic_hour, fhr)
            cache_stem = f"{date_str}_{synoptic_hour:02d}z_F{fhr:02d}_{Path(prs_fn).stem}"
            mmap_dir = final_cache_dir / cache_stem

            # Already fully done?
            if mmap_dir.is_dir() and (mmap_dir / "_complete").exists():
                continue

            all_fhrs.append(fhr)

            # GRIB exists in archive?
            has_grib = (final_grib_dir / prs_fn).exists() and (final_grib_dir / sfc_fn).exists()
            if not has_grib:
                fhrs_need_download.append(fhr)
            fhrs_need_convert.append(fhr)

        if all_fhrs:
            work_list.append(EventWork(
                event_key=event_key,
                event_name=event_info.get("name", event_key),
                date_str=date_str,
                cycle_hour=synoptic_hour,
                original_hour=original_hour,
                fhrs=all_fhrs,
                fhrs_need_download=fhrs_need_download,
                fhrs_need_convert=fhrs_need_convert,
            ))

    # Sort newest first
    work_list.sort(key=lambda e: e.event_key, reverse=True)
    return work_list


def process_event(event: EventWork, args, model_config, event_idx: int,
                  total_events: int, global_stats: dict):
    """Process a single event: download + convert in parallel on NVMe, then move to D:."""
    staging_grib = args.staging_dir / "grib" / "hrrr" / event.date_str / f"{event.cycle_hour:02d}z"
    staging_cache = args.staging_dir / "cache" / "xsect" / "hrrr"
    final_grib_base = args.archive_dir / "hrrr" / event.date_str / f"{event.cycle_hour:02d}z"
    final_cache = args.archive_dir / "cache" / "xsect" / "hrrr"

    staging_cache.mkdir(parents=True, exist_ok=True)
    final_cache.mkdir(parents=True, exist_ok=True)

    mapped = f" (-> {event.cycle_hour:02d}z)" if event.original_hour != event.cycle_hour else ""
    print(f"\n{'=' * 60}")
    print(f"[{event_idx}/{total_events}] {event.event_key}{mapped}: {event.event_name}")
    print(f"  Download: {len(event.fhrs_need_download)} FHRs | Convert: {len(event.fhrs_need_convert)} FHRs")
    print(f"{'=' * 60}")

    dl_ok = 0
    dl_fail = 0
    cv_ok = 0
    cv_fail = 0
    total_cv = len(event.fhrs_need_convert)
    progress_lock = threading.Lock()

    # --- Conversion queue: fed by downloads as they complete ---
    convert_queue = Queue()
    SENTINEL = None  # signals workers to stop

    # For FHRs that need convert but NOT download (GRIB already in archive),
    # copy them to staging and queue immediately
    fhrs_prequeued = set()
    for fhr in event.fhrs_need_convert:
        if fhr not in event.fhrs_need_download:
            src_dir = final_grib_base / f"F{fhr:02d}"
            dst_dir = staging_grib / f"F{fhr:02d}"
            if src_dir.exists() and not dst_dir.exists():
                dst_dir.mkdir(parents=True, exist_ok=True)
                shutil.copytree(str(src_dir), str(dst_dir), dirs_exist_ok=True)
            convert_queue.put(fhr)
            fhrs_prequeued.add(fhr)

    # Pre-create xsect instances sequentially — eccodes init is not thread-safe
    skip_convert = args.skip_convert or total_cv == 0
    xsect_instances = []
    if not skip_convert:
        for i in range(args.convert_workers):
            xsect_instances.append(InteractiveCrossSection(
                cache_dir=str(staging_cache),
                grib_backend='auto',
                sfc_resolver=lambda prs: str(Path(prs).parent / Path(prs).name.replace('wrfprs', 'wrfsfc')),
                nat_resolver=lambda prs: None,
            ))

    def convert_worker(worker_id):
        nonlocal cv_ok, cv_fail
        xsect = xsect_instances[worker_id]
        # Stagger starts — eccodes init (first GRIB load) is not thread-safe
        if worker_id > 0:
            time.sleep(worker_id * 5)
        while True:
            fhr = convert_queue.get()
            if fhr is SENTINEL:
                break
            prs_fn = get_prs_filename(model_config, event.cycle_hour, fhr)
            prs_path = staging_grib / f"F{fhr:02d}" / prs_fn
            try:
                start = time.perf_counter()
                ok = xsect.load_forecast_hour(str(prs_path), fhr)
                duration = time.perf_counter() - start
                xsect.forecast_hours.pop(fhr, None)
                with progress_lock:
                    if ok:
                        cv_ok += 1
                        print(f"    [cv-{worker_id}] F{fhr:02d} OK in {duration:.1f}s ({cv_ok}/{total_cv})")
                    else:
                        cv_fail += 1
                        print(f"    [cv-{worker_id}] F{fhr:02d} FAILED")
            except Exception as e:
                with progress_lock:
                    cv_fail += 1
                    print(f"    [cv-{worker_id}] F{fhr:02d} ERROR: {e}")

    # Start conversion workers
    cv_threads = []
    if not skip_convert:
        for i in range(args.convert_workers):
            t = threading.Thread(target=convert_worker, args=(i,), daemon=True)
            t.start()
            cv_threads.append(t)

    # --- Downloads: feed conversion queue as FHRs complete ---
    if event.fhrs_need_download:
        print(f"\n  Downloading {len(event.fhrs_need_download)} FHRs + converting as they arrive...")

        def download_fhr(fhr):
            fhr_dir = staging_grib / f"F{fhr:02d}"
            return fhr, download_forecast_hour(
                model='hrrr',
                date_str=event.date_str,
                cycle_hour=event.cycle_hour,
                forecast_hour=fhr,
                output_dir=fhr_dir,
                file_types=['pressure', 'surface'],
                source_preference=['aws'],
            )

        with ThreadPoolExecutor(max_workers=args.threads) as pool:
            futures = {pool.submit(download_fhr, fhr): fhr for fhr in event.fhrs_need_download}
            for future in as_completed(futures):
                fhr, ok = future.result()
                with progress_lock:
                    if ok:
                        dl_ok += 1
                        print(f"    [dl] F{fhr:02d} OK ({dl_ok}/{len(event.fhrs_need_download)})")
                        # Feed to conversion queue if needed
                        if not skip_convert and fhr in event.fhrs_need_convert:
                            convert_queue.put(fhr)
                    else:
                        dl_fail += 1
                        print(f"    [dl] F{fhr:02d} FAILED")
    elif not skip_convert and fhrs_prequeued:
        print(f"\n  Converting {len(fhrs_prequeued)} FHRs (GRIBs already on disk)...")

    # Signal conversion workers to stop (one sentinel per worker)
    for _ in cv_threads:
        convert_queue.put(SENTINEL)
    for t in cv_threads:
        t.join()

    global_stats['downloaded'] += dl_ok
    global_stats['download_failed'] += dl_fail
    global_stats['converted'] += cv_ok
    global_stats['convert_failed'] += cv_fail
    print(f"  Downloads: {dl_ok} OK, {dl_fail} failed | Conversions: {cv_ok} OK, {cv_fail} failed")

    # --- Phase 3: Move staging → archive (D:) ---
    print(f"\n  Phase 3: Moving to archive (D:)...")
    move_start = time.perf_counter()

    # Move GRIBs
    if staging_grib.exists():
        for fhr_dir in sorted(staging_grib.iterdir()):
            if not fhr_dir.is_dir():
                continue
            dest = final_grib_base / fhr_dir.name
            dest.parent.mkdir(parents=True, exist_ok=True)
            if dest.exists():
                shutil.rmtree(str(dest))
            shutil.move(str(fhr_dir), str(dest))

    # Move cache dirs
    for entry in sorted(staging_cache.iterdir()):
        if not entry.is_dir():
            continue
        # Only move dirs belonging to this event
        expected_prefix = f"{event.date_str}_{event.cycle_hour:02d}z_"
        if entry.name.startswith(expected_prefix):
            dest = final_cache / entry.name
            if dest.exists():
                shutil.rmtree(str(dest))
            shutil.move(str(entry), str(dest))

    # Clean up empty staging dirs
    if staging_grib.exists():
        shutil.rmtree(str(staging_grib), ignore_errors=True)

    move_duration = time.perf_counter() - move_start
    print(f"  Moved to archive in {move_duration:.1f}s")


def main():
    parser = argparse.ArgumentParser(description="Download & convert archive weather events")
    parser.add_argument("--threads", type=int, default=DEFAULT_THREADS,
                        help=f"Download threads (default: {DEFAULT_THREADS})")
    parser.add_argument("--convert-workers", type=int, default=DEFAULT_CONVERT_WORKERS,
                        help=f"Conversion workers (default: {DEFAULT_CONVERT_WORKERS})")
    parser.add_argument("--max-fhr", type=int, default=DEFAULT_MAX_FHR,
                        help=f"Max forecast hour (default: {DEFAULT_MAX_FHR})")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be done without doing it")
    parser.add_argument("--category", type=str, default=None,
                        help="Only process events in this category")
    parser.add_argument("--event", type=str, default=None,
                        help="Only process a specific event key (e.g. 20200817_12z)")
    parser.add_argument("--skip-convert", action="store_true",
                        help="Download only, don't convert to mmap")
    parser.add_argument("--archive-dir", type=Path, default=DEFAULT_ARCHIVE_DIR,
                        help=f"Final archive dir on D: (default: {DEFAULT_ARCHIVE_DIR})")
    parser.add_argument("--staging-dir", type=Path, default=DEFAULT_STAGING_DIR,
                        help=f"NVMe staging dir (default: {DEFAULT_STAGING_DIR})")
    parser.add_argument("--events-file", type=Path, default=DEFAULT_EVENTS_FILE,
                        help=f"Events JSON file (default: {DEFAULT_EVENTS_FILE})")
    args = parser.parse_args()

    # Load events
    with open(args.events_file) as f:
        events = json.load(f)
    print(f"Loaded {len(events)} events from {args.events_file}")

    # Build work list (newest first)
    work_list = build_event_work_list(
        events, args.archive_dir, args.max_fhr, args.category, args.event,
    )

    # Stats summary
    total_dl = sum(len(e.fhrs_need_download) for e in work_list)
    total_cv = sum(len(e.fhrs_need_convert) for e in work_list)
    total_cached = len(events) * (args.max_fhr + 1) - sum(len(e.fhrs) for e in work_list)

    print(f"\nResume check:")
    print(f"  Already cached (mmap):   {total_cached}")
    print(f"  Events to process:       {len(work_list)}")
    print(f"  FHRs to download:        {total_dl}")
    print(f"  FHRs to convert:         {total_cv}")

    # Show synoptic mapping
    mapped = [(e.event_key, e.original_hour, e.cycle_hour) for e in work_list
              if e.original_hour != e.cycle_hour]
    if mapped:
        print(f"\nSynoptic init mapping ({len(mapped)} non-synoptic events):")
        for key, orig, syn in mapped:
            print(f"  {key}: {orig:02d}z -> {syn:02d}z")

    if args.dry_run:
        print(f"\n[DRY RUN] Would process {len(work_list)} events (newest first):")
        for i, e in enumerate(work_list, 1):
            m = f" (-> {e.cycle_hour:02d}z)" if e.original_hour != e.cycle_hour else ""
            print(f"  {i:3d}. {e.event_key}{m}: {e.event_name} "
                  f"— {len(e.fhrs_need_download)} dl, {len(e.fhrs_need_convert)} cv")
        return

    if not work_list:
        print("\nNothing to do — all events already cached!")
        return

    # Get model config for filename generation
    from model_config import get_model_registry
    model_config = get_model_registry().get_model('hrrr')

    args.staging_dir.mkdir(parents=True, exist_ok=True)
    args.archive_dir.mkdir(parents=True, exist_ok=True)

    global_stats = {
        'downloaded': 0, 'download_failed': 0,
        'converted': 0, 'convert_failed': 0,
    }
    start_time = time.perf_counter()

    try:
        for i, event in enumerate(work_list, 1):
            process_event(event, args, model_config, i, len(work_list), global_stats)
    except KeyboardInterrupt:
        print("\n\nInterrupted! Re-run to resume from where you left off.")
        # Clean up staging
        if args.staging_dir.exists():
            shutil.rmtree(str(args.staging_dir), ignore_errors=True)
        sys.exit(1)

    # Clean up staging
    if args.staging_dir.exists():
        shutil.rmtree(str(args.staging_dir), ignore_errors=True)

    # Final summary
    elapsed = time.perf_counter() - start_time
    hours = int(elapsed // 3600)
    minutes = int((elapsed % 3600) // 60)
    seconds = int(elapsed % 60)

    print(f"\n{'=' * 60}")
    print(f"Completed in {hours}h {minutes}m {seconds}s")
    print(f"  Downloads:   {global_stats['downloaded']} OK, {global_stats['download_failed']} failed")
    print(f"  Conversions: {global_stats['converted']} OK, {global_stats['convert_failed']} failed")
    print(f"{'=' * 60}")

    if global_stats['download_failed'] or global_stats['convert_failed']:
        print("\nSome items failed. Re-run to retry.")
        sys.exit(1)


if __name__ == "__main__":
    main()
