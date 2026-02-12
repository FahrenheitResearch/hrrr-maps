#!/usr/bin/env python3
"""
MCP Server for wxsection.com — AI-agent-native atmospheric research platform.

Exposes 36 tools via stdin/stdout JSON-RPC (Model Context Protocol):

Cross-Section Tools:
  - get_capabilities: Discover models, products, parameter constraints
  - list_events: Browse 88 historical weather events by category
  - get_event: Get event details + suggested cross-sections + available FHRs
  - list_cycles: List available model cycles with forecast hours
  - list_products: List visualization styles with descriptions and units
  - generate_cross_section: Generate a PNG cross-section (returns base64 image)
  - get_atmospheric_data: Get numerical data along a cross-section path (JSON)
  - generate_cross_section_gif: Generate animated GIF cross-section over forecast hours
  - get_status: Server health, loaded cycles, memory usage

External Data Tools:
  - get_metar: Surface weather observations from ASOS/AWOS stations
  - find_stations: Find weather stations near a point
  - get_raws: RAWS fire weather station observations
  - get_spc_fire_outlook: SPC fire weather outlook polygons
  - get_spc_discussion: SPC fire weather discussion text
  - get_nws_alerts: Active NWS weather alerts
  - get_forecast_discussion: NWS Area Forecast Discussion text
  - get_elevation: Elevation at a point or along a path
  - get_drought: US Drought Monitor status

Fire Weather Tools:
  - assess_fire_risk: Assess fire weather risk along a cross-section transect
  - national_fire_scan: Quick national scan of fire risk across CONUS regions
  - compute_fire_indices: Calculate fire weather indices from atmospheric data

Investigation Tools (investigate, don't score):
  - investigate_location: Comprehensive fire weather investigation for a lat/lon
  - investigate_town: Investigate fire weather for a named town
  - compare_model_obs: Compare model forecast with actual surface observations
  - get_point_forecast: Get model surface conditions at a specific point
  - batch_investigate: Investigate multiple locations at once

Forecast Tools:
  - generate_forecast: Generate a complete weather forecast with cross-sections
  - quick_bulletin: Generate a short fire weather bulletin

Terrain & Fuel Tools:
  - analyze_terrain: Terrain complexity (canyons, valleys, slopes)
  - city_terrain: City quadrant terrain assessment with fire difficulty
  - assess_fuels: Fuel condition assessment (seasonal, drought, weather history)
  - get_ignition_sources: Ignition risk corridors (trucking, power lines, railroads)
  - detect_wind_shifts: Cold front / wind shift detection in HRRR forecast
  - classify_overnight: Overnight condition classification (recovery vs shift vs no recovery)
  - verify_winds: Wind observation verification across all station types
  - get_fire_climatology: Historical fire weather context for a station

Usage:
    python tools/mcp_server.py [--api-base http://127.0.0.1:5565]

Configure in Claude Code's MCP settings (~/.claude/claude_code_config.json):
    {
      "mcpServers": {
        "wxsection": {
          "command": "python",
          "args": ["C:/Users/drew/hrrr-maps/tools/mcp_server.py"],
          "env": {"WXSECTION_API_BASE": "http://127.0.0.1:5565", "GOOGLE_STREET_VIEW_KEY": "from .env"}
        }
      }
    }
"""

import base64
import json
import math
import os
import sys
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from urllib.parse import urlencode, quote

from mcp.server.fastmcp import FastMCP

# Add parent dir so we can import agent_tools
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

API_BASE = os.environ.get("WXSECTION_API_BASE", "http://127.0.0.1:5565")
STREET_VIEW_KEY = os.environ.get("GOOGLE_STREET_VIEW_KEY", "")

mcp = FastMCP(
    "wxsection",
    instructions=(
        "wxsection.com AI-agent atmospheric research platform. "
        "Generate vertical cross-sections from HRRR/GFS/RRFS weather models. "
        "Browse 88 historical weather events. Get raw numerical data for research. "
        "Ingest external data: METARs, RAWS, SPC products, NWS alerts, elevation, drought. "
        "Investigate fire weather at specific locations — gather observations, alerts, "
        "drought, and model data to build a complete picture. Compare model forecasts "
        "with actual surface observations to catch critical discrepancies. "
        "Assess fire weather risk. Generate forecasts and reports."
    ),
)


# ---------------------------------------------------------------------------
# Helpers (shared implementation in mcp_helpers.py)
# ---------------------------------------------------------------------------

from tools.mcp_helpers import _api_get as _api_get_shared


def _api_get(path: str, params: dict = None, raw: bool = False) -> dict | bytes:
    """GET from the dashboard HTTP API. Returns parsed JSON or raw bytes."""
    return _api_get_shared(path, params, raw=raw, api_base=API_BASE)


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

@mcp.tool()
def get_capabilities() -> str:
    """Discover models, products, parameter constraints, coverage areas, and rate limits.

    Returns machine-readable metadata about the wxsection.com API so agents can
    understand valid parameter ranges without trial and error.
    """
    result = _api_get("/api/v1/capabilities")
    return json.dumps(result, indent=2)


@mcp.tool()
def list_events(category: str | None = None, has_data: bool | None = None) -> str:
    """Browse historical weather events (fires, hurricanes, tornadoes, derechos, etc.).

    Args:
        category: Filter by category slug (e.g. 'fire-ca', 'hurricane', 'tornado',
                  'derecho', 'hail', 'ar', 'winter', 'other'). Omit for all events.
        has_data: If true, only return events whose data is currently loaded/available
                  on the server. If false/omitted, returns all 85 events.

    Returns:
        JSON array of events with cycle_key, name, category, date, notes, and
        has_data flag indicating whether the server has that cycle's data loaded.
    """
    params = {}
    if category:
        params["category"] = category
    if has_data is not None:
        params["has_data"] = str(has_data).lower()
    result = _api_get("/api/v1/events", params)
    return json.dumps(result, indent=2)


@mcp.tool()
def get_event(cycle_key: str) -> str:
    """Get detailed information about a specific historical weather event.

    Args:
        cycle_key: The event's cycle key (e.g. '20250107_00z' for the LA fires).
                   Get these from list_events().

    Returns:
        Event metadata (name, category, date, notes, why), available forecast hours,
        suggested cross-section paths with coordinates, and available products.
    """
    result = _api_get(f"/api/v1/events/{cycle_key}")
    return json.dumps(result, indent=2)


@mcp.tool()
def list_cycles(model: str = "hrrr") -> str:
    """List available model cycles with their forecast hours.

    Args:
        model: Weather model - 'hrrr' (3km CONUS, hourly), 'gfs' (0.25deg global),
               or 'rrfs' (3km CONUS experimental). Default: hrrr.

    Returns:
        Available cycles sorted newest-first, each with cycle key, display name,
        available forecast hours, and whether data is loaded in memory.
    """
    result = _api_get("/api/v1/cycles", {"model": model})
    return json.dumps(result, indent=2)


@mcp.tool()
def list_products(model: str = "hrrr") -> str:
    """List available atmospheric visualization products/styles.

    Args:
        model: Weather model ('hrrr', 'gfs', 'rrfs'). Some products like 'smoke'
               are only available for HRRR. Default: hrrr.

    Returns:
        Array of products with id, name, and units. Use the 'id' as the 'product'
        parameter in generate_cross_section and get_atmospheric_data.
    """
    result = _api_get("/api/v1/products", {"model": model})
    return json.dumps(result, indent=2)


@mcp.tool()
def generate_cross_section(
    start_lat: float,
    start_lon: float,
    end_lat: float,
    end_lon: float,
    product: str = "temperature",
    model: str = "hrrr",
    cycle: str = "latest",
    fhr: int = 0,
    y_axis: str = "pressure",
    y_top: int = 100,
    units: str = "km",
    marker_lat: float = None,
    marker_lon: float = None,
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
        product: Atmospheric variable to visualize. Common: 'temperature',
                 'wind_speed', 'rh', 'omega', 'theta_e', 'smoke', 'fire_wx'.
                 Use list_products() for the full list.
        model: Weather model ('hrrr', 'gfs', 'rrfs'). Default: hrrr.
        cycle: Model cycle key (e.g. '20260205_12z') or 'latest'. Default: latest.
        fhr: Forecast hour (0=analysis, 6=6hr forecast, etc.). Default: 0.
        y_axis: Vertical axis type - 'pressure' (hPa), 'height' (km), or 'isentropic' (theta K). Default: pressure. Isentropic mode shows data on constant-theta surfaces with pressure contours — ideal for downslope wind and stability analysis.
        y_top: Top of plot in hPa (100=full atmosphere, 300=mid-level, 500=low,
               700=boundary layer). Default: 100.
        units: Distance axis units - 'km' or 'mi'. Default: km.
        marker_lat: Optional POI marker latitude. Draws a red X on the terrain
                    surface at this location's projection onto the cross-section path.
                    Ignored if >50km from the transect.
        marker_lon: Optional POI marker longitude (pair with marker_lat).
        marker_label: Optional label for the POI marker (e.g. 'Camp Fire', 'Denver').
                      Displayed next to the red X on the cross-section.
        markers: Optional JSON array of multiple POI markers. Each element is an object
                 with 'lat', 'lon', and optional 'label'. Example:
                 '[{"lat":39.1,"lon":-121.4,"label":"Camp Fire"},{"lat":38.8,"lon":-120.9}]'
                 When provided, marker_lat/marker_lon/marker_label are ignored.

    Returns:
        JSON with base64-encoded PNG image and metadata (model, cycle, valid_time,
        distance_km, product). Display the image to see the cross-section.
    """
    params = {
        "start_lat": start_lat,
        "start_lon": start_lon,
        "end_lat": end_lat,
        "end_lon": end_lon,
        "product": product,
        "model": model,
        "cycle": cycle,
        "fhr": fhr,
        "y_axis": y_axis,
        "y_top": y_top,
        "units": units,
    }
    if markers:
        params["markers"] = markers if isinstance(markers, str) else json.dumps(markers)
    elif marker_lat is not None and marker_lon is not None:
        params["marker_lat"] = marker_lat
        params["marker_lon"] = marker_lon
        if marker_label:
            params["marker_label"] = marker_label

    # Fetch PNG bytes
    png_bytes = _api_get("/api/v1/cross-section", params, raw=True)

    if isinstance(png_bytes, dict):
        # Error response
        return json.dumps(png_bytes, indent=2)

    # Check if response is actually an error JSON
    if png_bytes[:1] == b'{':
        try:
            return json.dumps(json.loads(png_bytes), indent=2)
        except json.JSONDecodeError:
            pass

    b64 = base64.b64encode(png_bytes).decode("ascii")

    result = {
        "image_base64": b64,
        "mime_type": "image/png",
        "size_bytes": len(png_bytes),
        "metadata": {
            "model": model,
            "cycle": cycle,
            "fhr": fhr,
            "product": product,
            "start": [start_lat, start_lon],
            "end": [end_lat, end_lon],
            "y_axis": y_axis,
            "y_top": y_top,
            "units": units,
        },
    }
    return json.dumps(result)


@mcp.tool()
def get_atmospheric_data(
    start_lat: float,
    start_lon: float,
    end_lat: float,
    end_lon: float,
    product: str = "temperature",
    model: str = "hrrr",
    cycle: str = "latest",
    fhr: int = 0,
    y_axis: str = "pressure",
    y_top: int = 100,
    units: str = "km",
) -> str:
    """Get raw numerical atmospheric data along a cross-section path as JSON arrays.

    This is the research powerhouse — returns the actual interpolated values that
    make up a cross-section, not just an image. Use this when you need to analyze
    specific values, compute statistics, find extremes, or compare fields.

    Args:
        start_lat: Starting latitude (-90 to 90).
        start_lon: Starting longitude (-180 to 180). Use negative for west.
        end_lat: Ending latitude.
        end_lon: Ending longitude.
        product: Atmospheric variable. Common: 'temperature', 'wind_speed', 'rh',
                 'omega', 'theta_e'. Use list_products() for all options.
        model: Weather model ('hrrr', 'gfs', 'rrfs'). Default: hrrr.
        cycle: Model cycle key or 'latest'. Default: latest.
        fhr: Forecast hour. Default: 0.
        y_axis: Vertical axis - 'pressure', 'height', or 'isentropic'. Default: pressure.
        y_top: Top of plot in hPa (100/200/300/500/700). Default: 100.
        units: Distance units - 'km' or 'mi'. Default: km.

    Returns:
        JSON with:
        - distances_km: 1D array of distances along the path
        - pressure_levels_hpa: 1D array of pressure levels
        - lats, lons: 1D arrays of coordinates along the path
        - Data fields as 2D arrays [n_levels x n_points] (e.g. temperature_c,
          wind_speed_kts, rh_pct depending on the product)
        - metadata: model, cycle, fhr, valid_time, total distance

        Typical size: ~40 levels x ~200 points = 8,000 values per field (~64KB JSON).
    """
    params = {
        "start_lat": start_lat,
        "start_lon": start_lon,
        "end_lat": end_lat,
        "end_lon": end_lon,
        "product": product,
        "model": model,
        "cycle": cycle,
        "fhr": fhr,
        "y_axis": y_axis,
        "y_top": y_top,
        "units": units,
    }
    result = _api_get("/api/v1/data", params)
    return json.dumps(result)


@mcp.tool()
def get_status() -> str:
    """Get server health, loaded cycles, and memory usage.

    Returns:
        JSON with ok (bool), model name, loaded forecast hour count,
        memory usage in MB, and latest available cycle key.
    """
    result = _api_get("/api/v1/status")
    return json.dumps(result, indent=2)


# ---------------------------------------------------------------------------
# External Data Tools
# ---------------------------------------------------------------------------

from tools.mcp_helpers import _ext_fetch_json, _ext_fetch_text


@mcp.tool()
def get_metar(
    stations: str,
    hours_back: int = 3,
) -> str:
    """Get METAR surface weather observations from ASOS/AWOS stations.

    Returns temperature, dewpoint, wind, visibility, pressure, and cloud data
    from airport weather stations. Data from Iowa Environmental Mesonet.

    Args:
        stations: Comma-separated ICAO station IDs (e.g. "KDEN,KCOS,KGJT").
        hours_back: Hours of history to retrieve (1-48). Default: 3.

    Returns:
        JSON with observation data for each station including timestamp, temp_f,
        dwpf (dewpoint), sknt (wind knots), drct (wind direction), vsby (visibility),
        relh (relative humidity), alti (altimeter), skyc (sky condition).
    """
    from datetime import datetime, timedelta
    now = datetime.utcnow()
    dt_start = now - timedelta(hours=hours_back)
    dt_end = now
    url = (
        f"https://mesonet.agron.iastate.edu/json/asos.py?"
        f"station={stations}"
        f"&year1={dt_start.year}&month1={dt_start.month}&day1={dt_start.day}"
        f"&hour1={dt_start.hour}&minute1={dt_start.minute}"
        f"&year2={dt_end.year}&month2={dt_end.month}&day2={dt_end.day}"
        f"&hour2={dt_end.hour}&minute2={dt_end.minute}"
        f"&tz=UTC&format=json&latlon=yes&elev=yes&trace=0.0001"
    )
    result = _ext_fetch_json(url)
    return json.dumps(result, indent=2)


@mcp.tool()
def find_stations(
    lat: float,
    lon: float,
    radius_km: float = 100,
) -> str:
    """Find ASOS/AWOS weather stations near a geographic point.

    Args:
        lat: Latitude of search center.
        lon: Longitude of search center (negative for west).
        radius_km: Search radius in km (default 100, max 500).

    Returns:
        JSON array of stations sorted by distance, with id, name, state,
        lat, lon, elevation_m, and distance_km.
    """
    url = "https://mesonet.agron.iastate.edu/geojson/network/ASOS.geojson"
    data = _ext_fetch_json(url, timeout=30)
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
                "id": props.get("sid", ""),
                "name": props.get("sname", ""),
                "state": props.get("state", ""),
                "lat": slat, "lon": slon,
                "elevation_m": props.get("elevation"),
                "distance_km": round(dist_km, 1),
            })
    stations.sort(key=lambda s: s["distance_km"])
    return json.dumps(stations[:50], indent=2)


@mcp.tool()
def get_raws(
    lat: float,
    lon: float,
    radius_miles: float = 50,
    hours_back: int = 6,
) -> str:
    """Get RAWS fire weather station observations near a point.

    RAWS (Remote Automatic Weather Stations) provide fire-critical data
    including temperature, RH, wind, and fuel moisture. Data from Synoptic Data API.

    Args:
        lat: Latitude of search center.
        lon: Longitude of search center.
        radius_miles: Search radius in miles (default 50).
        hours_back: Hours of history (default 6).

    Returns:
        JSON with station observations including air_temp, relative_humidity,
        wind_speed, wind_direction, wind_gust, fuel_moisture.
    """
    from datetime import datetime, timedelta
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
    result = _ext_fetch_json(url, timeout=30)
    return json.dumps(result, indent=2)


@mcp.tool()
def get_spc_fire_outlook(day: int = 1) -> str:
    """Get SPC (Storm Prediction Center) Fire Weather Outlook.

    Returns the official fire weather outlook with risk polygons for
    CRITICAL, EXTREMELY CRITICAL, and ELEVATED areas.

    Args:
        day: Outlook day — 1 (today) or 2 (tomorrow). Default: 1.

    Returns:
        GeoJSON with fire weather outlook polygons and risk categories.
    """
    if day == 1:
        url = "https://www.spc.noaa.gov/products/fire_wx/fwdy1.json"
    elif day == 2:
        url = "https://www.spc.noaa.gov/products/fire_wx/fwdy2.json"
    else:
        return json.dumps({"error": f"Invalid day {day}, must be 1 or 2"})
    result = _ext_fetch_json(url)
    return json.dumps(result, indent=2)


@mcp.tool()
def get_spc_discussion() -> str:
    """Get the latest SPC Fire Weather Discussion text.

    Returns the forecaster's narrative discussion explaining the fire weather
    outlook, including reasoning for CRITICAL/ELEVATED areas, expected
    meteorological conditions, and timing.

    Returns:
        Plain text of the SPC fire weather discussion.
    """
    import re
    url = "https://www.spc.noaa.gov/products/fire_wx/fwdy1.html"
    html = _ext_fetch_text(url)
    if html.startswith("Error:"):
        return html
    m = re.search(r'<pre>(.*?)</pre>', html, re.DOTALL)
    return m.group(1).strip() if m else html[:5000]


@mcp.tool()
def get_nws_alerts(
    state: str | None = None,
    lat: float | None = None,
    lon: float | None = None,
    event_type: str | None = None,
) -> str:
    """Get active NWS weather alerts (Red Flag Warnings, Fire Weather Watches, etc.).

    Search by state or by geographic point. Filter by event type for fire-specific alerts.

    Args:
        state: Two-letter state code (e.g. "MT", "NM", "CA"). Searches state-wide.
        lat: Latitude for point-based search (use with lon).
        lon: Longitude for point-based search (use with lat).
        event_type: Filter by event type. Fire-relevant types:
                    "Red Flag Warning", "Fire Weather Watch", "Extreme Fire Behavior".

    Returns:
        GeoJSON FeatureCollection with alert features containing headline,
        description, severity, urgency, onset, expires, and affected areas.
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
    # Trim to essentials to stay under token limits
    if "features" in result:
        trimmed = []
        for f in result["features"][:20]:
            props = f.get("properties", {})
            trimmed.append({
                "event": props.get("event"),
                "headline": props.get("headline"),
                "severity": props.get("severity"),
                "urgency": props.get("urgency"),
                "onset": props.get("onset"),
                "expires": props.get("expires"),
                "areaDesc": props.get("areaDesc"),
                "description": (props.get("description") or "")[:1000],
            })
        return json.dumps({"count": len(result["features"]), "alerts": trimmed}, indent=2)
    return json.dumps(result, indent=2)


@mcp.tool()
def get_forecast_discussion(office: str) -> str:
    """Get NWS Area Forecast Discussion (AFD) from a specific weather office.

    The AFD contains the forecaster's detailed meteorological analysis and reasoning.
    Essential for understanding the local forecast context.

    Args:
        office: NWS Weather Forecast Office ID. Common fire-weather offices:
                BOU (Boulder CO), ABQ (Albuquerque NM), MSO (Missoula MT),
                GGW (Glasgow MT), BYZ (Billings MT), RIW (Riverton WY),
                AMA (Amarillo TX), LBB (Lubbock TX), LOX (Los Angeles CA),
                SGX (San Diego CA), STO (Sacramento CA), PDT (Pendleton OR).

    Returns:
        Full text of the latest Area Forecast Discussion.
    """
    url = f"https://api.weather.gov/products/types/AFD/locations/{office}"
    result = _ext_fetch_json(url, headers={"Accept": "application/json"})
    if "error" in result:
        return json.dumps(result)

    graph = result.get("@graph", [])
    if not graph:
        return json.dumps({"error": f"No AFD found for office {office}"})

    # Fetch latest product
    latest_url = graph[0].get("@id", "")
    if not latest_url:
        return json.dumps({"error": "Could not find latest AFD URL"})

    product = _ext_fetch_json(latest_url, headers={"Accept": "application/json"})
    return product.get("productText", "No text available")


@mcp.tool()
def get_elevation(
    lat: float,
    lon: float,
) -> str:
    """Get terrain elevation at a geographic point.

    Args:
        lat: Latitude.
        lon: Longitude.

    Returns:
        JSON with elevation_m and elevation_ft.
    """
    url = f"https://api.open-elevation.com/api/v1/lookup?locations={lat},{lon}"
    data = _ext_fetch_json(url, timeout=15)
    results = data.get("results", [{}])
    elev_m = results[0].get("elevation", 0) if results else 0
    return json.dumps({
        "lat": lat, "lon": lon,
        "elevation_m": elev_m,
        "elevation_ft": round(elev_m * 3.281),
    }, indent=2)


@mcp.tool()
def get_drought(state: str | None = None) -> str:
    """Get US Drought Monitor status.

    Returns current drought conditions with percentage area in each category
    (D0=Abnormally Dry through D4=Exceptional Drought).

    Args:
        state: Two-letter state code for state-level data (e.g. "MT", "CA").
               Omit for national statistics.

    Returns:
        Drought statistics with D0-D4 area percentages.
    """
    if state:
        url = f"https://usdm.unl.edu/api/area_percent/stateStatistics/{state}"
    else:
        url = "https://usdm.unl.edu/api/area_percent/nationalStatistics"
    result = _ext_fetch_json(url, timeout=15)
    return json.dumps(result, indent=2)


# ---------------------------------------------------------------------------
# Fire Weather Assessment Tools
# ---------------------------------------------------------------------------

# Standard fire-prone region transects for national scanning
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


def _compute_vpd(temp_c: float, rh_pct: float) -> float:
    """Compute vapor pressure deficit in hPa."""
    es = 6.112 * math.exp(17.67 * temp_c / (temp_c + 243.5))
    return es * (1 - rh_pct / 100.0)


def _assess_risk_from_data(rh_data: dict, wind_data: dict) -> dict:
    """Compute fire risk score from RH and wind cross-section data."""
    # Extract surface values
    def _surface_vals(data_dict):
        sp = data_dict.get("surface_pressure_hpa", [])
        pressures = data_dict.get("pressure_levels_hpa", [])
        # Find the main 2D data key
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
            # Find level closest to surface
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

    rh_vals, rh_key = _surface_vals(rh_data)
    wind_vals, wind_key = _surface_vals(wind_data)

    if not rh_vals or not wind_vals:
        return {"risk_level": "UNKNOWN", "risk_score": 0, "error": "Insufficient data"}

    rh_min = min(rh_vals)
    rh_mean = sum(rh_vals) / len(rh_vals)
    rh_below_15 = sum(1 for v in rh_vals if v < 15) / len(rh_vals) * 100
    rh_below_8 = sum(1 for v in rh_vals if v < 8) / len(rh_vals) * 100

    wind_max = max(wind_vals)
    wind_mean = sum(wind_vals) / len(wind_vals)
    wind_above_25 = sum(1 for v in wind_vals if v > 25) / len(wind_vals) * 100

    # Composite risk score (0-100)
    # RH component (40%): scaled by deficit below 30%
    rh_score = min(40, max(0, (30 - rh_mean) / 30 * 40))
    # Wind component (30%): scaled by excess above 15kt
    wind_score = min(30, max(0, (wind_mean - 15) / 25 * 30))
    # Extreme RH bonus (20%): pct below 15%
    extreme_rh_score = min(20, rh_below_15 / 100 * 20)
    # Extreme wind bonus (10%): pct above 25kt
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
        "risk_level": level,
        "risk_score": round(total, 1),
        "factors": factors,
        "stats": {
            "rh_min_pct": round(rh_min, 1),
            "rh_mean_pct": round(rh_mean, 1),
            "rh_pct_below_15": round(rh_below_15, 1),
            "wind_max_kt": round(wind_max, 1),
            "wind_mean_kt": round(wind_mean, 1),
            "wind_pct_above_25": round(wind_above_25, 1),
        },
    }


@mcp.tool()
def assess_fire_risk(
    start_lat: float,
    start_lon: float,
    end_lat: float,
    end_lon: float,
    cycle: str = "latest",
    fhr: int = 0,
    model: str = "hrrr",
) -> str:
    """Assess fire weather risk along a cross-section transect.

    Pulls RH and wind data from the dashboard, computes surface statistics,
    and returns a composite fire risk score (0-100) with risk level.

    Risk levels:
    - CRITICAL (70-100): Red Flag conditions, extreme fire danger
    - ELEVATED (50-69): Significant fire weather potential
    - MODERATE (30-49): Elevated but manageable conditions
    - LOW (0-29): Minimal fire weather concern

    Args:
        start_lat: Starting latitude.
        start_lon: Starting longitude.
        end_lat: Ending latitude.
        end_lon: Ending longitude.
        cycle: Model cycle key or 'latest'.
        fhr: Forecast hour (0-48 for HRRR).
        model: Weather model ('hrrr', 'gfs', 'rrfs').

    Returns:
        JSON with risk_level, risk_score, contributing factors, and surface statistics
        for RH and wind speed along the transect.
    """
    base_params = {
        "start_lat": start_lat, "start_lon": start_lon,
        "end_lat": end_lat, "end_lon": end_lon,
        "model": model, "cycle": cycle, "fhr": fhr,
    }

    # Fetch RH and wind data
    rh_data = _api_get("/api/v1/data", {**base_params, "product": "rh"})
    wind_data = _api_get("/api/v1/data", {**base_params, "product": "wind_speed"})

    if isinstance(rh_data, dict) and "error" in rh_data:
        return json.dumps(rh_data)
    if isinstance(wind_data, dict) and "error" in wind_data:
        return json.dumps(wind_data)

    assessment = _assess_risk_from_data(rh_data, wind_data)
    assessment["transect"] = {
        "start": [start_lat, start_lon],
        "end": [end_lat, end_lon],
    }
    assessment["model"] = model
    assessment["cycle"] = cycle
    assessment["fhr"] = fhr
    return json.dumps(assessment, indent=2)


@mcp.tool()
def national_fire_scan(
    cycle: str = "latest",
    fhr: int = 12,
    model: str = "hrrr",
) -> str:
    """Quick national scan of fire risk across 12 CONUS fire-prone regions.

    Assesses fire risk for: Northern Rockies, High Plains North/South,
    Southwest AZ, Southern California, Pacific NW, Sierra Nevada, Front Range,
    Great Basin, Texas Panhandle, Oklahoma, Central CA.

    Args:
        cycle: Model cycle key or 'latest'. Default: latest.
        fhr: Forecast hour to assess. Default: 12 (afternoon peak).
        model: Weather model. Default: hrrr.

    Returns:
        JSON with risk assessment for each region, sorted by risk score (highest first).
        Includes risk_level, risk_score, key factors, and transect coordinates.
    """
    results = {}
    for name, region in FIRE_REGIONS.items():
        base_params = {
            "start_lat": region["start"][0], "start_lon": region["start"][1],
            "end_lat": region["end"][0], "end_lon": region["end"][1],
            "model": model, "cycle": cycle, "fhr": fhr,
        }
        rh_data = _api_get("/api/v1/data", {**base_params, "product": "rh"})
        wind_data = _api_get("/api/v1/data", {**base_params, "product": "wind_speed"})

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

    # Sort by risk score
    sorted_results = dict(sorted(results.items(),
                                  key=lambda x: x[1].get("risk_score", 0),
                                  reverse=True))
    return json.dumps({
        "model": model, "cycle": cycle, "fhr": fhr,
        "regions": sorted_results,
        "summary": {
            "critical": [k for k, v in sorted_results.items() if v.get("risk_level") == "CRITICAL"],
            "elevated": [k for k, v in sorted_results.items() if v.get("risk_level") == "ELEVATED"],
        },
    }, indent=2)


SUB_METRO_KEYS = [
    "denver_metro", "colorado_springs", "la_metro",
    "phoenix_metro", "albuquerque_metro", "reno_tahoe",
    "oklahoma_metro",
]


@mcp.tool()
def sub_metro_fire_scan(
    metro: str,
    cycle: str = "latest",
    fhr: int = 12,
    model: str = "hrrr",
) -> str:
    """Scan sub-areas within a metro for granular WUI fire risk.

    Breaks a metro into specific WUI corridors, foothills communities,
    and fire-prone sub-areas (~10-30km transects) to differentiate risk
    within the metro.

    Available metros: denver_metro, colorado_springs, la_metro,
    phoenix_metro, albuquerque_metro, reno_tahoe, oklahoma_metro.

    Args:
        metro: Metro area key (e.g., 'denver_metro').
        cycle: Model cycle key or 'latest'.
        fhr: Forecast hour to assess. Default: 12.
        model: Weather model. Default: hrrr.

    Returns:
        JSON with per-sub-area risk assessments sorted by risk score.
        Each sub-area includes risk_level, risk_score, contributing_factors,
        and WUI notes.
    """
    from tools.agent_tools.fire_risk import SUB_METRO_AREAS

    metro_def = SUB_METRO_AREAS.get(metro)
    if not metro_def:
        return json.dumps({
            "error": f"Unknown metro '{metro}'. Available: {', '.join(SUB_METRO_KEYS)}",
        })

    results = {"metro": metro_def["label"], "sub_areas": {}}

    for area in metro_def["sub_areas"]:
        base_params = {
            "start_lat": area["start"][0], "start_lon": area["start"][1],
            "end_lat": area["end"][0], "end_lon": area["end"][1],
            "model": model, "cycle": cycle, "fhr": fhr,
        }
        rh_data = _api_get("/api/v1/data", {**base_params, "product": "rh"})
        wind_data = _api_get("/api/v1/data", {**base_params, "product": "wind_speed"})

        if isinstance(rh_data, dict) and "error" in rh_data:
            results["sub_areas"][area["key"]] = {
                "label": area["label"], "risk_level": "ERROR",
            }
            continue
        if isinstance(wind_data, dict) and "error" in wind_data:
            results["sub_areas"][area["key"]] = {
                "label": area["label"], "risk_level": "ERROR",
            }
            continue

        assessment = _assess_risk_from_data(rh_data, wind_data)
        assessment["label"] = area["label"]
        assessment["notes"] = area.get("notes", "")
        assessment["transect"] = {"start": area["start"], "end": area["end"]}
        results["sub_areas"][area["key"]] = assessment

    # Sort by risk score
    results["sub_areas"] = dict(sorted(
        results["sub_areas"].items(),
        key=lambda x: x[1].get("risk_score", 0),
        reverse=True,
    ))

    return json.dumps(results, indent=2)


@mcp.tool()
def compute_fire_indices(
    temp_c: float,
    rh_pct: float,
    wind_kt: float,
    temp_700_c: float | None = None,
    dewpoint_850_c: float | None = None,
) -> str:
    """Compute fire weather indices from atmospheric values.

    Calculates VPD, Fosberg Fire Weather Index, and optionally Haines Index
    from surface and upper-air values.

    Args:
        temp_c: Surface temperature in Celsius.
        rh_pct: Surface relative humidity (%).
        wind_kt: Surface wind speed in knots.
        temp_700_c: Temperature at 700 hPa in Celsius (for Haines Index).
        dewpoint_850_c: Dewpoint at 850 hPa in Celsius (for Haines Index).

    Returns:
        JSON with VPD (hPa), Fosberg FWI, and Haines Index (if upper-air data provided).
    """
    # VPD
    vpd = _compute_vpd(temp_c, rh_pct)

    # Fosberg Fire Weather Index (simplified)
    # FFWI = sqrt(1 + wind_mph^2) * (rh_factor) / 0.3002
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

    # Haines Index (if upper-air data provided)
    if temp_700_c is not None and dewpoint_850_c is not None:
        temp_850_c = temp_c - 15  # rough estimate if not provided
        # Stability component (A): T850 - T700
        stability = temp_850_c - temp_700_c
        if stability < 4:
            a = 1
        elif stability < 8:
            a = 2
        else:
            a = 3
        # Moisture component (B): T850 - Td850
        moisture_diff = temp_850_c - dewpoint_850_c
        if moisture_diff < 6:
            b = 1
        elif moisture_diff < 10:
            b = 2
        else:
            b = 3
        haines = a + b
        result["haines_index"] = haines
        result["haines_assessment"] = "HIGH" if haines >= 5 else "MODERATE" if haines >= 4 else "LOW"

    return json.dumps(result, indent=2)


# ---------------------------------------------------------------------------
# Ground Truth / Street View Tools
# ---------------------------------------------------------------------------

@mcp.tool()
def get_street_view(
    lat: float,
    lon: float,
    heading: int = 0,
    pitch: int = 0,
    fov: int = 90,
) -> str:
    """Get a Google Street View image at a location for ground-truth assessment.

    Useful for assessing vegetation density, fuel conditions, terrain features,
    urban-wildland interface exposure, and wildfire risk at specific locations.

    Args:
        lat: Latitude of the location.
        lon: Longitude of the location.
        heading: Camera heading (0=north, 90=east, 180=south, 270=west). Default: 0.
        pitch: Camera pitch (-90=down, 0=level, 90=up). Default: 0.
        fov: Field of view in degrees (10-120). Default: 90.

    Returns:
        JSON with base64-encoded JPEG image, or error if no coverage at location.
        Requires GOOGLE_STREET_VIEW_KEY environment variable.
    """
    if not STREET_VIEW_KEY:
        return json.dumps({"error": "GOOGLE_STREET_VIEW_KEY not set. Add it to .env or environment."})

    params = {
        "location": f"{lat},{lon}",
        "size": "640x480",
        "heading": heading,
        "pitch": pitch,
        "fov": fov,
        "key": STREET_VIEW_KEY,
        "return_error_code": "true",
    }
    url = "https://maps.googleapis.com/maps/api/streetview?" + urlencode(params)

    try:
        req = Request(url)
        with urlopen(req, timeout=30) as resp:
            img_data = resp.read()
            content_type = resp.headers.get("Content-Type", "")

            if "image" not in content_type:
                return json.dumps({"error": "No Street View coverage at this location"})

            b64 = base64.b64encode(img_data).decode("ascii")
            return json.dumps({
                "image_base64": b64,
                "mime_type": "image/jpeg",
                "size_bytes": len(img_data),
                "lat": lat,
                "lon": lon,
                "heading": heading,
                "pitch": pitch,
                "fov": fov,
            })
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def get_street_view_panorama(
    lat: float,
    lon: float,
    n_views: int = 4,
) -> str:
    """Get a panoramic set of Street View images (multiple headings) at a location.

    Takes N images at evenly-spaced headings to get a 360-degree view.
    Useful for comprehensive vegetation/fuel assessment around a point.

    Args:
        lat: Latitude of the location.
        lon: Longitude of the location.
        n_views: Number of views (4=90deg steps, 8=45deg steps). Default: 4.

    Returns:
        JSON array of base64-encoded images with heading/direction metadata.
    """
    if not STREET_VIEW_KEY:
        return json.dumps({"error": "GOOGLE_STREET_VIEW_KEY not set"})

    direction_names = {0: "N", 45: "NE", 90: "E", 135: "SE",
                       180: "S", 225: "SW", 270: "W", 315: "NW"}
    headings = [int(i * 360 / n_views) for i in range(n_views)]
    results = []

    for h in headings:
        params = {
            "location": f"{lat},{lon}",
            "size": "640x480",
            "heading": h,
            "pitch": 0,
            "fov": 90,
            "key": STREET_VIEW_KEY,
            "return_error_code": "true",
        }
        url = "https://maps.googleapis.com/maps/api/streetview?" + urlencode(params)
        try:
            req = Request(url)
            with urlopen(req, timeout=30) as resp:
                img_data = resp.read()
                if "image" in resp.headers.get("Content-Type", ""):
                    results.append({
                        "image_base64": base64.b64encode(img_data).decode("ascii"),
                        "mime_type": "image/jpeg",
                        "size_bytes": len(img_data),
                        "heading": h,
                        "direction": direction_names.get(h, f"{h}deg"),
                    })
        except Exception:
            pass

    return json.dumps({
        "lat": lat, "lon": lon,
        "n_views": len(results),
        "images": results,
    })


# ---------------------------------------------------------------------------
# Investigation Tools — "investigate, don't score"
# ---------------------------------------------------------------------------

@mcp.tool()
def investigate_location(
    lat: float,
    lon: float,
    name: str | None = None,
) -> str:
    """Comprehensive fire weather investigation for a specific location.

    Gathers current METAR observations, NWS alerts, SPC fire outlook,
    elevation, and drought status. Returns a complete profile with
    investigation notes and recommended next steps.

    Use this as the FIRST tool when investigating fire risk at a location.
    Follow up with recommended_next_steps in the response.
    """
    from tools.agent_tools.investigation import investigate_location as _investigate
    result = _investigate(lat, lon, name=name, base_url=API_BASE)
    return json.dumps(result, indent=2, default=str)


@mcp.tool()
def investigate_town(
    town: str,
    state: str,
) -> str:
    """Investigate fire weather conditions for a named town.

    Geocodes the town and runs a full investigation including METAR obs,
    NWS alerts, SPC outlook, elevation, and drought. Supports common
    fire-prone towns in OK, TX, NM, CO, CA.
    """
    from tools.agent_tools.investigation import investigate_town as _investigate_town
    result = _investigate_town(town, state, base_url=API_BASE)
    return json.dumps(result, indent=2, default=str)


@mcp.tool()
def compare_model_obs(
    lat: float,
    lon: float,
    station_id: str | None = None,
    model: str = "hrrr",
    fhr: int = 0,
) -> str:
    """Compare model forecast with actual surface observations.

    Critical for fire weather: model cross-section data averages through
    the full atmospheric column. Surface RH can be 11% while column
    average shows 45%. This tool reveals those discrepancies.

    If station_id not given, finds the nearest METAR station automatically.
    """
    from tools.agent_tools.external_data import get_model_obs_comparison
    result = get_model_obs_comparison(
        lat, lon, station_id=station_id, model=model, fhr=fhr, base_url=API_BASE
    )
    return json.dumps(result, indent=2, default=str)


@mcp.tool()
def get_point_forecast(
    lat: float,
    lon: float,
    model: str = "hrrr",
    fhr: int = 0,
) -> str:
    """Get model surface conditions at a specific point.

    Extracts the model's lowest-level forecast for temperature, RH,
    wind speed, and dewpoint at a single location. Note: this is the
    model's surface-level prediction, not actual observations.
    Compare with get_metar for ground truth.
    """
    from tools.agent_tools.external_data import get_point_surface_conditions
    result = get_point_surface_conditions(
        lat, lon, model=model, fhr=fhr, base_url=API_BASE
    )
    return json.dumps(result, indent=2, default=str)


@mcp.tool()
def batch_investigate(
    locations_json: str,
) -> str:
    """Investigate multiple locations at once for fire weather.

    Takes a JSON array of locations: [{"lat": 35.36, "lon": -97.18, "name": "Newalla"}, ...]
    Returns investigation profiles for each location.
    Use this to scan multiple towns in a region efficiently.
    """
    from tools.agent_tools.investigation import batch_investigate as _batch
    locations = json.loads(locations_json)
    locs = [(l["lat"], l["lon"], l.get("name")) for l in locations]
    results = _batch(locs, base_url=API_BASE)
    return json.dumps(results, indent=2, default=str)


@mcp.tool()
def generate_cross_section_gif(
    start_lat: float,
    start_lon: float,
    end_lat: float,
    end_lon: float,
    product: str = "fire_wx",
    model: str = "hrrr",
    fhr_min: int = 0,
    fhr_max: int = 12,
) -> str:
    """Generate an animated GIF cross-section showing temporal evolution.

    Creates a GIF cycling through forecast hours to show how conditions
    change over time. Essential for fire weather: shows wind shifts,
    humidity changes, frontal passages.

    Returns base64-encoded GIF image with metadata.
    """
    params = {
        "start_lat": start_lat, "start_lon": start_lon,
        "end_lat": end_lat, "end_lon": end_lon,
        "product": product, "model": model,
        "fhr_min": fhr_min, "fhr_max": fhr_max,
    }
    url = f"{API_BASE}/api/v1/cross-section/gif?{urlencode(params)}"
    try:
        req = Request(url, headers={"User-Agent": "mcp-wxsection/1.0"})
        with urlopen(req, timeout=120) as resp:
            gif_data = resp.read()
            return json.dumps({
                "format": "gif",
                "size_bytes": len(gif_data),
                "image_base64": base64.b64encode(gif_data).decode(),
                "params": params,
            })
    except Exception as e:
        return json.dumps({"error": str(e)})


# ---------------------------------------------------------------------------
# Multi-Panel Comparison Tools
# ---------------------------------------------------------------------------

@mcp.tool()
def generate_comparison(
    start_lat: float,
    start_lon: float,
    end_lat: float,
    end_lon: float,
    mode: str = "model",
    product: str = "temperature",
    model: str = "hrrr",
    cycle: str = "latest",
    fhr: int = 0,
    models: str = "",
    fhrs: str = "",
    products: str = "",
    cycles: str = "",
    cycle_match: str = "same_fhr",
    y_axis: str = "pressure",
    y_top: int = 300,
    units: str = "km",
) -> str:
    """Generate a multi-panel comparison cross-section image.

    Creates a single image with 2-4 cross-section panels for direct comparison.
    Panels share axes and colorbar for easy visual comparison.

    Modes:
    - model: Compare different models (e.g. HRRR vs GFS). Set models="hrrr,gfs".
    - temporal: Compare forecast hours. Set fhrs="0,6,12".
    - product: Compare products side-by-side. Set products="wind_speed,rh".
    - cycle: Compare init cycles. Set cycles="20260209_06z,20260209_00z".

    Args:
        start_lat/lon: Starting point of cross-section.
        end_lat/lon: Ending point of cross-section.
        mode: Comparison type - 'model', 'temporal', 'product', or 'cycle'.
        product: Product for modes that use a single product.
        model: Model for modes that use a single model.
        cycle: Cycle key or 'latest'.
        fhr: Forecast hour for modes that use a single FHR.
        models: Comma-separated models for mode=model (e.g. "hrrr,gfs").
        fhrs: Comma-separated FHRs for mode=temporal (e.g. "0,6,12").
        products: Comma-separated products for mode=product.
        cycles: Comma-separated cycles for mode=cycle.
        cycle_match: For mode=cycle: 'same_fhr' or 'valid_time'.
        y_axis: 'pressure', 'height', or 'isentropic'.
        y_top: Top of plot in hPa.
        units: 'km' or 'mi'.

    Returns:
        JSON with base64-encoded PNG image and metadata.
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

    png_bytes = _api_get("/api/v1/comparison", params, raw=True)

    if isinstance(png_bytes, dict):
        return json.dumps(png_bytes, indent=2)
    if png_bytes[:1] == b'{':
        try:
            return json.dumps(json.loads(png_bytes), indent=2)
        except json.JSONDecodeError:
            pass

    b64 = base64.b64encode(png_bytes).decode("ascii")
    return json.dumps({
        "image_base64": b64,
        "mime_type": "image/png",
        "size_bytes": len(png_bytes),
        "metadata": {
            "mode": mode, "model": model, "cycle": cycle, "fhr": fhr,
            "product": product, "models": models, "fhrs": fhrs,
            "products": products, "cycles": cycles,
            "start": [start_lat, start_lon], "end": [end_lat, end_lon],
        },
    })


@mcp.tool()
def generate_comparison_gif(
    start_lat: float,
    start_lon: float,
    end_lat: float,
    end_lon: float,
    mode: str = "model",
    product: str = "fire_wx",
    model: str = "hrrr",
    models: str = "",
    products: str = "",
    fhr_min: int = 0,
    fhr_max: int = 12,
) -> str:
    """Generate an animated GIF of multi-panel comparison across forecast hours.

    Creates an animation where each frame is a multi-panel comparison image,
    cycling through forecast hours. Works with mode=model (compare models
    as they evolve) or mode=product (compare products as they evolve).

    Returns base64-encoded GIF with metadata.
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
        req = Request(url, headers={"User-Agent": "mcp-wxsection/1.0"})
        with urlopen(req, timeout=180) as resp:
            gif_data = resp.read()
            return json.dumps({
                "format": "gif",
                "size_bytes": len(gif_data),
                "image_base64": base64.b64encode(gif_data).decode(),
                "params": params,
            })
    except Exception as e:
        return json.dumps({"error": str(e)})


# ---------------------------------------------------------------------------
# Terrain Analysis Tools
# ---------------------------------------------------------------------------

@mcp.tool()
def analyze_terrain(lat, lon, radius_km=15):
    """Analyze terrain complexity around a point — identifies canyons, valleys,
    slopes, and flat areas. Critical for fire behavior: canyon terrain creates
    channeled winds and extreme fire behavior that flat grassland analysis misses."""
    from tools.agent_tools.terrain import analyze_terrain_complexity
    return json.dumps(analyze_terrain_complexity(lat, lon, radius_km), indent=2, default=str)

@mcp.tool()
def city_terrain(lat, lon, city_name, radius_km=20):
    """Assess terrain around a city by quadrant (N/E/S/W/NE/SE/SW/NW).
    Maps terrain features to fire difficulty ratings. Includes hardcoded
    expert knowledge for key fire-prone cities (Amarillo, OKC, Denver, etc.)."""
    from tools.agent_tools.terrain import city_terrain_assessment
    return json.dumps(city_terrain_assessment(lat, lon, city_name, radius_km), indent=2, default=str)

@mcp.tool()
def assess_fuels(lat, lon, station_id=None):
    """Assess current fuel conditions — the #1 factor in fire behavior.
    Analyzes recent weather history (warm spells drying fuels, precipitation,
    RH trends), drought status, and seasonal context (winter freeze-dried
    grass vs summer cured grass). Fuels matter MORE than wind."""
    from tools.agent_tools.fuel_conditions import assess_fuel_conditions
    return json.dumps(assess_fuel_conditions(lat, lon, station_id, base_url=API_BASE), indent=2, default=str)

@mcp.tool()
def get_ignition_sources(lat, lon, city_name=None):
    """Get ignition risk sources near a location — trucking corridors (chains
    cause sparks), power lines, railroads, prescribed burn areas. Critical
    for Amarillo/OKC/I-40 corridor where trucking is #1 ignition source."""
    from tools.agent_tools.fuel_conditions import get_ignition_risk
    return json.dumps(get_ignition_risk(lat, lon, city_name), indent=2, default=str)

@mcp.tool()
def detect_wind_shifts(lat, lon, model="hrrr"):
    """Detect wind direction shifts in HRRR forecast — identifies cold front
    passages that reverse firelines. A wind shift is NOT 'nighttime recovery'
    — it reverses ALL fire spread directions while winds stay gusty."""
    from tools.agent_tools.frontal_analysis import detect_wind_shifts as _detect
    return json.dumps(_detect(lat, lon, model=model, base_url=API_BASE), indent=2, default=str)

@mcp.tool()
def classify_overnight(lat, lon, model="hrrr"):
    """Classify overnight fire weather — is it true recovery (calm + humid),
    frontal shift (wind reversal), partial recovery, or no recovery?
    Prevents incorrect 'nighttime recovery' claims in forecasts."""
    from tools.agent_tools.frontal_analysis import classify_overnight_conditions
    return json.dumps(classify_overnight_conditions(lat, lon, model=model, base_url=API_BASE), indent=2, default=str)

@mcp.tool()
def verify_winds(lat, lon, radius_miles=30, hours_back=24):
    """Verify wind speed claims against ALL available observations (ASOS +
    state mesonets + RAWS). Prevents overclaiming wind speeds in reports.
    Returns actual max gust/sustained from every station in radius."""
    from tools.agent_tools.external_data import verify_wind_claims
    return json.dumps(verify_wind_claims(lat, lon, radius_miles, hours_back), indent=2, default=str)

@mcp.tool()
def get_fire_climatology(station_id, month=None):
    """Get fire weather climatology for a station — what's normal vs extreme
    for this location. Contextualizes observations: is 9% RH 'bad' or
    'catastrophic' here? Is 39kt gust 'big' or 'run of the mill'?"""
    from tools.agent_tools.external_data import get_fire_weather_climatology
    return json.dumps(get_fire_weather_climatology(station_id, month), indent=2, default=str)


# ---------------------------------------------------------------------------
# Map Overlay Tools
# ---------------------------------------------------------------------------

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

    png_data = _api_get("/api/v1/map-overlay", params, raw=True)

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
    result = _api_get("/api/v1/map-overlay/products")
    return json.dumps(result, indent=2)


@mcp.tool()
def list_map_fields(model: str = "hrrr") -> str:
    """List available map overlay fields and their metadata.

    Args:
        model: Weather model ('hrrr', 'gfs', 'rrfs'). Default: hrrr.

    Returns:
        JSON list of fields with id, name, units, category, and value ranges.
    """
    result = _api_get("/api/v1/map-overlay/fields", {"model": model})
    return json.dumps(result, indent=2)


# ---------------------------------------------------------------------------
# Oregon WFO Agent Swarm Tools (10 tools)
# ---------------------------------------------------------------------------

@mcp.tool()
def list_oregon_zones() -> str:
    """List all 7 Oregon WFO coverage zones with status.

    Returns:
        JSON list of zones with zone_id, name, town_count, transect_count.
    """
    from tools.agent_tools.data.oregon_zones import list_zones
    from tools.agent_tools.wfo_swarm.scheduler import output_store

    zones = list_zones()
    # Attach run status to each zone
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


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Allow overriding API base via CLI arg
    if len(sys.argv) > 2 and sys.argv[1] == "--api-base":
        API_BASE = sys.argv[2]

    # Load .env file if present
    env_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    if os.path.exists(env_file):
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    os.environ.setdefault(key.strip(), val.strip())
        # Re-read after loading .env
        globals()["STREET_VIEW_KEY"] = os.environ.get("GOOGLE_STREET_VIEW_KEY", "")

    mcp.run()
