# stock/wedge_angled.py

import math
import Part
from FreeCAD import Vector

def build_wedge(row_dict, radius_at_func, solid_v=False):  # Added solid_v parameter
    start = float(row_dict['start'])
    width = float(row_dict['width'])
    length_out = float(row_dict['length'])      # CSV top-edge length
    t = float(row_dict['plate_thickness'])
    angle_deg = float(row_dict.get('angle', '90') or 90.0)
    label = row_dict.get('label', '')

    print(f"  🟩 wedge_angled.py hit: start={start}, width={width}, L_csv={length_out}, t={t}, angle={angle_deg}, solid_v={solid_v}")

    z_attach = -start
    try:
        r = float(radius_at_func(z_attach))
        r_bot = float(radius_at_func(z_attach - width))
    except Exception as e:
        print(f"  ⚠️ radius_at() failed: {e}")
        r = 0.0
        r_bot = 0.0

    parts = []

    if abs(angle_deg - 90.0) < 1e-9:
        # This is actually a 90° wedge, but called from angled path
        L_in = length_out
        R_eff = r - t
        alpha_rad = math.atan2(R_eff, L_in)
        alpha_deg = math.degrees(alpha_rad)
        d = math.hypot(R_eff, L_in)
        base_x = d - L_in

        if solid_v:
            # Create single trapezoid for filled V
            # Wide end at post: 2*r (diameter)
            # Narrow end at tip: 2*t
            post_face_verts = [
                Vector(base_x, -r, -start),
                Vector(base_x, r, -start),
                Vector(base_x, r, -(start + width)),
                Vector(base_x, -r, -(start + width))
            ]
            post_wire = Part.makePolygon(post_face_verts + [post_face_verts[0]])
            
            tip_face_verts = [
                Vector(d, -t, -start),
                Vector(d, t, -start),
                Vector(d, t, -(start + width)),
                Vector(d, -t, -(start + width))
            ]
            tip_wire = Part.makePolygon(tip_face_verts + [tip_face_verts[0]])
            
            solid_wedge = Part.makeLoft([post_wire, tip_wire], True, True)
            parts.append(solid_wedge)
        else:
            # Original hollow V behavior
            p_top = Part.makeBox(L_in, t, width)
            p_top.Placement.Base = Vector(base_x, 0.0, -(start + width))
            p_bot = Part.makeBox(L_in, t, width)
            p_bot.Placement.Base = Vector(base_x, -t, -(start + width))

            p_top = p_top.copy(); p_top.rotate(Vector(d, 0, -start), Vector(0, 0, 1), -alpha_deg)
            p_bot = p_bot.copy(); p_bot.rotate(Vector(d, 0, -start), Vector(0, 0, 1), +alpha_deg)

            parts.extend([p_top, p_bot])
        
        return parts, f"Wedge90 '{label}' (solid_v={solid_v})"

    # Angled wedge case
    theta_deg = abs(90.0 - angle_deg)
    theta_rad = math.radians(theta_deg)

    E_lead  = 2.0 * r
    E_trail = max(0.0, width * math.tan(theta_rad))

    L_total = length_out + E_lead + E_trail
    L_in = L_total
    R_eff = r_bot - t

    alpha_rad = math.atan2(R_eff, L_in)
    alpha_deg = math.degrees(alpha_rad)

    d = math.hypot(R_eff, L_in)
    base_x = d - L_in

    if solid_v:
        # Create single trapezoid following EXACT same geometry as hollow strips
        
        # Step 1: Create trapezoid with same length as strips (L_in)
        # Wide end at post: 2*r_bot (using r_bot like hollow case)
        # Narrow end at tip: 2*t
        # Starting at base_x, ending at d (same as strips)
        
        post_face_verts = [
            Vector(base_x, -r_bot, -start),
            Vector(base_x, r_bot, -start),
            Vector(base_x, r_bot, -(start + width)),
            Vector(base_x, -r_bot, -(start + width))
        ]
        post_wire = Part.makePolygon(post_face_verts + [post_face_verts[0]])
        
        tip_face_verts = [
            Vector(d, -t, -start),
            Vector(d, t, -start),
            Vector(d, t, -(start + width)),
            Vector(d, -t, -(start + width))
        ]
        tip_wire = Part.makePolygon(tip_face_verts + [tip_face_verts[0]])
        
        # Create loft between the faces
        solid_wedge = Part.makeLoft([post_wire, tip_wire], True, True)
        
        # Step 2: Apply same translation as hollow strips
        x_pivot_local = d - (length_out + E_trail)
        dx = r - x_pivot_local
        if abs(dx) > 1e-12:
            solid_wedge.translate(Vector(dx, 0.0, 0.0))
        
        # Step 3: Apply same tilt rotation as hollow strips
        tilt = 90.0 - angle_deg
        pivot = Vector(r, 0.0, -start)
        solid_wedge = solid_wedge.copy()
        solid_wedge.rotate(pivot, Vector(0, 1, 0), -tilt)
        
        # Step 4: Apply same tip cut as hollow strips
        x_cut = r + length_out * math.cos(theta_rad)
        bb = solid_wedge.BoundBox
        margin = max(10.0, 5.0 * max(1.0, r, length_out, width, t))
        
        trim = Part.makeBox(
            x_cut - (bb.XMin - margin),
            (bb.YMax + margin) - (bb.YMin - margin),
            (max(bb.ZMax, -start) + margin) - (min(bb.ZMin, -start - width) - margin)
        )
        trim.Placement.Base = Vector(bb.XMin - margin, bb.YMin - margin, min(bb.ZMin, -start - width) - margin)
        
        solid_wedge = solid_wedge.common(trim)
        
        parts.append(solid_wedge)
    else:
        # Original hollow V behavior
        p_top = Part.makeBox(L_in, t, width)
        p_top.Placement.Base = Vector(base_x, 0.0, -(start + width))
        p_bot = Part.makeBox(L_in, t, width)
        p_bot.Placement.Base = Vector(base_x, -t, -(start + width))

        p_top = p_top.copy(); p_top.rotate(Vector(d, 0, -start), Vector(0, 0, 1), -alpha_deg)
        p_bot = p_bot.copy(); p_bot.rotate(Vector(d, 0, -start), Vector(0, 0, 1), +alpha_deg)

        x_pivot_local = d - (length_out + E_trail)
        dx = r - x_pivot_local
        if abs(dx) > 1e-12:
            p_top.translate(Vector(dx, 0.0, 0.0))
            p_bot.translate(Vector(dx, 0.0, 0.0))

        tilt = 90.0 - angle_deg
        pivot = Vector(r, 0.0, -start)
        p_top = p_top.copy(); p_top.rotate(pivot, Vector(0, 1, 0), -tilt)
        p_bot = p_bot.copy(); p_bot.rotate(pivot, Vector(0, 1, 0), -tilt)

        # Tip cut
        x_cut = r + length_out * math.cos(theta_rad)
        bb = p_top.BoundBox; bb.add(p_bot.BoundBox)
        margin = max(10.0, 5.0 * max(1.0, r, length_out, width, t))

        trim = Part.makeBox(
            x_cut - (bb.XMin - margin),
            (bb.YMax + margin) - (bb.YMin - margin),
            (max(bb.ZMax, -start) + margin) - (min(bb.ZMin, -start - width) - margin)
        )
        trim.Placement.Base = Vector(bb.XMin - margin, bb.YMin - margin, min(bb.ZMin, -start - width) - margin)

        p_top = p_top.common(trim)
        p_bot = p_bot.common(trim)

        parts.extend([p_top, p_bot])

    return parts, f"WedgeAngled-TipCut '{label}' (solid_v={solid_v})"