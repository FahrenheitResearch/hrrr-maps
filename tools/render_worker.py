"""Render worker for multiprocess cross-section rendering and GRIB conversion.

Separate module to avoid Windows spawn importing Flask/dashboard code.
Each worker process creates its own InteractiveCrossSection engine
and renders independently with its own GIL.
"""
import sys
import os
import numpy as np
from pathlib import Path

_engine = None


def init_worker(project_dir, cache_dir, extra_cache_dirs, model_name, min_levels, grib_backend):
    """Initialize engine in worker process. Called once per process."""
    global _engine

    if project_dir not in sys.path:
        sys.path.insert(0, project_dir)

    # Suppress matplotlib GUI backend in workers
    import matplotlib
    matplotlib.use('Agg')

    from core.cross_section_interactive import InteractiveCrossSection

    _engine = InteractiveCrossSection(
        cache_dir=cache_dir,
        min_levels=min_levels,
        grib_backend=grib_backend,
    )
    _engine.model = model_name.upper()

    for d in extra_cache_dirs:
        p = Path(d)
        if p.is_dir():
            _engine.extra_cache_dirs.append(p)


def render_frame(args):
    """Render a single cross-section frame. Called per job in worker process."""
    global _engine

    (grib_file, engine_key, start, end, style, y_axis, vscale, y_top,
     units, temp_cmap, anomaly, marker, marker_label, markers,
     metadata, terrain_data) = args

    # Load FHR from mmap if not already loaded in this worker
    if engine_key not in _engine.forecast_hours:
        _engine.load_forecast_hour(grib_file, engine_key)

    # Render
    try:
        png = _engine.get_cross_section(
            start_point=start,
            end_point=end,
            style=style,
            forecast_hour=engine_key,
            return_image=True,
            dpi=100,
            y_axis=y_axis,
            vscale=vscale,
            y_top=y_top,
            units=units,
            terrain_data=terrain_data,
            temp_cmap=temp_cmap,
            metadata=metadata,
            anomaly=anomaly,
            marker=marker,
            marker_label=marker_label,
            markers=markers,
        )
        return engine_key, png
    except Exception as e:
        return engine_key, None


def convert_grib(args):
    """Convert a GRIB file to mmap cache. Returns (engine_key, success).

    The heavy work (eccodes decode + numpy conversion + mmap write) happens
    in the worker process with its own GIL. After conversion, the mmap cache
    files exist on disk for the main process to load cheaply.
    """
    global _engine
    grib_file, engine_key = args
    try:
        ok = _engine.load_forecast_hour(grib_file, engine_key)
        # Free worker memory — we only needed the side effect of writing mmap cache.
        # The mmap-backed arrays are lightweight but we free them to avoid accumulation
        # across many conversions in the same worker.
        _engine.forecast_hours.pop(engine_key, None)
        return engine_key, ok
    except Exception as e:
        return engine_key, False


def render_multi_panel(args):
    """Render a multi-panel composite frame. Returns PNG bytes or None.

    Panel data (pre-computed cross-section data dicts) is gathered in the main
    process and pickled to the worker. The worker only does the matplotlib
    rendering which is the CPU-bound part.
    """
    global _engine
    panels, render_kwargs = args
    try:
        png = _engine.render_multi_panel(panels, **render_kwargs)
        return png
    except Exception as e:
        return None
