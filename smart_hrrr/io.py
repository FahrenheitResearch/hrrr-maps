from pathlib import Path
from typing import Dict
import os
import shutil
from datetime import datetime
import logging


def create_output_structure(model: str, date: str, hour: int) -> Dict[str, Path]:
    """Create organized output directory structure"""
    base_dir = Path(os.environ.get('XSECT_OUTPUTS_DIR', 'outputs'))
    model_dir = base_dir / model.lower()
    date_dir = model_dir / date
    run_dir = date_dir / f"{hour:02d}z"

    run_dir.mkdir(parents=True, exist_ok=True)

    return {"base": base_dir, "model": model_dir, "date": date_dir, "run": run_dir}


def get_forecast_hour_dir(run_dir: Path, forecast_hour: int) -> Path:
    """Get directory for specific forecast hour"""
    fhr_dir = run_dir / f"F{forecast_hour:02d}"
    fhr_dir.mkdir(exist_ok=True, parents=True)
    return fhr_dir


def get_grib_download_dir(cycle: str, model: str = "hrrr") -> Path:
    """Get centralized GRIB download directory"""
    from datetime import datetime
    cycle_dt = datetime.strptime(cycle, "%Y%m%d%H")
    date_str = cycle_dt.strftime("%Y%m%d")
    hour = cycle[-2:]

    grib_dir = Path("grib_files") / model.lower() / date_str / f"{hour}z"
    grib_dir.mkdir(parents=True, exist_ok=True)
    return grib_dir


REQUIRED_TYPES = ("wrfprs", "wrfsfc")


def stage_gribs_for_hour(*, cycle: str, fhr: int, model: str, central_dir: Path, fhr_dir: Path):
    """Stage GRIB files from central location to forecast hour directory"""
    hour = int(cycle[-2:])
    filenames = [f"{model.lower()}.t{hour:02d}z.{ft}f{fhr:02d}.grib2" for ft in REQUIRED_TYPES]

    # Remove any existing GRIB files that aren't for this hour
    for p in fhr_dir.glob("*.grib2"):
        if p.name not in filenames:
            p.unlink(missing_ok=True)

    # Stage required files
    for name in filenames:
        src = central_dir / name
        dst = fhr_dir / name
        if not src.exists():
            raise FileNotFoundError(f"Missing GRIB: {src}")
        if dst.exists():
            continue
        
        # Try hard link first, then symlink, then copy
        try:
            os.link(src, dst)
        except OSError:
            try:
                os.symlink(src, dst)
            except OSError:
                shutil.copy2(src, dst)


def move_old_files():
    """Move old processing files to old_files directory"""
    logger = logging.getLogger(__name__)

    old_files_dir = Path("old_files")
    old_files_dir.mkdir(exist_ok=True)

    patterns = [
        "hrrr_processed_*",
        "all_products_*",
        "memory_safe_*",
        "debug_output_*",
        "hrrr_debug_*",
        "single_hour_*",
        "parallel_output*",
    ]

    moved = 0
    for pattern in patterns:
        for item in Path(".").glob(pattern):
            try:
                dest = old_files_dir / item.name
                if dest.exists():
                    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                    dest = old_files_dir / f"{item.stem}_{ts}{item.suffix}"
                shutil.move(str(item), str(dest))
                moved += 1
            except Exception as e:
                logger.warning(f"Could not move {item}: {e}")

    if moved:
        logger.info(f"Moved {moved} old files to {old_files_dir}")