#!/bin/bash
cd "$(dirname "$0")"
git pull && pkill -USR1 -f windowbox.py
