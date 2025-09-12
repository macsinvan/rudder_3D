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
                    f"Loft operation produced null shape."
                )
            
            parts.append(solid_wedge)
            
            # Add support plates for cutout (solid_v=True)
            plate_x = 100.0  # mm
            plate_y = 150.0  # mm
            plate_z = 5.0    # mm
            
            # Calculate midpoint of wedge
            midpoint_x = (base_x + d) / 2.0
            midpoint_y = 0.0  # Centered on Y
            
            # Create top plate (above wedge)
            top_plate = Part.makeBox(plate_x, plate_y, plate_z)
            # Position at midpoint, centered, touching top of wedge
            top_plate.Placement.Base = Vector(
                midpoint_x - plate_x/2,
                -plate_y/2,
                -start  # Top of wedge
            )
            parts.append(top_plate)
            
            # Create bottom plate (below wedge)
            bottom_plate = Part.makeBox(plate_x, plate_y, plate_z)
            # Position at midpoint, centered, touching bottom of wedge
            bottom_plate.Placement.Base = Vector(
                midpoint_x - plate_x/2,
                -plate_y/2,
                -(start + width + plate_z)  # Below wedge
            )
            parts.append(bottom_plate)
            
            print(f"    Added support plates at X={midpoint_x:.1f} for 90° wedge")
            
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
                f"Initial loft operation produced null shape."
            )
        
        # Calculate midpoint BEFORE transformations
        midpoint_x = (base_x + d) / 2.0
        midpoint_y = 0.0
        midpoint_z = -(start + width/2.0)  # Center of wedge height
        
        # Step 2: Apply same translation as hollow strips
        x_pivot_local = d - (length_out + E_trail)
        dx = r - x_pivot_local
        if abs(dx) > 1e-12:
            solid_wedge.translate(Vector(dx, 0.0, 0.0))
            midpoint_x += dx  # Update midpoint
        
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
                f"Wedge '{label}' at start={start}mm became NULL after tip cut!"
            )
        
        parts.append(solid_wedge)
        
        # Add support plates for angled cutout
        plate_x = 100.0  # mm
        plate_y = 150.0  # mm
        plate_z = 5.0    # mm
        
        # Calculate actual midpoint after transformations
        # Use the wedge's bounding box to find its actual center
        wedge_center_x = (bb.XMin + bb.XMax) / 2.0
        wedge_center_y = (bb.YMin + bb.YMax) / 2.0
        
        # Create top plate
        top_plate = Part.makeBox(plate_x, plate_y, plate_z)
        # Center the plate at wedge midpoint
        top_plate.Placement.Base = Vector(
            wedge_center_x - plate_x/2,
            wedge_center_y - plate_y/2,
            -start  # Top of wedge
        )
        
        # Apply the same rotations as the wedge
        # First rotate for the V-angle (around Z axis)
        if angle_deg < 90:
            top_plate.rotate(Vector(wedge_center_x, wedge_center_y, -start), 
                           Vector(0, 0, 1), -alpha_deg)
        else:
            top_plate.rotate(Vector(wedge_center_x, wedge_center_y, -start), 
                           Vector(0, 0, 1), alpha_deg)
        
        # Then apply the tilt rotation (around Y axis)
        top_plate.rotate(pivot, Vector(0, 1, 0), -tilt)
        
        # Apply same cut as wedge
        top_plate = top_plate.common(trim)
        if not top_plate.isNull():
            parts.append(top_plate)
            
        # Create bottom plate
        bottom_plate = Part.makeBox(plate_x, plate_y, plate_z)
        bottom_plate.Placement.Base = Vector(
            wedge_center_x - plate_x/2,
            wedge_center_y - plate_y/2,
            -(start + width + plate_z)  # Below wedge
        )
        
        # Apply same rotations
        if angle_deg < 90:
            bottom_plate.rotate(Vector(wedge_center_x, wedge_center_y, -(start + width + plate_z)), 
                              Vector(0, 0, 1), -alpha_deg)
        else:
            bottom_plate.rotate(Vector(wedge_center_x, wedge_center_y, -(start + width + plate_z)), 
                              Vector(0, 0, 1), alpha_deg)
        
        bottom_plate.rotate(pivot, Vector(0, 1, 0), -tilt)
        
        # Apply same cut
        bottom_plate = bottom_plate.common(trim)
        if not bottom_plate.isNull():
            parts.append(bottom_plate)
            
        print(f"    Added support plates at X={wedge_center_x:.1f}, Y={wedge_center_y:.1f} for {angle_deg}° wedge")
        
    else:
        # Original hollow V behavior (no plates for stock)
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