#!/usr/bin/env bash
# Creates a single shared venv at the repo root and installs every
# component's dependencies, for integration work.
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
echo "Done. Activate with: source .venv/bin/activate"
