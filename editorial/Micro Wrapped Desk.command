#!/bin/bash
# Double-click in Finder: starts the desk and opens it in your browser.
cd "$(dirname "$0")/.." || exit 1
python3 -c "import yaml" 2>/dev/null || pip3 install --quiet pyyaml pillow
exec python3 editorial/desk.py
