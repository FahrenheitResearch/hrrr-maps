"""
Fire Weather Investigation Support Tool for AI Agents

Provides investigation-oriented fire weather assessment from HRRR cross-section
data.  Instead of producing a misleading single score, this module helps agents
investigate conditions deeply by comparing model data against thresholds, flagging
data quality issues, and generating investigation checklists.

PHILOSOPHY: Cross-section data averages through the full vertical column, which
dilutes surface signals.  RH at 850 hPa might be 50% while the surface is 11%.
Wind at 700 hPa might be calm while the surface is 25 kt.  A composite score
from column-averaged data will say "LOW" when fires are literally exploding.
This module makes those data quality problems VISIBLE instead of hiding them
behind a number.

Usage:
    from tools.agent_tools.fire_risk import FireRiskAnalyzer, FIRE_REGIONS

    analyzer = FireRiskAnalyzer()  # connects to localhost:5565

    # Single transect assessment (returns detailed investigation data)
    result = analyzer.analyze_transect(
        start=(34.5, -119.5), end=(33.5, -117.0),
        cycle="20260209_06z", fhr=12, label="SoCal"
    )
    print(result.summary)
    print(result.data_quality_warnings)    # flags suspect data
    print(result.investigation_flags)      # what to investigate further

    # Get investigation checklist for a specific location
    checklist = analyzer.investigation_checklist(35.4, -97.5)
    for step in checklist:
        print(step["action"])

    # Temporal sweep to find peak danger window
    results = analyzer.analyze_temporal(
        start=(34.5, -119.5), end=(33.5, -117.0),
        cycle="20260209_06z", fhrs=range(0, 25),
    )

    # Quick scan of all predefined fire regions
    scan = analyzer.quick_scan(cycle="20260209_06z")
    for region, level in scan.items():
        print(f"{region}: {level}")
"""
import math
from dataclasses import dataclass, field
from typing import Optional

from tools.agent_tools.cross_section import CrossSectionTool, CrossSectionData


# ---------------------------------------------------------------------------
# Predefined transects for major fire-prone areas
# ---------------------------------------------------------------------------

FIRE_REGIONS = {
    "northern_rockies": {
        "start": (47.5, -116.0),
        "end": (45.0, -110.0),
        "label": "Northern Rockies (ID/MT)",
    },
    "high_plains_north": {
        "start": (43.0, -106.0),
        "end": (41.0, -102.0),
        "label": "High Plains North (WY/NE)",
    },
    "high_plains_south": {
        "start": (36.5, -106.0),
        "end": (35.0, -102.0),
        "label": "High Plains South (NM/TX)",
    },
    "southwest_az": {
        "start": (34.5, -114.0),
        "end": (32.0, -109.0),
        "label": "Southwest (AZ)",
    },
    "socal": {
        "start": (34.5, -119.5),
        "end": (33.5, -117.0),
        "label": "Southern California",
    },
    "pacific_nw": {
        "start": (47.0, -123.0),
        "end": (44.0, -120.0),
        "label": "Pacific NW (WA/OR)",
    },
    "sierra_nevada": {
        "start": (39.0, -122.0),
        "end": (37.0, -118.0),
        "label": "Sierra Nevada",
    },
    "front_range": {
        "start": (40.5, -106.0),
        "end": (38.5, -104.0),
        "label": "Front Range (CO)",
    },
    "great_basin": {
        "start": (41.0, -118.0),
        "end": (39.0, -114.0),
        "label": "Great Basin (NV)",
    },
    "texas_panhandle": {
        "start": (36.0, -103.0),
        "end": (34.0, -100.0),
        "label": "Texas Panhandle",
    },
    "oklahoma": {
        "start": (36.5, -100.0),
        "end": (35.0, -97.0),
        "label": "Oklahoma",
    },
    "central_ca": {
        "start": (38.0, -123.0),
        "end": (36.0, -119.0),
        "label": "Central CA Coast/Valley",
    },
}


# Sub-metro / WUI-level transects for granular risk analysis within metro areas.
# Each metro key maps to a list of short transects (~10-30km) targeting specific
# WUI corridors, foothills communities, and fire-prone sub-areas.
SUB_METRO_AREAS = {
    "denver_metro": {
        "label": "Denver Metro Area",
        "center": (39.74, -104.99),
        "sub_areas": [
            {
                "key": "boulder_foothills",
                "label": "Boulder Foothills / Marshall Fire Zone",
                "start": (40.05, -105.35),
                "end": (39.90, -105.15),
                "notes": "Marshall Fire corridor, grass/shrub WUI",
            },
            {
                "key": "denver_proper",
                "label": "Denver Proper (Urban Core)",
                "start": (39.80, -105.05),
                "end": (39.65, -104.85),
                "notes": "Urban core, lower fire risk",
            },
            {
                "key": "golden_morrison",
                "label": "Golden / Morrison Foothills",
                "start": (39.78, -105.30),
                "end": (39.60, -105.10),
                "notes": "Foothills WUI west of Denver",
            },
            {
                "key": "evergreen_conifer",
                "label": "Evergreen / Conifer (Mountain WUI)",
                "start": (39.68, -105.45),
                "end": (39.55, -105.25),
                "notes": "High-elevation pine forest WUI",
            },
            {
                "key": "castle_rock_palmer",
                "label": "Castle Rock / Palmer Divide",
                "start": (39.45, -105.00),
                "end": (39.30, -104.80),
                "notes": "Palmer Divide grassland corridor",
            },
            {
                "key": "noco_loveland",
                "label": "Loveland / Fort Collins Foothills",
                "start": (40.55, -105.25),
                "end": (40.35, -105.05),
                "notes": "Northern CO foothills WUI, Cameron Peak burn scar",
            },
        ],
    },
    "colorado_springs": {
        "label": "Colorado Springs Metro",
        "center": (38.83, -104.82),
        "sub_areas": [
            {
                "key": "waldo_canyon",
                "label": "Waldo Canyon / Manitou Springs",
                "start": (38.88, -105.00),
                "end": (38.78, -104.82),
                "notes": "Waldo Canyon Fire scar, steep terrain WUI",
            },
            {
                "key": "black_forest",
                "label": "Black Forest",
                "start": (39.02, -104.75),
                "end": (38.90, -104.60),
                "notes": "Dense ponderosa pine WUI",
            },
        ],
    },
    "la_metro": {
        "label": "Los Angeles Metro",
        "center": (34.05, -118.24),
        "sub_areas": [
            {
                "key": "palisades_malibu",
                "label": "Pacific Palisades / Malibu",
                "start": (34.10, -118.60),
                "end": (33.95, -118.45),
                "notes": "Santa Ana wind corridor, Palisades Fire zone",
            },
            {
                "key": "eaton_altadena",
                "label": "Altadena / Eaton Canyon",
                "start": (34.25, -118.15),
                "end": (34.10, -118.05),
                "notes": "San Gabriel foothills WUI, Eaton Fire zone",
            },
            {
                "key": "san_fernando_sylmar",
                "label": "Sylmar / San Fernando Valley North",
                "start": (34.35, -118.50),
                "end": (34.25, -118.35),
                "notes": "Santa Clarita/Sylmar corridor, Saddleridge zone",
            },
            {
                "key": "san_bernardino_foothills",
                "label": "San Bernardino Foothills",
                "start": (34.20, -117.35),
                "end": (34.05, -117.20),
                "notes": "Inland Empire WUI, frequent fire starts",
            },
        ],
    },
    "phoenix_metro": {
        "label": "Phoenix Metro",
        "center": (33.45, -112.07),
        "sub_areas": [
            {
                "key": "scottsdale_mcdowell",
                "label": "Scottsdale / McDowell Mountains",
                "start": (33.70, -111.85),
                "end": (33.55, -111.75),
                "notes": "Desert WUI, Sonoran brush",
            },
            {
                "key": "prescott_yarnell",
                "label": "Prescott / Yarnell Area",
                "start": (34.60, -112.50),
                "end": (34.20, -112.70),
                "notes": "Yarnell Hill Fire zone, chaparral WUI",
            },
        ],
    },
    "albuquerque_metro": {
        "label": "Albuquerque Metro",
        "center": (35.08, -106.65),
        "sub_areas": [
            {
                "key": "east_mountains",
                "label": "East Mountains / Sandia WUI",
                "start": (35.15, -106.45),
                "end": (35.00, -106.30),
                "notes": "Sandia Mountains pine WUI, Cedar Crest/Tijeras",
            },
            {
                "key": "santa_fe_corridor",
                "label": "Santa Fe / Cerro Grande Zone",
                "start": (35.70, -106.00),
                "end": (35.55, -105.85),
                "notes": "Cerro Grande/Las Conchas burn scars",
            },
        ],
    },
    "reno_tahoe": {
        "label": "Reno / Lake Tahoe",
        "center": (39.53, -119.81),
        "sub_areas": [
            {
                "key": "reno_west",
                "label": "Reno West / Mt Rose Corridor",
                "start": (39.55, -120.00),
                "end": (39.40, -119.80),
                "notes": "Sierra WUI, steep terrain",
            },
            {
                "key": "south_tahoe",
                "label": "South Lake Tahoe / Caldor Zone",
                "start": (38.95, -120.10),
                "end": (38.85, -119.95),
                "notes": "Caldor Fire zone, pine forest WUI",
            },
        ],
    },
    "oklahoma_metro": {
        "label": "Oklahoma City Metro",
        "center": (35.47, -97.52),
        "sub_areas": [
            {
                "key": "newalla_draper",
                "label": "Newalla / Draper Corridor",
                "start": (35.42, -97.20),
                "end": (35.32, -97.00),
                "notes": "Rural SE OKC, grass/cedar WUI, frequent fire starts",
            },
            {
                "key": "choctaw_harrah",
                "label": "Choctaw / Harrah",
                "start": (35.52, -97.25),
                "end": (35.42, -97.10),
                "notes": "Eastern OKC suburbs, mixed grass/timber WUI",
            },
            {
                "key": "norman_moore",
                "label": "Norman / Moore",
                "start": (35.30, -97.50),
                "end": (35.18, -97.35),
                "notes": "Southern OKC metro, grassland/urban interface",
            },
            {
                "key": "edmond_guthrie",
                "label": "Edmond / Guthrie",
                "start": (35.72, -97.50),
                "end": (35.85, -97.40),
                "notes": "Northern OKC metro, cross-timbers transition zone",
            },
            {
                "key": "rural_se_okc",
                "label": "Rural SE OKC (Luther / Jones)",
                "start": (35.55, -97.10),
                "end": (35.45, -96.90),
                "notes": "Rural eastern corridor, grass/cedar, isolated structures",
            },
        ],
    },
}


# ---------------------------------------------------------------------------
# Threshold and assessment data classes
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class FireWeatherThresholds:
    """Standard fire weather warning thresholds.

    All wind values are in knots.  RH values are percentages (0-100).
    VPD is in hectopascals (hPa).  Lapse rates are in C/km.
    """

    # Red Flag Warning criteria
    red_flag_rh_pct: float = 15.0
    red_flag_wind_sustained_kt: float = 25.0
    red_flag_wind_gust_kt: float = 35.0

    # Critical fire weather criteria
    critical_rh_pct: float = 8.0
    critical_wind_sustained_kt: float = 30.0

    # Extreme / VPD criteria
    extreme_vpd_hpa: float = 13.0

    # Atmospheric instability
    lapse_rate_unstable_c_per_km: float = 8.0

    # Haines Index component thresholds (Low-elevation variant)
    #   Stability (temperature difference 950-850 hPa)
    haines_stability_low: float = 4.0   # 1 point
    haines_stability_mod: float = 8.0   # 2 points
    haines_stability_high: float = 11.0  # 3 points (>= this)

    #   Moisture (850 hPa temperature - dewpoint spread)
    haines_moisture_low: float = 6.0    # 1 point
    haines_moisture_mod: float = 10.0   # 2 points
    haines_moisture_high: float = 14.0  # 3 points (>= this)

    #   Total index interpretation
    haines_low: int = 2       # low fire growth potential
    haines_moderate: int = 4  # moderate
    haines_high: int = 5      # high


# Singleton instance for convenient access
THRESHOLDS = FireWeatherThresholds()


@dataclass
class FireRiskAssessment:
    """Result of a fire weather investigation along a transect.

    NOTE ON DATA QUALITY: The risk_level and risk_score fields are retained
    for backward compatibility but should be interpreted with caution.
    Cross-section data averages through the vertical column, which dilutes
    surface signals.  Always check data_quality_warnings and
    investigation_flags before trusting the score.

    Attributes:
        transect_start: (lat, lon) of transect start point.
        transect_end: (lat, lon) of transect end point.
        transect_label: Human-readable label for the transect.
        cycle: Model cycle key (e.g. "20260209_06z").
        fhr: Forecast hour evaluated.
        risk_level: One of CRITICAL, ELEVATED, MODERATE, LOW.
            WARNING: May understate risk if data is column-averaged.
        risk_score: Composite score from 0 (no risk) to 100 (extreme).
            WARNING: May understate risk if data is column-averaged.
        contributing_factors: List of human-readable factor descriptions.
        threshold_exceedances: Dict mapping threshold name to exceedance info.
        temporal_peak: Dict with 'fhr' and 'reason' keys identifying the
            forecast hour of peak danger (populated by analyze_temporal).
        rh_stats: Surface RH statistics dict (min/max/mean/count).
        wind_stats: Surface wind speed statistics dict.
        temp_stats: Surface temperature statistics dict.
        component_assessments: Detailed per-component assessment dicts with
            value, threshold, status, and plain-English explanation.
        data_quality_warnings: List of warnings about suspect data (e.g.,
            column-averaged winds, diluted RH).  If non-empty, the score
            should NOT be trusted without verification.
        investigation_flags: List of things an agent should investigate
            further (e.g., "verify with METAR", "check surface obs").
        summary: Auto-generated narrative summary.
    """

    transect_start: tuple
    transect_end: tuple
    transect_label: str
    cycle: str
    fhr: int
    risk_level: str
    risk_score: int
    contributing_factors: list = field(default_factory=list)
    threshold_exceedances: dict = field(default_factory=dict)
    temporal_peak: dict = field(default_factory=dict)
    rh_stats: dict = field(default_factory=dict)
    wind_stats: dict = field(default_factory=dict)
    temp_stats: dict = field(default_factory=dict)
    component_assessments: dict = field(default_factory=dict)
    data_quality_warnings: list = field(default_factory=list)
    investigation_flags: list = field(default_factory=list)
    summary: str = ""


# ---------------------------------------------------------------------------
# Core analyzer
# ---------------------------------------------------------------------------

class FireRiskAnalyzer:
    """Investigation-oriented fire weather analysis using HRRR or GFS data.

    Pulls relative humidity, wind speed, and temperature cross-section data
    from the wxsection.com dashboard API, then evaluates conditions against
    fire weather thresholds.  Instead of relying solely on a composite score,
    produces detailed component assessments, data quality warnings, and
    investigation checklists that help agents dig deeper.

    IMPORTANT: Cross-section surface_stats() returns column-averaged data,
    not true surface observations.  This means:
      - RH will read 40-50% when surface may be 10-15%
      - Wind will read 0.5-2 m/s when surface may be 15-25 kt
      - The resulting risk score will understate actual danger

    Always verify model data against METAR, RAWS, and NWS observations
    before drawing conclusions about fire risk.

    Args:
        base_url: Dashboard API base URL.  Defaults to localhost:5565.
        model: Weather model to use ("hrrr" or "gfs").  GFS enables
            extended-range forecasts (F00-F384).
    """

    def __init__(self, base_url: str = "http://127.0.0.1:5565", model: str = "hrrr"):
        self.base_url = base_url
        self.model = model
        self.cs = CrossSectionTool(base_url=base_url, model=model)
        self.thresholds = THRESHOLDS

    # ------------------------------------------------------------------
    # Static helper computations
    # ------------------------------------------------------------------

    @staticmethod
    def compute_vpd(temp_c: float, rh_pct: float) -> float:
        """Compute vapor pressure deficit (VPD) in hectopascals.

        Uses the Magnus-Tetens approximation for saturation vapor pressure:
            es = 6.1078 * exp((17.27 * T) / (T + 237.3))
        VPD = es * (1 - RH/100)

        Args:
            temp_c: Air temperature in degrees Celsius.
            rh_pct: Relative humidity as a percentage (0-100).

        Returns:
            Vapor pressure deficit in hPa (millibars).
        """
        if rh_pct < 0:
            rh_pct = 0.0
        if rh_pct > 100:
            rh_pct = 100.0
        es = 6.1078 * math.exp((17.27 * temp_c) / (temp_c + 237.3))
        vpd = es * (1.0 - rh_pct / 100.0)
        return round(vpd, 2)

    @staticmethod
    def compute_haines_index(
        temp_950: float,
        temp_850: float,
        temp_700: float,
        dewpoint_850: float,
    ) -> dict:
        """Compute the Haines Index (Lower Atmosphere Severity Index).

        The Haines Index combines a stability term (temperature lapse between
        two levels) and a moisture term (dewpoint depression at 850 hPa) into
        a single 2-6 index.  This implementation uses the low-elevation
        variant (950-850 hPa stability layer).

        Args:
            temp_950: Temperature at 950 hPa in Celsius.
            temp_850: Temperature at 850 hPa in Celsius.
            temp_700: Temperature at 700 hPa in Celsius (unused in low
                variant but accepted for interface consistency with
                mid/high variants).
            dewpoint_850: Dewpoint temperature at 850 hPa in Celsius.

        Returns:
            Dict with keys:
                stability: Stability component (1-3).
                moisture: Moisture component (1-3).
                total: Sum of components (2-6).
                interpretation: "low", "moderate", or "high".
        """
        t = THRESHOLDS

        # Stability component: T_950 - T_850
        delta_t = temp_950 - temp_850
        if delta_t >= t.haines_stability_high:
            stability = 3
        elif delta_t >= t.haines_stability_mod:
            stability = 2
        else:
            stability = 1

        # Moisture component: T_850 - Td_850
        dd = temp_850 - dewpoint_850
        if dd >= t.haines_moisture_high:
            moisture = 3
        elif dd >= t.haines_moisture_mod:
            moisture = 2
        else:
            moisture = 1

        total = stability + moisture

        if total >= t.haines_high:
            interpretation = "high"
        elif total >= t.haines_moderate:
            interpretation = "moderate"
        else:
            interpretation = "low"

        return {
            "stability": stability,
            "moisture": moisture,
            "total": total,
            "interpretation": interpretation,
        }

    @staticmethod
    def compute_lapse_rate(
        temp_low_c: float,
        temp_high_c: float,
        height_diff_m: float,
    ) -> float:
        """Compute environmental lapse rate in C/km.

        A positive value indicates temperature decreasing with height
        (normal lapse).  Values above ~8 C/km indicate an unstable
        atmosphere favorable for erratic fire behavior.

        Args:
            temp_low_c: Temperature at the lower level (Celsius).
            temp_high_c: Temperature at the upper level (Celsius).
            height_diff_m: Height difference between levels in meters
                (must be positive; lower level to upper level).

        Returns:
            Lapse rate in degrees Celsius per kilometer.

        Raises:
            ValueError: If height_diff_m is zero or negative.
        """
        if height_diff_m <= 0:
            raise ValueError(
                f"height_diff_m must be positive, got {height_diff_m}"
            )
        return round((temp_low_c - temp_high_c) / (height_diff_m / 1000.0), 2)

    # ------------------------------------------------------------------
    # Condition assessment (replaces old risk_score_from_data)
    # ------------------------------------------------------------------

    def assess_conditions(
        self,
        rh_stats: dict,
        wind_stats: dict,
        temp_stats: dict,
    ) -> dict:
        """Assess fire weather conditions with detailed component analysis.

        Instead of producing a single misleading score, returns a detailed
        assessment for each component with the actual value, the threshold
        it is compared against, a plain-English explanation, and data quality
        caveats that flag when the input data looks suspect.

        Args:
            rh_stats: Dict with min/max/mean keys for RH (%).
            wind_stats: Dict with min/max/mean keys for wind (kt or m/s).
            temp_stats: Dict with min/max/mean keys for temp (C).

        Returns:
            Dict with keys:
                score: Integer 0-100 (retained for backward compat).
                level: One of "CRITICAL", "ELEVATED", "MODERATE", "LOW".
                factors: List of human-readable contributing factor strings.
                components: Dict of per-component assessments.
                data_caveats: List of data quality warnings.
                investigation_flags: List of things to investigate further.
        """
        t = self.thresholds
        factors = []
        components = {}
        data_caveats = []
        investigation_flags = []

        # --- Data quality checks first ---
        dq = self.data_quality_check(rh_stats, wind_stats, temp_stats)
        data_caveats = dq["warnings"]
        data_suspect = dq["suspect"]

        # --- RH assessment ---
        rh_min = rh_stats.get("min")
        rh_max = rh_stats.get("max")
        rh_mean = rh_stats.get("mean")
        rh_component = 0.0

        if rh_min is not None and rh_mean is not None:
            if rh_min < t.critical_rh_pct:
                rh_status = "CRITICAL"
                rh_component = 100.0
                rh_explanation = (
                    f"Min RH {rh_min:.1f}% is below the critical threshold "
                    f"of {t.critical_rh_pct}%. Fuels will be at or near "
                    f"their lowest moisture content."
                )
                factors.append(
                    f"Critically low RH: min {rh_min:.1f}% "
                    f"(< {t.critical_rh_pct}%)"
                )
            elif rh_min < t.red_flag_rh_pct:
                rh_status = "RED_FLAG"
                span = t.red_flag_rh_pct - t.critical_rh_pct
                deficit = t.red_flag_rh_pct - rh_min
                rh_component = 50.0 + 50.0 * (deficit / span)
                rh_explanation = (
                    f"Min RH {rh_min:.1f}% is below the Red Flag threshold "
                    f"of {t.red_flag_rh_pct}%. Fine fuels readily ignitable."
                )
                factors.append(
                    f"Red Flag RH: min {rh_min:.1f}% "
                    f"(< {t.red_flag_rh_pct}%)"
                )
            elif rh_mean < 25.0:
                rh_status = "MARGINAL"
                rh_component = max(0.0, 50.0 * (25.0 - rh_mean) / 10.0)
                rh_explanation = (
                    f"Mean RH {rh_mean:.1f}% is moderately low. Not at "
                    f"Red Flag level ({t.red_flag_rh_pct}%) but fuels are "
                    f"drying."
                )
                if rh_component > 10:
                    factors.append(f"Low mean RH: {rh_mean:.1f}%")
            else:
                rh_status = "OK"
                rh_explanation = (
                    f"RH values (min {rh_min:.1f}%, mean {rh_mean:.1f}%) "
                    f"are above fire weather thresholds."
                )

            components["rh"] = {
                "value_min": round(rh_min, 1) if rh_min is not None else None,
                "value_max": round(rh_max, 1) if rh_max is not None else None,
                "value_mean": round(rh_mean, 1) if rh_mean is not None else None,
                "threshold_red_flag": t.red_flag_rh_pct,
                "threshold_critical": t.critical_rh_pct,
                "status": rh_status,
                "explanation": rh_explanation,
            }

            # Flag if RH looks column-averaged
            if rh_min is not None and rh_min > 30.0:
                investigation_flags.append(
                    "RH min is above 30% -- this likely reflects column-"
                    "averaged data, not surface RH. Surface RH could be "
                    "10-15% lower. VERIFY with nearest METAR/RAWS station."
                )
        else:
            components["rh"] = {
                "status": "NO_DATA",
                "explanation": "No RH data available for this transect.",
            }

        # --- Wind assessment ---
        wind_max = wind_stats.get("max")
        wind_mean = wind_stats.get("mean")
        wind_component = 0.0

        if wind_max is not None:
            if wind_max >= t.critical_wind_sustained_kt:
                wind_status = "CRITICAL"
                wind_component = 100.0
                wind_explanation = (
                    f"Max wind {wind_max:.1f} kt meets or exceeds the "
                    f"critical threshold of {t.critical_wind_sustained_kt} kt. "
                    f"Extreme fire spread rates likely."
                )
                factors.append(
                    f"Critical winds: max {wind_max:.1f} kt "
                    f"(>= {t.critical_wind_sustained_kt} kt)"
                )
            elif wind_max >= t.red_flag_wind_sustained_kt:
                wind_status = "RED_FLAG"
                span = (
                    t.critical_wind_sustained_kt - t.red_flag_wind_sustained_kt
                )
                excess = wind_max - t.red_flag_wind_sustained_kt
                wind_component = (
                    50.0 + 50.0 * (excess / span) if span > 0 else 75.0
                )
                wind_explanation = (
                    f"Max wind {wind_max:.1f} kt exceeds the Red Flag "
                    f"threshold of {t.red_flag_wind_sustained_kt} kt."
                )
                factors.append(
                    f"Red Flag winds: max {wind_max:.1f} kt "
                    f"(>= {t.red_flag_wind_sustained_kt} kt)"
                )
            elif wind_max >= 15.0:
                wind_status = "ELEVATED"
                wind_component = max(
                    0.0,
                    50.0
                    * (wind_max - 15.0)
                    / (t.red_flag_wind_sustained_kt - 15.0),
                )
                wind_explanation = (
                    f"Max wind {wind_max:.1f} kt is elevated but below "
                    f"Red Flag threshold ({t.red_flag_wind_sustained_kt} kt)."
                )
                if wind_component > 10:
                    factors.append(f"Elevated winds: max {wind_max:.1f} kt")
            else:
                wind_status = "OK"
                wind_explanation = (
                    f"Max wind {wind_max:.1f} kt is below concern levels."
                )

            components["wind"] = {
                "value_max": round(wind_max, 1) if wind_max is not None else None,
                "value_mean": round(wind_mean, 1) if wind_mean is not None else None,
                "threshold_red_flag": t.red_flag_wind_sustained_kt,
                "threshold_critical": t.critical_wind_sustained_kt,
                "status": wind_status,
                "explanation": wind_explanation,
            }

            # Flag suspiciously low wind
            if wind_max < 1.0:
                investigation_flags.append(
                    f"Wind max of {wind_max:.2f} is suspiciously low. "
                    f"This likely reflects column-averaged data (many calm "
                    f"upper levels diluting surface wind) or m/s units "
                    f"instead of knots. Surface winds could be 15-25+ kt. "
                    f"VERIFY with nearest METAR/RAWS station."
                )
            elif wind_max < 5.0 and wind_mean is not None and wind_mean < 3.0:
                investigation_flags.append(
                    f"Wind values are very low (max {wind_max:.1f}, mean "
                    f"{wind_mean:.1f}). Cross-section wind may be column-"
                    f"averaged. Check METAR surface observations for actual "
                    f"wind speed."
                )
        else:
            components["wind"] = {
                "status": "NO_DATA",
                "explanation": "No wind data available for this transect.",
            }

        # --- Instability proxy ---
        temp_min = temp_stats.get("min")
        temp_max = temp_stats.get("max")
        temp_mean = temp_stats.get("mean")
        instability_component = 0.0

        if temp_min is not None and temp_max is not None:
            temp_range = temp_max - temp_min
            instability_component = min(100.0, temp_range * 5.0)

            if temp_range > 15:
                instability_status = "SIGNIFICANT"
                instability_explanation = (
                    f"Temperature range of {temp_range:.1f} C across the "
                    f"transect indicates significant terrain-driven differential "
                    f"heating, promoting erratic fire behavior."
                )
                factors.append(
                    f"Large temperature spread: {temp_range:.1f} C "
                    f"across transect"
                )
            elif temp_range > 8:
                instability_status = "MODERATE"
                instability_explanation = (
                    f"Temperature range of {temp_range:.1f} C shows moderate "
                    f"differential heating across the transect."
                )
            elif temp_range < 2.0:
                instability_status = "SUSPECT"
                instability_explanation = (
                    f"Temperature range of only {temp_range:.1f} C across "
                    f"the transect is unusually narrow. This may indicate "
                    f"data from a single pressure level rather than surface."
                )
                investigation_flags.append(
                    f"Temperature range is only {temp_range:.1f} C across "
                    f"the transect. This is suspiciously uniform -- may "
                    f"reflect single-level data rather than surface temps."
                )
            else:
                instability_status = "LOW"
                instability_explanation = (
                    f"Temperature range of {temp_range:.1f} C is modest. "
                    f"Limited terrain-driven instability."
                )

            components["instability"] = {
                "temp_range_c": round(temp_range, 1),
                "temp_min_c": round(temp_min, 1),
                "temp_max_c": round(temp_max, 1),
                "status": instability_status,
                "explanation": instability_explanation,
            }
        else:
            components["instability"] = {
                "status": "NO_DATA",
                "explanation": "No temperature data available.",
            }

        # --- VPD assessment ---
        vpd_component = 0.0

        if temp_mean is not None and rh_min is not None:
            vpd = self.compute_vpd(temp_mean, rh_min)

            if vpd >= t.extreme_vpd_hpa:
                vpd_status = "EXTREME"
                vpd_component = 100.0
                vpd_explanation = (
                    f"VPD of {vpd} hPa is extreme (>= {t.extreme_vpd_hpa} "
                    f"hPa). Atmosphere is aggressively drying fuels."
                )
                factors.append(
                    f"Extreme VPD: {vpd} hPa (>= {t.extreme_vpd_hpa})"
                )
            elif vpd >= t.extreme_vpd_hpa * 0.6:
                vpd_status = "ELEVATED"
                vpd_component = 100.0 * (vpd / t.extreme_vpd_hpa)
                vpd_explanation = (
                    f"VPD of {vpd} hPa is elevated. Fuels drying faster "
                    f"than normal."
                )
                if vpd_component > 40:
                    factors.append(f"Elevated VPD: {vpd} hPa")
            else:
                vpd_status = "OK"
                vpd_explanation = (
                    f"VPD of {vpd} hPa is within normal range."
                )

            components["vpd"] = {
                "value_hpa": vpd,
                "threshold_extreme": t.extreme_vpd_hpa,
                "status": vpd_status,
                "explanation": vpd_explanation,
            }
        else:
            components["vpd"] = {
                "status": "NO_DATA",
                "explanation": "Cannot compute VPD without temperature and RH.",
            }

        # --- Composite score (kept for backward compat) ---
        score = (
            0.40 * rh_component
            + 0.30 * wind_component
            + 0.20 * instability_component
            + 0.10 * vpd_component
        )
        score = max(0, min(100, int(round(score))))

        if score >= 75:
            level = "CRITICAL"
        elif score >= 50:
            level = "ELEVATED"
        elif score >= 25:
            level = "MODERATE"
        else:
            level = "LOW"

        # If data quality is suspect, add a prominent warning
        if data_suspect and level == "LOW":
            investigation_flags.insert(
                0,
                "DATA QUALITY WARNING: This assessment reads as LOW risk "
                "but the input data shows signs of column averaging. "
                "Surface conditions could be significantly worse than "
                "shown here. Do NOT rely on this score without verifying "
                "against surface observations (METAR, RAWS)."
            )
        elif data_suspect:
            investigation_flags.insert(
                0,
                "DATA QUALITY WARNING: Input data shows signs of column "
                "averaging or unit issues. The score may understate actual "
                "risk. Verify against surface observations."
            )

        return {
            "score": score,
            "level": level,
            "factors": factors,
            "components": components,
            "data_caveats": data_caveats,
            "investigation_flags": investigation_flags,
        }

    def risk_score_from_data(
        self,
        rh_stats: dict,
        wind_stats: dict,
        temp_stats: dict,
    ) -> tuple:
        """Backward-compatible wrapper around assess_conditions().

        Returns the same (score, level, factors) tuple as the old method.
        Prefer using assess_conditions() directly for richer output.
        """
        result = self.assess_conditions(rh_stats, wind_stats, temp_stats)
        return result["score"], result["level"], result["factors"]

    # ------------------------------------------------------------------
    # Data quality checks
    # ------------------------------------------------------------------

    @staticmethod
    def data_quality_check(
        rh_stats: dict,
        wind_stats: dict,
        temp_stats: dict,
    ) -> dict:
        """Check input data for obvious quality problems.

        Cross-section data often represents column averages, not surface
        values.  This method flags common indicators of bad data:
          - Wind speeds under 1 kt (column average or wrong units)
          - RH min above 30% when fires are reported (column dilution)
          - Temperature range under 2 C across a long transect

        Args:
            rh_stats: Dict with min/max/mean keys for RH.
            wind_stats: Dict with min/max/mean keys for wind.
            temp_stats: Dict with min/max/mean keys for temperature.

        Returns:
            Dict with:
                suspect: True if any serious data quality issue found.
                warnings: List of human-readable warning strings.
        """
        warnings = []
        suspect = False

        # Wind checks
        wind_max = wind_stats.get("max")
        wind_mean = wind_stats.get("mean")
        if wind_max is not None:
            if wind_max < 1.0:
                warnings.append(
                    f"Wind max of {wind_max:.2f} suggests column-averaged "
                    f"data or m/s units, not surface wind in knots. "
                    f"Surface winds could be 15-25+ kt. Verify with "
                    f"METAR observations."
                )
                suspect = True
            elif wind_max < 5.0 and wind_mean is not None and wind_mean < 2.0:
                warnings.append(
                    f"Wind values (max {wind_max:.1f}, mean {wind_mean:.1f}) "
                    f"are suspiciously low for a transect. May be column-"
                    f"averaged data diluting surface winds."
                )
                suspect = True

        # RH checks
        rh_min = rh_stats.get("min")
        rh_mean = rh_stats.get("mean")
        if rh_min is not None and rh_mean is not None:
            if rh_min > 30.0 and rh_mean > 40.0:
                warnings.append(
                    f"RH min {rh_min:.1f}% and mean {rh_mean:.1f}% are "
                    f"both well above fire weather thresholds, but this "
                    f"may reflect column-averaged data. Surface RH during "
                    f"fire weather events is often 10-15%. Check METAR "
                    f"dewpoint and temperature for actual surface RH."
                )
                suspect = True
            elif rh_min > 25.0 and rh_mean > 35.0:
                warnings.append(
                    f"RH values (min {rh_min:.1f}%, mean {rh_mean:.1f}%) "
                    f"seem moderate but could be masking dry surface "
                    f"conditions. Column averaging dilutes surface signals."
                )

        # Temperature range check
        temp_min = temp_stats.get("min")
        temp_max = temp_stats.get("max")
        if temp_min is not None and temp_max is not None:
            temp_range = temp_max - temp_min
            if temp_range < 2.0:
                warnings.append(
                    f"Temperature range is only {temp_range:.1f} C across "
                    f"the transect. This is unusually uniform and may "
                    f"indicate single-level data rather than true surface "
                    f"temperature variation."
                )

        return {"suspect": suspect, "warnings": warnings}

    # ------------------------------------------------------------------
    # Transect analysis
    # ------------------------------------------------------------------

    def analyze_transect(
        self,
        start: tuple,
        end: tuple,
        cycle: str,
        fhr: int,
        label: Optional[str] = None,
    ) -> FireRiskAssessment:
        """Analyze fire weather conditions along a transect with data quality awareness.

        Pulls RH, wind speed, and temperature cross-section data from the
        dashboard API, computes surface statistics, evaluates against fire
        weather thresholds, and returns a detailed assessment with data
        quality warnings and investigation flags.

        IMPORTANT: The returned risk_score may understate actual risk because
        cross-section surface_stats() can return column-averaged data rather
        than true surface values.  Always check data_quality_warnings.

        Args:
            start: (lat, lon) tuple for transect start.
            end: (lat, lon) tuple for transect end.
            cycle: Model cycle key (e.g. "20260209_06z").
            fhr: Forecast hour to evaluate.
            label: Optional human-readable label for this transect.

        Returns:
            FireRiskAssessment with all fields populated, including
            component_assessments, data_quality_warnings, and
            investigation_flags.
        """
        if label is None:
            label = f"({start[0]},{start[1]}) to ({end[0]},{end[1]})"

        # Fetch data for the three key fire weather variables
        rh_data = self.cs.get_data(start, end, cycle, fhr, "rh")
        wind_data = self.cs.get_data(start, end, cycle, fhr, "wind_speed")
        temp_data = self.cs.get_data(start, end, cycle, fhr, "temperature")

        rh_stats = rh_data.surface_stats() if rh_data else {}
        wind_stats = wind_data.surface_stats() if wind_data else {}
        temp_stats = temp_data.surface_stats() if temp_data else {}

        # Run the detailed condition assessment
        assessment = self.assess_conditions(rh_stats, wind_stats, temp_stats)
        score = assessment["score"]
        level = assessment["level"]
        factors = assessment["factors"]
        components = assessment["components"]
        data_caveats = assessment["data_caveats"]
        inv_flags = list(assessment["investigation_flags"])

        # Build threshold exceedance details
        exceedances = {}
        t = self.thresholds

        if rh_data:
            pct_below_rfw = rh_data.pct_exceeding(t.red_flag_rh_pct, above=False)
            pct_below_crit = rh_data.pct_exceeding(t.critical_rh_pct, above=False)
            if pct_below_rfw > 0:
                exceedances["rh_below_red_flag"] = {
                    "threshold": t.red_flag_rh_pct,
                    "pct_exceeding": pct_below_rfw,
                    "description": (
                        f"{pct_below_rfw}% of transect below "
                        f"{t.red_flag_rh_pct}% RH"
                    ),
                }
            if pct_below_crit > 0:
                exceedances["rh_below_critical"] = {
                    "threshold": t.critical_rh_pct,
                    "pct_exceeding": pct_below_crit,
                    "description": (
                        f"{pct_below_crit}% of transect below "
                        f"{t.critical_rh_pct}% RH"
                    ),
                }

        if wind_data:
            pct_above_rfw = wind_data.pct_exceeding(
                t.red_flag_wind_sustained_kt, above=True
            )
            pct_above_crit = wind_data.pct_exceeding(
                t.critical_wind_sustained_kt, above=True
            )
            if pct_above_rfw > 0:
                exceedances["wind_above_red_flag"] = {
                    "threshold": t.red_flag_wind_sustained_kt,
                    "pct_exceeding": pct_above_rfw,
                    "description": (
                        f"{pct_above_rfw}% of transect above "
                        f"{t.red_flag_wind_sustained_kt} kt"
                    ),
                }
            if pct_above_crit > 0:
                exceedances["wind_above_critical"] = {
                    "threshold": t.critical_wind_sustained_kt,
                    "pct_exceeding": pct_above_crit,
                    "description": (
                        f"{pct_above_crit}% of transect above "
                        f"{t.critical_wind_sustained_kt} kt"
                    ),
                }

        # Add transect-midpoint investigation checklist items
        mid_lat = (start[0] + end[0]) / 2.0
        mid_lon = (start[1] + end[1]) / 2.0
        if data_caveats:
            inv_flags.append(
                f"Get METAR from nearest station to ({mid_lat:.2f}, "
                f"{mid_lon:.2f}) to verify surface conditions "
                f"(use find_stations + get_metar)"
            )
            inv_flags.append(
                "Compare model cross-section surface values against "
                "actual METAR temperature, dewpoint, and wind to quantify "
                "the column-averaging bias"
            )

        # Build narrative summary (with data quality info)
        summary = self._build_summary(
            label, cycle, fhr, level, score, factors,
            rh_stats, wind_stats, temp_stats, exceedances,
            data_caveats,
        )

        return FireRiskAssessment(
            transect_start=start,
            transect_end=end,
            transect_label=label,
            cycle=cycle,
            fhr=fhr,
            risk_level=level,
            risk_score=score,
            contributing_factors=factors,
            threshold_exceedances=exceedances,
            temporal_peak={},
            rh_stats=rh_stats,
            wind_stats=wind_stats,
            temp_stats=temp_stats,
            component_assessments=components,
            data_quality_warnings=data_caveats,
            investigation_flags=inv_flags,
            summary=summary,
        )

    # ------------------------------------------------------------------
    # Temporal analysis
    # ------------------------------------------------------------------

    def analyze_temporal(
        self,
        start: tuple,
        end: tuple,
        cycle: str,
        fhrs: list,
        label: Optional[str] = None,
    ) -> list:
        """Analyze fire weather risk across multiple forecast hours.

        Runs analyze_transect for each forecast hour, identifies the peak
        danger window, and annotates each assessment with temporal_peak info.

        Args:
            start: (lat, lon) tuple for transect start.
            end: (lat, lon) tuple for transect end.
            cycle: Model cycle key.
            fhrs: List or range of forecast hours to evaluate.
            label: Optional label for this transect.

        Returns:
            List of FireRiskAssessment objects, one per forecast hour,
            each annotated with temporal_peak pointing to the worst hour.
        """
        results = []
        for fhr in fhrs:
            assessment = self.analyze_transect(start, end, cycle, fhr, label)
            results.append(assessment)

        if not results:
            return results

        # Find the peak danger hour
        peak = max(results, key=lambda a: a.risk_score)
        peak_info = {
            "fhr": peak.fhr,
            "risk_score": peak.risk_score,
            "risk_level": peak.risk_level,
            "reason": self._peak_reason(peak),
        }

        # Annotate all assessments with the temporal peak
        for assessment in results:
            assessment.temporal_peak = peak_info

        return results

    # ------------------------------------------------------------------
    # Quick scan
    # ------------------------------------------------------------------

    def quick_scan(
        self,
        cycle: str,
        fhrs: Optional[list] = None,
        regions: Optional[dict] = None,
    ) -> dict:
        """Scan predefined CONUS regions for fire weather risk.

        For each region, evaluates the given forecast hours and returns the
        maximum risk level observed.  This provides a fast overview of where
        fire weather concerns exist across the domain.

        Args:
            cycle: Model cycle key.
            fhrs: Forecast hours to check.  Defaults to [0, 6, 12, 18, 24].
            regions: Dict of region definitions.  Defaults to FIRE_REGIONS.
                Each entry must have 'start', 'end', and 'label' keys.

        Returns:
            Dict mapping region key to a dict with:
                max_risk_level: Highest risk level across all forecast hours.
                max_risk_score: Highest score across all forecast hours.
                peak_fhr: Forecast hour of peak risk.
                label: Human-readable region label.
        """
        if fhrs is None:
            fhrs = [0, 6, 12, 18, 24]
        if regions is None:
            regions = FIRE_REGIONS

        scan_results = {}

        for region_key, region_def in regions.items():
            start = region_def["start"]
            end = region_def["end"]
            region_label = region_def.get("label", region_key)

            best_score = -1
            best_level = "LOW"
            best_fhr = fhrs[0] if fhrs else 0

            for fhr in fhrs:
                try:
                    assessment = self.analyze_transect(
                        start, end, cycle, fhr, label=region_label
                    )
                    if assessment.risk_score > best_score:
                        best_score = assessment.risk_score
                        best_level = assessment.risk_level
                        best_fhr = fhr
                except Exception:
                    # API may not have data for this FHR; skip
                    continue

            scan_results[region_key] = {
                "max_risk_level": best_level,
                "max_risk_score": max(best_score, 0),
                "peak_fhr": best_fhr,
                "label": region_label,
            }

        return scan_results

    def sub_metro_scan(
        self,
        metro_key: str,
        cycle: str,
        fhrs: Optional[list] = None,
    ) -> dict:
        """Scan sub-areas within a metro for granular WUI fire risk.

        Uses SUB_METRO_AREAS transects (~10-30km) to differentiate risk
        between foothills WUI, urban cores, and specific fire corridors
        within a single metro area.

        Args:
            metro_key: Key from SUB_METRO_AREAS (e.g., "denver_metro").
            cycle: Model cycle key.
            fhrs: Forecast hours to check.  Defaults to [0, 6, 12, 18].

        Returns:
            Dict with metro info and per-sub-area risk assessments,
            sorted by risk score (highest first).
        """
        if fhrs is None:
            fhrs = [0, 6, 12, 18]

        metro = SUB_METRO_AREAS.get(metro_key)
        if not metro:
            available = ", ".join(SUB_METRO_AREAS.keys())
            raise ValueError(
                f"Unknown metro '{metro_key}'. Available: {available}"
            )

        results = {
            "metro": metro["label"],
            "center": metro["center"],
            "sub_areas": {},
        }

        for area in metro["sub_areas"]:
            key = area["key"]
            start = area["start"]
            end = area["end"]

            best_score = -1
            best_level = "LOW"
            best_fhr = fhrs[0] if fhrs else 0
            best_factors = []

            for fhr in fhrs:
                try:
                    assessment = self.analyze_transect(
                        start, end, cycle, fhr, label=area["label"]
                    )
                    if assessment.risk_score > best_score:
                        best_score = assessment.risk_score
                        best_level = assessment.risk_level
                        best_fhr = fhr
                        best_factors = assessment.contributing_factors
                except Exception:
                    continue

            results["sub_areas"][key] = {
                "label": area["label"],
                "notes": area.get("notes", ""),
                "risk_level": best_level,
                "risk_score": max(best_score, 0),
                "peak_fhr": best_fhr,
                "contributing_factors": best_factors,
                "transect": {"start": start, "end": end},
            }

        # Sort by risk score descending
        results["sub_areas"] = dict(
            sorted(
                results["sub_areas"].items(),
                key=lambda x: x[1]["risk_score"],
                reverse=True,
            )
        )

        return results

    # ------------------------------------------------------------------
    # Investigation support
    # ------------------------------------------------------------------

    @staticmethod
    def investigation_checklist(lat: float, lon: float) -> list:
        """Generate a prioritized investigation checklist for a location.

        Returns a list of concrete actions an agent should take to
        investigate fire weather conditions at (lat, lon).  Each item
        includes the action description, the tool to use, and
        suggested parameters pre-filled for the location.

        This replaces the old approach of trusting a single risk score.
        Instead, agents should work through this checklist to build a
        complete picture from multiple data sources.

        Args:
            lat: Latitude of the location to investigate.
            lon: Longitude of the location to investigate.

        Returns:
            List of dicts, each with:
                priority: 1 (highest) to 9 (lowest).
                action: What to do, in plain English.
                tool: The MCP tool or agent_tools method to call.
                params: Dict of suggested parameters.
                rationale: Why this step matters.
        """
        return [
            {
                "priority": 1,
                "action": "Get current METAR observations from nearest station",
                "tool": "get_metar",
                "params": {
                    "lat": lat,
                    "lon": lon,
                    "radius_km": 50,
                },
                "rationale": (
                    "METAR gives actual surface temperature, dewpoint, wind "
                    "speed/direction, and visibility. This is the ground "
                    "truth that model data should be compared against."
                ),
            },
            {
                "priority": 2,
                "action": "Get RAWS observations if in wildland area",
                "tool": "get_raws",
                "params": {
                    "lat": lat,
                    "lon": lon,
                    "radius_km": 50,
                },
                "rationale": (
                    "RAWS stations are placed in fire-prone wildland areas "
                    "and report fuel moisture in addition to standard weather "
                    "variables. Often closer to actual fire locations than "
                    "METAR stations."
                ),
            },
            {
                "priority": 3,
                "action": "Check NWS alerts and Red Flag Warnings",
                "tool": "get_nws_alerts",
                "params": {
                    "lat": lat,
                    "lon": lon,
                },
                "rationale": (
                    "NWS fire weather forecasters issue Red Flag Warnings "
                    "and Fire Weather Watches based on local knowledge and "
                    "surface observations. Their assessment carries more "
                    "weight than model-derived scores."
                ),
            },
            {
                "priority": 4,
                "action": "Check SPC fire weather outlook",
                "tool": "get_spc_fire_outlook",
                "params": {},
                "rationale": (
                    "The Storm Prediction Center issues daily fire weather "
                    "outlooks with Critical and Extremely Critical areas. "
                    "These integrate surface obs, model data, and forecaster "
                    "expertise."
                ),
            },
            {
                "priority": 5,
                "action": "Get elevation profile for the area",
                "tool": "get_elevation",
                "params": {
                    "lat": lat,
                    "lon": lon,
                },
                "rationale": (
                    "Terrain drives fire behavior: slope, aspect, and "
                    "channeling effects. Steep terrain accelerates fire "
                    "spread and creates erratic behavior."
                ),
            },
            {
                "priority": 6,
                "action": "Check drought status",
                "tool": "get_drought",
                "params": {
                    "lat": lat,
                    "lon": lon,
                },
                "rationale": (
                    "Long-term drought amplifies fire risk by pre-drying "
                    "fuels well below what RH alone would suggest. D2+ "
                    "drought with low RH and wind is especially dangerous."
                ),
            },
            {
                "priority": 7,
                "action": (
                    "Get cross-section image for visual vertical "
                    "structure analysis"
                ),
                "tool": "get_cross_section",
                "params": {
                    "start_lat": lat - 0.5,
                    "start_lon": lon - 1.0,
                    "end_lat": lat + 0.5,
                    "end_lon": lon + 1.0,
                    "product": "rh",
                },
                "rationale": (
                    "Looking at the full cross-section image shows the "
                    "vertical structure: where the dry air is, how deep "
                    "the mixing layer is, and whether surface dryness "
                    "extends through the boundary layer."
                ),
            },
            {
                "priority": 8,
                "action": (
                    "Get Street View imagery to assess fuel type and "
                    "WUI interface"
                ),
                "tool": "get_street_view",
                "params": {
                    "lat": lat,
                    "lon": lon,
                },
                "rationale": (
                    "Street View shows fuel loading (grass, brush, timber), "
                    "proximity of structures to wildland fuels, and whether "
                    "the area has been treated or is overgrown."
                ),
            },
            {
                "priority": 9,
                "action": (
                    "Compare model forecast values with actual METAR "
                    "observations to quantify model bias"
                ),
                "tool": "manual_comparison",
                "params": {
                    "lat": lat,
                    "lon": lon,
                    "compare": [
                        "model_surface_rh vs metar_rh",
                        "model_surface_wind vs metar_wind",
                        "model_surface_temp vs metar_temp",
                    ],
                },
                "rationale": (
                    "The most important step: compare what the model says "
                    "surface conditions are versus what is actually being "
                    "observed. If model says RH 45% but METAR shows RH 12%, "
                    "the model cross-section data is column-averaged and "
                    "the risk score is meaningless."
                ),
            },
        ]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _peak_reason(self, assessment: FireRiskAssessment) -> str:
        """Generate a concise reason string for why a forecast hour is peak."""
        parts = []
        rh_min = assessment.rh_stats.get("min")
        wind_max = assessment.wind_stats.get("max")

        if rh_min is not None and rh_min < self.thresholds.red_flag_rh_pct:
            parts.append(f"RH min {rh_min}%")
        if wind_max is not None and wind_max >= self.thresholds.red_flag_wind_sustained_kt:
            parts.append(f"wind max {wind_max} kt")

        if parts:
            return f"F{assessment.fhr:03d}: " + ", ".join(parts)
        if assessment.contributing_factors:
            return f"F{assessment.fhr:03d}: {assessment.contributing_factors[0]}"
        return f"F{assessment.fhr:03d}: score {assessment.risk_score}"

    @staticmethod
    def _build_summary(
        label: str,
        cycle: str,
        fhr: int,
        level: str,
        score: int,
        factors: list,
        rh_stats: dict,
        wind_stats: dict,
        temp_stats: dict,
        exceedances: dict,
        data_caveats: Optional[list] = None,
    ) -> str:
        """Build a human-readable narrative summary of the assessment."""
        lines = [
            f"Fire Weather Assessment: {label}",
            f"Cycle: {cycle}  |  Forecast Hour: F{fhr:03d}",
            f"Risk Level: {level} (score {score}/100)",
        ]

        # Data quality warnings -- show these FIRST so they are prominent
        if data_caveats:
            lines.append("")
            lines.append("*** DATA QUALITY WARNINGS ***")
            for caveat in data_caveats:
                lines.append(f"  ! {caveat}")
            lines.append(
                "  >> The score above may be MISLEADING. Verify with "
                "surface observations."
            )
            lines.append("")

        # Surface conditions block
        conditions = []
        rh_min = rh_stats.get("min")
        rh_mean = rh_stats.get("mean")
        if rh_min is not None:
            conditions.append(f"RH: min {rh_min}%, mean {rh_mean}%")

        wind_max = wind_stats.get("max")
        wind_mean = wind_stats.get("mean")
        if wind_max is not None:
            conditions.append(f"Wind: max {wind_max} kt, mean {wind_mean} kt")

        temp_min = temp_stats.get("min")
        temp_max = temp_stats.get("max")
        if temp_min is not None:
            conditions.append(f"Temp: {temp_min} - {temp_max} C")

        if conditions:
            lines.append(
                "Model cross-section values (may be column-averaged): "
                + " | ".join(conditions)
            )

        # Contributing factors
        if factors:
            lines.append("Contributing factors:")
            for f in factors:
                lines.append(f"  - {f}")

        # Threshold exceedances
        if exceedances:
            lines.append("Threshold exceedances:")
            for key, info in exceedances.items():
                lines.append(f"  - {info['description']}")

        # Closing remark based on level
        if level == "CRITICAL":
            lines.append(
                "ACTION: Conditions support rapid fire spread and extreme "
                "fire behavior.  Coordinate with dispatch and fire weather "
                "forecasters."
            )
        elif level == "ELEVATED":
            lines.append(
                "CAUTION: Multiple fire weather thresholds approached or "
                "exceeded.  Monitor trends closely."
            )
        elif level == "MODERATE":
            lines.append(
                "WATCH: Some fire weather parameters are elevated.  Continue "
                "monitoring for deterioration."
            )

        # Always add the verification reminder
        lines.append("")
        lines.append(
            "NEXT STEP: Verify these model values against actual surface "
            "observations (METAR, RAWS) before drawing conclusions."
        )

        return "\n".join(lines)
