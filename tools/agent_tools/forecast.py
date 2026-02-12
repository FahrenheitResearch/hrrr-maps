"""
Forecast Generator — AI Agent Atmospheric Research Orchestrator

The brain of the wxsection.com AI-agent research platform. Orchestrates
multi-phase analysis to produce world-class weather forecasts, fire risk
assessments, and structured research reports.

Coordinates:
    - Cross-section analysis (CrossSectionTool)
    - External data ingestion (external_data.py)
    - Fire risk assessment (FireRiskAnalyzer, FIRE_REGIONS)
    - Report building (future: ReportBuilder, CaseStudy)

All public interfaces are designed for AI-agent consumption via MCP or
direct Python API.  An agent can call:

    gen = ForecastGenerator()
    result = gen.quick_forecast(ForecastConfig(
        scope="national",
        forecast_type="fire_weather",
    ))

and receive a complete ForecastResult with figures, risk assessments,
key findings, and (when available) a compiled PDF report.

Usage:
    from tools.agent_tools.forecast import (
        ForecastGenerator, ForecastConfig, ForecastScope, ForecastType,
        AgentWorkflow, get_latest_cycle, summarize_results,
    )

    # Quick national fire weather scan
    gen = ForecastGenerator()
    scan = gen.national_fire_scan()

    # Full forecast with report
    config = ForecastConfig(scope="regional", forecast_type="fire_weather",
                            center=(34.1, -118.2), radius_deg=3.0)
    result = gen.quick_forecast(config)
    print(summarize_results(result))

    # Pre-built workflows
    wf = AgentWorkflow()
    briefing = wf.daily_briefing()
"""
import json
import math
import os
import time
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from typing import Optional, Callable

from tools.agent_tools.cross_section import CrossSectionTool
from tools.agent_tools.fire_risk import FireRiskAnalyzer, FIRE_REGIONS
from tools.agent_tools import external_data


# ============================================================================
# Enum-like scope and type classes
# ============================================================================

class ForecastScope:
    """Scope of the forecast analysis.

    Controls how many transects are generated and how wide the spatial
    coverage is.
    """
    NATIONAL = "national"   # Full CONUS scan across all FIRE_REGIONS
    REGIONAL = "regional"   # Focused on 1-3 states (center + radius)
    LOCAL = "local"         # Single metro area or fire zone (dense grid)
    POINT = "point"         # Single location analysis

    _ALL = ("national", "regional", "local", "point")

    @classmethod
    def validate(cls, value: str) -> str:
        """Validate and return a scope string, raising ValueError if invalid."""
        if value not in cls._ALL:
            raise ValueError(
                f"Invalid scope '{value}'. Must be one of: {cls._ALL}"
            )
        return value


class ForecastType:
    """Type of forecast analysis to perform.

    Determines which products, thresholds, and report templates are used.
    """
    FIRE_WEATHER = "fire_weather"
    SEVERE = "severe"
    WINTER = "winter"
    GENERAL = "general"
    CASE_STUDY = "case_study"

    _ALL = ("fire_weather", "severe", "winter", "general", "case_study")

    @classmethod
    def validate(cls, value: str) -> str:
        """Validate and return a forecast type string."""
        if value not in cls._ALL:
            raise ValueError(
                f"Invalid forecast_type '{value}'. Must be one of: {cls._ALL}"
            )
        return value


# ============================================================================
# Products by forecast type
# ============================================================================

# Maps forecast type -> list of cross-section products to generate
_PRODUCTS_BY_TYPE = {
    ForecastType.FIRE_WEATHER: [
        "wind_speed", "rh", "temperature", "fire_wx",
    ],
    ForecastType.SEVERE: [
        "wind_speed", "omega", "theta_e", "temperature", "rh",
    ],
    ForecastType.WINTER: [
        "temperature", "rh", "wind_speed", "omega",
    ],
    ForecastType.GENERAL: [
        "temperature", "wind_speed", "rh",
    ],
    ForecastType.CASE_STUDY: [
        "wind_speed", "rh", "temperature", "omega", "theta_e",
    ],
}

# NWS offices by approximate region (used for forecast discussion ingestion)
_REGIONAL_NWS_OFFICES = {
    "northern_rockies": ["MSO", "TFX", "GGW"],
    "pacific_nw": ["SEW", "PQR", "PDT"],
    "sierra_nevada": ["STO", "REV", "HNX"],
    "central_ca": ["MTR", "LOX", "STO"],
    "socal": ["LOX", "SGX"],
    "southwest_az": ["PSR", "TWC", "FGZ"],
    "front_range": ["BOU", "PUB"],
    "high_plains_north": ["CYS", "RIW", "UNR"],
    "high_plains_south": ["ABQ", "LUB", "AMA"],
    "texas_panhandle": ["AMA", "LUB"],
    "oklahoma": ["OUN", "TSA"],
    "great_basin": ["LKN", "REV"],
}

# States by region (for NWS alert queries)
_REGIONAL_STATES = {
    "northern_rockies": ["MT", "ID"],
    "pacific_nw": ["WA", "OR"],
    "sierra_nevada": ["CA"],
    "central_ca": ["CA"],
    "socal": ["CA"],
    "southwest_az": ["AZ", "NM"],
    "front_range": ["CO"],
    "high_plains_north": ["WY", "NE"],
    "high_plains_south": ["NM", "TX"],
    "texas_panhandle": ["TX", "OK"],
    "oklahoma": ["OK"],
    "great_basin": ["NV", "UT"],
}


# ============================================================================
# Data classes
# ============================================================================

@dataclass
class ForecastConfig:
    """Configuration for a forecast generation run.

    All parameters have sensible defaults.  At minimum, set scope and
    forecast_type.  For regional/local scopes, set center and optionally
    radius_deg.

    Attributes:
        scope: Spatial scope (ForecastScope constant).
        forecast_type: Analysis type (ForecastType constant).
        cycle: Model cycle key or "latest".
        model: Weather model ("hrrr", "gfs", "rrfs").
        fhr_range: (start_fhr, end_fhr) inclusive range.
        fhr_step: Step between forecast hours.
        regions: List of region names (keys from FIRE_REGIONS) or custom
            transect dicts with {label, start, end, products}.
        center: (lat, lon) for local/point scope.
        radius_deg: Radius in degrees for local scope transect generation.
        include_external_data: Whether to fetch SPC/NWS/METAR data.
        include_spc: Fetch SPC outlooks and discussions.
        include_nws_alerts: Fetch active NWS alerts.
        include_observations: Fetch METAR observations.
        output_dir: Directory for output files.
        report_format: "full" (PDF), "bulletin" (text), or "data_only".
    """
    scope: str = ForecastScope.NATIONAL
    forecast_type: str = ForecastType.FIRE_WEATHER
    cycle: str = "latest"
    model: str = "hrrr"
    fhr_range: tuple = None  # Auto-set based on model in __post_init__
    fhr_step: int = 6
    regions: list = None
    center: tuple = None
    radius_deg: float = 3.0
    include_external_data: bool = True
    include_spc: bool = True
    include_nws_alerts: bool = True
    include_observations: bool = True
    output_dir: str = ""
    report_format: str = "full"

    # Model-specific max forecast hours
    MODEL_FHR_MAX = {"hrrr": 48, "gfs": 384, "rrfs": 18}

    def __post_init__(self):
        ForecastScope.validate(self.scope)
        ForecastType.validate(self.forecast_type)
        # Auto-set fhr_range based on model if not explicitly provided
        if self.fhr_range is None:
            max_fhr = self.MODEL_FHR_MAX.get(self.model, 48)
            self.fhr_range = (0, max_fhr)
        if self.scope in (ForecastScope.LOCAL, ForecastScope.POINT):
            if self.center is None:
                raise ValueError(
                    f"center=(lat, lon) is required for scope '{self.scope}'"
                )
        if self.output_dir and not os.path.isabs(self.output_dir):
            self.output_dir = os.path.abspath(self.output_dir)


@dataclass
class ForecastPlan:
    """Execution plan produced by ForecastGenerator.plan().

    Describes exactly what the orchestrator intends to do before any API
    calls are made.  Useful for cost/time estimation and approval workflows.

    Attributes:
        config: The ForecastConfig that produced this plan.
        transects: List of transect dicts, each with:
            label (str), start (lat,lon), end (lat,lon), products (list[str]).
        fhrs: List of forecast hours to evaluate.
        external_data_sources: List of external data source names that will
            be queried (e.g. "spc_fire_outlook", "nws_alerts", "metar").
        estimated_api_calls: Approximate number of dashboard API calls.
        estimated_figures: Approximate number of PNG figures to generate.
        phases: Ordered list of execution phase names.
    """
    config: ForecastConfig
    transects: list = field(default_factory=list)
    fhrs: list = field(default_factory=list)
    external_data_sources: list = field(default_factory=list)
    estimated_api_calls: int = 0
    estimated_figures: int = 0
    phases: list = field(default_factory=list)


@dataclass
class ForecastResult:
    """Complete result of a forecast generation run.

    Contains all outputs: risk assessments, external data, figure paths,
    report path, key findings, and timing.

    Attributes:
        config: The ForecastConfig used.
        plan: The ForecastPlan that was executed.
        risk_assessments: List of risk assessment dicts (from FireRiskAnalyzer).
        external_data: Dict of ingested external data keyed by source name.
        figures: List of generated figure file paths.
        report_path: Path to compiled PDF report (empty if not generated).
        latex_path: Path to LaTeX source (empty if not generated).
        key_findings: List of human-readable key finding strings.
        peak_risk: Dict with peak risk info across all assessments.
        execution_time_s: Wall-clock execution time in seconds.
    """
    config: ForecastConfig = None
    plan: ForecastPlan = None
    risk_assessments: list = field(default_factory=list)
    external_data: dict = field(default_factory=dict)
    figures: list = field(default_factory=list)
    report_path: str = ""
    latex_path: str = ""
    key_findings: list = field(default_factory=list)
    peak_risk: dict = field(default_factory=dict)
    execution_time_s: float = 0.0


# ============================================================================
# Helper functions
# ============================================================================

def get_latest_cycle(model: str = "hrrr",
                     base_url: str = "http://127.0.0.1:5565") -> str:
    """Return the latest available cycle key from the dashboard.

    Queries the /api/v1/cycles endpoint and returns the newest cycle
    that has data loaded.

    Args:
        model: Weather model name ("hrrr", "gfs", "rrfs").
        base_url: Dashboard base URL.

    Returns:
        Cycle key string (e.g. "20260209_06z"), or "latest" if the
        API is unreachable.
    """
    url = f"{base_url}/api/v1/cycles?model={model}"
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": "wxsection-forecast/1.0"}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
        # The API returns a list of cycle objects sorted newest-first
        cycles = data if isinstance(data, list) else data.get("cycles", [])
        for c in cycles:
            key = c.get("cycle_key") or c.get("key") or c.get("cycle", "")
            if key:
                return key
    except Exception:
        pass
    return "latest"


def fhr_list(start: int, end: int, step: int = 1) -> list:
    """Generate a list of forecast hours from start to end (inclusive).

    Args:
        start: First forecast hour.
        end: Last forecast hour (included if aligned with step).
        step: Increment between hours.

    Returns:
        List of integer forecast hours.
    """
    if step < 1:
        step = 1
    result = []
    fhr = start
    while fhr <= end:
        result.append(fhr)
        fhr += step
    return result


def auto_transects_for_region(region_name: str) -> list:
    """Generate sensible transects for a named FIRE_REGION.

    For each predefined fire region, returns a list of transect dicts
    suitable for cross-section analysis.  Generates two orthogonal
    transects: the primary transect from the region definition, and a
    perpendicular transect through the midpoint.

    Args:
        region_name: Key from FIRE_REGIONS dict (e.g. "socal", "front_range").

    Returns:
        List of transect dicts: [{label, start, end, products}, ...].
        Returns empty list if region_name is not recognized.
    """
    region = FIRE_REGIONS.get(region_name)
    if region is None:
        return []

    start = region["start"]
    end = region["end"]
    label = region.get("label", region_name)

    # Primary transect (as defined)
    primary = {
        "label": f"{label} primary",
        "start": start,
        "end": end,
        "products": ["wind_speed", "rh", "temperature"],
    }

    # Perpendicular transect through midpoint
    mid_lat = (start[0] + end[0]) / 2.0
    mid_lon = (start[1] + end[1]) / 2.0

    # Rotate the vector 90 degrees
    dlat = end[0] - start[0]
    dlon = end[1] - start[1]
    length = math.sqrt(dlat ** 2 + dlon ** 2)
    if length == 0:
        return [primary]

    # Half-length of perpendicular transect
    half = length / 2.0
    perp_dlat = -dlon / length * half
    perp_dlon = dlat / length * half

    perp = {
        "label": f"{label} perpendicular",
        "start": (round(mid_lat + perp_dlat, 2), round(mid_lon + perp_dlon, 2)),
        "end": (round(mid_lat - perp_dlat, 2), round(mid_lon - perp_dlon, 2)),
        "products": ["wind_speed", "rh", "temperature"],
    }

    return [primary, perp]


def summarize_results(result: ForecastResult) -> str:
    """Generate a human-readable summary of a ForecastResult.

    Produces a structured text block covering scope, timing, risk findings,
    key observations, and figure counts.

    Args:
        result: A completed ForecastResult.

    Returns:
        Multi-line summary string.
    """
    lines = []
    lines.append("=" * 60)
    lines.append("FORECAST RESULT SUMMARY")
    lines.append("=" * 60)

    if result.config:
        lines.append(f"Scope:         {result.config.scope}")
        lines.append(f"Type:          {result.config.forecast_type}")
        lines.append(f"Model:         {result.config.model}")
        lines.append(f"Cycle:         {result.config.cycle}")
        lines.append(f"FHR Range:     {result.config.fhr_range}")

    lines.append(f"Execution:     {result.execution_time_s:.1f}s")
    lines.append(f"Figures:       {len(result.figures)}")
    lines.append(f"Assessments:   {len(result.risk_assessments)}")

    if result.report_path:
        lines.append(f"Report:        {result.report_path}")

    # Peak risk
    if result.peak_risk:
        lines.append("")
        lines.append("--- PEAK RISK ---")
        pr = result.peak_risk
        lines.append(
            f"Level: {pr.get('risk_level', 'N/A')} "
            f"(score {pr.get('risk_score', 'N/A')}/100)"
        )
        region = pr.get("region", pr.get("label", ""))
        if region:
            lines.append(f"Region: {region}")
        peak_fhr = pr.get("fhr", pr.get("peak_fhr", ""))
        if peak_fhr != "":
            lines.append(f"Peak FHR: F{peak_fhr:03d}" if isinstance(peak_fhr, int) else f"Peak FHR: {peak_fhr}")

    # Key findings
    if result.key_findings:
        lines.append("")
        lines.append("--- KEY FINDINGS ---")
        for i, finding in enumerate(result.key_findings, 1):
            lines.append(f"  {i}. {finding}")

    # External data summary
    if result.external_data:
        lines.append("")
        lines.append("--- EXTERNAL DATA ---")
        for source, data in result.external_data.items():
            if isinstance(data, dict) and "error" in data:
                lines.append(f"  {source}: ERROR - {data['error']}")
            elif isinstance(data, list):
                lines.append(f"  {source}: {len(data)} records")
            else:
                lines.append(f"  {source}: loaded")

    lines.append("")
    lines.append("=" * 60)
    return "\n".join(lines)


# ============================================================================
# ForecastGenerator — main orchestrator
# ============================================================================

class ForecastGenerator:
    """Orchestrates multi-phase atmospheric analysis and forecast generation.

    This is the primary entry point for AI agents.  Given a ForecastConfig,
    it plans the analysis (selecting transects, forecast hours, and data
    sources), then executes each phase sequentially:

        Phase 1: External data ingestion (SPC, NWS, METARs)
        Phase 2: Cross-section figure generation (batch PNG creation)
        Phase 3: Numerical data extraction + fire risk assessment
        Phase 4: Report compilation (key findings, bulletin, PDF)

    Args:
        base_url: Dashboard API base URL.  Defaults to localhost:5565.
    """

    def __init__(self, base_url: str = "http://127.0.0.1:5565", model: str = "hrrr"):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.cs = CrossSectionTool(base_url=self.base_url, model=model)
        self.fire_analyzer = FireRiskAnalyzer(base_url=self.base_url, model=model)

    # ------------------------------------------------------------------
    # Planning
    # ------------------------------------------------------------------

    def plan(self, config: ForecastConfig) -> ForecastPlan:
        """Analyze a ForecastConfig and produce an execution plan.

        Determines which transects to run, which forecast hours to
        evaluate, and which external data sources to query.  Does not
        make any API calls.

        Args:
            config: ForecastConfig describing the desired analysis.

        Returns:
            ForecastPlan ready for execute_plan().
        """
        # Resolve cycle
        resolved_cycle = config.cycle
        if resolved_cycle == "latest":
            resolved_cycle = get_latest_cycle(config.model, self.base_url)
            config.cycle = resolved_cycle

        # Build forecast hour list
        fhrs = fhr_list(config.fhr_range[0], config.fhr_range[1], config.fhr_step)

        # Build transect list
        transects = self._plan_transects(config)

        # Determine products for each transect that doesn't already have them
        default_products = _PRODUCTS_BY_TYPE.get(
            config.forecast_type,
            _PRODUCTS_BY_TYPE[ForecastType.GENERAL],
        )
        for t in transects:
            if "products" not in t or not t["products"]:
                t["products"] = list(default_products)

        # Determine external data sources
        ext_sources = []
        if config.include_external_data:
            if config.include_spc and config.forecast_type in (
                ForecastType.FIRE_WEATHER, ForecastType.SEVERE
            ):
                ext_sources.append("spc_fire_outlook")
                ext_sources.append("spc_fire_discussion")
            if config.include_nws_alerts:
                ext_sources.append("nws_alerts")
            if config.include_observations:
                ext_sources.append("metar")

        # Estimate API calls: per transect * per fhr * per product (data + image)
        n_data_calls = len(transects) * len(fhrs) * 3  # rh, wind, temp
        n_image_calls = sum(
            len(fhrs) * len(t.get("products", default_products))
            for t in transects
        )
        estimated_api_calls = n_data_calls + n_image_calls + len(ext_sources)
        estimated_figures = n_image_calls

        # Phases
        phases = []
        if ext_sources:
            phases.append("external_data")
        if estimated_figures > 0:
            phases.append("cross_section_figures")
        phases.append("risk_assessment")
        if config.report_format != "data_only":
            phases.append("report_compilation")

        return ForecastPlan(
            config=config,
            transects=transects,
            fhrs=fhrs,
            external_data_sources=ext_sources,
            estimated_api_calls=estimated_api_calls,
            estimated_figures=estimated_figures,
            phases=phases,
        )

    def _plan_transects(self, config: ForecastConfig) -> list:
        """Generate the transect list based on config scope and regions.

        For NATIONAL scope, uses all FIRE_REGIONS.
        For REGIONAL scope, uses named regions or generates from center.
        For LOCAL scope, creates a dense grid of short transects.
        For POINT scope, creates a single cross-hair transect pair.

        Returns:
            List of transect dicts with label, start, end, products.
        """
        # If explicit regions/transects were provided, use them
        if config.regions:
            transects = []
            for item in config.regions:
                if isinstance(item, dict):
                    # Custom transect dict
                    transects.append(item)
                elif isinstance(item, str) and item in FIRE_REGIONS:
                    # Named region -> expand to transects
                    transects.extend(auto_transects_for_region(item))
            if transects:
                return transects

        scope = config.scope

        if scope == ForecastScope.NATIONAL:
            # One primary transect per FIRE_REGION
            transects = []
            for key, region in FIRE_REGIONS.items():
                transects.append({
                    "label": region.get("label", key),
                    "start": region["start"],
                    "end": region["end"],
                    "products": [],  # will be filled with defaults
                })
            return transects

        if scope == ForecastScope.REGIONAL:
            if config.center is None:
                # Fall back to national
                return self._plan_transects(
                    ForecastConfig(
                        scope=ForecastScope.NATIONAL,
                        forecast_type=config.forecast_type,
                    )
                )
            lat, lon = config.center
            r = config.radius_deg
            # Generate 4 transects: N-S, E-W, NE-SW, NW-SE
            return [
                {
                    "label": "N-S transect",
                    "start": (round(lat + r, 2), round(lon, 2)),
                    "end": (round(lat - r, 2), round(lon, 2)),
                    "products": [],
                },
                {
                    "label": "E-W transect",
                    "start": (round(lat, 2), round(lon - r, 2)),
                    "end": (round(lat, 2), round(lon + r, 2)),
                    "products": [],
                },
                {
                    "label": "NE-SW transect",
                    "start": (round(lat + r * 0.7, 2), round(lon + r * 0.7, 2)),
                    "end": (round(lat - r * 0.7, 2), round(lon - r * 0.7, 2)),
                    "products": [],
                },
                {
                    "label": "NW-SE transect",
                    "start": (round(lat + r * 0.7, 2), round(lon - r * 0.7, 2)),
                    "end": (round(lat - r * 0.7, 2), round(lon + r * 0.7, 2)),
                    "products": [],
                },
            ]

        if scope == ForecastScope.LOCAL:
            lat, lon = config.center
            r = config.radius_deg
            # Dense grid: 8 transects (every 22.5 degrees)
            transects = []
            n_directions = 8
            for i in range(n_directions):
                angle_rad = math.radians(i * 180.0 / n_directions)
                dlat = r * math.cos(angle_rad)
                dlon = r * math.sin(angle_rad)
                transects.append({
                    "label": f"Local transect {i+1}/{n_directions}",
                    "start": (round(lat + dlat, 3), round(lon + dlon, 3)),
                    "end": (round(lat - dlat, 3), round(lon - dlon, 3)),
                    "products": [],
                })
            return transects

        if scope == ForecastScope.POINT:
            lat, lon = config.center
            r = min(config.radius_deg, 2.0)
            # Two short transects: N-S and E-W through the point
            return [
                {
                    "label": f"Point N-S ({lat:.2f}, {lon:.2f})",
                    "start": (round(lat + r, 3), round(lon, 3)),
                    "end": (round(lat - r, 3), round(lon, 3)),
                    "products": [],
                },
                {
                    "label": f"Point E-W ({lat:.2f}, {lon:.2f})",
                    "start": (round(lat, 3), round(lon - r, 3)),
                    "end": (round(lat, 3), round(lon + r, 3)),
                    "products": [],
                },
            ]

        return []

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def execute_plan(
        self,
        plan: ForecastPlan,
        progress_callback: Optional[Callable] = None,
    ) -> ForecastResult:
        """Execute a ForecastPlan and return a ForecastResult.

        Runs four phases in order:
            1. External data ingestion
            2. Cross-section figure generation
            3. Numerical data extraction + fire risk assessment
            4. Report compilation

        Args:
            plan: ForecastPlan from self.plan().
            progress_callback: Optional callable(phase, pct, message) for
                progress reporting.  pct is 0-100 within each phase.

        Returns:
            Completed ForecastResult.
        """
        t0 = time.time()
        config = plan.config
        result = ForecastResult(config=config, plan=plan)

        def _progress(phase: str, pct: float, msg: str = ""):
            if progress_callback:
                try:
                    progress_callback(phase, pct, msg)
                except Exception:
                    pass

        # Ensure output directory exists
        output_dir = config.output_dir or os.path.join(
            os.path.expanduser("~"), "hrrr-maps", "output", "forecasts",
            f"{config.cycle}_{config.forecast_type}"
        )
        os.makedirs(output_dir, exist_ok=True)
        figures_dir = os.path.join(output_dir, "figures")
        os.makedirs(figures_dir, exist_ok=True)

        # ---- Phase 1: External Data ----
        if "external_data" in plan.phases:
            _progress("external_data", 0, "Fetching external data")
            result.external_data = self._fetch_external_data(
                config, plan, _progress
            )
            _progress("external_data", 100, "External data complete")

        # ---- Phase 2: Cross-section Figures ----
        if "cross_section_figures" in plan.phases:
            _progress("cross_section_figures", 0, "Generating figures")
            result.figures = self._generate_figures(
                config, plan, figures_dir, _progress
            )
            _progress("cross_section_figures", 100, "Figures complete")

        # ---- Phase 3: Risk Assessment ----
        if "risk_assessment" in plan.phases:
            _progress("risk_assessment", 0, "Running risk assessment")
            assessments, peak = self._run_risk_assessment(
                config, plan, _progress
            )
            result.risk_assessments = assessments
            result.peak_risk = peak
            _progress("risk_assessment", 100, "Risk assessment complete")

        # ---- Phase 4: Report Compilation ----
        if "report_compilation" in plan.phases:
            _progress("report_compilation", 0, "Compiling report")
            key_findings = self._extract_key_findings(result)
            result.key_findings = key_findings

            if config.report_format == "bulletin":
                bulletin_text = self._compile_bulletin(result)
                bulletin_path = os.path.join(output_dir, "bulletin.txt")
                with open(bulletin_path, "w", encoding="utf-8") as f:
                    f.write(bulletin_text)
                result.report_path = bulletin_path
            elif config.report_format == "full":
                # Full LaTeX/PDF report via ReportBuilder (if available)
                latex_path, pdf_path = self._compile_full_report(
                    result, output_dir
                )
                result.latex_path = latex_path
                result.report_path = pdf_path
            _progress("report_compilation", 100, "Report complete")

        result.execution_time_s = round(time.time() - t0, 2)
        return result

    def quick_forecast(self, config: ForecastConfig) -> ForecastResult:
        """Plan and execute a forecast in one call.

        Convenience method that chains plan() and execute_plan().

        Args:
            config: ForecastConfig describing the desired analysis.

        Returns:
            Completed ForecastResult.
        """
        plan = self.plan(config)
        return self.execute_plan(plan)

    # ------------------------------------------------------------------
    # Quick-access methods
    # ------------------------------------------------------------------

    def national_fire_scan(
        self,
        cycle: str = "latest",
        fhrs: Optional[list] = None,
    ) -> dict:
        """Quick national scan of fire risk across all CONUS fire regions.

        Uses FireRiskAnalyzer.quick_scan() to evaluate each predefined
        region at the specified forecast hours.

        Args:
            cycle: Model cycle key or "latest".
            fhrs: Forecast hours to evaluate.  Default: [0, 6, 12, 18, 24].

        Returns:
            Dict mapping region key to:
                risk_level (str), risk_score (int), peak_fhr (int),
                key_factors (list[str]).
        """
        if fhrs is None:
            fhrs = [0, 6, 12, 18, 24]

        if cycle == "latest":
            cycle = get_latest_cycle(self.model, self.base_url)

        raw_scan = self.fire_analyzer.quick_scan(cycle=cycle, fhrs=fhrs)

        # Enrich with key_factors by running a single assessment at peak FHR
        enriched = {}
        for region_key, info in raw_scan.items():
            region_def = FIRE_REGIONS.get(region_key, {})
            peak_fhr = info.get("peak_fhr", 0)
            key_factors = []

            try:
                assessment = self.fire_analyzer.analyze_transect(
                    start=region_def["start"],
                    end=region_def["end"],
                    cycle=cycle,
                    fhr=peak_fhr,
                    label=info.get("label", region_key),
                )
                key_factors = assessment.contributing_factors
            except Exception:
                pass

            enriched[region_key] = {
                "risk_level": info["max_risk_level"],
                "risk_score": info["max_risk_score"],
                "peak_fhr": peak_fhr,
                "key_factors": key_factors,
                "label": info.get("label", region_key),
            }

        return enriched

    def localized_forecast(
        self,
        lat: float,
        lon: float,
        cycle: str = "latest",
        radius_deg: float = 2.0,
    ) -> ForecastResult:
        """Quick localized forecast centered on a geographic point.

        Generates a LOCAL-scope fire weather forecast with reasonable
        defaults for a quick analysis of a specific area.

        Args:
            lat: Center latitude.
            lon: Center longitude.
            cycle: Model cycle key or "latest".
            radius_deg: Analysis radius in degrees.

        Returns:
            Completed ForecastResult.
        """
        config = ForecastConfig(
            scope=ForecastScope.LOCAL,
            forecast_type=ForecastType.FIRE_WEATHER,
            cycle=cycle,
            model=self.model,
            center=(lat, lon),
            radius_deg=radius_deg,
            fhr_step=3,
            report_format="bulletin",
        )
        return self.quick_forecast(config)

    def generate_bulletin(self, config: ForecastConfig) -> str:
        """Generate a short text bulletin without full PDF compilation.

        Runs a streamlined analysis (fewer FHRs, no figures) and produces
        a structured text bulletin.

        Structure:
            SITUATION  - Current conditions and external data summary
            FORECAST   - Model-derived forecast details
            OUTLOOK    - Risk evolution through the forecast period
            RECOMMENDATIONS - Action items based on risk level

        Args:
            config: ForecastConfig (report_format is overridden to "bulletin").

        Returns:
            Bulletin text string.
        """
        # Override to bulletin mode with reduced FHR set
        config.report_format = "data_only"  # skip PDF generation
        config.fhr_step = max(config.fhr_step, 6)  # coarser for speed

        plan = self.plan(config)
        result = self.execute_plan(plan)
        return self._compile_bulletin(result)

    # ------------------------------------------------------------------
    # Phase implementations
    # ------------------------------------------------------------------

    def _fetch_external_data(
        self,
        config: ForecastConfig,
        plan: ForecastPlan,
        progress: Callable,
    ) -> dict:
        """Phase 1: Fetch external data from SPC, NWS, and METAR APIs.

        Each source is wrapped in a try/except so failures in one source
        don't block the others.

        Returns:
            Dict keyed by source name -> fetched data.
        """
        ext = {}
        sources = plan.external_data_sources
        n = max(len(sources), 1)

        for i, source in enumerate(sources):
            progress("external_data", int(100 * i / n), f"Fetching {source}")

            try:
                if source == "spc_fire_outlook":
                    ext["spc_fire_outlook"] = external_data.get_spc_fire_weather_outlook(day=1)

                elif source == "spc_fire_discussion":
                    ext["spc_fire_discussion"] = external_data.get_spc_fire_discussion()

                elif source == "nws_alerts":
                    ext["nws_alerts"] = self._fetch_nws_alerts(config)

                elif source == "metar":
                    ext["metar"] = self._fetch_observations(config)

            except Exception as e:
                ext[source] = {"error": str(e)}

        return ext

    def _fetch_nws_alerts(self, config: ForecastConfig) -> dict:
        """Fetch NWS alerts relevant to the forecast scope.

        For NATIONAL scope, queries fire-weather alerts for key states.
        For REGIONAL/LOCAL, queries by point or nearby states.
        """
        alerts_combined = {"features": []}

        if config.scope == ForecastScope.NATIONAL:
            # Query fire-weather alerts for all fire region states
            queried_states = set()
            for region_key in FIRE_REGIONS:
                for st in _REGIONAL_STATES.get(region_key, []):
                    if st not in queried_states:
                        queried_states.add(st)
                        try:
                            result = external_data.get_nws_alerts(state=st)
                            features = result.get("features", [])
                            alerts_combined["features"].extend(features)
                        except Exception:
                            pass

        elif config.center is not None:
            lat, lon = config.center
            try:
                alerts_combined = external_data.get_nws_alerts(lat=lat, lon=lon)
            except Exception as e:
                alerts_combined = {"error": str(e)}

        return alerts_combined

    def _fetch_observations(self, config: ForecastConfig) -> dict:
        """Fetch METAR observations relevant to the forecast scope.

        For LOCAL/POINT, finds nearby stations and pulls recent METARs.
        For REGIONAL/NATIONAL, skips (too many stations to be useful).
        """
        if config.scope in (ForecastScope.LOCAL, ForecastScope.POINT) and config.center:
            lat, lon = config.center
            try:
                nearby = external_data.get_nearby_stations(lat, lon, radius_km=150)
                if nearby:
                    station_ids = [s["id"] for s in nearby[:10]]
                    return external_data.get_metar_observations(
                        stations=station_ids, hours_back=6
                    )
            except Exception as e:
                return {"error": str(e)}

        return {"note": "Observations skipped for broad scope"}

    def _generate_figures(
        self,
        config: ForecastConfig,
        plan: ForecastPlan,
        figures_dir: str,
        progress: Callable,
    ) -> list:
        """Phase 2: Generate cross-section PNG figures via batch API.

        Iterates over transects and calls CrossSectionTool.batch_images()
        for each one.

        Returns:
            List of generated figure file paths.
        """
        all_figures = []
        n_transects = max(len(plan.transects), 1)

        for i, transect in enumerate(plan.transects):
            progress(
                "cross_section_figures",
                int(100 * i / n_transects),
                f"Generating figures for {transect.get('label', f'transect {i+1}')}",
            )

            # Sanitize label for filenames
            safe_label = (
                transect.get("label", f"t{i}")
                .replace(" ", "_")
                .replace("/", "-")
                .replace("(", "")
                .replace(")", "")
                .lower()
            )

            products = transect.get("products", ["wind_speed", "rh", "temperature"])

            batch_transect = {
                "name": safe_label,
                "start": tuple(transect["start"]),
                "end": tuple(transect["end"]),
            }

            generated = self.cs.batch_images(
                transects=[batch_transect],
                cycle=config.cycle,
                fhrs=plan.fhrs,
                products=products,
                output_dir=figures_dir,
            )
            all_figures.extend(generated)

        return all_figures

    def _run_risk_assessment(
        self,
        config: ForecastConfig,
        plan: ForecastPlan,
        progress: Callable,
    ) -> tuple:
        """Phase 3: Run fire risk assessment on all transects.

        Evaluates each transect at every forecast hour, computes risk
        scores, and identifies the peak risk across all regions and times.

        Returns:
            Tuple of (assessments_list, peak_risk_dict).
        """
        assessments = []
        peak_score = -1
        peak_info = {}

        n_transects = max(len(plan.transects), 1)

        for i, transect in enumerate(plan.transects):
            progress(
                "risk_assessment",
                int(100 * i / n_transects),
                f"Assessing {transect.get('label', f'transect {i+1}')}",
            )

            label = transect.get("label", f"Transect {i+1}")

            for fhr in plan.fhrs:
                try:
                    assessment = self.fire_analyzer.analyze_transect(
                        start=tuple(transect["start"]),
                        end=tuple(transect["end"]),
                        cycle=config.cycle,
                        fhr=fhr,
                        label=label,
                    )

                    entry = {
                        "label": label,
                        "fhr": fhr,
                        "risk_level": assessment.risk_level,
                        "risk_score": assessment.risk_score,
                        "contributing_factors": assessment.contributing_factors,
                        "rh_stats": assessment.rh_stats,
                        "wind_stats": assessment.wind_stats,
                        "temp_stats": assessment.temp_stats,
                        "summary": assessment.summary,
                    }
                    assessments.append(entry)

                    if assessment.risk_score > peak_score:
                        peak_score = assessment.risk_score
                        peak_info = {
                            "region": label,
                            "fhr": fhr,
                            "risk_level": assessment.risk_level,
                            "risk_score": assessment.risk_score,
                            "contributing_factors": assessment.contributing_factors,
                        }

                except Exception:
                    # Data not available for this FHR; skip
                    continue

        return assessments, peak_info

    def _extract_key_findings(self, result: ForecastResult) -> list:
        """Extract key findings from all result data.

        Scans risk assessments for critical/elevated regions, external data
        for active alerts, and identifies the most significant signals.

        Returns:
            List of human-readable finding strings.
        """
        findings = []

        # From risk assessments
        critical_regions = []
        elevated_regions = []
        for a in result.risk_assessments:
            if a["risk_level"] == "CRITICAL":
                if a["label"] not in critical_regions:
                    critical_regions.append(a["label"])
            elif a["risk_level"] == "ELEVATED":
                if a["label"] not in elevated_regions:
                    elevated_regions.append(a["label"])

        if critical_regions:
            findings.append(
                f"CRITICAL fire weather risk identified in: "
                f"{', '.join(critical_regions)}"
            )
        if elevated_regions:
            findings.append(
                f"ELEVATED fire weather risk in: "
                f"{', '.join(elevated_regions)}"
            )

        # Peak risk details
        if result.peak_risk:
            pr = result.peak_risk
            factors = pr.get("contributing_factors", [])
            if factors:
                findings.append(
                    f"Peak risk driver at F{pr.get('fhr', 0):03d}: "
                    f"{factors[0]}"
                )

        # From external data
        ext = result.external_data

        # NWS alerts
        nws = ext.get("nws_alerts", {})
        features = nws.get("features", [])
        if features:
            # Count by event type
            event_types = {}
            for feat in features:
                props = feat.get("properties", {})
                evt = props.get("event", "Alert")
                event_types[evt] = event_types.get(evt, 0) + 1
            for evt, count in event_types.items():
                findings.append(f"Active NWS: {count} {evt}(s)")

        # SPC outlook
        spc = ext.get("spc_fire_outlook", {})
        if isinstance(spc, dict) and spc.get("features"):
            risk_levels_found = set()
            for feat in spc["features"]:
                props = feat.get("properties", {})
                risk = props.get("LABEL", props.get("label", ""))
                if risk:
                    risk_levels_found.add(risk)
            if risk_levels_found:
                findings.append(
                    f"SPC Fire Weather Outlook: {', '.join(sorted(risk_levels_found))}"
                )

        if not findings:
            findings.append(
                "No significant fire weather concerns identified in this scan."
            )

        return findings

    def _compile_bulletin(self, result: ForecastResult) -> str:
        """Compile a structured text bulletin from forecast results.

        Structured as:
            SITUATION | FORECAST | OUTLOOK | RECOMMENDATIONS

        Returns:
            Multi-line bulletin string.
        """
        config = result.config
        lines = []

        lines.append("=" * 60)
        lines.append(
            f"WEATHER BULLETIN - {config.forecast_type.upper().replace('_', ' ')}"
        )
        lines.append(f"Model: {config.model.upper()}  Cycle: {config.cycle}")
        lines.append("=" * 60)

        # SITUATION
        lines.append("")
        lines.append("SITUATION")
        lines.append("-" * 40)

        ext = result.external_data
        spc_disc = ext.get("spc_fire_discussion", "")
        if isinstance(spc_disc, str) and len(spc_disc) > 50:
            # First 500 chars of SPC discussion
            lines.append(spc_disc[:500].strip())
            if len(spc_disc) > 500:
                lines.append("  [truncated]")
        else:
            lines.append("No SPC discussion available.")

        nws = ext.get("nws_alerts", {})
        features = nws.get("features", [])
        if features:
            lines.append("")
            lines.append(f"Active NWS alerts: {len(features)}")
            for feat in features[:5]:
                props = feat.get("properties", {})
                headline = props.get("headline", props.get("event", "Alert"))
                lines.append(f"  - {headline}")
            if len(features) > 5:
                lines.append(f"  ... and {len(features) - 5} more")

        # FORECAST
        lines.append("")
        lines.append("FORECAST")
        lines.append("-" * 40)

        if result.risk_assessments:
            # Group by transect label, show peak FHR for each
            by_label = {}
            for a in result.risk_assessments:
                lbl = a["label"]
                if lbl not in by_label or a["risk_score"] > by_label[lbl]["risk_score"]:
                    by_label[lbl] = a

            for lbl, a in by_label.items():
                rh_min = a["rh_stats"].get("min", "N/A")
                wind_max = a["wind_stats"].get("max", "N/A")
                lines.append(
                    f"  {lbl}: {a['risk_level']} "
                    f"(score {a['risk_score']}/100, "
                    f"peak F{a['fhr']:03d})"
                )
                lines.append(
                    f"    RH min: {rh_min}%  |  Wind max: {wind_max} kt"
                )
                for factor in a.get("contributing_factors", [])[:2]:
                    lines.append(f"    - {factor}")
        else:
            lines.append("  No risk assessment data available.")

        # OUTLOOK
        lines.append("")
        lines.append("OUTLOOK")
        lines.append("-" * 40)

        if result.peak_risk:
            pr = result.peak_risk
            lines.append(
                f"Peak risk: {pr.get('risk_level', 'N/A')} at "
                f"F{pr.get('fhr', 0):03d} in {pr.get('region', 'unknown')}"
            )
            lines.append(
                f"Composite score: {pr.get('risk_score', 0)}/100"
            )
        else:
            lines.append("No significant risk evolution identified.")

        # RECOMMENDATIONS
        lines.append("")
        lines.append("RECOMMENDATIONS")
        lines.append("-" * 40)

        peak_level = result.peak_risk.get("risk_level", "LOW") if result.peak_risk else "LOW"
        if peak_level == "CRITICAL":
            lines.append(
                "- IMMEDIATE ACTION: Conditions support extreme fire behavior."
            )
            lines.append(
                "- Coordinate with fire weather forecasters and dispatch."
            )
            lines.append(
                "- Monitor cross-section evolution at 1-3 hour intervals."
            )
            lines.append(
                "- Pre-position resources in highest-risk corridors."
            )
        elif peak_level == "ELEVATED":
            lines.append(
                "- MONITOR CLOSELY: Multiple thresholds approaching exceedance."
            )
            lines.append(
                "- Increase monitoring frequency to 3-6 hour intervals."
            )
            lines.append(
                "- Review resource positioning for potential escalation."
            )
        elif peak_level == "MODERATE":
            lines.append(
                "- AWARENESS: Some fire weather parameters elevated."
            )
            lines.append(
                "- Maintain standard monitoring schedule."
            )
            lines.append(
                "- Watch for trend deterioration."
            )
        else:
            lines.append(
                "- ROUTINE: No significant fire weather concerns."
            )
            lines.append(
                "- Continue standard monitoring."
            )

        lines.append("")
        lines.append("=" * 60)
        lines.append(
            f"Generated in {result.execution_time_s:.1f}s  |  "
            f"{len(result.figures)} figures  |  "
            f"{len(result.risk_assessments)} assessments"
        )
        lines.append("=" * 60)

        return "\n".join(lines)

    def _compile_full_report(
        self,
        result: ForecastResult,
        output_dir: str,
    ) -> tuple:
        """Compile a full LaTeX report and attempt PDF generation.

        If the ReportBuilder module is available, delegates to it.
        Otherwise, generates a standalone LaTeX document.

        Returns:
            Tuple of (latex_path, pdf_path).  pdf_path may be empty if
            pdflatex is not available.
        """
        config = result.config

        # Build LaTeX content
        lines = []
        lines.append(r"\documentclass[11pt,letterpaper]{article}")
        lines.append(r"\usepackage[margin=1in]{geometry}")
        lines.append(r"\usepackage{graphicx}")
        lines.append(r"\usepackage{booktabs}")
        lines.append(r"\usepackage{hyperref}")
        lines.append(r"\usepackage{xcolor}")
        lines.append(r"\definecolor{critical}{RGB}{220,38,38}")
        lines.append(r"\definecolor{elevated}{RGB}{245,158,11}")
        lines.append(r"\definecolor{moderate}{RGB}{59,130,246}")
        lines.append(r"\begin{document}")
        lines.append("")

        # Title
        ftype_display = config.forecast_type.replace("_", " ").title()
        lines.append(r"\begin{center}")
        lines.append(
            r"{\LARGE\bfseries " + ftype_display + r" Forecast Report}\\[6pt]"
        )
        lines.append(
            r"{\large Model: " + config.model.upper()
            + r" \quad Cycle: " + config.cycle + r"}\\[4pt]"
        )
        lines.append(
            r"{\normalsize Scope: " + config.scope.title()
            + r" \quad FHR: "
            + str(config.fhr_range[0]) + "--" + str(config.fhr_range[1])
            + r"}"
        )
        lines.append(r"\end{center}")
        lines.append(r"\vspace{12pt}")

        # Key Findings
        lines.append(r"\section*{Key Findings}")
        if result.key_findings:
            lines.append(r"\begin{itemize}")
            for finding in result.key_findings:
                escaped = finding.replace("&", r"\&").replace("%", r"\%").replace("_", r"\_")
                lines.append(r"  \item " + escaped)
            lines.append(r"\end{itemize}")
        else:
            lines.append("No significant findings.")

        # Peak Risk
        if result.peak_risk:
            pr = result.peak_risk
            level = pr.get("risk_level", "LOW")
            color_map = {
                "CRITICAL": "critical",
                "ELEVATED": "elevated",
                "MODERATE": "moderate",
                "LOW": "black",
            }
            color = color_map.get(level, "black")
            lines.append(r"\section*{Peak Risk}")
            lines.append(
                r"{\large\textcolor{" + color + r"}{\textbf{"
                + level + r"}}} "
                + f"(score {pr.get('risk_score', 0)}/100)"
            )
            region = pr.get("region", "").replace("_", r"\_")
            if region:
                lines.append(f" -- {region}")
            peak_fhr = pr.get("fhr", 0)
            lines.append(f"\\\\Peak at F{peak_fhr:03d}")

        # Risk Assessment Table
        if result.risk_assessments:
            lines.append(r"\section*{Regional Risk Summary}")
            lines.append(r"\begin{tabular}{lllrrr}")
            lines.append(r"\toprule")
            lines.append(
                r"Region & FHR & Level & Score & RH min & Wind max \\"
            )
            lines.append(r"\midrule")

            # Show only peak per region to keep table manageable
            by_label = {}
            for a in result.risk_assessments:
                lbl = a["label"]
                if lbl not in by_label or a["risk_score"] > by_label[lbl]["risk_score"]:
                    by_label[lbl] = a

            for lbl, a in sorted(by_label.items(), key=lambda x: -x[1]["risk_score"]):
                safe_lbl = lbl.replace("_", r"\_").replace("&", r"\&")
                rh_min = a["rh_stats"].get("min", "--")
                wind_max = a["wind_stats"].get("max", "--")
                lines.append(
                    f"{safe_lbl} & F{a['fhr']:03d} & {a['risk_level']} & "
                    f"{a['risk_score']} & {rh_min} & {wind_max} \\\\"
                )

            lines.append(r"\bottomrule")
            lines.append(r"\end{tabular}")

        # Figures (include up to 12)
        included_figures = []
        for fig_path in result.figures[:12]:
            if os.path.isfile(fig_path):
                included_figures.append(fig_path)

        if included_figures:
            lines.append(r"\section*{Cross-Section Figures}")
            for fig_path in included_figures:
                # Use forward slashes for LaTeX compatibility
                rel_path = os.path.relpath(fig_path, output_dir).replace("\\", "/")
                lines.append(r"\begin{figure}[htbp]")
                lines.append(r"\centering")
                lines.append(
                    r"\includegraphics[width=\textwidth]{"
                    + rel_path + r"}"
                )
                basename = os.path.splitext(os.path.basename(fig_path))[0]
                safe_caption = basename.replace("_", r"\_")
                lines.append(r"\caption{" + safe_caption + r"}")
                lines.append(r"\end{figure}")
                lines.append(r"\clearpage")

        # Execution metadata
        lines.append(r"\section*{Metadata}")
        lines.append(r"\begin{itemize}")
        lines.append(
            r"\item Execution time: "
            + f"{result.execution_time_s:.1f}s"
        )
        lines.append(r"\item Figures generated: " + str(len(result.figures)))
        lines.append(
            r"\item Risk assessments: "
            + str(len(result.risk_assessments))
        )
        lines.append(
            r"\item External data sources: "
            + str(len(result.external_data))
        )
        lines.append(r"\end{itemize}")

        lines.append(r"\end{document}")

        # Write LaTeX file
        latex_content = "\n".join(lines)
        latex_path = os.path.join(output_dir, "forecast_report.tex")
        with open(latex_path, "w", encoding="utf-8") as f:
            f.write(latex_content)

        # Attempt PDF compilation
        pdf_path = ""
        try:
            import subprocess
            proc = subprocess.run(
                ["pdflatex", "-interaction=nonstopmode", "-output-directory",
                 output_dir, latex_path],
                capture_output=True, timeout=60, cwd=output_dir,
            )
            candidate = os.path.join(output_dir, "forecast_report.pdf")
            if os.path.isfile(candidate):
                pdf_path = candidate
        except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
            # pdflatex not available or failed; LaTeX source is still available
            pass

        return latex_path, pdf_path


# ============================================================================
# AgentWorkflow — pre-built workflows for common agent tasks
# ============================================================================

class AgentWorkflow:
    """Pre-built workflows for common AI agent forecast tasks.

    Provides high-level methods that configure and run ForecastGenerator
    with sensible defaults for specific use cases.

    Args:
        base_url: Dashboard API base URL.
    """

    def __init__(self, base_url: str = "http://127.0.0.1:5565", model: str = "hrrr"):
        self.base_url = base_url
        self.model = model
        self.gen = ForecastGenerator(base_url=base_url, model=model)

    def fire_weather_forecast(
        self,
        cycle: str = "latest",
        scope: str = ForecastScope.NATIONAL,
        center: Optional[tuple] = None,
        radius_deg: float = 3.0,
        output_dir: str = "",
    ) -> ForecastResult:
        """Full fire weather forecast workflow.

        Runs a complete fire weather analysis at the specified scope:
        external data ingestion, cross-section generation, risk assessment,
        and report compilation.

        Args:
            cycle: Model cycle key or "latest".
            scope: ForecastScope constant.
            center: (lat, lon) for regional/local scope.
            radius_deg: Radius for regional/local scope.
            output_dir: Output directory (auto-generated if empty).

        Returns:
            Completed ForecastResult with all phases.
        """
        config = ForecastConfig(
            scope=scope,
            forecast_type=ForecastType.FIRE_WEATHER,
            cycle=cycle,
            model=self.gen.model,
            center=center,
            radius_deg=radius_deg,
            fhr_step=6,
            output_dir=output_dir,
            report_format="full",
        )
        return self.gen.quick_forecast(config)

    def event_case_study(
        self,
        cycle_key: str,
        output_dir: str = "",
    ) -> ForecastResult:
        """Historical event deep-dive case study.

        Loads event metadata (suggested transects, coordinates) from the
        dashboard events API, then runs a comprehensive case study
        analysis with all available products.

        Args:
            cycle_key: Event cycle key (e.g. "20250107_00z").
            output_dir: Output directory.

        Returns:
            Completed ForecastResult with case study analysis.
        """
        # Fetch event details
        cs_tool = CrossSectionTool(base_url=self.base_url)

        try:
            event = cs_tool.get_event(cycle_key)
        except Exception:
            event = {}

        # Extract transects from event metadata
        transects = []
        center = None
        coords = event.get("coordinates", {})

        if coords:
            center_data = coords.get("center")
            if center_data:
                center = tuple(center_data)

            for section in coords.get("suggested_sections", []):
                transects.append({
                    "label": section.get("label", "Event transect"),
                    "start": tuple(section["start"]),
                    "end": tuple(section["end"]),
                    "products": section.get("products", []),
                })

        # Determine scope based on available data
        scope = ForecastScope.REGIONAL if center else ForecastScope.NATIONAL

        if not output_dir:
            output_dir = os.path.join(
                os.path.expanduser("~"), "hrrr-maps", "output", "case_studies",
                cycle_key,
            )

        config = ForecastConfig(
            scope=scope,
            forecast_type=ForecastType.CASE_STUDY,
            cycle=cycle_key,
            model=self.gen.model,
            center=center,
            radius_deg=3.0,
            fhr_step=3,
            regions=transects if transects else None,
            output_dir=output_dir,
            report_format="full",
        )

        return self.gen.quick_forecast(config)

    def daily_briefing(self, cycle: str = "latest") -> str:
        """Generate a quick daily weather briefing text.

        Runs a streamlined national fire weather scan and produces a
        short text briefing suitable for a morning situation report.

        Args:
            cycle: Model cycle key or "latest".

        Returns:
            Briefing text string.
        """
        config = ForecastConfig(
            scope=ForecastScope.NATIONAL,
            forecast_type=ForecastType.FIRE_WEATHER,
            cycle=cycle,
            fhr_range=(0, 24),
            fhr_step=6,
            report_format="data_only",
            include_spc=True,
            include_nws_alerts=True,
            include_observations=False,
        )
        plan = self.gen.plan(config)
        result = self.gen.execute_plan(plan)

        # Build briefing
        lines = []
        lines.append("=" * 60)
        lines.append("DAILY FIRE WEATHER BRIEFING")
        lines.append(
            f"Model: {config.model.upper()}  Cycle: {config.cycle}  "
            f"FHR: 0-24"
        )
        lines.append("=" * 60)
        lines.append("")

        # Top-line risk summary
        if result.peak_risk:
            pr = result.peak_risk
            lines.append(
                f"OVERALL RISK: {pr.get('risk_level', 'LOW')} "
                f"(score {pr.get('risk_score', 0)}/100)"
            )
            region = pr.get("region", "")
            if region:
                lines.append(f"Highest concern: {region} at F{pr.get('fhr', 0):03d}")
        else:
            lines.append("OVERALL RISK: LOW")

        lines.append("")

        # Regional breakdown
        lines.append("REGIONAL RISK LEVELS:")
        lines.append("-" * 40)

        if result.risk_assessments:
            by_label = {}
            for a in result.risk_assessments:
                lbl = a["label"]
                if lbl not in by_label or a["risk_score"] > by_label[lbl]["risk_score"]:
                    by_label[lbl] = a

            # Sort by risk score descending
            for lbl, a in sorted(by_label.items(), key=lambda x: -x[1]["risk_score"]):
                indicator = {
                    "CRITICAL": "[!!!]",
                    "ELEVATED": "[ ! ]",
                    "MODERATE": "[ - ]",
                    "LOW": "[   ]",
                }.get(a["risk_level"], "[   ]")
                lines.append(
                    f"  {indicator} {lbl}: {a['risk_level']} ({a['risk_score']}/100)"
                )

        lines.append("")

        # Key findings
        if result.key_findings:
            lines.append("KEY POINTS:")
            lines.append("-" * 40)
            for finding in result.key_findings:
                lines.append(f"  * {finding}")

        lines.append("")
        lines.append("=" * 60)
        lines.append(f"Briefing generated in {result.execution_time_s:.1f}s")
        lines.append("=" * 60)

        return "\n".join(lines)

    def compare_models(
        self,
        cycle: str,
        transect: dict,
        products: Optional[list] = None,
        fhrs: Optional[list] = None,
    ) -> dict:
        """Compare HRRR vs GFS on the same transect.

        Generates cross-section data from both models for the same
        transect and forecast hours, then computes differences in
        surface statistics.

        Args:
            cycle: Model cycle key.
            transect: Dict with "start" and "end" (lat, lon) tuples.
            products: Products to compare.  Default: ["wind_speed", "rh", "temperature"].
            fhrs: Forecast hours to compare.  Default: [0, 6, 12].

        Returns:
            Dict with per-model results and computed differences.
        """
        if products is None:
            products = ["wind_speed", "rh", "temperature"]
        if fhrs is None:
            fhrs = [0, 6, 12]

        start = tuple(transect["start"])
        end = tuple(transect["end"])

        hrrr_tool = CrossSectionTool(base_url=self.base_url, model="hrrr")
        gfs_tool = CrossSectionTool(base_url=self.base_url, model="gfs")

        comparison = {
            "cycle": cycle,
            "transect": transect,
            "products": products,
            "fhrs": fhrs,
            "hrrr": {},
            "gfs": {},
            "differences": {},
        }

        for fhr in fhrs:
            fhr_key = f"f{fhr:03d}"
            comparison["hrrr"][fhr_key] = {}
            comparison["gfs"][fhr_key] = {}
            comparison["differences"][fhr_key] = {}

            for product in products:
                # HRRR
                hrrr_data = hrrr_tool.get_data(start, end, cycle, fhr, product)
                hrrr_stats = hrrr_data.surface_stats() if hrrr_data else {}

                # GFS
                gfs_data = gfs_tool.get_data(start, end, cycle, fhr, product)
                gfs_stats = gfs_data.surface_stats() if gfs_data else {}

                comparison["hrrr"][fhr_key][product] = hrrr_stats
                comparison["gfs"][fhr_key][product] = gfs_stats

                # Compute differences where both have data
                diff = {}
                for stat_key in ("min", "max", "mean"):
                    hval = hrrr_stats.get(stat_key)
                    gval = gfs_stats.get(stat_key)
                    if hval is not None and gval is not None:
                        diff[stat_key] = round(hval - gval, 2)
                    else:
                        diff[stat_key] = None

                comparison["differences"][fhr_key][product] = {
                    "hrrr_minus_gfs": diff,
                }

        return comparison
