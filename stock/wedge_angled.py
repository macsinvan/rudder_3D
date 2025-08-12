 # stock/wedge_angled.py

import math
import Part
from FreeCAD import Vector

def build_wedge(row_dict, radius_at_func):
    """
    Angled wedge tine — Baby Step 3

    What this step does
    -------------------
    1) Build the two plates as a V in plan using an **over‑length**:
         L_total = CSV_length + 2*r   (r = radius at attach Z)
    2) Compute the **pivot point** along the plate: exactly `CSV_length`
       back from the far (square) end of the over‑length V. In local X:
         x_pivot_local = d - CSV_length
       where d = hypot(R_eff, L_total) is the V’s tip X (inside-edge tangent).
    3) **Place** the V so this pivot lies on the post surface at x = r.
    4) **Rotate** the V by the requested departure angle about the **Y‑axis
       through that pivot**.  (No vertical tip cut yet.)

    Notes
    -----
    – 90° case is unchanged.
    – No trims/straps yet. The customer top‑edge length will be enforced
      in the next step by a vertical tip cut at the appropriate X plane.
    """

    # Inputs
    start = float(row_dict['start'])
    width = float(row_dict['width'])
    length_out = float(row_dict['length'])      # CSV customer length (top edge)
    t = float(row_dict['plate_thickness'])
    angle_deg = float(row_dict.get('angle', '90') or 90.0)
    label = row_dict.get('label', '')

    # Radius at attach Z (used for L_total and placement)
    z_attach = -start
    try:
        r = radius_at_func(z_attach)
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
    # ANGLED (≠90°): Baby Step 3 — V-only, place pivot, rotate about Y
    # ======================================================

    # 1) Over‑length then V construction in plan
    L_total = length_out + 2.0 * r
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

    # 2) Compute pivot (CSV_length back from the far end) in local X
    x_pivot_local = d - length_out  # inside coordinate of the rotation point

    # 3) Translate in X so the pivot sits on the post surface at x = r
    dx = r - x_pivot_local
    if abs(dx) > 1e-12:
        p_top.translate(Vector(dx, 0.0, 0.0))
        p_bot.translate(Vector(dx, 0.0, 0.0))

    # 4) Rotate about Y through that pivot (no tip trim yet)
    tilt = 90.0 - angle_deg
    rot_deg = -tilt
    pivot = Vector(r, 0.0, -start)  # pivot is exactly where we placed the rotation point
    p_top = p_top.copy()
    p_bot = p_bot.copy()
    p_top.rotate(pivot, Vector(0, 1, 0), rot_deg)
    p_bot.rotate(pivot, Vector(0, 1, 0), rot_deg)

    # Done (no vertical cut yet)
    parts.extend([p_top, p_bot])

    summary = (
        f"WedgeAngled-Rotate '{label}' start={start} w={width} "
        f"L_csv={length_out} L_total={L_total} t={t} r_at={r:.2f} "
        f"alpha={alpha_deg:.3f}° rotY={rot_deg:.2f}° (pivot at x=r; no trim)"
    )
    print(
        f"  ✓ WedgeAngled Rotate: label='{label}', r={r:.2f}, t={t}, "
        f"L_csv={length_out}, L_total={L_total}, alpha={alpha_deg:.3f}°, "
        f"x_pivot_local={x_pivot_local:.3f}, dx={dx:.3f}, rotY={rot_deg:.2f}° (no trim)"
    )
    return parts, summary
