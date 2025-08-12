# stock/plate.py

import math
import Part
from FreeCAD import Vector
from typing import Callable, Dict, Any, List, Tuple

# NOTE: pure-Python math helper (no FreeCAD deps)
from stock.plate_math import compute_plate_angles

__all__ = ["make_wedge_debug_block", "build_plate"]

# Fixed penetration into the post for 90° plates (mm)
_PENETRATION_90 = 5.0


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
        then use angle_deg = 90° - alpha_deg. (We preserve existing behavior.)
      - Else, use the CSV angle.
      - For exactly 90° after the above, place a flat/orthogonal plate.
      - Otherwise rotate about the Y-axis around the post contact line and trim.

    CHANGE (isolated): For the 90° case only, extend the plate into the post by a small fixed
    penetration along +X while shifting the base −penetration, so the visible top-edge length
    outside the post remains exactly the CSV 'length'.
    """
    # Inputs from CSV row
    start = float(row_dict['start'])
    width = float(row_dict['width'])
    length_out = float(row_dict['length'])
    t = float(row_dict['plate_thickness'])
    angle_deg_raw = float(row_dict.get('angle', '90') or 90.0)
    label = row_dict.get('label', '')

    # Post radius at attach Z (kept for logs; no change to 90° geometry beyond penetration)
    z_attach = -start
    try:
        r = radius_at_func(z_attach)
    except Exception:
        r = 0.0

    # Working angle
    angle_deg = angle_deg_raw
    if abs(angle_deg_raw - 90.0) < 1e-9:
        # Preserve existing behavior; compute but do not alter angle
        _, alpha_deg, _, _ = compute_plate_angles(r, length_out, t, tangent="inside")

    parts: List[Part.Shape] = []
    summary: str

    # Flat/orthogonal case after derivation
    if abs(angle_deg - 90.0) < 1e-9:
        # Extend into the post by a fixed penetration, but keep the user-specified
        # visible length (top edge) outside the post equal to 'length_out'.
        pen = _PENETRATION_90 if _PENETRATION_90 > 0.0 else 0.0
        eff_len = length_out

        p = Part.makeBox(eff_len, t, width)
        # Shift base X by -pen so that the segment from x=r to x=r+length_out is preserved.
        p.Placement.Base = Vector(r - pen, -t / 2.0, -(start + width))

        parts.append(p)
        summary = (
            f"Plate '{label}' start={start} w={width} len={length_out} t={t} "
            f"r_at={r:.2f} pen90={pen:.2f}"
        )
        return parts, summary

    # Rotated (angle-aware) case — unchanged from current behavior
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

    parts.append(p)
    summary = (
        f"Plate '{label}' start={start} w={width} len={length_out} t={t} "
        f"angle={angle_deg} r_at={r:.2f}"
    )
    return parts, summary