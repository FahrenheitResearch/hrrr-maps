#!/usr/bin/env python3
"""
Interactive Cross-Section Web Server

A Flask-based web UI for generating cross-sections interactively.
Drag markers on the map to define start/end points, select style and
forecast hour, and see the cross-section update in real-time.

Usage:
    python tools/interactive_xsect_server.py --load-run outputs/hrrr/20251224/19z
    python tools/interactive_xsect_server.py --load-latest
    python tools/interactive_xsect_server.py --load-grib path/to/file.grib2
"""

import argparse
import base64
import logging
import sys
from pathlib import Path
from flask import Flask, render_template_string, jsonify, request

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.cross_section_interactive import InteractiveCrossSection

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
ixs = None  # Global InteractiveCrossSection instance

# Available styles
STYLES = [
    ('wind_speed', 'Wind Speed'),
    ('temp', 'Temperature'),
    ('theta_e', 'Theta-E'),
    ('rh', 'Relative Humidity'),
    ('omega', 'Vertical Velocity'),
    ('q', 'Specific Humidity'),
    ('cloud_total', 'Total Cloud'),
    ('icing', 'Icing Potential'),
    ('shear', 'Wind Shear'),
    ('wetbulb', 'Wet Bulb Temp'),
    ('lapse_rate', 'Lapse Rate'),
]

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Interactive Cross-Section</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }
        .container { display: flex; height: 100vh; }

        /* Left panel - map */
        .map-panel { flex: 1; display: flex; flex-direction: column; }
        #map { flex: 1; }

        /* Right panel - cross-section */
        .xsect-panel {
            width: 55%;
            background: #1a1a2e;
            display: flex;
            flex-direction: column;
            border-left: 2px solid #333;
        }

        /* Controls bar */
        .controls {
            background: #16213e;
            padding: 12px 16px;
            display: flex;
            gap: 16px;
            align-items: center;
            flex-wrap: wrap;
        }
        .control-group {
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .control-group label {
            color: #8892b0;
            font-size: 13px;
            font-weight: 500;
        }
        select, button {
            padding: 8px 12px;
            border-radius: 4px;
            border: 1px solid #333;
            background: #0f0f23;
            color: #ccd6f6;
            font-size: 14px;
            cursor: pointer;
        }
        select:hover, button:hover { border-color: #64ffda; }
        button { background: #1d4ed8; border-color: #1d4ed8; }
        button:hover { background: #2563eb; }

        /* Cross-section image */
        .xsect-container {
            flex: 1;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 16px;
            overflow: auto;
        }
        #xsect-img {
            max-width: 100%;
            max-height: 100%;
            border-radius: 8px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.5);
        }
        .loading {
            color: #64ffda;
            font-size: 18px;
        }
        .error {
            color: #ff6b6b;
            padding: 20px;
            text-align: center;
        }

        /* Info bar */
        .info-bar {
            background: #0f0f23;
            padding: 8px 16px;
            color: #8892b0;
            font-size: 12px;
            display: flex;
            justify-content: space-between;
        }
        .info-bar .coords { font-family: monospace; }
        .info-bar .timing { color: #64ffda; }

        /* Predefined paths dropdown */
        .preset-paths {
            margin-left: auto;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="map-panel">
            <div id="map"></div>
        </div>
        <div class="xsect-panel">
            <div class="controls">
                <div class="control-group">
                    <label>Style:</label>
                    <select id="style-select">
                        {% for value, label in styles %}
                        <option value="{{ value }}" {% if value == 'wind_speed' %}selected{% endif %}>{{ label }}</option>
                        {% endfor %}
                    </select>
                </div>
                <div class="control-group">
                    <label>Hour:</label>
                    <select id="hour-select">
                        {% for hour in hours %}
                        <option value="{{ hour }}">F{{ '%02d'|format(hour) }}</option>
                        {% endfor %}
                    </select>
                </div>
                <div class="control-group">
                    <label>Points:</label>
                    <select id="points-select">
                        <option value="60">60</option>
                        <option value="80" selected>80</option>
                        <option value="100">100</option>
                        <option value="120">120</option>
                    </select>
                </div>
                <div class="control-group preset-paths">
                    <label>Presets:</label>
                    <select id="preset-select">
                        <option value="">-- Select Path --</option>
                        <option value="39.74,-104.99,41.88,-87.63">Denver → Chicago</option>
                        <option value="34.05,-118.24,33.45,-112.07">LA → Phoenix</option>
                        <option value="32.78,-96.80,35.47,-97.52">Dallas → OKC</option>
                        <option value="40.71,-74.01,42.36,-71.06">NYC → Boston</option>
                        <option value="47.61,-122.33,45.52,-122.68">Seattle → Portland</option>
                        <option value="25.76,-80.19,30.33,-81.66">Miami → Jacksonville</option>
                    </select>
                </div>
            </div>
            <div class="xsect-container">
                <div id="xsect-content" class="loading">Drag markers on the map to generate a cross-section</div>
            </div>
            <div class="info-bar">
                <span class="coords" id="coords-display">Start: -- | End: --</span>
                <span class="timing" id="timing-display"></span>
            </div>
        </div>
    </div>

    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script>
        // Initialize map centered on CONUS
        const map = L.map('map').setView([39.5, -98.5], 4);

        // Add tile layer
        L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
            attribution: '&copy; OpenStreetMap, &copy; CARTO',
            maxZoom: 19
        }).addTo(map);

        // Custom marker icons
        const startIcon = L.divIcon({
            className: 'custom-marker',
            html: '<div style="background:#22c55e; width:16px; height:16px; border-radius:50%; border:3px solid white; box-shadow:0 2px 5px rgba(0,0,0,0.5);"></div>',
            iconSize: [22, 22],
            iconAnchor: [11, 11]
        });

        const endIcon = L.divIcon({
            className: 'custom-marker',
            html: '<div style="background:#ef4444; width:16px; height:16px; border-radius:50%; border:3px solid white; box-shadow:0 2px 5px rgba(0,0,0,0.5);"></div>',
            iconSize: [22, 22],
            iconAnchor: [11, 11]
        });

        // Create draggable markers
        let startMarker = L.marker([39.74, -104.99], {draggable: true, icon: startIcon}).addTo(map);
        let endMarker = L.marker([41.88, -87.63], {draggable: true, icon: endIcon}).addTo(map);

        // Line connecting markers
        let pathLine = L.polyline([startMarker.getLatLng(), endMarker.getLatLng()], {
            color: '#64ffda',
            weight: 3,
            opacity: 0.8,
            dashArray: '10, 10'
        }).addTo(map);

        // Update line when markers move
        function updateLine() {
            pathLine.setLatLngs([startMarker.getLatLng(), endMarker.getLatLng()]);
        }

        startMarker.on('drag', updateLine);
        endMarker.on('drag', updateLine);

        // Debounce function
        let debounceTimer;
        function debounce(func, delay) {
            return function(...args) {
                clearTimeout(debounceTimer);
                debounceTimer = setTimeout(() => func.apply(this, args), delay);
            };
        }

        // Generate cross-section
        async function generateXsect() {
            const startPos = startMarker.getLatLng();
            const endPos = endMarker.getLatLng();
            const style = document.getElementById('style-select').value;
            const hour = document.getElementById('hour-select').value;
            const nPoints = document.getElementById('points-select').value;

            // Update coords display
            document.getElementById('coords-display').textContent =
                `Start: ${startPos.lat.toFixed(2)}, ${startPos.lng.toFixed(2)} | End: ${endPos.lat.toFixed(2)}, ${endPos.lng.toFixed(2)}`;

            // Show loading
            document.getElementById('xsect-content').innerHTML = '<div class="loading">Generating...</div>';
            document.getElementById('timing-display').textContent = '';

            const startTime = performance.now();

            try {
                const response = await fetch('/api/xsect', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        start_lat: startPos.lat,
                        start_lon: startPos.lng,
                        end_lat: endPos.lat,
                        end_lon: endPos.lng,
                        style: style,
                        forecast_hour: parseInt(hour),
                        n_points: parseInt(nPoints)
                    })
                });

                const data = await response.json();
                const elapsed = ((performance.now() - startTime) / 1000).toFixed(2);

                if (data.success) {
                    document.getElementById('xsect-content').innerHTML =
                        `<img id="xsect-img" src="data:image/png;base64,${data.image}" alt="Cross-section">`;
                    document.getElementById('timing-display').textContent = `Generated in ${elapsed}s`;
                } else {
                    document.getElementById('xsect-content').innerHTML =
                        `<div class="error">Error: ${data.error}</div>`;
                }
            } catch (err) {
                document.getElementById('xsect-content').innerHTML =
                    `<div class="error">Request failed: ${err.message}</div>`;
            }
        }

        // Debounced version for drag events
        const debouncedGenerate = debounce(generateXsect, 300);

        // Attach event listeners
        startMarker.on('dragend', debouncedGenerate);
        endMarker.on('dragend', debouncedGenerate);
        document.getElementById('style-select').addEventListener('change', generateXsect);
        document.getElementById('hour-select').addEventListener('change', generateXsect);
        document.getElementById('points-select').addEventListener('change', generateXsect);

        // Preset paths
        document.getElementById('preset-select').addEventListener('change', function() {
            if (!this.value) return;
            const [startLat, startLon, endLat, endLon] = this.value.split(',').map(parseFloat);
            startMarker.setLatLng([startLat, startLon]);
            endMarker.setLatLng([endLat, endLon]);
            updateLine();

            // Fit map to show both markers
            const bounds = L.latLngBounds([startMarker.getLatLng(), endMarker.getLatLng()]);
            map.fitBounds(bounds, {padding: [50, 50]});

            generateXsect();
        });

        // Generate initial cross-section on load
        setTimeout(generateXsect, 500);
    </script>
</body>
</html>
"""


@app.route('/')
def index():
    """Serve the main interactive UI."""
    hours = sorted(ixs.get_loaded_hours()) if ixs else [0]
    return render_template_string(HTML_TEMPLATE, styles=STYLES, hours=hours)


@app.route('/api/xsect', methods=['POST'])
def generate_xsect():
    """Generate a cross-section and return as base64 image."""
    if ixs is None:
        return jsonify({'success': False, 'error': 'No data loaded'})

    try:
        data = request.json
        start_point = (data['start_lat'], data['start_lon'])
        end_point = (data['end_lat'], data['end_lon'])
        style = data.get('style', 'wind_speed')
        forecast_hour = data.get('forecast_hour', 0)
        n_points = data.get('n_points', 80)

        # Generate cross-section
        img_bytes = ixs.get_cross_section(
            start_point=start_point,
            end_point=end_point,
            style=style,
            forecast_hour=forecast_hour,
            n_points=n_points,
        )

        if img_bytes is None:
            return jsonify({'success': False, 'error': 'Failed to generate cross-section'})

        # Encode to base64
        img_b64 = base64.b64encode(img_bytes).decode('utf-8')

        return jsonify({'success': True, 'image': img_b64})

    except Exception as e:
        logger.exception("Error generating cross-section")
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/info')
def get_info():
    """Get info about loaded data."""
    if ixs is None:
        return jsonify({'loaded': False})

    return jsonify({
        'loaded': True,
        'hours': sorted(ixs.get_loaded_hours()),
        'memory_mb': ixs.get_memory_usage(),
    })


def main():
    global ixs

    parser = argparse.ArgumentParser(description="Interactive Cross-Section Web Server")
    parser.add_argument("--load-run", type=str, help="Load from run directory (e.g., outputs/hrrr/20251224/19z)")
    parser.add_argument("--load-latest", action="store_true", help="Load latest available run")
    parser.add_argument("--load-grib", type=str, help="Load single GRIB file")
    parser.add_argument("--max-hours", type=int, default=18, help="Max forecast hours to load")
    parser.add_argument("--workers", "-w", type=int, default=1, help="Parallel workers for loading (default: 1)")
    parser.add_argument("--cache", type=str, default="cache/zarr", help="Zarr cache directory (default: cache/zarr)")
    parser.add_argument("--no-cache", action="store_true", help="Disable Zarr caching")
    parser.add_argument("--port", type=int, default=5000, help="Port to run server on")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host to bind to")

    args = parser.parse_args()

    # Initialize InteractiveCrossSection with optional caching
    cache_dir = None if args.no_cache else args.cache
    ixs = InteractiveCrossSection(cache_dir=cache_dir)
    if cache_dir:
        logger.info(f"Zarr cache enabled: {cache_dir}")

    if args.load_run:
        logger.info(f"Loading run from {args.load_run} with {args.workers} workers...")
        ixs.load_run(args.load_run, max_hours=args.max_hours, workers=args.workers)
    elif args.load_latest:
        # Find latest run directory
        outputs_dir = Path("outputs/hrrr")
        if outputs_dir.exists():
            date_dirs = sorted(outputs_dir.iterdir(), reverse=True)
            for date_dir in date_dirs:
                hour_dirs = sorted(date_dir.iterdir(), reverse=True)
                for hour_dir in hour_dirs:
                    if list(hour_dir.glob("F*/hrrr*.grib2")):
                        logger.info(f"Loading latest run: {hour_dir} with {args.workers} workers...")
                        ixs.load_run(str(hour_dir), max_hours=args.max_hours, workers=args.workers)
                        break
                else:
                    continue
                break
    elif args.load_grib:
        logger.info(f"Loading GRIB file: {args.load_grib}")
        ixs.load_forecast_hour(args.load_grib, forecast_hour=0)
    else:
        logger.warning("No data source specified. Use --load-run, --load-latest, or --load-grib")
        logger.info("Server will start but cross-sections won't work until data is loaded.")

    loaded_hours = ixs.get_loaded_hours()
    if loaded_hours:
        logger.info(f"Loaded {len(loaded_hours)} forecast hours ({ixs.get_memory_usage():.0f} MB)")
        logger.info(f"Hours: {sorted(loaded_hours)}")

    logger.info(f"\n{'='*60}")
    logger.info(f"Interactive Cross-Section Server")
    logger.info(f"Open in browser: http://{args.host}:{args.port}")
    logger.info(f"{'='*60}\n")

    app.run(host=args.host, port=args.port, debug=False, threaded=True)


if __name__ == "__main__":
    main()
