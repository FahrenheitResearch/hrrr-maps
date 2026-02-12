"""
Cross-Section Analysis Tool for AI Agents

Provides a clean Python API for generating cross-section images and
extracting numerical data from the wxsection.com dashboard.

Usage:
    from tools.agent_tools.cross_section import CrossSectionTool
    cs = CrossSectionTool()  # connects to localhost:5565

    # Generate a cross-section image
    cs.generate_image(
        start=(47.0, -113.0), end=(47.0, -103.0),
        cycle="20260209_06z", fhr=36, product="wind_speed",
        output_path="figures/wind_ew_f36.png"
    )

    # Get numerical data
    data = cs.get_data(
        start=(47.0, -113.0), end=(47.0, -103.0),
        cycle="20260209_06z", fhr=36, product="rh"
    )
    print(data.surface_min("rh_pct"))  # minimum surface RH
"""
import urllib.request
import json
import math
import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class CrossSectionData:
    """Parsed cross-section data with helper methods for analysis."""
    raw: dict
    product: str
    cycle: str
    fhr: int

    @property
    def pressures(self) -> list:
        return self.raw.get("pressure_levels_hpa", [])

    @property
    def surface_pressure(self) -> list:
        return self.raw.get("surface_pressure_hpa", [])

    @property
    def distances(self) -> list:
        return self.raw.get("distances_km", [])

    @property
    def lats(self) -> list:
        return self.raw.get("lats", [])

    @property
    def lons(self) -> list:
        return self.raw.get("lons", [])

    @property
    def n_points(self) -> int:
        return len(self.lons)

    @property
    def n_levels(self) -> int:
        return len(self.pressures)

    def _find_data_key(self) -> Optional[str]:
        """Find the main 2D data array key."""
        skip = {"pressure_levels_hpa", "surface_pressure_hpa", "distances_km",
                "lats", "lons", "metadata", "elevations_m"}
        for k, v in self.raw.items():
            if k not in skip and isinstance(v, list) and len(v) > 0:
                if isinstance(v[0], list):
                    return k
        return None

    @property
    def data_2d(self) -> Optional[list]:
        """Get the main 2D data array (levels x points)."""
        key = self._find_data_key()
        return self.raw.get(key) if key else None

    def _surface_index(self, j: int) -> Optional[int]:
        """Find the pressure level index closest to surface for column j."""
        sp = self.surface_pressure
        if not sp or j >= len(sp):
            return None
        target = sp[j]
        best_i = None
        for i, p in enumerate(self.pressures):
            if p <= target + 5:
                if best_i is None or self.pressures[i] > self.pressures[best_i]:
                    best_i = i
        return best_i

    def _level_index(self, target_hpa: float) -> int:
        """Find index of pressure level closest to target."""
        return min(range(len(self.pressures)),
                   key=lambda i: abs(self.pressures[i] - target_hpa))

    def surface_values(self) -> list:
        """Extract values at the surface level for each column."""
        data = self.data_2d
        if data is None:
            return []
        vals = []
        for j in range(self.n_points):
            si = self._surface_index(j)
            if si is not None:
                v = data[si][j]
                if v is not None and not math.isnan(v):
                    vals.append(v)
        return vals

    def level_values(self, hpa: float) -> list:
        """Extract values at a specific pressure level."""
        data = self.data_2d
        if data is None:
            return []
        idx = self._level_index(hpa)
        return [v for v in data[idx] if v is not None and not math.isnan(v)]

    def column_min_below(self, top_hpa: float) -> Optional[float]:
        """Get minimum value in the column from surface to top_hpa."""
        data = self.data_2d
        if data is None:
            return None
        sp = self.surface_pressure
        mins = []
        for j in range(self.n_points):
            for i, p in enumerate(self.pressures):
                if top_hpa <= p <= sp[j] + 5:
                    v = data[i][j]
                    if v is not None and not math.isnan(v):
                        mins.append(v)
        return min(mins) if mins else None

    def column_max_below(self, top_hpa: float) -> Optional[float]:
        """Get maximum value in the column from surface to top_hpa."""
        data = self.data_2d
        if data is None:
            return None
        sp = self.surface_pressure
        maxs = []
        for j in range(self.n_points):
            for i, p in enumerate(self.pressures):
                if top_hpa <= p <= sp[j] + 5:
                    v = data[i][j]
                    if v is not None and not math.isnan(v):
                        maxs.append(v)
        return max(maxs) if maxs else None

    def surface_stats(self) -> dict:
        """Get min/max/mean of surface values."""
        vals = self.surface_values()
        if not vals:
            return {"min": None, "max": None, "mean": None, "count": 0}
        return {
            "min": round(min(vals), 2),
            "max": round(max(vals), 2),
            "mean": round(sum(vals) / len(vals), 2),
            "count": len(vals),
        }

    def pct_exceeding(self, threshold: float, above: bool = True) -> float:
        """Percentage of surface values exceeding a threshold."""
        vals = self.surface_values()
        if not vals:
            return 0.0
        if above:
            count = sum(1 for v in vals if v > threshold)
        else:
            count = sum(1 for v in vals if v < threshold)
        return round(100.0 * count / len(vals), 1)


class CrossSectionTool:
    """Tool for generating cross-sections and extracting data."""

    def __init__(self, base_url: str = "http://127.0.0.1:5565", model: str = "hrrr"):
        self.base_url = base_url.rstrip("/")
        self.model = model

    def _build_params(self, start, end, cycle, fhr, product, y_top=300, **kwargs):
        params = {
            "model": self.model,
            "cycle": cycle,
            "fhr": fhr,
            "product": product,
            "start_lat": start[0],
            "start_lon": start[1],
            "end_lat": end[0],
            "end_lon": end[1],
            "y_top": y_top,
        }
        params.update(kwargs)
        return "&".join(f"{k}={v}" for k, v in params.items())

    def generate_image(self, start, end, cycle, fhr, product,
                       output_path: str, y_top: int = 300, **kwargs) -> bool:
        """Generate a cross-section PNG image.

        Args:
            start: (lat, lon) tuple
            end: (lat, lon) tuple
            cycle: e.g. "20260209_06z"
            fhr: forecast hour
            product: e.g. "wind_speed", "rh", "temperature"
            output_path: where to save the PNG
            y_top: top of cross-section in hPa (default 300)

        Returns:
            True if successful
        """
        params = self._build_params(start, end, cycle, fhr, product, y_top, **kwargs)
        url = f"{self.base_url}/api/v1/cross-section?{params}"
        try:
            os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
            r = urllib.request.urlopen(url, timeout=60)
            data = r.read()
            with open(output_path, "wb") as f:
                f.write(data)
            return True
        except Exception as e:
            print(f"Error generating image: {e}")
            return False

    def get_data(self, start, end, cycle, fhr, product, **kwargs) -> Optional[CrossSectionData]:
        """Get numerical cross-section data.

        Returns CrossSectionData object with helper methods for analysis.
        """
        params = self._build_params(start, end, cycle, fhr, product, **kwargs)
        url = f"{self.base_url}/api/v1/data?{params}"
        try:
            r = urllib.request.urlopen(url, timeout=60)
            raw = json.loads(r.read())
            return CrossSectionData(raw=raw, product=product, cycle=cycle, fhr=fhr)
        except Exception as e:
            print(f"Error fetching data: {e}")
            return None

    def get_capabilities(self) -> dict:
        """Get available models, products, and cycles."""
        url = f"{self.base_url}/api/v1/capabilities"
        r = urllib.request.urlopen(url, timeout=10)
        return json.loads(r.read())

    def get_events(self, category: str = None, has_data: bool = None) -> list:
        """Get list of historical weather events."""
        url = f"{self.base_url}/api/v1/events"
        params = []
        if category:
            params.append(f"category={category}")
        if has_data is not None:
            params.append(f"has_data={'true' if has_data else 'false'}")
        if params:
            url += "?" + "&".join(params)
        r = urllib.request.urlopen(url, timeout=10)
        data = json.loads(r.read())
        return data if isinstance(data, list) else data.get("events", [])

    def get_event(self, cycle_key: str) -> dict:
        """Get details for a specific event."""
        url = f"{self.base_url}/api/v1/events/{cycle_key}"
        r = urllib.request.urlopen(url, timeout=10)
        return json.loads(r.read())

    def generate_comparison(self, start, end, mode, output_path: str,
                            cycle='latest', fhr=0, product='temperature',
                            models=None, fhrs=None, products=None, cycles=None,
                            cycle_match='same_fhr', y_top=300, **kwargs) -> bool:
        """Generate a multi-panel comparison image via /api/v1/comparison.

        Args:
            start: (lat, lon) tuple
            end: (lat, lon) tuple
            mode: 'model', 'temporal', 'product', or 'cycle'
            output_path: where to save the PNG
            cycle: cycle key or 'latest'
            fhr: forecast hour (common)
            product: single product (when not multi-product)
            models: comma-separated model names for mode=model
            fhrs: comma-separated FHRs for mode=temporal
            products: comma-separated products for mode=product
            cycles: comma-separated cycle keys for mode=cycle
            cycle_match: 'same_fhr' or 'valid_time' for cycle mode
            y_top: top pressure level

        Returns:
            True if successful
        """
        params = {
            "mode": mode,
            "start_lat": start[0],
            "start_lon": start[1],
            "end_lat": end[0],
            "end_lon": end[1],
            "model": self.model,
            "cycle": cycle,
            "fhr": fhr,
            "product": product,
            "y_top": y_top,
        }
        if models:
            params["models"] = models
        if fhrs:
            params["fhrs"] = fhrs
        if products:
            params["products"] = products
        if cycles:
            params["cycles"] = cycles
        if cycle_match:
            params["cycle_match"] = cycle_match
        params.update(kwargs)
        query = "&".join(f"{k}={v}" for k, v in params.items())
        url = f"{self.base_url}/api/v1/comparison?{query}"
        try:
            os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
            r = urllib.request.urlopen(url, timeout=120)
            data = r.read()
            with open(output_path, "wb") as f:
                f.write(data)
            return True
        except Exception as e:
            print(f"Error generating comparison: {e}")
            return False

    def batch_images(self, transects: list, cycle: str, fhrs: list,
                     products: list, output_dir: str, prefix: str = "",
                     y_top: int = 300) -> list:
        """Generate a batch of cross-section images.

        Args:
            transects: list of {"name": str, "start": (lat,lon), "end": (lat,lon)}
            cycle: cycle key
            fhrs: list of forecast hours
            products: list of product names
            output_dir: directory for output PNGs
            prefix: filename prefix
            y_top: top pressure level

        Returns:
            list of generated file paths
        """
        generated = []
        os.makedirs(output_dir, exist_ok=True)
        for t in transects:
            for fhr in fhrs:
                for prod in products:
                    fname = f"{prefix}{t['name']}_{prod}_f{fhr:02d}.png"
                    path = os.path.join(output_dir, fname)
                    if self.generate_image(
                        t["start"], t["end"], cycle, fhr, prod, path, y_top
                    ):
                        generated.append(path)
                        print(f"  OK: {fname}")
                    else:
                        print(f"  FAIL: {fname}")
        return generated
