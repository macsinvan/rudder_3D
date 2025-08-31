# stock/wedge.py

import math
import Part
from FreeCAD import Vector
from stock.plate import compute_plate_angles


def build_wedge(row_dict, radius_at_func, solid_v=False):
    """
    Build a 'wedge' tine as two steel strips OR a solid wedge.
    
    Args:
        row_dict: Dictionary with wedge parameters
        radius_at_func: Function to get radius at a given Z position
        solid_v: If True, create a solid wedge. If False, create two strips (hollow V)
                Defaults to True for testing
    
    Returns:
        parts: List of Part objects
        summary: String description of what was built
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
    
    # Helper function to create a strip - either rectangular (hollow) or with angled inner face (filled)
    def create_strip(length, thickness, height, for_solid_v=False, is_top=True, alpha_deg=0):
        """
        Create a strip for the V-wedge.
        
        Args:
            length: Length of the strip (L_in)
            thickness: Thickness of the strip (t)
            height: Height of the strip in Z (width)
            for_solid_v: If True, create a strip with angled inner face for filled V
            is_top: True for top strip, False for bottom strip
            alpha_deg: Half-angle of the V
        
        Returns:
            Part object (strip shape)
        """
        if not for_solid_v:
            # Original rectangular strip
            return Part.makeBox(length, thickness, height)
        else:
            # For filled V: create a strip that fills the gap
            # Simple approach: just make each strip thicker on the inner side
            
            if is_top:
                # Top strip - standard thickness on outside, extends inward at post
                # Create as a simple tapered box
                strip = Part.makeBox(length, thickness * 2, height)
                # This creates a box that's too thick, we'll rely on rotation and positioning
            else:
                # Bottom strip - mirror
                strip = Part.makeBox(length, thickness * 2, height)
            
            return strip

    if abs(angle_deg - 90.0) < 1e-9:
        # ---- Inside-edge tangent geometry using INSIDE edge length (L_in) ----
        # Effective radius at the inside edge: R_eff = R - t  (Option B)
        L_in = length_out
        R_eff = r - t
        if L_in <= 0 or R_eff <= 0:
            raise ValueError(f"invalid inside geometry: L_in={L_in}, R_eff={R_eff} (r={r}, t={t})")

        alpha_rad = math.atan2(R_eff, L_in)
        alpha_deg = math.degrees(alpha_rad)

        # External tip point distance from center for inside-edge tangent
        d = math.hypot(R_eff, L_in)  # sqrt(R_eff^2 + L_in^2)
        base_x = d - L_in

        if solid_v:
            # Create ONE trapezoid for the filled V
            # Wide end at post: 2*r (diameter of cylinder)
            # Narrow end at tip: 2*t (combined thickness of two strips)
            # Length: L_in
            # Height: width (Z dimension)
            
            # Create the trapezoid as a loft between two rectangular faces
            # Face at post (wide end)
            post_face_verts = [
                Vector(base_x, -r, -start),
                Vector(base_x, r, -start),
                Vector(base_x, r, -(start + width)),
                Vector(base_x, -r, -(start + width))
            ]
            post_wire = Part.makePolygon(post_face_verts + [post_face_verts[0]])
            
            # Face at tip (narrow end)
            tip_face_verts = [
                Vector(d, -t, -start),
                Vector(d, t, -start),
                Vector(d, t, -(start + width)),
                Vector(d, -t, -(start + width))
            ]
            tip_wire = Part.makePolygon(tip_face_verts + [tip_face_verts[0]])
            
            # Create loft between the two faces
            solid_wedge = Part.makeLoft([post_wire, tip_wire], True, True)
            parts.append(solid_wedge)
            
            summary = (
                f"WedgeSolid90 '{label}' start={start} w={width} L_in={L_in} "
                f"t={t} r_at={r:.2f} (FILLED V - single trapezoid)"
            )
            print(
                f"  ✓ WedgeSolid90: label='{label}', r={r:.2f}, t={t}, L_in={L_in}, "
                f"(FILLED V - single trapezoid)"
            )
        else:
            # Original behavior: create two rectangular strips
            p_top = Part.makeBox(L_in, t, width)
            p_top.Placement.Base = Vector(base_x, 0.0, -(start + width))
            tip_pivot_top = Vector(d, 0.0, -start)

            p_bot = Part.makeBox(L_in, t, width)
            p_bot.Placement.Base = Vector(base_x, -t, -(start + width))
            tip_pivot_bot = Vector(d, 0.0, -start)

            # Rotate about Z so the V opens in plan view
            p_top = p_top.copy()
            p_top.rotate(tip_pivot_top, Vector(0, 0, 1), -alpha_deg)

            p_bot = p_bot.copy()
            p_bot.rotate(tip_pivot_bot, Vector(0, 0, 1), +alpha_deg)

            parts.extend([p_top, p_bot])  # Two separate strips
        
        if solid_v:
            summary = (
                f"WedgeSolid90 '{label}' start={start} w={width} L_in={L_in} "
                f"t={t} r_at={r:.2f} R_eff={R_eff:.2f} alpha={alpha_deg:.3f}° tip_x={d:.3f} (FILLED V)"
            )
            print(
                f"  ✓ WedgeSolid90: label='{label}', r={r:.2f}, t={t}, L_in={L_in}, "
                f"R_eff={R_eff:.2f}, alpha={alpha_deg:.3f}°, tip_x={d:.3f} (FILLED V)"
            )
            
            summary = (
                f"WedgeSolid90 '{label}' start={start} w={width} L_in={L_in} "
                f"t={t} r_at={r:.2f} R_eff={R_eff:.2f} alpha={alpha_deg:.3f}° tip_x={d:.3f} (SOLID V)"
            )
            print(
                f"  ✓ WedgeSolid90: label='{label}', r={r:.2f}, t={t}, L_in={L_in}, "
                f"R_eff={R_eff:.2f}, alpha={alpha_deg:.3f}°, tip_x={d:.3f} (SOLID V)"
            )
            
        else:
            # ---- Original behavior: two separate strips (hollow V) ----
            # Place both strips so their INSIDE edges lie on y = 0 and meet at the same tip (y = 0)
            # Top strip spans y ∈ [0, t]; bottom strip spans y ∈ [-t, 0]
            p_top = Part.makeBox(L_in, t, width)
            p_top.Placement.Base = Vector(base_x, 0.0, -(start + width))
            tip_pivot_top = Vector(d, 0.0, -start)

            p_bot = Part.makeBox(L_in, t, width)
            p_bot.Placement.Base = Vector(base_x, -t, -(start + width))
            tip_pivot_bot = Vector(d, 0.0, -start)

            # Rotate about Z so the V opens in plan view; inside edges share the same tip
            p_top = p_top.copy()
            p_top.rotate(tip_pivot_top, Vector(0, 0, 1), -alpha_deg)

            p_bot = p_bot.copy()
            p_bot.rotate(tip_pivot_bot, Vector(0, 0, 1), +alpha_deg)

            parts.extend([p_top, p_bot])  # no strap in the 90° case

            summary = (
                f"Wedge90 '{label}' start={start} w={width} L_in={L_in} "
                f"t={t} r_at={r:.2f} R_eff={R_eff:.2f} alpha={alpha_deg:.3f}° tip_x={d:.3f} (inside tangent, y=0 meet)"
            )
            print(
                f"  ✓ Wedge90: label='{label}', r={r:.2f}, t={t}, L_in={L_in}, "
                f"R_eff={R_eff:.2f}, alpha={alpha_deg:.3f}°, tip_x={d:.3f} (inside tangent, y=0 meet)"
            )
        
        return parts, summary

    # ----- Angled (≠ 90°): existing behavior with Y-rotation, trim, and small strap -----
    # For angled wedges, we keep the original behavior for now
    # Could be extended with solid_v support if needed
    
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