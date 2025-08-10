import math

__all__ = ["compute_plate_angles"]

def compute_plate_angles(radius: float,
                         length: float,
                         thickness: float,
                         tangent: str = "inside"):
    """
    Compute plate half-angle and V-angle so that the chosen edge is tangent to the post.

    Returns: (half_rad, half_deg, v_rad, v_deg)
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

    half = math.atan2(r_eff, length)
    v = 2.0 * half
    return half, math.degrees(half), v, math.degrees(v)
