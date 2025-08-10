# stock/wedge.py

import math
import Part
from FreeCAD import Vector
from stock.plate import compute_plate_angles


def build_wedge(row_dict, radius_at_func):
    """
    Build a 'wedge' tine as two steel strips.
      - If angle == 90°: compute half-angle and pivot each strip at the common tip P
        so the INSIDE edges (one from each strip) are tangent and meet at the tip.
      - Else (angled tine): rotate both strips about the post contact line (Y-rotation),
        trim to a constant-X plane, then add a small end strap.
    """
    # Inputs
    start = float(row_dict['start'])
    width = float(row_dict['width'])
    length_out = float(row_dict['length'])
    t = float(row_dict['plate_thickness'])
    angle_deg = float(row_dict.get('angle', '90') or 90.0)
    label = row_dict.get('label', '')

    # Radius at attach Z
    z_attach = -start
    try:
        r = radius_at_func(z_attach)
    except Exception as e:
        print(f"  ⚠️ radius_at({z_attach:.1f}) failed: {e}; default r=0")
        r = 0.0

    parts = []

    if abs(angle_deg - 90.0) < 1e-9:
        # Inside-edge tangent geometry using outside-edge length
        _, alpha_deg, _, _ = compute_plate_angles(r, length_out, t, tangent="inside")
        if length_out <= 0:
            raise ValueError("wedge length must be > 0")

        # External point (common tip) distance from center
        d = math.sqrt(r * r + length_out * length_out)  # ~221.097 for r=22, L=220
        base_x = d - length_out

        # Place both strips so their INSIDE edges lie on y = 0 and meet at the same tip (y = 0)
        # Top strip spans y ∈ [0, t]; bottom strip spans y ∈ [-t, 0]
        p_top = Part.makeBox(length_out, t, width)
        p_top.Placement.Base = Vector(base_x, 0.0, -(start + width))
        tip_pivot_top = Vector(d, 0.0, -start)

        p_bot = Part.makeBox(length_out, t, width)
        p_bot.Placement.Base = Vector(base_x, -t, -(start + width))
        tip_pivot_bot = Vector(d, 0.0, -start)

        # Rotate about Z so the V opens in plan view; inside edges share the same tip
        p_top = p_top.copy()
        p_top.rotate(tip_pivot_top, Vector(0, 0, 1), -alpha_deg)

        p_bot = p_bot.copy()
        p_bot.rotate(tip_pivot_bot, Vector(0, 0, 1), +alpha_deg)

        parts.extend([p_top, p_bot])  # no strap in the 90° case

        summary = (
            f"Wedge90 '{label}' start={start} w={width} len(edge)={length_out} "
            f"t={t} r_at={r:.2f} alpha={alpha_deg:.3f}° (tip pivot, inside tangent, y=0 meet)"
        )
        print(
            f"  ✓ Wedge90: label='{label}', r={r:.2f}, t={t}, len={length_out}, "
            f"alpha={alpha_deg:.3f}°, tip_x={d:.3f} (inside tangent, y=0 meet)"
        )
        return parts, summary

    # ----- Angled (≠ 90°): existing behavior with Y-rotation, trim, and small strap -----
    t_end = 2.0
    tilt = 90.0 - angle_deg
    rot_deg = -tilt
    rot_rad = math.radians(abs(tilt))
    extra = width * math.tan(rot_rad) if abs(tilt) > 1e-9 else 0.0
    eff_len = length_out + extra

    p_top = Part.makeBox(eff_len, t, width)
    p_bot = Part.makeBox(eff_len, t, width)
    p_top.Placement.Base = Vector(r, +t / 2.0, -(start + width))
    p_bot.Placement.Base = Vector(r, -t - t / 2.0, -(start + width))

    pivot = Vector(r, 0.0, -start)
    p_top = p_top.copy()
    p_bot = p_bot.copy()
    p_top.rotate(pivot, Vector(0, 1, 0), rot_deg)
    p_bot.rotate(pivot, Vector(0, 1, 0), rot_deg)

    x_cut = r + length_out * math.cos(math.radians(abs(tilt)))
    trim = Part.makeBox(
        x_cut + 10000.0,
        20000.0,
        20000.0,
        Vector(-10000.0, -10000.0, -10000.0),
    )
    p_top = p_top.common(trim)
    p_bot = p_bot.common(trim)
    if p_top.isNull() or p_bot.isNull():
        print("  ⚠️ Wedge plates became null after trim; check angle/length inputs and x_cut.")

    strap = Part.makeBox(t_end, 3.0 * t, width)
    strap.Placement.Base = Vector(x_cut - t_end, -1.5 * t, -(start + width))

    parts.extend([p_top, p_bot, strap])

    summary = (
        f"Wedge '{label}' start={start} w={width} len={length_out} t={t} "
        f"angle={angle_deg} r_at={r:.2f}"
    )
    print(
        f"  ✓ Wedge*:  label='{label}', start={start}, width={width}, length={length_out}, "
        f"t={t}, angle={angle_deg:.2f}°, rot={rot_deg:.2f}°, x_cut={x_cut:.2f}, r_at={r:.2f}"
    )
    return parts, summary