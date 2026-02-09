"""Benchmark suite for wxsection.com on native Windows."""
import time
import requests
import statistics
import concurrent.futures

BASE = "http://127.0.0.1:5565"

# Cross-section line: Oklahoma City to Dallas (~300km)
XSECT_PARAMS = "start_lat=35.4&start_lon=-97.5&end_lat=32.8&end_lon=-96.8"
CYCLE = "20260207_22z"
STYLES = ["temp", "wind_speed", "rh", "composite", "theta_e"]

def timed(label, fn, runs=3):
    """Run fn `runs` times, print stats."""
    times = []
    for i in range(runs):
        t0 = time.perf_counter()
        result = fn()
        elapsed = time.perf_counter() - t0
        times.append(elapsed)
        status = result.status_code if hasattr(result, 'status_code') else 'ok'
        size = len(result.content) if hasattr(result, 'content') else 0
        size_kb = size / 1024
        print(f"  {label} run {i+1}: {elapsed:.3f}s  (status={status}, {size_kb:.0f}KB)")
    avg = statistics.mean(times)
    mn = min(times)
    mx = max(times)
    med = statistics.median(times)
    print(f"  => avg={avg:.3f}s  min={mn:.3f}s  max={mx:.3f}s  median={med:.3f}s")
    print()
    return times

def xsect_url(fhr=6, style="temp", model="hrrr"):
    return f"{BASE}/api/xsect?{XSECT_PARAMS}&cycle={CYCLE}&fhr={fhr}&style={style}&model={model}"

def bench_api_latency():
    """Benchmark API endpoint latency (no render)."""
    print("=" * 60)
    print("1. API LATENCY (no render)")
    print("=" * 60)
    timed("/api/status", lambda: requests.get(f"{BASE}/api/status"), runs=5)
    timed("/api/cycles", lambda: requests.get(f"{BASE}/api/cycles?model=hrrr"), runs=5)

def bench_cross_section():
    """Benchmark single cross-section render for each style."""
    print("=" * 60)
    print("2. CROSS-SECTION RENDER (warm, single frame)")
    print("   OKC -> Dallas, 22z cycle, F06")
    print("=" * 60)
    all_times = {}
    for style in STYLES:
        url = xsect_url(fhr=6, style=style)
        times = timed(f"style={style}", lambda u=url: requests.get(u), runs=3)
        all_times[style] = times

    print("-" * 40)
    print("Style render summary (median):")
    for style, times in all_times.items():
        med = statistics.median(times)
        print(f"  {style:15s}: {med:.3f}s")
    print()

def bench_cached_frame():
    """Benchmark fetching an already-rendered frame (cache hit)."""
    print("=" * 60)
    print("3. CACHED FRAME FETCH (same params = cache hit)")
    print("=" * 60)
    url = xsect_url(fhr=0, style="temp")
    # Warm the cache
    print("  (warming cache...)")
    requests.get(url)
    time.sleep(0.5)
    # Now re-fetch — should be cached
    timed("cached temp F00", lambda: requests.get(url), runs=5)

def bench_concurrent_renders():
    """Benchmark concurrent cross-section renders."""
    print("=" * 60)
    print("4. CONCURRENT RENDERS (6 parallel, different FHRs)")
    print("=" * 60)

    urls = [xsect_url(fhr=fhr, style="temp") for fhr in range(0, 6)]

    def fetch_all():
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
            futures = [pool.submit(requests.get, url) for url in urls]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]
        return results

    for i in range(3):
        t0 = time.perf_counter()
        results = fetch_all()
        elapsed = time.perf_counter() - t0
        ok = sum(1 for r in results if r.status_code == 200)
        print(f"  Run {i+1}: {elapsed:.3f}s  ({ok}/6 succeeded)")
    print()

def bench_multi_style():
    """Benchmark rendering all styles for one FHR (sequential)."""
    print("=" * 60)
    print("5. ALL STYLES SEQUENTIAL (1 FHR, all styles)")
    print("=" * 60)

    all_styles = ["temp", "wind_speed", "rh", "composite", "theta_e",
                  "omega", "vorticity", "divergence", "frontogenesis",
                  "icing", "turbulence"]

    total_t0 = time.perf_counter()
    results = {}
    for style in all_styles:
        url = xsect_url(fhr=6, style=style)
        t0 = time.perf_counter()
        r = requests.get(url)
        elapsed = time.perf_counter() - t0
        results[style] = (elapsed, r.status_code)
        status_icon = "OK" if r.status_code == 200 else f"ERR {r.status_code}"
        print(f"  {style:20s}: {elapsed:.3f}s  [{status_icon}]")
    total = time.perf_counter() - total_t0

    ok_times = [t for t, s in results.values() if s == 200]
    if ok_times:
        print(f"\n  Total: {total:.3f}s for {len(ok_times)} styles")
        print(f"  Avg per style: {statistics.mean(ok_times):.3f}s")
    print()

def bench_different_lines():
    """Benchmark renders with different cross-section lines."""
    print("=" * 60)
    print("6. DIFFERENT LINES (varying length cross-sections)")
    print("=" * 60)

    lines = {
        "short (~100km)": "35.4,-97.5,34.5,-97.0",
        "medium (~300km)": "35.4,-97.5,32.8,-96.8",
        "long (~800km)":  "35.4,-97.5,29.7,-95.3",
        "very long (~1500km)": "47.6,-122.3,34.0,-118.2",
    }

    for label, coords in lines.items():
        parts = coords.split(",")
        params = f"start_lat={parts[0]}&start_lon={parts[1]}&end_lat={parts[2]}&end_lon={parts[3]}"
        url = f"{BASE}/api/xsect?{params}&cycle={CYCLE}&fhr=6&style=temp&model=hrrr"
        timed(label, lambda u=url: requests.get(u), runs=2)

if __name__ == "__main__":
    print()
    print("=" * 60)
    print("  wxsection.com Native Windows Benchmark")
    print(f"  {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    print()

    bench_api_latency()
    bench_cross_section()
    bench_cached_frame()
    bench_concurrent_renders()
    bench_multi_style()
    bench_different_lines()

    print("=" * 60)
    print("DONE")
    print("=" * 60)
