#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate
export DISPLAY=${DISPLAY:-:0}
export WAYLAND_DISPLAY=${WAYLAND_DISPLAY:-wayland-1}

# Apply display settings from windowbox.cfg
if command -v wlr-randr &>/dev/null && [ -f windowbox.cfg ]; then
    read -r WB_OUTPUT WB_ROTATION WB_RES < <(python3 - <<'EOF'
import configparser
c = configparser.ConfigParser()
c.read('windowbox.cfg')
d = c['display'] if 'display' in c else {}
print(d.get('output','HDMI-A-1'), d.get('rotation','normal'), d.get('resolution','1920x1080'))
EOF
)
    # Derive physical pre-rotation mode by swapping W×H for 90°/270° rotations
    W=${WB_RES%x*}
    H=${WB_RES#*x}
    if [[ "$WB_ROTATION" == "90" || "$WB_ROTATION" == "270" ]]; then
        PHYSICAL_MODE="${H}x${W}"
    else
        PHYSICAL_MODE="${W}x${H}"
    fi
    wlr-randr --output "$WB_OUTPUT" --mode "$PHYSICAL_MODE" --transform "$WB_ROTATION" 2>/dev/null || true
fi

if [[ "$1" == "-b" ]]; then
    nohup python3 windowbox.py >> windowbox.log 2>&1 &
    echo "windowbox started in background (pid $!). Log: windowbox.log"
else
    python3 windowbox.py
fi
