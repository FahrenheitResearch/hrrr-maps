# HRRR Cross-Section Generator

Interactive vertical atmospheric cross-section visualization from HRRR (High-Resolution Rapid Refresh) weather model data. Draw a line on a map, get an instant cross-section showing the vertical structure of the atmosphere.

**Live demo:** Deployed via Cloudflare Tunnel (URL changes on restart)

## What It Does

Cross-sections slice through the atmosphere along a path between two geographic points, revealing:
- Jet streams and wind maxima
- Temperature inversions and frontal boundaries
- Moisture transport and dry air intrusions
- Rising/sinking motion (omega)
- Snow banding potential (frontogenesis)
- Icing hazards for aviation

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Start the auto-update daemon (downloads latest HRRR data continuously)
python tools/auto_update.py --interval 2 --max-hours 18 &

# Run the dashboard
python tools/unified_dashboard.py --port 5559

# Expose publicly (optional)
cloudflared tunnel --url http://localhost:5559
```

## Features

### Interactive Web Dashboard
- **Leaflet map** with click-to-place markers and draggable endpoints
- **14 visualization styles** via dropdown with community voting
- **19 forecast hours** (F00-F18) shown as selectable chips
- **Model run picker** grouped by date with `<optgroup>`, shows load status and FHR count
- **Height/pressure toggle** - view Y-axis as hPa or km
- **Vertical scaling** - 1x, 1.5x, 2x exaggeration
- **Vertical range selector** - full atmosphere (100 hPa), mid (300), low (500), boundary layer (700)
- **Community favorites** - save/load cross-section configs by name, auto-expire after 12h
- **Feature request system** - users can submit and vote on feature ideas

### Continuous Auto-Updating
- **Progressive download daemon** (`auto_update.py`) checks every 2 minutes
- Maintains latest 2 init cycles with F00-F18 (full forecast set)
- Client-side auto-refresh polls every 60s for newly available data
- Background server rescan detects new downloads without restart
- **Parallel loading** with 4 worker threads for faster data loading

### Memory Management
- **117 GB RAM hard cap** with LRU eviction starting at 115 GB
- **Latest 2 cycles pre-loaded** in background at startup for instant access
- Unique engine key mapping allows multiple init cycles loaded simultaneously

### Disk Storage (500 GB)
- **Space-based eviction** instead of age-based - popular data persists
- **Popularity tracking** via `data/disk_meta.json` (last accessed time + access count)
- Protected cycles: latest 2 auto-update targets + anything accessed in last 2 hours
- Disk usage checked every 10 minutes, evicts least-recently-accessed first
- User-requested dates stay on disk as long as there's space

### Custom Date Requests
- **Request button** lets users download F00-F18 for any date/init cycle
- Downloads from NOMADS (recent) or AWS archive (older data)
- Progress polling shows download status in real-time

### Performance
- **Sub-second generation** after data is loaded (~0.3s typical)
- **NPZ caching** - first GRIB load ~25s, subsequent loads ~2s from cache
- **Parallel GRIB download** with configurable thread count
- Non-blocking startup - Flask serves immediately while data loads in background

### Production Ready
- Rate limiting (60 req/min) for public deployment
- REST API for programmatic access
- Cloudflare Tunnel integration for public access
- Batch generation for animations

## Visualization Styles

### Core Meteorology
| Style | Shows | Use For |
|-------|-------|---------|
| `wind_speed` | Horizontal wind (kt) | Jet streams, wind maxima |
| `temp` | Temperature (°C) with NWS NDFD colormap | Inversions, frontal zones |
| `theta_e` | Equivalent potential temp (K) | Warm/cold advection, instability |
| `omega` | Vertical velocity | Rising (blue) / sinking (red) motion |
| `vorticity` | Absolute vorticity | Cyclonic/anticyclonic patterns |

### Moisture & Clouds
| Style | Shows | Use For |
|-------|-------|---------|
| `rh` | Relative humidity (%) | Dry slots, moisture plumes |
| `q` | Specific humidity (g/kg) | Moisture transport |
| `cloud` | Cloud water (g/kg) | Cloud layers |
| `cloud_total` | All hydrometeors | Full precipitation picture |

### Winter Weather & Aviation
| Style | Shows | Use For |
|-------|-------|---------|
| `frontogenesis` | Petterssen frontogenesis | **Snow banding potential** |
| `wetbulb` | Wet-bulb temperature (°C) | Rain/snow transition |
| `icing` | Supercooled liquid water | Aircraft icing hazard |
| `shear` | Wind shear (1/s) | Turbulence, jet cores |
| `lapse_rate` | Temp lapse rate (°C/km) | Stability analysis |

### All Styles Include
- **Theta contours** (black lines) - atmospheric stability
- **Wind barbs** with actual U and V components
- **Freezing level** (magenta line) - 0°C isotherm
- **Terrain fill** (brown) - contourf fills entire grid, terrain covers underground (standard met practice)

### Temperature Colormap
Uses the NWS NDFD color table with 0°C (freezing) = yellow:
- Purple (-60°C) → Blue (-30°C) → Cyan (-10°C) → **Yellow (0°C)** → Orange (20°C) → Red (40°C)

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Dashboard UI |
| `/api/cycles` | GET | List available cycles (grouped by date) |
| `/api/status` | GET | Memory/load status |
| `/api/load` | POST | Load specific cycle + forecast hour |
| `/api/load_cycle` | POST | Load entire cycle (all FHRs) |
| `/api/unload` | POST | Unload a forecast hour |
| `/api/xsect` | GET | Generate cross-section PNG |
| `/api/request_cycle` | POST | Request download of a specific date/init |
| `/api/favorites` | GET | List community favorites |
| `/api/favorite` | POST | Save a favorite |
| `/api/favorite/<id>` | DELETE | Delete a favorite |
| `/api/votes` | GET | Style vote counts |
| `/api/vote` | POST | Vote for a style |

### Generate Cross-Section via API

```
GET /api/xsect?start_lat=40.0&start_lon=-100.0&end_lat=35.0&end_lon=-90.0&style=frontogenesis&cycle=20260204_04z&fhr=6&y_axis=pressure&vscale=1.5&y_top=300
```

## Architecture

```
tools/
├── unified_dashboard.py      # Flask server + Leaflet UI + data management
│   ├── CrossSectionManager   # Handles loading, eviction, engine key mapping
│   ├── Memory management     # 117GB cap, LRU eviction at 115GB
│   ├── Disk management       # 500GB cap, popularity-based eviction
│   ├── Community favorites   # Save/load/delete with 12h expiry
│   └── Thread-safe parallel loading
│
└── auto_update.py            # Continuous download daemon
    ├── Progressive download  # Latest 2 cycles, F00-F18
    └── Space-based cleanup   # Evicts least-popular when disk full

core/
├── cross_section_interactive.py  # Fast interactive engine
│   ├── Pre-loads 3D fields into RAM
│   ├── NPZ caching layer
│   ├── <1s cross-section generation
│   ├── Progress callback for field-level tracking
│   └── NWS NDFD temperature colormap
│
└── cross_section_production.py   # Batch processing

data/
├── favorites.json            # Community favorites
├── votes.json                # Style votes
├── requests.json             # Feature requests
└── disk_meta.json            # Disk usage tracking (access times, counts)
```

## Memory Usage

| Loaded | RAM Usage |
|--------|-----------|
| 1 forecast hour | ~700 MB |
| 1 full cycle (F00-F18) | ~13 GB |
| 2 full cycles (preloaded) | ~26 GB |
| Max before eviction | 115 GB |
| Hard cap | 117 GB |

The dashboard uses LRU eviction - when memory hits 115 GB, the oldest loaded items are evicted first.

## Command Line Options

### Dashboard
```
python tools/unified_dashboard.py [OPTIONS]

--port PORT          Server port (default: 5559)
--host HOST          Server host (default: 0.0.0.0)
--preload N          Cycles to pre-load at startup (default: 0)
--n-cycles N         Max cycles to scan for (default: 30)
--production         Enable rate limiting
--auto-update        Download latest data before starting
--max-hours N        Max forecast hour to download
```

### Auto-Update Daemon
```
python tools/auto_update.py [OPTIONS]

--interval N         Check interval in minutes (default: 2)
--max-hours N        Max forecast hour (default: 18)
--once               Run once and exit
--no-cleanup         Don't clean up old data
```

## Data Requirements

HRRR GRIB2 files with pressure-level data:

```
outputs/hrrr/{YYYYMMDD}/{HH}z/F{XX}/
├── hrrr.t{HH}z.wrfprsf{XX}.grib2  # Pressure levels (required)
└── hrrr.t{HH}z.wrfsfcf{XX}.grib2  # Surface (for terrain)
```

Required fields: Temperature, U/V wind, RH, geopotential height, specific humidity, vorticity, cloud water, dew point on isobaric levels. Surface pressure from surface file for terrain.

Data is automatically downloaded from NOAA NOMADS (recent, <48h) or AWS archive (older) by the auto-update daemon or on-demand via the request button.

## Dependencies

```
numpy
scipy
matplotlib
cfgrib
eccodes
flask
imageio
Pillow
```

Install with: `pip install -r requirements.txt`

For public access: `cloudflared` (Cloudflare Tunnel client)

## References

- [HRRR Model](https://rapidrefresh.noaa.gov/hrrr/) - NOAA's 3km CONUS model
- [NWS NDFD Color Tables](https://www.weather.gov/media/mdl/ndfd/NDFDelem_fullres.pdf) - Temperature colormap reference
- [Petterssen Frontogenesis](https://glossary.ametsoc.org/wiki/Frontogenesis) - AMS Glossary
- [cfgrib](https://github.com/ecmwf/cfgrib) - GRIB file reader
