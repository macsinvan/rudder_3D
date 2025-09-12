# stock/wedge_angled.py

import math
import Part
from FreeCAD import Vector

def build_wedge(row_dict, radius_at_func, solid_v=False):
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
            
            if solid_wedge.isNull():
                raise RuntimeError(
                    f"Failed to create 90° solid wedge '{label}' at start={start}mm. "
                    f"Loft operation produced null shape. "
                    f"Geometry: base_x={base_x:.2f}, d={d:.2f}, r={r:.2f}, t={t:.2f}"
                )
            
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
        
        if solid_wedge.isNull():
            raise RuntimeError(
                f"Failed to create angled solid wedge '{label}' at start={start}mm. "
                f"Initial loft operation produced null shape. "
                f"Geometry: base_x={base_x:.2f}, d={d:.2f}, r_bot={r_bot:.2f}, t={t:.2f}"
            )
        
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
        
        # Store original bounds for error reporting
        original_bounds = str(bb)
        solid_wedge = solid_wedge.common(trim)
        
        if solid_wedge.isNull():
            raise RuntimeError(
                f"Wedge '{label}' at start={start}mm became NULL after tip cut!\n"
                f"  Angle: {angle_deg}°, Position: {start}mm down post\n"
                f"  Radii: r={r:.2f}mm, r_bot={r_bot:.2f}mm\n"
                f"  Cut position: x_cut={x_cut:.2f}mm\n"
                f"  Base positions: base_x={base_x:.2f}mm, d={d:.2f}mm\n"
                f"  Original wedge bounds: {original_bounds}\n"
                f"  Trim box: X[{bb.XMin - margin:.2f}, {x_cut:.2f}]\n"
                f"  This typically means the trim box doesn't intersect the wedge properly."
            )
        
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

        original_bounds = str(bb)
        p_top = p_top.common(trim)
        p_bot = p_bot.common(trim)
        
        if p_top.isNull() or p_bot.isNull():
            null_parts = []
            if p_top.isNull():
                null_parts.append("top")
            if p_bot.isNull():
                null_parts.append("bottom")
            
            raise RuntimeError(
                f"Wedge '{label}' at start={start}mm: {', '.join(null_parts)} plate(s) became NULL after tip cut!\n"
                f"  Angle: {angle_deg}°\n"
                f"  Radii: r={r:.2f}mm, r_bot={r_bot:.2f}mm\n"
                f"  Cut position: x_cut={x_cut:.2f}mm\n"
                f"  Original bounds: {original_bounds}\n"
                f"  This typically means the trim box doesn't intersect the plates properly."
            )

        parts.extend([p_top, p_bot])

    return parts, f"WedgeAngled-TipCut '{label}' (solid_v={solid_v})"