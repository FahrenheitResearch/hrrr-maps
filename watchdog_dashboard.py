"""
Watchdog for wxsection.com dashboard.

Checks health every 30 seconds. If the dashboard is down, restarts it
using restart_dashboard.py. Logs all events.

Usage:
    python watchdog_dashboard.py

Runs forever. Start it and forget it. Kill with Ctrl+C or taskkill.
"""
import subprocess
import sys
import time
import os
import json
from datetime import datetime
from urllib.request import urlopen, Request
from urllib.error import URLError

HEALTH_URL = "http://127.0.0.1:5565/api/v1/status"
CHECK_INTERVAL = 30  # seconds between health checks
RESTART_COOLDOWN = 60  # minimum seconds between restart attempts
RESTART_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "restart_dashboard.py")
PYTHON = os.path.join(os.environ.get("CONDA_PREFIX", ""), "python.exe")
if not os.path.exists(PYTHON):
    PYTHON = sys.executable
LOG_FILE = os.path.join(os.environ.get("TEMP", "/tmp"), "wxsection_watchdog.log")
PID_FILE = os.path.join(os.environ.get("TEMP", "/tmp"), "wxsection_watchdog.pid")


def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    try:
        with open(LOG_FILE, "a") as f:
            f.write(line + "\n")
    except Exception:
        pass


def is_healthy():
    """Check if dashboard responds to health check."""
    try:
        req = Request(HEALTH_URL, headers={"User-Agent": "wxsection-watchdog/1.0"})
        with urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            return True
    except Exception:
        return False


def restart():
    """Run restart_dashboard.py."""
    log("RESTARTING dashboard...")
    try:
        result = subprocess.run(
            [PYTHON, RESTART_SCRIPT],
            capture_output=True, text=True, timeout=120
        )
        log(f"Restart stdout: {result.stdout.strip()[-200:]}")
        if result.returncode != 0:
            log(f"Restart stderr: {result.stderr.strip()[-200:]}")
        return result.returncode == 0
    except Exception as e:
        log(f"Restart failed: {e}")
        return False


def check_single_instance():
    """Ensure only one watchdog is running. Kill stale ones."""
    if os.path.exists(PID_FILE):
        try:
            old_pid = int(open(PID_FILE).read().strip())
            if old_pid != os.getpid():
                # Check if old watchdog is still alive
                result = subprocess.run(
                    ["tasklist", "/FI", f"PID eq {old_pid}", "/FO", "CSV", "/NH"],
                    capture_output=True, text=True, timeout=10
                )
                if str(old_pid) in result.stdout:
                    print(f"Another watchdog is already running (PID {old_pid}). Exiting.")
                    sys.exit(1)
        except Exception:
            pass  # Stale PID file, safe to overwrite


def snapshot_dashboard_log():
    """Capture the last 50 lines of dashboard log at time of crash."""
    dash_log = os.path.join(os.environ.get("TEMP", "/tmp"), "wxsection_dashboard.log")
    if not os.path.exists(dash_log):
        return
    try:
        with open(dash_log, "r") as f:
            lines = f.readlines()
        tail = lines[-50:] if len(lines) > 50 else lines
        log("--- Dashboard log tail at crash ---")
        for line in tail:
            line = line.rstrip()
            if line:
                log(f"  | {line[:200]}")
        log("--- End dashboard log tail ---")
    except Exception as e:
        log(f"Could not read dashboard log: {e}")


def main():
    check_single_instance()

    # Write PID file
    with open(PID_FILE, "w") as f:
        f.write(str(os.getpid()))

    log(f"Watchdog started (PID {os.getpid()})")
    log(f"  Health URL: {HEALTH_URL}")
    log(f"  Check interval: {CHECK_INTERVAL}s")
    log(f"  Restart script: {RESTART_SCRIPT}")
    log(f"  Log file: {LOG_FILE}")

    last_restart = 0
    consecutive_failures = 0
    total_restarts = 0

    while True:
        try:
            healthy = is_healthy()

            if healthy:
                if consecutive_failures > 0:
                    log(f"Dashboard recovered after {consecutive_failures} failed checks")
                consecutive_failures = 0
            else:
                consecutive_failures += 1
                log(f"Health check FAILED (attempt {consecutive_failures})")

                # Restart after 2 consecutive failures (to avoid restarting on transient blips)
                if consecutive_failures >= 2:
                    now = time.time()
                    if now - last_restart < RESTART_COOLDOWN:
                        log(f"  Cooldown active, waiting {int(RESTART_COOLDOWN - (now - last_restart))}s")
                    else:
                        snapshot_dashboard_log()
                        success = restart()
                        last_restart = time.time()
                        total_restarts += 1
                        if success:
                            log(f"Restart #{total_restarts} succeeded")
                            consecutive_failures = 0
                        else:
                            log(f"Restart #{total_restarts} FAILED")

            time.sleep(CHECK_INTERVAL)

        except KeyboardInterrupt:
            log("Watchdog stopped by user")
            break
        except Exception as e:
            log(f"Watchdog error: {e}")
            time.sleep(CHECK_INTERVAL)

    # Cleanup
    try:
        os.remove(PID_FILE)
    except Exception:
        pass


if __name__ == "__main__":
    main()
