# stock/wedge_angled.py

import math
import Part
from FreeCAD import Vector

def build_wedge(row_dict, radius_at_func):
    """
    Angled wedge tine — Baby Step 3 + Step 2 + Tip Cut (YZ at x = r + L_csv)

    What this step does
    -------------------
    1) Compute leading/trailing extensions:
         - E_lead  = 2*r                      (leading edge toward post)
         - E_trail = L_csv*(secθ-1) + w*tanθ  (trailing edge toward tip)
       where θ = |90° - angle| is the +Y tilt from vertical, w = plate width.
    2) Build the two plates as a V with over-length:
         L_total = L_csv + E_lead + E_trail
    3) Place the rotation pivot exactly (CSV + E_trail) back from the far end:
         x_pivot_local = d - (L_csv + E_trail)
       Translate so pivot sits on the post at x = r.
    4) Rotate the V by rotY = -(90° - angle) about +Y through that pivot.
    5) TIP CUT (new): trim with a YZ plane at x = r + L_csv to make the tip
       face parallel to the post while preserving the CSV top-edge length.

    90° case is unchanged (no extensions, no cut).
    """

    # Inputs
    start = float(row_dict['start'])
    width = float(row_dict['width'])
    length_out = float(row_dict['length'])      # CSV customer length (top edge)
    t = float(row_dict['plate_thickness'])
    angle_deg = float(row_dict.get('angle', '90') or 90.0)
    label = row_dict.get('label', '')

    # Quick heartbeat print
    print(f"  🟩 wedge_angled.py hit: start={start}, width={width}, L_csv={length_out}, t={t}, angle={angle_deg}")

    # Radius at attach Z (used for placement/seat math)
    z_attach = -start
    try:
        r = float(radius_at_func(z_attach))
    except Exception as e:
        print(f"  ⚠️ radius_at({z_attach:.1f}) failed: {e}; default r=0")
        r = 0.0

    parts = []

    # =========================
    # 90° WEDGE (unchanged)
    # =========================
    if abs(angle_deg - 90.0) < 1e-9:
        L_in = length_out
        R_eff = r - t
        if L_in <= 0 or R_eff <= 0:
            raise ValueError(f"invalid inside geometry: L_in={L_in}, R_eff={R_eff} (r={r}, t={t})")

        alpha_rad = math.atan2(R_eff, L_in)
        alpha_deg = math.degrees(alpha_rad)

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
            f"t={t} r_at={r:.2f} alpha={alpha_deg:.3f}° tip_x={d:.3f}"
        )
        print(
            f"  ✓ Wedge90: label='{label}', r={r:.2f}, t={t}, L_in={L_in}, "
            f"alpha={alpha_deg:.3f}°, tip_x={d:.3f}"
        )
        return parts, summary

    # ======================================================
    # ANGLED (≠90°): Apply extensions in geometry
    # ======================================================

    # --- Step 1: compute extensions ---
    theta_deg = abs(90.0 - angle_deg)             # tilt from vertical
    theta_rad = math.radians(theta_deg)

    # Leading-edge extension (toward post)
    E_lead = 2.0 * r

    # Trailing-edge extension (toward tip) = foreshortening + bottom-corner swing
    # ΔL = L_csv*(secθ - 1) + width*tanθ
    E_trail = length_out * (1.0 / math.cos(theta_rad) - 1.0) + width * math.tan(theta_rad)

    print(
        f"  ➜ Extensions: lead={E_lead:.3f}, trail={E_trail:.3f} "
        f"(θ={theta_deg:.1f}°, L_csv={length_out}, width={width})"
    )

    # --- Step 2: build V with both extensions ---
    L_total = length_out + E_lead + E_trail
    L_in = L_total
    R_eff = r - t
    if L_in <= 0 or R_eff <= 0:
        raise ValueError(f"invalid inside geometry: L_in={L_in}, R_eff={R_eff} (r={r}, t={t})")

    alpha_rad = math.atan2(R_eff, L_in)
    alpha_deg = math.degrees(alpha_rad)

    d = math.hypot(R_eff, L_in)     # X position of far tip of the over-length V
    base_x = d - L_in               # box base X before any translation

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

    # --- Step 3: place pivot (CSV + E_trail back from far end), then translate to x=r ---
    x_pivot_local = d - (length_out + E_trail)  # pivot distance from far tip inside the V

    dx = r - x_pivot_local
    if abs(dx) > 1e-12:
        p_top.translate(Vector(dx, 0.0, 0.0))
        p_bot.translate(Vector(dx, 0.0, 0.0))

    # --- Step 4: rotate about +Y through that pivot ---
    tilt = 90.0 - angle_deg
    rot_deg = -tilt
    pivot = Vector(r, 0.0, -start)  # pivot is exactly where we placed the rotation point
    p_top = p_top.copy()
    p_bot = p_bot.copy()
    p_top.rotate(pivot, Vector(0, 1, 0), rot_deg)
    p_bot.rotate(pivot, Vector(0, 1, 0), rot_deg)

    # --- Step 5: TIP CUT (YZ plane at x = r + L_csv) ---
    x_cut = r + length_out
    # Build a big cutting prism that keeps the side x <= x_cut
    # Use bounding boxes to size generously.
    bb = p_top.BoundBox
    bb.add(p_bot.BoundBox)
    margin = max(10.0, 5.0 * max(1.0, r, length_out, width, t))

    x_min = bb.XMin - margin      # far enough negative
    x_max = x_cut                 # plane location
    y_min = bb.YMin - margin
    y_max = bb.YMax + margin
    z_min = min(bb.ZMin, -start - width) - margin
    z_max = max(bb.ZMax, -start) + margin

    size_x = x_max - x_min
    size_y = y_max - y_min
    size_z = z_max - z_min
    trim = Part.makeBox(size_x, size_y, size_z)
    trim.Placement.Base = Vector(x_min, y_min, z_min)

    print(f"  ✂ TipCut: plane x = r + L_csv = {x_cut:.3f} (keep x ≤ plane)")

    p_top = p_top.common(trim)
    p_bot = p_bot.common(trim)

    if p_top.isNull() or p_bot.isNull():
        print("  ⚠️ Tip cut produced a null plate; check x_cut and extensions.")

    parts.extend([p_top, p_bot])

    summary = (
        f"WedgeAngled-TipCut '{label}' start={start} w={width} "
        f"L_csv={length_out} L_total={L_total} t={t} r_at={r:.2f} "
        f"alpha={alpha_deg:.3f}° rotY={rot_deg:.2f}° x_cut={x_cut:.3f} "
        f"[E_lead={E_lead:.3f}, E_trail={E_trail:.3f}, θ={theta_deg:.1f}°]"
    )
    print(
        f"  ✓ WedgeAngled TipCut: label='{label}', r={r:.2f}, t={t}, "
        f"L_csv={length_out}, L_total={L_total}, alpha={alpha_deg:.3f}°, "
        f"x_pivot_local={x_pivot_local:.3f}, dx={dx:.3f}, rotY={rot_deg:.2f}°, "
        f"x_cut={x_cut:.3f} [E_lead={E_lead:.3f}, E_trail={E_trail:.3f}, θ={theta_deg:.1f}°]"
    )
    return parts, summary