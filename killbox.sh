#!/bin/bash
if pkill -f windowbox.py; then
    echo "windowbox stopped."
else
    echo "windowbox is not running."
fi
