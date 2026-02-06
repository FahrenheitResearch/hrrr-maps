#!/bin/bash
# wxsection.com startup script — run after reboot
# Usage: cd ~/hrrr-maps && ./start.sh

set -e
cd "$(dirname "$0")"

echo "=== wxsection.com startup ==="

# 1. Mount the HRRR VHD if not already mounted
if ! mountpoint -q /mnt/hrrr; then
    echo "Mounting VHD..."
    sudo mkdir -p /mnt/hrrr
    sudo mount /dev/sde /mnt/hrrr
    echo "  Mounted /dev/sde at /mnt/hrrr"
else
    echo "  VHD already mounted at /mnt/hrrr"
fi

# 2. Create cache directory on NVMe (fast local storage)
mkdir -p /home/drew/hrrr-maps/cache/xsect

# 3. Start auto-update (downloads new GRIB data)
if pgrep -f "auto_update" > /dev/null; then
    echo "  Auto-update already running"
else
    echo "Starting auto-update..."
    nohup python tools/auto_update.py --interval 2 --models hrrr,gfs,rrfs \
        --hrrr-slots 3 --gfs-slots 1 --rrfs-slots 1 > /tmp/auto_update.log 2>&1 &
    echo "  PID: $!"
fi

# 4. Start dashboard
if pgrep -f "unified_dashboard" > /dev/null; then
    echo "  Dashboard already running"
else
    echo "Starting dashboard on port 5561..."
    XSECT_GRIB_BACKEND=cfgrib WXSECTION_KEY=cwtc nohup python3 tools/unified_dashboard.py \
        --port 5561 --models hrrr,gfs,rrfs \
        > /tmp/dashboard.log 2>&1 &
    echo "  PID: $!"
fi

# 5. Start cloudflared tunnel
if pgrep -f "cloudflared" > /dev/null; then
    echo "  Cloudflared already running"
else
    echo "Starting cloudflared tunnel..."
    nohup cloudflared tunnel run wxsection > /tmp/cloudflared.log 2>&1 &
    echo "  PID: $!"
fi

sleep 3
echo ""
echo "=== Status ==="
echo "Dashboard:  $(pgrep -f unified_dashboard > /dev/null && echo 'RUNNING' || echo 'NOT RUNNING')"
echo "Auto-update: $(pgrep -f auto_update > /dev/null && echo 'RUNNING' || echo 'NOT RUNNING')"
echo "Cloudflared: $(pgrep -f cloudflared > /dev/null && echo 'RUNNING' || echo 'NOT RUNNING')"
echo "VHD:        $(mountpoint -q /mnt/hrrr && echo 'MOUNTED' || echo 'NOT MOUNTED')"
echo ""
echo "Logs:"
echo "  Dashboard:    tail -f /tmp/dashboard.log"
echo "  Auto-update:  tail -f /tmp/auto_update.log"
echo "  Cloudflared:  tail -f /tmp/cloudflared.log"
echo ""
echo "Site: https://wxsection.com"
