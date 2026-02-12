# AI Agent Research Platform — wxsection.com

> Central documentation for the wxsection.com AI-agent-native atmospheric research platform.
> 36 MCP tools, 6 Python modules (~6,600 lines), 88 curated weather events, 20 visualization products.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Getting Started](#getting-started)
  - [MCP Server (Claude Code / AI Agents)](#mcp-server)
  - [Python API (Scripts / Notebooks)](#python-api)
  - [HTTP API (Any Client)](#http-api)
- [MCP Server Tools Reference](#mcp-server-tools-reference)
  - [Investigation Tools](#investigation-tools-6)
  - [Cross-Section Tools](#cross-section-tools-9)
  - [External Data Tools](#external-data-tools-9)
  - [Fire Weather Tools](#fire-weather-tools-4)
  - [Terrain & Fuel Tools](#terrain--fuel-tools-8)
  - [Street View Tools](#street-view-tools-2)
- [Python API Reference](#python-api-reference)
  - [cross_section — Cross-Section Generation & Analysis](#cross_section)
  - [external_data — External Data Ingestion](#external_data)
  - [fire_risk — Fire Weather Risk Assessment](#fire_risk)
  - [case_study — Historical Event Case Studies](#case_study)
  - [report_builder — LaTeX Report Generation](#report_builder)
  - [forecast — Forecast Generator & Agent Orchestrator](#forecast)
- [Fire Risk Regions](#fire-risk-regions)
- [Investigation Workflow](#investigation-workflow)
- [Expert-Level Fire Weather Analysis](#expert-level-fire-weather-analysis)
- [Common Pitfalls](#common-pitfalls)
- [Agent Workflows](#agent-workflows)
  - [National Fire Risk Scan](#workflow-national-fire-scan)
  - [Localized Forecast](#workflow-localized-forecast)
  - [Historical Case Study](#workflow-case-study)
  - [Agent Swarm Pattern](#workflow-agent-swarm)
- [Configuration](#configuration)
- [HTTP API Reference](#http-api-reference)

---

## Overview

wxsection.com is an atmospheric cross-section visualization tool. AI agents can use it to:

- **Generate cross-sections** from HRRR (3km), GFS (0.25deg), and RRFS (3km) weather models
- **Get raw numerical data** (temperature, wind, humidity, etc.) as JSON arrays for computation
- **Browse 88 historical weather events** (fires, hurricanes, tornadoes, derechos, winter storms)
- **Ingest external data** — METARs, RAWS stations, SPC products, NWS alerts, elevation, drought
- **Assess fire weather risk** across 12 CONUS regions with composite scoring
- **Generate PDF reports** with LaTeX, including cross-section figures, tables, and analysis
- **Capture ground-truth imagery** via Google Street View at locations of interest
- **Run multi-agent forecast swarms** for national or localized weather analysis

Three access layers, same capabilities:

| Layer | Best For | Protocol |
|-------|----------|----------|
| **MCP Server** | Claude Code, AI agents | stdin/stdout JSON-RPC |
| **Python API** | Scripts, notebooks, agent code | `import tools.agent_tools` |
| **HTTP API** | Any client, browser, curl | REST over HTTP |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        AI Agents                            │
│   Claude Code · Custom Agents · Notebooks · Scripts         │
└──────┬──────────────────┬──────────────────┬────────────────┘
       │ MCP (JSON-RPC)   │ Python import    │ HTTP REST
       ▼                  ▼                  ▼
┌──────────────┐  ┌───────────────┐  ┌──────────────────────┐
│  MCP Server  │  │  Python API   │  │    HTTP API          │
│  36 tools    │  │  6 modules    │  │    /api/v1/*         │
│  mcp_server  │  │  agent_tools/ │  │    unified_dashboard │
│    .py       │  │  ~6,600 lines │  │    .py               │
└──────┬───────┘  └──────┬────────┘  └──────────┬───────────┘
       │                 │                       │
       └─────────────────┴───────────────────────┘
                         │
              ┌──────────▼──────────┐
              │   wxsection.com     │
              │   Dashboard API     │
              │   localhost:5565    │
              ├─────────────────────┤
              │ HRRR · GFS · RRFS  │
              │ 40 pressure levels  │
              │ 20 products         │
              │ 88 events           │
              │ Mmap cache (NVMe)   │
              └─────────────────────┘

External Data Sources:
  ├── IEM (Iowa Environmental Mesonet) — METAR/ASOS observations
  ├── Synoptic Data API — RAWS fire weather stations
  ├── SPC (Storm Prediction Center) — Fire outlooks & discussions
  ├── NWS (National Weather Service) — Alerts, AFDs, forecasts
  ├── Open-Meteo / USGS — Elevation data
  ├── US Drought Monitor — Drought status
  └── Google Street View API — Ground-truth imagery
```

---

## Getting Started

### MCP Server

The MCP server exposes all 36 tools to Claude Code and other MCP-compatible AI agents.

**Setup** — Add to `~/.claude/claude_code_config.json`:

```json
{
  "mcpServers": {
    "wxsection": {
      "command": "python",
      "args": ["C:/Users/drew/hrrr-maps/tools/mcp_server.py"],
      "env": {
        "WXSECTION_API_BASE": "http://localhost:5565",
        "GOOGLE_STREET_VIEW_KEY": "your-key-here"
      }
    }
  }
}
```

Restart Claude Code. Verify with `/mcp` — you should see 36 tools listed.

**Example** — An agent asks for fire risk:
```
Agent: Use national_fire_scan to check today's fire risk
→ MCP calls national_fire_scan(cycle="latest", fhr=12)
→ Returns JSON with risk scores for 12 CONUS regions
```

### Python API

For scripts, notebooks, and custom agent code.

```python
from tools.agent_tools.cross_section import CrossSectionTool
from tools.agent_tools.fire_risk import FireRiskAnalyzer
from tools.agent_tools.case_study import CaseStudy
from tools.agent_tools.report_builder import ReportBuilder, ReportConfig
from tools.agent_tools.forecast import ForecastGenerator, ForecastConfig, AgentWorkflow
from tools.agent_tools.external_data import get_metar_observations, get_nws_alerts

# Quick national fire scan
gen = ForecastGenerator()
scan = gen.national_fire_scan()
for region, info in sorted(scan.items(), key=lambda x: x[1]["risk_score"], reverse=True):
    print(f"{info['label']}: {info['risk_level']} ({info['risk_score']})")

# Generate a cross-section image
tool = CrossSectionTool()
tool.generate_image(
    start=(39.74, -104.99), end=(41.88, -87.63),
    cycle="latest", fhr=0, product="temperature",
    output_path="denver_chicago_temp.png"
)
```

### HTTP API

Direct REST calls from any client. No authentication required. Full docs in [API_GUIDE.md](API_GUIDE.md).

```bash
# Cross-section image
curl -o xsect.png "https://wxsection.com/api/v1/cross-section?start_lat=39.74&start_lon=-104.99&end_lat=41.88&end_lon=-87.63"

# Numerical data as JSON
curl "https://wxsection.com/api/v1/data?start_lat=39.74&start_lon=-104.99&end_lat=41.88&end_lon=-87.63&product=wind_speed"

# Browse events
curl "https://wxsection.com/api/v1/events?category=fire-ca"

# Capabilities discovery
curl "https://wxsection.com/api/v1/capabilities"
```

---

## MCP Server Tools Reference

`tools/mcp_server.py` — 36 tools via stdin/stdout JSON-RPC.

### Investigation Tools (6)

High-level tools for fire weather analysis. These orchestrate multiple lower-level tools to produce comprehensive assessments.

#### `investigate_location`
Full-picture investigation of a geographic point. Pulls model data, nearby METAR observations, NWS alerts, SPC outlooks, elevation, drought status, and fire risk assessment in a single call.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `lat` | float | -- | Latitude |
| `lon` | float | -- | Longitude |
| `cycle` | string | `latest` | Model cycle |
| `fhr` | int | `12` | Forecast hour |
| `model` | string | `hrrr` | Weather model |

#### `investigate_town`
Same as `investigate_location` but accepts a town name instead of coordinates. Geocodes the town and runs the full investigation.

| Parameter | Type | Description |
|-----------|------|-------------|
| `town` | string | Town name (e.g., `"Norman, OK"`, `"Boulder, CO"`) |
| `cycle` | string | Model cycle (default: `latest`) |
| `fhr` | int | Forecast hour (default: `12`) |
| `model` | string | Weather model (default: `hrrr`) |

#### `compare_model_obs`
Compare model predictions against actual METAR surface observations at a location. Critical for validating model data, especially when column-averaged cross-section values can be misleading about surface conditions.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `lat` | float | -- | Latitude |
| `lon` | float | -- | Longitude |
| `cycle` | string | `latest` | Model cycle |
| `fhr` | int | `0` | Forecast hour |
| `model` | string | `hrrr` | Weather model |
| `hours_back` | int | `3` | Hours of METAR history to pull |

Returns: Side-by-side comparison of model surface values vs observed METAR data (temperature, RH, wind speed/direction, dewpoint).

#### `get_point_forecast`
Extract model surface conditions at a single geographic point. Returns surface-level temperature, RH, wind speed, wind direction, and other fields from the model grid point nearest to the specified coordinates.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `lat` | float | -- | Latitude |
| `lon` | float | -- | Longitude |
| `cycle` | string | `latest` | Model cycle |
| `fhr` | int | `0` | Forecast hour |
| `model` | string | `hrrr` | Weather model |

#### `batch_investigate`
Scan multiple towns in a region. Runs `investigate_town` for each town and returns a summary table sorted by fire risk.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `towns` | list[string] | -- | List of town names (e.g., `["Norman, OK", "Moore, OK", "Edmond, OK"]`) |
| `cycle` | string | `latest` | Model cycle |
| `fhr` | int | `12` | Forecast hour |
| `model` | string | `hrrr` | Weather model |

#### `generate_cross_section_gif`
Generate an animated GIF cycling through multiple forecast hours for a cross-section transect. Useful for visualizing temporal evolution of atmospheric features.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `start_lat` | float | -- | Start latitude |
| `start_lon` | float | -- | Start longitude |
| `end_lat` | float | -- | End latitude |
| `end_lon` | float | -- | End longitude |
| `product` | string | `temperature` | Atmospheric product (maps to style internally) |
| `model` | string | `hrrr` | Weather model |
| `cycle` | string | `latest` | Model cycle (auto-resolves latest if not specified) |
| `fhr_min` | int | `0` | First forecast hour |
| `fhr_max` | int | `18` | Last forecast hour |

Returns: base64-encoded animated GIF image.

---

### Cross-Section Tools (9)

#### `get_capabilities`
Discover models, products, parameter constraints, coverage areas, and rate limits. No parameters.

#### `list_events`
Browse 88 historical weather events.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `category` | string | — | Filter: `fire-ca`, `fire-pnw`, `fire-co`, `fire-sw`, `hurricane`, `tornado`, `derecho`, `hail`, `ar`, `winter`, `other` |
| `has_data` | bool | — | Only events with data currently loaded |

#### `get_event`
Get event details, suggested cross-sections, and available forecast hours.

| Parameter | Type | Description |
|-----------|------|-------------|
| `cycle_key` | string | Event cycle key (e.g., `20250107_00z`) |

#### `list_cycles`
List available model cycles with forecast hours.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `model` | string | `hrrr` | `hrrr`, `gfs`, or `rrfs` |

#### `list_products`
List available visualization products with descriptions and units.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `model` | string | `hrrr` | Model to check product availability |

#### `generate_cross_section`
Generate a PNG cross-section between two points. Returns base64-encoded image + metadata.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `start_lat` | float | — | Start latitude (-90 to 90) |
| `start_lon` | float | — | Start longitude (-180 to 180) |
| `end_lat` | float | — | End latitude |
| `end_lon` | float | — | End longitude |
| `product` | string | `temperature` | See [Products](#products) |
| `model` | string | `hrrr` | `hrrr`, `gfs`, or `rrfs` |
| `cycle` | string | `latest` | Cycle key or `latest` |
| `fhr` | int | `0` | Forecast hour (0–48) |
| `y_axis` | string | `pressure` | `pressure` (hPa) or `height` (km) |
| `y_top` | int | `100` | Top of plot: 100, 200, 300, 500, 700 hPa |
| `units` | string | `km` | Distance axis: `km` or `mi` |

#### `generate_cross_section_gif`
Generate an animated GIF of a cross-section across multiple forecast hours. Same coordinate parameters as `generate_cross_section`, plus `fhr_min` and `fhr_max`. The `product` parameter maps to the visualization style internally. Returns base64-encoded animated GIF.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `start_lat` | float | -- | Start latitude (-90 to 90) |
| `start_lon` | float | -- | Start longitude (-180 to 180) |
| `end_lat` | float | -- | End latitude |
| `end_lon` | float | -- | End longitude |
| `product` | string | `temperature` | See [Products](#products) |
| `model` | string | `hrrr` | `hrrr`, `gfs`, or `rrfs` |
| `cycle` | string | `latest` | Cycle key or `latest` (auto-resolves) |
| `fhr_min` | int | `0` | First forecast hour in the animation |
| `fhr_max` | int | `18` | Last forecast hour in the animation |
| `y_axis` | string | `pressure` | `pressure` (hPa) or `height` (km) |
| `y_top` | int | `100` | Top of plot: 100, 200, 300, 500, 700 hPa |
| `units` | string | `km` | Distance axis: `km` or `mi` |

#### `get_atmospheric_data`
Get raw numerical data along a cross-section as JSON arrays. Same parameters as `generate_cross_section`. Returns 2D arrays `[n_levels × n_points]` (~40 × ~200 values).

**Field names by product:**

| Product | JSON field(s) | Units |
|---------|--------------|-------|
| `temperature` | `temperature_c` | C |
| `wind_speed` | `u_wind_ms`, `v_wind_ms` | m/s |
| `rh` | `rh_pct` | % |
| `theta_e` | `theta_e_k` | K |
| `omega` | `omega_hpa_hr` | hPa/hr |
| `vpd` | `vpd_hpa` | hPa |
| `fire_wx` | `rh_pct` | % |
| `dewpoint_dep` | `dewpoint_dep_c` | C |
| `q` | `specific_humidity_gkg` | g/kg |
| `vorticity` | `vorticity_1e5_s` | 10^-5 s^-1 |
| `shear` | `shear_1e3_s` | 10^-3 s^-1 |
| `lapse_rate` | `lapse_rate_c_km` | C/km |
| `cloud_total` | `cloud_total_gkg` | g/kg |
| `wetbulb` | `wetbulb_c` | C |
| `icing` | `icing_gkg` | g/kg |
| `smoke` | `smoke_hyb` | ug/m3 |
| `moisture_transport` | `moisture_transport_gmkgs` | g*m/kg/s |
| `pv` | `pv_pvu` | PVU |

#### `get_status`
Server health check. Returns ok, model, loaded count, memory MB, latest cycle.

---

### External Data Tools (9)

#### `get_metar`
Surface weather observations from ASOS/AWOS stations.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `stations` | string | — | Comma-separated ICAO IDs (e.g., `KDEN,KCOS,KGJT`) |
| `hours_back` | int | `3` | Hours of history (1–48) |

Returns: temperature, dewpoint, wind speed/direction/gust, visibility, pressure, clouds.

#### `find_stations`
Find weather stations near a geographic point.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `lat` | float | — | Search center latitude |
| `lon` | float | — | Search center longitude |
| `radius_km` | float | `100` | Search radius (max 500) |

#### `get_raws`
RAWS fire weather station observations (via Synoptic Data API).

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `lat` | float | — | Search center latitude |
| `lon` | float | — | Search center longitude |
| `radius_miles` | float | `50` | Search radius |
| `hours_back` | int | `6` | Hours of history |

Returns: air temp, RH, wind speed/direction/gust, fuel moisture.

#### `get_spc_fire_outlook`
SPC Fire Weather Outlook GeoJSON (CRITICAL, EXTREMELY CRITICAL, ELEVATED areas).

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `day` | int | `1` | 1 = today, 2 = tomorrow |

#### `get_spc_discussion`
Latest SPC Fire Weather Discussion text. No parameters.

#### `get_nws_alerts`
Active NWS weather alerts (Red Flag Warnings, Fire Weather Watches, etc.).

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `state` | string | — | Two-letter state code (e.g., `MT`, `CA`) |
| `lat` | float | — | Point-based search latitude |
| `lon` | float | — | Point-based search longitude |
| `event_type` | string | — | Filter: `Red Flag Warning`, `Fire Weather Watch`, etc. |

#### `get_forecast_discussion`
NWS Area Forecast Discussion (AFD) from a specific Weather Forecast Office.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `office` | string | — | WFO ID (e.g., `BOU`, `ABQ`, `MSO`, `LOX`, `SGX`) |

#### `get_elevation`
Terrain elevation at a geographic point.

| Parameter | Type | Description |
|-----------|------|-------------|
| `lat` | float | Latitude |
| `lon` | float | Longitude |

Returns: `{elevation_m, elevation_ft}`

#### `get_drought`
US Drought Monitor status with D0–D4 area percentages.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `state` | string | — | Two-letter state code (optional, for state-level data) |

---

### Fire Weather Tools (4)

#### `assess_fire_risk`
Assess fire weather risk along a cross-section transect. Returns composite risk score 0–100.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `start_lat` | float | — | Transect start latitude |
| `start_lon` | float | — | Transect start longitude |
| `end_lat` | float | — | Transect end latitude |
| `end_lon` | float | — | Transect end longitude |
| `cycle` | string | `latest` | Model cycle |
| `fhr` | int | `0` | Forecast hour |
| `model` | string | `hrrr` | Weather model |

**Risk levels:**

| Level | Score | Meaning |
|-------|-------|---------|
| CRITICAL | 70–100 | Extreme fire danger, Red Flag conditions |
| ELEVATED | 50–69 | High fire danger |
| MODERATE | 30–49 | Moderate fire danger |
| LOW | 0–29 | Low fire danger |

**Scoring formula:** 40% RH deficit + 30% wind excess + 20% instability + 10% VPD

#### `national_fire_scan`
Quick scan of fire risk across 12 CONUS fire-prone regions. Returns all regions sorted by risk score.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `cycle` | string | `latest` | Model cycle |
| `fhr` | int | `12` | Forecast hour (afternoon peak recommended) |
| `model` | string | `hrrr` | Weather model |

#### `compute_fire_indices`
Calculate fire weather indices from atmospheric values.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `temp_c` | float | — | Surface temperature (C) |
| `rh_pct` | float | — | Surface relative humidity (%) |
| `wind_kt` | float | — | Surface wind speed (kt) |
| `temp_700_c` | float | — | 700 hPa temperature (C), optional |
| `dewpoint_850_c` | float | — | 850 hPa dewpoint (C), optional |

Returns: VPD (hPa), Fosberg FWI, Haines Index (if upper-air data provided).

#### `sub_metro_fire_scan`
Granular WUI fire risk within a metro area. Breaks metros into foothills, urban cores, and specific fire corridors.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `metro` | string | — | Metro key: `denver_metro`, `colorado_springs`, `la_metro`, `phoenix_metro`, `albuquerque_metro`, `reno_tahoe` |
| `cycle` | string | `latest` | Model cycle |
| `fhr` | int | `12` | Forecast hour |
| `model` | string | `hrrr` | Weather model |

Returns per-sub-area risk scores. E.g., for `denver_metro`: Boulder Foothills, Denver Proper, Golden/Morrison, Evergreen/Conifer, Castle Rock/Palmer Divide, Loveland/Fort Collins.

---

### Terrain & Fuel Tools (8)

Expert-level fire weather analysis tools. These address the most common mistakes in fire weather forecasting: ignoring fuels, assuming flat terrain, overclaiming wind speeds, and misidentifying overnight wind shifts as "recovery."

#### `analyze_terrain`
Analyze terrain complexity around a point. Identifies canyons, valleys, slopes, and flat areas. Canyon terrain creates channeled winds and extreme fire behavior that flat grassland analysis misses.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `lat` | float | -- | Latitude |
| `lon` | float | -- | Longitude |
| `radius_km` | float | `15` | Analysis radius |

#### `city_terrain`
Assess terrain around a city by quadrant (N/E/S/W/NE/SE/SW/NW). Maps terrain features to fire difficulty ratings. Includes hardcoded expert knowledge for **232 fire-vulnerable US cities** across 6 regions (California 62, PNW/Rockies 47, Colorado/Great Basin 38, Southwest 29, Southern Plains 28, Southeast/Misc 25).

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `lat` | float | -- | City center latitude |
| `lon` | float | -- | City center longitude |
| `city_name` | string | -- | City name for expert knowledge lookup |
| `radius_km` | float | `20` | Analysis radius |

#### `assess_fuels`
Assess current fuel conditions -- the #1 factor in fire behavior. Analyzes recent weather history (warm spells drying fuels, precipitation, RH trends), drought status, and seasonal context (winter freeze-dried grass vs summer cured grass).

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `lat` | float | -- | Latitude |
| `lon` | float | -- | Longitude |
| `station_id` | string | -- | Optional METAR station ID for weather history |

#### `get_ignition_sources`
Get ignition risk sources near a location -- trucking corridors (chains cause sparks), power lines, railroads, prescribed burn areas. Database covers **73 cities** with verified ignition source profiles. Critical for Amarillo/OKC/I-40 corridor where trucking is the #1 ignition source.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `lat` | float | -- | Latitude |
| `lon` | float | -- | Longitude |
| `city_name` | string | -- | Optional city name for corridor lookup |

#### `detect_wind_shifts`
Detect wind direction shifts in HRRR forecast. Identifies cold front passages that reverse firelines. A wind shift is NOT "nighttime recovery" -- it reverses ALL fire spread directions while winds stay gusty.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `lat` | float | -- | Latitude |
| `lon` | float | -- | Longitude |
| `model` | string | `hrrr` | Weather model |

#### `classify_overnight`
Classify overnight fire weather conditions. Determines whether overnight is true recovery (calm + humid), frontal shift (wind reversal), partial recovery, or no recovery. Prevents incorrect "nighttime recovery" claims in forecasts.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `lat` | float | -- | Latitude |
| `lon` | float | -- | Longitude |
| `model` | string | `hrrr` | Weather model |

#### `verify_winds`
Verify wind speed claims against ALL available observations (ASOS + state mesonets + RAWS). Prevents overclaiming wind speeds in reports. Returns actual max gust/sustained from every station in radius.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `lat` | float | -- | Latitude |
| `lon` | float | -- | Longitude |
| `radius_miles` | float | `30` | Search radius |
| `hours_back` | int | `24` | Hours of history to check |

#### `get_fire_climatology`
Get fire weather climatology for a station -- what is normal vs extreme for this location. Contextualizes observations: is 9% RH "bad" or "catastrophic" here? Is a 39kt gust "big" or "run of the mill"?

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `station_id` | string | -- | METAR station ID (e.g., `KAMA`, `KOKC`) |
| `month` | int | -- | Optional month (1-12) for seasonal context |

---

### Street View Tools (2)

Requires `GOOGLE_STREET_VIEW_KEY` environment variable.

#### `get_street_view`
Google Street View image at a location for ground-truth assessment.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `lat` | float | — | Latitude |
| `lon` | float | — | Longitude |
| `heading` | int | `0` | Camera heading (0=N, 90=E, 180=S, 270=W) |
| `pitch` | int | `0` | Camera pitch (-90 to 90) |
| `fov` | int | `90` | Field of view (10–120 degrees) |

Returns: base64-encoded JPEG image.

#### `get_street_view_panorama`
Multiple Street View images at different headings for panoramic coverage.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `lat` | float | — | Latitude |
| `lon` | float | — | Longitude |
| `n_views` | int | `4` | Number of views (4 = 90-degree steps, 8 = 45-degree) |

Returns: Array of base64-encoded images with heading/direction metadata.

---

## Python API Reference

`tools/agent_tools/` — 6 modules, ~6,600 lines total.

### cross_section

**`tools/agent_tools/cross_section.py`** (302 lines) — Generate and analyze HRRR/GFS/RRFS cross-sections.

#### CrossSectionTool

```python
from tools.agent_tools.cross_section import CrossSectionTool

tool = CrossSectionTool(base_url="http://localhost:5565", model="hrrr")
```

| Method | Description | Returns |
|--------|-------------|---------|
| `generate_image(start, end, cycle, fhr, product, output_path, y_top=300)` | Save cross-section PNG to file | `bool` |
| `get_data(start, end, cycle, fhr, product)` | Get numerical data | `CrossSectionData` |
| `get_capabilities()` | Models, products, cycles | `dict` |
| `get_events(category=None, has_data=None)` | Historical events | `list` |
| `get_event(cycle_key)` | Single event details | `dict` |
| `batch_images(transects, cycle, fhrs, products, output_dir, prefix="", y_top=300)` | Batch image generation | `list[str]` |

#### CrossSectionData

Returned by `CrossSectionTool.get_data()`. Provides analysis helpers.

| Property/Method | Description | Returns |
|-----------------|-------------|---------|
| `pressures` | Pressure levels in hPa | `list` |
| `distances` | Distances along transect (km) | `list` |
| `lats`, `lons` | Geographic coordinates along path | `list` |
| `data_2d` | Main 2D array [levels x points] | `list[list]` |
| `surface_values()` | Values at surface level | `list` |
| `level_values(hpa)` | Values at specific pressure level | `list` |
| `surface_stats()` | Min/max/mean of surface values | `dict` |
| `pct_exceeding(threshold, above=True)` | % of surface values exceeding threshold | `float` |
| `column_min_below(top_hpa)` | Minimum value below given level | `float` |
| `column_max_below(top_hpa)` | Maximum value below given level | `float` |

---

### external_data

**`tools/agent_tools/external_data.py`** (590 lines) — Ingest observations, advisories, elevation, drought, and Street View.

```python
from tools.agent_tools.external_data import (
    get_metar_observations, get_nearby_stations, get_raws_observations,
    get_spc_fire_weather_outlook, get_spc_fire_discussion, get_spc_mesoscale_discussions,
    get_nws_alerts, get_nws_forecast_discussion,
    get_elevation, get_elevation_profile, get_drought_status,
    get_street_view_image, street_view_panorama, street_view_along_path,
)
```

| Function | Description |
|----------|-------------|
| `get_metar_observations(stations, start, end, hours_back=3)` | ASOS/AWOS surface observations |
| `get_nearby_stations(lat, lon, radius_km=100)` | Find stations near a point |
| `get_raws_observations(stations, lat, lon, radius_miles=50, hours_back=6)` | RAWS fire weather stations |
| `get_spc_fire_weather_outlook(day=1)` | SPC fire outlook polygons (GeoJSON) |
| `get_spc_fire_discussion()` | SPC fire weather discussion text |
| `get_spc_mesoscale_discussions()` | Active mesoscale discussions |
| `get_nws_alerts(lat, lon, state, event_type)` | Active NWS alerts (GeoJSON) |
| `get_nws_forecast_discussion(office)` | NWS Area Forecast Discussion text |
| `get_elevation(lat, lon)` | Terrain elevation at a point |
| `get_elevation_profile(start_lat, start_lon, end_lat, end_lon, n_points=100)` | Elevation along a path |
| `get_drought_status(fips, state)` | US Drought Monitor conditions |
| `get_street_view_image(lat, lon, heading=0, pitch=0, fov=90, size="640x480", output_path=None)` | Single Street View image |
| `street_view_panorama(lat, lon, output_dir, prefix="sv", n_views=4)` | Multi-heading panorama |
| `street_view_along_path(start_lat, start_lon, end_lat, end_lon, output_dir, n_points=10)` | Street View along a transect |

API keys: `GOOGLE_STREET_VIEW_KEY` env var (loaded from `.env` if present).

---

### fire_risk

**`tools/agent_tools/fire_risk.py`** (803 lines) — Fire weather risk assessment with composite scoring.

```python
from tools.agent_tools.fire_risk import FireRiskAnalyzer, FIRE_REGIONS, FireRiskAssessment

analyzer = FireRiskAnalyzer(base_url="http://localhost:5565")
```

#### FireRiskAnalyzer

| Method | Description | Returns |
|--------|-------------|---------|
| `analyze_transect(start, end, cycle, fhr, label)` | Risk assessment for one transect/fhr | `FireRiskAssessment` |
| `analyze_temporal(start, end, cycle, fhrs, label)` | Risk over multiple forecast hours | `list[FireRiskAssessment]` |
| `quick_scan(cycle, fhrs, regions)` | Scan all 12 CONUS regions | `dict` |
| `risk_score_from_data(rh_stats, wind_stats, temp_stats)` | Compute score from stats | `(score, level, factors)` |

**Static methods:**

| Method | Description |
|--------|-------------|
| `compute_vpd(temp_c, rh_pct)` | Vapor pressure deficit (hPa) |
| `compute_haines_index(temp_950, temp_850, temp_700, dewpoint_850)` | Haines Index (stability + moisture) |
| `compute_lapse_rate(temp_low_c, temp_high_c, height_diff_m)` | Environmental lapse rate (C/km) |

#### FireRiskAssessment (dataclass)

Fields: `transect_start`, `transect_end`, `transect_label`, `cycle`, `fhr`, `risk_level`, `risk_score`, `contributing_factors`, `threshold_exceedances`, `temporal_peak`, `rh_stats`, `wind_stats`, `temp_stats`, `summary`.

#### Risk Scoring

```
Score = 40% * RH_deficit + 30% * wind_excess + 20% * instability + 10% * VPD

RH deficit:    score = (30 - mean_rh) / 30 * 100, capped at 100
Wind excess:   score = (mean_wind - 10) / 30 * 100, capped at 100
Instability:   score based on temp deviation from standard lapse rate
VPD:           score = vpd / 20 * 100, capped at 100

Levels: CRITICAL (70-100), ELEVATED (50-69), MODERATE (30-49), LOW (0-29)
```

**Thresholds:**
- Red Flag: RH < 15%, sustained wind > 25kt
- Critical: RH < 8%, sustained wind > 30kt
- Extreme VPD: > 13 hPa

---

### case_study

**`tools/agent_tools/case_study.py`** (931 lines) — Historical event case study framework.

```python
from tools.agent_tools.case_study import CaseStudy, TransectSpec, STANDARD_PRODUCTS

# From curated event
cs = CaseStudy.from_event("20250107_00z", "output/palisades_fire")

# Manual setup
cs = CaseStudy("Camp Fire", "20181108_06z", "output/camp_fire")
cs.add_transect("NE-SW", start=(39.8, -121.4), end=(39.6, -121.9))
```

#### CaseStudy

| Method | Description | Returns |
|--------|-------------|---------|
| `from_event(cycle_key, output_dir)` | Create from curated API event | `CaseStudy` |
| `add_transect(label, start, end, products, description)` | Add analysis transect | `TransectSpec` |
| `add_standard_transects(center_lat, center_lon, radius_deg=3.0)` | Auto-generate 4 cardinal transects | `list[TransectSpec]` |
| `analyze_transect(label, fhrs, products)` | Analyze one transect | `list[AnalysisResult]` |
| `analyze_all(fhrs)` | Analyze all transects | `dict` |
| `temporal_evolution(label, product, fhr_range)` | Track field evolution over time | `list[dict]` |
| `compare_events(other, label, product, fhr)` | Compare two events | `dict` |
| `generate_summary()` | Aggregate key findings | `dict` |
| `export_data(format="json")` | Export all results to file | `str` (path) |
| `get_figure_manifest()` | List all generated figures | `list[dict]` |

#### Standard Product Sets

```python
STANDARD_PRODUCTS = {
    "synoptic":     ["temperature", "wind_speed", "omega", "rh"],
    "fire_weather": ["wind_speed", "rh", "temperature", "theta_e"],
    "severe":       ["omega", "wind_speed", "theta_e", "temperature"],
    "winter":       ["temperature", "rh", "wind_speed", "omega"],
    "tropical":     ["wind_speed", "omega", "rh", "theta_e"],
}
```

---

### report_builder

**`tools/agent_tools/report_builder.py`** (1,124 lines) — LaTeX report generation with templates and PDF compilation.

```python
from tools.agent_tools.report_builder import ReportBuilder, ReportConfig, Figure, Section

# Use a template
report = ReportBuilder.forecast_template(
    title="Fire Weather Forecast — Feb 9, 2026",
    scope="National",
    output_dir="output/forecast"
)

# Add content
report.add_figure("Synoptic Analysis", "figures/wind.png", "Surface wind analysis")
report.set_abstract("High wind event across the Front Range...")

# Compile
pdf_path = report.compile_pdf()
```

#### ReportBuilder

| Method | Description | Returns |
|--------|-------------|---------|
| `add_section(title, content, label, level)` | Add report section | `Section` |
| `add_figure(section, path, caption, label, width)` | Add figure to section | `Figure` |
| `add_figure_grid(section, figures, caption, ncols=2)` | Multi-panel figure grid | `str` |
| `add_table(section, caption, headers, rows, label)` | Add data table | `Table` |
| `add_alert_box(text, color, title)` | Colored alert box | `str` |
| `add_key_finding(text)` | Highlighted finding box | `str` |
| `set_abstract(text)` | Set report abstract | — |
| `set_methodology(text)` | Set methodology section | — |
| `generate_latex()` | Generate complete LaTeX source | `str` |
| `save_latex(filename)` | Save .tex file | `str` (path) |
| `compile_pdf(passes=2)` | Compile to PDF via pdflatex | `str` (path) |

**Templates** (class methods, return pre-configured `ReportBuilder`):

| Template | Pre-populated Sections |
|----------|----------------------|
| `forecast_template(title, scope, output_dir)` | Situation Overview, Synoptic Analysis, Mesoscale Analysis, Fire Weather Assessment, Forecast Discussion, Recommendations |
| `case_study_template(event_name, date, output_dir)` | Event Overview, Synoptic Environment, Mesoscale Analysis, Temporal Evolution, Cross-Section Analysis, Ground Truth, Conclusions |
| `bulletin_template(title, output_dir)` | Alert, Key Findings, Discussion, Action Items |

#### ReportConfig (dataclass)

Fields: `title`, `author` (default: "AI Atmospheric Research Agent"), `date`, `report_type` (forecast/case_study/bulletin/research), `institution` (default: "wxsection.com"), `confidential`, `paper_size`, `font_size`.

#### Utility Functions

| Function | Description |
|----------|-------------|
| `escape_latex(text)` | Escape special LaTeX characters |
| `format_number(val, decimals=1, units="")` | Format number for LaTeX |
| `risk_color_box(level)` | Colored risk level box |
| `format_timestamp(cycle, fhr)` | Human-readable valid time |
| `table_from_dict(data, caption)` | Quick two-column table from dict |

---

### forecast

**`tools/agent_tools/forecast.py`** (1,832 lines) — Forecast generator and agent swarm orchestrator.

```python
from tools.agent_tools.forecast import (
    ForecastGenerator, ForecastConfig, AgentWorkflow,
    ForecastScope, ForecastType
)

# Quick national fire weather forecast
gen = ForecastGenerator()
config = ForecastConfig(
    scope=ForecastScope.NATIONAL,
    forecast_type=ForecastType.FIRE_WEATHER,
    output_dir="output/forecast"
)
result = gen.quick_forecast(config)
print(f"PDF: {result.report_path}")
print(f"Figures: {len(result.figures)}")
print(f"Peak risk: {result.peak_risk}")
```

#### ForecastGenerator

| Method | Description | Returns |
|--------|-------------|---------|
| `plan(config)` | Create execution plan (no API calls) | `ForecastPlan` |
| `execute_plan(plan, progress_callback)` | Execute plan, generate figures + report | `ForecastResult` |
| `quick_forecast(config)` | Plan + execute in one call | `ForecastResult` |
| `national_fire_scan(cycle, fhrs)` | Quick scan of 12 CONUS regions | `dict` |
| `localized_forecast(lat, lon, cycle, radius_deg=2.0)` | Forecast centered on a point | `ForecastResult` |
| `generate_bulletin(config)` | Short text bulletin (no PDF) | `str` |

#### AgentWorkflow

Pre-built workflows for common agent tasks.

```python
wf = AgentWorkflow()
```

| Method | Description | Returns |
|--------|-------------|---------|
| `fire_weather_forecast(cycle, scope, center, radius_deg, output_dir)` | Full fire weather forecast | `ForecastResult` |
| `event_case_study(cycle_key, output_dir)` | Historical event deep-dive | `ForecastResult` |
| `daily_briefing(cycle)` | Quick daily weather briefing text | `str` |
| `compare_models(cycle, transect, products, fhrs)` | HRRR vs GFS comparison | `dict` |

#### ForecastConfig (dataclass)

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `scope` | str | `national` | `national`, `regional`, `local`, `point` |
| `forecast_type` | str | `fire_weather` | `fire_weather`, `severe`, `winter`, `general`, `case_study` |
| `cycle` | str | `latest` | Model cycle key |
| `model` | str | `hrrr` | Weather model |
| `fhr_range` | tuple | `(0, 48)` | Start and end forecast hours |
| `fhr_step` | int | `1` | Step between forecast hours |
| `regions` | list | — | Region names or custom transect dicts |
| `center` | tuple | — | (lat, lon) for local/point scope |
| `radius_deg` | float | `3.0` | Radius for local scope |
| `include_external_data` | bool | `True` | Fetch SPC/NWS/METAR data |
| `output_dir` | str | — | Output directory |
| `report_format` | str | `full` | `full` (PDF), `bulletin`, `data_only` |

#### Module-Level Helpers

| Function | Description |
|----------|-------------|
| `get_latest_cycle(model)` | Get latest available cycle key |
| `fhr_list(start, end, step)` | Generate forecast hour list |
| `auto_transects_for_region(name)` | Generate transects for a named fire region |
| `summarize_results(result)` | Human-readable ForecastResult summary |

---

## Fire Risk Regions

12 predefined CONUS fire-prone regions used by `national_fire_scan` and `quick_scan`.

| Region Key | Label | Transect Start | Transect End |
|-----------|-------|----------------|--------------|
| `northern_rockies` | Northern Rockies (ID/MT) | 47.5, -116.0 | 45.0, -110.0 |
| `high_plains_north` | High Plains North (WY/NE) | 43.0, -106.0 | 41.0, -102.0 |
| `high_plains_south` | High Plains South (NM/TX) | 36.5, -106.0 | 35.0, -102.0 |
| `southwest_az` | Southwest (AZ) | 34.5, -114.0 | 32.0, -109.0 |
| `socal` | Southern California | 34.5, -119.5 | 33.5, -117.0 |
| `pacific_nw` | Pacific NW (WA/OR) | 47.0, -123.0 | 44.0, -120.0 |
| `sierra_nevada` | Sierra Nevada | 39.0, -122.0 | 37.0, -118.0 |
| `front_range` | Front Range (CO) | 40.5, -106.0 | 38.5, -104.0 |
| `great_basin` | Great Basin (NV) | 41.0, -118.0 | 39.0, -114.0 |
| `texas_panhandle` | Texas Panhandle | 36.0, -103.0 | 34.0, -100.0 |
| `oklahoma` | Oklahoma | 36.5, -100.0 | 35.0, -97.0 |
| `central_ca` | Central CA Coast/Valley | 38.0, -123.0 | 36.0, -119.0 |

---

## Investigation Workflow

The recommended approach for fire weather analysis using the investigation-oriented tools. These tools orchestrate multiple lower-level calls and provide a comprehensive picture that avoids the pitfalls of relying on any single data source.

### 1. Start with the Full Picture

Use `investigate_location` or `investigate_town` as your first call. These pull model data, METAR observations, NWS alerts, SPC outlooks, elevation, drought status, and fire risk assessment in a single invocation. This gives you the broadest possible context before drilling down.

```
Agent: Use investigate_town for "Norman, OK"
--> Returns: model surface conditions, nearby METAR obs, active alerts,
    SPC fire outlook, elevation, drought status, fire risk score
```

### 2. Validate Model Data Against Observations

Use `compare_model_obs` to compare model predictions against actual METAR surface observations. This step is critical because column-averaged model data from cross-sections can be highly misleading about surface conditions (see [Common Pitfalls](#common-pitfalls)).

```
Agent: Use compare_model_obs at lat=35.22, lon=-97.44
--> Returns: model says surface RH 42%, METAR reports 11%
    (column average was masking critically dry surface layer)
```

### 3. Get Model Surface Conditions

Use `get_point_forecast` to extract model surface-level values at a specific point. Unlike cross-section data which represents vertical slices, this returns the model's own surface fields (2m temperature, 2m RH, 10m wind) which are more representative of ground conditions.

### 4. Visualize Vertical Structure

Use `generate_cross_section` for a static snapshot and `generate_cross_section_gif` for temporal evolution. Cross-sections reveal vertical structure that surface observations cannot: elevated mixed layers, low-level jets, dry intrusions, and inversions.

```
Agent: Use generate_cross_section_gif with product=fire_wx, fhr_min=0, fhr_max=12
--> Returns: animated GIF showing fire weather composite evolving through the day
```

### 5. Assess Ground-Level Fuels and WUI

Use `get_street_view` to capture ground-truth imagery at locations of interest. This reveals fuel type (grass, brush, timber), fuel density, terrain, structures in the WUI (wildland-urban interface), and defensible space around buildings.

### 6. Scan a Region

Use `batch_investigate` to scan multiple towns in a region. This runs the full investigation for each town and returns results sorted by risk, making it easy to identify the most dangerous locations.

```
Agent: Use batch_investigate for ["Norman, OK", "Moore, OK", "Edmond, OK", "Stillwater, OK"]
--> Returns: summary table with risk scores, sorted highest to lowest
```

---

## Expert-Level Fire Weather Analysis

The recommended workflow for expert-level fire weather analysis, based on feedback from operational fire weather forecasters. These steps address the most common mistakes agents make when analyzing fire weather.

### 1. Assess Fuels FIRST

Use `assess_fuels` before anything else. Fuels are the main story in fire weather, not wind. A 40mph wind event over green irrigated cropland is a non-event. A 20mph wind event over freeze-dried dormant grass in January is a disaster. Fuel conditions determine whether a fire starts, spreads, and resists suppression.

```
Agent: Use assess_fuels at lat=35.2, lon=-101.8
--> Returns: fuel type (dormant winter grass), recent precip (none in 3 weeks),
    drought status (D2 Severe), seasonal context (freeze-dried, highly receptive)
```

### 2. Understand Terrain

Use `analyze_terrain` and `city_terrain` to characterize the landscape. Canyon terrain creates channeled winds and extreme fire behavior that flat grassland analysis completely misses. A fire burning into a canyon will accelerate catastrophically; the same fire on flat ground may be manageable.

```
Agent: Use city_terrain at lat=35.2, lon=-101.8, city_name="Amarillo"
--> Returns: mostly flat grassland, Palo Duro Canyon to SE (extreme fire difficulty),
    Canadian River breaks to N (moderate terrain complexity)
```

### 3. Verify Conditions

Use `verify_winds`, `get_metar`, and `get_fire_climatology` to ground-truth conditions. Do not overclaim wind speeds in reports. A model forecast of 45kt gusts means nothing if the nearest ASOS only recorded 32kt. Climatology tells you whether observed values are "noteworthy" or "just another Tuesday" for that location.

```
Agent: Use verify_winds at lat=35.2, lon=-101.8
--> Returns: max observed gust 37kt at KAMA, 34kt at KDHT, 29kt at mesonet
    (model was overclaiming by ~8kt)
```

### 4. Check Ignition Sources

Use `get_ignition_sources` to identify what could start a fire. In the Texas Panhandle and I-40 corridor, trucking sparks (tire chains, dragging equipment) are the #1 ignition source. In the WUI, power lines and prescribed burns that escape are common starters.

### 5. Analyze Wind Shifts

Use `detect_wind_shifts` and `classify_overnight` to identify frontal passages. A "nighttime recovery" claim is dangerous if a cold front is actually passing -- the wind reverses direction while staying gusty, which reverses ALL fire spread directions. Firefighters positioned on the "safe" side of a fire suddenly find themselves on the active flank.

```
Agent: Use classify_overnight at lat=35.2, lon=-101.8
--> Returns: classification="frontal_shift", wind_shift_timing="03Z",
    direction_change="SW->NW", NOT true recovery (winds remain 20-25kt through shift)
```

### 6. Visualize

Use `generate_cross_section` and `generate_cross_section_gif` to create the visual analysis. Pick transects that go THROUGH the terrain features that matter -- draw a line through the canyon, not parallel to it. Use `fire_wx` product for the composite view, `wind_speed` and `rh` for individual fields.

---

## Common Pitfalls

### Column-Averaged Data vs Surface Conditions

Cross-section data averages through the full vertical column. A surface RH of 11% can show as 45% in column averages because moist air aloft dilutes the critically dry surface layer. **ALWAYS compare with METAR observations using `compare_model_obs`.** This is the single most important validation step in fire weather analysis.

### Wind Units

Cross-section wind data may be in m/s. METAR winds are in knots. Always check units before comparing or combining wind values from different sources. Conversion: 1 m/s = 1.944 knots.

### Fire Risk Scores

The algorithmic risk scores from `assess_fire_risk` and `national_fire_scan` use column-averaged data and may significantly underestimate danger. A location with a "MODERATE" algorithmic risk score can have genuinely critical surface conditions. Use the investigation tools (`investigate_location`, `compare_model_obs`, `get_point_forecast`) for real assessment rather than relying solely on the composite score.

### Nighttime Recovery vs Frontal Wind Shift

Do not say "nighttime recovery" without checking. Use `classify_overnight` to determine whether overnight conditions represent true recovery (calm winds + rising humidity) or a cold front wind shift that reverses firelines while winds stay gusty. Mislabeling a frontal shift as "recovery" is dangerous -- it implies firefighters can safely reposition when conditions are actually worsening from a new direction.

### Fuels Are Often the Main Story

Do not focus only on wind. Fuels are often the dominant factor in fire behavior, especially in winter. Freeze-dried dormant grass is MORE flammable than summer-cured grass because it has lower live fuel moisture content. A January grass fire in the Texas Panhandle can spread faster than an August grass fire. Use `assess_fuels` to understand the fuel context before writing wind-focused analysis.

### Terrain Assumptions

Do not assume flat grassland. Use `analyze_terrain` or `city_terrain` to check for canyons, river breaks, and valleys. Palo Duro Canyon near Amarillo, the Canadian River breaks, and the Wichita Mountains near OKC all create localized extreme fire behavior that flat-terrain analysis completely misses.

### Wind Speed Verification

Verify wind claims against actual mesonet observations before publishing. Use `verify_winds` to check what stations actually recorded. Model forecasts regularly overclaim wind speeds by 5-10 knots. Reporting "50mph gusts" when the nearest ASOS only recorded 38kt undermines credibility and may trigger inappropriate response levels.

### Winter Fire Behavior

Winter fires are different from summer fires. Freeze-dried dormant grass is MORE flammable than summer-cured grass because dormant vegetation has lost all live fuel moisture. Warm spells in January/February that melt snow but leave grass exposed create the most dangerous conditions. Use `assess_fuels` with seasonal context to capture this.

---

## Agent Workflows

### Workflow: National Fire Scan

Quickest way to assess fire risk across the US.

```python
# Via MCP (Claude Code)
# Agent calls: national_fire_scan(cycle="latest", fhr=12)

# Via Python
from tools.agent_tools.forecast import ForecastGenerator
gen = ForecastGenerator()
scan = gen.national_fire_scan()
# Returns dict: {region_key: {risk_level, risk_score, peak_fhr, label, key_factors}}
```

```bash
# Via HTTP (once exposed as endpoint)
curl "http://localhost:5565/api/v1/data?start_lat=40.5&start_lon=-106.0&end_lat=38.5&end_lon=-104.0&product=rh&fhr=12"
```

### Workflow: Localized Forecast

Deep analysis centered on a specific location.

```python
from tools.agent_tools.forecast import ForecastGenerator

gen = ForecastGenerator()
result = gen.localized_forecast(lat=39.74, lon=-104.99, radius_deg=2.0)
# Auto-generates 4 cardinal transects around Denver
# Produces cross-section figures + risk assessment + PDF
```

### Workflow: Case Study

Analyze a historical weather event with curated transects.

```python
from tools.agent_tools.case_study import CaseStudy

# From curated event (auto-loads suggested transects)
cs = CaseStudy.from_event("20250107_00z", "output/la_fires")
results = cs.analyze_all(fhrs=[0, 6, 12, 18, 24])
summary = cs.generate_summary()

# Export figures + data
manifest = cs.get_figure_manifest()
cs.export_data("json")
```

### Workflow: Agent Swarm

For comprehensive reports, launch multiple parallel agents that each handle a piece of the analysis, then compile.

**Pattern:**

```
Agent 1: National scan + SPC/NWS data → sections/01_national.tex
Agent 2: Region A deep analysis → sections/02_region_a.tex + figures/
Agent 3: Region B deep analysis → sections/03_region_b.tex + figures/
Agent 4: City-level ranking → sections/04_rankings.tex
Agent 5: Compiler → main.tex → main.pdf (waits for Agents 1-4)
```

Each agent independently:
1. Calls MCP tools or Python API to generate cross-sections and pull data
2. Writes LaTeX section files and saves figures
3. The compiler agent assembles `\input{sections/...}` into main.tex and runs pdflatex

**Example output:** 77-page PDF, 185 cross-section figures, 46 Street View photos, 6 sections.

---

## Configuration

### Dashboard

```bash
# Start dashboard (Windows, via restart script)
python C:\Users\drew\hrrr-maps\restart_dashboard.py

# Manual start
python tools/unified_dashboard.py --port 5565 --models hrrr,gfs
```

### Environment Variables

| Variable | Description | Where Set |
|----------|-------------|-----------|
| `WXSECTION_API_BASE` | Dashboard URL | MCP config or shell |
| `GOOGLE_STREET_VIEW_KEY` | Street View API key | `.env` file (gitignored) |

### .env File

Located at `C:\Users\drew\hrrr-maps\.env` (gitignored). Loaded by MCP server at startup.

```
GOOGLE_STREET_VIEW_KEY=your-key-here
WXSECTION_API_BASE=http://localhost:5565
```

### Watchdog

Auto-restarts dashboard if it crashes. Checks health every 30 seconds.

```bash
python C:\Users\drew\hrrr-maps\watchdog_dashboard.py
```

Logs: `%TEMP%\wxsection_watchdog.log`

---

## HTTP API Reference

Full HTTP API documentation is in [API_GUIDE.md](API_GUIDE.md). All endpoints are public, no auth required, CORS enabled.

### Core Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/v1/cross-section` | Generate PNG cross-section |
| `GET /api/v1/cross-section/gif` | Generate animated GIF cross-section (multiple forecast hours) |
| `GET /api/v1/data` | Numerical cross-section data (JSON) |
| `GET /api/v1/events` | Browse 88 historical events |
| `GET /api/v1/events/<cycle_key>` | Single event details |
| `GET /api/v1/events/categories` | Event category summary |
| `GET /api/v1/capabilities` | Machine-readable parameter constraints |
| `GET /api/v1/tools` | Anthropic tool_use compatible schemas |
| `GET /api/v1/products` | Available visualization products |
| `GET /api/v1/cycles` | Available model cycles |
| `GET /api/v1/status` | Server health check |

### External Data Proxy Endpoints (Public)

| Endpoint | Description |
|----------|-------------|
| `GET /api/v1/spc/fire-outlook?day=1` | SPC Fire Weather Outlook GeoJSON (day 1 or 2) |
| `GET /api/v1/nws/alerts?state=CO` | Active NWS alerts (also supports `lat`, `lon`, `event` params) |
| `GET /api/v1/nws/discussion/BOU` | NWS Area Forecast Discussion text by office ID |
| `GET /api/v1/fire-risk?start_lat=...&end_lat=...` | Fire risk score along a transect (0-100) |
| `GET /api/v1/fire-risk/national?fhr=12` | National fire risk scan across 12 CONUS regions |

**Examples:**

```bash
# SPC fire outlook for today
curl "https://wxsection.com/api/v1/spc/fire-outlook"

# Red Flag Warnings in Colorado
curl "https://wxsection.com/api/v1/nws/alerts?state=CO&event=Red+Flag+Warning"

# NWS Area Forecast Discussion from Boulder office
curl "https://wxsection.com/api/v1/nws/discussion/BOU"

# Fire risk along Front Range transect
curl "https://wxsection.com/api/v1/fire-risk?start_lat=40.5&start_lon=-106.0&end_lat=38.5&end_lon=-104.0&fhr=12"

# National fire risk scan (all 12 regions)
curl "https://wxsection.com/api/v1/fire-risk/national?fhr=12"
```

---

## Products

20 atmospheric visualization products available across all access layers.

| Product | Name | Units | Use For |
|---------|------|-------|---------|
| `temperature` | Temperature | C | Inversions, frontal zones |
| `wind_speed` | Wind Speed | knots | Jet streams, wind maxima |
| `theta_e` | Equivalent Potential Temp | K | Instability, warm/cold advection |
| `rh` | Relative Humidity | % | Dry slots, moisture plumes |
| `omega` | Vertical Velocity | hPa/hr | Rising/sinking motion |
| `q` | Specific Humidity | g/kg | Moisture transport |
| `vorticity` | Absolute Vorticity | 10^-5 s^-1 | Cyclonic/anticyclonic rotation |
| `shear` | Wind Shear | 10^-3 s^-1 | Turbulence, jet cores |
| `lapse_rate` | Lapse Rate | C/km | Atmospheric stability |
| `cloud_total` | Cloud Condensate | g/kg | Cloud layers |
| `wetbulb` | Wet-Bulb Temperature | C | Rain/snow transition |
| `icing` | Icing Potential | g/kg | Aircraft icing hazard |
| `frontogenesis` | Frontogenesis | K/100km/3hr | Snow banding |
| `smoke` | PM2.5 Smoke | ug/m3 | Wildfire smoke plumes |
| `vpd` | Vapor Pressure Deficit | hPa | Fire weather, plant stress |
| `dewpoint_dep` | Dewpoint Depression | C | Dry layers |
| `moisture_transport` | Moisture Transport | g*m/kg/s | Atmospheric rivers |
| `pv` | Potential Vorticity | PVU | Tropopause dynamics |
| `fire_wx` | Fire Weather Composite | composite | VPD + wind + RH overlay |

---

## Models

| Model | Resolution | Domain | Update Frequency | Forecast Range |
|-------|-----------|--------|------------------|----------------|
| **HRRR** | 3 km | CONUS | Hourly | F00–F18 (F00–F48 for 00/06/12/18z) |
| **GFS** | 0.25 deg | Global | 4x/day | F00–F48 |
| **RRFS** | 3 km | CONUS | Hourly | F00–F18 |

All models: 40 pressure levels, 1000 hPa to 50 hPa.
