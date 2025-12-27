#!/usr/bin/env python3
"""
Full Pipeline Runner - Process everything as fast as possible:
1. Standard weather maps (104 parameters)
2. Diurnal temperature analysis
3. Cross-sections for predefined paths

Usage:
    python run_full_pipeline.py --latest
    python run_full_pipeline.py --date 20251224 --hour 12
    python run_full_pipeline.py --latest --skip-maps --xsect-only
"""

import argparse
import logging
import time
import sys
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


# Predefined cross-section paths (can be extended)
CROSS_SECTION_PATHS = {
    'denver_chicago': {
        'name': 'Denver → Chicago',
        'start': (39.74, -104.99),
        'end': (41.88, -87.63),
    },
    'la_phoenix': {
        'name': 'Los Angeles → Phoenix',
        'start': (34.05, -118.24),
        'end': (33.45, -112.07),
    },
    'dallas_okc': {
        'name': 'Dallas → OKC',
        'start': (32.78, -96.80),
        'end': (35.47, -97.52),
    },
    'nyc_boston': {
        'name': 'NYC → Boston',
        'start': (40.71, -74.01),
        'end': (42.36, -71.06),
    },
}

# Cross-section styles to generate
XSECT_STYLES = ['wind_speed', 'rh', 'omega', 'temp', 'theta_e', 'icing']


def get_latest_cycle():
    """Get the latest available HRRR cycle"""
    from smart_hrrr.availability import get_latest_cycle
    cycle, cycle_time = get_latest_cycle('hrrr')
    if cycle is None:
        logger.error("No available cycles found")
        return None, None, None
    date_str = cycle_time.strftime("%Y%m%d")
    hour = cycle_time.hour
    return cycle, date_str, hour


def run_standard_maps(cycle: str, date_str: str, hour: int,
                      forecast_hours: list, categories: list = None,
                      workers: int = 1):
    """Run standard weather map processing"""
    logger.info("=" * 60)
    logger.info("PHASE 1: STANDARD WEATHER MAPS")
    logger.info("=" * 60)

    from smart_hrrr.orchestrator import process_model_run

    start = time.time()
    results = process_model_run(
        model='hrrr',
        date=date_str,
        hour=hour,
        forecast_hours=forecast_hours,
        categories=categories,
        max_workers=workers,
    )

    duration = time.time() - start
    successful = sum(1 for r in results if r.get('success'))

    logger.info(f"Standard maps complete: {successful}/{len(forecast_hours)} hours in {duration:.1f}s")
    return results


def run_diurnal_analysis(date_str: str, hour: int, end_fhr: int = 48,
                         rolling: bool = True, workers: int = 4):
    """Run diurnal temperature analysis"""
    logger.info("=" * 60)
    logger.info("PHASE 2: DIURNAL TEMPERATURE ANALYSIS")
    logger.info("=" * 60)

    import subprocess

    cmd = [
        sys.executable, "tools/process_diurnal.py",
        "--date", date_str,
        "--hour", str(hour),
        "--end-fhr", str(end_fhr),
        "--workers", str(workers),
    ]
    if rolling:
        cmd.append("--rolling")

    start = time.time()
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
    duration = time.time() - start

    if result.returncode == 0:
        logger.info(f"Diurnal analysis complete in {duration:.1f}s")
    else:
        logger.error(f"Diurnal analysis failed: {result.stderr[-500:]}")

    return result.returncode == 0


def run_cross_sections(date_str: str, hour: int, forecast_hours: list,
                       paths: dict = None, styles: list = None,
                       workers: int = 4, use_fast_mode: bool = True):
    """Run cross-section generation for predefined paths.

    Args:
        use_fast_mode: If True, pre-load data into memory for ~20x faster generation.
                       Requires ~3.5GB RAM per forecast hour.
    """
    logger.info("=" * 60)
    logger.info("PHASE 3: CROSS-SECTIONS")
    logger.info("=" * 60)

    paths = paths or CROSS_SECTION_PATHS
    styles = styles or XSECT_STYLES

    # Find GRIB files
    run_dir = Path(f"outputs/hrrr/{date_str}/{hour:02d}z")
    if not run_dir.exists():
        logger.error(f"Run directory not found: {run_dir}")
        return False

    grib_files = []
    for fhr in forecast_hours:
        fhr_dir = run_dir / f"F{fhr:02d}"
        prs_files = list(fhr_dir.glob("*wrfprs*.grib2"))
        if prs_files:
            grib_files.append((str(prs_files[0]), fhr))

    if not grib_files:
        logger.error("No GRIB files found for cross-sections")
        return False

    logger.info(f"Found {len(grib_files)} forecast hours")
    logger.info(f"Paths: {list(paths.keys())}")
    logger.info(f"Styles: {styles}")
    logger.info(f"Mode: {'FAST (memory)' if use_fast_mode else 'Standard (disk)'}")

    cycle = f"{date_str}_{hour:02d}Z"
    output_base = Path(f"outputs/xsect/{date_str}/{hour:02d}z")

    start = time.time()
    total_generated = 0

    if use_fast_mode:
        # FAST MODE: Pre-load all data into memory, then generate cross-sections
        from core.cross_section_interactive import InteractiveCrossSection

        ixs = InteractiveCrossSection()

        # Load all forecast hours
        logger.info("\nPre-loading forecast hours into memory...")
        load_start = time.time()
        for grib_file, fhr in grib_files:
            ixs.load_forecast_hour(grib_file, fhr)
        load_time = time.time() - load_start
        logger.info(f"Loaded {len(ixs.get_loaded_hours())} hours in {load_time:.1f}s ({ixs.get_memory_usage():.0f} MB)")

        # Generate cross-sections for each path/style/hour
        logger.info("\nGenerating cross-sections...")
        gen_start = time.time()

        for path_id, path_info in paths.items():
            logger.info(f"\n  {path_info['name']}:")

            for style in styles:
                output_dir = output_base / path_id / style
                output_dir.mkdir(parents=True, exist_ok=True)

                frames = []
                for fhr in sorted(ixs.get_loaded_hours()):
                    try:
                        img_bytes = ixs.get_cross_section(
                            start_point=path_info['start'],
                            end_point=path_info['end'],
                            style=style,
                            forecast_hour=fhr,
                            n_points=80,
                        )
                        if img_bytes:
                            # Save frame
                            frame_path = output_dir / f"xsect_{style}_f{fhr:02d}.png"
                            with open(frame_path, 'wb') as f:
                                f.write(img_bytes)
                            frames.append(frame_path)
                    except Exception as e:
                        logger.debug(f"    Frame F{fhr:02d} failed: {e}")

                # Create GIF from frames
                if len(frames) >= 2:
                    try:
                        from PIL import Image
                        images = [Image.open(f) for f in frames]
                        gif_path = output_dir / f"xsect_{style}_{cycle}.gif"
                        images[0].save(
                            gif_path, save_all=True, append_images=images[1:],
                            duration=500, loop=0
                        )
                        total_generated += 1
                        logger.info(f"    ✓ {style}: {len(frames)} frames → {gif_path.name}")
                    except Exception as e:
                        logger.error(f"    ✗ {style} GIF failed: {e}")
                elif frames:
                    total_generated += 1
                    logger.info(f"    ✓ {style}: {len(frames)} frame(s)")

        gen_time = time.time() - gen_start
        logger.info(f"\nGenerated in {gen_time:.1f}s ({gen_time/max(1,total_generated):.1f}s per animation)")

    else:
        # STANDARD MODE: Read from disk for each frame (slower but less memory)
        from core.cross_section_production import create_cross_section_animation

        for path_id, path_info in paths.items():
            logger.info(f"\nProcessing path: {path_info['name']}")

            for style in styles:
                output_dir = output_base / path_id / style
                output_dir.mkdir(parents=True, exist_ok=True)

                try:
                    anim_path = create_cross_section_animation(
                        grib_files=grib_files[:13],
                        start_point=path_info['start'],
                        end_point=path_info['end'],
                        cycle=cycle,
                        output_dir=output_dir,
                        n_points=80,
                        fps=2,
                        style=style,
                    )

                    if anim_path:
                        total_generated += 1
                        logger.info(f"  ✓ {style}: {anim_path.name}")

                except Exception as e:
                    logger.error(f"  ✗ {style}: {e}")

    duration = time.time() - start
    logger.info(f"\nCross-sections complete: {total_generated} animations in {duration:.1f}s")
    return total_generated > 0


def run_cross_section_single_frame(grib_file: str, start_point: tuple,
                                    end_point: tuple, style: str,
                                    output_dir: Path):
    """Generate a single cross-section frame (for parallel processing)"""
    from core.cross_section_production import (
        extract_cross_section_multi_fields,
        create_production_cross_section,
    )

    try:
        data = extract_cross_section_multi_fields(
            grib_file, start_point, end_point,
            n_points=80, style=style
        )
        if data is None:
            return None

        return create_production_cross_section(
            data=data,
            cycle="",
            forecast_hour=0,
            output_dir=output_dir,
            style=style,
            fast_mode=True,
        )
    except Exception as e:
        return None


def main():
    parser = argparse.ArgumentParser(description="Full HRRR Pipeline Runner")
    parser.add_argument("--latest", action="store_true", help="Use latest available cycle")
    parser.add_argument("--date", type=str, help="Date (YYYYMMDD)")
    parser.add_argument("--hour", type=int, help="Hour (0-23)")
    parser.add_argument("--hours", type=str, default="0-12", help="Forecast hours (e.g., 0-12 or 0,3,6,9)")
    parser.add_argument("--categories", type=str, help="Categories to process (comma-separated)")
    parser.add_argument("--workers", type=int, default=4, help="Number of parallel workers")

    # Skip flags
    parser.add_argument("--skip-maps", action="store_true", help="Skip standard map generation")
    parser.add_argument("--skip-diurnal", action="store_true", help="Skip diurnal analysis")
    parser.add_argument("--skip-xsect", action="store_true", help="Skip cross-sections")

    # Only flags
    parser.add_argument("--maps-only", action="store_true", help="Only run standard maps")
    parser.add_argument("--diurnal-only", action="store_true", help="Only run diurnal analysis")
    parser.add_argument("--xsect-only", action="store_true", help="Only run cross-sections")

    # Cross-section options
    parser.add_argument("--xsect-paths", type=str, help="Cross-section paths (comma-separated)")
    parser.add_argument("--xsect-styles", type=str, help="Cross-section styles (comma-separated)")

    args = parser.parse_args()

    # Determine cycle
    if args.latest:
        cycle, date_str, hour = get_latest_cycle()
        if cycle is None:
            sys.exit(1)
        logger.info(f"Using latest cycle: {date_str} {hour:02d}Z")
    elif args.date and args.hour is not None:
        date_str = args.date
        hour = args.hour
        cycle = f"{date_str}{hour:02d}"
    else:
        parser.error("Must specify --latest or --date and --hour")

    # Parse forecast hours
    if "-" in args.hours:
        start, end = map(int, args.hours.split("-"))
        forecast_hours = list(range(start, end + 1))
    else:
        forecast_hours = [int(h) for h in args.hours.split(",")]

    # Parse categories
    categories = args.categories.split(",") if args.categories else None

    # Handle only/skip flags
    run_maps = not args.skip_maps
    run_diurnal = not args.skip_diurnal
    run_xsect = not args.skip_xsect

    if args.maps_only:
        run_maps, run_diurnal, run_xsect = True, False, False
    elif args.diurnal_only:
        run_maps, run_diurnal, run_xsect = False, True, False
    elif args.xsect_only:
        run_maps, run_diurnal, run_xsect = False, False, True

    # Parse cross-section options
    xsect_paths = None
    if args.xsect_paths:
        xsect_paths = {k: CROSS_SECTION_PATHS[k] for k in args.xsect_paths.split(",")
                       if k in CROSS_SECTION_PATHS}

    xsect_styles = args.xsect_styles.split(",") if args.xsect_styles else None

    # Run pipeline
    logger.info("=" * 60)
    logger.info("HRRR FULL PIPELINE")
    logger.info(f"Cycle: {date_str} {hour:02d}Z | Hours: F{min(forecast_hours):02d}-F{max(forecast_hours):02d}")
    logger.info(f"Maps: {'✓' if run_maps else '✗'} | Diurnal: {'✓' if run_diurnal else '✗'} | XSect: {'✓' if run_xsect else '✗'}")
    logger.info("=" * 60)

    total_start = time.time()

    # Phase 1: Standard Maps
    if run_maps:
        run_standard_maps(cycle, date_str, hour, forecast_hours, categories, args.workers)

    # Phase 2: Diurnal
    if run_diurnal:
        run_diurnal_analysis(date_str, hour, end_fhr=max(forecast_hours), workers=args.workers)

    # Phase 3: Cross-sections
    if run_xsect:
        run_cross_sections(date_str, hour, forecast_hours, xsect_paths, xsect_styles, args.workers)

    total_duration = time.time() - total_start
    logger.info("=" * 60)
    logger.info(f"PIPELINE COMPLETE - Total time: {total_duration:.1f}s ({total_duration/60:.1f} min)")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
