"""Benchmark GRIB-to-mmap conversion with varying worker counts.

Tests the actual InteractiveCrossSection.load_forecast_hour() pipeline
with different ThreadPoolExecutor/ProcessPoolExecutor configurations.
"""
import os, sys, time, shutil, statistics, glob
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed

os.environ.setdefault('XSECT_OUTPUTS_DIR', 'C:/Users/drew/hrrr-maps/outputs')
os.environ.setdefault('XSECT_CACHE_DIR', 'C:/Users/drew/hrrr-maps/cache/xsect')
os.environ.setdefault('XSECT_GRIB_BACKEND', 'auto')
sys.path.insert(0, '.')

CACHE_BASE = Path(os.environ['XSECT_CACHE_DIR'])
MODEL = 'hrrr'
CYCLE_DATE = '20260208'
CYCLE_HOUR = '00'
CYCLE_KEY = f'{CYCLE_DATE}_{CYCLE_HOUR}z'
GRIB_BASE = Path(os.environ['XSECT_OUTPUTS_DIR']) / f'hrrr/{CYCLE_DATE}/{CYCLE_HOUR}z'


def get_test_fhrs():
    fhrs = []
    for d in sorted(GRIB_BASE.iterdir()):
        if d.is_dir() and d.name.startswith('F'):
            fhrs.append(int(d.name[1:]))
    return fhrs


def clear_cache(fhrs):
    """Remove mmap cache entries for given FHRs."""
    cache_model = CACHE_BASE / MODEL
    if not cache_model.exists():
        return 0
    removed = 0
    for entry in list(cache_model.iterdir()):
        if not entry.is_dir():
            continue
        name = entry.name
        if not name.startswith(CYCLE_KEY):
            continue
        # e.g. 20260207_22z_F06_wrfprs
        parts = name.split('_')
        if len(parts) >= 3 and parts[2].startswith('F'):
            try:
                fhr = int(parts[2][1:])
                if fhr in fhrs:
                    shutil.rmtree(entry, ignore_errors=True)
                    removed += 1
            except ValueError:
                pass
    return removed


def convert_fhr(fhr):
    """Convert a single FHR from GRIB. Returns (fhr, seconds, status)."""
    from core.cross_section_interactive import InteractiveCrossSection
    backend = os.environ.get('XSECT_GRIB_BACKEND', 'auto')
    xsect = InteractiveCrossSection(cache_dir=str(CACHE_BASE / MODEL), grib_backend=backend)

    fhr_dir = GRIB_BASE / f"F{fhr:02d}"
    prs = sorted(fhr_dir.glob("*wrfprs*.grib2"))
    sfc = sorted(fhr_dir.glob("*wrfsfc*.grib2"))

    if not prs:
        return fhr, 0, "no prs file"

    t0 = time.perf_counter()
    try:
        ok = xsect.load_forecast_hour(str(prs[0]), fhr)
        elapsed = time.perf_counter() - t0
        return fhr, elapsed, "ok" if ok else "failed"
    except Exception as e:
        elapsed = time.perf_counter() - t0
        return fhr, elapsed, str(e)[:100]


def bench_thread_scaling(fhrs):
    """Benchmark ThreadPoolExecutor with different worker counts.

    Uses non-overlapping FHR slices so each test does fresh GRIB conversion.
    Windows locks mmap'd files, so cache can't be cleared within a process.
    """
    # Each test gets its own slice of FHRs (no overlap)
    tests = [
        (1, 2),   # 1 worker, 2 FHRs — baseline
        (2, 2),   # 2 workers, 2 FHRs
        (4, 4),   # 4 workers, 4 FHRs
        (8, 8),   # 8 workers, 8 FHRs
    ]

    # Calculate slices
    offset = 0
    test_plan = []
    for n_workers, n_fhrs in tests:
        n_fhrs = min(n_fhrs, len(fhrs) - offset)
        if n_fhrs <= 0:
            break
        test_plan.append((n_workers, fhrs[offset:offset + n_fhrs]))
        offset += n_fhrs

    print(f"\n{'='*60}")
    print("  ThreadPoolExecutor GRIB->mmap Scaling (eccodes)")
    print(f"  Using {offset} FHRs from: {fhrs[:offset]}")
    print(f"  Non-overlapping slices (Windows mmap lock workaround)")
    print(f"{'='*60}")

    baseline_per_fhr = None

    for n_workers, test_fhrs in test_plan:
        # Clear cache for these FHRs (may fail on Windows due to mmap locks
        # but that's ok since we use non-overlapping slices)
        clear_cache(test_fhrs)
        time.sleep(0.5)

        print(f"\n  --- {n_workers} worker(s), {len(test_fhrs)} FHRs: {test_fhrs} ---")
        wall_t0 = time.perf_counter()

        with ThreadPoolExecutor(max_workers=n_workers) as pool:
            futures = {pool.submit(convert_fhr, fhr): fhr for fhr in test_fhrs}
            results = []
            for fut in as_completed(futures):
                fhr, elapsed, status = fut.result()
                results.append((fhr, elapsed, status))
                print(f"    F{fhr:02d}: {elapsed:.1f}s [{status}]")

        wall = time.perf_counter() - wall_t0
        ok_times = [e for _, e, s in results if s == "ok"]
        if ok_times:
            avg_per_fhr = statistics.mean(ok_times)
            throughput = len(ok_times) / wall
            if baseline_per_fhr is None:
                baseline_per_fhr = avg_per_fhr
            # Speedup = how much faster than doing them all sequentially
            expected_sequential = avg_per_fhr * len(ok_times)
            speedup = expected_sequential / wall if wall > 0 else 0
            print(f"  WALL: {wall:.1f}s | avg/FHR: {avg_per_fhr:.1f}s | "
                  f"throughput: {throughput:.2f} FHR/s | speedup: {speedup:.1f}x")


if __name__ == "__main__":
    print("GRIB-to-Mmap Conversion Benchmark (Native Windows)")
    print(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Backend: {os.environ.get('XSECT_GRIB_BACKEND', 'auto')}")

    test_fhrs = get_test_fhrs()
    print(f"Available FHRs: {test_fhrs}")

    # Need enough uncached FHRs for non-overlapping slices
    # Tests: 1w*2 + 2w*2 + 4w*4 + 8w*8 = 16 FHRs
    fhrs = test_fhrs[:16]
    bench_thread_scaling(fhrs)

    print(f"\n{'='*60}")
    print("DONE")
    print(f"{'='*60}")
