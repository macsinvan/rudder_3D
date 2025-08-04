#!/usr/bin/env bash
set -e

# Activate the venv
source venv/bin/activate

# Ensure Python finds your outline package
export PYTHONPATH="$PWD/outline:$PYTHONPATH"

# Run exactly the outline test file
python -m pytest -q outline/tests/test_outline.py "$@"