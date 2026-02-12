"""
Location Investigation Tool for Fire Weather Agents

Instead of algorithmic risk scores, agents should deeply investigate specific
locations by combining multiple data sources. This module orchestrates that
investigation: it gathers real observations, model data, alerts, terrain,
drought status, and SPC outlooks for a given point, then returns everything
an agent needs to assess fire risk.

Usage:
    from tools.agent_tools.investigation import (
        investigate_location,
        investigate_town,
        batch_investigate,
        generate_investigation_report_text,
    )

    # Investigate by coordinates
    result = investigate_location(35.36, -97.18, name="Newalla, OK")

    # Investigate by town name
    result = investigate_town("newalla", "ok")

    # Batch investigate multiple locations
    results = batch_investigate([
        (35.36, -97.18, "Newalla"),
        (35.50, -97.27, "Choctaw"),
        (35.22, -97.44, "Norman"),
    ])

    # Generate a readable text report
    print(generate_investigation_report_text(result))
"""
import math
from datetime import datetime
from typing import Optional

from tools.agent_tools.external_data import (
    get_metar_observations,
    get_nearby_stations,
    get_nws_alerts,
    get_elevation,
    get_drought_status,
    get_spc_fire_weather_outlook,
)


# =============================================================================
# Town coordinate lookup table
# =============================================================================

TOWN_COORDS = {
    # Oklahoma
    ("newalla", "ok"): (35.36, -97.18),
    ("draper", "ok"): (35.36, -97.30),
    ("choctaw", "ok"): (35.50, -97.27),
    ("harrah", "ok"): (35.49, -97.16),
    ("norman", "ok"): (35.22, -97.44),
    ("moore", "ok"): (35.34, -97.49),
    ("edmond", "ok"): (35.65, -97.48),
    ("guthrie", "ok"): (35.88, -97.43),
    ("el reno", "ok"): (35.53, -97.95),
    ("yukon", "ok"): (35.51, -97.76),
    ("mustang", "ok"): (35.38, -97.72),
    ("oklahoma city", "ok"): (35.47, -97.52),
    # TX panhandle
    ("amarillo", "tx"): (35.22, -101.83),
    ("lubbock", "tx"): (33.58, -101.85),
    ("tucumcari", "nm"): (35.17, -103.73),
    # CO front range
    ("boulder", "co"): (40.01, -105.27),
    ("denver", "co"): (39.74, -104.99),
    ("colorado springs", "co"): (38.83, -104.82),
    # CA fire areas
    ("paradise", "ca"): (39.76, -121.62),
    ("malibu", "ca"): (34.03, -118.68),
    ("santa rosa", "ca"): (38.44, -122.71),
    # Oregon — Columbia Gorge / North Central
    ("hood river", "or"): (45.7054, -121.5215),
    ("the dalles", "or"): (45.5946, -121.1787),
    ("mosier", "or"): (45.6837, -121.3997),
    ("maupin", "or"): (45.1754, -121.0795),
    ("dufur", "or"): (45.4571, -121.1292),
    ("grass valley", "or"): (45.3054, -120.7534),
    # Oregon — Central Oregon Cascades
    ("bend", "or"): (44.0582, -121.3153),
    ("sisters", "or"): (44.2907, -121.5493),
    ("camp sherman", "or"): (44.4640, -121.6510),
    ("la pine", "or"): (43.6804, -121.5036),
    ("sunriver", "or"): (43.8840, -121.4350),
    ("redmond", "or"): (44.2726, -121.1739),
    # Oregon — Cascade Crest Corridor
    ("detroit", "or"): (44.7352, -122.1531),
    ("gates", "or"): (44.7502, -122.4069),
    ("blue river", "or"): (44.1626, -122.3398),
    ("oakridge", "or"): (43.7465, -122.4610),
    ("mckenzie bridge", "or"): (44.1826, -122.1260),
    ("vida", "or"): (44.1196, -122.5136),
    # Oregon — Southern Oregon / Rogue Valley
    ("medford", "or"): (42.3265, -122.8756),
    ("ashland", "or"): (42.1946, -122.7095),
    ("talent", "or"): (42.2457, -122.7878),
    ("phoenix", "or"): (42.2751, -122.8189),
    ("grants pass", "or"): (42.4390, -123.3284),
    ("jacksonville", "or"): (42.3134, -122.9668),
    # Oregon — Klamath Basin / High Desert
    ("klamath falls", "or"): (42.2249, -121.7817),
    ("lakeview", "or"): (42.1888, -120.3455),
    ("chiloquin", "or"): (42.5779, -121.8667),
    ("bonanza", "or"): (42.1962, -121.4077),
    ("bly", "or"): (42.3971, -120.9977),
    ("paisley", "or"): (42.6912, -120.5427),
    # Oregon — NE Oregon Blue Mountains
    ("pendleton", "or"): (45.6721, -118.7886),
    ("la grande", "or"): (45.3246, -118.0878),
    ("baker city", "or"): (44.7749, -117.8344),
    ("enterprise", "or"): (45.4268, -117.2788),
    ("joseph", "or"): (45.3543, -117.2296),
    ("john day", "or"): (44.4160, -118.9530),
    ("canyon city", "or"): (44.3907, -118.9498),
    ("prairie city", "or"): (44.4571, -118.7124),
    # Oregon — Coast Range / Willamette Valley Interface
    ("sweet home", "or"): (44.3968, -122.7351),
    ("roseburg", "or"): (43.2165, -123.3417),
    ("florence", "or"): (43.9826, -124.0998),
    ("cottage grove", "or"): (43.7976, -123.0595),
    ("drain", "or"): (43.6590, -123.3184),
    ("myrtle creek", "or"): (42.9957, -123.2917),
}

# State abbreviation to full name mapping for drought API
_STATE_ABBREVS = {
    "al": "AL", "ak": "AK", "az": "AZ", "ar": "AR", "ca": "CA",
    "co": "CO", "ct": "CT", "de": "DE", "fl": "FL", "ga": "GA",
    "hi": "HI", "id": "ID", "il": "IL", "in": "IN", "ia": "IA",
    "ks": "KS", "ky": "KY", "la": "LA", "me": "ME", "md": "MD",
    "ma": "MA", "mi": "MI", "mn": "MN", "ms": "MS", "mo": "MO",
    "mt": "MT", "ne": "NE", "nv": "NV", "nh": "NH", "nj": "NJ",
    "nm": "NM", "ny": "NY", "nc": "NC", "nd": "ND", "oh": "OH",
    "ok": "OK", "or": "OR", "pa": "PA", "ri": "RI", "sc": "SC",
    "sd": "SD", "tn": "TN", "tx": "TX", "ut": "UT", "vt": "VT",
    "va": "VA", "wa": "WA", "wv": "WV", "wi": "WI", "wy": "WY",
}


# =============================================================================
# Internal helpers
# =============================================================================

def _compute_rh(temp_f: float, dewpoint_f: float) -> Optional[float]:
    """Approximate RH from temperature and dewpoint (both in F).

    Uses the Magnus formula to compute saturation vapor pressures
    and derive relative humidity as a percentage.
    """
    if temp_f is None or dewpoint_f is None:
        return None
    try:
        t_c = (temp_f - 32) * 5 / 9
        td_c = (dewpoint_f - 32) * 5 / 9
        # Magnus coefficients
        a, b = 17.27, 237.7
        e_td = math.exp((a * td_c) / (b + td_c))
        e_t = math.exp((a * t_c) / (b + t_c))
        rh = 100 * (e_td / e_t)
        return round(max(0, min(100, rh)), 1)
    except (ValueError, ZeroDivisionError):
        return None


def _extract_latest_observation(metar_data: dict) -> Optional[dict]:
    """Pull the most recent observation from a METAR API response.

    The IEM ASOS API returns a list of observations under the "data" key.
    We grab the last entry (most recent) and extract the fields we care about.

    Returns None if no usable data is found.
    """
    data_list = metar_data.get("data", [])
    if not data_list:
        return None

    # Take the most recent observation
    obs = data_list[-1]

    temp_f = obs.get("tmpf")
    dwpf = obs.get("dwpf")

    # Parse numeric fields, guarding against None / non-numeric
    def _num(val):
        if val is None:
            return None
        try:
            return float(val)
        except (ValueError, TypeError):
            return None

    temp_f = _num(temp_f)
    dwpf = _num(dwpf)
    wind_speed = _num(obs.get("sknt"))
    wind_gust = _num(obs.get("gust"))
    wind_dir = _num(obs.get("drct"))
    visibility = _num(obs.get("vsby"))

    rh = _compute_rh(temp_f, dwpf) if temp_f is not None and dwpf is not None else None

    return {
        "temperature_f": temp_f,
        "dewpoint_f": dwpf,
        "rh_pct": rh,
        "wind_dir": int(wind_dir) if wind_dir is not None else None,
        "wind_speed_kt": wind_speed,
        "wind_gust_kt": wind_gust,
        "visibility_sm": visibility,
        "raw_metar": obs.get("metar", ""),
        "observation_time": obs.get("valid", ""),
    }


def _guess_state_from_coords(lat: float, lon: float) -> Optional[str]:
    """Very rough state guess from lat/lon for CONUS.

    This is a coarse approximation used only as a fallback for the
    drought API when no explicit state is available. It uses simple
    bounding boxes and is not authoritative.
    """
    # Simple bounding-box heuristics for states we care about most
    regions = [
        ("OK", 33.6, 37.0, -103.0, -94.4),
        ("TX", 25.8, 36.5, -106.6, -93.5),
        ("NM", 31.3, 37.0, -109.1, -103.0),
        ("CO", 37.0, 41.0, -109.1, -102.0),
        ("CA", 32.5, 42.0, -124.5, -114.1),
        ("KS", 37.0, 40.0, -102.1, -94.6),
        ("NE", 40.0, 43.0, -104.1, -95.3),
        ("MT", 44.4, 49.0, -116.1, -104.0),
        ("ID", 42.0, 49.0, -117.2, -111.0),
        ("AZ", 31.3, 37.0, -114.8, -109.0),
        ("UT", 37.0, 42.0, -114.1, -109.0),
        ("WY", 41.0, 45.0, -111.1, -104.1),
        ("OR", 42.0, 46.3, -124.6, -116.5),
        ("WA", 45.5, 49.0, -124.8, -116.9),
        ("NV", 35.0, 42.0, -120.0, -114.0),
    ]
    for state, s, n, w, e in regions:
        if s <= lat <= n and w <= lon <= e:
            return state
    return None


def _check_point_in_outlook(lat: float, lon: float, outlook_data: dict) -> dict:
    """Check if a point falls within any SPC fire weather outlook polygon.

    Uses a simple ray-casting point-in-polygon test against the GeoJSON
    features returned by the SPC fire weather outlook endpoint.

    Returns a dict with risk_level and in_outlook_area.
    """
    result = {"risk_level": None, "in_outlook_area": False}

    features = outlook_data.get("features", [])
    if not features:
        return result

    for feature in features:
        props = feature.get("properties", {})
        geom = feature.get("geometry", {})
        geom_type = geom.get("type", "")

        # Determine the risk level from the properties
        # SPC uses various property keys; try common ones
        risk = (
            props.get("LABEL", "")
            or props.get("label", "")
            or props.get("RISK", "")
            or props.get("dn", "")
            or props.get("DN", "")
            or ""
        )

        # Get the coordinate rings
        if geom_type == "Polygon":
            rings = geom.get("coordinates", [])
        elif geom_type == "MultiPolygon":
            # Flatten to list of rings
            rings = []
            for poly in geom.get("coordinates", []):
                rings.extend(poly)
        else:
            continue

        for ring in rings:
            if _point_in_polygon(lat, lon, ring):
                result["risk_level"] = risk if risk else "OUTLINED"
                result["in_outlook_area"] = True
                return result  # Return on first match (highest priority)

    return result


def _point_in_polygon(lat: float, lon: float, ring: list) -> bool:
    """Ray-casting point-in-polygon test.

    ring is a list of [lon, lat] pairs (GeoJSON coordinate order).
    """
    n = len(ring)
    inside = False
    j = n - 1
    for i in range(n):
        xi, yi = ring[i][0], ring[i][1]  # lon, lat
        xj, yj = ring[j][0], ring[j][1]
        if ((yi > lat) != (yj > lat)) and (lon < (xj - xi) * (lat - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside


def _parse_drought_response(drought_data: dict) -> dict:
    """Parse the USDM drought API response into a concise summary.

    The USDM API returns a list of weekly records. We take the most recent
    and extract D0-D4 percentages and identify the dominant drought level.
    """
    result = {"level": None, "description": "No data", "detail": {}}

    if isinstance(drought_data, dict) and "error" in drought_data:
        result["description"] = f"Error: {drought_data['error']}"
        return result

    # The API returns a list of records; take the most recent
    records = drought_data if isinstance(drought_data, list) else []
    if not records:
        return result

    latest = records[-1] if records else {}

    # Extract D0-D4 percentages (keys vary: D0, D1, D2, D3, D4 or d0, d1...)
    d_levels = {}
    for level in ["D0", "D1", "D2", "D3", "D4"]:
        val = latest.get(level) or latest.get(level.lower())
        if val is not None:
            try:
                d_levels[level] = float(val)
            except (ValueError, TypeError):
                pass

    # Also try alternative keys
    for key in ["None", "none", "NONE"]:
        val = latest.get(key)
        if val is not None:
            try:
                d_levels["None"] = float(val)
            except (ValueError, TypeError):
                pass

    result["detail"] = d_levels

    # Determine dominant drought level
    descriptions = {
        "D4": "Exceptional Drought",
        "D3": "Extreme Drought",
        "D2": "Severe Drought",
        "D1": "Moderate Drought",
        "D0": "Abnormally Dry",
    }
    for level in ["D4", "D3", "D2", "D1", "D0"]:
        pct = d_levels.get(level, 0)
        if pct and pct > 0:
            result["level"] = level
            result["description"] = descriptions[level]
            break

    if result["level"] is None:
        result["level"] = "None"
        result["description"] = "No drought"

    return result


def _generate_investigation_notes(profile: dict) -> list[str]:
    """Analyze the gathered data and produce human-readable investigation notes.

    These notes highlight fire-weather-relevant findings: low RH, high winds,
    active alerts, drought conditions, SPC outlook inclusion, etc.
    """
    notes = []
    cc = profile.get("current_conditions", {})
    alerts = profile.get("alerts", [])
    spc = profile.get("spc_outlook", {})
    drought = profile.get("drought", {})

    # -- RH analysis --
    rh = cc.get("rh_pct")
    if rh is not None:
        if rh < 10:
            notes.append(f"RH at {rh}% -- critically low, well below Red Flag threshold of 15%")
        elif rh < 15:
            notes.append(f"RH at {rh}% -- below Red Flag threshold of 15%")
        elif rh < 20:
            notes.append(f"RH at {rh}% -- marginally low, near fire weather threshold")
        elif rh < 25:
            notes.append(f"RH at {rh}% -- somewhat low but above Red Flag threshold")
        else:
            notes.append(f"RH at {rh}% -- within normal range")

    # -- Wind analysis --
    gust = cc.get("wind_gust_kt")
    sustained = cc.get("wind_speed_kt")
    if gust is not None and sustained is not None:
        notes.append(f"Wind gusts {gust} kt with sustained {sustained} kt")
        if gust >= 35:
            notes.append("Wind gusts exceeding 35 kt -- extreme fire spread potential")
        elif gust >= 25:
            notes.append("Wind gusts 25+ kt -- significant fire weather concern")
    elif sustained is not None:
        notes.append(f"Sustained winds {sustained} kt")
        if sustained >= 20:
            notes.append("Sustained winds 20+ kt -- elevated fire risk from wind alone")

    # -- Temperature / dewpoint spread --
    temp = cc.get("temperature_f")
    dwpf = cc.get("dewpoint_f")
    if temp is not None and dwpf is not None:
        spread = temp - dwpf
        if spread > 40:
            notes.append(f"Temperature-dewpoint spread {spread:.0f}F -- extremely dry atmosphere")
        elif spread > 30:
            notes.append(f"Temperature-dewpoint spread {spread:.0f}F -- very dry atmosphere")

    # -- Alert analysis --
    rfw_found = False
    for alert in alerts:
        event = alert.get("event", "")
        if "red flag" in event.lower():
            rfw_found = True
            notes.append(f"Active {event} for this area")
        elif "fire" in event.lower():
            notes.append(f"Active {event} for this area")
    if not rfw_found and rh is not None and rh < 15:
        notes.append("No active Red Flag Warning despite sub-15% RH -- check if NWS has issued one for the zone")

    # -- SPC outlook --
    if spc.get("in_outlook_area"):
        risk = spc.get("risk_level", "UNKNOWN")
        notes.append(f"In SPC {risk} fire weather outlook area")
    else:
        notes.append("Not in an SPC fire weather outlook area (or outlook data unavailable)")

    # -- Drought --
    drought_level = drought.get("level")
    if drought_level and drought_level != "None":
        desc = drought.get("description", "")
        notes.append(f"Drought status: {drought_level} ({desc})")
    elif drought_level == "None":
        notes.append("No drought conditions reported for this area")

    return notes


def _generate_recommended_steps(lat: float, lon: float) -> list[dict]:
    """Build a list of recommended follow-up actions for an agent.

    These suggest specific tools and parameters the agent can invoke
    to deepen the investigation.
    """
    return [
        {
            "action": "Get Street View imagery",
            "tool": "get_street_view",
            "params": {"lat": lat, "lon": lon},
        },
        {
            "action": "Run HRRR cross-section through area",
            "tool": "generate_cross_section",
            "params": {
                "start_lat": round(lat - 0.3, 4),
                "start_lon": round(lon - 0.5, 4),
                "end_lat": round(lat + 0.3, 4),
                "end_lon": round(lon + 0.5, 4),
                "product": "fire_wx",
            },
        },
        {
            "action": "Check temporal evolution",
            "tool": "generate_cross_section",
            "note": "Run for fhr 0,3,6,9,12 to see how conditions change",
        },
        {
            "action": "Get RAWS station data",
            "tool": "get_raws",
            "note": "RAWS stations report fuel moisture and fire-specific weather",
        },
    ]


# =============================================================================
# Public API
# =============================================================================

def investigate_location(
    lat: float,
    lon: float,
    name: Optional[str] = None,
    base_url: str = "http://127.0.0.1:5565",
) -> dict:
    """Comprehensive fire weather investigation for a specific location.

    Gathers real observations, model data, alerts, terrain, drought, and
    returns everything an agent needs to assess fire risk at this point.

    Each external data call is independently wrapped in error handling so
    that a failure in one source does not prevent the rest from completing.

    Args:
        lat: Latitude of the investigation point.
        lon: Longitude of the investigation point.
        name: Human-readable name for the location (e.g. "Newalla, OK").
        base_url: Base URL for the wxsection dashboard API. Currently
                  unused but reserved for future HRRR point-query integration.

    Returns:
        A comprehensive investigation dict with keys:
            location, current_conditions, alerts, spc_outlook,
            drought, terrain, investigation_notes, recommended_next_steps
    """
    profile = {
        "location": {"lat": lat, "lon": lon, "name": name, "elevation_ft": None},
        "current_conditions": {},
        "alerts": [],
        "spc_outlook": {"risk_level": None, "in_outlook_area": False},
        "drought": {"level": None, "description": "No data"},
        "terrain": {"elevation_ft": None},
        "investigation_notes": [],
        "recommended_next_steps": [],
        "_errors": [],
    }

    # ----- 1. Elevation / terrain -----
    try:
        elev = get_elevation(lat, lon)
        elev_ft = elev.get("elevation_ft")
        profile["terrain"]["elevation_ft"] = elev_ft
        profile["terrain"]["elevation_m"] = elev.get("elevation_m")
        profile["location"]["elevation_ft"] = elev_ft
    except Exception as exc:
        profile["_errors"].append(f"elevation: {exc}")

    # ----- 2. Nearby stations + METAR observations -----
    try:
        stations = get_nearby_stations(lat, lon, radius_km=50)
        if stations:
            nearest = stations[0]
            station_id = nearest["id"]
            distance_km = nearest["distance_km"]

            # Fetch observations for the nearest station
            try:
                metar_data = get_metar_observations([station_id], hours_back=2)
                obs = _extract_latest_observation(metar_data)
                if obs:
                    obs["station"] = station_id
                    obs["station_name"] = nearest.get("name", "")
                    obs["distance_km"] = distance_km
                    profile["current_conditions"] = obs
                else:
                    profile["current_conditions"] = {
                        "station": station_id,
                        "distance_km": distance_km,
                        "note": "Station found but no recent observations",
                    }
            except Exception as exc:
                profile["_errors"].append(f"metar_observations: {exc}")
                profile["current_conditions"] = {
                    "station": station_id,
                    "distance_km": distance_km,
                    "note": f"Could not fetch observations: {exc}",
                }

            # Include a few alternate stations for reference
            if len(stations) > 1:
                profile["current_conditions"]["nearby_stations"] = [
                    {"id": s["id"], "name": s.get("name", ""), "distance_km": s["distance_km"]}
                    for s in stations[:5]
                ]
        else:
            profile["current_conditions"]["note"] = "No ASOS/AWOS stations found within 50 km"
    except Exception as exc:
        profile["_errors"].append(f"nearby_stations: {exc}")

    # ----- 3. NWS alerts -----
    try:
        alerts_data = get_nws_alerts(lat=lat, lon=lon)
        features = alerts_data.get("features", [])
        for feat in features:
            props = feat.get("properties", {})
            profile["alerts"].append({
                "event": props.get("event", "Unknown"),
                "headline": props.get("headline", ""),
                "severity": props.get("severity", ""),
                "urgency": props.get("urgency", ""),
                "description": (props.get("description", "") or "")[:500],
            })
    except Exception as exc:
        profile["_errors"].append(f"nws_alerts: {exc}")

    # ----- 4. SPC Fire Weather Outlook -----
    try:
        spc_data = get_spc_fire_weather_outlook(day=1)
        if "error" not in spc_data:
            spc_result = _check_point_in_outlook(lat, lon, spc_data)
            profile["spc_outlook"] = spc_result
    except Exception as exc:
        profile["_errors"].append(f"spc_outlook: {exc}")

    # ----- 5. Drought status -----
    try:
        state = _guess_state_from_coords(lat, lon)
        if state:
            drought_raw = get_drought_status(state=state)
            profile["drought"] = _parse_drought_response(drought_raw)
            profile["drought"]["state_queried"] = state
        else:
            profile["drought"]["description"] = "Could not determine state for drought lookup"
    except Exception as exc:
        profile["_errors"].append(f"drought: {exc}")

    # ----- 6. Generate investigation notes -----
    profile["investigation_notes"] = _generate_investigation_notes(profile)

    # ----- 7. Recommended next steps -----
    profile["recommended_next_steps"] = _generate_recommended_steps(lat, lon)

    return profile


def investigate_town(
    town_name: str,
    state: str,
    base_url: str = "http://127.0.0.1:5565",
) -> dict:
    """Investigate fire weather conditions for a named town.

    Looks up the town in the built-in coordinate table. If not found,
    attempts to geocode via the NWS API (points endpoint). Then calls
    investigate_location() with the resolved coordinates.

    Args:
        town_name: Town/city name (case-insensitive), e.g. "Newalla".
        state: Two-letter state abbreviation (case-insensitive), e.g. "OK".
        base_url: Base URL for the wxsection dashboard API.

    Returns:
        The same comprehensive investigation dict as investigate_location(),
        with the location name set to "Town, ST" format.
    """
    key = (town_name.lower().strip(), state.lower().strip())

    coords = TOWN_COORDS.get(key)

    if coords:
        lat, lon = coords
    else:
        # Try NWS geocoding as a fallback -- this is best-effort
        lat, lon = _geocode_nws(town_name, state)
        if lat is None:
            return {
                "error": f"Could not find coordinates for {town_name}, {state.upper()}. "
                         "Add it to TOWN_COORDS or provide lat/lon directly.",
                "location": {"lat": None, "lon": None, "name": f"{town_name}, {state.upper()}"},
            }

    display_name = f"{town_name.title()}, {state.upper()}"
    return investigate_location(lat, lon, name=display_name, base_url=base_url)


def _geocode_nws(town_name: str, state: str) -> tuple:
    """Attempt to geocode a town via the US Census geocoder.

    This is a best-effort fallback when the town is not in TOWN_COORDS.
    Returns (lat, lon) or (None, None) on failure.
    """
    import urllib.request
    import urllib.parse
    import json

    address = f"{town_name}, {state.upper()}"
    params = {
        "address": address,
        "benchmark": "Public_AR_Current",
        "format": "json",
    }
    url = "https://geocoding.geo.census.gov/geocoder/locations/onelineaddress?" + urllib.parse.urlencode(params)

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "wxsection-agent/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
        matches = data.get("result", {}).get("addressMatches", [])
        if matches:
            coords = matches[0].get("coordinates", {})
            lat = coords.get("y")
            lon = coords.get("x")
            if lat is not None and lon is not None:
                return (float(lat), float(lon))
    except Exception:
        pass

    return (None, None)


def batch_investigate(
    locations: list,
    base_url: str = "http://127.0.0.1:5565",
) -> list[dict]:
    """Investigate multiple locations sequentially.

    Args:
        locations: List of (lat, lon, name) tuples. The name element is
                   optional -- you can pass (lat, lon) tuples as well.
        base_url: Base URL for the wxsection dashboard API.

    Returns:
        List of investigation result dicts, one per location, in the
        same order as the input list.
    """
    results = []
    for loc in locations:
        if len(loc) >= 3:
            lat, lon, name = loc[0], loc[1], loc[2]
        else:
            lat, lon = loc[0], loc[1]
            name = None

        result = investigate_location(lat, lon, name=name, base_url=base_url)
        results.append(result)

    return results


def generate_investigation_report_text(investigation_result: dict) -> str:
    """Generate a clean, readable text summary of an investigation.

    Takes the output of investigate_location() and produces formatted
    plain text suitable for inclusion in reports, agent reasoning traces,
    or direct human consumption.

    Args:
        investigation_result: Dict returned by investigate_location().

    Returns:
        Multi-line string with the formatted report.
    """
    r = investigation_result

    # Handle error case
    if "error" in r:
        return f"INVESTIGATION ERROR: {r['error']}"

    loc = r.get("location", {})
    cc = r.get("current_conditions", {})
    alerts = r.get("alerts", [])
    spc = r.get("spc_outlook", {})
    drought = r.get("drought", {})
    terrain = r.get("terrain", {})
    notes = r.get("investigation_notes", [])
    steps = r.get("recommended_next_steps", [])
    errors = r.get("_errors", [])

    lines = []
    lines.append("=" * 70)
    header = f"FIRE WEATHER INVESTIGATION: {loc.get('name') or 'Unknown Location'}"
    lines.append(header)
    lines.append("=" * 70)

    # Location
    lines.append("")
    lines.append("LOCATION")
    lines.append(f"  Coordinates: {loc.get('lat')}, {loc.get('lon')}")
    elev = terrain.get("elevation_ft")
    if elev is not None:
        lines.append(f"  Elevation:   {elev:.0f} ft ({terrain.get('elevation_m', 0):.0f} m)")
    lines.append(f"  Queried at:  {datetime.utcnow().strftime('%Y-%m-%d %H:%MZ')}")

    # Current conditions
    lines.append("")
    lines.append("CURRENT CONDITIONS")
    station = cc.get("station")
    if station:
        dist = cc.get("distance_km", "?")
        stn_name = cc.get("station_name", "")
        lines.append(f"  Station: {station} ({stn_name}), {dist} km away")
        obs_time = cc.get("observation_time", "")
        if obs_time:
            lines.append(f"  Obs time: {obs_time}")

        temp = cc.get("temperature_f")
        dwpf = cc.get("dewpoint_f")
        rh = cc.get("rh_pct")
        if temp is not None:
            lines.append(f"  Temperature: {temp:.0f} F")
        if dwpf is not None:
            lines.append(f"  Dewpoint:    {dwpf:.0f} F")
        if rh is not None:
            lines.append(f"  RH:          {rh:.0f}%")

        wind_dir = cc.get("wind_dir")
        wind_spd = cc.get("wind_speed_kt")
        wind_gst = cc.get("wind_gust_kt")
        if wind_spd is not None:
            wind_str = f"  Wind:        {wind_dir if wind_dir is not None else '---'}deg at {wind_spd:.0f} kt"
            if wind_gst is not None:
                wind_str += f", gusting {wind_gst:.0f} kt"
            lines.append(wind_str)

        vis = cc.get("visibility_sm")
        if vis is not None:
            lines.append(f"  Visibility:  {vis} SM")

        raw = cc.get("raw_metar", "")
        if raw:
            lines.append(f"  Raw METAR:   {raw}")
    else:
        note = cc.get("note", "No observation data available")
        lines.append(f"  {note}")

    # Alerts
    lines.append("")
    lines.append("ACTIVE ALERTS")
    if alerts:
        for a in alerts:
            lines.append(f"  [{a.get('severity', '?')}] {a.get('event', 'Unknown')}")
            headline = a.get("headline", "")
            if headline:
                lines.append(f"    {headline}")
    else:
        lines.append("  No active NWS alerts for this point")

    # SPC outlook
    lines.append("")
    lines.append("SPC FIRE WEATHER OUTLOOK")
    if spc.get("in_outlook_area"):
        lines.append(f"  Risk level: {spc.get('risk_level', 'UNKNOWN')}")
        lines.append(f"  In outlook area: YES")
    else:
        lines.append("  Not in an SPC fire weather outlook area")

    # Drought
    lines.append("")
    lines.append("DROUGHT STATUS")
    drought_level = drought.get("level")
    if drought_level and drought_level != "None":
        lines.append(f"  Level: {drought_level} -- {drought.get('description', '')}")
        detail = drought.get("detail", {})
        if detail:
            detail_parts = [f"{k}: {v:.1f}%" for k, v in detail.items() if k.startswith("D")]
            if detail_parts:
                lines.append(f"  Area percentages: {', '.join(detail_parts)}")
    else:
        lines.append(f"  {drought.get('description', 'No data')}")

    state_q = drought.get("state_queried")
    if state_q:
        lines.append(f"  (State-level data for {state_q})")

    # Investigation notes
    lines.append("")
    lines.append("INVESTIGATION NOTES")
    if notes:
        for note in notes:
            lines.append(f"  * {note}")
    else:
        lines.append("  No notes generated")

    # Recommended next steps
    lines.append("")
    lines.append("RECOMMENDED NEXT STEPS")
    for i, step in enumerate(steps, 1):
        lines.append(f"  {i}. {step.get('action', 'Unknown action')}")
        tool = step.get("tool", "")
        if tool:
            lines.append(f"     Tool: {tool}")
        note = step.get("note", "")
        if note:
            lines.append(f"     Note: {note}")
        params = step.get("params")
        if params:
            params_str = ", ".join(f"{k}={v}" for k, v in params.items())
            lines.append(f"     Params: {params_str}")

    # Errors (if any)
    if errors:
        lines.append("")
        lines.append("DATA RETRIEVAL ERRORS")
        for err in errors:
            lines.append(f"  ! {err}")

    lines.append("")
    lines.append("=" * 70)

    return "\n".join(lines)
