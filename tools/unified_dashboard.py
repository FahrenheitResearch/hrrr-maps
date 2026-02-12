#!/usr/bin/env python3
"""
HRRR Cross-Section Dashboard

Interactive cross-section visualization on a Leaflet map.
Draw a line on the map to generate vertical cross-sections.

Usage:
    python tools/unified_dashboard.py --data-dir outputs/hrrr/20251227/09z
    python tools/unified_dashboard.py --auto-update
"""

import argparse
import json
import logging
import os
import sys
import time
import io
import tempfile
import threading
from pathlib import Path
from datetime import datetime
from functools import wraps
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed

import imageio.v2 as imageio
from PIL import Image

from flask import Flask, jsonify, request, send_file, abort, Response

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.map_overlay import MapOverlayEngine, OVERLAY_FIELDS, get_colormap_lut, PRODUCT_PRESETS, ContourSpec, BarbSpec, CompositeSpec

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)


@app.after_request
def add_response_headers(response):
    """Add CORS for public API + security headers on all responses."""
    if request.path.startswith('/api/v1/'):
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    # Security headers
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    return response


# =============================================================================
# CONFIGURATION
# =============================================================================

EVENTS_FILE = Path(__file__).parent.parent / 'events.json'
VOTES_FILE = Path(__file__).parent.parent / 'data' / 'votes.json'
REQUESTS_FILE = Path(__file__).parent.parent / 'data' / 'requests.json'
FAVORITES_FILE = Path(__file__).parent.parent / 'data' / 'favorites.json'
DISK_META_FILE = Path(__file__).parent.parent / 'data' / 'disk_meta.json'
DISK_LIMIT_GB = 1000  # Max disk usage for HRRR data (GRIB source on VHD)
CACHE_LIMIT_GB = 2000  # Max NVMe cache for mmap files (4TB drive, ~2TB free)
CLIMATOLOGY_DIR = Path(os.environ.get('CLIMATOLOGY_DIR', str(Path(__file__).resolve().parent.parent / 'climatology')))

# Styles that support anomaly mode (must match ANOMALY_STYLES in cross_section_interactive.py)
ANOMALY_STYLES = {
    'temp', 'wind_speed', 'rh', 'omega', 'theta_e',
    'q', 'vorticity', 'shear', 'lapse_rate', 'wetbulb',
}

# --- v1 API: product name mapping and metadata ---
PRODUCT_TO_STYLE = {
    'temperature': 'temp', 'temp': 'temp',
    'wind_speed': 'wind_speed', 'wind': 'wind_speed',
    'theta_e': 'theta_e',
    'relative_humidity': 'rh', 'rh': 'rh',
    'vertical_velocity': 'omega', 'omega': 'omega',
    'specific_humidity': 'q', 'q': 'q',
    'vorticity': 'vorticity',
    'wind_shear': 'shear', 'shear': 'shear',
    'lapse_rate': 'lapse_rate',
    'cloud': 'cloud_total', 'cloud_total': 'cloud_total',
    'wetbulb': 'wetbulb', 'wet_bulb': 'wetbulb',
    'icing': 'icing',
    'frontogenesis': 'frontogenesis',
    'smoke': 'smoke',
    'vpd': 'vpd', 'vapor_pressure_deficit': 'vpd',
    'dewpoint_dep': 'dewpoint_dep', 'dewpoint_depression': 'dewpoint_dep',
    'moisture_transport': 'moisture_transport',
    'pv': 'pv', 'potential_vorticity': 'pv',
    'fire_wx': 'fire_wx', 'fire_weather': 'fire_wx',
    'isentropic_ascent': 'isentropic_ascent',
}
PRODUCTS_INFO = [
    {'id': 'temperature', 'name': 'Temperature', 'units': '\u00b0C'},
    {'id': 'wind_speed', 'name': 'Wind Speed', 'units': 'knots'},
    {'id': 'theta_e', 'name': 'Equivalent Potential Temperature', 'units': 'K'},
    {'id': 'rh', 'name': 'Relative Humidity', 'units': '%'},
    {'id': 'omega', 'name': 'Vertical Velocity', 'units': 'hPa/hr'},
    {'id': 'q', 'name': 'Specific Humidity', 'units': 'g/kg'},
    {'id': 'vorticity', 'name': 'Absolute Vorticity', 'units': '10\u207b\u2075 s\u207b\u00b9'},
    {'id': 'shear', 'name': 'Wind Shear', 'units': '10\u207b\u00b3 s\u207b\u00b9'},
    {'id': 'lapse_rate', 'name': 'Lapse Rate', 'units': '\u00b0C/km'},
    {'id': 'cloud_total', 'name': 'Cloud Total Condensate', 'units': 'g/kg'},
    {'id': 'wetbulb', 'name': 'Wet-Bulb Temperature', 'units': '\u00b0C'},
    {'id': 'icing', 'name': 'Icing Potential', 'units': 'g/kg'},
    {'id': 'frontogenesis', 'name': 'Frontogenesis', 'units': 'K/100km/3hr'},
    {'id': 'smoke', 'name': 'PM2.5 Smoke', 'units': '\u03bcg/m\u00b3'},
    {'id': 'vpd', 'name': 'Vapor Pressure Deficit', 'units': 'hPa'},
    {'id': 'dewpoint_dep', 'name': 'Dewpoint Depression', 'units': '\u00b0C'},
    {'id': 'moisture_transport', 'name': 'Moisture Transport', 'units': 'g\u00b7m/kg/s'},
    {'id': 'pv', 'name': 'Potential Vorticity', 'units': 'PVU'},
    {'id': 'fire_wx', 'name': 'Fire Weather Composite', 'units': 'RH% + wind'},
    {'id': 'isentropic_ascent', 'name': 'Isentropic Ascent', 'units': 'RH% + \u03c9 + V\u2097'},
]

# --- Events cache (loaded once at import time) ---
EVENTS_DATA = {}  # cycle_key -> event dict (loaded from events.json)
if EVENTS_FILE.exists():
    try:
        with open(EVENTS_FILE, encoding='utf-8') as _ef:
            EVENTS_DATA = json.load(_ef)
        logger.info(f"Loaded {len(EVENTS_DATA)} events from {EVENTS_FILE}")
    except Exception as _e:
        logger.warning(f"Failed to load events.json: {_e}")

def load_votes():
    """Load votes from JSON file."""
    if VOTES_FILE.exists():
        try:
            with open(VOTES_FILE) as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_votes(votes):
    """Save votes to JSON file."""
    VOTES_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(VOTES_FILE, 'w') as f:
        json.dump(votes, f, indent=2)

def load_requests():
    """Load feature requests from JSON file."""
    if REQUESTS_FILE.exists():
        try:
            with open(REQUESTS_FILE) as f:
                return json.load(f)
        except:
            return []
    return []

def save_request(name, text):
    """Save a new feature request."""
    REQUESTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    requests = load_requests()
    requests.append({
        'name': name,
        'text': text,
        'timestamp': datetime.now().isoformat()
    })
    with open(REQUESTS_FILE, 'w') as f:
        json.dump(requests, f, indent=2)

def load_favorites():
    """Load community favorites from JSON file."""
    if FAVORITES_FILE.exists():
        try:
            with open(FAVORITES_FILE) as f:
                favorites = json.load(f)
            # Clean up old favorites (>12 hours) but keep at least the name
            now = datetime.now()
            cleaned = []
            for fav in favorites:
                try:
                    created = datetime.fromisoformat(fav.get('created', ''))
                    age_hours = (now - created).total_seconds() / 3600
                    if age_hours < 12 or fav.get('permanent', False):
                        cleaned.append(fav)
                except:
                    cleaned.append(fav)  # Keep if can't parse date
            return cleaned
        except:
            return []
    return []

def save_favorite(name, config, label=''):
    """Save a new community favorite."""
    FAVORITES_FILE.parent.mkdir(parents=True, exist_ok=True)
    favorites = load_favorites()
    # Generate unique ID
    import hashlib
    fav_id = hashlib.md5(f"{name}{datetime.now().isoformat()}".encode()).hexdigest()[:8]
    favorites.append({
        'id': fav_id,
        'name': name,
        'label': label,
        'config': config,
        'created': datetime.now().isoformat()
    })
    with open(FAVORITES_FILE, 'w') as f:
        json.dump(favorites, f, indent=2)
    return fav_id

def delete_favorite(fav_id):
    """Delete a community favorite by ID."""
    favorites = load_favorites()
    favorites = [f for f in favorites if f.get('id') != fav_id]
    with open(FAVORITES_FILE, 'w') as f:
        json.dump(favorites, f, indent=2)

def load_disk_meta():
    """Load disk metadata (last-accessed times, request source)."""
    if DISK_META_FILE.exists():
        try:
            with open(DISK_META_FILE) as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_disk_meta(meta):
    """Save disk metadata."""
    DISK_META_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(DISK_META_FILE, 'w') as f:
        json.dump(meta, f, indent=2)

def touch_cycle_access(cycle_key):
    """Mark a cycle as recently accessed (for popularity tracking)."""
    meta = load_disk_meta()
    if cycle_key not in meta:
        meta[cycle_key] = {}
    meta[cycle_key]['last_accessed'] = time.time()
    meta[cycle_key]['access_count'] = meta[cycle_key].get('access_count', 0) + 1
    save_disk_meta(meta)

def get_disk_usage_gb():
    """Get total disk usage of HRRR data directory in GB."""
    base = Path(os.environ.get('XSECT_OUTPUTS_DIR', 'outputs')) / 'hrrr'
    if not base.exists():
        return 0
    total = sum(f.stat().st_size for f in base.rglob("*") if f.is_file())
    return total / (1024 ** 3)

def disk_evict_least_popular(target_gb=None):
    """Evict least-recently-accessed cycles from disk until under target_gb.

    Never evicts cycles accessed in the last 2 hours (likely still in use).
    """
    import shutil
    if target_gb is None:
        target_gb = DISK_LIMIT_GB * 0.85  # Evict down to 85% of limit

    base = Path(os.environ.get('XSECT_OUTPUTS_DIR', 'outputs')) / 'hrrr'
    if not base.exists():
        return

    usage = get_disk_usage_gb()
    if usage <= target_gb:
        return

    meta = load_disk_meta()
    now = time.time()
    recent_cutoff = now - 7200  # Don't evict anything accessed in last 2 hours

    # Build list of all cycles on disk with their last access time
    disk_cycles = []
    for date_dir in base.iterdir():
        if not date_dir.is_dir() or not date_dir.name.isdigit():
            continue
        for hour_dir in date_dir.iterdir():
            if not hour_dir.is_dir() or not hour_dir.name.endswith('z'):
                continue
            hour = hour_dir.name.replace('z', '')
            cycle_key = f"{date_dir.name}_{hour}z"
            last_access = meta.get(cycle_key, {}).get('last_accessed', 0)
            if last_access > recent_cutoff:
                continue  # Skip recently used
            disk_cycles.append((last_access, cycle_key, hour_dir))

    # Sort by last access (oldest first = evict first)
    disk_cycles.sort()

    for last_access, cycle_key, hour_dir in disk_cycles:
        if get_disk_usage_gb() <= target_gb:
            break
        logger.info(f"Disk evict: {cycle_key} (last accessed {int((now - last_access)/3600)}h ago)")
        try:
            shutil.rmtree(hour_dir)
            # Clean up empty parent date dir
            parent = hour_dir.parent
            if parent.exists() and not any(parent.iterdir()):
                parent.rmdir()
            # Remove from meta
            meta.pop(cycle_key, None)
        except Exception as e:
            logger.warning(f"Failed to evict {cycle_key}: {e}")

    save_disk_meta(meta)


def get_cache_usage_gb(managers: dict) -> float:
    """Get total NVMe cache usage across all models in GB."""
    total = 0
    for model_name, mgr in managers.items():
        cache_dir = Path(mgr.CACHE_BASE) / model_name
        if cache_dir.exists():
            total += sum(f.stat().st_size for f in cache_dir.rglob("*") if f.is_file())
    return total / (1024 ** 3)


def _evict_cache_dirs(dirs, label):
    """Delete a list of cache directories."""
    import shutil
    for d in dirs:
        try:
            shutil.rmtree(d)
        except Exception as e:
            logger.warning(f"Cache evict failed for {d.name}: {e}")
    total_gb = len(dirs) * 2.3
    logger.info(f"Cache evict: {label} — removed {len(dirs)} FHRs (~{total_gb:.0f}GB)")


def cache_evict_old_cycles(managers: dict):
    """Two-tier NVMe cache eviction.

    Tier 1 (always): Rotated preload cycles — if a cycle falls out of the target
    window and wasn't an archive request, delete its cache immediately regardless
    of disk space.

    Tier 2 (size-based): Archive request caches — only evict when total cache
    exceeds CACHE_LIMIT_GB (670GB). Oldest archive caches go first.
    """
    import re

    for model_name, mgr in managers.items():
        cache_dir = Path(mgr.CACHE_BASE) / model_name
        if not cache_dir.exists():
            continue

        # Build key sets
        target_keys = {c['cycle_key'] for c in mgr._get_target_cycles()}
        with mgr._lock:
            loaded_keys = {ck for ck, _ in mgr.loaded_items}

        # Scan cache dirs and group by cycle key (format: YYYYMMDD_HHz_F##_...)
        cycle_dirs = {}
        for entry in cache_dir.iterdir():
            if not entry.is_dir():
                continue
            m = re.match(r'(\d{8}_\d{2}z)_', entry.name)
            if m:
                ck = m.group(1)
                cycle_dirs.setdefault(ck, []).append(entry)

        # Tier 1: Always evict rotated preload cycles (not target, not loaded, not archive)
        from datetime import datetime, timedelta
        archive_cutoff = (datetime.utcnow() - timedelta(days=7)).strftime('%Y%m%d')
        for ck, dirs in cycle_dirs.items():
            if ck in target_keys or ck in loaded_keys or ck in ARCHIVE_CACHE_KEYS:
                continue
            # Never auto-evict cycles older than 7 days — they're intentional archive data
            ck_date = ck.split('_')[0]
            if ck_date < archive_cutoff:
                ARCHIVE_CACHE_KEYS.add(ck)
                continue
            _evict_cache_dirs(dirs, f"{model_name} {ck} (rotated out)")

    # Tier 2: Size-based eviction of archive caches
    usage_gb = get_cache_usage_gb(managers)
    if usage_gb <= CACHE_LIMIT_GB:
        return

    logger.info(f"Cache usage {usage_gb:.0f}GB > {CACHE_LIMIT_GB}GB limit, evicting archive caches...")
    import re
    target_gb = CACHE_LIMIT_GB * 0.85

    # Collect all evictable archive caches across models, sorted oldest first
    evictable = []
    for model_name, mgr in managers.items():
        cache_dir = Path(mgr.CACHE_BASE) / model_name
        if not cache_dir.exists():
            continue
        target_keys = {c['cycle_key'] for c in mgr._get_target_cycles()}
        with mgr._lock:
            loaded_keys = {ck for ck, _ in mgr.loaded_items}

        for entry in cache_dir.iterdir():
            if not entry.is_dir():
                continue
            m = re.match(r'(\d{8}_\d{2}z)_', entry.name)
            if not m:
                continue
            ck = m.group(1)
            if ck in target_keys or ck in loaded_keys:
                continue
            evictable.append((ck, entry, model_name))

    # Sort by cycle key (oldest first)
    evictable.sort(key=lambda x: x[0])

    removed_keys = set()
    for ck, d, model_name in evictable:
        if get_cache_usage_gb(managers) <= target_gb:
            break
        try:
            import shutil
            shutil.rmtree(d)
        except Exception as e:
            logger.warning(f"Cache evict failed for {d.name}: {e}")
        if ck not in removed_keys:
            logger.info(f"Cache evict: {model_name} {ck} (archive, over size limit)")
            removed_keys.add(ck)
    # Clean up ARCHIVE_CACHE_KEYS for fully evicted cycles
    ARCHIVE_CACHE_KEYS.difference_update(removed_keys)


CONUS_BOUNDS = {
    'south': 21.14, 'north': 52.62,
    'west': -134.10, 'east': -60.92,
}

XSECT_STYLES = [
    ('wind_speed', 'Wind Speed'),
    ('temp', 'Temperature'),
    ('theta_e', 'Theta-E'),
    ('rh', 'Relative Humidity'),
    ('q', 'Specific Humidity'),
    ('omega', 'Vertical Velocity'),
    ('vorticity', 'Vorticity'),
    ('shear', 'Wind Shear'),
    ('lapse_rate', 'Lapse Rate'),
    ('cloud', 'Cloud Water'),
    ('cloud_total', 'Total Condensate'),
    ('wetbulb', 'Wet-Bulb Temp'),
    ('icing', 'Icing Potential'),
    ('frontogenesis', '❄ Frontogenesis'),  # Winter Bander mode
    ('smoke', 'PM2.5 Smoke'),
    ('vpd', 'Vapor Pressure Deficit'),
    ('dewpoint_dep', 'Dewpoint Depression'),
    ('moisture_transport', 'Moisture Transport'),
    ('pv', 'Potential Vorticity'),
    ('fire_wx', '🔥 Fire Weather'),
    ('isentropic_ascent', 'Isentropic Ascent'),
]

# =============================================================================
# RATE LIMITING
# =============================================================================

class RateLimiter:
    def __init__(self, rpm=60, burst=10):
        self.rpm, self.burst = rpm, burst
        self.requests = defaultdict(list)
        self.lock = threading.Lock()

    def is_allowed(self, ip):
        now = time.time()
        with self.lock:
            self.requests[ip] = [t for t in self.requests[ip] if t > now - 60]
            if len(self.requests[ip]) >= self.rpm:
                return False
            if len([t for t in self.requests[ip] if t > now - 1]) >= self.burst:
                return False
            self.requests[ip].append(now)
            return True

rate_limiter = RateLimiter()

# Limit concurrent matplotlib renders to prevent CPU/memory thrash under load
# 12 = up to 8 prerender workers + 4 live user requests
RENDER_SEMAPHORE = threading.Semaphore(12)
PRERENDER_WORKERS = 8  # Parallel processes for batch prerender (true parallelism, separate GILs)

# =============================================================================
# PERSISTENT RENDER POOL — stays alive between prerender calls
# =============================================================================
_RENDER_POOL = None          # ProcessPoolExecutor instance
_RENDER_POOL_LOCK = threading.Lock()
_RENDER_POOL_CONFIG = None   # config dict used to init current pool


def _get_render_pool(pool_config, project_dir):
    """Get or create persistent render pool. Recreates if config changes."""
    global _RENDER_POOL, _RENDER_POOL_CONFIG
    config_key = (project_dir, pool_config['cache_dir'], tuple(pool_config['extra_cache_dirs']),
                  pool_config['model_name'], pool_config['min_levels'], pool_config['grib_backend'])

    with _RENDER_POOL_LOCK:
        if _RENDER_POOL is not None and _RENDER_POOL_CONFIG == config_key:
            # Check pool is still alive by submitting a no-op
            try:
                _RENDER_POOL.submit(int, 0).result(timeout=5)
                return _RENDER_POOL
            except Exception:
                logger.warning("Render pool dead, recreating")
                try:
                    _RENDER_POOL.shutdown(wait=False)
                except Exception:
                    pass
                _RENDER_POOL = None

        # Shutdown old pool if config changed
        if _RENDER_POOL is not None:
            logger.info("Render pool config changed, recreating")
            try:
                _RENDER_POOL.shutdown(wait=False)
            except Exception:
                pass
            _RENDER_POOL = None

        from tools.render_worker import init_worker
        logger.info(f"Creating persistent render pool ({PRERENDER_WORKERS} workers, model={pool_config['model_name']})")
        _RENDER_POOL = ProcessPoolExecutor(
            max_workers=PRERENDER_WORKERS,
            initializer=init_worker,
            initargs=(project_dir, pool_config['cache_dir'],
                      pool_config['extra_cache_dirs'], pool_config['model_name'],
                      pool_config['min_levels'], pool_config['grib_backend']),
        )
        _RENDER_POOL_CONFIG = config_key
        return _RENDER_POOL


def shutdown_render_pool():
    """Shut down the persistent render pool (call on exit)."""
    global _RENDER_POOL
    with _RENDER_POOL_LOCK:
        if _RENDER_POOL is not None:
            logger.info("Shutting down render pool")
            try:
                _RENDER_POOL.shutdown(wait=False)
            except Exception:
                pass
            _RENDER_POOL = None


# =============================================================================
# PERSISTENT GRIB POOL — separate pool for GRIB→mmap conversion
# =============================================================================
_GRIB_POOL = None
_GRIB_POOL_LOCK = threading.Lock()
_GRIB_POOL_CONFIG = None
GRIB_POOL_WORKERS = 6  # Overridden by --grib-workers at startup


def _get_grib_pool(pool_config, project_dir):
    """Get or create persistent GRIB conversion pool. Recreates if config changes."""
    global _GRIB_POOL, _GRIB_POOL_CONFIG
    config_key = (project_dir, pool_config['cache_dir'], tuple(pool_config['extra_cache_dirs']),
                  pool_config['model_name'], pool_config['min_levels'], pool_config['grib_backend'])

    with _GRIB_POOL_LOCK:
        if _GRIB_POOL is not None and _GRIB_POOL_CONFIG == config_key:
            try:
                _GRIB_POOL.submit(int, 0).result(timeout=5)
                return _GRIB_POOL
            except Exception:
                logger.warning("GRIB pool dead, recreating")
                try:
                    _GRIB_POOL.shutdown(wait=False)
                except Exception:
                    pass
                _GRIB_POOL = None

        if _GRIB_POOL is not None:
            logger.info("GRIB pool config changed, recreating")
            try:
                _GRIB_POOL.shutdown(wait=False)
            except Exception:
                pass
            _GRIB_POOL = None

        from tools.render_worker import init_worker
        logger.info(f"Creating persistent GRIB pool ({GRIB_POOL_WORKERS} workers, model={pool_config['model_name']})")
        _GRIB_POOL = ProcessPoolExecutor(
            max_workers=GRIB_POOL_WORKERS,
            initializer=init_worker,
            initargs=(project_dir, pool_config['cache_dir'],
                      pool_config['extra_cache_dirs'], pool_config['model_name'],
                      pool_config['min_levels'], pool_config['grib_backend']),
        )
        _GRIB_POOL_CONFIG = config_key
        return _GRIB_POOL


def shutdown_grib_pool():
    """Shut down the persistent GRIB pool (call on exit)."""
    global _GRIB_POOL
    with _GRIB_POOL_LOCK:
        if _GRIB_POOL is not None:
            logger.info("Shutting down GRIB pool")
            try:
                _GRIB_POOL.shutdown(wait=False)
            except Exception:
                pass
            _GRIB_POOL = None


# =============================================================================
# FRAME PRERENDER CACHE — stores rendered PNG bytes for slider/comparison
# =============================================================================
FRAME_CACHE = {}            # cache_key -> PNG bytes
FRAME_CACHE_LOCK = threading.Lock()
MAX_FRAME_CACHE = 500       # ~500 * 150KB = ~75MB max

def frame_cache_key(model, cycle_key, fhr, style, start, end, y_axis, vscale, y_top, units, temp_cmap, anomaly):
    """Deterministic cache key for a rendered frame."""
    return f"{model}:{cycle_key}:F{fhr:02d}:{style}:{start[0]:.4f},{start[1]:.4f}:{end[0]:.4f},{end[1]:.4f}:{y_axis}:{vscale}:{y_top}:{units}:{temp_cmap}:{anomaly}"

def frame_cache_put(key, png_bytes):
    """Store a rendered frame, evicting oldest if full."""
    with FRAME_CACHE_LOCK:
        FRAME_CACHE[key] = png_bytes
        while len(FRAME_CACHE) > MAX_FRAME_CACHE:
            oldest = next(iter(FRAME_CACHE))
            del FRAME_CACHE[oldest]

def frame_cache_get(key):
    """Retrieve cached frame or None."""
    with FRAME_CACHE_LOCK:
        return FRAME_CACHE.get(key)

# =============================================================================
# OVERLAY PRERENDER CACHE — stores rendered overlay PNG bytes per FHR/product
# =============================================================================
OVERLAY_CACHE = {}              # cache_key -> PNG bytes
OVERLAY_CACHE_LOCK = threading.Lock()
MAX_OVERLAY_CACHE = 500         # ~500 * 150KB = ~75MB max (multiple products)

def overlay_cache_key(model, cycle_key, fhr, product_or_field, level=None):
    """Deterministic cache key for an overlay frame."""
    return f"overlay:{model}:{cycle_key}:F{fhr:02d}:{product_or_field}:{level or 'sfc'}"

def overlay_cache_put(key, png_bytes):
    """Store a rendered overlay frame, evicting oldest if full."""
    with OVERLAY_CACHE_LOCK:
        OVERLAY_CACHE[key] = png_bytes
        while len(OVERLAY_CACHE) > MAX_OVERLAY_CACHE:
            oldest = next(iter(OVERLAY_CACHE))
            del OVERLAY_CACHE[oldest]

def overlay_cache_get(key):
    """Retrieve cached overlay frame or None."""
    with OVERLAY_CACHE_LOCK:
        return OVERLAY_CACHE.get(key)

AUTO_PRERENDER_PRODUCTS = ['surface_analysis', 'fire_weather']  # products to prerender on cycle load

def auto_prerender_overlay(mgr, model_name: str, cycle_key: str, product: str = 'surface_analysis'):
    """Background: prerender overlay frames for all loaded FHRs of a cycle.
    Called automatically after cycle load completes."""
    try:
        from core.map_overlay import PRODUCT_PRESETS, MapOverlayEngine
        spec = PRODUCT_PRESETS.get(product)
        if not spec:
            return

        # Collect loaded FHRs for this cycle
        fhrs = sorted(fhr for ck, fhr in mgr.loaded_items if ck == cycle_key)
        if not fhrs:
            return

        # Skip if all already cached
        to_render = [f for f in fhrs if not overlay_cache_get(
            overlay_cache_key(model_name, cycle_key, f, product))]
        if not to_render:
            return

        cache_dir = mgr.cache_dir if hasattr(mgr, 'cache_dir') else ''
        engine = _get_overlay_engine(model_name, cache_dir)
        rendered = 0
        for fhr in to_render:
            fhr_data = mgr.get_forecast_hour(cycle_key, fhr)
            if fhr_data is None:
                continue
            try:
                result = engine.render_composite(fhr_data, spec, opacity=1.0)
                webp_data = _png_to_webp(result.data)
                key = overlay_cache_key(model_name, cycle_key, fhr, product)
                overlay_cache_put(key, webp_data)
                rendered += 1
            except Exception as exc:
                logger.debug(f"Overlay prerender {cycle_key} F{fhr:02d}: {exc}")
        if rendered:
            logger.info(f"Auto-prerendered {rendered} overlay frames for {model_name} {cycle_key} ({product})")
    except Exception as e:
        logger.warning(f"Overlay auto-prerender failed: {e}")


def auto_prerender_overlay_all_products(mgr, model_name: str, cycle_key: str):
    """Background: prerender overlay frames for all default products."""
    for product in AUTO_PRERENDER_PRODUCTS:
        auto_prerender_overlay(mgr, model_name, cycle_key, product=product)

MAPBOX_TOKEN = os.environ.get('MAPBOX_TOKEN', '')

def rate_limit(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not rate_limiter.is_allowed(request.remote_addr):
            return jsonify({'error': 'Rate limit exceeded'}), 429
        return f(*args, **kwargs)
    return decorated

# =============================================================================
# PROGRESS TRACKING
# =============================================================================

PROGRESS = {}  # Global progress dict: op_id -> {op, label, step, total, detail, started, done, done_at, ...}

def progress_update(op_id, step, total, detail, label=None):
    """Update progress for an operation."""
    now = time.time()
    if op_id not in PROGRESS:
        PROGRESS[op_id] = {
            'op': op_id.split(':')[0],
            'label': label or op_id,
            'step': step,
            'total': total,
            'detail': detail,
            'started': now,
            'done': False,
            'done_at': None,
            'last_step_at': now,
            'rate_history': [],  # (timestamp, step) for rate estimation
        }
    else:
        prev_step = PROGRESS[op_id]['step']
        PROGRESS[op_id]['step'] = step
        PROGRESS[op_id]['total'] = total
        PROGRESS[op_id]['detail'] = detail
        if label:
            PROGRESS[op_id]['label'] = label
        # Track rate for ETA
        if step > prev_step:
            PROGRESS[op_id]['last_step_at'] = now
            hist = PROGRESS[op_id]['rate_history']
            hist.append((now, step))
            # Keep last 20 data points
            if len(hist) > 20:
                PROGRESS[op_id]['rate_history'] = hist[-20:]

def progress_done(op_id):
    """Mark an operation as complete."""
    if op_id in PROGRESS:
        PROGRESS[op_id]['done'] = True
        PROGRESS[op_id]['done_at'] = time.time()
        PROGRESS[op_id]['step'] = PROGRESS[op_id]['total']
        PROGRESS[op_id]['detail'] = 'Done'

def progress_remove(op_id):
    """Remove a progress entry."""
    PROGRESS.pop(op_id, None)

def progress_cleanup():
    """Remove entries that finished more than 8s ago."""
    now = time.time()
    to_remove = [k for k, v in PROGRESS.items() if v.get('done') and v.get('done_at') and now - v['done_at'] > 8]
    for k in to_remove:
        del PROGRESS[k]
    # Also clean up stale cancel flags
    for k in list(CANCEL_FLAGS.keys()):
        if k not in PROGRESS:
            CANCEL_FLAGS.pop(k, None)

CANCEL_FLAGS = {}  # op_id -> True when cancellation requested
ARCHIVE_CACHE_KEYS = set()  # cycle keys (YYYYMMDD_HHz) from archive requests — persist on NVMe

# NOTE: eccodes warm-up removed — ProcessPoolExecutor gives each worker its own eccodes
# instance with no shared-state race condition.

def _scan_archive_cache_keys():
    """Scan mmap cache dirs for cycles outside the recent window and register them as archive keys.

    Scans both the main cache (XSECT_CACHE_DIR, NVMe) and the archive cache
    (XSECT_ARCHIVE_DIR/cache/xsect, D: drive) so that events converted by
    standalone scripts appear in the UI dropdown.
    """
    from datetime import datetime, timedelta
    cache_base = Path(os.environ.get('XSECT_CACHE_DIR', str(Path(__file__).resolve().parent.parent / 'cache' / 'xsect')))
    archive_env = os.environ.get('XSECT_ARCHIVE_DIR', '')
    archive_caches = []
    for p in archive_env.split(','):
        p = p.strip()
        if p:
            ac = Path(p) / 'cache' / 'xsect'
            if ac.is_dir():
                archive_caches.append(ac)
    cutoff = (datetime.utcnow() - timedelta(days=7)).strftime('%Y%m%d')
    seen = set()
    scan_dirs = [cache_base] + archive_caches
    for cache_dir in scan_dirs:
        for model_dir in cache_dir.iterdir():
            if not model_dir.is_dir():
                continue
            for entry in model_dir.iterdir():
                if not entry.is_dir() or not (entry / '_complete').exists():
                    continue
                # Parse cycle key from dir name: YYYYMMDD_HHz_Fxx_filename
                parts = entry.name.split('_')
                if len(parts) >= 2 and len(parts[0]) == 8 and parts[0].isdigit():
                    date_str = parts[0]
                    if date_str < cutoff:
                        ck = f"{parts[0]}_{parts[1]}"
                        seen.add(ck)
    return seen

ARCHIVE_CACHE_KEYS.update(_scan_archive_cache_keys())

def cancel_request(op_id):
    """Request cancellation of an operation."""
    CANCEL_FLAGS[op_id] = True
    if op_id in PROGRESS and not PROGRESS[op_id].get('done'):
        PROGRESS[op_id]['detail'] = 'Cancelling...'

def is_cancelled(op_id):
    """Check if an operation has been cancelled."""
    return CANCEL_FLAGS.get(op_id, False)

# =============================================================================
# PROCESS POOL WORKER — runs in separate process, own GIL, true parallelism
# =============================================================================

# =============================================================================
# DATA MANAGER - On-Demand Loading for Memory Efficiency
# =============================================================================

# Model-specific configuration for CrossSectionManager
MODEL_PRS_PATTERNS = {
    'hrrr': '*wrfprs*.grib2',
    'rrfs': '*prslev*.grib2',
    'gfs':  '*pgrb2.0p25*',  # GFS files have no .grib2 extension
}
MODEL_SFC_PATTERNS = {
    'hrrr': '*wrfsfc*.grib2',
    'rrfs': '*prslev*.grib2',   # RRFS: surface in same prslev file
    'gfs':  '*pgrb2.0p25*',    # GFS: surface in same pgrb2 file (no .grib2 ext)
}
MODEL_NEEDS_SEPARATE_SFC = {'hrrr'}  # Only HRRR has separate wrfsfc
MODEL_FORECAST_HOURS = {
    'hrrr': list(range(19)),                # F00-F18 (base; synoptic cycles extend to F48)
    'gfs':  list(range(0, 385, 6)),         # F00-F384 every 6 hours
    'rrfs': list(range(19)),                # F00-F18
}
SYNOPTIC_HOURS = {0, 6, 12, 18}

def get_max_fhr_for_cycle(model_name: str, cycle_hour: int) -> int:
    """Return max forecast hour for a given model+cycle. HRRR synoptic cycles go to 48."""
    if model_name == 'hrrr' and cycle_hour in SYNOPTIC_HOURS:
        return 48
    base = MODEL_FORECAST_HOURS.get(model_name, list(range(19)))
    return base[-1] if base else 18

def get_model_fhr_list(model_name: str, cycle_hour: int = None) -> list:
    """Return the actual FHR list for a model+cycle (handles sparse GFS FHRs)."""
    if model_name == 'hrrr' and cycle_hour is not None and cycle_hour in SYNOPTIC_HOURS:
        return list(range(49))  # F00-F48 every hour
    return MODEL_FORECAST_HOURS.get(model_name, list(range(19)))
MODEL_MIN_LEVELS = {
    'hrrr': 40,
    'gfs':  20,  # GFS has ~34 pressure levels
    'rrfs': 40,
}
MODEL_EXCLUDED_STYLES = {
    'gfs': {'smoke'},       # GFS has no PM2.5/smoke
    'rrfs': {'smoke'},      # RRFS has no smoke either
    'hrrr': set(),          # HRRR supports all styles
}

# ── Lazy wrfnat download for smoke style ──
# wrfnat files (~663MB) are no longer downloaded by auto_update (saves 56% bandwidth).
# When a smoke cross-section is first requested, this triggers a background download.
_wrfnat_download_pending = set()  # Set of (cycle_key, fhr) currently downloading
_wrfnat_download_lock = threading.Lock()

def _trigger_lazy_wrfnat_download(model_name: str, cycle_key: str, fhr: int):
    """Trigger background download of wrfnat file for smoke data.

    Returns True if download was triggered or already in progress,
    False if not applicable (non-HRRR or wrfnat already exists).
    """
    if model_name != 'hrrr':
        return False

    key = (cycle_key, fhr)
    with _wrfnat_download_lock:
        if key in _wrfnat_download_pending:
            return True  # Already downloading

    # Parse cycle_key to find the wrfprs file and derive wrfnat path
    # cycle_key format: "YYYYMMDD/HHz"
    try:
        parts = cycle_key.split('/')
        date_str = parts[0]
        hour = int(parts[1].replace('z', ''))
    except (IndexError, ValueError):
        return False

    outputs_dir = Path('outputs') / 'hrrr' / date_str / f"{hour:02d}z" / f"F{fhr:02d}"
    if not outputs_dir.exists():
        return False

    # Check if wrfnat already exists
    nat_files = list(outputs_dir.glob('*wrfnat*.grib2'))
    if nat_files:
        return False  # Already have it

    # Check if wrfprs exists (need it to derive the nat filename)
    prs_files = list(outputs_dir.glob('*wrfprs*.grib2'))
    if not prs_files:
        return False

    nat_filename = prs_files[0].name.replace('wrfprs', 'wrfnat')
    nat_path = outputs_dir / nat_filename

    with _wrfnat_download_lock:
        if key in _wrfnat_download_pending:
            return True
        _wrfnat_download_pending.add(key)

    def _download():
        try:
            from smart_hrrr.orchestrator import download_forecast_hour
            logger.info(f"[LAZY-WRFNAT] Downloading wrfnat for {cycle_key} F{fhr:02d}...")
            ok = download_forecast_hour(
                model='hrrr',
                date_str=date_str,
                cycle_hour=hour,
                forecast_hour=fhr,
                output_dir=outputs_dir,
                file_types=['native'],  # Only wrfnat
            )
            if ok:
                logger.info(f"[LAZY-WRFNAT] Downloaded wrfnat for {cycle_key} F{fhr:02d} — reload to pick up smoke data")
                # Force reload: unload + reload so mmap cache picks up wrfnat smoke fields
                for mgr in model_registry.managers.values():
                    if mgr.model_name == 'hrrr' and (cycle_key, fhr) in mgr.loaded_items:
                        try:
                            mgr._unload_item(cycle_key, fhr)
                            with mgr._lock:
                                if (cycle_key, fhr) in mgr.loaded_items:
                                    mgr.loaded_items.remove((cycle_key, fhr))
                            # Delete mmap cache for this FHR so it reconverts with smoke
                            cache_dir = Path(mgr.CACHE_BASE) / 'hrrr'
                            fhr_cache = cache_dir / date_str / f"{hour:02d}z" / f"F{fhr:02d}"
                            if fhr_cache.exists():
                                import shutil
                                shutil.rmtree(fhr_cache, ignore_errors=True)
                                logger.info(f"[LAZY-WRFNAT] Cleared mmap cache {fhr_cache}")
                            mgr.load_forecast_hour(cycle_key, fhr)
                        except Exception as e:
                            logger.warning(f"[LAZY-WRFNAT] Reload failed: {e}")
                        break
            else:
                logger.warning(f"[LAZY-WRFNAT] Failed to download wrfnat for {cycle_key} F{fhr:02d}")
        finally:
            with _wrfnat_download_lock:
                _wrfnat_download_pending.discard(key)

    threading.Thread(target=_download, daemon=True, name=f"wrfnat-{cycle_key}-F{fhr:02d}").start()
    return True

def _env_int(name: str, default: int) -> int:
    """Parse integer env var with fallback."""
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except (TypeError, ValueError):
        return default


class CrossSectionManager:
    """Manages cross-section data with smart pre-loading.

    Pre-loads latest N cycles at startup for instant access.
    Older cycles are available on-demand with loading indicator.
    Parameterized by model_name for multi-model support.
    """

    PRELOAD_WORKERS = 20  # Thread workers for mmap loads (fast, ~14ms each)
    GRIB_WORKERS = 4      # Workers for GRIB conversion
    CACHE_BASE = os.environ.get('XSECT_CACHE_DIR', str(Path(__file__).resolve().parent.parent / 'cache' / 'xsect'))  # NVMe — faster I/O

    PRELOAD_CYCLES = 0  # Don't pre-load; load on demand

    def __init__(self, model_name: str = 'hrrr', mem_limit_mb: int = 48000, mem_evict_mb: int = 46000):
        self.model_name = model_name
        self.xsect = None
        self.base_dir = Path(os.environ.get('XSECT_OUTPUTS_DIR', 'outputs')) / model_name
        self.available_cycles = []  # List of available cycles (metadata only)
        self.loaded_cycles = set()  # Cycle keys that are fully loaded
        self.loaded_items = []  # List of (cycle_key, fhr) currently in memory (ordered by load time = LRU)
        self.current_cycle = None  # Currently selected cycle
        self._lock = threading.Lock()  # Protects all state mutations
        self._loading = threading.Lock()  # Prevents overlapping bulk loads (preload vs load_cycle)
        self._engine_key_map = {}  # (cycle_key, fhr) -> unique engine int key
        self._next_engine_key = 0  # Counter for unique keys
        # Model-specific config
        self._prs_pattern = MODEL_PRS_PATTERNS.get(model_name, '*.grib2')
        self._sfc_pattern = MODEL_SFC_PATTERNS.get(model_name, '*.grib2')
        self._needs_separate_sfc = model_name in MODEL_NEEDS_SEPARATE_SFC
        self.FORECAST_HOURS = MODEL_FORECAST_HOURS.get(model_name, list(range(19)))
        self.PRELOAD_FHRS = self.FORECAST_HOURS  # All FHRs — mmap cache makes this cheap
        self.MEM_LIMIT_MB = mem_limit_mb
        self.MEM_EVICT_MB = mem_evict_mb
        self._min_levels = MODEL_MIN_LEVELS.get(model_name, 40)
        self._display_prefix = model_name.upper()
        # Load model config for metadata
        try:
            from model_config import get_model_registry
            self.model_config = get_model_registry().get_model(model_name)
            if self.model_config:
                self._display_prefix = self.model_config.full_name.split('(')[0].strip()
        except Exception:
            self.model_config = None

    def _sfc_file_from_prs(self, prs_file: str) -> str:
        """Derive the surface GRIB path from a pressure GRIB path."""
        if self.model_name == 'hrrr':
            sfc = Path(prs_file).parent / Path(prs_file).name.replace('wrfprs', 'wrfsfc')
            return str(sfc) if sfc.exists() else prs_file
        # GFS/RRFS: surface data is in the same pressure file
        return prs_file

    def _nat_file_from_prs(self, prs_file: str):
        """Derive the native-level GRIB path (for smoke). Returns None if not applicable."""
        if self.model_name == 'hrrr':
            nat = Path(prs_file).parent / Path(prs_file).name.replace('wrfprs', 'wrfnat')
            return str(nat) if nat.exists() else None
        elif self.model_name == 'rrfs':
            nat = Path(prs_file).parent / Path(prs_file).name.replace('prslev', 'natlev')
            return str(nat) if nat.exists() else None
        return None  # GFS has no native levels

    # ── Smart cycle selection ──
    # HRRR: newest synoptic (48h) + 5 most recent hourly (18h each)
    #        Keep previous synoptic during handoff until new one is ready.
    # GFS/RRFS: newest cycle only; keep previous during handoff.
    HRRR_HOURLY_CYCLES = 3   # Number of recent hourly cycles to keep
    HRRR_SYNOPTIC_CYCLES = 2 # Number of synoptic (48h) cycles to keep
    GFS_CYCLES = 2            # GFS cycles to keep (evict oldest on 3rd)
    RRFS_CYCLES = 2           # RRFS cycles to keep (evict oldest on 3rd)

    def _get_target_cycles(self) -> list:
        """Return the list of cycles we WANT loaded, in priority order (newest first).

        HRRR: newest synoptic (48h) + N most recent hourly cycles.
              Only one synoptic kept (no previous synoptic handoff).
        GFS/RRFS: newest cycle only, no handoff.
        """
        if not self.available_cycles:
            return []

        if self.model_name == 'hrrr':
            return self._get_hrrr_target_cycles()
        else:
            return self._get_simple_target_cycles()

    def _get_hrrr_target_cycles(self) -> list:
        """HRRR: latest init first, then synoptics, then recent hourlies.

        Priority order:
          1. Latest init cycle (whatever it is) — always #1
          2. Up to HRRR_SYNOPTIC_CYCLES synoptic (48h) cycles
          3. N most recent hourly cycles
        """
        targets = []
        seen = set()

        newest = self.available_cycles[0]  # Overall newest init
        synoptics = [c for c in self.available_cycles if c.get('is_synoptic')]

        # 1. Latest init — always first, period
        targets.append(newest)
        seen.add(newest['cycle_key'])

        # 2. Up to HRRR_SYNOPTIC_CYCLES synoptic cycles
        syn_count = 0
        for c in synoptics:
            if c['cycle_key'] not in seen:
                targets.append(c)
                seen.add(c['cycle_key'])
                syn_count += 1
                if syn_count >= self.HRRR_SYNOPTIC_CYCLES:
                    break
            else:
                # The newest synoptic was already added as latest init
                syn_count += 1

        # 3. Recent hourly cycles (up to N)
        count = 0
        for c in self.available_cycles:
            if c['cycle_key'] not in seen:
                targets.append(c)
                seen.add(c['cycle_key'])
                count += 1
                if count >= self.HRRR_HOURLY_CYCLES:
                    break

        return targets

    def _get_simple_target_cycles(self) -> list:
        """GFS/RRFS: keep up to GFS_CYCLES/RRFS_CYCLES newest cycles."""
        max_cycles = self.GFS_CYCLES if self.model_name == 'gfs' else self.RRFS_CYCLES
        return self.available_cycles[:max_cycles]

    def get_protected_cycles(self) -> set:
        """Return cycle keys that should never be evicted — matches target cycle strategy."""
        return {c['cycle_key'] for c in self._get_target_cycles()}

    @staticmethod
    def _priority_sort_fhrs(fhrs: list) -> list:
        """Sort FHRs by temporal priority: every 6h, then 3h fill, then hourly.

        Users see the full time range at coarse resolution fast, then it fills in.
        E.g. for F00-F48: [0,6,12,18,24,30,36,42,48, 3,9,15,21,27,33,39,45, 1,2,4,5,7,8,...]
        """
        tier1 = [f for f in fhrs if f % 6 == 0]  # Every 6h
        tier2 = [f for f in fhrs if f % 3 == 0 and f % 6 != 0]  # Every 3h fill
        tier3 = [f for f in fhrs if f % 3 != 0]  # Hourly fill
        return tier1 + tier2 + tier3

    def is_archive_cycle(self, cycle_key: str) -> bool:
        """Return True if cycle_key is NOT one of the 2 latest (i.e. it's archive/old)."""
        return cycle_key not in self.get_protected_cycles()

    def _get_engine_key(self, cycle_key: str, fhr: int) -> int:
        """Get or create a unique engine key for a (cycle_key, fhr) pair."""
        pair = (cycle_key, fhr)
        if pair not in self._engine_key_map:
            self._engine_key_map[pair] = self._next_engine_key
            self._next_engine_key += 1
        return self._engine_key_map[pair]

    def _evict_if_needed(self):
        """Evict oldest loaded items if memory exceeds threshold. Protected cycles are skipped."""
        if not self.xsect:
            return
        protected = self.get_protected_cycles()
        mem_mb = self.xsect.get_memory_usage()
        while mem_mb > self.MEM_EVICT_MB and self.loaded_items:
            # Find oldest non-protected item to evict
            evict_idx = None
            for i, (ck, fhr) in enumerate(self.loaded_items):
                if ck not in protected:
                    evict_idx = i
                    break
            if evict_idx is None:
                logger.warning(f"Memory {mem_mb:.0f}MB > limit but only protected cycles loaded, cannot evict")
                break
            old_key, old_fhr = self.loaded_items.pop(evict_idx)
            logger.info(f"Memory {mem_mb:.0f}MB > {self.MEM_EVICT_MB}MB, evicting {old_key} F{old_fhr:02d}")
            self._unload_item(old_key, old_fhr)
            if not any(k == old_key for k, _ in self.loaded_items):
                self.loaded_cycles.discard(old_key)
            mem_mb = self.xsect.get_memory_usage()

    def init_engine(self):
        """Initialize the cross-section engine if needed."""
        if self.xsect is None:
            from core.cross_section_interactive import InteractiveCrossSection
            cache_dir = f'{self.CACHE_BASE}/{self.model_name}'
            grib_backend = os.environ.get('XSECT_GRIB_BACKEND', 'auto').strip().lower()
            try:
                self.xsect = InteractiveCrossSection(
                    cache_dir=cache_dir,
                    min_levels=self._min_levels,
                    sfc_resolver=lambda prs: self._sfc_file_from_prs(prs),
                    nat_resolver=lambda prs: self._nat_file_from_prs(prs),
                    grib_backend=grib_backend,
                )
            except ValueError:
                logger.warning(f"Invalid XSECT_GRIB_BACKEND='{grib_backend}', falling back to 'auto'")
                self.xsect = InteractiveCrossSection(
                    cache_dir=cache_dir,
                    min_levels=self._min_levels,
                    sfc_resolver=lambda prs: self._sfc_file_from_prs(prs),
                    nat_resolver=lambda prs: self._nat_file_from_prs(prs),
                    grib_backend='auto',
                )
            self.xsect.model = self.model_name.upper()
            # Add archive cache dirs as fallback for mmap lookups (comma-separated)
            archive_env = os.environ.get('XSECT_ARCHIVE_DIR', '')
            for p in archive_env.split(','):
                p = p.strip()
                if p:
                    archive_cache = Path(p) / 'cache' / 'xsect' / self.model_name
                    if archive_cache.is_dir():
                        self.xsect.extra_cache_dirs.append(archive_cache)
                        logger.info(f"Archive cache fallback: {archive_cache}")
            logger.info(f"Cross-section GRIB backend: {self.xsect.grib_backend}")

    def scan_available_cycles(self):
        """Scan for all available cycles on disk WITHOUT loading data."""
        from datetime import datetime

        cycles = []

        if not self.base_dir.exists():
            self.available_cycles = cycles
            return self.available_cycles

        # Scan for date directories
        for date_dir in sorted(self.base_dir.iterdir(), reverse=True):
            if not date_dir.is_dir() or not date_dir.name.isdigit():
                continue
            if len(date_dir.name) != 8:
                continue

            # Scan for hour directories within date
            for hour_dir in sorted(date_dir.iterdir(), reverse=True):
                if not hour_dir.is_dir() or not hour_dir.name.endswith('z'):
                    continue

                hour = hour_dir.name.replace('z', '')
                if not hour.isdigit():
                    continue

                # Check what forecast hours are available on disk
                available_fhrs = []
                cycle_hour_int = int(hour)
                max_fhr = get_max_fhr_for_cycle(self.model_name, cycle_hour_int)
                expected_fhrs = get_model_fhr_list(self.model_name, cycle_hour_int)
                for fhr in expected_fhrs:
                    fhr_dir = hour_dir / f"F{fhr:02d}"
                    if fhr_dir.exists():
                        has_prs = [f for f in fhr_dir.glob(self._prs_pattern)
                                   if not f.name.endswith('.partial')]
                        if self._needs_separate_sfc:
                            has_sfc = [f for f in fhr_dir.glob(self._sfc_pattern)
                                       if not f.name.endswith('.partial')]
                            if has_prs and has_sfc:
                                available_fhrs.append(fhr)
                        else:
                            # GFS/RRFS: surface data is in the pressure file
                            if has_prs:
                                available_fhrs.append(fhr)

                if available_fhrs:
                    cycle_key = f"{date_dir.name}_{hour}z"
                    init_dt = datetime.strptime(f"{date_dir.name}{hour}", "%Y%m%d%H")

                    cycles.append({
                        'cycle_key': cycle_key,
                        'date': date_dir.name,
                        'hour': hour,
                        'path': str(hour_dir),
                        'available_fhrs': available_fhrs,
                        'init_dt': init_dt,
                        'display': f"{self._display_prefix} - {init_dt.strftime('%b %d %HZ')}",
                        'max_fhr': max_fhr,
                        'is_synoptic': cycle_hour_int in SYNOPTIC_HOURS,
                        'expected_fhrs': expected_fhrs,
                    })

        # Also scan archive GRIB dirs (XSECT_ARCHIVE_DIR, comma-separated) for archive event cycles
        archive_env = os.environ.get('XSECT_ARCHIVE_DIR', '')
        for archive_base in [p.strip() for p in archive_env.split(',') if p.strip()]:
            archive_model_dir = Path(archive_base) / self.model_name
            if archive_model_dir.is_dir():
                existing_keys = {c['cycle_key'] for c in cycles}
                for date_dir in sorted(archive_model_dir.iterdir(), reverse=True):
                    if not date_dir.is_dir() or not date_dir.name.isdigit() or len(date_dir.name) != 8:
                        continue
                    for hour_dir in sorted(date_dir.iterdir(), reverse=True):
                        if not hour_dir.is_dir() or not hour_dir.name.endswith('z'):
                            continue
                        hour = hour_dir.name.replace('z', '')
                        if not hour.isdigit():
                            continue
                        cycle_key = f"{date_dir.name}_{hour}z"
                        if cycle_key in existing_keys:
                            continue
                        available_fhrs = []
                        cycle_hour_int = int(hour)
                        max_fhr = get_max_fhr_for_cycle(self.model_name, cycle_hour_int)
                        expected_fhrs = get_model_fhr_list(self.model_name, cycle_hour_int)
                        for fhr in expected_fhrs:
                            fhr_dir = hour_dir / f"F{fhr:02d}"
                            if fhr_dir.exists():
                                has_prs = [f for f in fhr_dir.glob(self._prs_pattern)
                                           if not f.name.endswith('.partial')]
                                if has_prs:
                                    available_fhrs.append(fhr)
                        if available_fhrs:
                            init_dt = datetime.strptime(f"{date_dir.name}{hour}", "%Y%m%d%H")
                            cycles.append({
                                'cycle_key': cycle_key,
                                'date': date_dir.name,
                                'hour': hour,
                                'path': str(hour_dir),
                                'available_fhrs': available_fhrs,
                                'init_dt': init_dt,
                                'display': f"{self._display_prefix} - {init_dt.strftime('%b %d %HZ')}",
                                'max_fhr': max_fhr,
                                'is_synoptic': cycle_hour_int in SYNOPTIC_HOURS,
                                'expected_fhrs': expected_fhrs,
                            })

        # Also scan archive mmap cache dirs for events that have no GRIBs left (already converted)
        archive_env = os.environ.get('XSECT_ARCHIVE_DIR', '')
        for archive_base in [p.strip() for p in archive_env.split(',') if p.strip()]:
            archive_cache_dir = Path(archive_base) / 'cache' / 'xsect' / self.model_name
            if not archive_cache_dir.is_dir():
                continue
            existing_keys = {c['cycle_key'] for c in cycles}
            # Group FHR dirs by cycle key
            import re
            cache_cycle_fhrs = {}
            for entry in archive_cache_dir.iterdir():
                if not entry.is_dir():
                    continue
                m = re.match(r'(\d{8})_(\d{2})z_F(\d+)_', entry.name)
                if m:
                    ck = f"{m.group(1)}_{m.group(2)}z"
                    fhr = int(m.group(3))
                    cache_cycle_fhrs.setdefault(ck, []).append(fhr)
            for ck, fhrs in cache_cycle_fhrs.items():
                if ck in existing_keys:
                    continue
                date_str, hour_str = ck.split('_')
                hour = hour_str.replace('z', '')
                cycle_hour_int = int(hour)
                max_fhr = get_max_fhr_for_cycle(self.model_name, cycle_hour_int)
                expected_fhrs = get_model_fhr_list(self.model_name, cycle_hour_int)
                init_dt = datetime.strptime(f"{date_str}{hour}", "%Y%m%d%H")
                cycles.append({
                    'cycle_key': ck,
                    'date': date_str,
                    'hour': hour,
                    'path': str(archive_cache_dir),
                    'available_fhrs': sorted(fhrs),
                    'init_dt': init_dt,
                    'display': f"{self._display_prefix} - {init_dt.strftime('%b %d %HZ')}",
                    'max_fhr': max_fhr,
                    'is_synoptic': cycle_hour_int in SYNOPTIC_HOURS,
                    'expected_fhrs': expected_fhrs,
                })
                existing_keys.add(ck)

        # Also scan local NVMe mmap cache for operational cycles with cleaned-up GRIBs
        local_cache_dir = Path(self.CACHE_BASE) / self.model_name
        if local_cache_dir.is_dir():
            import re
            cache_cycle_fhrs = {}
            for entry in local_cache_dir.iterdir():
                if not entry.is_dir():
                    continue
                m = re.match(r'(\d{8})_(\d{2})z_F(\d+)_', entry.name)
                if m and (entry / '_complete').exists():
                    ck = f"{m.group(1)}_{m.group(2)}z"
                    fhr = int(m.group(3))
                    cache_cycle_fhrs.setdefault(ck, []).append(fhr)
            existing_keys = {c['cycle_key'] for c in cycles}
            for ck, fhrs in cache_cycle_fhrs.items():
                if ck in existing_keys:
                    # Merge mmap-cached FHRs into existing cycle entry
                    for c in cycles:
                        if c['cycle_key'] == ck:
                            c['available_fhrs'] = sorted(set(c['available_fhrs']) | set(fhrs))
                            break
                else:
                    # New cycle only in local mmap cache
                    date_str, hour_str = ck.split('_')
                    hour = hour_str.replace('z', '')
                    cycle_hour_int = int(hour)
                    max_fhr = get_max_fhr_for_cycle(self.model_name, cycle_hour_int)
                    expected_fhrs = get_model_fhr_list(self.model_name, cycle_hour_int)
                    init_dt = datetime.strptime(f"{date_str}{hour}", "%Y%m%d%H")
                    cycles.append({
                        'cycle_key': ck,
                        'date': date_str,
                        'hour': hour,
                        'path': str(self.base_dir / date_str / f"{hour}z"),
                        'available_fhrs': sorted(fhrs),
                        'init_dt': init_dt,
                        'display': f"{self._display_prefix} - {init_dt.strftime('%b %d %HZ')}",
                        'max_fhr': max_fhr,
                        'is_synoptic': cycle_hour_int in SYNOPTIC_HOURS,
                        'expected_fhrs': expected_fhrs,
                    })
                    existing_keys.add(ck)

        # Sort by init_dt descending so newest cycles are always first,
        # regardless of whether they came from GRIB scan, archive, or NVMe mmap scan.
        # This ensures _get_hrrr_target_cycles picks the actual newest init and
        # recent synoptic cycles instead of old archive events.
        cycles.sort(key=lambda c: c['init_dt'], reverse=True)

        self.available_cycles = cycles  # Atomic swap — no empty window
        return self.available_cycles

    def get_cycles_for_ui(self):
        """Return cycles formatted for UI dropdown.

        Only includes cycles that are either:
          - In the preload target window (recent inits the dashboard manages)
          - Have loaded data (e.g. from archive requests)
          - Have an active download/load in progress
        Older cycles on disk are hidden until explicitly requested via archive.
        """
        target_keys = {c['cycle_key'] for c in self._get_target_cycles()}
        loaded_keys = {ck for ck, _ in self.loaded_items}

        # Include cycles with active download/load operations
        # op_id format: "download:hrrr:20250618/15z" or "load:hrrr:20250618/15z"
        active_keys = set()
        for op_id, info in PROGRESS.items():
            if info.get('done'):
                continue
            parts = op_id.split(':')
            if len(parts) >= 3 and parts[1] == self.model_name:
                # Convert "20250618/15z" -> "20250618_15z"
                ck = parts[2].replace('/', '_')
                active_keys.add(ck)

        visible_keys = target_keys | loaded_keys | active_keys | ARCHIVE_CACHE_KEYS

        return [
            {
                'key': c['cycle_key'],
                'display': c['display'],
                'date': c['date'],
                'hour': c['hour'],
                'fhrs': c['available_fhrs'],
                'fhr_count': len(c['available_fhrs']),
                'loaded': c['cycle_key'] in loaded_keys,
                'max_fhr': c.get('max_fhr', 18),
                'is_synoptic': c.get('is_synoptic', False),
                'expected_fhrs': c.get('expected_fhrs', None),
            }
            for c in self.available_cycles
            if c['cycle_key'] in visible_keys
        ]

    def preload_latest_cycles(self, n_cycles: int = None):
        """Pre-load the latest N cycles with every 3rd forecast hour, newest first, parallel."""
        if n_cycles is None:
            n_cycles = self.PRELOAD_CYCLES

        with self._loading:
            self._preload_latest_cycles_inner(n_cycles)

    def _preload_latest_cycles_inner(self, n_cycles):
        self.init_engine()

        # Smart cycle selection: load only what matters
        cycles_to_load = self._get_target_cycles()

        # Build per-cycle FHR queues, priority-sorted within each cycle
        cycle_queues = []
        for cycle in cycles_to_load:
            cycle_key = cycle['cycle_key']
            is_synoptic = cycle.get('is_synoptic', False) and self.model_name == 'hrrr'
            allowed = cycle['available_fhrs'] if is_synoptic else [f for f in cycle['available_fhrs'] if f in self.PRELOAD_FHRS]
            with self._lock:
                fhrs = [fhr for fhr in allowed if (cycle_key, fhr) not in self.loaded_items]
            if fhrs:
                fhrs = self._priority_sort_fhrs(fhrs)
                cycle_queues.append((cycle, fhrs))

        if not cycle_queues:
            return

        # Build flat list, newest-first, priority-sorted within each cycle
        interleaved = []
        for cycle, fhrs in cycle_queues:
            for fhr in fhrs:
                interleaved.append((cycle, fhr))

        # Partition into cached (instant mmap load) vs uncached (slow GRIB conversion).
        # Cached items load first so users see rapid progress instead of waiting
        # for GRIB conversions before anything appears.
        cache_dir = Path(f'{self.CACHE_BASE}/{self.model_name}')
        cached_items = []
        uncached_items = []
        for cycle, fhr in interleaved:
            found_cache = False
            prs_files = list((Path(cycle['path']) / f"F{fhr:02d}").glob(self._prs_pattern))
            if prs_files:
                stem = self.xsect._get_cache_stem(str(prs_files[0]))
                if stem and (cache_dir / stem).is_dir():
                    found_cache = True
            if not found_cache:
                # Check local NVMe cache and archive cache for mmap-only items
                synthetic = self._find_cache_grib_path(cycle, fhr)
                if synthetic:
                    stem = self.xsect._get_cache_stem(synthetic)
                    if stem:
                        # Check local cache
                        if (cache_dir / stem).is_dir():
                            found_cache = True
                        else:
                            # Check extra_cache_dirs (archive SSDs)
                            for extra in getattr(self.xsect, 'extra_cache_dirs', []):
                                if (Path(extra) / stem).is_dir():
                                    found_cache = True
                                    break
            if found_cache:
                cached_items.append((cycle, fhr))
            else:
                uncached_items.append((cycle, fhr))

        # Load cached first, then uncached
        ordered = cached_items + uncached_items
        n_cached = len(cached_items)

        total = len(ordered)
        done = [0]
        op_id = "preload:startup"
        n_cyc = len(cycle_queues)

        cycle_list = ', '.join(c['cycle_key'] for c, _ in cycle_queues)
        progress_update(op_id, 0, total, "Starting...",
                        label=f"Pre-loading {n_cyc} cycles ({total} FHRs, {n_cached} cached)")
        logger.info(f"Pre-loading {total} FHRs across {n_cyc} cycles: [{cycle_list}] ({n_cached} cached, {total - n_cached} need GRIB)")

        def _make_loader(c):
            def _load_one(fhr):
                ck = c['cycle_key']
                with self._lock:
                    if (ck, fhr) in self.loaded_items:
                        return ck, fhr, True
                    self.xsect.init_date = c['date']
                    self.xsect.init_hour = c['hour']
                    self._evict_if_needed()
                    engine_key = self._get_engine_key(ck, fhr)

                fhr_dir = Path(c['path']) / f"F{fhr:02d}"
                prs_files = list(fhr_dir.glob(self._prs_pattern))
                if not prs_files:
                    # No GRIB — try mmap cache (local NVMe or archive SSD)
                    synthetic = self._find_cache_grib_path(c, fhr)
                    if synthetic:
                        prs_files = [Path(synthetic)]
                if prs_files and self.xsect.load_forecast_hour(str(prs_files[0]), engine_key):
                    with self._lock:
                        if (ck, fhr) not in self.loaded_items:
                            self.loaded_items.append((ck, fhr))
                    self._cleanup_grib_dir(fhr_dir)
                    return ck, fhr, True
                return ck, fhr, False
            return _load_one

        # Phase 1: Load cached items (fast — mmap loads in <0.1s each)
        cancelled = False
        if cached_items:
            logger.info(f"  Phase 1: Loading {n_cached} cached FHRs...")
            with ThreadPoolExecutor(max_workers=self.PRELOAD_WORKERS) as pool:
                futures = {}
                for cycle, fhr in cached_items:
                    loader = _make_loader(cycle)
                    futures[pool.submit(loader, fhr)] = (cycle['cycle_key'], fhr)

                for future in as_completed(futures):
                    if is_cancelled(op_id):
                        for f in futures:
                            f.cancel()
                        cancelled = True
                        break
                    try:
                        ck, fhr, ok = future.result()
                        done[0] += 1
                        if ok:
                            logger.info(f"  Loaded {ck} F{fhr:02d} (cached)")
                            progress_update(op_id, done[0], total, f"Loaded {ck} F{fhr:02d} (cached)")
                        else:
                            progress_update(op_id, done[0], total, f"Failed {ck} F{fhr:02d}")
                    except Exception as e:
                        done[0] += 1
                        logger.warning(f"  Failed to load FHR: {e}")

            logger.info(f"  Phase 1 done: {done[0]}/{n_cached} cached FHRs loaded")

        # Phase 2: Convert uncached items from GRIB (ProcessPool — true parallelism)
        if uncached_items and not cancelled:
            # Build list of (grib_file, engine_key) for worker processes + metadata for main process
            grib_tasks = []  # (grib_file, engine_key, cycle, fhr)
            for cycle, fhr in uncached_items:
                ck = cycle['cycle_key']
                with self._lock:
                    engine_key = self._get_engine_key(ck, fhr)
                fhr_dir = Path(cycle['path']) / f"F{fhr:02d}"
                prs_files = list(fhr_dir.glob(self._prs_pattern))
                if not prs_files:
                    synthetic = self._find_cache_grib_path(cycle, fhr)
                    if synthetic:
                        prs_files = [Path(synthetic)]
                if prs_files:
                    grib_tasks.append((str(prs_files[0]), engine_key, cycle, fhr))
                else:
                    done[0] += 1
                    progress_update(op_id, done[0], total, f"No GRIB for {ck} F{fhr:02d}")

            if grib_tasks and not cancelled:
                logger.info(f"  Phase 2: Converting {len(grib_tasks)} FHRs from GRIB ({GRIB_POOL_WORKERS} process workers)...")
                pool_config = self.get_render_pool_config()
                project_dir = str(Path(__file__).resolve().parent.parent)
                from tools.render_worker import convert_grib
                try:
                    grib_pool = _get_grib_pool(pool_config, project_dir)
                    futures = {}
                    for grib_file, engine_key, cycle, fhr in grib_tasks:
                        future = grib_pool.submit(convert_grib, (grib_file, engine_key))
                        futures[future] = (cycle, fhr)

                    for future in as_completed(futures):
                        if is_cancelled(op_id):
                            for f in futures:
                                f.cancel()
                            cancelled = True
                            break
                        cycle, fhr = futures[future]
                        ck = cycle['cycle_key']
                        try:
                            engine_key_r, ok = future.result(timeout=120)
                            if ok:
                                # Worker wrote mmap cache; now load in main process (fast path, <0.1s)
                                loader = _make_loader(cycle)
                                ck_r, fhr_r, loaded = loader(fhr)
                                done[0] += 1
                                if loaded:
                                    logger.info(f"  Loaded {ck} F{fhr:02d} (GRIB→mmap)")
                                    progress_update(op_id, done[0], total, f"Loaded {ck} F{fhr:02d} (GRIB)")
                                else:
                                    progress_update(op_id, done[0], total, f"Failed {ck} F{fhr:02d} (mmap load)")
                            else:
                                done[0] += 1
                                progress_update(op_id, done[0], total, f"Failed {ck} F{fhr:02d}")
                        except Exception as e:
                            done[0] += 1
                            logger.warning(f"  GRIB worker failed for {ck} F{fhr:02d}: {e}")
                except Exception as e:
                    logger.error(f"GRIB pool error: {e}, falling back to threaded conversion")
                    shutdown_grib_pool()
                    # Fallback: sequential conversion in main process
                    for grib_file, engine_key, cycle, fhr in grib_tasks:
                        if is_cancelled(op_id):
                            cancelled = True
                            break
                        loader = _make_loader(cycle)
                        try:
                            ck_r, fhr_r, ok = loader(fhr)
                            done[0] += 1
                            tag = "GRIB fallback"
                            if ok:
                                logger.info(f"  Loaded {ck_r} F{fhr_r:02d} ({tag})")
                                progress_update(op_id, done[0], total, f"Loaded {ck_r} F{fhr_r:02d} ({tag})")
                            else:
                                progress_update(op_id, done[0], total, f"Failed {ck_r} F{fhr_r:02d}")
                        except Exception as e2:
                            done[0] += 1
                            logger.warning(f"  Fallback failed: {e2}")

        mem_mb = self.xsect.get_memory_usage()
        if cancelled:
            logger.info(f"  Pre-load CANCELLED at {done[0]}/{total} ({mem_mb:.0f} MB)")
            PROGRESS[op_id]['detail'] = 'Cancelled'
        else:
            logger.info(f"  Pre-load done ({mem_mb:.0f} MB total)")
        progress_done(op_id)
        CANCEL_FLAGS.pop(op_id, None)

        # Auto-prerender overlay frames for the loaded cycle(s)
        loaded_cycles = set(ck for ck, _ in self.loaded_items)
        for ck in loaded_cycles:
            threading.Thread(
                target=auto_prerender_overlay_all_products,
                args=(self, self.model_name, ck),
                daemon=True,
            ).start()

    def auto_load_latest(self):
        """Load new FHRs from disk, newest cycle first (priority)."""
        if not self._loading.acquire(blocking=False):
            logger.info("Skipping auto-load — another load operation in progress")
            return
        try:
            self._auto_load_latest_inner()
        finally:
            self._loading.release()

    def _auto_load_latest_inner(self):
        if not self.xsect or not self.available_cycles:
            return

        # Use the same smart cycle selection as preload — only load target cycles
        priority_cycles = self._get_target_cycles()

        # Evict FHRs from cycles that are no longer targeted
        target_keys = {c['cycle_key'] for c in priority_cycles}
        with self._lock:
            to_evict = [(ck, fhr) for ck, fhr in self.loaded_items
                        if ck not in target_keys and ck not in ARCHIVE_CACHE_KEYS]
        for ck, fhr in to_evict:
            logger.info(f"  Evicting {ck} F{fhr:02d} (no longer in target cycles)")
            with self._lock:
                if (ck, fhr) in self.loaded_items:
                    self.loaded_items.remove((ck, fhr))
            self._unload_item(ck, fhr)

        # Collect all FHRs to load across all target cycles for progress tracking
        all_work = []  # [(cycle, cycle_key, fhr, is_cached)]
        newest = priority_cycles[0] if priority_cycles else None
        for cycle in priority_cycles:
            cycle_key = cycle['cycle_key']
            is_synoptic = cycle.get('is_synoptic', False)

            if is_synoptic and self.model_name == 'hrrr':
                allowed_fhrs = cycle['available_fhrs']
            else:
                allowed_fhrs = [f for f in cycle['available_fhrs'] if f in self.PRELOAD_FHRS]

            with self._lock:
                fhrs_to_load = [fhr for fhr in allowed_fhrs
                                if (cycle_key, fhr) not in self.loaded_items]

            if not fhrs_to_load:
                continue

            fhrs_to_load = self._priority_sort_fhrs(fhrs_to_load)

            # Partition into cached vs uncached
            cache_dir = Path(f'{self.CACHE_BASE}/{self.model_name}')
            for fhr in fhrs_to_load:
                prs_files = list((Path(cycle['path']) / f"F{fhr:02d}").glob(self._prs_pattern))
                is_cached = False
                if prs_files:
                    stem = self.xsect._get_cache_stem(str(prs_files[0]))
                    if stem and (cache_dir / stem).is_dir():
                        is_cached = True
                all_work.append((cycle, cycle_key, fhr, is_cached))

        if not all_work:
            return

        # Sort: cached first, then uncached
        all_work.sort(key=lambda x: (not x[3], x[1], x[2]))

        n_cached = sum(1 for _, _, _, c in all_work if c)
        n_uncached = len(all_work) - n_cached

        # Progress tracking
        op_id = f"autoload:{self.model_name}"
        cycle_keys = sorted(set(ck for _, ck, _, _ in all_work))
        cycle_label = cycle_keys[0] if len(cycle_keys) == 1 else f"{len(cycle_keys)} cycles"
        progress_update(op_id, 0, len(all_work), "Starting...",
                        label=f"Loading {self.model_name.upper()} {cycle_label} ({n_cached} cached, {n_uncached} GRIB)")

        completed = [0]

        def _make_loader(c, ck):
            def _load_one(fhr):
                with self._lock:
                    if (ck, fhr) in self.loaded_items:
                        return fhr, True
                    self.xsect.init_date = c['date']
                    self.xsect.init_hour = c['hour']
                    self._evict_if_needed()
                    engine_key = self._get_engine_key(ck, fhr)

                fhr_dir = Path(c['path']) / f"F{fhr:02d}"
                prs_files = list(fhr_dir.glob(self._prs_pattern))
                if prs_files and self.xsect.load_forecast_hour(str(prs_files[0]), engine_key):
                    with self._lock:
                        if (ck, fhr) not in self.loaded_items:
                            self.loaded_items.append((ck, fhr))
                    self._cleanup_grib_dir(fhr_dir)
                    return fhr, True
                return fhr, False
            return _load_one

        def _on_complete(cycle_key, fhr, ok, is_cached):
            completed[0] += 1
            tag = "cached" if is_cached else "GRIB"
            detail = f"{cycle_key} F{fhr:02d} {'OK' if ok else 'FAILED'} ({tag})"
            progress_update(op_id, completed[0], len(all_work), detail)
            if ok:
                logger.info(f"  Auto-loaded {cycle_key} F{fhr:02d} ({tag})")

        # Phase 1: cached (fast)
        cached_work = [(c, ck, fhr) for c, ck, fhr, is_c in all_work if is_c]
        if cached_work:
            with ThreadPoolExecutor(max_workers=self.PRELOAD_WORKERS) as pool:
                futures = {}
                for c, ck, fhr in cached_work:
                    loader = _make_loader(c, ck)
                    fut = pool.submit(loader, fhr)
                    futures[fut] = (ck, fhr)
                for future in as_completed(futures):
                    ck, fhr = futures[future]
                    try:
                        _, ok = future.result()
                        _on_complete(ck, fhr, ok, True)
                    except Exception as e:
                        _on_complete(ck, fhr, False, True)
                        logger.warning(f"  Auto-load failed: {e}")

        # Phase 2: uncached GRIB conversion (ProcessPool — true parallelism)
        uncached_work = [(c, ck, fhr) for c, ck, fhr, is_c in all_work if not is_c]
        if uncached_work:
            # Build worker args: (grib_file, engine_key) + metadata for main process
            grib_tasks = []
            for c, ck, fhr in uncached_work:
                with self._lock:
                    engine_key = self._get_engine_key(ck, fhr)
                fhr_dir = Path(c['path']) / f"F{fhr:02d}"
                prs_files = list(fhr_dir.glob(self._prs_pattern))
                if prs_files:
                    grib_tasks.append((str(prs_files[0]), engine_key, c, ck, fhr))
                else:
                    _on_complete(ck, fhr, False, False)

            if grib_tasks:
                logger.info(f"  Phase 2: Converting {len(grib_tasks)} FHRs from GRIB ({GRIB_POOL_WORKERS} process workers)...")
                pool_config = self.get_render_pool_config()
                project_dir = str(Path(__file__).resolve().parent.parent)
                from tools.render_worker import convert_grib
                try:
                    grib_pool = _get_grib_pool(pool_config, project_dir)
                    futures = {}
                    for grib_file, engine_key, c, ck, fhr in grib_tasks:
                        fut = grib_pool.submit(convert_grib, (grib_file, engine_key))
                        futures[fut] = (c, ck, fhr)

                    for future in as_completed(futures):
                        c, ck, fhr = futures[future]
                        try:
                            engine_key_r, ok = future.result(timeout=120)
                            if ok:
                                # Worker wrote mmap; load in main process (fast)
                                loader = _make_loader(c, ck)
                                _, loaded = loader(fhr)
                                _on_complete(ck, fhr, loaded, False)
                            else:
                                _on_complete(ck, fhr, False, False)
                        except Exception as e:
                            _on_complete(ck, fhr, False, False)
                            logger.warning(f"  GRIB worker failed for {ck} F{fhr:02d}: {e}")
                except Exception as e:
                    logger.error(f"GRIB pool error: {e}, falling back to sequential")
                    shutdown_grib_pool()
                    for grib_file, engine_key, c, ck, fhr in grib_tasks:
                        loader = _make_loader(c, ck)
                        try:
                            _, ok = loader(fhr)
                            _on_complete(ck, fhr, ok, False)
                        except Exception as e2:
                            _on_complete(ck, fhr, False, False)
                            logger.warning(f"  Fallback failed: {e2}")

        progress_done(op_id)

        # Auto-prerender overlay frames for newly loaded FHRs
        loaded_cycles = set(ck for ck, _ in self.loaded_items)
        for ck in loaded_cycles:
            threading.Thread(
                target=auto_prerender_overlay_all_products,
                args=(self, self.model_name, ck),
                daemon=True,
            ).start()

    def get_loaded_status(self):
        """Return current memory status."""
        mem_mb = self.xsect.get_memory_usage() if self.xsect else 0
        return {
            'loaded': self.loaded_items.copy(),
            'loaded_cycles': list(self.loaded_cycles),
            'memory_mb': round(mem_mb, 0),
            'loading': self._lock.locked(),
        }

    def resolve_cycle(self, cycle_key: str, fhr: int) -> 'Optional[str]':
        """Resolve 'latest' to an actual cycle key. Returns None if nothing available."""
        if cycle_key and cycle_key != 'latest':
            return cycle_key
        with self._lock:
            # Prefer newest loaded cycle that has this FHR
            for ck, f in reversed(self.loaded_items):
                if f == fhr:
                    return ck
            # Fall back to newest available cycle on disk
            for c in self.available_cycles:
                if fhr in c['available_fhrs']:
                    return c['cycle_key']
        return None

    def ensure_loaded(self, cycle_key: str, fhr: int) -> bool:
        """Ensure a forecast hour is loaded (auto-loads from mmap/GRIB). Returns True if ready."""
        with self._lock:
            if (cycle_key, fhr) in self.loaded_items:
                return True
        result = self.load_forecast_hour(cycle_key, fhr)
        return result.get('success', False)

    def get_forecast_hour(self, cycle_key: str, fhr: int):
        """Get ForecastHourData for a loaded cycle+FHR. Returns None if not loaded."""
        with self._lock:
            if (cycle_key, fhr) not in self.loaded_items:
                return None
        engine_key = self._engine_key_map.get((cycle_key, fhr))
        if engine_key is None:
            return None
        return self.xsect.forecast_hours.get(engine_key) if self.xsect else None

    def load_cycle(self, cycle_key: str) -> dict:
        """Load an entire cycle (all available FHRs) into memory, parallel."""
        if not self._loading.acquire(timeout=120):
            return {'success': False, 'error': 'Timed out waiting for other load to finish'}
        try:
            return self._load_cycle_inner(cycle_key)
        finally:
            self._loading.release()

    def _load_cycle_inner(self, cycle_key: str) -> dict:
        with self._lock:
            cycle = next((c for c in self.available_cycles if c['cycle_key'] == cycle_key), None)
            if not cycle:
                return {'success': False, 'error': f'Cycle {cycle_key} not found'}

            # Check if ALL available FHRs are already loaded
            loaded_fhrs = {fhr for ck, fhr in self.loaded_items if ck == cycle_key}
            if loaded_fhrs >= set(cycle['available_fhrs']):
                mem_mb = self.xsect.get_memory_usage() if self.xsect else 0
                return {'success': True, 'already_loaded': True, 'loaded_fhrs': len(loaded_fhrs), 'memory_mb': round(mem_mb, 0)}

            self.init_engine()

        run_path = Path(cycle['path'])
        op_id = f"cycle:{cycle_key}"
        total_fhrs = len(cycle['available_fhrs'])
        progress_update(op_id, 0, total_fhrs, "Starting...", label=f"Loading cycle {cycle_key}")
        loaded_count = [0]  # mutable for closure

        # Count already-loaded
        with self._lock:
            fhrs_to_load = []
            for fhr in cycle['available_fhrs']:
                if (cycle_key, fhr) in self.loaded_items:
                    loaded_count[0] += 1
                else:
                    fhrs_to_load.append(fhr)

        def _load_one(fhr):
            with self._lock:
                if (cycle_key, fhr) in self.loaded_items:
                    return fhr, True
                self.xsect.init_date = cycle['date']
                self.xsect.init_hour = cycle['hour']
                self._evict_if_needed()
                engine_key = self._get_engine_key(cycle_key, fhr)

            fhr_dir = run_path / f"F{fhr:02d}"
            prs_files = list(fhr_dir.glob(self._prs_pattern))
            if not prs_files:
                # Try archive mmap cache (no GRIBs, already converted)
                synthetic = self._find_cache_grib_path(cycle, fhr)
                if synthetic:
                    prs_files = [Path(synthetic)]
            if prs_files and self.xsect.load_forecast_hour(str(prs_files[0]), engine_key):
                with self._lock:
                    if (cycle_key, fhr) not in self.loaded_items:
                        self.loaded_items.append((cycle_key, fhr))
                self._cleanup_grib_dir(fhr_dir)
                return fhr, True
            return fhr, False

        logger.info(f"Loading {cycle['display']} ({len(fhrs_to_load)} FHRs, {self.PRELOAD_WORKERS} workers)...")

        cancelled = False
        with ThreadPoolExecutor(max_workers=self.PRELOAD_WORKERS) as pool:
            futures = {pool.submit(_load_one, fhr): fhr for fhr in fhrs_to_load}
            for future in as_completed(futures):
                if is_cancelled(op_id):
                    for f in futures:
                        f.cancel()
                    cancelled = True
                    break
                try:
                    fhr, ok = future.result()
                    if ok:
                        loaded_count[0] += 1
                        progress_update(op_id, loaded_count[0], total_fhrs, f"Loaded F{fhr:02d}")
                        logger.info(f"  Loaded {cycle_key} F{fhr:02d}")
                except Exception as e:
                    logger.warning(f"  Failed to load FHR: {e}")

        with self._lock:
            self.loaded_cycles.add(cycle_key)
        mem_mb = self.xsect.get_memory_usage()
        if cancelled:
            logger.info(f"Load CANCELLED for {cycle['display']} at {loaded_count[0]}/{total_fhrs} ({mem_mb:.0f} MB)")
            PROGRESS[op_id]['detail'] = 'Cancelled'
        else:
            logger.info(f"Loaded {cycle['display']} ({loaded_count[0]} FHRs, {mem_mb:.0f} MB total)")
        progress_done(op_id)
        CANCEL_FLAGS.pop(op_id, None)

        # Auto-prerender overlay frames for the loaded cycle (all default products)
        threading.Thread(
            target=auto_prerender_overlay_all_products,
            args=(self, self.model_name, cycle_key),
            daemon=True,
        ).start()

        return {
            'success': True,
            'cycle': cycle_key,
            'loaded_fhrs': loaded_count[0],
            'memory_mb': round(mem_mb, 0),
        }

    def _find_cache_grib_path(self, cycle, fhr):
        """For cycles with mmap cache but no GRIBs, find the cache dir
        and construct a synthetic GRIB path so load_forecast_hour can locate it.
        Checks both local NVMe cache and archive cache dirs."""
        import re
        prefix = f"{cycle['date']}_{cycle['hour']}z_F{fhr:02d}_"

        # Check local NVMe cache first (operational cycles)
        local_cache_dir = Path(self.CACHE_BASE) / self.model_name
        if local_cache_dir.is_dir():
            for entry in local_cache_dir.iterdir():
                if entry.is_dir() and entry.name.startswith(prefix):
                    if (entry / '_complete').exists():
                        parts = entry.name.split('_', 3)
                        if len(parts) >= 4:
                            grib_stem = parts[3]
                            synthetic = self.base_dir / cycle['date'] / f"{cycle['hour']}z" / f"F{fhr:02d}" / f"{grib_stem}.grib2"
                            return str(synthetic)

        # Check archive cache dirs
        archive_env = os.environ.get('XSECT_ARCHIVE_DIR', '')
        for archive_base in [p.strip() for p in archive_env.split(',') if p.strip()]:
            cache_dir = Path(archive_base) / 'cache' / 'xsect' / self.model_name
            if not cache_dir.is_dir():
                continue
            for entry in cache_dir.iterdir():
                if entry.is_dir() and entry.name.startswith(prefix):
                    if (entry / '_complete').exists():
                        parts = entry.name.split('_', 3)
                        if len(parts) >= 4:
                            grib_stem = parts[3]
                            synthetic = Path(archive_base) / self.model_name / cycle['date'] / f"{cycle['hour']}z" / f"F{fhr:02d}" / f"{grib_stem}.grib2"
                            return str(synthetic)
        return None

    @staticmethod
    def _cleanup_grib_dir(fhr_dir: Path):
        """Delete GRIB files from an FHR directory after successful mmap conversion."""
        if not fhr_dir or not fhr_dir.is_dir():
            return
        try:
            for f in fhr_dir.iterdir():
                if f.is_file() and f.suffix == '.grib2':
                    f.unlink()
            # Remove empty FHR dir, then empty parent dirs
            if fhr_dir.exists() and not any(fhr_dir.iterdir()):
                fhr_dir.rmdir()
                parent = fhr_dir.parent  # HHz dir
                if parent.exists() and not any(parent.iterdir()):
                    parent.rmdir()
                    grandparent = parent.parent  # YYYYMMDD dir
                    if grandparent.exists() and not any(grandparent.iterdir()):
                        grandparent.rmdir()
        except Exception as e:
            logger.debug(f"GRIB cleanup for {fhr_dir}: {e}")

    def load_forecast_hour(self, cycle_key: str, fhr: int) -> dict:
        """Load a specific forecast hour into memory."""
        from datetime import datetime, timedelta

        # Fast checks and state setup under lock
        with self._lock:
            if (cycle_key, fhr) in self.loaded_items:
                return {'success': True, 'already_loaded': True}

            cycle = next((c for c in self.available_cycles if c['cycle_key'] == cycle_key), None)
            if not cycle:
                return {'success': False, 'error': f'Cycle {cycle_key} not found'}

            if fhr not in cycle['available_fhrs']:
                return {'success': False, 'error': f'F{fhr:02d} not available for {cycle_key}'}

            self.init_engine()
            self.xsect.init_date = cycle['date']
            self.xsect.init_hour = cycle['hour']

            run_path = Path(cycle['path'])
            fhr_dir = run_path / f"F{fhr:02d}"
            prs_files = list(fhr_dir.glob(self._prs_pattern))
            if not prs_files:
                # No GRIB — try to find existing mmap cache (archive events on SSD)
                # Construct a synthetic GRIB path that matches the cache stem convention
                synthetic_grib = self._find_cache_grib_path(cycle, fhr)
                if synthetic_grib:
                    prs_files = [Path(synthetic_grib)]
                else:
                    return {'success': False, 'error': f'No GRIB file found for F{fhr:02d}'}

            self._evict_if_needed()
            engine_key = self._get_engine_key(cycle_key, fhr)

        # Slow GRIB I/O runs WITHOUT lock
        op_id = f"load:{cycle_key}:F{fhr:02d}"
        progress_update(op_id, 0, 12, "Starting...", label=f"Loading {cycle_key} F{fhr:02d}")
        logger.info(f"Loading {cycle_key} F{fhr:02d} (engine key {engine_key})...")
        load_start = time.time()

        def _progress_cb(step, total, detail):
            progress_update(op_id, step, total, detail)

        success = self.xsect.load_forecast_hour(str(prs_files[0]), engine_key, progress_callback=_progress_cb)

        # State update under lock
        if success:
            load_time = time.time() - load_start
            with self._lock:
                if (cycle_key, fhr) not in self.loaded_items:
                    self.loaded_items.append((cycle_key, fhr))
                self.current_cycle = cycle_key
            self._cleanup_grib_dir(fhr_dir)
            mem_mb = self.xsect.get_memory_usage()
            logger.info(f"Loaded {cycle_key} F{fhr:02d} in {load_time:.1f}s (Total: {mem_mb:.0f} MB)")
            progress_done(op_id)
            return {
                'success': True,
                'loaded': (cycle_key, fhr),
                'memory_mb': round(mem_mb, 0),
                'load_time': round(load_time, 1),
            }
        else:
            progress_remove(op_id)
            return {'success': False, 'error': 'Failed to load data'}

    def _unload_item(self, cycle_key: str, fhr: int):
        """Unload a forecast hour from memory."""
        engine_key = self._engine_key_map.get((cycle_key, fhr))
        if self.xsect and engine_key is not None and engine_key in self.xsect.forecast_hours:
            self.xsect.unload_hour(engine_key)
            logger.info(f"Unloaded {cycle_key} F{fhr:02d}")

    def unload_forecast_hour(self, cycle_key: str, fhr: int, is_admin: bool = False) -> dict:
        """Explicitly unload a forecast hour."""
        with self._lock:
            if (cycle_key, fhr) not in self.loaded_items:
                return {'success': True, 'not_loaded': True}

            self._unload_item(cycle_key, fhr)
            self.loaded_items.remove((cycle_key, fhr))

        mem_mb = self.xsect.get_memory_usage() if self.xsect else 0
        return {
            'success': True,
            'unloaded': (cycle_key, fhr),
            'memory_mb': round(mem_mb, 0),
        }

    def generate_cross_section(self, start, end, cycle_key, fhr, style, y_axis='pressure', vscale=1.0, y_top=100, units='km', terrain_data=None, temp_cmap='standard', anomaly=False, marker=None, marker_label=None, markers=None):
        """Generate a cross-section for a loaded forecast hour."""
        if not self.xsect:
            return None

        if (cycle_key, fhr) not in self.loaded_items:
            return None

        cycle = next((c for c in self.available_cycles if c['cycle_key'] == cycle_key), None)
        engine_key = self._engine_key_map.get((cycle_key, fhr))
        if engine_key is None:
            return None

        # Build metadata with real FHR (not engine key) — thread-safe, no shared state
        meta = {
            'model': self.model_name.upper(),
            'init_date': cycle['date'] if cycle else None,
            'init_hour': cycle['hour'] if cycle else None,
            'forecast_hour': fhr,
        }

        try:
            png_bytes = self.xsect.get_cross_section(
                start_point=start,
                end_point=end,
                forecast_hour=engine_key,
                style=style,
                return_image=True,
                dpi=100,
                y_axis=y_axis,
                vscale=vscale,
                y_top=y_top,
                units=units,
                terrain_data=terrain_data,
                temp_cmap=temp_cmap,
                metadata=meta,
                anomaly=anomaly,
            )
            if png_bytes is None:
                return None
            return io.BytesIO(png_bytes)
        except Exception as e:
            import traceback
            logger.error(f"Cross-section error: {e}\n{traceback.format_exc()}")
            return None

    def get_render_info(self, cycle_key, fhr):
        """Get info needed for multiprocess rendering: grib_file, engine_key, metadata."""
        engine_key = self._engine_key_map.get((cycle_key, fhr))
        if engine_key is None:
            return None
        fhr_data = self.xsect.forecast_hours.get(engine_key) if self.xsect else None
        if fhr_data is None:
            return None
        cycle = next((c for c in self.available_cycles if c['cycle_key'] == cycle_key), None)
        return {
            'grib_file': fhr_data.grib_file,
            'engine_key': engine_key,
            'metadata': {
                'model': self.model_name.upper(),
                'init_date': cycle['date'] if cycle else None,
                'init_hour': cycle['hour'] if cycle else None,
                'forecast_hour': fhr,
            },
        }

    def get_render_pool_config(self):
        """Get config needed to initialize render worker processes."""
        cache_dir = str(self.xsect.cache_dir) if self.xsect and self.xsect.cache_dir else None
        extra = [str(d) for d in (self.xsect.extra_cache_dirs if self.xsect else [])]
        return {
            'cache_dir': cache_dir,
            'extra_cache_dirs': extra,
            'model_name': self.model_name,
            'min_levels': self._min_levels,
            'grib_backend': self.xsect.grib_backend if self.xsect else 'auto',
        }

    def get_cross_section_data(self, start, end, cycle_key, fhr, style):
        """Get raw cross-section data dict (no image rendering). Returns dict or None."""
        if not self.xsect:
            return None
        if (cycle_key, fhr) not in self.loaded_items:
            return None
        engine_key = self._engine_key_map.get((cycle_key, fhr))
        if engine_key is None:
            return None
        try:
            data = self.xsect.get_cross_section(
                start_point=start,
                end_point=end,
                forecast_hour=engine_key,
                style=style,
                return_image=False,
            )
            return data
        except Exception as e:
            import traceback
            logger.error(f"Cross-section data error: {e}\n{traceback.format_exc()}")
            return None

    def get_terrain_data(self, start, end, cycle_key, fhr, style):
        """Extract terrain data from a forecast hour for consistent GIF frames."""
        if not self.xsect:
            return None
        engine_key = self._engine_key_map.get((cycle_key, fhr))
        if engine_key is None:
            return None
        fhr_data = self.xsect.forecast_hours.get(engine_key)
        if fhr_data is None:
            return None
        import numpy as np
        # Adaptive n_points: ~1 per 3km, clamped [50, 1000]
        lat1, lon1 = np.radians(start[0]), np.radians(start[1])
        lat2, lon2 = np.radians(end[0]), np.radians(end[1])
        dlat, dlon = lat2 - lat1, lon2 - lon1
        a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
        dist_km = 6371 * 2 * np.arcsin(np.sqrt(a))
        n_points = int(np.clip(dist_km / 3.0, 50, 1000))
        path_lats = np.linspace(start[0], end[0], n_points)
        path_lons = np.linspace(start[1], end[1], n_points)
        data = self.xsect._interpolate_to_path(fhr_data, path_lats, path_lons, style)
        return {
            'surface_pressure': data.get('surface_pressure'),
            'surface_pressure_hires': data.get('surface_pressure_hires'),
            'distances_hires': data.get('distances_hires'),
            'pressure_levels': fhr_data.pressure_levels,
        }

    def get_panel_data(self, start, end, cycle_key, fhr, style):
        """Get data + metadata for one comparison panel.

        Returns dict with: data, metadata, style, or None on failure.
        """
        if not self.xsect:
            return None
        if (cycle_key, fhr) not in self.loaded_items:
            return None
        engine_key = self._engine_key_map.get((cycle_key, fhr))
        if engine_key is None:
            return None
        cycle = next((c for c in self.available_cycles if c['cycle_key'] == cycle_key), None)
        try:
            data = self.xsect.get_cross_section(
                start_point=start, end_point=end,
                forecast_hour=engine_key, style=style,
                return_image=False,
            )
            if data is None:
                return None
            from datetime import datetime, timedelta
            meta = {
                'model': self.model_name.upper(),
                'init_date': cycle['date'] if cycle else None,
                'init_hour': cycle['hour'] if cycle else None,
                'forecast_hour': fhr,
            }
            return {'data': data, 'metadata': meta, 'style': style}
        except Exception as e:
            import traceback
            logger.error(f"Panel data error: {e}\n{traceback.format_exc()}")
            return None

    # Legacy compatibility methods
    def get_available_times(self):
        """Legacy: Return loaded times for old API."""
        from datetime import timedelta
        times = []
        for cycle_key, fhr in self.loaded_items:
            cycle = next((c for c in self.available_cycles if c['cycle_key'] == cycle_key), None)
            if cycle:
                valid_dt = cycle['init_dt'] + timedelta(hours=fhr)
                times.append({
                    'valid': valid_dt.strftime("%Y-%m-%d %HZ"),
                    'init': cycle['init_dt'].strftime("%Y-%m-%d %HZ"),
                    'fhr': fhr,
                    'cycle_key': cycle_key,
                })
        return times


# =============================================================================
# MODEL MANAGER REGISTRY
# =============================================================================

ENABLED_MODELS = ['hrrr']  # Default; overridden by --models CLI arg
MODEL_MEM_BUDGETS = {
    'hrrr': (58000, 56000),
    'gfs':  (8000, 7500),
    'rrfs': (8000, 7500),
}


class ModelManagerRegistry:
    """Registry of CrossSectionManagers, one per model."""

    def __init__(self):
        self.managers: Dict[str, CrossSectionManager] = {}
        self.default_model = 'hrrr'

    def register(self, model_name: str):
        limit, evict = MODEL_MEM_BUDGETS.get(model_name, (25000, 24000))
        mgr = CrossSectionManager(
            model_name=model_name,
            mem_limit_mb=limit,
            mem_evict_mb=evict,
        )
        self.managers[model_name] = mgr
        return mgr

    def get(self, model_name: str = None) -> CrossSectionManager:
        name = (model_name or self.default_model).lower()
        if name not in self.managers:
            raise ValueError(f"Unknown model: {name}. Available: {list(self.managers.keys())}")
        return self.managers[name]

    def all_managers(self):
        return self.managers.items()

    def list_models(self):
        return [
            {
                'id': name,
                'name': mgr.model_config.full_name if mgr.model_config else name.upper(),
                'resolution': mgr.model_config.resolution if mgr.model_config else 'unknown',
                'domain': mgr.model_config.domain if mgr.model_config else 'unknown',
                'cycle_count': len(mgr.available_cycles),
                'loaded_count': len(mgr.loaded_items),
                'excluded_styles': sorted(MODEL_EXCLUDED_STYLES.get(name, set())),
            }
            for name, mgr in self.managers.items()
        ]


model_registry = ModelManagerRegistry()
model_registry.register('hrrr')  # Always register HRRR at import time
data_manager = model_registry.get('hrrr')  # Backward compat alias


def get_manager_from_request() -> CrossSectionManager:
    """Extract ?model= from request and return the correct manager."""
    model = request.args.get('model', 'hrrr').lower()
    try:
        return model_registry.get(model)
    except ValueError:
        return None


# =============================================================================
# HTML TEMPLATE
# =============================================================================

HTML_TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>wxsection.com — Cross-Section Dashboard</title>
    <link href="https://api.mapbox.com/mapbox-gl-js/v3.4.0/mapbox-gl.css" rel="stylesheet" />
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
        tailwind.config = {
            theme: {
                extend: {
                    colors: {
                        surface: { DEFAULT: '#1e293b', alt: '#334155' },
                    }
                }
            }
        }
    </script>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        :root {
            --bg: #0f172a;
            --panel: #1e293b;
            --card: #334155;
            --text: #f1f5f9;
            --muted: #94a3b8;
            --accent: #0ea5e9;
            --accent-hover: #38bdf8;
            --border: #475569;
            --success: #22c55e;
            --warning: #f59e0b;
            --danger: #f43f5e;
            --sidebar-icon-w: 48px;
            --sidebar-panel-w: 400px;
        }
        body {
            font-family: system-ui, -apple-system, sans-serif;
            background: var(--bg);
            color: var(--text);
            height: 100vh;
            overflow: hidden;
        }
        label { color: var(--muted); font-size: 12px; font-weight: 500; }
        select {
            background: var(--card);
            color: var(--text);
            border: 1px solid var(--border);
            padding: 5px 8px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 13px;
            min-width: 120px;
        }
        select:focus { outline: 2px solid var(--accent); outline-offset: 1px; }

        /* ===== Forecast Hour Chips ===== */
        .chip-group {
            display: flex;
            gap: 3px;
            align-items: center;
            flex-wrap: wrap;
        }
        .chip {
            background: var(--card);
            color: var(--muted);
            border: 1px solid var(--border);
            padding: 4px 8px;
            border-radius: 12px;
            cursor: pointer;
            font-size: 11px;
            font-weight: 500;
            transition: all 0.15s ease;
            user-select: none;
        }
        .chip:hover { border-color: var(--accent); color: var(--text); }
        .chip.loaded {
            background: rgba(76, 175, 80, 0.15);
            color: #4caf50;
            border-color: #4caf50;
        }
        .chip.loaded:hover { background: rgba(76, 175, 80, 0.3); }
        .chip.active {
            background: var(--accent);
            color: #000;
            border-color: var(--accent);
            font-weight: 700;
        }
        .chip.loading {
            background: var(--warning);
            color: #000;
            border-color: var(--warning);
            animation: pulse 1s infinite;
        }
        .chip:disabled, .chip.unavailable {
            opacity: 0.4;
            cursor: not-allowed;
        }
        .chip.loaded:active, .chip.active:active { opacity: 0.7; }
        .chip.extended {
            border-style: dashed;
            font-size: 10px;
            padding: 3px 5px;
        }
        .chip-divider {
            color: var(--muted);
            margin: 0 2px;
            font-size: 14px;
            user-select: none;
            display: flex;
            align-items: center;
        }

        /* ===== Toggle Groups ===== */
        .toggle-group {
            display: flex;
            border: 1px solid var(--border);
            border-radius: 6px;
            overflow: hidden;
        }
        .toggle-btn {
            background: var(--card);
            color: var(--muted);
            border: none;
            padding: 6px 12px;
            cursor: pointer;
            font-size: 13px;
            font-weight: 500;
            transition: all 0.15s ease;
        }
        .toggle-btn:not(:last-child) { border-right: 1px solid var(--border); }
        .toggle-btn:hover { color: var(--text); }
        .toggle-btn.active { background: var(--accent); color: #000; }
        .toggle-btn.anomaly-active { background: #FF6D00; color: #fff; font-weight: bold; }

        button {
            background: var(--card);
            color: var(--text);
            border: 1px solid var(--border);
            padding: 6px 12px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 13px;
        }
        button:hover { background: var(--accent); color: #000; }

        /* ===== Layout: Icon Sidebar + Expanded Panel + Map + Bottom Panel ===== */
        #app-layout {
            display: flex;
            height: 100vh;
            width: 100vw;
        }

        /* Icon sidebar (48px narrow strip) */
        #icon-sidebar {
            width: var(--sidebar-icon-w);
            background: #0c1222;
            border-right: 1px solid var(--border);
            display: flex;
            flex-direction: column;
            align-items: center;
            padding-top: 8px;
            flex-shrink: 0;
            z-index: 100;
        }
        .icon-tab {
            width: 40px;
            height: 40px;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 8px;
            cursor: pointer;
            color: var(--muted);
            font-size: 18px;
            margin-bottom: 4px;
            transition: all 0.15s ease;
            position: relative;
        }
        .icon-tab:hover { background: var(--card); color: var(--text); }
        .icon-tab.active { background: var(--accent); color: #000; }
        .icon-tab .badge {
            position: absolute;
            top: 2px; right: 2px;
            background: var(--danger);
            color: #fff;
            font-size: 9px;
            font-weight: 700;
            min-width: 14px;
            height: 14px;
            border-radius: 7px;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 0 3px;
        }

        /* Expanded panel (320px, collapsible) */
        #expanded-panel {
            width: var(--sidebar-panel-w);
            background: var(--panel);
            border-right: 1px solid var(--border);
            display: flex;
            flex-direction: column;
            overflow: hidden;
            transition: width 0.2s ease, opacity 0.2s ease;
            flex-shrink: 0;
            z-index: 99;
        }
        #expanded-panel.collapsed {
            width: 0;
            opacity: 0;
            border-right: none;
            pointer-events: none;
        }
        #panel-header {
            padding: 12px 16px;
            border-bottom: 1px solid var(--border);
            font-weight: 600;
            font-size: 14px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-shrink: 0;
        }
        #panel-header .close-panel {
            background: none; border: none; color: var(--muted); cursor: pointer;
            font-size: 16px; padding: 2px 4px;
        }
        #panel-header .close-panel:hover { color: var(--text); background: none; }
        .tab-content {
            display: none;
            flex: 1;
            overflow-y: auto;
            padding: 12px 16px;
        }
        .tab-content.active { display: flex; flex-direction: column; }

        /* ===== Map area (fills remaining space) ===== */
        #map-area {
            flex: 1;
            display: flex;
            flex-direction: column;
            position: relative;
            min-width: 0;
        }
        #map {
            flex: 1;
            z-index: 1;
            width: 100%;
            min-height: 0;
        }

        /* ===== Bottom Slide-Up Panel ===== */
        #bottom-panel {
            position: absolute;
            bottom: 0;
            left: 0;
            right: 0;
            z-index: 50;
            background: var(--panel);
            border-top: 1px solid var(--border);
            transition: height 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            display: flex;
            flex-direction: column;
            box-shadow: 0 -4px 20px rgba(0,0,0,0.3);
        }
        #bottom-panel.collapsed { height: 48px; }
        #bottom-panel.half { height: 40vh; }
        #bottom-panel.full { height: 85vh; }

        #bottom-handle {
            height: 48px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0 16px;
            cursor: ns-resize;
            user-select: none;
            flex-shrink: 0;
            border-bottom: 1px solid var(--border);
        }
        #bottom-handle .drag-indicator {
            width: 40px;
            height: 4px;
            background: var(--border);
            border-radius: 2px;
            position: absolute;
            left: 50%;
            transform: translateX(-50%);
            top: 4px;
        }
        #bottom-status {
            font-size: 12px;
            color: var(--muted);
            display: flex;
            align-items: center;
            gap: 8px;
        }
        #bottom-status .fhr-label { color: var(--accent); font-weight: 600; }
        #bottom-actions {
            display: flex;
            gap: 6px;
            align-items: center;
        }
        .bottom-action-btn {
            background: var(--card);
            border: 1px solid var(--border);
            color: var(--text);
            padding: 3px 8px;
            border-radius: 4px;
            font-size: 11px;
            cursor: pointer;
        }
        .bottom-action-btn:hover { background: var(--accent); color: #000; }

        #bottom-body {
            flex: 1;
            overflow: hidden;
            display: flex;
            flex-direction: column;
        }
        #bottom-panel.collapsed #bottom-body { display: none; }

        /* Cross-section display area inside bottom panel */
        #xsect-container {
            flex: 1;
            display: flex;
            align-items: center;
            justify-content: center;
            overflow: hidden;
            padding: 8px;
        }
        #xsect-img {
            max-width: 100%;
            max-height: 100%;
            border-radius: 4px;
        }
        #instructions {
            color: var(--muted);
            text-align: center;
            padding: 20px;
        }
        .loading-text {
            color: var(--accent);
            animation: pulse 1.5s infinite;
        }

        /* Compare panels inside bottom body */
        #xsect-panels {
            flex: 1;
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }
        #xsect-panels.compare-active { flex-direction: row; }
        .xsect-panel { flex: 1; display: flex; flex-direction: column; overflow: hidden; min-width: 0; }
        .xsect-panel-label {
            padding: 4px 12px; font-size: 11px; color: var(--muted);
            border-bottom: 1px solid var(--border); display: none;
        }
        #xsect-panels.compare-active .xsect-panel-label { display: block; }
        #xsect-panels.compare-active .xsect-panel + .xsect-panel { border-left: 1px solid var(--border); }
        .xsect-panel-body {
            flex: 1; display: flex; align-items: center; justify-content: center;
            padding: 8px; overflow: hidden;
        }
        .xsect-panel-body img { max-width: 100%; max-height: 100%; border-radius: 4px; }

        /* Compare & multi-panel controls inside bottom panel */
        #compare-controls {
            display: none; align-items: center; gap: 8px; padding: 0 16px 8px;
        }
        #compare-controls.visible { display: flex; }
        #compare-controls select { font-size: 12px; }
        #compare-controls .toggle-group { display: flex; gap: 2px; }
        #compare-controls .toggle-btn { font-size: 11px; padding: 2px 8px; }
        #multi-panel-controls {
            display: none; padding: 4px 16px 8px; gap: 6px; flex-direction: column;
        }
        #multi-panel-controls.visible { display: flex; }
        .mp-mode-section { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
        .mp-chip-row { display: flex; gap: 4px; flex-wrap: wrap; }
        .mp-chip {
            font-size: 11px; padding: 2px 8px; border: 1px solid var(--border);
            border-radius: 4px; cursor: pointer; background: var(--bg); color: var(--text);
            transition: background 0.15s, border-color 0.15s;
        }
        .mp-chip:hover { border-color: var(--accent); }
        .mp-chip.selected { background: var(--accent); color: #000; border-color: var(--accent); }
        #multi-panel-controls .toggle-group { display: flex; gap: 2px; }
        #multi-panel-controls .toggle-btn { font-size: 11px; padding: 2px 8px; }

        /* Slider row inside bottom panel */
        #slider-row {
            padding: 4px 16px;
            background: rgba(0,0,0,0.15);
            border-top: 1px solid var(--border);
            gap: 8px;
            display: none;
            align-items: center;
            flex-shrink: 0;
        }
        #slider-row.visible { display: flex; }
        #fhr-slider {
            -webkit-appearance: none; height: 6px; background: var(--card);
            border-radius: 3px; outline: none;
        }
        #fhr-slider::-webkit-slider-thumb {
            -webkit-appearance: none; width: 16px; height: 16px;
            background: var(--accent); border-radius: 50%; cursor: pointer;
        }

        /* ===== Sidebar Controls Tab Styles ===== */
        .ctrl-section {
            margin-bottom: 12px;
        }
        .ctrl-section-title {
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: var(--muted);
            margin-bottom: 6px;
        }
        .ctrl-row {
            display: flex;
            gap: 6px;
            align-items: center;
            flex-wrap: wrap;
            margin-bottom: 6px;
        }
        .ctrl-row label { white-space: nowrap; }
        .ctrl-row select { min-width: 0; flex: 1; }

        /* ===== Cities Tab ===== */
        #city-search {
            width: 100%;
            background: var(--bg);
            border: 1px solid var(--border);
            border-radius: 6px;
            color: var(--text);
            padding: 8px 12px;
            font-size: 13px;
            margin-bottom: 8px;
        }
        #city-search:focus { outline: 2px solid var(--accent); outline-offset: 1px; }
        .region-chips {
            display: flex;
            gap: 4px;
            flex-wrap: wrap;
            margin-bottom: 10px;
        }
        .region-chip {
            font-size: 10px;
            padding: 3px 8px;
            border-radius: 10px;
            cursor: pointer;
            border: 1px solid transparent;
            font-weight: 600;
            transition: all 0.15s;
        }
        .region-chip:hover { opacity: 0.8; }
        .region-chip.active { border-color: white; }
        .region-chip[data-region="california"] { background: #f97316; color: #000; }
        .region-chip[data-region="pnw_rockies"] { background: #22c55e; color: #000; }
        .region-chip[data-region="colorado_basin"] { background: #3b82f6; color: #fff; }
        .region-chip[data-region="southwest"] { background: #ef4444; color: #fff; }
        .region-chip[data-region="southern_plains"] { background: #eab308; color: #000; }
        .region-chip[data-region="southeast_misc"] { background: #a855f7; color: #fff; }
        .city-list {
            flex: 1;
            overflow-y: auto;
        }
        .city-item {
            padding: 8px 10px;
            border-radius: 6px;
            cursor: pointer;
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 13px;
            transition: background 0.1s;
        }
        .city-item:hover { background: var(--card); }
        .city-item .city-name { font-weight: 500; }
        .city-item .city-meta { font-size: 11px; color: var(--muted); }
        .city-detail-panel {
            display: none;
            flex-direction: column;
            gap: 10px;
        }
        .city-detail-panel.active { display: flex; }
        .city-detail-back {
            background: none; border: none; color: var(--accent); cursor: pointer;
            font-size: 12px; padding: 0; text-align: left;
        }
        .city-detail-back:hover { text-decoration: underline; background: none; color: var(--accent-hover); }

        /* ===== Events Tab ===== */
        .event-item {
            padding: 8px 10px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 13px;
            transition: background 0.1s;
            border-left: 3px solid transparent;
            margin-bottom: 4px;
        }
        .event-item:hover { background: var(--card); }
        .event-item .event-name { font-weight: 500; }
        .event-item .event-meta { font-size: 11px; color: var(--muted); }
        .event-item.has-coords { border-left-color: var(--accent); }
        .event-category-chip {
            font-size: 10px; padding: 2px 6px; border-radius: 8px;
            background: var(--card); color: var(--muted); display: inline-block;
        }
        .event-desc {
            font-size: 11px; color: var(--muted); margin: 2px 0 4px;
            line-height: 1.3; opacity: 0.8;
        }
        .event-hero-badge {
            font-size: 9px; padding: 1px 5px; border-radius: 6px;
            background: #0ea5e9; color: #fff; display: inline-block;
            font-weight: 600; letter-spacing: 0.3px; margin-left: 4px;
        }
        .event-data-badge {
            font-size: 9px; padding: 1px 5px; border-radius: 6px;
            background: #22c55e; color: #fff; display: inline-block;
            font-weight: 600; letter-spacing: 0.3px; margin-left: 4px;
        }

        /* ===== Event Detail Panel ===== */
        .event-detail-panel {
            display: none;
            flex-direction: column;
            gap: 10px;
            overflow-y: auto;
        }
        .event-detail-panel.active { display: flex; }
        .event-detail-back {
            background: none; border: none; color: var(--accent); cursor: pointer;
            font-size: 12px; padding: 0; text-align: left;
        }
        .event-detail-back:hover { text-decoration: underline; background: none; color: var(--accent-hover); }
        .event-detail-header {
            display: flex; flex-direction: column; gap: 6px;
        }
        .event-detail-header h3 {
            margin: 0; font-size: 15px; color: var(--text); font-weight: 600;
        }
        .event-detail-header .event-detail-badges {
            display: flex; gap: 6px; align-items: center; flex-wrap: wrap;
        }
        .event-detail-section {
            padding: 8px 0; border-top: 1px solid var(--border);
        }
        .event-detail-section-title {
            font-size: 11px; font-weight: 600; color: var(--accent);
            text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 6px;
        }
        .event-detail-text {
            font-size: 12px; color: var(--text); line-height: 1.5; opacity: 0.9;
        }
        .event-detail-text ul {
            margin: 4px 0; padding-left: 18px;
        }
        .event-detail-text ul li {
            margin-bottom: 4px; font-size: 12px; line-height: 1.4;
        }
        .event-impact-grid {
            display: grid; grid-template-columns: 1fr 1fr; gap: 6px;
        }
        .event-impact-stat {
            background: var(--bg); border: 1px solid var(--border); border-radius: 6px;
            padding: 8px 10px; text-align: center;
        }
        .event-impact-stat .stat-value {
            font-size: 16px; font-weight: 700; color: var(--text);
        }
        .event-impact-stat .stat-label {
            font-size: 10px; color: var(--muted); text-transform: uppercase;
            letter-spacing: 0.3px; margin-top: 2px;
        }
        .event-eval-notes {
            font-size: 11px; color: var(--accent); font-style: italic;
            line-height: 1.5; padding: 6px 10px;
            background: rgba(14, 165, 233, 0.08); border-radius: 6px;
            border-left: 3px solid var(--accent);
        }
        .showcase-actions {
            display: flex; flex-direction: column; gap: 6px;
        }
        .showcase-btn {
            display: flex; align-items: center; gap: 10px;
            width: 100%; padding: 10px 12px; border-radius: 8px;
            background: var(--bg); border: 1px solid var(--border);
            color: var(--text); cursor: pointer; text-align: left;
            transition: border-color 0.15s, background 0.15s;
        }
        .showcase-btn:hover {
            border-color: var(--accent); background: rgba(14, 165, 233, 0.06);
        }
        .showcase-btn .btn-icon {
            font-size: 18px; min-width: 24px; text-align: center;
        }
        .showcase-btn .btn-label {
            font-size: 13px; font-weight: 600;
        }
        .showcase-btn .btn-desc {
            font-size: 11px; color: var(--muted); margin-top: 1px;
        }
        .showcase-btn.primary-action {
            background: rgba(14, 165, 233, 0.1); border-color: var(--accent);
        }
        .showcase-btn.primary-action:hover {
            background: rgba(14, 165, 233, 0.18);
        }

        /* ===== Showcase Notes Bar ===== */
        .showcase-notes-bar {
            background: rgba(14, 165, 233, 0.08);
            border: 1px solid rgba(14, 165, 233, 0.2);
            border-radius: 6px; padding: 8px 12px; margin-bottom: 8px;
        }
        .showcase-notes-bar .notes-title {
            font-size: 10px; font-weight: 600; color: var(--accent);
            text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 4px;
        }
        .showcase-notes-bar #showcase-notes-text {
            font-size: 12px; color: var(--text); line-height: 1.5;
            font-style: italic; opacity: 0.9;
        }

        /* ===== Toast & Progress (repositioned) ===== */
        #toast-container {
            position: fixed;
            bottom: 60px;
            left: 50%;
            transform: translateX(-50%);
            z-index: 10000;
            display: flex;
            flex-direction: column;
            gap: 8px;
        }
        .toast {
            background: var(--panel);
            border: 1px solid var(--border);
            padding: 12px 20px;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
            display: flex;
            align-items: center;
            gap: 10px;
            animation: slideUp 0.3s ease;
        }
        .toast.loading { border-left: 3px solid var(--warning); }
        .toast.success { border-left: 3px solid var(--success); }
        .toast.error { border-left: 3px solid #ef4444; }
        @keyframes slideUp {
            from { transform: translateY(20px); opacity: 0; }
            to { transform: translateY(0); opacity: 1; }
        }
        @keyframes pulse { 50% { opacity: 0.6; } }

        #progress-panel {
            position: fixed;
            bottom: 60px;
            right: 20px;
            z-index: 9999;
            background: var(--panel);
            border: 1px solid var(--border);
            border-radius: 10px;
            padding: 0;
            min-width: 340px;
            max-width: 420px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.4);
            display: none;
            overflow: hidden;
        }
        #progress-panel.visible { display: block; animation: slideUp 0.3s ease; }
        #progress-panel.collapsed .progress-items,
        #progress-panel.collapsed .progress-footer { display: none; }

        /* Progress header */
        .progress-header {
            display: flex; justify-content: space-between; align-items: center;
            padding: 10px 14px; cursor: pointer; user-select: none;
            background: var(--surface); border-bottom: 1px solid var(--border);
            border-radius: 10px 10px 0 0;
        }
        .progress-header:hover { background: var(--surface-alt); }
        .progress-header-left { display: flex; align-items: center; gap: 8px; font-size: 13px; font-weight: 600; color: var(--text); }
        .progress-collapse-icon { font-size: 10px; color: var(--muted); transition: transform 0.2s; }
        #progress-panel.collapsed .progress-collapse-icon { transform: rotate(-90deg); }

        /* Progress badge */
        .progress-badge {
            display: inline-flex; align-items: center; justify-content: center;
            min-width: 20px; height: 20px; padding: 0 6px;
            border-radius: 10px; font-size: 11px; font-weight: 700;
            background: var(--accent); color: #fff;
        }
        .progress-badge.done-badge { background: var(--success); }

        /* Progress items container */
        .progress-items { max-height: 320px; overflow-y: auto; padding: 4px 0; }

        /* Individual progress item */
        .progress-item {
            padding: 10px 14px; border-bottom: 1px solid var(--border);
            transition: opacity 0.3s;
        }
        .progress-item:last-child { border-bottom: none; }
        .progress-item.done { opacity: 0.5; }

        /* Item header row */
        .progress-item-header {
            display: flex; justify-content: space-between; align-items: center;
            margin-bottom: 6px; gap: 8px;
        }
        .progress-label { font-size: 12px; font-weight: 600; color: var(--text); display: flex; align-items: center; gap: 5px; }
        .op-icon { font-size: 11px; opacity: 0.8; }
        .progress-stats { font-size: 11px; color: var(--muted); white-space: nowrap; display: flex; align-items: center; gap: 4px; }

        /* Progress bar */
        .progress-bar-bg {
            width: 100%; height: 6px; border-radius: 3px;
            background: var(--border); overflow: hidden; margin-bottom: 5px;
        }
        .progress-bar-fill {
            height: 100%; border-radius: 3px;
            background: var(--accent); transition: width 0.4s ease;
        }

        /* Color-coded progress bars by operation type */
        .progress-item[data-op="preload"] .progress-bar-fill { background: #6366f1; }
        .progress-item[data-op="autoload"] .progress-bar-fill { background: #818cf8; }
        .progress-item[data-op="download"] .progress-bar-fill { background: #f59e0b; }
        .progress-item[data-op="prerender"] .progress-bar-fill { background: #a855f7; }
        .progress-item[data-op="autoupdate"] .progress-bar-fill { background: #06b6d4; }

        /* Detail row */
        .progress-detail {
            display: flex; justify-content: space-between; align-items: center;
            font-size: 11px; color: var(--muted);
        }
        .eta { font-size: 11px; color: var(--accent); white-space: nowrap; }

        /* Cancel button */
        .cancel-op-btn {
            background: none; border: 1px solid var(--border); border-radius: 4px;
            color: var(--muted); cursor: pointer; font-size: 11px;
            padding: 1px 5px; margin-left: 6px; line-height: 1;
        }
        .cancel-op-btn:hover { color: #ef4444; border-color: #ef4444; }

        /* Progress footer */
        .progress-footer { padding: 6px 14px; font-size: 11px; color: var(--muted); border-top: 1px solid var(--border); }

        /* ===== Modals ===== */
        .modal-overlay {
            display: none; position: fixed; top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(0,0,0,0.6); z-index: 10000; justify-content: center; align-items: center;
        }
        .modal-overlay.visible { display: flex; }
        .modal {
            background: var(--bg); border: 1px solid var(--border); border-radius: 12px;
            padding: 20px; min-width: 360px; max-width: 500px; max-height: 80vh;
            overflow-y: auto; box-shadow: 0 8px 32px rgba(0,0,0,0.4);
        }
        .modal h3 { margin: 0 0 12px 0; font-size: 15px; color: var(--text); }
        .modal .close-btn {
            float: right; background: none; border: none; color: var(--muted);
            font-size: 18px; cursor: pointer; padding: 0 4px;
        }
        .modal .close-btn:hover { color: var(--text); }
        .modal table { width: 100%; border-collapse: collapse; font-size: 12px; }
        .modal th { text-align: left; padding: 6px 8px; border-bottom: 1px solid var(--border); color: var(--muted); font-weight: 600; }
        .modal td { padding: 5px 8px; border-bottom: 1px solid rgba(255,255,255,0.05); }
        .modal .cycle-group { color: var(--accent); font-weight: 600; }
        .modal .summary { margin-top: 12px; padding-top: 10px; border-top: 1px solid var(--border); font-size: 12px; color: var(--muted); }

        #explainer-modal {
            display: none; position: fixed; top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(0,0,0,0.7); z-index: 10001; align-items: center; justify-content: center;
        }
        #explainer-modal.visible { display: flex; }
        .modal-content {
            background: var(--panel); border: 1px solid var(--border); border-radius: 12px;
            width: 90%; max-width: 700px; max-height: 80vh; overflow-y: auto;
            box-shadow: 0 8px 32px rgba(0,0,0,0.5);
        }
        .modal-header {
            padding: 16px 20px; border-bottom: 1px solid var(--border);
            display: flex; justify-content: space-between; align-items: center;
            position: sticky; top: 0; background: var(--panel); z-index: 1;
        }
        .modal-header h2 { margin: 0; font-size: 18px; }
        .modal-close {
            background: none; border: none; color: var(--muted); font-size: 24px;
            cursor: pointer; padding: 0; line-height: 1;
        }
        .modal-close:hover { color: var(--text); background: none; }
        .modal-body { padding: 16px 20px; }

        .param-card {
            background: var(--card); border: 1px solid var(--border);
            border-radius: 8px; padding: 14px; margin-bottom: 12px;
        }
        .param-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px; }
        .param-name { font-weight: 600; color: var(--accent); font-size: 15px; }
        .param-desc { color: var(--muted); font-size: 13px; line-height: 1.5; }
        .param-tech { color: var(--text); font-size: 12px; margin-top: 8px; padding-top: 8px; border-top: 1px solid var(--border); font-family: monospace; }

        #request-modal {
            display: none; position: fixed; top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(0,0,0,0.7); z-index: 10001; align-items: center; justify-content: center;
        }
        #request-modal.visible { display: flex; }
        #run-request-modal {
            display: none; position: fixed; top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(0,0,0,0.7); z-index: 10002; align-items: center; justify-content: center;
        }
        #run-request-modal.visible { display: flex; }
        .request-form { display: flex; flex-direction: column; gap: 12px; }
        .request-form textarea {
            background: var(--bg); border: 1px solid var(--border); border-radius: 6px;
            color: var(--text); padding: 12px; font-size: 14px; resize: vertical;
            min-height: 100px; font-family: inherit;
        }
        .request-form textarea:focus { outline: 2px solid var(--accent); outline-offset: 1px; }
        .request-form input {
            background: var(--bg); border: 1px solid var(--border); border-radius: 6px;
            color: var(--text); padding: 10px 12px; font-size: 14px;
        }
        .request-form input:focus { outline: 2px solid var(--accent); outline-offset: 1px; }
        .submit-btn {
            background: var(--accent);
            color: #000;
            border: none;
            padding: 10px 20px;
            border-radius: 6px;
            font-weight: 600;
            cursor: pointer;
            font-size: 14px;
        }
        .submit-btn:hover { background: #7dd3fc; }
        .submit-btn:disabled { opacity: 0.5; cursor: not-allowed; }
        .request-list {
            max-height: 300px; overflow-y: auto; margin-top: 16px;
            border-top: 1px solid var(--border); padding-top: 16px;
        }
        .request-item {
            background: var(--card); border: 1px solid var(--border);
            border-radius: 6px; padding: 12px; margin-bottom: 8px;
        }
        .request-item-header {
            display: flex; justify-content: space-between; margin-bottom: 6px;
            font-size: 12px; color: var(--muted);
        }
        .request-item-text { font-size: 14px; line-height: 1.4; }

        /* ===== Mapbox GL overrides ===== */
        .mapboxgl-canvas { outline: none; }
        .mapboxgl-popup-content { background: #1e293b; color: #f4f4f4; border-radius: 8px; padding: 12px; font-family: system-ui, sans-serif; }
        .mapboxgl-popup-tip { border-top-color: #1e293b; }
        .mapboxgl-popup-close-button { color: #94a3b8; font-size: 18px; padding: 4px 8px; }
        .mapboxgl-popup-close-button:hover { color: #fff; background: transparent; }
        .mapboxgl-ctrl-attrib { font-size: 10px !important; background: rgba(0,0,0,0.5) !important; }
        .mapboxgl-ctrl-attrib a { color: #94a3b8 !important; }

        /* Memory bar in settings */
        .mem-bar { width: 60px; height: 6px; background: var(--card); border-radius: 3px; overflow: hidden; }
        .mem-fill { height: 100%; background: var(--accent); transition: width 0.3s ease; }

        /* Scrollbar styling */
        ::-webkit-scrollbar { width: 6px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }
        ::-webkit-scrollbar-thumb:hover { background: var(--muted); }

        /* ===== Mobile Responsive ===== */
        @media (max-width: 768px) {
            :root {
                --sidebar-icon-w: 44px;
                --sidebar-panel-w: 100vw;
            }

            /* Stack: icon bar on bottom, panel as full overlay, map fills screen */
            #app-layout {
                flex-direction: column;
            }

            /* Icon sidebar becomes bottom tab bar */
            #icon-sidebar {
                order: 3;
                width: 100%;
                height: 48px;
                flex-direction: row;
                justify-content: space-around;
                padding: 0;
                border-right: none;
                border-top: 1px solid var(--border);
                z-index: 200;
            }
            .icon-tab {
                width: 44px;
                height: 44px;
                margin: 0;
            }

            /* Expanded panel becomes full-screen overlay */
            #expanded-panel {
                position: fixed;
                top: 0;
                left: 0;
                width: 100vw;
                height: calc(100vh - 48px);
                z-index: 150;
                border-right: none;
                transition: transform 0.25s ease, opacity 0.2s ease;
                transform: translateX(0);
            }
            #expanded-panel.collapsed {
                width: 100vw;
                opacity: 0;
                pointer-events: none;
                transform: translateX(-100%);
            }

            /* Map fills remaining space */
            #map-area {
                order: 1;
                flex: 1;
                min-height: 0;
            }

            /* Bottom panel adjustments */
            #bottom-panel { z-index: 120; }
            #bottom-panel.half { height: 45vh; }
            #bottom-panel.full { height: 80vh; }

            /* Larger touch targets */
            .chip { padding: 6px 10px; font-size: 12px; min-height: 32px; }
            .toggle-btn { padding: 8px 14px; font-size: 14px; }
            button { padding: 8px 14px; font-size: 14px; min-height: 36px; }
            select { padding: 8px 10px; font-size: 14px; min-height: 36px; }
            .bottom-action-btn { padding: 6px 12px; font-size: 13px; }

            /* Cross-section images fill width */
            #xsect-panels img { max-width: 100%; height: auto; }

            /* Close panel button gets larger */
            #panel-header .close-panel { font-size: 24px; padding: 4px 8px; }

            /* Menu-top mode: icon sidebar on top instead of bottom */
            body.menu-top #icon-sidebar {
                order: 0;
                border-top: none;
                border-bottom: 1px solid var(--border);
            }
            body.menu-top #map-area { order: 1; }
            body.menu-top #expanded-panel {
                top: 48px;
                height: calc(100vh - 48px);
            }
            body.menu-top #bottom-panel { bottom: 0; }
        }

        /* Small phones (< 400px) */
        @media (max-width: 400px) {
            .icon-tab { width: 38px; height: 38px; }
            #icon-sidebar { height: 44px; }
            #expanded-panel { height: calc(100vh - 44px); }
            body.menu-top #expanded-panel { top: 44px; height: calc(100vh - 44px); }
            .chip { padding: 5px 7px; font-size: 11px; }
        }

    </style>
</head>
<body>
    <!-- ===== APP LAYOUT ===== -->
    <div id="app-layout">

        <!-- Icon Sidebar (48px) -->
        <div id="icon-sidebar">
            <div class="icon-tab active" data-tab="controls" title="Controls">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="4" y1="21" x2="4" y2="14"/><line x1="4" y1="10" x2="4" y2="3"/><line x1="12" y1="21" x2="12" y2="12"/><line x1="12" y1="8" x2="12" y2="3"/><line x1="20" y1="21" x2="20" y2="16"/><line x1="20" y1="12" x2="20" y2="3"/><line x1="1" y1="14" x2="7" y2="14"/><line x1="9" y1="8" x2="15" y2="8"/><line x1="17" y1="16" x2="23" y2="16"/></svg>
            </div>
            <div class="icon-tab" data-tab="cities" title="Fire Weather Cities (232)">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="4" y="2" width="16" height="20" rx="2"/><line x1="8" y1="6" x2="16" y2="6"/><line x1="8" y1="10" x2="16" y2="10"/><line x1="8" y1="14" x2="12" y2="14"/></svg>
            </div>
            <div class="icon-tab" data-tab="events" title="Historical Events (88)">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>
            </div>
            <div class="icon-tab" data-tab="activity" title="Activity">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12,6 12,12 16,14"/></svg>
                <span class="badge" id="activity-badge" style="display:none;">0</span>
            </div>
            <div class="icon-tab" data-tab="settings" title="Settings">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-2 2 2 2 0 01-2-2v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83 0 2 2 0 010-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 01-2-2 2 2 0 012-2h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 010-2.83 2 2 0 012.83 0l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 012-2 2 2 0 012 2v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 0 2 2 0 010 2.83l-.06.06a1.65 1.65 0 00-.33 1.82V9a1.65 1.65 0 001.51 1H21a2 2 0 012 2 2 2 0 01-2 2h-.09a1.65 1.65 0 00-1.51 1z"/></svg>
            </div>
        </div>

        <!-- Expanded Panel (320px, collapsible) -->
        <div id="expanded-panel">
            <div id="panel-header">
                <span id="panel-title">Controls</span>
                <button class="close-panel" id="close-panel-btn" title="Collapse panel">&times;</button>
            </div>

            <!-- TAB: Controls -->
            <div class="tab-content active" id="tab-controls">
                <div class="ctrl-section">
                    <div class="ctrl-section-title">Model & Run</div>
                    <div class="ctrl-row">
                        <label>Model:</label>
                        <select id="model-select"></select>
                    </div>
                    <div class="ctrl-row">
                        <label>Run:</label>
                        <select id="cycle-select" style="font-size:12px;"></select>
                    </div>
                </div>
                <div class="ctrl-section">
                    <div class="ctrl-section-title">Visualization</div>
                    <div class="ctrl-row">
                        <label>Style:</label>
                        <select id="style-select"></select>
                    </div>
                    <div class="ctrl-row" id="temp-cmap-row" style="display:none;">
                        <label>Colormap:</label>
                        <select id="temp-cmap-select">
                            <option value="standard">Standard</option>
                            <option value="nws_ndfd">NWS Classic</option>
                            <option value="white_zero">White at 0\u00b0C</option>
                            <option value="green_purple">Green-Purple</option>
                        </select>
                    </div>
                    <div class="ctrl-row" id="anomaly-group" style="display:none;">
                        <label>Mode:</label>
                        <div class="toggle-group">
                            <button class="toggle-btn active" id="anomaly-off">Raw</button>
                            <button class="toggle-btn" id="anomaly-on">5yr Dep</button>
                        </div>
                    </div>
                    <div class="ctrl-row">
                        <label>Y-Axis:</label>
                        <div class="toggle-group">
                            <button class="toggle-btn active" id="yaxis-pressure">hPa</button>
                            <button class="toggle-btn" id="yaxis-height">km</button>
                            <button class="toggle-btn" id="yaxis-isentropic">\u03b8</button>
                        </div>
                    </div>
                    <div class="ctrl-row">
                        <label>V-Scale:</label>
                        <select id="vscale-select" style="min-width:60px;">
                            <option value="0.5">0.5x</option>
                            <option value="1.0" selected>1x</option>
                            <option value="1.5">1.5x</option>
                            <option value="2.0">2x</option>
                        </select>
                        <label>Top:</label>
                        <select id="ytop-select" style="min-width:70px;">
                            <option value="100" selected>100 hPa</option>
                            <option value="200">200 hPa</option>
                            <option value="300">300 hPa</option>
                            <option value="500">500 hPa</option>
                            <option value="700">700 hPa</option>
                        </select>
                        <label>Units:</label>
                        <select id="units-select" style="min-width:50px;">
                            <option value="km" selected>km</option>
                            <option value="mi">mi</option>
                        </select>
                    </div>
                </div>
                <div class="ctrl-section">
                    <div class="ctrl-section-title">Favorites & Presets</div>
                    <div class="ctrl-row">
                        <select id="favorites-select" style="flex:1;">
                            <option value="">Presets & Favorites</option>
                        </select>
                        <button id="save-favorite-btn" style="padding:3px 8px;font-size:12px;">Save</button>
                    </div>
                </div>
                <div class="ctrl-section">
                    <div class="ctrl-section-title">Map Overlay</div>
                    <div class="ctrl-row">
                        <label>Overlay:</label>
                        <div class="toggle-group">
                            <button class="toggle-btn active" id="overlay-off">Off</button>
                            <button class="toggle-btn" id="overlay-on">On</button>
                        </div>
                        <button class="toggle-btn" id="overlay-loop" style="margin-left:4px;font-size:10px;padding:2px 6px;" title="Animate through forecast hours">Loop</button>
                    </div>
                    <div id="overlay-controls" style="display:none;">
                        <div class="ctrl-row">
                            <label>Product:</label>
                            <select id="overlay-product-select" style="flex:1;font-size:11px;">
                                <option value="surface_analysis">Surface Analysis</option>
                                <option value="radar_composite">Reflectivity</option>
                                <option value="severe_weather">Severe Weather</option>
                                <option value="upper_500">500mb Analysis</option>
                                <option value="upper_250">250mb Jet</option>
                                <option value="moisture">Moisture</option>
                                <option value="fire_weather">Fire Weather</option>
                                <option value="precip">Precipitation</option>
                                <option value="">Custom (single field)</option>
                            </select>
                        </div>
                        <div id="overlay-custom-controls">
                            <div class="ctrl-row">
                                <label>Field:</label>
                                <select id="overlay-field-select" style="flex:1;font-size:11px;"></select>
                            </div>
                            <div class="ctrl-row" id="overlay-level-row" style="display:none;">
                                <label>Level:</label>
                                <select id="overlay-level-select" style="min-width:80px;">
                                    <option value="850">850 hPa</option>
                                    <option value="700">700 hPa</option>
                                    <option value="500" selected>500 hPa</option>
                                    <option value="300">300 hPa</option>
                                    <option value="250">250 hPa</option>
                                </select>
                            </div>
                        </div>
                        <div class="ctrl-row">
                            <label>Opacity:</label>
                            <input type="range" id="overlay-opacity" min="0" max="100" value="70" style="flex:1;">
                            <span id="overlay-opacity-val" style="font-size:11px;min-width:30px;">70%</span>
                        </div>
                    </div>
                </div>
                <div class="ctrl-section">
                    <div class="ctrl-section-title">Forecast Hours</div>
                    <div class="chip-group" id="fhr-chips"></div>
                </div>
                <div class="ctrl-section">
                    <div class="ctrl-section-title">Actions</div>
                    <div class="ctrl-row" style="flex-wrap:wrap;">
                        <button id="swap-btn" style="padding:3px 8px;font-size:12px;">Swap</button>
                        <button id="clear-btn" style="padding:3px 8px;font-size:12px;">Clear</button>
                        <button id="poi-btn" style="padding:3px 8px;font-size:12px;" title="Place POI marker (or right-click map)">+ POI</button>
                        <button id="load-all-btn" style="padding:3px 8px;font-size:12px;">Load All</button>
                        <button id="gif-btn" style="padding:3px 8px;font-size:12px;">GIF</button>
                        <button id="compare-btn" style="padding:3px 8px;font-size:12px;">Compare</button>
                        <button id="help-btn" style="padding:3px 8px;font-size:12px;">Guide</button>
                    </div>
                    <div class="ctrl-row">
                        <select id="gif-speed" title="GIF speed" style="min-width:55px;font-size:11px;">
                            <option value="1">1x</option>
                            <option value="0.75">0.75x</option>
                            <option value="0.5" selected>0.5x</option>
                            <option value="0.25">0.25x</option>
                        </select>
                        <input id="gif-fhr-min" type="number" placeholder="F start" title="GIF start FHR" style="width:50px;padding:2px 4px;font-size:11px;background:var(--bg);border:1px solid var(--border);border-radius:4px;color:var(--text);">
                        <input id="gif-fhr-max" type="number" placeholder="F end" title="GIF end FHR" style="width:50px;padding:2px 4px;font-size:11px;background:var(--bg);border:1px solid var(--border);border-radius:4px;color:var(--text);">
                    </div>
                    <div class="ctrl-row">
                        <select id="multi-panel-mode" title="Multi-panel comparison" style="font-size:11px;padding:2px 4px;flex:1;">
                            <option value="">Multi-Panel</option>
                            <option value="model">Model vs Model</option>
                            <option value="temporal">Temporal (FHRs)</option>
                            <option value="product">Multi-Product</option>
                            <option value="cycle">Cycle Compare</option>
                        </select>
                        <button id="request-cycle-btn" style="padding:3px 8px;font-size:12px;">Request Run</button>
                    </div>
                </div>
            </div>

            <!-- TAB: Cities -->
            <div class="tab-content" id="tab-cities">
                <div id="city-list-view">
                    <input type="text" id="city-search" placeholder="Search 232 cities...">
                    <div class="region-chips" id="region-chips">
                        <span class="region-chip active" data-region="all" style="background:var(--card);color:var(--text);">All</span>
                        <span class="region-chip" data-region="california">CA</span>
                        <span class="region-chip" data-region="pnw_rockies">PNW</span>
                        <span class="region-chip" data-region="colorado_basin">CO</span>
                        <span class="region-chip" data-region="southwest">SW</span>
                        <span class="region-chip" data-region="southern_plains">Plains</span>
                        <span class="region-chip" data-region="southeast_misc">SE</span>
                    </div>
                    <div class="city-list" id="city-list"></div>
                </div>
                <div class="city-detail-panel" id="city-detail">
                    <button class="city-detail-back" id="city-detail-back">&larr; Back to list</button>
                    <div id="city-detail-content"></div>
                </div>
            </div>

            <!-- TAB: Events -->
            <div class="tab-content" id="tab-events">
                <div id="event-list-view">
                    <input type="text" id="event-search" placeholder="Search events..." style="width:100%;background:var(--bg);border:1px solid var(--border);border-radius:6px;color:var(--text);padding:8px 12px;font-size:13px;margin-bottom:8px;">
                    <div class="ctrl-row" style="margin-bottom:8px;">
                        <label style="font-size:11px;">Filter:</label>
                        <select id="event-category-filter" style="font-size:11px;min-width:80px;">
                            <option value="">All Categories</option>
                        </select>
                        <label><input type="checkbox" id="event-coords-only" style="margin-right:4px;">With coords</label>
                    </div>
                    <div id="event-list" style="flex:1;overflow-y:auto;"></div>
                </div>
                <div class="event-detail-panel" id="event-detail">
                    <button class="event-detail-back" id="event-detail-back">&larr; Back to events</button>
                    <div id="event-detail-content"></div>
                </div>
            </div>

            <!-- TAB: Activity -->
            <div class="tab-content" id="tab-activity">
                <div class="ctrl-section">
                    <div class="ctrl-section-title">Generation Progress</div>
                    <div id="activity-progress-items"></div>
                </div>
                <div class="ctrl-section">
                    <div class="ctrl-section-title">Memory Status</div>
                    <div id="memory-status" style="cursor:pointer;">
                        <span id="mem-text" style="font-size:12px;color:var(--muted);">0 MB</span>
                        <div class="mem-bar"><div class="mem-fill" id="mem-fill" style="width:0%"></div></div>
                    </div>
                </div>
            </div>

            <!-- TAB: Settings -->
            <div class="tab-content" id="tab-settings">
                <div class="ctrl-section">
                    <div class="ctrl-section-title">Map Style</div>
                    <div class="ctrl-row">
                        <label>Basemap:</label>
                        <select id="tile-layer-select" style="flex:1;">
                            <option value="dark">Dark</option>
                            <option value="light">Light</option>
                            <option value="satellite">Satellite</option>
                            <option value="outdoors">Outdoors</option>
                        </select>
                    </div>
                </div>
                <div class="ctrl-section">
                    <div class="ctrl-section-title">Map Markers</div>
                    <div class="ctrl-row">
                        <label><input type="checkbox" id="toggle-city-markers" style="margin-right:4px;">Show city markers</label>
                    </div>
                    <div class="ctrl-row">
                        <label><input type="checkbox" id="toggle-event-markers" style="margin-right:4px;">Show event markers</label>
                    </div>
                    <div class="ctrl-row">
                        <label><input type="checkbox" id="toggle-clustering" checked style="margin-right:4px;">Cluster markers</label>
                    </div>
                </div>
                <div class="ctrl-section mobile-only-setting" style="display:none;">
                    <div class="ctrl-section-title">Layout</div>
                    <div class="ctrl-row">
                        <label>Menu position:</label>
                        <select id="menu-position-select" style="flex:1;">
                            <option value="bottom">Bottom</option>
                            <option value="top">Top</option>
                        </select>
                    </div>
                    <div style="font-size:11px;color:var(--muted);margin-top:4px;">
                        Use "Top" if your browser has a bottom URL bar (e.g. Safari on iPhone).
                    </div>
                </div>
            </div>
        </div>

        <!-- Map Area (fills remaining space) -->
        <div id="map-area">
            <div id="map"></div>
            <!-- Map Overlay Colorbar Legend -->
            <div id="overlay-colorbar" style="display:none;position:absolute;bottom:30px;right:10px;z-index:1000;background:rgba(0,0,0,0.75);border-radius:6px;padding:6px 10px;pointer-events:none;">
                <div style="font-size:10px;color:#ccc;margin-bottom:3px;" id="colorbar-title"></div>
                <canvas id="colorbar-canvas" width="200" height="14" style="border-radius:2px;display:block;"></canvas>
                <div style="display:flex;justify-content:space-between;font-size:9px;color:#aaa;margin-top:2px;">
                    <span id="colorbar-min"></span>
                    <span id="colorbar-units" style="opacity:0.7;"></span>
                    <span id="colorbar-max"></span>
                </div>
            </div>

            <!-- Bottom Slide-Up Panel -->
            <div id="bottom-panel" class="collapsed">
                <div id="bottom-handle">
                    <div class="drag-indicator"></div>
                    <div id="bottom-status">
                        <span>Cross-Section</span>
                        <span class="fhr-label" id="active-fhr"></span>
                    </div>
                    <div id="bottom-actions">
                        <button class="bottom-action-btn" id="bottom-expand-btn" title="Expand">&#9650;</button>
                        <button class="bottom-action-btn" id="bottom-collapse-btn" title="Collapse" style="display:none;">&#9660;</button>
                    </div>
                </div>
                <div id="bottom-body">
                    <!-- Slider row -->
                    <div id="slider-row">
                        <button id="prev-btn" title="Previous frame" style="padding:3px 6px;font-size:12px;min-width:28px;">&#9664;</button>
                        <button id="play-btn" title="Auto-play" style="padding:3px 8px;font-size:14px;min-width:32px;">&#9654;</button>
                        <button id="next-btn" title="Next frame" style="padding:3px 6px;font-size:12px;min-width:28px;">&#9654;</button>
                        <input type="range" id="fhr-slider" min="0" max="18" value="0" style="flex:1;">
                        <span id="slider-label" style="font-size:11px;color:var(--muted);min-width:32px;text-align:center;">F00</span>
                        <select id="play-speed" title="Playback speed" style="min-width:50px;font-size:11px;">
                            <option value="2000">0.5x</option>
                            <option value="1000" selected>1x</option>
                            <option value="500">2x</option>
                            <option value="250">4x</option>
                        </select>
                        <button id="prerender-btn" title="Pre-render all frames" style="padding:3px 6px;font-size:11px;">Pre-render</button>
                    </div>
                    <!-- Compare controls -->
                    <div id="compare-controls">
                        <label style="font-size:12px;color:var(--muted);">vs</label>
                        <select id="compare-cycle-select" style="min-width:120px;"></select>
                        <div class="toggle-group" id="compare-mode-toggle">
                            <button class="toggle-btn active" data-value="same_fhr">Same FHR</button>
                            <button class="toggle-btn" data-value="valid_time">Valid Time</button>
                        </div>
                        <span id="compare-fhr-label" style="font-size:11px;color:var(--muted);"></span>
                    </div>
                    <!-- Multi-panel controls -->
                    <div id="multi-panel-controls">
                        <div id="mp-model-controls" class="mp-mode-section" style="display:none;">
                            <label style="font-size:11px;color:var(--muted);">Models:</label>
                            <div id="mp-model-checkboxes" class="mp-chip-row"></div>
                        </div>
                        <div id="mp-temporal-controls" class="mp-mode-section" style="display:none;">
                            <label style="font-size:11px;color:var(--muted);">FHRs:</label>
                            <input id="mp-fhrs-input" type="text" placeholder="e.g. 0,6,12" style="width:100px;padding:2px 6px;font-size:11px;background:var(--bg);border:1px solid var(--border);border-radius:4px;color:var(--text);">
                            <button id="mp-temporal-go" style="padding:2px 8px;font-size:11px;">Go</button>
                        </div>
                        <div id="mp-product-controls" class="mp-mode-section" style="display:none;">
                            <label style="font-size:11px;color:var(--muted);">Products:</label>
                            <div id="mp-product-checkboxes" class="mp-chip-row"></div>
                        </div>
                        <div id="mp-cycle-controls" class="mp-mode-section" style="display:none;">
                            <label style="font-size:11px;color:var(--muted);">vs Cycle:</label>
                            <select id="mp-cycle-select" style="min-width:120px;font-size:11px;"></select>
                            <div class="toggle-group" id="mp-cycle-match-toggle">
                                <button class="toggle-btn active" data-value="same_fhr">Same FHR</button>
                                <button class="toggle-btn" data-value="valid_time">Valid Time</button>
                            </div>
                            <button id="mp-cycle-go" style="padding:2px 8px;font-size:11px;">Go</button>
                        </div>
                        <div id="mp-status" style="display:none;font-size:11px;color:var(--accent);padding:2px 0;"></div>
                    </div>
                    <!-- Showcase notes bar -->
                    <div id="showcase-notes" class="showcase-notes-bar" style="display:none;">
                        <div class="notes-title">Analysis</div>
                        <div id="showcase-notes-text"></div>
                    </div>
                    <!-- Cross-section panels -->
                    <div id="xsect-panels">
                        <div class="xsect-panel" id="panel-primary">
                            <div class="xsect-panel-label" id="panel-primary-label"></div>
                            <div class="xsect-panel-body" id="xsect-container">
                                <div id="instructions">
                                    Click two points on the map to draw a cross-section line.<br>
                                    Then select forecast hours to load.
                                </div>
                            </div>
                        </div>
                        <div class="xsect-panel" id="panel-compare" style="display:none;">
                            <div class="xsect-panel-label" id="panel-compare-label"></div>
                            <div class="xsect-panel-body" id="xsect-container-compare">
                                <div style="color:var(--muted);">Select a comparison cycle</div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- Toast & Progress (overlays) -->
    <div id="toast-container"></div>
    <div id="progress-panel">
        <div class="progress-header" id="progress-header">
            <span class="progress-header-left">Activity <span class="progress-badge" id="progress-badge">0</span></span>
            <span class="progress-collapse-icon">&#9660;</span>
        </div>
        <div class="progress-items" id="progress-items"></div>
        <div class="progress-footer" id="progress-footer"></div>
    </div>

    <!-- Modals (unchanged) -->
    <div id="explainer-modal">
        <div class="modal-content">
            <div class="modal-header">
                <h2>Style Guide</h2>
                <button class="modal-close" id="modal-close">&times;</button>
            </div>
            <div class="modal-body" id="modal-body"></div>
        </div>
    </div>

    <div id="request-modal">
        <div class="modal-content">
            <div class="modal-header">
                <h2>Feature Requests & Feedback</h2>
                <button class="modal-close" id="request-modal-close">&times;</button>
            </div>
            <div class="modal-body">
                <form class="request-form" id="request-form">
                    <input type="text" id="request-name" placeholder="Your name (optional)">
                    <textarea id="request-text" placeholder="Describe your feature request, bug report, or feedback..." required></textarea>
                    <button type="submit" class="submit-btn">Submit Request</button>
                </form>
                <div class="request-list" id="request-list"></div>
            </div>
        </div>
    </div>

    <div id="run-request-modal">
        <div class="modal-content" style="max-width:340px;padding:20px;">
            <div class="modal-header" style="margin-bottom:12px;">
                <h2 style="font-size:16px;margin:0;">Request Archive Run</h2>
                <button class="modal-close" id="req-cancel">&times;</button>
            </div>
            <div style="display:flex;flex-direction:column;gap:10px;">
                <div>
                    <label style="font-size:12px;color:var(--muted);display:block;margin-bottom:3px;">Date</label>
                    <input type="date" id="req-date" style="width:100%;padding:6px 8px;background:var(--bg);border:1px solid var(--border);border-radius:4px;color:var(--text);font-size:14px;">
                </div>
                <div>
                    <label style="font-size:12px;color:var(--muted);display:block;margin-bottom:3px;">Init Hour (UTC)</label>
                    <select id="req-hour" style="width:100%;padding:6px 8px;background:var(--bg);border:1px solid var(--border);border-radius:4px;color:var(--text);font-size:14px;">
                        <option value="0">00z</option><option value="1">01z</option><option value="2">02z</option>
                        <option value="3">03z</option><option value="4">04z</option><option value="5">05z</option>
                        <option value="6">06z</option><option value="7">07z</option><option value="8">08z</option>
                        <option value="9">09z</option><option value="10">10z</option><option value="11">11z</option>
                        <option value="12" selected>12z</option><option value="13">13z</option><option value="14">14z</option>
                        <option value="15">15z</option><option value="16">16z</option><option value="17">17z</option>
                        <option value="18">18z</option><option value="19">19z</option><option value="20">20z</option>
                        <option value="21">21z</option><option value="22">22z</option><option value="23">23z</option>
                    </select>
                </div>
                <div style="display:flex;gap:8px;align-items:end;">
                    <div style="flex:1;">
                        <label style="font-size:12px;color:var(--text-dim);display:block;margin-bottom:3px;">FHR Start</label>
                        <input type="number" id="req-fhr-start" value="0" min="0" max="48" style="width:100%;padding:6px 8px;background:var(--bg);border:1px solid var(--border);border-radius:4px;color:var(--text);font-size:14px;">
                    </div>
                    <span style="padding-bottom:8px;color:var(--text-dim);">to</span>
                    <div style="flex:1;">
                        <label style="font-size:12px;color:var(--text-dim);display:block;margin-bottom:3px;">FHR End <span id="req-fhr-max-hint" style="opacity:0.6;">(max 18)</span></label>
                        <input type="number" id="req-fhr-end" value="18" min="0" max="48" style="width:100%;padding:6px 8px;background:var(--bg);border:1px solid var(--border);border-radius:4px;color:var(--text);font-size:14px;">
                    </div>
                </div>
                <button id="req-submit" style="padding:8px;background:var(--accent,#4a9eff);border:none;border-radius:4px;color:#fff;font-size:14px;cursor:pointer;font-weight:500;margin-top:4px;">Download & Load</button>
            </div>
        </div>
    </div>

    <div class="modal-overlay" id="ram-modal">
        <div class="modal">
            <button class="close-btn" id="ram-modal-close">&times;</button>
            <h3>RAM Status</h3>
            <div id="ram-modal-body"></div>
        </div>
    </div>
    <script src="https://api.mapbox.com/mapbox-gl-js/v3.4.0/mapbox-gl.js"></script>
    <script>
        const styles = ''' + json.dumps(XSECT_STYLES) + ''';
        const MAX_SELECTED = 4;

        // =====================================================================
        // State (all preserved from original)
        // =====================================================================
        let startMarker = null, endMarker = null, lineExists = false;
        let poiMarkers = [];  // Array of {marker, label} objects

        // ---- Mapbox marker/line helpers ----
        function createXSMarker(lat, lng, color) {
            const el = document.createElement('div');
            el.style.cssText = 'width:' + markerSize + 'px;height:' + markerSize + 'px;background:' + color + ';border-radius:50%;border:2px solid white;cursor:grab;box-shadow:0 1px 4px rgba(0,0,0,0.4);';
            const m = new mapboxgl.Marker({ element: el, draggable: true })
                .setLngLat([lng, lat])
                .addTo(map);
            // Leaflet-compat: getLatLng() returns {lat, lng}
            m.getLatLng = () => { const ll = m.getLngLat(); return { lat: ll.lat, lng: ll.lng }; };
            return m;
        }

        function updateLine() {
            if (!startMarker || !endMarker || !mapStyleLoaded) return;
            const s = startMarker.getLngLat();
            const e = endMarker.getLngLat();
            const data = {
                type: 'Feature',
                geometry: { type: 'LineString', coordinates: [[s.lng, s.lat], [e.lng, e.lat]] }
            };
            if (map.getSource('xs-line')) {
                map.getSource('xs-line').setData(data);
            } else {
                map.addSource('xs-line', { type: 'geojson', data: data });
                map.addLayer({
                    id: 'xs-line',
                    type: 'line',
                    source: 'xs-line',
                    paint: { 'line-color': '#fbbf24', 'line-width': 3, 'line-dasharray': [3, 1.5] }
                });
            }
            lineExists = true;
        }

        function removeLine() {
            if (mapStyleLoaded) {
                if (map.getLayer('xs-line')) map.removeLayer('xs-line');
                if (map.getSource('xs-line')) map.removeSource('xs-line');
            }
            lineExists = false;
        }

        function clearXSMarkers() {
            if (startMarker) { startMarker.remove(); startMarker = null; }
            if (endMarker) { endMarker.remove(); endMarker = null; }
            removeLine();
        }

        function setupStartMarker(lat, lng) {
            const m = createXSMarker(lat, lng, '#38bdf8');
            m.on('drag', () => { updateLine(); liveDragRender(); });
            m.on('dragend', () => { invalidatePrerender(); generateCrossSection(); });
            return m;
        }

        function setupEndMarker(lat, lng) {
            const m = createXSMarker(lat, lng, '#f87171');
            m.on('drag', () => { updateLine(); liveDragRender(); });
            m.on('dragend', () => { invalidatePrerender(); generateCrossSection(); });
            return m;
        }
        let cycles = [];
        let currentCycle = null;
        let selectedFhrs = [];
        let activeFhr = null;
        let currentModel = 'hrrr';
        let modelExcludedStyles = {};

        let isPlaying = false;
        let playInterval = null;
        let prerenderedFrames = {};
        let xsectAbortController = null;

        let compareActive = false;
        let compareCycle = null;
        let compareMode = 'same_fhr';

        // New state for cities/events
        let allCities = [];
        let allEvents = [];
        let cityClusterGroup = null;
        let eventLayerGroup = null;
        let activeRegionFilter = 'all';
        let selectedCityKey = null;

        function modelParam() { return `&model=${currentModel}`; }

        // Load available models from server and populate dropdown
        async function loadModels() {
            try {
                const res = await fetch('/api/models');
                const data = await res.json();
                const select = document.getElementById('model-select');
                select.innerHTML = '';
                (data.models || []).forEach(m => {
                    const opt = document.createElement('option');
                    opt.value = m.id;
                    opt.textContent = m.name.toUpperCase();
                    select.appendChild(opt);
                    if (m.excluded_styles) {
                        modelExcludedStyles[m.id] = new Set(m.excluded_styles);
                    }
                });
                if (select.options.length > 0) {
                    currentModel = select.value;
                }
                select.onchange = async () => {
                    currentModel = select.value;
                    stopPlayback();
                    invalidatePrerender();
                    modelMapOverlay.invalidateCache();
                    updateStyleDropdownForModel();
                    await loadCycles();
                    generateCrossSection();
                    modelMapOverlay.loadFieldsMeta().then(() => modelMapOverlay.update());
                };
            } catch (e) {
                console.error('Failed to load models:', e);
                // Fallback: just show HRRR
                const select = document.getElementById('model-select');
                select.innerHTML = '<option value="hrrr">HRRR</option>';
            }
        }

        // Hide styles that aren't available for the current model
        function updateStyleDropdownForModel() {
            const excluded = modelExcludedStyles[currentModel] || new Set();
            const select = document.getElementById('style-select');
            const currentVal = select.value;
            Array.from(select.options).forEach(opt => {
                opt.style.display = excluded.has(opt.value) ? 'none' : '';
            });
            // If current selection is excluded, switch to first visible
            if (excluded.has(currentVal)) {
                const first = Array.from(select.options).find(o => !excluded.has(o.value));
                if (first) select.value = first.value;
            }
            updateTempCmapVisibility();
            updateAnomalyVisibility();
        }

        // Load All button — loads every FHR for current cycle
        document.getElementById('load-all-btn').onclick = async () => {
            if (!currentCycle) return;
            const btn = document.getElementById('load-all-btn');
            btn.disabled = true;
            btn.textContent = 'Loading...';
            const toast = showToast(`Loading all FHRs for ${currentCycle}...`);
            try {
                const res = await fetch(`/api/load_cycle?cycle=${currentCycle}${modelParam()}`, {method: 'POST'});
                const data = await res.json();
                toast.remove();
                if (data.success) {
                    showToast(`Loaded ${data.loaded_fhrs} FHRs (${Math.round(data.memory_mb || 0)} MB)`, 'success');
                    await refreshLoadedStatus();
                    updateChipStates();
                } else {
                    showToast(data.error || 'Load failed', 'error');
                }
            } catch (err) {
                toast.remove();
                showToast('Load all failed: ' + err.message, 'error');
            }
            btn.disabled = false;
            btn.textContent = 'Load All';
        };

        // =====================================================================
        // Sidebar Tab Switching
        // =====================================================================
        const iconTabs = document.querySelectorAll('.icon-tab');
        const tabContents = document.querySelectorAll('.tab-content');
        const expandedPanel = document.getElementById('expanded-panel');
        const panelTitle = document.getElementById('panel-title');
        const tabNames = { controls: 'Controls', cities: 'Fire Weather Cities', events: 'Historical Events', activity: 'Activity', settings: 'Settings' };
        let activeTab = 'controls';

        function closePanelMobile() {
            // On mobile, close the overlay panel to reveal the map
            if (isMobile && !expandedPanel.classList.contains('collapsed')) {
                expandedPanel.classList.add('collapsed');
                iconTabs.forEach(t => t.classList.remove('active'));
                setTimeout(() => map.resize(), 300);
            }
        }

        function switchTab(tabId) {
            if (activeTab === tabId && !expandedPanel.classList.contains('collapsed')) {
                // Clicking active tab collapses
                expandedPanel.classList.add('collapsed');
                iconTabs.forEach(t => t.classList.remove('active'));
                setTimeout(() => map.resize(), 250);
                return;
            }
            activeTab = tabId;
            expandedPanel.classList.remove('collapsed');
            iconTabs.forEach(t => t.classList.toggle('active', t.dataset.tab === tabId));
            tabContents.forEach(tc => tc.classList.toggle('active', tc.id === 'tab-' + tabId));
            panelTitle.textContent = tabNames[tabId] || tabId;
            // Trigger resize so map reflows
            setTimeout(() => map.resize(), 250);
        }

        iconTabs.forEach(tab => {
            tab.addEventListener('click', () => switchTab(tab.dataset.tab));
        });

        document.getElementById('close-panel-btn').onclick = () => {
            expandedPanel.classList.add('collapsed');
            iconTabs.forEach(t => t.classList.remove('active'));
            setTimeout(() => map.resize(), 250);
        };

        // =====================================================================
        // Bottom Panel State Management
        // =====================================================================
        const bottomPanel = document.getElementById('bottom-panel');
        const bottomExpandBtn = document.getElementById('bottom-expand-btn');
        const bottomCollapseBtn = document.getElementById('bottom-collapse-btn');
        let bottomState = 'collapsed'; // 'collapsed', 'half', 'full'

        function setBottomState(state) {
            bottomState = state;
            bottomPanel.className = state;
            bottomExpandBtn.style.display = state === 'full' ? 'none' : '';
            bottomCollapseBtn.style.display = state === 'collapsed' ? 'none' : '';
            bottomExpandBtn.innerHTML = state === 'collapsed' ? '&#9650;' : '&#9650;&#9650;';
            setTimeout(() => map.resize(), 350);
        }

        bottomExpandBtn.onclick = () => {
            if (bottomState === 'collapsed') setBottomState('half');
            else if (bottomState === 'half') setBottomState('full');
        };

        bottomCollapseBtn.onclick = () => {
            if (bottomState === 'full') setBottomState('half');
            else if (bottomState === 'half') setBottomState('collapsed');
        };

        // Double-click handle to toggle collapsed/half
        document.getElementById('bottom-handle').addEventListener('dblclick', () => {
            if (bottomState === 'collapsed') setBottomState('half');
            else setBottomState('collapsed');
        });

        // =====================================================================
        // Initialize Map (Mapbox GL JS)
        // =====================================================================
        const isMobile = window.matchMedia('(max-width: 768px)').matches || ('ontouchstart' in window && window.innerWidth < 900);
        const markerSize = isMobile ? 24 : 16;
        const markerAnchor = markerSize / 2;

        mapboxgl.accessToken = '%%MAPBOX_TOKEN%%';
        const MAPBOX_STYLES = {
            dark: 'mapbox://styles/mapbox/dark-v11',
            light: 'mapbox://styles/mapbox/light-v11',
            satellite: 'mapbox://styles/mapbox/satellite-streets-v12',
            outdoors: 'mapbox://styles/mapbox/outdoors-v12',
        };
        let currentStyleKey = 'dark';
        const map = new mapboxgl.Map({
            container: 'map',
            style: MAPBOX_STYLES.dark,
            center: [-98, 39],
            zoom: isMobile ? 4 : 5,
            minZoom: 3,
            maxZoom: 12,
            projection: 'mercator',
        });
        map.addControl(new mapboxgl.NavigationControl(), 'top-right');

        // Track map load state for deferred source/layer additions
        let mapStyleLoaded = false;

        // ---- Compatibility helpers: Leaflet [lat,lng] → Mapbox [lng,lat] ----
        function fitBoundsLL(latLngs, padding) {
            // Accept [[lat,lng],[lat,lng]] like Leaflet, convert to Mapbox [[lng,lat],[lng,lat]]
            const sw = [latLngs[0][1], latLngs[0][0]];
            const ne = [latLngs[1][1], latLngs[1][0]];
            map.fitBounds([sw, ne], { padding: padding || 50 });
        }

        // ---- Re-add custom sources/layers after style change ----
        let _pendingStyleReload = false;
        // Forward-declare variables used by readdCustomLayers (defined later)
        var _citiesGeoJSON = null;
        var _eventsGeoJSON = null;
        var _modelMapOverlayRef = null;  // set after modelMapOverlay IIFE
        function readdCustomLayers() {
            // Weather overlay source (hidden by default)
            addWeatherOverlaySource();
            // XS line
            if (startMarker && endMarker) updateLine();
            // City + event GeoJSON layers
            if (_citiesGeoJSON && typeof addCityLayers === 'function') addCityLayers(_citiesGeoJSON);
            if (_eventsGeoJSON && typeof addEventLayers === 'function') addEventLayers(_eventsGeoJSON);
            // Restore overlay visibility
            if (_modelMapOverlayRef && _modelMapOverlayRef._isEnabled()) {
                map.setLayoutProperty('weather-overlay-a', 'visibility', 'visible');
                map.setLayoutProperty('weather-overlay-b', 'visibility', 'visible');
                _modelMapOverlayRef.update();
            }
        }

        map.on('style.load', () => {
            mapStyleLoaded = true;
            readdCustomLayers();
        });

        // Settings: basemap style selector
        document.getElementById('tile-layer-select').onchange = function() {
            const style = MAPBOX_STYLES[this.value];
            if (style) {
                currentStyleKey = this.value;
                map.setStyle(style);
            }
        };

        // =========================================================================
        // Weather overlay — Mapbox image source (server-rendered PNGs)
        // =========================================================================
        // 1x1 transparent PNG for placeholder
        const TRANSPARENT_PNG = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=';
        const OVERLAY_BOUNDS = [[-135, 53], [-60, 53], [-60, 21], [-135, 21]]; // TL, TR, BR, BL

        function findFirstLabelLayer() {
            // Find the first Mapbox label or boundary layer to insert overlay below it
            const layers = map.getStyle().layers;
            for (const layer of layers) {
                // Mapbox dark-v11 uses these prefixes for labels and boundaries
                if (layer.id.match(/^(admin|state|country|place|settlement|poi|road-label|water-label|natural)/)) {
                    return layer.id;
                }
            }
            return undefined; // add on top if no label layer found
        }

        function addWeatherOverlaySource() {
            if (map.getSource('weather-overlay-a')) return;
            // Double-buffered overlay: two image sources/layers for flash-free swaps
            map.addSource('weather-overlay-a', { type: 'image', url: TRANSPARENT_PNG, coordinates: OVERLAY_BOUNDS });
            map.addSource('weather-overlay-b', { type: 'image', url: TRANSPARENT_PNG, coordinates: OVERLAY_BOUNDS });
            const beforeLayer = findFirstLabelLayer();
            map.addLayer({
                id: 'weather-overlay-b', type: 'raster', source: 'weather-overlay-b',
                paint: { 'raster-opacity': 0 }, layout: { visibility: 'none' },
            }, beforeLayer);
            map.addLayer({
                id: 'weather-overlay-a', type: 'raster', source: 'weather-overlay-a',
                paint: { 'raster-opacity': 0.7 }, layout: { visibility: 'none' },
            }, beforeLayer);
            // Alias for compatibility checks
            map._weatherOverlayActiveLayer = 'a';

            // Bold white state/country borders above overlay
            if (!map.getLayer('admin-borders-bold')) {
                map.addLayer({
                    id: 'admin-borders-bold',
                    type: 'line',
                    source: 'composite',
                    'source-layer': 'admin',
                    filter: ['==', ['get', 'admin_level'], 1],
                    paint: {
                        'line-color': '#ffffff',
                        'line-width': 1.5,
                        'line-opacity': 0.7,
                    },
                });
                map.addLayer({
                    id: 'country-borders-bold',
                    type: 'line',
                    source: 'composite',
                    'source-layer': 'admin',
                    filter: ['==', ['get', 'admin_level'], 0],
                    paint: {
                        'line-color': '#ffffff',
                        'line-width': 2,
                        'line-opacity': 0.8,
                    },
                });
                // Coastline outlines (water polygon boundaries)
                map.addLayer({
                    id: 'coastline-bold',
                    type: 'line',
                    source: 'composite',
                    'source-layer': 'water',
                    paint: {
                        'line-color': '#ffffff',
                        'line-width': 1.2,
                        'line-opacity': 0.5,
                    },
                });
            }
        }

        // Model Map Overlay controller (Mapbox GL JS version — always PNG, no WebGL)
        const modelMapOverlay = (function() {
            let enabled = false;
            let currentField = 'temperature';
            let currentLevel = 500;
            let currentProduct = 'surface_analysis';
            let opacity = 0.7;
            let fieldsMetadata = null;
            let productsMetadata = null;
            let colormapLUTs = {};
            let abortCtrl = null;
            let dataCache = new Map();
            const MAX_CACHE = 40;
            let looping = false;
            let loopTimer = null;
            let loopFhrIndex = 0;
            // Blob URL prefetch cache for animation
            let frameBlobURLs = {};
            // Preloaded Image objects (decoded and ready to swap without flash)
            let frameImages = {};
            // Swap guard: prevent overlapping swaps from racing
            let _swapSeq = 0;
            let _swapBusy = false;
            // Debounce timer for slider-triggered updates
            let _updateDebounceTimer = null;

            // Double-buffer swap: load into back buffer, then instantly flip
            function swapOverlayImage(url) {
                const seq = ++_swapSeq;
                return new Promise((resolve) => {
                    // If another swap was queued after us, bail out
                    if (seq !== _swapSeq) { resolve(false); return; }

                    const active = map._weatherOverlayActiveLayer || 'a';
                    const back = active === 'a' ? 'b' : 'a';
                    const backSrc = map.getSource('weather-overlay-' + back);
                    if (!backSrc) { resolve(false); return; }

                    // Pre-decode image
                    const img = new Image();
                    img.onload = () => {
                        // Stale check: if a newer swap was requested, skip this one
                        if (seq !== _swapSeq) { resolve(false); return; }
                        // Load into back buffer
                        backSrc.updateImage({ url });
                        // Wait a frame for Mapbox to process the image update
                        requestAnimationFrame(() => {
                            if (seq !== _swapSeq) { resolve(false); return; }
                            const op = opacity !== undefined ? opacity : 0.7;
                            // Show back buffer at full opacity
                            map.setPaintProperty('weather-overlay-' + back, 'raster-opacity', op);
                            // Hide front buffer
                            map.setPaintProperty('weather-overlay-' + active, 'raster-opacity', 0);
                            map._weatherOverlayActiveLayer = back;
                            resolve(true);
                        });
                    };
                    img.onerror = () => resolve(false);
                    img.src = url;
                });
            }

            async function loadFieldsMeta() {
                try {
                    const r = await fetch('/api/v1/map-overlay/fields?model=' + (currentModel||'hrrr') + '&colormaps=true');
                    const d = await r.json();
                    fieldsMetadata = {};
                    d.fields.forEach(f => { fieldsMetadata[f.id] = f; });
                    if (d.colormaps) {
                        for (const [name, b64] of Object.entries(d.colormaps)) {
                            const raw = atob(b64);
                            const arr = new Uint8Array(raw.length);
                            for (let i = 0; i < raw.length; i++) arr[i] = raw.charCodeAt(i);
                            colormapLUTs[name] = arr;
                        }
                    }
                    populateFieldDropdown();
                    updateLevelVisibility();
                } catch (e) { console.error('Failed to load overlay fields:', e); }
            }

            async function loadProductsMeta() {
                try {
                    const r = await fetch('/api/v1/map-overlay/products');
                    const d = await r.json();
                    productsMetadata = {};
                    (d.products || []).forEach(p => { productsMetadata[p.id] = p; });
                } catch (e) { console.error('Failed to load overlay products:', e); }
            }

            function populateFieldDropdown() {
                const sel = document.getElementById('overlay-field-select');
                sel.innerHTML = '';
                const groups = {surface: 'Surface', derived: 'Derived', isobaric: 'Isobaric'};
                for (const [cat, label] of Object.entries(groups)) {
                    const grp = document.createElement('optgroup');
                    grp.label = label;
                    let hasItems = false;
                    for (const [fid, meta] of Object.entries(fieldsMetadata || {})) {
                        if (meta.category !== cat && !(cat === 'derived' && meta.category === 'derived')) continue;
                        const opt = document.createElement('option');
                        opt.value = fid;
                        opt.textContent = meta.name;
                        if (fid === currentField) opt.selected = true;
                        grp.appendChild(opt);
                        hasItems = true;
                    }
                    if (hasItems) sel.appendChild(grp);
                }
            }

            function cacheKey(fhr_override) {
                const fhr = fhr_override !== undefined ? fhr_override : (activeFhr || 0);
                if (currentProduct) {
                    return `prod_${currentProduct}_${currentModel||'hrrr'}_${currentCycle||'latest'}_${fhr}`;
                }
                const f = currentField;
                const meta = fieldsMetadata && fieldsMetadata[f];
                const lev = (meta && meta.needs_level) ? currentLevel : '';
                return `${currentModel||'hrrr'}_${currentCycle||'latest'}_${fhr}_${f}_${lev}`;
            }

            function addToCache(key, val) {
                if (dataCache.size >= MAX_CACHE) {
                    const oldest = dataCache.keys().next().value;
                    const old = dataCache.get(oldest);
                    if (old && old.blobUrl) URL.revokeObjectURL(old.blobUrl);
                    dataCache.delete(oldest);
                }
                dataCache.set(key, val);
            }

            function updateLevelVisibility() {
                const meta = fieldsMetadata && fieldsMetadata[currentField];
                const levelRow = document.getElementById('overlay-level-row');
                levelRow.style.display = (meta && meta.needs_level) ? 'flex' : 'none';
            }

            function updateCustomControlsVisibility() {
                const customCtrl = document.getElementById('overlay-custom-controls');
                customCtrl.style.display = currentProduct ? 'none' : 'block';
            }

            function updateColorbar(vmin, vmax, units, title, cmapName) {
                const bar = document.getElementById('overlay-colorbar');
                const canvas = document.getElementById('colorbar-canvas');
                const ctx = canvas.getContext('2d');
                const lut = colormapLUTs[cmapName];
                if (!lut) { bar.style.display = 'none'; return; }
                bar.style.display = 'block';
                document.getElementById('colorbar-title').textContent = title;
                document.getElementById('colorbar-min').textContent = vmin.toFixed(0);
                document.getElementById('colorbar-max').textContent = vmax.toFixed(0);
                document.getElementById('colorbar-units').textContent = units;
                const imgData = ctx.createImageData(200, 14);
                for (let x = 0; x < 200; x++) {
                    const idx = Math.round((x / 199) * 255);
                    const r = lut[idx * 4], g = lut[idx * 4 + 1], b = lut[idx * 4 + 2], a = lut[idx * 4 + 3];
                    for (let y = 0; y < 14; y++) {
                        const p = (y * 200 + x) * 4;
                        imgData.data[p] = r; imgData.data[p+1] = g;
                        imgData.data[p+2] = b; imgData.data[p+3] = a;
                    }
                }
                ctx.putImageData(imgData, 0, 0);
            }

            function updateProductColorbar() {
                if (!currentProduct || !productsMetadata) return;
                const pmeta = productsMetadata[currentProduct];
                if (!pmeta) return;
                const fillMeta = fieldsMetadata && fieldsMetadata[pmeta.fill_field];
                const cmapName = pmeta.fill_cmap || (fillMeta && fillMeta.default_cmap) || '';
                const vmin = pmeta.fill_vmin != null ? pmeta.fill_vmin : (fillMeta ? fillMeta.default_vmin : 0);
                const vmax = pmeta.fill_vmax != null ? pmeta.fill_vmax : (fillMeta ? fillMeta.default_vmax : 100);
                const units = fillMeta ? fillMeta.units : '';
                updateColorbar(vmin, vmax, units, pmeta.name, cmapName);
            }

            function buildOverlayURL(fhr) {
                const params = new URLSearchParams({
                    model: currentModel || 'hrrr',
                    cycle: currentCycle || 'latest',
                    fhr: fhr,
                });
                if (currentProduct) {
                    params.set('product', currentProduct);
                } else {
                    params.set('field', currentField);
                    const meta = fieldsMetadata && fieldsMetadata[currentField];
                    if (meta && meta.needs_level) params.set('level', currentLevel);
                }
                params.set('_v', '3');  // cache buster (v3 = webp)
                return '/api/v1/map-overlay/frame?' + params;
            }

            let _updateSeq = 0;

            async function update(fhr_override) {
                if (!enabled || !mapStyleLoaded) return;
                const mySeq = ++_updateSeq;
                const fhr = fhr_override !== undefined ? fhr_override : (activeFhr || 0);

                // Fast path: use prefetched blob URL (instant, no network)
                if (frameBlobURLs[fhr]) {
                    if (mySeq !== _updateSeq) return;  // stale
                    await swapOverlayImage(frameBlobURLs[fhr]);
                    if (currentProduct) updateProductColorbar();
                    else {
                        const meta = fieldsMetadata && fieldsMetadata[currentField];
                        if (meta) updateColorbar(meta.default_vmin, meta.default_vmax, meta.units || '', meta.name, meta.default_cmap);
                    }
                    // Proactively fetch grid data for hover values
                    if (typeof fetchOverlayGrid === 'function') fetchOverlayGrid(fhr);
                    return;
                }

                const key = cacheKey(fhr);
                let cached = dataCache.get(key);

                if (!cached) {
                    if (abortCtrl) abortCtrl.abort();
                    abortCtrl = new AbortController();
                    try {
                        const resp = await fetch(buildOverlayURL(fhr), {signal: abortCtrl.signal});
                        if (!resp.ok) return;
                        if (mySeq !== _updateSeq) return;  // stale — newer update in flight
                        const blob = await resp.blob();
                        const blobUrl = URL.createObjectURL(blob);
                        cached = { blobUrl };
                        addToCache(key, cached);
                        // Also store in prefetch cache for instant re-access
                        frameBlobURLs[fhr] = blobUrl;
                    } catch (e) {
                        if (e.name !== 'AbortError') console.error('Overlay fetch error:', e);
                        return;
                    }
                }

                if (mySeq !== _updateSeq) return;  // stale

                // Pre-decode image then swap (no flash)
                await swapOverlayImage(cached.blobUrl);

                // Update colorbar
                if (currentProduct) {
                    updateProductColorbar();
                } else {
                    const meta = fieldsMetadata && fieldsMetadata[currentField];
                    if (meta) {
                        updateColorbar(meta.default_vmin, meta.default_vmax, meta.units || '', meta.name, meta.default_cmap);
                    }
                }
            }

            // Debounced update for slider scrubbing — instant if prefetched, else waits for scrub to settle
            function updateDebounced(fhr) {
                // If frame is already prefetched, update immediately (no flash)
                if (frameBlobURLs[fhr]) {
                    if (_updateDebounceTimer) { clearTimeout(_updateDebounceTimer); _updateDebounceTimer = null; }
                    update(fhr);
                    return;
                }
                // Frame needs server fetch — debounce to avoid hammering
                if (_updateDebounceTimer) clearTimeout(_updateDebounceTimer);
                _updateDebounceTimer = setTimeout(() => {
                    _updateDebounceTimer = null;
                    update(fhr);
                }, 120);
            }

            function setEnabled(on) {
                enabled = on;
                document.getElementById('overlay-controls').style.display = on ? 'block' : 'none';
                if (on) {
                    if (!fieldsMetadata) {
                        Promise.all([loadFieldsMeta(), loadProductsMeta()]).then(() => {
                            updateCustomControlsVisibility();
                            if (mapStyleLoaded) {
                                map.setLayoutProperty('weather-overlay-a', 'visibility', 'visible');
                                map.setLayoutProperty('weather-overlay-b', 'visibility', 'visible');
                            }
                            update();
                            // Prefetch all FHR frames in background for instant slider
                            prefetchAllFrames(getLoadedFHRs());
                        });
                    } else {
                        updateCustomControlsVisibility();
                        if (mapStyleLoaded) {
                            map.setLayoutProperty('weather-overlay-a', 'visibility', 'visible');
                            map.setLayoutProperty('weather-overlay-b', 'visibility', 'visible');
                        }
                        update();
                        // Prefetch all FHR frames in background for instant slider
                        prefetchAllFrames(getLoadedFHRs());
                    }
                } else {
                    stopLoop();
                    if (mapStyleLoaded && map.getLayer('weather-overlay-a')) {
                        map.setLayoutProperty('weather-overlay-a', 'visibility', 'none');
                        map.setLayoutProperty('weather-overlay-b', 'visibility', 'none');
                    }
                    document.getElementById('overlay-colorbar').style.display = 'none';
                }
            }

            let _prefetchGeneration = 0;  // bump on product/field change to cancel stale prefetches

            async function setProduct(p) {
                currentProduct = p;
                _prefetchGeneration++;
                // Clear prefetched frames — product changed
                for (const url of Object.values(frameBlobURLs)) URL.revokeObjectURL(url);
                frameBlobURLs = {};
                if (typeof clearOverlayGridCache === 'function') clearOverlayGridCache();
                updateCustomControlsVisibility();
                // Immediately update colorbar for new product
                if (currentProduct) updateProductColorbar();
                // Fetch current frame first, THEN prefetch rest
                await update();
                if (enabled) prefetchAllFrames(getLoadedFHRs());
            }

            async function setField(f) {
                currentField = f;
                _prefetchGeneration++;
                for (const url of Object.values(frameBlobURLs)) URL.revokeObjectURL(url);
                frameBlobURLs = {};
                if (typeof clearOverlayGridCache === 'function') clearOverlayGridCache();
                updateLevelVisibility();
                await update();
                if (enabled) prefetchAllFrames(getLoadedFHRs());
            }
            async function setLevel(l) {
                currentLevel = parseInt(l);
                _prefetchGeneration++;
                for (const url of Object.values(frameBlobURLs)) URL.revokeObjectURL(url);
                frameBlobURLs = {};
                if (typeof clearOverlayGridCache === 'function') clearOverlayGridCache();
                await update();
                if (enabled) prefetchAllFrames(getLoadedFHRs());
            }
            function setOpacity(v) {
                opacity = v;
                // Mapbox raster-opacity is instant — no re-fetch needed
                const active = map._weatherOverlayActiveLayer || 'a';
                if (mapStyleLoaded && map.getLayer('weather-overlay-' + active)) {
                    map.setPaintProperty('weather-overlay-' + active, 'raster-opacity', v);
                }
            }
            function invalidateCache() {
                for (const [k, v] of dataCache) {
                    if (v && v.blobUrl) URL.revokeObjectURL(v.blobUrl);
                }
                dataCache.clear();
                // Clear animation blob URLs
                for (const url of Object.values(frameBlobURLs)) URL.revokeObjectURL(url);
                frameBlobURLs = {};
            }

            // --- Animation loop with prefetched blob URLs ---
            function getLoadedFHRs() {
                const chips = document.querySelectorAll('#fhr-chips .chip.loaded, #fhr-chips .chip.active');
                return Array.from(chips).map(c => parseInt(c.dataset.fhr || c.textContent)).filter(n => !isNaN(n));
            }

            async function prefetchAllFrames(fhrs) {
                const gen = _prefetchGeneration;
                // Fetch frames in batches of 6 — server cache hits are fast
                const BATCH = 6;
                for (let i = 0; i < fhrs.length; i += BATCH) {
                    if (_prefetchGeneration !== gen) return;  // product/field changed, stop stale prefetch
                    await Promise.all(fhrs.slice(i, i + BATCH).map(async fhr => {
                        if (frameBlobURLs[fhr]) return;
                        if (_prefetchGeneration !== gen) return;
                        try {
                            const resp = await fetch(buildOverlayURL(fhr));
                            if (!resp.ok || _prefetchGeneration !== gen) return;
                            const blob = await resp.blob();
                            if (_prefetchGeneration !== gen) return;
                            const blobUrl = URL.createObjectURL(blob);
                            frameBlobURLs[fhr] = blobUrl;
                            // Pre-decode into browser image cache for flash-free swap
                            const img = new Image();
                            img.src = blobUrl;
                        } catch (e) {}
                    }));
                }
            }

            function startLoop() {
                if (looping) return;
                looping = true;
                document.getElementById('overlay-loop').classList.add('active');
                const fhrs = getLoadedFHRs();
                if (fhrs.length < 2) { stopLoop(); return; }
                loopFhrIndex = fhrs.indexOf(activeFhr || 0);
                if (loopFhrIndex < 0) loopFhrIndex = 0;

                // Prefetch all frames as blob URLs for smooth animation
                prefetchAllFrames(fhrs);

                const speedSel = document.getElementById('gif-speed');
                const interval = speedSel ? parseInt(speedSel.value) || 250 : 250;

                loopTimer = setInterval(() => {
                    const loadedFhrs = getLoadedFHRs();
                    if (loadedFhrs.length < 2) { stopLoop(); return; }
                    loopFhrIndex = (loopFhrIndex + 1) % loadedFhrs.length;
                    const nextFhr = loadedFhrs[loopFhrIndex];

                    // Use prefetched blob URL if available, else fetch from cache/server
                    const blobUrl = frameBlobURLs[nextFhr];
                    if (blobUrl) {
                        swapOverlayImage(blobUrl);
                    } else {
                        update(nextFhr);
                    }

                    const titleEl = document.getElementById('colorbar-title');
                    if (titleEl) {
                        const base = currentProduct ? (productsMetadata && productsMetadata[currentProduct] ? productsMetadata[currentProduct].name : currentProduct) : (fieldsMetadata && fieldsMetadata[currentField] ? fieldsMetadata[currentField].name : '');
                        titleEl.textContent = base + ' (F' + String(nextFhr).padStart(2, '0') + ')';
                    }
                }, interval);
            }

            function stopLoop() {
                looping = false;
                if (loopTimer) { clearInterval(loopTimer); loopTimer = null; }
                document.getElementById('overlay-loop').classList.remove('active');
            }

            function toggleLoop() {
                if (looping) stopLoop();
                else startLoop();
            }

            return { setEnabled, setField, setLevel, setOpacity, setProduct, update,
                     updateDebounced, invalidateCache, loadFieldsMeta, toggleLoop,
                     _isEnabled: () => enabled,
                     _getProduct: () => currentProduct,
                     _getField: () => currentField,
                     _getLevel: () => currentLevel };
        })();
        _modelMapOverlayRef = modelMapOverlay;  // expose for readdCustomLayers

        // Wire up overlay UI controls
        document.getElementById('overlay-off').onclick = function() {
            this.classList.add('active');
            document.getElementById('overlay-on').classList.remove('active');
            modelMapOverlay.setEnabled(false);
        };
        document.getElementById('overlay-on').onclick = function() {
            this.classList.add('active');
            document.getElementById('overlay-off').classList.remove('active');
            modelMapOverlay.setEnabled(true);
        };
        document.getElementById('overlay-product-select').onchange = function() {
            modelMapOverlay.setProduct(this.value);
        };
        document.getElementById('overlay-field-select').onchange = function() {
            modelMapOverlay.setField(this.value);
        };
        document.getElementById('overlay-level-select').onchange = function() {
            modelMapOverlay.setLevel(this.value);
        };
        document.getElementById('overlay-opacity').oninput = function() {
            document.getElementById('overlay-opacity-val').textContent = this.value + '%';
            modelMapOverlay.setOpacity(parseInt(this.value) / 100);
        };
        document.getElementById('overlay-loop').onclick = function() {
            modelMapOverlay.toggleLoop();
        };

        // =========================================================================
        // Overlay data value readout — client-side grid lookup (instant, no server round-trip)
        // =========================================================================
        const _overlayTooltip = document.createElement('div');
        _overlayTooltip.id = 'overlay-tooltip';
        _overlayTooltip.style.cssText = 'position:fixed;z-index:999;pointer-events:none;display:none;background:rgba(15,23,42,0.92);color:#f4f4f4;font-family:system-ui;font-size:12px;padding:6px 10px;border-radius:6px;border:1px solid rgba(255,255,255,0.15);white-space:nowrap;backdrop-filter:blur(4px);box-shadow:0 2px 8px rgba(0,0,0,0.4);';
        document.body.appendChild(_overlayTooltip);

        // Grid data cache: binary uint16 grids for instant hover lookup
        // cacheKey -> { bounds, rows, cols, lat_step, lon_step, fields: [{name,units,vmin,vmax,data:Uint16Array}] }
        let _overlayGridCache = {};
        let _overlayGridLoading = {};
        const _NAN_SENTINEL = 65535;

        function _gridCacheKey(fhr) {
            const prod = modelMapOverlay._getProduct();
            return fhr + ':' + (prod || (modelMapOverlay._getField() + ':' + modelMapOverlay._getLevel()));
        }

        function fetchOverlayGrid(fhr) {
            const key = _gridCacheKey(fhr);
            if (_overlayGridCache[key]) return Promise.resolve(_overlayGridCache[key]);
            if (_overlayGridLoading[key]) return _overlayGridLoading[key];
            const params = new URLSearchParams({
                model: currentModel || 'hrrr',
                cycle: currentCycle || 'latest',
                fhr: fhr,
            });
            const prod = modelMapOverlay._getProduct();
            if (prod) params.set('product', prod);
            else {
                params.set('field', modelMapOverlay._getField());
                const lev = modelMapOverlay._getLevel();
                if (lev) params.set('level', lev);
            }
            const promise = fetch('/api/v1/map-overlay/grid-sample?' + params, {cache: 'no-store'})
                .then(r => { if (!r.ok) return null; return r.arrayBuffer(); })
                .then(buf => {
                    if (!buf) return null;
                    const view = new DataView(buf);
                    const headerLen = view.getUint32(0, true);
                    const headerStr = new TextDecoder().decode(new Uint8Array(buf, 4, headerLen));
                    const meta = JSON.parse(headerStr);
                    // Parse binary uint16 fields
                    let offset = 4 + headerLen;
                    const count = meta.rows * meta.cols;
                    for (const field of meta.fields) {
                        // Copy to aligned buffer for Uint16Array
                        const raw = new Uint8Array(buf, offset, count * 2);
                        const aligned = new ArrayBuffer(count * 2);
                        new Uint8Array(aligned).set(raw);
                        field.data = new Uint16Array(aligned);
                        offset += count * 2;
                    }
                    _overlayGridCache[key] = meta;
                    delete _overlayGridLoading[key];
                    return meta;
                })
                .catch(() => { delete _overlayGridLoading[key]; return null; });
            _overlayGridLoading[key] = promise;
            return promise;
        }

        function clearOverlayGridCache() { _overlayGridCache = {}; _overlayGridLoading = {}; }

        function lookupGridValues(gridData, lat, lng) {
            if (!gridData || !gridData.fields || gridData.fields.length === 0) return null;
            const rowF = (lat - gridData.bounds.lat_min) / gridData.lat_step;
            const colF = (lng - gridData.bounds.lon_min) / gridData.lon_step;
            if (rowF < 0 || rowF > gridData.rows - 1 || colF < 0 || colF > gridData.cols - 1) return null;
            const r0 = Math.floor(rowF), r1 = Math.min(r0 + 1, gridData.rows - 1);
            const c0 = Math.floor(colF), c1 = Math.min(c0 + 1, gridData.cols - 1);
            const dr = rowF - r0, dc = colF - c0;
            const cols = gridData.cols;
            const results = [];
            for (const field of gridData.fields) {
                const d = field.data;
                const v00 = d[r0*cols+c0], v01 = d[r0*cols+c1], v10 = d[r1*cols+c0], v11 = d[r1*cols+c1];
                if (v00 === _NAN_SENTINEL || v01 === _NAN_SENTINEL || v10 === _NAN_SENTINEL || v11 === _NAN_SENTINEL) continue;
                const interp = v00*(1-dr)*(1-dc) + v01*(1-dr)*dc + v10*dr*(1-dc) + v11*dr*dc;
                const val = field.vmin + (interp / 65534) * (field.vmax - field.vmin);
                results.push({ name: field.name, value: Math.round(val * 10) / 10, units: field.units });
            }
            return results.length > 0 ? results : null;
        }

        map.on('mousemove', (e) => {
            if (!modelMapOverlay._isEnabled()) { _overlayTooltip.style.display = 'none'; return; }
            const lat = e.lngLat.lat, lng = e.lngLat.lng;
            const fhr = activeFhr || 0;
            // Reposition tooltip immediately (always follows cursor)
            _overlayTooltip.style.left = (e.originalEvent.clientX + 16) + 'px';
            _overlayTooltip.style.top = (e.originalEvent.clientY - 10) + 'px';
            // Instant client-side grid lookup
            const key = _gridCacheKey(fhr);
            const gridData = _overlayGridCache[key];
            if (gridData) {
                const vals = lookupGridValues(gridData, lat, lng);
                if (vals) {
                    let html = '';
                    vals.forEach(v => { html += '<strong>' + v.value + ' ' + v.units + '</strong> <span style="color:#94a3b8;">' + v.name + '</span><br>'; });
                    _overlayTooltip.innerHTML = html;
                    _overlayTooltip.style.display = 'block';
                } else {
                    _overlayTooltip.style.display = 'none';
                }
            } else {
                // Grid not yet cached — fetch in background, show coords
                fetchOverlayGrid(fhr);
                _overlayTooltip.innerHTML = '<span style="color:#94a3b8;">' + lat.toFixed(2) + ', ' + lng.toFixed(2) + '</span>';
                _overlayTooltip.style.display = 'block';
            }
        });

        map.on('mouseout', () => { _overlayTooltip.style.display = 'none'; });

        // =========================================================================
        // Toast Notification System
        // =========================================================================
        function showToast(message, type = 'loading', duration = null) {
            const container = document.getElementById('toast-container');
            const toast = document.createElement('div');
            toast.className = `toast ${type}`;
            const icon = type === 'loading' ? '⏳' : (type === 'success' ? '✓' : '✗');
            toast.innerHTML = `<span>${icon} ${message}</span>`;
            container.appendChild(toast);

            if (duration || type !== 'loading') {
                setTimeout(() => toast.remove(), duration || 3000);
            }
            return toast;
        }

        function updateMemoryDisplay(memMb) {
            document.getElementById('mem-text').textContent = `${Math.round(memMb)} MB`;
            document.getElementById('mem-fill').style.width = `${Math.min(100, memMb / 500)}%`;
        }

        // =========================================================================
        // Style Selector
        // =========================================================================
        const styleSelect = document.getElementById('style-select');
        styles.forEach(([val, label]) => {
            const opt = document.createElement('option');
            opt.value = val;
            opt.textContent = label;
            styleSelect.appendChild(opt);
        });
        const tempCmapSelect = document.getElementById('temp-cmap-select');
        const tempCmapRow = document.getElementById('temp-cmap-row');
        function updateTempCmapVisibility() {
            if (tempCmapRow) tempCmapRow.style.display = styleSelect.value === 'temp' ? '' : 'none';
        }
        styleSelect.onchange = () => { updateTempCmapVisibility(); updateAnomalyVisibility(); generateCrossSection(); };
        tempCmapSelect.onchange = generateCrossSection;

        // =========================================================================
        // Anomaly Mode — disabled (kept for future use, always false)
        // =========================================================================
        let anomalyMode = false;
        let anomalyStyles = new Set();
        let climatologyAvailable = false;
        const anomalyGroup = document.getElementById('anomaly-group');
        const anomalyOffBtn = document.getElementById('anomaly-off');
        const anomalyOnBtn = document.getElementById('anomaly-on');

        // Handlers kept but anomaly group is permanently hidden
        anomalyOffBtn.onclick = () => {};
        anomalyOnBtn.onclick = () => {};

        function updateAnomalyVisibility() {
            // Anomaly mode disabled — always hidden
            anomalyGroup.style.display = 'none';
        }

        // Climatology fetch skipped — anomaly mode disabled

        // =========================================================================
        // Y-Axis Toggle (Pressure / Height)
        // =========================================================================
        let currentYAxis = 'pressure';
        const yaxisPressureBtn = document.getElementById('yaxis-pressure');
        const yaxisHeightBtn = document.getElementById('yaxis-height');
        const yaxisIsentropicBtn = document.getElementById('yaxis-isentropic');
        const yaxisBtns = [yaxisPressureBtn, yaxisHeightBtn, yaxisIsentropicBtn];

        function setYAxis(value) {
            if (currentYAxis !== value) {
                currentYAxis = value;
                yaxisBtns.forEach(b => b.classList.remove('active'));
                document.getElementById('yaxis-' + value).classList.add('active');
                generateCrossSection();
            }
        }
        yaxisPressureBtn.onclick = () => setYAxis('pressure');
        yaxisHeightBtn.onclick = () => setYAxis('height');
        yaxisIsentropicBtn.onclick = () => setYAxis('isentropic');

        // =========================================================================
        // Vertical Scale Selector
        // =========================================================================
        const vscaleSelect = document.getElementById('vscale-select');
        vscaleSelect.onchange = generateCrossSection;

        // =========================================================================
        // Y-Top (Vertical Range) Selector
        // =========================================================================
        const ytopSelect = document.getElementById('ytop-select');
        ytopSelect.onchange = generateCrossSection;

        // =========================================================================
        // Units (km/mi) Selector
        // =========================================================================
        const unitsSelect = document.getElementById('units-select');
        unitsSelect.onchange = generateCrossSection;

        // =========================================================================
        // Community Favorites
        // =========================================================================
        const favoritesSelect = document.getElementById('favorites-select');
        const saveFavoriteBtn = document.getElementById('save-favorite-btn');

        const CA_PRESETS = [
            { name: 'Sierra Crest', config: { start_lat: 37.0, start_lon: -121.0, end_lat: 37.0, end_lon: -118.0 }},
            { name: 'LA Basin \u2192 San Gabriels', config: { start_lat: 33.95, start_lon: -118.4, end_lat: 34.35, end_lon: -117.6 }},
            { name: 'Diablo Wind Corridor', config: { start_lat: 37.85, start_lon: -122.5, end_lat: 37.85, end_lon: -121.5 }},
            { name: 'Central Valley N\u2192S', config: { start_lat: 40.5, start_lon: -122.0, end_lat: 35.0, end_lon: -119.0 }},
            { name: 'SoCal Offshore Flow', config: { start_lat: 34.1, start_lon: -119.5, end_lat: 34.1, end_lon: -117.0 }},
        ];

        async function loadFavorites() {
            try {
                const res = await fetch('/api/favorites');
                const favorites = await res.json();
                favoritesSelect.innerHTML = '<option value="">Presets & Favorites</option>';
                // CA Presets group
                const presetGroup = document.createElement('optgroup');
                presetGroup.label = 'CA Presets';
                CA_PRESETS.forEach(p => {
                    const opt = document.createElement('option');
                    opt.value = JSON.stringify(p);
                    opt.textContent = p.name;
                    presetGroup.appendChild(opt);
                });
                favoritesSelect.appendChild(presetGroup);
                // User favorites group
                if (favorites.length > 0) {
                    const favGroup = document.createElement('optgroup');
                    favGroup.label = 'Saved (' + favorites.length + ')';
                    favorites.forEach(fav => {
                        const opt = document.createElement('option');
                        opt.value = JSON.stringify(fav);
                        opt.textContent = fav.name + (fav.label ? ' - ' + fav.label.substring(0, 30) : '');
                        opt.title = fav.label || fav.name;
                        favGroup.appendChild(opt);
                    });
                    favoritesSelect.appendChild(favGroup);
                }
            } catch (e) {
                console.error('Failed to load favorites:', e);
            }
        }

        favoritesSelect.onchange = function() {
            if (!this.value) return;
            try {
                const fav = JSON.parse(this.value);
                const cfg = fav.config;
                // Apply the favorite config
                if (cfg.start_lat && cfg.start_lon && cfg.end_lat && cfg.end_lon) {
                    clearXSMarkers();
                    startMarker = setupStartMarker(cfg.start_lat, cfg.start_lon);
                    endMarker = setupEndMarker(cfg.end_lat, cfg.end_lon);
                    updateLine();
                    fitBoundsLL([[cfg.start_lat, cfg.start_lon], [cfg.end_lat, cfg.end_lon]], 50);
                }
                if (cfg.style) document.getElementById('style-select').value = cfg.style;
                if (cfg.y_axis) {
                    currentYAxis = cfg.y_axis;
                    document.querySelectorAll('.toggle-btn').forEach(b => b.classList.remove('active'));
                    document.getElementById('yaxis-' + cfg.y_axis).classList.add('active');
                }
                if (cfg.vscale) document.getElementById('vscale-select').value = cfg.vscale;
                if (cfg.y_top) document.getElementById('ytop-select').value = cfg.y_top;
                this.value = '';  // Reset dropdown
                generateCrossSection();
                showToast('Loaded: ' + fav.name, 'success');
            } catch (e) {
                console.error('Failed to apply favorite:', e);
            }
        };

        saveFavoriteBtn.onclick = async function() {
            if (!startMarker || !endMarker) {
                showToast('Draw a cross-section first!', true);
                return;
            }
            const name = prompt('Name this favorite (e.g., "LA Basin East-West"):');
            if (!name) return;
            const label = prompt('Optional description (leave blank for none):') || '';

            const start = startMarker.getLatLng();
            const end = endMarker.getLatLng();
            const config = {
                start_lat: start.lat,
                start_lon: start.lng,
                end_lat: end.lat,
                end_lon: end.lng,
                style: document.getElementById('style-select').value,
                y_axis: currentYAxis,
                vscale: document.getElementById('vscale-select').value,
                y_top: document.getElementById('ytop-select').value
            };

            try {
                const res = await fetch('/api/favorite', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({name, label, config})
                });
                if (res.ok) {
                    showToast('Saved: ' + name);
                    loadFavorites();
                } else {
                    showToast('Failed to save', true);
                }
            } catch (e) {
                showToast('Error saving favorite', true);
            }
        };

        // Load favorites on startup
        loadFavorites();

        // =========================================================================
        // Request Custom Date/Cycle — Modal Dialog
        // =========================================================================
        document.getElementById('request-cycle-btn').onclick = function() {
            document.getElementById('run-request-modal').classList.add('visible');
            // Set date default to today
            const today = new Date().toISOString().slice(0, 10);
            document.getElementById('req-date').value = today;
            updateMaxFhr();
        };
        document.getElementById('req-cancel').onclick = function() {
            document.getElementById('run-request-modal').classList.remove('visible');
        };
        // Close on backdrop click
        document.getElementById('run-request-modal').addEventListener('click', function(e) {
            if (e.target === this) this.classList.remove('visible');
        });

        // Update max FHR when hour changes (HRRR synoptic = 48)
        function updateMaxFhr() {
            const hour = parseInt(document.getElementById('req-hour').value) || 0;
            const isSynoptic = [0, 6, 12, 18].includes(hour);
            const model = currentModel;
            let maxFhr = 18;
            if (model === 'hrrr' && isSynoptic) maxFhr = 48;
            else if (model === 'gfs') maxFhr = 384;
            const endInput = document.getElementById('req-fhr-end');
            endInput.max = maxFhr;
            if (parseInt(endInput.value) > maxFhr) endInput.value = maxFhr;
            document.getElementById('req-fhr-max-hint').textContent = `(max ${maxFhr})`;
        }
        document.getElementById('req-hour').addEventListener('change', updateMaxFhr);

        // Submit request
        document.getElementById('req-submit').onclick = async function() {
            const dateStr = document.getElementById('req-date').value.replace(/-/g, '');
            const hour = parseInt(document.getElementById('req-hour').value);
            const fhrStart = parseInt(document.getElementById('req-fhr-start').value);
            const fhrEnd = parseInt(document.getElementById('req-fhr-end').value);

            if (!dateStr || dateStr.length !== 8) { showToast('Invalid date', 'error'); return; }
            if (isNaN(hour)) { showToast('Select an init hour', 'error'); return; }
            if (fhrStart > fhrEnd) { showToast('Start FHR must be <= End FHR', 'error'); return; }

            document.getElementById('run-request-modal').classList.remove('visible');
            const label = `${dateStr}/${String(hour).padStart(2,'0')}z F${String(fhrStart).padStart(2,'0')}-F${String(fhrEnd).padStart(2,'0')}`;
            showToast(`Requesting ${label}...`, 'success', 3000);

            try {
                const res = await fetch(
                    `/api/request_cycle?date=${dateStr}&hour=${hour}&fhr_start=${fhrStart}&fhr_end=${fhrEnd}${modelParam()}`,
                    {method: 'POST'}
                );
                const data = await res.json();
                if (!data.success) {
                    showToast(data.error || 'Request failed', 'error');
                }
                // Progress is shown in the progress panel now — no need for separate polling
            } catch (e) {
                showToast('Request failed', 'error');
            }
        };

        // =========================================================================
        // Cycle (Model Run) Selector
        // =========================================================================
        const cycleSelect = document.getElementById('cycle-select');

        function buildCycleDropdown(cycleList, preserveSelection) {
            const savedCycle = preserveSelection ? currentCycle : null;
            cycleSelect.innerHTML = '';

            if (cycleList.length === 0) {
                const opt = document.createElement('option');
                opt.textContent = 'No data available';
                cycleSelect.appendChild(opt);
                return;
            }

            // Group by date
            const groups = {};
            cycleList.forEach(c => {
                const d = c.date || c.key.split('_')[0];
                if (!groups[d]) groups[d] = [];
                groups[d].push(c);
            });

            Object.keys(groups).sort().reverse().forEach(date => {
                const formatted = date.slice(0,4)+'-'+date.slice(4,6)+'-'+date.slice(6,8);
                const grp = document.createElement('optgroup');
                grp.label = formatted;
                groups[date].forEach(c => {
                    const opt = document.createElement('option');
                    opt.value = c.key;
                    const status = c.loaded ? '●' : '○';
                    opt.textContent = `${status} ${c.display} (${c.fhr_count} FHRs)`;
                    opt.dataset.fhrs = JSON.stringify(c.fhrs);
                    opt.dataset.loaded = c.loaded ? 'true' : 'false';
                    grp.appendChild(opt);
                });
                cycleSelect.appendChild(grp);
            });

            // Restore selection if it still exists
            if (savedCycle) {
                const exists = Array.from(cycleSelect.options).some(o => o.value === savedCycle);
                if (exists) {
                    cycleSelect.value = savedCycle;
                    return;
                }
            }

            // Otherwise select first
            if (cycleList.length > 0) {
                cycleSelect.value = cycleList[0].key;
                currentCycle = cycleList[0].key;
            }
        }

        async function loadCycles() {
            try {
                const res = await fetch(`/api/cycles?model=${currentModel}`);
                const data = await res.json();
                cycles = data.cycles || [];

                const hadSelection = !!currentCycle;
                buildCycleDropdown(cycles, hadSelection);

                if (cycles.length === 0) return;

                // Only auto-select latest if no prior selection was preserved
                // Also reset if the current cycle doesn't exist in this model's cycles
                const cycleExistsInModel = cycles.some(c => c.key === currentCycle);
                if (!hadSelection || !cycleExistsInModel) {
                    currentCycle = cycles[0].key;
                }

                // Check what's already loaded, then render chips
                await refreshLoadedStatus();

                // Update FHR chips for current cycle
                const curCycleData = cycles.find(c => c.key === currentCycle);
                if (curCycleData) {
                    renderFhrChips(curCycleData.fhrs);
                } else {
                    renderFhrChips(cycles[0].fhrs);
                }

                if (selectedFhrs.length > 0 && !activeFhr) {
                    activeFhr = selectedFhrs[0];
                    document.getElementById('active-fhr').textContent = `F${String(activeFhr).padStart(2,'0')}`;
                }
            } catch (err) {
                console.error('Failed to load cycles:', err);
            }
        }

        // Auto-refresh cycles every 60s to pick up newly downloaded forecast hours
        async function refreshCycleList() {
            try {
                const res = await fetch(`/api/cycles?model=${currentModel}`);
                const data = await res.json();
                const newCycles = data.cycles || [];
                if (!newCycles.length) return;

                // Check if anything changed at all
                const oldKeys = cycles.map(c => c.key + ':' + c.fhr_count).join(',');
                const newKeys = newCycles.map(c => c.key + ':' + c.fhr_count).join(',');
                if (oldKeys === newKeys) return;  // Nothing changed

                // Update FHR chips if current cycle got new forecast hours
                const currentInfo = newCycles.find(c => c.key === currentCycle);
                const oldInfo = cycles.find(c => c.key === currentCycle);
                if (currentInfo && oldInfo) {
                    const newFhrs = JSON.stringify(currentInfo.fhrs);
                    const oldFhrs = JSON.stringify(oldInfo.fhrs);
                    if (newFhrs !== oldFhrs) {
                        renderFhrChips(currentInfo.fhrs);
                    }
                }

                cycles = newCycles;
                buildCycleDropdown(cycles, true);  // Always preserve selection
                if (compareActive) populateCompareCycleDropdown();
            } catch (e) {
                // Silent fail for background refresh
            }
        }
        setInterval(() => { refreshCycleList(); refreshLoadedStatus(); }, 5000);

        // === Progress Panel ===
        const OP_ICONS = {
            preload: '\\u25B6',  // play triangle
            load: '\\u2191',     // up arrow
            autoload: '\\u25B6', // play triangle (same as preload)
            prerender: '\\u25CF',// filled circle
            download: '\\u2193', // down arrow
            autoupdate: '\\u21BB', // clockwise arrow ↻
        };

        function fmtTime(sec) {
            if (sec >= 3600) return `${Math.floor(sec/3600)}h ${Math.floor((sec%3600)/60)}m`;
            if (sec >= 60) return `${Math.floor(sec/60)}m ${sec%60}s`;
            return `${sec}s`;
        }

        // Collapse/expand toggle
        document.getElementById('progress-header').addEventListener('click', () => {
            document.getElementById('progress-panel').classList.toggle('collapsed');
        });

        async function pollProgress() {
            try {
                const res = await fetch('/api/progress');
                const data = await res.json();
                const panel = document.getElementById('progress-panel');
                const container = document.getElementById('progress-items');
                const footer = document.getElementById('progress-footer');
                const badge = document.getElementById('progress-badge');
                const entries = Object.entries(data);

                if (entries.length === 0) {
                    panel.classList.remove('visible');
                    return;
                }

                panel.classList.add('visible');
                container.innerHTML = '';

                let activeCount = 0;
                let allDone = true;

                for (const [opId, info] of entries) {
                    if (!info.done) { activeCount++; allDone = false; }

                    const item = document.createElement('div');
                    item.className = 'progress-item' + (info.done ? ' done' : '');
                    item.setAttribute('data-op', info.op || '');

                    const icon = OP_ICONS[info.op] || '\\u2022';  // bullet default
                    const timeStr = fmtTime(info.elapsed);

                    // ETA string
                    let etaStr = '';
                    if (info.eta && !info.done) {
                        etaStr = `<span class="eta">${fmtTime(info.eta)} left</span>`;
                    } else if (info.done) {
                        etaStr = `<span class="eta" style="color:var(--success)">done</span>`;
                    }

                    // Rate string
                    let rateStr = '';
                    if (info.rate && !info.done) {
                        rateStr = ` · ${info.rate.toFixed(1)}/s`;
                    }

                    // If detail is "Starting..." and elapsed > 10s, show converting hint
                    let detailText = info.detail;
                    if (detailText === 'Starting...' && info.elapsed > 10 && !info.done) {
                        detailText = 'Converting GRIB files to cache...';
                    }

                    // Cancel button for admins on active pre-render and download jobs
                    let cancelBtn = '';
                    if (!info.done && info.detail !== 'Cancelling...' && (info.op === 'prerender' || info.op === 'download')) {
                        cancelBtn = `<button class="cancel-op-btn" data-op="${opId}" title="Cancel">\u2715</button>`;
                    }

                    item.innerHTML = `
                        <div class="progress-item-header">
                            <span class="progress-label"><span class="op-icon">${icon}</span>${info.label}</span>
                            <span class="progress-stats">${info.step}/${info.total}${rateStr} · ${timeStr}${cancelBtn}</span>
                        </div>
                        <div class="progress-bar-bg">
                            <div class="progress-bar-fill" style="width:${info.pct}%"></div>
                        </div>
                        <div class="progress-detail"><span>${detailText}</span>${etaStr}</div>
                    `;
                    container.appendChild(item);
                }

                // Badge
                badge.textContent = activeCount > 0 ? activeCount : '\\u2713';
                badge.className = 'progress-badge' + (allDone ? ' done-badge' : '');

                // Mirror into sidebar activity tab
                const sidebarProgress = document.getElementById('activity-progress-items');
                if (sidebarProgress) {
                    sidebarProgress.innerHTML = container.innerHTML;
                }

                // Update activity tab badge
                const actBadge = document.getElementById('activity-badge');
                if (actBadge) {
                    if (activeCount > 0) {
                        actBadge.textContent = activeCount;
                        actBadge.style.display = '';
                    } else {
                        actBadge.style.display = 'none';
                    }
                }

                // Footer summary
                try {
                    const statusRes = await fetch(`/api/status?model=${currentModel}`);
                    const status = await statusRes.json();
                    const loadedCount = (status.loaded || []).length;
                    const memMb = Math.round(status.memory_mb || 0);
                    footer.innerHTML = `<span>${loadedCount} FHRs loaded</span><span>${memMb} MB</span>`;
                } catch(e) {
                    footer.innerHTML = '';
                }

                // Also update memory display from any active load
                refreshLoadedStatus();
            } catch (e) {
                // Silent fail
            }
        }
        setInterval(pollProgress, 1500);
        pollProgress();

        // Cancel button handler (delegated)
        document.getElementById('progress-items').addEventListener('click', async (e) => {
            const btn = e.target.closest('.cancel-op-btn');
            if (!btn) return;
            const opId = btn.dataset.op;
            btn.disabled = true;
            btn.textContent = '...';
            try {
                await fetch(`/api/cancel?op_id=${encodeURIComponent(opId)}`, {method: 'POST'});
            } catch(err) {
                console.error('Cancel failed:', err);
            }
        });

        cycleSelect.onchange = async () => {
            stopPlayback();
            invalidatePrerender();
            modelMapOverlay.invalidateCache();
            const selected = cycleSelect.options[cycleSelect.selectedIndex];
            currentCycle = selected.value;
            const fhrs = JSON.parse(selected.dataset.fhrs || '[]');
            const isLoaded = selected.dataset.loaded === 'true';

            if (!isLoaded) {
                // Need to load this cycle first
                const toast = showToast(`Loading cycle (this may take a minute)...`);
                try {
                    const res = await fetch(`/api/load_cycle?cycle=${currentCycle}${modelParam()}`, {method: 'POST'});
                    const data = await res.json();
                    toast.remove();

                    if (data.success) {
                        showToast(`Loaded ${data.loaded_fhrs} forecast hours`, 'success');
                        selected.textContent = selected.textContent.replace(' ⏳', '');
                        selected.dataset.loaded = 'true';
                        updateMemoryDisplay(data.memory_mb || 0);

                        // Refresh cycles list to update loaded status
                        const cyclesRes = await fetch(`/api/cycles?model=${currentModel}`);
                        const cyclesData = await cyclesRes.json();
                        cycles = cyclesData.cycles || [];
                    } else {
                        showToast(data.error || 'Failed to load cycle', 'error');
                        return;
                    }
                } catch (err) {
                    toast.remove();
                    showToast('Failed to load cycle', 'error');
                    return;
                }
            }

            // Update loaded state and render chips
            await refreshLoadedStatus();
            renderFhrChips(fhrs);

            // Auto-select first FHR
            if (selectedFhrs.length > 0) {
                activeFhr = selectedFhrs[0];
                document.getElementById('active-fhr').textContent = `F${String(activeFhr).padStart(2,'0')}`;
                updateChipStates();
                generateCrossSection();
                modelMapOverlay.update();
            }
        };

        // =========================================================================
        // Forecast Hour Chips (Redesigned: clear states, no accidental unloads)
        //
        // Visual states:
        //   - default (grey)  = downloaded on disk, not loaded to RAM
        //   - .loaded (green) = loaded in RAM, click for instant view
        //   - .active (blue)  = currently viewing this FHR
        //   - .loading (yellow pulse) = loading in progress
        //   - .unavailable (faded) = not downloaded yet
        //
        // Click behavior:
        //   - Click loaded/active chip = instant view switch (no load time)
        //   - Click unloaded chip = load to RAM (~15s), then view
        //   - Shift+click loaded chip = unload from RAM (deliberate only)
        // =========================================================================
        function renderFhrChips(availableFhrs) {
            const container = document.getElementById('fhr-chips');
            container.innerHTML = '';

            // Determine expected FHRs from current cycle metadata
            const cycleInfo = cycles.find(c => c.key === currentCycle);
            const maxFhr = (cycleInfo && cycleInfo.max_fhr) || 18;
            const isSynoptic = cycleInfo && cycleInfo.is_synoptic;
            const expectedFhrs = (cycleInfo && cycleInfo.expected_fhrs) || null;

            if (expectedFhrs) {
                // Use the model's actual FHR list (handles GFS every-6h, etc.)
                let addedDivider = false;
                for (const fhr of expectedFhrs) {
                    // Add divider before extended range (HRRR synoptic only)
                    if (!addedDivider && isSynoptic && fhr > 18) {
                        const divider = document.createElement('span');
                        divider.className = 'chip-divider';
                        divider.textContent = '|';
                        container.appendChild(divider);
                        addedDivider = true;
                    }
                    const chip = createFhrChip(fhr, availableFhrs);
                    if (fhr > 18 && isSynoptic) chip.classList.add('extended');
                    container.appendChild(chip);
                }
            } else {
                // Fallback: F00-F18 + extended F19-maxFhr for synoptic
                for (let fhr = 0; fhr <= Math.min(maxFhr, 18); fhr++) {
                    container.appendChild(createFhrChip(fhr, availableFhrs));
                }
                if (isSynoptic && maxFhr > 18) {
                    const divider = document.createElement('span');
                    divider.className = 'chip-divider';
                    divider.textContent = '|';
                    container.appendChild(divider);
                    for (let fhr = 19; fhr <= maxFhr; fhr++) {
                        const chip = createFhrChip(fhr, availableFhrs);
                        chip.classList.add('extended');
                        container.appendChild(chip);
                    }
                }
            }

            updateSliderVisibility();
        }

        function createFhrChip(fhr, availableFhrs) {
            const chip = document.createElement('div');
            chip.className = 'chip';
            chip.textContent = `F${String(fhr).padStart(2, '0')}`;
            chip.dataset.fhr = fhr;

            if (!availableFhrs.includes(fhr)) {
                chip.classList.add('unavailable');
                chip.title = 'Not downloaded yet';
            } else {
                // Set visual state based on loaded/active
                if (fhr === activeFhr) {
                    chip.classList.add('active');
                    chip.title = 'Currently viewing (Shift+click to unload)';
                } else if (selectedFhrs.includes(fhr)) {
                    chip.classList.add('loaded');
                    chip.title = 'Loaded in RAM — click for instant view (Shift+click to unload)';
                } else {
                    chip.title = 'Click to load (~15s)';
                }
                chip.onclick = (e) => handleChipClick(fhr, chip, e);
            }
            return chip;
        }

        // Unified click handler for all chips
        async function handleChipClick(fhr, chipEl, event) {
            if (chipEl.classList.contains('loading') || chipEl.classList.contains('unavailable')) {
                return;
            }

            const isLoaded = selectedFhrs.includes(fhr);

            // --- Shift+click = UNLOAD (deliberate action only) ---
            if (event.shiftKey && isLoaded) {
                chipEl.classList.add('loading');
                chipEl.classList.remove('loaded', 'active');
                const toast = showToast(`Unloading F${String(fhr).padStart(2,'0')}...`);

                try {
                    const res = await fetch(`/api/unload?cycle=${currentCycle}&fhr=${fhr}${modelParam()}`, {method: 'POST'});
                    const data = await res.json();

                    if (data.success) {
                        selectedFhrs = selectedFhrs.filter(f => f !== fhr);
                        toast.remove();
                        showToast(`Unloaded F${String(fhr).padStart(2,'0')}`, 'success');
                        updateMemoryDisplay(data.memory_mb || 0);

                        if (activeFhr === fhr) {
                            activeFhr = selectedFhrs.length > 0 ? selectedFhrs[selectedFhrs.length - 1] : null;
                            if (activeFhr !== null) {
                                document.getElementById('active-fhr').textContent = `F${String(activeFhr).padStart(2,'0')}`;
                                generateCrossSection();
                            } else {
                                document.getElementById('xsect-container').innerHTML =
                                    '<div id="instructions">Select a forecast hour to view</div>';
                                document.getElementById('active-fhr').textContent = '';
                            }
                        }
                    } else {
                        toast.remove();
                        showToast(data.error || 'Unload failed', 'error');
                    }
                } catch (err) {
                    toast.remove();
                    showToast('Unload failed', 'error');
                }
                chipEl.classList.remove('loading');
                updateChipStates();
                return;
            }

            // --- Normal click on loaded chip = INSTANT VIEW SWITCH ---
            if (isLoaded) {
                activeFhr = fhr;
                document.getElementById('active-fhr').textContent = `F${String(fhr).padStart(2,'0')}`;
                updateChipStates();
                generateCrossSection();
                return;
            }

            // --- Normal click on unloaded chip = LOAD then VIEW ---
            chipEl.classList.add('loading');
            const toast = showToast(`Loading F${String(fhr).padStart(2,'0')}... (~15s)`);

            try {
                const loadStart = Date.now();
                const res = await fetch(`/api/load?cycle=${currentCycle}&fhr=${fhr}${modelParam()}`, {method: 'POST'});
                const data = await res.json();
                const loadSec = ((Date.now() - loadStart) / 1000).toFixed(1);

                if (data.success) {
                    toast.remove();
                    const serverTime = data.load_time ? `${data.load_time}s` : `${loadSec}s`;
                    showToast(`Loaded F${String(fhr).padStart(2,'0')} in ${serverTime} (${Math.round(data.memory_mb || 0)} MB)`, 'success');

                    await refreshLoadedStatus();

                    activeFhr = fhr;
                    document.getElementById('active-fhr').textContent = `F${String(fhr).padStart(2,'0')}`;
                    generateCrossSection();
                } else {
                    toast.remove();
                    showToast(data.error || 'Load failed', 'error');
                }
            } catch (err) {
                toast.remove();
                showToast('Load failed', 'error');
            }
            chipEl.classList.remove('loading');
            updateChipStates();
        }

        // Update all chip visual states to match current data
        function updateChipStates() {
            document.querySelectorAll('#fhr-chips .chip').forEach(chip => {
                const fhr = parseInt(chip.dataset.fhr);
                if (chip.classList.contains('unavailable') || chip.classList.contains('loading')) return;

                chip.classList.remove('loaded', 'active');
                if (fhr === activeFhr) {
                    chip.classList.add('active');
                    chip.title = 'Currently viewing (Shift+click to unload)';
                } else if (selectedFhrs.includes(fhr)) {
                    chip.classList.add('loaded');
                    chip.title = 'Loaded in RAM — click for instant view (Shift+click to unload)';
                } else {
                    chip.title = 'Click to load (~15s)';
                }
            });
            updateSliderVisibility();
        }

        async function refreshLoadedStatus() {
            try {
                const res = await fetch(`/api/status?model=${currentModel}`);
                const data = await res.json();

                // Update selected FHRs based on what's actually loaded
                selectedFhrs = [];
                (data.loaded || []).forEach(item => {
                    if (item[0] === currentCycle) {
                        selectedFhrs.push(item[1]);
                    }
                });

                // Update chip UI with new state system
                updateChipStates();

                updateMemoryDisplay(data.memory_mb || 0);
            } catch (err) {
                console.error('Failed to refresh status:', err);
            }
        }

        // =========================================================================
        // Time Slider + Auto-Play
        // =========================================================================

        function updateSliderVisibility() {
            const sliderRow = document.getElementById('slider-row');
            if (selectedFhrs.length >= 2) {
                sliderRow.classList.add('visible');
                updateSliderRange();
            } else {
                sliderRow.classList.remove('visible');
                stopPlayback();
            }
        }

        function updateSliderRange() {
            const slider = document.getElementById('fhr-slider');
            const sorted = [...selectedFhrs].sort((a, b) => a - b);
            slider.min = 0;
            slider.max = sorted.length - 1;
            const idx = sorted.indexOf(activeFhr);
            slider.value = idx >= 0 ? idx : 0;
            slider.dataset.fhrMap = JSON.stringify(sorted);
            document.getElementById('slider-label').textContent = activeFhr != null ? `F${String(activeFhr).padStart(2, '0')}` : '';
        }

        document.getElementById('fhr-slider').addEventListener('input', function() {
            const fhrMap = JSON.parse(this.dataset.fhrMap || '[]');
            const fhr = fhrMap[parseInt(this.value)];
            if (fhr === undefined) return;

            document.getElementById('slider-label').textContent = `F${String(fhr).padStart(2, '0')}`;
            activeFhr = fhr;
            updateChipStates();

            // Use prerendered frame if available
            if (prerenderedFrames[fhr]) {
                const container = document.getElementById('xsect-container');
                let img = document.getElementById('xsect-img');
                if (!img) {
                    img = document.createElement('img');
                    img.id = 'xsect-img';
                    img.style.maxWidth = '100%';
                    container.innerHTML = '';
                    container.appendChild(img);
                }
                img.src = prerenderedFrames[fhr];
                document.getElementById('active-fhr').textContent = `F${String(fhr).padStart(2, '0')}`;
                if (compareActive) { updateCompareLabels(); generateComparisonSection(); }
            } else {
                generateCrossSection();
            }
            modelMapOverlay.updateDebounced(fhr);
        });

        document.getElementById('play-btn').addEventListener('click', () => {
            if (isPlaying) {
                stopPlayback();
            } else {
                startPlayback();
            }
        });

        function stepFrame(delta) {
            stopPlayback();
            const slider = document.getElementById('fhr-slider');
            let val = parseInt(slider.value) + delta;
            if (val < 0) val = parseInt(slider.max);
            if (val > parseInt(slider.max)) val = 0;
            slider.value = val;
            slider.dispatchEvent(new Event('input'));
        }

        document.getElementById('prev-btn').addEventListener('click', () => stepFrame(-1));
        document.getElementById('next-btn').addEventListener('click', () => stepFrame(1));

        function startPlayback() {
            isPlaying = true;
            document.getElementById('play-btn').innerHTML = '&#9646;&#9646;';
            const speed = parseInt(document.getElementById('play-speed').value);
            const slider = document.getElementById('fhr-slider');

            playInterval = setInterval(() => {
                let val = parseInt(slider.value) + 1;
                if (val > parseInt(slider.max)) val = 0;
                slider.value = val;
                slider.dispatchEvent(new Event('input'));
            }, speed);
        }

        function stopPlayback() {
            isPlaying = false;
            document.getElementById('play-btn').innerHTML = '&#9654;';
            if (playInterval) {
                clearInterval(playInterval);
                playInterval = null;
            }
        }

        function invalidatePrerender() {
            Object.values(prerenderedFrames).forEach(url => {
                if (url && url.startsWith('blob:')) URL.revokeObjectURL(url);
            });
            prerenderedFrames = {};
        }

        document.getElementById('prerender-btn').addEventListener('click', async () => {
            if (!startMarker || !endMarker || !currentCycle) return;

            const btn = document.getElementById('prerender-btn');
            btn.disabled = true;
            btn.textContent = 'Rendering...';

            const start = startMarker.getLatLng();
            const end = endMarker.getLatLng();
            const sorted = [...selectedFhrs].sort((a, b) => a - b);

            const body = {
                frames: sorted.map(fhr => ({cycle: currentCycle, fhr})),
                start: [start.lat, start.lng],
                end: [end.lat, end.lng],
                style: document.getElementById('style-select').value,
                y_axis: document.querySelector('#y-axis-toggle .toggle-btn.active')?.dataset?.value || 'pressure',
                vscale: parseFloat(document.getElementById('vscale-select').value),
                y_top: parseInt(document.getElementById('ytop-select').value),
                units: document.getElementById('units-select').value,
                temp_cmap: document.getElementById('temp-cmap-select')?.value || 'standard',
                anomaly: document.querySelector('#anomaly-toggle .toggle-btn.active')?.dataset?.value === 'anomaly',
                model: currentModel,
            };
            const _mkrs = buildMarkersBody();
            if (_mkrs) body.markers = _mkrs;

            try {
                const res = await fetch('/api/prerender', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(body),
                });
                const data = await res.json();
                const sessionId = data.session_id;

                // Poll progress until done
                const pollId = setInterval(async () => {
                    try {
                        const pRes = await fetch('/api/progress');
                        const progress = await pRes.json();
                        const session = progress[sessionId];

                        if (session) {
                            btn.textContent = `${session.pct}%`;
                        }

                        if (!session || session.done) {
                            clearInterval(pollId);
                            btn.disabled = false;
                            btn.textContent = 'Pre-render';

                            // Fetch all frames as blob URLs
                            const style = body.style;
                            const baseParams = `start_lat=${body.start[0]}&start_lon=${body.start[1]}&end_lat=${body.end[0]}&end_lon=${body.end[1]}&style=${style}&y_axis=${body.y_axis}&vscale=${body.vscale}&y_top=${body.y_top}&units=${body.units}&temp_cmap=${body.temp_cmap}&anomaly=${body.anomaly ? '1' : '0'}&model=${currentModel}`;

                            for (const fhr of sorted) {
                                try {
                                    const fRes = await fetch(`/api/frame?cycle=${currentCycle}&fhr=${fhr}&${baseParams}`);
                                    if (fRes.ok) {
                                        const blob = await fRes.blob();
                                        prerenderedFrames[fhr] = URL.createObjectURL(blob);
                                    }
                                } catch (e) { /* skip failed frames */ }
                            }
                            showToast(`${sorted.length} frames pre-rendered`, 'success');
                        }
                    } catch (e) {
                        clearInterval(pollId);
                        btn.disabled = false;
                        btn.textContent = 'Pre-render';
                    }
                }, 800);
            } catch (err) {
                btn.disabled = false;
                btn.textContent = 'Pre-render';
                showToast('Pre-render failed', 'error');
            }
        });

        // Invalidate prerendered frames when render params change
        ['style-select', 'vscale-select', 'ytop-select', 'units-select', 'temp-cmap-select'].forEach(id => {
            const el = document.getElementById(id);
            if (el) el.addEventListener('change', invalidatePrerender);
        });

        // =========================================================================
        // Cycle Comparison Mode
        // =========================================================================

        function toggleCompareMode() {
            compareActive = !compareActive;
            const btn = document.getElementById('compare-btn');
            const controls = document.getElementById('compare-controls');
            const panels = document.getElementById('xsect-panels');
            const panelCompare = document.getElementById('panel-compare');

            if (compareActive) {
                // Deactivate multi-panel mode if active
                if (multiPanelMode) {
                    multiPanelMode = '';
                    mpModeSelect.value = '';
                    mpControls.classList.remove('visible');
                    document.body.classList.remove('layout-multipanel');
                }
                btn.style.background = 'var(--accent)';
                btn.style.color = '#000';
                controls.classList.add('visible');
                panels.classList.add('compare-active');
                panelCompare.style.display = '';
                populateCompareCycleDropdown();
                updateCompareLabels();
            } else {
                btn.style.background = '';
                btn.style.color = '';
                controls.classList.remove('visible');
                panels.classList.remove('compare-active');
                panelCompare.style.display = 'none';
                compareCycle = null;
                document.getElementById('xsect-container-compare').innerHTML =
                    '<div style="color:var(--muted);">Select a comparison cycle</div>';
            }
        }

        document.getElementById('compare-btn').addEventListener('click', toggleCompareMode);

        function populateCompareCycleDropdown() {
            const sel = document.getElementById('compare-cycle-select');
            sel.innerHTML = '<option value="">-- Select cycle --</option>';
            cycles.forEach(c => {
                if (c.key === currentCycle) return;
                const opt = document.createElement('option');
                opt.value = c.key;
                opt.textContent = c.label || c.key;
                sel.appendChild(opt);
            });
            if (compareCycle) sel.value = compareCycle;
        }

        document.getElementById('compare-cycle-select').addEventListener('change', function() {
            compareCycle = this.value || null;
            updateCompareLabels();
            generateComparisonSection();
        });

        // Compare mode toggle (Same FHR vs Valid Time)
        document.querySelectorAll('#compare-mode-toggle .toggle-btn').forEach(btn => {
            btn.addEventListener('click', function() {
                document.querySelectorAll('#compare-mode-toggle .toggle-btn').forEach(b => b.classList.remove('active'));
                this.classList.add('active');
                compareMode = this.dataset.value;
                updateCompareLabels();
                generateComparisonSection();
            });
        });

        function getCompareFhr() {
            if (!compareCycle || activeFhr === null) return null;

            if (compareMode === 'same_fhr') {
                return activeFhr;
            }

            // Valid Time mode: find FHR in comparison cycle that matches same valid time
            const primaryInfo = cycles.find(c => c.key === currentCycle);
            const compareInfo = cycles.find(c => c.key === compareCycle);
            if (!primaryInfo || !compareInfo) return activeFhr;

            // Parse cycle init hours from keys like "20260205_18z"
            const parseCycleTime = (key) => {
                const m = key.match(/(\d{8})_(\d{2})z/);
                if (!m) return null;
                const yr = parseInt(m[1].substring(0, 4));
                const mo = parseInt(m[1].substring(4, 6)) - 1;
                const dy = parseInt(m[1].substring(6, 8));
                const hr = parseInt(m[2]);
                return new Date(Date.UTC(yr, mo, dy, hr));
            };

            const primaryInit = parseCycleTime(currentCycle);
            const compareInit = parseCycleTime(compareCycle);
            if (!primaryInit || !compareInit) return activeFhr;

            // Valid time = init + FHR hours
            const validTime = new Date(primaryInit.getTime() + activeFhr * 3600000);
            const neededFhr = Math.round((validTime - compareInit) / 3600000);

            if (neededFhr < 0 || neededFhr > (compareInfo.max_fhr || 48)) return null;
            return neededFhr;
        }

        function updateCompareLabels() {
            const primaryLabel = document.getElementById('panel-primary-label');
            const compareLabel = document.getElementById('panel-compare-label');
            const fhrLabel = document.getElementById('compare-fhr-label');

            if (!compareActive) return;

            const primaryInfo = cycles.find(c => c.key === currentCycle);
            primaryLabel.textContent = (primaryInfo ? primaryInfo.label || currentCycle : currentCycle || '') +
                (activeFhr !== null ? ` F${String(activeFhr).padStart(2, '0')}` : '');

            if (compareCycle) {
                const cFhr = getCompareFhr();
                const compareInfo = cycles.find(c => c.key === compareCycle);
                const cLabel = compareInfo ? compareInfo.label || compareCycle : compareCycle;
                compareLabel.textContent = cLabel + (cFhr !== null ? ` F${String(cFhr).padStart(2, '0')}` : '');

                if (compareMode === 'valid_time' && cFhr !== null && activeFhr !== null) {
                    const primaryInit = parseCycleKey(currentCycle);
                    if (primaryInit) {
                        const vt = new Date(primaryInit.getTime() + activeFhr * 3600000);
                        fhrLabel.textContent = `Valid: ${vt.getUTCHours().toString().padStart(2,'0')}z`;
                    }
                } else {
                    fhrLabel.textContent = '';
                }
            } else {
                compareLabel.textContent = 'No cycle selected';
                fhrLabel.textContent = '';
            }
        }

        function parseCycleKey(key) {
            const m = key.match(/(\d{8})_(\d{2})z/);
            if (!m) return null;
            const yr = parseInt(m[1].substring(0, 4));
            const mo = parseInt(m[1].substring(4, 6)) - 1;
            const dy = parseInt(m[1].substring(6, 8));
            const hr = parseInt(m[2]);
            return new Date(Date.UTC(yr, mo, dy, hr));
        }

        async function generateComparisonSection() {
            if (!compareActive || !compareCycle || !startMarker || !endMarker) return;

            const container = document.getElementById('xsect-container-compare');
            const cFhr = getCompareFhr();

            if (cFhr === null) {
                container.innerHTML = '<div style="color:var(--muted);">FHR not available in comparison cycle</div>';
                return;
            }

            container.innerHTML = '<div class="loading-text">Generating...</div>';

            const start = startMarker.getLatLng();
            const end = endMarker.getLatLng();
            const style = document.getElementById('style-select').value;
            const vscale = document.getElementById('vscale-select').value;
            const ytop = document.getElementById('ytop-select').value;
            const units = document.getElementById('units-select').value;
            const tempCmap = document.getElementById('temp-cmap-select').value;

            // Use /api/frame for comparison (benefits from prerender cache)
            const url = `/api/frame?start_lat=${start.lat}&start_lon=${start.lng}` +
                `&end_lat=${end.lat}&end_lon=${end.lng}&cycle=${compareCycle}&fhr=${cFhr}&style=${style}` +
                `&y_axis=${currentYAxis}&vscale=${vscale}&y_top=${ytop}&units=${units}&temp_cmap=${tempCmap}` +
                `&anomaly=${anomalyMode ? 1 : 0}&model=${currentModel}`;

            try {
                const res = await fetch(url);
                if (!res.ok) throw new Error('Failed to generate comparison');
                const blob = await res.blob();
                // Revoke previous blob URL
                const oldImg = container.querySelector('img');
                if (oldImg && oldImg.src && oldImg.src.startsWith('blob:')) URL.revokeObjectURL(oldImg.src);
                const img = document.createElement('img');
                img.src = URL.createObjectURL(blob);
                container.innerHTML = '';
                container.appendChild(img);
            } catch (err) {
                container.innerHTML = `<div style="color:#f87171">${err.message}</div>`;
            }
        }

        // =========================================================================
        // Multi-Panel Comparison Mode
        // =========================================================================
        let multiPanelMode = '';  // '', 'model', 'temporal', 'product', 'cycle'
        let multiPanelCycleMatch = 'same_fhr';

        const mpModeSelect = document.getElementById('multi-panel-mode');
        const mpControls = document.getElementById('multi-panel-controls');
        const mpStatus = document.getElementById('mp-status');
        const mpModeSections = {
            model: document.getElementById('mp-model-controls'),
            temporal: document.getElementById('mp-temporal-controls'),
            product: document.getElementById('mp-product-controls'),
            cycle: document.getElementById('mp-cycle-controls'),
        };

        function initMultiPanelModelChips() {
            const container = document.getElementById('mp-model-checkboxes');
            container.innerHTML = '';
            const modelSelect = document.getElementById('model-select');
            Array.from(modelSelect.options).forEach(opt => {
                const chip = document.createElement('span');
                chip.className = 'mp-chip';
                chip.dataset.value = opt.value;
                chip.textContent = opt.textContent;
                // Pre-select the current model
                if (opt.value === currentModel) chip.classList.add('selected');
                chip.onclick = () => {
                    chip.classList.toggle('selected');
                    const selected = container.querySelectorAll('.selected');
                    if (selected.length >= 2) generateMultiPanel();
                };
                container.appendChild(chip);
            });
        }

        function initMultiPanelProductChips() {
            const container = document.getElementById('mp-product-checkboxes');
            container.innerHTML = '';
            const excluded = modelExcludedStyles[currentModel] || new Set();
            styles.forEach(([val, label]) => {
                if (excluded.has(val)) return;
                const chip = document.createElement('span');
                chip.className = 'mp-chip';
                chip.dataset.value = val;
                chip.textContent = label;
                // Pre-select the current style
                const curStyle = document.getElementById('style-select').value;
                if (val === curStyle) chip.classList.add('selected');
                chip.onclick = () => {
                    chip.classList.toggle('selected');
                    const selected = container.querySelectorAll('.selected');
                    if (selected.length >= 2) generateMultiPanel();
                };
                container.appendChild(chip);
            });
        }

        function initMultiPanelCycleDropdown() {
            const sel = document.getElementById('mp-cycle-select');
            sel.innerHTML = '<option value="">-- Select cycle --</option>';
            cycles.forEach(c => {
                if (c.key === currentCycle) return;
                const opt = document.createElement('option');
                opt.value = c.key;
                opt.textContent = c.label || c.key;
                sel.appendChild(opt);
            });
        }

        mpModeSelect.addEventListener('change', function() {
            const mode = this.value;
            multiPanelMode = mode;

            // Hide all mode sections
            Object.values(mpModeSections).forEach(el => el.style.display = 'none');
            mpStatus.style.display = 'none';

            if (!mode) {
                mpControls.classList.remove('visible');
                document.body.classList.remove('layout-multipanel');
                // Regenerate single-panel cross-section
                generateCrossSection();
                return;
            }

            // Deactivate old compare mode when entering multi-panel
            if (compareActive) toggleCompareMode();

            mpControls.classList.add('visible');
            document.body.classList.add('layout-multipanel');

            // Show the relevant mode section
            if (mpModeSections[mode]) {
                mpModeSections[mode].style.display = '';
            }

            // Initialize mode-specific controls
            if (mode === 'model') {
                initMultiPanelModelChips();
            } else if (mode === 'product') {
                initMultiPanelProductChips();
            } else if (mode === 'cycle') {
                initMultiPanelCycleDropdown();
            }
        });

        // Temporal mode: go button
        document.getElementById('mp-temporal-go').addEventListener('click', () => {
            if (multiPanelMode === 'temporal') generateMultiPanel();
        });
        document.getElementById('mp-fhrs-input').addEventListener('keydown', e => {
            if (e.key === 'Enter' && multiPanelMode === 'temporal') generateMultiPanel();
        });

        // Cycle mode: go button and match toggle
        document.getElementById('mp-cycle-go').addEventListener('click', () => {
            if (multiPanelMode === 'cycle') generateMultiPanel();
        });
        document.getElementById('mp-cycle-select').addEventListener('change', () => {
            if (multiPanelMode === 'cycle') generateMultiPanel();
        });
        document.querySelectorAll('#mp-cycle-match-toggle .toggle-btn').forEach(btn => {
            btn.addEventListener('click', function() {
                document.querySelectorAll('#mp-cycle-match-toggle .toggle-btn').forEach(b => b.classList.remove('active'));
                this.classList.add('active');
                multiPanelCycleMatch = this.dataset.value;
                if (multiPanelMode === 'cycle') generateMultiPanel();
            });
        });

        async function generateMultiPanel() {
            if (!startMarker || !endMarker || !multiPanelMode) return;
            if (activeFhr === null) return;

            const start = startMarker.getLatLng();
            const end = endMarker.getLatLng();
            const style = document.getElementById('style-select').value;
            const vscale = document.getElementById('vscale-select').value;
            const ytop = document.getElementById('ytop-select').value;
            const units = document.getElementById('units-select').value;
            const tempCmap = document.getElementById('temp-cmap-select').value;

            const mpPoiParams = buildMarkersParam();
            let params = `mode=${multiPanelMode}` +
                `&start_lat=${start.lat}&start_lon=${start.lng}` +
                `&end_lat=${end.lat}&end_lon=${end.lng}` +
                `&cycle=${currentCycle}&fhr=${activeFhr}` +
                `&product=${style}&model=${currentModel}` +
                `&y_axis=${currentYAxis}&y_top=${ytop}&units=${units}` +
                `&temp_cmap=${tempCmap}${mpPoiParams}`;

            // Mode-specific params
            if (multiPanelMode === 'model') {
                const chips = document.querySelectorAll('#mp-model-checkboxes .mp-chip.selected');
                const models = Array.from(chips).map(c => c.dataset.value);
                if (models.length < 2) {
                    mpStatus.textContent = 'Select at least 2 models';
                    mpStatus.style.display = '';
                    return;
                }
                params += `&models=${models.join(',')}`;
            } else if (multiPanelMode === 'temporal') {
                const fhrsStr = document.getElementById('mp-fhrs-input').value.trim();
                if (!fhrsStr) {
                    mpStatus.textContent = 'Enter comma-separated FHRs';
                    mpStatus.style.display = '';
                    return;
                }
                params += `&fhrs=${fhrsStr}`;
            } else if (multiPanelMode === 'product') {
                const chips = document.querySelectorAll('#mp-product-checkboxes .mp-chip.selected');
                const products = Array.from(chips).map(c => c.dataset.value);
                if (products.length < 2) {
                    mpStatus.textContent = 'Select at least 2 products';
                    mpStatus.style.display = '';
                    return;
                }
                params += `&products=${products.join(',')}`;
            } else if (multiPanelMode === 'cycle') {
                const mpCycle = document.getElementById('mp-cycle-select').value;
                if (!mpCycle) {
                    mpStatus.textContent = 'Select a comparison cycle';
                    mpStatus.style.display = '';
                    return;
                }
                params += `&cycles=${currentCycle},${mpCycle}&cycle_match=${multiPanelCycleMatch}`;
            }

            // Show loading
            const container = document.getElementById('xsect-container');
            container.innerHTML = '<div class="loading-text">Generating multi-panel...</div>';
            mpStatus.textContent = 'Rendering...';
            mpStatus.style.display = '';

            // Hide the compare panel (we use the primary panel for multi-panel output)
            document.getElementById('panel-compare').style.display = 'none';
            document.getElementById('xsect-panels').classList.remove('compare-active');

            try {
                const url = `/api/v1/comparison?${params}`;
                const res = await fetch(url);
                if (!res.ok) {
                    const errText = await res.text();
                    throw new Error(errText || 'Failed to generate comparison');
                }
                const blob = await res.blob();
                const oldImg = container.querySelector('img');
                if (oldImg && oldImg.src && oldImg.src.startsWith('blob:')) URL.revokeObjectURL(oldImg.src);
                const img = document.createElement('img');
                img.id = 'xsect-img';
                img.src = URL.createObjectURL(blob);
                container.innerHTML = '';
                container.appendChild(img);
                mpStatus.textContent = 'Done';
                setTimeout(() => { if (mpStatus.textContent === 'Done') mpStatus.style.display = 'none'; }, 2000);
            } catch (err) {
                container.innerHTML = `<div style="color:#f87171">${err.message}</div>`;
                mpStatus.textContent = 'Error';
            }
        }

        // =========================================================================
        // Map Interaction
        // =========================================================================
        map.on('click', e => {
            // Don't create XS markers when clicking on city/event/cluster features
            const features = map.queryRenderedFeatures(e.point, {
                layers: ['city-points', 'city-clusters', 'event-points'].filter(id => map.getLayer(id))
            });
            if (features.length > 0) return;

            const lat = e.lngLat.lat;
            const lng = e.lngLat.lng;

            if (!startMarker) {
                startMarker = setupStartMarker(lat, lng);
            } else if (!endMarker) {
                endMarker = setupEndMarker(lat, lng);
                updateLine();
                generateCrossSection();
            }
        });

        // POI markers (multiple, right-click or + POI button)
        const poiMarkerSize = isMobile ? 20 : 14;
        let poiPlaceMode = false;

        function buildMarkersParam() {
            if (poiMarkers.length === 0) return '';
            const arr = poiMarkers.map(p => {
                const ll = p.marker.getLngLat();
                return { lat: ll.lat, lon: ll.lng, label: p.label || '' };
            });
            return '&markers=' + encodeURIComponent(JSON.stringify(arr));
        }
        function buildMarkersBody() {
            if (poiMarkers.length === 0) return null;
            return poiMarkers.map(p => {
                const ll = p.marker.getLngLat();
                return { lat: ll.lat, lon: ll.lng, label: p.label || '' };
            });
        }
        function poiPopupHtml(poi) {
            const safeLabel = (poi.label || '').replace(/"/g, '&quot;');
            const idx = poiMarkers.indexOf(poi);
            return '<div style="min-width:150px;background:#1e293b;color:#f4f4f4;">' +
                '<input class="poi-label-input" data-poi-idx="' + idx + '" type="text" value="' + safeLabel + '" placeholder="Label (e.g. Camp Fire)" style="width:100%;box-sizing:border-box;padding:3px 6px;border:1px solid #475569;border-radius:4px;font-size:12px;background:#334155;color:#f4f4f4;">' +
                '<div style="display:flex;justify-content:space-between;align-items:center;margin-top:4px">' +
                '<span style="font-size:10px;color:#94a3b8">Enter to apply</span>' +
                '<button class="poi-remove-btn" data-poi-idx="' + idx + '" style="font-size:10px;color:#f87171;background:none;border:1px solid #f87171;border-radius:3px;padding:1px 6px;cursor:pointer">Remove</button>' +
                '</div></div>';
        }
        function bindPoiPopup(poi) {
            const idx = poiMarkers.indexOf(poi);
            // Create a Mapbox popup and attach to marker
            if (poi._popup) poi._popup.remove();
            const popup = new mapboxgl.Popup({ closeButton: true, offset: 12, className: 'poi-popup' })
                .setHTML(poiPopupHtml(poi));
            poi._popup = popup;
            poi.marker.setPopup(popup);
            popup.on('open', () => {
                setTimeout(() => {
                    const inp = document.querySelector('.poi-label-input[data-poi-idx="' + idx + '"]');
                    const rmBtn = document.querySelector('.poi-remove-btn[data-poi-idx="' + idx + '"]');
                    if (inp) {
                        inp.focus();
                        inp.addEventListener('keydown', ev => {
                            if (ev.key === 'Enter') {
                                poi.label = inp.value.trim();
                                popup.remove();
                                invalidatePrerender();
                                generateCrossSection();
                            }
                        });
                        inp.addEventListener('blur', () => {
                            const newVal = inp.value.trim();
                            if (newVal !== poi.label) {
                                poi.label = newVal;
                                invalidatePrerender();
                                generateCrossSection();
                            }
                        });
                    }
                    if (rmBtn) {
                        rmBtn.addEventListener('click', () => { removePoi(poi); });
                    }
                }, 50);
            });
        }
        function removePoi(poi) {
            if (poi._popup) poi._popup.remove();
            poi.marker.remove();
            poiMarkers = poiMarkers.filter(p => p !== poi);
            poiMarkers.forEach(p => bindPoiPopup(p));
            invalidatePrerender();
            generateCrossSection();
            updatePoiBtn();
        }
        function addPoi(lat, lng, label) {
            const el = document.createElement('div');
            el.style.cssText = 'width:' + poiMarkerSize + 'px;height:' + poiMarkerSize + 'px;background:#10b981;border-radius:50%;border:2px solid white;box-shadow:0 1px 4px rgba(0,0,0,0.3);cursor:grab;';
            const m = new mapboxgl.Marker({ element: el, draggable: true })
                .setLngLat([lng, lat])
                .addTo(map);
            m.getLatLng = () => { const ll = m.getLngLat(); return { lat: ll.lat, lng: ll.lng }; };
            const poi = { marker: m, label: label || '' };
            poiMarkers.push(poi);
            bindPoiPopup(poi);
            m.on('dragend', () => { invalidatePrerender(); generateCrossSection(); });
            if (!label) {
                invalidatePrerender();
                generateCrossSection();
                if (poi._popup) poi._popup.addTo(map);
            }
            updatePoiBtn();
        }
        function updatePoiBtn() {
            const btn = document.getElementById('poi-btn');
            if (poiPlaceMode) {
                btn.style.background = '#10b981';
                btn.style.color = '#fff';
            } else {
                btn.style.background = '';
                btn.style.color = '';
            }
        }
        // Right-click to place POI (desktop)
        map.on('contextmenu', e => {
            e.preventDefault();
            addPoi(e.lngLat.lat, e.lngLat.lng);
        });
        // + POI button (mobile-friendly tap mode)
        document.getElementById('poi-btn').onclick = () => {
            poiPlaceMode = !poiPlaceMode;
            updatePoiBtn();
        };
        // Intercept map clicks when in POI place mode
        map.on('click', e => {
            if (!poiPlaceMode) return;
            if (!startMarker || !endMarker) return;
            addPoi(e.lngLat.lat, e.lngLat.lng);
        });

        // =========================================================================
        // Live Drag Rendering — debounced cross-section while dragging A/B
        // =========================================================================
        let _liveDragTimer = null;
        let _liveDragAbort = null;
        const LIVE_DRAG_DEBOUNCE_MS = 200;

        function liveDragRender() {
            if (_liveDragTimer) clearTimeout(_liveDragTimer);
            _liveDragTimer = setTimeout(() => {
                if (!startMarker || !endMarker || activeFhr === null) return;
                if (_liveDragAbort) _liveDragAbort.abort();
                _liveDragAbort = new AbortController();
                const s = startMarker.getLatLng(), e = endMarker.getLatLng();
                const style = (document.getElementById('style-select') || {}).value || 'temperature';
                const vscale = (document.getElementById('vscale-select') || {}).value || '1.0';
                const ytop = (document.getElementById('ytop-select') || {}).value || '100';
                const units = (document.getElementById('units-select') || {}).value || 'km';
                const tempCmap = (document.getElementById('temp-cmap-select') || {}).value || 'standard';
                const url = `/api/xsect?start_lat=${s.lat}&start_lon=${s.lng}` +
                    `&end_lat=${e.lat}&end_lon=${e.lng}&cycle=${currentCycle}&fhr=${activeFhr}&style=${style}` +
                    `&y_axis=${currentYAxis}&vscale=${vscale}&y_top=${ytop}&units=${units}&temp_cmap=${tempCmap}` +
                    `&anomaly=${anomalyMode ? 1 : 0}${modelParam()}`;
                fetch(url, {signal: _liveDragAbort.signal})
                    .then(r => { if (!r.ok) throw new Error(r.status); return r.blob(); })
                    .then(blob => {
                        const imgUrl = URL.createObjectURL(blob);
                        const container = document.getElementById('xsect-container');
                        let img = document.getElementById('xsect-img');
                        if (!img) {
                            img = document.createElement('img');
                            img.id = 'xsect-img';
                            img.style.maxWidth = '100%';
                            container.innerHTML = '';
                            container.appendChild(img);
                        }
                        const old = img._blobUrl;
                        img._blobUrl = imgUrl;
                        img.src = imgUrl;
                        if (old) URL.revokeObjectURL(old);
                    })
                    .catch(e => { if (e.name !== 'AbortError') console.warn('Live drag:', e); });
            }, LIVE_DRAG_DEBOUNCE_MS);
        }

        // =========================================================================
        // Cross-Section Generation
        // =========================================================================
        async function generateCrossSection() {
            hideShowcaseNotes();
            if (!startMarker || !endMarker) return;
            if (activeFhr === null) {
                document.getElementById('xsect-container').innerHTML =
                    '<div id="instructions">Select a forecast hour chip to load data first</div>';
                return;
            }

            // If multi-panel mode is active, generate multi-panel instead
            if (multiPanelMode) {
                generateMultiPanel();
                return;
            }

            // Cancel any in-flight request
            if (xsectAbortController) xsectAbortController.abort();
            xsectAbortController = new AbortController();

            const container = document.getElementById('xsect-container');
            container.innerHTML = '<div class="loading-text">Generating cross-section...</div>';

            const start = startMarker.getLatLng();
            const end = endMarker.getLatLng();
            const style = document.getElementById('style-select').value;
            const vscale = document.getElementById('vscale-select').value;
            const ytop = document.getElementById('ytop-select').value;

            const units = document.getElementById('units-select').value;

            const tempCmap = document.getElementById('temp-cmap-select').value;
            const poiParams = buildMarkersParam();
            const url = `/api/xsect?start_lat=${start.lat}&start_lon=${start.lng}` +
                `&end_lat=${end.lat}&end_lon=${end.lng}&cycle=${currentCycle}&fhr=${activeFhr}&style=${style}` +
                `&y_axis=${currentYAxis}&vscale=${vscale}&y_top=${ytop}&units=${units}&temp_cmap=${tempCmap}` +
                `&anomaly=${anomalyMode ? 1 : 0}${modelParam()}${poiParams}`;

            try {
                const res = await fetch(url, { signal: xsectAbortController.signal });
                if (!res.ok) throw new Error('Failed to generate');
                const blob = await res.blob();
                const oldImg = document.getElementById('xsect-img');
                if (oldImg && oldImg.src && oldImg.src.startsWith('blob:')) URL.revokeObjectURL(oldImg.src);
                const img = document.createElement('img');
                img.id = 'xsect-img';
                img.src = URL.createObjectURL(blob);
                container.innerHTML = '';
                container.appendChild(img);
                // Auto-open bottom panel when cross-section generated
                if (bottomState === 'collapsed') setBottomState('half');
            } catch (err) {
                if (err.name === 'AbortError') return;
                container.innerHTML = `<div style="color:#f87171">${err.message}</div>`;
            }

            if (compareActive) {
                updateCompareLabels();
                generateComparisonSection();
            }
        }

        // Clear button
        document.getElementById('clear-btn').onclick = () => {
            clearXSMarkers();
            poiMarkers.forEach(p => p.marker.remove());
            poiMarkers = [];
            poiPlaceMode = false;
            updatePoiBtn();
            document.getElementById('xsect-container').innerHTML =
                '<div id="instructions">Click two points on the map to draw a cross-section line</div>';
            if (compareActive) {
                document.getElementById('xsect-container-compare').innerHTML =
                    '<div style="color:var(--muted);">Draw a line to compare</div>';
            }
        };

        // GIF button
        document.getElementById('gif-btn').onclick = async () => {
            if (!startMarker || !endMarker || !currentCycle) return;
            const btn = document.getElementById('gif-btn');
            btn.disabled = true;
            btn.textContent = 'GIF...';
            const start = startMarker.getLatLng();
            const end = endMarker.getLatLng();
            const style = document.getElementById('style-select').value;
            const vscale = document.getElementById('vscale-select').value;
            const ytop = document.getElementById('ytop-select').value;
            const units = document.getElementById('units-select').value;
            const speed = document.getElementById('gif-speed').value;
            const fhrMin = document.getElementById('gif-fhr-min').value;
            const fhrMax = document.getElementById('gif-fhr-max').value;
            const url = `/api/xsect_gif?start_lat=${start.lat}&start_lon=${start.lng}` +
                `&end_lat=${end.lat}&end_lon=${end.lng}&cycle=${currentCycle}&style=${style}` +
                `&y_axis=${currentYAxis}&vscale=${vscale}&y_top=${ytop}&units=${units}&speed=${speed}` +
                `&temp_cmap=${document.getElementById('temp-cmap-select').value}` +
                `&anomaly=${anomalyMode ? 1 : 0}${modelParam()}` +
                (fhrMin ? `&fhr_min=${fhrMin}` : '') + (fhrMax ? `&fhr_max=${fhrMax}` : '');
            try {
                const res = await fetch(url);
                if (!res.ok) {
                    try {
                        const err = await res.json();
                        alert(err.error || 'GIF generation failed');
                    } catch(e) {
                        alert('GIF generation failed (server error)');
                    }
                    return;
                }
                const blob = await res.blob();
                const a = document.createElement('a');
                a.href = URL.createObjectURL(blob);
                a.download = `xsect_${currentCycle}_${style}.gif`;
                a.click();
                URL.revokeObjectURL(a.href);
            } catch (err) {
                alert('GIF generation failed: ' + err.message);
            } finally {
                btn.disabled = false;
                btn.textContent = 'GIF';
            }
        };

        // Swap start/end button
        document.getElementById('swap-btn').onclick = () => {
            if (!startMarker || !endMarker) return;

            // Get current positions
            const startPos = startMarker.getLatLng();
            const endPos = endMarker.getLatLng();

            // Swap positions (Mapbox uses setLngLat with [lng, lat])
            startMarker.setLngLat([endPos.lng, endPos.lat]);
            endMarker.setLngLat([startPos.lng, startPos.lat]);

            // Update line
            updateLine();

            // Regenerate cross-section
            generateCrossSection();
        };

        // =========================================================================
        // Auto-refresh for new cycles
        // =========================================================================
        setInterval(async () => {
            const oldCount = cycles.length;
            await loadCycles();
            if (cycles.length > oldCount) {
                showToast('New model run available!', 'success');
            }
        }, 5 * 60 * 1000);  // Every 5 minutes

        // =========================================================================
        // Style Guide
        // =========================================================================
        const styleGuide = [
            { category: 'Temperature & Moisture', styles: [
                { key: 'temp', name: 'Temperature', desc: 'Temperature in \u00b0C. Identify inversions, frontal zones, and freezing level. Cyan isotherms at -10/-20\u00b0C, light blue DGZ band (-12 to -18\u00b0C) for snow growth.', overlays: 'Freezing level (magenta), isotherms, DGZ band, snow level' },
                { key: 'wetbulb', name: 'Wet-Bulb Temperature', desc: 'Wet-bulb temperature \u2014 accounts for evaporative cooling. The 0\u00b0C line (lime) is the rain/snow boundary. More accurate than dry-bulb for precipitation type.', overlays: '0\u00b0C wet-bulb snow line (lime)' },
                { key: 'rh', name: 'Relative Humidity', desc: 'Relative humidity. Brown = dry air (subsidence, dry slots), green = moist. Track moisture plumes and dry intrusions aloft.', overlays: 'Snow level' },
                { key: 'q', name: 'Specific Humidity', desc: 'Specific humidity \u2014 absolute moisture in g/kg. Unlike RH, not temperature-dependent. Best for tracking moisture transport and atmospheric rivers.', overlays: 'RH contours at 70/80/90%' },
                { key: 'theta_e', name: 'Theta-E', desc: 'Equivalent potential temperature \u2014 conserved in moist processes. Higher values = warmer, moister air. Identifies warm/cold advection, instability, and atmospheric river cores.', overlays: 'Snow level' },
                { key: 'dewpoint_dep', name: 'Dewpoint Depression', desc: 'Dewpoint depression (T \u2212 Td). Near-zero = saturated air (clouds/fog). Large values = very dry. Useful for identifying cloud layers and dry air entrainment.' },
                { key: 'vpd', name: 'Vapor Pressure Deficit', desc: 'Vapor pressure deficit \u2014 how much more moisture the air can hold. High VPD drives evapotranspiration and fuels wildfire spread. Critical for fire weather and agriculture.' },
            ]},
            { category: 'Wind & Dynamics', styles: [
                { key: 'wind_speed', name: 'Wind Speed', desc: 'Wind speed in knots with wind barbs showing direction. Identify jet streams, low-level jets, gap winds, and mountain wave amplification.' },
                { key: 'omega', name: 'Vertical Velocity', desc: 'Vertical velocity in hPa/hr. Blue = rising (frontal lift, convection), red = sinking (subsidence). Key for precipitation and cloud formation.', overlays: 'Snow level' },
                { key: 'vorticity', name: 'Absolute Vorticity', desc: 'Absolute vorticity \u2014 atmospheric spin. Red = cyclonic (counterclockwise in NH). Maxima mark troughs and areas of storm development.' },
                { key: 'shear', name: 'Wind Shear', desc: 'Wind shear \u2014 rate of wind change with height. High values indicate jet cores, turbulence zones, and severe weather potential.' },
                { key: 'moisture_transport', name: 'Moisture Transport', desc: 'Moisture flux (q \u00d7 wind speed). Highlights atmospheric rivers and moisture conveyor belts. Higher values = stronger moisture transport.', overlays: 'Snow level' },
                { key: 'pv', name: 'Potential Vorticity', desc: 'Potential vorticity. The 2 PVU surface (magenta) marks the dynamical tropopause. Stratospheric intrusions appear as high-PV tongues descending into the troposphere.' },
            ]},
            { category: 'Clouds & Precip', styles: [
                { key: 'cloud', name: 'Cloud Water', desc: 'Cloud liquid water content. Shows cloud layer locations, thickness, and density.' },
                { key: 'cloud_total', name: 'Total Condensate', desc: 'All hydrometeors combined: cloud water, rain, snow, ice, graupel. Complete picture of where precipitation exists.' },
                { key: 'icing', name: 'Icing Potential', desc: 'Supercooled liquid water where T is 0 to -20\u00b0C. Purple = higher aircraft icing risk. Key for aviation safety.' },
                { key: 'lapse_rate', name: 'Lapse Rate', desc: 'Temperature change with height (\u00b0C/km). Near 9.8 = dry adiabatic (very unstable). Below 6 = stable. Reference lines show dry and moist adiabatic rates.' },
                { key: 'frontogenesis', name: 'Frontogenesis', desc: 'Petterssen frontogenesis \u2014 the key diagnostic for mesoscale snow bands. Red = temperature gradients intensifying (banding likely). Blue = frontolysis.' },
            ]},
            { category: 'Hazards & Composites', styles: [
                { key: 'fire_wx', name: 'Fire Weather', desc: 'Fire weather composite. RH fill (red=dry, green=moist) with Red Flag thresholds: 15% RH (red dashed), 25% RH (orange dashed), 25 kt wind (black). Cross-hatched zones meet both criteria simultaneously.', overlays: 'RH 15% (red), 25% (orange), wind 25kt (black), critical zone hatching, snow level' },
                { key: 'smoke', name: 'PM2.5 Smoke', desc: 'PM2.5 smoke concentration on native hybrid model levels. Shows smoke plume altitude and density. Only available when HRRR wrfnat files are loaded.' },
            ]},
        ];

        function renderExplainerModal() {
            const body = document.getElementById('modal-body');
            body.innerHTML = styleGuide.map(group => `
                <div style="margin-bottom:16px;">
                    <h3 style="color:var(--accent);font-size:14px;margin:12px 0 8px;text-transform:uppercase;letter-spacing:1px;">${group.category}</h3>
                    ${group.styles.map(s => `
                        <div class="param-card" style="cursor:pointer" onclick="document.getElementById('style-select').value='${s.key}';document.getElementById('explainer-modal').classList.remove('visible');generateCrossSection();">
                            <div class="param-header"><span class="param-name">${s.name}</span></div>
                            <div class="param-desc">${s.desc}</div>
                            ${s.overlays ? '<div class="param-tech">Overlays: ' + s.overlays + '</div>' : ''}
                        </div>
                    `).join('')}
                </div>
            `).join('');
        }

        document.getElementById('help-btn').onclick = () => {
            renderExplainerModal();
            document.getElementById('explainer-modal').classList.add('visible');
        };

        document.getElementById('modal-close').onclick = () => {
            document.getElementById('explainer-modal').classList.remove('visible');
        };

        document.getElementById('explainer-modal').onclick = (e) => {
            if (e.target.id === 'explainer-modal') {
                document.getElementById('explainer-modal').classList.remove('visible');
            }
        };

        // =========================================================================
        // Feature Requests
        // =========================================================================
        let requests = [];

        async function loadRequests() {
            try {
                const res = await fetch('/api/requests');
                requests = await res.json();
            } catch (e) {
                requests = [];
            }
        }

        function renderRequests() {
            const list = document.getElementById('request-list');
            if (requests.length === 0) {
                list.innerHTML = '<div style="color:var(--muted);text-align:center;padding:20px;">No requests yet. Be the first!</div>';
                return;
            }
            list.innerHTML = '<h3 style="margin:0 0 12px 0;font-size:14px;color:var(--muted);">Recent Requests</h3>' +
                requests.slice().reverse().slice(0, 20).map(r => `
                    <div class="request-item">
                        <div class="request-item-header">
                            <span>${r.name || 'Anonymous'}</span>
                            <span>${new Date(r.timestamp).toLocaleDateString()}</span>
                        </div>
                        <div class="request-item-text">${escapeHtml(r.text)}</div>
                    </div>
                `).join('');
        }

        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        // Feedback UI removed — check data/requests.json directly

        // =========================================================================
        // Initialize
        // =========================================================================
        // =========================================================================
        // RAM Status Modal
        // =========================================================================
        const ramModal = document.getElementById('ram-modal');
        const ramModalBody = document.getElementById('ram-modal-body');

        document.getElementById('memory-status').onclick = async () => {
            try {
                // Fetch status for all registered models
                const modelsRes = await fetch('/api/models');
                const modelsData = await modelsRes.json();
                const modelIds = (modelsData.models || []).map(m => m.id);

                const allResults = await Promise.all(
                    modelIds.map(async m => {
                        const r = await fetch(`/api/status?model=${m}`);
                        const d = await r.json();
                        return { model: m, loaded: d.loaded || [], memory_mb: d.memory_mb || 0 };
                    })
                );

                const totalLoaded = allResults.reduce((s, r) => s + r.loaded.length, 0);
                const totalMb = allResults.reduce((s, r) => s + r.memory_mb, 0);

                if (totalLoaded === 0) {
                    ramModalBody.innerHTML = '<p style="color:var(--muted);text-align:center;padding:20px;">Nothing loaded in RAM</p>';
                } else {
                    let html = '';
                    for (const { model, loaded, memory_mb } of allResults) {
                        if (loaded.length === 0) continue;

                        // Group by cycle
                        const groups = {};
                        loaded.forEach(([cycle, fhr]) => {
                            if (!groups[cycle]) groups[cycle] = [];
                            groups[cycle].push(fhr);
                        });

                        const perFhr = loaded.length > 0 ? memory_mb / loaded.length : 0;
                        const modelMbStr = memory_mb >= 1000 ? (memory_mb/1000).toFixed(1) + ' GB' : Math.round(memory_mb) + ' MB';

                        html += `<div style="margin-bottom:8px;"><strong style="color:var(--accent)">${model.toUpperCase()}</strong> <span style="color:var(--muted);font-size:11px;">${loaded.length} FHRs \u00B7 ${modelMbStr}</span></div>`;
                        html += '<table><tr><th>Cycle</th><th>Forecast Hours</th><th>~RAM</th></tr>';

                        Object.keys(groups).sort().reverse().forEach(cycle => {
                            const fhrs = groups[cycle].sort((a,b) => a - b);
                            const cycleMb = fhrs.length * perFhr;
                            const fhrStr = fhrs.map(f => 'F' + String(f).padStart(2,'0')).join(', ');
                            html += `<tr>
                                <td class="cycle-group">${cycle}</td>
                                <td>${fhrStr}</td>
                                <td>${cycleMb >= 1000 ? (cycleMb/1000).toFixed(1) + ' GB' : Math.round(cycleMb) + ' MB'}</td>
                            </tr>`;
                        });
                        html += '</table>';
                    }

                    const totalStr = totalMb >= 1000 ? (totalMb/1000).toFixed(1) + ' GB' : Math.round(totalMb) + ' MB';
                    html += `<div class="summary">
                        <strong>${totalLoaded}</strong> forecast hours loaded &bull;
                        <strong>${totalStr}</strong> total RAM &bull;
                        <strong>117 GB</strong> cap
                    </div>`;
                    ramModalBody.innerHTML = html;
                }

                ramModal.classList.add('visible');
            } catch (e) {
                showToast('Failed to fetch RAM status', 'error');
            }
        };

        ramModal.onclick = (e) => {
            if (e.target === ramModal) ramModal.classList.remove('visible');
        };
        document.getElementById('ram-modal-close').onclick = () => ramModal.classList.remove('visible');

        // =====================================================================
        // City Markers (232 dots, Mapbox GeoJSON clustering)
        // =====================================================================
        const REGION_COLORS = {
            california: '#f97316', pnw_rockies: '#22c55e', colorado_basin: '#3b82f6',
            southwest: '#ef4444', southern_plains: '#eab308', southeast_misc: '#a855f7',
        };
        const REGION_LABELS = {
            california: 'California', pnw_rockies: 'PNW / Rockies', colorado_basin: 'Colorado Basin',
            southwest: 'Southwest', southern_plains: 'Southern Plains', southeast_misc: 'Southeast / Misc',
        };
        // _citiesGeoJSON declared earlier (var) for readdCustomLayers forward reference

        function addCityLayers(geojson) {
            if (map.getSource('cities')) return;
            const cityVis = document.getElementById('toggle-city-markers') && document.getElementById('toggle-city-markers').checked ? 'visible' : 'none';
            map.addSource('cities', {
                type: 'geojson',
                data: geojson,
                cluster: true,
                clusterMaxZoom: 7,
                clusterRadius: 40,
            });
            map.addLayer({
                id: 'city-clusters',
                type: 'circle',
                source: 'cities',
                filter: ['has', 'point_count'],
                layout: { visibility: cityVis },
                paint: {
                    'circle-color': 'rgba(14,165,233,0.6)',
                    'circle-radius': ['step', ['get', 'point_count'], 14, 10, 18, 50, 24],
                    'circle-stroke-width': 1,
                    'circle-stroke-color': 'rgba(14,165,233,0.3)',
                },
            });
            map.addLayer({
                id: 'city-cluster-count',
                type: 'symbol',
                source: 'cities',
                filter: ['has', 'point_count'],
                layout: { 'text-field': '{point_count_abbreviated}', 'text-size': 11, visibility: cityVis },
                paint: { 'text-color': '#fff' },
            });
            map.addLayer({
                id: 'city-points',
                type: 'circle',
                source: 'cities',
                filter: ['!', ['has', 'point_count']],
                layout: { visibility: cityVis },
                paint: {
                    'circle-color': ['match', ['get', 'region'],
                        'california', '#f97316', 'pnw_rockies', '#22c55e',
                        'colorado_basin', '#3b82f6', 'southwest', '#ef4444',
                        'southern_plains', '#eab308', 'southeast_misc', '#a855f7',
                        '#94a3b8'],
                    'circle-radius': 5,
                    'circle-stroke-width': 1.5,
                    'circle-stroke-color': 'rgba(255,255,255,0.7)',
                },
            });

            // Click cluster to zoom
            map.on('click', 'city-clusters', (e) => {
                const features = map.queryRenderedFeatures(e.point, { layers: ['city-clusters'] });
                const clusterId = features[0].properties.cluster_id;
                map.getSource('cities').getClusterExpansionZoom(clusterId, (err, zoom) => {
                    if (err) return;
                    map.easeTo({ center: features[0].geometry.coordinates, zoom });
                });
            });

            // Click city point for popup
            map.on('click', 'city-points', (e) => {
                const f = e.features[0];
                const p = f.properties;
                const coords = f.geometry.coordinates.slice();
                const regionLabel = REGION_LABELS[p.region] || p.region;
                const elevText = p.elevation_ft ? ' &middot; ' + p.elevation_ft + ' ft' : '';
                const wuiText = p.wui_exposure ? '<br><span style="font-size:11px;color:#f87171;">' + p.wui_exposure + '</span>' : '';
                new mapboxgl.Popup({ offset: 8 })
                    .setLngLat(coords)
                    .setHTML(
                        '<div style="font-family:system-ui;min-width:180px;">' +
                        '<strong style="font-size:14px;">' + p.name + '</strong><br>' +
                        '<span style="font-size:11px;color:#94a3b8;">' + regionLabel + elevText + '</span>' +
                        wuiText +
                        '<br><br>' +
                        '<button data-action="profile" data-key="' + p.key + '" style="background:#0ea5e9;color:#fff;border:none;padding:4px 10px;border-radius:4px;cursor:pointer;font-size:12px;margin-right:4px;">Profile</button>' +
                        '<button data-action="section" data-key="' + p.key + '" style="background:#334155;color:#f1f5f9;border:1px solid #475569;padding:4px 10px;border-radius:4px;cursor:pointer;font-size:12px;">Set X-Sect</button>' +
                        '</div>'
                    ).addTo(map);
                // Wire up data-action buttons in popup
                setTimeout(() => {
                    document.querySelectorAll('button[data-action="profile"]').forEach(btn => {
                        btn.onclick = () => loadCityProfile(btn.dataset.key);
                    });
                    document.querySelectorAll('button[data-action="section"]').forEach(btn => {
                        btn.onclick = () => setCitySection(btn.dataset.key);
                    });
                }, 50);
            });

            // Cursor changes
            map.on('mouseenter', 'city-clusters', () => { map.getCanvas().style.cursor = 'pointer'; });
            map.on('mouseleave', 'city-clusters', () => { map.getCanvas().style.cursor = ''; });
            map.on('mouseenter', 'city-points', () => { map.getCanvas().style.cursor = 'pointer'; });
            map.on('mouseleave', 'city-points', () => { map.getCanvas().style.cursor = ''; });
        }

        async function loadCityMarkers() {
            try {
                const res = await fetch('/api/v1/cities');
                const data = await res.json();
                allCities = data.cities || [];

                // Build GeoJSON
                _citiesGeoJSON = {
                    type: 'FeatureCollection',
                    features: allCities.map(city => ({
                        type: 'Feature',
                        geometry: { type: 'Point', coordinates: [city.lon, city.lat] },
                        properties: {
                            key: city.key,
                            name: city.name,
                            region: city.region,
                            elevation_ft: city.elevation_ft || '',
                            wui_exposure: city.wui_exposure || '',
                        },
                    })),
                };

                if (mapStyleLoaded) addCityLayers(_citiesGeoJSON);
                renderCityList();
            } catch (e) {
                console.error('Failed to load cities:', e);
            }
        }

        function renderCityList(filter = '', region = 'all') {
            const container = document.getElementById('city-list');
            if (!container) return;
            let filtered = allCities;
            if (region !== 'all') {
                filtered = filtered.filter(c => c.region === region);
            }
            if (filter) {
                const q = filter.toLowerCase();
                filtered = filtered.filter(c => c.name.toLowerCase().includes(q) || c.key.includes(q));
            }

            // Group by region
            const groups = {};
            filtered.forEach(c => {
                if (!groups[c.region]) groups[c.region] = [];
                groups[c.region].push(c);
            });

            let html = '';
            const regionOrder = ['california', 'pnw_rockies', 'colorado_basin', 'southwest', 'southern_plains', 'southeast_misc'];
            for (const r of regionOrder) {
                const cities = groups[r];
                if (!cities || cities.length === 0) continue;
                html += `<div style="margin-bottom:8px;"><div style="font-size:10px;font-weight:600;color:${REGION_COLORS[r]};text-transform:uppercase;letter-spacing:0.5px;margin-bottom:4px;">${REGION_LABELS[r]} (${cities.length})</div>`;
                cities.sort((a, b) => a.name.localeCompare(b.name));
                cities.forEach(c => {
                    html += `<div class="city-item" onclick="loadCityProfile('${c.key}')">
                        <span class="city-name">${c.name}</span>
                        <span class="city-meta">${c.elevation_ft ? c.elevation_ft + ' ft' : ''}</span>
                    </div>`;
                });
                html += '</div>';
            }

            container.innerHTML = html || '<div style="color:var(--muted);text-align:center;padding:20px;">No cities found</div>';
        }

        // City search
        const citySearch = document.getElementById('city-search');
        if (citySearch) {
            citySearch.addEventListener('input', () => {
                renderCityList(citySearch.value, activeRegionFilter);
            });
        }

        // Region filter chips
        document.querySelectorAll('.region-chip').forEach(chip => {
            chip.addEventListener('click', () => {
                activeRegionFilter = chip.dataset.region;
                document.querySelectorAll('.region-chip').forEach(c => c.classList.toggle('active', c.dataset.region === activeRegionFilter));
                renderCityList(citySearch ? citySearch.value : '', activeRegionFilter);
            });
        });

        // Load city profile
        window.loadCityProfile = async function(key) {
            selectedCityKey = key;
            const city = allCities.find(c => c.key === key);
            if (city) {
                map.flyTo({ center: [city.lon, city.lat], zoom: 9, duration: 1000 });
            }

            // Switch to cities tab and show detail
            switchTab('cities');
            document.getElementById('city-list-view').style.display = 'none';
            const detailPanel = document.getElementById('city-detail');
            detailPanel.classList.add('active');

            const content = document.getElementById('city-detail-content');
            content.innerHTML = '<div class="loading-text">Loading profile...</div>';

            try {
                const res = await fetch(`/api/v1/cities/${key}`);
                const p = await res.json();

                let html = `<div style="margin-bottom:12px;">
                    <h3 style="font-size:16px;margin:0 0 4px;">${p.name}</h3>
                    <span style="font-size:11px;color:var(--muted);">${REGION_LABELS[p.region] || p.region}${p.elevation_ft ? ' · ' + p.elevation_ft + ' ft' : ''}</span>
                </div>`;

                if (p.terrain_notes) {
                    html += `<div style="margin-bottom:10px;"><div style="font-size:11px;font-weight:600;color:var(--muted);text-transform:uppercase;margin-bottom:4px;">Terrain</div><div style="font-size:12px;line-height:1.5;">${p.terrain_notes}</div></div>`;
                }

                if (p.danger_quadrants && p.danger_quadrants.length) {
                    html += `<div style="margin-bottom:10px;"><div style="font-size:11px;font-weight:600;color:var(--danger);text-transform:uppercase;margin-bottom:4px;">Danger Quadrants</div><div style="font-size:12px;">${p.danger_quadrants.join(', ')}</div></div>`;
                }

                if (p.wui_exposure) {
                    html += `<div style="margin-bottom:10px;"><div style="font-size:11px;font-weight:600;color:var(--warning);text-transform:uppercase;margin-bottom:4px;">WUI Exposure</div><div style="font-size:12px;line-height:1.5;">${p.wui_exposure}</div></div>`;
                }

                if (p.key_features && p.key_features.length) {
                    html += `<div style="margin-bottom:10px;"><div style="font-size:11px;font-weight:600;color:var(--muted);text-transform:uppercase;margin-bottom:4px;">Key Features</div>`;
                    p.key_features.forEach(f => {
                        if (typeof f === 'string') {
                            html += `<div style="font-size:12px;padding:4px 0;border-bottom:1px solid var(--border);">${f}</div>`;
                        } else {
                            html += `<div style="font-size:12px;padding:4px 0;border-bottom:1px solid var(--border);"><strong>${f.name}</strong> <span style="color:var(--muted);">${f.bearing || ''} · ${f.type || ''}</span>${f.notes ? '<br><span style="color:var(--muted);">' + f.notes + '</span>' : ''}</div>`;
                        }
                    });
                    html += '</div>';
                }

                if (p.historical_fires && p.historical_fires.length) {
                    html += `<div style="margin-bottom:10px;"><div style="font-size:11px;font-weight:600;color:#ef4444;text-transform:uppercase;margin-bottom:4px;">Historical Fires</div>`;
                    p.historical_fires.forEach(f => {
                        if (typeof f === 'string') {
                            html += `<div style="font-size:12px;padding:3px 0;">${f}</div>`;
                        } else {
                            html += `<div style="font-size:12px;padding:3px 0;"><strong>${f.name || 'Unknown'}</strong> ${f.year ? '(' + f.year + ')' : ''} ${f.acres ? '- ' + f.acres.toLocaleString() + ' acres' : ''}</div>`;
                        }
                    });
                    html += '</div>';
                }

                if (p.evacuation_routes && p.evacuation_routes.length) {
                    html += `<div style="margin-bottom:10px;"><div style="font-size:11px;font-weight:600;color:var(--accent);text-transform:uppercase;margin-bottom:4px;">Evacuation Routes</div>`;
                    p.evacuation_routes.forEach(r => {
                        html += `<div style="font-size:12px;padding:3px 0;">${typeof r === 'string' ? r : (r.route || r.name || JSON.stringify(r))}</div>`;
                    });
                    html += '</div>';
                }

                // Set cross-section button
                html += `<div style="margin-top:12px;"><button onclick="setCitySection('${key}')" style="width:100%;padding:8px;font-size:13px;">Set Cross-Section</button></div>`;

                content.innerHTML = html;
            } catch (e) {
                content.innerHTML = `<div style="color:#f87171;">Failed to load profile</div>`;
            }
        };

        // Back button from city detail
        document.getElementById('city-detail-back').onclick = () => {
            document.getElementById('city-list-view').style.display = '';
            document.getElementById('city-detail').classList.remove('active');
        };

        // Set cross-section from city profile
        window.setCitySection = async function(key) {
            try {
                const res = await fetch(`/api/v1/cities/${key}`);
                const p = await res.json();
                const features = p.key_features || [];

                let startLat, startLon, endLat, endLon;

                // Try to find meaningful endpoints from features
                if (features.length >= 2) {
                    // Use city center and offset based on danger quadrants
                    const dangerDirs = p.danger_quadrants || [];
                    const offset = 0.5;  // ~55km
                    startLat = p.lat + offset;
                    startLon = p.lon - offset;
                    endLat = p.lat - offset;
                    endLon = p.lon + offset;

                    if (dangerDirs.includes('north') || dangerDirs.includes('northeast')) {
                        startLat = p.lat + offset;
                        startLon = p.lon + (dangerDirs.includes('northeast') ? offset : 0);
                        endLat = p.lat - offset;
                        endLon = p.lon - (dangerDirs.includes('northeast') ? offset : 0);
                    } else if (dangerDirs.includes('east')) {
                        startLat = p.lat;
                        startLon = p.lon + offset;
                        endLat = p.lat;
                        endLon = p.lon - offset;
                    }
                } else {
                    // Default: E-W transect through city
                    startLat = p.lat;
                    startLon = p.lon - 0.5;
                    endLat = p.lat;
                    endLon = p.lon + 0.5;
                }

                // Clear existing
                clearXSMarkers();

                // Place markers
                startMarker = setupStartMarker(startLat, startLon);
                endMarker = setupEndMarker(endLat, endLon);
                updateLine();
                fitBoundsLL([[startLat, startLon], [endLat, endLon]], 60);
                closePanelMobile();
                generateCrossSection();
                showToast(`Cross-section set for ${p.name}`, 'success');
            } catch (e) {
                showToast('Failed to set cross-section', 'error');
            }
        };

        // =====================================================================
        // Event Markers (22 with coordinates, Mapbox GeoJSON)
        // =====================================================================
        // _eventsGeoJSON declared earlier (var) for readdCustomLayers forward reference
        let _eventsLookup = {};  // cycle_key -> evt object for popup rendering

        function addEventLayers(geojson) {
            if (map.getSource('events')) return;
            const evtVis = document.getElementById('toggle-event-markers') && document.getElementById('toggle-event-markers').checked ? 'visible' : 'none';
            map.addSource('events', { type: 'geojson', data: geojson });
            map.addLayer({
                id: 'event-points',
                type: 'circle',
                source: 'events',
                layout: { visibility: evtVis },
                paint: {
                    'circle-color': '#f43f5e',
                    'circle-radius': 7,
                    'circle-stroke-width': 2,
                    'circle-stroke-color': '#fff',
                },
            });
            map.addLayer({
                id: 'event-stars',
                type: 'symbol',
                source: 'events',
                layout: {
                    'text-field': '★',
                    'text-size': 10,
                    'text-allow-overlap': true,
                    visibility: evtVis,
                },
                paint: { 'text-color': '#fff' },
            });

            // Click event point for popup
            map.on('click', 'event-points', (e) => {
                const f = e.features[0];
                const p = f.properties;
                const coords = f.geometry.coordinates.slice();
                const evt = _eventsLookup[p.cycle_key] || _eventsLookup[p.archive_cycle];

                let sectionsHtml = '';
                if (evt && evt.coordinates && evt.coordinates.suggested_sections) {
                    const cycleKey = evt.archive_cycle || evt.cycle_key;
                    const offset = evt.fhr_offset || 0;
                    sectionsHtml = evt.coordinates.suggested_sections.map((s, i) => {
                        return '<button class="evt-section-btn" data-cycle="' + cycleKey + '" data-sidx="' + i + '" data-offset="' + offset + '" style="background:#334155;color:#f1f5f9;border:1px solid #475569;padding:3px 8px;border-radius:4px;cursor:pointer;font-size:11px;margin:2px;">' + (s.label || 'Load') + '</button>';
                    }).join('');
                }

                const heroInfo = p.hero_product ? '<br><span style="font-size:10px;background:#0ea5e9;color:#fff;padding:1px 6px;border-radius:4px;font-weight:600;">Best: ' + p.hero_product + ' F' + String(p.hero_fhr || 0).padStart(2,'0') + '</span>' : '';
                const descText = p.description ? '<br><span style="font-size:11px;color:#94a3b8;">' + p.description.substring(0, 180) + '</span>' : '';

                const popup = new mapboxgl.Popup({ offset: 10 })
                    .setLngLat(coords)
                    .setHTML(
                        '<div style="font-family:system-ui;min-width:220px;">' +
                        '<strong style="font-size:13px;">' + p.name + '</strong><br>' +
                        '<span style="font-size:11px;color:#94a3b8;">' + (p.date_local || p.cycle_key) + ' &middot; ' + (p.category || '') + '</span>' +
                        heroInfo + descText +
                        (sectionsHtml ? '<br><div style="margin-top:6px;">' + sectionsHtml + '</div>' : '') +
                        '</div>'
                    ).addTo(map);

                // Attach click handlers to section buttons after popup opens
                popup.on('open', () => {
                    setTimeout(() => {
                        document.querySelectorAll('.evt-section-btn').forEach(btn => {
                            btn.addEventListener('click', () => {
                                const ck = btn.dataset.cycle;
                                const sidx = parseInt(btn.dataset.sidx);
                                const off = parseInt(btn.dataset.offset);
                                const evtData = _eventsLookup[ck];
                                if (evtData && evtData.coordinates && evtData.coordinates.suggested_sections[sidx]) {
                                    loadEventSection(ck, evtData.coordinates.suggested_sections[sidx], off);
                                }
                            });
                        });
                    }, 50);
                });
            });

            map.on('mouseenter', 'event-points', () => { map.getCanvas().style.cursor = 'pointer'; });
            map.on('mouseleave', 'event-points', () => { map.getCanvas().style.cursor = ''; });
        }

        async function loadEventMarkers() {
            try {
                const res = await fetch('/api/v1/events');
                const data = await res.json();
                allEvents = data.events || [];

                // Build lookup
                allEvents.forEach(evt => {
                    _eventsLookup[evt.cycle_key] = evt;
                    if (evt.archive_cycle) _eventsLookup[evt.archive_cycle] = evt;
                });

                // Build GeoJSON
                const features = allEvents
                    .filter(e => e.coordinates && e.coordinates.center)
                    .map(evt => ({
                        type: 'Feature',
                        geometry: { type: 'Point', coordinates: [evt.coordinates.center[1], evt.coordinates.center[0]] },
                        properties: {
                            name: evt.name || '',
                            cycle_key: evt.cycle_key || '',
                            archive_cycle: evt.archive_cycle || '',
                            date_local: evt.date_local || '',
                            category: evt.category || '',
                            hero_product: evt.hero_product || '',
                            hero_fhr: evt.hero_fhr || 0,
                            description: evt.description || evt.notes || '',
                        },
                    }));

                _eventsGeoJSON = { type: 'FeatureCollection', features };
                if (mapStyleLoaded) addEventLayers(_eventsGeoJSON);
                renderEventList();
            } catch (e) {
                console.error('Failed to load events:', e);
            }
        }

        // Load event cross-section from popup
        window.loadEventSection = function(cycleKey, section, fhrOffset) {
            if (typeof section === 'string') section = JSON.parse(section);
            fhrOffset = fhrOffset || 0;
            if (!section.start || !section.end) return;

            clearXSMarkers();
            // Clear existing POI markers
            poiMarkers.forEach(p => p.marker.remove());
            poiMarkers = [];
            poiPlaceMode = false;
            updatePoiBtn();

            // section.start/end are [lat, lon] arrays
            startMarker = setupStartMarker(section.start[0], section.start[1]);
            endMarker = setupEndMarker(section.end[0], section.end[1]);
            updateLine();

            // Load POI markers from section if present
            if (section.markers && Array.isArray(section.markers)) {
                section.markers.forEach(mkr => {
                    const lat = mkr.lat || mkr[0];
                    const lon = mkr.lon || mkr[1];
                    const label = mkr.label || '';
                    addPoi(lat, lon, label);
                });
            }

            fitBoundsLL([section.start, section.end], 60);
            closePanelMobile();

            // Set product if suggested
            if (section.products && section.products.length > 0) {
                const styleSelect = document.getElementById('style-select');
                const firstProduct = section.products[0];
                if (Array.from(styleSelect.options).some(o => o.value === firstProduct)) {
                    styleSelect.value = firstProduct;
                    updateTempCmapVisibility();
                    updateAnomalyVisibility();
                }
            }

            // Set best FHR for this section if available (apply offset for archive_cycle)
            if (section.best_fhr !== undefined && section.best_fhr !== null) {
                const fhr = section.best_fhr + fhrOffset;
                if (selectedFhrs.includes(fhr)) {
                    activeFhr = fhr;
                    document.getElementById('active-fhr').textContent = `F${String(fhr).padStart(2,'0')}`;
                    updateChipStates();
                }
            }

            generateCrossSection();
            showToast(`Loaded: ${section.label || 'Event section'}`, 'success');
        };

        // Render events list in sidebar
        function renderEventList(filter = '', category = '', coordsOnly = false) {
            const container = document.getElementById('event-list');
            if (!container) return;

            let filtered = allEvents;
            if (category) filtered = filtered.filter(e => e.category === category);
            if (coordsOnly) filtered = filtered.filter(e => e.coordinates && e.coordinates.center);
            if (filter) {
                const q = filter.toLowerCase();
                filtered = filtered.filter(e => (e.name || '').toLowerCase().includes(q) || (e.notes || '').toLowerCase().includes(q));
            }

            const categoryColors = {
                'fire-ca': '#f97316', 'fire-pnw': '#22c55e', 'fire-co': '#3b82f6',
                'fire-sw': '#ef4444', 'hurricane': '#06b6d4', 'tornado': '#a855f7',
                'derecho': '#eab308', 'hail': '#d946ef', 'ar': '#0ea5e9',
                'winter': '#94a3b8', 'other': '#64748b',
            };

            let html = '';
            filtered.forEach(evt => {
                const hasCoords = evt.coordinates && evt.coordinates.center;
                const catColor = categoryColors[evt.category] || '#64748b';
                const heroTag = evt.hero_product ? `<span class="event-hero-badge" title="Best view: F${String(evt.hero_fhr).padStart(2,'0')} ${evt.hero_product}">${evt.hero_product} F${String(evt.hero_fhr).padStart(2,'0')}</span>` : '';
                const desc = evt.description ? `<div class="event-desc">${evt.description.substring(0, 120)}${evt.description.length > 120 ? '...' : ''}</div>` : '';
                const dataTag = evt.has_data ? '<span class="event-data-badge" title="HRRR data available">LIVE</span>' : '';
                html += `<div class="event-item ${hasCoords ? 'has-coords' : ''}" onclick="showEventDetail('${evt.cycle_key}')" style="border-left-color:${catColor};">
                    <div class="event-name">${evt.name || evt.cycle_key}</div>
                    ${desc}
                    <div class="event-meta">
                        ${evt.date_local || ''} &middot;
                        <span class="event-category-chip" style="border:1px solid ${catColor};color:${catColor};">${evt.category}</span>
                        ${hasCoords ? ' <span style="color:var(--accent);" title="Has map coordinates">&#128205;</span>' : ''}
                        ${dataTag}
                        ${heroTag}
                    </div>
                </div>`;
            });

            container.innerHTML = html || '<div style="color:var(--muted);text-align:center;padding:20px;">No events found</div>';
        }

        // Populate category filter dropdown
        function populateEventCategories() {
            const sel = document.getElementById('event-category-filter');
            if (!sel) return;
            const cats = {};
            allEvents.forEach(e => { cats[e.category] = (cats[e.category] || 0) + 1; });
            Object.keys(cats).sort().forEach(cat => {
                const opt = document.createElement('option');
                opt.value = cat;
                opt.textContent = `${cat} (${cats[cat]})`;
                sel.appendChild(opt);
            });
        }

        // Event search/filter handlers
        const eventSearch = document.getElementById('event-search');
        const eventCategoryFilter = document.getElementById('event-category-filter');
        const eventCoordsOnly = document.getElementById('event-coords-only');

        function refreshEventList() {
            renderEventList(
                eventSearch ? eventSearch.value : '',
                eventCategoryFilter ? eventCategoryFilter.value : '',
                eventCoordsOnly ? eventCoordsOnly.checked : false
            );
        }

        if (eventSearch) eventSearch.addEventListener('input', refreshEventList);
        if (eventCategoryFilter) eventCategoryFilter.addEventListener('change', refreshEventList);
        if (eventCoordsOnly) eventCoordsOnly.addEventListener('change', refreshEventList);

        // =====================================================================
        // Event Detail Panel
        // =====================================================================
        window.showEventDetail = function(cycleKey) {
            const evt = allEvents.find(e => e.cycle_key === cycleKey);
            if (!evt) return;

            const categoryColors = {
                'fire-ca': '#f97316', 'fire-pnw': '#22c55e', 'fire-co': '#3b82f6',
                'fire-sw': '#ef4444', 'hurricane': '#06b6d4', 'tornado': '#a855f7',
                'derecho': '#eab308', 'hail': '#d946ef', 'ar': '#0ea5e9',
                'winter': '#94a3b8', 'other': '#64748b',
            };
            const catColor = categoryColors[evt.category] || '#64748b';
            const hasCoords = evt.coordinates && evt.coordinates.center;
            const hasHero = evt.hero_product && evt.hero_fhr !== undefined && evt.hero_fhr !== null;
            const sections = (evt.coordinates && evt.coordinates.suggested_sections) || [];

            let html = '<div class="event-detail-header">';
            html += `<h3>${evt.name || evt.cycle_key}</h3>`;
            html += '<div class="event-detail-badges">';
            html += `<span class="event-category-chip" style="border:1px solid ${catColor};color:${catColor};">${evt.category}</span>`;
            if (hasHero) html += `<span class="event-hero-badge">${evt.hero_product} F${String(evt.hero_fhr).padStart(2,'0')}</span>`;
            if (evt.has_data) html += '<span class="event-data-badge">LIVE</span>';
            html += `<span style="font-size:11px;color:var(--muted);">${evt.date_local || evt.cycle_key}</span>`;
            html += '</div></div>';

            // Description
            if (evt.description) {
                html += `<div class="event-detail-text">${evt.description}</div>`;
            }

            // Meteorological setup
            if (evt.meteorological_setup) {
                html += '<div class="event-detail-section">';
                html += '<div class="event-detail-section-title">Meteorological Setup</div>';
                html += `<div class="event-detail-text">${evt.meteorological_setup}</div>`;
                html += '</div>';
            }

            // Key features
            if (evt.key_features && evt.key_features.length) {
                html += '<div class="event-detail-section">';
                html += '<div class="event-detail-section-title">Key Features</div>';
                html += '<div class="event-detail-text"><ul>';
                evt.key_features.forEach(f => { html += `<li>${f}</li>`; });
                html += '</ul></div></div>';
            }

            // Impact stats
            const impacts = evt.impacts || {};
            const impactEntries = [];
            if (impacts.fatalities != null) impactEntries.push({v: impacts.fatalities, l: 'Fatalities'});
            if (impacts.structures_destroyed != null) impactEntries.push({v: impacts.structures_destroyed.toLocaleString(), l: 'Structures'});
            if (impacts.acres_burned != null) impactEntries.push({v: impacts.acres_burned.toLocaleString(), l: 'Acres'});
            if (impacts.damage_estimate) impactEntries.push({v: impacts.damage_estimate, l: 'Damage'});
            if (impacts.storm_surge_ft != null) impactEntries.push({v: impacts.storm_surge_ft + ' ft', l: 'Storm Surge'});
            if (impacts.max_rainfall_in != null) impactEntries.push({v: impacts.max_rainfall_in + ' in', l: 'Max Rainfall'});
            if (impactEntries.length) {
                html += '<div class="event-detail-section">';
                html += '<div class="event-detail-section-title">Impacts</div>';
                html += '<div class="event-impact-grid">';
                impactEntries.forEach(s => {
                    html += `<div class="event-impact-stat"><div class="stat-value">${s.v}</div><div class="stat-label">${s.l}</div></div>`;
                });
                html += '</div></div>';
            }

            // Evaluation notes
            if (evt.evaluation_notes) {
                html += `<div class="event-eval-notes">${evt.evaluation_notes}</div>`;
            }

            // Action buttons
            html += '<div class="event-detail-section"><div class="event-detail-section-title">Actions</div>';
            html += '<div class="showcase-actions">';

            if (hasHero && hasCoords) {
                html += `<button class="showcase-btn primary-action" onclick="launchShowcase('${evt.cycle_key}')">
                    <span class="btn-icon">&#9733;</span>
                    <div><div class="btn-label">Launch Showcase</div>
                    <div class="btn-desc">Load data, fly to location, auto-generate quad plot</div></div>
                </button>`;
            } else if (hasCoords) {
                html += `<button class="showcase-btn primary-action" onclick="flyToEvent('${evt.cycle_key}')">
                    <span class="btn-icon">&#128205;</span>
                    <div><div class="btn-label">Fly to Event</div>
                    <div class="btn-desc">Load data and fly to event location</div></div>
                </button>`;
            }

            if (evt.quad_products && evt.quad_products.length >= 2) {
                html += `<button class="showcase-btn" onclick="showcaseQuadPlot('${evt.cycle_key}')">
                    <span class="btn-icon">&#9638;</span>
                    <div><div class="btn-label">4-Panel Analysis</div>
                    <div class="btn-desc">${evt.quad_products.join(', ')}</div></div>
                </button>`;
            }

            if (evt.essential_fhrs && evt.essential_fhrs.length >= 4) {
                html += `<button class="showcase-btn" onclick="showcaseTemporalEvolution('${evt.cycle_key}')">
                    <span class="btn-icon">&#9202;</span>
                    <div><div class="btn-label">Time Evolution</div>
                    <div class="btn-desc">F${evt.essential_fhrs[0]}–F${evt.essential_fhrs[evt.essential_fhrs.length-1]} temporal grid</div></div>
                </button>`;
            }

            if (evt.essential_fhrs && evt.essential_fhrs.length >= 2) {
                html += `<button class="showcase-btn" onclick="showcasePlayback('${evt.cycle_key}')">
                    <span class="btn-icon">&#9654;</span>
                    <div><div class="btn-label">Animated Playback</div>
                    <div class="btn-desc">Prerender &amp; animate through ${evt.essential_fhrs.length} key frames</div></div>
                </button>`;
            }

            sections.forEach((s, i) => {
                const sJson = JSON.stringify(s).replace(/'/g, "\\\\'").replace(/"/g, '&quot;');
                html += `<button class="showcase-btn" onclick="loadEventSection('${evt.archive_cycle || evt.cycle_key}', '${sJson}', ${evt.fhr_offset || 0})">
                    <span class="btn-icon">&#8596;</span>
                    <div><div class="btn-label">${s.label || 'Cross-Section ' + (i+1)}</div>
                    <div class="btn-desc">Load cross-section line on map</div></div>
                </button>`;
            });

            html += '</div></div>';

            document.getElementById('event-detail-content').innerHTML = html;
            document.getElementById('event-list-view').style.display = 'none';
            document.getElementById('event-detail').classList.add('active');
        };

        // Back button for event detail panel
        document.getElementById('event-detail-back').addEventListener('click', () => {
            document.getElementById('event-detail').classList.remove('active');
            document.getElementById('event-list-view').style.display = '';
        });

        window.flyToEvent = async function(cycleKey) {
            const evt = allEvents.find(e => e.cycle_key === cycleKey);
            if (!evt) return;

            // Switch to HRRR model if not already (events are HRRR cycles)
            if (currentModel !== 'hrrr') {
                const modelSelect = document.getElementById('model-select');
                if (modelSelect) {
                    modelSelect.value = 'hrrr';
                    modelSelect.dispatchEvent(new Event('change'));
                    await new Promise(r => setTimeout(r, 500));
                }
            }

            // Load the event's cycle (use archive_cycle if available for mismatched keys)
            const dataCycle = evt.archive_cycle || cycleKey;
            const fhrOffset = evt.fhr_offset || 0;
            const toast = showToast(`Loading ${evt.name || cycleKey}...`);
            try {
                const res = await fetch(`/api/load_cycle?cycle=${dataCycle}`, {method: 'POST'});
                const data = await res.json();
                toast.remove();

                if (data.success) {
                    showToast(`Loaded ${data.loaded_fhrs || 'all'} forecast hours for ${evt.name || cycleKey}`, 'success');

                    // Refresh cycle dropdown so the event cycle appears
                    const cyclesRes = await fetch(`/api/cycles?model=hrrr`);
                    const cyclesData = await cyclesRes.json();
                    cycles = cyclesData.cycles || [];
                    buildCycleDropdown(cycles, false);

                    // Select the archive cycle (may differ from event key)
                    currentCycle = dataCycle;
                    cycleSelect.value = dataCycle;

                    // Update FHR chips
                    await refreshLoadedStatus();
                    const curCycleData = cycles.find(c => c.key === dataCycle);
                    if (curCycleData) {
                        renderFhrChips(curCycleData.fhrs);
                    }

                    // Select hero FHR if available (offset for archive_cycle mismatch), otherwise first FHR
                    const heroFhr = (evt.hero_fhr !== undefined && evt.hero_fhr !== null) ? evt.hero_fhr + fhrOffset : null;
                    if (heroFhr !== undefined && heroFhr !== null && selectedFhrs.includes(heroFhr)) {
                        activeFhr = heroFhr;
                    } else if (selectedFhrs.length > 0) {
                        activeFhr = selectedFhrs[0];
                    }
                    document.getElementById('active-fhr').textContent = `F${String(activeFhr).padStart(2,'0')}`;
                    updateChipStates();

                    // Select hero product if available
                    if (evt.hero_product) {
                        const styleSelect = document.getElementById('style-select');
                        if (Array.from(styleSelect.options).some(o => o.value === evt.hero_product)) {
                            styleSelect.value = evt.hero_product;
                            updateTempCmapVisibility();
                            updateAnomalyVisibility();
                        }
                    }
                } else {
                    showToast(data.error || `Failed to load cycle ${cycleKey}`, 'error');
                    return;
                }
            } catch (err) {
                toast.remove();
                showToast(`Failed to load cycle: ${err.message}`, 'error');
                return;
            }

            closePanelMobile();

            // Fly to location and set up cross-section if event has coordinates
            if (evt.coordinates && evt.coordinates.center) {
                map.flyTo({ center: [evt.coordinates.center[1], evt.coordinates.center[0]], zoom: 8, duration: 1000 });
                if (evt.coordinates.suggested_sections && evt.coordinates.suggested_sections.length > 0) {
                    loadEventSection(dataCycle, evt.coordinates.suggested_sections[0], fhrOffset);
                }
            }
        };

        // =====================================================================
        // Showcase Orchestration
        // =====================================================================
        let showcaseEvent = null;
        let showcaseMode = null;

        function showShowcaseNotes(notes) {
            const bar = document.getElementById('showcase-notes');
            const text = document.getElementById('showcase-notes-text');
            if (bar && text && notes) {
                text.textContent = notes;
                bar.style.display = '';
            }
        }

        function hideShowcaseNotes() {
            const bar = document.getElementById('showcase-notes');
            if (bar) bar.style.display = 'none';
            showcaseEvent = null;
            showcaseMode = null;
        }

        // Helper: ensure event cycle is loaded, returns evt object or null on failure
        async function ensureEventLoaded(cycleKey) {
            const evt = allEvents.find(e => e.cycle_key === cycleKey);
            if (!evt) return null;

            // Switch to HRRR
            if (currentModel !== 'hrrr') {
                const modelSelect = document.getElementById('model-select');
                if (modelSelect) {
                    modelSelect.value = 'hrrr';
                    modelSelect.dispatchEvent(new Event('change'));
                    await new Promise(r => setTimeout(r, 500));
                }
            }

            // Load cycle
            const toast = showToast(`Loading ${evt.name || cycleKey}...`);
            try {
                const res = await fetch(`/api/load_cycle?cycle=${cycleKey}`, {method: 'POST'});
                const data = await res.json();
                toast.remove();
                if (!data.success) {
                    showToast(data.error || `Failed to load cycle ${cycleKey}`, 'error');
                    return null;
                }
                showToast(`Loaded ${data.loaded_fhrs || 'all'} FHRs for ${evt.name || cycleKey}`, 'success');

                // Refresh cycle dropdown
                const cyclesRes = await fetch('/api/cycles?model=hrrr');
                const cyclesData = await cyclesRes.json();
                cycles = cyclesData.cycles || [];
                buildCycleDropdown(cycles, false);
                currentCycle = cycleKey;
                cycleSelect.value = cycleKey;
                await refreshLoadedStatus();
                const curCycleData = cycles.find(c => c.key === cycleKey);
                if (curCycleData) renderFhrChips(curCycleData.fhrs);

                // Set hero FHR
                if (evt.hero_fhr !== undefined && evt.hero_fhr !== null && selectedFhrs.includes(evt.hero_fhr)) {
                    activeFhr = evt.hero_fhr;
                } else if (selectedFhrs.length > 0) {
                    activeFhr = selectedFhrs[0];
                }
                document.getElementById('active-fhr').textContent = `F${String(activeFhr).padStart(2,'0')}`;
                updateChipStates();

                // Set hero product
                if (evt.hero_product) {
                    const styleSelect = document.getElementById('style-select');
                    if (Array.from(styleSelect.options).some(o => o.value === evt.hero_product)) {
                        styleSelect.value = evt.hero_product;
                        updateTempCmapVisibility();
                        updateAnomalyVisibility();
                    }
                }

                return evt;
            } catch (err) {
                toast.remove();
                showToast(`Failed to load cycle: ${err.message}`, 'error');
                return null;
            }
        }

        window.launchShowcase = async function(cycleKey) {
            showcaseEvent = cycleKey;
            showcaseMode = 'showcase';

            const evt = await ensureEventLoaded(cycleKey);
            if (!evt) return;

            closePanelMobile();

            // Fly to location
            if (evt.coordinates && evt.coordinates.center) {
                map.flyTo({ center: [evt.coordinates.center[1], evt.coordinates.center[0]], zoom: 8, duration: 1000 });
            }

            // Load first cross-section line
            const sections = (evt.coordinates && evt.coordinates.suggested_sections) || [];
            if (sections.length > 0) {
                loadEventSection(cycleKey, sections[0]);
            }

            // Update bottom status
            const statusEl = document.getElementById('bottom-status');
            if (statusEl) statusEl.innerHTML = `<span style="color:var(--accent);">&#9733; ${evt.name || cycleKey}</span> <span class="fhr-label" id="active-fhr">F${String(activeFhr).padStart(2,'0')}</span>`;

            // Auto-generate quad plot after a brief delay for cross-section to render
            if (evt.quad_products && evt.quad_products.length >= 2) {
                await new Promise(r => setTimeout(r, 1500));
                await showcaseQuadPlot(cycleKey);
            }
        };

        window.showcaseQuadPlot = async function(cycleKey) {
            const evt = allEvents.find(e => e.cycle_key === cycleKey);
            if (!evt || !evt.quad_products || evt.quad_products.length < 2) return;

            // Ensure data is loaded if not already
            if (currentCycle !== cycleKey) {
                const loaded = await ensureEventLoaded(cycleKey);
                if (!loaded) return;
            }

            // Need cross-section line
            if (!startMarker || !endMarker) {
                const sections = (evt.coordinates && evt.coordinates.suggested_sections) || [];
                if (sections.length > 0) {
                    loadEventSection(cycleKey, sections[0]);
                    await new Promise(r => setTimeout(r, 500));
                } else {
                    showToast('No cross-section line set', 'error');
                    return;
                }
            }

            showcaseEvent = cycleKey;
            showcaseMode = 'quad';

            const start = startMarker.getLatLng();
            const end = endMarker.getLatLng();
            const fhr = evt.hero_fhr !== undefined && evt.hero_fhr !== null ? evt.hero_fhr : activeFhr;
            const products = evt.quad_products.slice(0, 4).join(',');
            const vscale = document.getElementById('vscale-select').value;
            const ytop = document.getElementById('ytop-select').value;
            const units = document.getElementById('units-select').value;
            const tempCmap = document.getElementById('temp-cmap-select').value;

            const params = `mode=product&start_lat=${start.lat}&start_lon=${start.lng}` +
                `&end_lat=${end.lat}&end_lon=${end.lng}&cycle=${cycleKey}&fhr=${fhr}` +
                `&products=${products}&model=hrrr&y_axis=${currentYAxis}&y_top=${ytop}` +
                `&units=${units}&temp_cmap=${tempCmap}`;

            const container = document.getElementById('xsect-container');
            container.innerHTML = '<div class="loading-text">Generating 4-panel analysis...</div>';
            setBottomState('half');

            // Hide compare panel
            document.getElementById('panel-compare').style.display = 'none';
            document.getElementById('xsect-panels').classList.remove('compare-active');

            try {
                const res = await fetch(`/api/v1/comparison?${params}`);
                if (!res.ok) throw new Error(await res.text() || 'Failed to generate comparison');
                const blob = await res.blob();
                const oldImg = container.querySelector('img');
                if (oldImg && oldImg.src && oldImg.src.startsWith('blob:')) URL.revokeObjectURL(oldImg.src);
                const img = document.createElement('img');
                img.id = 'xsect-img';
                img.src = URL.createObjectURL(blob);
                container.innerHTML = '';
                container.appendChild(img);

                if (evt.evaluation_notes) showShowcaseNotes(evt.evaluation_notes);
            } catch (err) {
                container.innerHTML = `<div style="color:#f87171">${err.message}</div>`;
            }
        };

        window.showcaseTemporalEvolution = async function(cycleKey) {
            const evt = allEvents.find(e => e.cycle_key === cycleKey);
            if (!evt || !evt.essential_fhrs || evt.essential_fhrs.length < 2) return;

            if (currentCycle !== cycleKey) {
                const loaded = await ensureEventLoaded(cycleKey);
                if (!loaded) return;
            }

            // Need cross-section line
            if (!startMarker || !endMarker) {
                const sections = (evt.coordinates && evt.coordinates.suggested_sections) || [];
                if (sections.length > 0) {
                    loadEventSection(cycleKey, sections[0]);
                    await new Promise(r => setTimeout(r, 500));
                } else {
                    showToast('No cross-section line set', 'error');
                    return;
                }
            }

            showcaseEvent = cycleKey;
            showcaseMode = 'temporal';

            // Pick up to 4 evenly-spaced FHRs
            const allFhrs = evt.essential_fhrs;
            let picked;
            if (allFhrs.length <= 4) {
                picked = allFhrs;
            } else {
                const step = (allFhrs.length - 1) / 3;
                picked = [0, 1, 2, 3].map(i => allFhrs[Math.round(i * step)]);
            }

            const start = startMarker.getLatLng();
            const end = endMarker.getLatLng();
            const product = evt.hero_product || document.getElementById('style-select').value;
            const vscale = document.getElementById('vscale-select').value;
            const ytop = document.getElementById('ytop-select').value;
            const units = document.getElementById('units-select').value;
            const tempCmap = document.getElementById('temp-cmap-select').value;

            const params = `mode=temporal&start_lat=${start.lat}&start_lon=${start.lng}` +
                `&end_lat=${end.lat}&end_lon=${end.lng}&cycle=${cycleKey}` +
                `&fhrs=${picked.join(',')}&product=${product}&model=hrrr` +
                `&y_axis=${currentYAxis}&y_top=${ytop}&units=${units}&temp_cmap=${tempCmap}`;

            const container = document.getElementById('xsect-container');
            container.innerHTML = '<div class="loading-text">Generating temporal evolution...</div>';
            setBottomState('half');

            document.getElementById('panel-compare').style.display = 'none';
            document.getElementById('xsect-panels').classList.remove('compare-active');

            try {
                const res = await fetch(`/api/v1/comparison?${params}`);
                if (!res.ok) throw new Error(await res.text() || 'Failed to generate comparison');
                const blob = await res.blob();
                const oldImg = container.querySelector('img');
                if (oldImg && oldImg.src && oldImg.src.startsWith('blob:')) URL.revokeObjectURL(oldImg.src);
                const img = document.createElement('img');
                img.id = 'xsect-img';
                img.src = URL.createObjectURL(blob);
                container.innerHTML = '';
                container.appendChild(img);

                if (evt.evaluation_notes) showShowcaseNotes(evt.evaluation_notes);
            } catch (err) {
                container.innerHTML = `<div style="color:#f87171">${err.message}</div>`;
            }
        };

        window.showcasePlayback = async function(cycleKey) {
            const evt = allEvents.find(e => e.cycle_key === cycleKey);
            if (!evt || !evt.essential_fhrs || evt.essential_fhrs.length < 2) return;

            if (currentCycle !== cycleKey) {
                const loaded = await ensureEventLoaded(cycleKey);
                if (!loaded) return;
            }

            // Need cross-section line
            if (!startMarker || !endMarker) {
                const sections = (evt.coordinates && evt.coordinates.suggested_sections) || [];
                if (sections.length > 0) {
                    loadEventSection(cycleKey, sections[0]);
                    await new Promise(r => setTimeout(r, 500));
                } else {
                    showToast('No cross-section line set', 'error');
                    return;
                }
            }

            showcaseEvent = cycleKey;
            showcaseMode = 'playback';
            setBottomState('half');

            const start = startMarker.getLatLng();
            const end = endMarker.getLatLng();
            const product = evt.hero_product || document.getElementById('style-select').value;
            const vscale = document.getElementById('vscale-select').value;
            const ytop = document.getElementById('ytop-select').value;
            const units = document.getElementById('units-select').value;
            const tempCmap = document.getElementById('temp-cmap-select').value;
            const anomaly = document.querySelector('#anomaly-toggle .toggle-btn.active')?.dataset?.value === 'anomaly';

            const fhrs = evt.essential_fhrs;

            // Prerender all essential FHRs
            const container = document.getElementById('xsect-container');
            container.innerHTML = `<div class="loading-text">Pre-rendering ${fhrs.length} frames...</div>`;

            const body = {
                frames: fhrs.map(fhr => ({cycle: cycleKey, fhr})),
                start: [start.lat, start.lng],
                end: [end.lat, end.lng],
                style: product,
                y_axis: currentYAxis,
                vscale: parseFloat(vscale),
                y_top: parseInt(ytop),
                units: units,
                temp_cmap: tempCmap,
                anomaly: anomaly,
                model: 'hrrr',
            };
            const _mkrs = buildMarkersBody();
            if (_mkrs) body.markers = _mkrs;

            try {
                const res = await fetch('/api/prerender', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(body),
                });
                const data = await res.json();
                const sessionId = data.session_id;

                // Poll until done
                await new Promise((resolve, reject) => {
                    const pollId = setInterval(async () => {
                        try {
                            const pRes = await fetch('/api/progress');
                            const progress = await pRes.json();
                            const session = progress[sessionId];
                            if (session) {
                                container.innerHTML = `<div class="loading-text">Pre-rendering... ${session.pct}%</div>`;
                            }
                            if (!session || session.done) {
                                clearInterval(pollId);
                                resolve();
                            }
                        } catch (e) {
                            clearInterval(pollId);
                            reject(e);
                        }
                    }, 500);
                });

                // Fetch frame blobs into prerenderedFrames
                invalidatePrerender();
                for (const fhr of fhrs) {
                    try {
                        const frameRes = await fetch(`/api/frame?cycle=${cycleKey}&fhr=${fhr}&style=${product}` +
                            `&y_axis=${currentYAxis}&vscale=${vscale}&y_top=${ytop}&units=${units}` +
                            `&temp_cmap=${tempCmap}&anomaly=${anomaly ? 1 : 0}&model=hrrr` +
                            `&start_lat=${start.lat}&start_lon=${start.lng}&end_lat=${end.lat}&end_lon=${end.lng}`);
                        if (frameRes.ok) {
                            const blob = await frameRes.blob();
                            prerenderedFrames[fhr] = URL.createObjectURL(blob);
                        }
                    } catch (e) { /* skip frame */ }
                }

                // Set slider to essential FHRs range and start playback
                const slider = document.getElementById('fhr-slider');
                const fhrIdx = selectedFhrs.indexOf(fhrs[0]);
                if (fhrIdx >= 0) {
                    slider.value = fhrIdx;
                    slider.dispatchEvent(new Event('input'));
                }

                if (evt.evaluation_notes) showShowcaseNotes(evt.evaluation_notes);
                startPlayback();
            } catch (err) {
                container.innerHTML = `<div style="color:#f87171">Playback failed: ${err.message}</div>`;
            }
        };

        // =====================================================================
        // Settings: Marker visibility toggles
        // =====================================================================
        document.getElementById('toggle-city-markers').onchange = function() {
            const vis = this.checked ? 'visible' : 'none';
            ['city-clusters', 'city-cluster-count', 'city-points'].forEach(id => {
                if (map.getLayer(id)) map.setLayoutProperty(id, 'visibility', vis);
            });
        };
        document.getElementById('toggle-event-markers').onchange = function() {
            const vis = this.checked ? 'visible' : 'none';
            ['event-points', 'event-stars'].forEach(id => {
                if (map.getLayer(id)) map.setLayoutProperty(id, 'visibility', vis);
            });
        };
        document.getElementById('toggle-clustering').onchange = function() {
            // With Mapbox built-in clustering, toggle by changing clusterMaxZoom
            if (map.getSource('cities')) {
                // Re-create source with different cluster setting
                const data = _citiesGeoJSON;
                ['city-clusters', 'city-cluster-count', 'city-points'].forEach(id => {
                    if (map.getLayer(id)) map.removeLayer(id);
                });
                map.removeSource('cities');
                addCityLayers(data);
            }
        };

        // =====================================================================
        // Settings: Menu position (mobile only)
        // =====================================================================
        (function() {
            const sel = document.getElementById('menu-position-select');
            const settings = document.querySelectorAll('.mobile-only-setting');
            const isMob = window.matchMedia('(max-width: 768px)').matches || ('ontouchstart' in window && window.innerWidth < 900);
            // Show the setting only on mobile
            if (isMob) settings.forEach(s => s.style.display = '');
            // Restore saved preference
            const saved = localStorage.getItem('wxs-menu-pos');
            if (saved === 'top' && isMob) {
                document.body.classList.add('menu-top');
                sel.value = 'top';
            }
            sel.onchange = function() {
                if (this.value === 'top') {
                    document.body.classList.add('menu-top');
                    localStorage.setItem('wxs-menu-pos', 'top');
                } else {
                    document.body.classList.remove('menu-top');
                    localStorage.setItem('wxs-menu-pos', 'bottom');
                }
                map.resize();
            };
        })();

        // =====================================================================
        // Initialize everything
        // =====================================================================
        loadModels().then(() => loadCycles());
        loadCityMarkers();
        loadEventMarkers().then(() => populateEventCategories());

        // Mobile: start with sidebar collapsed so map is visible
        if (isMobile) {
            expandedPanel.classList.add('collapsed');
            iconTabs.forEach(t => t.classList.remove('active'));
        }
    </script>
</body>
</html>'''

# =============================================================================
# ROUTES
# =============================================================================

@app.route('/')
def index():
    return HTML_TEMPLATE.replace('%%MAPBOX_TOKEN%%', MAPBOX_TOKEN)

@app.route('/api/models')
def api_models():
    """List enabled models."""
    return jsonify({'models': model_registry.list_models()})

@app.route('/api/cycles')
def api_cycles():
    """Return available cycles for the dropdown. Supports ?model=hrrr."""
    mgr = get_manager_from_request() or data_manager
    # Keep cycle visibility fresh for clients polling this endpoint.
    try:
        mgr.scan_available_cycles()
    except Exception:
        pass
    return jsonify({
        'cycles': mgr.get_cycles_for_ui(),
        'model': mgr.model_name,
    })


@app.route('/api/climatology_status')
def api_climatology_status():
    """Return climatology availability for anomaly mode."""
    if not CLIMATOLOGY_DIR.exists():
        return jsonify({'available': False})
    # Scan for available climo files
    months = {}
    for npz in CLIMATOLOGY_DIR.glob('climo_*.npz'):
        parts = npz.stem.split('_')  # climo_01_00z_F06
        if len(parts) == 4:
            month = int(parts[1])
            init = parts[2]  # "00z"
            if month not in months:
                months[month] = set()
            months[month].add(init)
    # Convert sets to sorted lists
    months = {m: sorted(inits) for m, inits in sorted(months.items())}
    return jsonify({
        'available': len(months) > 0,
        'months': months,
        'anomaly_styles': sorted(ANOMALY_STYLES),
    })

@app.route('/api/status')
def api_status():
    """Return current memory/loading status. Supports ?model=."""
    mgr = get_manager_from_request() or data_manager
    return jsonify(mgr.get_loaded_status())

AUTO_UPDATE_STATUS_FILE = os.path.join(tempfile.gettempdir(), 'auto_update_status.json')

def _read_auto_update_status():
    """Read auto-update status file written by auto_update.py. Returns dict or None."""
    try:
        import os
        stat = os.stat(AUTO_UPDATE_STATUS_FILE)
        # Skip if stale (>5 min old)
        if time.time() - stat.st_mtime > 300:
            return None
        with open(AUTO_UPDATE_STATUS_FILE, 'r') as f:
            return json.loads(f.read())
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None


@app.route('/api/progress')
def api_progress():
    """Return all active progress operations."""
    progress_cleanup()
    now = time.time()
    result = {}
    for op_id, info in PROGRESS.items():
        elapsed = now - info['started']
        step = info['step']
        total = info['total']
        pct = round(100 * step / max(total, 1))

        # Compute rate and ETA from history
        rate = None  # items/sec
        eta = None   # seconds remaining
        hist = info.get('rate_history', [])
        last_step_at = info.get('last_step_at', info['started'])
        stalled = (now - last_step_at) > 10  # no progress for 10s
        if step > 0 and not info['done']:
            if stalled:
                # Use overall rate when stalled (more accurate long-term estimate)
                rate = step / elapsed if elapsed > 0 else None
            elif len(hist) >= 2:
                t0, s0 = hist[0]
                t1, s1 = hist[-1]
                dt = t1 - t0
                ds = s1 - s0
                if dt > 0 and ds > 0:
                    rate = ds / dt
            if rate and rate > 0:
                remaining = total - step
                eta = round(remaining / rate)

        entry = {
            'label': info['label'],
            'op': info['op'],
            'step': step,
            'total': total,
            'detail': info['detail'],
            'pct': pct,
            'elapsed': round(elapsed),
            'done': info['done'],
        }
        if rate is not None:
            entry['rate'] = round(rate, 2)
        if eta is not None:
            entry['eta'] = eta
        result[op_id] = entry

    # Inject auto-update progress from status file (written by auto_update.py)
    au = _read_auto_update_status()
    if au and au.get('models'):
        au_started = au.get('started', au.get('ts', now))
        au_elapsed = round(now - au_started)
        for model, ms in au['models'].items():
            op_id = f"autoupdate:{model}"
            step = ms.get('done', 0)
            total = ms.get('total', 0)
            if total <= 0:
                continue
            # Skip models that are done (no in-flight, all complete)
            if step >= total and not ms.get('in_flight'):
                continue
            pct = round(100 * step / max(total, 1))
            flying = ms.get('in_flight', [])
            last_ok = ms.get('last_ok')
            last_fail = ms.get('last_fail')

            # Build detail string like: "F05 OK — downloading F06, F07, F08"
            parts = []
            if last_ok:
                parts.append(f"{last_ok} OK")
            if last_fail:
                parts.append(f"{last_fail} FAIL")
            detail = ' · '.join(parts) if parts else 'Starting...'
            if flying:
                detail += f" \u2014 downloading {', '.join(flying)}"

            # Compute rate/ETA from elapsed time
            au_rate = None
            au_eta = None
            if step > 0 and au_elapsed > 0:
                au_rate = step / au_elapsed
                remaining = total - step
                if au_rate > 0:
                    au_eta = round(remaining / au_rate)

            entry = {
                'label': f"Auto-update {model.upper()} {ms.get('cycle', '')}",
                'op': 'autoupdate',
                'step': step,
                'total': total,
                'detail': detail,
                'pct': pct,
                'elapsed': au_elapsed,
                'done': False,
            }
            if au_rate is not None:
                entry['rate'] = round(au_rate, 3)
            if au_eta is not None:
                entry['eta'] = au_eta
            result[op_id] = entry

    return jsonify(result)

@app.route('/api/cancel', methods=['POST'])
@rate_limit
def api_cancel():
    """Cancel an active progress operation."""
    op_id = request.args.get('op_id', '')
    if not op_id:
        return jsonify({'error': 'op_id required'}), 400
    if op_id not in PROGRESS:
        return jsonify({'error': 'Operation not found'}), 404
    if PROGRESS[op_id].get('done'):
        return jsonify({'error': 'Operation already finished'}), 400
    cancel_request(op_id)
    logger.info(f"Cancel requested for {op_id}")
    return jsonify({'ok': True, 'op_id': op_id})

@app.route('/api/load', methods=['POST'])
@rate_limit
def api_load():
    """Load a forecast hour into memory."""
    cycle_key = request.args.get('cycle')
    fhr = request.args.get('fhr')

    if not cycle_key or fhr is None:
        return jsonify({'success': False, 'error': 'Missing cycle or fhr parameter'}), 400

    try:
        fhr = int(fhr)
    except ValueError:
        return jsonify({'success': False, 'error': 'Invalid fhr'}), 400

    mgr = get_manager_from_request() or data_manager
    result = mgr.load_forecast_hour(cycle_key, fhr)
    return jsonify(result)

@app.route('/api/load_cycle', methods=['POST'])
@rate_limit
def api_load_cycle():
    """Load an entire cycle (all FHRs) into memory."""
    cycle_key = request.args.get('cycle')

    if not cycle_key:
        return jsonify({'success': False, 'error': 'Missing cycle parameter'}), 400

    mgr = get_manager_from_request() or data_manager
    result = mgr.load_cycle(cycle_key)
    touch_cycle_access(cycle_key)
    return jsonify(result)

@app.route('/api/unload', methods=['POST'])
@rate_limit
def api_unload():
    """Unload a forecast hour from memory."""
    cycle_key = request.args.get('cycle')
    fhr = request.args.get('fhr')

    if not cycle_key or fhr is None:
        return jsonify({'success': False, 'error': 'Missing cycle or fhr parameter'}), 400

    try:
        fhr = int(fhr)
    except ValueError:
        return jsonify({'success': False, 'error': 'Invalid fhr'}), 400

    mgr = get_manager_from_request() or data_manager
    result = mgr.unload_forecast_hour(cycle_key, fhr)
    return jsonify(result)

def _parse_markers(args_or_data):
    """Parse POI markers from request args (dict-like) or POST data (dict).
    Supports: markers=[{lat,lon,label},...] JSON, or single marker_lat/marker_lon/marker_label.
    Returns (markers_list_or_None, legacy_marker_tuple_or_None, legacy_label_or_None).
    """
    import json as _json
    markers = None
    marker = None
    marker_label = None
    # Try JSON markers array first
    raw = args_or_data.get('markers')
    if raw:
        try:
            parsed = _json.loads(raw) if isinstance(raw, str) else raw
            if isinstance(parsed, list) and len(parsed) > 0:
                markers = [{'lat': float(m['lat']), 'lon': float(m['lon']),
                            'label': str(m.get('label', ''))} for m in parsed]
        except Exception:
            pass
    # Fallback: single marker params
    if not markers:
        try:
            m_lat = args_or_data.get('marker_lat')
            m_lon = args_or_data.get('marker_lon')
            if m_lat is not None and m_lon is not None:
                marker = (float(m_lat), float(m_lon))
                marker_label = str(args_or_data.get('marker_label', '') or '') or None
        except (ValueError, TypeError):
            pass
    return markers, marker, marker_label


@app.route('/api/xsect')
@rate_limit
def api_xsect():
    """Generate a cross-section image."""
    try:
        start = (float(request.args['start_lat']), float(request.args['start_lon']))
        end = (float(request.args['end_lat']), float(request.args['end_lon']))
        cycle_key = request.args.get('cycle')
        fhr = int(request.args.get('fhr', 0))
        style = request.args.get('style', 'wind_speed')
        y_axis = request.args.get('y_axis', 'pressure')  # 'pressure', 'height', or 'isentropic'
        vscale = float(request.args.get('vscale', 1.0))  # vertical exaggeration
        y_top = int(request.args.get('y_top', 100))  # top of plot in hPa
        dist_units = request.args.get('units', 'km')  # 'km' or 'mi'
    except (KeyError, ValueError) as e:
        return jsonify({'error': f'Invalid parameters: {e}'}), 400

    if not cycle_key:
        return jsonify({'error': 'Missing cycle parameter'}), 400

    # Validate parameters
    if y_axis not in ('pressure', 'height', 'isentropic'):
        y_axis = 'pressure'
    vscale = max(0.5, min(3.0, vscale))  # Clamp between 0.5x and 3x
    if y_top not in (100, 200, 300, 500, 700):
        y_top = 100  # Default to full atmosphere

    if dist_units not in ('km', 'mi'):
        dist_units = 'km'
    temp_cmap_param = request.args.get('temp_cmap', 'standard')
    if temp_cmap_param not in ('standard', 'green_purple', 'white_zero', 'nws_ndfd'):
        temp_cmap_param = 'standard'
    anomaly_param = request.args.get('anomaly', '0') == '1'
    markers, marker, marker_label = _parse_markers(request.args)

    # Lazy wrfnat download for smoke style — trigger background download if needed
    mgr = get_manager_from_request() or data_manager
    if style == 'smoke' and mgr.model_name == 'hrrr':
        downloading = _trigger_lazy_wrfnat_download('hrrr', cycle_key, fhr)
        if downloading:
            return jsonify({
                'error': 'Smoke data (wrfnat) is downloading in the background. This is a ~663MB file and may take 1-2 minutes. Please try again shortly.',
                'smoke_downloading': True,
            }), 202

    acquired = RENDER_SEMAPHORE.acquire(timeout=10)
    if not acquired:
        return jsonify({'error': 'Server busy, try again in a moment'}), 503
    try:
        buf = mgr.generate_cross_section(start, end, cycle_key, fhr, style, y_axis, vscale, y_top, units=dist_units, temp_cmap=temp_cmap_param, anomaly=anomaly_param, marker=marker, marker_label=marker_label, markers=markers)
    finally:
        RENDER_SEMAPHORE.release()
    if buf is None:
        return jsonify({'error': 'Failed to generate cross-section. Data may not be loaded.'}), 500

    touch_cycle_access(cycle_key)
    return send_file(buf, mimetype='image/png')

@app.route('/api/xsect_gif')
@rate_limit
def api_xsect_gif():
    """Generate an animated GIF of all loaded FHRs for a cycle."""
    try:
        start = (float(request.args['start_lat']), float(request.args['start_lon']))
        end = (float(request.args['end_lat']), float(request.args['end_lon']))
        cycle_key = request.args.get('cycle')
        style = request.args.get('style', 'wind_speed')
        y_axis = request.args.get('y_axis', 'pressure')
        vscale = float(request.args.get('vscale', 1.0))
        y_top = int(request.args.get('y_top', 100))
        dist_units = request.args.get('units', 'km')
    except (KeyError, ValueError) as e:
        return jsonify({'error': f'Invalid parameters: {e}'}), 400

    if not cycle_key:
        return jsonify({'error': 'Missing cycle parameter'}), 400
    if y_axis not in ('pressure', 'height', 'isentropic'):
        y_axis = 'pressure'
    vscale = max(0.5, min(3.0, vscale))
    if y_top not in (100, 200, 300, 500, 700):
        y_top = 100
    if dist_units not in ('km', 'mi'):
        dist_units = 'km'
    gif_temp_cmap = request.args.get('temp_cmap', 'standard')
    if gif_temp_cmap not in ('standard', 'green_purple', 'white_zero', 'nws_ndfd'):
        gif_temp_cmap = 'standard'
    gif_anomaly = request.args.get('anomaly', '0') == '1'
    fhr_min = request.args.get('fhr_min')
    fhr_max = request.args.get('fhr_max')

    mgr = get_manager_from_request() or data_manager

    # All loaded FHRs available for GIF (mmap makes loading all FHRs cheap)
    loaded_fhrs = sorted(fhr for ck, fhr in mgr.loaded_items
                         if ck == cycle_key)

    # Filter to requested FHR range if specified
    if fhr_min is not None:
        try:
            loaded_fhrs = [f for f in loaded_fhrs if f >= int(fhr_min)]
        except ValueError:
            pass
    if fhr_max is not None:
        try:
            loaded_fhrs = [f for f in loaded_fhrs if f <= int(fhr_max)]
        except ValueError:
            pass

    if len(loaded_fhrs) < 2:
        return jsonify({'error': f'Need at least 2 loaded FHRs in range for GIF (have {len(loaded_fhrs)})'}), 400

    # Try to use prerendered frames from FRAME_CACHE first
    model_name = request.args.get('model', 'hrrr').lower()
    cached_frames = []
    uncached_fhrs = []
    for fhr in loaded_fhrs:
        ck = frame_cache_key(model_name, cycle_key, fhr, style, start, end, y_axis, vscale, y_top, dist_units, gif_temp_cmap, gif_anomaly)
        png = frame_cache_get(ck)
        if png:
            cached_frames.append((fhr, png))
        else:
            uncached_fhrs.append(fhr)

    # If all frames are prerendered, skip matplotlib entirely
    if not uncached_fhrs:
        frames = []
        for fhr, png in sorted(cached_frames, key=lambda x: x[0]):
            frames.append(imageio.imread(io.BytesIO(png)))
    else:
        # Lock terrain to first FHR so elevation doesn't jitter between frames
        terrain_data = mgr.get_terrain_data(start, end, cycle_key, loaded_fhrs[0], style)

        # Render uncached frames in parallel via persistent process pool
        pool_config = mgr.get_render_pool_config()
        project_dir = str(Path(__file__).resolve().parent.parent)
        from tools.render_worker import render_frame
        rendered_pngs = {}  # fhr -> png bytes

        try:
            pool = _get_render_pool(pool_config, project_dir)
            futures = {}
            for fhr in uncached_fhrs:
                info = mgr.get_render_info(cycle_key, fhr)
                if info is None:
                    continue
                cache_k = frame_cache_key(model_name, cycle_key, fhr, style, start, end, y_axis, vscale, y_top, dist_units, gif_temp_cmap, gif_anomaly)
                worker_args = (
                    info['grib_file'], info['engine_key'], start, end, style,
                    y_axis, vscale, y_top, dist_units, gif_temp_cmap, gif_anomaly,
                    None, None, None, info['metadata'], terrain_data,
                )
                futures[pool.submit(render_frame, worker_args)] = (fhr, cache_k)

            for future in as_completed(futures):
                fhr, cache_k = futures[future]
                try:
                    engine_key, png_bytes = future.result(timeout=60)
                    if png_bytes:
                        rendered_pngs[fhr] = png_bytes
                        frame_cache_put(cache_k, png_bytes)
                except Exception:
                    pass
        except Exception as e:
            logger.error(f"GIF render pool error: {e}, falling back to sequential")
            # Fallback: sequential rendering in main process
            acquired = RENDER_SEMAPHORE.acquire(timeout=90)
            if not acquired:
                return jsonify({'error': 'Server busy, try again in a moment'}), 503
            try:
                for fhr in uncached_fhrs:
                    buf = mgr.generate_cross_section(start, end, cycle_key, fhr, style, y_axis, vscale, y_top, units=dist_units, terrain_data=terrain_data, temp_cmap=gif_temp_cmap, anomaly=gif_anomaly)
                    if buf is not None:
                        rendered_pngs[fhr] = buf.getvalue()
            finally:
                RENDER_SEMAPHORE.release()

        # Assemble all frames (cached + freshly rendered) sorted by FHR
        all_pngs = {fhr: png for fhr, png in cached_frames}
        all_pngs.update(rendered_pngs)
        frames = []
        for fhr in loaded_fhrs:
            png = all_pngs.get(fhr)
            if png:
                frames.append(imageio.imread(io.BytesIO(png) if isinstance(png, bytes) else png))

    if len(frames) < 2:
        return jsonify({'error': 'Failed to generate enough frames'}), 500

    # Speed: 1x = 250ms (fast), 0.75x = 500ms, 0.5x = 1000ms, 0.25x = 2000ms
    SPEED_MS = {'1': 250, '0.75': 500, '0.5': 1000, '0.25': 2000}
    speed_key = request.args.get('speed', '0.5')
    frame_ms = SPEED_MS.get(speed_key, 1000)

    # Use Pillow with disposal=2 (replace each frame) to prevent flickering on Discord
    gif_buf = io.BytesIO()
    pil_frames = [Image.fromarray(f) for f in frames]
    pil_frames[0].save(
        gif_buf, format='GIF', save_all=True,
        append_images=pil_frames[1:],
        duration=frame_ms, loop=0, disposal=2
    )
    gif_buf.seek(0)

    touch_cycle_access(cycle_key)
    return send_file(gif_buf, mimetype='image/gif', download_name=f'xsect_{cycle_key}_{style}.gif')

# =============================================================================
# V1 GIF ENDPOINT (agent-friendly alias for /api/xsect_gif)
# =============================================================================

@app.route('/api/v1/cross-section/gif')
@rate_limit
def api_v1_cross_section_gif():
    """Generate animated GIF of cross-section across all loaded FHRs.

    Agent-friendly endpoint: accepts 'product' param (mapped to style),
    auto-resolves cycle from model if not specified.
    """
    # Map 'product' to 'style' for consistency with v1 API
    product = request.args.get('product', request.args.get('style', 'wind_speed'))
    style = PRODUCT_TO_STYLE.get(product, product)

    # Auto-resolve cycle if not provided
    cycle_key = request.args.get('cycle')
    if not cycle_key:
        mgr = get_manager_from_request() or data_manager
        # Use latest cycle that has loaded FHRs
        avail = sorted(
            set(ck for ck, fhr in mgr.loaded_items),
            reverse=True
        )
        if avail:
            cycle_key = avail[0]
        else:
            return jsonify({'error': 'No cycles loaded'}), 404

    # Forward to the existing GIF handler with style and cycle injected
    from werkzeug.datastructures import ImmutableMultiDict
    args = dict(request.args)
    args['style'] = style
    args['cycle'] = cycle_key
    args.pop('product', None)
    request.args = ImmutableMultiDict(args)
    return api_xsect_gif()


# =============================================================================
# MULTI-PANEL COMPARISON API
# =============================================================================

def comparison_cache_key(mode, params_key, start, end, y_axis, y_top, units, temp_cmap):
    """Deterministic cache key for a comparison image."""
    return f"cmp:{mode}:{params_key}:{start[0]:.4f},{start[1]:.4f}:{end[0]:.4f},{end[1]:.4f}:{y_axis}:{y_top}:{units}:{temp_cmap}"


@app.route('/api/v1/comparison')
@rate_limit
def api_v1_comparison():
    """Generate a multi-panel comparison cross-section PNG.

    Modes: model, temporal, product, cycle.
    """
    try:
        for p in ('start_lat', 'start_lon', 'end_lat', 'end_lon', 'mode'):
            if p not in request.args:
                raise KeyError(p)
        start = (float(request.args['start_lat']), float(request.args['start_lon']))
        end = (float(request.args['end_lat']), float(request.args['end_lon']))
    except KeyError as e:
        return jsonify({'error': f'Missing required parameter: {e.args[0]}',
                        'usage': 'Required: mode, start_lat, start_lon, end_lat, end_lon'}), 400
    except ValueError:
        return jsonify({'error': 'Coordinates must be numeric'}), 400

    mode = request.args['mode']
    if mode not in ('model', 'temporal', 'product', 'cycle'):
        return jsonify({'error': f'Invalid mode: {mode}. Use: model, temporal, product, cycle'}), 400

    # Common params
    product = request.args.get('product', 'temperature')
    style = PRODUCT_TO_STYLE.get(product, product)
    cycle_raw = request.args.get('cycle', 'latest')
    try:
        fhr = int(request.args.get('fhr', 0))
    except ValueError:
        fhr = 0
    model_name = request.args.get('model', 'hrrr').lower()
    y_axis = request.args.get('y_axis', 'pressure')
    if y_axis not in ('pressure', 'height', 'isentropic'):
        y_axis = 'pressure'
    try:
        y_top = int(request.args.get('y_top', 100))
    except ValueError:
        y_top = 100
    if y_top not in (100, 200, 300, 500, 700):
        y_top = 100
    units = request.args.get('units', 'km')
    if units not in ('km', 'mi'):
        units = 'km'
    temp_cmap = request.args.get('temp_cmap', 'standard')
    if temp_cmap not in ('standard', 'green_purple', 'white_zero', 'nws_ndfd'):
        temp_cmap = 'standard'
    markers, marker, marker_label = _parse_markers(request.args)

    panels = []
    shared_colorbar = True

    try:
        if mode == 'model':
            from datetime import datetime, timedelta
            models_raw = request.args.get('models', '')
            model_list = [m.strip().lower() for m in models_raw.split(',') if m.strip()]
            if len(model_list) < 2:
                return jsonify({'error': 'model mode requires models param with 2+ comma-separated models'}), 400

            # Resolve the primary model's cycle to compute valid time
            try:
                primary_mgr = model_registry.get(model_list[0])
            except ValueError:
                return jsonify({'error': f'Unknown model: {model_list[0]}'}), 400
            primary_cycle = primary_mgr.resolve_cycle(cycle_raw, fhr)
            if not primary_cycle:
                return jsonify({'error': f'No data for {model_list[0]} with F{fhr:02d}'}), 404

            # Parse primary init time to compute valid time
            def parse_cycle_init(ck):
                m = __import__('re').match(r'(\d{8})_(\d{2})z', ck)
                if not m:
                    return None
                return datetime.strptime(m.group(1) + m.group(2), '%Y%m%d%H')

            primary_init = parse_cycle_init(primary_cycle)
            if primary_init:
                valid_time = primary_init + timedelta(hours=fhr)

            for m_name in model_list:
                try:
                    mgr = model_registry.get(m_name)
                except ValueError:
                    return jsonify({'error': f'Unknown model: {m_name}'}), 400

                m_cycle = None
                m_fhr = fhr

                # Check if this model has the exact requested cycle
                with mgr._lock:
                    has_exact = any(c['cycle_key'] == primary_cycle for c in mgr.available_cycles)
                if has_exact:
                    m_cycle = primary_cycle
                    m_fhr = fhr

                # If not, find the best cycle that can match the valid time
                if not m_cycle and primary_init:
                    best_cycle = None
                    best_fhr = None
                    with mgr._lock:
                        for c in mgr.available_cycles:
                            c_init = parse_cycle_init(c['cycle_key'])
                            if not c_init:
                                continue
                            needed_fhr = int((valid_time - c_init).total_seconds() / 3600)
                            if needed_fhr < 0:
                                continue
                            if needed_fhr in c.get('available_fhrs', []):
                                if best_cycle is None or needed_fhr < best_fhr:
                                    best_cycle = c['cycle_key']
                                    best_fhr = needed_fhr
                    if best_cycle:
                        m_cycle = best_cycle
                        m_fhr = best_fhr

                if not m_cycle:
                    return jsonify({'error': f'No {m_name.upper()} data for valid time {valid_time.strftime("%HZ %b %d") if primary_init else "unknown"}'}), 404
                if not mgr.ensure_loaded(m_cycle, m_fhr):
                    return jsonify({'error': f'Failed to load {m_name} {m_cycle} F{m_fhr:02d}'}), 500
                pd = mgr.get_panel_data(start, end, m_cycle, m_fhr, style)
                if pd is None:
                    return jsonify({'error': f'Failed to get data for {m_name}'}), 500
                # Label: MODEL — Init HHz, F##, Valid HHz Mon DD
                c_init = parse_cycle_init(m_cycle)
                if c_init:
                    m_valid = c_init + timedelta(hours=m_fhr)
                    pd['label'] = (f'{m_name.upper()} \u2014 Init {c_init.strftime("%HZ %b %d")}, '
                                   f'F{m_fhr:02d}, Valid {m_valid.strftime("%HZ %b %d")}')
                else:
                    pd['label'] = m_name.upper()
                panels.append(pd)

        elif mode == 'temporal':
            fhrs_raw = request.args.get('fhrs', '')
            fhr_list = [int(f.strip()) for f in fhrs_raw.split(',') if f.strip()]
            if len(fhr_list) < 2:
                return jsonify({'error': 'temporal mode requires fhrs param with 2+ comma-separated FHRs'}), 400

            mgr = model_registry.get(model_name)
            cycle_key = mgr.resolve_cycle(cycle_raw, fhr_list[0])
            if not cycle_key:
                return jsonify({'error': f'No data for {model_name}'}), 404

            from datetime import datetime, timedelta
            for f in fhr_list:
                if not mgr.ensure_loaded(cycle_key, f):
                    return jsonify({'error': f'Failed to load {cycle_key} F{f:02d}'}), 500
                pd = mgr.get_panel_data(start, end, cycle_key, f, style)
                if pd is None:
                    return jsonify({'error': f'Failed to get data for F{f:02d}'}), 500
                meta = pd['metadata']
                try:
                    init_dt = datetime.strptime(f"{meta['init_date']}{meta['init_hour']}", "%Y%m%d%H")
                    valid_dt = init_dt + timedelta(hours=f)
                    pd['label'] = f'F{f:02d} (Valid {valid_dt.strftime("%HZ %b %d")})'
                except:
                    pd['label'] = f'F{f:02d}'
                panels.append(pd)

        elif mode == 'product':
            products_raw = request.args.get('products', '')
            product_list = [p.strip() for p in products_raw.split(',') if p.strip()]
            if len(product_list) < 2:
                return jsonify({'error': 'product mode requires products param with 2+ comma-separated products'}), 400

            shared_colorbar = False  # Different products need different colorbars
            mgr = model_registry.get(model_name)
            cycle_key = mgr.resolve_cycle(cycle_raw, fhr)
            if not cycle_key:
                return jsonify({'error': f'No data for {model_name}'}), 404
            if not mgr.ensure_loaded(cycle_key, fhr):
                return jsonify({'error': f'Failed to load {cycle_key} F{fhr:02d}'}), 500

            # Product display names
            PRODUCT_NAMES = {
                'wind_speed': 'Wind Speed', 'rh': 'RH', 'temp': 'Temperature',
                'fire_wx': 'Fire Wx', 'omega': 'Omega', 'theta_e': 'θe',
                'smoke': 'Smoke', 'vorticity': 'Vorticity', 'shear': 'Shear',
                'cloud_total': 'Cloud', 'lapse_rate': 'Lapse Rate', 'wetbulb': 'Wet Bulb',
                'vpd': 'VPD', 'dewpoint_dep': 'T-Td', 'pv': 'PV',
            }

            for prod in product_list:
                s = PRODUCT_TO_STYLE.get(prod, prod)
                pd = mgr.get_panel_data(start, end, cycle_key, fhr, s)
                if pd is None:
                    return jsonify({'error': f'Failed to get data for product {prod}'}), 500
                pd['style'] = s
                pd['label'] = PRODUCT_NAMES.get(s, prod)
                panels.append(pd)

        elif mode == 'cycle':
            cycles_raw = request.args.get('cycles', '')
            cycle_list = [c.strip() for c in cycles_raw.split(',') if c.strip()]
            if len(cycle_list) < 2:
                return jsonify({'error': 'cycle mode requires cycles param with 2+ comma-separated cycles'}), 400
            cycle_match = request.args.get('cycle_match', 'same_fhr')

            mgr = model_registry.get(model_name)
            from datetime import datetime, timedelta

            for i, ck in enumerate(cycle_list):
                this_fhr = fhr
                if cycle_match == 'valid_time' and i > 0:
                    # Match valid time: compute equivalent FHR
                    try:
                        base_cycle = next(c for c in mgr.available_cycles if c['cycle_key'] == cycle_list[0])
                        this_cycle = next(c for c in mgr.available_cycles if c['cycle_key'] == ck)
                        base_init = base_cycle['init_dt']
                        this_init = this_cycle['init_dt']
                        hour_diff = int((base_init - this_init).total_seconds() / 3600)
                        this_fhr = fhr + hour_diff
                    except:
                        pass

                if not mgr.ensure_loaded(ck, this_fhr):
                    return jsonify({'error': f'Failed to load {ck} F{this_fhr:02d}'}), 500
                pd = mgr.get_panel_data(start, end, ck, this_fhr, style)
                if pd is None:
                    return jsonify({'error': f'Failed to get data for {ck}'}), 500
                # Label: show cycle init time
                try:
                    cycle_info = next(c for c in mgr.available_cycles if c['cycle_key'] == ck)
                    pd['label'] = f'{cycle_info["init_dt"].strftime("%HZ %b %d")} Init'
                except:
                    pd['label'] = ck
                panels.append(pd)

    except Exception as e:
        import traceback
        logger.error(f"Comparison error: {e}\n{traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500

    if len(panels) < 2:
        return jsonify({'error': 'Need at least 2 panels for comparison'}), 400

    # Determine layout
    n = len(panels)
    if mode == 'product':
        layout = {2: '2x1', 3: '3x1', 4: '2x2'}.get(n, '2x1')
    else:
        layout = {2: '1x2', 3: '1x3', 4: '1x4'}.get(n, '1x2')

    # Use the first model's engine for rendering
    first_model = panels[0]['metadata']['model'].lower()
    try:
        render_mgr = model_registry.get(first_model)
    except:
        render_mgr = data_manager
    engine = render_mgr.xsect

    if engine is None:
        return jsonify({'error': 'Render engine not initialized'}), 500

    acquired = RENDER_SEMAPHORE.acquire(timeout=90)
    if not acquired:
        return jsonify({'error': 'Server busy rendering, try again'}), 503
    try:
        png_bytes = engine.render_multi_panel(
            panels, layout=layout, shared_colorbar=shared_colorbar,
            dpi=100, y_axis=y_axis, y_top=y_top, units=units,
            temp_cmap=temp_cmap, marker=marker, marker_label=marker_label, markers=markers)
    finally:
        RENDER_SEMAPHORE.release()

    if png_bytes is None:
        return jsonify({'error': 'Render failed'}), 500

    return send_file(io.BytesIO(png_bytes), mimetype='image/png')


@app.route('/api/v1/comparison/gif')
@rate_limit
def api_v1_comparison_gif():
    """Generate animated GIF of multi-panel comparison across FHRs.

    Works with mode=model and mode=product (FHR is the animation variable).
    """
    mode = request.args.get('mode', '')
    if mode not in ('model', 'product'):
        return jsonify({'error': 'GIF comparison only supports mode=model or mode=product'}), 400

    try:
        start = (float(request.args['start_lat']), float(request.args['start_lon']))
        end = (float(request.args['end_lat']), float(request.args['end_lon']))
    except (KeyError, ValueError) as e:
        return jsonify({'error': f'Invalid parameters: {e}'}), 400

    try:
        fhr_min = int(request.args.get('fhr_min', 0))
        fhr_max = int(request.args.get('fhr_max', 48))
    except ValueError:
        fhr_min, fhr_max = 0, 48

    # Build the base args (everything except fhr) and iterate over FHRs
    from werkzeug.datastructures import ImmutableMultiDict

    # Determine which FHRs are available
    model_name = request.args.get('model', 'hrrr').lower()
    mgr = model_registry.get(model_name)
    cycle_raw = request.args.get('cycle', 'latest')
    cycle_key = mgr.resolve_cycle(cycle_raw, fhr_min)
    if not cycle_key:
        return jsonify({'error': 'No data available'}), 404

    available_fhrs = sorted(set(
        fhr for ck, fhr in mgr.loaded_items
        if ck == cycle_key and fhr_min <= fhr <= fhr_max
    ))

    if len(available_fhrs) < 2:
        return jsonify({'error': f'Need at least 2 FHRs in range [{fhr_min}, {fhr_max}]'}), 400

    # Gather panel data for all FHRs first (fast — reads from mmap), then render in parallel
    import imageio
    from PIL import Image as PILImage

    base_args = dict(request.args)
    y_axis = base_args.get('y_axis', 'pressure')
    y_top = int(base_args.get('y_top', 100))
    units = base_args.get('units', 'km')
    temp_cmap = base_args.get('temp_cmap', 'standard')

    # Phase 1: Gather panel data for every FHR (sequential, fast from mmap)
    per_fhr_panels = {}  # fhr -> (result_panels, layout, shared_cb)
    for fhr in available_fhrs:
        result_panels = []

        if mode == 'model':
            models_raw = base_args.get('models', '')
            model_list = [m.strip().lower() for m in models_raw.split(',') if m.strip()]
            for m in model_list:
                m_mgr = model_registry.get(m)
                m_ck = m_mgr.resolve_cycle(cycle_raw, fhr)
                if m_ck and m_mgr.ensure_loaded(m_ck, fhr):
                    pd = m_mgr.get_panel_data(start, end, m_ck, fhr,
                                               PRODUCT_TO_STYLE.get(base_args.get('product', 'temperature'), 'temperature'))
                    if pd:
                        pd['label'] = m.upper()
                        result_panels.append(pd)

        elif mode == 'product':
            products_raw = base_args.get('products', '')
            product_list = [p.strip() for p in products_raw.split(',') if p.strip()]
            if mgr.ensure_loaded(cycle_key, fhr):
                for prod in product_list:
                    s = PRODUCT_TO_STYLE.get(prod, prod)
                    pd = mgr.get_panel_data(start, end, cycle_key, fhr, s)
                    if pd:
                        pd['style'] = s
                        pd['label'] = prod
                        result_panels.append(pd)

        if len(result_panels) >= 2:
            n = len(result_panels)
            shared_cb = (mode != 'product')
            layout = {2: '2x1', 3: '3x1', 4: '2x2'}.get(n, '2x1') if mode == 'product' else {2: '1x2', 3: '1x3', 4: '1x4'}.get(n, '1x2')
            per_fhr_panels[fhr] = (result_panels, layout, shared_cb)

    # Phase 2: Render multi-panel composites in parallel via process pool
    frames = []
    if per_fhr_panels:
        pool_config = mgr.get_render_pool_config()
        project_dir = str(Path(__file__).resolve().parent.parent)
        from tools.render_worker import render_multi_panel as render_mp

        rendered = {}  # fhr -> png bytes
        try:
            pool = _get_render_pool(pool_config, project_dir)
            futures = {}
            for fhr, (panels, layout, shared_cb) in per_fhr_panels.items():
                render_kwargs = dict(layout=layout, shared_colorbar=shared_cb,
                                     dpi=100, y_axis=y_axis, y_top=y_top,
                                     units=units, temp_cmap=temp_cmap)
                fut = pool.submit(render_mp, (panels, render_kwargs))
                futures[fut] = fhr

            for future in as_completed(futures):
                fhr = futures[future]
                try:
                    png = future.result(timeout=60)
                    if png:
                        rendered[fhr] = png
                except Exception:
                    pass
        except Exception as e:
            logger.error(f"Comparison GIF pool error: {e}, falling back to sequential")
            # Fallback: sequential rendering in main process
            acquired = RENDER_SEMAPHORE.acquire(timeout=90)
            if not acquired:
                return jsonify({'error': 'Server busy'}), 503
            try:
                for fhr, (panels, layout, shared_cb) in per_fhr_panels.items():
                    try:
                        eng = model_registry.get(panels[0]['metadata']['model'].lower()).xsect
                    except Exception:
                        eng = data_manager.xsect
                    png = eng.render_multi_panel(
                        panels, layout=layout, shared_colorbar=shared_cb,
                        dpi=100, y_axis=y_axis, y_top=y_top,
                        units=units, temp_cmap=temp_cmap)
                    if png:
                        rendered[fhr] = png
            finally:
                RENDER_SEMAPHORE.release()

        # Assemble frames sorted by FHR
        for fhr in available_fhrs:
            if fhr in rendered:
                frames.append(imageio.imread(io.BytesIO(rendered[fhr])))

    if len(frames) < 2:
        return jsonify({'error': 'Failed to generate enough frames'}), 500

    SPEED_MS = {'1': 250, '0.75': 500, '0.5': 1000, '0.25': 2000}
    speed_key = request.args.get('speed', '0.5')
    frame_ms = SPEED_MS.get(speed_key, 1000)

    gif_buf = io.BytesIO()
    pil_frames = [PILImage.fromarray(f) for f in frames]
    pil_frames[0].save(
        gif_buf, format='GIF', save_all=True,
        append_images=pil_frames[1:],
        duration=frame_ms, loop=0, disposal=2
    )
    gif_buf.seek(0)
    return send_file(gif_buf, mimetype='image/gif',
                     download_name=f'comparison_{mode}.gif')


# =============================================================================
# FRAME PRERENDER + CACHED FRAME API
# =============================================================================

@app.route('/api/prerender', methods=['POST'])
@rate_limit
def api_prerender():
    """Batch prerender frames for slider/comparison. Returns session_id for progress polling.

    POST JSON: {frames: [{cycle, fhr}, ...], start: [lat, lon], end: [lat, lon],
                style, y_axis, vscale, y_top, units, temp_cmap, anomaly, model}
    """
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Missing JSON body'}), 400

    try:
        frames = data['frames']  # [{cycle: str, fhr: int}, ...]
        start = tuple(data['start'])
        end = tuple(data['end'])
    except (KeyError, TypeError) as e:
        return jsonify({'error': f'Missing required field: {e}'}), 400

    style = data.get('style', 'temperature')
    y_axis = data.get('y_axis', 'pressure')
    vscale = float(data.get('vscale', 1.0))
    y_top = int(data.get('y_top', 100))
    units = data.get('units', 'km')
    temp_cmap = data.get('temp_cmap', 'standard')
    anomaly = bool(data.get('anomaly', False))
    model = data.get('model', 'hrrr')
    markers, marker, marker_label = _parse_markers(data)

    session_id = f"prerender:{int(time.time() * 1000)}"

    def _render_batch():
        mgr = model_registry.get(model)
        if not mgr:
            progress_update(session_id, 0, 1, "Unknown model", label="Pre-render failed")
            progress_done(session_id)
            return

        total = len(frames)
        progress_update(session_id, 0, total, "Starting...", label=f"Pre-rendering {total} frames")

        # Lock terrain to first frame for consistency
        first = frames[0]
        try:
            terrain_data = mgr.get_terrain_data(start, end, first['cycle'], first['fhr'], style)
        except Exception:
            terrain_data = None

        # Ensure all data is loaded first (sequential, fast from mmap cache)
        render_frames = []
        rendered = [0]  # mutable for closure
        for frame in frames:
            ck = frame['cycle']
            fhr = int(frame['fhr'])
            cache_key = frame_cache_key(model, ck, fhr, style, start, end, y_axis, vscale, y_top, units, temp_cmap, anomaly)

            if frame_cache_get(cache_key) is not None:
                rendered[0] += 1
                progress_update(session_id, rendered[0], total, f"F{fhr:02d} (cached)")
                continue

            try:
                mgr.ensure_loaded(ck, fhr)
                render_frames.append((ck, fhr, cache_key))
            except Exception:
                rendered[0] += 1
                progress_update(session_id, rendered[0], total, f"F{fhr:02d} load failed")

        if not render_frames:
            progress_done(session_id)
            return

        # Build args for multiprocess rendering — each worker gets everything it needs
        pool_config = mgr.get_render_pool_config()
        project_dir = str(Path(__file__).resolve().parent.parent)
        worker_args = []
        fhr_to_cache_key = {}
        for ck, fhr, cache_key in render_frames:
            info = mgr.get_render_info(ck, fhr)
            if info is None:
                rendered[0] += 1
                progress_update(session_id, rendered[0], total, f"F{fhr:02d} no data")
                continue
            fhr_to_cache_key[info['engine_key']] = (fhr, cache_key)
            worker_args.append((
                info['grib_file'], info['engine_key'], start, end, style,
                y_axis, vscale, y_top, units, temp_cmap, anomaly,
                marker, marker_label, markers, info['metadata'], terrain_data,
            ))

        if not worker_args:
            progress_done(session_id)
            return

        # Multiprocess render — persistent pool, each worker has its own GIL
        from tools.render_worker import render_frame
        try:
            pool = _get_render_pool(pool_config, project_dir)
            futures = {pool.submit(render_frame, args): args for args in worker_args}
            for future in as_completed(futures):
                try:
                    engine_key, png_bytes = future.result(timeout=60)
                except Exception as e:
                    logger.error(f"Render worker error: {e}")
                    rendered[0] += 1
                    progress_update(session_id, rendered[0], total, "worker error")
                    continue

                fhr, cache_key = fhr_to_cache_key.get(engine_key, (engine_key, None))
                rendered[0] += 1
                if png_bytes and cache_key:
                    frame_cache_put(cache_key, png_bytes)
                    progress_update(session_id, rendered[0], total, f"F{fhr:02d} rendered")
                else:
                    progress_update(session_id, rendered[0], total, f"F{fhr:02d} failed")

                if is_cancelled(session_id):
                    for f in futures:
                        f.cancel()
                    logger.info(f"Pre-render CANCELLED at {rendered[0]}/{total}")
                    PROGRESS[session_id]['detail'] = 'Cancelled'
                    break
        except Exception as e:
            logger.error(f"Process pool error: {e}, falling back to threaded render")
            # Kill the broken pool so next prerender creates a fresh one
            shutdown_render_pool()
            # Fallback to single-threaded if process pool fails
            for ck, fhr, cache_key in render_frames:
                if is_cancelled(session_id):
                    break
                try:
                    buf = mgr.generate_cross_section(
                        start, end, ck, fhr, style, y_axis, vscale, y_top,
                        units=units, terrain_data=terrain_data,
                        temp_cmap=temp_cmap, anomaly=anomaly,
                        marker=marker, marker_label=marker_label, markers=markers
                    )
                    if buf:
                        frame_cache_put(cache_key, buf.getvalue())
                except Exception:
                    pass
                rendered[0] += 1
                progress_update(session_id, rendered[0], total, f"F{fhr:02d} (fallback)")

        progress_done(session_id)
        CANCEL_FLAGS.pop(session_id, None)

    threading.Thread(target=_render_batch, daemon=True).start()

    return jsonify({
        'session_id': session_id,
        'total': len(frames),
        'status': 'rendering',
    })


@app.route('/api/frame')
@rate_limit
def api_frame():
    """Get a single cross-section frame. Checks prerender cache first, falls back to live render."""
    try:
        start = (float(request.args['start_lat']), float(request.args['start_lon']))
        end = (float(request.args['end_lat']), float(request.args['end_lon']))
        cycle_key = request.args.get('cycle')
        fhr = int(request.args.get('fhr', 0))
        style = request.args.get('style', 'wind_speed')
        y_axis = request.args.get('y_axis', 'pressure')
        vscale = float(request.args.get('vscale', 1.0))
        y_top = int(request.args.get('y_top', 100))
        dist_units = request.args.get('units', 'km')
        temp_cmap = request.args.get('temp_cmap', 'standard')
        anomaly = request.args.get('anomaly', '0') == '1'
        model = request.args.get('model', 'hrrr')
    except (KeyError, ValueError) as e:
        return jsonify({'error': f'Invalid parameters: {e}'}), 400

    if not cycle_key:
        return jsonify({'error': 'Missing cycle parameter'}), 400

    # Check cache first
    cache_key = frame_cache_key(model, cycle_key, fhr, style, start, end, y_axis, vscale, y_top, dist_units, temp_cmap, anomaly)
    cached = frame_cache_get(cache_key)
    if cached:
        return send_file(io.BytesIO(cached), mimetype='image/png')

    # Fall back to live render (same as /api/xsect)
    vscale = max(0.5, min(3.0, vscale))
    if y_axis not in ('pressure', 'height', 'isentropic'):
        y_axis = 'pressure'
    if y_top not in (100, 200, 300, 500, 700):
        y_top = 100
    if dist_units not in ('km', 'mi'):
        dist_units = 'km'
    if temp_cmap not in ('standard', 'green_purple', 'white_zero', 'nws_ndfd'):
        temp_cmap = 'standard'

    acquired = RENDER_SEMAPHORE.acquire(timeout=10)
    if not acquired:
        return jsonify({'error': 'Server busy, try again in a moment'}), 503
    mgr = model_registry.get(model) or data_manager
    try:
        buf = mgr.generate_cross_section(start, end, cycle_key, fhr, style, y_axis, vscale, y_top, units=dist_units, temp_cmap=temp_cmap, anomaly=anomaly)
    finally:
        RENDER_SEMAPHORE.release()
    if buf is None:
        return jsonify({'error': 'Failed to generate frame. Data may not be loaded.'}), 500

    # Cache the result for future requests
    frame_cache_put(cache_key, buf.getvalue())
    buf.seek(0)
    return send_file(buf, mimetype='image/png')


# =============================================================================
# v1 API — agent-friendly endpoints with smart defaults
# =============================================================================

@app.route('/api/v1/cross-section')
@rate_limit
def api_v1_cross_section():
    """Generate a cross-section PNG. Defaults to latest cycle, F00, temperature."""
    try:
        for p in ('start_lat', 'start_lon', 'end_lat', 'end_lon'):
            if p not in request.args:
                raise KeyError(p)
        start = (float(request.args['start_lat']), float(request.args['start_lon']))
        end = (float(request.args['end_lat']), float(request.args['end_lon']))
    except KeyError as e:
        return jsonify({
            'error': f'Missing required parameter: {e.args[0]}',
            'usage': 'Required: start_lat, start_lon, end_lat, end_lon',
            'example': '/api/v1/cross-section?start_lat=39.74&start_lon=-104.99&end_lat=41.88&end_lon=-87.63',
        }), 400
    except ValueError:
        return jsonify({
            'error': 'Coordinates must be numeric (e.g. start_lat=39.74)',
        }), 400

    product = request.args.get('product', 'temperature')
    cycle_raw = request.args.get('cycle', 'latest')
    try:
        fhr = int(request.args.get('fhr', 0))
    except ValueError:
        fhr = 0
    y_axis = request.args.get('y_axis', 'pressure')
    if y_axis not in ('pressure', 'height', 'isentropic'):
        y_axis = 'pressure'
    try:
        y_top = int(request.args.get('y_top', 100))
    except ValueError:
        y_top = 100
    if y_top not in (100, 200, 300, 500, 700):
        y_top = 100
    units = request.args.get('units', 'km')
    if units not in ('km', 'mi'):
        units = 'km'

    # Map product name to internal style
    style = PRODUCT_TO_STYLE.get(product)
    if style is None:
        return jsonify({
            'error': f'Unknown product: {product}',
            'available': [p['id'] for p in PRODUCTS_INFO],
        }), 400

    mgr = get_manager_from_request() or data_manager

    # Resolve cycle
    cycle_key = mgr.resolve_cycle(cycle_raw, fhr)
    if not cycle_key:
        return jsonify({'error': f'No data available with forecast hour F{fhr:02d}'}), 404

    # Auto-load if needed (mmap = ~14ms, GRIB = ~30s)
    if not mgr.ensure_loaded(cycle_key, fhr):
        return jsonify({'error': f'Failed to load {cycle_key} F{fhr:02d}'}), 500

    markers, marker, marker_label = _parse_markers(request.args)
    acquired = RENDER_SEMAPHORE.acquire(timeout=90)
    if not acquired:
        return jsonify({'error': 'Server busy rendering other requests, try again in a moment'}), 503
    try:
        buf = mgr.generate_cross_section(
            start, end, cycle_key, fhr, style, y_axis, 1.0, y_top, units=units, marker=marker, marker_label=marker_label, markers=markers)
    finally:
        RENDER_SEMAPHORE.release()

    if buf is None:
        return jsonify({'error': 'Render failed'}), 500

    touch_cycle_access(cycle_key)
    return send_file(buf, mimetype='image/png')


@app.route('/api/v1/products')
@rate_limit
def api_v1_products():
    """List available cross-section products. Filters by model (e.g. no smoke for GFS)."""
    model = request.args.get('model', 'hrrr').lower()
    excluded = MODEL_EXCLUDED_STYLES.get(model, set())
    if excluded:
        filtered = [p for p in PRODUCTS_INFO if PRODUCT_TO_STYLE.get(p['id']) not in excluded]
        return jsonify({'products': filtered, 'model': model})
    return jsonify({'products': PRODUCTS_INFO, 'model': model})


@app.route('/api/v1/cycles')
@rate_limit
def api_v1_cycles():
    """List available cycles and their forecast hours."""
    mgr = get_manager_from_request() or data_manager
    cycles_out = []
    for c in mgr.available_cycles:
        ck = c['cycle_key']
        cycles_out.append({
            'key': ck,
            'display': c['display'],
            'forecast_hours': c['available_fhrs'],
            'loaded': any(k == ck for k, _ in mgr.loaded_items),
        })
    latest = mgr.available_cycles[0]['cycle_key'] if mgr.available_cycles else None
    return jsonify({'cycles': cycles_out, 'latest': latest, 'model': mgr.model_name})


@app.route('/api/v1/status')
@rate_limit
def api_v1_status():
    """Server health and status."""
    mgr = get_manager_from_request() or data_manager
    mem_mb = mgr.xsect.get_memory_usage() if mgr.xsect else 0
    latest = mgr.available_cycles[0]['cycle_key'] if mgr.available_cycles else None
    return jsonify({
        'ok': True,
        'model': mgr.model_name,
        'loaded_count': len(mgr.loaded_items),
        'memory_mb': round(mem_mb, 0),
        'latest_cycle': latest,
    })


# =============================================================================
# v1 API — Data endpoint (numerical cross-section data as JSON)
# =============================================================================

def _numpy_to_list(obj):
    """Convert numpy arrays in a dict to JSON-serializable lists. Handles NaN → null."""
    import numpy as np
    if isinstance(obj, np.ndarray):
        # Replace NaN with None for JSON serialization
        if obj.dtype.kind == 'f':  # float arrays
            return [[None if np.isnan(v) else round(float(v), 4) for v in row]
                    for row in obj] if obj.ndim == 2 else [None if np.isnan(v) else round(float(v), 4) for v in obj]
        return obj.tolist()
    if isinstance(obj, (np.float32, np.float64, np.float16)):
        return round(float(obj), 4)
    if isinstance(obj, (np.int32, np.int64)):
        return int(obj)
    return obj


# Map style -> list of (output_key, data_dict_key, description)
# These define which fields from _interpolate_to_path go into the JSON response.
_DATA_FIELD_MAP = {
    'temp':               [('temperature_c', 'temp_c', '°C')],
    'wind_speed':         [('u_wind_ms', 'u_wind', 'm/s'), ('v_wind_ms', 'v_wind', 'm/s')],
    'theta_e':            [('theta_e_k', 'theta_e', 'K')],
    'rh':                 [('rh_pct', 'rh', '%')],
    'omega':              [('omega_hpa_hr', 'omega', 'hPa/hr')],
    'q':                  [('specific_humidity_gkg', 'specific_humidity', 'g/kg')],
    'vorticity':          [('vorticity_1e5_s', 'vorticity', '10⁻⁵ s⁻¹')],
    'shear':              [('shear_1e3_s', 'shear', '10⁻³ s⁻¹')],
    'lapse_rate':         [('lapse_rate_c_km', 'lapse_rate', '°C/km')],
    'cloud_total':        [('cloud_total_gkg', 'cloud', 'g/kg')],
    'wetbulb':            [('wetbulb_c', 'wetbulb', '°C')],
    'icing':              [('icing_gkg', 'icing', 'g/kg')],
    'frontogenesis':      [('temperature_c', 'temp_c', '°C')],
    'smoke':              [('smoke_hyb', 'smoke_hyb', 'μg/m³')],
    'vpd':                [('vpd_hpa', 'vpd', 'hPa')],
    'dewpoint_dep':       [('dewpoint_dep_c', 'dewpoint_dep', '°C')],
    'moisture_transport': [('moisture_transport_gmkgs', 'moisture_transport', 'g·m/kg/s')],
    'pv':                 [('pv_pvu', 'pv', 'PVU')],
    'fire_wx':            [('rh_pct', 'rh', '%')],
}


@app.route('/api/v1/data')
@rate_limit
def api_v1_data():
    """Return numerical cross-section data as JSON arrays.

    Same coordinate params as /api/v1/cross-section but returns raw interpolated
    values instead of a PNG image. This is the research powerhouse endpoint.
    """
    import numpy as np

    # Parse coordinates (same as cross-section endpoint)
    try:
        for p in ('start_lat', 'start_lon', 'end_lat', 'end_lon'):
            if p not in request.args:
                raise KeyError(p)
        start = (float(request.args['start_lat']), float(request.args['start_lon']))
        end = (float(request.args['end_lat']), float(request.args['end_lon']))
    except KeyError as e:
        return jsonify({
            'error': f'Missing required parameter: {e.args[0]}',
            'usage': 'Required: start_lat, start_lon, end_lat, end_lon',
            'example': '/api/v1/data?start_lat=39.74&start_lon=-104.99&end_lat=41.88&end_lon=-87.63&product=temperature',
        }), 400
    except ValueError:
        return jsonify({'error': 'Coordinates must be numeric'}), 400

    product = request.args.get('product', 'temperature')
    cycle_raw = request.args.get('cycle', 'latest')
    try:
        fhr = int(request.args.get('fhr', 0))
    except ValueError:
        fhr = 0
    y_axis = request.args.get('y_axis', 'pressure')
    if y_axis not in ('pressure', 'height', 'isentropic'):
        y_axis = 'pressure'
    try:
        y_top = int(request.args.get('y_top', 100))
    except ValueError:
        y_top = 100
    if y_top not in (100, 200, 300, 500, 700):
        y_top = 100
    units = request.args.get('units', 'km')
    if units not in ('km', 'mi'):
        units = 'km'

    # Map product name to internal style
    style = PRODUCT_TO_STYLE.get(product)
    if style is None:
        return jsonify({
            'error': f'Unknown product: {product}',
            'available': [p['id'] for p in PRODUCTS_INFO],
        }), 400

    mgr = get_manager_from_request() or data_manager
    cycle_key = mgr.resolve_cycle(cycle_raw, fhr)
    if not cycle_key:
        return jsonify({'error': f'No data available with forecast hour F{fhr:02d}'}), 404

    if not mgr.ensure_loaded(cycle_key, fhr):
        return jsonify({'error': f'Failed to load {cycle_key} F{fhr:02d}'}), 500

    # Get raw data dict (no rendering, no semaphore needed)
    data = mgr.get_cross_section_data(start, end, cycle_key, fhr, style)
    if data is None:
        return jsonify({'error': 'Failed to generate data. Data may not be loaded.'}), 500

    # Build JSON response
    result = {
        'distances_km': _numpy_to_list(data.get('distances')),
        'pressure_levels_hpa': _numpy_to_list(data.get('pressure_levels')),
        'lats': _numpy_to_list(data.get('lats')),
        'lons': _numpy_to_list(data.get('lons')),
    }

    # Add style-specific data fields
    field_map = _DATA_FIELD_MAP.get(style, [])
    fields_included = []
    for out_key, data_key, field_units in field_map:
        if data_key in data:
            result[out_key] = _numpy_to_list(data[data_key])
            fields_included.append({'key': out_key, 'units': field_units})

    # Always include wind components if available (useful for all styles)
    if 'u_wind' in data and style != 'wind_speed':
        result['u_wind_ms'] = _numpy_to_list(data['u_wind'])
        result['v_wind_ms'] = _numpy_to_list(data['v_wind'])

    # Always include surface pressure for terrain context
    if 'surface_pressure' in data:
        result['surface_pressure_hpa'] = _numpy_to_list(data['surface_pressure'])

    # Metadata
    cycle = next((c for c in mgr.available_cycles if c['cycle_key'] == cycle_key), None)
    from datetime import timedelta
    if cycle:
        init_dt = cycle.get('init_dt')
        valid_dt = init_dt + timedelta(hours=fhr) if init_dt else None
        result['metadata'] = {
            'model': mgr.model_name,
            'cycle': cycle_key,
            'fhr': fhr,
            'valid_time': valid_dt.strftime('%Y-%m-%dT%H:%MZ') if valid_dt else None,
            'product': product,
            'style': style,
            'distance_km': round(float(data['distances'][-1]), 1) if 'distances' in data else None,
            'n_points': len(data.get('lats', [])),
            'n_levels': len(data.get('pressure_levels', [])),
            'fields': fields_included,
        }

    touch_cycle_access(cycle_key)
    return jsonify(result)


# =============================================================================
# v1 API — Events endpoints
# =============================================================================

def _get_events_with_availability():
    """Return events list with has_data flag checked against loaded cycles."""
    available_keys = set()
    for _, mgr in model_registry.all_managers():
        for c in mgr.available_cycles:
            available_keys.add(c['cycle_key'])

    events_out = []
    for cycle_key, evt in EVENTS_DATA.items():
        e = {
            'cycle_key': cycle_key,
            'name': evt.get('name', ''),
            'category': evt.get('category', ''),
            'date_local': evt.get('date_local', ''),
            'notes': evt.get('notes', ''),
            'why': evt.get('why', ''),
            'has_data': cycle_key in available_keys or evt.get('archive_cycle', '') in available_keys,
            'coordinates': evt.get('coordinates'),
            'description': evt.get('description', ''),
            'hero_fhr': evt.get('hero_fhr'),
            'hero_product': evt.get('hero_product', ''),
            'quad_products': evt.get('quad_products', []),
            'evaluation_notes': evt.get('evaluation_notes', ''),
            'impacts': evt.get('impacts', {}),
            'essential_fhrs': evt.get('essential_fhrs', []),
            'meteorological_setup': evt.get('meteorological_setup', ''),
            'key_features': evt.get('key_features', []),
            'archive_cycle': evt.get('archive_cycle'),
            'fhr_offset': evt.get('fhr_offset', 0),
        }
        events_out.append(e)
    return events_out


@app.route('/api/v1/events')
@rate_limit
def api_v1_events():
    """List all historical weather events with availability status."""
    events = _get_events_with_availability()

    # Optional filters
    category = request.args.get('category')
    if category:
        events = [e for e in events if e['category'] == category]

    has_data = request.args.get('has_data')
    if has_data and has_data.lower() == 'true':
        events = [e for e in events if e['has_data']]

    return jsonify({'events': events, 'count': len(events)})


@app.route('/api/v1/events/categories')
@rate_limit
def api_v1_events_categories():
    """List event categories with counts."""
    cats = defaultdict(int)
    for evt in EVENTS_DATA.values():
        cats[evt.get('category', 'other')] += 1

    categories = [{'category': cat, 'count': count} for cat, count in sorted(cats.items())]
    return jsonify({'categories': categories})


@app.route('/api/v1/events/<cycle_key>')
@rate_limit
def api_v1_event_detail(cycle_key):
    """Get detailed information about a specific event."""
    evt = EVENTS_DATA.get(cycle_key)
    if not evt:
        return jsonify({'error': f'Event not found: {cycle_key}', 'hint': 'Use /api/v1/events to list all events'}), 404

    # Check availability and get FHRs
    available_fhrs = []
    has_data = False
    for _, mgr in model_registry.all_managers():
        for c in mgr.available_cycles:
            if c['cycle_key'] == cycle_key:
                available_fhrs = c['available_fhrs']
                has_data = True
                break

    # Get products available for the model (assume HRRR for events)
    model = 'hrrr'
    excluded = MODEL_EXCLUDED_STYLES.get(model, set())
    products = [p for p in PRODUCTS_INFO if PRODUCT_TO_STYLE.get(p['id']) not in excluded]

    result = {
        'cycle_key': cycle_key,
        'name': evt.get('name', ''),
        'category': evt.get('category', ''),
        'date_local': evt.get('date_local', ''),
        'notes': evt.get('notes', ''),
        'why': evt.get('why', ''),
        'has_data': has_data,
        'available_fhrs': available_fhrs,
        'coordinates': evt.get('coordinates'),
        'available_products': products,
    }
    return jsonify(result)


# =============================================================================
# v1 API — City terrain profiles
# =============================================================================

# Lazy import to avoid circular / startup cost
_CITY_PROFILES = None

def _get_city_profiles():
    global _CITY_PROFILES
    if _CITY_PROFILES is None:
        try:
            from tools.agent_tools.terrain import CITY_TERRAIN_PROFILES
            _CITY_PROFILES = CITY_TERRAIN_PROFILES
        except ImportError:
            _CITY_PROFILES = {}
    return _CITY_PROFILES


# Region classification for color-coded map markers
_REGION_MAP = {
    'california_profiles': 'california',
    'pnw_rockies_profiles': 'pnw_rockies',
    'colorado_basin_profiles': 'colorado_basin',
    'southwest_profiles': 'southwest',
    'southern_plains_profiles': 'southern_plains',
    'southeast_misc_profiles': 'southeast_misc',
}

def _infer_region(key, profile):
    """Infer region from city key or profile metadata."""
    # Check if profile has region hint from its source module
    if 'region' in profile:
        return profile['region']
    # Heuristic from key suffix
    suffix = key.rsplit('_', 1)[-1].lower() if '_' in key else ''
    state_to_region = {
        'ca': 'california',
        'or': 'pnw_rockies', 'wa': 'pnw_rockies', 'id': 'pnw_rockies', 'mt': 'pnw_rockies', 'wy': 'pnw_rockies',
        'co': 'colorado_basin', 'ut': 'colorado_basin', 'nv': 'colorado_basin',
        'az': 'southwest', 'nm': 'southwest',
        'tx': 'southern_plains', 'ok': 'southern_plains', 'ks': 'southern_plains',
    }
    return state_to_region.get(suffix, 'southeast_misc')


@app.route('/api/v1/cities')
@rate_limit
def api_v1_cities():
    """All 232 cities with coords and basic info for map markers."""
    profiles = _get_city_profiles()
    cities = []
    for key, p in profiles.items():
        center = p.get('center') or p.get('coords')
        if not center:
            continue
        city_name = p.get('city', key.replace('_', ' ').title())
        # Strip state suffix for display if already in city name
        region = _infer_region(key, p)
        cities.append({
            'key': key,
            'name': city_name,
            'lat': center[0],
            'lon': center[1],
            'region': region,
            'elevation_ft': p.get('elevation_ft'),
            'wui_exposure': (p.get('wui_exposure') or '')[:80],
            'terrain_class': p.get('terrain_class', ''),
            'has_suggested_section': bool(p.get('suggested_section') or p.get('key_features')),
        })
    return jsonify({'cities': cities, 'count': len(cities)})


@app.route('/api/v1/cities/search')
@rate_limit
def api_v1_cities_search():
    """Search cities by name/keyword or lat/lon proximity."""
    profiles = _get_city_profiles()
    q = request.args.get('q', '').lower().strip()
    lat = request.args.get('lat', type=float)
    lon = request.args.get('lon', type=float)
    limit = request.args.get('limit', 20, type=int)

    results = []
    if lat is not None and lon is not None:
        # Proximity search
        for key, p in profiles.items():
            center = p.get('center') or p.get('coords')
            if not center:
                continue
            dist = ((center[0] - lat) ** 2 + (center[1] - lon) ** 2) ** 0.5
            results.append((dist, key, p))
        results.sort(key=lambda x: x[0])
        results = results[:limit]
        return jsonify({'cities': [{
            'key': k,
            'name': p.get('city', k.replace('_', ' ').title()),
            'lat': (p.get('center') or p.get('coords', (0, 0)))[0],
            'lon': (p.get('center') or p.get('coords', (0, 0)))[1],
            'distance_deg': round(d, 3),
            'region': _infer_region(k, p),
        } for d, k, p in results], 'count': len(results)})
    elif q:
        # Text search
        for key, p in profiles.items():
            city_name = p.get('city', key.replace('_', ' ').title()).lower()
            if q in city_name or q in key:
                center = p.get('center') or p.get('coords')
                if center:
                    results.append({
                        'key': key,
                        'name': p.get('city', key.replace('_', ' ').title()),
                        'lat': center[0],
                        'lon': center[1],
                        'region': _infer_region(key, p),
                    })
        return jsonify({'cities': results[:limit], 'count': len(results[:limit])})
    else:
        return jsonify({'error': 'Provide ?q=name or ?lat=&lon= parameters'}), 400


@app.route('/api/v1/cities/<key>')
@rate_limit
def api_v1_city_detail(key):
    """Full profile for one city."""
    profiles = _get_city_profiles()
    p = profiles.get(key)
    if not p:
        return jsonify({'error': f'City not found: {key}', 'hint': 'Use /api/v1/cities to list all'}), 404

    center = p.get('center') or p.get('coords')
    result = {
        'key': key,
        'name': p.get('city', key.replace('_', ' ').title()),
        'lat': center[0] if center else None,
        'lon': center[1] if center else None,
        'region': _infer_region(key, p),
        'elevation_ft': p.get('elevation_ft'),
        'elevation_range_ft': p.get('elevation_range_ft'),
        'terrain_class': p.get('terrain_class', ''),
        'terrain_notes': p.get('terrain_notes', ''),
        'terrain_description': p.get('terrain_description', ''),
        'vegetation': p.get('vegetation', ''),
        'wui_exposure': p.get('wui_exposure', ''),
        'fire_behavior_notes': p.get('fire_behavior_notes', ''),
        'danger_quadrants': p.get('danger_quadrants', []),
        'safe_quadrants': p.get('safe_quadrants', []),
        'key_features': p.get('key_features') or p.get('terrain_features', []),
        'historical_fires': p.get('historical_fires', []),
        'evacuation_routes': p.get('evacuation_routes', []),
        'fire_spread_characteristics': p.get('fire_spread_characteristics', ''),
        'suggested_section': p.get('suggested_section'),
    }
    return jsonify(result)


# =============================================================================
# v1 API — Capabilities endpoint
# =============================================================================

@app.route('/api/v1/capabilities')
@rate_limit
def api_v1_capabilities():
    """Machine-readable parameter constraints and coverage information."""
    models = []
    for name, mgr in model_registry.all_managers():
        cfg = mgr.model_config
        excluded = MODEL_EXCLUDED_STYLES.get(name, set())
        cycle_count = len(mgr.available_cycles)
        model_info = {
            'id': name,
            'name': cfg.full_name if cfg else name.upper(),
            'resolution': cfg.resolution if cfg else 'unknown',
            'domain': cfg.domain if cfg else 'CONUS',
            'forecast_hours': {
                'base': MODEL_FORECAST_HOURS.get(name, []),
                'synoptic_max': 48 if name == 'hrrr' else MODEL_FORECAST_HOURS.get(name, [0])[-1],
            },
            'synoptic_hours': sorted(SYNOPTIC_HOURS) if name == 'hrrr' else None,
            'excluded_products': sorted(excluded),
            'available_cycles': cycle_count,
        }
        models.append(model_info)

    return jsonify({
        'models': models,
        'products': PRODUCTS_INFO,
        'parameters': {
            'y_axis': {'values': ['pressure', 'height', 'isentropic'], 'default': 'pressure'},
            'y_top': {'values': [100, 200, 300, 500, 700], 'default': 100, 'units': 'hPa'},
            'units': {'values': ['km', 'mi'], 'default': 'km'},
        },
        'coordinate_bounds': CONUS_BOUNDS,
        'rate_limits': {
            'requests_per_minute': 60,
            'burst_per_second': 10,
        },
        'event_count': len(EVENTS_DATA),
    })


# =============================================================================
# =============================================================================
# v1 API — External data proxy endpoints (public)
# =============================================================================

@app.route('/api/v1/spc/fire-outlook')
@rate_limit
def api_v1_spc_fire_outlook():
    """SPC Fire Weather Outlook polygons via NOAA MapServer. dn values: 2=Non-Critical, 5=Elevated, 8=Critical, 10=Extremely Critical."""
    import urllib.request
    day = int(request.args.get('day', '1'))
    # NOAA MapServer layers: Day N Outlook at layer (day-1)*3+1, Dry Thunderstorm at (day-1)*3+2
    layer = (day - 1) * 3 + 1
    include_dry_tstm = request.args.get('dry_tstm', 'false').lower() == 'true'
    base = "https://mapservices.weather.noaa.gov/vector/rest/services/fire_weather/SPC_firewx/MapServer"
    try:
        url = f"{base}/{layer}/query?where=1%3D1&outFields=*&f=geojson"
        req = urllib.request.Request(url, headers={"User-Agent": "wxsection.com contact@wxsection.com"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            outlook = json.loads(resp.read())
        # Add human-readable risk level to properties
        dn_labels = {2: "Non-Critical", 5: "Elevated", 8: "Critical", 10: "Extremely Critical"}
        for feat in outlook.get("features", []):
            dn = feat.get("properties", {}).get("dn")
            feat["properties"]["risk_label"] = dn_labels.get(dn, f"Unknown ({dn})")
        result = {"day": day, "outlook": outlook}
        if include_dry_tstm:
            dry_layer = layer + 1
            dry_url = f"{base}/{dry_layer}/query?where=1%3D1&outFields=*&f=geojson"
            req2 = urllib.request.Request(dry_url, headers={"User-Agent": "wxsection.com contact@wxsection.com"})
            with urllib.request.urlopen(req2, timeout=15) as resp2:
                result["dry_thunderstorm"] = json.loads(resp2.read())
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 502


@app.route('/api/v1/nws/alerts')
@rate_limit
def api_v1_nws_alerts():
    """Active NWS weather alerts. Filter by state, lat/lon, or event type."""
    import urllib.request, urllib.parse
    base = "https://api.weather.gov/alerts/active"
    params = {}
    state = request.args.get('state')
    lat = request.args.get('lat')
    lon = request.args.get('lon')
    event_type = request.args.get('event')
    if state:
        params['area'] = state.upper()
    if lat and lon:
        params['point'] = f"{lat},{lon}"
    if event_type:
        params['event'] = event_type
    url = base + ("?" + urllib.parse.urlencode(params) if params else "")
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "wxsection.com contact@wxsection.com",
            "Accept": "application/geo+json",
        })
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = resp.read()
        return Response(data, mimetype='application/json',
                        headers={'Access-Control-Allow-Origin': '*'})
    except Exception as e:
        return jsonify({"error": str(e)}), 502


@app.route('/api/v1/nws/discussion/<office>')
@rate_limit
def api_v1_nws_discussion(office):
    """NWS Area Forecast Discussion text for a Weather Forecast Office."""
    import urllib.request
    try:
        url = f"https://api.weather.gov/products/types/AFD/locations/{office.upper()}"
        req = urllib.request.Request(url, headers={
            "User-Agent": "wxsection.com contact@wxsection.com",
        })
        with urllib.request.urlopen(req, timeout=15) as resp:
            products = json.loads(resp.read())
        if not products.get("@graph"):
            return jsonify({"error": f"No AFD found for {office}"}), 404
        latest_url = products["@graph"][0]["@id"]
        req2 = urllib.request.Request(latest_url, headers={
            "User-Agent": "wxsection.com contact@wxsection.com",
        })
        with urllib.request.urlopen(req2, timeout=15) as resp2:
            product = json.loads(resp2.read())
        return jsonify({
            "office": office.upper(),
            "text": product.get("productText", ""),
            "issued": product.get("issuanceTime", ""),
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 502


@app.route('/api/v1/fire-risk')
@rate_limit
def api_v1_fire_risk():
    """Assess fire weather risk along a transect. Returns composite score 0-100."""
    start_lat = request.args.get('start_lat', type=float)
    start_lon = request.args.get('start_lon', type=float)
    end_lat = request.args.get('end_lat', type=float)
    end_lon = request.args.get('end_lon', type=float)
    if None in (start_lat, start_lon, end_lat, end_lon):
        return jsonify({"error": "start_lat, start_lon, end_lat, end_lon required"}), 400

    model = request.args.get('model', 'hrrr')
    cycle = request.args.get('cycle', 'latest')
    fhr = request.args.get('fhr', 0, type=int)

    # Get RH and wind data
    rh_params = {
        'start_lat': start_lat, 'start_lon': start_lon,
        'end_lat': end_lat, 'end_lon': end_lon,
        'model': model, 'cycle': cycle, 'fhr': fhr, 'product': 'rh',
    }
    wind_params = dict(rh_params, product='wind_speed')
    temp_params = dict(rh_params, product='temperature')

    try:
        from tools.agent_tools.cross_section import CrossSectionTool
        from tools.agent_tools.fire_risk import FireRiskAnalyzer
        base_url = request.url_root.rstrip('/')
        analyzer = FireRiskAnalyzer(base_url=base_url, model=model)
        assessment = analyzer.analyze_transect(
            start=(start_lat, start_lon),
            end=(end_lat, end_lon),
            cycle=cycle, fhr=fhr,
            label=request.args.get('label'),
        )
        return jsonify({
            "risk_level": assessment.risk_level,
            "risk_score": assessment.risk_score,
            "contributing_factors": assessment.contributing_factors,
            "rh_stats": assessment.rh_stats,
            "wind_stats": assessment.wind_stats,
            "temp_stats": assessment.temp_stats,
            "model": model, "cycle": cycle, "fhr": fhr,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/v1/fire-risk/national')
@rate_limit
def api_v1_fire_risk_national():
    """Quick national fire risk scan across 12 CONUS regions."""
    model = request.args.get('model', 'hrrr')
    cycle = request.args.get('cycle', 'latest')
    fhr = request.args.get('fhr', 12, type=int)

    try:
        from tools.agent_tools.fire_risk import FireRiskAnalyzer, FIRE_REGIONS
        base_url = request.url_root.rstrip('/')
        analyzer = FireRiskAnalyzer(base_url=base_url, model=model)

        results = {}
        for name, region in FIRE_REGIONS.items():
            try:
                assessment = analyzer.analyze_transect(
                    start=region["start"], end=region["end"],
                    cycle=cycle, fhr=fhr, label=region["label"],
                )
                results[name] = {
                    "label": region["label"],
                    "risk_level": assessment.risk_level,
                    "risk_score": assessment.risk_score,
                    "contributing_factors": assessment.contributing_factors,
                }
            except Exception:
                results[name] = {"label": region["label"], "risk_level": "ERROR"}

        # Sort by score
        results = dict(sorted(results.items(),
                               key=lambda x: x[1].get("risk_score", 0),
                               reverse=True))
        return jsonify({
            "model": model, "cycle": cycle, "fhr": fhr,
            "regions": results,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# v1 API — Tool schemas endpoint (Anthropic tool_use format)
# =============================================================================

@app.route('/api/v1/tools')
@rate_limit
def api_v1_tools():
    """Export Anthropic tool_use compatible schemas for agent integration."""
    tools = [
        {
            'name': 'wxsection_cross_section',
            'description': 'Generate a PNG atmospheric cross-section between two geographic points from HRRR/GFS/RRFS weather models.',
            'input_schema': {
                'type': 'object',
                'properties': {
                    'start_lat': {'type': 'number', 'description': 'Start latitude (-90 to 90)'},
                    'start_lon': {'type': 'number', 'description': 'Start longitude (-180 to 180)'},
                    'end_lat': {'type': 'number', 'description': 'End latitude'},
                    'end_lon': {'type': 'number', 'description': 'End longitude'},
                    'product': {'type': 'string', 'description': 'Atmospheric product', 'default': 'temperature',
                                'enum': [p['id'] for p in PRODUCTS_INFO]},
                    'model': {'type': 'string', 'enum': ['hrrr', 'gfs', 'rrfs'], 'default': 'hrrr'},
                    'cycle': {'type': 'string', 'description': "Cycle key or 'latest'", 'default': 'latest'},
                    'fhr': {'type': 'integer', 'description': 'Forecast hour', 'default': 0, 'minimum': 0},
                    'y_axis': {'type': 'string', 'enum': ['pressure', 'height', 'isentropic'], 'default': 'pressure'},
                    'y_top': {'type': 'integer', 'enum': [100, 200, 300, 500, 700], 'default': 100},
                    'units': {'type': 'string', 'enum': ['km', 'mi'], 'default': 'km'},
                },
                'required': ['start_lat', 'start_lon', 'end_lat', 'end_lon'],
            },
        },
        {
            'name': 'wxsection_data',
            'description': 'Get raw numerical atmospheric data along a cross-section path as JSON arrays. Returns pressure levels, distances, coordinates, and 2D field arrays.',
            'input_schema': {
                'type': 'object',
                'properties': {
                    'start_lat': {'type': 'number', 'description': 'Start latitude'},
                    'start_lon': {'type': 'number', 'description': 'Start longitude'},
                    'end_lat': {'type': 'number', 'description': 'End latitude'},
                    'end_lon': {'type': 'number', 'description': 'End longitude'},
                    'product': {'type': 'string', 'description': 'Atmospheric product', 'default': 'temperature',
                                'enum': [p['id'] for p in PRODUCTS_INFO]},
                    'model': {'type': 'string', 'enum': ['hrrr', 'gfs', 'rrfs'], 'default': 'hrrr'},
                    'cycle': {'type': 'string', 'default': 'latest'},
                    'fhr': {'type': 'integer', 'default': 0, 'minimum': 0},
                },
                'required': ['start_lat', 'start_lon', 'end_lat', 'end_lon'],
            },
        },
        {
            'name': 'wxsection_events',
            'description': 'List historical weather events (85 curated events: fires, hurricanes, tornadoes, derechos, hail, atmospheric rivers, winter storms).',
            'input_schema': {
                'type': 'object',
                'properties': {
                    'category': {'type': 'string', 'description': 'Filter by category',
                                 'enum': sorted(set(e.get('category', 'other') for e in EVENTS_DATA.values()))},
                    'has_data': {'type': 'boolean', 'description': 'Only events with data loaded'},
                },
            },
        },
        {
            'name': 'wxsection_event_detail',
            'description': 'Get details about a specific weather event including suggested cross-section paths and available forecast hours.',
            'input_schema': {
                'type': 'object',
                'properties': {
                    'cycle_key': {'type': 'string', 'description': "Event cycle key (e.g. '20250107_00z')"},
                },
                'required': ['cycle_key'],
            },
        },
        {
            'name': 'wxsection_cycles',
            'description': 'List available model cycles with forecast hours.',
            'input_schema': {
                'type': 'object',
                'properties': {
                    'model': {'type': 'string', 'enum': ['hrrr', 'gfs', 'rrfs'], 'default': 'hrrr'},
                },
            },
        },
        {
            'name': 'wxsection_status',
            'description': 'Check server health, loaded data, and memory usage.',
            'input_schema': {
                'type': 'object',
                'properties': {
                    'model': {'type': 'string', 'enum': ['hrrr', 'gfs', 'rrfs'], 'default': 'hrrr'},
                },
            },
        },
    ]
    return jsonify({'tools': tools, 'format': 'anthropic_tool_use'})


# v1 API — Map overlay endpoints
# =============================================================================

_overlay_engines: dict[str, MapOverlayEngine] = {}
_overlay_engines_lock = threading.Lock()


def _get_overlay_engine(model_name: str, cache_dir: str) -> MapOverlayEngine:
    """Get or create a MapOverlayEngine singleton for a model."""
    with _overlay_engines_lock:
        if model_name not in _overlay_engines:
            _overlay_engines[model_name] = MapOverlayEngine(model_name, cache_dir)
        return _overlay_engines[model_name]


@app.route('/api/v1/map-overlay')
@rate_limit
def api_v1_map_overlay():
    """Render a model field as a map overlay (binary float32 or PNG).

    Query params:
        product: Product preset name (e.g. 'surface_analysis') — overrides field/level
        field: Field ID from OVERLAY_FIELDS (required unless product is set)
        model: hrrr/gfs/rrfs (default: hrrr)
        cycle: Cycle key or 'latest' (default: latest)
        fhr: Forecast hour (default: 0)
        level: Pressure level hPa (required for isobaric fields)
        format: 'binary' (float32 for WebGL) or 'png' (colored raster) (default: binary)
        bbox: south,west,north,east for viewport crop
        cmap: Override colormap name (PNG only)
        vmin/vmax: Override value range
        opacity: 0-1 (PNG only, default 0.8)
        contours: Ad-hoc contours 'field:interval:color' (comma-separated)
        barbs: '10m' (surface) or pressure level (e.g. '500')
    """
    product_id = request.args.get('product', '')
    field_id = request.args.get('field', '')
    model = request.args.get('model', 'hrrr').lower()
    cycle = request.args.get('cycle', 'latest')
    fhr = int(request.args.get('fhr', 0))
    level_str = request.args.get('level', '')
    fmt = request.args.get('format', 'binary')
    bbox_str = request.args.get('bbox', '')
    opacity = float(request.args.get('opacity', 0.8))

    # Parse bbox
    bbox = None
    if bbox_str:
        try:
            parts = [float(x) for x in bbox_str.split(',')]
            if len(parts) == 4:
                bbox = {'south': parts[0], 'west': parts[1], 'north': parts[2], 'east': parts[3]}
        except ValueError:
            pass

    # Get manager and ensure data is loaded
    try:
        mgr = model_registry.get(model)
    except ValueError:
        return jsonify({'error': f'Unknown model: {model}. Available: {list(model_registry.managers.keys())}'}), 400

    cycle_key = mgr.resolve_cycle(cycle, fhr)
    if not cycle_key:
        return jsonify({'error': f'No cycle available for {model} with fhr={fhr}'}), 404

    if not mgr.ensure_loaded(cycle_key, fhr):
        return jsonify({'error': f'Failed to load {cycle_key} fhr={fhr}'}), 500

    # Get ForecastHourData
    engine_key = mgr._engine_key_map.get((cycle_key, fhr))
    if engine_key is None:
        return jsonify({'error': 'Data not available'}), 404
    fhr_data = mgr.xsect.forecast_hours.get(engine_key)
    if fhr_data is None:
        return jsonify({'error': 'FHR data not loaded'}), 404

    # Get overlay engine
    cache_dir = str(mgr.xsect.cache_dir) if mgr.xsect and mgr.xsect.cache_dir else None
    engine = _get_overlay_engine(model, cache_dir)

    # --- Product preset mode ---
    if product_id:
        if product_id not in PRODUCT_PRESETS:
            return jsonify({'error': f'Unknown product: {product_id}',
                            'available': list(PRODUCT_PRESETS.keys())}), 400
        composite_spec = PRODUCT_PRESETS[product_id]
        result = engine.render_composite(fhr_data, composite_spec, bbox, opacity)
        if result is None:
            return jsonify({'error': f'Product {product_id} not available (missing data fields)'}), 404
        resp = Response(result.data, content_type=result.content_type)
        for key, val in result.headers().items():
            resp.headers[key] = val
        resp.headers['X-Product'] = product_id
        return resp

    # --- Ad-hoc composite mode (field + optional contours/barbs) ---
    contours_str = request.args.get('contours', '')
    barbs_str = request.args.get('barbs', '')

    if not field_id:
        return jsonify({'error': 'field or product parameter required'}), 400
    if field_id not in OVERLAY_FIELDS:
        return jsonify({'error': f'Unknown field: {field_id}', 'available': list(OVERLAY_FIELDS.keys())}), 400

    spec = OVERLAY_FIELDS[field_id]
    level = None
    if spec.needs_level:
        if not level_str:
            return jsonify({'error': f'level parameter required for isobaric field {field_id}'}), 400
        level = int(level_str)

    # Check if ad-hoc composite is requested
    if contours_str or barbs_str:
        # Build an ad-hoc CompositeSpec
        contour_list = []
        if contours_str:
            for part in contours_str.split(','):
                tokens = part.strip().split(':')
                if len(tokens) >= 2:
                    c_field = tokens[0]
                    c_interval = float(tokens[1])
                    c_color = tokens[2] if len(tokens) > 2 else 'black'
                    contour_list.append(ContourSpec(c_field, c_interval, c_color))

        barbs_spec = None
        if barbs_str:
            if barbs_str.lower() in ('10m', 'surface'):
                barbs_spec = BarbSpec('u10m', 'v10m')
            else:
                try:
                    blevel = int(barbs_str)
                    barbs_spec = BarbSpec('u_wind', 'v_wind', level=blevel)
                except ValueError:
                    pass

        cmap = request.args.get('cmap', spec.default_cmap)
        vmin = float(request.args.get('vmin')) if request.args.get('vmin') else spec.default_vmin
        vmax = float(request.args.get('vmax')) if request.args.get('vmax') else spec.default_vmax

        adhoc = CompositeSpec(
            id='adhoc', name='Custom', description='Ad-hoc composite',
            fill_field=field_id, fill_cmap=cmap, fill_vmin=vmin, fill_vmax=vmax,
            contours=contour_list or None, barbs=barbs_spec,
            level=level,
        )
        result = engine.render_composite(fhr_data, adhoc, bbox, opacity)
        if result is None:
            return jsonify({'error': f'Ad-hoc composite not available (missing data)'}), 404
        resp = Response(result.data, content_type=result.content_type)
        for key, val in result.headers().items():
            resp.headers[key] = val
        return resp

    # --- Single field mode (original behavior) ---
    if fmt == 'png':
        cmap = request.args.get('cmap')
        vmin = float(request.args.get('vmin')) if request.args.get('vmin') else None
        vmax = float(request.args.get('vmax')) if request.args.get('vmax') else None
        result = engine.render_png(fhr_data, field_id, level, bbox, cmap, vmin, vmax, opacity)
    else:
        result = engine.render_binary(fhr_data, field_id, level, bbox)

    if result is None:
        return jsonify({'error': f'Field {field_id} not available in loaded data'}), 404

    resp = Response(result.data, content_type=result.content_type)
    for key, val in result.headers().items():
        resp.headers[key] = val
    return resp


@app.route('/api/v1/map-overlay/fields')
@rate_limit
def api_v1_map_overlay_fields():
    """List available map overlay fields with metadata and colormap LUTs.

    Query params:
        model: hrrr/gfs/rrfs (default: hrrr)
        colormaps: 'true' to include base64 RGBA colormap arrays (default: false)
    """
    model = request.args.get('model', 'hrrr').lower()
    include_cmaps = request.args.get('colormaps', 'false').lower() == 'true'

    # Try to get a loaded FHR to check field availability
    mgr = None
    fhr_data = None
    try:
        mgr = model_registry.get(model)
        if mgr and mgr.loaded_items:
            ck, fhr = next(iter(mgr.loaded_items))
            ek = mgr._engine_key_map.get((ck, fhr))
            if ek is not None and mgr.xsect:
                fhr_data = mgr.xsect.forecast_hours.get(ek)
    except Exception:
        pass

    cache_dir = str(mgr.xsect.cache_dir) if mgr and mgr.xsect and mgr.xsect.cache_dir else None
    engine = _get_overlay_engine(model, cache_dir) if cache_dir else MapOverlayEngine(model, None)

    fields = engine.get_available_fields(fhr_data)

    result = {'model': model, 'fields': fields}

    if include_cmaps:
        import base64
        cmaps = {}
        seen = set()
        for f in fields:
            cmap_name = f['default_cmap']
            if cmap_name in seen:
                continue
            seen.add(cmap_name)
            lut = get_colormap_lut(cmap_name)
            cmaps[cmap_name] = base64.b64encode(lut.tobytes()).decode()
        result['colormaps'] = cmaps

    # Grid info
    grid = engine.grid
    result['grid'] = {
        'south': grid.south, 'north': grid.north,
        'west': grid.west, 'east': grid.east,
        'dlat': grid.dlat, 'dlon': grid.dlon,
        'ny': grid.shape[0], 'nx': grid.shape[1],
    }

    return jsonify(result)


@app.route('/api/v1/map-overlay/products')
@rate_limit
def api_v1_map_overlay_products():
    """List available composite map product presets."""
    products = []
    for pid, pspec in PRODUCT_PRESETS.items():
        fill_spec = OVERLAY_FIELDS.get(pspec.fill_field) if pspec.fill_field else None
        needs_surface = fill_spec is not None and not fill_spec.needs_level
        products.append({
            'id': pspec.id,
            'name': pspec.name,
            'description': pspec.description,
            'needs_surface': needs_surface,
            'level': pspec.level,
            'fill_field': pspec.fill_field,
            'fill_cmap': pspec.fill_cmap,
            'fill_vmin': pspec.fill_vmin,
            'fill_vmax': pspec.fill_vmax,
        })
    return jsonify({'products': products})


def _png_to_webp(png_bytes: bytes, quality: int = 80) -> bytes:
    """Convert PNG bytes to WebP for ~70-80% size reduction with transparency."""
    try:
        from PIL import Image as PILImage
        img = PILImage.open(io.BytesIO(png_bytes))
        buf = io.BytesIO()
        img.save(buf, format='WEBP', quality=quality, method=4)
        return buf.getvalue()
    except Exception:
        return png_bytes  # fallback to original PNG


@app.route('/api/v1/map-overlay/frame')
def api_v1_overlay_frame():
    """Get a single prerendered overlay frame. Cache-first, then render on-demand."""
    try:
        return _overlay_frame_inner()
    except Exception as exc:
        import traceback
        logger.error(f"Overlay frame error: {exc}\n{traceback.format_exc()}")
        return jsonify({'error': str(exc)}), 500

def _overlay_frame_inner():
    model_name = request.args.get('model', 'hrrr')
    cycle = request.args.get('cycle', 'latest')
    fhr = int(request.args.get('fhr', 0))
    product = request.args.get('product', '')
    field = request.args.get('field', '')
    level = request.args.get('level', None)
    # If neither product nor field specified, default to surface_analysis
    if not product and not field:
        product = 'surface_analysis'

    product_or_field = product if product else field
    key = overlay_cache_key(model_name, cycle, fhr, product_or_field, level)
    cached = overlay_cache_get(key)
    if cached:
        return send_file(io.BytesIO(cached), mimetype='image/webp',
                         download_name=f'overlay_F{fhr:02d}.webp',
                         max_age=300)

    # Render on-demand and cache
    mgr = get_manager_from_request() or data_manager
    if mgr is None:
        return jsonify({'error': 'No data manager'}), 503
    cycle_key = mgr.resolve_cycle(cycle, fhr) if hasattr(mgr, 'resolve_cycle') else cycle
    if cycle_key is None:
        return jsonify({'error': 'No data loaded'}), 404
    # Auto-load from mmap/GRIB if needed (supports archive cycles)
    if not mgr.ensure_loaded(cycle_key, fhr):
        return jsonify({'error': f'FHR {fhr} not available for {cycle_key}'}), 404
    fhr_data = mgr.get_forecast_hour(cycle_key, fhr)
    if fhr_data is None:
        return jsonify({'error': f'FHR {fhr} not loaded'}), 404

    # Also cache with resolved cycle_key (in case request used 'latest')
    resolved_key = overlay_cache_key(model_name, cycle_key, fhr, product_or_field, level)
    cached2 = overlay_cache_get(resolved_key)
    if cached2:
        return send_file(io.BytesIO(cached2), mimetype='image/webp',
                         download_name=f'overlay_F{fhr:02d}.webp',
                         max_age=300)

    cache_dir = mgr.cache_dir if hasattr(mgr, 'cache_dir') else ''
    overlay_engine = _get_overlay_engine(model_name, cache_dir)

    try:
        if product:
            from core.map_overlay import PRODUCT_PRESETS
            spec = PRODUCT_PRESETS.get(product)
            if not spec:
                return jsonify({'error': f'Unknown product: {product}'}), 400
            result = overlay_engine.render_composite(fhr_data, spec, opacity=1.0)
        else:
            result = overlay_engine.render_png(fhr_data, field, level=int(level) if level else None, opacity=1.0)
    except Exception as exc:
        return jsonify({'error': str(exc)}), 500

    if result is None:
        return jsonify({'error': f'Surface fields not available for {cycle_key} F{fhr:02d} (cache may need re-extraction)'}), 404

    # Convert PNG → WebP for ~70-80% size reduction
    webp_data = _png_to_webp(result.data)
    overlay_cache_put(resolved_key, webp_data)
    resp = send_file(io.BytesIO(webp_data), mimetype='image/webp',
                     download_name=f'overlay_F{fhr:02d}.webp',
                     max_age=300)
    return resp


@app.route('/api/v1/map-overlay/prerender', methods=['POST'])
def api_v1_overlay_prerender():
    """Batch prerender overlay frames for all FHRs of a product."""
    body = request.get_json(force=True, silent=True) or {}
    model_name = body.get('model', 'hrrr')
    cycle = body.get('cycle', 'latest')
    product = body.get('product', 'surface_analysis')
    fhrs = body.get('fhrs', [])

    if not fhrs:
        return jsonify({'error': 'No FHRs specified'}), 400

    mgr = get_manager_from_request() or data_manager
    if mgr is None:
        return jsonify({'error': 'No data manager'}), 503

    cycle_key = cycle
    if cycle == 'latest':
        times = mgr.get_available_times()
        if times:
            cycle_key = times[0].get('cycle', cycle)

    # Check how many are already cached
    to_render = []
    for fhr in fhrs:
        key = overlay_cache_key(model_name, cycle_key, fhr, product)
        if not overlay_cache_get(key):
            to_render.append(fhr)

    if not to_render:
        return jsonify({'status': 'all_cached', 'cached': len(fhrs), 'rendered': 0})

    # Render missing frames in a background thread
    session_id = f"overlay_prerender_{int(time.time())}"

    def _do_prerender():
        cache_dir = mgr.cache_dir if hasattr(mgr, 'cache_dir') else ''
        engine = _get_overlay_engine(model_name, cache_dir)
        from core.map_overlay import PRODUCT_PRESETS
        spec = PRODUCT_PRESETS.get(product)
        if not spec:
            return
        rendered = 0
        for fhr in to_render:
            fhr_data = mgr.get_forecast_hour(cycle_key, fhr)
            if fhr_data is None:
                continue
            try:
                result = engine.render_composite(fhr_data, spec, opacity=1.0)
                webp_data = _png_to_webp(result.data)
                key = overlay_cache_key(model_name, cycle_key, fhr, product)
                overlay_cache_put(key, webp_data)
                rendered += 1
            except Exception as exc:
                logger.warning(f"Overlay prerender F{fhr:02d} failed: {exc}")

    threading.Thread(target=_do_prerender, daemon=True).start()
    return jsonify({'status': 'started', 'session_id': session_id,
                    'to_render': len(to_render), 'already_cached': len(fhrs) - len(to_render)})


@app.route('/api/v1/map-overlay/value')
def api_v1_overlay_value():
    """Query the data value at a specific lat/lng point for the current overlay."""
    import numpy as np
    lat = float(request.args.get('lat', 0))
    lng = float(request.args.get('lng', 0))
    model_name = request.args.get('model', 'hrrr')
    cycle = request.args.get('cycle', 'latest')
    fhr = int(request.args.get('fhr', 0))
    product = request.args.get('product', '')
    field = request.args.get('field', '')
    level = request.args.get('level', None)

    mgr = get_manager_from_request() or data_manager
    if mgr is None:
        return jsonify({'error': 'No data manager'}), 503

    cycle_key = mgr.resolve_cycle(cycle, fhr) if hasattr(mgr, 'resolve_cycle') else cycle
    if cycle_key is None:
        return jsonify({'error': 'No data loaded'}), 404
    if not mgr.ensure_loaded(cycle_key, fhr):
        return jsonify({'error': f'FHR {fhr} not available'}), 404
    fhr_data = mgr.get_forecast_hour(cycle_key, fhr)
    if fhr_data is None:
        return jsonify({'error': f'FHR {fhr} not loaded'}), 404

    from core.map_overlay import OVERLAY_FIELDS, PRODUCT_PRESETS, _apply_transform

    results = []
    # Determine which fields to query
    if product:
        spec = PRODUCT_PRESETS.get(product)
        if not spec:
            return jsonify({'error': f'Unknown product: {product}'}), 400
        field_ids = [spec.fill_field]
        if spec.contours:
            field_ids += [c.field_id for c in spec.contours]
    elif field:
        field_ids = [field]
    else:
        field_ids = ['t2m']

    # Find nearest grid point index once
    lats_arr = np.asarray(fhr_data.lats)
    lons_arr = np.asarray(fhr_data.lons)
    if lats_arr.ndim == 1 and lons_arr.ndim == 1:
        lat_idx = int(np.argmin(np.abs(lats_arr - lat)))
        lon_idx = int(np.argmin(np.abs(lons_arr - lng)))
        grid_idx = (lat_idx, lon_idx)
    elif lats_arr.ndim == 2:
        dist = (lats_arr - lat)**2 + (lons_arr - lng)**2
        grid_idx = np.unravel_index(np.argmin(dist), dist.shape)
    else:
        return jsonify({'error': 'Unsupported grid'}), 500

    for fid in field_ids:
        fspec = OVERLAY_FIELDS.get(fid)
        if not fspec:
            continue
        try:
            # Extract raw value from native grid
            if fspec.derived_from:
                # Derived field (wind speed, RH, etc.)
                components = []
                for comp_name in fspec.derived_from:
                    arr = getattr(fhr_data, comp_name, None)
                    if arr is None:
                        break
                    if arr.ndim == 3 and level is not None:
                        # Find pressure level index
                        plevs = getattr(fhr_data, 'pressure_levels', None)
                        if plevs is not None:
                            lvl_idx = int(np.argmin(np.abs(np.asarray(plevs) - int(level))))
                            arr = arr[lvl_idx]
                        else:
                            break
                    elif arr.ndim == 3:
                        break
                    components.append(np.asarray(arr, dtype=np.float32))
                if len(components) < len(fspec.derived_from):
                    continue
                # Field-specific derivation (mirrors map_overlay.py)
                if fid in ('wind_speed_10m', 'wind_speed') and len(components) == 2:
                    val = float(np.sqrt(components[0][grid_idx]**2 + components[1][grid_idx]**2))
                elif fid == 'rh_surface' and len(components) == 2:
                    t_c = float(components[0][grid_idx]) - 273.15
                    td_c = float(components[1][grid_idx]) - 273.15
                    val = min(100.0, max(0.0, 100.0 * np.exp(17.625 * td_c / (243.04 + td_c)) / np.exp(17.625 * t_c / (243.04 + t_c))))
                elif fid == 'wind_chill' and len(components) == 3:
                    t_f = (float(components[0][grid_idx]) - 273.15) * 9.0 / 5.0 + 32.0
                    ws_mph = float(np.sqrt(components[1][grid_idx]**2 + components[2][grid_idx]**2)) * 2.23694
                    val = 35.74 + 0.6215 * t_f - 35.75 * max(ws_mph, 0.5)**0.16 + 0.4275 * t_f * max(ws_mph, 0.5)**0.16 if t_f <= 50 else t_f
                elif fid == 'heat_index' and len(components) == 2:
                    t_f = (float(components[0][grid_idx]) - 273.15) * 9.0 / 5.0 + 32.0
                    td_c = float(components[1][grid_idx]) - 273.15
                    rh = min(100.0, max(0.0, 100.0 * np.exp(17.625 * td_c / (243.04 + td_c)) / np.exp(17.625 * (float(components[0][grid_idx]) - 273.15) / (243.04 + (float(components[0][grid_idx]) - 273.15)))))
                    val = (-42.379 + 2.04901523 * t_f + 10.14333127 * rh - 0.22475541 * t_f * rh - 0.00683783 * t_f**2 - 0.05481717 * rh**2 + 0.00122874 * t_f**2 * rh + 0.00085282 * t_f * rh**2 - 0.00000199 * t_f**2 * rh**2) if t_f >= 80 else t_f
                elif fid in ('hdw', 'hdw_paired') and len(components) == 4:
                    # HDW: scan lowest 50 hPa AGL for max VPD and wind
                    import math
                    DEPTH = 50.0
                    is_paired = (fid == 'hdw_paired')
                    plevs = getattr(fhr_data, 'pressure_levels', None)
                    sp = getattr(fhr_data, 'surface_pressure', None)
                    t3d = getattr(fhr_data, 'temperature', None)
                    td3d = getattr(fhr_data, 'dew_point', None)
                    u3d = getattr(fhr_data, 'u_wind', None)
                    v3d = getattr(fhr_data, 'v_wind', None)
                    # Surface values
                    t_c = float(components[0][grid_idx]) - 273.15
                    td_c = float(components[1][grid_idx]) - 273.15
                    es_s = 6.112 * math.exp(17.67 * t_c / (t_c + 243.5))
                    ea_s = 6.112 * math.exp(17.67 * td_c / (td_c + 243.5))
                    sfc_vpd = max(es_s - ea_s, 0.0)
                    sfc_ws = math.sqrt(float(components[2][grid_idx])**2 + float(components[3][grid_idx])**2)
                    if is_paired:
                        max_product = sfc_vpd * sfc_ws
                    else:
                        max_vpd = sfc_vpd
                        max_ws = sfc_ws
                    if plevs is not None and sp is not None and t3d is not None and t3d.ndim == 3:
                        sp_val = float(sp[grid_idx])
                        for li in range(len(plevs)):
                            p = float(plevs[li])
                            if p > sp_val or p < sp_val - DEPTH:
                                continue
                            tc = float(t3d[li][grid_idx]) - 273.15
                            tdc = float(td3d[li][grid_idx]) - 273.15
                            es_l = 6.112 * math.exp(17.67 * tc / (tc + 243.5))
                            ea_l = 6.112 * math.exp(17.67 * tdc / (tdc + 243.5))
                            vpd_l = max(es_l - ea_l, 0.0)
                            ws_l = math.sqrt(float(u3d[li][grid_idx])**2 + float(v3d[li][grid_idx])**2)
                            if is_paired:
                                product_l = vpd_l * ws_l
                                if product_l > max_product:
                                    max_product = product_l
                            else:
                                if vpd_l > max_vpd:
                                    max_vpd = vpd_l
                                if ws_l > max_ws:
                                    max_ws = ws_l
                    val = max_product if is_paired else max_vpd * max_ws
                elif len(components) == 2:
                    val = float(np.sqrt(components[0][grid_idx]**2 + components[1][grid_idx]**2))
                elif len(components) == 3:
                    val = float(components[0][grid_idx])
                else:
                    continue
            else:
                arr = getattr(fhr_data, fspec.attr_name, None)
                if arr is None:
                    continue
                if arr.ndim == 3 and fspec.needs_level and level is not None:
                    plevs = getattr(fhr_data, 'pressure_levels', None)
                    if plevs is not None:
                        lvl_idx = int(np.argmin(np.abs(np.asarray(plevs) - int(level))))
                        arr = arr[lvl_idx]
                    else:
                        continue
                val = float(arr[grid_idx])

            if not np.isfinite(val):
                continue
            # Apply transform (K→C, m/s→kt, etc)
            transformed = _apply_transform(np.array([val]), fspec.transform)
            val_out = round(float(transformed[0]), 1)
            results.append({
                'field': fid,
                'name': fspec.name,
                'value': val_out,
                'units': fspec.units,
            })
        except Exception:
            continue

    return jsonify({'lat': lat, 'lng': lng, 'fhr': fhr, 'cycle': cycle_key, 'values': results})


@app.route('/api/v1/map-overlay/grid-sample')
def api_v1_overlay_grid_sample():
    """Return a binary grid of overlay values for instant client-side hover.

    Binary format: [4B header_len][JSON header][uint16 field0][uint16 field1]...
    Values encoded as uint16: encoded = (val - vmin) / (vmax - vmin) * 65534, 65535 = NaN.
    Response is gzip-compressed. ~200-800KB at 0.05deg for 3 fields.
    """
    import numpy as np
    import gzip as gzip_mod
    import struct
    model_name = request.args.get('model', 'hrrr')
    cycle = request.args.get('cycle', 'latest')
    fhr = int(request.args.get('fhr', 0))
    product = request.args.get('product', '')
    field = request.args.get('field', '')
    level = request.args.get('level', None)

    mgr = get_manager_from_request() or data_manager
    if mgr is None:
        return jsonify({'error': 'No data manager'}), 503

    cycle_key = mgr.resolve_cycle(cycle, fhr) if hasattr(mgr, 'resolve_cycle') else cycle
    if cycle_key is None:
        return jsonify({'error': 'No data loaded'}), 404
    if not mgr.ensure_loaded(cycle_key, fhr):
        return jsonify({'error': f'FHR {fhr} not available'}), 404
    fhr_data = mgr.get_forecast_hour(cycle_key, fhr)
    if fhr_data is None:
        return jsonify({'error': f'FHR {fhr} not loaded'}), 404

    from core.map_overlay import OVERLAY_FIELDS, PRODUCT_PRESETS, _apply_transform

    # Determine fields to sample
    if product:
        spec = PRODUCT_PRESETS.get(product)
        if not spec:
            return jsonify({'error': f'Unknown product: {product}'}), 400
        field_ids = [spec.fill_field]
        if spec.contours:
            field_ids += [c.field_id for c in spec.contours]
        if spec.hover_extra:
            field_ids += [f for f in spec.hover_extra if f not in field_ids]
    elif field:
        field_ids = [field]
    else:
        field_ids = ['t2m']

    # Output grid: 0.05 deg over CONUS (full-res feel, compact binary)
    STEP = 0.05
    out_lats = np.arange(21.0, 53.001, STEP)
    out_lons = np.arange(-135.0, -59.999, STEP)
    n_rows = len(out_lats)
    n_cols = len(out_lons)

    # Build native grid index mapping
    native_lats = np.asarray(fhr_data.lats)
    native_lons = np.asarray(fhr_data.lons)

    if native_lats.ndim == 1 and native_lons.ndim == 1:
        lat_indices = np.searchsorted(native_lats if native_lats[0] < native_lats[-1] else native_lats[::-1], out_lats).clip(0, len(native_lats) - 1)
        if native_lats[0] > native_lats[-1]:
            lat_indices = len(native_lats) - 1 - lat_indices
        lon_indices = np.searchsorted(native_lons if native_lons[0] < native_lons[-1] else native_lons[::-1], out_lons).clip(0, len(native_lons) - 1)
        if native_lons[0] > native_lons[-1]:
            lon_indices = len(native_lons) - 1 - lon_indices
        use_2d = False
        domain_mask_2d = None  # no masking for regular grids
    else:
        try:
            from scipy.spatial import cKDTree
            tree = cKDTree(np.column_stack([native_lats.ravel(), native_lons.ravel()]))
            out_mesh_lat, out_mesh_lon = np.meshgrid(out_lats, out_lons, indexing='ij')
            dists, flat_indices = tree.query(np.column_stack([out_mesh_lat.ravel(), out_mesh_lon.ravel()]))
            flat_indices = flat_indices.reshape(n_rows, n_cols)
            # Mask points too far from native grid (HRRR ~3km ≈ 0.03°, threshold ~0.1°)
            domain_mask_2d = dists.reshape(n_rows, n_cols) > 0.1
            use_2d = True
        except ImportError:
            flat_lats = native_lats.ravel().astype(np.float32)
            flat_lons = native_lons.ravel().astype(np.float32)
            flat_indices = np.zeros((n_rows, n_cols), dtype=np.int64)
            for i, olat in enumerate(out_lats):
                for j, olon in enumerate(out_lons):
                    dist = (flat_lats - olat)**2 + (flat_lons - olon)**2
                    flat_indices[i, j] = np.argmin(dist)
            domain_mask_2d = None
            use_2d = True

    fields_meta = []
    binary_chunks = []
    NAN_SENTINEL = 65535

    for fid in field_ids:
        fspec = OVERLAY_FIELDS.get(fid)
        if not fspec:
            continue
        try:
            if fspec.derived_from:
                components = []
                for comp_name in fspec.derived_from:
                    arr = getattr(fhr_data, comp_name, None)
                    if arr is None:
                        break
                    if arr.ndim == 3 and level is not None:
                        plevs = getattr(fhr_data, 'pressure_levels', None)
                        if plevs is not None:
                            lvl_idx = int(np.argmin(np.abs(np.asarray(plevs) - int(level))))
                            arr = arr[lvl_idx]
                        else:
                            break
                    elif arr.ndim == 3:
                        break
                    components.append(np.asarray(arr, dtype=np.float32))
                if len(components) < len(fspec.derived_from):
                    continue
                # Field-specific derivation (mirrors map_overlay.py)
                if fid in ('wind_speed_10m', 'wind_speed') and len(components) == 2:
                    full_grid = np.sqrt(components[0]**2 + components[1]**2)
                elif fid == 'rh_surface' and len(components) == 2:
                    t_c = components[0] - 273.15
                    td_c = components[1] - 273.15
                    full_grid = np.clip(100.0 * np.exp(17.625 * td_c / (243.04 + td_c)) / np.exp(17.625 * t_c / (243.04 + t_c)), 0, 100)
                elif fid == 'wind_chill' and len(components) == 3:
                    t_f = (components[0] - 273.15) * 9.0 / 5.0 + 32.0
                    ws_mph = np.sqrt(components[1]**2 + components[2]**2) * 2.23694
                    wc = 35.74 + 0.6215 * t_f - 35.75 * np.power(np.maximum(ws_mph, 0.5), 0.16) + 0.4275 * t_f * np.power(np.maximum(ws_mph, 0.5), 0.16)
                    full_grid = np.where(t_f <= 50, wc, t_f)
                elif fid == 'heat_index' and len(components) == 2:
                    t_f = (components[0] - 273.15) * 9.0 / 5.0 + 32.0
                    td_c = components[1] - 273.15
                    rh = np.clip(100.0 * np.exp(17.625 * td_c / (243.04 + td_c)) / np.exp(17.625 * (components[0] - 273.15) / (243.04 + (components[0] - 273.15))), 0, 100)
                    hi = (-42.379 + 2.04901523 * t_f + 10.14333127 * rh - 0.22475541 * t_f * rh - 0.00683783 * t_f**2 - 0.05481717 * rh**2 + 0.00122874 * t_f**2 * rh + 0.00085282 * t_f * rh**2 - 0.00000199 * t_f**2 * rh**2)
                    full_grid = np.where(t_f >= 80, hi, t_f)
                elif fid in ('hdw', 'hdw_paired') and len(components) == 4:
                    # HDW via overlay engine — paired or USFS mode
                    cache_dir = mgr.cache_dir if hasattr(mgr, 'cache_dir') else ''
                    oe = _get_overlay_engine(model_name, cache_dir)
                    full_grid = oe._compute_hdw(fhr_data, components, paired=(fid == 'hdw_paired'))
                elif len(components) == 2:
                    full_grid = np.sqrt(components[0]**2 + components[1]**2)
                else:
                    full_grid = components[0]
            else:
                arr = getattr(fhr_data, fspec.attr_name, None)
                if arr is None:
                    continue
                if arr.ndim == 3 and fspec.needs_level and level is not None:
                    plevs = getattr(fhr_data, 'pressure_levels', None)
                    if plevs is not None:
                        lvl_idx = int(np.argmin(np.abs(np.asarray(plevs) - int(level))))
                        arr = arr[lvl_idx]
                    else:
                        continue
                full_grid = np.asarray(arr, dtype=np.float32)

            full_grid = _apply_transform(full_grid, fspec.transform)

            if not use_2d:
                sampled = full_grid[np.ix_(lat_indices, lon_indices)]
            else:
                sampled = full_grid.ravel()[flat_indices]

            # Mask out-of-domain pixels for curvilinear grids (HRRR/RRFS)
            if domain_mask_2d is not None:
                sampled = sampled.copy()
                sampled[domain_mask_2d] = np.nan

            # Compute vmin/vmax from actual data (robust: 0.5th-99.5th percentile)
            finite_vals = sampled[np.isfinite(sampled)]
            if len(finite_vals) == 0:
                continue
            vmin = float(np.percentile(finite_vals, 0.5))
            vmax = float(np.percentile(finite_vals, 99.5))
            if vmax <= vmin:
                vmax = vmin + 1.0

            # Encode to uint16: 0-65534 = data range, 65535 = NaN
            normalized = (sampled - vmin) / (vmax - vmin)
            encoded = np.clip(normalized * 65534, 0, 65534).astype(np.uint16)
            encoded[~np.isfinite(sampled)] = NAN_SENTINEL

            fields_meta.append({
                'field': fid,
                'name': fspec.name,
                'units': fspec.units,
                'vmin': round(vmin, 2),
                'vmax': round(vmax, 2),
            })
            binary_chunks.append(encoded.tobytes())
        except Exception:
            continue

    # Build binary response: [4B header_len_LE][header JSON][field0 uint16][field1 uint16]...
    header = json.dumps({
        'bounds': {'lat_min': 21.0, 'lat_max': 53.0, 'lon_min': -135.0, 'lon_max': -60.0},
        'rows': n_rows,
        'cols': n_cols,
        'lat_step': STEP,
        'lon_step': STEP,
        'fields': fields_meta,
    }).encode('utf-8')
    # Pad header to even length for uint16 alignment
    if len(header) % 2 != 0:
        header += b' '

    buf = struct.pack('<I', len(header)) + header
    for chunk in binary_chunks:
        buf += chunk

    compressed = gzip_mod.compress(buf, compresslevel=6)

    return Response(compressed, mimetype='application/octet-stream',
                    headers={'Content-Encoding': 'gzip', 'Cache-Control': 'no-store'})


# Legacy endpoint for compatibility
@app.route('/api/info')
def api_info():
    """Legacy endpoint - returns available times."""
    mgr = get_manager_from_request() or data_manager
    times = mgr.get_available_times()
    return jsonify({
        'times': times,
        'hours': [t['fhr'] for t in times],
        'styles': XSECT_STYLES,
    })

@app.route('/api/votes')
def api_votes():
    """Get current vote counts for all styles."""
    return jsonify(load_votes())

@app.route('/api/vote', methods=['POST'])
def api_vote():
    """Submit a vote for a style."""
    try:
        data = request.get_json()
        style = data.get('style')
        vote = data.get('vote')  # 'up' or 'down'

        if not style or vote not in ('up', 'down'):
            return jsonify({'error': 'Invalid vote data'}), 400

        votes = load_votes()
        if style not in votes:
            votes[style] = {'up': 0, 'down': 0}

        votes[style][vote] += 1
        save_votes(votes)

        return jsonify(votes[style])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/requests')
def api_requests():
    """Get all feature requests."""
    return jsonify(load_requests())

@app.route('/api/request', methods=['POST'])
def api_request():
    """Submit a new feature request."""
    try:
        data = request.get_json()
        name = data.get('name', '').strip()[:100]  # Limit name length
        text = data.get('text', '').strip()[:1000]  # Limit text length

        if not text:
            return jsonify({'error': 'Request text is required'}), 400

        save_request(name, text)
        logger.info(f"New feature request from {name or 'Anonymous'}: {text[:50]}...")

        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/request_cycle', methods=['POST'])
@rate_limit
def api_request_cycle():
    """Download specific FHR range for a date/init cycle."""

    date_str = request.args.get('date', '')  # YYYYMMDD
    hour = int(request.args.get('hour', -1))
    fhr_start = int(request.args.get('fhr_start', 0))
    fhr_end = int(request.args.get('fhr_end', request.args.get('max_fhr', 18)))

    if not date_str:
        return jsonify({'error': 'date required (YYYYMMDD)'}), 400
    if hour < 0 or hour > 23:
        return jsonify({'error': 'hour required (0-23)'}), 400

    try:
        datetime.strptime(date_str, '%Y%m%d')
    except ValueError:
        return jsonify({'error': 'Invalid date format, use YYYYMMDD'}), 400

    mgr = get_manager_from_request() or data_manager
    model_name = mgr.model_name
    cycle_key = f"{date_str}/{hour:02d}z"

    # Determine source label + source preference for archive requests
    from datetime import timezone
    date_dt = datetime.strptime(f"{date_str}{hour:02d}", '%Y%m%d%H').replace(tzinfo=timezone.utc)
    age_hours = (datetime.now(timezone.utc) - date_dt).total_seconds() / 3600
    source_preference = None
    if model_name == 'hrrr':
        if age_hours > 48:
            source = "AWS archive"
            source_preference = ['aws', 'pando', 'nomads']
        else:
            source = "NOMADS"
    elif model_name == 'rrfs':
        source = "AWS"
        source_preference = ['aws']
    elif model_name == 'gfs':
        source = "NOMADS/NCEP"
        if age_hours > 48:
            source = "NCEP backup"
            source_preference = ['ftpprd', 'nomads']
    else:
        source = "primary sources"

    # Download in background with progress tracking — load each FHR as it arrives
    def download_cycle():
        from smart_hrrr.orchestrator import download_gribs_parallel
        from smart_hrrr.io import create_output_structure

        op_id = f"download:{model_name}:{cycle_key}"
        fhrs = list(range(fhr_start, fhr_end + 1))
        completed = [0]
        downloaded_fhrs = []
        in_flight = set()

        def on_fhr_start(fhr):
            in_flight.add(fhr)
            active = ', '.join(f'F{f:02d}' for f in sorted(in_flight))
            progress_update(op_id, completed[0], len(fhrs),
                            f"Downloading {active} from {source}...")

        def on_fhr_done(fhr, ok):
            in_flight.discard(fhr)
            completed[0] += 1
            if ok:
                downloaded_fhrs.append(fhr)
            active = ', '.join(f'F{f:02d}' for f in sorted(in_flight))
            detail = f"F{fhr:02d} {'OK' if ok else 'FAILED'}"
            if active:
                detail += f" — downloading {active}"
            progress_update(op_id, completed[0], len(fhrs), detail)

        try:
            create_output_structure(model_name, date_str, hour)
            fhr_label = f"F{fhr_start:02d}-F{fhr_end:02d}" if fhr_start != 0 or fhr_end != 18 else f"{len(fhrs)} FHRs"
            progress_update(op_id, 0, len(fhrs), f"Connecting to {source}...",
                            label=f"Downloading {model_name.upper()} {cycle_key} ({fhr_label})")
            results = download_gribs_parallel(
                model=model_name,
                date_str=date_str,
                cycle_hour=hour,
                forecast_hours=fhrs,
                max_threads=4,
                on_complete=on_fhr_done,
                on_start=on_fhr_start,
                should_cancel=lambda: is_cancelled(op_id),
                source_preference=source_preference,
            )
            if is_cancelled(op_id):
                logger.info(f"Download CANCELLED for {model_name} {cycle_key}")
                PROGRESS[op_id]['detail'] = 'Cancelled'
                progress_done(op_id)
                CANCEL_FLAGS.pop(op_id, None)
                return

            success = sum(1 for ok in results.values() if ok)
            logger.info(f"Cycle request {model_name} {cycle_key}: {success}/{len(fhrs)} forecast hours downloaded")

            # Immediately load the downloaded FHRs into memory
            if downloaded_fhrs:
                mgr.scan_available_cycles()
                ck = f"{date_str}_{hour:02d}z"
                ARCHIVE_CACHE_KEYS.add(ck)
                load_id = f"load:{model_name}:{cycle_key}"
                progress_update(load_id, 0, len(downloaded_fhrs), "Loading...",
                                label=f"Loading {model_name.upper()} {cycle_key}")
                for i, fhr in enumerate(sorted(downloaded_fhrs)):
                    try:
                        mgr.ensure_loaded(ck, fhr)
                        progress_update(load_id, i + 1, len(downloaded_fhrs), f"Loaded F{fhr:02d}")
                    except Exception as e:
                        logger.warning(f"Failed to load {ck} F{fhr:02d}: {e}")
                progress_done(load_id)
                logger.info(f"Loaded {len(downloaded_fhrs)} FHRs for {model_name} {cycle_key}")
        except Exception as e:
            logger.warning(f"Cycle request {model_name} {cycle_key} failed: {e}")
        finally:
            progress_done(op_id)

    t = threading.Thread(target=download_cycle, daemon=True)
    t.start()

    n_fhrs = fhr_end - fhr_start + 1
    est_minutes = max(2, n_fhrs * (0.3 if age_hours <= 48 else 0.8))
    return jsonify({
        'success': True,
        'message': f'Downloading {cycle_key} F{fhr_start:02d}-F{fhr_end:02d} from {source} (~{est_minutes:.0f} min)',
        'cycle_key': cycle_key,
        'source': source,
        'est_minutes': round(est_minutes),
        'fhr_start': fhr_start,
        'fhr_end': fhr_end,
    })

@app.route('/api/favorites')
def api_favorites():
    """Get all community favorites."""
    return jsonify(load_favorites())

@app.route('/api/favorite', methods=['POST'])
def api_favorite_save():
    """Save a new community favorite."""
    try:
        data = request.get_json()
        name = data.get('name', '').strip()[:50]  # Limit name length
        label = data.get('label', '').strip()[:200]  # Limit label length
        config = data.get('config', {})

        if not name:
            return jsonify({'error': 'Name is required'}), 400

        fav_id = save_favorite(name, config, label)
        logger.info(f"New favorite saved: {name}")

        return jsonify({'success': True, 'id': fav_id})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/favorite/<fav_id>', methods=['DELETE'])
def api_favorite_delete(fav_id):
    """Delete a community favorite."""
    try:
        delete_favorite(fav_id)
        logger.info(f"Favorite deleted: {fav_id}")
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# =============================================================================
# Oregon WFO Agent Swarm API Endpoints
# =============================================================================

@app.route('/api/v1/oregon/zones')
@rate_limit
def api_v1_oregon_zones():
    """List all Oregon WFO coverage zones."""
    try:
        from tools.agent_tools.data.oregon_zones import list_zones
        from tools.agent_tools.wfo_swarm.scheduler import output_store

        zones = list_zones()
        for z in zones:
            status = output_store.get_status(z["zone_id"])
            z["status"] = status.get("status", "not_run") if status else "not_run"
            z["last_cycle"] = status.get("cycle", "") if status else ""
        return jsonify(zones)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/v1/oregon/zones/<zone_id>/bulletin')
@rate_limit
def api_v1_oregon_zone_bulletin(zone_id):
    """Get the latest fire weather bulletin for a zone."""
    try:
        from tools.agent_tools.wfo_swarm.scheduler import get_zone_bulletin
        bulletin = get_zone_bulletin(zone_id)
        if bulletin is None:
            return jsonify({
                'error': f'No bulletin available for {zone_id}. Run the swarm first.',
            }), 404
        return jsonify(bulletin)
    except KeyError:
        return jsonify({'error': f'Unknown zone: {zone_id}'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/v1/oregon/zones/<zone_id>/forecast/<town>')
@rate_limit
def api_v1_oregon_zone_forecast(zone_id, town):
    """Get a specific town's forecast from the latest bulletin."""
    try:
        from tools.agent_tools.wfo_swarm.scheduler import get_zone_town_forecast
        forecast = get_zone_town_forecast(zone_id, town)
        if forecast is None:
            return jsonify({
                'error': f"No forecast for '{town}' in {zone_id}.",
            }), 404
        return jsonify(forecast)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/v1/oregon/zones/<zone_id>/ranking')
@rate_limit
def api_v1_oregon_zone_ranking(zone_id):
    """Get all towns ranked by fire risk for a zone."""
    try:
        from tools.agent_tools.wfo_swarm.scheduler import get_zone_risk_ranking
        ranking = get_zone_risk_ranking(zone_id)
        if ranking is None:
            return jsonify({
                'error': f'No ranking available for {zone_id}.',
            }), 404
        return jsonify(ranking)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/v1/oregon/scan')
@rate_limit
def api_v1_oregon_scan():
    """Quick fire weather scan across all 7 Oregon zones."""
    try:
        from tools.agent_tools.wfo_swarm.scheduler import oregon_fire_scan
        return jsonify(oregon_fire_scan())
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/v1/oregon/bulletin')
@rate_limit
def api_v1_oregon_bulletin():
    """State-level aggregated fire weather bulletin for all Oregon zones."""
    try:
        from tools.agent_tools.wfo_swarm.scheduler import oregon_state_bulletin
        return jsonify(oregon_state_bulletin())
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# =============================================================================
# MAIN
# =============================================================================

def main():
    global data_manager

    parser = argparse.ArgumentParser(description='Cross-Section Dashboard (multi-model)')
    parser.add_argument('--auto-update', action='store_true', help='Download latest data before starting')
    parser.add_argument('--preload', type=int, default=12, help='Number of latest cycles to pre-load (mmap makes all cheap)')
    parser.add_argument('--max-hours', type=int, default=18, help='Max forecast hour to download')
    parser.add_argument('--port', type=int, default=5000, help='Server port')
    parser.add_argument('--host', type=str, default='0.0.0.0', help='Server host')
    parser.add_argument('--models', type=str, default='hrrr',
                        help='Comma-separated list of models to enable (e.g. hrrr,gfs)')
    parser.add_argument('--grib-workers', type=int, default=_env_int('XSECT_GRIB_WORKERS', 4),
                        help='Workers for uncached GRIB->mmap conversion (default: env XSECT_GRIB_WORKERS or 4)')
    parser.add_argument('--preload-workers', type=int, default=_env_int('XSECT_PRELOAD_WORKERS', 20),
                        help='Workers for cached mmap loads (default: env XSECT_PRELOAD_WORKERS or 20)')

    args = parser.parse_args()
    # Register requested models
    enabled_models = [m.strip().lower() for m in args.models.split(',') if m.strip()]
    for model_name in enabled_models:
        if model_name not in model_registry.managers:
            model_registry.register(model_name)

    # Apply runtime worker tuning to all managers
    grib_workers = max(1, args.grib_workers)
    preload_workers = max(1, args.preload_workers)
    global GRIB_POOL_WORKERS
    GRIB_POOL_WORKERS = grib_workers
    for _, mgr in model_registry.managers.items():
        mgr.GRIB_WORKERS = grib_workers
        mgr.PRELOAD_WORKERS = preload_workers

    data_manager = model_registry.get('hrrr')  # Keep backward compat alias

    # Optionally download fresh data (HRRR only for now)
    if args.auto_update:
        from smart_hrrr.orchestrator import download_latest_cycle

        logger.info("Downloading latest HRRR data...")
        fhrs_to_download = [0, 6, 12, 18]
        fhrs_to_download = [f for f in fhrs_to_download if f <= args.max_hours]

        date_str, hour, results = download_latest_cycle(
            max_hours=max(fhrs_to_download),
            forecast_hours=fhrs_to_download
        )
        if not date_str:
            logger.error("Failed to download data")
            sys.exit(1)
        logger.info(f"Downloaded {sum(results.values())}/{len(fhrs_to_download)} forecast hours")

    # Scan for available cycles across all models
    for model_name, mgr in model_registry.managers.items():
        logger.info(f"Scanning {model_name.upper()} for available cycles...")
        cycles = mgr.scan_available_cycles()
        if cycles:
            logger.info(f"  {model_name.upper()}: {len(cycles)} cycles found")
            for c in cycles[:3]:  # Show first 3
                fhrs_str = ', '.join(f'F{f:02d}' for f in c['available_fhrs'])
                logger.info(f"    {c['display']}: [{fhrs_str}]")
            if len(cycles) > 3:
                logger.info(f"    ... and {len(cycles) - 3} more")
        else:
            logger.info(f"  {model_name.upper()}: No data found")

    # Pre-load latest cycles in background so Flask starts immediately
    if args.preload > 0:
        def _startup_preload():
            time.sleep(2)  # Let Flask bind first
            # HRRR always loads first — it's the primary product
            ordered = sorted(model_registry.managers.items(),
                             key=lambda x: (0 if x[0] == 'hrrr' else 1, x[0]))
            for model_name, mgr in ordered:
                if mgr.available_cycles:
                    logger.info(f"Background: Pre-loading latest {args.preload} {model_name.upper()} cycles...")
                    try:
                        mgr.preload_latest_cycles(n_cycles=args.preload)
                    except Exception as e:
                        logger.warning(f"{model_name.upper()} preload failed: {e}")
        threading.Thread(target=_startup_preload, daemon=True).start()

    # Background re-scan thread: low-latency cycle detection for all models.
    def background_rescan():
        rescan_seconds = max(1, int(os.environ.get("XSECT_RESCAN_SECONDS", "2")))
        while True:
            time.sleep(rescan_seconds)
            for model_name, mgr in model_registry.managers.items():
                try:
                    mgr.scan_available_cycles()
                    mgr.auto_load_latest()
                except Exception as e:
                    logger.warning(f"Background rescan failed for {model_name}: {e}")

            # Evict old NVMe cache + check GRIB disk usage every 10 minutes
            if int(time.time()) % 600 < 60:
                try:
                    cache_evict_old_cycles(model_registry.managers)
                except Exception as e:
                    logger.warning(f"Cache eviction failed: {e}")
                try:
                    usage = get_disk_usage_gb()
                    if usage > DISK_LIMIT_GB:
                        logger.info(f"Disk usage {usage:.1f}GB > {DISK_LIMIT_GB}GB limit, evicting...")
                        disk_evict_least_popular()
                        for _, mgr in model_registry.managers.items():
                            mgr.scan_available_cycles()
                except Exception as e:
                    logger.warning(f"Disk eviction check failed: {e}")

    rescan_thread = threading.Thread(target=background_rescan, daemon=True)
    rescan_thread.start()

    disk_gb = get_disk_usage_gb()
    logger.info("")
    logger.info("=" * 60)
    logger.info("Cross-Section Dashboard")
    logger.info(f"Models: {', '.join(m.upper() for m in enabled_models)}")
    logger.info(f"GRIB backend default: {os.environ.get('XSECT_GRIB_BACKEND', 'auto')}")
    logger.info(f"Workers: grib={grib_workers}, preload={preload_workers}")
    for model_name, mgr in model_registry.managers.items():
        mem_mb = mgr.xsect.get_memory_usage() if mgr.xsect else 0
        logger.info(f"  {model_name.upper()}: {len(mgr.loaded_cycles)} cycles loaded ({mem_mb:.0f} MB)")
    logger.info(f"Disk: {disk_gb:.1f}GB / {DISK_LIMIT_GB}GB")
    logger.info("Auto-refreshing cycle list every 5s (UI)")
    logger.info(f"Open: http://{args.host}:{args.port}")
    logger.info("=" * 60)

    import atexit
    atexit.register(shutdown_render_pool)
    atexit.register(shutdown_grib_pool)

    app.run(host=args.host, port=args.port, threaded=True)

if __name__ == '__main__':
    main()
