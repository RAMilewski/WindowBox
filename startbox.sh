#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate
DISPLAY=:0 WAYLAND_DISPLAY=wayland-1 python3 windowbox.py
