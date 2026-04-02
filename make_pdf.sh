#!/bin/bash
# Regenerate README.pdf from README.md
cd "$(dirname "$0")"
pandoc README.md -o /tmp/readme_temp.html --standalone --css raspi_print.css && \
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
    --headless --disable-gpu \
    --no-pdf-header-footer \
    --print-to-pdf="$(pwd)/README.pdf" \
    /tmp/readme_temp.html
echo "README.pdf written."
