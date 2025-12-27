#!/usr/bin/env python3
"""
HRRR Cross-Section Dashboard

Interactive cross-section visualization on a Leaflet map.
Draw a line on the map to generate vertical cross-sections.

Usage:
    python tools/unified_dashboard.py --data-dir outputs/hrrr/20251227/09z
    python tools/unified_dashboard.py --auto-update
"""

import argparse
import json
import logging
import sys
import time
import io
import threading
from pathlib import Path
from datetime import datetime
from functools import wraps
from collections import defaultdict

from flask import Flask, jsonify, request, send_file, abort

sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

# =============================================================================
# CONFIGURATION
# =============================================================================

CONUS_BOUNDS = {
    'south': 21.14, 'north': 52.62,
    'west': -134.10, 'east': -60.92,
}

XSECT_STYLES = [
    ('wind_speed', 'Wind Speed'),
    ('temp', 'Temperature'),
    ('theta_e', 'Theta-E'),
    ('rh', 'Relative Humidity'),
    ('omega', 'Vertical Velocity'),
    ('vorticity', 'Vorticity'),
    ('cloud', 'Cloud Water'),
]

# =============================================================================
# RATE LIMITING
# =============================================================================

class RateLimiter:
    def __init__(self, rpm=60, burst=10):
        self.rpm, self.burst = rpm, burst
        self.requests = defaultdict(list)
        self.lock = threading.Lock()

    def is_allowed(self, ip):
        now = time.time()
        with self.lock:
            self.requests[ip] = [t for t in self.requests[ip] if t > now - 60]
            if len(self.requests[ip]) >= self.rpm:
                return False
            if len([t for t in self.requests[ip] if t > now - 1]) >= self.burst:
                return False
            self.requests[ip].append(now)
            return True

rate_limiter = RateLimiter()

def rate_limit(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if app.config.get('PRODUCTION'):
            if not rate_limiter.is_allowed(request.remote_addr):
                return jsonify({'error': 'Rate limit exceeded'}), 429
        return f(*args, **kwargs)
    return decorated

# =============================================================================
# DATA MANAGER
# =============================================================================

class CrossSectionManager:
    """Manages cross-section data and generation."""

    def __init__(self):
        self.xsect = None
        self.data_dir = None
        self.available_hours = []
        self.cycle_info = {}

    def load_run(self, data_dir: str, max_hours: int = 6):
        """Load HRRR run data for cross-sections."""
        from core.cross_section_interactive import InteractiveCrossSection

        self.data_dir = Path(data_dir).resolve()
        logger.info(f"Loading data from {self.data_dir}...")

        # Parse cycle info from path
        parts = str(self.data_dir).split('/')
        for i, p in enumerate(parts):
            if p in ['hrrr', 'rrfs']:
                if i + 2 < len(parts):
                    self.cycle_info = {
                        'model': p,
                        'date': parts[i + 1],
                        'hour': parts[i + 2].replace('z', ''),
                    }
                break

        # Find available forecast hours
        self.available_hours = sorted([
            int(d.name[1:]) for d in self.data_dir.iterdir()
            if d.is_dir() and d.name.startswith('F') and d.name[1:].isdigit()
        ])

        # Load cross-section engine
        self.xsect = InteractiveCrossSection(cache_dir='cache/dashboard/xsect')
        loaded = self.xsect.load_run(str(self.data_dir), max_hours=max_hours)

        logger.info(f"Loaded {loaded} hours for cross-sections")
        logger.info(f"Available hours: {self.available_hours}")

        return loaded

    def generate_cross_section(self, start, end, hour, style):
        """Generate a cross-section image."""
        if not self.xsect:
            return None

        try:
            # get_cross_section returns PNG bytes directly
            png_bytes = self.xsect.get_cross_section(
                start_point=start,
                end_point=end,
                forecast_hour=hour,
                style=style,
                return_image=True,
                dpi=100
            )
            if png_bytes is None:
                return None

            return io.BytesIO(png_bytes)
        except Exception as e:
            logger.error(f"Cross-section error: {e}")
            return None

data_manager = CrossSectionManager()

# =============================================================================
# HTML TEMPLATE
# =============================================================================

HTML_TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>HRRR Cross-Section Dashboard</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        :root {
            --bg: #0f172a;
            --panel: #1e293b;
            --card: #334155;
            --text: #f1f5f9;
            --muted: #94a3b8;
            --accent: #38bdf8;
            --border: #475569;
        }
        body {
            font-family: system-ui, sans-serif;
            background: var(--bg);
            color: var(--text);
            height: 100vh;
            display: flex;
        }
        #map-container {
            flex: 1;
            display: flex;
            flex-direction: column;
        }
        #map { flex: 1; }
        #controls {
            background: var(--panel);
            padding: 12px;
            display: flex;
            gap: 16px;
            align-items: center;
            border-bottom: 1px solid var(--border);
        }
        .control-group { display: flex; align-items: center; gap: 8px; }
        label { color: var(--muted); font-size: 13px; }
        select, button {
            background: var(--card);
            color: var(--text);
            border: 1px solid var(--border);
            padding: 6px 12px;
            border-radius: 4px;
            cursor: pointer;
        }
        button:hover { background: var(--accent); color: #000; }
        #cycle-info {
            margin-left: auto;
            color: var(--muted);
            font-size: 13px;
        }
        #sidebar {
            width: 450px;
            background: var(--panel);
            border-left: 1px solid var(--border);
            display: flex;
            flex-direction: column;
        }
        #xsect-header {
            padding: 12px;
            border-bottom: 1px solid var(--border);
            font-weight: 600;
        }
        #xsect-container {
            flex: 1;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 12px;
            overflow: hidden;
        }
        #xsect-img {
            max-width: 100%;
            max-height: 100%;
            border-radius: 4px;
        }
        #instructions {
            color: var(--muted);
            text-align: center;
            padding: 20px;
        }
        .loading {
            color: var(--accent);
            animation: pulse 1.5s infinite;
        }
        @keyframes pulse { 50% { opacity: 0.5; } }
    </style>
</head>
<body>
    <div id="map-container">
        <div id="controls">
            <div class="control-group">
                <label>Hour:</label>
                <select id="hour-select"></select>
            </div>
            <div class="control-group">
                <label>Style:</label>
                <select id="style-select"></select>
            </div>
            <button id="clear-btn">Clear Line</button>
            <div id="cycle-info"></div>
        </div>
        <div id="map"></div>
    </div>
    <div id="sidebar">
        <div id="xsect-header">Cross-Section</div>
        <div id="xsect-container">
            <div id="instructions">
                Click two points on the map to draw a cross-section line
            </div>
        </div>
    </div>

    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script>
        const bounds = ''' + json.dumps(CONUS_BOUNDS) + ''';
        const styles = ''' + json.dumps(XSECT_STYLES) + ''';

        // Initialize map
        const map = L.map('map', {
            center: [39, -98],
            zoom: 5,
            minZoom: 4,
            maxZoom: 10
        });

        L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
            attribution: '&copy; OpenStreetMap, &copy; CARTO'
        }).addTo(map);

        // State
        let startMarker = null, endMarker = null, line = null;
        let availableHours = [];

        // Populate style selector
        const styleSelect = document.getElementById('style-select');
        styles.forEach(([val, label]) => {
            const opt = document.createElement('option');
            opt.value = val;
            opt.textContent = label;
            styleSelect.appendChild(opt);
        });

        // Load initial data
        fetch('/api/info')
            .then(r => r.json())
            .then(data => {
                availableHours = data.hours || [];
                const hourSelect = document.getElementById('hour-select');
                availableHours.forEach(h => {
                    const opt = document.createElement('option');
                    opt.value = h;
                    opt.textContent = 'F' + String(h).padStart(2, '0');
                    hourSelect.appendChild(opt);
                });

                if (data.cycle) {
                    document.getElementById('cycle-info').textContent =
                        `${data.cycle.model.toUpperCase()} ${data.cycle.date} ${data.cycle.hour}Z`;
                }
            });

        // Map click handler
        map.on('click', e => {
            const {lat, lng} = e.latlng;

            if (!startMarker) {
                startMarker = L.circleMarker([lat, lng], {
                    radius: 8, color: '#38bdf8', fillOpacity: 0.8
                }).addTo(map);
            } else if (!endMarker) {
                endMarker = L.circleMarker([lat, lng], {
                    radius: 8, color: '#f87171', fillOpacity: 0.8
                }).addTo(map);

                line = L.polyline([startMarker.getLatLng(), endMarker.getLatLng()], {
                    color: '#fbbf24', weight: 3, dashArray: '10, 5'
                }).addTo(map);

                generateCrossSection();
            }
        });

        // Generate cross-section
        function generateCrossSection() {
            if (!startMarker || !endMarker) return;

            const container = document.getElementById('xsect-container');
            container.innerHTML = '<div class="loading">Generating cross-section...</div>';

            const start = startMarker.getLatLng();
            const end = endMarker.getLatLng();
            const hour = document.getElementById('hour-select').value;
            const style = document.getElementById('style-select').value;

            const url = `/api/xsect?start_lat=${start.lat}&start_lon=${start.lng}` +
                `&end_lat=${end.lat}&end_lon=${end.lng}&hour=${hour}&style=${style}`;

            fetch(url)
                .then(r => {
                    if (!r.ok) throw new Error('Failed to generate');
                    return r.blob();
                })
                .then(blob => {
                    const img = document.createElement('img');
                    img.id = 'xsect-img';
                    img.src = URL.createObjectURL(blob);
                    container.innerHTML = '';
                    container.appendChild(img);
                })
                .catch(err => {
                    container.innerHTML = `<div style="color:#f87171">${err.message}</div>`;
                });
        }

        // Clear button
        document.getElementById('clear-btn').onclick = () => {
            if (startMarker) { map.removeLayer(startMarker); startMarker = null; }
            if (endMarker) { map.removeLayer(endMarker); endMarker = null; }
            if (line) { map.removeLayer(line); line = null; }
            document.getElementById('xsect-container').innerHTML =
                '<div id="instructions">Click two points on the map to draw a cross-section line</div>';
        };

        // Regenerate on option change
        document.getElementById('hour-select').onchange = generateCrossSection;
        document.getElementById('style-select').onchange = generateCrossSection;
    </script>
</body>
</html>'''

# =============================================================================
# ROUTES
# =============================================================================

@app.route('/')
def index():
    return HTML_TEMPLATE

@app.route('/api/info')
def api_info():
    return jsonify({
        'hours': data_manager.available_hours,
        'cycle': data_manager.cycle_info,
        'styles': XSECT_STYLES,
    })

@app.route('/api/xsect')
@rate_limit
def api_xsect():
    try:
        start = (float(request.args['start_lat']), float(request.args['start_lon']))
        end = (float(request.args['end_lat']), float(request.args['end_lon']))
        hour = int(request.args.get('hour', 0))
        style = request.args.get('style', 'wind_speed')
    except (KeyError, ValueError) as e:
        return jsonify({'error': f'Invalid parameters: {e}'}), 400

    buf = data_manager.generate_cross_section(start, end, hour, style)
    if buf is None:
        return jsonify({'error': 'Failed to generate cross-section'}), 500

    return send_file(buf, mimetype='image/png')

# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description='HRRR Cross-Section Dashboard')
    parser.add_argument('--data-dir', type=str, help='Path to HRRR run data')
    parser.add_argument('--auto-update', action='store_true', help='Auto-download latest')
    parser.add_argument('--max-hours', type=int, default=6, help='Hours to load for xsect')
    parser.add_argument('--port', type=int, default=5000, help='Server port')
    parser.add_argument('--host', type=str, default='0.0.0.0', help='Server host')
    parser.add_argument('--production', action='store_true', help='Enable rate limiting')

    args = parser.parse_args()
    app.config['PRODUCTION'] = args.production

    if args.auto_update:
        from smart_hrrr.orchestrator import download_latest_cycle
        from smart_hrrr.io import create_output_structure

        date_str, hour, results = download_latest_cycle(max_hours=args.max_hours)
        if date_str:
            output_dirs = create_output_structure('hrrr', date_str, hour)
            args.data_dir = str(output_dirs['run'])
        else:
            logger.error("Failed to download data")
            sys.exit(1)

    if not args.data_dir:
        parser.error("Must specify --data-dir or --auto-update")

    data_manager.load_run(args.data_dir, max_hours=args.max_hours)

    logger.info("=" * 60)
    logger.info("HRRR Cross-Section Dashboard")
    logger.info(f"Open: http://{args.host}:{args.port}")
    logger.info("=" * 60)

    app.run(host=args.host, port=args.port, threaded=True)

if __name__ == '__main__':
    main()
