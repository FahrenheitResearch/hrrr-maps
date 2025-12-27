"""Interactive Cross-Section System with Pre-loaded Data.

Pre-loads all required 3D fields into memory for sub-second cross-section generation.
With 128GB RAM, can easily hold 18 forecast hours (~2GB each).

Features:
- Zarr caching: First load converts GRIB→Zarr (~25s), subsequent loads ~2s
- Parallel loading with multiprocessing
- Sub-second cross-section generation once loaded

Usage:
    from core.cross_section_interactive import InteractiveCrossSection

    ixs = InteractiveCrossSection(cache_dir="cache/zarr")  # Enable Zarr caching
    ixs.load_run("outputs/hrrr/20251224/19z", max_hours=18, workers=4)

    # Generate cross-sections instantly (~0.5s)
    img_bytes = ixs.get_cross_section(
        start_point=(39.74, -104.99),
        end_point=(41.88, -87.63),
        style="wind_speed",
        forecast_hour=0,
    )
"""

import numpy as np
from pathlib import Path
from typing import Optional, Dict, Any, Tuple, List
from dataclasses import dataclass, field
import warnings
import time
import io


@dataclass
class ForecastHourData:
    """Holds all pre-loaded data for a single forecast hour."""
    forecast_hour: int
    pressure_levels: np.ndarray  # (n_levels,) hPa
    lats: np.ndarray  # (ny, nx) or (ny,)
    lons: np.ndarray  # (ny, nx) or (nx,)

    # 3D fields: (n_levels, ny, nx)
    temperature: np.ndarray = None  # K
    u_wind: np.ndarray = None  # m/s
    v_wind: np.ndarray = None  # m/s
    rh: np.ndarray = None  # %
    omega: np.ndarray = None  # Pa/s
    specific_humidity: np.ndarray = None  # kg/kg
    geopotential_height: np.ndarray = None  # gpm
    vorticity: np.ndarray = None  # 1/s
    cloud: np.ndarray = None  # kg/kg
    dew_point: np.ndarray = None  # K

    # Surface fields: (ny, nx)
    surface_pressure: np.ndarray = None  # hPa

    # Pre-computed derived fields
    theta: np.ndarray = None  # K
    temp_c: np.ndarray = None  # C

    def memory_usage_mb(self) -> float:
        """Estimate memory usage in MB."""
        total = 0
        for name, val in self.__dict__.items():
            if isinstance(val, np.ndarray):
                total += val.nbytes
        return total / 1024 / 1024


# Standalone function for multiprocessing (must be at module level for pickle)
def _load_hour_process(grib_file: str, forecast_hour: int) -> Optional[ForecastHourData]:
    """Load a single forecast hour - standalone function for ProcessPoolExecutor."""
    import cfgrib

    try:
        print(f"Loading F{forecast_hour:02d} from {Path(grib_file).name}...")
        start = time.time()

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")

            # Load temperature first to get grid info
            ds_t = cfgrib.open_dataset(
                grib_file,
                filter_by_keys={'typeOfLevel': 'isobaricInhPa', 'shortName': 't'},
                backend_kwargs={'indexpath': ''},
            )

            var_name = list(ds_t.data_vars)[0]
            t_data = ds_t[var_name]

            if 'isobaricInhPa' in t_data.dims:
                pressure_levels = t_data.isobaricInhPa.values
            else:
                pressure_levels = t_data.level.values

            if 'latitude' in t_data.coords:
                lats = t_data.latitude.values
                lons = t_data.longitude.values
            else:
                lats = t_data.lat.values
                lons = t_data.lon.values

            if lons.max() > 180:
                lons = np.where(lons > 180, lons - 360, lons)

            fhr_data = ForecastHourData(
                forecast_hour=forecast_hour,
                pressure_levels=pressure_levels,
                lats=lats,
                lons=lons,
                temperature=t_data.values,
            )
            ds_t.close()

            # Load other fields
            fields = {
                'u': 'u_wind', 'v': 'v_wind', 'r': 'rh', 'w': 'omega',
                'q': 'specific_humidity', 'gh': 'geopotential_height',
                'absv': 'vorticity', 'clwmr': 'cloud', 'dpt': 'dew_point',
            }

            for grib_key, field_name in fields.items():
                try:
                    ds = cfgrib.open_dataset(
                        grib_file,
                        filter_by_keys={'typeOfLevel': 'isobaricInhPa', 'shortName': grib_key},
                        backend_kwargs={'indexpath': ''},
                    )
                    if ds and len(ds.data_vars) > 0:
                        setattr(fhr_data, field_name, ds[list(ds.data_vars)[0]].values)
                    ds.close()
                except Exception:
                    pass

            # Surface pressure
            try:
                sfc_file = Path(grib_file).parent / Path(grib_file).name.replace('wrfprs', 'wrfsfc')
                sp_file = str(sfc_file) if sfc_file.exists() else grib_file
                ds_sp = cfgrib.open_dataset(
                    sp_file,
                    filter_by_keys={'typeOfLevel': 'surface', 'shortName': 'sp'},
                    backend_kwargs={'indexpath': ''},
                )
                if ds_sp and len(ds_sp.data_vars) > 0:
                    sp_data = ds_sp[list(ds_sp.data_vars)[0]].values
                    while sp_data.ndim > 2:
                        sp_data = sp_data[0]
                    if sp_data.max() > 2000:
                        sp_data = sp_data / 100.0
                    fhr_data.surface_pressure = sp_data
                ds_sp.close()
            except Exception:
                pass

            # Pre-compute theta
            if fhr_data.temperature is not None:
                theta = np.zeros_like(fhr_data.temperature)
                for lev_idx, p in enumerate(pressure_levels):
                    theta[lev_idx] = fhr_data.temperature[lev_idx] * (1000.0 / p) ** 0.286
                fhr_data.theta = theta
                fhr_data.temp_c = fhr_data.temperature - 273.15

            duration = time.time() - start
            print(f"  Loaded F{forecast_hour:02d} in {duration:.1f}s ({fhr_data.memory_usage_mb():.0f} MB)")
            return fhr_data

    except Exception as e:
        print(f"Error loading F{forecast_hour:02d}: {e}")
        return None


class InteractiveCrossSection:
    """Pre-loads HRRR data for fast interactive cross-section generation."""

    # Fields to pre-load (covers all 13 styles)
    FIELDS_TO_LOAD = {
        't': 'temperature',
        'u': 'u_wind',
        'v': 'v_wind',
        'r': 'rh',
        'w': 'omega',
        'q': 'specific_humidity',
        'gh': 'geopotential_height',
        'absv': 'vorticity',
        'clwmr': 'cloud',
        'dpt': 'dew_point',
    }

    def __init__(self, cache_dir: str = None):
        """Initialize the interactive cross-section system.

        Args:
            cache_dir: Directory for Zarr cache. If provided, enables fast caching.
                      First load from GRIB takes ~25s, subsequent loads ~2s.
        """
        self.forecast_hours: Dict[int, ForecastHourData] = {}
        self._interpolator_cache = {}
        self.cache_dir = Path(cache_dir) if cache_dir else None
        if self.cache_dir:
            self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_cache_path(self, grib_file: str) -> Optional[Path]:
        """Get cache path for a GRIB file."""
        if not self.cache_dir:
            return None
        # Create unique cache name based on GRIB path
        grib_path = Path(grib_file)
        # e.g., outputs/hrrr/20251224/19z/F00/hrrr.t19z.wrfprsf00.grib2
        # -> 20251224_19z_F00_hrrr.t19z.wrfprsf00.npz
        parts = grib_path.parts
        try:
            date_idx = next(i for i, p in enumerate(parts) if p.isdigit() and len(p) == 8)
            cache_name = f"{parts[date_idx]}_{parts[date_idx+1]}_{parts[date_idx+2]}_{grib_path.stem}.npz"
        except (StopIteration, IndexError):
            cache_name = f"{grib_path.stem}.npz"
        return self.cache_dir / cache_name

    def _save_to_cache(self, fhr_data: ForecastHourData, cache_path: Path):
        """Save ForecastHourData to numpy format (uncompressed for speed)."""
        data = {'forecast_hour': np.array([fhr_data.forecast_hour])}

        for field in ['pressure_levels', 'lats', 'lons', 'temperature', 'u_wind', 'v_wind',
                      'rh', 'omega', 'specific_humidity', 'geopotential_height', 'vorticity',
                      'cloud', 'dew_point', 'surface_pressure', 'theta', 'temp_c']:
            arr = getattr(fhr_data, field, None)
            if arr is not None:
                data[field] = arr

        # Use uncompressed for fast save (~3.5GB per file, but saves in ~5s vs 60s)
        np.savez(cache_path, **data)

    def _load_from_cache(self, cache_path: Path) -> Optional[ForecastHourData]:
        """Load ForecastHourData from compressed numpy format."""
        try:
            data = np.load(cache_path)

            fhr_data = ForecastHourData(
                forecast_hour=int(data['forecast_hour'][0]),
                pressure_levels=data['pressure_levels'],
                lats=data['lats'],
                lons=data['lons'],
            )

            # Load optional arrays
            for field in ['temperature', 'u_wind', 'v_wind', 'rh', 'omega',
                          'specific_humidity', 'geopotential_height', 'vorticity',
                          'cloud', 'dew_point', 'surface_pressure', 'theta', 'temp_c']:
                if field in data:
                    setattr(fhr_data, field, data[field])

            return fhr_data
        except Exception as e:
            print(f"Error loading from cache: {e}")
            return None

    def load_forecast_hour(self, grib_file: str, forecast_hour: int) -> bool:
        """Load all fields for a forecast hour into memory.

        Args:
            grib_file: Path to wrfprs GRIB2 file
            forecast_hour: Forecast hour number

        Returns:
            True if successful
        """
        # Check cache first
        cache_path = self._get_cache_path(grib_file)
        if cache_path and cache_path.exists():
            print(f"Loading F{forecast_hour:02d} from cache...")
            start = time.time()
            fhr_data = self._load_from_cache(cache_path)
            if fhr_data is not None:
                self.forecast_hours[forecast_hour] = fhr_data
                duration = time.time() - start
                print(f"  Loaded F{forecast_hour:02d} from cache in {duration:.1f}s ({fhr_data.memory_usage_mb():.0f} MB)")
                return True

        try:
            import cfgrib
            from scipy.spatial import cKDTree

            print(f"Loading F{forecast_hour:02d} from {Path(grib_file).name}...")
            start = time.time()

            with warnings.catch_warnings():
                warnings.simplefilter("ignore")

                # First, get grid info and pressure levels from temperature
                ds_t = cfgrib.open_dataset(
                    grib_file,
                    filter_by_keys={'typeOfLevel': 'isobaricInhPa', 'shortName': 't'},
                    backend_kwargs={'indexpath': ''},
                )

                var_name = list(ds_t.data_vars)[0]
                t_data = ds_t[var_name]

                # Get pressure levels
                if 'isobaricInhPa' in t_data.dims:
                    pressure_levels = t_data.isobaricInhPa.values
                else:
                    pressure_levels = t_data.level.values

                # Get lat/lon grid
                if 'latitude' in t_data.coords:
                    lats = t_data.latitude.values
                    lons = t_data.longitude.values
                else:
                    lats = t_data.lat.values
                    lons = t_data.lon.values

                # Convert lons to -180 to 180
                if lons.max() > 180:
                    lons = np.where(lons > 180, lons - 360, lons)

                # Create data holder
                fhr_data = ForecastHourData(
                    forecast_hour=forecast_hour,
                    pressure_levels=pressure_levels,
                    lats=lats,
                    lons=lons,
                    temperature=t_data.values,
                )
                ds_t.close()

                # Load all other fields
                for grib_key, field_name in self.FIELDS_TO_LOAD.items():
                    if grib_key == 't':
                        continue  # Already loaded

                    try:
                        ds = cfgrib.open_dataset(
                            grib_file,
                            filter_by_keys={'typeOfLevel': 'isobaricInhPa', 'shortName': grib_key},
                            backend_kwargs={'indexpath': ''},
                        )
                        if ds and len(ds.data_vars) > 0:
                            var = list(ds.data_vars)[0]
                            setattr(fhr_data, field_name, ds[var].values)
                        ds.close()
                    except Exception as e:
                        print(f"  Warning: Could not load {grib_key}: {e}")

                # Load surface pressure
                try:
                    # Try wrfsfc file first
                    sfc_file = Path(grib_file).parent / Path(grib_file).name.replace('wrfprs', 'wrfsfc')
                    sp_file = str(sfc_file) if sfc_file.exists() else grib_file

                    ds_sp = cfgrib.open_dataset(
                        sp_file,
                        filter_by_keys={'typeOfLevel': 'surface', 'shortName': 'sp'},
                        backend_kwargs={'indexpath': ''},
                    )
                    if ds_sp and len(ds_sp.data_vars) > 0:
                        sp_var = list(ds_sp.data_vars)[0]
                        sp_data = ds_sp[sp_var].values
                        while sp_data.ndim > 2:
                            sp_data = sp_data[0]
                        # Convert Pa to hPa
                        if sp_data.max() > 2000:
                            sp_data = sp_data / 100.0
                        fhr_data.surface_pressure = sp_data
                    ds_sp.close()
                except Exception as e:
                    print(f"  Warning: Could not load surface pressure: {e}")

                # Pre-compute theta and temp_c
                if fhr_data.temperature is not None:
                    P_ref = 1000.0
                    kappa = 0.286
                    theta = np.zeros_like(fhr_data.temperature)
                    for lev_idx, p in enumerate(pressure_levels):
                        theta[lev_idx] = fhr_data.temperature[lev_idx] * (P_ref / p) ** kappa
                    fhr_data.theta = theta
                    fhr_data.temp_c = fhr_data.temperature - 273.15

                # Store
                self.forecast_hours[forecast_hour] = fhr_data

                duration = time.time() - start
                mem_mb = fhr_data.memory_usage_mb()
                print(f"  Loaded F{forecast_hour:02d} in {duration:.1f}s ({mem_mb:.0f} MB)")

                # Save to cache for fast subsequent loads
                if cache_path:
                    try:
                        self._save_to_cache(fhr_data, cache_path)
                        print(f"  Cached to {cache_path.name}")
                    except Exception as e:
                        print(f"  Warning: Could not cache: {e}")

                return True

        except Exception as e:
            print(f"Error loading F{forecast_hour:02d}: {e}")
            import traceback
            traceback.print_exc()
            return False

    def load_run(self, run_dir: str, max_hours: int = 18, workers: int = 1) -> int:
        """Load all forecast hours from a run directory.

        Args:
            run_dir: Path to run directory (e.g., outputs/hrrr/20251224/19z)
            max_hours: Maximum forecast hours to load
            workers: Number of parallel workers (1 = sequential)

        Returns:
            Number of hours loaded
        """
        run_path = Path(run_dir)
        if not run_path.exists():
            print(f"Run directory not found: {run_dir}")
            return 0

        # Collect files to load
        files_to_load = []
        for fhr in range(max_hours + 1):
            fhr_dir = run_path / f"F{fhr:02d}"
            prs_files = list(fhr_dir.glob("*wrfprs*.grib2"))
            if prs_files:
                files_to_load.append((str(prs_files[0]), fhr))

        if not files_to_load:
            print("No GRIB files found")
            return 0

        print(f"Loading {len(files_to_load)} forecast hours with {workers} workers...")
        start_time = time.time()

        if workers <= 1:
            # Sequential loading
            for grib_file, fhr in files_to_load:
                self.load_forecast_hour(grib_file, fhr)
        else:
            # Parallel loading with multiprocessing (bypasses GIL)
            from concurrent.futures import ProcessPoolExecutor, as_completed

            with ProcessPoolExecutor(max_workers=workers) as executor:
                futures = {
                    executor.submit(_load_hour_process, grib_file, fhr): fhr
                    for grib_file, fhr in files_to_load
                }

                for future in as_completed(futures):
                    fhr = futures[future]
                    try:
                        result = future.result()
                        if result is not None:
                            self.forecast_hours[result.forecast_hour] = result
                    except Exception as e:
                        print(f"Error loading F{fhr:02d}: {e}")

        duration = time.time() - start_time
        loaded = len(self.forecast_hours)
        total_mem = sum(fh.memory_usage_mb() for fh in self.forecast_hours.values())
        print(f"\nLoaded {loaded} forecast hours ({total_mem:.0f} MB total) in {duration:.1f}s")
        print(f"  ({duration/max(1,loaded):.1f}s per hour with {workers} workers)")
        return loaded

    def _load_hour_worker(self, grib_file: str, forecast_hour: int) -> Optional[ForecastHourData]:
        """Worker function for parallel loading. Returns ForecastHourData or None."""
        try:
            import cfgrib

            print(f"Loading F{forecast_hour:02d} from {Path(grib_file).name}...")
            start = time.time()

            with warnings.catch_warnings():
                warnings.simplefilter("ignore")

                # First, get grid info and pressure levels from temperature
                ds_t = cfgrib.open_dataset(
                    grib_file,
                    filter_by_keys={'typeOfLevel': 'isobaricInhPa', 'shortName': 't'},
                    backend_kwargs={'indexpath': ''},
                )

                var_name = list(ds_t.data_vars)[0]
                t_data = ds_t[var_name]

                # Get pressure levels
                if 'isobaricInhPa' in t_data.dims:
                    pressure_levels = t_data.isobaricInhPa.values
                else:
                    pressure_levels = t_data.level.values

                # Get lat/lon grid
                if 'latitude' in t_data.coords:
                    lats = t_data.latitude.values
                    lons = t_data.longitude.values
                else:
                    lats = t_data.lat.values
                    lons = t_data.lon.values

                # Convert lons to -180 to 180
                if lons.max() > 180:
                    lons = np.where(lons > 180, lons - 360, lons)

                # Create data holder
                fhr_data = ForecastHourData(
                    forecast_hour=forecast_hour,
                    pressure_levels=pressure_levels,
                    lats=lats,
                    lons=lons,
                    temperature=t_data.values,
                )
                ds_t.close()

                # Load all other fields
                for grib_key, field_name in self.FIELDS_TO_LOAD.items():
                    if grib_key == 't':
                        continue  # Already loaded

                    try:
                        ds = cfgrib.open_dataset(
                            grib_file,
                            filter_by_keys={'typeOfLevel': 'isobaricInhPa', 'shortName': grib_key},
                            backend_kwargs={'indexpath': ''},
                        )
                        if ds and len(ds.data_vars) > 0:
                            var = list(ds.data_vars)[0]
                            setattr(fhr_data, field_name, ds[var].values)
                        ds.close()
                    except Exception:
                        pass  # Silently skip unavailable fields in parallel mode

                # Load surface pressure
                try:
                    sfc_file = Path(grib_file).parent / Path(grib_file).name.replace('wrfprs', 'wrfsfc')
                    sp_file = str(sfc_file) if sfc_file.exists() else grib_file

                    ds_sp = cfgrib.open_dataset(
                        sp_file,
                        filter_by_keys={'typeOfLevel': 'surface', 'shortName': 'sp'},
                        backend_kwargs={'indexpath': ''},
                    )
                    if ds_sp and len(ds_sp.data_vars) > 0:
                        sp_var = list(ds_sp.data_vars)[0]
                        sp_data = ds_sp[sp_var].values
                        while sp_data.ndim > 2:
                            sp_data = sp_data[0]
                        if sp_data.max() > 2000:
                            sp_data = sp_data / 100.0
                        fhr_data.surface_pressure = sp_data
                    ds_sp.close()
                except Exception:
                    pass

                # Pre-compute theta and temp_c
                if fhr_data.temperature is not None:
                    P_ref = 1000.0
                    kappa = 0.286
                    theta = np.zeros_like(fhr_data.temperature)
                    for lev_idx, p in enumerate(pressure_levels):
                        theta[lev_idx] = fhr_data.temperature[lev_idx] * (P_ref / p) ** kappa
                    fhr_data.theta = theta
                    fhr_data.temp_c = fhr_data.temperature - 273.15

                duration = time.time() - start
                mem_mb = fhr_data.memory_usage_mb()
                print(f"  Loaded F{forecast_hour:02d} in {duration:.1f}s ({mem_mb:.0f} MB)")

                return fhr_data

        except Exception as e:
            print(f"Error loading F{forecast_hour:02d}: {e}")
            return None

    def get_cross_section(
        self,
        start_point: Tuple[float, float],
        end_point: Tuple[float, float],
        style: str = "wind_speed",
        forecast_hour: int = 0,
        n_points: int = 100,
        return_image: bool = True,
        dpi: int = 100,
    ) -> Optional[bytes]:
        """Generate cross-section from pre-loaded data.

        This is the fast path - should complete in <1 second.

        Args:
            start_point: (lat, lon) start
            end_point: (lat, lon) end
            style: Cross-section style
            forecast_hour: Which forecast hour to use
            n_points: Points along path
            return_image: If True, return PNG bytes; if False, return data dict
            dpi: Output resolution

        Returns:
            PNG image bytes, or data dict if return_image=False
        """
        if forecast_hour not in self.forecast_hours:
            print(f"Forecast hour {forecast_hour} not loaded")
            return None

        start = time.time()

        # Get pre-loaded data
        fhr_data = self.forecast_hours[forecast_hour]

        # Create path
        path_lats = np.linspace(start_point[0], end_point[0], n_points)
        path_lons = np.linspace(start_point[1], end_point[1], n_points)

        # Interpolate all needed fields to path
        data = self._interpolate_to_path(fhr_data, path_lats, path_lons, style)

        t_interp = time.time() - start

        if not return_image:
            return data

        # Render
        img_bytes = self._render_cross_section(data, style, dpi)

        t_total = time.time() - start
        print(f"Cross-section generated in {t_total:.3f}s (interp: {t_interp:.3f}s)")

        return img_bytes

    def _interpolate_to_path(
        self,
        fhr_data: ForecastHourData,
        path_lats: np.ndarray,
        path_lons: np.ndarray,
        style: str,
    ) -> Dict[str, Any]:
        """Interpolate 3D fields to cross-section path."""
        from scipy.spatial import cKDTree
        from scipy.interpolate import RegularGridInterpolator

        n_points = len(path_lats)
        n_levels = len(fhr_data.pressure_levels)

        lats_grid = fhr_data.lats
        lons_grid = fhr_data.lons

        # Build interpolator (curvilinear vs regular grid)
        if lats_grid.ndim == 2:
            # Curvilinear grid - use KDTree
            src_pts = np.column_stack([lats_grid.ravel(), lons_grid.ravel()])
            tree = cKDTree(src_pts)
            tgt_pts = np.column_stack([path_lats, path_lons])
            _, indices = tree.query(tgt_pts, k=1)

            def interp_3d(field_3d):
                result = np.full((n_levels, n_points), np.nan)
                for lev in range(min(field_3d.shape[0], n_levels)):
                    result[lev, :] = field_3d[lev].ravel()[indices]
                return result

            def interp_2d(field_2d):
                return field_2d.ravel()[indices]
        else:
            # Regular grid - use bilinear interpolation
            lats_1d = lats_grid if lats_grid.ndim == 1 else lats_grid[:, 0]
            lons_1d = lons_grid if lons_grid.ndim == 1 else lons_grid[0, :]
            pts = np.column_stack([path_lats, path_lons])

            def interp_3d(field_3d):
                result = np.full((n_levels, n_points), np.nan)
                for lev in range(min(field_3d.shape[0], n_levels)):
                    interp = RegularGridInterpolator(
                        (lats_1d, lons_1d), field_3d[lev],
                        method='linear', bounds_error=False, fill_value=np.nan
                    )
                    result[lev, :] = interp(pts)
                return result

            def interp_2d(field_2d):
                interp = RegularGridInterpolator(
                    (lats_1d, lons_1d), field_2d,
                    method='linear', bounds_error=False, fill_value=np.nan
                )
                return interp(pts)

        # Build result dict
        result = {
            'lats': path_lats,
            'lons': path_lons,
            'distances': self._calculate_distances(path_lats, path_lons),
            'pressure_levels': fhr_data.pressure_levels,
        }

        # Always interpolate base fields
        if fhr_data.temperature is not None:
            result['temperature'] = interp_3d(fhr_data.temperature)
            result['temp_c'] = result['temperature'] - 273.15

        if fhr_data.theta is not None:
            result['theta'] = interp_3d(fhr_data.theta)

        if fhr_data.u_wind is not None:
            result['u_wind'] = interp_3d(fhr_data.u_wind)

        if fhr_data.v_wind is not None:
            result['v_wind'] = interp_3d(fhr_data.v_wind)

        if fhr_data.surface_pressure is not None:
            result['surface_pressure'] = interp_2d(fhr_data.surface_pressure)

        # Style-specific fields
        if style in ['rh', 'q'] and fhr_data.rh is not None:
            result['rh'] = interp_3d(fhr_data.rh)

        if style == 'omega' and fhr_data.omega is not None:
            result['omega'] = interp_3d(fhr_data.omega)

        if style == 'vorticity' and fhr_data.vorticity is not None:
            result['vorticity'] = interp_3d(fhr_data.vorticity)

        if style in ['cloud', 'cloud_total', 'icing'] and fhr_data.cloud is not None:
            result['cloud'] = interp_3d(fhr_data.cloud)

        if style == 'theta_e' and fhr_data.specific_humidity is not None:
            q = interp_3d(fhr_data.specific_humidity)
            result['specific_humidity'] = q
            # Compute theta_e
            T = result['temperature']
            theta = result['theta']
            Lv = 2.5e6
            cp = 1004.0
            theta_e = np.zeros_like(T)
            for lev in range(len(fhr_data.pressure_levels)):
                theta_e[lev, :] = theta[lev, :] * np.exp(Lv * q[lev, :] / (cp * T[lev, :]))
            result['theta_e'] = theta_e

        if style == 'q' and fhr_data.specific_humidity is not None:
            result['specific_humidity'] = interp_3d(fhr_data.specific_humidity)

        if style in ['shear', 'lapse_rate'] and fhr_data.geopotential_height is not None:
            gh = interp_3d(fhr_data.geopotential_height)
            result['geopotential_height'] = gh

            if style == 'shear':
                # Compute shear
                u = result.get('u_wind')
                v = result.get('v_wind')
                if u is not None and v is not None:
                    shear = np.full((n_levels, n_points), np.nan)
                    for lev in range(n_levels - 1):
                        dz = gh[lev, :] - gh[lev + 1, :]
                        dz = np.where(np.abs(dz) < 10, np.nan, dz)
                        du = u[lev, :] - u[lev + 1, :]
                        dv = v[lev, :] - v[lev + 1, :]
                        dwind = np.sqrt(du**2 + dv**2)
                        shear[lev, :] = (dwind / np.abs(dz)) * 1000
                    shear[-1, :] = shear[-2, :]
                    result['shear'] = shear

            if style == 'lapse_rate':
                T = result['temperature']
                lapse = np.full((n_levels, n_points), np.nan)
                for lev in range(n_levels - 1):
                    dz = (gh[lev, :] - gh[lev + 1, :]) / 1000.0
                    dz = np.where(np.abs(dz) < 0.01, np.nan, dz)
                    dT = T[lev, :] - T[lev + 1, :]
                    lapse[lev, :] = -dT / dz
                lapse[-1, :] = lapse[-2, :]
                result['lapse_rate'] = lapse

        if style == 'wetbulb' and fhr_data.rh is not None:
            T_c = result['temp_c']
            RH = interp_3d(fhr_data.rh)
            result['rh'] = RH
            Tw = (T_c * np.arctan(0.151977 * np.sqrt(RH + 8.313659))
                  + np.arctan(T_c + RH)
                  - np.arctan(RH - 1.676331)
                  + 0.00391838 * (RH ** 1.5) * np.arctan(0.023101 * RH)
                  - 4.686035)
            result['wetbulb'] = Tw

        if style == 'icing' and fhr_data.cloud is not None:
            T_c = result['temp_c']
            cloud = result['cloud'] * 1000  # g/kg
            icing = np.where((T_c >= -20) & (T_c <= 0), cloud, 0)
            result['icing'] = icing

        return result

    def _calculate_distances(self, lats: np.ndarray, lons: np.ndarray) -> np.ndarray:
        """Calculate cumulative distance along path in km."""
        R = 6371
        distances = [0]
        for i in range(1, len(lats)):
            lat1, lon1 = np.radians(lats[i-1]), np.radians(lons[i-1])
            lat2, lon2 = np.radians(lats[i]), np.radians(lons[i])
            dlat = lat2 - lat1
            dlon = lon2 - lon1
            a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
            c = 2 * np.arcsin(np.sqrt(a))
            distances.append(distances[-1] + R * c)
        return np.array(distances)

    def _render_cross_section(self, data: Dict, style: str, dpi: int) -> bytes:
        """Render cross-section to PNG bytes."""
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        import matplotlib.colors as mcolors
        from matplotlib.ticker import MultipleLocator

        distances = data['distances']
        pressure_levels = data['pressure_levels']
        theta = data.get('theta')
        temperature = data.get('temperature')
        surface_pressure = data.get('surface_pressure')
        u_wind = data.get('u_wind')
        v_wind = data.get('v_wind')
        lats = data['lats']
        lons = data['lons']

        n_levels, n_points = theta.shape if theta is not None else (len(pressure_levels), len(distances))

        # Compute wind speed
        if u_wind is not None and v_wind is not None:
            wind_speed = np.sqrt(u_wind**2 + v_wind**2) * 1.944
        else:
            wind_speed = None

        # Apply terrain masking
        if surface_pressure is not None and theta is not None:
            theta = theta.copy()
            for i in range(n_points):
                sp = surface_pressure[i]
                for lev_idx, plev in enumerate(pressure_levels):
                    if plev > sp:
                        theta[lev_idx, i] = np.nan
                        if wind_speed is not None:
                            wind_speed[lev_idx, i] = np.nan

        # Create figure
        fig, ax = plt.subplots(figsize=(12, 7), facecolor='white')
        X, Y = np.meshgrid(distances, pressure_levels)

        # Style-specific shading
        shading_label = style

        if style == "wind_speed" and wind_speed is not None:
            wspd_colors = ['#FFFFFF', '#E0F0FF', '#A0D0FF', '#60B0FF', '#FFFF80', '#FFC000', '#FF6000', '#FF0000']
            wspd_cmap = mcolors.LinearSegmentedColormap.from_list('wspd', wspd_colors, N=256)
            cf = ax.contourf(X, Y, wind_speed, levels=np.arange(0, 105, 5), cmap=wspd_cmap, extend='max')
            cbar = plt.colorbar(cf, ax=ax, shrink=0.9)
            cbar.set_label('Wind Speed (kts)')
            shading_label = "Wind Speed"
        elif style == "temp":
            temp_c = data.get('temp_c')
            if temp_c is not None:
                if surface_pressure is not None:
                    temp_c = temp_c.copy()
                    for i in range(n_points):
                        for lev_idx, plev in enumerate(pressure_levels):
                            if plev > surface_pressure[i]:
                                temp_c[lev_idx, i] = np.nan
                cf = ax.contourf(X, Y, temp_c, levels=np.arange(-60, 45, 5), cmap='coolwarm', extend='both')
                cbar = plt.colorbar(cf, ax=ax, shrink=0.9)
                cbar.set_label('Temperature (°C)')
                shading_label = "T(°C)"
        elif style == "rh":
            rh = data.get('rh')
            if rh is not None:
                if surface_pressure is not None:
                    rh = rh.copy()
                    for i in range(n_points):
                        for lev_idx, plev in enumerate(pressure_levels):
                            if plev > surface_pressure[i]:
                                rh[lev_idx, i] = np.nan
                rh_colors = [(0.6, 0.4, 0.2), (0.7, 0.5, 0.3), (0.85, 0.75, 0.5),
                             (0.9, 0.9, 0.7), (0.7, 0.9, 0.7), (0.4, 0.8, 0.4),
                             (0.2, 0.6, 0.3), (0.1, 0.4, 0.2)]
                rh_cmap = mcolors.LinearSegmentedColormap.from_list('rh', rh_colors, N=256)
                cf = ax.contourf(X, Y, rh, levels=np.arange(0, 105, 5), cmap=rh_cmap, extend='both')
                cbar = plt.colorbar(cf, ax=ax, shrink=0.9)
                cbar.set_label('Relative Humidity (%)')
                shading_label = "RH(%)"
        elif style == "omega":
            omega = data.get('omega')
            if omega is not None:
                if surface_pressure is not None:
                    omega = omega.copy()
                    for i in range(n_points):
                        for lev_idx, plev in enumerate(pressure_levels):
                            if plev > surface_pressure[i]:
                                omega[lev_idx, i] = np.nan
                omega_display = omega * 36.0
                omega_max = min(np.nanmax(np.abs(omega_display)), 20)
                cf = ax.contourf(X, Y, omega_display, levels=np.linspace(-omega_max, omega_max, 21),
                                cmap='RdBu_r', extend='both')
                cbar = plt.colorbar(cf, ax=ax, shrink=0.9)
                cbar.set_label('ω (hPa/hr)')
                shading_label = "ω"
        elif style == "theta_e":
            theta_e = data.get('theta_e')
            if theta_e is not None:
                if surface_pressure is not None:
                    theta_e = theta_e.copy()
                    for i in range(n_points):
                        for lev_idx, plev in enumerate(pressure_levels):
                            if plev > surface_pressure[i]:
                                theta_e[lev_idx, i] = np.nan
                cf = ax.contourf(X, Y, theta_e, levels=np.arange(280, 365, 4), cmap='Spectral_r', extend='both')
                cbar = plt.colorbar(cf, ax=ax, shrink=0.9)
                cbar.set_label('θₑ (K)')
                shading_label = "θₑ"
        elif style == "shear":
            shear = data.get('shear')
            if shear is not None:
                if surface_pressure is not None:
                    shear = shear.copy()
                    for i in range(n_points):
                        for lev_idx, plev in enumerate(pressure_levels):
                            if plev > surface_pressure[i]:
                                shear[lev_idx, i] = np.nan
                cf = ax.contourf(X, Y, shear, levels=np.linspace(0, 10, 11), cmap='OrRd', extend='max')
                cbar = plt.colorbar(cf, ax=ax, shrink=0.9)
                cbar.set_label('Shear (10⁻³/s)')
                shading_label = "Shear"
        else:
            # Default to theta shading
            if theta is not None:
                cf = ax.contourf(X, Y, theta, levels=np.arange(270, 360, 4), cmap='viridis', extend='both')
                cbar = plt.colorbar(cf, ax=ax, shrink=0.9)
                cbar.set_label('θ (K)')
                shading_label = "θ"

        # Theta contours
        if theta is not None:
            cs = ax.contour(X, Y, theta, levels=np.arange(270, 330, 4), colors='black', linewidths=0.8)
            ax.clabel(cs, inline=True, fontsize=8, fmt='%.0f')

        # Freezing level
        if temperature is not None:
            temp_c_plot = temperature - 273.15
            if surface_pressure is not None:
                temp_c_plot = temp_c_plot.copy()
                for i in range(n_points):
                    for lev_idx, plev in enumerate(pressure_levels):
                        if plev > surface_pressure[i]:
                            temp_c_plot[lev_idx, i] = np.nan
            try:
                ax.contour(X, Y, temp_c_plot, levels=[0], colors='magenta', linewidths=2)
            except:
                pass

        # Terrain fill
        if surface_pressure is not None:
            max_p = max(pressure_levels.max(), surface_pressure.max()) + 20
            terrain_x = np.concatenate([[distances[0]], distances, [distances[-1]]])
            terrain_y = np.concatenate([[max_p], surface_pressure, [max_p]])
            ax.fill(terrain_x, terrain_y, color='saddlebrown', alpha=0.9, zorder=5)
            ax.plot(distances, surface_pressure, 'k-', linewidth=1.5, zorder=6)

        # Axes
        ax.set_ylim(max(pressure_levels), min(pressure_levels))
        ax.set_xlim(0, distances[-1])
        ax.set_xlabel('Distance (km)')
        ax.set_ylabel('Pressure (hPa)')
        ax.yaxis.set_major_locator(MultipleLocator(100))
        ax.grid(True, alpha=0.3)

        ax.set_title(f'Cross-Section: {shading_label} + θ | {lats[0]:.1f},{lons[0]:.1f} → {lats[-1]:.1f},{lons[-1]:.1f}')

        # Save to bytes
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=dpi, bbox_inches='tight', facecolor='white')
        plt.close(fig)
        buf.seek(0)

        return buf.read()

    def get_loaded_hours(self) -> List[int]:
        """Get list of loaded forecast hours."""
        return sorted(self.forecast_hours.keys())

    def get_memory_usage(self) -> float:
        """Get total memory usage in MB."""
        return sum(fh.memory_usage_mb() for fh in self.forecast_hours.values())

    def unload_hour(self, forecast_hour: int):
        """Unload a forecast hour to free memory."""
        if forecast_hour in self.forecast_hours:
            del self.forecast_hours[forecast_hour]


# Convenience function for testing
def test_interactive():
    """Test interactive cross-section performance."""
    ixs = InteractiveCrossSection()

    # Load a single hour
    run_dir = Path("outputs/hrrr/20251224/19z")
    if not run_dir.exists():
        print("No test data available")
        return

    prs_file = list((run_dir / "F00").glob("*wrfprs*.grib2"))
    if not prs_file:
        print("No GRIB file found")
        return

    print("\n=== Loading data ===")
    ixs.load_forecast_hour(str(prs_file[0]), 0)

    print(f"\nMemory usage: {ixs.get_memory_usage():.0f} MB")

    # Test multiple cross-sections
    print("\n=== Testing cross-section generation ===")

    paths = [
        ((39.74, -104.99), (41.88, -87.63), "Denver → Chicago"),
        ((34.05, -118.24), (33.45, -112.07), "LA → Phoenix"),
        ((40.71, -74.01), (42.36, -71.06), "NYC → Boston"),
    ]

    styles = ['wind_speed', 'temp', 'theta_e', 'rh', 'omega']

    for start, end, name in paths:
        print(f"\n{name}:")
        for style in styles:
            t0 = time.time()
            img = ixs.get_cross_section(start, end, style=style, forecast_hour=0)
            duration = time.time() - t0
            print(f"  {style:12}: {duration:.3f}s ({len(img)/1024:.0f} KB)")


if __name__ == "__main__":
    test_interactive()
