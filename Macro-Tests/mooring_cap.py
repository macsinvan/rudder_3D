"""
FreeCAD Script: Mooring Line Cap with Compression Ring
- Sphere with conical cutout
- Split compression ring with ratchet teeth and internal ridges
- Ring sized to fit cutout with clearance
"""

import FreeCAD as App
import Part
import math

# ============================================================================
# DESIGN PARAMETERS
# ============================================================================

# Primary dimensions
LINE_DIA = 12.0
SPHERE_RATIO = 2.5
TAPER_ANGLE = 3.5
GAP_WIDTH = 2.0
WALL_THICKNESS = 3.0

# Internal ridges (grip rope)
RIDGE_HEIGHT = 0.5
RIDGE_SPACING = 3.0
RIDGE_WIDTH = 0.5

# External ratchet teeth (one-way lock)
RATCHET_TOOTH_HEIGHT = 0.5
RATCHET_TOOTH_SPACING = 2.0
RATCHET_TOOTH_WIDTH = 0.5

# Clearances
CUTOUT_CLEARANCE = 1.0
LINE_LENGTH = 100.0  # Visualization only

# ============================================================================
# CALCULATED DIMENSIONS
# ============================================================================

# Sphere
SPHERE_OUTER_DIA = LINE_DIA * SPHERE_RATIO
SPHERE_RADIUS = SPHERE_OUTER_DIA / 2.0

# Ring dimensions
FERRULE_LENGTH = SPHERE_RADIUS
taper_rad = math.radians(TAPER_ANGLE)
radius_increase = FERRULE_LENGTH * math.tan(taper_rad)

RING_INNER_DIA = LINE_DIA
RING_HEAD_OUTER_DIA = RING_INNER_DIA + (2 * WALL_THICKNESS)
RING_BASE_OUTER_DIA = RING_HEAD_OUTER_DIA + (2 * radius_increase)

RING_HEAD_WITH_TEETH = RING_HEAD_OUTER_DIA + (2 * RATCHET_TOOTH_HEIGHT)
RING_BASE_WITH_TEETH = RING_BASE_OUTER_DIA + (2 * RATCHET_TOOTH_HEIGHT)

# Cutout dimensions
Z_EXIT = math.sqrt(SPHERE_RADIUS**2 - (LINE_DIA/2.0)**2)
diameter_at_exit = LINE_DIA

ENTRY_DIA = RING_HEAD_WITH_TEETH + CUTOUT_CLEARANCE
Z_ENTRY = -math.sqrt(SPHERE_RADIUS**2 - (ENTRY_DIA/2.0)**2)
diameter_at_entry = ENTRY_DIA

Z_SPHERE_BOTTOM = -SPHERE_RADIUS

# Linear interpolation for cone extension
radius_at_exit = diameter_at_exit / 2.0
radius_at_entry = diameter_at_entry / 2.0
radius_at_sphere_bottom = radius_at_exit + (radius_at_entry - radius_at_exit) * \
                         (Z_SPHERE_BOTTOM - Z_EXIT) / (Z_ENTRY - Z_EXIT)
Z_SPHERE_ENTRY_DIAMETER = 2 * radius_at_sphere_bottom

CONE_HEIGHT = Z_EXIT - Z_SPHERE_BOTTOM

# Ring positioning
RING_HEAD_Z = Z_ENTRY
RING_BASE_Z = RING_HEAD_Z - FERRULE_LENGTH

# ============================================================================
# GEOMETRY CREATION
# ============================================================================

def create_line():
    """Mooring line cylinder"""
    doc = App.ActiveDocument or App.newDocument("MooringCap")
    
    line = Part.makeCylinder(
        LINE_DIA / 2.0,
        LINE_LENGTH,
        App.Vector(0, 0, -LINE_LENGTH/2),
        App.Vector(0, 0, 1)
    )
    
    line_obj = doc.addObject("Part::Feature", "Line")
    line_obj.Shape = line
    line_obj.ViewObject.ShapeColor = (0.6, 0.4, 0.2)
    
    return line_obj


def create_ratchet_tooth_ring(z_position, outer_radius):
    """Single ratchet tooth ring - asymmetric sawtooth for one-way locking"""
    peak_offset = RATCHET_TOOTH_WIDTH * 0.7  # 70% ramp, 30% catch
    
    base_top = App.Vector(outer_radius, 0, z_position)
    peak = App.Vector(outer_radius + RATCHET_TOOTH_HEIGHT, 0, z_position - peak_offset)
    base_bottom = App.Vector(outer_radius, 0, z_position - RATCHET_TOOTH_WIDTH)
    
    edge1 = Part.LineSegment(base_top, peak).toShape()
    edge2 = Part.LineSegment(peak, base_bottom).toShape()
    edge3 = Part.LineSegment(base_bottom, base_top).toShape()
    
    wire = Part.Wire([edge1, edge2, edge3])
    face = Part.Face(wire)
    
    return face.revolve(App.Vector(0, 0, 0), App.Vector(0, 0, 1), 360)


def create_sphere_with_cone():
    """Sphere with conical cutout and ratchet grooves"""
    doc = App.ActiveDocument
    
    solid_sphere = Part.makeSphere(SPHERE_RADIUS)
    
    # Top cylinder hole
    top_hole = Part.makeCylinder(
        LINE_DIA / 2.0,
        SPHERE_RADIUS - Z_EXIT + 5,
        App.Vector(0, 0, Z_EXIT),
        App.Vector(0, 0, 1)
    )
    
    # Conical cutout
    cone_cutout = Part.makeCone(
        diameter_at_exit / 2.0,
        Z_SPHERE_ENTRY_DIAMETER / 2.0,
        CONE_HEIGHT,
        App.Vector(0, 0, Z_EXIT),
        App.Vector(0, 0, -1)
    )
    
    # Add ratchet grooves
    num_teeth = int(CONE_HEIGHT / RATCHET_TOOTH_SPACING)
    ratchet_grooves = None
    
    for i in range(num_teeth):
        z_pos = Z_EXIT - (i * RATCHET_TOOTH_SPACING) - RATCHET_TOOTH_WIDTH/2
        
        if z_pos > Z_SPHERE_BOTTOM:
            t = (Z_EXIT - z_pos) / CONE_HEIGHT
            cutout_radius = radius_at_exit + t * (radius_at_sphere_bottom - radius_at_exit)
            groove = create_ratchet_tooth_ring(z_pos, cutout_radius)
            
            ratchet_grooves = groove if ratchet_grooves is None else ratchet_grooves.fuse(groove)
    
    if ratchet_grooves:
        cone_cutout = cone_cutout.fuse(ratchet_grooves)
    
    # Create visible cutter
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
    """Single internal ridge ring for rope grip"""
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
    
    return face.revolve(App.Vector(0, 0, 0), App.Vector(0, 0, 1), 360)


def create_compression_ring():
    """Compression ring with internal ridges, external ratchet teeth, and split"""
    doc = App.ActiveDocument
    
    # Base tapered ring
    ring_cone = Part.makeCone(
        RING_HEAD_OUTER_DIA / 2.0,
        RING_BASE_OUTER_DIA / 2.0,
        FERRULE_LENGTH,
        App.Vector(0, 0, RING_HEAD_Z),
        App.Vector(0, 0, -1)
    )
    
    # Hollow for line
    line_hole = Part.makeCylinder(
        RING_INNER_DIA / 2.0,
        FERRULE_LENGTH + 2,
        App.Vector(0, 0, RING_HEAD_Z + 1),
        App.Vector(0, 0, -1)
    )
    
    hollow_ring = ring_cone.cut(line_hole)
    
    # Add internal ridges
    num_ridges = int(FERRULE_LENGTH / RIDGE_SPACING)
    ridges_combined = None
    
    for i in range(num_ridges):
        z_pos = RING_HEAD_Z - (i * RIDGE_SPACING) - RIDGE_SPACING/2
        if z_pos > RING_BASE_Z:
            ridge = create_ridge_ring(z_pos)
            ridges_combined = ridge if ridges_combined is None else ridges_combined.fuse(ridge)
    
    if ridges_combined:
        hollow_ring = hollow_ring.fuse(ridges_combined)
    
    # Add external ratchet teeth
    num_teeth = int(FERRULE_LENGTH / RATCHET_TOOTH_SPACING)
    ratchet_teeth = None
    
    for i in range(num_teeth):
        z_pos = RING_HEAD_Z - (i * RATCHET_TOOTH_SPACING) - RATCHET_TOOTH_WIDTH/2
        if z_pos > RING_BASE_Z:
            t = abs(z_pos - RING_HEAD_Z) / FERRULE_LENGTH
            ring_radius = (RING_HEAD_OUTER_DIA/2.0) + t * (RING_BASE_OUTER_DIA/2.0 - RING_HEAD_OUTER_DIA/2.0)
            tooth = create_ratchet_tooth_ring(z_pos, ring_radius)
            ratchet_teeth = tooth if ratchet_teeth is None else ratchet_teeth.fuse(tooth)
    
    if ratchet_teeth:
        hollow_ring = hollow_ring.fuse(ratchet_teeth)
    
    # Create split
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
    
    # Visible split plate
    plate_obj = doc.addObject("Part::Feature", "SplitPlate_Cutter")
    plate_obj.Shape = cutting_plate
    plate_obj.ViewObject.ShapeColor = (1.0, 1.0, 0.0)
    plate_obj.ViewObject.Transparency = 60
    
    # Apply split
    split_ring = hollow_ring.cut(cutting_plate)
    
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
    print("MOORING LINE CAP - Parametric Design")
    print("=" * 70)
    print(f"\nDimensions:")
    print(f"  Sphere: {SPHERE_OUTER_DIA:.1f}mm diameter")
    print(f"  Ring HEAD: {RING_HEAD_OUTER_DIA}mm outer ({RING_HEAD_WITH_TEETH:.1f}mm with teeth)")
    print(f"  Ring BASE: {RING_BASE_OUTER_DIA:.2f}mm outer ({RING_BASE_WITH_TEETH:.2f}mm with teeth)")
    print(f"\nCutout:")
    print(f"  Z_exit: {Z_EXIT:.2f}mm, diameter: {diameter_at_exit}mm")
    print(f"  Z_entry: {Z_ENTRY:.2f}mm, diameter: {diameter_at_entry:.1f}mm")
    print(f"  Extends to: {Z_SPHERE_BOTTOM:.2f}mm, diameter: {Z_SPHERE_ENTRY_DIAMETER:.2f}mm")
    print(f"\nRing Position:")
    print(f"  HEAD: {RING_HEAD_Z:.2f}mm")
    print(f"  BASE: {RING_BASE_Z:.2f}mm")
    print()
    
    create_line()
    create_sphere_with_cone()
    create_compression_ring()
    
    App.ActiveDocument.recompute()
    if App.GuiUp:
        import FreeCADGui
        FreeCADGui.SendMsgToActiveView("ViewFit")
    
    print("Design complete!")


if __name__ == '__main__':
    main()