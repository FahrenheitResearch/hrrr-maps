#!/usr/bin/env python
"""
Bulletproof dashboard restart script for wxsection.com (Windows).

Usage:
    python restart_dashboard.py           # Kill existing + start fresh
    python restart_dashboard.py --status  # Just check status
    python restart_dashboard.py --kill    # Just kill, don't restart

This script:
  1. Finds and kills ANY existing dashboard process (by port or PID file)
  2. Waits for the port to be free
  3. Starts the dashboard with correct env vars and model flags
  4. Waits for HTTP 200 health check
  5. Saves PID for future management
  6. Prints status summary
"""
import subprocess
import sys
import os
import time
import signal
import json
import socket

# ============================================================================
# CONFIGURATION - Edit these if paths change
# ============================================================================
PYTHON = r"C:\Users\drew\miniforge3\envs\wxsection\python.exe"
DASHBOARD = r"C:\Users\drew\hrrr-maps\tools\unified_dashboard.py"
WORKDIR = r"C:\Users\drew\hrrr-maps"
PORT = 5565
MODELS = "hrrr,gfs,rrfs"
GRIB_WORKERS = 8
PID_FILE = os.path.join(os.environ.get("TEMP", r"C:\Users\drew\AppData\Local\Temp"), "wxsection_dashboard.pid")
LOG_FILE = os.path.join(os.environ.get("TEMP", r"C:\Users\drew\AppData\Local\Temp"), "wxsection_dashboard.log")

def _get_user_env(name):
    """Get env var, falling back to Windows User registry (for vars set via SetEnvironmentVariable)."""
    val = os.environ.get(name, "")
    if not val and sys.platform == "win32":
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Environment") as key:
                val, _ = winreg.QueryValueEx(key, name)
        except (OSError, FileNotFoundError):
            pass
    return val

ENV_VARS = {
    "XSECT_GRIB_BACKEND": "auto",
    "MAPBOX_TOKEN": _get_user_env("MAPBOX_TOKEN"),
    "XSECT_CACHE_DIR": r"C:\Users\drew\hrrr-maps\cache\xsect",
    "XSECT_OUTPUTS_DIR": r"C:\Users\drew\hrrr-maps\outputs",
    "XSECT_ARCHIVE_DIR": r"E:\hrrr-archive,F:\hrrr-archive,H:\hrrr-archive",
}

# Protected PIDs - NEVER kill these (auto_update, archive pipeline, etc.)
# Read from a file if it exists, otherwise empty
PROTECTED_PIDS_FILE = os.path.join(os.environ.get("TEMP", r"C:\Users\drew\AppData\Local\Temp"), "wxsection_protected_pids.txt")


def get_protected_pids():
    """Get PIDs that should never be killed."""
    pids = set()
    if os.path.exists(PROTECTED_PIDS_FILE):
        for line in open(PROTECTED_PIDS_FILE):
            line = line.strip()
            if line.isdigit():
                pids.add(int(line))
    return pids


def is_port_in_use(port):
    """Check if a port is in use."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) == 0


def find_pid_on_port(port):
    """Find the PID listening on a given port."""
    try:
        r = subprocess.run(
            ["netstat", "-ano", "-p", "TCP"],
            capture_output=True, text=True, timeout=10
        )
        for line in r.stdout.split("\n"):
            if f":{port}" in line and "LISTENING" in line:
                parts = line.strip().split()
                if parts:
                    pid = int(parts[-1])
                    return pid
    except Exception:
        pass
    return None


def get_saved_pid():
    """Get PID from PID file."""
    if os.path.exists(PID_FILE):
        try:
            pid = int(open(PID_FILE).read().strip())
            # Verify it's still running
            r = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
                capture_output=True, text=True, timeout=10
            )
            if str(pid) in r.stdout:
                return pid
        except Exception:
            pass
    return None


def kill_pid(pid, label=""):
    """Kill a specific PID."""
    protected = get_protected_pids()
    if pid in protected:
        print(f"  SKIP PID {pid} (protected) {label}")
        return False
    try:
        r = subprocess.run(
            ["taskkill", "/PID", str(pid), "/F"],
            capture_output=True, text=True, timeout=10
        )
        if "SUCCESS" in r.stdout:
            print(f"  Killed PID {pid} {label}")
            return True
        else:
            print(f"  Failed to kill PID {pid}: {r.stdout.strip()} {r.stderr.strip()}")
            return False
    except Exception as e:
        print(f"  Error killing PID {pid}: {e}")
        return False


def kill_all_dashboards():
    """Kill any process using our port + any saved PID."""
    killed = []

    # Method 1: Kill by port
    port_pid = find_pid_on_port(PORT)
    if port_pid:
        if kill_pid(port_pid, f"(port {PORT})"):
            killed.append(port_pid)

    # Method 2: Kill by saved PID
    saved_pid = get_saved_pid()
    if saved_pid and saved_pid not in killed:
        if kill_pid(saved_pid, "(saved PID)"):
            killed.append(saved_pid)

    # Method 3: Find large python processes that might be dashboard
    # (Dashboard uses 1GB+ RAM after loading mmap caches)
    try:
        r = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq python.exe", "/FO", "CSV", "/NH"],
            capture_output=True, text=True, timeout=10
        )
        protected = get_protected_pids()
        for line in r.stdout.strip().split("\n"):
            if not line.strip():
                continue
            parts = line.strip().split(",")
            if len(parts) < 5:
                continue
            pid = int(parts[1].strip('"'))
            mem_str = parts[4].strip('"').replace(" K", "").replace(",", "")
            try:
                mem_kb = int(mem_str)
            except ValueError:
                continue
            # Large python process (>500MB) that's not protected and not already killed
            if mem_kb > 500_000 and pid not in killed and pid not in protected:
                if kill_pid(pid, f"(large python, {mem_kb // 1024}MB)"):
                    killed.append(pid)
    except Exception:
        pass

    # Wait for port to be free
    if killed:
        for i in range(30):  # Wait up to 15 seconds
            if not is_port_in_use(PORT):
                break
            time.sleep(0.5)
        else:
            print(f"  WARNING: Port {PORT} still in use after 15s")

    return killed


def start_dashboard():
    """Start the dashboard with correct configuration."""
    env = os.environ.copy()
    env.update(ENV_VARS)

    cmd = [
        PYTHON, "-u", DASHBOARD,
        "--port", str(PORT),
        "--models", MODELS,
        "--grib-workers", str(GRIB_WORKERS),
    ]

    # Append mode — preserves crash evidence from previous runs
    log_fh = open(LOG_FILE, "a")
    log_fh.write(f"\n{'=' * 72}\n")
    log_fh.write(f"=== DASHBOARD RESTART at {time.strftime('%Y-%m-%d %H:%M:%S')} ===\n")
    log_fh.write(f"{'=' * 72}\n\n")
    log_fh.flush()

    p = subprocess.Popen(
        cmd,
        cwd=WORKDIR,
        env=env,
        stdout=log_fh,
        stderr=subprocess.STDOUT,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )

    # Save PID
    with open(PID_FILE, "w") as f:
        f.write(str(p.pid))

    return p.pid


def wait_for_healthy(timeout=120):
    """Wait for dashboard to respond to HTTP requests."""
    import urllib.request
    start = time.time()
    while time.time() - start < timeout:
        try:
            r = urllib.request.urlopen(f"http://127.0.0.1:{PORT}/api/status", timeout=5)
            if r.status == 200:
                return True
        except Exception:
            pass
        time.sleep(2)
    return False


def get_status():
    """Get current dashboard status."""
    import urllib.request
    status = {
        "pid": get_saved_pid(),
        "port_in_use": is_port_in_use(PORT),
        "port_pid": find_pid_on_port(PORT),
        "healthy": False,
        "models": {},
        "events_with_data": 0,
    }
    try:
        r = urllib.request.urlopen(f"http://127.0.0.1:{PORT}/api/v1/capabilities", timeout=5)
        d = json.loads(r.read())
        status["healthy"] = True
        for m in d.get("models", []):
            status["models"][m["id"]] = m["available_cycles"]
        status["event_count"] = d.get("event_count", 0)

        r2 = urllib.request.urlopen(f"http://127.0.0.1:{PORT}/api/v1/events", timeout=5)
        events = json.loads(r2.read())
        if isinstance(events, dict):
            events = events.get("events", [])
        status["events_with_data"] = sum(1 for e in events if e.get("has_data"))
    except Exception:
        pass
    return status


def print_status(status):
    """Pretty print status."""
    print(f"\n{'=' * 50}")
    print(f"wxsection.com Dashboard Status")
    print(f"{'=' * 50}")
    print(f"PID:            {status['pid'] or 'NOT RUNNING'}")
    print(f"Port {PORT}:      {'IN USE' if status['port_in_use'] else 'FREE'}")
    print(f"Health:         {'OK' if status['healthy'] else 'DOWN'}")
    if status["healthy"]:
        for model, cycles in status["models"].items():
            print(f"  {model:12s}  {cycles} cycles")
        print(f"Events:         {status.get('events_with_data', 0)}/{status.get('event_count', 0)} with data")
    print(f"Log:            {LOG_FILE}")
    print(f"PID file:       {PID_FILE}")
    print(f"{'=' * 50}")


def main():
    args = sys.argv[1:]

    if "--status" in args:
        print_status(get_status())
        return

    if "--kill" in args:
        print("Killing dashboard...")
        killed = kill_all_dashboards()
        if killed:
            print(f"Killed {len(killed)} process(es)")
        else:
            print("No dashboard processes found")
        return

    # Default: kill + restart
    print("=== wxsection.com Dashboard Restart ===\n")

    # Step 1: Kill existing
    print("Step 1: Killing existing dashboard...")
    killed = kill_all_dashboards()
    if not killed:
        print("  No existing dashboard found")

    # Step 2: Verify port is free
    if is_port_in_use(PORT):
        print(f"\nERROR: Port {PORT} still in use! Cannot start.")
        port_pid = find_pid_on_port(PORT)
        if port_pid:
            print(f"  PID {port_pid} is holding the port")
        sys.exit(1)

    # Step 3: Start
    print(f"\nStep 2: Starting dashboard...")
    print(f"  Python:  {PYTHON}")
    print(f"  Port:    {PORT}")
    print(f"  Models:  {MODELS}")
    print(f"  Archive: {ENV_VARS['XSECT_ARCHIVE_DIR']}")
    pid = start_dashboard()
    print(f"  PID:     {pid}")

    # Step 4: Wait for healthy
    print(f"\nStep 3: Waiting for health check...", end="", flush=True)
    if wait_for_healthy(timeout=90):
        print(" OK!")
    else:
        print(" TIMEOUT (dashboard may still be loading)")

    # Step 5: Status
    time.sleep(2)
    print_status(get_status())


if __name__ == "__main__":
    main()
