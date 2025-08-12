# stock/wedge_angled.py

import math
import Part
from FreeCAD import Vector

def build_wedge(row_dict, radius_at_func):
    """
    Angled wedge tine geometry — visual description:

    Imagine standing in front of the rudder stock and looking straight down at it from above:
    - Two flat plates extend from opposite sides of the post, meeting at an angle to form a wedge.
    - The inside edges of the plates curve gently around the post where they’re welded.
    - The outside tip of the wedge has a straight cut that is perfectly parallel to the post —
      like slicing the wedge with a vertical guillotine.
    - This tip face is where the two angled plates meet and are welded together.
    - From above, the wedge looks like an open “V” with the point cut off square so the open ends
      line up parallel to the post.
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
        # ---- Inside-edge tangent geometry using INSIDE edge length (L_in) ----
        L_in = length_out
        R_eff = r - t
        if L_in <= 0 or R_eff <= 0:
            raise ValueError(f"invalid inside geometry: L_in={L_in}, R_eff={R_eff} (r={r}, t={t})")

        alpha_rad = math.atan2(R_eff, L_in)
        alpha_deg = math.degrees(alpha_rad)

        # External tip point distance from center for inside-edge tangent
        d = math.hypot(R_eff, L_in)
        base_x = d - L_in

        p_top = Part.makeBox(L_in, t, width)
        p_top.Placement.Base = Vector(base_x, 0.0, -(start + width))
        tip_pivot_top = Vector(d, 0.0, -start)

        p_bot = Part.makeBox(L_in, t, width)
        p_bot.Placement.Base = Vector(base_x, -t, -(start + width))
        tip_pivot_bot = Vector(d, 0.0, -start)

        p_top = p_top.copy()
        p_top.rotate(tip_pivot_top, Vector(0, 0, 1), -alpha_deg)

        p_bot = p_bot.copy()
        p_bot.rotate(tip_pivot_bot, Vector(0, 0, 1), +alpha_deg)

        parts.extend([p_top, p_bot])

        summary = (
            f"Wedge90 '{label}' start={start} w={width} L_in={L_in} "
            f"t={t} r_at={r:.2f} R_eff={R_eff:.2f} alpha={alpha_deg:.3f}° tip_x={d:.3f} (inside tangent, y=0 meet)"
        )
        print(
            f"  ✓ Wedge90: label='{label}', r={r:.2f}, t={t}, L_in={L_in}, "
            f"R_eff={R_eff:.2f}, alpha={alpha_deg:.3f}°, tip_x={d:.3f} (inside tangent, y=0 meet)"
        )
        return parts, summary

    # ----- Angled (≠ 90°): rotated about post and vertically trimmed -----
    tilt = 90.0 - angle_deg
    rot_deg = -tilt
    rot_rad = math.radians(abs(tilt))
    extra = width * math.tan(rot_rad) if abs(tilt) > 1e-9 else 0.0
    eff_len = length_out + extra

    # Place so INSIDE edges coincide at y=0 (top [0,t], bottom [-t,0])
    p_top = Part.makeBox(eff_len, t, width)
    p_bot = Part.makeBox(eff_len, t, width)
    p_top.Placement.Base = Vector(r, 0.0, -(start + width))   # spans y ∈ [0, t]
    p_bot.Placement.Base = Vector(r, -t,  -(start + width))   # spans y ∈ [-t, 0]

    # Rotate both about the post contact line (x=r, y=0, z=-start)
    pivot = Vector(r, 0.0, -start)
    p_top = p_top.copy()
    p_bot = p_bot.copy()
    p_top.rotate(pivot, Vector(0, 1, 0), rot_deg)
    p_bot.rotate(pivot, Vector(0, 1, 0), rot_deg)

    # Vertical tip plane parallel to post; keep x <= x_cut (inside portion).
    x_cut = r + length_out * math.cos(abs(rot_rad))
    trim = Part.makeBox(
        x_cut + 10000.0,            # from large negative X up to x_cut
        20000.0,
        20000.0,
        Vector(-10000.0, -10000.0, -10000.0),
    )

    p_top = p_top.common(trim)
    p_bot = p_bot.common(trim)
    if p_top.isNull() or p_bot.isNull():
        print("  ⚠️ Wedge plates became null after vertical trim; check angle/length inputs and x_cut.")

    parts.extend([p_top, p_bot])

    summary = (
        f"Wedge '{label}' start={start} w={width} len={length_out} t={t} "
        f"angle={angle_deg} r_at={r:.2f} vertical_tip_cut"
    )
    print(
        f"  ✓ Wedge*:  label='{label}', start={start}, width={width}, length={length_out}, "
        f"t={t}, angle={angle_deg:.2f}°, rot={rot_deg:.2f}°, vertical tip cut at x={x_cut:.2f}, r_at={r:.2f}"
    )
    return parts, summary