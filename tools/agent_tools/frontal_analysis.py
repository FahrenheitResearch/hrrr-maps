"""
Frontal Analysis & Wind Shift Detection for Fire Weather

Detects wind direction shifts from HRRR/GFS/RRFS temporal evolution data,
classifies frontal passages, and assesses their impact on active fires.

This module exists because "nighttime recovery" is a dangerously vague term.
What actually matters to firefighters is:
  - WHEN does the wind shift?
  - HOW MUCH does direction change?
  - Do winds stay gusty after the shift?
  - Which flanks of active fires become headfires?

A cold front passage that shifts winds 110 degrees while maintaining 25-kt
gusts is NOT "recovery" -- it's a fireline reversal that can trap crews.

Usage:
    from tools.agent_tools.frontal_analysis import (
        detect_wind_shifts,
        analyze_frontal_impact_on_fires,
        classify_overnight_conditions,
    )

    # Detect wind shifts at a point
    result = detect_wind_shifts(34.05, -118.25)

    # Analyze impact on an active fire spreading NE
    impact = analyze_frontal_impact_on_fires(34.05, -118.25, fire_bearing=45)

    # Classify what actually happens overnight (vs blindly saying "recovery")
    overnight = classify_overnight_conditions(34.05, -118.25)
"""
import json
import math
import urllib.request
import urllib.parse
from datetime import datetime, timedelta
from typing import Optional

from tools.agent_tools.external_data import _fetch_json, _find_surface_value


# =============================================================================
# Constants
# =============================================================================

# Wind shift classification thresholds (degrees)
MAJOR_SHIFT_DEG = 90       # >90 degrees = major (likely frontal)
MODERATE_SHIFT_DEG = 45    # 45-90 degrees = moderate (trough, outflow, etc.)

# Recovery thresholds for fire weather
CALM_WIND_KT = 10          # Below this, hand crews can work
RECOVERY_RH_PCT = 50       # Above this, fires lay down
MARGINAL_RH_PCT = 25       # Below this, fires still spread even with some moisture
GUSTY_WIND_KT = 15         # Above this, fires spread aggressively

# Compass directions
_COMPASS_16 = [
    "N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
    "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW",
]


def _deg_to_compass(deg: float) -> str:
    """Convert meteorological wind direction (degrees) to compass label."""
    idx = round(deg / 22.5) % 16
    return _COMPASS_16[idx]


def _wind_dir_from_uv(u: float, v: float) -> float:
    """Compute meteorological wind direction from U and V components.

    Meteorological convention: direction wind is COMING FROM.
    U = east-west component (positive = from west)
    V = north-south component (positive = from south)

    Returns degrees [0, 360).
    """
    # atan2 gives the direction the wind is blowing TO
    # Add 180 to get direction wind is coming FROM (meteorological convention)
    direction = (math.degrees(math.atan2(u, v)) + 180.0) % 360.0
    return round(direction, 1)


def _angular_difference(dir1: float, dir2: float) -> float:
    """Compute the smallest angular difference between two directions.

    Returns value in [0, 180] degrees.
    """
    diff = abs(dir1 - dir2) % 360
    if diff > 180:
        diff = 360 - diff
    return round(diff, 1)


def _classify_shift_type(
    dir_before: float,
    dir_after: float,
    speed_before_kt: float,
    speed_after_kt: float,
    rh_before: Optional[float],
    rh_after: Optional[float],
    hour_utc_after: int,
) -> str:
    """Classify the meteorological cause of a wind shift.

    Returns one of: "cold_front", "warm_front", "sea_breeze",
    "land_breeze", "outflow", "dryline", "trough", "unknown".
    """
    change = _angular_difference(dir_before, dir_after)

    # Cold front: typically veers (clockwise in NH) from S/SW to W/NW/N
    # with wind speed maintained or increasing, often RH increase
    before_compass = dir_before % 360
    after_compass = dir_after % 360

    # Check if shift is veering (clockwise)
    raw_diff = (dir_after - dir_before) % 360
    is_veering = raw_diff < 180  # clockwise shift

    # Check quadrants
    before_south = 135 <= before_compass <= 270  # S/SW/W
    after_north = (270 <= after_compass <= 360) or (0 <= after_compass <= 90)  # N/NW/NE

    # Cold front signature: S/SW shifting to N/NW, veering, winds stay up
    if before_south and after_north and change >= MODERATE_SHIFT_DEG:
        if speed_after_kt >= CALM_WIND_KT:
            return "cold_front"

    # Warm front: backing (counterclockwise), E/SE shifting to S/SW
    before_east = 45 <= before_compass <= 180
    after_south = 135 <= after_compass <= 270
    if before_east and after_south and not is_veering:
        return "warm_front"

    # Sea breeze: afternoon onshore flow (typically after 18Z in CONUS)
    # Shift from offshore to onshore
    if 15 <= hour_utc_after <= 23 and change >= MODERATE_SHIFT_DEG:
        if speed_before_kt < 15 and speed_after_kt < 20:
            return "sea_breeze"

    # Dryline: in the southern Plains, shift from SE to SW/W
    # Often no RH increase -- may actually get drier
    if rh_before is not None and rh_after is not None:
        if rh_after <= rh_before and change >= MODERATE_SHIFT_DEG:
            if before_east and (180 <= after_compass <= 315):
                return "dryline"

    # Outflow boundary: rapid shift with speed increase, any direction
    if speed_after_kt > speed_before_kt * 1.5 and change >= MODERATE_SHIFT_DEG:
        return "outflow"

    # Generic trough
    if change >= MODERATE_SHIFT_DEG:
        return "trough"

    return "unknown"


def _format_valid_time(init_dt: datetime, fhr: int) -> str:
    """Format a valid time string from init datetime and forecast hour."""
    valid = init_dt + timedelta(hours=fhr)
    return valid.strftime("%H:%MZ %b %d")


def _parse_cycle_to_datetime(cycle_key: str) -> Optional[datetime]:
    """Parse a cycle key like '20260209_21z' into a datetime."""
    try:
        # Format: YYYYMMDD_HHz
        return datetime.strptime(cycle_key.replace("z", ""), "%Y%m%d_%H")
    except (ValueError, AttributeError):
        return None


def _fire_impact_text(
    dir_change: float,
    dir_before: float,
    dir_after: float,
    speed_before_kt: float,
    speed_after_kt: float,
    gust_before_kt: Optional[float],
    gust_after_kt: Optional[float],
    rh_after: Optional[float],
    shift_type: str,
) -> str:
    """Generate plain-English fire impact assessment for a wind shift."""
    compass_before = _deg_to_compass(dir_before)
    compass_after = _deg_to_compass(dir_after)

    parts = []

    if dir_change >= MAJOR_SHIFT_DEG:
        parts.append(
            f"CRITICAL: Wind shift from {compass_before} to {compass_after} "
            f"({dir_change:.0f} degrees) will reverse fire spread directions."
        )
        # Explain which flanks become headfires
        # Wind FROM the north pushes fire south, etc.
        fire_dir_before = (dir_before + 180) % 360
        fire_dir_after = (dir_after + 180) % 360
        compass_fire_before = _deg_to_compass(fire_dir_before)
        compass_fire_after = _deg_to_compass(fire_dir_after)
        parts.append(
            f"Pre-shift fires spread {compass_fire_before}; post-shift fires "
            f"spread {compass_fire_after}."
        )
    elif dir_change >= MODERATE_SHIFT_DEG:
        parts.append(
            f"SIGNIFICANT: Wind shift from {compass_before} to {compass_after} "
            f"({dir_change:.0f} degrees) will alter fire spread patterns."
        )
    else:
        parts.append(
            f"Minor wind direction change from {compass_before} to {compass_after} "
            f"({dir_change:.0f} degrees)."
        )

    # Assess post-shift wind conditions
    gust_str = ""
    if gust_after_kt is not None:
        gust_str = f" with gusts to {gust_after_kt:.0f} kt"
    if speed_after_kt >= GUSTY_WIND_KT:
        parts.append(
            f"This is NOT 'nighttime recovery' -- winds remain "
            f"{speed_after_kt:.0f} kt sustained{gust_str} after the shift."
        )
    elif speed_after_kt >= CALM_WIND_KT:
        parts.append(
            f"Winds moderate to {speed_after_kt:.0f} kt{gust_str} but remain "
            f"operationally significant."
        )
    else:
        parts.append(
            f"Winds drop to {speed_after_kt:.0f} kt{gust_str} after the shift."
        )

    # RH context
    if rh_after is not None:
        if rh_after < MARGINAL_RH_PCT:
            parts.append(
                f"RH remains critically low at {rh_after:.0f}% -- "
                f"fires will continue to spread in the new direction."
            )
        elif rh_after < RECOVERY_RH_PCT:
            parts.append(
                f"RH increases to {rh_after:.0f}% -- above critical thresholds "
                f"but NOT high enough for containment."
            )
        else:
            parts.append(
                f"RH rises to {rh_after:.0f}% -- approaching recovery levels."
            )

    return " ".join(parts)


# =============================================================================
# Core data fetching
# =============================================================================

def _get_point_wind_and_rh(
    lat: float,
    lon: float,
    model: str,
    cycle: str,
    fhr: int,
    base_url: str,
) -> dict:
    """Fetch surface wind U/V components AND RH at a point for a single FHR.

    Returns dict with wind_dir, wind_speed_kt, wind_gust_kt (estimated),
    rh_pct, u_wind_ms, v_wind_ms, valid_time, and metadata.
    """
    offset = 0.005
    start_lat = lat - offset
    start_lon = lon
    end_lat = lat + offset
    end_lon = lon
    base = base_url.rstrip("/")

    # Fetch wind_speed (returns u_wind_ms, v_wind_ms) and rh
    result = {
        "fhr": fhr,
        "wind_dir": None,
        "wind_speed_kt": None,
        "wind_speed_ms": None,
        "wind_gust_kt": None,
        "rh_pct": None,
        "u_wind_ms": None,
        "v_wind_ms": None,
        "valid_time": None,
        "error": None,
    }

    for product in ("wind_speed", "rh"):
        params = (
            f"start_lat={start_lat}&start_lon={start_lon}"
            f"&end_lat={end_lat}&end_lon={end_lon}"
            f"&product={product}&model={model}&cycle={cycle}&fhr={fhr}"
        )
        url = f"{base}/api/v1/data?{params}"
        try:
            data = _fetch_json(url, timeout=60)
        except Exception as e:
            result["error"] = f"Failed to fetch {product} for fhr={fhr}: {e}"
            continue

        pressure_levels = data.get("pressure_levels_hpa", [])
        surface_pressures = data.get("surface_pressure_hpa", [])
        if not pressure_levels or not surface_pressures:
            result["error"] = f"No pressure data for {product} fhr={fhr}"
            continue

        n_pts = len(surface_pressures)
        center = n_pts // 2
        sfc_pressure = surface_pressures[center]

        if product == "wind_speed":
            u_2d = data.get("u_wind_ms")
            v_2d = data.get("v_wind_ms")
            if u_2d and v_2d:
                u_val, _ = _find_surface_value(u_2d, pressure_levels, sfc_pressure, center)
                v_val, _ = _find_surface_value(v_2d, pressure_levels, sfc_pressure, center)
                if u_val is not None and v_val is not None:
                    speed_ms = math.sqrt(u_val**2 + v_val**2)
                    result["u_wind_ms"] = round(u_val, 2)
                    result["v_wind_ms"] = round(v_val, 2)
                    result["wind_speed_ms"] = round(speed_ms, 2)
                    result["wind_speed_kt"] = round(speed_ms * 1.94384, 1)
                    result["wind_dir"] = _wind_dir_from_uv(u_val, v_val)
                    # Estimate gusts as ~1.4x sustained (common approximation
                    # when actual gust data isn't available from the model)
                    result["wind_gust_kt"] = round(speed_ms * 1.94384 * 1.4, 0)

            # Extract valid_time from metadata
            meta = data.get("metadata", {})
            result["valid_time"] = meta.get("valid_time")
            result["cycle"] = meta.get("cycle", cycle)

        elif product == "rh":
            rh_2d = data.get("rh_pct")
            if rh_2d:
                rh_val, _ = _find_surface_value(rh_2d, pressure_levels, sfc_pressure, center)
                if rh_val is not None:
                    result["rh_pct"] = round(rh_val, 1)

    return result


def _get_available_fhrs(model: str, cycle: str, base_url: str) -> list:
    """Get available forecast hours for a cycle from the cycles endpoint."""
    base = base_url.rstrip("/")
    url = f"{base}/api/v1/cycles?model={model}"
    try:
        data = _fetch_json(url, timeout=15)
    except Exception:
        # Fallback: try common HRRR FHR range
        return list(range(0, 49))

    for c in data.get("cycles", []):
        if c.get("key") == cycle:
            return c.get("forecast_hours", list(range(0, 49)))

    # If cycle is "latest", use the first cycle
    if cycle == "latest" and data.get("cycles"):
        return data["cycles"][0].get("forecast_hours", list(range(0, 49)))

    return list(range(0, 49))


# =============================================================================
# Public API: detect_wind_shifts
# =============================================================================

def detect_wind_shifts(
    lat: float,
    lon: float,
    model: str = "hrrr",
    cycle: str = "latest",
    fhr_range: Optional[tuple] = None,
    fhr_step: int = 1,
    base_url: str = "http://127.0.0.1:5565",
) -> dict:
    """Detect significant wind direction shifts at a location over time.

    Pulls wind and RH data at the surface for multiple forecast hours and
    identifies when wind direction changes significantly, indicating frontal
    passages, troughs, sea breezes, or outflow boundaries.

    Args:
        lat: Latitude of the point.
        lon: Longitude of the point.
        model: Model name ("hrrr", "gfs", "rrfs"). Default: "hrrr".
        cycle: Cycle key (e.g. "20260209_21z") or "latest". Default: "latest".
        fhr_range: Tuple of (min_fhr, max_fhr). Default: full range.
        fhr_step: Step between forecast hours to sample. Default: 1.
            Use 3 for faster scans, 1 for precise timing.
        base_url: Dashboard URL. Default: "http://127.0.0.1:5565".

    Returns:
        Dict with keys:
            location: {lat, lon}
            model: model name
            cycle: resolved cycle key
            wind_evolution: list of hourly wind data dicts
            rh_evolution: list of hourly RH data dicts
            wind_shifts: list of detected wind shift events
            overnight_assessment: summary of overnight conditions
    """
    # Get available forecast hours
    available_fhrs = _get_available_fhrs(model, cycle, base_url)
    if fhr_range:
        fhrs = [f for f in available_fhrs if fhr_range[0] <= f <= fhr_range[1]]
    else:
        fhrs = available_fhrs

    # Apply step
    if fhr_step > 1:
        fhrs = fhrs[::fhr_step]
        # Always include first and last
        if available_fhrs and available_fhrs[-1] not in fhrs:
            fhrs.append(available_fhrs[-1])

    # Fetch wind + RH for each forecast hour
    wind_evolution = []
    rh_evolution = []
    resolved_cycle = cycle
    init_dt = None

    for fhr in sorted(fhrs):
        point_data = _get_point_wind_and_rh(lat, lon, model, cycle, fhr, base_url)

        if point_data.get("error") and not point_data.get("wind_dir"):
            continue

        # Resolve cycle key from first successful response
        if resolved_cycle == "latest" and point_data.get("cycle"):
            resolved_cycle = point_data["cycle"]

        # Parse init datetime from cycle key
        if init_dt is None and resolved_cycle != "latest":
            init_dt = _parse_cycle_to_datetime(resolved_cycle)

        valid_time = point_data.get("valid_time", "")
        if not valid_time and init_dt:
            valid_time = _format_valid_time(init_dt, fhr)

        wind_entry = {
            "fhr": fhr,
            "valid_time": valid_time,
            "wind_dir": point_data["wind_dir"],
            "wind_speed_kt": point_data["wind_speed_kt"],
            "wind_gust_kt": point_data["wind_gust_kt"],
        }
        wind_evolution.append(wind_entry)

        rh_entry = {
            "fhr": fhr,
            "valid_time": valid_time,
            "rh_pct": point_data["rh_pct"],
        }
        rh_evolution.append(rh_entry)

    # Detect wind shifts between consecutive time steps
    wind_shifts = []
    for i in range(1, len(wind_evolution)):
        prev = wind_evolution[i - 1]
        curr = wind_evolution[i]

        if prev["wind_dir"] is None or curr["wind_dir"] is None:
            continue

        dir_change = _angular_difference(prev["wind_dir"], curr["wind_dir"])

        if dir_change < MODERATE_SHIFT_DEG:
            continue

        # Get RH values for classification
        rh_before = None
        rh_after = None
        for rh_e in rh_evolution:
            if rh_e["fhr"] == prev["fhr"]:
                rh_before = rh_e["rh_pct"]
            if rh_e["fhr"] == curr["fhr"]:
                rh_after = rh_e["rh_pct"]

        # Parse hour for classification
        hour_utc = 0
        if curr.get("valid_time"):
            try:
                # Try to parse HH from valid_time string
                vt = curr["valid_time"]
                if "T" in vt:
                    hour_utc = int(vt.split("T")[1][:2])
                elif ":" in vt:
                    hour_utc = int(vt.split(":")[0][-2:])
            except (ValueError, IndexError):
                pass

        # Classify the shift
        shift_type = _classify_shift_type(
            prev["wind_dir"], curr["wind_dir"],
            prev["wind_speed_kt"] or 0, curr["wind_speed_kt"] or 0,
            rh_before, rh_after,
            hour_utc,
        )

        classification = "major" if dir_change >= MAJOR_SHIFT_DEG else "moderate"

        # Generate fire impact text
        impact_text = _fire_impact_text(
            dir_change,
            prev["wind_dir"], curr["wind_dir"],
            prev["wind_speed_kt"] or 0, curr["wind_speed_kt"] or 0,
            prev["wind_gust_kt"], curr["wind_gust_kt"],
            rh_after,
            shift_type,
        )

        shift_event = {
            "fhr_before": prev["fhr"],
            "fhr_after": curr["fhr"],
            "time_before": prev["valid_time"],
            "time_after": curr["valid_time"],
            "dir_before": prev["wind_dir"],
            "dir_after": curr["wind_dir"],
            "dir_change_deg": dir_change,
            "speed_before_kt": prev["wind_speed_kt"],
            "speed_after_kt": curr["wind_speed_kt"],
            "gust_before_kt": prev["wind_gust_kt"],
            "gust_after_kt": curr["wind_gust_kt"],
            "rh_before_pct": rh_before,
            "rh_after_pct": rh_after,
            "type": shift_type,
            "classification": classification,
            "fire_impact": impact_text,
        }
        wind_shifts.append(shift_event)

    # Build overnight assessment
    overnight = _build_overnight_assessment(
        wind_evolution, rh_evolution, wind_shifts, init_dt
    )

    return {
        "location": {"lat": lat, "lon": lon},
        "model": model,
        "cycle": resolved_cycle,
        "wind_evolution": wind_evolution,
        "rh_evolution": rh_evolution,
        "wind_shifts": wind_shifts,
        "overnight_assessment": overnight,
    }


# =============================================================================
# Public API: analyze_frontal_impact_on_fires
# =============================================================================

def analyze_frontal_impact_on_fires(
    lat: float,
    lon: float,
    fire_bearing: Optional[float] = None,
    model: str = "hrrr",
    cycle: str = "latest",
    base_url: str = "http://127.0.0.1:5565",
) -> dict:
    """Analyze how a detected wind shift will affect an active fire.

    Takes an active fire location and optionally the current fire spread
    bearing, detects wind shifts, and produces tactical fire weather guidance.

    Args:
        lat: Latitude of the fire.
        lon: Longitude of the fire.
        fire_bearing: Current fire spread bearing in degrees (0=N, 90=E).
            If None, inferred from current wind direction.
        model: Model name. Default: "hrrr".
        cycle: Cycle key or "latest". Default: "latest".
        base_url: Dashboard URL. Default: "http://127.0.0.1:5565".

    Returns:
        Dict with current_spread, post_shift_spread, impact assessment,
        tactical_window, and post_frontal_conditions.
    """
    # Run full wind shift detection
    shift_data = detect_wind_shifts(
        lat, lon, model=model, cycle=cycle, base_url=base_url
    )

    wind_evo = shift_data.get("wind_evolution", [])
    shifts = shift_data.get("wind_shifts", [])
    rh_evo = shift_data.get("rh_evolution", [])
    init_dt = _parse_cycle_to_datetime(shift_data.get("cycle", ""))

    # Get current conditions from the first forecast hour
    current_wind_dir = None
    current_wind_speed = None
    if wind_evo:
        current_wind_dir = wind_evo[0].get("wind_dir")
        current_wind_speed = wind_evo[0].get("wind_speed_kt")

    # Infer fire bearing from wind if not provided
    # Fire spreads in the direction the wind is blowing TO
    # Wind direction is where it comes FROM, so fire bearing = wind_dir + 180
    if fire_bearing is None and current_wind_dir is not None:
        fire_bearing = (current_wind_dir + 180) % 360

    current_spread = {
        "bearing": fire_bearing,
        "description": (
            f"Fire spreading {_deg_to_compass(fire_bearing)} "
            f"driven by {_deg_to_compass(current_wind_dir)} winds"
            if fire_bearing is not None and current_wind_dir is not None
            else "Unknown -- no wind data available"
        ),
        "wind_dir": current_wind_dir,
        "wind_speed_kt": current_wind_speed,
    }

    # If no shifts detected, return calm assessment
    if not shifts:
        return {
            "location": {"lat": lat, "lon": lon},
            "model": model,
            "cycle": shift_data.get("cycle", cycle),
            "current_spread": current_spread,
            "post_shift_spread": None,
            "impact": (
                "No significant wind shifts detected in the forecast period. "
                "Current fire spread direction expected to continue."
            ),
            "tactical_window": None,
            "post_frontal_conditions": None,
            "wind_shifts": [],
            "wind_evolution": wind_evo,
        }

    # Find the most significant shift (largest direction change)
    primary_shift = max(shifts, key=lambda s: s["dir_change_deg"])

    # Compute post-shift fire bearing
    post_wind_dir = primary_shift["dir_after"]
    post_fire_bearing = (post_wind_dir + 180) % 360

    post_shift_spread = {
        "bearing": post_fire_bearing,
        "description": (
            f"After {primary_shift['type'].replace('_', ' ')} shift, "
            f"fire will spread {_deg_to_compass(post_fire_bearing)} "
            f"driven by {_deg_to_compass(post_wind_dir)} winds"
        ),
        "wind_dir": post_wind_dir,
        "wind_speed_kt": primary_shift["speed_after_kt"],
    }

    # Bearing change for the fire itself
    if fire_bearing is not None:
        bearing_change = _angular_difference(fire_bearing, post_fire_bearing)
    else:
        bearing_change = primary_shift["dir_change_deg"]

    # Generate impact assessment
    impact_parts = []

    if bearing_change >= MAJOR_SHIFT_DEG:
        impact_parts.append(
            f"CRITICAL REVERSAL: Fire spread direction changes {bearing_change:.0f} degrees "
            f"from {_deg_to_compass(fire_bearing)} to {_deg_to_compass(post_fire_bearing)}."
        )
        # Identify which flanks reverse
        # The flank opposite to current spread direction is the "back"
        # After shift, this back may become the new head
        back_before = (fire_bearing + 180) % 360
        impact_parts.append(
            f"Current {_deg_to_compass(back_before)} flank (rear/heel) may become "
            f"active or even the new headfire. Any suppression resources positioned "
            f"on that flank must be warned."
        )
    elif bearing_change >= MODERATE_SHIFT_DEG:
        impact_parts.append(
            f"SIGNIFICANT SHIFT: Fire spread direction changes {bearing_change:.0f} degrees. "
            f"Flank fires may become headfires on the {_deg_to_compass(post_fire_bearing)} side."
        )
    else:
        impact_parts.append(
            f"Minor direction change ({bearing_change:.0f} degrees). "
            f"Fire behavior expected to continue with modest course correction."
        )

    # Tactical window calculation
    hours_until_shift = primary_shift["fhr_after"] - (wind_evo[0]["fhr"] if wind_evo else 0)
    time_str = primary_shift.get("time_after", f"FHR {primary_shift['fhr_after']}")

    tactical_window = (
        f"{hours_until_shift} hours until wind shift -- all operations on the "
        f"{_deg_to_compass(back_before if bearing_change >= MAJOR_SHIFT_DEG else fire_bearing)} "
        f"flank must be completed or secured before {time_str}."
        if hours_until_shift > 0
        else f"Wind shift is occurring NOW or has already passed."
    )

    # Post-frontal conditions summary
    post_rh = primary_shift.get("rh_after_pct")

    if primary_shift["speed_after_kt"] and primary_shift["speed_after_kt"] >= GUSTY_WIND_KT:
        wind_assessment = (
            f"Winds decrease but remain operationally significant at "
            f"{primary_shift['speed_after_kt']:.0f} kt sustained"
        )
    elif primary_shift["speed_after_kt"] and primary_shift["speed_after_kt"] >= CALM_WIND_KT:
        wind_assessment = (
            f"Winds moderate to {primary_shift['speed_after_kt']:.0f} kt -- "
            f"still enough to push fire"
        )
    else:
        kt = primary_shift["speed_after_kt"] or 0
        wind_assessment = f"Winds diminish to {kt:.0f} kt"

    if post_rh is not None:
        if post_rh < MARGINAL_RH_PCT:
            rh_assessment = f"RH remains critically low at {post_rh:.0f}%"
        elif post_rh < RECOVERY_RH_PCT:
            rh_assessment = f"RH improves to {post_rh:.0f}% but below recovery threshold"
        else:
            rh_assessment = f"RH rises to {post_rh:.0f}% -- approaching containment levels"
    else:
        rh_assessment = "RH data unavailable"

    post_frontal = {
        "wind_dir": _deg_to_compass(post_wind_dir),
        "wind_dir_deg": post_wind_dir,
        "wind_speed_kt": primary_shift["speed_after_kt"],
        "wind_gust_kt": primary_shift["gust_after_kt"],
        "rh_pct": post_rh,
        "assessment": (
            f"{wind_assessment}. {rh_assessment}. "
            f"Post-frontal conditions {'still support fire spread in the new direction' if (primary_shift['speed_after_kt'] or 0) >= CALM_WIND_KT else 'may allow suppression operations'}."
        ),
    }

    return {
        "location": {"lat": lat, "lon": lon},
        "model": model,
        "cycle": shift_data.get("cycle", cycle),
        "current_spread": current_spread,
        "post_shift_spread": post_shift_spread,
        "impact": " ".join(impact_parts),
        "tactical_window": tactical_window,
        "post_frontal_conditions": post_frontal,
        "primary_shift": primary_shift,
        "all_shifts": shifts,
        "wind_evolution": wind_evo,
    }


# =============================================================================
# Public API: classify_overnight_conditions
# =============================================================================

def _build_overnight_assessment(
    wind_evolution: list,
    rh_evolution: list,
    wind_shifts: list,
    init_dt: Optional[datetime],
) -> dict:
    """Build overnight conditions assessment from wind/RH evolution data.

    Called internally by detect_wind_shifts and also by
    classify_overnight_conditions.
    """
    # Determine overnight hours (roughly 00Z-12Z for CONUS,
    # which is evening through early morning local time)
    overnight_wind = []
    overnight_rh = []

    for w in wind_evolution:
        fhr = w["fhr"]
        if init_dt:
            valid = init_dt + timedelta(hours=fhr)
            hour_utc = valid.hour
        else:
            # Guess from valid_time string
            hour_utc = None
            vt = w.get("valid_time", "")
            if vt:
                try:
                    if "T" in vt:
                        hour_utc = int(vt.split("T")[1][:2])
                    elif ":" in vt:
                        hour_utc = int(vt.split(":")[0][-2:])
                except (ValueError, IndexError):
                    pass
            if hour_utc is None:
                continue

        # Overnight = 00Z through 12Z (roughly 6 PM - 6 AM CST)
        if 0 <= hour_utc <= 12:
            overnight_wind.append(w)

    for r in rh_evolution:
        fhr = r["fhr"]
        if init_dt:
            valid = init_dt + timedelta(hours=fhr)
            hour_utc = valid.hour
        else:
            hour_utc = None
            vt = r.get("valid_time", "")
            if vt:
                try:
                    if "T" in vt:
                        hour_utc = int(vt.split("T")[1][:2])
                    elif ":" in vt:
                        hour_utc = int(vt.split(":")[0][-2:])
                except (ValueError, IndexError):
                    pass
            if hour_utc is None:
                continue
        if 0 <= hour_utc <= 12:
            overnight_rh.append(r)

    # Classify based on overnight conditions
    has_frontal_shift = any(
        s["classification"] == "major" and s["type"] in ("cold_front", "trough")
        for s in wind_shifts
    )

    # Check if winds actually calm down overnight
    overnight_speeds = [
        w["wind_speed_kt"] for w in overnight_wind
        if w.get("wind_speed_kt") is not None
    ]
    overnight_rhs = [
        r["rh_pct"] for r in overnight_rh
        if r.get("rh_pct") is not None
    ]

    min_overnight_wind = min(overnight_speeds) if overnight_speeds else None
    max_overnight_rh = max(overnight_rhs) if overnight_rhs else None

    # Determine classification
    if has_frontal_shift:
        classification = "frontal_shift"
    elif (min_overnight_wind is not None and min_overnight_wind < CALM_WIND_KT
          and max_overnight_rh is not None and max_overnight_rh >= RECOVERY_RH_PCT):
        classification = "true_recovery"
    elif (max_overnight_rh is not None and max_overnight_rh >= MARGINAL_RH_PCT
          and min_overnight_wind is not None and min_overnight_wind < GUSTY_WIND_KT):
        classification = "partial_recovery"
    elif (min_overnight_wind is not None and min_overnight_wind >= GUSTY_WIND_KT
          and max_overnight_rh is not None and max_overnight_rh < MARGINAL_RH_PCT):
        classification = "no_recovery"
    elif min_overnight_wind is not None and min_overnight_wind >= CALM_WIND_KT:
        classification = "partial_recovery"
    else:
        classification = "partial_recovery"  # default if data is incomplete

    # Find key times
    key_times = {}

    # Frontal passage time (from the first major shift)
    for s in wind_shifts:
        if s["classification"] == "major":
            key_times["frontal_passage"] = s["time_after"]
            # Wind shift completion: next FHR where direction stabilizes
            # Look for when direction stops changing rapidly
            fhr_after = s["fhr_after"]
            for w in wind_evolution:
                if w["fhr"] > fhr_after and w.get("wind_dir") is not None:
                    prev_dir = s["dir_after"]
                    curr_dir = w["wind_dir"]
                    if _angular_difference(prev_dir, curr_dir) < 20:
                        key_times["wind_shift_complete"] = w["valid_time"]
                        break
            break

    # True calm time: when winds drop below CALM_WIND_KT
    for w in wind_evolution:
        if (w.get("wind_speed_kt") is not None
                and w["wind_speed_kt"] < CALM_WIND_KT):
            key_times["true_calm"] = w["valid_time"]
            break

    # Build explanation
    explanation_parts = []

    if classification == "frontal_shift":
        front_time = key_times.get("frontal_passage", "unknown time")
        explanation_parts.append(
            f"This is NOT nighttime recovery. A frontal passage at ~{front_time} "
            f"will shift winds significantly."
        )
        if overnight_speeds:
            min_spd = min(overnight_speeds)
            max_spd = max(overnight_speeds)
            explanation_parts.append(
                f"Winds remain {min_spd:.0f}-{max_spd:.0f} kt overnight -- "
                f"{'gusty enough to maintain fire spread' if max_spd >= CALM_WIND_KT else 'diminishing'}."
            )
        if overnight_rhs:
            min_rh = min(overnight_rhs)
            max_rh = max(overnight_rhs)
            explanation_parts.append(
                f"RH ranges {min_rh:.0f}-{max_rh:.0f}% overnight."
            )
        explanation_parts.append(
            "All active firelines will change direction with the wind shift."
        )

    elif classification == "true_recovery":
        calm_time = key_times.get("true_calm", "overnight")
        explanation_parts.append(
            f"True overnight recovery expected. Winds drop below {CALM_WIND_KT} kt "
            f"by {calm_time} and RH rises above {RECOVERY_RH_PCT}%. "
            f"Fires should lay down. Hand crews can operate."
        )

    elif classification == "partial_recovery":
        explanation_parts.append(
            "Partial recovery: "
        )
        if max_overnight_rh is not None and max_overnight_rh >= MARGINAL_RH_PCT:
            explanation_parts.append(
                f"RH improves to {max_overnight_rh:.0f}% (above critical but below recovery). "
            )
        if min_overnight_wind is not None:
            if min_overnight_wind >= CALM_WIND_KT:
                explanation_parts.append(
                    f"Winds remain {min_overnight_wind:.0f}+ kt -- fires moderate but don't go out. "
                )
            else:
                explanation_parts.append(
                    f"Winds diminish to {min_overnight_wind:.0f} kt. "
                )
        explanation_parts.append(
            "Fire activity will decrease but not cease. Mop-up and containment "
            "opportunities may exist but expect flare-ups."
        )

    elif classification == "no_recovery":
        explanation_parts.append(
            "NO overnight recovery expected. "
        )
        if min_overnight_wind is not None:
            explanation_parts.append(
                f"Winds persist at {min_overnight_wind:.0f}+ kt. "
            )
        if max_overnight_rh is not None:
            explanation_parts.append(
                f"RH stays below {max_overnight_rh:.0f}%. "
            )
        explanation_parts.append(
            "Fires will continue to run overnight. Extended attack operations "
            "must account for active fire behavior through the night."
        )

    return {
        "has_true_recovery": classification == "true_recovery",
        "classification": classification,
        "explanation": "".join(explanation_parts),
        "key_times": key_times,
        "overnight_wind_range_kt": (
            (round(min(overnight_speeds), 0), round(max(overnight_speeds), 0))
            if overnight_speeds else None
        ),
        "overnight_rh_range_pct": (
            (round(min(overnight_rhs), 0), round(max(overnight_rhs), 0))
            if overnight_rhs else None
        ),
    }


def classify_overnight_conditions(
    lat: float,
    lon: float,
    model: str = "hrrr",
    cycle: str = "latest",
    base_url: str = "http://127.0.0.1:5565",
) -> dict:
    """Classify what actually happens overnight instead of blindly saying "recovery."

    Queries HRRR temporal evolution and returns one of four classifications:
        - true_recovery: winds <10 kt AND RH >50% -- fires lay down
        - partial_recovery: RH rises but winds remain gusty -- fires moderate
        - frontal_shift: cold front passes -- wind reversal, NOT recovery
        - no_recovery: persistent gradient/LLJ -- fires run all night

    Args:
        lat: Latitude.
        lon: Longitude.
        model: Model name. Default: "hrrr".
        cycle: Cycle key or "latest". Default: "latest".
        base_url: Dashboard URL. Default: "http://127.0.0.1:5565".

    Returns:
        Dict with classification, actual conditions, and plain-English assessment.
    """
    # Run full wind shift detection (which includes overnight assessment)
    shift_data = detect_wind_shifts(
        lat, lon, model=model, cycle=cycle, base_url=base_url
    )

    overnight = shift_data.get("overnight_assessment", {})
    classification = overnight.get("classification", "partial_recovery")

    # Classification definitions (always included for reference)
    classifications = {
        "true_recovery": (
            "Winds drop below 10 kt AND RH rises above 50% -- "
            "fires lay down, hand crews can work"
        ),
        "partial_recovery": (
            "RH rises but winds remain gusty -- "
            "fires moderate but don't go out"
        ),
        "frontal_shift": (
            "Cold front passes -- wind direction reverses, speed may drop "
            "but gusts continue. NOT recovery."
        ),
        "no_recovery": (
            "Low-level jet or persistent gradient keeps winds up, RH stays low -- "
            "fires continue to run overnight"
        ),
    }

    # Build detailed actual conditions
    wind_evo = shift_data.get("wind_evolution", [])
    rh_evo = shift_data.get("rh_evolution", [])
    shifts = shift_data.get("wind_shifts", [])

    # Find the primary shift if any
    primary_shift = None
    if shifts:
        primary_shift = max(shifts, key=lambda s: s["dir_change_deg"])

    # Build post-frontal wind description
    post_frontal_winds = None
    if primary_shift:
        compass = _deg_to_compass(primary_shift["dir_after"])
        spd = primary_shift["speed_after_kt"] or 0
        gust = primary_shift["gust_after_kt"]
        if gust:
            post_frontal_winds = f"{compass} {spd:.0f} kt gusting {gust:.0f} kt"
        else:
            post_frontal_winds = f"{compass} {spd:.0f} kt"

    # Post-frontal RH
    post_frontal_rh = None
    if primary_shift and primary_shift.get("rh_after_pct"):
        post_frontal_rh = f"{primary_shift['rh_after_pct']:.0f}%"

    actual_conditions = {
        "classification": classification,
        "frontal_passage_time": (
            primary_shift["time_after"] if primary_shift else None
        ),
        "post_frontal_winds": post_frontal_winds,
        "post_frontal_rh": post_frontal_rh,
        "assessment": overnight.get("explanation", "Insufficient data for assessment."),
    }

    # Add key times
    actual_conditions["key_times"] = overnight.get("key_times", {})

    return {
        "location": {"lat": lat, "lon": lon},
        "model": model,
        "cycle": shift_data.get("cycle", cycle),
        "classification": classification,
        "classifications": classifications,
        "actual_conditions": actual_conditions,
        "wind_evolution": wind_evo,
        "rh_evolution": rh_evo,
        "wind_shifts": shifts,
        "overnight_wind_range_kt": overnight.get("overnight_wind_range_kt"),
        "overnight_rh_range_pct": overnight.get("overnight_rh_range_pct"),
    }
