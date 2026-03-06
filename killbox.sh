#!/bin/bash
if pkill -f windowbox.py; then
    echo "WindowBox stopped."
else
    echo "WindowBox is not running."
fi
