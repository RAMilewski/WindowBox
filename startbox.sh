#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate
export DISPLAY=${DISPLAY:-:0}
export WAYLAND_DISPLAY=${WAYLAND_DISPLAY:-wayland-1}

if [[ "$1" == "-b" ]]; then
    nohup python3 windowbox.py >> windowbox.log 2>&1 &
    echo "WindowBox started in background (pid $!). Log: windowbox.log"
else
    python3 windowbox.py
fi
