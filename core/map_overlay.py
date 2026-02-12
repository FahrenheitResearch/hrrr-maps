"""Map overlay engine — reprojects model fields to regular lat/lon grids.

HRRR/RRFS data lives on Lambert Conformal Conic curvilinear grids (2D lat/lon).
Map overlays need a regular lat/lon grid for WebGL rendering or PNG output.

Approach: precomputed cKDTree index map for nearest-neighbor reprojection.
  - One-time: build tree from 2D lat/lon arrays, query for output grid → indices array
  - Per-request: field.ravel()[indices] — ~10ms

GFS is already on a regular lat/lon grid, so no reprojection is needed.

Performance targets:
  - Binary (float32 for WebGL): ~20ms total
  - PNG (colormapped RGBA):     ~50ms total
"""

import numpy as np
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict, Tuple, Any
import threading
import io


# ---------------------------------------------------------------------------
# Output grid specification
# ---------------------------------------------------------------------------

@dataclass
class OutputGrid:
    """Regular lat/lon grid specification for reprojected output."""
    south: float = 21.0
    north: float = 53.0
    west: float = -135.0
    east: float = -60.0
    dlat: float = 0.03
    dlon: float = 0.03

    @property
    def lats(self) -> np.ndarray:
        return np.arange(self.south, self.north + self.dlat / 2, self.dlat, dtype=np.float32)

    @property
    def lons(self) -> np.ndarray:
        return np.arange(self.west, self.east + self.dlon / 2, self.dlon, dtype=np.float32)

    @property
    def shape(self) -> Tuple[int, int]:
        return (len(self.lats), len(self.lons))


CONUS_GRID = OutputGrid()  # Default CONUS grid


# ---------------------------------------------------------------------------
# Field specifications + registry
# ---------------------------------------------------------------------------

@dataclass
class FieldSpec:
    """Metadata for one overlay-able field."""
    id: str
    name: str
    units: str
    category: str       # 'surface', 'isobaric', 'derived'
    attr_name: str      # ForecastHourData attribute, or None for derived
    default_cmap: str
    default_vmin: float
    default_vmax: float
    transform: str = None         # 'K_to_C', 'ms_to_kt', etc.
    derived_from: tuple = None    # e.g. ('u10m', 'v10m') for wind speed
    needs_level: bool = False     # True for isobaric fields


OVERLAY_FIELDS: Dict[str, FieldSpec] = {
    # --- Surface fields (from GRIB extraction) ---
    't2m': FieldSpec('t2m', '2m Temperature', '\u00b0C', 'surface', 't2m',
                     'RdYlBu_r', -40, 45, transform='K_to_C'),
    'd2m': FieldSpec('d2m', '2m Dew Point', '\u00b0C', 'surface', 'd2m',
                     'YlGn', -30, 30, transform='K_to_C'),
    'wind_speed_10m': FieldSpec('wind_speed_10m', '10m Wind Speed', 'kt', 'derived', None,
                                'plasma', 0, 60, derived_from=('u10m', 'v10m'), transform='ms_to_kt'),
    'refc': FieldSpec('refc', 'Reflectivity', 'dBZ', 'surface', 'refc',
                      'NWSReflectivity', -10, 70),
    'cape_sfc': FieldSpec('cape_sfc', 'Surface CAPE', 'J/kg', 'surface', 'cape_sfc',
                          'hot_r', 0, 4000),
    'mslp': FieldSpec('mslp', 'Sea Level Pressure', 'hPa', 'surface', 'mslp',
                      'coolwarm', 990, 1040),
    'vis': FieldSpec('vis', 'Visibility', 'mi', 'surface', 'vis',
                     'gray_r', 0, 10, transform='m_to_mi'),
    'gust': FieldSpec('gust', 'Wind Gust', 'kt', 'surface', 'gust',
                      'plasma', 0, 80, transform='ms_to_kt'),
    'prate': FieldSpec('prate', 'Precip Rate', 'mm/hr', 'surface', 'prate',
                       'Blues', 0, 25, transform='kgm2s_to_mmhr'),
    # --- Isobaric fields (already in mmap, no new extraction) ---
    'temperature': FieldSpec('temperature', 'Temperature', '\u00b0C', 'isobaric', 'temperature',
                             'RdYlBu_r', -60, 30, transform='K_to_C', needs_level=True),
    'wind_speed': FieldSpec('wind_speed', 'Wind Speed', 'kt', 'derived', None,
                            'plasma', 0, 120, derived_from=('u_wind', 'v_wind'),
                            transform='ms_to_kt', needs_level=True),
    'rh': FieldSpec('rh', 'Relative Humidity', '%', 'isobaric', 'rh',
                    'BrBG', 0, 100, needs_level=True),
    'geopotential_height': FieldSpec('geopotential_height', 'Heights', 'dam', 'isobaric',
                                     'geopotential_height', 'viridis', 480, 580,
                                     transform='gpm_to_dam', needs_level=True),
    'vorticity': FieldSpec('vorticity', 'Abs Vorticity', '\u00d710\u207b\u2075/s', 'isobaric',
                           'vorticity', 'RdBu_r', -30, 30,
                           transform='scale_1e5', needs_level=True),
    'omega': FieldSpec('omega', 'Vertical Velocity', 'hPa/hr', 'isobaric', 'omega',
                       'RdBu_r', -20, 20, transform='Pas_to_hPahr', needs_level=True),
    'theta': FieldSpec('theta', 'Potential Temp', 'K', 'isobaric', 'theta',
                       'Spectral_r', 280, 360, needs_level=True),
    # --- Derived surface fields ---
    'rh_surface': FieldSpec('rh_surface', 'Surface RH', '%', 'derived', None,
                            'BrBG', 0, 100, derived_from=('t2m', 'd2m')),
    'wind_chill': FieldSpec('wind_chill', 'Wind Chill', '\u00b0F', 'derived', None,
                            'cool', -40, 50, derived_from=('t2m', 'u10m', 'v10m')),
    'heat_index': FieldSpec('heat_index', 'Heat Index', '\u00b0F', 'derived', None,
                            'YlOrRd', 70, 130, derived_from=('t2m', 'd2m')),
    'hdw': FieldSpec('hdw', 'HDW (USFS)', '', 'derived', None,
                     'YlOrRd', 0, 200, derived_from=('t2m', 'd2m', 'u10m', 'v10m')),
    'hdw_paired': FieldSpec('hdw_paired', 'HDW (Paired)', '', 'derived', None,
                            'YlOrRd', 0, 200, derived_from=('t2m', 'd2m', 'u10m', 'v10m')),
}


# ---------------------------------------------------------------------------
# Composite map product specs
# ---------------------------------------------------------------------------

@dataclass
class ContourSpec:
    """Specification for contour lines on a composite map product."""
    field_id: str
    interval: float
    color: str = 'black'
    linewidth: float = 1.0
    label: bool = True
    levels: list = None

@dataclass
class BarbSpec:
    """Specification for wind barbs on a composite map product."""
    u_attr: str
    v_attr: str
    level: int = None
    thin: int = 25
    color: str = 'black'
    length: float = 5.5

@dataclass
class CompositeSpec:
    """A complete map product specification."""
    id: str
    name: str
    description: str
    fill_field: str = None
    fill_cmap: str = None
    fill_vmin: float = None
    fill_vmax: float = None
    contours: list = None
    barbs: 'BarbSpec' = None
    level: int = None
    hover_extra: list = None  # Extra field IDs to include in hover tooltip


PRODUCT_PRESETS: Dict[str, CompositeSpec] = {
    'surface_analysis': CompositeSpec(
        id='surface_analysis',
        name='Surface Analysis',
        description='2m temp fill + MSLP contours + 10m wind barbs',
        fill_field='t2m', fill_cmap='RdYlBu_r', fill_vmin=-40, fill_vmax=45,
        contours=[ContourSpec('mslp', interval=4, color='#333333', linewidth=1.2, label=True)],
        barbs=BarbSpec('u10m', 'v10m', color='#333333'),
    ),
    'radar_composite': CompositeSpec(
        id='radar_composite',
        name='Reflectivity',
        description='Composite reflectivity + MSLP contours',
        fill_field='refc', fill_cmap='NWSReflectivity', fill_vmin=-10, fill_vmax=70,
        contours=[ContourSpec('mslp', interval=4, color='white', linewidth=0.8)],
    ),
    'severe_weather': CompositeSpec(
        id='severe_weather',
        name='Severe Weather',
        description='CAPE fill + wind barbs + MSLP contours',
        fill_field='cape_sfc', fill_cmap='hot_r', fill_vmin=0, fill_vmax=4000,
        contours=[ContourSpec('mslp', interval=4, color='#333333')],
        barbs=BarbSpec('u10m', 'v10m', color='#333333'),
    ),
    'upper_500': CompositeSpec(
        id='upper_500',
        name='500mb Analysis',
        description='Temperature fill + height contours + wind barbs at 500 hPa',
        fill_field='temperature', fill_cmap='RdYlBu_r', fill_vmin=-40, fill_vmax=10,
        contours=[ContourSpec('geopotential_height', interval=6, color='black', linewidth=1.5, label=True)],
        barbs=BarbSpec('u_wind', 'v_wind', level=500, thin=20, color='#333333'),
        level=500,
    ),
    'upper_250': CompositeSpec(
        id='upper_250',
        name='250mb Jet',
        description='Wind speed fill + height contours at 250 hPa',
        fill_field='wind_speed', fill_cmap='plasma', fill_vmin=0, fill_vmax=120,
        contours=[ContourSpec('geopotential_height', interval=12, color='white', linewidth=1.0, label=True)],
        barbs=BarbSpec('u_wind', 'v_wind', level=250, thin=15, color='white'),
        level=250,
    ),
    'moisture': CompositeSpec(
        id='moisture',
        name='Moisture',
        description='Dew point fill + MSLP contours + 10m wind barbs',
        fill_field='d2m', fill_cmap='YlGn', fill_vmin=-30, fill_vmax=30,
        contours=[ContourSpec('mslp', interval=4, color='#333333')],
        barbs=BarbSpec('u10m', 'v10m', color='#333333'),
    ),
    'fire_weather': CompositeSpec(
        id='fire_weather',
        name='Fire Weather (HDW)',
        description='Hot-Dry-Windy Index fill + 10m wind barbs',
        fill_field='hdw', fill_cmap='YlOrRd', fill_vmin=0, fill_vmax=200,
        barbs=BarbSpec('u10m', 'v10m', color='#333333'),
        hover_extra=['hdw_paired', 't2m', 'rh_surface', 'wind_speed_10m'],
    ),
    'precip': CompositeSpec(
        id='precip',
        name='Precipitation',
        description='Precip rate fill + MSLP contours',
        fill_field='prate', fill_cmap='Blues', fill_vmin=0, fill_vmax=25,
        contours=[ContourSpec('mslp', interval=4, color='#333333')],
    ),
}


# ---------------------------------------------------------------------------
# Unit transforms
# ---------------------------------------------------------------------------

def _apply_transform(data: np.ndarray, transform: str) -> np.ndarray:
    """Apply unit conversion in-place on a float32 copy."""
    if transform is None:
        return data
    if transform == 'K_to_C':
        return data - 273.15
    if transform == 'ms_to_kt':
        return data * 1.94384
    if transform == 'm_to_mi':
        return data / 1609.34
    if transform == 'kgm2s_to_mmhr':
        return data * 3600.0
    if transform == 'gpm_to_dam':
        return data / 10.0
    if transform == 'scale_1e5':
        return data * 1e5
    if transform == 'Pas_to_hPahr':
        return data * (3600.0 / 100.0)
    return data


# ---------------------------------------------------------------------------
# Colormaps — generated from matplotlib, cached as uint8 RGBA arrays
# ---------------------------------------------------------------------------

_CMAP_CACHE: Dict[str, np.ndarray] = {}
_CMAP_LOCK = threading.Lock()


def _nws_reflectivity_cmap() -> np.ndarray:
    """Custom NWS-style reflectivity colormap (256x4 uint8 RGBA)."""
    lut = np.zeros((256, 4), dtype=np.uint8)
    lut[:, 3] = 255  # Opaque by default

    # Map dBZ range -10..70 to 0..255 indices
    # Approx: index = (dBZ + 10) * 255/80
    # Below 5 dBZ (idx ~48): transparent
    lut[:48, 3] = 0
    # 5-20 dBZ: greens
    lut[48:96, 0] = 0
    lut[48:96, 1] = np.linspace(100, 255, 48).astype(np.uint8)
    lut[48:96, 2] = 0
    # 20-35 dBZ: yellows
    lut[96:144, 0] = np.linspace(200, 255, 48).astype(np.uint8)
    lut[96:144, 1] = np.linspace(255, 200, 48).astype(np.uint8)
    lut[96:144, 2] = 0
    # 35-50 dBZ: reds
    lut[144:192, 0] = 255
    lut[144:192, 1] = np.linspace(150, 0, 48).astype(np.uint8)
    lut[144:192, 2] = 0
    # 50-65 dBZ: magentas
    lut[192:240, 0] = np.linspace(255, 200, 48).astype(np.uint8)
    lut[192:240, 1] = 0
    lut[192:240, 2] = np.linspace(100, 255, 48).astype(np.uint8)
    # 65+ dBZ: white
    lut[240:, :3] = 255
    return lut


def get_colormap_lut(cmap_name: str) -> np.ndarray:
    """Get a 256x4 uint8 RGBA lookup table for a colormap name.

    Supports matplotlib names + custom 'NWSReflectivity'.
    Thread-safe with LRU cache.
    """
    with _CMAP_LOCK:
        if cmap_name in _CMAP_CACHE:
            return _CMAP_CACHE[cmap_name]

    if cmap_name == 'NWSReflectivity':
        lut = _nws_reflectivity_cmap()
    else:
        try:
            import matplotlib.cm as cm
            cmap = cm.get_cmap(cmap_name, 256)
            lut = (cmap(np.linspace(0, 1, 256)) * 255).astype(np.uint8)
        except Exception:
            # Fallback: viridis
            import matplotlib.cm as cm
            cmap = cm.get_cmap('viridis', 256)
            lut = (cmap(np.linspace(0, 1, 256)) * 255).astype(np.uint8)

    with _CMAP_LOCK:
        _CMAP_CACHE[cmap_name] = lut
    return lut


# ---------------------------------------------------------------------------
# Overlay result container
# ---------------------------------------------------------------------------

@dataclass
class OverlayResult:
    """Result of a map overlay render."""
    data: bytes             # Binary payload (float32 or PNG)
    content_type: str
    nx: int
    ny: int
    south: float
    north: float
    west: float
    east: float
    vmin: float
    vmax: float
    units: str
    nan_value: float = -9999.0

    def headers(self) -> dict:
        return {
            'X-Grid-Nx': str(self.nx),
            'X-Grid-Ny': str(self.ny),
            'X-Bounds-South': f'{self.south:.4f}',
            'X-Bounds-North': f'{self.north:.4f}',
            'X-Bounds-West': f'{self.west:.4f}',
            'X-Bounds-East': f'{self.east:.4f}',
            'X-Value-Min': f'{self.vmin:.2f}',
            'X-Value-Max': f'{self.vmax:.2f}',
            'X-Units': self.units,
            'X-NaN-Value': str(self.nan_value),
            'Access-Control-Expose-Headers': (
                'X-Grid-Nx, X-Grid-Ny, X-Bounds-South, X-Bounds-North, '
                'X-Bounds-West, X-Bounds-East, X-Value-Min, X-Value-Max, '
                'X-Units, X-NaN-Value'
            ),
        }


# ---------------------------------------------------------------------------
# MapOverlayEngine — one per model, thread-safe, lazily builds projection map
# ---------------------------------------------------------------------------

class MapOverlayEngine:
    """Reprojects model fields onto a regular lat/lon grid for map overlays.

    One instance per model. Thread-safe. Lazily builds and caches the
    cKDTree projection index map on first use.
    """

    def __init__(self, model_name: str, cache_dir: str, output_grid: OutputGrid = None):
        self.model_name = model_name
        self.cache_dir = Path(cache_dir) if cache_dir else None
        self.grid = output_grid or CONUS_GRID
        self._proj_indices: Optional[np.ndarray] = None
        self._proj_mask: Optional[np.ndarray] = None  # True = out-of-domain (too far from native grid)
        self._proj_lock = threading.Lock()
        self._is_regular_grid: Optional[bool] = None
        # For regular grids (GFS): lat/lon 1D arrays for direct indexing
        self._reg_lat_1d: Optional[np.ndarray] = None
        self._reg_lon_1d: Optional[np.ndarray] = None

    def _ensure_projection_map(self, fhr_data) -> Optional[np.ndarray]:
        """Build or load the projection index map. Thread-safe."""
        if self._proj_indices is not None:
            return self._proj_indices

        with self._proj_lock:
            if self._proj_indices is not None:
                return self._proj_indices

            lats = fhr_data.lats
            lons = fhr_data.lons

            # Detect regular grid (1D lat/lon = GFS)
            if lats.ndim == 1 and lons.ndim == 1:
                self._is_regular_grid = True
                self._reg_lat_1d = lats.astype(np.float64)
                self._reg_lon_1d = lons.astype(np.float64)
                print(f"  MapOverlay [{self.model_name}]: regular grid {len(lats)}x{len(lons)}, no reprojection needed")
                self._proj_indices = np.array([])  # Sentinel: use direct indexing
                return self._proj_indices

            self._is_regular_grid = False

            # Try to load from disk cache
            proj_path = None
            if self.cache_dir:
                proj_path = Path(self.cache_dir) / self.model_name / '_projection_map.npy'
                mask_path = Path(self.cache_dir) / self.model_name / '_projection_mask.npy'
                if proj_path.exists() and mask_path.exists():
                    try:
                        self._proj_indices = np.load(proj_path)
                        self._proj_mask = np.load(mask_path)
                        print(f"  MapOverlay [{self.model_name}]: loaded projection map from cache "
                              f"({self._proj_indices.shape}, {int(self._proj_mask.sum())} masked)")
                        return self._proj_indices
                    except Exception as e:
                        print(f"  MapOverlay [{self.model_name}]: failed to load cached projection map: {e}")
                elif proj_path.exists():
                    # Old cache without mask — rebuild
                    try:
                        proj_path.unlink()
                    except Exception:
                        pass

            # Build cKDTree from 2D lat/lon
            import time
            from scipy.spatial import cKDTree

            t0 = time.time()
            lat_2d = np.asarray(lats, dtype=np.float64)
            lon_2d = np.asarray(lons, dtype=np.float64)

            # Convert lat/lon to 3D Cartesian for accurate KDTree queries
            lat_r = np.deg2rad(lat_2d.ravel())
            lon_r = np.deg2rad(lon_2d.ravel())
            x = np.cos(lat_r) * np.cos(lon_r)
            y = np.cos(lat_r) * np.sin(lon_r)
            z = np.sin(lat_r)
            tree = cKDTree(np.column_stack([x, y, z]))

            # Query for output grid points
            out_lats = self.grid.lats
            out_lons = self.grid.lons
            out_lat_2d, out_lon_2d = np.meshgrid(out_lats, out_lons, indexing='ij')
            olat_r = np.deg2rad(out_lat_2d.ravel())
            olon_r = np.deg2rad(out_lon_2d.ravel())
            ox = np.cos(olat_r) * np.cos(olon_r)
            oy = np.cos(olat_r) * np.sin(olon_r)
            oz = np.sin(olat_r)
            dists, indices = tree.query(np.column_stack([ox, oy, oz]))

            self._proj_indices = indices.astype(np.int32)

            # Build domain mask: points too far from native grid are out-of-domain.
            # HRRR ~3km spacing ≈ 0.027° ≈ 0.00047 rad on unit sphere (Cartesian dist).
            # Threshold at ~2.5× grid spacing to allow some edge tolerance.
            # Cartesian distance on unit sphere for 0.07° ≈ 0.00122
            DIST_THRESHOLD = 0.002  # ~0.11° — generous for HRRR 3km
            self._proj_mask = dists.reshape(self.grid.shape) > DIST_THRESHOLD

            elapsed = time.time() - t0
            n_masked = int(self._proj_mask.sum())
            print(f"  MapOverlay [{self.model_name}]: built projection map "
                  f"{lat_2d.shape} -> {self.grid.shape} in {elapsed:.1f}s "
                  f"({n_masked} out-of-domain pixels masked)")

            # Save to disk (indices + mask)
            if proj_path:
                try:
                    proj_path.parent.mkdir(parents=True, exist_ok=True)
                    np.save(proj_path, self._proj_indices)
                    mask_path = proj_path.parent / '_projection_mask.npy'
                    np.save(mask_path, self._proj_mask)
                except Exception as e:
                    print(f"  MapOverlay: failed to cache projection map: {e}")

            return self._proj_indices

    @staticmethod
    def _get_field(fhr_data, name):
        """Get a field from ForecastHourData, trying lazy surface load if needed."""
        val = getattr(fhr_data, name, None)
        if val is None and hasattr(fhr_data, 'load_surface_field'):
            val = fhr_data.load_surface_field(name)
        return val

    def _extract_field(self, fhr_data, field_spec: FieldSpec, level: int = None) -> Optional[np.ndarray]:
        """Extract a 2D field from ForecastHourData, handling derived fields and level selection."""
        if field_spec.derived_from:
            # Derived field: compute from components
            components = []
            for comp_name in field_spec.derived_from:
                arr = self._get_field(fhr_data, comp_name)
                if arr is None:
                    return None
                if arr.ndim == 3 and level is not None:
                    idx = self._level_index(fhr_data, level)
                    if idx is None:
                        return None
                    arr = arr[idx]
                elif arr.ndim == 3:
                    return None  # Need a level for 3D field
                components.append(np.asarray(arr, dtype=np.float32))

            # Wind speed from u, v
            if field_spec.id in ('wind_speed_10m', 'wind_speed') and len(components) == 2:
                return np.sqrt(components[0]**2 + components[1]**2)
            # Surface RH from t2m (K) and d2m (K) via Magnus formula
            if field_spec.id == 'rh_surface' and len(components) == 2:
                t_c = components[0] - 273.15  # t2m in Celsius
                td_c = components[1] - 273.15  # d2m in Celsius
                rh = 100.0 * np.exp(17.625 * td_c / (243.04 + td_c)) / np.exp(17.625 * t_c / (243.04 + t_c))
                return np.clip(rh, 0, 100)
            # Wind chill from t2m (K) and u10m/v10m (m/s) → result in °F
            if field_spec.id == 'wind_chill' and len(components) == 3:
                t_f = (components[0] - 273.15) * 9.0 / 5.0 + 32.0  # K → °F
                ws_mph = np.sqrt(components[1]**2 + components[2]**2) * 2.23694  # m/s → mph
                wc = 35.74 + 0.6215 * t_f - 35.75 * np.power(np.maximum(ws_mph, 0.5), 0.16) + 0.4275 * t_f * np.power(np.maximum(ws_mph, 0.5), 0.16)
                return np.where(t_f <= 50, wc, t_f)
            # Heat index from t2m (K) and d2m (K) → result in °F
            if field_spec.id == 'heat_index' and len(components) == 2:
                t_f = (components[0] - 273.15) * 9.0 / 5.0 + 32.0
                td_c = components[1] - 273.15
                rh = 100.0 * np.exp(17.625 * td_c / (243.04 + td_c)) / np.exp(17.625 * (components[0] - 273.15) / (243.04 + (components[0] - 273.15)))
                rh = np.clip(rh, 0, 100)
                hi = (-42.379 + 2.04901523 * t_f + 10.14333127 * rh
                      - 0.22475541 * t_f * rh - 0.00683783 * t_f**2
                      - 0.05481717 * rh**2 + 0.00122874 * t_f**2 * rh
                      + 0.00085282 * t_f * rh**2 - 0.00000199 * t_f**2 * rh**2)
                return np.where(t_f >= 80, hi, t_f)
            # HDW (USFS): max(VPD) × max(wind) — separate maxima
            if field_spec.id == 'hdw' and len(components) == 4:
                return self._compute_hdw(fhr_data, components, paired=False)
            # HDW (Paired): max(VPD × wind) — co-located at each level
            if field_spec.id == 'hdw_paired' and len(components) == 4:
                return self._compute_hdw(fhr_data, components, paired=True)
            # Fallback: 2-component wind speed
            if len(components) == 2:
                return np.sqrt(components[0]**2 + components[1]**2)
            return None

        # Direct field
        arr = self._get_field(fhr_data, field_spec.attr_name)
        if arr is None:
            return None
        arr = np.asarray(arr, dtype=np.float32)

        if arr.ndim == 3 and level is not None:
            idx = self._level_index(fhr_data, level)
            if idx is None:
                return None
            arr = arr[idx]
        elif arr.ndim == 3:
            return None  # 3D field needs a level

        return arr

    def _compute_hdw(self, fhr_data, surface_components, paired: bool = False) -> np.ndarray:
        """Compute HDW in lowest ~50 hPa AGL (Srock et al.).

        paired=False (default, USFS-style): max(VPD) × max(wind) — separate maxima.
        paired=True: max(VPD × wind) — co-located maxima at each level.
        Falls back to surface-only if 3D data isn't available.
        """
        t2m, d2m, u10m, v10m = surface_components

        # Check for 3D pressure level data
        plevs = getattr(fhr_data, 'pressure_levels', None)
        t3d = getattr(fhr_data, 'temperature', None)    # (n_lev, ny, nx) K
        td3d = getattr(fhr_data, 'dew_point', None)     # (n_lev, ny, nx) K
        u3d = getattr(fhr_data, 'u_wind', None)          # (n_lev, ny, nx) m/s
        v3d = getattr(fhr_data, 'v_wind', None)          # (n_lev, ny, nx) m/s
        sp = getattr(fhr_data, 'surface_pressure', None)  # (ny, nx) hPa

        has_3d = (plevs is not None and t3d is not None and td3d is not None
                  and u3d is not None and v3d is not None and sp is not None
                  and t3d.ndim == 3)

        if not has_3d:
            # Fallback: surface-only HDW (same for both modes)
            t_c = t2m - 273.15
            td_c = d2m - 273.15
            es = 6.112 * np.exp(17.67 * t_c / (t_c + 243.5))
            ea = 6.112 * np.exp(17.67 * td_c / (td_c + 243.5))
            vpd = np.maximum(es - ea, 0)
            ws = np.sqrt(u10m**2 + v10m**2)
            return vpd * ws

        DEPTH_HPA = 50.0
        plevs = np.asarray(plevs, dtype=np.float32)
        sp_2d = np.asarray(sp, dtype=np.float32)

        # Find indices of levels that could be in the lowest 50 hPa for any point
        min_sp = float(sp_2d.min())
        candidate_mask = plevs >= (min_sp - DEPTH_HPA - 25)  # generous buffer
        candidate_idx = np.where(candidate_mask)[0]

        if len(candidate_idx) == 0:
            t_c = t2m - 273.15
            td_c = d2m - 273.15
            es = 6.112 * np.exp(17.67 * t_c / (t_c + 243.5))
            ea = 6.112 * np.exp(17.67 * td_c / (td_c + 243.5))
            return np.maximum(es - ea, 0) * np.sqrt(u10m**2 + v10m**2)

        # Initialize with surface values
        t_c_sfc = np.asarray(t2m, dtype=np.float32) - 273.15
        td_c_sfc = np.asarray(d2m, dtype=np.float32) - 273.15
        es_sfc = 6.112 * np.exp(17.67 * t_c_sfc / (t_c_sfc + 243.5))
        ea_sfc = 6.112 * np.exp(17.67 * td_c_sfc / (td_c_sfc + 243.5))
        sfc_vpd = np.maximum(es_sfc - ea_sfc, 0)
        sfc_ws = np.sqrt(np.asarray(u10m, dtype=np.float32)**2 +
                         np.asarray(v10m, dtype=np.float32)**2)

        if paired:
            # Paired mode: track max(VPD × wind) at each level
            max_product = sfc_vpd * sfc_ws
        else:
            # USFS mode: track separate maxima
            max_vpd = sfc_vpd.copy()
            max_ws = sfc_ws.copy()

        # Scan candidate pressure levels
        for li in candidate_idx:
            plev = plevs[li]
            # Mask: this level is below surface AND within 50 hPa of surface
            valid = (plev <= sp_2d) & (plev >= sp_2d - DEPTH_HPA)

            if not valid.any():
                continue

            t_lev = np.asarray(t3d[li], dtype=np.float32)
            td_lev = np.asarray(td3d[li], dtype=np.float32)
            u_lev = np.asarray(u3d[li], dtype=np.float32)
            v_lev = np.asarray(v3d[li], dtype=np.float32)

            t_c = t_lev - 273.15
            td_c = td_lev - 273.15
            es = 6.112 * np.exp(17.67 * t_c / (t_c + 243.5))
            ea = 6.112 * np.exp(17.67 * td_c / (td_c + 243.5))
            vpd_lev = np.maximum(es - ea, 0)
            ws_lev = np.sqrt(u_lev**2 + v_lev**2)

            if paired:
                product_lev = vpd_lev * ws_lev
                max_product = np.where(valid & (product_lev > max_product), product_lev, max_product)
            else:
                max_vpd = np.where(valid & (vpd_lev > max_vpd), vpd_lev, max_vpd)
                max_ws = np.where(valid & (ws_lev > max_ws), ws_lev, max_ws)

        if paired:
            return max_product
        else:
            return max_vpd * max_ws

    def _level_index(self, fhr_data, level_hpa: int) -> Optional[int]:
        """Find the index of a pressure level in the data."""
        levels = fhr_data.pressure_levels
        if levels is None:
            return None
        matches = np.where(np.abs(levels - level_hpa) < 1.0)[0]
        if len(matches) == 0:
            return None
        return int(matches[0])

    def _reproject(self, field_2d: np.ndarray, fhr_data,
                   bbox: dict = None) -> Tuple[np.ndarray, dict]:
        """Reproject a 2D model field to the output grid.

        Args:
            field_2d: (ny_model, nx_model) float32 array
            fhr_data: ForecastHourData (for lat/lon)
            bbox: Optional crop {south, north, west, east}

        Returns:
            (output_2d, bounds_dict) where output_2d is on the regular grid
        """
        indices = self._ensure_projection_map(fhr_data)

        if self._is_regular_grid:
            # GFS: direct lat/lon indexing, no KDTree needed
            return self._reproject_regular(field_2d, bbox)

        # Curvilinear grid (HRRR/RRFS): fancy-index via precomputed map
        out_shape = self.grid.shape
        flat = field_2d.ravel()
        output = flat[indices].reshape(out_shape).astype(np.float32)

        # Mask out-of-domain pixels (beyond native grid boundary)
        if self._proj_mask is not None:
            output[self._proj_mask] = np.nan

        bounds = {
            'south': self.grid.south, 'north': self.grid.north,
            'west': self.grid.west, 'east': self.grid.east,
        }

        if bbox:
            output, bounds = self._crop_to_bbox(output, bounds, bbox)

        return output, bounds

    def _reproject_regular(self, field_2d: np.ndarray,
                           bbox: dict = None) -> Tuple[np.ndarray, dict]:
        """For regular grids (GFS): subset by lat/lon index, then bilinear
        interpolation up to CONUS_GRID resolution for smooth rendering.

        Without upscaling, GFS 0.25° produces a tiny ~129×301 pixel image
        that looks blocky when stretched across CONUS, with jagged contours
        and far too few wind barbs.
        """
        from scipy.ndimage import zoom as _ndimage_zoom

        lat_1d = self._reg_lat_1d
        lon_1d = self._reg_lon_1d

        # Default: match CONUS_GRID bounds so the image aligns with the client overlay
        b = bbox or {'south': self.grid.south, 'north': self.grid.north,
                     'west': self.grid.west, 'east': self.grid.east}

        lat_mask = (lat_1d >= b['south']) & (lat_1d <= b['north'])
        lon_mask = (lon_1d >= b['west']) & (lon_1d <= b['east'])

        lat_idx = np.where(lat_mask)[0]
        lon_idx = np.where(lon_mask)[0]

        if len(lat_idx) == 0 or len(lon_idx) == 0:
            return np.array([]), b

        lat_sl = slice(lat_idx[0], lat_idx[-1] + 1)
        lon_sl = slice(lon_idx[0], lon_idx[-1] + 1)

        output = np.asarray(field_2d[lat_sl, lon_sl], dtype=np.float32)

        # Ensure south < north (GFS lats may be descending)
        actual_lats = lat_1d[lat_sl]
        if len(actual_lats) > 1 and actual_lats[0] > actual_lats[-1]:
            output = output[::-1]
            actual_lats = actual_lats[::-1]

        bounds = {
            'south': float(actual_lats[0]), 'north': float(actual_lats[-1]),
            'west': float(lon_1d[lon_sl][0]), 'east': float(lon_1d[lon_sl][-1]),
        }

        # Bilinear upscale to CONUS_GRID resolution (0.03°) if native grid
        # is coarser. This makes GFS overlays smooth and ensures barb/contour
        # density matches HRRR.
        target_ny = max(1, round((b['north'] - b['south']) / self.grid.dlat))
        target_nx = max(1, round((b['east'] - b['west']) / self.grid.dlon))

        src_ny, src_nx = output.shape
        if src_ny < target_ny or src_nx < target_nx:
            zy = target_ny / src_ny
            zx = target_nx / src_nx
            nan_mask = ~np.isfinite(output)
            if nan_mask.any():
                # Fill NaN before zoom (bilinear propagates NaN), re-mask after
                filled = output.copy()
                filled[nan_mask] = 0
                output = _ndimage_zoom(filled, (zy, zx), order=1).astype(np.float32)
                mask_z = _ndimage_zoom(nan_mask.astype(np.float32), (zy, zx), order=0) > 0.5
                output[mask_z] = np.nan
            else:
                output = _ndimage_zoom(output, (zy, zx), order=1).astype(np.float32)

        return output, bounds

    def _crop_to_bbox(self, output: np.ndarray, bounds: dict,
                      bbox: dict) -> Tuple[np.ndarray, dict]:
        """Crop a reprojected grid to a bounding box."""
        out_lats = self.grid.lats
        out_lons = self.grid.lons

        lat_mask = (out_lats >= bbox['south']) & (out_lats <= bbox['north'])
        lon_mask = (out_lons >= bbox['west']) & (out_lons <= bbox['east'])

        lat_idx = np.where(lat_mask)[0]
        lon_idx = np.where(lon_mask)[0]

        if len(lat_idx) == 0 or len(lon_idx) == 0:
            return output, bounds

        lat_sl = slice(lat_idx[0], lat_idx[-1] + 1)
        lon_sl = slice(lon_idx[0], lon_idx[-1] + 1)

        cropped = output[lat_sl, lon_sl]
        new_bounds = {
            'south': float(out_lats[lat_idx[0]]),
            'north': float(out_lats[lat_idx[-1]]),
            'west': float(out_lons[lon_idx[0]]),
            'east': float(out_lons[lon_idx[-1]]),
        }
        return cropped, new_bounds

    def render_binary(self, fhr_data, field_id: str, level: int = None,
                      bbox: dict = None) -> Optional[OverlayResult]:
        """Render a field as raw float32 bytes for WebGL consumption.

        Returns OverlayResult with float32 row-major bytes, NaN=-9999.
        """
        spec = OVERLAY_FIELDS.get(field_id)
        if spec is None:
            return None

        field_2d = self._extract_field(fhr_data, spec, level)
        if field_2d is None:
            return None

        output, bounds = self._reproject(field_2d, fhr_data, bbox)
        if output.size == 0:
            return None

        # Apply unit transform
        output = output.copy()
        output = _apply_transform(output, spec.transform)

        # Replace NaN with sentinel
        nan_mask = ~np.isfinite(output)
        nan_value = -9999.0
        output[nan_mask] = nan_value

        # Compute data range (excluding NaN sentinel)
        valid = output[~nan_mask] if not nan_mask.all() else output
        vmin = float(np.nanmin(valid)) if valid.size > 0 else spec.default_vmin
        vmax = float(np.nanmax(valid)) if valid.size > 0 else spec.default_vmax

        ny, nx = output.shape
        return OverlayResult(
            data=output.astype(np.float32).tobytes(),
            content_type='application/octet-stream',
            nx=nx, ny=ny,
            south=bounds['south'], north=bounds['north'],
            west=bounds['west'], east=bounds['east'],
            vmin=vmin, vmax=vmax,
            units=spec.units,
            nan_value=nan_value,
        )

    def render_png(self, fhr_data, field_id: str, level: int = None,
                   bbox: dict = None, cmap: str = None,
                   vmin: float = None, vmax: float = None,
                   opacity: float = 0.8) -> Optional[OverlayResult]:
        """Render a field as a transparent RGBA PNG for map overlay.

        Uses PIL for efficiency — applies colormap via numpy LUT, not matplotlib Figure.
        """
        from PIL import Image

        spec = OVERLAY_FIELDS.get(field_id)
        if spec is None:
            return None

        field_2d = self._extract_field(fhr_data, spec, level)
        if field_2d is None:
            return None

        output, bounds = self._reproject(field_2d, fhr_data, bbox)
        if output.size == 0:
            return None

        output = output.copy()
        output = _apply_transform(output, spec.transform)

        cmap_name = cmap or spec.default_cmap
        v0 = vmin if vmin is not None else spec.default_vmin
        v1 = vmax if vmax is not None else spec.default_vmax

        # Compute actual data range for headers
        valid_mask = np.isfinite(output)
        actual_vmin = float(np.nanmin(output[valid_mask])) if valid_mask.any() else v0
        actual_vmax = float(np.nanmax(output[valid_mask])) if valid_mask.any() else v1

        # Normalize to 0-255 index
        nan_mask = ~valid_mask
        normalized = np.clip((output - v0) / max(v1 - v0, 1e-10), 0, 1)
        indices = (normalized * 255).astype(np.uint8)

        # Apply colormap LUT
        lut = get_colormap_lut(cmap_name)
        rgba = lut[indices]  # (ny, nx, 4)

        # Apply opacity
        alpha = (rgba[:, :, 3].astype(np.float32) * opacity).astype(np.uint8)
        rgba[:, :, 3] = alpha

        # Make NaN pixels transparent
        rgba[nan_mask, 3] = 0

        # For reflectivity, make low values transparent
        if field_id == 'refc':
            low_mask = output < 5.0
            rgba[low_mask, 3] = 0

        # Flip vertically: image origin is top-left, geo origin is bottom-left
        rgba = rgba[::-1]

        ny, nx = output.shape
        img = Image.fromarray(rgba, 'RGBA')
        buf = io.BytesIO()
        img.save(buf, format='PNG', optimize=False)
        buf.seek(0)

        return OverlayResult(
            data=buf.read(),
            content_type='image/png',
            nx=nx, ny=ny,
            south=bounds['south'], north=bounds['north'],
            west=bounds['west'], east=bounds['east'],
            vmin=actual_vmin, vmax=actual_vmax,
            units=spec.units,
        )

    def _extract_raw_field(self, fhr_data, attr_name: str, level: int = None) -> Optional[np.ndarray]:
        """Extract a raw field by attribute name (no transforms). Used for contour/barb data."""
        arr = self._get_field(fhr_data, attr_name)
        if arr is None:
            return None
        arr = np.asarray(arr, dtype=np.float32)
        if arr.ndim == 3 and level is not None:
            idx = self._level_index(fhr_data, level)
            if idx is None:
                return None
            arr = arr[idx]
        elif arr.ndim == 3:
            return None
        return arr

    def render_composite(self, fhr_data, spec: 'CompositeSpec',
                         bbox: dict = None, opacity: float = 0.8) -> Optional[OverlayResult]:
        """Render a composite map product (fill + contours + barbs) as PNG.

        Uses matplotlib OO API (Figure, not pyplot) for server-side rendering.
        """
        from matplotlib.figure import Figure
        from matplotlib.backends.backend_agg import FigureCanvasAgg
        import matplotlib.colors as mcolors

        # Determine level for fill field
        fill_level = spec.level
        fill_spec = OVERLAY_FIELDS.get(spec.fill_field) if spec.fill_field else None

        # Extract and reproject fill field
        fill_2d = None
        fill_bounds = None
        if fill_spec:
            fill_2d = self._extract_field(fhr_data, fill_spec, fill_level)
            if fill_2d is not None:
                fill_2d, fill_bounds = self._reproject(fill_2d, fhr_data, bbox)
                fill_2d = fill_2d.copy()
                fill_2d = _apply_transform(fill_2d, fill_spec.transform)

        if fill_2d is None or fill_2d.size == 0:
            return None

        ny, nx = fill_2d.shape
        bounds = fill_bounds

        # Compute figure size to match pixel dimensions (~1:1 pixel mapping)
        dpi = 100
        fig_w = nx / dpi
        fig_h = ny / dpi
        fig = Figure(figsize=(fig_w, fig_h), dpi=dpi)
        fig.patch.set_alpha(0)
        canvas = FigureCanvasAgg(fig)
        ax = fig.add_axes([0, 0, 1, 1])  # fill entire figure
        ax.set_xlim(0, nx)
        ax.set_ylim(0, ny)
        ax.axis('off')
        ax.patch.set_alpha(0)

        # --- Fill layer ---
        cmap_name = spec.fill_cmap or (fill_spec.default_cmap if fill_spec else 'viridis')
        v0 = spec.fill_vmin if spec.fill_vmin is not None else fill_spec.default_vmin
        v1 = spec.fill_vmax if spec.fill_vmax is not None else fill_spec.default_vmax

        # Get matplotlib cmap
        if cmap_name == 'NWSReflectivity':
            lut = _nws_reflectivity_cmap()
            from matplotlib.colors import ListedColormap
            mpl_cmap = ListedColormap(lut / 255.0)
        else:
            import matplotlib.cm as cm
            try:
                mpl_cmap = cm.get_cmap(cmap_name)
            except Exception:
                mpl_cmap = cm.get_cmap('viridis')

        # NaN masking for fill
        nan_mask = ~np.isfinite(fill_2d)
        display = np.ma.array(fill_2d, mask=nan_mask)

        ax.imshow(display, origin='lower', extent=[0, nx, 0, ny],
                  cmap=mpl_cmap, vmin=v0, vmax=v1, alpha=opacity, aspect='auto',
                  interpolation='nearest')

        # For reflectivity: mask low values
        if spec.fill_field == 'refc':
            low_mask = fill_2d < 5.0
            mask_rgba = np.zeros((ny, nx, 4))
            mask_rgba[low_mask, 3] = 0  # already 0, no-op but explicit
            # We handle this via NaN masking in the fill array
            display_data = np.ma.array(fill_2d, mask=(nan_mask | low_mask))
            ax.cla()
            ax.set_xlim(0, nx)
            ax.set_ylim(0, ny)
            ax.axis('off')
            ax.patch.set_alpha(0)
            ax.imshow(display_data, origin='lower', extent=[0, nx, 0, ny],
                      cmap=mpl_cmap, vmin=v0, vmax=v1, alpha=opacity, aspect='auto',
                      interpolation='nearest')

        # --- Contour layers ---
        if spec.contours:
            for cspec in spec.contours:
                contour_spec = OVERLAY_FIELDS.get(cspec.field_id)
                if contour_spec is None:
                    continue
                contour_level = spec.level  # use product's default level
                # For surface contour fields, no level needed
                if not contour_spec.needs_level:
                    contour_level = None

                c_2d = self._extract_field(fhr_data, contour_spec, contour_level)
                if c_2d is None:
                    continue
                c_2d, _ = self._reproject(c_2d, fhr_data, bbox)
                c_2d = c_2d.copy()
                c_2d = _apply_transform(c_2d, contour_spec.transform)

                # Crop/resize to match fill grid if needed
                if c_2d.shape != (ny, nx):
                    continue  # shapes must match after same bbox reprojection

                # Determine levels
                if cspec.levels:
                    levels = cspec.levels
                else:
                    valid = c_2d[np.isfinite(c_2d)]
                    if valid.size == 0:
                        continue
                    lo = np.floor(valid.min() / cspec.interval) * cspec.interval
                    hi = np.ceil(valid.max() / cspec.interval) * cspec.interval
                    levels = np.arange(lo, hi + cspec.interval / 2, cspec.interval)
                    if len(levels) < 2:
                        continue

                cs = ax.contour(np.arange(nx), np.arange(ny), c_2d,
                                levels=levels, colors=cspec.color,
                                linewidths=cspec.linewidth)
                if cspec.label and len(cs.levels) > 0:
                    ax.clabel(cs, inline=True, fontsize=max(6, min(8, ny / 120)),
                              fmt='%g')

        # --- Wind barbs layer ---
        if spec.barbs:
            bspec = spec.barbs
            barb_level = bspec.level or spec.level
            u_arr = self._extract_raw_field(fhr_data, bspec.u_attr, barb_level)
            v_arr = self._extract_raw_field(fhr_data, bspec.v_attr, barb_level)
            if u_arr is not None and v_arr is not None:
                u_2d, _ = self._reproject(u_arr, fhr_data, bbox)
                v_2d, _ = self._reproject(v_arr, fhr_data, bbox)
                if u_2d.shape == (ny, nx) and v_2d.shape == (ny, nx):
                    # Convert m/s to knots
                    u_kt = np.asarray(u_2d, dtype=np.float32) * 1.94384
                    v_kt = np.asarray(v_2d, dtype=np.float32) * 1.94384
                    # Thin
                    thin = bspec.thin
                    y_pts = np.arange(0, ny, thin)
                    x_pts = np.arange(0, nx, thin)
                    xg, yg = np.meshgrid(x_pts, y_pts)
                    u_thin = u_kt[::thin, ::thin]
                    v_thin = v_kt[::thin, ::thin]
                    # Ensure shapes match
                    min_y = min(yg.shape[0], u_thin.shape[0])
                    min_x = min(yg.shape[1], u_thin.shape[1])
                    ax.barbs(xg[:min_y, :min_x], yg[:min_y, :min_x],
                             u_thin[:min_y, :min_x], v_thin[:min_y, :min_x],
                             color=bspec.color, length=bspec.length,
                             linewidth=0.5, barb_increments=dict(half=5, full=10, flag=50))

        # --- Render to PNG ---
        buf = io.BytesIO()
        fig.savefig(buf, format='png', transparent=True, dpi=dpi,
                    bbox_inches=None, pad_inches=0)
        buf.seek(0)

        # Compute actual data range
        valid_fill = fill_2d[~nan_mask] if not nan_mask.all() else fill_2d
        actual_vmin = float(np.nanmin(valid_fill)) if valid_fill.size > 0 else v0
        actual_vmax = float(np.nanmax(valid_fill)) if valid_fill.size > 0 else v1

        return OverlayResult(
            data=buf.read(),
            content_type='image/png',
            nx=nx, ny=ny,
            south=bounds['south'], north=bounds['north'],
            west=bounds['west'], east=bounds['east'],
            vmin=actual_vmin, vmax=actual_vmax,
            units=fill_spec.units if fill_spec else '',
        )

    def get_available_fields(self, fhr_data=None) -> list:
        """Return list of available fields with metadata.

        If fhr_data is provided, checks which fields actually have data.
        """
        result = []
        for fid, spec in OVERLAY_FIELDS.items():
            available = True
            if fhr_data is not None and spec.derived_from is None and spec.attr_name:
                available = self._get_field(fhr_data, spec.attr_name) is not None

            result.append({
                'id': fid,
                'name': spec.name,
                'units': spec.units,
                'category': spec.category,
                'needs_level': spec.needs_level,
                'default_cmap': spec.default_cmap,
                'default_vmin': spec.default_vmin,
                'default_vmax': spec.default_vmax,
                'available': available,
            })
        return result
