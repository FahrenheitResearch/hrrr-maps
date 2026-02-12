"""
Fuel Condition Assessment Module for AI Agents

Born from firefighter feedback: "Our fuels were the main highlight, not so much
the wind." Standard fire weather reports focus on wind, RH, and temperature.
But the #1 factor in Southern Plains winter fires is FUEL CONDITION — freeze-
dried prairie grass that has been further desiccated by abnormally warm temps
evaporating any residual snow moisture.

This module provides:
  - assess_fuel_conditions(): Full fuel assessment for a lat/lon point
  - get_recent_weather_history(): Extended METAR lookback (7-day trend analysis)
  - SEASONAL_FUEL_CONTEXT: Knowledge base for fuel behavior by season and region
  - IGNITION_SOURCES: Common ignition source awareness by region
  - get_ignition_risk(): Location-based ignition risk from highways, power lines, etc.

Key insight from the field:
  "It doesn't mention the current drought or highlight that this prairie grass
  is even more prone to burn after being freeze dried all winter long. The
  moisture from the recent snow is likely non existent since we have been
  rocking the 70s damn near every day, furthering the drying process even
  worse than it would be with the freezing temps."

Usage:
    from tools.agent_tools.fuel_conditions import (
        assess_fuel_conditions, get_recent_weather_history,
        get_ignition_risk, SEASONAL_FUEL_CONTEXT, IGNITION_SOURCES,
    )

    # Full assessment at a point
    result = assess_fuel_conditions(35.22, -101.83, station_id="KAMA")

    # Just the weather history
    history = get_recent_weather_history("KAMA", days_back=7)

    # Ignition risk near a location
    ignition = get_ignition_risk(35.22, -101.83)
"""
import math
from datetime import datetime, timedelta
from typing import Optional

from tools.agent_tools.external_data import (
    get_metar_observations,
    get_nearby_stations,
    get_drought_status,
    _fetch_json,
    _guess_nearby_states,
)


# =============================================================================
# Seasonal Fuel Context Knowledge Base
# =============================================================================

SEASONAL_FUEL_CONTEXT = {
    "southern_plains_winter": {
        "months": [11, 12, 1, 2, 3],
        "regions": ["TX_panhandle", "OK_western", "KS_western", "NM_eastern"],
        "lat_range": (33.0, 38.0),
        "lon_range": (-104.0, -97.0),
        "fuel_type": "Dormant prairie grass (blue grama, buffalo grass, sideoats grama)",
        "base_condition": (
            "Freeze-dried dormant grass — repeated freeze-thaw cycles break down "
            "cell structure making fuels extremely receptive to ignition. Unlike "
            "summer-cured grass, winter fuels have been through months of freezing "
            "that ruptures plant cells, creating a porous structure that dries "
            "faster and ignites more easily."
        ),
        "key_factors": [
            "Winter temps: freeze-dried grass is more flammable than summer-cured grass",
            "Snow moisture: evaporates quickly when temps hit 50s-60s, gone within 2-3 days of warm weather",
            "Persistent warm spells (>70F) in winter rapidly desiccate fuels beyond normal winter dryness",
            "No green-up until April-May — fuels are 100% dormant and cured",
            "Continuous grass fuels allow unimpeded fire spread across the landscape",
            "CRP grasslands and rangeland create miles of unbroken fuel beds",
            "Wind erosion of topsoil in drought creates additional surface litter",
        ],
        "critical_thresholds": {
            "days_above_60f": "3+ days above 60F after freeze = elevated fuel receptivity",
            "days_above_70f": "Any day above 70F in winter = extreme fuel desiccation",
            "precip_free_days": "7+ days without precip = critically dry fuels",
            "rh_below_15": "Daytime RH <15% = extreme fire behavior conditions",
            "dewpoint_below_20f": (
                "Dewpoints <20F = extremely dry air mass, fuels cannot absorb "
                "moisture even overnight"
            ),
        },
        "normal_temps_f": {
            "amarillo_feb": 52,
            "oklahoma_city_feb": 53,
            "lubbock_feb": 57,
            "dodge_city_feb": 47,
            "wichita_feb": 48,
        },
    },
    "southern_plains_spring": {
        "months": [4, 5],
        "regions": ["TX_panhandle", "OK_western", "KS_western", "NM_eastern"],
        "lat_range": (33.0, 38.0),
        "lon_range": (-104.0, -97.0),
        "fuel_type": "Transitioning — dormant grass beginning green-up",
        "base_condition": (
            "Mixed live/dead fuels during green-up — fire behavior depends on "
            "green-up progress. Dead grass still present under new green growth."
        ),
        "key_factors": [
            "Green-up progress varies by species and rainfall",
            "Dead grass still present under new green growth acts as ladder fuel",
            "Once green-up exceeds 30%, fire behavior moderates significantly",
            "Late spring dry spells can halt green-up and re-cure fuels",
            "Prescribed burns are common — escaped burns are frequent ignition source",
        ],
        "critical_thresholds": {
            "green_up_pct": "Below 30% green-up = fire behavior similar to winter",
            "days_above_80f": "3+ days above 80F = rapid curing of new growth",
            "precip_free_days": "10+ days = green-up stalls, dead fuel dominates",
        },
    },
    "southern_plains_summer": {
        "months": [6, 7, 8, 9, 10],
        "regions": ["TX_panhandle", "OK_western", "KS_western"],
        "lat_range": (33.0, 38.0),
        "lon_range": (-104.0, -97.0),
        "fuel_type": "Summer-cured grass if drought, green grass if normal precip",
        "base_condition": (
            "In normal years grass is green and fire risk is lower. In drought "
            "years grass cures early and becomes volatile. Summer heat + drought "
            "can create conditions similar to winter fire season."
        ),
        "key_factors": [
            "Drought determines whether grass is green or cured",
            "100+ degree days can cure green grass within a week",
            "Summer thunderstorms can provide ignition via lightning",
            "Dry thunderstorms (virga) are the worst: lightning + outflow wind, no rain",
        ],
        "critical_thresholds": {
            "days_above_100f": "3+ days above 100F = rapid curing even of green grass",
            "drought_level": "D2+ drought = assume fuels are largely cured by July",
        },
    },
    "california_fall_winter": {
        "months": [9, 10, 11, 12],
        "regions": ["socal", "norcal", "central_ca"],
        "lat_range": (32.0, 42.0),
        "lon_range": (-124.0, -114.0),
        "fuel_type": "Chaparral, dead grass, cured annual grasses",
        "base_condition": (
            "End of dry season — 5-6 months without rain, live fuel moisture "
            "at seasonal minimum. Annual grasses 100% cured since June."
        ),
        "key_factors": [
            "Santa Ana / Diablo winds create extreme fire weather",
            "Chaparral live fuel moisture drops below 60% = extreme fire behavior",
            "Dead grass 100% cured since June",
            "Urban-wildland interface is extremely compressed in SoCal",
            "Decades of fire suppression created massive fuel loads in chaparral",
            "Climate change extending fire season later into December-January",
        ],
        "critical_thresholds": {
            "live_fuel_moisture_pct": "Below 60% = critical chaparral fire conditions",
            "days_since_rain": "180+ days = peak dry season danger",
            "rh_below_10": "Santa Ana events can drop RH to 2-5%",
            "wind_above_50mph": "Santa Ana gusts >50mph = extreme fire weather",
        },
    },
    "front_range_winter": {
        "months": [11, 12, 1, 2, 3],
        "regions": ["front_range", "CO_foothills"],
        "lat_range": (38.0, 41.0),
        "lon_range": (-106.0, -104.0),
        "fuel_type": "Mixed grass/shrub/pine depending on elevation",
        "base_condition": (
            "Dormant grass at lower elevations, dry conifers at higher elevations. "
            "Chinook winds can create extreme drying events along the Front Range."
        ),
        "key_factors": [
            "Chinook (downslope) winds create extreme drying events",
            "Marshall Fire showed grass/shrub WUI fires can be catastrophic in winter",
            "Foothills WUI has continuous fuels from grassland into pine forest",
            "Open space and trail corridors create fuel continuity into neighborhoods",
            "December 2021 Marshall Fire: 1,000+ structures, wind-driven grass fire",
            "Palmer Divide grasslands are particularly exposed to downslope winds",
        ],
        "critical_thresholds": {
            "chinook_wind_kt": "35+ kt sustained = extreme downslope event",
            "rh_below_10": "Chinook events can drop RH below 5%",
            "days_above_55f": "Warm spells above 55F in winter = snow melt + fuel drying",
        },
        "normal_temps_f": {
            "denver_feb": 47,
            "boulder_feb": 48,
            "colorado_springs_feb": 45,
        },
    },
    "northern_rockies_summer": {
        "months": [6, 7, 8, 9],
        "regions": ["northern_rockies", "ID_central", "MT_western"],
        "lat_range": (44.0, 49.0),
        "lon_range": (-117.0, -110.0),
        "fuel_type": "Conifer forest, grass/sage understory",
        "base_condition": (
            "Summer dry season with timber fuels. Large fire potential depends "
            "on winter snowpack, spring rainfall, and summer drought duration."
        ),
        "key_factors": [
            "Low snowpack years = earlier fire season start",
            "Lightning is the primary natural ignition source",
            "Beetle-kill stands create extreme fire behavior",
            "Inversions trap smoke creating visibility and health issues",
        ],
        "critical_thresholds": {
            "eri_1000hr": "1000-hr fuel moisture below 13% = large fire potential",
            "days_above_90f": "Extended heat = rapid drying of timber fuels",
        },
    },
    "great_basin_summer": {
        "months": [5, 6, 7, 8, 9],
        "regions": ["great_basin", "NV_central", "UT_western"],
        "lat_range": (37.0, 43.0),
        "lon_range": (-120.0, -112.0),
        "fuel_type": "Sagebrush, cheatgrass, native bunchgrass",
        "base_condition": (
            "Cheatgrass invasion has fundamentally changed fire regimes. Annual "
            "grass cures by late June, creating continuous fine fuels across "
            "millions of acres that historically had sparse sagebrush."
        ),
        "key_factors": [
            "Cheatgrass (Bromus tectorum) cures early, burns hot, spreads fast",
            "Cheatgrass fire cycle prevents sagebrush recovery",
            "Wet springs = more cheatgrass = bigger fires the following summer",
            "Dry thunderstorms ignite millions of acres annually",
        ],
        "critical_thresholds": {
            "cheatgrass_cured": "Usually 100% cured by late June at lower elevations",
            "rh_below_10": "Combined with wind = extreme rates of spread in grass",
        },
    },
}


# =============================================================================
# Ignition Sources Knowledge Base
# =============================================================================

IGNITION_SOURCES = {
    "amarillo_tx": {
        "lat": 35.22,
        "lon": -101.83,
        "radius_km": 80,
        "primary": [
            {
                "source": "Commercial trucking (I-40/I-27 hub)",
                "risk": "HIGH",
                "detail": (
                    "Amarillo is a major trucking crossroads connecting the west. "
                    "Trucks with dragging chains, brake failures, and tire blowouts "
                    "on I-40 and I-27 are the #1 human ignition source. Winter "
                    "chains left on during warm weather create sparks on dry pavement."
                ),
            },
            {
                "source": "Power lines",
                "risk": "HIGH",
                "detail": (
                    "High winds cause line slap and equipment failures. Xcel Energy "
                    "territory. Wooden poles in rural areas are vulnerable to wind "
                    "damage."
                ),
            },
            {
                "source": "Agricultural equipment",
                "risk": "MODERATE",
                "detail": (
                    "Farm equipment in winter wheat fields and rangeland. Disc "
                    "plows striking rocks, combines during harvest, and equipment "
                    "dragging on roads."
                ),
            },
            {
                "source": "Railroad (BNSF)",
                "risk": "MODERATE",
                "detail": (
                    "BNSF mainline runs through the Panhandle. Brake sparks, "
                    "hot journal boxes, and track maintenance equipment."
                ),
            },
        ],
        "corridors": [
            {
                "name": "I-40",
                "direction": "E-W",
                "risk": "Major trucking ignition corridor — highest volume route",
            },
            {
                "name": "I-27",
                "direction": "N-S",
                "risk": "Connects Amarillo to Lubbock, heavy truck traffic",
            },
            {
                "name": "US-287",
                "direction": "NW-SE",
                "risk": "Connects Amarillo to DFW, significant truck traffic",
            },
            {
                "name": "US-66/I-40 Business",
                "direction": "E-W",
                "risk": "Historic route, urban corridor through Amarillo",
            },
        ],
    },
    "oklahoma_city_ok": {
        "lat": 35.47,
        "lon": -97.52,
        "radius_km": 80,
        "primary": [
            {
                "source": "I-40/I-35 interchange trucking",
                "risk": "HIGH",
                "detail": (
                    "Major interstate crossroads. I-40 E-W and I-35 N-S create "
                    "the highest volume interchange in Oklahoma."
                ),
            },
            {
                "source": "Power lines (OG&E territory)",
                "risk": "HIGH",
                "detail": (
                    "OG&E distribution lines in rural areas. High wind events "
                    "cause conductor slap and broken poles."
                ),
            },
            {
                "source": "Prescribed burns escaping",
                "risk": "MODERATE",
                "detail": (
                    "Oklahoma allows prescribed burning — escaped burns are a "
                    "common ignition source, especially in eastern OK cross-timbers."
                ),
            },
            {
                "source": "Railroad (BNSF east-west corridor)",
                "risk": "MODERATE",
                "detail": (
                    "BNSF and UP mainlines through central Oklahoma. Brake sparks "
                    "along rural rights-of-way."
                ),
            },
            {
                "source": "Arson / debris burning",
                "risk": "MODERATE",
                "detail": (
                    "Illegal debris burning in rural areas, especially during "
                    "burn bans. SE Oklahoma has historically high arson rates."
                ),
            },
        ],
        "corridors": [
            {
                "name": "I-40",
                "direction": "E-W",
                "risk": "Major cross-country trucking corridor",
            },
            {
                "name": "I-35",
                "direction": "N-S",
                "risk": "Connects Dallas to Wichita, heavy truck traffic",
            },
            {
                "name": "I-44 (Turner Turnpike)",
                "direction": "NE",
                "risk": "Connects OKC to Tulsa, moderate truck volume",
            },
            {
                "name": "US-270/US-281",
                "direction": "NW",
                "risk": "Rural corridor into western OK, equipment/ag ignitions",
            },
        ],
    },
    "lubbock_tx": {
        "lat": 33.58,
        "lon": -101.85,
        "radius_km": 80,
        "primary": [
            {
                "source": "I-27 trucking corridor",
                "risk": "HIGH",
                "detail": (
                    "I-27 connects Amarillo to Lubbock through open grassland. "
                    "Truck-related ignitions are frequent."
                ),
            },
            {
                "source": "Cotton gin fires",
                "risk": "MODERATE",
                "detail": (
                    "Lubbock is the center of Texas cotton country. Cotton gins "
                    "and module storage create ignition risk during processing season."
                ),
            },
            {
                "source": "Agricultural equipment",
                "risk": "MODERATE",
                "detail": (
                    "Extensive farming operations in cotton, wheat, and grain sorghum. "
                    "Equipment sparks on rocky soils."
                ),
            },
            {
                "source": "Power lines (Lubbock Power & Light / Xcel)",
                "risk": "HIGH",
                "detail": (
                    "High winds in the South Plains frequently cause power line "
                    "failures in rural areas."
                ),
            },
        ],
        "corridors": [
            {
                "name": "I-27",
                "direction": "N-S",
                "risk": "Primary north-south corridor through open grassland",
            },
            {
                "name": "US-84",
                "direction": "NW-SE",
                "risk": "Rural highway through ranchland to Post/Snyder",
            },
            {
                "name": "US-62/82 (Marsha Sharp Fwy)",
                "direction": "E-W",
                "risk": "Connects Lubbock eastward through cotton country",
            },
        ],
    },
    "denver_co": {
        "lat": 39.74,
        "lon": -104.99,
        "radius_km": 60,
        "primary": [
            {
                "source": "Downed power lines (Xcel Energy)",
                "risk": "HIGH",
                "detail": (
                    "Chinook wind events cause extensive power line damage along "
                    "the Front Range. The Marshall Fire (Dec 2021) was ignited by "
                    "downed power lines in extreme winds."
                ),
            },
            {
                "source": "I-25 corridor traffic",
                "risk": "MODERATE",
                "detail": (
                    "I-25 runs along the base of the foothills. Vehicle-related "
                    "ignitions along the urban-wildland interface."
                ),
            },
            {
                "source": "Campfires / recreational",
                "risk": "MODERATE",
                "detail": (
                    "Heavy recreational use of foothills open space and mountain "
                    "parks. Illegal campfires in fire-banned areas."
                ),
            },
        ],
        "corridors": [
            {
                "name": "I-25",
                "direction": "N-S",
                "risk": "Foothills corridor, WUI interface from Colorado Springs to Ft Collins",
            },
            {
                "name": "I-70",
                "direction": "E-W",
                "risk": "Mountain corridor, vehicle ignitions in steep terrain",
            },
            {
                "name": "US-36 (Boulder Turnpike)",
                "direction": "NW",
                "risk": "Marshall Fire corridor, connects Denver to Boulder along WUI",
            },
        ],
    },
    "wichita_ks": {
        "lat": 37.69,
        "lon": -97.34,
        "radius_km": 80,
        "primary": [
            {
                "source": "I-35 trucking",
                "risk": "HIGH",
                "detail": "I-35 corridor from Oklahoma to Nebraska, heavy truck traffic through open prairie.",
            },
            {
                "source": "Prescribed burns (Flint Hills)",
                "risk": "HIGH",
                "detail": (
                    "The Flint Hills east of Wichita have the largest remaining "
                    "tallgrass prairie in North America. Annual spring prescribed "
                    "burns are essential for prairie management but frequently "
                    "escape, especially during unexpected wind shifts."
                ),
            },
            {
                "source": "Power lines (Evergy territory)",
                "risk": "MODERATE",
                "detail": "Wind-related power line failures in rural areas.",
            },
            {
                "source": "Railroad (BNSF/UP)",
                "risk": "MODERATE",
                "detail": "Multiple rail lines converge at Wichita. Brake sparks in grass along rights-of-way.",
            },
        ],
        "corridors": [
            {
                "name": "I-35",
                "direction": "N-S",
                "risk": "Major trucking corridor through open prairie",
            },
            {
                "name": "I-135",
                "direction": "N-S",
                "risk": "Connects Wichita to Salina through grassland",
            },
            {
                "name": "US-54",
                "direction": "E-W",
                "risk": "Rural highway to Liberal, open range country",
            },
            {
                "name": "Kansas Turnpike (I-35)",
                "direction": "NE",
                "risk": "Connects to Topeka/KC, Flint Hills prairie",
            },
        ],
    },
    "midland_odessa_tx": {
        "lat": 31.99,
        "lon": -102.08,
        "radius_km": 80,
        "primary": [
            {
                "source": "Oil field equipment",
                "risk": "HIGH",
                "detail": (
                    "Permian Basin is the most active oil field in the US. Pump "
                    "jacks, flare stacks, welding, and heavy equipment create "
                    "constant ignition potential in dry grass."
                ),
            },
            {
                "source": "I-20 trucking",
                "risk": "HIGH",
                "detail": "Heavy truck traffic serving the oil field, plus cross-country commercial traffic.",
            },
            {
                "source": "Pipeline construction/maintenance",
                "risk": "MODERATE",
                "detail": "Continuous pipeline construction and maintenance in the Permian Basin.",
            },
        ],
        "corridors": [
            {
                "name": "I-20",
                "direction": "E-W",
                "risk": "Major trucking corridor through oil country",
            },
            {
                "name": "TX-349/TX-158",
                "direction": "Various",
                "risk": "Oil field service roads, heavy equipment traffic",
            },
        ],
    },
}

# ---------------------------------------------------------------------------
# Merge regional ignition profiles from data/ directory
# ---------------------------------------------------------------------------
def _normalize_ignition_entry(key, val, terrain_profiles=None):
    """Normalize an ignition source entry to standard format.

    Standard format: {lat, lon, radius_km, primary: [...], corridors: [...]}
    """
    if not isinstance(val, dict):
        return None
    # Skip non-city entries (e.g. 'trucking_corridors', 'region_overview')
    if "primary" not in val and "primary_sources" not in val:
        return None
    normalized = {}
    # Get coordinates — try entry first, then terrain profiles
    if "lat" in val and "lon" in val:
        normalized["lat"] = val["lat"]
        normalized["lon"] = val["lon"]
    elif terrain_profiles and key in terrain_profiles:
        center = terrain_profiles[key].get("center", (0, 0))
        normalized["lat"] = center[0]
        normalized["lon"] = center[1]
    else:
        return None  # Can't use without coordinates
    normalized["radius_km"] = val.get("radius_km", 80)
    # Normalize primary sources key
    normalized["primary"] = val.get("primary", val.get("primary_sources", []))
    # Normalize corridors
    corridors = val.get("corridors", [])
    if not corridors:
        corridors = val.get("highway_corridors", [])
        corridors.extend(val.get("railroad_corridors", []))
    normalized["corridors"] = corridors
    return normalized


def _merge_regional_ignition():
    """Load and merge all regional ignition sources into IGNITION_SOURCES."""
    # Load terrain profiles to get coordinates for entries missing lat/lon
    _terrain_mods = [
        ("agent_tools.data.california_profiles", "CA_TERRAIN_PROFILES"),
        ("agent_tools.data.pnw_rockies_profiles", "PNW_TERRAIN_PROFILES"),
        ("agent_tools.data.colorado_basin_profiles", "CO_BASIN_TERRAIN_PROFILES"),
        ("agent_tools.data.southwest_profiles", "SW_TERRAIN_PROFILES"),
        ("agent_tools.data.southern_plains_profiles", "PLAINS_TERRAIN_PROFILES"),
        ("agent_tools.data.southeast_misc_profiles", "SE_MISC_TERRAIN_PROFILES"),
    ]
    all_terrain = {}
    for mod_name, attr_name in _terrain_mods:
        try:
            mod = __import__(mod_name, fromlist=[attr_name])
            all_terrain.update(getattr(mod, attr_name, {}))
        except ImportError:
            pass

    _regional_modules = [
        ("agent_tools.data.california_profiles", "CA_IGNITION_SOURCES"),
        ("agent_tools.data.pnw_rockies_profiles", "PNW_IGNITION_SOURCES"),
        ("agent_tools.data.colorado_basin_profiles", "CO_BASIN_IGNITION_SOURCES"),
        ("agent_tools.data.southwest_profiles", "SW_IGNITION_SOURCES"),
        ("agent_tools.data.southern_plains_profiles", "PLAINS_IGNITION_SOURCES"),
        ("agent_tools.data.southeast_misc_profiles", "SE_MISC_IGNITION_SOURCES"),
    ]
    count = 0
    for mod_name, attr_name in _regional_modules:
        try:
            mod = __import__(mod_name, fromlist=[attr_name])
            sources = getattr(mod, attr_name, {})
            for key, val in sources.items():
                if key in IGNITION_SOURCES:
                    continue
                normalized = _normalize_ignition_entry(key, val, all_terrain)
                if normalized:
                    IGNITION_SOURCES[key] = normalized
                    count += 1
        except ImportError:
            pass
    return count

_merge_regional_ignition()


# Interstate highway database for proximity-based ignition risk
_INTERSTATE_CORRIDORS = [
    {"name": "I-40", "segments": [
        {"lat1": 35.15, "lon1": -106.65, "lat2": 35.22, "lon2": -101.83},  # ABQ to Amarillo
        {"lat1": 35.22, "lon1": -101.83, "lat2": 35.47, "lon2": -97.52},  # Amarillo to OKC
        {"lat1": 35.47, "lon1": -97.52, "lat2": 35.15, "lon2": -89.97},  # OKC to Memphis
    ]},
    {"name": "I-35", "segments": [
        {"lat1": 37.69, "lon1": -97.34, "lat2": 35.47, "lon2": -97.52},  # Wichita to OKC
        {"lat1": 35.47, "lon1": -97.52, "lat2": 32.78, "lon2": -96.80},  # OKC to Dallas
    ]},
    {"name": "I-27", "segments": [
        {"lat1": 35.22, "lon1": -101.83, "lat2": 33.58, "lon2": -101.85},  # Amarillo to Lubbock
    ]},
    {"name": "I-25", "segments": [
        {"lat1": 40.59, "lon1": -105.08, "lat2": 39.74, "lon2": -104.99},  # Ft Collins to Denver
        {"lat1": 39.74, "lon1": -104.99, "lat2": 38.83, "lon2": -104.82},  # Denver to Co Springs
        {"lat1": 38.83, "lon1": -104.82, "lat2": 36.72, "lon2": -105.97},  # Co Springs to Santa Fe
    ]},
    {"name": "I-20", "segments": [
        {"lat1": 32.45, "lon1": -100.44, "lat2": 31.99, "lon2": -102.08},  # Abilene to Midland
        {"lat1": 31.99, "lon1": -102.08, "lat2": 31.76, "lon2": -106.44},  # Midland to El Paso
    ]},
    {"name": "I-10", "segments": [
        {"lat1": 31.76, "lon1": -106.44, "lat2": 32.22, "lon2": -110.93},  # El Paso to Tucson
        {"lat1": 32.22, "lon1": -110.93, "lat2": 33.45, "lon2": -112.07},  # Tucson to Phoenix
    ]},
    {"name": "I-70", "segments": [
        {"lat1": 39.74, "lon1": -104.99, "lat2": 38.57, "lon2": -109.55},  # Denver to Grand Junction
    ]},
    {"name": "US-287", "segments": [
        {"lat1": 35.22, "lon1": -101.83, "lat2": 34.20, "lon2": -98.39},  # Amarillo to Wichita Falls
    ]},
]


# February normal high temperatures for reference cities (F)
_NORMAL_TEMPS_F = {
    "KAMA": {"city": "Amarillo, TX", "feb_high": 52, "jan_high": 49, "dec_high": 50, "mar_high": 60},
    "KOKC": {"city": "Oklahoma City, OK", "feb_high": 53, "jan_high": 49, "dec_high": 50, "mar_high": 62},
    "KDEN": {"city": "Denver, CO", "feb_high": 47, "jan_high": 44, "dec_high": 44, "mar_high": 54},
    "KLBB": {"city": "Lubbock, TX", "feb_high": 57, "jan_high": 53, "dec_high": 54, "mar_high": 65},
    "KDDC": {"city": "Dodge City, KS", "feb_high": 47, "jan_high": 42, "dec_high": 43, "mar_high": 56},
    "KICT": {"city": "Wichita, KS", "feb_high": 48, "jan_high": 42, "dec_high": 44, "mar_high": 58},
    "KTUL": {"city": "Tulsa, OK", "feb_high": 53, "jan_high": 47, "dec_high": 49, "mar_high": 62},
    "KGCK": {"city": "Garden City, KS", "feb_high": 49, "jan_high": 44, "dec_high": 45, "mar_high": 58},
    "KABI": {"city": "Abilene, TX", "feb_high": 59, "jan_high": 55, "dec_high": 56, "mar_high": 67},
    "KMAF": {"city": "Midland, TX", "feb_high": 61, "jan_high": 57, "dec_high": 57, "mar_high": 70},
    "KCDS": {"city": "Childress, TX", "feb_high": 56, "jan_high": 52, "dec_high": 52, "mar_high": 65},
    "KGAG": {"city": "Gage, OK", "feb_high": 49, "jan_high": 44, "dec_high": 45, "mar_high": 57},
    "KWDG": {"city": "Enid, OK", "feb_high": 50, "jan_high": 45, "dec_high": 47, "mar_high": 60},
    "KSPS": {"city": "Wichita Falls, TX", "feb_high": 56, "jan_high": 52, "dec_high": 53, "mar_high": 65},
}


# =============================================================================
# Core Functions
# =============================================================================

def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Haversine distance in km between two lat/lon points."""
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(lat1))
         * math.cos(math.radians(lat2))
         * math.sin(dlon / 2) ** 2)
    return 6371 * 2 * math.asin(math.sqrt(a))


def _point_to_segment_distance_km(
    lat: float, lon: float,
    lat1: float, lon1: float, lat2: float, lon2: float,
) -> float:
    """Approximate minimum distance (km) from a point to a line segment.

    Uses a simple projection onto the segment in lat/lon space (works well
    enough for short segments at mid-latitudes).
    """
    # Vector from segment start to end
    dx = lon2 - lon1
    dy = lat2 - lat1
    seg_len_sq = dx * dx + dy * dy

    if seg_len_sq < 1e-12:
        return _haversine_km(lat, lon, lat1, lon1)

    # Project point onto segment, clamped to [0, 1]
    t = max(0.0, min(1.0, ((lon - lon1) * dx + (lat - lat1) * dy) / seg_len_sq))
    proj_lon = lon1 + t * dx
    proj_lat = lat1 + t * dy

    return _haversine_km(lat, lon, proj_lat, proj_lon)


def _c_to_f(temp_c: float) -> float:
    """Celsius to Fahrenheit."""
    return temp_c * 9.0 / 5.0 + 32.0


def _f_to_c(temp_f: float) -> float:
    """Fahrenheit to Celsius."""
    return (temp_f - 32.0) * 5.0 / 9.0


def _get_month_key(month: int) -> str:
    """Map month number to the normal-temp dict key suffix."""
    mapping = {1: "jan", 2: "feb", 3: "mar", 4: "apr", 12: "dec", 11: "nov"}
    return mapping.get(month, "feb")


def _get_normal_high_f(station_id: str, month: int) -> Optional[float]:
    """Look up the climatological normal high temp for a station and month."""
    sid = station_id.upper().strip()
    if not sid.startswith("K"):
        sid = "K" + sid
    info = _NORMAL_TEMPS_F.get(sid)
    if not info:
        return None
    key = f"{_get_month_key(month)}_high"
    return info.get(key)


def _determine_season(lat: float, lon: float, month: int) -> tuple:
    """Determine the seasonal fuel context key and season name.

    Returns (context_key, season_name) or (None, season_name) if no
    matching entry in SEASONAL_FUEL_CONTEXT.
    """
    season_name = "unknown"
    if month in [12, 1, 2]:
        season_name = "winter"
    elif month in [3, 4, 5]:
        season_name = "spring"
    elif month in [6, 7, 8]:
        season_name = "summer"
    elif month in [9, 10, 11]:
        season_name = "fall"

    # Try to match a specific context entry
    for key, ctx in SEASONAL_FUEL_CONTEXT.items():
        if month not in ctx.get("months", []):
            continue
        lat_range = ctx.get("lat_range")
        lon_range = ctx.get("lon_range")
        if lat_range and lon_range:
            if lat_range[0] <= lat <= lat_range[1] and lon_range[0] <= lon <= lon_range[1]:
                return key, season_name
    return None, season_name


def _estimate_fuel_moisture(
    warm_days_60f: int,
    warm_days_70f: int,
    precip_7d_inches: float,
    days_since_precip: int,
    avg_rh_daytime: float,
    avg_dewpoint_f: float,
    season: str,
    drought_level: Optional[str] = None,
) -> tuple:
    """Estimate dead fuel moisture category and percentage range.

    Uses a heuristic based on recent weather, season, and drought status
    to estimate 1-hour dead fuel moisture in fine grass fuels. This is an
    approximation — actual fuel moisture requires field sampling or NFDRS
    station data.

    Returns:
        (category, low_pct, high_pct)
        category: one of "critically_low", "very_low", "low", "moderate", "adequate"
    """
    # Start with base score — higher = drier
    score = 0.0

    # Warm days drying effect (winter/spring only)
    if season in ("winter", "spring"):
        score += warm_days_60f * 3.0
        score += warm_days_70f * 5.0  # Extra credit for extreme warmth in winter

    # Precipitation (recent rain helps, lack of rain hurts)
    if precip_7d_inches >= 0.5:
        score -= 15.0
    elif precip_7d_inches >= 0.25:
        score -= 8.0
    elif precip_7d_inches >= 0.1:
        score -= 3.0

    # Days since measurable precipitation
    if days_since_precip >= 14:
        score += 15.0
    elif days_since_precip >= 7:
        score += 8.0
    elif days_since_precip >= 3:
        score += 3.0

    # Low RH accelerates drying
    if avg_rh_daytime < 10:
        score += 15.0
    elif avg_rh_daytime < 15:
        score += 10.0
    elif avg_rh_daytime < 20:
        score += 5.0
    elif avg_rh_daytime < 30:
        score += 2.0

    # Dry dewpoints — fuels can't recover overnight
    if avg_dewpoint_f < 10:
        score += 10.0
    elif avg_dewpoint_f < 20:
        score += 6.0
    elif avg_dewpoint_f < 30:
        score += 3.0

    # Drought amplifier
    if drought_level:
        drought_scores = {"D0": 2, "D1": 5, "D2": 10, "D3": 15, "D4": 20}
        level = drought_level.upper().strip()
        score += drought_scores.get(level, 0)

    # Season baseline — winter freeze-dried fuels start drier
    if season == "winter":
        score += 8.0  # Freeze-dried fuel baseline bonus
    elif season == "fall":
        score += 3.0  # End of growing season

    # Classify
    if score >= 45:
        return ("critically_low", 2, 5)
    elif score >= 30:
        return ("very_low", 5, 8)
    elif score >= 18:
        return ("low", 8, 12)
    elif score >= 8:
        return ("moderate", 12, 18)
    else:
        return ("adequate", 18, 30)


def get_recent_weather_history(
    station_id: str,
    days_back: int = 7,
    network: Optional[str] = None,
) -> dict:
    """Pull METAR data for a station over the last N days and compute statistics.

    Queries the IEM ASOS API for historical observations, then computes:
      - Daily high/low temps (F)
      - Daily minimum RH
      - Daily precipitation totals
      - Daily average dewpoint
      - Trend analysis (warming? drying? wetting?)

    Args:
        station_id: ICAO station ID (e.g. "KAMA", "KOKC", "AMA")
        days_back: Number of days to look back. Default 7.
        network: IEM network override (e.g. "TX_ASOS"). Auto-detected if None.

    Returns:
        Dict with raw observations and computed daily/summary statistics.
    """
    now = datetime.utcnow()
    start = now - timedelta(days=days_back)

    start_str = start.strftime("%Y-%m-%d %H:%M")
    end_str = now.strftime("%Y-%m-%d %H:%M")

    try:
        result = get_metar_observations(
            stations=[station_id],
            start=start_str,
            end=end_str,
            network=network,
        )
    except Exception as e:
        return {
            "error": f"Failed to fetch METAR data for {station_id}: {e}",
            "station_id": station_id,
            "days_back": days_back,
        }

    obs_list = result.get("data", [])
    if not obs_list:
        return {
            "station_id": station_id,
            "days_back": days_back,
            "obs_count": 0,
            "error": "No observations returned",
            "daily": [],
            "summary": {},
        }

    # Organize observations by date (UTC)
    daily_obs = {}
    for obs in obs_list:
        ts = obs.get("utc_valid", obs.get("valid", ""))
        if not ts:
            continue

        # Parse timestamp
        try:
            if "T" in ts:
                obs_dt = datetime.strptime(ts.replace("Z", ""), "%Y-%m-%dT%H:%M")
            else:
                obs_dt = datetime.strptime(ts, "%Y-%m-%d %H:%M")
        except (ValueError, TypeError):
            continue

        date_key = obs_dt.strftime("%Y-%m-%d")
        if date_key not in daily_obs:
            daily_obs[date_key] = []
        daily_obs[date_key].append({
            "time": obs_dt,
            "hour_utc": obs_dt.hour,
            "tmpf": _safe_float(obs.get("tmpf")),
            "dwpf": _safe_float(obs.get("dwpf")),
            "relh": _safe_float(obs.get("relh")),
            "sknt": _safe_float(obs.get("sknt")),
            "gust": _safe_float(obs.get("gust_sknt", obs.get("gust"))),
            "drct": _safe_float(obs.get("drct")),
            "p01i": _safe_float(obs.get("p01i")),
            "vsby": _safe_float(obs.get("vsby")),
        })

    # Compute daily stats
    daily_stats = []
    all_temps = []
    all_rh = []
    all_dewpoints = []
    total_precip = 0.0

    for date_key in sorted(daily_obs.keys()):
        day_data = daily_obs[date_key]
        temps = [o["tmpf"] for o in day_data if o["tmpf"] is not None]
        rhs = [o["relh"] for o in day_data if o["relh"] is not None]
        dewpoints = [o["dwpf"] for o in day_data if o["dwpf"] is not None]
        winds = [o["sknt"] for o in day_data if o["sknt"] is not None]
        gusts = [o["gust"] for o in day_data if o["gust"] is not None]
        precips = [o["p01i"] for o in day_data if o["p01i"] is not None and o["p01i"] >= 0]

        # Filter daytime RH (12-00 UTC ~ roughly 6am-6pm CST for central US)
        daytime_rhs = [
            o["relh"] for o in day_data
            if o["relh"] is not None and 15 <= o["hour_utc"] <= 23
        ]

        day_high = max(temps) if temps else None
        day_low = min(temps) if temps else None
        day_min_rh = min(rhs) if rhs else None
        day_daytime_avg_rh = (sum(daytime_rhs) / len(daytime_rhs)) if daytime_rhs else None
        day_avg_dewpoint = (sum(dewpoints) / len(dewpoints)) if dewpoints else None
        day_max_wind = max(winds) if winds else None
        day_max_gust = max(gusts) if gusts else None
        day_precip = sum(precips) if precips else 0.0

        daily_entry = {
            "date": date_key,
            "obs_count": len(day_data),
            "high_f": round(day_high, 1) if day_high is not None else None,
            "low_f": round(day_low, 1) if day_low is not None else None,
            "min_rh": round(day_min_rh, 1) if day_min_rh is not None else None,
            "daytime_avg_rh": round(day_daytime_avg_rh, 1) if day_daytime_avg_rh is not None else None,
            "avg_dewpoint_f": round(day_avg_dewpoint, 1) if day_avg_dewpoint is not None else None,
            "max_wind_kt": round(day_max_wind, 1) if day_max_wind is not None else None,
            "max_gust_kt": round(day_max_gust, 1) if day_max_gust is not None else None,
            "precip_in": round(day_precip, 2),
        }
        daily_stats.append(daily_entry)

        if day_high is not None:
            all_temps.append(day_high)
        if day_min_rh is not None:
            all_rh.append(day_min_rh)
        if day_avg_dewpoint is not None:
            all_dewpoints.append(day_avg_dewpoint)
        total_precip += day_precip

    # Count days above temperature thresholds
    warm_days_60 = sum(1 for t in all_temps if t > 60)
    warm_days_70 = sum(1 for t in all_temps if t > 70)
    warm_days_80 = sum(1 for t in all_temps if t > 80)

    # Find days since measurable precipitation
    days_since_precip = _compute_days_since_precip(daily_stats)

    # Trend analysis (simple: compare first half vs second half)
    trend = _compute_trends(daily_stats)

    # Max temp in period
    max_temp = max(all_temps) if all_temps else None

    # Average daytime RH
    daytime_rh_vals = [d["daytime_avg_rh"] for d in daily_stats if d["daytime_avg_rh"] is not None]
    avg_daytime_rh = (sum(daytime_rh_vals) / len(daytime_rh_vals)) if daytime_rh_vals else None

    # Min RH across all days
    min_rh_overall = min(all_rh) if all_rh else None

    # Average dewpoint
    avg_dewpoint = (sum(all_dewpoints) / len(all_dewpoints)) if all_dewpoints else None

    summary = {
        "period_days": days_back,
        "obs_count": len(obs_list),
        "daily_count": len(daily_stats),
        "warm_days_above_60f": warm_days_60,
        "warm_days_above_70f": warm_days_70,
        "warm_days_above_80f": warm_days_80,
        "max_temp_f": round(max_temp, 1) if max_temp is not None else None,
        "total_precip_in": round(total_precip, 2),
        "days_since_measurable_precip": days_since_precip,
        "avg_daytime_rh": round(avg_daytime_rh, 1) if avg_daytime_rh is not None else None,
        "min_rh": round(min_rh_overall, 1) if min_rh_overall is not None else None,
        "avg_dewpoint_f": round(avg_dewpoint, 1) if avg_dewpoint is not None else None,
        "trends": trend,
    }

    return {
        "station_id": station_id,
        "days_back": days_back,
        "start": start_str,
        "end": end_str,
        "obs_count": len(obs_list),
        "daily": daily_stats,
        "summary": summary,
    }


def assess_fuel_conditions(
    lat: float,
    lon: float,
    station_id: Optional[str] = None,
    base_url: str = "http://127.0.0.1:5565",
    days_back: int = 7,
) -> dict:
    """Full fuel condition assessment for a lat/lon point.

    Gathers data from multiple sources to assess fuel conditions:
      - Recent METAR history (7 days) for temperature, RH, precip, dewpoint trends
      - Drought status (USDM)
      - Seasonal context (fuel type, curing state, vulnerability)
      - Comparison to climatological normals
      - Fuel moisture estimate
      - Fire behavior implications

    The key insight driving this function: FUELS are often the main story in
    fire weather, not wind. Winter freeze-dried prairie grass + persistent warm
    temps evaporating snow moisture = extremely receptive fuels. Our reports
    historically focused too much on wind and not enough on fuel conditions.

    Args:
        lat: Latitude of the assessment point.
        lon: Longitude of the assessment point.
        station_id: ICAO station ID for METAR data (e.g. "KAMA"). If None,
            finds the nearest station automatically.
        base_url: Dashboard API URL (unused currently, reserved for future
            model-based fuel moisture products).
        days_back: Number of days of METAR history to pull. Default 7.

    Returns:
        Dict with comprehensive fuel condition assessment including:
        - location, station info
        - fuel_assessment (season, context, weather impact, moisture estimate)
        - drought status
        - fire_behavior_implications
        - comparison_to_normal
    """
    now = datetime.utcnow()
    month = now.month

    # --- Find station if not provided ---
    station_info = None
    if station_id is None:
        try:
            nearby = get_nearby_stations(lat, lon, radius_km=100)
            if nearby:
                station_info = nearby[0]
                station_id = station_info["id"]
                # Ensure ICAO prefix for METAR queries
                if len(station_id) == 3:
                    station_id = "K" + station_id
            else:
                station_id = None
        except Exception:
            station_id = None

    if station_id is None:
        return {
            "error": "No ASOS/AWOS station found within 100km",
            "location": {"lat": lat, "lon": lon},
        }

    # --- Get weather history ---
    history = get_recent_weather_history(station_id, days_back=days_back)
    summary = history.get("summary", {})

    # --- Get drought status ---
    drought_info = _get_drought_for_point(lat, lon)

    # --- Determine season and fuel context ---
    context_key, season_name = _determine_season(lat, lon, month)
    fuel_ctx = SEASONAL_FUEL_CONTEXT.get(context_key, {})

    # --- Build seasonal context description ---
    if fuel_ctx:
        seasonal_context = fuel_ctx.get("base_condition", "")
    else:
        seasonal_context = _generic_seasonal_context(season_name, lat, lon)

    # --- Extract weather summary values ---
    warm_days_60 = summary.get("warm_days_above_60f", 0)
    warm_days_70 = summary.get("warm_days_above_70f", 0)
    max_temp_f = summary.get("max_temp_f")
    total_precip = summary.get("total_precip_in", 0.0)
    days_since_precip = summary.get("days_since_measurable_precip", 0)
    avg_rh_daytime = summary.get("avg_daytime_rh")
    min_rh = summary.get("min_rh")
    avg_dewpoint_f = summary.get("avg_dewpoint_f")

    # --- Estimate fuel moisture ---
    drought_level = drought_info.get("level") if drought_info else None

    fuel_cat, fm_low, fm_high = _estimate_fuel_moisture(
        warm_days_60f=warm_days_60,
        warm_days_70f=warm_days_70,
        precip_7d_inches=total_precip,
        days_since_precip=days_since_precip,
        avg_rh_daytime=avg_rh_daytime if avg_rh_daytime is not None else 30.0,
        avg_dewpoint_f=avg_dewpoint_f if avg_dewpoint_f is not None else 25.0,
        season=season_name,
        drought_level=drought_level,
    )

    # --- Build the explanation ---
    explanation = _build_fuel_explanation(
        warm_days_60, warm_days_70, max_temp_f, total_precip,
        days_since_precip, avg_rh_daytime, min_rh, avg_dewpoint_f,
        fuel_cat, fm_low, fm_high, season_name,
    )

    # --- Comparison to normal ---
    normal_high = _get_normal_high_f(station_id, month)
    temp_anomaly_f = None
    is_abnormal = False
    anomaly_context = ""
    if normal_high is not None and max_temp_f is not None:
        temp_anomaly_f = round(max_temp_f - normal_high, 1)
        is_abnormal = abs(temp_anomaly_f) >= 15
        month_name = now.strftime("%B")
        if temp_anomaly_f > 0:
            anomaly_context = (
                f"Max temperature of {max_temp_f}F is {temp_anomaly_f}F above the "
                f"{month_name} normal high of {normal_high}F for the area"
            )
        else:
            anomaly_context = (
                f"Max temperature of {max_temp_f}F is {abs(temp_anomaly_f)}F below the "
                f"{month_name} normal high of {normal_high}F for the area"
            )

    # --- Fire behavior implications ---
    implications = _build_fire_behavior_implications(
        fuel_cat, fm_low, fm_high, season_name, warm_days_70,
        days_since_precip, avg_rh_daytime, drought_level,
        fuel_ctx,
    )

    # --- Assemble result ---
    result = {
        "location": {"lat": lat, "lon": lon},
        "station": {
            "id": station_id,
            "name": station_info.get("name", station_id) if station_info else station_id,
            "distance_km": station_info.get("distance_km") if station_info else None,
        },
        "assessment_time_utc": now.strftime("%Y-%m-%dT%H:%MZ"),
        "fuel_assessment": {
            "season": season_name,
            "seasonal_fuel_context_key": context_key,
            "seasonal_context": seasonal_context,
            "fuel_type": fuel_ctx.get("fuel_type", "Unknown — no regional fuel data available"),
            "key_factors": fuel_ctx.get("key_factors", []),
            "critical_thresholds": fuel_ctx.get("critical_thresholds", {}),
            "recent_weather_impact": {
                "warm_days_above_60f_7d": warm_days_60,
                "warm_days_above_70f_7d": warm_days_70,
                "max_temp_7d_f": max_temp_f,
                "precip_7d_inches": round(total_precip, 2),
                "days_since_measurable_precip": days_since_precip,
                "avg_rh_daytime_7d": avg_rh_daytime,
                "min_rh_7d": min_rh,
                "avg_dewpoint_7d_f": avg_dewpoint_f,
            },
            "fuel_moisture_estimate": fuel_cat,
            "fuel_moisture_range_pct": f"{fm_low}-{fm_high}%",
            "explanation": explanation,
        },
        "drought": drought_info,
        "fire_behavior_implications": implications,
        "comparison_to_normal": {
            "normal_high_f": normal_high,
            "max_observed_f": max_temp_f,
            "temp_anomaly_f": temp_anomaly_f,
            "is_abnormal": is_abnormal,
            "context": anomaly_context,
        },
        "weather_history": {
            "daily": history.get("daily", []),
            "summary": summary,
            "trends": summary.get("trends", {}),
        },
    }

    return result


def get_ignition_risk(
    lat: float,
    lon: float,
    city_name: Optional[str] = None,
    search_radius_km: float = 100,
) -> dict:
    """Get ignition sources and corridors relevant to a location.

    Checks proximity to known ignition source areas and interstate highway
    corridors. Returns relevant ignition risk information.

    Args:
        lat: Latitude
        lon: Longitude
        city_name: Optional city name to search for in IGNITION_SOURCES.
            If None, searches by proximity.
        search_radius_km: Maximum distance to search for ignition data.

    Returns:
        Dict with ignition sources, corridors, and highway proximity info.
    """
    # --- Match by city name if provided ---
    if city_name:
        city_key = city_name.lower().replace(" ", "_").replace(",", "")
        for key, data in IGNITION_SOURCES.items():
            if city_key in key or key in city_key:
                dist = _haversine_km(lat, lon, data["lat"], data["lon"])
                return {
                    "location": {"lat": lat, "lon": lon},
                    "matched_city": key,
                    "distance_to_city_km": round(dist, 1),
                    "sources": data["primary"],
                    "corridors": data.get("corridors", []),
                    "nearby_interstates": _find_nearby_interstates(lat, lon, max_dist_km=50),
                }

    # --- Match by proximity ---
    nearest_city = None
    nearest_dist = float("inf")

    for key, data in IGNITION_SOURCES.items():
        dist = _haversine_km(lat, lon, data["lat"], data["lon"])
        radius = data.get("radius_km", 80)
        if dist <= radius and dist < nearest_dist:
            nearest_city = key
            nearest_dist = dist

    # Even if no city match, always return interstate proximity
    nearby_interstates = _find_nearby_interstates(lat, lon, max_dist_km=50)

    if nearest_city:
        data = IGNITION_SOURCES[nearest_city]
        return {
            "location": {"lat": lat, "lon": lon},
            "matched_city": nearest_city,
            "distance_to_city_km": round(nearest_dist, 1),
            "sources": data["primary"],
            "corridors": data.get("corridors", []),
            "nearby_interstates": nearby_interstates,
        }

    # No city match — return highway-only assessment
    general_sources = [
        {
            "source": "Power lines",
            "risk": "MODERATE",
            "detail": (
                "Power line failures are a common ignition source in any rural "
                "area with overhead distribution lines, especially during high "
                "wind events."
            ),
        },
        {
            "source": "Highway traffic",
            "risk": "MODERATE" if nearby_interstates else "LOW",
            "detail": (
                "Vehicle-related ignitions (catalytic converters, tire blowouts, "
                "dragging chains/equipment) occur along any major highway."
            ),
        },
        {
            "source": "Agricultural equipment",
            "risk": "MODERATE",
            "detail": (
                "Farm equipment striking rocks, metal-on-metal contact, and "
                "overheated bearings in grassland/cropland areas."
            ),
        },
    ]

    return {
        "location": {"lat": lat, "lon": lon},
        "matched_city": None,
        "distance_to_city_km": None,
        "note": (
            f"No specific ignition profile for this location. Using general "
            f"assessment. Nearest profiled city is "
            f"{_find_nearest_profiled_city(lat, lon)} away."
        ),
        "sources": general_sources,
        "corridors": [],
        "nearby_interstates": nearby_interstates,
    }


# =============================================================================
# Internal Helpers
# =============================================================================

def _safe_float(val) -> Optional[float]:
    """Convert a value to float, returning None for missing/invalid data."""
    if val is None or val == "M" or val == "" or val == "None":
        return None
    try:
        f = float(val)
        if math.isnan(f) or math.isinf(f):
            return None
        return f
    except (ValueError, TypeError):
        return None


def _compute_days_since_precip(daily_stats: list) -> int:
    """Count days backward from most recent day to last measurable precip.

    Measurable precipitation is defined as >= 0.01 inches.
    """
    for i, day in enumerate(reversed(daily_stats)):
        precip = day.get("precip_in", 0.0)
        if precip is not None and precip >= 0.01:
            return i
    return len(daily_stats)  # No precip found in entire period


def _compute_trends(daily_stats: list) -> dict:
    """Simple trend analysis: compare first half vs second half of period."""
    if len(daily_stats) < 4:
        return {"note": "Insufficient data for trend analysis (need 4+ days)"}

    mid = len(daily_stats) // 2
    first_half = daily_stats[:mid]
    second_half = daily_stats[mid:]

    def _avg(days, key):
        vals = [d[key] for d in days if d.get(key) is not None]
        return sum(vals) / len(vals) if vals else None

    first_temp = _avg(first_half, "high_f")
    second_temp = _avg(second_half, "high_f")
    first_rh = _avg(first_half, "min_rh")
    second_rh = _avg(second_half, "min_rh")
    first_dew = _avg(first_half, "avg_dewpoint_f")
    second_dew = _avg(second_half, "avg_dewpoint_f")

    trends = {}

    if first_temp is not None and second_temp is not None:
        diff = second_temp - first_temp
        if diff > 5:
            trends["temperature"] = f"WARMING (+{diff:.0f}F over period)"
        elif diff < -5:
            trends["temperature"] = f"COOLING ({diff:.0f}F over period)"
        else:
            trends["temperature"] = "STEADY"

    if first_rh is not None and second_rh is not None:
        diff = second_rh - first_rh
        if diff < -5:
            trends["humidity"] = f"DRYING ({diff:.0f}% RH over period)"
        elif diff > 5:
            trends["humidity"] = f"MOISTENING (+{diff:.0f}% RH over period)"
        else:
            trends["humidity"] = "STEADY"

    if first_dew is not None and second_dew is not None:
        diff = second_dew - first_dew
        if diff < -5:
            trends["dewpoint"] = f"DRYING ({diff:.0f}F dewpoint over period)"
        elif diff > 5:
            trends["dewpoint"] = f"MOISTENING (+{diff:.0f}F dewpoint over period)"
        else:
            trends["dewpoint"] = "STEADY"

    # Overall fuel trend
    drying_signals = sum(1 for v in trends.values() if "DRYING" in str(v) or "WARMING" in str(v))
    wetting_signals = sum(1 for v in trends.values() if "MOISTENING" in str(v) or "COOLING" in str(v))

    if drying_signals >= 2:
        trends["overall_fuel_trend"] = "DETERIORATING — fuels are getting drier"
    elif wetting_signals >= 2:
        trends["overall_fuel_trend"] = "IMPROVING — some moisture recovery"
    else:
        trends["overall_fuel_trend"] = "MIXED — no clear trend"

    return trends


def _get_drought_for_point(lat: float, lon: float) -> dict:
    """Get drought information for a point using state-level USDM data.

    Falls back gracefully if the API is unavailable.
    """
    states = _guess_nearby_states(lat, lon)
    if not states:
        return {"level": None, "description": "Unknown", "impact": "Unable to determine drought status"}

    state = states[0]
    try:
        drought_data = get_drought_status(state=state)
    except Exception as e:
        return {
            "level": None,
            "description": "API unavailable",
            "impact": f"Could not fetch drought data: {e}",
        }

    if isinstance(drought_data, dict) and "error" in drought_data:
        return {
            "level": None,
            "description": "API error",
            "impact": drought_data.get("error", "Unknown error"),
        }

    # Parse USDM response — the API returns a list of date entries
    # Each entry has percentages for None, D0, D1, D2, D3, D4
    if isinstance(drought_data, list) and drought_data:
        latest = drought_data[-1] if drought_data else {}
        # Determine the worst drought level that covers significant area
        d4_pct = _safe_float(latest.get("D4", latest.get("d4", 0))) or 0
        d3_pct = _safe_float(latest.get("D3", latest.get("d3", 0))) or 0
        d2_pct = _safe_float(latest.get("D2", latest.get("d2", 0))) or 0
        d1_pct = _safe_float(latest.get("D1", latest.get("d1", 0))) or 0
        d0_pct = _safe_float(latest.get("D0", latest.get("d0", 0))) or 0

        # Find the worst level with >10% area coverage
        if d4_pct > 10:
            level, desc = "D4", "Exceptional Drought"
        elif d3_pct > 10:
            level, desc = "D3", "Extreme Drought"
        elif d2_pct > 10:
            level, desc = "D2", "Severe Drought"
        elif d1_pct > 10:
            level, desc = "D1", "Moderate Drought"
        elif d0_pct > 10:
            level, desc = "D0", "Abnormally Dry"
        else:
            level, desc = "None", "No significant drought"

        impact_map = {
            "D4": "Exceptional drought — catastrophic fuel conditions, no moisture recovery possible",
            "D3": "Extreme drought — all fuel moisture indicators at or near record lows",
            "D2": "Severe drought — persistent drought compounds seasonal drying, subsoil moisture deficit means no moisture recovery from below",
            "D1": "Moderate drought — fuels are drier than normal for the season, reduced overnight recovery",
            "D0": "Abnormally dry — slight drought stress, fuels drier than average",
            "None": "No drought stress — fuel moisture near normal for season",
        }

        return {
            "level": level if level != "None" else None,
            "description": desc,
            "state": state,
            "d0_pct": d0_pct,
            "d1_pct": d1_pct,
            "d2_pct": d2_pct,
            "d3_pct": d3_pct,
            "d4_pct": d4_pct,
            "impact": impact_map.get(level, ""),
            "date": latest.get("MapDate", latest.get("mapDate", "")),
        }

    return {
        "level": None,
        "description": "Unknown format",
        "impact": "Drought data format not recognized",
    }


def _generic_seasonal_context(season: str, lat: float, lon: float) -> str:
    """Generate generic seasonal context when no specific fuel context matches."""
    contexts = {
        "winter": (
            "Winter dormant fuels — grasses and deciduous vegetation are dormant. "
            "Freeze-thaw cycles break down cell structure in fine fuels. Any warm "
            "spells rapidly evaporate residual moisture from recent snow or rain. "
            "No green-up has begun."
        ),
        "spring": (
            "Spring transition — dormant fuels beginning green-up depending on "
            "rainfall and temperatures. Dead grass still present. Fire behavior "
            "moderates as green-up progresses past 30%."
        ),
        "summer": (
            "Summer fuels — condition depends on drought status. Normal rainfall "
            "keeps grass green; drought causes early curing. High temperatures "
            "accelerate fuel drying regardless."
        ),
        "fall": (
            "Fall curing — warm-season grasses are curing or already dormant. "
            "Deciduous leaf litter accumulating. Fire risk increasing as dormancy "
            "progresses and live fuel moisture declines."
        ),
    }
    return contexts.get(season, "Unable to determine seasonal fuel context")


def _build_fuel_explanation(
    warm_days_60: int, warm_days_70: int, max_temp_f: Optional[float],
    total_precip: float, days_since_precip: int,
    avg_rh_daytime: Optional[float], min_rh: Optional[float],
    avg_dewpoint_f: Optional[float],
    fuel_cat: str, fm_low: int, fm_high: int,
    season: str,
) -> str:
    """Build a human-readable explanation of the fuel condition assessment."""
    parts = []

    # Temperature impact
    if warm_days_70 > 0 and season in ("winter", "spring"):
        parts.append(
            f"{warm_days_60} of 7 days above 60F with {warm_days_70} above 70F "
            f"has rapidly evaporated any residual snow moisture"
        )
    elif warm_days_60 > 0 and season in ("winter", "spring"):
        parts.append(
            f"{warm_days_60} of 7 days above 60F — warm enough to significantly "
            f"dry out dormant fuels"
        )

    # Precipitation
    if total_precip < 0.01:
        parts.append(
            f"No measurable precipitation in {days_since_precip} days"
        )
    elif total_precip < 0.1:
        parts.append(
            f"Only trace precipitation ({total_precip:.2f} inches) in the past "
            f"7 days — insufficient to meaningfully wet fuels"
        )
    elif total_precip >= 0.5:
        parts.append(
            f"{total_precip:.2f} inches of precipitation in the past 7 days "
            f"provided some fuel moisture"
        )
        if days_since_precip >= 3:
            parts.append(
                f"but it has been {days_since_precip} days since the last rain "
                f"and fuels are re-drying"
            )

    # Humidity
    if avg_rh_daytime is not None and min_rh is not None:
        if avg_rh_daytime < 15:
            parts.append(
                f"Average daytime RH of {avg_rh_daytime:.0f}% with minimums "
                f"reaching {min_rh:.0f}% further desiccates fine fuels"
            )
        elif avg_rh_daytime < 25:
            parts.append(
                f"Average daytime RH of {avg_rh_daytime:.0f}% (minimum {min_rh:.0f}%) "
                f"is well below the level needed for fuel moisture recovery"
            )
        elif avg_rh_daytime < 35:
            parts.append(
                f"Average daytime RH of {avg_rh_daytime:.0f}% is marginal — "
                f"some overnight recovery possible but limited"
            )

    # Dewpoint
    if avg_dewpoint_f is not None and avg_dewpoint_f < 20:
        parts.append(
            f"Dewpoints averaging {avg_dewpoint_f:.0f}F indicate an extremely "
            f"dry air mass — fuels cannot absorb moisture even overnight"
        )
    elif avg_dewpoint_f is not None and avg_dewpoint_f < 30:
        parts.append(
            f"Dewpoints averaging {avg_dewpoint_f:.0f}F limit overnight fuel "
            f"moisture recovery"
        )

    # Fuel moisture conclusion
    category_labels = {
        "critically_low": "critically low",
        "very_low": "very low",
        "low": "low",
        "moderate": "moderate",
        "adequate": "adequate",
    }
    cat_label = category_labels.get(fuel_cat, fuel_cat)

    if fuel_cat in ("critically_low", "very_low"):
        parts.append(
            f"Prairie grass dead fuel moisture likely {fm_low}-{fm_high}%, "
            f"well below the 8% threshold for extreme fire behavior"
        )
    elif fuel_cat == "low":
        parts.append(
            f"Dead fuel moisture estimated at {fm_low}-{fm_high}% — approaching "
            f"the 8% extreme fire behavior threshold"
        )
    else:
        parts.append(
            f"Dead fuel moisture estimated at {fm_low}-{fm_high}% ({cat_label})"
        )

    return ". ".join(parts) + "."


def _build_fire_behavior_implications(
    fuel_cat: str, fm_low: int, fm_high: int,
    season: str, warm_days_70: int,
    days_since_precip: int, avg_rh_daytime: Optional[float],
    drought_level: Optional[str],
    fuel_ctx: dict,
) -> list:
    """Build a list of fire behavior implications based on fuel conditions."""
    implications = []

    # Fuel moisture implications
    if fuel_cat == "critically_low":
        implications.append(
            f"Fine dead fuel moisture likely {fm_low}-{fm_high}% — extreme fire behavior threshold"
        )
        implications.append(
            "Any spark source (chains, equipment, power lines) will ignite fuels instantly"
        )
    elif fuel_cat == "very_low":
        implications.append(
            f"Fine dead fuel moisture likely {fm_low}-{fm_high}% — high fire behavior potential"
        )
        implications.append(
            "Most ignition sources will readily ignite fuels"
        )
    elif fuel_cat == "low":
        implications.append(
            f"Fine dead fuel moisture likely {fm_low}-{fm_high}% — elevated fire behavior"
        )

    # Season-specific implications
    if season == "winter" and warm_days_70 > 0:
        implications.append(
            "Freeze-dried winter grass ignites more easily than summer-cured grass"
        )
        implications.append(
            "No green-up has begun — fuels are 100% cured/dormant"
        )

    # Fuel continuity / spread
    fuel_type = fuel_ctx.get("fuel_type", "")
    if "grass" in fuel_type.lower() or "prairie" in fuel_type.lower():
        if fuel_cat in ("critically_low", "very_low"):
            implications.append(
                "Rapid rate of spread in continuous grass fuels — 2-4 mph typical, 6+ mph in worst conditions"
            )
            implications.append(
                "Short flame lengths (3-8ft) but extremely fast spread makes entrapment risk high"
            )
        else:
            implications.append(
                "Grass fuels support moderate to fast rates of spread depending on wind"
            )

    if "chaparral" in fuel_type.lower():
        implications.append(
            "Chaparral fires produce long flame lengths (20-60ft) and extreme radiant heat"
        )
        implications.append(
            "Spotting distances of 0.5-1 mile common in chaparral with wind"
        )

    # Drought compounding
    if drought_level and drought_level in ("D2", "D3", "D4"):
        implications.append(
            f"Drought ({drought_level}) compounds fuel drying — subsoil moisture "
            f"deficit prevents any moisture recovery from below"
        )

    # RH implications
    if avg_rh_daytime is not None and avg_rh_daytime < 15:
        implications.append(
            f"Daytime RH averaging {avg_rh_daytime:.0f}% — fuels will reach "
            f"minimum moisture content by early afternoon"
        )

    # Days without rain
    if days_since_precip >= 14:
        implications.append(
            f"No precipitation in {days_since_precip} days — even heavier fuels "
            f"(100-hr, 1000-hr) are drying out"
        )
    elif days_since_precip >= 7:
        implications.append(
            f"No precipitation in {days_since_precip} days — fine fuels are at "
            f"minimum moisture, larger fuels trending lower"
        )

    # Generic safety implications if fuel condition is bad
    if fuel_cat in ("critically_low", "very_low"):
        implications.append(
            "Spot fires will establish rapidly from any burning debris or embers"
        )
        implications.append(
            "Fire spread will be difficult to contain with initial attack resources"
        )

    return implications


def _find_nearby_interstates(lat: float, lon: float, max_dist_km: float = 50) -> list:
    """Find interstate highways within max_dist_km of a point."""
    nearby = []

    for corridor in _INTERSTATE_CORRIDORS:
        name = corridor["name"]
        min_dist = float("inf")

        for seg in corridor["segments"]:
            dist = _point_to_segment_distance_km(
                lat, lon,
                seg["lat1"], seg["lon1"],
                seg["lat2"], seg["lon2"],
            )
            if dist < min_dist:
                min_dist = dist

        if min_dist <= max_dist_km:
            risk_level = "HIGH" if min_dist <= 5 else ("MODERATE" if min_dist <= 20 else "LOW")
            nearby.append({
                "highway": name,
                "distance_km": round(min_dist, 1),
                "ignition_risk": risk_level,
                "detail": (
                    f"{name} is {min_dist:.0f} km away. "
                    + ("Direct ignition risk from truck/vehicle sparks. " if min_dist <= 5
                       else "Moderate ignition risk from vehicle-related sources. " if min_dist <= 20
                       else "Lower but non-zero ignition risk from highway traffic. ")
                    + "Fires starting along highways spread into adjacent grassland."
                ),
            })

    return sorted(nearby, key=lambda x: x["distance_km"])


def _find_nearest_profiled_city(lat: float, lon: float) -> str:
    """Find the nearest city in IGNITION_SOURCES and return a distance string."""
    nearest = None
    nearest_dist = float("inf")
    for key, data in IGNITION_SOURCES.items():
        dist = _haversine_km(lat, lon, data["lat"], data["lon"])
        if dist < nearest_dist:
            nearest = key
            nearest_dist = dist
    if nearest:
        return f"{nearest.replace('_', ' ').title()} ({nearest_dist:.0f} km)"
    return "unknown"
