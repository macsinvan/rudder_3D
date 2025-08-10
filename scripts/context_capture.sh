#!/usr/bin/env bash
set -euo pipefail

echo "### stock2d VERSION and wedge import"
grep -nE 'VERSION\s*=' stock/stock2d.py || true
grep -n 'from stock.wedge import build_wedge' stock/stock2d.py || true

echo
echo "### stock2d draw.py imports"
grep -n 'from stock.draw import' stock/stock2d.py || true

echo
echo "### draw.py function presence"
grep -n 'def create_drawing_page' stock/draw.py || echo "create_drawing_page: not found"
grep -n 'def calculate_uniform_scale' stock/draw.py || echo "calculate_uniform_scale: not found"

echo
echo "### wedge.py build_wedge presence"
grep -n 'def build_wedge' stock/wedge.py || echo "build_wedge: not found"

echo
echo "### Last 10 commits for stock2d.py"
git log --oneline -- stock/stock2d.py | head -10

echo
echo "### Last 10 commits for wedge.py"
git log --oneline -- stock/wedge.py | head -10

echo
echo "### Last 10 commits for draw.py"
git log --oneline -- stock/draw.py | head -10

echo
echo "### Working tree status"
git status -sb

echo
echo "### TechDraw imports in stock2d.py"
grep -n 'TechDraw' stock/stock2d.py || echo "No TechDraw imports in stock2d"

echo
echo "### End of Context Dump"
