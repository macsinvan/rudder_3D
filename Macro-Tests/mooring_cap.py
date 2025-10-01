"""
FreeCAD Script: Cap - CORRECTED VERSION
All cutout cones visible, ridges protruding inward, correct taper direction
"""

import FreeCAD as App
import Part
import math

# ============================================================================
# PARAMETERS
# ============================================================================

# Primary design parameters
LINE_DIA = 12.0                    # Line diameter (mm)
SPHERE_RATIO = 2.5                 # Sphere = 2.5 × Line diameter
TAPER_ANGLE = 3.5                  # Taper angle in degrees
GAP_WIDTH = 2.0                    # Gap width for compression (mm)
WALL_THICKNESS = 3.0               # Ring wall thickness (mm)

# Ridge parameters
RIDGE_HEIGHT = 1.0                 # Ridge protrusion height inward (mm)
RIDGE_SPACING = 3.0                # Ridge spacing along Z (mm)
RIDGE_WIDTH = 1.0                  # Base width of ridge (mm)

# Calculated dimensions
SPHERE_OUTER_DIA = LINE_DIA * SPHERE_RATIO      # 30.0mm
FERRULE_LENGTH = SPHERE_OUTER_DIA / 2.0         # 15.0mm
HOLE_DIA = LINE_DIA + 0.5                       # 12.5mm

# Taper calculation
taper_rad = math.radians(TAPER_ANGLE)
radius_increase_bottom = FERRULE_LENGTH * math.tan(taper_rad)  # For bottom cone
radius_decrease_top = FERRULE_LENGTH * math.tan(taper_rad)     # For top cone (narrows)

# Ring dimensions
RING_NARROW_DIA = LINE_DIA + (2 * WALL_THICKNESS)                    # 18.0mm at Z=0
RING_WIDE_DIA = RING_NARROW_DIA + (2 * radius_increase_bottom)      # ~19.83mm at bottom

# Top cutout narrows from Z=0 upward
TOP_CUTOUT_NARROW_DIA = RING_NARROW_DIA - (2 * radius_decrease_top)  # ~16.17mm at apex

# Visualization
LINE_LENGTH = 100.0

# ============================================================================
# CREATE COMPONENTS
# ============================================================================

def create_line():
    """Create the mooring line as a cylinder"""
    print(f"Creating line: {LINE_DIA}mm diameter")
    
    doc = App.ActiveDocument
    if not doc:
        doc = App.newDocument("CapCorrected")
    
    line_start = App.Vector(0, 0, -LINE_LENGTH/2)
    line_direction = App.Vector(0, 0, 1)
    
    line_cylinder = Part.makeCylinder(
        LINE_DIA / 2.0,
        LINE_LENGTH,
        line_start,
        line_direction
    )
    
    line_obj = doc.addObject("Part::Feature", "Line")
    line_obj.Shape = line_cylinder
    line_obj.ViewObject.ShapeColor = (0.6, 0.4, 0.2)
    
    return line_obj


def create_sphere_with_cutouts():
    """Create sphere with visible cutout cones"""
    print(f"Creating sphere: {SPHERE_OUTER_DIA:.1f}mm diameter")
    
    doc = App.ActiveDocument
    
    # Solid sphere
    solid_sphere = Part.makeSphere(SPHERE_OUTER_DIA / 2.0)
    
    # TOP HOLE - small straight cylinder above apex
    top_hole = Part.makeCylinder(
        HOLE_DIA / 2.0,
        10,  # Short cylinder above apex
        App.Vector(0, 0, FERRULE_LENGTH),
        App.Vector(0, 0, 1)
    )
    
    # BOTTOM CONE CUTOUT - widens going down (Z=0 to Z=-15mm)
    bottom_cone_cutout = Part.makeCone(
        RING_NARROW_DIA / 2.0,   # Narrow at Z=0 (9.0mm radius)
        RING_WIDE_DIA / 2.0,     # Wide at bottom (9.915mm radius)
        FERRULE_LENGTH,
        App.Vector(0, 0, 0),
        App.Vector(0, 0, -1)
    )
    
    # Make bottom cone visible
    bottom_cone_obj = doc.addObject("Part::Feature", "BottomCone_Cutter")
    bottom_cone_obj.Shape = bottom_cone_cutout
    bottom_cone_obj.ViewObject.ShapeColor = (0.0, 1.0, 0.0)  # Green
    bottom_cone_obj.ViewObject.Transparency = 60
    
    # TOP CONE CUTOUT - NARROWS going up (Z=0 to Z=+15mm) - FIXED!
    top_cone_cutout = Part.makeCone(
        TOP_CUTOUT_NARROW_DIA / 2.0,  # Narrow at apex (~8.085mm radius) 
        RING_NARROW_DIA / 2.0,        # Wide at Z=0 (9.0mm radius)
        FERRULE_LENGTH,
        App.Vector(0, 0, FERRULE_LENGTH),  # Start at apex
        App.Vector(0, 0, -1)               # Point downward (narrows upward)
    )
    
    # Make top cone visible
    top_cone_obj = doc.addObject("Part::Feature", "TopCone_Cutter")
    top_cone_obj.Shape = top_cone_cutout
    top_cone_obj.ViewObject.ShapeColor = (0.0, 0.0, 1.0)  # Blue
    top_cone_obj.ViewObject.Transparency = 60
    
    # Cut sphere
    sphere_cut = solid_sphere.cut(top_hole).cut(bottom_cone_cutout).cut(top_cone_cutout)
    
    sphere_obj = doc.addObject("Part::Feature", "Sphere")
    sphere_obj.Shape = sphere_cut
    sphere_obj.ViewObject.ShapeColor = (0.8, 0.2, 0.2)
    sphere_obj.ViewObject.Transparency = 30
    
    print(f"  Diameter: {SPHERE_OUTER_DIA:.1f}mm")
    print(f"  Bottom cone: {RING_NARROW_DIA:.2f}mm → {RING_WIDE_DIA:.2f}mm (widens down)")
    print(f"  Top cone: {RING_NARROW_DIA:.2f}mm → {TOP_CUTOUT_NARROW_DIA:.2f}mm (narrows up)")
    print(f"  Cutout cones are VISIBLE (green=bottom, blue=top)")
    
    return sphere_obj, bottom_cone_obj, top_cone_obj


def create_ridge_ring(z_position):
    """Create a single ridge ring protruding INWARD"""
    
    outer_radius = LINE_DIA / 2.0
    inner_radius = outer_radius - RIDGE_HEIGHT
    
    # Triangle pointing inward
    base_top = App.Vector(outer_radius, 0, z_position + RIDGE_WIDTH/2)
    peak = App.Vector(inner_radius, 0, z_position)
    base_bottom = App.Vector(outer_radius, 0, z_position - RIDGE_WIDTH/2)
    
    edge1 = Part.LineSegment(base_top, peak).toShape()
    edge2 = Part.LineSegment(peak, base_bottom).toShape()
    edge3 = Part.LineSegment(base_bottom, base_top).toShape()
    
    wire = Part.Wire([edge1, edge2, edge3])
    face = Part.Face(wire)
    
    ridge_ring = face.revolve(
        App.Vector(0, 0, 0),
        App.Vector(0, 0, 1),
        360
    )
    
    return ridge_ring


def create_compression_ring_with_ridges():
    """Create compression ring with inward ridges"""
    print(f"Creating compression ring with ridges")
    
    doc = App.ActiveDocument
    
    # Outer tapered shell
    ring_cone = Part.makeCone(
        RING_NARROW_DIA / 2.0,
        RING_WIDE_DIA / 2.0,
        FERRULE_LENGTH,
        App.Vector(0, 0, 0),
        App.Vector(0, 0, -1)
    )
    
    # Hollow with line hole
    line_hole = Part.makeCylinder(
        LINE_DIA / 2.0,
        FERRULE_LENGTH + 2,
        App.Vector(0, 0, 1),
        App.Vector(0, 0, -1)
    )
    
    hollow_ring = ring_cone.cut(line_hole)
    
    # ADD RIDGES
    num_ridges = int(FERRULE_LENGTH / RIDGE_SPACING)
    print(f"  Adding {num_ridges} ridges ({RIDGE_HEIGHT}mm inward)...")
    
    ridges_combined = None
    for i in range(num_ridges):
        z_pos = -i * RIDGE_SPACING - RIDGE_SPACING/2
        if z_pos > -FERRULE_LENGTH:  # Keep within ring bounds
            ridge = create_ridge_ring(z_pos)
            if ridges_combined is None:
                ridges_combined = ridge
            else:
                ridges_combined = ridges_combined.fuse(ridge)
    
    # Fuse ridges to ring
    if ridges_combined:
        ring_with_ridges = hollow_ring.fuse(ridges_combined)
    else:
        ring_with_ridges = hollow_ring
    
    # CREATE SPLIT with 2mm plate
    plate_size = RING_WIDE_DIA + 10
    
    cutting_plate = Part.makeBox(
        plate_size,
        GAP_WIDTH,
        FERRULE_LENGTH + 2
    )
    
    cutting_plate.translate(App.Vector(
        -plate_size/2,
        -GAP_WIDTH/2,
        -FERRULE_LENGTH - 1
    ))
    
    # Make plate visible
    plate_obj = doc.addObject("Part::Feature", "SplitPlate_Cutter")
    plate_obj.Shape = cutting_plate
    plate_obj.ViewObject.ShapeColor = (1.0, 1.0, 0.0)  # Yellow
    plate_obj.ViewObject.Transparency = 60
    
    # Cut gap
    split_ring = ring_with_ridges.cut(cutting_plate)
    
    ring_obj = doc.addObject("Part::Feature", "CompressionRing")
    ring_obj.Shape = split_ring
    ring_obj.ViewObject.ShapeColor = (0.9, 0.9, 0.9)  # Light gray
    ring_obj.ViewObject.Transparency = 20
    
    print(f"  Ridges fused to ring, {GAP_WIDTH}mm split applied")
    
    return ring_obj, plate_obj


# ============================================================================
# MAIN
# ============================================================================

def main():
    print("=" * 70)
    print("CAP - CORRECTED: Proper Taper, Visible Cutters, Ridges")
    print("=" * 70)
    print(f"\nParameters:")
    print(f"  Sphere: {SPHERE_OUTER_DIA:.1f}mm ({SPHERE_RATIO}× line)")
    print(f"  Ring wall: {WALL_THICKNESS}mm")
    print(f"  Ridge height: {RIDGE_HEIGHT}mm inward")
    print(f"  Gap: {GAP_WIDTH}mm")
    print()
    
    line = create_line()
    sphere, bottom_cone, top_cone = create_sphere_with_cutouts()
    ring, plate = create_compression_ring_with_ridges()
    
    print("\nComponents:")
    print("  1. Line (brown)")
    print("  2. Sphere (red) - with cutouts")
    print("  3. BottomCone_Cutter (green) - VISIBLE")
    print("  4. TopCone_Cutter (blue) - VISIBLE, narrows upward")
    print("  5. CompressionRing (light gray) - with inward ridges")
    print("  6. SplitPlate_Cutter (yellow) - VISIBLE")
    print()
    
    App.ActiveDocument.recompute()
    if App.GuiUp:
        import FreeCADGui
        FreeCADGui.SendMsgToActiveView("ViewFit")


if __name__ == '__main__':
    main()