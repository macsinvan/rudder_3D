# stock/plate.py

import math
import Part
from FreeCAD import Vector
from typing import Callable, Dict, Any, List, Tuple

# NOTE: pure-Python math helper (no FreeCAD deps)
from stock.plate_math import compute_plate_angles

__all__ = ["make_wedge_debug_block", "build_plate"]


def make_wedge_debug_block(start: float, width: float, length_out: float, plate_thickness: float) -> Part.Shape:
    """
    Simple rectangular block to validate tine Z placement.

    - Visible thickness across Y = 2 * plate_thickness
    - Placement along Z uses -(start + width)
    """
    box = Part.makeBox(length_out, 2.0 * plate_thickness, width)
    box.Placement.Base = Vector(0.0, -plate_thickness, -(start + width))
    return box


def build_plate(row_dict: Dict[str, Any], radius_at_func: Callable[[float], float]) -> Tuple[List[Part.Shape], str]:
    """
    Build a 'plate' tine (single plate). This is a move-only of the current plate block from stock2d.py:
      - If CSV angle == 90°, compute inside-edge-tangent half-angle from (R, length, t),
        then use angle_deg = 90° - alpha_deg.
      - Else, use the CSV angle.
      - For exactly 90° after the above, place a flat/orthogonal plate.
      - Otherwise rotate about the Y-axis around the post contact line and trim.

    Returns (parts, summary)
    """
    # Inputs from CSV row
    start = float(row_dict['start'])
    width = float(row_dict['width'])
    length_out = float(row_dict['length'])
    t = float(row_dict['plate_thickness'])
    angle_deg_raw = float(row_dict.get('angle', '90') or 90.0)
    label = row_dict.get('label', '')

    # Post radius at attach Z
    z_attach = -start
    try:
        r = radius_at_func(z_attach)
    except Exception as e:
        print(f"  ⚠️ radius_at({z_attach:.1f}) failed: {e}; default r=0")
        r = 0.0

    # If CSV says 90°, compute inside-edge tangent half-angle and derive working angle
    angle_deg = angle_deg_raw
    if abs(angle_deg_raw - 90.0) < 1e-9:
        # inside edge tangent, using outside-edge length as per current behavior
        _, alpha_deg, _, _ = compute_plate_angles(r, length_out, t, tangent="inside")
        angle_deg = 90.0 - alpha_deg

    parts: List[Part.Shape] = []
    summary: str

    # Flat/orthogonal case after derivation
    if abs(angle_deg - 90.0) < 1e-9:
        p = Part.makeBox(length_out, t, width)
        p.Placement.Base = Vector(r, -t / 2.0, -(start + width))
        parts.append(p)
        summary = f"Plate '{label}' start={start} w={width} len={length_out} t={t} r_at={r:.2f}"
        print(f"  ✓ Plate:   label='{label}', start={start}, width={width}, length={length_out}, t={t}, r_at={r:.2f}")
        return parts, summary

    # Rotated (angle-aware) case — mirrors current stock2d.py logic
    tilt = 90.0 - angle_deg
    rot_deg = -tilt
    rot_rad = math.radians(abs(tilt))
    extra = width * math.tan(rot_rad) if abs(tilt) > 1e-9 else 0.0
    eff_len = length_out + extra

    p = Part.makeBox(eff_len, t, width)
    p.Placement.Base = Vector(r, -t / 2.0, -(start + width))

    pivot = Vector(r, 0.0, -start)
    p = p.copy()
    p.rotate(pivot, Vector(0, 1, 0), rot_deg)

    x_cut = r + length_out * math.cos(math.radians(abs(tilt)))
    trim = Part.makeBox(
        x_cut + 10000.0,
        20000.0,
        20000.0,
        Vector(-10000.0, -10000.0, -10000.0),
    )
    p = p.common(trim)
    if p.isNull():
        print("  ⚠️ Plate became null after trim; check angle/length inputs and x_cut.")

    parts.append(p)
    summary = (
        f"Plate '{label}' start={start} w={width} len={length_out} t={t} "
        f"angle={angle_deg} r_at={r:.2f}"
    )
    print(
        f"  ✓ Plate*:  label='{label}', start={start}, width={width}, length={length_out}, "
        f"t={t}, angle={angle_deg:.2f}°, rot={rot_deg:.2f}°"
    )
    return parts, summary