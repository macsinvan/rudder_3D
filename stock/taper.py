# stock/taper.py
# Move-only refactor of taper geometry from stock2d.py

import Part
from FreeCAD import Vector

def build_taper(row_dict):
    """
    Build a single taper (truncated cone) Part shape from a CSV row.

    Expected row_dict keys:
      - start, end: Z positions (mm)
      - diameter_start: diameter at the TOP (mm)
      - diameter_end: diameter at the BOTTOM (mm)
      - label: optional text label
    Returns:
      (parts, summary) where:
        parts  = [Part.Shape]
        summary = str
    """
    label = row_dict.get('label', '')

    z0 = -float(row_dict['start'])
    z1 = -float(row_dict['end'])
    height = abs(z1 - z0)

    d_top = float(row_dict['diameter_start'])  # top
    d_bot = float(row_dict['diameter_end'])    # bottom

    # FreeCAD's makeCone takes radii and height, with the base at given vector.
    # Original code: base at Vector(0, 0, z0 - height)
    cone = Part.makeCone(d_bot / 2.0, d_top / 2.0, height, Vector(0, 0, z0 - height))

    summary = f"Taper '{label}' h={height} d1={d_top}→d2={d_bot}"
    return [cone], summary