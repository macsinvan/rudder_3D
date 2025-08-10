# stock/wedge.py
import math
import Part
from FreeCAD import Vector
from typing import Callable, Dict, List, Tuple, Any

def build_wedge(row_dict: Dict[str, Any], radius_at: Callable[[float], float]) -> Tuple[List[Part.Shape], str]:
    """
    Build the 'wedge' tine variant (two steel strips forming a V).
    Returns (list_of_shapes, summary_str).
    Behavior matches the previous inline handler in stock2d.py.
    """
    start = float(row_dict['start'])
    width = float(row_dict['width'])
    length_out = float(row_dict['length'])
    t = float(row_dict['plate_thickness'])
    angle_deg = float(row_dict.get('angle', '90') or 90.0)
    label = row_dict.get('label', '')

    z_attach = -start
    try:
        r = radius_at(z_attach)
    except Exception as e:
        print(f"  ⚠️ radius_at({z_attach:.1f}) failed: {e}; default r=0")
        r = 0.0

    parts: List[Part.Shape] = []
    summary = ""

    if abs(angle_deg - 90.0) < 1e-9:
        # 90° case (two strips). Keep the same geometry as before.
        if length_out <= 0:
            raise ValueError("wedge length must be > 0")

        # If your current inline code used a hard-coded test angle, keep it.
        # Otherwise, preserve the alpha derived from plate thickness & length:
        # alpha_deg = 20.0  # (use this if that’s what your current file has)
        alpha_rad = math.atan(0.5 * t / length_out)
        alpha_deg = math.degrees(alpha_rad)

        # Top strip: pivot at the strip’s far tip on the top edge
        p_top = Part.makeBox(length_out, t, width)
        p_top.Placement.Base = Vector(r, +0.5 * t, -(start + width))
        tip_pivot_top = Vector(r + length_out, +0.5 * t, -start)
        p_top = p_top.copy()
        p_top.rotate(tip_pivot_top, Vector(0, 0, 1), -alpha_deg)

        # Bottom strip: pivot at the strip’s far tip on the bottom edge
        p_bot = Part.makeBox(length_out, t, width)
        p_bot.Placement.Base = Vector(r, -1.5 * t, -(start + width))
        tip_pivot_bot = Vector(r + length_out, -0.5 * t, -start)
        p_bot = p_bot.copy()
        p_bot.rotate(tip_pivot_bot, Vector(0, 0, 1), +alpha_deg)

        parts.extend([p_top, p_bot])
        summary = (f"Wedge90 '{label}' start={start} w={width} len(edge)={length_out} "
                   f"t={t} r_at={r:.2f} alpha={alpha_deg:.3f}°")
        print(f"  ✓ Wedge90: label='{label}', r={r:.2f}, t={t}, len={length_out}, alpha={alpha_deg:.3f}°")

    else:
        # Angled case (unchanged from your inline behavior): rotate about post line then trim + optional strap.
        t_end = 2.0
        tilt   = 90.0 - angle_deg
        rot_deg = -tilt
        rot_rad = math.radians(abs(tilt))
        extra   = width * math.tan(rot_rad) if abs(tilt) > 1e-9 else 0.0
        eff_len = length_out + extra

        p_top = Part.makeBox(eff_len, t, width)
        p_bot = Part.makeBox(eff_len, t, width)
        p_top.Placement.Base = Vector(r,  +t/2.0, -(start + width))
        p_bot.Placement.Base = Vector(r,  -t - t/2.0, -(start + width))

        pivot = Vector(r, 0.0, -start)
        p_top = p_top.copy(); p_top.rotate(pivot, Vector(0,1,0), rot_deg)
        p_bot = p_bot.copy(); p_bot.rotate(pivot, Vector(0,1,0), rot_deg)

        x_cut = r + length_out * math.cos(math.radians(abs(tilt)))
        trim  = Part.makeBox(x_cut + 10000.0, 20000.0, 20000.0,
                             Vector(-10000.0, -10000.0, -10000.0))
        p_top = p_top.common(trim)
        p_bot = p_bot.common(trim)
        if p_top.isNull() or p_bot.isNull():
            print("  ⚠️ Wedge plates became null after trim; check angle/length inputs and x_cut.")

        strap = Part.makeBox(t_end, 3.0 * t, width)
        strap.Placement.Base = Vector(x_cut - t_end, -1.5 * t, -(start + width))

        parts.extend([p_top, p_bot, strap])
        summary = (f"Wedge '{label}' start={start} w={width} len={length_out} t={t} "
                   f"angle={angle_deg} r_at={r:.2f}")
        print(f"  ✓ Wedge*:  label='{label}', start={start}, width={width}, length={length_out}, "
              f"t={t}, angle={angle_deg:.2f}°, rot={rot_deg:.2f}°, x_cut={x_cut:.2f}, r_at={r:.2f}")

    return parts, summary