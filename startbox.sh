#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate
export DISPLAY=${DISPLAY:-:0}
export WAYLAND_DISPLAY=${WAYLAND_DISPLAY:-wayland-1}

# Apply display settings from windowbox.cfg
if command -v wlr-randr &>/dev/null && [ -f windowbox.cfg ]; then
    WB_VALS=$(python3 - <<'EOF'
import configparser
c = configparser.ConfigParser()
c.read('windowbox.cfg')
d = c['display'] if 'display' in c else {}
print(d.get('output','HDMI-A-1'), d.get('rotation','normal'))
EOF
)
    read -r WB_OUTPUT WB_ROTATION <<< "$WB_VALS"
    wlr-randr --output "$WB_OUTPUT" --transform "$WB_ROTATION" 2>/dev/null || true
fi

if [[ "$1" == "-b" ]]; then
    nohup python3 windowbox.py >> windowbox.log 2>&1 &
    echo "windowbox started in background (pid $!). Log: windowbox.log"
else
    python3 windowbox.py
fi
