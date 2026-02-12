"""
External Data Ingestion Tools for AI Agents

Provides access to real-time and historical weather data from public APIs:
  - METAR/SYNOP observations (Iowa Environmental Mesonet)
  - RAWS fire weather stations (MesoWest/Synoptic Data)
  - State mesonet observations (West TX, OK, KS, CO, NM via Synoptic/IEM)
  - Wind verification against ALL available surface observations
  - Fire weather climatology (what's normal vs extreme for a station)
  - RH/dewpoint severity assessment with regional context
  - SPC products (outlooks, watches, mesoscale discussions)
  - NWS alerts and forecasts
  - GOES satellite imagery
  - US Drought Monitor
  - Elevation/terrain data (Open-Elevation API)
  - ASOS 1-minute observations

All tools return structured JSON. No API keys required for most sources.
"""
import json
import os
import urllib.request
import urllib.parse
from datetime import datetime, timedelta
from typing import Optional


def _fetch_json(url: str, timeout: int = 30) -> dict:
    """Fetch JSON from a URL."""
    req = urllib.request.Request(url, headers={"User-Agent": "wxsection-agent/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())


def _fetch_text(url: str, timeout: int = 30) -> str:
    """Fetch text from a URL."""
    req = urllib.request.Request(url, headers={"User-Agent": "wxsection-agent/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


# =============================================================================
# METAR / Surface Observations (Iowa Environmental Mesonet)
# =============================================================================

def _station_id_to_iem(station_id: str) -> tuple:
    """Convert an ICAO station ID to IEM (network, sid) pair.

    IEM's API uses 3-letter identifiers with state-based ASOS networks.
    ICAO codes like "KOKC" become ("OK_ASOS", "OKC").
    Already-short IDs like "OKC" need a state guess.
    """
    sid = station_id.upper().strip()
    # If 4-char ICAO with K prefix (CONUS): strip K, derive state from network
    if len(sid) == 4 and sid.startswith("K"):
        sid = sid[1:]
    # For network, we'll pass None and let the caller handle it
    return sid


def get_metar_observations(
    stations: list[str],
    start: Optional[str] = None,
    end: Optional[str] = None,
    hours_back: int = 3,
    network: Optional[str] = None,
) -> dict:
    """Get METAR observations from IEM ASOS API v1.

    Args:
        stations: List of station IDs (e.g. ["KOKC", "KDEN"] or ["OKC", "DEN"]).
            ICAO K-prefix is stripped automatically.
        start: Start time as "YYYY-MM-DD HH:MM" UTC. Default: hours_back ago.
        end: End time as "YYYY-MM-DD HH:MM" UTC. Default: now.
        hours_back: Hours to look back if start not specified. Default: 3.
        network: IEM network (e.g. "OK_ASOS"). If None, auto-detects from
            station list by trying common state networks.

    Returns:
        Dict with 'data' key containing list of observation dicts, each with:
        tmpf, dwpf, sknt, drct, relh, gust, raw, utc_valid, vsby, alti, mslp.
    """
    now = datetime.utcnow()
    if start is None:
        dt_start = now - timedelta(hours=hours_back)
    else:
        dt_start = datetime.strptime(start, "%Y-%m-%d %H:%M")
    if end is None:
        dt_end = now
    else:
        dt_end = datetime.strptime(end, "%Y-%m-%d %H:%M")

    clean_ids = [_station_id_to_iem(s) for s in stations]
    all_data = []

    for sid in clean_ids:
        # Try to fetch from IEM obhistory API (per-station, per-date)
        # We need to cover all dates in the range
        date = dt_start.date()
        end_date = dt_end.date()
        while date <= end_date:
            date_str = date.strftime("%Y-%m-%d")
            # If network not given, try to auto-detect
            networks_to_try = [network] if network else []
            if not networks_to_try:
                # Try common networks based on station ID patterns
                for state in ["OK", "TX", "KS", "CO", "NM", "CA", "AZ",
                              "NV", "OR", "WA", "MT", "ID", "WY", "NE",
                              "AR", "MO", "IL", "GA", "FL", "NY", "PA"]:
                    networks_to_try.append(f"{state}_ASOS")

            for net in networks_to_try:
                url = (
                    f"https://mesonet.agron.iastate.edu/api/1/obhistory.json?"
                    f"station={sid}&network={net}&date={date_str}"
                )
                try:
                    result = _fetch_json(url, timeout=15)
                    rows = result.get("data", [])
                    if rows:
                        # Filter to our time window
                        for row in rows:
                            ts = row.get("utc_valid", "")
                            if ts:
                                try:
                                    obs_time = datetime.strptime(
                                        ts, "%Y-%m-%dT%H:%MZ"
                                    )
                                    if dt_start <= obs_time <= dt_end:
                                        row["station"] = sid
                                        row["network"] = net
                                        all_data.append(row)
                                except ValueError:
                                    all_data.append(row)
                        break  # Found the right network
                except Exception:
                    continue

            from datetime import timedelta as _td
            date += _td(days=1)

    return {"data": all_data}


def _guess_nearby_states(lat: float, lon: float) -> list:
    """Guess which US state ASOS networks to query based on coordinates.

    IEM uses state-specific networks (e.g., OK_ASOS, TX_ASOS) rather than
    a single national ASOS network.  Returns 1-4 state codes covering the
    target point and neighboring states for border areas.
    """
    # Simple bounding-box lookup: (min_lat, max_lat, min_lon, max_lon)
    _STATE_BOXES = {
        "AL": (30.2, 35.0, -88.5, -84.9), "AR": (33.0, 36.5, -94.6, -89.6),
        "AZ": (31.3, 37.0, -114.8, -109.0), "CA": (32.5, 42.0, -124.4, -114.1),
        "CO": (37.0, 41.0, -109.1, -102.0), "CT": (41.0, 42.1, -73.7, -71.8),
        "DE": (38.5, 39.8, -75.8, -75.0), "FL": (24.5, 31.0, -87.6, -80.0),
        "GA": (30.4, 35.0, -85.6, -80.8), "IA": (40.4, 43.5, -96.6, -90.1),
        "ID": (42.0, 49.0, -117.2, -111.0), "IL": (37.0, 42.5, -91.5, -87.5),
        "IN": (37.8, 41.8, -88.1, -84.8), "KS": (37.0, 40.0, -102.1, -94.6),
        "KY": (36.5, 39.1, -89.6, -82.0), "LA": (29.0, 33.0, -94.0, -89.0),
        "MA": (41.2, 42.9, -73.5, -69.9), "MD": (38.0, 39.7, -79.5, -75.0),
        "ME": (43.1, 47.5, -71.1, -67.0), "MI": (41.7, 48.3, -90.4, -82.1),
        "MN": (43.5, 49.4, -97.2, -89.5), "MO": (36.0, 40.6, -95.8, -89.1),
        "MS": (30.2, 35.0, -91.7, -88.1), "MT": (44.4, 49.0, -116.0, -104.0),
        "NC": (33.8, 36.6, -84.3, -75.5), "ND": (45.9, 49.0, -104.0, -96.6),
        "NE": (40.0, 43.0, -104.1, -95.3), "NH": (42.7, 45.3, -72.6, -70.7),
        "NJ": (38.9, 41.4, -75.6, -73.9), "NM": (31.3, 37.0, -109.0, -103.0),
        "NV": (35.0, 42.0, -120.0, -114.0), "NY": (40.5, 45.0, -79.8, -71.9),
        "OH": (38.4, 42.0, -84.8, -80.5), "OK": (33.6, 37.0, -103.0, -94.4),
        "OR": (42.0, 46.3, -124.6, -116.5), "PA": (39.7, 42.3, -80.5, -74.7),
        "RI": (41.1, 42.0, -71.9, -71.1), "SC": (32.0, 35.2, -83.4, -78.5),
        "SD": (42.5, 46.0, -104.1, -96.4), "TN": (35.0, 36.7, -90.3, -81.6),
        "TX": (25.8, 36.5, -106.6, -93.5), "UT": (37.0, 42.0, -114.1, -109.0),
        "VA": (36.5, 39.5, -83.7, -75.2), "VT": (42.7, 45.0, -73.4, -71.5),
        "WA": (45.5, 49.0, -124.7, -116.9), "WI": (42.5, 47.1, -92.9, -86.8),
        "WV": (37.2, 40.6, -82.6, -77.7), "WY": (41.0, 45.0, -111.1, -104.1),
    }
    # Expand search box by ~1 degree to catch border stations
    matches = []
    for st, (s, n, w, e) in _STATE_BOXES.items():
        if s - 1 <= lat <= n + 1 and w - 1 <= lon <= e + 1:
            matches.append(st)
    if not matches:
        matches = ["OK"]  # fallback
    return matches[:4]


def get_nearby_stations(lat: float, lon: float, radius_km: float = 100) -> list:
    """Find ASOS/AWOS stations near a point.

    Queries IEM state-specific ASOS networks for nearby states, then
    filters by haversine distance.

    Args:
        lat: Latitude
        lon: Longitude
        radius_km: Search radius in km. Default: 100.

    Returns:
        List of nearby stations with IDs, names, distances.
    """
    import math
    states = _guess_nearby_states(lat, lon)
    stations = []
    seen_ids = set()

    for state in states:
        url = f"https://mesonet.agron.iastate.edu/geojson/network/{state}_ASOS.geojson"
        try:
            data = _fetch_json(url, timeout=15)
        except Exception:
            continue
        for feat in data.get("features", []):
            props = feat.get("properties", {})
            coords = feat.get("geometry", {}).get("coordinates", [0, 0])
            slon, slat = coords[0], coords[1]
            sid = props.get("sid", "")
            if sid in seen_ids:
                continue
            seen_ids.add(sid)
            # Haversine distance
            dlat = math.radians(slat - lat)
            dlon = math.radians(slon - lon)
            a = (math.sin(dlat / 2) ** 2
                 + math.cos(math.radians(lat))
                 * math.cos(math.radians(slat))
                 * math.sin(dlon / 2) ** 2)
            dist_km = 6371 * 2 * math.asin(math.sqrt(a))
            if dist_km <= radius_km:
                stations.append({
                    "id": sid,
                    "name": props.get("sname", ""),
                    "state": props.get("state", state),
                    "lat": slat,
                    "lon": slon,
                    "elevation_m": props.get("elevation", None),
                    "distance_km": round(dist_km, 1),
                })

    return sorted(stations, key=lambda s: s["distance_km"])


# =============================================================================
# RAWS / MesoWest (Synoptic Data API - free tier)
# =============================================================================

def get_raws_observations(
    stations: Optional[list[str]] = None,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    radius_miles: float = 50,
    hours_back: int = 6,
    api_token: str = "demotoken",
) -> dict:
    """Get RAWS fire weather station observations from Synoptic Data API.

    Either provide station IDs or lat/lon + radius for nearby stations.

    Args:
        stations: List of RAWS station IDs (e.g. ["BAWW1", "FSHC2"])
        lat: Latitude for radius search
        lon: Longitude for radius search
        radius_miles: Search radius in miles (default 50)
        hours_back: Hours of history to retrieve
        api_token: Synoptic Data API token (default: demo token with limits)

    Returns:
        Station observations with temp, RH, wind speed/direction, fuel moisture.
    """
    base = "https://api.synopticdata.com/v2/stations/timeseries"
    now = datetime.utcnow()
    start = now - timedelta(hours=hours_back)

    params = {
        "token": api_token,
        "start": start.strftime("%Y%m%d%H%M"),
        "end": now.strftime("%Y%m%d%H%M"),
        "obtimezone": "UTC",
        "vars": "air_temp,relative_humidity,wind_speed,wind_direction,wind_gust,fuel_moisture",
        "units": "english",
    }

    if stations:
        params["stid"] = ",".join(stations)
    elif lat is not None and lon is not None:
        params["radius"] = f"{lat},{lon},{radius_miles}"
        params["network"] = "2"  # RAWS network
    else:
        return {"error": "Provide either stations or lat/lon"}

    url = base + "?" + urllib.parse.urlencode(params)
    return _fetch_json(url, timeout=30)


# =============================================================================
# SPC Products (Storm Prediction Center)
# =============================================================================

def get_spc_fire_weather_outlook(day: int = 1) -> dict:
    """Get SPC Fire Weather Outlook.

    Args:
        day: Outlook day (1=today, 2=tomorrow). Default: 1.

    Returns:
        GeoJSON with fire weather outlook polygons (CRITICAL, ELEVATED, etc.)
    """
    if day == 1:
        url = "https://www.spc.noaa.gov/products/fire_wx/fwdy1.json"
    elif day == 2:
        url = "https://www.spc.noaa.gov/products/fire_wx/fwdy2.json"
    else:
        return {"error": f"Invalid day {day}, must be 1 or 2"}

    try:
        return _fetch_json(url)
    except Exception:
        # Fallback to KML parsing
        return {"error": "Could not fetch SPC fire weather outlook"}


def get_spc_fire_discussion() -> str:
    """Get SPC Fire Weather Discussion text.

    Returns:
        Plain text of the latest SPC fire weather discussion.
    """
    url = "https://www.spc.noaa.gov/products/fire_wx/fwdy1.html"
    try:
        html = _fetch_text(url)
        # Extract the discussion text from HTML
        import re
        # The discussion is in a <pre> tag
        m = re.search(r'<pre>(.*?)</pre>', html, re.DOTALL)
        if m:
            return m.group(1).strip()
        return html[:5000]
    except Exception as e:
        return f"Error: {e}"


def get_spc_mesoscale_discussions() -> list:
    """Get active SPC Mesoscale Discussions.

    Returns:
        List of active mesoscale discussions with text and affected areas.
    """
    url = "https://www.spc.noaa.gov/products/md/"
    try:
        html = _fetch_text(url)
        import re
        # Find MD links
        mds = re.findall(r'href="(md\d+\.html)"', html)
        results = []
        for md_file in mds[:5]:  # Limit to 5 most recent
            md_url = f"https://www.spc.noaa.gov/products/md/{md_file}"
            md_html = _fetch_text(md_url)
            m = re.search(r'<pre>(.*?)</pre>', md_html, re.DOTALL)
            if m:
                results.append({
                    "id": md_file.replace(".html", ""),
                    "text": m.group(1).strip()[:3000],
                    "url": md_url,
                })
        return results
    except Exception as e:
        return [{"error": str(e)}]


# =============================================================================
# NWS Alerts and Forecasts
# =============================================================================

def get_nws_alerts(
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    state: Optional[str] = None,
    event_type: Optional[str] = None,
    active_only: bool = True,
) -> dict:
    """Get NWS weather alerts.

    Args:
        lat: Latitude for point-based search
        lon: Longitude for point-based search
        state: Two-letter state code (e.g. "MT", "NM") for state-wide search
        event_type: Filter by event type (e.g. "Red Flag Warning", "Fire Weather Watch")
        active_only: Only return active alerts. Default: True.

    Returns:
        GeoJSON FeatureCollection of alerts with headline, description, severity.
    """
    base = "https://api.weather.gov/alerts"
    params = {"status": "actual"}
    if active_only:
        params["status"] = "actual"
    if lat is not None and lon is not None:
        params["point"] = f"{lat},{lon}"
    if state:
        params["area"] = state
    if event_type:
        params["event"] = event_type

    url = base + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={
        "User-Agent": "wxsection-agent/1.0",
        "Accept": "application/geo+json",
    })
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def get_nws_forecast_discussion(office: str) -> str:
    """Get NWS Area Forecast Discussion.

    Args:
        office: NWS office ID (e.g. "BOU" for Boulder, "ABQ" for Albuquerque,
                "MSO" for Missoula, "SEW" for Seattle)

    Returns:
        Plain text of the latest Area Forecast Discussion.
    """
    url = f"https://api.weather.gov/products/types/AFD/locations/{office}"
    req = urllib.request.Request(url, headers={
        "User-Agent": "wxsection-agent/1.0",
        "Accept": "application/json",
    })
    with urllib.request.urlopen(req, timeout=15) as resp:
        products = json.loads(resp.read())

    if not products.get("@graph"):
        return f"No AFD found for office {office}"

    # Get the latest
    latest_url = products["@graph"][0]["@id"]
    req2 = urllib.request.Request(latest_url, headers={
        "User-Agent": "wxsection-agent/1.0",
        "Accept": "application/json",
    })
    with urllib.request.urlopen(req2, timeout=15) as resp2:
        product = json.loads(resp2.read())

    return product.get("productText", "No text available")


# =============================================================================
# Elevation / Terrain
# =============================================================================

def get_elevation(lat: float, lon: float) -> dict:
    """Get elevation at a point using Open-Elevation API.

    Args:
        lat: Latitude
        lon: Longitude

    Returns:
        Dict with elevation_m and elevation_ft.
    """
    url = f"https://api.open-elevation.com/api/v1/lookup?locations={lat},{lon}"
    data = _fetch_json(url, timeout=15)
    results = data.get("results", [{}])
    elev_m = results[0].get("elevation", 0)
    return {
        "lat": lat,
        "lon": lon,
        "elevation_m": elev_m,
        "elevation_ft": round(elev_m * 3.281, 0),
    }


def get_elevation_profile(start_lat: float, start_lon: float,
                          end_lat: float, end_lon: float,
                          n_points: int = 100) -> list:
    """Get elevation profile along a path.

    Args:
        start_lat, start_lon: Start point
        end_lat, end_lon: End point
        n_points: Number of sample points (default 100)

    Returns:
        List of {lat, lon, elevation_m, distance_km} along the path.
    """
    import math
    points = []
    for i in range(n_points):
        frac = i / (n_points - 1)
        lat = start_lat + frac * (end_lat - start_lat)
        lon = start_lon + frac * (end_lon - start_lon)
        points.append(f"{lat},{lon}")

    locations = "|".join(points)
    url = f"https://api.open-elevation.com/api/v1/lookup?locations={locations}"
    data = _fetch_json(url, timeout=60)

    results = []
    for i, r in enumerate(data.get("results", [])):
        frac = i / (n_points - 1)
        lat = start_lat + frac * (end_lat - start_lat)
        lon = start_lon + frac * (end_lon - start_lon)
        # Distance from start using haversine
        dlat = math.radians(lat - start_lat)
        dlon = math.radians(lon - start_lon)
        a = math.sin(dlat/2)**2 + math.cos(math.radians(start_lat)) * math.cos(math.radians(lat)) * math.sin(dlon/2)**2
        dist_km = 6371 * 2 * math.asin(math.sqrt(a))
        results.append({
            "lat": round(lat, 4),
            "lon": round(lon, 4),
            "elevation_m": r.get("elevation", 0),
            "distance_km": round(dist_km, 1),
        })
    return results


# =============================================================================
# US Drought Monitor
# =============================================================================

def get_drought_status(fips: Optional[str] = None, state: Optional[str] = None) -> dict:
    """Get US Drought Monitor status.

    Args:
        fips: County FIPS code for county-level data
        state: Two-letter state code for state-level data

    Returns:
        Current drought conditions with D0-D4 percentages.
    """
    if state:
        url = f"https://usdm.unl.edu/api/area_percent/stateStatistics/{state}"
    elif fips:
        url = f"https://usdm.unl.edu/api/area_percent/countyStatistics/{fips}"
    else:
        url = "https://usdm.unl.edu/api/area_percent/nationalStatistics"

    try:
        return _fetch_json(url, timeout=15)
    except Exception as e:
        return {"error": str(e)}


# =============================================================================
# Google Street View (requires API key)
# =============================================================================

def get_street_view_image(
    lat: float,
    lon: float,
    api_key: Optional[str] = None,
    heading: int = 0,
    pitch: int = 0,
    fov: int = 90,
    size: str = "640x480",
    output_path: Optional[str] = None,
) -> dict:
    """Get Google Street View image at a location.

    Useful for ground-truth assessment of vegetation, fuel conditions,
    terrain features, and wildfire risk at specific locations.

    Args:
        lat: Latitude
        lon: Longitude
        api_key: Google Maps API key with Street View Static API enabled
        heading: Camera heading (0=north, 90=east, 180=south, 270=west)
        pitch: Camera pitch (-90=down, 0=level, 90=up)
        fov: Field of view (10-120 degrees, default 90)
        size: Image size as "WIDTHxHEIGHT" (max 640x640 for free tier)
        output_path: Where to save the image. If None, returns base64.

    Returns:
        Dict with image info, or base64-encoded image if no output_path.
    """
    import base64
    if api_key is None:
        api_key = os.environ.get("GOOGLE_STREET_VIEW_KEY", "")
    if not api_key:
        return {"error": "No API key. Set GOOGLE_STREET_VIEW_KEY env var or pass api_key."}
    params = {
        "location": f"{lat},{lon}",
        "size": size,
        "heading": heading,
        "pitch": pitch,
        "fov": fov,
        "key": api_key,
        "return_error_code": "true",
    }
    url = "https://maps.googleapis.com/maps/api/streetview?" + urllib.parse.urlencode(params)

    req = urllib.request.Request(url)
    try:
        resp = urllib.request.urlopen(req, timeout=30)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return {"error": "No Street View coverage at this location", "lat": lat, "lon": lon}
        return {"error": f"Street View API error: HTTP {e.code}", "lat": lat, "lon": lon}
    with resp:
        img_data = resp.read()
        content_type = resp.headers.get("Content-Type", "")

        if "image" not in content_type:
            return {"error": "No Street View available at this location", "status": resp.status}

        if output_path:
            os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
            with open(output_path, "wb") as f:
                f.write(img_data)
            return {
                "saved_to": output_path,
                "size_bytes": len(img_data),
                "lat": lat,
                "lon": lon,
                "heading": heading,
            }
        else:
            return {
                "image_base64": base64.b64encode(img_data).decode("ascii"),
                "mime_type": "image/jpeg",
                "size_bytes": len(img_data),
                "lat": lat,
                "lon": lon,
                "heading": heading,
            }


def street_view_panorama(
    lat: float,
    lon: float,
    api_key: Optional[str] = None,
    output_dir: str = ".",
    prefix: str = "sv",
    n_views: int = 4,
) -> list:
    """Capture a panoramic set of Street View images at a location.

    Takes multiple images at different headings to get a 360-degree view.

    Args:
        lat: Latitude
        lon: Longitude
        api_key: Google Maps API key
        output_dir: Directory to save images
        prefix: Filename prefix
        n_views: Number of views (4=90deg steps, 8=45deg steps)

    Returns:
        List of saved image info dicts.
    """
    results = []
    headings = [int(i * 360 / n_views) for i in range(n_views)]
    direction_names = {0: "N", 45: "NE", 90: "E", 135: "SE",
                       180: "S", 225: "SW", 270: "W", 315: "NW"}

    for h in headings:
        name = direction_names.get(h, f"{h}deg")
        path = f"{output_dir}/{prefix}_{lat:.4f}_{lon:.4f}_{name}.jpg"
        result = get_street_view_image(lat, lon, api_key, heading=h, output_path=path)
        if "error" not in result:
            result["direction"] = name
            results.append(result)

    return results


def street_view_along_path(
    start_lat: float, start_lon: float,
    end_lat: float, end_lon: float,
    api_key: Optional[str] = None,
    output_dir: str = ".",
    n_points: int = 10,
    heading_mode: str = "forward",
) -> list:
    """Capture Street View images along a path (e.g., a fire's propagation path).

    Args:
        start_lat, start_lon: Start of path
        end_lat, end_lon: End of path
        api_key: Google Maps API key
        output_dir: Directory to save images
        n_points: Number of sample points along the path
        heading_mode: "forward" (pointing along path), "perpendicular" (looking sideways),
                      or a specific heading as int

    Returns:
        List of image info dicts with lat, lon, distance_km.
    """
    import math
    results = []

    for i in range(n_points):
        frac = i / (n_points - 1) if n_points > 1 else 0
        lat = start_lat + frac * (end_lat - start_lat)
        lon = start_lon + frac * (end_lon - start_lon)

        # Calculate forward heading
        if heading_mode == "forward":
            dy = end_lat - start_lat
            dx = (end_lon - start_lon) * math.cos(math.radians(lat))
            heading = int(math.degrees(math.atan2(dx, dy))) % 360
        elif heading_mode == "perpendicular":
            dy = end_lat - start_lat
            dx = (end_lon - start_lon) * math.cos(math.radians(lat))
            heading = (int(math.degrees(math.atan2(dx, dy))) + 90) % 360
        else:
            heading = int(heading_mode)

        # Distance from start
        dlat = math.radians(lat - start_lat)
        dlon = math.radians(lon - start_lon)
        a = math.sin(dlat/2)**2 + math.cos(math.radians(start_lat)) * math.cos(math.radians(lat)) * math.sin(dlon/2)**2
        dist_km = 6371 * 2 * math.asin(math.sqrt(a))

        path = f"{output_dir}/path_{i:02d}_{lat:.4f}_{lon:.4f}.jpg"
        result = get_street_view_image(lat, lon, api_key, heading=heading, output_path=path)
        if "error" not in result:
            result["distance_km"] = round(dist_km, 1)
            result["point_index"] = i
            results.append(result)

    return results


# =============================================================================
# Model Surface Point Extraction (HRRR/GFS/RRFS)
# =============================================================================

def _compute_dewpoint(temp_c: float, rh_pct: float) -> float:
    """Compute dewpoint from temperature (C) and RH (%) using Magnus formula."""
    import math
    if rh_pct <= 0:
        rh_pct = 0.1
    a, b = 17.27, 237.7
    gamma = (a * temp_c) / (b + temp_c) + math.log(rh_pct / 100.0)
    return round((b * gamma) / (a - gamma), 2)


def _compute_vpd(temp_c: float, rh_pct: float) -> float:
    """Compute vapor pressure deficit (hPa) from temperature (C) and RH (%)."""
    import math
    # Tetens formula for saturation vapor pressure
    es = 6.1078 * math.exp((17.27 * temp_c) / (temp_c + 237.3))
    ea = es * (rh_pct / 100.0)
    return round(es - ea, 2)


def _find_surface_value(data_2d: list, pressure_levels: list,
                        surface_pressure: float, col: int = 0) -> tuple:
    """Extract value at the lowest valid pressure level for a column.

    Finds the pressure level closest to (but not exceeding by >5 hPa) the
    surface pressure. This gives the model's near-surface value, NOT a
    column average.

    Returns (value, pressure_hpa) or (None, None) if no valid level found.
    """
    import math
    best_i = None
    for i, p in enumerate(pressure_levels):
        if p <= surface_pressure + 5:
            if best_i is None or pressure_levels[i] > pressure_levels[best_i]:
                best_i = i
    if best_i is not None:
        val = data_2d[best_i][col]
        if val is not None and not math.isnan(val):
            return val, pressure_levels[best_i]
    return None, None


def get_point_surface_conditions(
    lat: float,
    lon: float,
    model: str = "hrrr",
    cycle: str = "latest",
    fhr: int = 0,
    base_url: str = "http://127.0.0.1:5565",
) -> dict:
    """Extract HRRR/GFS/RRFS model surface-level data for a specific lat/lon point.

    Uses the /api/v1/data endpoint with a minimal-length transect to extract
    the model's surface prediction at a single point. Returns the LOWEST
    PRESSURE LEVEL values (closest to ground), NOT column averages.

    This is critical for fire weather: column-averaged RH may be 40-50% while
    the actual surface RH can be 10-15%. Always use this for surface conditions.

    Args:
        lat: Latitude of the point
        lon: Longitude of the point
        model: Model name ("hrrr", "gfs", "rrfs"). Default: "hrrr".
        cycle: Cycle key (e.g. "20260209_06z") or "latest". Default: "latest".
        fhr: Forecast hour. Default: 0.
        base_url: Dashboard URL. Default: "http://127.0.0.1:5565".

    Returns:
        Dict with surface temperature, RH, wind, dewpoint, VPD, and metadata.
        Keys: lat, lon, model, cycle, fhr, valid_time, temperature_c, rh_pct,
        wind_speed_ms, wind_speed_kt, dewpoint_c, vpd_hpa, pressure_hpa,
        surface_level_hpa, data_source, caveat.
    """
    import math

    # Use a tiny transect (0.01 deg ~ 1km) centered on the point
    offset = 0.005
    start_lat = lat - offset
    start_lon = lon
    end_lat = lat + offset
    end_lon = lon

    base = base_url.rstrip("/")

    # Fetch three products: temperature, RH, and wind speed
    # Each gives us the 2D field + pressure levels + surface pressure
    results = {}
    products = {
        "temperature": "temperature_c",
        "rh": "rh_pct",
        "wind_speed": None,  # wind has u/v components
    }

    for product, field_key in products.items():
        params = (
            f"start_lat={start_lat}&start_lon={start_lon}"
            f"&end_lat={end_lat}&end_lon={end_lon}"
            f"&product={product}&model={model}&cycle={cycle}&fhr={fhr}"
        )
        url = f"{base}/api/v1/data?{params}"
        try:
            data = _fetch_json(url, timeout=60)
        except Exception as e:
            return {
                "error": f"Failed to fetch {product} data: {e}",
                "url": url,
            }
        results[product] = data

    # Extract pressure info from the first successful response
    temp_data = results.get("temperature", {})
    pressure_levels = temp_data.get("pressure_levels_hpa", [])
    surface_pressures = temp_data.get("surface_pressure_hpa", [])

    if not pressure_levels or not surface_pressures:
        return {
            "error": "No pressure level data returned from API",
            "hint": "Check that the dashboard is running and data is loaded",
            "raw_keys": list(temp_data.keys()),
        }

    # Use the center column (middle point of our tiny transect)
    n_pts = len(surface_pressures)
    center = n_pts // 2
    sfc_pressure = surface_pressures[center]

    # Extract surface temperature
    temp_2d = temp_data.get("temperature_c")
    temp_c = None
    temp_level = None
    if temp_2d:
        temp_c, temp_level = _find_surface_value(
            temp_2d, pressure_levels, sfc_pressure, center
        )

    # Extract surface RH
    rh_data = results.get("rh", {})
    rh_2d = rh_data.get("rh_pct")
    rh_pct = None
    if rh_2d:
        rh_pct, _ = _find_surface_value(
            rh_2d, pressure_levels, sfc_pressure, center
        )

    # Extract surface wind speed from u/v components
    wind_data = results.get("wind_speed", {})
    u_2d = wind_data.get("u_wind_ms")
    v_2d = wind_data.get("v_wind_ms")
    wind_speed_ms = None
    wind_speed_kt = None
    if u_2d and v_2d:
        u_val, _ = _find_surface_value(u_2d, pressure_levels, sfc_pressure, center)
        v_val, _ = _find_surface_value(v_2d, pressure_levels, sfc_pressure, center)
        if u_val is not None and v_val is not None:
            wind_speed_ms = math.sqrt(u_val**2 + v_val**2)
            wind_speed_kt = round(wind_speed_ms * 1.94384, 1)
            wind_speed_ms = round(wind_speed_ms, 1)

    # Compute derived quantities
    dewpoint_c = None
    vpd_hpa = None
    if temp_c is not None and rh_pct is not None:
        dewpoint_c = _compute_dewpoint(temp_c, rh_pct)
        vpd_hpa = _compute_vpd(temp_c, rh_pct)

    # Round primary values
    if temp_c is not None:
        temp_c = round(temp_c, 1)
    if rh_pct is not None:
        rh_pct = round(rh_pct, 1)

    # Extract metadata from response
    meta = temp_data.get("metadata", {})

    return {
        "lat": lat,
        "lon": lon,
        "model": meta.get("model", model),
        "cycle": meta.get("cycle", cycle),
        "fhr": meta.get("fhr", fhr),
        "valid_time": meta.get("valid_time"),
        "temperature_c": temp_c,
        "rh_pct": rh_pct,
        "wind_speed_ms": wind_speed_ms,
        "wind_speed_kt": wind_speed_kt,
        "dewpoint_c": dewpoint_c,
        "vpd_hpa": vpd_hpa,
        "pressure_hpa": round(sfc_pressure, 1) if sfc_pressure else None,
        "surface_level_hpa": round(temp_level, 1) if temp_level else None,
        "data_source": "model_surface_level",
        "caveat": (
            "Values are model lowest pressure level, not true 2m observations. "
            "Compare with nearest METAR for ground truth."
        ),
    }


def get_model_obs_comparison(
    lat: float,
    lon: float,
    station_id: str = None,
    model: str = "hrrr",
    cycle: str = "latest",
    fhr: int = 0,
    base_url: str = "http://127.0.0.1:5565",
) -> dict:
    """Compare model surface conditions with actual METAR observations.

    This is the key diagnostic tool for understanding model bias. Fire weather
    decisions should NEVER rely solely on cross-section column averages.

    Workflow:
      1. Calls get_point_surface_conditions() for model surface-level data.
      2. Finds the nearest METAR station (or uses the provided station_id).
      3. Fetches recent METAR observations from IEM.
      4. Returns a side-by-side comparison with differences and plain-English
         assessment of model bias.

    Args:
        lat: Latitude of the point of interest
        lon: Longitude of the point of interest
        station_id: ICAO station ID for METAR (e.g. "KDEN"). If None,
                    finds the nearest station automatically.
        model: Model name. Default: "hrrr".
        cycle: Cycle key or "latest". Default: "latest".
        fhr: Forecast hour. Default: 0.
        base_url: Dashboard URL. Default: "http://127.0.0.1:5565".

    Returns:
        Dict with keys: model, observed, differences, assessment.
    """
    # Step 1: Get model surface conditions
    model_data = get_point_surface_conditions(
        lat, lon, model=model, cycle=cycle, fhr=fhr, base_url=base_url
    )
    if "error" in model_data:
        return {
            "error": f"Failed to get model data: {model_data['error']}",
            "model_data": model_data,
        }

    # Step 2: Find station and get METAR observations
    obs_station = station_id
    obs_data = None
    station_info = None

    if obs_station is None:
        # Find nearest ASOS/AWOS station
        try:
            nearby = get_nearby_stations(lat, lon, radius_km=100)
            if nearby:
                station_info = nearby[0]
                obs_station = station_info["id"]
            else:
                return {
                    "model": model_data,
                    "observed": None,
                    "differences": {},
                    "error_obs": "No ASOS/AWOS stations found within 100km",
                    "assessment": (
                        "Could not find a nearby METAR station for comparison. "
                        "Model surface values are provided but cannot be verified."
                    ),
                }
        except Exception as e:
            return {
                "model": model_data,
                "observed": None,
                "differences": {},
                "error_obs": f"Station search failed: {e}",
                "assessment": "Station lookup failed. Model values cannot be verified.",
            }

    # Fetch METAR for the station
    obs_temp_c = None
    obs_rh_pct = None
    obs_wind_kt = None
    obs_dewpoint_c = None
    obs_time = None

    try:
        metar = get_metar_observations([obs_station], hours_back=3)
        obs_list = metar.get("data", [])
        if obs_list:
            # Use the most recent observation
            latest = obs_list[-1]
            # IEM ASOS API returns tmpf/dwpf (Fahrenheit), sknt, relh
            tmpf = latest.get("tmpf")
            dwpf = latest.get("dwpf")
            sknt = latest.get("sknt")
            relh = latest.get("relh")
            obs_time = latest.get("valid")

            if tmpf is not None and tmpf != "M":
                obs_temp_c = round((float(tmpf) - 32) * 5.0 / 9.0, 1)
            if dwpf is not None and dwpf != "M":
                obs_dewpoint_c = round((float(dwpf) - 32) * 5.0 / 9.0, 1)
            if sknt is not None and sknt != "M":
                obs_wind_kt = round(float(sknt), 1)
            if relh is not None and relh != "M":
                obs_rh_pct = round(float(relh), 1)
    except Exception as e:
        return {
            "model": model_data,
            "observed": None,
            "differences": {},
            "error_obs": f"METAR fetch failed for {obs_station}: {e}",
            "assessment": "METAR data unavailable. Model values cannot be verified.",
        }

    # Step 3: Build comparison
    observed = {
        "station_id": obs_station,
        "station_name": station_info["name"] if station_info else obs_station,
        "distance_km": station_info["distance_km"] if station_info else None,
        "obs_time": obs_time,
        "temperature_c": obs_temp_c,
        "dewpoint_c": obs_dewpoint_c,
        "rh_pct": obs_rh_pct,
        "wind_speed_kt": obs_wind_kt,
    }

    # Compute differences (model minus observed; positive = model higher)
    differences = {}
    if model_data.get("temperature_c") is not None and obs_temp_c is not None:
        differences["temp_diff_c"] = round(model_data["temperature_c"] - obs_temp_c, 1)
    if model_data.get("rh_pct") is not None and obs_rh_pct is not None:
        differences["rh_diff_pct"] = round(model_data["rh_pct"] - obs_rh_pct, 1)
    if model_data.get("wind_speed_kt") is not None and obs_wind_kt is not None:
        differences["wind_diff_kt"] = round(model_data["wind_speed_kt"] - obs_wind_kt, 1)
    if model_data.get("dewpoint_c") is not None and obs_dewpoint_c is not None:
        differences["dewpoint_diff_c"] = round(model_data["dewpoint_c"] - obs_dewpoint_c, 1)

    # Step 4: Generate plain-English assessment
    assessment_parts = []

    rh_diff = differences.get("rh_diff_pct")
    if rh_diff is not None:
        m_rh = model_data["rh_pct"]
        o_rh = obs_rh_pct
        if abs(rh_diff) > 15:
            if rh_diff > 0:
                assessment_parts.append(
                    f"Model shows {m_rh}% RH but METAR reports {o_rh}% "
                    f"-- model is significantly overestimating moisture (+{rh_diff}%)."
                )
            else:
                assessment_parts.append(
                    f"Model shows {m_rh}% RH but METAR reports {o_rh}% "
                    f"-- model is significantly underestimating moisture ({rh_diff}%)."
                )
        elif abs(rh_diff) > 5:
            direction = "overestimating" if rh_diff > 0 else "underestimating"
            assessment_parts.append(
                f"Model RH ({m_rh}%) vs observed ({o_rh}%): moderate {direction} ({rh_diff:+.0f}%)."
            )
        else:
            assessment_parts.append(
                f"Model RH ({m_rh}%) is close to observed ({o_rh}%): good agreement."
            )

    temp_diff = differences.get("temp_diff_c")
    if temp_diff is not None:
        m_t = model_data["temperature_c"]
        o_t = obs_temp_c
        if abs(temp_diff) > 3:
            direction = "warmer" if temp_diff > 0 else "cooler"
            assessment_parts.append(
                f"Model temperature ({m_t}C) is {abs(temp_diff):.1f}C {direction} than observed ({o_t}C)."
            )
        else:
            assessment_parts.append(
                f"Model temperature ({m_t}C) is close to observed ({o_t}C)."
            )

    wind_diff = differences.get("wind_diff_kt")
    if wind_diff is not None:
        m_w = model_data["wind_speed_kt"]
        o_w = obs_wind_kt
        if abs(wind_diff) > 10:
            direction = "overpredicting" if wind_diff > 0 else "underpredicting"
            assessment_parts.append(
                f"Model wind ({m_w} kt) is {direction} compared to observed ({o_w} kt)."
            )

    if not assessment_parts:
        assessment_parts.append(
            "Comparison data incomplete. Check that METAR observations are available."
        )

    # Add the column-average caveat
    assessment_parts.append(
        "Cross-section column data does NOT represent surface conditions. "
        "Always use surface-level extraction for fire weather assessments."
    )

    return {
        "model": model_data,
        "observed": observed,
        "differences": differences,
        "assessment": " ".join(assessment_parts),
    }


# =============================================================================
# State Mesonet Observations (Synoptic Data / IEM aggregated networks)
# =============================================================================

# IEM network codes for common state mesonets and supplemental networks.
# Synoptic Data uses different codes; IEM is the free fallback.
_MESONET_NETWORKS = {
    "WTM": {
        "iem_network": "TX_WTMESO",
        "description": "West Texas Mesonet (Texas Tech / NWI)",
        "url": "https://www.depts.ttu.edu/nwi/research/facilities/wtm/",
    },
    "OK_OKMESO": {
        "iem_network": "OK_OKMESO",
        "description": "Oklahoma Mesonet (OU / Oklahoma Climatological Survey)",
        "url": "https://www.mesonet.org/",
    },
    "KS_KSMESO": {
        "iem_network": "KS_KSMESO",
        "description": "Kansas Mesonet (K-State)",
        "url": "https://mesonet.k-state.edu/",
    },
    "CO_COAGMET": {
        "iem_network": "CO_COAGMET",
        "description": "Colorado Agricultural Meteorological Network",
        "url": "https://coagmet.colostate.edu/",
    },
    "NM_NMMESO": {
        "iem_network": "NM_NMMESO",
        "description": "New Mexico Climate Center Mesonet",
        "url": "https://weather.nmsu.edu/",
    },
    "RAWS": {
        "iem_network": None,  # RAWS are per-state: e.g. TX_RAWS, OK_RAWS
        "description": "Remote Automatic Weather Stations (BLM/USFS)",
        "synoptic_network": "2",
    },
}


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Haversine distance in km between two lat/lon points."""
    import math
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(lat1))
         * math.cos(math.radians(lat2))
         * math.sin(dlon / 2) ** 2)
    return 6371.0 * 2 * math.asin(math.sqrt(a))


def get_mesonet_observations(
    lat: float,
    lon: float,
    radius_miles: float = 30,
    hours_back: int = 24,
    network: Optional[str] = None,
    api_token: str = "demotoken",
) -> dict:
    """Get observations from state mesonets and supplemental networks.

    Queries Synoptic Data API (which aggregates West Texas Mesonet, Oklahoma
    Mesonet, RAWS, and other networks) and falls back to IEM if needed.

    State mesonets report data that ASOS/METAR often lack:
      - Peak wind gust with precise timestamp
      - 2-minute sustained wind (vs METAR 10-minute average)
      - Fuel moisture sensors (some RAWS stations)
      - Solar radiation (affects fuel drying rates)
      - Soil temperature/moisture (affects green-up timing)

    Args:
        lat: Center latitude for search.
        lon: Center longitude for search.
        radius_miles: Search radius in miles. Default: 30.
        hours_back: Hours of history to retrieve. Default: 24.
        network: Filter to a specific network. Examples:
            "WTM" - West Texas Mesonet only
            "OK_OKMESO" - Oklahoma Mesonet only
            None - all available networks (ASOS + mesonet + RAWS)
        api_token: Synoptic Data API token. Default: "demotoken" (free tier,
            rate-limited to ~5 requests/min, 1440/day).

    Returns:
        Dict with keys:
          - stations: list of station dicts, each with id, name, network,
            lat, lon, distance_km, and observations (list of obs dicts)
          - summary: dict with station_count, networks_found, time_range
          - source: "synoptic" or "iem_fallback"
          - errors: list of any non-fatal errors encountered
    """
    now = datetime.utcnow()
    start = now - timedelta(hours=hours_back)
    errors = []

    # --- Attempt 1: Synoptic Data API (aggregates all networks) ---
    try:
        result = _fetch_mesonet_synoptic(
            lat, lon, radius_miles, start, now, network, api_token
        )
        if result.get("stations"):
            return result
        errors.append("Synoptic API returned no stations; trying IEM fallback")
    except Exception as e:
        errors.append(f"Synoptic API failed: {e}; trying IEM fallback")

    # --- Attempt 2: IEM fallback (state mesonet networks) ---
    try:
        result = _fetch_mesonet_iem(lat, lon, radius_miles, start, now, network)
        result["errors"] = errors + result.get("errors", [])
        return result
    except Exception as e:
        errors.append(f"IEM fallback also failed: {e}")
        return {
            "stations": [],
            "summary": {"station_count": 0, "networks_found": [], "time_range": None},
            "source": "none",
            "errors": errors,
        }


def _fetch_mesonet_synoptic(
    lat: float, lon: float, radius_miles: float,
    start: datetime, end: datetime,
    network: Optional[str], api_token: str,
) -> dict:
    """Fetch mesonet data from Synoptic Data API (MesoWest).

    The Synoptic API aggregates data from 30,000+ stations across the US
    including state mesonets, ASOS, RAWS, and DOT road weather stations.

    Free tier ("demotoken"): ~5 req/min, 1440/day. Sufficient for agent use.
    """
    base = "https://api.synopticdata.com/v2/stations/timeseries"
    params = {
        "token": api_token,
        "radius": f"{lat},{lon},{radius_miles}",
        "start": start.strftime("%Y%m%d%H%M"),
        "end": end.strftime("%Y%m%d%H%M"),
        "obtimezone": "UTC",
        "vars": (
            "air_temp,relative_humidity,wind_speed,wind_direction,"
            "wind_gust,peak_wind_speed,peak_wind_direction,"
            "fuel_moisture,fuel_temp,solar_radiation,"
            "soil_temp,soil_moisture,dew_point_temperature"
        ),
        "units": "english",  # temp in F, wind in kt
    }

    # Filter by network if requested
    if network:
        net_info = _MESONET_NETWORKS.get(network, {})
        synoptic_net = net_info.get("synoptic_network")
        if synoptic_net:
            params["network"] = synoptic_net
        elif network in ("WTM",):
            # West Texas Mesonet network ID in Synoptic
            params["network"] = "143"
        elif network in ("OK_OKMESO",):
            params["network"] = "2"  # Oklahoma Mesonet
        # Otherwise, don't filter — let all networks come through

    url = base + "?" + urllib.parse.urlencode(params)
    raw = _fetch_json(url, timeout=30)

    # Check API response status
    summary_resp = raw.get("SUMMARY", {})
    if summary_resp.get("RESPONSE_CODE") != 1:
        msg = summary_resp.get("RESPONSE_MESSAGE", "Unknown error")
        return {
            "stations": [],
            "summary": {"station_count": 0, "networks_found": [], "time_range": None},
            "source": "synoptic",
            "errors": [f"Synoptic API: {msg}"],
        }

    stations = []
    networks_found = set()

    for stn in raw.get("STATION", []):
        stn_lat = float(stn.get("LATITUDE", 0))
        stn_lon = float(stn.get("LONGITUDE", 0))
        dist_km = _haversine_km(lat, lon, stn_lat, stn_lon)

        net_name = stn.get("MNET_SHORTNAME", stn.get("NETWORK", "unknown"))
        networks_found.add(net_name)

        # Parse observations from the timeseries
        obs_data = stn.get("OBSERVATIONS", {})
        timestamps = obs_data.get("date_time", [])

        observations = []
        for i, ts in enumerate(timestamps):
            obs = {"time_utc": ts}
            for var_key, out_key in [
                ("air_temp_set_1", "air_temp_f"),
                ("relative_humidity_set_1", "rh_pct"),
                ("wind_speed_set_1", "wind_speed_kt"),
                ("wind_direction_set_1", "wind_dir_deg"),
                ("wind_gust_set_1", "wind_gust_kt"),
                ("peak_wind_speed_set_1", "peak_wind_kt"),
                ("peak_wind_direction_set_1", "peak_wind_dir_deg"),
                ("fuel_moisture_set_1", "fuel_moisture_pct"),
                ("fuel_temp_set_1", "fuel_temp_f"),
                ("solar_radiation_set_1", "solar_rad_wm2"),
                ("soil_temp_set_1", "soil_temp_f"),
                ("soil_moisture_set_1", "soil_moisture_pct"),
                ("dew_point_temperature_set_1", "dewpoint_f"),
            ]:
                vals = obs_data.get(var_key, [])
                if i < len(vals) and vals[i] is not None:
                    obs[out_key] = vals[i]
            observations.append(obs)

        stations.append({
            "id": stn.get("STID", ""),
            "name": stn.get("NAME", ""),
            "network": net_name,
            "network_id": stn.get("MNET_ID", ""),
            "lat": stn_lat,
            "lon": stn_lon,
            "elevation_ft": stn.get("ELEVATION", None),
            "distance_km": round(dist_km, 1),
            "observations": observations,
        })

    stations.sort(key=lambda s: s["distance_km"])

    return {
        "stations": stations,
        "summary": {
            "station_count": len(stations),
            "networks_found": sorted(networks_found),
            "time_range": f"{start.strftime('%Y-%m-%d %H:%MZ')} to {end.strftime('%Y-%m-%d %H:%MZ')}",
        },
        "source": "synoptic",
        "errors": [],
    }


def _fetch_mesonet_iem(
    lat: float, lon: float, radius_miles: float,
    start: datetime, end: datetime,
    network: Optional[str],
) -> dict:
    """Fallback: fetch mesonet data from Iowa Environmental Mesonet.

    IEM aggregates many state mesonet networks. Less comprehensive than
    Synoptic but fully free with no rate limits.
    """
    radius_km = radius_miles * 1.60934
    states = _guess_nearby_states(lat, lon)
    errors = []

    # Determine which IEM networks to query
    networks_to_try = []
    if network:
        net_info = _MESONET_NETWORKS.get(network, {})
        iem_net = net_info.get("iem_network")
        if iem_net:
            networks_to_try.append(iem_net)
        else:
            # Try state-specific variant
            for st in states:
                networks_to_try.append(f"{st}_{network}")
    else:
        # Query ASOS + mesonet + RAWS for nearby states
        for st in states:
            networks_to_try.extend([
                f"{st}_ASOS",
                # Common IEM mesonet network naming
            ])
            # Add mesonet networks if they exist for this state
            for net_key, net_info in _MESONET_NETWORKS.items():
                iem_net = net_info.get("iem_network", "")
                if iem_net and iem_net.startswith(st):
                    networks_to_try.append(iem_net)
            # RAWS
            networks_to_try.append(f"{st}_RAWS")

    # Fetch station lists and observations
    import math
    all_stations = []
    seen_ids = set()
    networks_found = set()

    for net in networks_to_try:
        # Get station list for this network
        geo_url = f"https://mesonet.agron.iastate.edu/geojson/network/{net}.geojson"
        try:
            geo_data = _fetch_json(geo_url, timeout=15)
        except Exception:
            continue

        for feat in geo_data.get("features", []):
            props = feat.get("properties", {})
            coords = feat.get("geometry", {}).get("coordinates", [0, 0])
            slon, slat = coords[0], coords[1]
            sid = props.get("sid", "")
            if sid in seen_ids:
                continue

            dist_km = _haversine_km(lat, lon, slat, slon)
            if dist_km > radius_km:
                continue

            seen_ids.add(sid)

            # Fetch observations for this station
            date = start.date()
            end_date = end.date()
            observations = []
            while date <= end_date:
                date_str = date.strftime("%Y-%m-%d")
                obs_url = (
                    f"https://mesonet.agron.iastate.edu/api/1/obhistory.json?"
                    f"station={sid}&network={net}&date={date_str}"
                )
                try:
                    obs_result = _fetch_json(obs_url, timeout=15)
                    for row in obs_result.get("data", []):
                        ts = row.get("utc_valid", "")
                        if ts:
                            try:
                                obs_time = datetime.strptime(ts, "%Y-%m-%dT%H:%MZ")
                                if start <= obs_time <= end:
                                    obs = {"time_utc": ts}
                                    if row.get("tmpf") is not None:
                                        obs["air_temp_f"] = row["tmpf"]
                                    if row.get("relh") is not None:
                                        obs["rh_pct"] = row["relh"]
                                    if row.get("sknt") is not None:
                                        obs["wind_speed_kt"] = row["sknt"]
                                    if row.get("drct") is not None:
                                        obs["wind_dir_deg"] = row["drct"]
                                    if row.get("gust") is not None:
                                        obs["wind_gust_kt"] = row["gust"]
                                    if row.get("dwpf") is not None:
                                        obs["dewpoint_f"] = row["dwpf"]
                                    observations.append(obs)
                            except ValueError:
                                pass
                except Exception as e:
                    errors.append(f"IEM obs fetch failed for {sid}/{net}/{date_str}: {e}")
                date += timedelta(days=1)

            if observations:
                networks_found.add(net)
                all_stations.append({
                    "id": sid,
                    "name": props.get("sname", ""),
                    "network": net,
                    "lat": slat,
                    "lon": slon,
                    "elevation_ft": props.get("elevation", None),
                    "distance_km": round(dist_km, 1),
                    "observations": observations,
                })

    all_stations.sort(key=lambda s: s["distance_km"])

    return {
        "stations": all_stations,
        "summary": {
            "station_count": len(all_stations),
            "networks_found": sorted(networks_found),
            "time_range": f"{start.strftime('%Y-%m-%d %H:%MZ')} to {end.strftime('%Y-%m-%d %H:%MZ')}",
        },
        "source": "iem_fallback",
        "errors": errors,
    }


# =============================================================================
# Wind Verification — cross-check claims against ALL available observations
# =============================================================================

def verify_wind_claims(
    lat: float,
    lon: float,
    radius_miles: float = 30,
    hours_back: int = 24,
    api_token: str = "demotoken",
) -> dict:
    """Verify wind speed claims against ALL available surface observations.

    This is the key credibility tool. Pulls wind data from ASOS, state
    mesonets, and RAWS stations within the search radius, then produces a
    verification summary with explicit statements about what the data does
    and does NOT support.

    Motivation: model output and media reports frequently overstate wind
    speeds. A firefighter who checks their local mesonet will immediately
    spot overclaims. This tool prevents that credibility hit.

    Args:
        lat: Center latitude.
        lon: Center longitude.
        radius_miles: Search radius in miles. Default: 30.
        hours_back: Hours of history to check. Default: 24.
        api_token: Synoptic Data API token. Default: "demotoken".

    Returns:
        Dict with:
          - location: {lat, lon}
          - time_range: human-readable UTC time range
          - stations_checked: int
          - wind_summary: {max_gust_observed, max_sustained_observed, stations}
          - verification_notes: list of plain-English statements
          - raw_errors: list of any API errors encountered
    """
    now = datetime.utcnow()
    start = now - timedelta(hours=hours_back)
    time_range = f"{start.strftime('%Y-%m-%d %H:%MZ')} to {now.strftime('%Y-%m-%d %H:%MZ')}"

    # Pull ALL networks (no network filter) to get comprehensive coverage
    mesonet_data = get_mesonet_observations(
        lat=lat, lon=lon,
        radius_miles=radius_miles,
        hours_back=hours_back,
        network=None,
        api_token=api_token,
    )

    stations_summary = []
    overall_max_gust = {"speed_kt": 0, "station": None, "time": None}
    overall_max_sustained = {"speed_kt": 0, "station": None, "time": None}

    for stn in mesonet_data.get("stations", []):
        stn_max_gust_kt = 0
        stn_max_gust_time = None
        stn_max_sustained_kt = 0
        stn_max_sustained_time = None

        for obs in stn.get("observations", []):
            # Check gust (wind_gust_kt or peak_wind_kt)
            gust = obs.get("wind_gust_kt") or obs.get("peak_wind_kt")
            if gust is not None:
                try:
                    gust_val = float(gust)
                    if gust_val > stn_max_gust_kt:
                        stn_max_gust_kt = gust_val
                        stn_max_gust_time = obs.get("time_utc")
                except (ValueError, TypeError):
                    pass

            # Check sustained wind
            sustained = obs.get("wind_speed_kt")
            if sustained is not None:
                try:
                    sustained_val = float(sustained)
                    if sustained_val > stn_max_sustained_kt:
                        stn_max_sustained_kt = sustained_val
                        stn_max_sustained_time = obs.get("time_utc")
                except (ValueError, TypeError):
                    pass

        stations_summary.append({
            "id": stn["id"],
            "name": stn.get("name", ""),
            "type": _classify_station_type(stn.get("network", "")),
            "network": stn.get("network", ""),
            "max_gust_kt": round(stn_max_gust_kt, 1) if stn_max_gust_kt else 0,
            "max_gust_time": stn_max_gust_time,
            "max_sustained_kt": round(stn_max_sustained_kt, 1) if stn_max_sustained_kt else 0,
            "max_sustained_time": stn_max_sustained_time,
            "distance_km": stn.get("distance_km", 0),
        })

        # Update overall maxes
        if stn_max_gust_kt > overall_max_gust["speed_kt"]:
            overall_max_gust = {
                "speed_kt": round(stn_max_gust_kt, 1),
                "speed_mph": round(stn_max_gust_kt * 1.15078, 0),
                "station": stn["id"],
                "station_name": stn.get("name", ""),
                "time": stn_max_gust_time,
            }
        if stn_max_sustained_kt > overall_max_sustained["speed_kt"]:
            overall_max_sustained = {
                "speed_kt": round(stn_max_sustained_kt, 1),
                "speed_mph": round(stn_max_sustained_kt * 1.15078, 0),
                "station": stn["id"],
                "station_name": stn.get("name", ""),
                "time": stn_max_sustained_time,
            }

    # Sort stations by max gust descending
    stations_summary.sort(key=lambda s: s["max_gust_kt"], reverse=True)

    # Generate verification notes
    notes = _generate_wind_verification_notes(
        overall_max_gust, overall_max_sustained,
        stations_summary, radius_miles
    )

    return {
        "location": {"lat": lat, "lon": lon},
        "time_range": time_range,
        "stations_checked": len(stations_summary),
        "networks_queried": mesonet_data.get("summary", {}).get("networks_found", []),
        "data_source": mesonet_data.get("source", "unknown"),
        "wind_summary": {
            "max_gust_observed": overall_max_gust,
            "max_sustained_observed": overall_max_sustained,
            "stations": stations_summary,
        },
        "verification_notes": notes,
        "raw_errors": mesonet_data.get("errors", []),
    }


def _classify_station_type(network: str) -> str:
    """Classify a station's network into a human-readable type."""
    net_upper = network.upper()
    if "ASOS" in net_upper or "AWOS" in net_upper:
        return "ASOS"
    if "RAWS" in net_upper:
        return "RAWS"
    if "MESO" in net_upper or "WTM" in net_upper:
        return "mesonet"
    if "COOP" in net_upper:
        return "COOP"
    if "DCP" in net_upper:
        return "DCP"
    return "other"


def _generate_wind_verification_notes(
    max_gust: dict, max_sustained: dict,
    stations: list, radius_miles: float,
) -> list:
    """Generate plain-English verification notes from wind observations."""
    notes = []

    n_stations = len(stations)
    if n_stations == 0:
        notes.append(
            f"WARNING: No stations found within {radius_miles} miles. "
            "Wind claims cannot be verified."
        )
        return notes

    gust_kt = max_gust.get("speed_kt", 0)
    gust_mph = max_gust.get("speed_mph", 0)
    sustained_kt = max_sustained.get("speed_kt", 0)
    sustained_mph = max_sustained.get("speed_mph", 0)

    notes.append(
        f"Checked {n_stations} stations within {radius_miles} miles."
    )

    if gust_kt > 0:
        notes.append(
            f"Peak gust observed: {gust_kt} kt ({gust_mph:.0f} mph) at "
            f"{max_gust.get('station', '?')} ({max_gust.get('station_name', '')}) "
            f"at {max_gust.get('time', '?')}."
        )
    else:
        notes.append("No wind gust data available from any station in the search area.")

    if sustained_kt > 0:
        notes.append(
            f"Peak sustained wind observed: {sustained_kt} kt ({sustained_mph:.0f} mph) at "
            f"{max_sustained.get('station', '?')} ({max_sustained.get('station_name', '')}) "
            f"at {max_sustained.get('time', '?')}."
        )

    # Generate specific claim-verification statements at key thresholds
    # These thresholds are commonly overclaimed in fire weather reports
    for threshold_kt, threshold_mph, label in [
        (52, 60, "60 mph sustained winds"),
        (43, 50, "50 mph sustained winds"),
        (35, 40, "40 mph sustained winds"),
    ]:
        if sustained_kt < threshold_kt:
            notes.append(
                f"No station within {radius_miles} miles reported sustained "
                f"winds at or above {threshold_kt} kt ({threshold_mph} mph). "
                f"Any claim of '{label}' is NOT supported by surface observations."
            )
            break  # Only add the most relevant threshold

    for threshold_kt, threshold_mph, label in [
        (52, 60, "60 mph gusts"),
        (43, 50, "50 mph gusts"),
    ]:
        if gust_kt < threshold_kt:
            notes.append(
                f"No station within {radius_miles} miles reported gusts at "
                f"or above {threshold_kt} kt ({threshold_mph} mph). "
                f"Any claim of '{label}' is NOT supported by surface observations."
            )
            break

    # Characterize the actual conditions
    if sustained_kt > 0 and gust_kt > 0:
        notes.append(
            f"Observed conditions: sustained winds {sustained_kt} kt "
            f"({sustained_mph:.0f} mph) with gusts to {gust_kt} kt "
            f"({gust_mph:.0f} mph)."
        )
        # Qualitative assessment
        if gust_kt >= 50:
            notes.append("This is a HIGH WIND event (NWS criteria: gusts >= 58 mph or sustained >= 40 mph).")
        elif gust_kt >= 35:
            notes.append(
                "This is a WIND ADVISORY level event — significant but not extreme. "
                "Common in the southern Great Plains during strong synoptic events."
            )
        elif gust_kt >= 25:
            notes.append(
                "This is a breezy/windy day but within normal range for open terrain. "
                "Fire risk comes from combination with low RH, not wind alone."
            )

    return notes


# =============================================================================
# Fire Weather Climatology — what's normal vs. extreme for a station
# =============================================================================

# Hardcoded climatology for key stations. These are based on historical ASOS
# records (1990-2025) and are more reliable than pulling from limited APIs.
# Sources: WRCC, xmACIS2, IEM, local climate pages.
_STATION_CLIMATOLOGY = {
    "KAMA": {
        "name": "Amarillo, TX (Rick Husband Intl)",
        "elevation_ft": 3607,
        "region": "Texas Panhandle",
        "months": {
            1: {"normal_high_f": 49, "normal_low_f": 23, "rh_typical_min": 25, "rh_extreme_min": 8, "rh_low_days_per_month": 3, "dp_typical_low_f": 14, "dp_extreme_low_f": -8, "gust_typical_max_kt": 35, "gust_extreme_kt": 58, "gust_sig_threshold_kt": 45},
            2: {"normal_high_f": 52, "normal_low_f": 25, "rh_typical_min": 20, "rh_extreme_min": 7, "rh_low_days_per_month": 5, "dp_typical_low_f": 15, "dp_extreme_low_f": -5, "gust_typical_max_kt": 38, "gust_extreme_kt": 62, "gust_sig_threshold_kt": 45},
            3: {"normal_high_f": 61, "normal_low_f": 32, "rh_typical_min": 15, "rh_extreme_min": 5, "rh_low_days_per_month": 8, "dp_typical_low_f": 15, "dp_extreme_low_f": -3, "gust_typical_max_kt": 42, "gust_extreme_kt": 68, "gust_sig_threshold_kt": 50},
            4: {"normal_high_f": 70, "normal_low_f": 40, "rh_typical_min": 12, "rh_extreme_min": 4, "rh_low_days_per_month": 10, "dp_typical_low_f": 18, "dp_extreme_low_f": 0, "gust_typical_max_kt": 45, "gust_extreme_kt": 70, "gust_sig_threshold_kt": 50},
            5: {"normal_high_f": 79, "normal_low_f": 50, "rh_typical_min": 15, "rh_extreme_min": 5, "rh_low_days_per_month": 6, "dp_typical_low_f": 30, "dp_extreme_low_f": 10, "gust_typical_max_kt": 42, "gust_extreme_kt": 65, "gust_sig_threshold_kt": 50},
            6: {"normal_high_f": 88, "normal_low_f": 60, "rh_typical_min": 18, "rh_extreme_min": 6, "rh_low_days_per_month": 4, "dp_typical_low_f": 42, "dp_extreme_low_f": 20, "gust_typical_max_kt": 40, "gust_extreme_kt": 62, "gust_sig_threshold_kt": 48},
            7: {"normal_high_f": 91, "normal_low_f": 64, "rh_typical_min": 22, "rh_extreme_min": 8, "rh_low_days_per_month": 2, "dp_typical_low_f": 50, "dp_extreme_low_f": 30, "gust_typical_max_kt": 38, "gust_extreme_kt": 58, "gust_sig_threshold_kt": 45},
            8: {"normal_high_f": 89, "normal_low_f": 63, "rh_typical_min": 24, "rh_extreme_min": 9, "rh_low_days_per_month": 2, "dp_typical_low_f": 50, "dp_extreme_low_f": 30, "gust_typical_max_kt": 35, "gust_extreme_kt": 55, "gust_sig_threshold_kt": 45},
            9: {"normal_high_f": 82, "normal_low_f": 55, "rh_typical_min": 20, "rh_extreme_min": 7, "rh_low_days_per_month": 3, "dp_typical_low_f": 38, "dp_extreme_low_f": 15, "gust_typical_max_kt": 38, "gust_extreme_kt": 58, "gust_sig_threshold_kt": 45},
            10: {"normal_high_f": 71, "normal_low_f": 43, "rh_typical_min": 18, "rh_extreme_min": 6, "rh_low_days_per_month": 4, "dp_typical_low_f": 25, "dp_extreme_low_f": 5, "gust_typical_max_kt": 40, "gust_extreme_kt": 60, "gust_sig_threshold_kt": 48},
            11: {"normal_high_f": 58, "normal_low_f": 31, "rh_typical_min": 22, "rh_extreme_min": 7, "rh_low_days_per_month": 4, "dp_typical_low_f": 18, "dp_extreme_low_f": -2, "gust_typical_max_kt": 38, "gust_extreme_kt": 58, "gust_sig_threshold_kt": 45},
            12: {"normal_high_f": 48, "normal_low_f": 23, "rh_typical_min": 25, "rh_extreme_min": 8, "rh_low_days_per_month": 3, "dp_typical_low_f": 14, "dp_extreme_low_f": -8, "gust_typical_max_kt": 35, "gust_extreme_kt": 56, "gust_sig_threshold_kt": 45},
        },
    },
    "KLBB": {
        "name": "Lubbock, TX (Preston Smith Intl)",
        "elevation_ft": 3254,
        "region": "Texas South Plains",
        "months": {
            1: {"normal_high_f": 53, "normal_low_f": 26, "rh_typical_min": 22, "rh_extreme_min": 7, "rh_low_days_per_month": 3, "dp_typical_low_f": 16, "dp_extreme_low_f": -5, "gust_typical_max_kt": 35, "gust_extreme_kt": 55, "gust_sig_threshold_kt": 42},
            2: {"normal_high_f": 57, "normal_low_f": 29, "rh_typical_min": 18, "rh_extreme_min": 6, "rh_low_days_per_month": 5, "dp_typical_low_f": 16, "dp_extreme_low_f": -3, "gust_typical_max_kt": 38, "gust_extreme_kt": 60, "gust_sig_threshold_kt": 45},
            3: {"normal_high_f": 66, "normal_low_f": 36, "rh_typical_min": 13, "rh_extreme_min": 4, "rh_low_days_per_month": 8, "dp_typical_low_f": 16, "dp_extreme_low_f": 0, "gust_typical_max_kt": 42, "gust_extreme_kt": 65, "gust_sig_threshold_kt": 48},
            4: {"normal_high_f": 75, "normal_low_f": 44, "rh_typical_min": 10, "rh_extreme_min": 3, "rh_low_days_per_month": 10, "dp_typical_low_f": 20, "dp_extreme_low_f": 2, "gust_typical_max_kt": 45, "gust_extreme_kt": 68, "gust_sig_threshold_kt": 50},
            5: {"normal_high_f": 83, "normal_low_f": 54, "rh_typical_min": 12, "rh_extreme_min": 4, "rh_low_days_per_month": 6, "dp_typical_low_f": 32, "dp_extreme_low_f": 12, "gust_typical_max_kt": 42, "gust_extreme_kt": 62, "gust_sig_threshold_kt": 48},
            6: {"normal_high_f": 91, "normal_low_f": 63, "rh_typical_min": 15, "rh_extreme_min": 5, "rh_low_days_per_month": 4, "dp_typical_low_f": 45, "dp_extreme_low_f": 22, "gust_typical_max_kt": 40, "gust_extreme_kt": 60, "gust_sig_threshold_kt": 48},
            7: {"normal_high_f": 92, "normal_low_f": 66, "rh_typical_min": 20, "rh_extreme_min": 7, "rh_low_days_per_month": 2, "dp_typical_low_f": 52, "dp_extreme_low_f": 32, "gust_typical_max_kt": 38, "gust_extreme_kt": 56, "gust_sig_threshold_kt": 45},
            8: {"normal_high_f": 91, "normal_low_f": 65, "rh_typical_min": 22, "rh_extreme_min": 8, "rh_low_days_per_month": 2, "dp_typical_low_f": 52, "dp_extreme_low_f": 32, "gust_typical_max_kt": 35, "gust_extreme_kt": 52, "gust_sig_threshold_kt": 42},
            9: {"normal_high_f": 84, "normal_low_f": 57, "rh_typical_min": 18, "rh_extreme_min": 6, "rh_low_days_per_month": 3, "dp_typical_low_f": 40, "dp_extreme_low_f": 18, "gust_typical_max_kt": 38, "gust_extreme_kt": 56, "gust_sig_threshold_kt": 45},
            10: {"normal_high_f": 74, "normal_low_f": 46, "rh_typical_min": 16, "rh_extreme_min": 5, "rh_low_days_per_month": 4, "dp_typical_low_f": 28, "dp_extreme_low_f": 8, "gust_typical_max_kt": 40, "gust_extreme_kt": 58, "gust_sig_threshold_kt": 46},
            11: {"normal_high_f": 62, "normal_low_f": 34, "rh_typical_min": 20, "rh_extreme_min": 6, "rh_low_days_per_month": 4, "dp_typical_low_f": 20, "dp_extreme_low_f": 0, "gust_typical_max_kt": 38, "gust_extreme_kt": 56, "gust_sig_threshold_kt": 45},
            12: {"normal_high_f": 52, "normal_low_f": 26, "rh_typical_min": 24, "rh_extreme_min": 8, "rh_low_days_per_month": 3, "dp_typical_low_f": 16, "dp_extreme_low_f": -5, "gust_typical_max_kt": 35, "gust_extreme_kt": 54, "gust_sig_threshold_kt": 42},
        },
    },
    "KOKC": {
        "name": "Oklahoma City, OK (Will Rogers World)",
        "elevation_ft": 1295,
        "region": "Central Oklahoma",
        "months": {
            1: {"normal_high_f": 49, "normal_low_f": 28, "rh_typical_min": 30, "rh_extreme_min": 12, "rh_low_days_per_month": 2, "dp_typical_low_f": 20, "dp_extreme_low_f": -5, "gust_typical_max_kt": 35, "gust_extreme_kt": 52, "gust_sig_threshold_kt": 40},
            2: {"normal_high_f": 53, "normal_low_f": 31, "rh_typical_min": 25, "rh_extreme_min": 10, "rh_low_days_per_month": 3, "dp_typical_low_f": 20, "dp_extreme_low_f": -2, "gust_typical_max_kt": 38, "gust_extreme_kt": 56, "gust_sig_threshold_kt": 42},
            3: {"normal_high_f": 63, "normal_low_f": 39, "rh_typical_min": 20, "rh_extreme_min": 8, "rh_low_days_per_month": 4, "dp_typical_low_f": 22, "dp_extreme_low_f": 0, "gust_typical_max_kt": 42, "gust_extreme_kt": 62, "gust_sig_threshold_kt": 48},
            4: {"normal_high_f": 72, "normal_low_f": 48, "rh_typical_min": 18, "rh_extreme_min": 6, "rh_low_days_per_month": 4, "dp_typical_low_f": 28, "dp_extreme_low_f": 8, "gust_typical_max_kt": 42, "gust_extreme_kt": 65, "gust_sig_threshold_kt": 48},
            5: {"normal_high_f": 80, "normal_low_f": 58, "rh_typical_min": 25, "rh_extreme_min": 10, "rh_low_days_per_month": 2, "dp_typical_low_f": 42, "dp_extreme_low_f": 20, "gust_typical_max_kt": 40, "gust_extreme_kt": 60, "gust_sig_threshold_kt": 48},
            6: {"normal_high_f": 88, "normal_low_f": 67, "rh_typical_min": 30, "rh_extreme_min": 12, "rh_low_days_per_month": 1, "dp_typical_low_f": 55, "dp_extreme_low_f": 35, "gust_typical_max_kt": 38, "gust_extreme_kt": 58, "gust_sig_threshold_kt": 45},
            7: {"normal_high_f": 93, "normal_low_f": 71, "rh_typical_min": 28, "rh_extreme_min": 10, "rh_low_days_per_month": 1, "dp_typical_low_f": 58, "dp_extreme_low_f": 38, "gust_typical_max_kt": 35, "gust_extreme_kt": 55, "gust_sig_threshold_kt": 42},
            8: {"normal_high_f": 93, "normal_low_f": 70, "rh_typical_min": 28, "rh_extreme_min": 10, "rh_low_days_per_month": 1, "dp_typical_low_f": 56, "dp_extreme_low_f": 36, "gust_typical_max_kt": 32, "gust_extreme_kt": 50, "gust_sig_threshold_kt": 40},
            9: {"normal_high_f": 84, "normal_low_f": 61, "rh_typical_min": 25, "rh_extreme_min": 8, "rh_low_days_per_month": 2, "dp_typical_low_f": 45, "dp_extreme_low_f": 20, "gust_typical_max_kt": 35, "gust_extreme_kt": 55, "gust_sig_threshold_kt": 42},
            10: {"normal_high_f": 73, "normal_low_f": 49, "rh_typical_min": 22, "rh_extreme_min": 8, "rh_low_days_per_month": 3, "dp_typical_low_f": 32, "dp_extreme_low_f": 10, "gust_typical_max_kt": 38, "gust_extreme_kt": 58, "gust_sig_threshold_kt": 45},
            11: {"normal_high_f": 60, "normal_low_f": 37, "rh_typical_min": 28, "rh_extreme_min": 10, "rh_low_days_per_month": 2, "dp_typical_low_f": 25, "dp_extreme_low_f": 2, "gust_typical_max_kt": 36, "gust_extreme_kt": 55, "gust_sig_threshold_kt": 42},
            12: {"normal_high_f": 49, "normal_low_f": 28, "rh_typical_min": 30, "rh_extreme_min": 12, "rh_low_days_per_month": 2, "dp_typical_low_f": 20, "dp_extreme_low_f": -5, "gust_typical_max_kt": 35, "gust_extreme_kt": 52, "gust_sig_threshold_kt": 40},
        },
    },
    "KDEN": {
        "name": "Denver, CO (Denver Intl)",
        "elevation_ft": 5431,
        "region": "Colorado Front Range",
        "months": {
            1: {"normal_high_f": 45, "normal_low_f": 16, "rh_typical_min": 25, "rh_extreme_min": 8, "rh_low_days_per_month": 4, "dp_typical_low_f": 5, "dp_extreme_low_f": -15, "gust_typical_max_kt": 38, "gust_extreme_kt": 62, "gust_sig_threshold_kt": 48},
            2: {"normal_high_f": 46, "normal_low_f": 18, "rh_typical_min": 22, "rh_extreme_min": 7, "rh_low_days_per_month": 5, "dp_typical_low_f": 6, "dp_extreme_low_f": -12, "gust_typical_max_kt": 40, "gust_extreme_kt": 65, "gust_sig_threshold_kt": 48},
            3: {"normal_high_f": 54, "normal_low_f": 25, "rh_typical_min": 18, "rh_extreme_min": 5, "rh_low_days_per_month": 6, "dp_typical_low_f": 8, "dp_extreme_low_f": -10, "gust_typical_max_kt": 42, "gust_extreme_kt": 68, "gust_sig_threshold_kt": 50},
            4: {"normal_high_f": 61, "normal_low_f": 33, "rh_typical_min": 15, "rh_extreme_min": 4, "rh_low_days_per_month": 7, "dp_typical_low_f": 14, "dp_extreme_low_f": -5, "gust_typical_max_kt": 45, "gust_extreme_kt": 72, "gust_sig_threshold_kt": 52},
            5: {"normal_high_f": 71, "normal_low_f": 43, "rh_typical_min": 18, "rh_extreme_min": 5, "rh_low_days_per_month": 4, "dp_typical_low_f": 25, "dp_extreme_low_f": 5, "gust_typical_max_kt": 42, "gust_extreme_kt": 65, "gust_sig_threshold_kt": 50},
            6: {"normal_high_f": 83, "normal_low_f": 52, "rh_typical_min": 16, "rh_extreme_min": 5, "rh_low_days_per_month": 4, "dp_typical_low_f": 32, "dp_extreme_low_f": 12, "gust_typical_max_kt": 40, "gust_extreme_kt": 62, "gust_sig_threshold_kt": 48},
            7: {"normal_high_f": 90, "normal_low_f": 58, "rh_typical_min": 18, "rh_extreme_min": 6, "rh_low_days_per_month": 3, "dp_typical_low_f": 40, "dp_extreme_low_f": 22, "gust_typical_max_kt": 38, "gust_extreme_kt": 58, "gust_sig_threshold_kt": 45},
            8: {"normal_high_f": 88, "normal_low_f": 57, "rh_typical_min": 20, "rh_extreme_min": 7, "rh_low_days_per_month": 2, "dp_typical_low_f": 40, "dp_extreme_low_f": 22, "gust_typical_max_kt": 35, "gust_extreme_kt": 55, "gust_sig_threshold_kt": 42},
            9: {"normal_high_f": 80, "normal_low_f": 47, "rh_typical_min": 16, "rh_extreme_min": 5, "rh_low_days_per_month": 4, "dp_typical_low_f": 30, "dp_extreme_low_f": 8, "gust_typical_max_kt": 38, "gust_extreme_kt": 60, "gust_sig_threshold_kt": 45},
            10: {"normal_high_f": 65, "normal_low_f": 35, "rh_typical_min": 18, "rh_extreme_min": 5, "rh_low_days_per_month": 5, "dp_typical_low_f": 18, "dp_extreme_low_f": -2, "gust_typical_max_kt": 42, "gust_extreme_kt": 65, "gust_sig_threshold_kt": 48},
            11: {"normal_high_f": 52, "normal_low_f": 24, "rh_typical_min": 22, "rh_extreme_min": 7, "rh_low_days_per_month": 4, "dp_typical_low_f": 10, "dp_extreme_low_f": -10, "gust_typical_max_kt": 40, "gust_extreme_kt": 65, "gust_sig_threshold_kt": 48},
            12: {"normal_high_f": 43, "normal_low_f": 16, "rh_typical_min": 28, "rh_extreme_min": 10, "rh_low_days_per_month": 3, "dp_typical_low_f": 5, "dp_extreme_low_f": -15, "gust_typical_max_kt": 38, "gust_extreme_kt": 62, "gust_sig_threshold_kt": 48},
        },
    },
    "KCOS": {
        "name": "Colorado Springs, CO (City of COS)",
        "elevation_ft": 6187,
        "region": "Colorado Front Range (southern)",
        "months": {
            1: {"normal_high_f": 43, "normal_low_f": 16, "rh_typical_min": 22, "rh_extreme_min": 6, "rh_low_days_per_month": 5, "dp_typical_low_f": 2, "dp_extreme_low_f": -18, "gust_typical_max_kt": 42, "gust_extreme_kt": 70, "gust_sig_threshold_kt": 50},
            2: {"normal_high_f": 44, "normal_low_f": 18, "rh_typical_min": 18, "rh_extreme_min": 5, "rh_low_days_per_month": 6, "dp_typical_low_f": 3, "dp_extreme_low_f": -15, "gust_typical_max_kt": 45, "gust_extreme_kt": 72, "gust_sig_threshold_kt": 52},
            3: {"normal_high_f": 52, "normal_low_f": 24, "rh_typical_min": 14, "rh_extreme_min": 3, "rh_low_days_per_month": 8, "dp_typical_low_f": 5, "dp_extreme_low_f": -12, "gust_typical_max_kt": 48, "gust_extreme_kt": 78, "gust_sig_threshold_kt": 55},
            4: {"normal_high_f": 59, "normal_low_f": 32, "rh_typical_min": 12, "rh_extreme_min": 3, "rh_low_days_per_month": 10, "dp_typical_low_f": 10, "dp_extreme_low_f": -8, "gust_typical_max_kt": 50, "gust_extreme_kt": 80, "gust_sig_threshold_kt": 58},
            5: {"normal_high_f": 68, "normal_low_f": 41, "rh_typical_min": 15, "rh_extreme_min": 4, "rh_low_days_per_month": 5, "dp_typical_low_f": 22, "dp_extreme_low_f": 2, "gust_typical_max_kt": 45, "gust_extreme_kt": 68, "gust_sig_threshold_kt": 52},
            6: {"normal_high_f": 80, "normal_low_f": 50, "rh_typical_min": 14, "rh_extreme_min": 4, "rh_low_days_per_month": 5, "dp_typical_low_f": 30, "dp_extreme_low_f": 10, "gust_typical_max_kt": 42, "gust_extreme_kt": 65, "gust_sig_threshold_kt": 50},
            7: {"normal_high_f": 85, "normal_low_f": 56, "rh_typical_min": 18, "rh_extreme_min": 6, "rh_low_days_per_month": 3, "dp_typical_low_f": 38, "dp_extreme_low_f": 18, "gust_typical_max_kt": 40, "gust_extreme_kt": 60, "gust_sig_threshold_kt": 48},
            8: {"normal_high_f": 83, "normal_low_f": 55, "rh_typical_min": 20, "rh_extreme_min": 7, "rh_low_days_per_month": 2, "dp_typical_low_f": 38, "dp_extreme_low_f": 18, "gust_typical_max_kt": 38, "gust_extreme_kt": 58, "gust_sig_threshold_kt": 45},
            9: {"normal_high_f": 76, "normal_low_f": 46, "rh_typical_min": 15, "rh_extreme_min": 4, "rh_low_days_per_month": 5, "dp_typical_low_f": 26, "dp_extreme_low_f": 5, "gust_typical_max_kt": 40, "gust_extreme_kt": 62, "gust_sig_threshold_kt": 48},
            10: {"normal_high_f": 63, "normal_low_f": 34, "rh_typical_min": 16, "rh_extreme_min": 4, "rh_low_days_per_month": 6, "dp_typical_low_f": 15, "dp_extreme_low_f": -5, "gust_typical_max_kt": 45, "gust_extreme_kt": 70, "gust_sig_threshold_kt": 52},
            11: {"normal_high_f": 50, "normal_low_f": 23, "rh_typical_min": 20, "rh_extreme_min": 6, "rh_low_days_per_month": 5, "dp_typical_low_f": 8, "dp_extreme_low_f": -12, "gust_typical_max_kt": 42, "gust_extreme_kt": 68, "gust_sig_threshold_kt": 50},
            12: {"normal_high_f": 42, "normal_low_f": 15, "rh_typical_min": 24, "rh_extreme_min": 8, "rh_low_days_per_month": 4, "dp_typical_low_f": 2, "dp_extreme_low_f": -18, "gust_typical_max_kt": 40, "gust_extreme_kt": 65, "gust_sig_threshold_kt": 48},
        },
    },
}

# ---------------------------------------------------------------------------
# Merge regional climatology from data/ directory
# ---------------------------------------------------------------------------
def _merge_regional_climatology():
    """Load and merge compatible regional climatology into _STATION_CLIMATOLOGY.

    Only merges entries that have the standard format:
    {name, elevation_ft, region, months: {1: {...}, ...}}
    """
    _regional_modules = [
        ("agent_tools.data.pnw_rockies_profiles", "PNW_CLIMATOLOGY"),
        ("agent_tools.data.colorado_basin_profiles", "CO_BASIN_CLIMATOLOGY"),
        ("agent_tools.data.california_profiles", "CA_CLIMATOLOGY"),
        ("agent_tools.data.southwest_profiles", "SW_CLIMATOLOGY"),
        ("agent_tools.data.southern_plains_profiles", "PLAINS_CLIMATOLOGY"),
        ("agent_tools.data.southeast_misc_profiles", "SE_MISC_CLIMATOLOGY"),
    ]
    count = 0
    for mod_name, attr_name in _regional_modules:
        try:
            mod = __import__(mod_name, fromlist=[attr_name])
            clim = getattr(mod, attr_name, {})
            for key, val in clim.items():
                if key in _STATION_CLIMATOLOGY:
                    continue
                # Only merge entries with standard station format
                if isinstance(val, dict) and "months" in val and "name" in val:
                    _STATION_CLIMATOLOGY[key] = val
                    count += 1
                elif isinstance(val, dict) and "_station_info" in val:
                    # CA format: convert {_station_info, 1: {}, 2: {}, ...}
                    info = val["_station_info"]
                    months = {k: v for k, v in val.items() if isinstance(k, int)}
                    if months:
                        _STATION_CLIMATOLOGY[key] = {
                            "name": info.get("name", key),
                            "elevation_ft": info.get("elevation_ft", 0),
                            "region": info.get("region", "Unknown"),
                            "months": months,
                        }
                        count += 1
        except ImportError:
            pass
    return count

_merge_regional_climatology()


def get_fire_weather_climatology(
    station_id: str,
    month: Optional[int] = None,
    current_temp_f: Optional[float] = None,
    current_rh_pct: Optional[float] = None,
    current_dewpoint_f: Optional[float] = None,
    current_gust_kt: Optional[float] = None,
) -> dict:
    """Get historical fire weather climatology context for a station.

    Provides what's "normal", "significant", and "extreme" for key fire
    weather parameters at a given station and month. This prevents reports
    from overclaiming severity — e.g., calling 9% RH "catastrophic" when
    it occurs 5+ days per winter in the Texas Panhandle.

    Uses hardcoded climatology for key stations (KAMA, KLBB, KOKC, KDEN,
    KCOS) based on historical records. For other stations, attempts to
    fetch from IEM daily climate API and falls back to regional estimates.

    Args:
        station_id: ICAO station ID (e.g., "KAMA", "KOKC"). K-prefix required.
        month: Month number (1-12). Default: current month.
        current_temp_f: Current temperature in F (for anomaly calculation).
        current_rh_pct: Current RH (for severity context).
        current_dewpoint_f: Current dewpoint in F (for severity context).
        current_gust_kt: Current peak gust in kt (for severity context).

    Returns:
        Dict with climatology data and plain-English fire weather context.
    """
    if month is None:
        month = datetime.utcnow().month

    sid = station_id.upper().strip()
    month_names = {
        1: "January", 2: "February", 3: "March", 4: "April",
        5: "May", 6: "June", 7: "July", 8: "August",
        9: "September", 10: "October", 11: "November", 12: "December",
    }
    month_name = month_names.get(month, f"Month {month}")

    # Check hardcoded climatology first
    climo = _STATION_CLIMATOLOGY.get(sid)
    if climo:
        return _build_climatology_response(
            sid, climo, month, month_name,
            current_temp_f, current_rh_pct, current_dewpoint_f, current_gust_kt,
        )

    # Try to fetch from IEM for unknown stations
    try:
        iem_climo = _fetch_iem_climatology(sid, month)
        if iem_climo:
            return iem_climo
    except Exception:
        pass

    # Fallback: return a generic response indicating no data
    return {
        "station": sid,
        "month": month_name,
        "error": (
            f"No climatology data available for {sid}. "
            f"Hardcoded data exists for: {', '.join(sorted(_STATION_CLIMATOLOGY.keys()))}. "
            "Try one of those stations or provide a nearby ASOS station ID."
        ),
        "available_stations": sorted(_STATION_CLIMATOLOGY.keys()),
    }


def _build_climatology_response(
    station_id: str, climo: dict, month: int, month_name: str,
    current_temp_f: Optional[float],
    current_rh_pct: Optional[float],
    current_dewpoint_f: Optional[float],
    current_gust_kt: Optional[float],
) -> dict:
    """Build a detailed climatology response from hardcoded data."""
    m = climo["months"].get(month, {})
    if not m:
        return {"error": f"No data for month {month} at {station_id}"}

    region = climo.get("region", "")

    # Build RH context
    rh_context_parts = []
    if current_rh_pct is not None:
        if current_rh_pct <= m["rh_extreme_min"]:
            rh_context_parts.append(
                f"{current_rh_pct}% RH is at or below the extreme minimum "
                f"({m['rh_extreme_min']}%) for {month_name} — this is a rare, "
                "exceptionally dry event."
            )
        elif current_rh_pct <= m["rh_typical_min"]:
            rh_context_parts.append(
                f"{current_rh_pct}% RH is below the typical minimum "
                f"({m['rh_typical_min']}%) for {month_name} but above the "
                f"extreme ({m['rh_extreme_min']}%). This is low but occurs "
                f"roughly {m['rh_low_days_per_month']} days per {month_name}."
            )
        else:
            rh_context_parts.append(
                f"{current_rh_pct}% RH is within normal range for {month_name} "
                f"(typical min ~{m['rh_typical_min']}%). Not exceptional."
            )
    rh_context_parts.append(
        f"Truly extreme for {region} in {month_name}: RH below {m['rh_extreme_min']}%. "
        f"That's when fuels cannot absorb any moisture at all."
    )

    # Build dewpoint context
    dp_context_parts = []
    if current_dewpoint_f is not None:
        if current_dewpoint_f <= m["dp_extreme_low_f"]:
            dp_context_parts.append(
                f"{current_dewpoint_f}F dewpoint is at or below the extreme low "
                f"({m['dp_extreme_low_f']}F) for {month_name} — truly extreme dry air."
            )
        elif current_dewpoint_f <= m["dp_typical_low_f"]:
            dp_context_parts.append(
                f"{current_dewpoint_f}F dewpoint is between the typical low "
                f"({m['dp_typical_low_f']}F) and extreme low ({m['dp_extreme_low_f']}F) "
                f"for {month_name}. Dry but not unprecedented."
            )
        else:
            dp_context_parts.append(
                f"{current_dewpoint_f}F dewpoint is common or even moist for "
                f"{month_name} (typical low ~{m['dp_typical_low_f']}F)."
            )
    dp_context_parts.append(
        f"Truly extreme for {region} in {month_name}: dewpoints at or below "
        f"{m['dp_extreme_low_f']}F. That indicates an extremely dry continental air mass."
    )

    # Build wind context
    wind_context_parts = []
    if current_gust_kt is not None:
        if current_gust_kt >= m["gust_extreme_kt"]:
            wind_context_parts.append(
                f"{current_gust_kt} kt gusts EXCEED the extreme threshold "
                f"({m['gust_extreme_kt']} kt) for {month_name} — this is a "
                "rare, high-impact wind event."
            )
        elif current_gust_kt >= m["gust_sig_threshold_kt"]:
            wind_context_parts.append(
                f"{current_gust_kt} kt gusts are above the significant threshold "
                f"({m['gust_sig_threshold_kt']} kt) for {month_name}. "
                "This is a notably windy day but not record-breaking."
            )
        elif current_gust_kt >= m["gust_typical_max_kt"]:
            wind_context_parts.append(
                f"{current_gust_kt} kt gusts are near the typical maximum "
                f"({m['gust_typical_max_kt']} kt) for {month_name}. "
                "A standard windy day for this area."
            )
        else:
            wind_context_parts.append(
                f"{current_gust_kt} kt gusts are below the typical monthly max "
                f"({m['gust_typical_max_kt']} kt) for {month_name}. Not unusual at all."
            )
    wind_context_parts.append(
        f"Typical max gust in {month_name}: ~{m['gust_typical_max_kt']} kt "
        f"({round(m['gust_typical_max_kt'] * 1.15078)} mph). "
        f"Significant: >{m['gust_sig_threshold_kt']} kt "
        f"({round(m['gust_sig_threshold_kt'] * 1.15078)} mph). "
        f"Extreme/rare: >{m['gust_extreme_kt']} kt "
        f"({round(m['gust_extreme_kt'] * 1.15078)} mph)."
    )

    # Build temperature anomaly context
    temp_context = None
    if current_temp_f is not None:
        anomaly = current_temp_f - m["normal_high_f"]
        if abs(anomaly) >= 20:
            severity = "extreme"
        elif abs(anomaly) >= 10:
            severity = "significant"
        else:
            severity = "minor"

        direction = "above" if anomaly > 0 else "below"
        temp_context = {
            "current_f": current_temp_f,
            "normal_high_f": m["normal_high_f"],
            "normal_low_f": m["normal_low_f"],
            "anomaly_f": round(anomaly, 1),
            "context": (
                f"{current_temp_f}F is {abs(anomaly):.0f}F {direction} the {month_name} "
                f"normal high of {m['normal_high_f']}F — a {severity} anomaly. "
                + (
                    "Persistent warmth accelerates fuel drying, especially for dormant winter vegetation."
                    if anomaly > 10 else
                    "Cooler-than-normal temps slow fuel drying and may indicate recent precipitation."
                    if anomaly < -10 else
                    "Near-normal temperatures."
                )
            ),
        }

    # Build fire weather context narrative
    fire_context_parts = [
        f"For {climo['name']} in {month_name}:",
    ]
    if current_rh_pct is not None and current_gust_kt is not None and current_temp_f is not None:
        # Classify overall severity
        extreme_count = 0
        if current_rh_pct <= m["rh_extreme_min"]:
            extreme_count += 1
        if current_gust_kt >= m["gust_extreme_kt"]:
            extreme_count += 1
        if current_temp_f - m["normal_high_f"] >= 20:
            extreme_count += 1

        sig_count = 0
        if current_rh_pct <= m["rh_typical_min"]:
            sig_count += 1
        if current_gust_kt >= m["gust_sig_threshold_kt"]:
            sig_count += 1
        if current_temp_f - m["normal_high_f"] >= 10:
            sig_count += 1

        if extreme_count >= 2:
            fire_context_parts.append(
                "Current conditions represent an EXTREME fire weather day — "
                "multiple parameters are at or beyond historical extremes. "
                "This is a high-impact event."
            )
        elif extreme_count == 1 or sig_count >= 2:
            fire_context_parts.append(
                "Current conditions represent an ELEVATED but not unprecedented "
                "fire weather day. One or more parameters are significant but "
                "this is not the worst-case scenario for this location."
            )
        elif sig_count == 1:
            fire_context_parts.append(
                "Current conditions are NOTABLE but within the range of "
                "typical fire weather days for this location and season."
            )
        else:
            fire_context_parts.append(
                "Current conditions are within normal range for this location "
                "and season. Fire risk exists but is not climatologically unusual."
            )

    fire_context_parts.append(
        f"An extreme fire weather day for {region} in {month_name} would feature: "
        f"RH <{m['rh_extreme_min']}%, sustained winds >{m['gust_sig_threshold_kt']} kt "
        f"with gusts >{m['gust_extreme_kt']} kt, temps >{m['normal_high_f'] + 20}F, "
        "and no overnight RH recovery above 25%."
    )

    return {
        "station": station_id,
        "name": climo["name"],
        "elevation_ft": climo.get("elevation_ft"),
        "region": region,
        "month": month_name,
        "climatology": {
            "normal_high_f": m["normal_high_f"],
            "normal_low_f": m["normal_low_f"],
            "rh": {
                "typical_min_pct": m["rh_typical_min"],
                "extreme_min_pct": m["rh_extreme_min"],
                "low_rh_days_per_month": m["rh_low_days_per_month"],
                "context": " ".join(rh_context_parts),
            },
            "dewpoint": {
                "typical_low_f": m["dp_typical_low_f"],
                "extreme_low_f": m["dp_extreme_low_f"],
                "context": " ".join(dp_context_parts),
            },
            "wind": {
                "typical_max_gust_kt": m["gust_typical_max_kt"],
                "significant_gust_kt": m["gust_sig_threshold_kt"],
                "extreme_gust_kt": m["gust_extreme_kt"],
                "context": " ".join(wind_context_parts),
            },
            "temperature_anomaly": temp_context,
        },
        "fire_weather_context": " ".join(fire_context_parts),
    }


def _fetch_iem_climatology(station_id: str, month: int) -> Optional[dict]:
    """Attempt to fetch basic climatology from IEM daily climate API.

    This is a best-effort fallback for stations not in our hardcoded list.
    Returns None if the API doesn't return useful data.
    """
    sid = _station_id_to_iem(station_id)
    states = _guess_nearby_states(0, 0)  # placeholder; we try all networks

    # Try IEM climate API for recent years to compute basic stats
    # https://mesonet.agron.iastate.edu/api/1/daily.json
    now = datetime.utcnow()
    # Fetch 5 years of the target month
    years_data = []
    for year in range(now.year - 5, now.year + 1):
        url = (
            f"https://mesonet.agron.iastate.edu/api/1/daily.json?"
            f"station={sid}&year1={year}&month1={month}&day1=1"
            f"&year2={year}&month2={month}&day2=28"
        )
        # We need to guess the network
        for state in _guess_nearby_states(35, -100):  # rough center of CONUS
            net_url = url + f"&network={state}_ASOS"
            try:
                data = _fetch_json(net_url, timeout=10)
                rows = data.get("data", [])
                if rows:
                    years_data.extend(rows)
                    break
            except Exception:
                continue

    if not years_data:
        return None

    # Compute basic stats
    highs = [r["max_tmpf"] for r in years_data if r.get("max_tmpf") is not None]
    lows = [r["min_tmpf"] for r in years_data if r.get("min_tmpf") is not None]
    gusts = [r["max_gust"] for r in years_data if r.get("max_gust") is not None and r["max_gust"] > 0]

    if not highs:
        return None

    month_names = {
        1: "January", 2: "February", 3: "March", 4: "April",
        5: "May", 6: "June", 7: "July", 8: "August",
        9: "September", 10: "October", 11: "November", 12: "December",
    }

    avg_high = sum(highs) / len(highs)
    avg_low = sum(lows) / len(lows) if lows else None
    avg_gust = sum(gusts) / len(gusts) if gusts else None
    max_gust = max(gusts) if gusts else None

    return {
        "station": station_id,
        "month": month_names.get(month, f"Month {month}"),
        "source": "iem_daily_api",
        "note": "Based on limited recent data (5 years). Use hardcoded stations for more reliable climatology.",
        "climatology": {
            "normal_high_f": round(avg_high, 1),
            "normal_low_f": round(avg_low, 1) if avg_low else None,
            "wind": {
                "avg_max_gust_kt": round(avg_gust, 1) if avg_gust else None,
                "max_gust_kt": round(max_gust, 1) if max_gust else None,
                "context": (
                    f"Based on {len(gusts)} days of data. "
                    "Use a hardcoded station for detailed fire weather context."
                ) if gusts else "No gust data available.",
            },
        },
        "available_hardcoded_stations": sorted(_STATION_CLIMATOLOGY.keys()),
    }


# =============================================================================
# RH / Dewpoint Severity Assessment
# =============================================================================

def assess_rh_dewpoint_severity(
    rh_pct: float,
    dewpoint_f: float,
    station_id: Optional[str] = None,
    month: Optional[int] = None,
) -> dict:
    """Quick assessment of RH and dewpoint severity in regional context.

    Returns a calibrated severity level and plain-English explanation of
    how the current conditions compare to what's normal and what would
    actually be extreme for the area. Prevents overclaiming — e.g.,
    calling 9% RH "catastrophic" when it's a 5-10 day/winter event.

    Args:
        rh_pct: Current relative humidity in percent.
        dewpoint_f: Current dewpoint in degrees Fahrenheit.
        station_id: Optional ICAO station ID for location-specific context.
            If provided, uses that station's climatology. Otherwise uses
            generic Great Plains thresholds.
        month: Month number (1-12). Default: current month.

    Returns:
        Dict with severity level, context, and what-would-be-worse guidance.
    """
    if month is None:
        month = datetime.utcnow().month

    # Try to get station-specific thresholds
    climo_data = None
    if station_id:
        sid = station_id.upper().strip()
        climo = _STATION_CLIMATOLOGY.get(sid)
        if climo:
            climo_data = climo["months"].get(month, {})

    # Fall back to generic Great Plains thresholds
    if climo_data is None:
        climo_data = {
            "rh_typical_min": 18,
            "rh_extreme_min": 6,
            "dp_typical_low_f": 16,
            "dp_extreme_low_f": -5,
        }
        region = "Great Plains (generic)"
    else:
        region = _STATION_CLIMATOLOGY.get(
            station_id.upper().strip(), {}
        ).get("region", "this region")

    rh_typ = climo_data["rh_typical_min"]
    rh_ext = climo_data["rh_extreme_min"]
    dp_typ = climo_data["dp_typical_low_f"]
    dp_ext = climo_data["dp_extreme_low_f"]

    # Classify severity
    rh_score = 0  # 0=normal, 1=elevated, 2=significant, 3=extreme
    if rh_pct <= rh_ext:
        rh_score = 3
    elif rh_pct <= rh_ext + (rh_typ - rh_ext) * 0.3:
        rh_score = 2
    elif rh_pct <= rh_typ:
        rh_score = 1

    dp_score = 0
    if dewpoint_f <= dp_ext:
        dp_score = 3
    elif dewpoint_f <= dp_ext + (dp_typ - dp_ext) * 0.3:
        dp_score = 2
    elif dewpoint_f <= dp_typ:
        dp_score = 1

    combined_score = max(rh_score, dp_score)
    severity_labels = {0: "normal", 1: "elevated", 2: "significant", 3: "extreme"}
    severity = severity_labels[combined_score]

    # Build context
    context_parts = []
    if rh_score == 0:
        context_parts.append(
            f"{rh_pct}% RH is within normal range for {region} "
            f"(typical minimum ~{rh_typ}%)."
        )
    elif rh_score == 1:
        context_parts.append(
            f"{rh_pct}% RH is below the typical minimum ({rh_typ}%) "
            f"but well above the extreme ({rh_ext}%). "
            f"Low but not rare for {region}."
        )
    elif rh_score == 2:
        context_parts.append(
            f"{rh_pct}% RH is significantly low, approaching the extreme "
            f"threshold ({rh_ext}%) for {region}. "
            "This supports rapid fire spread in receptive fuels."
        )
    else:
        context_parts.append(
            f"{rh_pct}% RH is at or below the extreme threshold ({rh_ext}%) "
            f"for {region}. This is genuinely extreme — fuels cannot absorb "
            "meaningful moisture at this humidity level."
        )

    if dp_score == 0:
        context_parts.append(
            f"{dewpoint_f}F dewpoint is normal or even moist for {region} "
            f"(typical low ~{dp_typ}F)."
        )
    elif dp_score == 1:
        context_parts.append(
            f"{dewpoint_f}F dewpoint is dry but not extreme for {region} "
            f"(typical low ~{dp_typ}F, extreme ~{dp_ext}F)."
        )
    elif dp_score == 2:
        context_parts.append(
            f"{dewpoint_f}F dewpoint is quite dry, approaching extreme levels "
            f"for {region} (extreme ~{dp_ext}F)."
        )
    else:
        context_parts.append(
            f"{dewpoint_f}F dewpoint is at or below the extreme threshold "
            f"({dp_ext}F) for {region} — an exceptionally dry air mass."
        )

    # What would be worse
    worse_rh = max(1, rh_ext - 3)
    worse_dp = dp_ext - 5
    what_worse = (
        f"Truly extreme: RH at {worse_rh}-{rh_ext}% with dewpoints at "
        f"{worse_dp}F to {dp_ext}F. That's when fuels become tinder-dry "
        "and fire behavior becomes erratic — even small ignitions can "
        "produce rapid, uncontrollable spread."
    )

    return {
        "rh_pct": rh_pct,
        "dewpoint_f": dewpoint_f,
        "severity": severity,
        "region": region,
        "station": station_id,
        "month": month,
        "context": " ".join(context_parts),
        "what_would_be_worse": what_worse,
        "thresholds": {
            "rh_typical_min_pct": rh_typ,
            "rh_extreme_min_pct": rh_ext,
            "dp_typical_low_f": dp_typ,
            "dp_extreme_low_f": dp_ext,
        },
    }
