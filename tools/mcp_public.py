#!/usr/bin/env python3
"""
Public SSE MCP Server for wxsection.com — API-key authenticated, rate-limited.

Exposes 40 tools (37 from private server + 3 new city browsing) over SSE transport.
Cloudflare tunnel routes mcp.wxsection.com -> localhost:5566.

Usage:
    python tools/mcp_public.py [--port 5566]

Key management:
    python tools/mcp_public.py --generate-key "username"
    python tools/mcp_public.py --list-keys
    python tools/mcp_public.py --revoke-key wxs_...

Users connect via MCP config:
    {
      "mcpServers": {
        "wxsection": {
          "url": "https://mcp.wxsection.com/sse?api_key=wxs_YOUR_KEY"
        }
      }
    }
"""

import argparse
import base64
import hashlib
import json
import math
import os
import secrets
import sys
import time
from collections import defaultdict
from datetime import datetime, timedelta
from urllib.parse import urlencode

from mcp.server.fastmcp import FastMCP

# Add parent dir so we can import agent_tools
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.mcp_helpers import _api_get, _ext_fetch_json, _ext_fetch_text

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

API_BASE = os.environ.get("WXSECTION_API_BASE", "http://127.0.0.1:5565")
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
API_KEYS_FILE = os.path.join(DATA_DIR, "mcp_api_keys.json")

# ---------------------------------------------------------------------------
# API Key Management
# ---------------------------------------------------------------------------

def _load_keys() -> dict:
    try:
        with open(API_KEYS_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_keys(keys: dict):
    os.makedirs(os.path.dirname(API_KEYS_FILE), exist_ok=True)
    with open(API_KEYS_FILE, "w") as f:
        json.dump(keys, f, indent=2)


def generate_key(name: str, rate_limit: int = 20) -> str:
    """Generate a new API key, store its hash, return plaintext once."""
    raw = secrets.token_hex(24)
    api_key = f"wxs_{raw}"
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()
    keys = _load_keys()
    keys[key_hash] = {
        "name": name,
        "created": datetime.utcnow().strftime("%Y-%m-%d"),
        "rate_limit": rate_limit,
    }
    _save_keys(keys)
    return api_key


def list_keys() -> list[dict]:
    keys = _load_keys()
    return [
        {"hash_prefix": h[:12] + "...", "name": v["name"],
         "created": v["created"], "rate_limit": v.get("rate_limit", 20)}
        for h, v in keys.items()
    ]


def revoke_key(api_key: str) -> bool:
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()
    keys = _load_keys()
    if key_hash in keys:
        del keys[key_hash]
        _save_keys(keys)
        return True
    return False


# ---------------------------------------------------------------------------
# MCP Server Instance
# ---------------------------------------------------------------------------

mcp = FastMCP(
    "wxsection-public",
    instructions=(
        "wxsection.com public atmospheric research platform. "
        "Generate vertical cross-sections from HRRR/GFS/RRFS weather models. "
        "Browse 88 historical weather events. Get raw numerical data. "
        "Access 232 city fire weather profiles with terrain, fuels, ignition sources, "
        "and evacuation routes. "
        "Ingest external data: METARs, RAWS, SPC products, NWS alerts, elevation, drought. "
        "Investigate fire weather at specific locations. "
        "Compare model forecasts with surface observations. "
        "Assess fire weather risk across CONUS regions."
    ),
)


# ============================================================================
# Cross-Section Tools (11)
# ============================================================================

@mcp.tool()
def get_capabilities() -> str:
    """Discover models, products, parameter constraints, coverage areas, and rate limits.

    Returns machine-readable metadata about the wxsection.com API so agents can
    understand valid parameter ranges without trial and error.
    """
    return json.dumps(_api_get("/api/v1/capabilities", api_base=API_BASE), indent=2)


@mcp.tool()
def list_events(category: str | None = None, has_data: bool | None = None) -> str:
    """Browse historical weather events (fires, hurricanes, tornadoes, derechos, etc.).

    Args:
        category: Filter by category slug (e.g. 'fire-ca', 'hurricane', 'tornado',
                  'derecho', 'hail', 'ar', 'winter', 'other'). Omit for all events.
        has_data: If true, only return events whose data is currently loaded/available.
    """
    params = {}
    if category:
        params["category"] = category
    if has_data is not None:
        params["has_data"] = str(has_data).lower()
    return json.dumps(_api_get("/api/v1/events", params, api_base=API_BASE), indent=2)


@mcp.tool()
def get_event(cycle_key: str) -> str:
    """Get detailed information about a specific historical weather event.

    Args:
        cycle_key: The event's cycle key (e.g. '20250107_00z' for the LA fires).
    """
    return json.dumps(_api_get(f"/api/v1/events/{cycle_key}", api_base=API_BASE), indent=2)


@mcp.tool()
def list_cycles(model: str = "hrrr") -> str:
    """List available model cycles with their forecast hours.

    Args:
        model: Weather model - 'hrrr' (3km CONUS, hourly), 'gfs' (0.25deg global),
               or 'rrfs' (3km CONUS experimental). Default: hrrr.
    """
    return json.dumps(_api_get("/api/v1/cycles", {"model": model}, api_base=API_BASE), indent=2)


@mcp.tool()
def list_products(model: str = "hrrr") -> str:
    """List available atmospheric visualization products/styles.

    Args:
        model: Weather model ('hrrr', 'gfs', 'rrfs'). Some products like 'smoke'
               are only available for HRRR. Default: hrrr.
    """
    return json.dumps(_api_get("/api/v1/products", {"model": model}, api_base=API_BASE), indent=2)


@mcp.tool()
def generate_cross_section(
    start_lat: float, start_lon: float,
    end_lat: float, end_lon: float,
    product: str = "temperature", model: str = "hrrr",
    cycle: str = "latest", fhr: int = 0,
    y_axis: str = "pressure", y_top: int = 100, units: str = "km",
    marker_lat: float = None, marker_lon: float = None,
    marker_label: str = None,
    markers: str = None,
) -> str:
    """Generate a PNG atmospheric cross-section between two geographic points.

    Draws a vertical slice through the atmosphere along a great-circle path.
    Returns a base64-encoded PNG image suitable for display, plus metadata.

    Args:
        start_lat: Starting latitude (-90 to 90).
        start_lon: Starting longitude (-180 to 180). Use negative for west.
        end_lat: Ending latitude.
        end_lon: Ending longitude.
        product: Atmospheric variable ('temperature', 'wind_speed', 'rh', 'omega',
                 'theta_e', 'smoke', 'fire_wx'). Use list_products() for all.
        model: Weather model ('hrrr', 'gfs', 'rrfs'). Default: hrrr.
        cycle: Model cycle key (e.g. '20260205_12z') or 'latest'.
        fhr: Forecast hour (0=analysis). Default: 0.
        y_axis: 'pressure' (hPa), 'height' (km), or 'isentropic' (theta K).
        y_top: Top of plot in hPa (100=full, 300=mid, 500=low, 700=BL). Default: 100.
        units: Distance axis units - 'km' or 'mi'. Default: km.
        marker_lat: Optional POI latitude. Draws a red X on terrain at this point.
        marker_lon: Optional POI longitude (pair with marker_lat).
        marker_label: Optional label for the POI (e.g. 'Camp Fire', 'Denver').
        markers: Optional JSON array of multiple POIs. Each: {"lat","lon","label"}.
                 Example: '[{"lat":39.1,"lon":-121.4,"label":"Camp Fire"}]'
    """
    params = {
        "start_lat": start_lat, "start_lon": start_lon,
        "end_lat": end_lat, "end_lon": end_lon,
        "product": product, "model": model, "cycle": cycle, "fhr": fhr,
        "y_axis": y_axis, "y_top": y_top, "units": units,
    }
    if markers:
        params["markers"] = markers if isinstance(markers, str) else json.dumps(markers)
    elif marker_lat is not None and marker_lon is not None:
        params["marker_lat"] = marker_lat
        params["marker_lon"] = marker_lon
        if marker_label:
            params["marker_label"] = marker_label
    png_bytes = _api_get("/api/v1/cross-section", params, raw=True, api_base=API_BASE)
    if isinstance(png_bytes, dict):
        return json.dumps(png_bytes, indent=2)
    if png_bytes[:1] == b'{':
        try:
            return json.dumps(json.loads(png_bytes), indent=2)
        except json.JSONDecodeError:
            pass
    b64 = base64.b64encode(png_bytes).decode("ascii")
    return json.dumps({
        "image_base64": b64, "mime_type": "image/png",
        "size_bytes": len(png_bytes),
        "metadata": {
            "model": model, "cycle": cycle, "fhr": fhr, "product": product,
            "start": [start_lat, start_lon], "end": [end_lat, end_lon],
            "y_axis": y_axis, "y_top": y_top, "units": units,
        },
    })


@mcp.tool()
def get_atmospheric_data(
    start_lat: float, start_lon: float,
    end_lat: float, end_lon: float,
    product: str = "temperature", model: str = "hrrr",
    cycle: str = "latest", fhr: int = 0,
    y_axis: str = "pressure", y_top: int = 100, units: str = "km",
) -> str:
    """Get raw numerical atmospheric data along a cross-section path as JSON arrays.

    Returns interpolated values along a cross-section: distances, pressure levels,
    coordinates, and 2D data arrays [n_levels x n_points].

    Args:
        start_lat: Starting latitude (-90 to 90).
        start_lon: Starting longitude (-180 to 180).
        end_lat: Ending latitude.
        end_lon: Ending longitude.
        product: Atmospheric variable ('temperature', 'wind_speed', 'rh', etc.).
        model: Weather model ('hrrr', 'gfs', 'rrfs'). Default: hrrr.
        cycle: Model cycle key or 'latest'. Default: latest.
        fhr: Forecast hour. Default: 0.
        y_axis: 'pressure', 'height', or 'isentropic'. Default: pressure.
        y_top: Top of plot in hPa. Default: 100.
        units: 'km' or 'mi'. Default: km.
    """
    params = {
        "start_lat": start_lat, "start_lon": start_lon,
        "end_lat": end_lat, "end_lon": end_lon,
        "product": product, "model": model, "cycle": cycle, "fhr": fhr,
        "y_axis": y_axis, "y_top": y_top, "units": units,
    }
    return json.dumps(_api_get("/api/v1/data", params, api_base=API_BASE))


@mcp.tool()
def generate_cross_section_gif(
    start_lat: float, start_lon: float,
    end_lat: float, end_lon: float,
    product: str = "fire_wx", model: str = "hrrr",
    fhr_min: int = 0, fhr_max: int = 12,
) -> str:
    """Generate an animated GIF cross-section showing temporal evolution.

    Cycles through forecast hours to show wind shifts, humidity changes,
    frontal passages. Returns base64-encoded GIF.

    Args:
        start_lat/lon: Starting point.
        end_lat/lon: Ending point.
        product: Atmospheric variable. Default: fire_wx.
        model: Weather model. Default: hrrr.
        fhr_min: First forecast hour. Default: 0.
        fhr_max: Last forecast hour. Default: 12.
    """
    params = {
        "start_lat": start_lat, "start_lon": start_lon,
        "end_lat": end_lat, "end_lon": end_lon,
        "product": product, "model": model,
        "fhr_min": fhr_min, "fhr_max": fhr_max,
    }
    url = f"{API_BASE}/api/v1/cross-section/gif?{urlencode(params)}"
    try:
        from urllib.request import urlopen, Request
        req = Request(url, headers={"User-Agent": "wxsection-mcp/1.0"})
        with urlopen(req, timeout=120) as resp:
            gif_data = resp.read()
            return json.dumps({
                "format": "gif", "size_bytes": len(gif_data),
                "image_base64": base64.b64encode(gif_data).decode(),
                "params": params,
            })
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def get_status() -> str:
    """Get server health, loaded cycles, and memory usage."""
    return json.dumps(_api_get("/api/v1/status", api_base=API_BASE), indent=2)


@mcp.tool()
def generate_comparison(
    start_lat: float, start_lon: float,
    end_lat: float, end_lon: float,
    mode: str = "model", product: str = "temperature",
    model: str = "hrrr", cycle: str = "latest", fhr: int = 0,
    models: str = "", fhrs: str = "", products: str = "", cycles: str = "",
    cycle_match: str = "same_fhr",
    y_axis: str = "pressure", y_top: int = 300, units: str = "km",
) -> str:
    """Generate a multi-panel comparison cross-section image (2-4 panels).

    Modes:
    - model: Compare models (set models="hrrr,gfs").
    - temporal: Compare forecast hours (set fhrs="0,6,12").
    - product: Compare products (set products="wind_speed,rh").
    - cycle: Compare init cycles (set cycles="20260209_06z,20260209_00z").

    Returns base64-encoded PNG.
    """
    params = {
        "start_lat": start_lat, "start_lon": start_lon,
        "end_lat": end_lat, "end_lon": end_lon,
        "mode": mode, "product": product, "model": model,
        "cycle": cycle, "fhr": fhr,
        "y_axis": y_axis, "y_top": y_top, "units": units,
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
    png_bytes = _api_get("/api/v1/comparison", params, raw=True, api_base=API_BASE)
    if isinstance(png_bytes, dict):
        return json.dumps(png_bytes, indent=2)
    if png_bytes[:1] == b'{':
        try:
            return json.dumps(json.loads(png_bytes), indent=2)
        except json.JSONDecodeError:
            pass
    b64 = base64.b64encode(png_bytes).decode("ascii")
    return json.dumps({
        "image_base64": b64, "mime_type": "image/png",
        "size_bytes": len(png_bytes),
        "metadata": {
            "mode": mode, "model": model, "cycle": cycle, "fhr": fhr,
            "product": product, "start": [start_lat, start_lon],
            "end": [end_lat, end_lon],
        },
    })


@mcp.tool()
def generate_comparison_gif(
    start_lat: float, start_lon: float,
    end_lat: float, end_lon: float,
    mode: str = "model", product: str = "fire_wx", model: str = "hrrr",
    models: str = "", products: str = "",
    fhr_min: int = 0, fhr_max: int = 12,
) -> str:
    """Generate animated GIF of multi-panel comparison across forecast hours.

    Returns base64-encoded GIF.
    """
    params = {
        "start_lat": start_lat, "start_lon": start_lon,
        "end_lat": end_lat, "end_lon": end_lon,
        "mode": mode, "product": product, "model": model,
        "fhr_min": fhr_min, "fhr_max": fhr_max,
    }
    if models:
        params["models"] = models
    if products:
        params["products"] = products
    url = f"{API_BASE}/api/v1/comparison/gif?{urlencode(params)}"
    try:
        from urllib.request import urlopen, Request
        req = Request(url, headers={"User-Agent": "wxsection-mcp/1.0"})
        with urlopen(req, timeout=180) as resp:
            gif_data = resp.read()
            return json.dumps({
                "format": "gif", "size_bytes": len(gif_data),
                "image_base64": base64.b64encode(gif_data).decode(),
                "params": params,
            })
    except Exception as e:
        return json.dumps({"error": str(e)})


# ============================================================================
# External Data Tools (9)
# ============================================================================

@mcp.tool()
def get_metar(stations: str, hours_back: int = 3) -> str:
    """Get METAR surface weather observations from ASOS/AWOS stations.

    Args:
        stations: Comma-separated ICAO station IDs (e.g. "KDEN,KCOS,KGJT").
        hours_back: Hours of history to retrieve (1-48). Default: 3.
    """
    now = datetime.utcnow()
    dt_start = now - timedelta(hours=hours_back)
    url = (
        f"https://mesonet.agron.iastate.edu/json/asos.py?"
        f"station={stations}"
        f"&year1={dt_start.year}&month1={dt_start.month}&day1={dt_start.day}"
        f"&hour1={dt_start.hour}&minute1={dt_start.minute}"
        f"&year2={now.year}&month2={now.month}&day2={now.day}"
        f"&hour2={now.hour}&minute2={now.minute}"
        f"&tz=UTC&format=json&latlon=yes&elev=yes&trace=0.0001"
    )
    return json.dumps(_ext_fetch_json(url), indent=2)


@mcp.tool()
def find_stations(lat: float, lon: float, radius_km: float = 100) -> str:
    """Find ASOS/AWOS weather stations near a geographic point.

    Args:
        lat: Latitude of search center.
        lon: Longitude of search center (negative for west).
        radius_km: Search radius in km (default 100, max 500).
    """
    data = _ext_fetch_json(
        "https://mesonet.agron.iastate.edu/geojson/network/ASOS.geojson", timeout=30
    )
    if "error" in data:
        return json.dumps(data)
    stations = []
    for feat in data.get("features", []):
        props = feat.get("properties", {})
        coords = feat.get("geometry", {}).get("coordinates", [0, 0])
        slon, slat = coords[0], coords[1]
        dlat = math.radians(slat - lat)
        dlon = math.radians(slon - lon)
        a = (math.sin(dlat / 2) ** 2 +
             math.cos(math.radians(lat)) * math.cos(math.radians(slat)) *
             math.sin(dlon / 2) ** 2)
        dist_km = 6371 * 2 * math.asin(math.sqrt(a))
        if dist_km <= radius_km:
            stations.append({
                "id": props.get("sid", ""), "name": props.get("sname", ""),
                "state": props.get("state", ""),
                "lat": slat, "lon": slon,
                "elevation_m": props.get("elevation"),
                "distance_km": round(dist_km, 1),
            })
    stations.sort(key=lambda s: s["distance_km"])
    return json.dumps(stations[:50], indent=2)


@mcp.tool()
def get_raws(lat: float, lon: float, radius_miles: float = 50, hours_back: int = 6) -> str:
    """Get RAWS fire weather station observations near a point.

    Args:
        lat: Latitude of search center.
        lon: Longitude of search center.
        radius_miles: Search radius in miles (default 50).
        hours_back: Hours of history (default 6).
    """
    now = datetime.utcnow()
    start = now - timedelta(hours=hours_back)
    params = {
        "token": "demotoken",
        "start": start.strftime("%Y%m%d%H%M"),
        "end": now.strftime("%Y%m%d%H%M"),
        "obtimezone": "UTC",
        "vars": "air_temp,relative_humidity,wind_speed,wind_direction,wind_gust,fuel_moisture",
        "units": "english",
        "radius": f"{lat},{lon},{radius_miles}",
        "network": "2",
    }
    url = "https://api.synopticdata.com/v2/stations/timeseries?" + urlencode(params)
    return json.dumps(_ext_fetch_json(url, timeout=30), indent=2)


@mcp.tool()
def get_spc_fire_outlook(day: int = 1) -> str:
    """Get SPC Fire Weather Outlook with risk polygons (CRITICAL/ELEVATED areas).

    Args:
        day: Outlook day — 1 (today) or 2 (tomorrow). Default: 1.
    """
    if day == 1:
        url = "https://www.spc.noaa.gov/products/fire_wx/fwdy1.json"
    elif day == 2:
        url = "https://www.spc.noaa.gov/products/fire_wx/fwdy2.json"
    else:
        return json.dumps({"error": f"Invalid day {day}, must be 1 or 2"})
    return json.dumps(_ext_fetch_json(url), indent=2)


@mcp.tool()
def get_spc_discussion() -> str:
    """Get the latest SPC Fire Weather Discussion text."""
    import re
    html = _ext_fetch_text("https://www.spc.noaa.gov/products/fire_wx/fwdy1.html")
    if html.startswith("Error:"):
        return html
    m = re.search(r'<pre>(.*?)</pre>', html, re.DOTALL)
    return m.group(1).strip() if m else html[:5000]


@mcp.tool()
def get_nws_alerts(
    state: str | None = None, lat: float | None = None,
    lon: float | None = None, event_type: str | None = None,
) -> str:
    """Get active NWS weather alerts (Red Flag Warnings, Fire Weather Watches, etc.).

    Args:
        state: Two-letter state code (e.g. "MT", "CA").
        lat: Latitude for point search (use with lon).
        lon: Longitude for point search.
        event_type: Filter (e.g. "Red Flag Warning", "Fire Weather Watch").
    """
    params = {"status": "actual"}
    if lat is not None and lon is not None:
        params["point"] = f"{lat},{lon}"
    if state:
        params["area"] = state
    if event_type:
        params["event"] = event_type
    url = "https://api.weather.gov/alerts?" + urlencode(params)
    result = _ext_fetch_json(url, headers={"Accept": "application/geo+json"})
    if "features" in result:
        trimmed = []
        for f in result["features"][:20]:
            props = f.get("properties", {})
            trimmed.append({
                "event": props.get("event"), "headline": props.get("headline"),
                "severity": props.get("severity"), "urgency": props.get("urgency"),
                "onset": props.get("onset"), "expires": props.get("expires"),
                "areaDesc": props.get("areaDesc"),
                "description": (props.get("description") or "")[:1000],
            })
        return json.dumps({"count": len(result["features"]), "alerts": trimmed}, indent=2)
    return json.dumps(result, indent=2)


@mcp.tool()
def get_forecast_discussion(office: str) -> str:
    """Get NWS Area Forecast Discussion from a weather office.

    Args:
        office: NWS WFO ID (e.g. BOU, ABQ, MSO, LOX, SGX, STO, PDT, AMA, LBB).
    """
    result = _ext_fetch_json(
        f"https://api.weather.gov/products/types/AFD/locations/{office}",
        headers={"Accept": "application/json"},
    )
    if "error" in result:
        return json.dumps(result)
    graph = result.get("@graph", [])
    if not graph:
        return json.dumps({"error": f"No AFD found for office {office}"})
    latest_url = graph[0].get("@id", "")
    if not latest_url:
        return json.dumps({"error": "Could not find latest AFD URL"})
    product = _ext_fetch_json(latest_url, headers={"Accept": "application/json"})
    return product.get("productText", "No text available")


@mcp.tool()
def get_elevation(lat: float, lon: float) -> str:
    """Get terrain elevation at a geographic point.

    Args:
        lat: Latitude.
        lon: Longitude.
    """
    data = _ext_fetch_json(
        f"https://api.open-elevation.com/api/v1/lookup?locations={lat},{lon}", timeout=15
    )
    results = data.get("results", [{}])
    elev_m = results[0].get("elevation", 0) if results else 0
    return json.dumps({
        "lat": lat, "lon": lon,
        "elevation_m": elev_m, "elevation_ft": round(elev_m * 3.281),
    }, indent=2)


@mcp.tool()
def get_drought(state: str | None = None) -> str:
    """Get US Drought Monitor status (D0-D4 area percentages).

    Args:
        state: Two-letter state code, or omit for national stats.
    """
    if state:
        url = f"https://usdm.unl.edu/api/area_percent/stateStatistics/{state}"
    else:
        url = "https://usdm.unl.edu/api/area_percent/nationalStatistics"
    return json.dumps(_ext_fetch_json(url, timeout=15), indent=2)


# ============================================================================
# Fire Weather Assessment Tools (4)
# ============================================================================

FIRE_REGIONS = {
    "northern_rockies": {"start": [47.5, -116.0], "end": [45.0, -110.0], "label": "Northern Rockies (ID/MT)"},
    "high_plains_north": {"start": [43.0, -106.0], "end": [41.0, -102.0], "label": "High Plains North (WY/NE)"},
    "high_plains_south": {"start": [36.5, -106.0], "end": [35.0, -102.0], "label": "High Plains South (NM/TX)"},
    "southwest_az": {"start": [34.5, -114.0], "end": [32.0, -109.0], "label": "Southwest (AZ)"},
    "socal": {"start": [34.5, -119.5], "end": [33.5, -117.0], "label": "Southern California"},
    "pacific_nw": {"start": [47.0, -123.0], "end": [44.0, -120.0], "label": "Pacific NW (WA/OR)"},
    "sierra_nevada": {"start": [39.0, -122.0], "end": [37.0, -118.0], "label": "Sierra Nevada"},
    "front_range": {"start": [40.5, -106.0], "end": [38.5, -104.0], "label": "Front Range (CO)"},
    "great_basin": {"start": [41.0, -118.0], "end": [39.0, -114.0], "label": "Great Basin (NV)"},
    "texas_panhandle": {"start": [36.0, -103.0], "end": [34.0, -100.0], "label": "Texas Panhandle"},
    "oklahoma": {"start": [36.5, -100.0], "end": [35.0, -97.0], "label": "Oklahoma"},
    "central_ca": {"start": [38.0, -123.0], "end": [36.0, -119.0], "label": "Central CA Coast/Valley"},
}


def _assess_risk_from_data(rh_data: dict, wind_data: dict) -> dict:
    """Compute fire risk score from RH and wind cross-section data."""
    def _surface_vals(data_dict):
        sp = data_dict.get("surface_pressure_hpa", [])
        pressures = data_dict.get("pressure_levels_hpa", [])
        skip = {"pressure_levels_hpa", "surface_pressure_hpa", "distances_km",
                "lats", "lons", "metadata", "elevations_m"}
        data_2d = None
        data_key = None
        for k, v in data_dict.items():
            if k not in skip and isinstance(v, list) and len(v) > 0:
                if isinstance(v[0], list):
                    data_2d = v
                    data_key = k
                    break
        if data_2d is None or not sp or not pressures:
            return [], data_key
        vals = []
        for j in range(len(sp)):
            best_i = None
            for i, p in enumerate(pressures):
                if p <= sp[j] + 5:
                    if best_i is None or pressures[i] > pressures[best_i]:
                        best_i = i
            if best_i is not None and j < len(data_2d[best_i]):
                v = data_2d[best_i][j]
                if v is not None:
                    vals.append(v)
        return vals, data_key

    rh_vals, _ = _surface_vals(rh_data)
    wind_vals, _ = _surface_vals(wind_data)

    if not rh_vals or not wind_vals:
        return {"risk_level": "UNKNOWN", "risk_score": 0, "error": "Insufficient data"}

    rh_min = min(rh_vals)
    rh_mean = sum(rh_vals) / len(rh_vals)
    rh_below_15 = sum(1 for v in rh_vals if v < 15) / len(rh_vals) * 100
    wind_max = max(wind_vals)
    wind_mean = sum(wind_vals) / len(wind_vals)
    wind_above_25 = sum(1 for v in wind_vals if v > 25) / len(wind_vals) * 100

    rh_score = min(40, max(0, (30 - rh_mean) / 30 * 40))
    wind_score = min(30, max(0, (wind_mean - 15) / 25 * 30))
    extreme_rh_score = min(20, rh_below_15 / 100 * 20)
    extreme_wind_score = min(10, wind_above_25 / 100 * 10)
    total = rh_score + wind_score + extreme_rh_score + extreme_wind_score

    if total >= 70:
        level = "CRITICAL"
    elif total >= 50:
        level = "ELEVATED"
    elif total >= 30:
        level = "MODERATE"
    else:
        level = "LOW"

    factors = []
    if rh_min < 15:
        factors.append(f"Red Flag RH: min {rh_min:.0f}%")
    if rh_below_15 > 20:
        factors.append(f"{rh_below_15:.0f}% of transect below 15% RH")
    if wind_max > 25:
        factors.append(f"Red Flag winds: max {wind_max:.0f} kt")
    if wind_above_25 > 10:
        factors.append(f"{wind_above_25:.0f}% of transect above 25 kt wind")
    if rh_min < 8:
        factors.append(f"Extreme: min RH {rh_min:.0f}%")

    return {
        "risk_level": level, "risk_score": round(total, 1), "factors": factors,
        "stats": {
            "rh_min_pct": round(rh_min, 1), "rh_mean_pct": round(rh_mean, 1),
            "rh_pct_below_15": round(rh_below_15, 1),
            "wind_max_kt": round(wind_max, 1), "wind_mean_kt": round(wind_mean, 1),
            "wind_pct_above_25": round(wind_above_25, 1),
        },
    }


@mcp.tool()
def assess_fire_risk(
    start_lat: float, start_lon: float,
    end_lat: float, end_lon: float,
    cycle: str = "latest", fhr: int = 0, model: str = "hrrr",
) -> str:
    """Assess fire weather risk along a cross-section transect (0-100 score).

    Risk levels: CRITICAL (70-100), ELEVATED (50-69), MODERATE (30-49), LOW (0-29).

    Args:
        start_lat/lon: Start of transect.
        end_lat/lon: End of transect.
        cycle: Model cycle or 'latest'.
        fhr: Forecast hour.
        model: Weather model.
    """
    base = {
        "start_lat": start_lat, "start_lon": start_lon,
        "end_lat": end_lat, "end_lon": end_lon,
        "model": model, "cycle": cycle, "fhr": fhr,
    }
    rh_data = _api_get("/api/v1/data", {**base, "product": "rh"}, api_base=API_BASE)
    wind_data = _api_get("/api/v1/data", {**base, "product": "wind_speed"}, api_base=API_BASE)
    if isinstance(rh_data, dict) and "error" in rh_data:
        return json.dumps(rh_data)
    if isinstance(wind_data, dict) and "error" in wind_data:
        return json.dumps(wind_data)
    assessment = _assess_risk_from_data(rh_data, wind_data)
    assessment["transect"] = {"start": [start_lat, start_lon], "end": [end_lat, end_lon]}
    assessment["model"] = model
    assessment["cycle"] = cycle
    assessment["fhr"] = fhr
    return json.dumps(assessment, indent=2)


@mcp.tool()
def national_fire_scan(
    cycle: str = "latest", fhr: int = 12, model: str = "hrrr",
) -> str:
    """Quick national scan of fire risk across 12 CONUS fire-prone regions.

    Args:
        cycle: Model cycle or 'latest'. Default: latest.
        fhr: Forecast hour. Default: 12 (afternoon peak).
        model: Weather model. Default: hrrr.
    """
    results = {}
    for name, region in FIRE_REGIONS.items():
        base = {
            "start_lat": region["start"][0], "start_lon": region["start"][1],
            "end_lat": region["end"][0], "end_lon": region["end"][1],
            "model": model, "cycle": cycle, "fhr": fhr,
        }
        rh_data = _api_get("/api/v1/data", {**base, "product": "rh"}, api_base=API_BASE)
        wind_data = _api_get("/api/v1/data", {**base, "product": "wind_speed"}, api_base=API_BASE)
        if isinstance(rh_data, dict) and "error" in rh_data:
            results[name] = {"risk_level": "ERROR", "error": rh_data.get("error")}
            continue
        if isinstance(wind_data, dict) and "error" in wind_data:
            results[name] = {"risk_level": "ERROR", "error": wind_data.get("error")}
            continue
        assessment = _assess_risk_from_data(rh_data, wind_data)
        assessment["label"] = region["label"]
        assessment["transect"] = {"start": region["start"], "end": region["end"]}
        results[name] = assessment
    sorted_results = dict(sorted(results.items(),
                                  key=lambda x: x[1].get("risk_score", 0), reverse=True))
    return json.dumps({
        "model": model, "cycle": cycle, "fhr": fhr,
        "regions": sorted_results,
        "summary": {
            "critical": [k for k, v in sorted_results.items() if v.get("risk_level") == "CRITICAL"],
            "elevated": [k for k, v in sorted_results.items() if v.get("risk_level") == "ELEVATED"],
        },
    }, indent=2)


@mcp.tool()
def sub_metro_fire_scan(
    metro: str, cycle: str = "latest", fhr: int = 12, model: str = "hrrr",
) -> str:
    """Scan sub-areas within a metro for granular WUI fire risk.

    Available metros: denver_metro, colorado_springs, la_metro,
    phoenix_metro, albuquerque_metro, reno_tahoe, oklahoma_metro.
    """
    from tools.agent_tools.fire_risk import SUB_METRO_AREAS
    metro_def = SUB_METRO_AREAS.get(metro)
    if not metro_def:
        return json.dumps({"error": f"Unknown metro '{metro}'. Available: denver_metro, colorado_springs, la_metro, phoenix_metro, albuquerque_metro, reno_tahoe, oklahoma_metro"})
    results = {"metro": metro_def["label"], "sub_areas": {}}
    for area in metro_def["sub_areas"]:
        base = {
            "start_lat": area["start"][0], "start_lon": area["start"][1],
            "end_lat": area["end"][0], "end_lon": area["end"][1],
            "model": model, "cycle": cycle, "fhr": fhr,
        }
        rh_data = _api_get("/api/v1/data", {**base, "product": "rh"}, api_base=API_BASE)
        wind_data = _api_get("/api/v1/data", {**base, "product": "wind_speed"}, api_base=API_BASE)
        if isinstance(rh_data, dict) and "error" in rh_data:
            results["sub_areas"][area["key"]] = {"label": area["label"], "risk_level": "ERROR"}
            continue
        if isinstance(wind_data, dict) and "error" in wind_data:
            results["sub_areas"][area["key"]] = {"label": area["label"], "risk_level": "ERROR"}
            continue
        assessment = _assess_risk_from_data(rh_data, wind_data)
        assessment["label"] = area["label"]
        assessment["notes"] = area.get("notes", "")
        assessment["transect"] = {"start": area["start"], "end": area["end"]}
        results["sub_areas"][area["key"]] = assessment
    results["sub_areas"] = dict(sorted(
        results["sub_areas"].items(),
        key=lambda x: x[1].get("risk_score", 0), reverse=True,
    ))
    return json.dumps(results, indent=2)


@mcp.tool()
def compute_fire_indices(
    temp_c: float, rh_pct: float, wind_kt: float,
    temp_700_c: float | None = None, dewpoint_850_c: float | None = None,
) -> str:
    """Compute fire weather indices (VPD, Fosberg FWI, Haines Index).

    Args:
        temp_c: Surface temperature in Celsius.
        rh_pct: Surface relative humidity (%).
        wind_kt: Surface wind speed in knots.
        temp_700_c: Temperature at 700 hPa (for Haines Index).
        dewpoint_850_c: Dewpoint at 850 hPa (for Haines Index).
    """
    es = 6.112 * math.exp(17.67 * temp_c / (temp_c + 243.5))
    vpd = es * (1 - rh_pct / 100.0)
    wind_mph = wind_kt * 1.15078
    if rh_pct <= 10:
        m = 0.03229 + 0.281073 * rh_pct - 0.000578 * rh_pct * temp_c
    elif rh_pct <= 50:
        m = 2.22749 + 0.160107 * rh_pct - 0.01478 * temp_c
    else:
        m = 21.0606 + 0.005565 * rh_pct ** 2 - 0.00035 * rh_pct * temp_c - 0.483199 * rh_pct
    m = max(0, min(m, 35))
    eta = 1 - 2 * (m / 30) + 1.5 * (m / 30) ** 2 - 0.5 * (m / 30) ** 3
    ffwi = eta * math.sqrt(1 + wind_mph ** 2) / 0.3002
    result = {
        "vpd_hpa": round(vpd, 2),
        "vpd_assessment": "EXTREME" if vpd > 45 else "HIGH" if vpd > 30 else "MODERATE" if vpd > 15 else "LOW",
        "fosberg_fwi": round(ffwi, 1),
        "fwi_assessment": "EXTREME" if ffwi > 75 else "VERY HIGH" if ffwi > 50 else "HIGH" if ffwi > 25 else "MODERATE" if ffwi > 13 else "LOW",
        "rh_flag": rh_pct < 15,
        "wind_flag": wind_kt > 25,
    }
    if temp_700_c is not None and dewpoint_850_c is not None:
        temp_850_c = temp_c - 15
        stability = temp_850_c - temp_700_c
        a = 1 if stability < 4 else (2 if stability < 8 else 3)
        moisture_diff = temp_850_c - dewpoint_850_c
        b = 1 if moisture_diff < 6 else (2 if moisture_diff < 10 else 3)
        haines = a + b
        result["haines_index"] = haines
        result["haines_assessment"] = "HIGH" if haines >= 5 else "MODERATE" if haines >= 4 else "LOW"
    return json.dumps(result, indent=2)


# ============================================================================
# Investigation Tools (5)
# ============================================================================

@mcp.tool()
def investigate_location(lat: float, lon: float, name: str | None = None) -> str:
    """Comprehensive fire weather investigation for a specific location.

    Gathers METAR observations, NWS alerts, SPC fire outlook, elevation,
    and drought status. Returns a complete profile with investigation notes.
    """
    from tools.agent_tools.investigation import investigate_location as _investigate
    return json.dumps(_investigate(lat, lon, name=name, base_url=API_BASE), indent=2, default=str)


@mcp.tool()
def investigate_town(town: str, state: str) -> str:
    """Investigate fire weather conditions for a named town.

    Geocodes the town and runs a full investigation.
    """
    from tools.agent_tools.investigation import investigate_town as _investigate_town
    return json.dumps(_investigate_town(town, state, base_url=API_BASE), indent=2, default=str)


@mcp.tool()
def compare_model_obs(
    lat: float, lon: float, station_id: str | None = None,
    model: str = "hrrr", fhr: int = 0,
) -> str:
    """Compare model forecast with actual surface observations.

    Critical for fire weather: model cross-section data averages through
    the full column. Surface RH can be 11% while column average shows 45%.
    """
    from tools.agent_tools.external_data import get_model_obs_comparison
    return json.dumps(
        get_model_obs_comparison(lat, lon, station_id=station_id, model=model, fhr=fhr, base_url=API_BASE),
        indent=2, default=str,
    )


@mcp.tool()
def get_point_forecast(lat: float, lon: float, model: str = "hrrr", fhr: int = 0) -> str:
    """Get model surface conditions at a specific point.

    Returns temperature, RH, wind speed, dewpoint from model's lowest level.
    """
    from tools.agent_tools.external_data import get_point_surface_conditions
    return json.dumps(
        get_point_surface_conditions(lat, lon, model=model, fhr=fhr, base_url=API_BASE),
        indent=2, default=str,
    )


@mcp.tool()
def batch_investigate(locations_json: str) -> str:
    """Investigate multiple locations at once.

    Args:
        locations_json: JSON array: [{"lat": 35.36, "lon": -97.18, "name": "Newalla"}, ...]
    """
    from tools.agent_tools.investigation import batch_investigate as _batch
    locations = json.loads(locations_json)
    locs = [(l["lat"], l["lon"], l.get("name")) for l in locations]
    return json.dumps(_batch(locs, base_url=API_BASE), indent=2, default=str)


# ============================================================================
# Terrain & Fuel Tools (8)
# ============================================================================

@mcp.tool()
def analyze_terrain(lat: float, lon: float, radius_km: float = 15) -> str:
    """Analyze terrain complexity — identifies canyons, valleys, slopes, flat areas.
    Critical for fire behavior: canyon terrain creates channeled winds."""
    from tools.agent_tools.terrain import analyze_terrain_complexity
    return json.dumps(analyze_terrain_complexity(lat, lon, radius_km), indent=2, default=str)


@mcp.tool()
def city_terrain(lat: float, lon: float, city_name: str, radius_km: float = 20) -> str:
    """Assess terrain around a city by quadrant (N/E/S/W/NE/SE/SW/NW).
    Includes expert knowledge for 232 fire-prone cities."""
    from tools.agent_tools.terrain import city_terrain_assessment
    return json.dumps(city_terrain_assessment(lat, lon, city_name, radius_km), indent=2, default=str)


@mcp.tool()
def assess_fuels(lat: float, lon: float, station_id: str | None = None) -> str:
    """Assess current fuel conditions — recent weather history, drought, seasonal context.
    Fuels are the #1 factor in fire behavior."""
    from tools.agent_tools.fuel_conditions import assess_fuel_conditions
    return json.dumps(assess_fuel_conditions(lat, lon, station_id, base_url=API_BASE), indent=2, default=str)


@mcp.tool()
def get_ignition_sources(lat: float, lon: float, city_name: str | None = None) -> str:
    """Get ignition risk sources — trucking corridors, power lines, railroads."""
    from tools.agent_tools.fuel_conditions import get_ignition_risk
    return json.dumps(get_ignition_risk(lat, lon, city_name), indent=2, default=str)


@mcp.tool()
def detect_wind_shifts(lat: float, lon: float, model: str = "hrrr") -> str:
    """Detect wind direction shifts in HRRR forecast — cold front passages
    that reverse firelines."""
    from tools.agent_tools.frontal_analysis import detect_wind_shifts as _detect
    return json.dumps(_detect(lat, lon, model=model, base_url=API_BASE), indent=2, default=str)


@mcp.tool()
def classify_overnight(lat: float, lon: float, model: str = "hrrr") -> str:
    """Classify overnight fire weather — true recovery, frontal shift,
    partial recovery, or no recovery."""
    from tools.agent_tools.frontal_analysis import classify_overnight_conditions
    return json.dumps(classify_overnight_conditions(lat, lon, model=model, base_url=API_BASE), indent=2, default=str)


@mcp.tool()
def verify_winds(lat: float, lon: float, radius_miles: float = 30, hours_back: int = 24) -> str:
    """Verify wind speed claims against ALL available observations
    (ASOS + state mesonets + RAWS)."""
    from tools.agent_tools.external_data import verify_wind_claims
    return json.dumps(verify_wind_claims(lat, lon, radius_miles, hours_back), indent=2, default=str)


@mcp.tool()
def get_fire_climatology(station_id: str, month: int | None = None) -> str:
    """Get fire weather climatology for a station — what's normal vs extreme."""
    from tools.agent_tools.external_data import get_fire_weather_climatology
    return json.dumps(get_fire_weather_climatology(station_id, month), indent=2, default=str)


# ============================================================================
# NEW: City Data Browsing Tools (3)
# ============================================================================

def _get_all_city_profiles() -> dict:
    """Lazy-load and return the merged CITY_TERRAIN_PROFILES dict."""
    from tools.agent_tools.terrain import CITY_TERRAIN_PROFILES
    return CITY_TERRAIN_PROFILES


def _get_ignition_sources() -> dict:
    """Lazy-load and return the merged IGNITION_SOURCES dict."""
    from tools.agent_tools.fuel_conditions import IGNITION_SOURCES
    return IGNITION_SOURCES


# Map city keys to their region based on import source
_REGION_MAP = {}


def _build_region_map():
    """Build a mapping of city_key -> region name."""
    if _REGION_MAP:
        return
    region_modules = [
        ("california", "tools.agent_tools.data.california_profiles", "CA_TERRAIN_PROFILES"),
        ("pnw_rockies", "tools.agent_tools.data.pnw_rockies_profiles", "PNW_TERRAIN_PROFILES"),
        ("colorado_basin", "tools.agent_tools.data.colorado_basin_profiles", "CO_BASIN_TERRAIN_PROFILES"),
        ("southwest", "tools.agent_tools.data.southwest_profiles", "SW_TERRAIN_PROFILES"),
        ("southern_plains", "tools.agent_tools.data.southern_plains_profiles", "PLAINS_TERRAIN_PROFILES"),
        ("southeast_misc", "tools.agent_tools.data.southeast_misc_profiles", "SE_MISC_TERRAIN_PROFILES"),
    ]
    for region_name, mod_name, attr_name in region_modules:
        try:
            mod = __import__(mod_name, fromlist=[attr_name])
            profiles = getattr(mod, attr_name, {})
            for key in profiles:
                _REGION_MAP[key] = region_name
        except ImportError:
            pass
    # Remaining keys in CITY_TERRAIN_PROFILES not in any regional file
    profiles = _get_all_city_profiles()
    for key in profiles:
        if key not in _REGION_MAP:
            _REGION_MAP[key] = "other"


@mcp.tool()
def list_cities(region: str = "") -> str:
    """List all 232 cities with fire weather profiles.

    Filter by region: california, pnw_rockies, colorado_basin,
    southwest, southern_plains, southeast_misc.

    Args:
        region: Region filter (optional). Empty string for all cities.

    Returns:
        JSON array of cities with key, center coordinates, elevation,
        WUI class, danger quadrants, and region.
    """
    _build_region_map()
    profiles = _get_all_city_profiles()
    cities = []
    for key, profile in sorted(profiles.items()):
        city_region = _REGION_MAP.get(key, "other")
        if region and city_region != region:
            continue
        center = profile.get("center", profile.get("coords", (0, 0)))
        cities.append({
            "key": key,
            "lat": center[0] if center else 0,
            "lon": center[1] if center else 0,
            "elevation_ft": profile.get("elevation_ft"),
            "wui_class": profile.get("wui_class"),
            "danger_quadrants": profile.get("danger_quadrants", []),
            "region": city_region,
        })
    return json.dumps({
        "count": len(cities),
        "regions": sorted(set(c["region"] for c in cities)),
        "cities": cities,
    }, indent=2)


@mcp.tool()
def get_city_profile(city_key: str) -> str:
    """Get complete fire weather profile for a city.

    Returns terrain notes, danger quadrants, key features, evacuation routes,
    historical fires, WUI class, ignition sources, and more.

    Args:
        city_key: City identifier (e.g. 'paradise_ca', 'amarillo_tx').
               Use list_cities() to see all available keys.
    """
    profiles = _get_all_city_profiles()
    profile = profiles.get(city_key)
    if not profile:
        # Try fuzzy match
        matches = [k for k in profiles if city_key.lower() in k.lower()]
        if matches:
            return json.dumps({
                "error": f"City '{city_key}' not found. Did you mean: {', '.join(matches[:5])}?",
            })
        return json.dumps({"error": f"City '{city_key}' not found. Use list_cities() to see available keys."})

    # Build comprehensive response
    result = {"city_key": city_key}
    center = profile.get("center", profile.get("coords"))
    if center:
        result["lat"] = center[0]
        result["lon"] = center[1]

    # Copy all relevant fields
    for field in [
        "elevation_ft", "terrain_notes", "danger_quadrants", "safe_quadrants",
        "key_features", "terrain_features", "wui_class", "wui_exposure",
        "historical_fires", "post_fire_changes", "evacuation_routes",
        "population", "elevation_range_ft", "fire_spread_characteristics",
        "infrastructure_vulnerabilities", "demographics_risk_factors",
        "vegetation", "terrain_class", "terrain_description",
        "fire_behavior_notes",
    ]:
        val = profile.get(field)
        if val is not None:
            result[field] = val

    # Attach ignition sources if available
    ignition = _get_ignition_sources()
    if city_key in ignition:
        result["ignition_sources"] = ignition[city_key]

    _build_region_map()
    result["region"] = _REGION_MAP.get(city_key, "other")

    return json.dumps(result, indent=2, default=str)


@mcp.tool()
def search_cities(
    query: str = "", lat: float = 0, lon: float = 0, radius_km: float = 100,
) -> str:
    """Search cities by name/keyword or proximity to coordinates.

    Args:
        query: Text search in city key and terrain notes (e.g. "canyon", "evacuation").
        lat: Latitude for proximity search (use with lon).
        lon: Longitude for proximity search (use with lat).
        radius_km: Search radius in km (default 100). Only used with lat/lon.

    Returns:
        Matching cities with key, coordinates, distance (if geo search), and summary.
    """
    profiles = _get_all_city_profiles()
    _build_region_map()
    results = []

    for key, profile in profiles.items():
        center = profile.get("center", profile.get("coords"))
        if not center:
            continue

        # Text search
        if query:
            searchable = (
                key + " " +
                profile.get("terrain_notes", "") + " " +
                " ".join(profile.get("danger_quadrants", [])) + " " +
                (profile.get("wui_class") or "") + " " +
                " ".join(str(f.get("name", "")) for f in profile.get("key_features", []))
            ).lower()
            if query.lower() not in searchable:
                continue

        # Geo search
        distance_km = None
        if lat != 0 or lon != 0:
            dlat = math.radians(center[0] - lat)
            dlon = math.radians(center[1] - lon)
            a = (math.sin(dlat / 2) ** 2 +
                 math.cos(math.radians(lat)) * math.cos(math.radians(center[0])) *
                 math.sin(dlon / 2) ** 2)
            distance_km = 6371 * 2 * math.asin(math.sqrt(a))
            if distance_km > radius_km:
                continue

        entry = {
            "key": key,
            "lat": center[0], "lon": center[1],
            "elevation_ft": profile.get("elevation_ft"),
            "wui_class": profile.get("wui_class"),
            "danger_quadrants": profile.get("danger_quadrants", []),
            "region": _REGION_MAP.get(key, "other"),
        }
        if distance_km is not None:
            entry["distance_km"] = round(distance_km, 1)
        # Add a brief summary
        notes = profile.get("terrain_notes", "")
        entry["summary"] = notes[:200] + ("..." if len(notes) > 200 else "")
        results.append(entry)

    # Sort by distance if geo search, else alphabetically
    if lat != 0 or lon != 0:
        results.sort(key=lambda x: x.get("distance_km", 999999))
    else:
        results.sort(key=lambda x: x["key"])

    return json.dumps({"count": len(results), "cities": results[:50]}, indent=2)


# ============================================================================
# Map Overlay Tools
# ============================================================================

@mcp.tool()
def get_model_map(
    field: str = "t2m",
    level: str = "surface",
    model: str = "hrrr",
    cycle: str = "latest",
    fhr: int = 0,
    bounds: str = "",
    product: str = "",
) -> list:
    """Get a model map overlay as PNG — plan-view of an atmospheric field.

    Returns a colormapped PNG image showing a horizontal slice through the
    atmosphere. Ideal for seeing the spatial pattern of temperature, wind,
    reflectivity, CAPE, etc.

    Args:
        field: Field to plot. Surface: 't2m' (2m temp), 'd2m' (dew point),
               'wind_speed_10m', 'refc' (reflectivity), 'cape_sfc', 'mslp',
               'vis', 'gust', 'prate'. Isobaric: 'temperature', 'wind_speed',
               'rh', 'geopotential_height', 'vorticity', 'omega', 'theta'.
               Derived: 'rh_surface', 'wind_chill', 'heat_index'.
        level: Pressure level in hPa (e.g. '500', '850') for isobaric fields,
               or 'surface' for surface fields. Default: surface.
        model: Weather model ('hrrr', 'gfs', 'rrfs'). Default: hrrr.
        cycle: Model cycle key (e.g. '20260205_12z') or 'latest'.
        fhr: Forecast hour. Default: 0.
        bounds: Optional geographic crop 'south,west,north,east'
                (e.g. '30,-120,45,-100' for western US).
        product: Composite product preset name. When set, overrides field/level.
                 Options: 'surface_analysis', 'radar_composite', 'severe_weather',
                 'upper_500', 'upper_250', 'moisture', 'fire_weather', 'precip'.
                 Use list_map_products() to see all available presets.

    Returns:
        PNG image of the map overlay.
    """
    from mcp import types

    params = {
        "model": model,
        "cycle": cycle,
        "fhr": str(fhr),
        "format": "png",
    }
    if product:
        params["product"] = product
    else:
        params["field"] = field
        if level and level != "surface":
            params["level"] = level
    if bounds:
        params["bbox"] = bounds

    png_data = _api_get("/api/v1/map-overlay", params, raw=True, api_base=API_BASE)

    if isinstance(png_data, dict) and "error" in png_data:
        return json.dumps(png_data)

    b64 = base64.b64encode(png_data).decode()
    return [types.ImageContent(type="image", data=b64, mimeType="image/png")]


@mcp.tool()
def list_map_products() -> str:
    """List available composite map product presets.

    Returns metadata for each preset including name, description, fill field,
    and whether it needs surface data.
    """
    result = _api_get("/api/v1/map-overlay/products", api_base=API_BASE)
    return json.dumps(result, indent=2)


@mcp.tool()
def list_map_fields(model: str = "hrrr") -> str:
    """List available map overlay fields and their metadata.

    Args:
        model: Weather model ('hrrr', 'gfs', 'rrfs'). Default: hrrr.

    Returns:
        JSON list of fields with id, name, units, category, and value ranges.
    """
    result = _api_get("/api/v1/map-overlay/fields", {"model": model}, api_base=API_BASE)
    return json.dumps(result, indent=2)


# ============================================================================
# Oregon WFO Agent Swarm Tools (10 tools)
# ============================================================================

@mcp.tool()
def list_oregon_zones() -> str:
    """List all 7 Oregon WFO coverage zones with status.

    Returns:
        JSON list of zones with zone_id, name, town_count, transect_count.
    """
    from tools.agent_tools.data.oregon_zones import list_zones
    from tools.agent_tools.wfo_swarm.scheduler import output_store

    zones = list_zones()
    for z in zones:
        status = output_store.get_status(z["zone_id"])
        z["status"] = status.get("status", "not_run") if status else "not_run"
        z["last_cycle"] = status.get("cycle", "") if status else ""
    return json.dumps(zones, indent=2)


@mcp.tool()
def get_zone_config(zone_id: str) -> str:
    """Get full configuration for an Oregon zone.

    Args:
        zone_id: Zone identifier (e.g. 'OR-CENTCAS', 'OR-GORGE').

    Returns:
        JSON with zone name, towns, stations, transect IDs, bounds.
    """
    from tools.agent_tools.data.oregon_zones import get_zone
    z = get_zone(zone_id)
    return json.dumps({
        "zone_id": z.zone_id,
        "name": z.name,
        "description": z.description,
        "towns": {t: list(c) for t, c in z.towns.items()},
        "wfos": z.wfos,
        "metar_stations": z.metar_stations,
        "transect_ids": z.transect_ids,
        "priority_transects": z.priority_transects,
        "bounds": z.bounds,
        "town_count": z.town_count,
        "transect_count": z.transect_count,
    }, indent=2)


@mcp.tool()
def get_zone_transects(zone_id: str) -> str:
    """Get all cross-section transect presets for a zone with coordinates.

    Args:
        zone_id: Zone identifier (e.g. 'OR-CENTCAS').

    Returns:
        JSON dict of transect_id -> {start, end, label, description, length_km}.
    """
    from tools.agent_tools.data.oregon_transects import get_zone_transects
    transects = get_zone_transects(zone_id)
    return json.dumps(transects, indent=2)


@mcp.tool()
def get_zone_bulletin(zone_id: str) -> str:
    """Get the latest fire weather forecast bulletin for a zone.

    Args:
        zone_id: Zone identifier (e.g. 'OR-CENTCAS').

    Returns:
        JSON bulletin with headline, risk_summary, town_forecasts, discussion.
    """
    from tools.agent_tools.wfo_swarm.scheduler import get_zone_bulletin as _get
    bulletin = _get(zone_id)
    if bulletin is None:
        return json.dumps({"error": f"No bulletin available for {zone_id}. Run the swarm first."})
    return json.dumps(bulletin, indent=2, default=str)


@mcp.tool()
def get_zone_town_forecast(zone_id: str, town: str) -> str:
    """Get a specific town's fire weather forecast from the latest bulletin.

    Args:
        zone_id: Zone identifier (e.g. 'OR-CENTCAS').
        town: Town name (e.g. 'Bend', 'Sisters'). Case-insensitive.

    Returns:
        JSON forecast with headline, text, risk_level, data_sources.
    """
    from tools.agent_tools.wfo_swarm.scheduler import get_zone_town_forecast as _get
    forecast = _get(zone_id, town)
    if forecast is None:
        return json.dumps({"error": f"No forecast for '{town}' in {zone_id}."})
    return json.dumps(forecast, indent=2, default=str)


@mcp.tool()
def get_zone_risk_ranking(zone_id: str) -> str:
    """Get all towns ranked by fire risk for a zone.

    Args:
        zone_id: Zone identifier (e.g. 'OR-CENTCAS').

    Returns:
        JSON list of {town, score, level, factors} sorted by risk.
    """
    from tools.agent_tools.wfo_swarm.scheduler import get_zone_risk_ranking as _get
    ranking = _get(zone_id)
    if ranking is None:
        return json.dumps({"error": f"No ranking available for {zone_id}."})
    return json.dumps(ranking, indent=2, default=str)


@mcp.tool()
def get_zone_discussion(zone_id: str) -> str:
    """Get the AFD-style zone meteorological discussion.

    Args:
        zone_id: Zone identifier (e.g. 'OR-CENTCAS').

    Returns:
        Plain text discussion (AFD format).
    """
    from tools.agent_tools.wfo_swarm.scheduler import get_zone_discussion as _get
    discussion = _get(zone_id)
    if discussion is None:
        return json.dumps({"error": f"No discussion available for {zone_id}."})
    return discussion


@mcp.tool()
def oregon_fire_scan() -> str:
    """Quick fire weather scan across all 7 Oregon zones.

    Returns highest risk level and top concern per zone.

    Returns:
        JSON dict of zone_id -> {headline, max_risk_level, top_concern}.
    """
    from tools.agent_tools.wfo_swarm.scheduler import oregon_fire_scan as _scan
    return json.dumps(_scan(), indent=2, default=str)


@mcp.tool()
def oregon_state_bulletin() -> str:
    """State-level aggregated fire weather bulletin for all Oregon zones.

    Returns:
        JSON with statewide max risk, per-zone summaries, top 20 towns.
    """
    from tools.agent_tools.wfo_swarm.scheduler import oregon_state_bulletin as _bulletin
    return json.dumps(_bulletin(), indent=2, default=str)


@mcp.tool()
def get_swarm_status() -> str:
    """Get the pipeline status for all Oregon zone swarms.

    Returns:
        JSON with per-zone status (running/complete/failed), last_cycle.
    """
    from tools.agent_tools.wfo_swarm.scheduler import get_swarm_status as _status
    return json.dumps(_status(), indent=2, default=str)


# ============================================================================
# Auth + Rate Limiting Middleware (Starlette)
# ============================================================================

def _create_app(mcp_instance, port: int):
    """Build the Starlette ASGI app with auth and rate-limit middleware.

    Uses pure ASGI middleware (not BaseHTTPMiddleware) to avoid breaking
    SSE streaming responses. BaseHTTPMiddleware buffers the full response
    body which is incompatible with long-lived SSE connections.
    """
    from starlette.applications import Starlette
    from starlette.responses import JSONResponse
    from starlette.routing import Mount, Route
    from urllib.parse import parse_qs

    # Shared state
    api_keys = {"_data": _load_keys(), "_mtime": 0}
    request_windows: dict[str, list[float]] = defaultdict(list)

    def _refresh_keys():
        """Reload keys from disk (at most once per second)."""
        now = time.time()
        if now - api_keys["_mtime"] > 1:
            try:
                api_keys["_data"] = _load_keys()
            except Exception:
                pass
            api_keys["_mtime"] = now

    async def _send_json_error(send, status: int, body: dict, extra_headers=None):
        """Send a JSON error response via raw ASGI."""
        payload = json.dumps(body).encode()
        headers = [
            (b"content-type", b"application/json"),
            (b"content-length", str(len(payload)).encode()),
        ]
        if extra_headers:
            headers.extend(extra_headers)
        await send({"type": "http.response.start", "status": status, "headers": headers})
        await send({"type": "http.response.body", "body": payload})

    class AuthAndRateLimitMiddleware:
        """Pure ASGI middleware — auth + rate limiting in one pass.

        Doesn't buffer responses, so SSE streams work correctly.
        """
        def __init__(self, app):
            self.app = app

        async def __call__(self, scope, receive, send):
            if scope["type"] != "http":
                return await self.app(scope, receive, send)

            path = scope.get("path", "")

            # Health endpoint is unauthenticated
            if path == "/health":
                return await self.app(scope, receive, send)

            # --- Auth ---
            # Extract API key from Authorization header
            api_key = None
            for header_name, header_val in scope.get("headers", []):
                if header_name == b"authorization":
                    decoded = header_val.decode("latin-1")
                    if decoded.startswith("Bearer "):
                        api_key = decoded[7:]
                    break

            # Fall back to ?api_key= query param
            if not api_key:
                qs = scope.get("query_string", b"").decode("latin-1")
                params = parse_qs(qs)
                api_key_list = params.get("api_key", [])
                if api_key_list:
                    api_key = api_key_list[0]

            if not api_key:
                return await _send_json_error(send, 401, {
                    "error": "Missing API key. Use Authorization: Bearer wxs_... or ?api_key=wxs_..."
                })

            key_hash = hashlib.sha256(api_key.encode()).hexdigest()
            _refresh_keys()
            key_meta = api_keys["_data"].get(key_hash)

            if not key_meta:
                return await _send_json_error(send, 403, {"error": "Invalid API key"})

            # --- Rate Limiting (skip for /sse — only limit /messages) ---
            if path != "/sse":
                rpm = key_meta.get("rate_limit", 20)
                burst = 30 if rpm >= 300 else (10 if rpm >= 60 else 3)

                now = time.time()
                window = request_windows[key_hash]
                window[:] = [t for t in window if now - t < 60]

                if len(window) >= rpm:
                    retry_after = int(60 - (now - window[0])) + 1
                    return await _send_json_error(send, 429, {
                        "error": "Rate limit exceeded", "retry_after": retry_after,
                    }, extra_headers=[(b"retry-after", str(retry_after).encode())])

                recent = sum(1 for t in window if now - t < 1)
                if recent >= burst:
                    return await _send_json_error(send, 429, {
                        "error": "Burst limit exceeded", "retry_after": 1,
                    }, extra_headers=[(b"retry-after", b"1")])

                window.append(now)

            return await self.app(scope, receive, send)

    async def health_endpoint(request):
        return JSONResponse({
            "status": "ok",
            "server": "wxsection-public-mcp",
            "tools": 40,
            "cities": len(_get_all_city_profiles()),
            "timestamp": datetime.utcnow().isoformat() + "Z",
        })

    # Build app: mount MCP SSE app under /, add health route
    sse_app = mcp_instance.sse_app()

    app = Starlette(
        routes=[
            Route("/health", health_endpoint),
            Mount("/", app=sse_app),
        ],
    )

    # Wrap with pure ASGI middleware
    return AuthAndRateLimitMiddleware(app)



# ============================================================================
# CLI Entry Point
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description="wxsection.com Public MCP Server")
    parser.add_argument("--port", type=int, default=5566, help="Server port (default: 5566)")
    parser.add_argument("--generate-key", metavar="USERNAME", help="Generate a new API key")
    parser.add_argument("--rate-limit", type=int, default=20, help="RPM limit for generated key (default: 20)")
    parser.add_argument("--list-keys", action="store_true", help="List registered API keys")
    parser.add_argument("--revoke-key", metavar="API_KEY", help="Revoke an API key")
    args = parser.parse_args()

    # Key management commands (no server needed)
    if args.generate_key:
        key = generate_key(args.generate_key, args.rate_limit)
        print(f"Generated API key for '{args.generate_key}':")
        print(f"  {key}")
        print(f"  Rate limit: {args.rate_limit} RPM")
        print()
        print("This key is shown ONCE. Store it securely.")
        print(f"Users connect with:")
        print(f'  "url": "https://mcp.wxsection.com/sse?api_key={key}"')
        return

    if args.list_keys:
        keys = list_keys()
        if not keys:
            print("No API keys registered.")
            return
        print(f"{'Name':<20} {'Created':<12} {'RPM':<6} {'Hash Prefix'}")
        print("-" * 60)
        for k in keys:
            print(f"{k['name']:<20} {k['created']:<12} {k['rate_limit']:<6} {k['hash_prefix']}")
        return

    if args.revoke_key:
        if revoke_key(args.revoke_key):
            print(f"Key revoked successfully.")
        else:
            print(f"Key not found.")
        return

    # Start SSE server
    import uvicorn

    # Load .env if present
    env_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    if os.path.exists(env_file):
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())

    # Update API_BASE from env
    global API_BASE
    API_BASE = os.environ.get("WXSECTION_API_BASE", "http://127.0.0.1:5565")

    app = _create_app(mcp, args.port)

    print(f"wxsection.com Public MCP Server")
    print(f"  Port:      {args.port}")
    print(f"  API Base:  {API_BASE}")
    print(f"  Tools:     40 (37 private + 3 city browsing)")
    print(f"  Health:    http://localhost:{args.port}/health")
    print(f"  SSE:       http://localhost:{args.port}/sse")
    print()

    uvicorn.run(app, host="0.0.0.0", port=args.port, log_level="info")


if __name__ == "__main__":
    main()
