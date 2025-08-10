import math
import FreeCAD as App
import Part
from FreeCAD import Vector

__all__ = ["make_wedge_debug_block", "compute_plate_angles"]

def make_wedge_debug_block(start: float, width: float, length_out: float, plate_thickness: float) -> Part.Shape:
    """
    Simple rectangular block to validate tine Z placement.

    Notes:
    - Visible thickness across Y = 2 * plate_thickness (debug viz only)
    - Placement along Z uses -(start + width)
    """
    box = Part.makeBox(length_out, 2.0 * plate_thickness, width)
    box.Placement.Base = Vector(0.0, -plate_thickness, -(start + width))
    return box

def compute_plate_angles(radius: float,
                         length: float,
                         thickness: float,
                         tangent: str = "inside"):
    """
    Compute the V-angle so that the selected edge of each plate is tangent to the post
    at the attachment Z. Returns:
        (half_angle_rad, half_angle_deg, v_angle_rad, v_angle_deg)

    Parameters
    ----------
    radius : float
        Post radius R at attachment mid-span (mm).
    length : float
        Plate length measured along the OUTSIDE long edge (mm).
    thickness : float
        Plate thickness t (mm).
    tangent : str
        Which plate edge is tangent to the post: "inside" | "center" | "outside".

    Geometry
    --------
    Let R_eff be:
        inside  -> R
        center  -> R + t/2
        outside -> R + t
    Then half-angle alpha satisfies:  tan(alpha) = R_eff / length
    and V-angle phi = 2 * alpha.

    Raises
    ------
    ValueError on invalid inputs.
    """
    if length <= 0 or radius <= 0 or thickness < 0:
        raise ValueError("radius>0, length>0, thickness>=0 required")

    key = tangent.strip().lower()
    if key == "inside":
        r_eff = radius
    elif key == "center":
        r_eff = radius + thickness * 0.5
    elif key == "outside":
        r_eff = radius + thickness
    else:
        raise ValueError("tangent must be 'inside', 'center', or 'outside'")

    half = math.atan2(r_eff, length)  # radians
    v = 2.0 * half
    return half, math.degrees(half), v, math.degrees(v)
