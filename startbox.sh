#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate
export DISPLAY=${DISPLAY:-:0}
export WAYLAND_DISPLAY=${WAYLAND_DISPLAY:-wayland-1}
python3 windowbox.py
