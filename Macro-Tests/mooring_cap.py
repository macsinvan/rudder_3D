"""
FreeCAD Script: Cap - Corrected Ring Dimensions and Position
Ring sized to fit cutout with proper clearance
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

# Ridge parameters (inward ridges on interior)
RIDGE_HEIGHT = 0.5                 # Ridge protrusion height inward (mm)
RIDGE_SPACING = 3.0                # Ridge spacing along Z (mm)
RIDGE_WIDTH = 0.5                  # Base width of ridge (mm)

# Ratchet parameters (outward teeth on exterior)
RATCHET_TOOTH_HEIGHT = 0.5        # Tooth protrusion outward (mm)
RATCHET_TOOTH_SPACING = 2        # Distance between teeth (mm)
RATCHET_TOOTH_WIDTH = 0.5          # Width of tooth (mm)

# Clearance for ring to fit in sphere
CUTOUT_CLEARANCE = 1.0             # Clearance around ring+teeth (mm)

# Calculated dimensions
SPHERE_OUTER_DIA = LINE_DIA * SPHERE_RATIO      # 30.0mm
SPHERE_RADIUS = SPHERE_OUTER_DIA / 2.0          # 15.0mm

# Ring dimensions - calculate FIRST
FERRULE_LENGTH = SPHERE_RADIUS  # 15mm ring length
taper_rad = math.radians(TAPER_ANGLE)
radius_increase = FERRULE_LENGTH * math.tan(taper_rad)

RING_INNER_DIA = LINE_DIA
RING_HEAD_OUTER_DIA = RING_INNER_DIA + (2 * WALL_THICKNESS)      # 18mm
RING_BASE_OUTER_DIA = RING_HEAD_OUTER_DIA + (2 * radius_increase) # 19.83mm

# Ring WITH teeth
RING_HEAD_WITH_TEETH = RING_HEAD_OUTER_DIA + (2 * RATCHET_TOOTH_HEIGHT)  # 19.5mm
RING_BASE_WITH_TEETH = RING_BASE_OUTER_DIA + (2 * RATCHET_TOOTH_HEIGHT)

# Calculate cutout based on ring dimensions
# Z_exit: where line cylinder intersects sphere (top)
Z_EXIT = math.sqrt(SPHERE_RADIUS**2 - (LINE_DIA/2.0)**2)  # +13.75mm
diameter_at_exit = LINE_DIA  # 12mm

# Z_entry: where cutout must fit ring HEAD with teeth + clearance
ENTRY_DIA = RING_HEAD_WITH_TEETH + CUTOUT_CLEARANCE  # 20.5mm
Z_ENTRY = -math.sqrt(SPHERE_RADIUS**2 - (ENTRY_DIA/2.0)**2)  # -10.95mm
diameter_at_entry = ENTRY_DIA

# Z_sphere_bottom
Z_SPHERE_BOTTOM = -SPHERE_RADIUS  # -15mm

# Calculate diameter at sphere bottom using linear interpolation
radius_at_exit = diameter_at_exit / 2.0  # 6mm
radius_at_entry = diameter_at_entry / 2.0  # 10.25mm
radius_at_sphere_bottom = radius_at_exit + (radius_at_entry - radius_at_exit) * (Z_SPHERE_BOTTOM - Z_EXIT) / (Z_ENTRY - Z_EXIT)
Z_SPHERE_ENTRY_DIAMETER = 2 * radius_at_sphere_bottom  # 21.89mm

# Cone cutout dimensions
CONE_HEIGHT = Z_EXIT - Z_SPHERE_BOTTOM  # 28.75mm

# Ring HEAD position
RING_HEAD_Z = Z_ENTRY  # -10.95mm
RING_BASE_Z = RING_HEAD_Z - FERRULE_LENGTH  # -25.95mm

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


def create_ratchet_tooth_ring(z_position, outer_radius):
    """Create a single ratchet tooth ring protruding OUTWARD"""
    
    peak_offset = RATCHET_TOOTH_WIDTH * 0.7
    
    base_top = App.Vector(outer_radius, 0, z_position)
    peak = App.Vector(outer_radius + RATCHET_TOOTH_HEIGHT, 0, z_position - peak_offset)
    base_bottom = App.Vector(outer_radius, 0, z_position - RATCHET_TOOTH_WIDTH)
    
    edge1 = Part.LineSegment(base_top, peak).toShape()
    edge2 = Part.LineSegment(peak, base_bottom).toShape()
    edge3 = Part.LineSegment(base_bottom, base_top).toShape()
    
    wire = Part.Wire([edge1, edge2, edge3])
    face = Part.Face(wire)
    
    tooth_ring = face.revolve(
        App.Vector(0, 0, 0),
        App.Vector(0, 0, 1),
        360
    )
    
    return tooth_ring


def create_sphere_with_cone():
    """Create sphere with cone cutout sized for ring"""
    print(f"Creating sphere: {SPHERE_OUTER_DIA:.1f}mm diameter")
    print(f"  Cutout sized for ring:")
    print(f"    Ring HEAD with teeth: {RING_HEAD_WITH_TEETH:.1f}mm")
    print(f"    Cutout at entry (with clearance): {diameter_at_entry:.1f}mm")
    print(f"  Z_exit: {Z_EXIT:.2f}mm, diameter: {diameter_at_exit}mm")
    print(f"  Z_entry: {Z_ENTRY:.2f}mm, diameter: {diameter_at_entry:.1f}mm")
    print(f"  Z_sphere_bottom: {Z_SPHERE_BOTTOM:.2f}mm, diameter: {Z_SPHERE_ENTRY_DIAMETER:.2f}mm")
    
    doc = App.ActiveDocument
    
    # Solid sphere
    solid_sphere = Part.makeSphere(SPHERE_RADIUS)
    
    # TOP HOLE
    top_hole = Part.makeCylinder(
        LINE_DIA / 2.0,
        SPHERE_RADIUS - Z_EXIT + 5,
        App.Vector(0, 0, Z_EXIT),
        App.Vector(0, 0, 1)
    )
    
    # CONE CUTOUT - sized to fit ring
    cone_cutout = Part.makeCone(
        diameter_at_exit / 2.0,
        Z_SPHERE_ENTRY_DIAMETER / 2.0,
        CONE_HEIGHT,
        App.Vector(0, 0, Z_EXIT),
        App.Vector(0, 0, -1)
    )
    
    # ADD RATCHET GROOVES
    print(f"  Adding ratchet grooves...")
    num_teeth = int(CONE_HEIGHT / RATCHET_TOOTH_SPACING)
    
    ratchet_grooves = None
    for i in range(num_teeth):
        z_pos = Z_EXIT - (i * RATCHET_TOOTH_SPACING) - RATCHET_TOOTH_WIDTH/2
        
        if z_pos > Z_SPHERE_BOTTOM:
            t = (Z_EXIT - z_pos) / CONE_HEIGHT
            cutout_radius = radius_at_exit + t * (radius_at_sphere_bottom - radius_at_exit)
            
            groove = create_ratchet_tooth_ring(z_pos, cutout_radius)
            
            if ratchet_grooves is None:
                ratchet_grooves = groove
            else:
                ratchet_grooves = ratchet_grooves.fuse(groove)
    
    if ratchet_grooves:
        cone_cutout = cone_cutout.fuse(ratchet_grooves)
    
    # Make cone visible
    cone_obj = doc.addObject("Part::Feature", "Cone_Cutter")
    cone_obj.Shape = cone_cutout
    cone_obj.ViewObject.ShapeColor = (0.0, 1.0, 0.0)
    cone_obj.ViewObject.Transparency = 60
    
    # Cut sphere
    sphere_cut = solid_sphere.cut(top_hole).cut(cone_cutout)
    
    sphere_obj = doc.addObject("Part::Feature", "Sphere")
    sphere_obj.Shape = sphere_cut
    sphere_obj.ViewObject.ShapeColor = (0.8, 0.2, 0.2)
    sphere_obj.ViewObject.Transparency = 30
    
    return sphere_obj, cone_obj


def create_ridge_ring(z_position):
    """Create a single ridge ring protruding INWARD"""
    
    outer_radius = RING_INNER_DIA / 2.0
    inner_radius = outer_radius - RIDGE_HEIGHT
    
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
    """Create compression ring - properly sized and positioned"""
    print(f"Creating compression ring")
    print(f"  HEAD: {RING_HEAD_OUTER_DIA}mm outer, {RING_HEAD_WITH_TEETH:.1f}mm with teeth")
    print(f"  BASE: {RING_BASE_OUTER_DIA:.2f}mm outer, {RING_BASE_WITH_TEETH:.2f}mm with teeth")
    print(f"  Position: HEAD at Z={RING_HEAD_Z:.2f}mm, BASE at Z={RING_BASE_Z:.2f}mm")
    
    doc = App.ActiveDocument
    
    # CREATE RING at Z_ENTRY position
    ring_cone = Part.makeCone(
        RING_HEAD_OUTER_DIA / 2.0,
        RING_BASE_OUTER_DIA / 2.0,
        FERRULE_LENGTH,
        App.Vector(0, 0, RING_HEAD_Z),
        App.Vector(0, 0, -1)
    )
    
    # Hollow with line hole
    line_hole = Part.makeCylinder(
        RING_INNER_DIA / 2.0,
        FERRULE_LENGTH + 2,
        App.Vector(0, 0, RING_HEAD_Z + 1),
        App.Vector(0, 0, -1)
    )
    
    hollow_ring = ring_cone.cut(line_hole)
    
    # ADD INWARD RIDGES
    num_ridges = int(FERRULE_LENGTH / RIDGE_SPACING)
    
    ridges_combined = None
    for i in range(num_ridges):
        z_pos = RING_HEAD_Z - (i * RIDGE_SPACING) - RIDGE_SPACING/2
        if z_pos > RING_BASE_Z:
            ridge = create_ridge_ring(z_pos)
            if ridges_combined is None:
                ridges_combined = ridge
            else:
                ridges_combined = ridges_combined.fuse(ridge)
    
    if ridges_combined:
        ring_with_ridges = hollow_ring.fuse(ridges_combined)
    else:
        ring_with_ridges = hollow_ring
    
    # ADD OUTWARD RATCHET TEETH
    num_teeth = int(FERRULE_LENGTH / RATCHET_TOOTH_SPACING)
    
    ratchet_teeth = None
    for i in range(num_teeth):
        z_pos = RING_HEAD_Z - (i * RATCHET_TOOTH_SPACING) - RATCHET_TOOTH_WIDTH/2
        if z_pos > RING_BASE_Z:
            t = abs(z_pos - RING_HEAD_Z) / FERRULE_LENGTH
            ring_radius = (RING_HEAD_OUTER_DIA/2.0) + t * (RING_BASE_OUTER_DIA/2.0 - RING_HEAD_OUTER_DIA/2.0)
            
            tooth = create_ratchet_tooth_ring(z_pos, ring_radius)
            
            if ratchet_teeth is None:
                ratchet_teeth = tooth
            else:
                ratchet_teeth = ratchet_teeth.fuse(tooth)
    
    if ratchet_teeth:
        ring_complete = ring_with_ridges.fuse(ratchet_teeth)
    else:
        ring_complete = ring_with_ridges
    
    # CREATE SPLIT
    plate_size = RING_BASE_WITH_TEETH + 10
    
    cutting_plate = Part.makeBox(
        plate_size,
        GAP_WIDTH,
        FERRULE_LENGTH + 2
    )
    
    cutting_plate.translate(App.Vector(
        -plate_size/2,
        -GAP_WIDTH/2,
        RING_HEAD_Z - FERRULE_LENGTH - 1
    ))
    
    plate_obj = doc.addObject("Part::Feature", "SplitPlate_Cutter")
    plate_obj.Shape = cutting_plate
    plate_obj.ViewObject.ShapeColor = (1.0, 1.0, 0.0)
    plate_obj.ViewObject.Transparency = 60
    
    # Cut gap
    split_ring = ring_complete.cut(cutting_plate)
    
    ring_obj = doc.addObject("Part::Feature", "CompressionRing")
    ring_obj.Shape = split_ring
    ring_obj.ViewObject.ShapeColor = (0.9, 0.9, 0.9)
    ring_obj.ViewObject.Transparency = 20
    
    return ring_obj, plate_obj


# ============================================================================
# MAIN
# ============================================================================

def main():
    print("=" * 70)
    print("CAP - CORRECTED RING DIMENSIONS AND POSITION")
    print("=" * 70)
    print(f"\nDesign Logic:")
    print(f"  1. Ring HEAD with teeth: {RING_HEAD_WITH_TEETH:.1f}mm")
    print(f"  2. Required cutout at entry: {diameter_at_entry:.1f}mm (ring + {CUTOUT_CLEARANCE}mm clearance)")
    print(f"  3. Z_ENTRY calculated: {Z_ENTRY:.2f}mm (where cutout = {diameter_at_entry:.1f}mm)")
    print(f"  4. Ring HEAD positioned at Z_ENTRY")
    print()
    print(f"Cutout Dimensions:")
    print(f"  Z_exit: {Z_EXIT:.2f}mm, diameter: {diameter_at_exit}mm")
    print(f"  Z_entry: {Z_ENTRY:.2f}mm, diameter: {diameter_at_entry:.1f}mm")
    print(f"  Z_sphere_bottom: {Z_SPHERE_BOTTOM:.2f}mm, diameter: {Z_SPHERE_ENTRY_DIAMETER:.2f}mm")
    print()
    print(f"Ring Position:")
    print(f"  HEAD: {RING_HEAD_Z:.2f}mm")
    print(f"  BASE: {RING_BASE_Z:.2f}mm")
    print()
    
    line = create_line()
    sphere, cone = create_sphere_with_cone()
    ring, plate = create_compression_ring_with_ridges()
    
    print("Ring now fits cutout with proper clearance!")
    print()
    
    App.ActiveDocument.recompute()
    if App.GuiUp:
        import FreeCADGui
        FreeCADGui.SendMsgToActiveView("ViewFit")


if __name__ == '__main__':
    main()