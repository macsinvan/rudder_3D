# stock/heel_cutter.py
# ------------------------------------------------------------
# Heel Cutter utilities for trimming tines/arms flush to a plane.
# This version anchors the cutter’s INNER FACE on X = plane_x (default 0)
# and extends the block away from that plane toward +X or –X.
# ------------------------------------------------------------

from typing import List, Dict, Tuple, Optional
from FreeCAD import Vector
import Part

__all__ = [
    "add_post_half_box",
    "add_post_half_box_from_segments",
]

"""
Heel Cutter Module (plane-anchored)
-----------------------------------

Purpose:
    Build a rectangular cutter whose inner face lies exactly on a given
    plane X = plane_x (default 0). Use it to trim any geometry that
    protrudes across that plane.

Key behavior:
    - side="negX": inner face at X=plane_x, box extends toward –X
    - side="posX": inner face at X=plane_x, box extends toward +X
    - Z span covers [z_bottom, z_top] with oversize padding
    - Y span is symmetric about Y=0 with oversize padding

Returns:
    (Part.Shape, Part::Feature document object)
"""


def add_post_half_box(doc,
                      z_bottom: float,
                      z_top: float,
                      r_bottom: float,   # kept for signature compatibility (unused)
                      r_top: float,      # kept for signature compatibility (unused)
                      *,
                      side: str = "negX",
                      oversize: float = 1.0,
                      plane_x: float = 0.0,
                      y_clear: Optional[float] = None,
                      x_depth: Optional[float] = None,
                      name: str = "HeelCutterHalfBox") -> Tuple[Part.Shape, object]:
    """
    Create a rectangular cutter with its inner face lying on X = plane_x.

    Args:
        doc: FreeCAD document.
        z_bottom, z_top: Z extents (mm). Order does not matter.
        r_bottom, r_top: Ignored (kept for API compatibility).
        side: "negX" (extend to -X) or "posX" (extend to +X).
        oversize: padding (mm) applied to Z and Y spans.
        plane_x: X position of the inner face (default 0.0).
        y_clear: overrides computed Y length if provided.
        x_depth: explicit depth away from the plane; otherwise auto.
        name: object name.

    Geometry:
        - z_len = (z_top - z_bottom) + 2*oversize
        - y_len = y_clear or (40.0 + 2*oversize)   # widen as needed
        - x_len = x_depth or (80.0 + 2*oversize)   # depth toward chosen side

        Box is created at origin with makeBox(x_len, y_len, z_len) (X length, Y width, Z height),
        then translated so that:
          - side="negX": X-max face is at plane_x  (box from plane_x - x_len → plane_x)
          - side="posX": X-min face is at plane_x  (box from plane_x → plane_x + x_len)
    """
    # Normalize Z
    z0 = float(min(z_bottom, z_top))
    z1 = float(max(z_bottom, z_top))
    pad = float(oversize if oversize is not None else 0.0)

    # Dimensions
    z_len = (z1 - z0) + 2.0 * pad
    if z_len <= 0:
        raise ValueError("Computed z_len must be positive.")

    y_len = float(y_clear) if y_clear is not None else (40.0 + 2.0 * pad)
    x_len = float(x_depth) if x_depth is not None else (80.0 + 2.0 * pad)
    if y_len <= 0 or x_len <= 0:
        raise ValueError("Computed cutter x_len/y_len must be positive.")

    # Build box at origin
    box = Part.makeBox(x_len, y_len, z_len)

    # Place so inner face is exactly at X = plane_x
    if side == "negX":
        # X-max at plane_x
        base_x = float(plane_x) - x_len
    elif side == "posX":
        # X-min at plane_x
        base_x = float(plane_x)
    else:
        raise ValueError("side must be 'negX' or 'posX'")

    base = Vector(base_x, -0.5 * y_len, z0 - pad)

    # Add to document
    cutter_obj = doc.addObject("Part::Feature", name)
    cutter_obj.Shape = box
    cutter_obj.Placement.Base = base

    # Debug appearance
    try:
        v = cutter_obj.ViewObject
        v.Transparency = 70
        v.LineColor = (0.0, 1.0, 0.0)   # green edges
        v.ShapeColor = (1.0, 1.0, 0.6)  # pale yellow
    except Exception:
        pass

    doc.recompute()
    return box, cutter_obj


def add_post_half_box_from_segments(doc,
                                    post_segments: List[Dict[str, float]],
                                    *,
                                    side: str = "negX",
                                    oversize: float = 1.0,
                                    plane_x: float = 0.0,
                                    name: str = "HeelCutterHalfBox") -> Tuple[Part.Shape, object]:
    """
    Convenience wrapper: derive Z limits from segments and build a plane-anchored box.

    `post_segments` entries must include at least:
        "z_bot", "z_top"  (radii fields are ignored by this plane-anchored cutter)
    """
    if not post_segments:
        raise ValueError("No post segments available to size cutter box.")

    z_bottom = min(float(seg["z_bot"]) for seg in post_segments)
    z_top    = max(float(seg["z_top"]) for seg in post_segments)

    return add_post_half_box(doc,
                             z_bottom, z_top,
                             r_bottom=0.0, r_top=0.0,
                             side=side, oversize=oversize,
                             plane_x=plane_x,
                             name=name)