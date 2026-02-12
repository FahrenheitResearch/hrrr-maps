"""
Fire Weather Report Quality Checklist & Validation

Pre-publication quality gate for AI-generated fire weather reports.  Born from
a real firefighter/analyst review that found critical errors in an AI report:
overclaimed winds, oversimplified terrain, wrong overnight classification,
missing fuel context, wrong areas highlighted, no ignition sources, and no
seasonal/drought context.

This module provides:
    1. fire_report_checklist() — mandatory verification items before publishing
    2. validate_report_claims() — checks specific claims against tools/data
    3. REPORT_ANTI_PATTERNS — common mistakes to avoid (static reference)

Every fire weather report MUST pass this checklist before being finalized.
Skipping verification steps has real consequences: firefighters position
resources based on these reports.

Usage:
    from tools.agent_tools.report_quality import (
        fire_report_checklist,
        validate_report_claims,
        REPORT_ANTI_PATTERNS,
    )

    # Before publishing any fire weather report:
    checklist = fire_report_checklist(35.22, -101.83, city_name="Amarillo")
    for item in checklist["checklist"]:
        print(f"[{item['priority']}] {item['item']}: {item['question']}")

    # Validate specific claims from a draft report:
    claims = [
        {"type": "wind_speed", "value": 60, "unit": "mph", "qualifier": "sustained"},
        {"type": "terrain", "value": "flat grassland"},
    ]
    result = validate_report_claims(claims, 35.22, -101.83)
    for v in result["validations"]:
        print(f"{v['status']}: {v['claim']} — {v['evidence']}")
"""

from typing import Optional


# =============================================================================
# Common anti-patterns — static reference for agents
# =============================================================================

REPORT_ANTI_PATTERNS = [
    {
        "pattern": "Reporting model winds as observed winds",
        "example": "Sustained winds of 60 mph across the area",
        "fix": (
            "Always verify with mesonet/ASOS: "
            "'KAMA observed gusts to 39kt; HRRR forecast shows...'"
        ),
    },
    {
        "pattern": "Assuming flat terrain",
        "example": "The area is characterized by flat grassland with continuous fine fuels",
        "fix": (
            "Check terrain tool: 'While eastern areas are flat grassland, "
            "canyon terrain to N/W/SE creates channeled winds and extreme "
            "fire behavior'"
        ),
    },
    {
        "pattern": "Saying 'nighttime recovery' without checking",
        "example": "Nighttime recovery of humidity expected after sunset",
        "fix": (
            "Check classify_overnight: 'Cold front passage at 03Z shifts "
            "winds from SSW to NNW; this is NOT recovery but a dangerous "
            "fireline reversal'"
        ),
    },
    {
        "pattern": "Ignoring fuels as the main story",
        "example": "High winds and low RH drive fire behavior today",
        "fix": (
            "Assess fuels first: 'Freeze-dried winter prairie grass, "
            "desiccated by 5 consecutive days above 70F with no precipitation "
            "in 12 days, is the primary fire behavior driver'"
        ),
    },
    {
        "pattern": "No ignition source context",
        "example": "(No mention of how fires start)",
        "fix": (
            "Include ignition sources: 'Amarillo is a major trucking hub; "
            "chains on pavement create sparks. I-40 and I-27 are primary "
            "ignition corridors'"
        ),
    },
    {
        "pattern": "No regional context for severity",
        "example": "RH of 9% indicates EXTREME fire danger",
        "fix": (
            "Contextualize: '9% RH is concerning but occurs 5-10 days per "
            "winter in the TX Panhandle. Truly extreme would be <3% RH with "
            "negative dewpoints'"
        ),
    },
    {
        "pattern": "Highlighting wrong areas of a city",
        "example": "East Amarillo faces the greatest fire threat",
        "fix": (
            "Check city terrain: 'N, W, and SE Amarillo face greatest threat "
            "due to canyon terrain; east side is flat grassland with easier "
            "suppression'"
        ),
    },
]


# =============================================================================
# Checklist — mandatory verification items
# =============================================================================

# Priority levels (for sorting / gating):
#   CRITICAL  — report MUST NOT be published without verifying these
#   HIGH      — operationally significant; strongly recommended
#   MODERATE  — professional quality; should be included

_PRIORITY_ORDER = {"CRITICAL": 0, "HIGH": 1, "MODERATE": 2}

_CHECKLIST_ITEMS = [
    {
        "item": "WIND VERIFICATION",
        "priority": "CRITICAL",
        "question": (
            "Are reported wind speeds verified against actual mesonet/ASOS "
            "observations?"
        ),
        "how_to_verify": (
            "Use verify_winds tool to check all stations within 30 miles. "
            "Never report wind speeds higher than what stations actually "
            "observed."
        ),
        "common_error": (
            "Model winds or forecast winds reported as observed. Always "
            "distinguish 'model shows' from 'stations reported'."
        ),
        "tool": "verify_winds",
    },
    {
        "item": "TERRAIN ACCURACY",
        "priority": "CRITICAL",
        "question": (
            "Does the report accurately describe terrain? Are canyon/valley "
            "features mentioned?"
        ),
        "how_to_verify": (
            "Use analyze_terrain and city_terrain tools. Check "
            "CITY_TERRAIN_PROFILES for expert knowledge."
        ),
        "common_error": (
            "Assuming 'flat grassland' everywhere. Many High Plains cities "
            "have canyon terrain nearby (Palo Duro, Canadian River breaks)."
        ),
        "tool": "analyze_terrain",
    },
    {
        "item": "FUEL CONDITIONS",
        "priority": "CRITICAL",
        "question": (
            "Are fuel conditions highlighted as a primary factor? Is seasonal "
            "context included?"
        ),
        "how_to_verify": (
            "Use assess_fuels tool. Check drought status, recent weather "
            "history, seasonal fuel type."
        ),
        "common_error": (
            "Focusing only on wind/RH without discussing fuel state. In "
            "winter, freeze-dried grass is the main story."
        ),
        "tool": "assess_fuels",
    },
    {
        "item": "OVERNIGHT CONDITIONS",
        "priority": "HIGH",
        "question": (
            "Is 'nighttime recovery' accurately characterized? Is it truly "
            "recovery or a frontal wind shift?"
        ),
        "how_to_verify": (
            "Use classify_overnight and detect_wind_shifts tools. A cold "
            "front wind shift is NOT recovery."
        ),
        "common_error": (
            "Saying 'nighttime recovery expected' when actually a cold front "
            "will shift winds — this reverses firelines and is operationally "
            "critical."
        ),
        "tool": "classify_overnight",
    },
    {
        "item": "GEOGRAPHIC FOCUS",
        "priority": "HIGH",
        "question": (
            "Are the correct areas of the city highlighted for fire risk?"
        ),
        "how_to_verify": (
            "Use city_terrain tool to identify which city quadrants have "
            "dangerous terrain. Don't default to highlighting the 'east "
            "side' — check terrain on all sides."
        ),
        "common_error": (
            "Highlighting the wrong areas. For Amarillo: N/W/SE are "
            "dangerous (canyons), not E (flat)."
        ),
        "tool": "city_terrain",
    },
    {
        "item": "IGNITION SOURCES",
        "priority": "HIGH",
        "question": (
            "Are local ignition sources mentioned? Trucking corridors? "
            "Power lines? Prescribed burns?"
        ),
        "how_to_verify": (
            "Use get_ignition_sources tool. Check for major highways (I-40, "
            "I-35, etc.) and known ignition patterns."
        ),
        "common_error": (
            "Ignoring the #1 human ignition source. Amarillo/OKC/I-40 "
            "corridor: truckers with chains = sparks. Oklahoma: prescribed "
            "burns escape."
        ),
        "tool": "get_ignition_sources",
    },
    {
        "item": "REGIONAL CONTEXT",
        "priority": "MODERATE",
        "question": (
            "Are conditions put in regional context? Is this a 'run of the "
            "mill' day or truly extreme?"
        ),
        "how_to_verify": (
            "Use get_fire_climatology tool. Compare current conditions to "
            "historical range for this station and month."
        ),
        "common_error": (
            "Treating every low-RH day as catastrophic. In the TX Panhandle, "
            "9% RH and 39kt gusts is an elevated day but not extreme. "
            "1% RH and 60kt sustained would be extreme."
        ),
        "tool": "get_fire_climatology",
    },
    {
        "item": "MODEL vs OBSERVATION",
        "priority": "MODERATE",
        "question": (
            "Are model forecasts clearly distinguished from actual "
            "observations?"
        ),
        "how_to_verify": (
            "Use compare_model_obs tool. Label model data as 'HRRR "
            "shows...' not 'conditions are...'"
        ),
        "common_error": (
            "Presenting model cross-section column-averaged data as surface "
            "conditions. Model RH of 45% when surface is 9%."
        ),
        "tool": "compare_model_obs",
    },
    {
        "item": "COLD FRONT TIMING",
        "priority": "MODERATE",
        "question": (
            "If a cold front is approaching, is the timing and wind shift "
            "clearly communicated?"
        ),
        "how_to_verify": (
            "Use detect_wind_shifts tool. Identify the exact FHR/time of "
            "wind direction change and what it means for active fires."
        ),
        "common_error": (
            "Burying frontal passage in forecast details. A wind shift "
            "reverses ALL firelines — this must be prominently highlighted."
        ),
        "tool": "detect_wind_shifts",
    },
    {
        "item": "DROUGHT & SEASONAL",
        "priority": "MODERATE",
        "question": (
            "Is current drought status and seasonal context included?"
        ),
        "how_to_verify": (
            "Use get_drought and assess_fuels tools. Winter fires on "
            "freeze-dried grass are different from summer fires."
        ),
        "common_error": (
            "No mention of drought or seasonal fuel conditions. A warm "
            "February after a freeze-dried winter is fundamentally different "
            "from a normal February."
        ),
        "tool": "assess_fuels",
    },
]


def fire_report_checklist(
    lat: float,
    lon: float,
    city_name: Optional[str] = None,
    base_url: str = "http://127.0.0.1:5565",
) -> dict:
    """Return the mandatory verification checklist for a fire weather report.

    Every fire weather report MUST have each CRITICAL item verified before
    publication.  HIGH items are strongly recommended.  MODERATE items
    distinguish a professional report from an amateur one.

    Args:
        lat: Latitude of the report focus area.
        lon: Longitude of the report focus area.
        city_name: Optional city name for terrain/ignition lookups.
        base_url: wxsection API base URL.

    Returns:
        Dict with keys:
            checklist  — list of checklist item dicts (sorted by priority)
            location   — dict with lat, lon, city_name
            summary    — human-readable summary of what to do
            critical_count — number of CRITICAL items
            total_count — total number of items
    """
    # Build location context
    location = {"lat": lat, "lon": lon}
    if city_name:
        location["city_name"] = city_name

    # Sort by priority (CRITICAL first)
    sorted_items = sorted(
        _CHECKLIST_ITEMS,
        key=lambda x: _PRIORITY_ORDER.get(x["priority"], 99),
    )

    critical_count = sum(
        1 for item in sorted_items if item["priority"] == "CRITICAL"
    )

    summary_parts = [
        f"Fire weather report quality checklist for "
        f"({lat:.2f}, {lon:.2f})",
    ]
    if city_name:
        summary_parts[0] = (
            f"Fire weather report quality checklist for {city_name} "
            f"({lat:.2f}, {lon:.2f})"
        )
    summary_parts.append(
        f"{critical_count} CRITICAL items must be verified before publication."
    )
    summary_parts.append(
        f"{len(sorted_items)} total verification items."
    )
    summary_parts.append(
        "Run each tool listed and confirm your report matches the evidence."
    )

    return {
        "checklist": sorted_items,
        "location": location,
        "summary": " ".join(summary_parts),
        "critical_count": critical_count,
        "total_count": len(sorted_items),
    }


# =============================================================================
# Claim validation — check specific report claims against tools
# =============================================================================

# Maps claim type -> which tool to use and how to frame the validation
_CLAIM_VALIDATORS = {
    "wind_speed": {
        "tool": "verify_winds",
        "description": "Wind speed verification against mesonet/ASOS observations",
        "params_needed": ["value", "unit", "qualifier"],
    },
    "rh": {
        "tool": "verify_winds",  # verify_winds includes RH from mesonet obs
        "description": "Relative humidity verification against surface observations",
        "params_needed": ["value", "unit"],
    },
    "terrain": {
        "tool": "analyze_terrain",
        "description": "Terrain characterization accuracy",
        "params_needed": ["value"],
    },
    "overnight": {
        "tool": "classify_overnight",
        "description": "Overnight condition classification (recovery vs frontal shift)",
        "params_needed": ["value"],
    },
    "fuels": {
        "tool": "assess_fuels",
        "description": "Fuel condition assessment accuracy",
        "params_needed": ["value"],
    },
    "ignition": {
        "tool": "get_ignition_sources",
        "description": "Ignition source identification",
        "params_needed": ["value"],
    },
    "drought": {
        "tool": "get_drought",
        "description": "Drought status verification",
        "params_needed": ["value"],
    },
    "geographic_focus": {
        "tool": "city_terrain",
        "description": "Geographic focus area accuracy for fire risk",
        "params_needed": ["value"],
    },
    "model_data": {
        "tool": "compare_model_obs",
        "description": "Model vs observation distinction",
        "params_needed": ["value"],
    },
    "front_timing": {
        "tool": "detect_wind_shifts",
        "description": "Cold front timing and wind shift characterization",
        "params_needed": ["value"],
    },
}


def _format_claim(claim: dict) -> str:
    """Turn a claim dict into a readable sentence."""
    ctype = claim.get("type", "unknown")
    value = claim.get("value", "")
    unit = claim.get("unit", "")
    qualifier = claim.get("qualifier", "")

    if ctype == "wind_speed":
        unit_label = {"mph": "mph", "kt": "kt", "knots": "kt", "kph": "km/h"}.get(
            str(unit).lower(), unit
        )
        if qualifier:
            return f"{qualifier.capitalize()} winds of {value} {unit_label}"
        return f"Winds of {value} {unit_label}"

    if ctype == "rh":
        unit_label = {"pct": "%", "%": "%", "percent": "%"}.get(
            str(unit).lower(), unit
        )
        qualifier_str = f"{qualifier} " if qualifier else ""
        return f"{qualifier_str.capitalize()}RH of {value}{unit_label}"

    if ctype == "terrain":
        return f"Terrain described as: {value}"

    if ctype == "overnight":
        return f"Overnight conditions: {value}"

    if ctype == "fuels":
        return f"Fuel conditions: {value}"

    if ctype == "ignition":
        return f"Ignition sources: {value}"

    if ctype == "drought":
        return f"Drought status: {value}"

    if ctype == "geographic_focus":
        return f"Geographic focus: {value}"

    if ctype == "model_data":
        return f"Model/observation claim: {value}"

    if ctype == "front_timing":
        return f"Frontal timing: {value}"

    # Fallback
    parts = [str(value)]
    if unit:
        parts.append(str(unit))
    if qualifier:
        parts.insert(0, str(qualifier))
    return f"{ctype}: {' '.join(parts)}"


def _build_verification_instruction(claim: dict, lat: float, lon: float) -> dict:
    """Build a verification instruction for a single claim.

    Returns a dict describing what tool to call and what to look for.
    This is the 'dry run' version — it tells the agent what to do rather
    than calling tools directly (which would require async MCP calls).
    """
    ctype = claim.get("type", "unknown")
    validator = _CLAIM_VALIDATORS.get(ctype)

    claim_text = _format_claim(claim)

    if not validator:
        return {
            "claim": claim_text,
            "status": "UNVERIFIABLE",
            "evidence": f"No validator registered for claim type '{ctype}'.",
            "tool_to_run": None,
            "verification_steps": [
                "Manually verify this claim against available data."
            ],
        }

    # Build tool-specific verification instructions
    tool = validator["tool"]
    steps = []

    if ctype == "wind_speed":
        value = claim.get("value", 0)
        unit = claim.get("unit", "mph")
        qualifier = claim.get("qualifier", "")
        # Convert to common unit for comparison guidance
        if str(unit).lower() in ("kt", "knots"):
            mph_equiv = round(value * 1.15078, 1)
            kt_value = value
        else:
            mph_equiv = value
            kt_value = round(value / 1.15078, 1)

        steps = [
            f"Run: verify_winds(lat={lat}, lon={lon}, radius_miles=30, hours_back=24)",
            f"Check: Did ANY station report {qualifier} winds >= {kt_value} kt ({mph_equiv} mph)?",
            "Compare max observed gust vs claimed value.",
            "If claim exceeds max observation, mark INCORRECT.",
            (
                f"Remember: {qualifier + ' ' if qualifier else ''}winds of "
                f"{value} {unit} is a specific, verifiable claim."
            ),
        ]

    elif ctype == "rh":
        steps = [
            f"Run: verify_winds(lat={lat}, lon={lon}, radius_miles=30, hours_back=24)",
            "Check RH values in returned METAR/mesonet observations.",
            f"Look for minimum RH near {claim.get('value', '?')}%.",
            "Cross-check with HRRR surface values (not column-averaged).",
        ]

    elif ctype == "terrain":
        steps = [
            f"Run: analyze_terrain(lat={lat}, lon={lon}, radius_km=15)",
            f"Run: city_terrain(lat={lat}, lon={lon}, city_name=..., radius_km=20)",
            f"Compare terrain description '{claim.get('value', '')}' with actual terrain data.",
            "Check ALL quadrants around the city, not just the obvious ones.",
            "Look for canyons, river breaks, escarpments that the report may have missed.",
        ]

    elif ctype == "overnight":
        steps = [
            f"Run: classify_overnight(lat={lat}, lon={lon})",
            f"Run: detect_wind_shifts(lat={lat}, lon={lon})",
            "Check if overnight is truly 'recovery' or a frontal wind shift.",
            "A cold front wind shift is NOT recovery — it reverses firelines.",
            "Look at RH forecast: does it reach >50%? If not, it's not true recovery.",
            "Look at wind forecast: do winds stay >10kt? If so, it's not true recovery.",
        ]

    elif ctype == "fuels":
        steps = [
            f"Run: assess_fuels(lat={lat}, lon={lon})",
            "Check seasonal context: is this winter freeze-dried or summer cured?",
            "Check recent weather: warm spell drying? Recent precip?",
            "Check drought status for long-term dryness.",
        ]

    elif ctype == "ignition":
        steps = [
            f"Run: get_ignition_sources(lat={lat}, lon={lon})",
            "Check for trucking corridors (I-40, I-35, etc.).",
            "Check for power line corridors.",
            "Check for railroad lines.",
            "Check for prescribed burn activity.",
        ]

    elif ctype == "drought":
        steps = [
            "Run: get_drought(state=...)",
            "Check current drought classification (D0-D4).",
            "Compare with claim in report.",
        ]

    elif ctype == "geographic_focus":
        steps = [
            f"Run: city_terrain(lat={lat}, lon={lon}, city_name=..., radius_km=20)",
            "Check which quadrants actually have dangerous terrain.",
            "Verify the report highlights the RIGHT areas.",
            "Common error: defaulting to 'east side' when canyons are N/W/SE.",
        ]

    elif ctype == "model_data":
        steps = [
            f"Run: compare_model_obs(lat={lat}, lon={lon})",
            "Check if model values are clearly labeled as model output.",
            "Cross-section data is COLUMN-AVERAGED — not surface values.",
            "Surface obs may differ dramatically from model cross-section values.",
        ]

    elif ctype == "front_timing":
        steps = [
            f"Run: detect_wind_shifts(lat={lat}, lon={lon})",
            "Identify exact FHR/time of wind direction change.",
            "This MUST be prominently communicated — a wind shift reverses all firelines.",
        ]

    else:
        steps = [
            f"Run: {tool}(...) with appropriate parameters for ({lat}, {lon}).",
            f"Verify claim: '{claim.get('value', '')}'",
        ]

    return {
        "claim": claim_text,
        "status": "NEEDS_VERIFICATION",
        "evidence": (
            f"Must be verified using {tool} tool. See verification_steps."
        ),
        "tool_to_run": tool,
        "tool_call": f"{tool}(lat={lat}, lon={lon}, ...)",
        "verification_steps": steps,
    }


def validate_report_claims(
    claims: list[dict],
    lat: float,
    lon: float,
    base_url: str = "http://127.0.0.1:5565",
) -> dict:
    """Validate a list of specific claims from a fire weather report.

    Each claim is a dict with at minimum:
        type  — one of: wind_speed, rh, terrain, overnight, fuels,
                ignition, drought, geographic_focus, model_data,
                front_timing
        value — the claimed value (number or string)

    Optional keys: unit, qualifier.

    This function returns verification instructions — it tells the agent
    which tools to call and what to look for.  In a future version this
    will call the tools directly and return pass/fail results.

    Args:
        claims: List of claim dicts from the report.
        lat: Latitude of the report focus area.
        lon: Longitude of the report focus area.
        base_url: wxsection API base URL.

    Returns:
        Dict with keys:
            validations — list of validation result dicts
            summary — human-readable summary
            needs_verification — count of claims needing tool verification
            unverifiable — count of claims with no validator
    """
    validations = []
    needs_verification = 0
    unverifiable = 0

    for claim in claims:
        result = _build_verification_instruction(claim, lat, lon)
        validations.append(result)

        if result["status"] == "NEEDS_VERIFICATION":
            needs_verification += 1
        elif result["status"] == "UNVERIFIABLE":
            unverifiable += 1

    # Build summary
    total = len(claims)
    summary_parts = [
        f"{total} claim(s) extracted from report.",
        f"{needs_verification} need verification via tools.",
    ]
    if unverifiable:
        summary_parts.append(f"{unverifiable} could not be mapped to a validator.")

    # Identify which unique tools need to be run
    tools_needed = sorted(
        {v["tool_to_run"] for v in validations if v.get("tool_to_run")}
    )
    if tools_needed:
        summary_parts.append(f"Tools to run: {', '.join(tools_needed)}.")

    # Add priority guidance
    critical_types = {"wind_speed", "terrain", "fuels"}
    critical_claims = [c for c in claims if c.get("type") in critical_types]
    if critical_claims:
        summary_parts.append(
            f"CRITICAL claims to verify first: "
            f"{', '.join(c.get('type', '?') for c in critical_claims)}."
        )

    return {
        "validations": validations,
        "summary": " ".join(summary_parts),
        "needs_verification": needs_verification,
        "unverifiable": unverifiable,
        "tools_needed": tools_needed,
    }


# =============================================================================
# Convenience: quick severity check (is the agent overclaiming?)
# =============================================================================

def check_for_overclaiming(
    wind_mph: Optional[float] = None,
    rh_pct: Optional[float] = None,
    description_words: Optional[list[str]] = None,
) -> list[dict]:
    """Quick heuristic check for common overclaiming patterns.

    This does NOT replace tool-based verification. It catches obvious red
    flags before the agent even gets to the checklist.

    Args:
        wind_mph: Claimed wind speed in mph (sustained).
        rh_pct: Claimed minimum RH in percent.
        description_words: List of words/phrases used in the report
            (e.g., ["extreme", "unprecedented", "catastrophic"]).

    Returns:
        List of warning dicts. Empty list = no obvious overclaiming.
    """
    warnings = []

    if wind_mph is not None:
        if wind_mph >= 80:
            warnings.append({
                "flag": "EXTREME_WIND_CLAIM",
                "detail": (
                    f"Claimed sustained winds of {wind_mph} mph. Sustained "
                    f"winds this high are extremely rare outside of hurricanes "
                    f"and the most intense derechos. Verify this is not a gust "
                    f"being reported as sustained."
                ),
                "severity": "CRITICAL",
            })
        elif wind_mph >= 55:
            warnings.append({
                "flag": "HIGH_WIND_CLAIM",
                "detail": (
                    f"Claimed sustained winds of {wind_mph} mph. This exceeds "
                    f"High Wind Warning criteria (58 mph). Verify this is "
                    f"sustained (not gusts) and comes from actual observations "
                    f"(not model output)."
                ),
                "severity": "HIGH",
            })
        elif wind_mph >= 40:
            warnings.append({
                "flag": "ELEVATED_WIND_CLAIM",
                "detail": (
                    f"Claimed sustained winds of {wind_mph} mph. Verify with "
                    f"mesonet observations. Common error: reporting gusts as "
                    f"sustained, or model winds as observed."
                ),
                "severity": "MODERATE",
            })

    if rh_pct is not None:
        if rh_pct <= 3:
            warnings.append({
                "flag": "EXTREME_RH_CLAIM",
                "detail": (
                    f"Claimed RH of {rh_pct}%. Sub-3% RH is genuinely extreme "
                    f"and does occur in the High Plains/Southwest. Verify with "
                    f"mesonet/ASOS — model RH may differ significantly from "
                    f"surface observations."
                ),
                "severity": "HIGH",
            })

    if description_words:
        hyperbolic = {
            "unprecedented", "never seen before", "worst ever",
            "catastrophic", "apocalyptic", "unsurvivable",
        }
        used_hyperbole = [
            w for w in description_words
            if w.lower() in hyperbolic
        ]
        if used_hyperbole:
            warnings.append({
                "flag": "HYPERBOLIC_LANGUAGE",
                "detail": (
                    f"Report uses strong language: {', '.join(used_hyperbole)}. "
                    f"Verify with get_fire_climatology that conditions truly "
                    f"exceed historical extremes for this location and season. "
                    f"'Unprecedented' should mean 'literally never observed at "
                    f"this station' — not just 'bad'."
                ),
                "severity": "MODERATE",
            })

    return warnings
