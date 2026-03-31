#!/bin/bash
# deploy.sh <config-folder>
# Copies playlist.txt, priority.txt, windowbox.cfg, and images/ from the
# specified folder into ~/windowbox, then reloads windowbox.

set -e

if [[ -z "$1" ]]; then
    echo "Usage: $0 <config-folder>"
    exit 1
fi

SRC="$(cd "$(dirname "$0")/$1" 2>/dev/null && pwd)" || {
    echo "Error: folder '$1' not found relative to $(dirname "$0")"
    exit 1
}

DEST=~/windowbox

for f in playlist.txt priority.txt windowbox.cfg; do
    if [[ -f "$SRC/$f" ]]; then
        cp "$SRC/$f" "$DEST/$f"
        echo "Copied $f"
    fi
done

if [[ -d "$SRC/images" ]]; then
    cp -r "$SRC/images/." "$DEST/images/"
    echo "Copied images/"
fi

echo "Deploy complete. Reloading windowbox..."
pkill -USR1 -f windowbox.py && echo "Reloaded." || echo "windowbox not running — start it with ./startbox.sh"
